#!/usr/bin/env python3
"""Board-to-harness interface check (2026-10-28): every HARNESS_MASTER_v5 conductor that ends on a board with a pads.json must
  1. land on a pad that exists, carries the harness signal's net and can take the wire: through-hole drill >= conductor diameter + 0.10 mm,
     SMD wire pad shorter side >= conductor diameter;
  2. carry its worst current at <= 10 A/mm2 of copper (ASSUMED rule for short hookup wire in a closed housing, ASSUMPTIONS 42);
     5.08 mm screw terminals (drill 1.7, 5.08 pitch): wire gauge inside the terminal's datasheet range and net voltage <= its rating;
  3. on a multi-wire connector, sit at a pad pitch >= conductor diameter + 0.5 mm (room for the insulation and a solder fillet).
Conductor diameter from the AWG formula (solid-equivalent; stranded wire is slightly larger: the 0.10 mm drill allowance covers it). Currents: worst case per signal
from the system model (system_live.json, au1_check, the LED firmware cap) or a stated estimate; signal lines 20 mA. Wires ending off-board (formers, switch, speaker,
jack, MT60, splices) and boards without a pads.json (TXJ1, AB1A / AB1B, SB1R) are listed as NOT COVERED, never passed.
MODELED / tool-checked: nothing measured. usage (in work/): python3 interface_check.py [OUT.json]"""
import csv, json, math, re, sys, os

PADS = {"CB1D": "kit_v18/CB1D/pads.json", "LB1": "kit_v18/LB1/pads.json", "AU1": "kit_v6/AU1/pads.json", "HB2": "kit_v6/HB2/pads.json",
        "PB1R": "kit_v6/PB1R/pads.json", "PM2": "kit_v6/PM2/pads.json"}
# 5.08 mm-pitch screw terminal (pw_design TERM2 / TERM4, drill 1.7): the family the design assumed, Phoenix MKDS 1,5/ 2-5,08 (order 1715721), data sheet via RS
# https://docs.rs-online.com/c702/0900766b817142b7.pdf: conductor AWG 26 ... 14, flexible 0.14-1.5 mm2, rated insulation voltage 250 V (III/3), UL 300 V / 10 A
TERM = dict(awg_min_n=26, awg_max_n=14, V=250.0)
HV_NETS = {"DRAIN1": 460.0, "DRAIN2": 460.0, "COIL_B": 460.0}                # flyback peak (CLAUDE.md HV rule; tx_vbus_sweep Vds peak about 460 V)
J_MAX = 10.0                                                                     # A / mm2, ASSUMED (ASSUMPTIONS 42)
def awg_d(n): return 0.127 * 92 ** ((36 - n) / 39)                               # mm
SL = json.load(open("kit_v23/system_live.json"))
TX = max(g["i_rms"] for g in SL["golden"] if "i_rms" in g) if any("i_rms" in g for g in SL["golden"]) else 20.0 * math.sqrt(1 / 3)
AU1_IN = SL["au1"]["W_max"] / 19.6
# worst current per signal (A): power from the system model, audio from the amplifier ratings, everything else a 20 mA signal
I_SIG = {"VBUS_AU": AU1_IN, "SPK_P": math.sqrt(1.4 / 8), "SPK_N": math.sqrt(1.4 / 8),                       # TPA2005D1 1.4 W into 8 ohm (SLOS369G), RMS
         "HP_L": math.sqrt(0.025 / 16), "HP_R": math.sqrt(0.025 / 16),                                     # TPA6132A2 25 mW into 16 ohm (SLOS597B)
         "+5V_LED": SL["i5"]["led_cap"] + SL["i5"]["led_static"], "LED_5V": SL["i5"]["led_cap"] + SL["i5"]["led_static"]}
def current(r):
    s = r["signal"]
    if s in I_SIG: return I_SIG[s], "model"
    if "COIL" in s: return TX, "TX RMS of the whole array (system_live i_rms = I sqrt(ton f / 3), I = total coil current), worst golden case"
    if "litz" in r["spec"]: return TX / 6, "TX RMS per layer lead: six layers in parallel share the total"
    if re.search(r"VBUS|BAT|GND_P|PACK|^\+?12V|^\+?5V|\+5V|P5V", s): return None, "power cord: power_dock_check.py holds its rating check"
    return 0.02, "signal"
pads = {b: json.load(open(p))["pads"] for b, p in PADS.items() if os.path.exists(p)}
TYPES = {}                                                                      # board -> ref -> part type, from the exported BOM next to pads.json
for b, p in PADS.items():
    bom = [f for f in os.listdir(os.path.dirname(p)) if f.endswith("_BOM.csv")] if os.path.exists(os.path.dirname(p)) else []
    for r in (csv.DictReader(open(os.path.join(os.path.dirname(p), bom[0]))) if bom else []):
        for ref in r["Refs"].replace(";", " ").replace(",", " ").split(): TYPES.setdefault(b, {})[ref] = r["Type"]
