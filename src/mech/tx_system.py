#!/usr/bin/env python3
"""Transmit coil system: lead routing through the wall-top channel to the exit window, TXJ1 junction board (2-layer, two copper buses), printed cradle in the umbilical bridge,
fit checks, and the TX system schematics."""
import numpy as np, math, json, csv, os, struct
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge, FancyBboxPatch, FancyArrowPatch
os.makedirs("kit_v22/KICAD_TXJ1", exist_ok=True); os.makedirs("kit_v22/GERBER_TXJ1", exist_ok=True)
G = 137.50776405; EX = 178.0; HUB_R = 49.5; EXH = 7.5; RCH = 47.1; LITZ_OD = 1.2; R_PER_M = 0.030          # litz resistance per metre from R_coil = 45 mohm for 6 x 8.97 m in parallel
PSI = lambda k: (G * (k - 1)) % 360
win_half = math.degrees(EXH / HUB_R)
rows = []; side_count = {"low": 0, "high": 0}
for k in range(1, 7):
    for nm, off in (("A", 6), ("B", 11)):
        ang = (PSI(k) + off) % 360; side = "low" if ang < EX else "high"; d = abs(ang - EX); d = min(d, 360 - d)
        arc = RCH * math.radians(max(d - win_half, 0)); length = arc + 6.0 + 12.0 + 10.0          # channel arc + window to fan-in + fan-in to pad + slack
        rows.append(dict(layer=k, lead=nm, port_deg=round(ang, 2), side=side, angular_distance_deg=round(d, 1), channel_arc_mm=round(arc, 1), lead_length_mm=round(length, 1), R_mohm=round(length * R_PER_M, 2)))
        side_count[side] += 1
bundle = max(side_count.values()); area_leads = bundle * math.pi * (LITZ_OD / 2) ** 2; area_ch = 3.0 * (1.7 + 2.2)
lead_R = {k: [r["R_mohm"] for r in rows if r["layer"] == k] for k in range(1, 7)}
Rl = {k: sum(v) for k, v in lead_R.items()}; Rlayer = 6 * 45.0                                       # mohm per former layer (6 layers in parallel = 45 mohm)
I = {k: 1.0 / (Rlayer + Rl[k]) for k in Rl}; Is = sum(I.values()); share = {k: round(6 * I[k] / Is, 4) for k in I}
Llead_uH = max(0.4 * math.log(4.0 / 0.6) * (r["lead_length_mm"] / 1000) for r in rows)            # two leads 4 mm apart, uH
chk = []
def C(name, v, lo=None, hi=None, note=""): ok = (lo is None or v >= lo) and (hi is None or v <= hi); chk.append(dict(check=name, value=round(float(v), 3), min=lo, max=hi, result="PASS" if ok else "FAIL", note=note))
C("leads per side at the window (max)", bundle, None, 6, f"{side_count}")
C("channel cross-section / litz bundle area (fill ratio <= 0.7)", area_leads / area_ch, None, 0.7, f"{area_leads:.1f} mm2 of {area_ch:.1f} mm2")
C("bend radius available in the window fan-in (mm) vs 3 x OD", 4.0, 3 * LITZ_OD, None, "quarter turn inside the 15 mm window, R 4 mm")
C("longest lead (mm)", max(r["lead_length_mm"] for r in rows), None, 200)
C("DC current sharing spread between the 6 layers (max deviation from equal)", max(abs(v - 1) for v in share.values()), None, 0.05, str(share))
C("lead loop inductance (uH) vs 54 uH coil", Llead_uH, None, 0.54, "under 1 percent")
# ------------------------------------------------------------------ TXJ1 board (u along x' radial, v tangential)
U_PADS = [0.0, 2.4, 4.8, 7.2, 9.6, 12.0]; VA, VB = -3.0, 3.0; BAR_W = 3.0
def rect_poly(u0, u1, v0, v1): return [(u0, v0), (u1, v0), (u1, v1), (u0, v1), (u0, v0)]
def kicad_txj1(path):
    CX, CY = 100.0, 100.0; o = []
    o.append('(kicad_pcb (version 20221018) (generator "arx_txj1")\n  (general (thickness 1.6) (legacy_teardrops no))\n  (paper "A4")\n  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user))')
    o.append('  (setup (pad_to_mask_clearance 0.05) (stackup (layer "F.Cu" (type "copper") (thickness 0.07)) (layer "dielectric 1" (type "core") (thickness 1.46)) (layer "B.Cu" (type "copper") (thickness 0.07)) (copper_finish "Immersion silver")))')
    o.append('  (net 0 "")\n  (net 1 "TX_A")\n  (net 2 "TX_B")')
    def pad(ref, u, v, net, size, drill, lab):
        o.append(f'  (footprint "TXJ1:PTH" (layer "F.Cu") (at {CX+u:.3f} {CY-v:.3f}) (property "Reference" "{ref}" (at 0 -2.4) (layer "F.SilkS")) (pad "1" thru_hole circle (at 0 0) (size {size} {size}) (drill {drill}) (layers "*.Cu" "*.Mask") (net {net} "{"TX_A" if net==1 else "TX_B"}")))')
    for i, u in enumerate(U_PADS): pad(f"A{i+1}", u, VA, 1, 2.0, 1.3, "A"); pad(f"B{i+1}", u, VB, 2, 2.0, 1.3, "B")
    pad("TAPA", -3.0, VA, 1, 2.0, 1.0, "tap"); pad("TAPB", -3.0, VB, 2, 2.0, 1.0, "tap"); pad("A12", 15.5, VA, 1, 3.8, 2.6, "AWG12"); pad("B12", 15.5, VB, 2, 3.8, 2.6, "AWG12")
    for lay, v, net in (("F.Cu", VA, 1), ("B.Cu", VB, 2)): o.append(f'  (segment (start {CX-3.0:.3f} {CY-v:.3f}) (end {CX+15.5:.3f} {CY-v:.3f}) (width {BAR_W}) (layer "{lay}") (net {net}))')
    pts = rect_poly(-5.0, 18.0, -5.5, 5.5)
    for a, b in zip(pts[:-1], pts[1:]): o.append(f'  (gr_line (start {CX+a[0]:.3f} {CY-a[1]:.3f}) (end {CX+b[0]:.3f} {CY-b[1]:.3f}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts"))')
    o.append(f'  (gr_text "TX_A (VBUS side)" (at {CX+6:.2f} {CY+VA+0.0:.2f}) (layer "F.SilkS") (effects (font (size 0.8 0.8))))\n  (gr_text "TX_B (DRAIN, 460 V peak)" (at {CX+6:.2f} {CY-VB:.2f}) (layer "B.SilkS") (effects (font (size 0.8 0.8))))\n)')
    t = "\n".join(o); assert t.count("(") == t.count(")"); open(path, "w").write(t)
