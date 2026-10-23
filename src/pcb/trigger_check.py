#!/usr/bin/env python3
"""Handle inputs end to end: the trigger (boost) chain HB1 HS1 -> RH1 -> JH.3 -> harness -> CB1D JTR.3 -> RT1 -> TRIG_IN -> Pico pin 7, the
dial ladder (DIAL -> ADC) and the joystick switch. Checks connectivity in the generated netlists and the harness, that the sensor type
matches the GPIO type (a digital-only pin needs a digital switch), the logic levels and time constant of the trigger node, the dial ladder
levels at the ADC, and the boost-mode stress rows. Logic thresholds, Hall-switch saturation voltage and the Pico ADC pin list are
UNVERIFIED (docs/ASSUMPTIONS.md 22)."""
import json, csv, re, sys
sys.path.insert(0, "."); from sch_export import parse_net

VCC, VIL, VIH, VSAT, ILEAK = 3.3, 0.8, 2.0, 0.4, 1e-6          # RP2350 IOVDD 3.3 V thresholds, Hall-switch Vsat, input + clamp leakage (unverified)
ADC_PINS = {31: "GP26/ADC0", 32: "GP27/ADC1", 34: "GP28/ADC2"}     # Pico 2 board pins (unverified pinout from memory)
R = []
def chk(n, ok, v="", note="", warn=False): R.append(dict(check=n, result="PASS" if ok else ("WARN" if warn else "FAIL"), value=v, note=note))
def val(s):
    m = re.match(r"([\d.]+)\s*([kKmMuUnNpP]?)", s.strip()); mul = dict(k=1e3, K=1e3, M=1e6, m=1e-3, u=1e-6, U=1e-6, n=1e-9, N=1e-9, p=1e-12, P=1e-12)
    return float(m[1]) * mul.get(m[2], 1.0)
def libpart(path):
    return dict(re.findall(r'\(comp \(ref "([^"]+)"\).*?\(part "([^"]+)"\)', open(path).read()))

hc, hn = parse_net("kit_v6/HB1/PF233-HB1.net"); cc, cn = parse_net("kit_v18/CB1D/PF233-CB1D.net"); hp = libpart("kit_v6/HB1/PF233-HB1.net")
def net_of(nets, ref, pin): return next((n for n, nodes in nets.items() if any(r == ref and p == pin for r, p, _ in nodes)), None)
def on(nets, n, ref, pin): return any(r == ref and p == pin for r, p, _ in nets.get(n, []))
H = list(csv.DictReader(open("harness/HARNESS_MASTER_v2.csv")))
row = next((h for h in H if "HB1.JH.3" in json.dumps(h) and "CB1D.JTR.3" in json.dumps(h)), None)

# 1 connectivity of the trigger chain
t_hb = net_of(hn, "JH", "3"); chain = [on(hn, net_of(hn, "HS1", "3"), "RH1", "1"), on(hn, t_hb, "RH1", "2"), row is not None,
         on(cn, net_of(cn, "JTR", "3"), "RT1", "1"), all(on(cn, "TRIG_IN", r, p) for r, p in (("RT1", "2"), ("U1", "7"), ("RP1", "1"), ("CQ1", "1")))]
chk("trigger chain HS1.OUT -> RH1 -> JH.3 -> harness -> CB1D JTR.3 -> RT1 -> TRIG_IN -> U1.7 (+ RP1 pull-up, CQ1)", all(chain), str(chain), (row or {}).get("ID", ""))
# 2 sensor type versus input type
digital_pin = 7 not in ADC_PINS
chk("trigger sensor type matches the input: digital-only pin 7 needs a digital (open-drain) Hall switch", (hp.get("HS1") == "HALL_SW") or not digital_pin, hp.get("HS1"),
    "a linear Hall (SS49E) rests near VCC/2, inside the undefined logic band")
# 3 levels and time constant of TRIG_IN
Rs = val(hc["RH1"]["value"]) + val(cc["RT1"]["value"]); Rp = val(cc["RP1"]["value"]); Cq = val(cc["CQ1"]["value"])
vlow = VSAT + (VCC - VSAT) * Rs / (Rs + Rp); vhigh = VCC - ILEAK * Rp; tau = Rp * Cq
chk("trigger low level (switch on) at least 0.2 V under VIL 0.8 V", vlow <= VIL - 0.2, round(vlow, 3), f"Vsat {VSAT} + divider {Rs:.0f} / {Rs+Rp:.0f} ohm")
chk("trigger high level (switch off) at least 0.5 V over VIH 2.0 V", vhigh >= VIH + 0.5, round(vhigh, 3), f"{ILEAK*1e6:.0f} uA leakage through {Rp:.0f} ohm")
chk("trigger node time constant 0.1-5 ms (debounce without lag)", 1e-4 <= tau <= 5e-3, round(tau * 1e3, 3), "ms")
# 4 dial ladder at the ADC: HB1 RD0 pull-up, rotary positions to GND, CB1D RD1 series and RP2 pull-up
rd0 = val(hc["RD0"]["value"]); rs2 = val(cc["RD1"]["value"]); rp2 = val(cc["RP2"]["value"]); pos = {"P1": 0.0, "P2": val(hc["RD2"]["value"]), "P3": val(hc["RD3"]["value"]), "P4": val(hc["RD4"]["value"]), "open": None}
def vdial(rpos):
    if rpos is None: return VCC
    rup = 1 / (1 / rd0 + 1 / (rp2 + rs2)); return VCC * rpos / (rpos + rup)
lv = {k: round(vdial(v), 3) for k, v in pos.items()}; sep = min(abs(a - b) for i, a in enumerate(lv.values()) for b in list(lv.values())[i + 1:])
chk("dial reaches an ADC pin (DIAL_IN on U1.32)", on(cn, "DIAL_IN", "U1", "32") and 32 in ADC_PINS, ADC_PINS.get(32))
chk("dial ladder levels at the ADC separated by >= 0.3 V (incl. the CB1D pull-up)", sep >= 0.3, lv, f"min separation {sep:.2f} V; firmware thresholds must use these levels, not the HB1-only ladder")
# 5 joystick switch
js = hn.get("JOY_SW", []); chk("joystick push switch reaches the head", any(r == "JH" for r, _, _ in js), [f"{r}.{p}" for r, p, _ in js],
    "JOY_SW ends at the pull-up RSW: the 7-core cable has no spare conductor (open item, handle redesign P04)", warn=True)
# 6 boost mode stress (20 A / 400 Hz, selected by the trigger in firmware)
sb = json.load(open("kit_v22/system_budget.json")); boost = [r for r in sb["rows"] if any(w in (r["stress"] + r["part"]) for w in ("20 A", "boost"))]
chk("boost-mode stress rows (20 A / 400 Hz) all pass", all(r["status"] == "PASS" for r in boost), [(r["part"], r["margin_pct"]) for r in boost])
out = dict(checks=R, levels=dict(trig_low_V=round(vlow, 3), trig_high_V=round(vhigh, 3), tau_ms=round(tau * 1e3, 3), dial_V=lv),
           assumptions=dict(VIL=VIL, VIH=VIH, Vsat=VSAT, leak_uA=ILEAK * 1e6, adc_pins=ADC_PINS))
json.dump(out, open("kit_v22/trigger_check.json", "w"), indent=1, default=str)
for x in R: print(x["result"], x["check"], "=", x["value"], "|", x["note"][:100])
print("FAILS", sum(x["result"] == "FAIL" for x in R), "WARNS", sum(x["result"] == "WARN" for x in R), "of", len(R))