rows, covered, notcov = [], 0, []
H = list(csv.DictReader(open("HARNESS_MASTER_v5.csv" if os.path.exists("HARNESS_MASTER_v5.csv") else "../data/seed/harness/HARNESS_MASTER_v5.csv")))
for r in H:
    m = re.search(r"AWG\s?(\d+)", r["spec"]); d = awg_d(int(m.group(1))) if m else (1.2 if "litz 1.2" in r["spec"] else None)
    for end in (r["from (board.connector.pin)"], r["to (board.connector.pin)"]):
        p = end.split(".")
        if len(p) != 3 or p[0] not in PADS: notcov.append(f'{r["id"]} {end[:40]}'); continue
        b, cn, pin = p
        if b not in pads: notcov.append(f'{r["id"]} {end} (pads.json missing)'); continue
        pd = next((x for x in pads[b] if x["ref"] == cn and x["num"] == pin), None); covered += 1
        res = dict(id=r["id"], end=end, signal=r["signal"], spec=r["spec"][:40], d_mm=round(d, 3) if d else None)
        if pd is None: res.update(result="FAIL", why="no such pad"); rows.append(res); continue
        if d is None: res.update(result="NOT CHECKED", why="no wire gauge in the spec (braid, mesh or a part)", net=pd["net"]); rows.append(res); continue
        net_ok = pd["net"] == r["signal"] or (pd["net"] or "").replace("+", "") == r["signal"].replace("+", "")
        term = TYPES.get(b, {}).get(cn, "").startswith("TERM")                    # part type from the board BOM (TERM2 / TERM4 = 5.08 mm screw terminal)
        if term:                                                       # 5.08 mm screw terminal: the wire clamps in the block, so its datasheet range rules, not the pin drill
            awg = int(m.group(1)) if m else None; vnet = HV_NETS.get(pd["net"], 30.0)
            fit = awg is not None and TERM["awg_max_n"] <= awg <= TERM["awg_min_n"]; res["land"] = f'5.08 terminal (AWG {TERM["awg_min_n"]}-{TERM["awg_max_n"]}, {TERM["V"]:.0f} V)'
            res["term_V_ok"] = vnet <= TERM["V"]; res["net_V"] = vnet
            if not res["term_V_ok"]: fit = False
        elif pd["tht"]: fit = pd["drill"] >= d + 0.10; res["land"] = f'drill {pd["drill"]}'
        else: fit = min(pd["w"], pd["h"]) >= d; res["land"] = f'SMD {pd["w"]} x {pd["h"]}'
        same = [x for x in pads[b] if x["ref"] == cn and x is not pd]
        pitch = min((math.hypot(x["x"] - pd["x"], x["y"] - pd["y"]) for x in same), default=99.0)
        I, src = current(r); A = math.pi / 4 * d * d if d else None
        J = I / A if (I is not None and A) else None
        res.update(net=pd["net"], net_ok=net_ok, fit=fit, pitch_mm=round(pitch, 2), pitch_ok=pitch >= d + 0.5, I_A=round(I, 3) if I is not None else None,
                   J_A_mm2=round(J, 2) if J is not None else None, J_ok=(J is None or J <= J_MAX), I_src=src)
        res["result"] = "PASS" if (fit and res["pitch_ok"] and res["J_ok"]) else "FAIL"
        res["net_note"] = "" if net_ok else "harness signal name differs from the board net (wiring_audit.py rules the net match)"
        rows.append(res)
# every screw terminal on every board against the voltage of its nets (independent of how the harness rows are written)
term_rows = []
for b, P in pads.items():
    for pd in P:
        if TYPES.get(b, {}).get(pd["ref"], "").startswith("TERM"):
            v = HV_NETS.get(pd["net"], 30.0)
            term_rows.append(dict(board=b, pad=f'{pd["ref"]}.{pd["num"]}', net=pd["net"], net_V=v, rating_V=TERM["V"], result="PASS" if v <= TERM["V"] else "FAIL"))
for t in term_rows:
    if t["result"] == "FAIL": rows.append(dict(id="TERM", end=f'{t["board"]}.{t["pad"]}', signal=t["net"], result="FAIL", why=f'{t["net_V"]:.0f} V net on a {t["rating_V"]:.0f} V terminal', d_mm=None))
fails = [x for x in rows if x["result"] == "FAIL"]
out = dict(status="MODELED / tool-checked", terminals=term_rows, rule_J_A_mm2=J_MAX, ends_checked=covered, fails=len(fails), rows=rows, not_covered=notcov,
           boards=sorted(pads))
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "kit_v23/interface_check.json", "w"), indent=1)
for x in fails: print("FAIL", x["id"], x["end"], x.get("why", ""), x.get("land"), "d", x["d_mm"], "pitch", x.get("pitch_mm"), "J", x.get("J_A_mm2"))
print(f"interface_check: {covered} board ends on {len(pads)} boards, {len(fails)} FAIL; not covered {len(notcov)} (off-board or no pads.json)")