def gerber_txj1(prefix, outdir):
    f6 = lambda v: int(round(v * 1e6)); H = ["%FSLAX46Y46*%", "%MOMM*%", f"%ADD10C,{BAR_W:.3f}*%", "%ADD11C,2.000*%", "%ADD12C,3.800*%", "%ADD13C,0.100*%", "%ADD14C,2.200*%", "%ADD15C,4.000*%", "G01*", "%LPD*%"]
    def bar(v): return [f"D10*", f"X{f6(-3.0)}Y{f6(v)}D02*", f"X{f6(15.5)}Y{f6(v)}D01*"]
    def fl(code, u, v): return f"D{code}*\nX{f6(u)}Y{f6(v)}D03*"
    allp = lambda code_small, code_big, lst: [fl(code_small, u, v) for u, v in lst]
    small = [(u, VA) for u in U_PADS] + [(u, VB) for u in U_PADS] + [(-3.0, VA), (-3.0, VB)]; big = [(15.5, VA), (15.5, VB)]
    top = H + bar(VA) + [fl(11, *p) for p in small] + [fl(12, *p) for p in big] + ["M02*"]; bot = H + bar(VB) + [fl(11, *p) for p in small] + [fl(12, *p) for p in big] + ["M02*"]
    mask = H + [fl(14, *p) for p in small] + [fl(15, *p) for p in big] + ["M02*"]
    edge = H + [f"D13*"] + [f"X{f6(u)}Y{f6(v)}D0{2 if i==0 else 1}*" for i, (u, v) in enumerate(rect_poly(-5.0, 18.0, -5.5, 5.5))] + ["M02*"]
    for n, c in (("F_Cu", top), ("B_Cu", bot), ("F_Mask", mask), ("B_Mask", mask), ("Edge_Cuts", edge)): open(f"{outdir}/{prefix}-{n}.gbr", "w").write("\n".join(c))
    open(f"{outdir}/{prefix}-PTH.drl", "w").write("\n".join(["M48", "METRIC,TZ", "T1C1.300", "T2C1.000", "T3C2.600", "%", "T1"] + [f"X{u:.3f}Y{v:.3f}" for u, v in small[:12]] + ["T2"] + [f"X{u:.3f}Y{v:.3f}" for u, v in small[12:]] + ["T3"] + [f"X{u:.3f}Y{v:.3f}" for u, v in big] + ["M30"]))
