#!/usr/bin/env python3
"""One-piece head companions (all in the shared frame, z=0 = ground-facing underside of the body):
 P04b trough lid with a 12 deg cable/lead gap at 90 deg
 P05b bay lid with yoke, seat gap at 90 deg
 P07b three PCB slot rings (3 boards in the bay)
 P11  lead + cable cover strip (face, r 37..119, azimuth 90 deg)
 + light assembly / exploded views."""
import math, json, os
import numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, phi_fold_v2 as v2
from struct import unpack
OUT = "kit_v3"; T = v2.T_SLOPE; zf = lambda r: 13.0 + (116.5 - r) * T; AL = math.atan(T)
rep = {}
def weld_clean(V, F, tol=1e-4):
    key = np.round(V / tol).astype(np.int64); _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V2 = V[idx]; F2 = inv.reshape(-1)[F]; ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2]); F2 = F2[ok]
    a, b, c = V2[F2[:, 0]], V2[F2[:, 1]], V2[F2[:, 2]]; F2 = F2[np.linalg.norm(np.cross(b - a, c - a), axis=1) > 1e-12]
    if rc.signed_volume(V2, F2) < 0: F2 = F2[:, ::-1]
    return V2, F2
def emit(name, VF, note="", weld=True):
    V, F = weld_clean(*VF) if weld else VF; gd, bad = rc.edge_manifold_check(F) if weld else (0, 0); rc.write_stl(f"{OUT}/{name}.stl", V, F, name)
    rep[name] = dict(triangles=int(len(F)), nonmanifold_edges=int(bad), bbox_mm=[round(float(x), 2) for x in (*V.min(0), *V.max(0))], note=note); return V, F
def revolve_sector(poly, a0, a1, n):
    """revolve the (r,z) polygon from angle a0 to a1 (rad), end caps included"""
    m = len(poly); ang = np.linspace(a0, a1, n)
    V = np.array([(r * math.cos(a), r * math.sin(a), z) for a in ang for (r, z) in poly]); F = []
    for k in range(n - 1):
        for j in range(m):
            j2 = (j + 1) % m; F += [[k * m + j, (k + 1) * m + j, (k + 1) * m + j2], [k * m + j, (k + 1) * m + j2, k * m + j2]]
    for i in range(1, m - 1): F += [[0, i + 1, i], [(n - 1) * m, (n - 1) * m + i, (n - 1) * m + i + 1]]
    F = np.array(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F
GAP = math.radians(6.0); A0, A1 = math.radians(90) + GAP, math.radians(90) - GAP + 2 * math.pi
# ---- P04b trough lid (parallelogram section, gap at 90 deg)
lid = [(62.5, zf(62.4) - 1.5), (70.5, zf(70.6) - 1.5), (70.5, zf(70.6)), (62.5, zf(62.4))]
emit("P04b_trough_lid_with_gap", revolve_sector(lid, A0, A1, 720), "12 deg gap at 90 deg: leads rise from the trough into the P11 strip channel")
# ---- P05b bay lid with yoke
ZL0, ZL1 = 35.6, 38.6
base = [(0.01, 33.6), (24.8, 33.6), (24.8, ZL0), (33.0, ZL0), (33.0, ZL1), (0.01, ZL1)]
VB, FB = g.revolve(base, 720)
seat = [(33.0, zf(33.0)), (36.5, zf(36.5)), (36.5, ZL1), (33.0, ZL1)]
VS, FS = revolve_sector(seat, A0, A1, 360)
def box(cx, cy, cz, lx, ly, lz):
    x = np.array([-1, 1]) * lx / 2; y = np.array([-1, 1]) * ly / 2; z = np.array([-1, 1]) * lz / 2
    V = np.array([[a, b, c] for a in x for b in y for c in z]) + [cx, cy, cz]
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
ears = [box(0, s * 21.0, ZL1 + 13.0 - 0.5, 30, 6, 27) for s in (-1, 1)]; rib = box(0, 0, ZL1 + 3.0, 30, 48, 6)
Vl, Fl = g.merge([(VB, FB), (VS, FS), rib] + ears)
emit("P05b_bay_lid_with_yoke_cable_gap", (Vl, Fl), "plug r 24.8; seat r 33-36.5 with a 12 deg gap at 90 deg for the lead/cable bundle; yoke pivot hole z=50 (drill 8.1)")
# ---- P07b three slot rings (boards at z = 6.8 / 15.8 / 24.8, 1.6 thick)
rings = [g.revolve([(19.6, zc - 0.9), (20.75, zc - 0.9), (20.75, zc + 0.9), (19.6, zc + 0.9)], 180) for zc in (6.8, 15.8, 24.8)]
emit("P07b_pcb_slot_rings_x3", g.merge(rings), "three 1.8 mm rings glued inside the liner: main board z=6.8, analog A z=15.8, analog B z=24.8 (9 mm pitch)")
# ---- P11 cover strip (azimuth 90 deg)
PHI = math.radians(90); er = np.array([math.cos(PHI), math.sin(PHI), 0.0]); et = np.array([-math.sin(PHI), math.cos(PHI), 0.0])
st = [(37.0, zf(37.0), math.sin(AL), math.cos(AL)), (116.5, zf(116.5), None, None), (119.0, 13.0, 0.0, 1.0)]
nr_m, nz_m = (math.sin(AL) + 0) / 2, (math.cos(AL) + 1) / 2; nn = math.hypot(nr_m, nz_m)
st[1] = (116.5, zf(116.5), nr_m / nn, nz_m / nn)
def prism(w0, w1, n0, n1):
    Vs = []
    for (r, z, nr, nz) in st:
        for (w, n) in ((w0, n0), (w1, n0), (w1, n1), (w0, n1)):
            Vs.append((r + n * nr) * er + w * et + np.array([0, 0, z + n * nz]))
    Vs = np.array(Vs); F = []
    for k in range(len(st) - 1):
        for j in range(4):
            j2 = (j + 1) % 4; a, b, c, d = 4 * k + j, 4 * k + j2, 4 * (k + 1) + j2, 4 * (k + 1) + j; F += [[a, b, c], [a, c, d]]
    F += [[0, 2, 1], [0, 3, 2]]; e = 4 * (len(st) - 1); F += [[e, e + 1, e + 2], [e, e + 2, e + 3]]
    F = np.array(F); return Vs, (F if rc.signed_volume(Vs, F) > 0 else F[:, ::-1])
CH_W, CH_H, WALL, ROOF = 14.0, 2.8, 1.5, 1.4
roof = prism(-(CH_W / 2 + WALL), CH_W / 2 + WALL, CH_H, CH_H + ROOF)
wl = prism(-(CH_W / 2 + WALL), -CH_W / 2, 0.0, CH_H); wr = prism(CH_W / 2, CH_W / 2 + WALL, 0.0, CH_H)
for _nm, _p in (("roof", roof), ("wall_l", wl), ("wall_r", wr)):
    assert rc.edge_manifold_check(_p[1])[1] == 0, _nm
emit("P11_lead_and_cable_cover_strip", g.merge([roof, wl, wr]), weld=False, note="3 touching shells (roof + 2 walls, each watertight); 17 mm wide strip, channel 14 x 2.8 mm; follows the face from r 37 to 116.5 then flat over the bezel to r 119, azimuth 90 deg")
json.dump(rep, open(f"{OUT}/head_parts_report.json", "w"), indent=1); print(json.dumps({k: (v["nonmanifold_edges"], v["triangles"]) for k, v in rep.items()}))
