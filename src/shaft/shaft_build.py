#!/usr/bin/env python3
"""
PHI-FOLD 233 dual-chamber power spine (all dimensions mm).  Axis = z, print upright (axis vertical) unless noted.
  Envelope 58 x 41 rounded (r 17).  Battery segments: two cartridge bores D22.4 at x = +-15.5, centre raceway.
  Electronics segment: two stacked compartments (52 x 16.8 each) for PM1 (28 x 136) and PB1 (28 x 224), separated by a 2.4 mm septum.
"""
import math, json, os
import numpy as np
import rodin_core_v4 as rc, golden_cone_head as g
OUT = "kit_v4/SHAFT"; os.makedirs(OUT, exist_ok=True); rep = {}
W, H, RR = 58.0, 41.0, 17.0
WALL = 2.4; IW, IH = W - 2 * WALL, 32.4            # internal 53.2? keep 52 x 32.4 below
IW = 52.0
BORE_D, BORE_X = 22.4, 15.5
def rrect(w, h, r, na=8):
    pts = []; cx, cy = w / 2 - r, h / 2 - r
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(na + 1):
            a = math.radians(a0 + 90 * k / na); pts.append((sx * cx + r * math.cos(a), sy * cy + r * math.sin(a)))
    return np.array(pts)
def circ(r, m, cx=0.0, cy=0.0): t = np.linspace(0, 2 * np.pi, m, endpoint=False); return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]
def ring(outer, inner, z0, z1):
    m = len(outer); assert len(inner) == m
    V = np.concatenate([np.c_[outer, np.full(m, z0)], np.c_[outer, np.full(m, z1)], np.c_[inner, np.full(m, z0)], np.c_[inner, np.full(m, z1)]])
    O0, O1, I0, I1 = (np.arange(m) + k * m for k in range(4)); n = np.roll(np.arange(m), -1); F = []
    for i in range(m):
        j = n[i]
        F += [[O0[i], O0[j], O1[j]], [O0[i], O1[j], O1[i]], [I0[j], I0[i], I1[i]], [I0[j], I1[i], I1[j]], [O0[j], O0[i], I0[i]], [O0[j], I0[i], I0[j]], [O1[i], O1[j], I1[j]], [O1[i], I1[j], I1[i]]]
    F = np.array(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F
def plate(cx, cy, cz, lx, ly, lz):
    x = np.array([-1, 1]) * lx / 2; y = np.array([-1, 1]) * ly / 2; z = np.array([-1, 1]) * lz / 2
    V = np.array([[a, b, c] for a in x for b in y for c in z]) + [cx, cy, cz]
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
def tube(ro, ri, z0, z1, cx=0.0, cy=0.0, m=72): return ring(circ(ro, m, cx, cy), circ(ri, m, cx, cy), z0, z1)
def emit(name, shells, note=""):
    bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells)
    V, F = g.merge(shells); rc.write_stl(f"{OUT}/{name}.stl", V, F, name)
    rep[name] = dict(shells=len(shells), triangles=int(len(F)), nonmanifold_edges=int(bad), bbox_mm=[round(float(x), 2) for x in (*V.min(0), *V.max(0))], note=note)
    return V, F
SPIGOT = 12.0
def spine_shell(L, spigot=True):
    inner = rrect(IW, 36.0, 15.0); shells = [ring(rrect(W, H, RR), inner, 0, L)]
    if spigot: shells.append(ring(rrect(IW - 0.5, 35.5, 14.7), rrect(IW - 5.0, 31.0, 12.2), L - 0.01, L + SPIGOT))
    return shells
# ---------------- battery segment (x3): two bores + septum + raceway walls
def battery_segment(L=165.0):
    sh = spine_shell(L)
    for sx in (-1, 1): sh.append(tube(BORE_D / 2 + 2.0, BORE_D / 2, 0, L, cx=sx * BORE_X))
    sh.append(plate(0, 0, L / 2, 2.4, 36.0, L))                           # centre septum (copper-foil shield face)
    for sx in (-1, 1): sh.append(plate(sx * 3.9, 0, L / 2, 1.6, 12.0, L))   # raceway walls (cable channel 6 x 12)
    for z in (20.0, L / 2, L - 20.0):
        sh.append(plate(0, 14.2, z, IW, 7.6, 3.0)); sh.append(plate(0, -14.2, z, IW, 7.6, 3.0))   # stiffening ribs
    return sh
for k in (1, 2, 3):
    emit(f"SH0{k}_battery_segment_165", battery_segment(), "two D22.4 cartridge bores, centre raceway 6x12, septum for foil shield; spigot on top, receives the next segment; print upright")
