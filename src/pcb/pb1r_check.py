#!/usr/bin/env python3
"""PB1R cross-check against the transmit stage (Step 3c). MODELED / geometric; nothing measured.
 1 pulse path: DC resistance and stray inductance of the 20 A path (DRAIN1 JL1.1 -> FET drains, FET sources -> RS1S shunt) from the ROUTED copper, against the loop budget of tx_vbus_sweep.py
 2 return vias: vias on the shunt's ground pad and per-via pulse current / RMS
 3 shunt Kelvin: where the ISENSE1 tap (RK1.1) joins the SRC1 trace relative to the shunt pad, and the ground-reference drop between the shunt and the comparator
 4 flyback-net parts: voltage ratings listed in the BOM against the simulated stress and the repo's 630 V rule (ratings are from the BOM text, UNVERIFIED until Step 5)
 5 connectors: PB1R JC / JP / JL1 against CB1D JPB / JCL, PM2 JP and the TXJ1 pads
 6 neck-module eddy estimate: what a SOLID copper plane the size of PB1R would return at the receiver versus the hatched planes actually used
usage (inside work/): pb1r_check.py   -> kit_v22/pb1r_check.json"""
import json, math, re, heapq
import numpy as np
from sch_export import parse_net
P = json.load(open("kit_v6/PB1R/pads.json"))["pads"]; RT = json.load(open("kit_v20/route_PB1R.json"))
tx = json.load(open("kit_v23/tx_vbus.json")); R_LOOP_MOHM = tx["assumptions"]["R_loop_mohm"]
sim = {r["case"]: r for r in json.load(open("kit_v20/sim_head1.json"))["tx_stage"]}; film = sim["100 nF C0G/film"]
out = []
def C(name, ok, value, limit, note="", warn=False): out.append(dict(check=name, result=("PASS" if ok else ("WARN" if warn else "FAIL")), value=value, limit=limit, note=note))
RHO, T_OUT = 1.72e-8, 70e-6                                                      # copper, 2 oz outer layer (stackup F.Cu 0.07 mm)
pad = {(p["ref"], p["num"]): p for p in P}
# ---- routed-copper graph (nodes = rounded track vertices and pad centres)
def key(q): return (round(q[0], 2), round(q[1], 2))
adj = {}
def edge(a, b, w, layer):
    L = math.dist(a, b)
    if L < 1e-9: return
    adj.setdefault(a, []).append((b, L, w, layer)); adj.setdefault(b, []).append((a, L, w, layer))
for t in RT["tracks"]:
    pts = [key(q) for q in t["pts"]]
    for a, b in zip(pts[:-1], pts[1:]): edge(a, b, t["width"], t["layer"])
def path(src, dst, net_ok=None):
    """cheapest copper path (by length) between two points; returns (length, [(len, width)])"""
    s, d = key(src), key(dst)
    if s not in adj or d not in adj: return None
    dist = {s: 0.0}; prev = {}; h = [(0.0, s)]
    while h:
        c, u = heapq.heappop(h)
        if u == d: break
        if c > dist.get(u, 1e18): continue
        for v, L, w, ly in adj[u]:
            if c + L < dist.get(v, 1e18): dist[v] = c + L; prev[v] = (u, L, w); heapq.heappush(h, (c + L, v))
    if d not in dist: return None
    segs = []; u = d
    while u != s: pu, L, w = prev[u]; segs.append((L, w)); u = pu
    return dist[d], segs
def rl(segs):
    R = sum(RHO * (L * 1e-3) / ((w * 1e-3) * T_OUT) for L, w in segs)                            # ohm
    H = 0.2e-3                                                                                      # F.Cu to the GND plane (prepreg 0.2 mm)
    Lh = sum(4e-7 * math.pi * H / (w * 1e-3) * (L * 1e-3) for L, w in segs) * 1.5                   # strip over a plane, x1.5 for the hatched return (nH not used: henry)
    return R, Lh
# ---- 1 pulse path
res = {}
for name, a, b in (("DRAIN1 JL1.1 -> Q1A.2", ("JL1", "1"), ("Q1A", "2")), ("DRAIN1 JL1.1 -> Q1B.2", ("JL1", "1"), ("Q1B", "2")), ("SRC1 Q1A.3 -> RS1S.1", ("Q1A", "3"), ("RS1S", "1")), ("SRC1 Q1B.3 -> RS1S.1", ("Q1B", "3"), ("RS1S", "1"))):
    r_ = path((pad[a]["x"], pad[a]["y"]), (pad[b]["x"], pad[b]["y"]))
    if r_ is None: res[name] = None; continue
    Lmm, segs = r_; R, Lh = rl(segs); res[name] = dict(length_mm=round(Lmm, 1), min_width_mm=round(min(w for _, w in segs), 2), R_mohm=round(R * 1e3, 2), L_nH=round(Lh * 1e9, 2))
