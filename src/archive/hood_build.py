#!/usr/bin/env python3
"""H01 ferrite-tile hood carrier (experimental accessory): conical ring following the golden face at +6 mm, r 72-118, 20 radial tile pockets,
gap sector at 90 deg for the cable strip, 6 legs onto the bezel top. Tiles: MnZn 44 x 19 x 2.5 mm (buy), 20 pcs."""
import math, json
import numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, phi_fold_v2 as v2
T = v2.T_SLOPE; AL = math.atan(T); zf = lambda r: 13.0 + (116.5 - r) * T
OFF = 6.0; R0, R1 = 72.0, 118.0; BASE = 1.5; RIB = 2.9
def weld_clean(V, F, tol=1e-4):
    key = np.round(V / tol).astype(np.int64); _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V2 = V[idx]; F2 = inv.reshape(-1)[F]; ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2]); F2 = F2[ok]
    if rc.signed_volume(V2, F2) < 0: F2 = F2[:, ::-1]
    return V2, F2
def revolve_sector(poly, a0, a1, n):
    m = len(poly); ang = np.linspace(a0, a1, n); V = np.array([(r * math.cos(a), r * math.sin(a), z) for a in ang for (r, z) in poly]); F = []
    for k in range(n - 1):
        for j in range(m):
            j2 = (j + 1) % m; F += [[k * m + j, (k + 1) * m + j, (k + 1) * m + j2], [k * m + j, (k + 1) * m + j2, k * m + j2]]
    for i in range(1, m - 1): F += [[0, i + 1, i], [(n - 1) * m, (n - 1) * m + i, (n - 1) * m + i + 1]]
    F = np.array(F); F = F if rc.signed_volume(V, F) > 0 else F[:, ::-1]; return V, F
def surf(r, n): return (r + n * math.sin(AL), zf(r) + OFF + n * math.cos(AL))            # point at normal offset n above the hood base surface
GAP = math.radians(12.0); A0, A1 = math.radians(90) + GAP, math.radians(90) - GAP + 2 * math.pi
base = [surf(R0, 0), surf(R1, 0), surf(R1, BASE), surf(R0, BASE)]
shells = [revolve_sector(base, A0, A1, 720)]
for r_, w in ((R0, 1.6), (R1 - 1.6, 1.6)):                                     # inner and outer retaining rims
    pr = [surf(r_, 0), surf(r_ + w, 0), surf(r_ + w, RIB), surf(r_, RIB)]; shells.append(revolve_sector(pr, A0, A1, 720))
def rib(phi):
    er = np.array([math.cos(phi), math.sin(phi), 0.0]); et = np.array([-math.sin(phi), math.cos(phi), 0.0]); pts = []
    for r in (R0, R1):
        for (w, n) in ((-0.9, BASE - 0.01), (0.9, BASE - 0.01), (0.9, RIB), (-0.9, RIB)):
            rr, zz = surf(r, n); pts.append(rr * er + w * et + np.array([0, 0, zz]))
    V = np.array(pts); F = []
    for j in range(4): j2 = (j + 1) % 4; F += [[j, j2, 4 + j2], [j, 4 + j2, 4 + j]]
    F += [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7]]; F = np.array(F); return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
n_t = 20; ph = [2 * math.pi * (k + 0.5) / n_t for k in range(n_t)]
ph = [p for p in ph if abs(((p - math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) > GAP + 0.03]
for p in ph: shells.append(rib(p))
bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells)
V, F = g.merge(shells); rc.write_stl("kit_v5/H01_ferrite_hood_carrier.stl", V, F, "hood")
legs = []
for k in range(6):
    a = math.radians(30 + 60 * k + 15); r = 119.0; z0 = 13.0; z1 = zf(r) + OFF - 0.01
    Vl, Fl = g.revolve([(0.01, z0), (2.4, z0), (2.4, z1), (0.01, z1)], 24); Vl = Vl + np.array([r * math.cos(a), r * math.sin(a), 0]); legs.append((Vl, Fl))
Vg, Fg = g.merge(legs); rc.write_stl("kit_v5/H02_hood_legs_x6.stl", Vg, Fg, "legs")
tile_cm3 = 4.4 * 1.9 * 0.25; rep = dict(tiles=len(ph), tile_MnZn_mm="44 x 19 x 2.5", tile_mass_g_each=round(tile_cm3 * 4.9, 1), tiles_total_g=round(len(ph) * tile_cm3 * 4.9, 0),
    carrier_triangles=int(len(F)), nonmanifold_edges=int(bad), offset_above_face_mm=OFF, ring_r_mm=[R0, R1], gap_deg=24)
json.dump(rep, open("kit_v5/hood_carrier_report.json", "w"), indent=1); print(rep)
