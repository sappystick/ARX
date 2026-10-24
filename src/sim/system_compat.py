#!/usr/bin/env python3
"""System compatibility matrix: every interface between the battery, the handle (upper assembly v1), the shaft, the neck module and the head,
read from the repo's own outputs and source constants. Status: OK (checked by a tool), ACTION (a known change is needed), DATA (rests on an
unverified part fact, see ASSUMPTIONS). The check fails only on an incompatibility (negative fit, wiring error, rating exceeded).
Also draws the system schematic (power, signal and TX paths with harness ids) as one figure."""
import json, re, math, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
J = lambda p: json.load(open(p))
UC, PD, WA, TC, SB, SC = J("kit_v23/upper_check.json"), J("kit_v23/power_dock_check.json"), J("kit_v22/wiring_audit.json"), J("kit_v22/trigger_check.json"), J("kit_v22/system_budget.json"), J("kit_v19/shaft_calc_v20.json")
UR = J("kit_v23/UPPER/upper_v21_report.json")["params"]; CS = J("kit_v23/config_study.json") if os.path.exists("kit_v23/config_study.json") else None
rows = []
def row(area, interface, a, b, value, status, source, action=""):
    rows.append(dict(area=area, interface=interface, side_a=a, side_b=b, value=value, status=status, source=source, action=action))
# ------------------------------------------------------------------ mechanical
npm = open("mech_v20.py").read(); m = re.search(r"socket_hi = tube\(([\d.]+), ([\d.]+),", npm); sock_id = 2 * float(m[2])
tb = UR["tube_B"]["od"]; row("mech", "tube B into the neck-module upper socket", "upper v1 tube B OD", "NPM_N1 socket_hi ID (mech_v20.py)", f"{tb} in {sock_id} (radial {(sock_id-tb)/2:.2f} mm)",
    "OK" if sock_id > tb else "FAIL", "source constants")
t = re.search(r"tunnel = ring\(rrect\(([\d.]+), ([\d.]+), [\d.]+\), rrect\(([\d.]+), ([\d.]+)", npm); tun = float(t[3])
row("mech", "coiled cords through the neck-module tunnel", "2 coiled cords OD <= 10.4 side by side", f"NPM tunnel {tun} x {tun}", f"{2*UR['cord_od']:.1f} > {tun}",
    "ACTION", "source constants", "add U10: cord end anchor at the tube B front; below it the signal runs as straight 5-core shielded cable (OD about 4.5) and the power pair ends at the NPM splice")
for c in UC["checks"]:
    if c["check"].startswith(("tube A in the top-housing socket", "telescoping overlap", "armrest tube in its socket")):
        row("mech", c["check"], "upper v1", "upper v1", c["value"], "OK" if c["result"] == "PASS" else "FAIL", "upper_check.py (meshes)")
yk = J("kit_v19/yoke_check.json"); row("mech", "lower GFRP tube, hinge, yoke, bridge to the head", "head side (unchanged)", "yoke_check.py", f"{sum(c['result'] == 'PASS' for c in yk['checks'])}/{len(yk['checks'])} checks",
    "OK" if all(c["result"] == "PASS" for c in yk["checks"]) else "FAIL", "yoke_check.py")
row("mech", "hood carrier v4 (one tile per spoke, configurations C1-C3)", "hood v3 envelope r52.6-116.1 z29.4-33.4", "v4 not generated", "-", "ACTION", "hood_axi.py variant", "generate hood_v21.py with the same envelope and run the hood, yoke and head cross-checks")
# ------------------------------------------------------------------ electrical
row("elec", "handle cord to CB1D JTR", "HB2 JH (5 conductors)", "CB1D JTR (7 pins)", f"{WA['link_pins']} link pins, errors {len(WA['errors'])}; open by design: {len(WA['open_by_design'])}",
    "ACTION" if WA["open_by_design"] else "OK", "wiring_audit.py", "CB1D revision: tie or depopulate RJX/RJY, CJX/CJY (OPEN_ITEMS 20)")
