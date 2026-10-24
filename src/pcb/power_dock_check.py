#!/usr/bin/env python3
"""PM2 battery-dock power path (upper assembly v1), computed from the generated PM2 netlist and the PB1R / CB1D netlists: interlock truth table
(Q1 conducts only with the pack seated AND the power switch closed), gate drive over the pack voltage range, soft-start ramp and inrush into the
real bus capacitance, voltage ratings, cord drop, runtime of a 7S1P Molicel P30B pack. Cell, MOSFET, BMS and connector figures are
ASSUMPTIONS 24-26 (datasheets not opened in this container)."""
import json, re, itertools, os
import numpy as np
from sch_export import parse_net
R = []
def chk(n, ok, v="", note=""): R.append(dict(check=n, result="PASS" if ok else "FAIL", value=v, note=note))
def val(s):
    m = re.match(r"([\d.]+)\s*([kKmMuUnNpP]?)", s.strip()); return float(m[1]) * dict(k=1e3, K=1e3, M=1e6, m=1e-3, u=1e-6, U=1e-6, n=1e-9, N=1e-9, p=1e-12, P=1e-12).get(m[2], 1.0)
pc, pn = parse_net("kit_v6/PM2/PF233-PM2.net")
NS, V_NOM, V_MAX, V_UV, AH = 7, 3.6, 4.2, 2.8, 3.0                     # P30B nominal / charge cut-off; BMS under-voltage per cell; nominal capacity (unverified)
VMAX, VMIN, VNOM = NS * V_MAX, NS * V_UV, NS * V_NOM
# 1 interlock truth table: DC paths through resistors and the two external contacts (switch J3, pack loop ILK-GND); capacitors and the zener open
def node_of(ref, pin): return next(n for n, nodes in pn.items() if any(r == ref and p == pin for r, p, _ in nodes))
def conducts(switch_closed, pack_seated):
    edges = []
    for ref, c in pc.items():
        if ref.startswith("R"): edges.append((node_of(ref, "1"), node_of(ref, "2")))
    if switch_closed: edges.append((node_of("J3", "1"), node_of("J3", "2")))
    if pack_seated: edges.append((node_of("J1", "3"), node_of("J1", "2")))           # pack MT60-F pin 3 looped to pin 2 (GND)
    comp = {n: n for n in pn}
    def f(x):
        while comp[x] != x: comp[x] = comp[comp[x]]; x = comp[x]
        return x
    gnd_path = False
    # Q1 is on when the gate has a resistive path to GND (then R1/R2 divide the pack voltage); R1 alone ties it to the source
    adj = {}
    for a, b in edges: adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
    seen, todo = {"Q1_G"}, ["Q1_G"]
    while todo:
        x = todo.pop()
        for y in adj.get(x, ()):
            if y == "BAT_F": continue                                              # R1 to the source does not turn Q1 on
            if y not in seen: seen.add(y); todo.append(y)
    return "GND" in seen
table = {f"switch {'closed' if s else 'open'}, pack {'seated' if p else 'absent'}": conducts(s, p) for s, p in itertools.product((False, True), (False, True))}
chk("interlock: Q1 conducts only with the pack seated AND the switch closed", table == {"switch open, pack absent": False, "switch open, pack seated": False, "switch closed, pack absent": False, "switch closed, pack seated": True}, table)
# 2 gate drive
R1, R2, R3, C1 = val(pc["R1"]["value"]), val(pc["R2"]["value"]), val(pc["R3"]["value"]), val(pc["C1"]["value"]); VZ = val(pc["DZ1"]["value"].split("V")[0])
vgs = lambda v: v * R1 / (R1 + R2)
chk("gate drive at full charge 29.4 V below the 15 V zener and the 20 V Vgs limit (V)", vgs(VMAX) < VZ < 20.0, round(vgs(VMAX), 2))
chk("gate drive at the BMS cut-off 19.6 V above the -4.5 V logic-level rating (V)", vgs(VMIN) >= 4.5, round(vgs(VMIN), 2))
# 3 soft start: Miller plateau at about 3 V; gate current through R2 minus R1 charges C1; load = every capacitor on the bus (PM2 + PB1R + CB1D input)
VPL = 3.0
cap = sum(val(c["value"].split()[0]) for r, c in pc.items() if r.startswith("C") and node_of(r, "1") == "VBUS" and node_of(r, "2") == "GND")
rc, rn = parse_net("kit_v6/PB1R/PF233-PB1R.net" if os.path.exists("kit_v6/PB1R/PF233-PB1R.net") else "legacy/PHIFOLD233_KIT_v6_ARCHITECTURE/PB1R/PF233-PB1R.net"); cc_, cn_ = parse_net("kit_v18/CB1D/PF233-CB1D.net")
def bus_caps(comps, nets, busnames):
    tot = 0.0
    for ref, c in comps.items():
        if not ref.startswith("C"): continue
        ns = {n for n, nodes in nets.items() if any(r == ref for r, _, _ in nodes)}
        if ns & busnames and "GND" in ns: tot += val(c["value"].split()[0])
    return tot