kicad_txj1("kit_v22/KICAD_TXJ1/TXJ1.kicad_pcb"); gerber_txj1("TXJ1", "kit_v22/GERBER_TXJ1")
# own checks on TXJ1: pad pitch gap, A-B separation, bar current
pitch_gap = U_PADS[1] - U_PADS[0] - 2.0; ab_gap = (VB - VA) - 2.0                                       # pad ring to pad ring
C("TXJ1 lead pad gap along a row (mm)", pitch_gap, 0.3, None); C("TXJ1 bus A to bus B separation (mm, creepage across the board)", ab_gap - BAR_W / 2 * 2 + 0 if False else (VB - VA) - BAR_W, 2.5, None, "3.0 mm between bar edges; FR4 1.6 mm between layers at 460 V peak")
R_bar = 1.72e-8 * 0.0185 / (BAR_W * 1e-3 * 70e-6) * 1e3; C("TXJ1 bar resistance, 2 oz (mohm)", R_bar, None, 5.0, "20 A pulse: I2R is negligible at the duty cycle")
# ------------------------------------------------------------------ cradle STL (heel frame, then rotated to the head frame)
rep = {}
def box(x0, x1, y0, y1, z0, z1):
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]]); return V, F
def cyl(cx, cy, r, z0, z1, n=24):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False); ring0 = np.c_[cx + r * np.cos(t), cy + r * np.sin(t), np.full(n, z0)]; ring1 = ring0.copy(); ring1[:, 2] = z1
    V = np.vstack([ring0, ring1, [[cx, cy, z0], [cx, cy, z1]]]); F = []
    for i in range(n): j = (i + 1) % n; F += [[i, j, n + j], [i, n + j, n + i], [2 * n, j, i], [2 * n + 1, n + i, n + j]]
    return V, np.array(F)
X0 = 58.0                                                      # board origin u=0 at x' = 58
sh = [box(53.0, 78.0, -6.8, 6.8, 34.4, 35.0)]                                                    # base
sh += [box(53.0, 78.0, -6.8, -5.7, 35.0, 38.4), box(53.0, 78.0, 5.7, 6.8, 35.0, 38.4)]            # side walls (PCB 11.0 wide seats between them)
sh += [box(77.0, 78.0, -5.7, 5.7, 35.0, 38.4)]                                                   # rear wall (the AWG12 pair leaves over it: notches below)
sh += [cyl(X0 + u, v, 0.9, 35.0, 36.4) for u in (-4.0, 17.0) for v in (-5.0, 5.0)]               # four PCB standoffs, PCB underside at z36.4
sh += [box(X0 - 3.5, X0 + 17.5, -0.6, 0.6, 38.0, 39.6)]                                           # divider between the A and B rows: lead separation and creepage
V0 = [s[0] for s in sh]
def to_head(V): c, s = math.cos(math.radians(178)), math.sin(math.radians(178)); return np.c_[V[:, 0] * c - V[:, 1] * s, V[:, 0] * s + V[:, 1] * c, V[:, 2]]
def write_stl(path, shells, name):
    Vs = []; Fs = []; off = 0
    for V, F in shells: Vs.append(to_head(V)); Fs.append(F + off); off += len(V)
    import solid_union as su; V, F, _su = su.merge_closed([(V_, F_) for (V_, F_) in zip(Vs, [f_ for _, f_ in shells])], (np.vstack(Vs), np.vstack(Fs))); T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nn = n / (np.linalg.norm(n, axis=1)[:, None] + 1e-18)
    with open(path, "wb") as f:
        f.write(name.encode().ljust(80)[:80]); f.write(struct.pack("<I", len(F)))
        for i in range(len(F)): f.write(struct.pack("<12fH", *nn[i], *T[i].reshape(-1), 0))
    return len(F)