row("elec", "harness conductors vs the netlists", "HARNESS_MASTER_v3", "all netlists", f"{WA['harness_conductors']} conductors, bad {WA['harness_bad']}", "OK" if WA["harness_bad"] == 0 and not WA["errors"] else "FAIL", "wiring_audit.py")
row("elec", "pack interlock and soft start", "MT60 pin 3 loop", "PM2 Q1", str(PD["interlock_table"]["switch closed, pack seated"]) + f", ramp {PD['soft_start']['ramp_ms']} ms, inrush {PD['soft_start']['inrush_A']} A",
    "OK" if all(c["result"] == "PASS" for c in PD["checks"]) else "FAIL", "power_dock_check.py")
VMAX, VMIN = 29.4, 19.6
row("elec", "VBUS range vs CB1D input regulator", f"{VMIN}-{VMAX} V", "OKI-78SR-5 (36 V max, from memory)", f"{VMAX/36*100:.0f} % of max", "DATA", "system_budget.py", "read the OKI-78SR datasheet (C05)")
row("elec", "VBUS range vs PB1R 12 V module", f"{VMIN}-{VMAX} V", "M12 '12 V 1.5 A switching module' (input range not recorded)", "unknown", "DATA", "PB1R netlist", "choose the module; input >= 36 V and drop-out below 19.6 V")
row("elec", "VBUS vs PB1R bulk capacitors", f"{VMAX} V", "CD1-CD6 150 uF 35 V polymer tantalum", f"{VMAX/35*100:.0f} % of rating", "ACTION", "PB1R netlist; KEMET polymer-Ta guidance about 80 %",
    "use 50 V polymer/hybrid parts (as PM2) or keep 35 V only after the series datasheet allows 84 % (this predates v1: v20 also reached 29.4 V)")
ton = 54e-6 * 20 / VMIN * 1e6; row("elec", "TX on-time at the lowest pack voltage (boost 20 A)", f"{VMIN} V", "400 Hz period 2500 us", f"{ton:.1f} us", "OK", "L I / V",
    "firmware constant-current rule: ton = L I / VBUS from VBUS_SENSE")
row("elec", "trigger levels and polarity", "HB2 HS1 + RH1", "CB1D TRIG_IN (RP1 47k)", f"low {TC['levels']['trig_low_V']} V, high {TC['levels']['trig_high_V']} V",
    "OK" if all(c["result"] != "FAIL" for c in TC["checks"]) else "FAIL", "trigger_check.py", "firmware boot rule for the active-low lever")
for r_ in SB["rows"]:
    if any(k in r_["part"] for k in ("Power cord", "PM2 fuse", "Battery pack", "SMCJ33A", "OKI-78SR-5")):
        row("elec", f"stress: {r_['part']}", r_["stress"][:40], f"{r_['rating']} {r_['unit']}", f"{r_['value']} ({r_['margin_pct']} %)", "OK" if r_["status"] == "PASS" else ("DATA" if r_["status"] == "WATCH" else "FAIL"), "system_budget.py")
# ------------------------------------------------------------------ eddy rule and fields at the handle
fa = {p["where"]: p["percent_of_200mm_target_field"] for p in SC["field_along_shaft"]["points"]}
row("eddy", "metal in the handle (latch, MT60 brass, cells, optional aluminium rails)", "elbow/handle region", "field there", f"{fa.get('elbow')} % of the 200 mm target field at the elbow", "OK", "shaft_calc_v20.py",
    "keep the GFRP lower tube; no closed loops in the septum shield (slit), drain only at PM2")
# ------------------------------------------------------------------ balance and runtime vs v20
row("system", "torque about the grip vs v20 at the same reach", "upper v1", "v20", f"{UC['balance']['new_47deg_working']} vs {UC['balance']['baseline_v20_kg_m']} kg m",
    "OK" if UC["balance"]["new_47deg_working"] <= UC["balance"]["baseline_v20_kg_m"] else "FAIL", "upper_check.py")
row("system", "runtime vs v20", "7S1P P30B 75.6 Wh", "v20 90.7 Wh", f"boost {PD['runtime']['boost_h_one_pack']} vs {PD['runtime']['v20_boost_h']} h", "ACTION", "power_dock_check.py",
    "accept, carry two packs, or use the P42A 21700 pack (configuration C3)")