# ---------------- electronics segment: two stacked compartments
def electronics_segment(L=232.0):
    sh = spine_shell(L)
    sh.append(plate(0, 0, L / 2, IW, 2.4, L))                           # septum between PM1 (top) and PB1 (bottom) compartments
    for sy in (-1, 1):                                                    # sled rails: 2 per compartment
        for sx in (-1, 1): sh.append(plate(sx * 24.2, sy * 9.6, L / 2, 3.6, 2.2, L))
    sh.append(plate(0, 0, 1.5, IW, 36.0, 3.0))                          # front bulkhead with cartridge-socket windows below
    return sh
emit("SH04_electronics_segment_232", electronics_segment(), "upper compartment = PM1 sled, lower compartment = PB1 sled; septum 2.4 mm carries the foil shield; front bulkhead")
# ---------------- front cap (cartridge entry) and rear cap
def front_cap():
    L = 38.0; sh = [ring(rrect(W, H, RR), rrect(IW - 2, 34.4, 14.0), 0, L)]
    for sx in (-1, 1): sh.append(tube(BORE_D / 2 + 3.2, BORE_D / 2 + 0.2, 0, L, cx=sx * BORE_X))
    sh.append(plate(0, 0, 3.0, IW, 34.4, 6.0))
    return sh
emit("SH05_front_cap_cartridge_entry", front_cap(), "faces the head; two cartridge bores with funnel lead-in and latch windows")
def rear_cap():
    L = 30.0; sh = [ring(rrect(W, H, RR), rrect(IW - 2, 34.4, 14.0), 0, L), ring(rrect(IW - 0.5, 35.5, 14.7), rrect(IW - 5.0, 31.0, 12.2), L - 0.01, L + SPIGOT)]
    sh.append(plate(0, 0, L + SPIGOT + 1.5, IW - 4, 32.0, 3.0))
    return sh
emit("SH06_rear_cap_cable_exit", rear_cap(), "closes the electronics segment at the grip end; 3 cable grommet seats on the cap are to be drilled 8 mm")
# ---------------- cartridge parts (per cartridge: 4 segments + plug + cap)
CS_OD, CS_ID = 21.2, 19.4
emit("CT01_cartridge_sleeve_segment_121", [tube(CS_OD / 2, CS_ID / 2, 0, 121.0, m=96)], "print 4 per cartridge; butt-joined, wrapped in 2 layers of heat-shrink; holds 7S 18650 in line (cells 65 mm x 7 = 455 mm)")
def plug():
    sh = [tube(CS_OD / 2, 0.01 + 0.0, 0, 3.0, m=96), tube(CS_OD / 2, CS_ID / 2, 3.0, 30.0, m=96)]
    sh.append(plate(0, 0, 16.5, 17.0, 2.0, 27.0)); sh.append(plate(0, 0, 1.5, 19.0, 7.0, 3.0))     # contact block web + blade carrier
    return sh
emit("CT02_cartridge_contact_plug", plug(), "contact end: 4 blade slots 1.0 x 6.3 in the carrier at x = -6,-2,2,6; blade protrusion NEG 14.0 / PRE 12.2 / POS 10.6 / ID 10.6 mm (mate order NEG, PRE, POS+ID)")
emit("CT03_cartridge_rear_cap", [tube(CS_OD / 2, 0.01, 0, 3.0, m=96), tube(CS_OD / 2, CS_ID / 2, 3.0, 12.0, m=96), plate(0, 0, 5.0, 8.0, 3.0, 4.0)], "closes the cell stack; pull-tab eyelet for removal")
# ---------------- board sleds
def sled(Ls, Wb=51.6, holes=6, name="SLED"):
    sh = [plate(0, 0, 0.75, Wb, Ls, 1.5)]
    ys = np.linspace(-Ls / 2 + 10, Ls / 2 - 10, holes)
    for y in ys:
        for sx in (-1, 1): sh.append(tube(2.6, 1.15, 1.5, 3.5, cx=sx * 11.5, cy=y, m=36))     # M2.5 stand-offs, board pitch 23 mm, 28 mm board
    return sh
emit("SL01_sled_PM1_136", sled(138.0, holes=5), "PM1 carrier: 28 x 136 board on 10 stand-offs; slides into the UPPER compartment rails")
emit("SL02_sled_PB1_224", sled(226.0, holes=8), "PB1 carrier: 28 x 224 board on 16 stand-offs; slides into the LOWER compartment; add 2.5 mm thermal pad to the aluminium plate under the FETs")
# ---------------- latch slider (x2)
emit("LT01_cartridge_latch_slider", [plate(0, 0, 8.0, 10.0, 6.0, 16.0), plate(0, 0, 18.0, 4.0, 6.0, 4.0), tube(2.2, 1.0, 0.0, 6.0, cx=0, cy=0, m=36)], "push-button latch: hook engages the cartridge plug shoulder; 3 x 8 mm compression spring in the tube pocket")
json.dump(rep, open(f"{OUT}/shaft_report.json", "w"), indent=1)
print(json.dumps({k: (v["nonmanifold_edges"], v["triangles"]) for k, v in rep.items()}))
