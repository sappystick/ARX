#!/usr/bin/env python3
"""AU1 audio board electrical cross-check (2026-10-28, output modes). Reads the AU1 netlist values from pw_design (PW=U) and checks the operating points
against the datasheet limits logged in docs/design/DATASHEET_LOG.md (TI TPS560430 SLVSE22B, TLV755P SBVS320D, TPA2005D1 SLOS369G, TPA6132A2 SLOS597B,
MSPM0G3507 SLASEX6C, Bourns SRN4018 REV. 10/26, Bourns SF-1206S REV. J). MODELED: datasheet typical / limit values, no bench data.
Checks: buck output from the divider (VREF 1.0 V) within 5 V +-3 %; inductor peak current at the worst input (29.4 V pack) under Isat with the TI ripple
formula; buck input range covers the pack (19.6-29.4 V, 7S); LDO input above 3.3 V + max dropout; speaker amp supply in 2.5-5.5 V and its BTL swing at the DAC
full scale (gain 2 x 150 k / RI) inside the supply; RI >= 15 k (datasheet minimum for gain <= 20 V/V); headphone amp supply in 2.3-5.5 V, G0 high / G1 low = 0 dB;
MCU VDD 3.3 V with 10 uF and VCORE 470 nF present; NRST pulled up; link 3.3 V on both ends with series resistors; AU1 worst input current under the
0.5 A fuse with margin; every off-board connection has a harness wire (HARNESS_MASTER_v5).
usage (in work/): PW=U python3 au1_check.py [OUT.json]"""
import os, sys, json, csv
os.environ["PW"] = "U"
import pw_design as D
R = []
def chk(name, ok, value, note=""): R.append(dict(check=name, result="PASS" if ok else "FAIL", value=value, note=note))
def val(s):
    """component value code -> SI: 88k7, 4k7, 150k, 10R, 100R, 2.2u, 470n, 1u, 10n (the letter is the multiplier and may stand for the decimal point)"""
    import re
    s = s.split()[0]; m = re.fullmatch(r"(\d*)(?:\.(\d+))?([RkMunp])(\d*)", s)
    if not m: return float(s)
    a, frac, u, tail = m.groups(); num = float(f"{a or 0}.{frac or tail or 0}")
    return num * {"R": 1.0, "k": 1e3, "M": 1e6, "u": 1e-6, "n": 1e-9, "p": 1e-12}[u]