ok = all(v is not None for v in res.values())
C("pulse path: every 20 A segment (JL1.1 to both drains, both sources to the shunt) is connected by routed copper", ok, {k: (v["length_mm"], v["min_width_mm"]) if v else None for k, v in res.items()}, "all connected", "length mm, min width mm")
if ok:
    Rtot = (max(res["DRAIN1 JL1.1 -> Q1A.2"]["R_mohm"], res["DRAIN1 JL1.1 -> Q1B.2"]["R_mohm"]) / 2 + max(res["SRC1 Q1A.3 -> RS1S.1"]["R_mohm"], res["SRC1 Q1B.3 -> RS1S.1"]["R_mohm"]) / 2)
    Ltot = (max(res["DRAIN1 JL1.1 -> Q1A.2"]["L_nH"], res["DRAIN1 JL1.1 -> Q1B.2"]["L_nH"]) / 2 + max(res["SRC1 Q1A.3 -> RS1S.1"]["L_nH"], res["SRC1 Q1B.3 -> RS1S.1"]["L_nH"]) / 2)
    C("PB1R pulse-path copper resistance (two FET branches in parallel) under 5 % of the 113 mohm loop budget (mohm)", Rtot < 0.05 * R_LOOP_MOHM, round(Rtot, 2), round(0.05 * R_LOOP_MOHM, 2), "2 oz outer copper, widths as routed")
    dv = (Ltot * 1e-9) * (20.0 / 20e-9)
    C("stray-inductance spike at turn-off (L x di/dt, 20 A in 20 ns, gate-drive time assumed) leaves the 650 V FET margin: spike under 30 V (V)", dv < 30.0, round(dv, 1), 30.0, f"stray {Ltot:.1f} nH (strip over the hatched GND plane, x1.5); Vds peak 466 V at 29.4 V from tx_vbus.json")
    out[-1]["extra"] = dict(R_mohm=round(Rtot, 2), L_nH=round(Ltot, 1))
# ---- 2 return vias on the shunt ground pad and the bank
def vias_near(net, ref, num, rad):
    p = pad[(ref, num)]; return [v for v in RT["vias"] if v[2] == net and math.dist(v[:2], (p["x"], p["y"])) <= rad]
n_sh = len(vias_near("GND", "RS1S", "2", 3.0)); n_bank = {f"CB{i}.2": len(vias_near("GND", f"CB{i}", "2", 3.0)) for i in range(1, 10)}
I_rms = 20 * math.sqrt(tx["ton_rule"][-1]["duty_pct"] / 100 / 3)
C("shunt ground pad: at least 4 GND vias within 3 mm (pulse 20 A peak, 1.8 A rms; 5 A per via peak at most)", n_sh >= 4, n_sh, ">= 4", f"{20 / max(n_sh, 1):.1f} A peak and {I_rms / max(n_sh, 1):.2f} A rms per via; via rating from memory, UNVERIFIED")
C("each bulk capacitor ground pad has at least 2 GND vias within 3 mm", all(v >= 2 for v in n_bank.values()), n_bank, ">= 2")
# ---- 3 Kelvin
rk = pad[("RK1", "1")]; rs1 = pad[("RS1S", "1")]; rs2 = pad[("RS1S", "2")]
pk = path((rk["x"], rk["y"]), (rs1["x"], rs1["y"]))
if pk:
    Lk, sg = pk; wide = [(L, w) for L, w in sg if w >= 1.0]          # only the wide (power) segments carry the 20 A; a narrow sense track carries microamps
    Rk, _ = rl(wide) if wide else (0.0, 0.0); err = Rk * 20.0 / (0.010 * 20.0) * 100
    C("shunt Kelvin: the ISENSE1 tap (RK1.1) reaches the shunt pad over a sense track, so the 20 A power copper between tap and pad is under 5 % of the shunt voltage", err < 5.0, f"sense path {Lk:.1f} mm of which {sum(L for L, _ in wide):.1f} mm power copper, drop {Rk * 20 * 1e3:.1f} mV = {err:.1f} % of 200 mV", "< 5 %", "RK1 100 ohm into the comparator: the tap carries almost no current")