# ------------------------------------------------------------------ data to gather (each closes a DATA row or an assumption)
DATA = [("D044-A stem: tube ODs, housing sections, grip, armrest positions, mass by part", "measure a stem or the owner's arm; trial-print grip and cup", "ASSUMPTIONS 24"),
        ("Amass MT60 drawing: body, pin pitch, keying, mating depth, current rating", "Amass datasheet", "ASSUMPTIONS 25"),
        ("Molicel P30B / P42A datasheets: envelope, mass, continuous current, cut-offs", "Molicel PDFs", "ASSUMPTIONS 27"),
        ("7S BMS 10-15 A that fits 60 x 41 x 5.4 mm (or a resized bay)", "supplier drawing", "ASSUMPTIONS 27"),
        ("coiled cords: OD, retracted length, 356 mm stroke, conductor count, shield", "supplier drawing", "ASSUMPTIONS 27"),
        ("SO-8 P-MOSFET part: pinout, Rds(on) at -8 V, Vgs max", "datasheet", "ASSUMPTIONS 26"),
        ("Hall switch part and magnet grade: operate/release points at 6.6 / 9.1 mm", "datasheet + first-article test", "ASSUMPTIONS 22, 27"),
        ("PB1R M12 module input range; OKI-78SR maximum input", "datasheets", "ASSUMPTIONS 19"),
        ("PB1R bulk: polymer-Ta series derating at 29.4 V or a 50 V replacement", "KEMET/series datasheet", "this matrix"),
        ("coil self-capacitance and ring-down of the built TX coil and SB1R boards (with RD)", "bench", "ASSUMPTIONS 1, 14"),
        ("ADC noise (ADS8860 class) to decide gain 40 vs 100", "datasheet", "enhancement review 7"),
        ("weights of the printed parts and the pack; torque about the grip", "scale + spring balance", "ASSUMPTIONS 10, 27")]
bad = [r_ for r_ in rows if r_["status"] == "FAIL"]
summary = {s: sum(r_["status"] == s for r_ in rows) for s in ("OK", "ACTION", "DATA", "FAIL")}
json.dump(dict(rows=rows, summary=summary, data_to_gather=[dict(item=a, how=b, ref=c) for a, b, c in DATA]), open("kit_v23/system_compat.json", "w"), indent=1)
for r_ in rows: print(f"{r_['status']:6} {r_['area']:6} {r_['interface'][:58]:58} {str(r_['value'])[:60]}")
print("summary", summary)

# ------------------------------------------------------------------ system schematic (one figure)
fig, ax = plt.subplots(figsize=(17, 10)); ax.set_xlim(0, 170); ax.set_ylim(0, 100); ax.axis("off")
def blk(x, y, w, h, title, lines, fc):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec="#333", lw=1.0)); ax.text(x + 1, y + h - 1.5, title, fontsize=9, weight="bold", va="top")
    for k, l in enumerate(lines): ax.text(x + 1, y + h - 5 - 2.6 * k, l, fontsize=7, va="top")
def arrow(x0, y0, x1, y1, lab, col):
    ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", color=col, lw=1.4)); ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.8, lab, fontsize=6.5, color=col, ha="center")