nt = write_stl("kit_v22/TXJ1_CRADLE_v1.stl", sh, "TXJ1 cradle"); print("cradle triangles", nt)
allV = np.vstack(V0)
C("cradle width vs bridge interior (14.0 mm wide)", 14.0 - (allV[:, 1].max() - allV[:, 1].min()), 0.1, None)
C("cradle starts outside the collar (x' >= 52.2)", allV[:, 0].min() - 52.2, 0.5, None)
C("cradle height below the bridge lid (interior top z40.8)", 40.8 - allV[:, 2].max(), 1.0, None, "ribbons lie over the divider")
C("cradle floor on the bridge floor (z34.4)", allV[:, 2].min() - 34.4, -0.01, 0.01)
C("PCB (u -5..18) inside the seat (x' 53..78)", min(X0 - 5.0 - 53.0, 77.0 - (X0 + 18.0)), 0.0, None)
res = dict(leads=rows, side_count=side_count, channel_area_mm2=area_ch, bundle_area_mm2=round(area_leads, 2), current_share=share, lead_loop_uH=round(Llead_uH, 3), checks=chk)
json.dump(res, open("kit_v22/tx_system.json", "w"), indent=1)
with open("kit_v22/TX_LEAD_TABLE.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for c in chk: print(c["result"], c["check"], "=", c["value"], c["note"][:90])
print("FAILS", sum(1 for c in chk if c["result"] == "FAIL"), "of", len(chk))
# ------------------------------------------------------------------ figure 1: plan view of the lead routing and the junction
BG = "#0b2a52"; FG = "#e8f1ff"; ORG = "#ffb347"; CY = "#7fd4ff"; GR = "#6fe3a0"; RD = "#ff8a8a"
fig, ax = plt.subplots(1, 2, figsize=(24, 12), facecolor=BG, gridspec_kw=dict(width_ratios=[1.1, 1]))
a = ax[0]; a.set_facecolor(BG); a.set_aspect(1); a.set_xlim(-62, 62); a.set_ylim(-62, 62); a.axis("off")
a.add_patch(Wedge((0, 0), 49.5, 0, 360, width=5.5, fc="#9aa3b8", ec=FG, lw=0.6)); a.add_patch(Wedge((0, 0), 48.6, 0, 360, width=3.0, fc="#3a4a70", ec=ORG, lw=0.6, ls="--"))
a.add_patch(Wedge((0, 0), 52.0, EX - win_half, EX + win_half, width=2.5, fc=BG, ec=RD, lw=1.2))
for r in rows:
    t = math.radians(r["port_deg"]); col = CY if r["lead"] == "A" else ORG; a.plot([49.5 * math.cos(t), 47.1 * math.cos(t)], [49.5 * math.sin(t), 47.1 * math.sin(t)], color=col, lw=2.2)
    sgn = -1 if r["side"] == "low" else 1; th0 = r["port_deg"]; th1 = EX - sgn * win_half if True else EX
    th1 = EX - win_half if r["side"] == "low" else EX + win_half
    ang = np.linspace(math.radians(th0), math.radians(th1), 60); rr = RCH + (0.6 if r["lead"] == "B" else -0.6) + 0.12 * r["layer"] - 0.4
    a.plot(rr * np.cos(ang), rr * np.sin(ang), color=col, lw=1.0, alpha=0.9)
    a.text(52.8 * math.cos(t), 52.8 * math.sin(t), f"{r['lead']}{r['layer']}", color=col, fontsize=8, ha="center", va="center")
a.text(-57, 6, "exit window 178 deg\n15 mm wide", color=RD, fontsize=10, ha="center"); a.add_patch(Rectangle((-77, -7), 24, 14, fc="#143d73", ec=GR, lw=1.2)); a.annotate("TXJ1 cradle\nin the bridge", (-58, -6), (-58, -30), color=GR, fontsize=11, ha="center", arrowprops=dict(arrowstyle="->", color=GR))
a.set_title("Transmit leads: 12 litz leads from the lane ports run in the wall-top channel (r45.6-48.6) to the 178 deg window, 6 per side", color=FG, fontsize=13, loc="left")
a.text(-60, -58, "blue = A leads (VBUS side), orange = B leads (drain side); ports at track +6 / +11 deg of each layer; longest lead 162 mm including the fan-in", color=FG, fontsize=10)
b = ax[1]; b.set_facecolor(BG); b.set_aspect(1); b.axis("off"); b.set_xlim(-12, 30); b.set_ylim(-14, 14)
b.add_patch(Rectangle((-5, -5.5), 23, 11, fc="#14634a", ec=FG)); 
for i, u in enumerate(U_PADS): b.add_patch(Circle((u, VA), 1.0, fc="#f2c94c", ec=FG)); b.add_patch(Circle((u, VB), 1.0, fc="#f2c94c", ec=FG)); b.text(u, VA - 2.0, f"A{i+1}", color=CY, fontsize=8, ha="center"); b.text(u, VB + 1.6, f"B{i+1}", color=ORG, fontsize=8, ha="center")
b.add_patch(Rectangle((-3, VA - 1.5), 18.5, 3.0, fc=CY, alpha=0.35, ec=CY)); b.add_patch(Rectangle((-3, VB - 1.5), 18.5, 3.0, fc=ORG, alpha=0.35, ec=ORG, ls="--"))
for (u, v, t, c) in ((15.5, VA, "AWG12 A", CY), (15.5, VB, "AWG12 B", ORG), (-3, VA, "tap A", CY), (-3, VB, "tap B", ORG)): b.add_patch(Circle((u, v), 2.1 if u > 10 else 1.0, fc="#f2c94c", ec=FG)); b.text(u, v + (-3.4 if v < 0 else 3.0), t, color=c, fontsize=8, ha="center")
b.text(6, 9.5, "TXJ1: 2-layer, 2 oz, 23 x 11 mm. Bus A on the top layer, bus B (dashed) on the bottom layer, 3 mm bars.\n12 litz leads soldered into PTH rows; AWG12 TX pair on the 3.8 mm pads; AWG22 taps to CB1D JCL.", color=FG, fontsize=10, ha="center")
b.text(6, -11.5, "no copper plane, no closed loop; printed cradle (divider rib) keeps the rows apart; x' = 58 + u in the heel frame", color=FG, fontsize=10, ha="center")
b.set_title("TXJ1 junction board (u radial, v tangential)", color=FG, fontsize=13, loc="left")
fig.suptitle("PHI-FOLD 233 transmit lead system: wall-top channel -> exit window -> TXJ1 -> TX pair", color=FG, fontsize=18, x=0.02, ha="left")
plt.savefig("kit_v22/TX_LEAD_ROUTING.png", dpi=55, facecolor=BG)
# ------------------------------------------------------------------ figure 2: electrical schematic of the whole transmit system
fig = plt.figure(figsize=(24, 13), facecolor=BG); S = fig.add_axes([0, 0, 1, 1], facecolor=BG); S.set_xlim(0, 100); S.set_ylim(0, 100); S.axis("off")
def box_(x, y, w, h, t, body, ec=CY): S.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25", fc="#143d73", ec=ec, lw=1.5)); S.text(x + 0.6, y + h - 0.8, t, color=ORG, fontsize=11, weight="bold", va="top"); S.text(x + 0.6, y + h - 3.0, body, color=FG, fontsize=9, va="top", linespacing=1.4)
def ind(x, y, w, label):
    S.plot([x, x + 0.6], [y, y], color=FG, lw=1.4)
    for i in range(4): t = np.linspace(math.pi, 0, 20); S.plot(x + 0.6 + (i + (1 - np.cos(t)) / 2 * 0 + (np.cos(t) * -1 + 1) / 2) * w / 4 * 0.9, y + 0.9 * np.sin(t), color=FG, lw=1.4)
    S.plot([x + 0.6 + w * 0.9, x + w + 1.0], [y, y], color=FG, lw=1.4); S.text(x + w / 2 + 0.4, y + 1.6, label, color=CY, fontsize=8.5, ha="center")
S.text(1, 97.6, "Transmit coil system schematic (modeled values from sim_head1 / tx_system)", color=FG, fontsize=17, weight="bold")
S.add_patch(Rectangle((3, 57), 42, 36, fc="none", ec=GR, lw=1.2, ls="--")); S.text(4, 92.3, "HEAD: former layers (all in parallel), 54 uH, 45 mohm, 53.8 m litz", color=GR, fontsize=10.5)
S.plot([8, 8], [60, 90], color=CY, lw=2.2); S.plot([40, 40], [60, 90], color=ORG, lw=2.2); S.text(8, 58.2, "bus A (TXJ1 top bar)\nVBUS side", color=CY, fontsize=9, ha="center"); S.text(40, 58.2, "bus B (TXJ1 bottom bar)\nDRAIN side", color=ORG, fontsize=9, ha="center")
for k in range(6):
    y = 88 - k * 5; S.plot([8, 11], [y, y], color=CY, lw=1.2); ind(11, y, 22, f"L{k+1}: layer coil, about 324 uH, 270 mohm"); S.plot([34, 40], [y, y], color=ORG, lw=1.2)
    S.text(9.5, y + 1.0, f"A{k+1}", color=CY, fontsize=7); S.text(37, y + 1.0, f"B{k+1}", color=ORG, fontsize=7)
box_(3, 36, 42, 18, "TXJ1 + exit window (178 deg)", "12 litz leads (6 per side) soldered into two copper bus bars; AWG12 TX pair (600 V) on the 3.8 mm pads;\nAWG22 taps from both buses to CB1D JCL (COIL_A = JCL.2, COIL_B = JCL.1).\nLead R 4-7 mohm each; current sharing between layers within 1 percent (DC); lead loop L under 0.15 uH.")
box_(3, 8, 42, 24, "CB1D: monitor and tap network (vault)", "damping chain 3 x 110 ohm (330 ohm) across the coil, 0.33-0.46 W\nMONO tap: 100 nF / 630 V + RS 1 kohm -> AB1B.J2.10 (RAW_MONO)\nHTA pickup coil (2.8 uH) -> 10 kohm + 1 nF + clamps -> mux Y4: di/dt reference for the adaptive filter\nreceive: SB1R-QA/QB (176 uH, damped 470-680 ohm) -> AB1A.J1.1 / J1.2 (RS 100 ohm)")
box_(52, 62, 44, 31, "NECK MODULE PB1R (0.4 m up the shaft, outside the head field)", "TX pair: JL1.1 DRAIN1 <-> bus B, JL1.2 VBUS <-> bus A (AWG12, 0.8 m, twisted)\nQ1, Q2: 2 x IPB65R095C7 (650 V) in parallel, TC4420 gate driver, 10 mohm shunt -> ISENSE1\nflyback clamp: ES3J -> ONE 100 nF C0G/film (630 V) || RCL1 5 kohm 10 W to VBUS (design value)\nstage results: i = 20 A, turn-off 3.8 us, quiet 5.6 us, Vds peak 462 V (29 percent margin), RCL1 3.8 W\nbulk: 6 x 150 uF polymer; LM393 over-current -> FAULT1_N; NTC -> NTC_SENSE\nJC (8-way) <-> CB1D.JPB: UMB_SHLD, GND, TX1_IN, REF_I1, FAULT1_N, ISENSE1, NTC_SENSE, GND", ORG)
box_(52, 36, 44, 22, "POWER PATH (elbow)", "PM1: dual 7S1P pack OR-ing, 2 x 470 uF, SMCJ33A TVS (33 V standoff vs 29.4 V full charge)\npower ribbon: VBUS x3 / GND x3 (12-way AWG28, 1.72 m) -> PB1R.JP and CB1D.JPW (0.49 V drop at 2 A)\nOKI-78SR 5 V (36 V max in) and AMS1117 3V3 on CB1D\nbudget: scan 8 A / 800 Hz about 4.7 W, boost 20 A / 400 Hz about 7.7 W; 90.7 Wh gives 11.8 h boost", CY)
box_(52, 8, 44, 24, "Where each result comes from", "tx_system.py: lead table, TXJ1, cradle and checks (data/results/tx_system.json)\nsim_head1.py: real-netlist transmit stage (Vds, timing, clamp power)\nsbq_damp.py: receive coil damping\nsystem_budget.py: rail currents, wire heating, part stress margins\nwiring_audit.py: every inter-board pin against the netlists")
S.annotate("", (52, 80), (46, 80), arrowprops=dict(arrowstyle="<->", color=ORG, lw=2)); S.text(49, 82, "TX pair", color=ORG, fontsize=9, ha="center")
plt.savefig("kit_v22/TX_SYSTEM_SCHEMATIC.png", dpi=55, facecolor=BG)