else: C("shunt Kelvin: RK1.1 is connected to the shunt pad by SRC1 copper", False, None, "connected")
u3g = pad[("U3", "4")]; dg = math.dist((rs2["x"], rs2["y"]), (u3g["x"], u3g["y"]))
Rs_h = 0.5e-3 / (1 - (1.5 / 1.8) ** 2) * 1.0      # hatched 1 oz plane: 0.5 mohm/sq / copper coverage (0.3 mm lines, 1.5 mm gaps)
Rg = Rs_h * dg / 20.0 if dg else 0.0                # crude: distance / 20 mm effective return width
err_g = Rg * 20 * 1e3
C("comparator ground reference: the GND-plane drop between the shunt's ground pad and U3 pin 4 (20 A pulse) is under 10 % of the 200 mV shunt signal (mV)", err_g < 20.0, round(err_g, 1), 20.0, f"distance {dg:.0f} mm, hatched 1 oz plane about {Rs_h * 1e3:.1f} mohm/sq over a 20 mm effective width: a one-sided estimate, NOT a field solution", warn=True)
# ---- 4 flyback-net parts
nodes = parse_net("kit_v6/PB1R/PF233-PB1R.net"); comps, nets = nodes
hv_refs = sorted({r for n in ("DRAIN1", "CLAMP1") for r, _, _ in nets[n]})
rated = {}
for r in hv_refs:
    v = comps[r]["value"]; m = re.search(r"(\d+)\s*V", v); rated[r] = (v, int(m[1]) if m else None)