P, S, T = "#c0392b", "#2c6fbb", "#7d3c98"
blk(2, 70, 26, 26, "Battery pack (U7)", ["7S1P Molicel P30B, 25.2 V nom", "29.4 V max, 19.6 V BMS cut", "BMS 7S 10-15 A", "MT60-F: 1 BAT+, 2 BAT-, 3 loop->2"], "#fbe9e7")
blk(34, 70, 30, 26, "PM2 (bottom housing)", ["J1 MT60-M leads W060-W062", "F1 5 A slow -> Q1 P-FET (S-G R1 47k,", " DZ1 15 V, R2 68k -> SW -> ILK)", "C1 220 nF soft start 19.9 ms", "SMCJ33A, 470 uF; JP VBUS/GND, JS shields"], "#fbe9e7")
blk(34, 50, 30, 15, "HB2 (top housing)", ["HS1 Hall switch <- trigger magnet", "dial ladder RD0/RD2-4", "JH 1 P3V3 2 GND 3 TRIG 4 DIAL 7 SHLD"], "#e8f0fb")
blk(2, 50, 26, 15, "Top housing controls", ["power switch SW (W063/W064)", "4-position dial", "trigger lever (active-low)"], "#e8f0fb")
blk(72, 58, 30, 34, "Shaft: tube A / tube B", ["twin cavity (septum + spacers)", "power cord 2 x AWG20 shielded", "  W001 VBUS, W002 GND, W003/W004", "  drains: cord braid + septum mesh", "signal cord 5 x AWG28 shielded", "  W013 TRIG W016 DIAL W018 GND", "  W020 SHLD W021 P3V3", "stroke 356 mm; U10 end anchor (to add)"], "#f4f4f4")
blk(110, 62, 28, 30, "NPM: PB1R (neck)", ["JP VBUS/GND (splice to CB1D JPW)", "M12 12 V module, TC4420", "Q1A/Q1B 650 V, RS1S shunt, LM393 OCP", "DC1 ES3J -> CL1A/B 100 nF -> RCL1 5k", "bulk 6 x 150 uF 35 V (ACTION 50 V)", "JL1 DRAIN1 / VBUS -> TX pair AWG12", "JC umbilical: TX1_IN REF_I1 FAULT1_N ISENSE1 NTC"], "#f3e9f7")
blk(144, 62, 24, 30, "TX coil (head)", ["TXJ1 junction", "6 formers in parallel", "54 uH, 45 mohm", "20 A boost / 8 A scan", "wall-top channel W046-W057"], "#f3e9f7")
blk(110, 8, 34, 46, "CB1D (vault)", ["JPW VBUS_IN, OKI-78SR-5, P3V3", "Pico (RP2350): TRIG_IN GP5, DIAL ADC1", "  VBUS_SENSE ADC2, mux, ADS8860 ADC", "JTR from the signal cord (5/6 open)", "JPB to PB1R JC (umbilical)", "JA / JB to AB1A / AB1B", "JLB to LB1, JHTA from HTA", "JCL COIL_A/COIL_B taps (HV)"], "#e8f0fb")
blk(150, 30, 19, 24, "AB1A / AB1B", ["RS 100 ohm, BAV199", "74LVC1G66 blank", "OPA2211 x40", "362 kHz AA filter"], "#e8f0fb")
blk(150, 4, 19, 22, "SB1R-QA / QB", ["4-layer quadrupoles", "176 uH, 10.4 ohm", "RD1/RD2 680 ohm", "on the QA top"], "#e8f0fb")
blk(72, 8, 30, 20, "LB1 / HTA (vault top)", ["LB1: 66 SK6812 LEDs, 5 V rail", "  firmware cap 0.35 A (OPEN 0)", "HTA: 2 x 1.915 turns, TX timing", "  and EMI reference"], "#e8f0fb")
arrow(28, 84, 34, 84, "MT60 (W060-W062)", P); arrow(64, 84, 72, 84, "power cord", P); arrow(102, 84, 110, 84, "VBUS/GND", P); arrow(138, 78, 144, 78, "TX pair AWG12", T)
arrow(124, 62, 124, 54, "VBUS splice + JC umbilical", P); arrow(28, 57, 34, 57, "dial", S); arrow(15, 65, 40, 70, "SW pair (grip rear channel)", P)
arrow(64, 57, 72, 64, "signal cord", S); arrow(102, 64, 110, 40, "signal cable below U10", S); arrow(150, 42, 144, 42, "SDO / control", S); arrow(159, 26, 159, 30, "QUAD-A/B pairs", S)
arrow(110, 18, 102, 18, "LED_IN, HTA_P", S)
ax.text(2, 2, "System schematic, upper assembly v1 + head v5 (power red, signal blue, TX violet). Pin-level schematics: data/kicad/sch/*.kicad_sch (9 boards); harness: HARNESS_MASTER_v3.csv. Modeled, not built.", fontsize=8)
fig.tight_layout(); fig.savefig("kit_v23/SYSTEM_SCHEMATIC_v1.png", dpi=80)
if bad: raise SystemExit(f"{len(bad)} incompatibilities")