cap_pb, cap_cb = bus_caps(rc, rn, {"VBUS"}), bus_caps(cc_, cn_, {"VBUS_IN", "VBUS"})
C_load = cap + cap_pb + cap_cb
ig = (VMAX - VPL) / R2 - VPL / R1; slew = ig / C1; t_ramp = VMAX / slew; i_in = C_load * slew
chk("soft-start ramp to full charge 5-50 ms", 5e-3 <= t_ramp <= 50e-3, round(t_ramp * 1e3, 1), f"slew {slew/1e3:.2f} V/ms")
chk("inrush into the bus capacitance below the 5 A fuse and the MT60 rating (A)", i_in <= 5.0, round(i_in, 2), f"C_load {C_load*1e6:.0f} uF (PM2 {cap*1e6:.0f}, PB1R {cap_pb*1e6:.0f}, CB1D {cap_cb*1e6:.0f})")
# 4 ratings against the pack maximum
chk("TVS stand-off above the pack maximum (V)", val(pc["DTVS"]["value"].replace("SMCJ", "").replace("A", "")) > VMAX, f"{pc['DTVS']['value']} vs {VMAX}")
chk("bulk capacitor rating >= 1.5 x pack maximum (V)", 50.0 >= 1.5 * VMAX, f"50 V vs {1.5*VMAX:.1f}")
chk("MOSFET rating >= 1.25 x pack maximum (V)", 40.0 >= 1.25 * VMAX, f"-40 V vs {1.25*VMAX:.1f}")
# 5 currents, drop and runtime
P_SCAN, P_BOOST = 4.7, 7.7                                              # system_budget.py
i_avg = P_BOOST / VMIN / 0.85; R_cord = 2 * 1.75 * 0.0333
# crude bound (earlier version of this check): the whole bank droop of one 20 A pulse recharged instantly through the cord, at the worst-case charge (BMS cut-off, loop resistance, -20 % capacitance: tx_vbus.json)
q = max(r["charge_uC"] for r in json.load(open("kit_v23/tx_vbus.json"))["ton_rule"] if r["I_A"] == 20) * 1e-6 if os.path.exists("kit_v23/tx_vbus.json") else 20.0 * 41.5e-6 / 2
droop = q / cap_pb; i_pk_bound = droop / R_cord
# time-domain model of the real chain at the BMS cut-off (largest charge per pulse): pack -> R_src (cells, BMS, F1, Q1, MT60) -> CB1 (PM2) -> cord R_cord -> PB1R bank -> coil (switched on until it reaches 20 A, 400 Hz).
# F1 and Q1 sit BEFORE CB1, so they carry the filtered current, not the cord's pulse. R_src is an assumption swept 0.10-0.30 ohm (ASSUMPTIONS 28); capacitors -20 %; cord inductance ignored (conservative peaks)
C_CB, C_PB, L_COIL, R_LOOP = cap * 0.8, cap_pb * 0.8, 54e-6, 0.113
def chain(R_src, Vp=VMIN, f=400.0, dt=1e-7, periods=8):
    n = int(periods / f / dt); vcb = vpb = Vp; iL = 0.0; on = True; steps = int(1 / f / dt); i_f = []; i_c = []
    for k in range(n):
        if k % steps == 0: on = True; iL = 0.0
        ic = (vcb - vpb) / R_cord; i_s = (Vp - vcb) / R_src
        if on:
            iL += dt * (vpb - R_LOOP * iL) / L_COIL
            if iL >= 20.0: on = False                      # the coil then freewheels into the clamp: no more bank current
        il = iL if on else 0.0
        vcb += dt * (i_s - ic) / C_CB; vpb += dt * (ic - il) / C_PB
        if k >= n - 3 * steps: i_f.append(i_s); i_c.append(ic)
    i_f, i_c = np.array(i_f), np.array(i_c)
    return dict(R_src=R_src, F1_mean=float(i_f.mean()), F1_peak=float(i_f.max()), F1_rms=float(np.sqrt((i_f ** 2).mean())), cord_peak=float(i_c.max()), cord_rms=float(np.sqrt((i_c ** 2).mean())))