low = {r: x for r, x in rated.items() if x[1] is not None and x[1] < 630}; unk = [r for r, x in rated.items() if x[1] is None]
C("parts on the flyback nets are 630 V or better (BOM text): exceptions are listed, not hidden", not low, {r: x for r, x in rated.items()}, ">= 630 V", f"below 630: {sorted(low)}; no voltage in the BOM text: {unk}; stress: capacitor peak {film['vc_peak']:.0f} V, Vds {film['Vds_peak']:.0f} V (UNVERIFIED ratings, Step 5)", warn=True)
# ---- 5 connectors
cc, cn = parse_net("kit_v18/CB1D/PF233-CB1D.net"); pc, pn = parse_net("kit_v6/PM2/PF233-PM2.net")
def pins(nets_, ref): return {p: n for n, nodes_ in nets_.items() for r, p, _ in nodes_ if r == ref}
jc, jpb = pins(nets, "JC"), pins(cn, "JPB")
C("PB1R JC (umbilical) pin names equal CB1D JPB pin names", jc == jpb, f"{len(jc)} pins", "identical", str({p: (jc.get(p), jpb.get(p)) for p in set(jc) | set(jpb) if jc.get(p) != jpb.get(p)}))
jp, pjp = pins(nets, "JP"), pins(pn, "JP")
def netset(d, names): return sorted(p for p, n in d.items() if n in names)
C("PB1R JP (power in): VBUS on pins 1-2 and GND on pins 3-4; PM2 JP supplies VBUS and GND on the same count", sorted(p for p, n in jp.items() if n == "VBUS") == ["1", "2"] and sorted(p for p, n in jp.items() if n == "GND") == ["3", "4"] and any(n == "VBUS" for n in pjp.values()) and any(n == "GND" for n in pjp.values()), {"PB1R": jp, "PM2": pjp}, "VBUS 1-2, GND 3-4")
jl = pins(nets, "JL1"); jcl = pins(cn, "JCL")
C("PB1R JL1 (coil band) pin 1 = DRAIN1, pin 2 = VBUS; CB1D JCL pin 1 = COIL_B (drain side), pin 2 = COIL_A (VBUS side); TXJ1 bus B = drain side, bus A = VBUS side", jl.get("1") == "DRAIN1" and jl.get("2") == "VBUS" and jcl.get("1") == "COIL_B" and jcl.get("2") == "COIL_A", {"JL1": jl, "JCL": jcl}, "as stated", "TXJ1: pads B12 = TX_B (bus B), A12 = TX_A (bus A), tx_system.py")
# ---- 6 neck-module eddy estimate (on-axis upper bound; sphere and disc polarizabilities, late-time first mode)
mu0, sig_au, sig_cu = 4e-7 * math.pi, 4.1e7, 5.8e7
a = (3 * 1e-3 / (4 * math.pi * 19300)) ** (1 / 3); tau_s = mu0 * sig_au * a * a / math.pi ** 2            # 1 g gold sphere
Rpl = math.sqrt(70e-3 * 70e-3 / math.pi); alpha_disc = 8 * Rpl ** 3 / (3 * mu0); alpha_sph = 2 * math.pi * a ** 3 / mu0
tg = 7e-6                                                                                                  # first gate, modeled 5.1-7.5 us
tau_solid = 17.8e-6 * (35 / 39.0)                                                                           # 1 oz D78 solid plane: 17.8 us (DESIGN_STATE 2b); thickness 2 oz here would double it
alpha_t_solid = alpha_disc * math.exp(-tg / (2 * tau_solid)) if False else alpha_disc * math.exp(-tg / tau_solid)
alpha_t_nug = alpha_sph * (6 / math.pi ** 2) * math.exp(-tg / tau_s)
geom = (150.0 / 400.0) ** 6                                                                                  # dipole on-axis: B_tx x B_rx fall as z^-6 (plane 400 mm, nugget 150 mm)
ratio_solid = alpha_t_solid / alpha_t_nug * geom
# the hatched border of the zone is a closed 0.3 mm ring of radius ~35 mm; the mesh cells are tiny loops
Lring = mu0 * 0.035 * (math.log(8 * 0.035 / 0.3e-3) - 2); Rring = RHO * 2 * math.pi * 0.035 / (0.3e-3 * 35e-6); tau_ring = Lring / Rring
alpha_ring = (math.pi * 0.035 ** 2) ** 2 / Lring * math.exp(-tg / tau_ring)
ratio_ring = alpha_ring / alpha_t_nug * geom
C("neck module at 0.4 m: a SOLID copper plane the size of PB1R would return more than a 1 g gold nugget at 150 mm (on-axis upper bound): shown, and not used", ratio_solid > 1.0, f"{ratio_solid:.1f} x the nugget", "> 1 (rejected)", f"plane 70 x 70 mm (disc-equivalent R {Rpl*1e3:.0f} mm), tau {tau_solid*1e6:.1f} us, gate {tg*1e6:.0f} us; nugget a {a*1e3:.2f} mm, tau {tau_s*1e6:.0f} us; dipole z^-6 scaling; the air template removes a static plane but not its motion with the hinge")
C("hatched planes: the closed hatch border ring (0.3 mm, r 35 mm) decays before the first gate and returns less than 1e-3 of the nugget", ratio_ring < 1e-3, f"{ratio_ring:.1e} x the nugget", "< 1e-3", f"ring L {Lring*1e9:.0f} nH, R {Rring:.2f} ohm, tau {tau_ring*1e6:.2f} us vs gate {tg*1e6:.0f} us; mesh cells (1.5 mm gaps) are smaller loops with shorter tau")
# the Step 5 bulk bank is aluminium cans (9 x phi 10 x 10.2 mm hybrid): each wall is a closed loop around the can axis. Thin cylindrical sheet: L = mu0 pi r^2 / h,
# R = 2 pi r / (sigma t h), tau = mu0 sigma r t / 2. The wall thickness is not in the Panasonic data: 1.0 mm is taken as a deliberate overestimate (ASSUMPTIONS 32)
sig_al, r_can, h_can, t_can, n_can = 3.5e7, 5.0e-3, 10.2e-3, 1.0e-3, 9
L_can = mu0 * math.pi * r_can ** 2 / h_can; tau_can = mu0 * sig_al * r_can * t_can / 2
ratio_can = n_can * (math.pi * r_can ** 2) ** 2 / L_can * math.exp(-tg / tau_can) / alpha_t_nug * geom
C("bulk-capacitor cans (9 x aluminium): return less than 1e-3 of the nugget (as the hatched planes do); WARN = listed exception, owner decision (OPEN_ITEMS 34)", ratio_can < 1e-3, f"{ratio_can:.2f} x the nugget", "< 1e-3",
  f"tau {tau_can*1e6:.0f} us (1.0 mm wall; 0.3 mm gives {mu0*sig_al*r_can*0.3e-3/2*1e6:.0f} us) vs gate {tg*1e6:.0f} us: the cans do NOT decay before the gate, so the result hardly depends on the wall. Static and rigidly mounted it is an offset for the air template; the 7343 polymer-Ta it replaces had no closed can", warn=True)
out_ = dict(checks=out, pulse_path=res, eddy=dict(ratio_solid=ratio_solid, ratio_hatch_ring=ratio_ring, tau_solid_us=tau_solid * 1e6, tau_ring_us=tau_ring * 1e6, ratio_cans=ratio_can, tau_can_us=tau_can * 1e6))
json.dump(out_, open("kit_v22/pb1r_check.json", "w"), indent=1, default=str)
for c in out: print(c["result"], c["check"][:120], "=", str(c["value"])[:90])
print("FAILS", sum(c["result"] == "FAIL" for c in out), "WARNS", sum(c["result"] == "WARN" for c in out), "of", len(out))