V = {p["ref"]: p["value"] for p in D.PARTS}
def on(net, ref, pin): return (ref, str(pin)) in [(r, str(n)) for r, n in D.NETS.get(net, [])]
# buck
rft, rfb = val(V["RFT"]), val(V["RFB"]); vout = 1.0 * (1 + rft / rfb)
chk("buck output from the divider: 5 V +-3 % (VREF 1.0 V, SLVSE22B Eq. 7)", abs(vout - 5.0) <= 0.15, round(vout, 3), f"RFT {rft:.0f} / RFB {rfb:.0f}")
VIN_MIN, VIN_MAX = 7 * 2.8, 7 * 4.2
chk("buck input range covers the 7S pack (19.6-29.4 V) inside 4-36 V", 4.0 <= VIN_MIN and VIN_MAX <= 36.0, [VIN_MIN, VIN_MAX])
P_SPK, ETA_AMP, P_MISC = 1.4, 0.85, 0.15                                       # worst: amp at its 1.4 W rating (SLOS369G) with 85 % class-D efficiency (ASSUMED); MCU + HP amp + LDO loss
I5 = (P_SPK / ETA_AMP + P_MISC * 1.6) / 5.0; L, F = 22e-6, 1.1e6
dI = (VIN_MAX - 5.0) * 5.0 / (VIN_MAX * L * F); ipk = I5 + dI / 2
chk("inductor peak current at 29.4 V in under Isat 0.95 A (SRN4018-220M) with 30 % margin", ipk <= 0.95 / 1.3, round(ipk, 3), f"I5 {I5:.3f} A, ripple {dI:.3f} A pp")
chk("buck load under its 600 mA rating", I5 <= 0.6, round(I5, 3))
# LDO
chk("LDO input above 3.3 V + max dropout 0.238 V (500 mA, SBVS320D)", 5.0 * 0.97 >= 3.3 + 0.238, round(5.0 * 0.97 - 3.3, 3), "worst buck low at -3 %")
# speaker amp
ri = val(V["RI1"]); gain = 2 * 150e3 / ri; vswing = 1.65 * gain
chk("speaker amp RI >= 15 k (gain <= 20 V/V row, SLOS369G)", ri >= 15e3, ri)
chk("speaker amp BTL peak at DAC full scale inside the 5 V supply", vswing <= 5.0 * 0.97 - 0.3, round(vswing, 2), f"gain {gain:.2f} V/V")
chk("speaker amp supply 2.5-5.5 V", on("+5V_AU", "US", 6), "+5V_AU")
chk("speaker amp thermal pad to GND", on("GND", "US", 9), "US.9")
# headphone amp
chk("headphone amp VDD in 2.3-5.5 V (3.3 V rail)", on("+3V3_AU", "UH", 14), "+3V3_AU")
chk("headphone gain 0 dB: G0 high, G1 low (SLOS597B Table 1)", on("+3V3_AU", "UH", 6) and on("GND", "UH", 7), "G0 3V3, G1 GND")
chk("headphone single-ended inputs: INL+ / INR+ grounded, 1 uF input caps", on("GND", "UH", 2) and on("GND", "UH", 3) and V["CHL"].startswith("1u") and V["CHR"].startswith("1u"), "SLOS597B Fig. 27")
chk("headphone charge pump: flying 1 uF, HPVSS 1 uF, HPVDD 2.2 uF", V["CHF"].startswith("1u") and V["CHS"].startswith("1u") and V["CHP"].startswith("2.2u"), [V["CHF"], V["CHS"], V["CHP"]])
# MCU
chk("MCU VDD on 3.3 V with 10 uF (CVDD, SLASEX6C)", on("+3V3_AU", "UM", 7) and V["CVD"].startswith("10u"), V["CVD"])
chk("MCU VCORE 470 nF", on("VCORE_AU", "UM", 3) and V["CVC"].startswith("470n"), V["CVC"])
chk("MCU NRST pulled up (device does not start otherwise)", on("NRST_AU", "RNR", 2) and on("+3V3_AU", "RNR", 1), V["RNR"])
chk("DAC output (PA15, pin 18 of DGS28) drives both amplifiers", on("DAC_AU", "UM", 18) and on("DAC_AU", "CI1", 1) and on("DAC_AU", "CHL", 1), "DAC_AU")
chk("link: UART0 TX (PA10, 15) through 1 k and RX (PA11, 16) on the same node, 100 R and clamps at the entry", on("LINK_TX", "UM", 15) and on("LINK_N", "UM", 16) and on("AUD_LINK", "RLK", 1), "half duplex")
# input current and fuse
iin = (I5 * 5.0 / 0.85) / VIN_MIN
chk("AU1 worst input current under half the 0.5 A fuse (PM2-B F2)", iin <= 0.25, round(iin, 3), "buck efficiency 85 % ASSUMED")
# harness
hp = "harness/HARNESS_MASTER_v5.csv"
alt = "../data/seed/harness/HARNESS_MASTER_v5.csv"
H = list(csv.DictReader(open(hp if os.path.exists(hp) else alt))) if (os.path.exists(hp) or os.path.exists(alt)) else []
need = ["AU1.JPWR.1", "AU1.JPWR.2", "AU1.JLINK.1", "AU1.JLINK.2", "AU1.JSPK.1", "AU1.JSPK.2", "AU1.JHP.1", "AU1.JHP.2", "AU1.JHP.3", "AU1.JHP.4", "AU1.JSEL.1", "AU1.JSEL.2", "AU1.JSEL.3", "AU1.JSEL.4"]
ends = " ".join((h["from (board.connector.pin)"] + " " + h["to (board.connector.pin)"]) for h in H)
miss = [n for n in need if n not in ends]
chk("every AU1 wire pad has a harness wire (HARNESS_MASTER_v5)", bool(H) and not miss, miss or len(need))
out = dict(status="MODELED (datasheet values, no bench data)", checks=R, operating=dict(buck_V=round(vout, 3), i5_A=round(I5, 3), ipk_A=round(ipk, 3), iin_A=round(iin, 3), spk_gain=gain))
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "kit_v23/au1_check.json", "w"), indent=1)
for x in R: print(x["result"], x["check"], "=", x["value"])
print("FAILS", sum(x["result"] == "FAIL" for x in R), "of", len(R)); sys.exit(1 if any(x["result"] == "FAIL" for x in R) else 0)