sweep = [chain(r) for r in (0.10, 0.20, 0.30)]
F1_peak = max(x["F1_peak"] for x in sweep); F1_rms = max(x["F1_rms"] for x in sweep); cord_peak = max(x["cord_peak"] for x in sweep); cord_rms = max(x["cord_rms"] for x in sweep)
i_pk = F1_peak
chk("battery side (F1, Q1) at the BMS cut-off: peak under the 5 A slow fuse and RMS under 70 % of it (A)", F1_peak < 5.0 and F1_rms < 3.5, f"peak {F1_peak:.2f}, rms {F1_rms:.2f}, mean {max(x['F1_mean'] for x in sweep):.2f}", f"time-domain, R_src 0.10-0.30 ohm; the crude instant-recharge bound through the cord alone is {i_pk_bound:.2f} A")
chk("power cord (2 x AWG20) RMS under its 5 A enclosed rating at the BMS cut-off (A)", cord_rms < 5.0, f"rms {cord_rms:.2f}, peak {cord_peak:.2f}", f"pulse charge {q*1e6:.0f} uC, droop {droop:.2f} V on {cap_pb*1e6:.0f} uF nominal; cord {R_cord*1000:.0f} mohm")
chk("power-cord drop at the boost average (mV)", i_avg * R_cord * 1000 < 100, round(i_avg * R_cord * 1000, 1))
chk("Q1 dissipation from the RMS battery-side current, 15 mohm (W)", F1_rms ** 2 * 0.015 < 0.25, round(F1_rms ** 2 * 0.015, 4), "no heat sink (eddy rule: no metal sinks)")
E = NS * V_NOM * AH
run = dict(pack_Wh=round(E, 1), scan_h_one_pack=round(E / P_SCAN, 1), boost_h_one_pack=round(E / P_BOOST, 1), scan_h_two_packs=round(2 * E / P_SCAN, 1), boost_h_two_packs=round(2 * E / P_BOOST, 1),
           v20_pack_Wh=90.7, v20_boost_h=round(90.7 / P_BOOST, 1))
chk("runtime of one P30B pack in boost (h)", run["boost_h_one_pack"] >= 8.0, run["boost_h_one_pack"], f"{E:.1f} Wh vs 90.7 Wh in v20 ({run['v20_boost_h']} h)")
out = dict(checks=R, interlock_table=table, runtime=run, currents_A=dict(boost_avg=round(i_avg, 3), recharge_peak=round(i_pk, 3), F1_rms=round(F1_rms, 3), cord_peak=round(cord_peak, 2), cord_rms=round(cord_rms, 3), cord_peak_instant_bound=round(i_pk_bound, 2)), chain_sweep=sweep, gate_V=dict(at_max=round(vgs(VMAX), 2), at_min=round(vgs(VMIN), 2)), soft_start=dict(ramp_ms=round(t_ramp * 1e3, 1), inrush_A=round(i_in, 2), C_load_uF=round(C_load * 1e6)),
           assumptions=dict(cell="Molicel INR-18650-P30B: 3.0 Ah, 3.6 V nominal, 4.2 V charge, 30 A continuous, 47 g (retailer copies of the datasheet, unverified)", BMS_uv_per_cell=V_UV, miller_plateau_V=VPL, mosfet="SO-8 P-channel -40 V, 15 mohm (to be chosen)"))
os.makedirs("kit_v23", exist_ok=True); json.dump(out, open("kit_v23/power_dock_check.json", "w"), indent=1, default=str)
for x in R: print(x["result"], x["check"], "=", x["value"], "|", x["note"][:90])
print("FAILS", sum(x["result"] == "FAIL" for x in R), "of", len(R))
