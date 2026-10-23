#!/usr/bin/env python3
"""
PHI-FOLD 233 v6: everything inside the head.  Inner band removed (it added only ~2 %) -> central drum cavity r < 59 mm, z 0-42.
Parts: H20 core (gallery ring + drum wall + support ledge, 4 outer-band wire windows, cable notch at 90 deg), H21 lid (potting ports, vents, cable glands, yoke),
       H22 vault liner tray, H23 vault liner lid, assembly + section drawing + potting budget.  Outer band shell comes from onepiece.py (rotated 65 deg).
"""
import math, json, os, io, contextlib
import numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, phi_fold_v2 as v2
with contextlib.redirect_stdout(io.StringIO()):
    import onepiece as OP
OUT = "kit_v6/HEAD"; os.makedirs(OUT, exist_ok=True); rep = {}
T = v2.T_SLOPE; zf = lambda r: 13.0 + (116.5 - r) * T
def weld_clean(V, F, tol=1e-4):
    key = np.round(V / tol).astype(np.int64); _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V2 = V[idx]; F2 = inv.reshape(-1)[F]; ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2]); F2 = F2[ok]
    a, b, c = V2[F2[:, 0]], V2[F2[:, 1]], V2[F2[:, 2]]; F2 = F2[np.linalg.norm(np.cross(b - a, c - a), axis=1) > 1e-12]
    if rc.signed_volume(V2, F2) < 0: F2 = F2[:, ::-1]
    return V2, F2
def emit(name, shells, note=""):
    shells = [weld_clean(V, F) for V, F in shells]; bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells)
    V, F = g.merge(shells); rc.write_stl(f"{OUT}/{name}.stl", V, F, name)
    rep[name] = dict(shells=len(shells), triangles=int(len(F)), nonmanifold_edges=int(bad), bbox_mm=[round(float(x), 2) for x in (*V.min(0), *V.max(0))], note=note); return V, F
# ---------------------------------------------------------------- H20 core
DRUM_H, LEDGE_R, LEDGE_T, DRUM_RI, DRUM_RO = 42.0, 52.5, 3.0, 59.0, 62.4
prof = [(LEDGE_R, 0.0), (72.15, 0.0), (72.15, 17.0), (70.6, zf(70.6)), (70.6, zf(70.6) - 1.5), (69.6, zf(70.6) - 1.5), (69.6, zf(70.6) - 7.5), (63.4, zf(70.6) - 7.5), (63.4, zf(62.4) - 1.5),
        (DRUM_RO, zf(62.4) - 1.5), (DRUM_RO, DRUM_H), (DRUM_RI, DRUM_H), (DRUM_RI, LEDGE_T), (LEDGE_R, LEDGE_T)]
NA = 2880; ang = np.linspace(0, 2 * np.pi, NA, endpoint=False); m = len(prof); HW = OP.HW
az_o = np.array(OP.az_o); CAB = math.radians(90.0); SLOT_HW = 7.0
def near(a, centres, R): d = np.abs((a[:, None] - np.array(centres)[None, :] + np.pi) % (2 * np.pi) - np.pi).min(1); return d < HW / R
win = near(ang, az_o, 72.0); slot = near(ang, [CAB], 60.0 * 1.0) | (np.abs(((ang - CAB + np.pi) % (2 * np.pi)) - np.pi) < SLOT_HW / 60.7)
Vr = []
for k, a in enumerate(ang):
    for i, (r_, z_) in enumerate(prof):
        rr, zz = r_, z_
        if win[k] and rr > 69.6 and i < 9: rr = 69.6                       # outer-band wire window opens onto the trough
        if slot[k] and i in (10, 11): zz = 26.0                            # cable / lead notch through the drum wall
        Vr.append((rr * math.cos(a), rr * math.sin(a), zz))
Vr = np.array(Vr); I, J = np.meshgrid(np.arange(NA), np.arange(m), indexing="ij"); I2, J2 = (I + 1) % NA, (J + 1) % m
Fr = np.concatenate([np.stack([I * m + J, I2 * m + J, I2 * m + J2], -1).reshape(-1, 3), np.stack([I * m + J, I2 * m + J2, I * m + J2], -1).reshape(-1, 3)])
V_out, F_out = OP.rotz(OP.Vo), OP.Fo
emit("H20_head_core_and_outer_band_ONE_PIECE", [(V_out, F_out), (Vr, Fr)], "outer wound band + gallery ring + drum wall (r 59-62.4, h 42) + vault ledge; 4 wire windows; cable notch at 90 deg; print base down, no supports")
# ---------------------------------------------------------------- H21 lid: flat plate with potting ports, vents, glands (grid-extracted, watertight)
LID_R, Z0, Z1, CELL = 63.2, DRUM_H, DRUM_H + 2.5, 0.4
holes = [(45 * math.cos(math.radians(a)), 45 * math.sin(math.radians(a)), 4.0) for a in (30, 150, 270)] + [(52 * math.cos(math.radians(a)), 52 * math.sin(math.radians(a)), 1.5) for a in (90, 210, 330)] + [(-24.0, 0.0, 5.0), (24.0, 0.0, 5.0)]
n = int(2 * LID_R / CELL) + 2; xs = (np.arange(n) - n / 2 + 0.5) * CELL; X, Y = np.meshgrid(xs, xs, indexing="ij")
keep = X ** 2 + Y ** 2 <= LID_R ** 2
for (hx, hy, hr) in holes: keep &= ((X - hx) ** 2 + (Y - hy) ** 2) > hr ** 2
def plate_from_mask(keep, z0, z1):
    V = []; F = []; idx = {}
    def vid(x, y, z):
        key = (round(x / CELL), round(y / CELL), round(z, 3))
        if key not in idx: idx[key] = len(V); V.append((x, y, z))
        return idx[key]
    for i in range(n):
        for j in range(n):
            if not keep[i, j]: continue
            x0, x1_, y0, y1_ = xs[i] - CELL / 2, xs[i] + CELL / 2, xs[j] - CELL / 2, xs[j] + CELL / 2
            for zz, up in ((z1, True), (z0, False)):
                a, b, c, d = vid(x0, y0, zz), vid(x1_, y0, zz), vid(x1_, y1_, zz), vid(x0, y1_, zz)
                F += [[a, b, c], [a, c, d]] if up else [[a, c, b], [a, d, c]]
            for (di, dj, p, q) in ((1, 0, (x1_, y0), (x1_, y1_)), (-1, 0, (x0, y1_), (x0, y0)), (0, 1, (x1_, y1_), (x0, y1_)), (0, -1, (x0, y0), (x1_, y0))):
                ni, nj = i + di, j + dj
                if not (0 <= ni < n and 0 <= nj < n and keep[ni, nj]):
                    a, b, c, d = vid(p[0], p[1], z0), vid(q[0], q[1], z0), vid(q[0], q[1], z1), vid(p[0], p[1], z1); F += [[a, b, c], [a, c, d]]
    return np.array(V), np.array(F)
Vl, Fl = plate_from_mask(keep, Z0, Z1)
def box(cx, cy, cz, lx, ly, lz):
    x = np.array([-1, 1]) * lx / 2; y = np.array([-1, 1]) * ly / 2; z = np.array([-1, 1]) * lz / 2
    V = np.array([[a, b, c] for a in x for b in y for c in z]) + [cx, cy, cz]
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
ears = [box(0, s * 21.0, Z1 + 13.0 - 0.5, 30, 6, 27) for s in (-1, 1)]; rib = box(0, 0, Z1 + 3.0, 30, 48, 6)
bosses = []
for (hx, hy, hr) in holes[:3]:
    Vb, Fb = g.revolve([(hr + 0.01, Z1), (hr + 3.0, Z1), (hr + 1.5, Z1 + 8.0), (hr + 0.01, Z1 + 8.0)], 48); bosses.append((Vb + np.array([hx, hy, 0]), Fb))
emit("H21_lid_with_potting_ports_glands_yoke", [(Vl, Fl), rib] + ears + bosses, "3 x D8 fill ports (tapered bosses), 3 x D3 vents, 2 x D10 cable glands at x +-24, yoke pivot hole z=58 (drill 8.1); drill nothing else; print flat")
# ---------------------------------------------------------------- H22/H23 vault liner (tiles are bonded to the OUTSIDE of the liner)
def rrect(w, h, r, na=6):
    pts = []; cx, cy = w / 2 - r, h / 2 - r
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(na + 1): a = math.radians(a0 + 90 * k / na); pts.append((sx * cx + r * math.cos(a), sy * cy + r * math.sin(a)))
    return np.array(pts)
def ring(outer, inner, z0, z1):
    mm = len(outer); V = np.concatenate([np.c_[outer, np.full(mm, z0)], np.c_[outer, np.full(mm, z1)], np.c_[inner, np.full(mm, z0)], np.c_[inner, np.full(mm, z1)]])
    O0, O1, I0, I1 = (np.arange(mm) + k * mm for k in range(4)); nn = np.roll(np.arange(mm), -1); F = []
    for i in range(mm):
        j = nn[i]; F += [[O0[i], O0[j], O1[j]], [O0[i], O1[j], O1[i]], [I0[j], I0[i], I1[i]], [I0[j], I1[i], I1[j]], [O0[j], O0[i], I0[i]], [O0[j], I0[i], I0[j]], [O1[i], O1[j], I1[j]], [O1[i], I1[j], I1[i]]]
    F = np.array(F); return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
VZ0 = LEDGE_T + 3.0                                      # vault outer bottom z = 3.0 (tile 3.0 sits on the ledge): liner floor starts at z 6.0
INNER_H = 30.0
tray = [ring(rrect(76.4, 76.4, 2.0), rrect(74.0, 74.0, 1.2), VZ0, VZ0 + INNER_H + 1.2), box(0, 0, VZ0 + 0.6, 76.4 - 1.0, 76.4 - 1.0, 1.2)]
emit("H22_vault_liner_tray", tray, "square liner 76.4 x 76.4, inner 74 x 74 x 30; tiles (MnZn 3 mm) bond to the OUTSIDE faces; boards stack inside")
lidl = [box(0, 0, 0.6, 76.4, 76.4, 1.2), ring(rrect(73.6, 73.6, 1.2), rrect(71.2, 71.2, 1.0), -3.0, 0.0)]
V23, F23 = g.merge(lidl); V23 = V23 + np.array([0, 0, VZ0 + INNER_H + 1.2]); emit("H23_vault_liner_lid", [(V23, F23)], "closing plate with 3 mm locating lip; one 6 mm corner notch is left unfilled for silicone filling and the harness exit")
# ---------------------------------------------------------------- budget numbers
cav_V = math.pi * DRUM_RI ** 2 * DRUM_H / 1000.0; vault_out = (80.4 * 80.4 * (INNER_H + 2.4 + 6.0)) / 1000.0; vault_in = 74.0 * 74.0 * INNER_H / 1000.0
tiles = dict(plates_8=(8 * 40 * 40 * 3) / 1000.0, walls_4=(4 * 80 * (INNER_H + 2.4) * 3) / 1000.0); tile_cm3 = sum(tiles.values())
boards_cm3 = 4 * (70 * 70 * 1.6) / 1000.0 + 2 * (math.pi * 20 ** 2 * 1.6) / 1000.0
bud = dict(cavity_drum_cm3=round(cav_V, 1), vault_outer_cm3=round(vault_out, 1), vault_inner_cm3=round(vault_in, 1), MnZn_tiles_cm3=round(tile_cm3, 1), MnZn_tiles_g=round(tile_cm3 * 4.9, 0),
           syntactic_foam_volume_cm3=round(cav_V - vault_out, 1), syntactic_foam_g=round((cav_V - vault_out) * 0.7, 0), silicone_volume_cm3=round(vault_in - 0.5 * vault_in * 0.35 - 60, 1))
bud["silicone_g"] = round(bud["silicone_volume_cm3"] * 1.25, 0)
bud["head_mass_estimate_g"] = dict(printed_body_lid_liner=720, wound_Litz_outer_band=320, antenna_board_SB1=260, bezel_skid=250, vault_tiles=bud["MnZn_tiles_g"], boards_and_parts=190, foam=bud["syntactic_foam_g"], silicone=bud["silicone_g"])
bud["head_mass_estimate_g"]["total"] = sum(bud["head_mass_estimate_g"].values())
bud["head_height_mm_underside_to_lid_top"] = Z1; bud["head_height_with_skid_mm"] = Z1 + 6.0
rep["budget"] = bud
# ---------------------------------------------------------------- section drawing
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(14, 5.6))
fo = OP.fo; so = np.linspace(0, fo.L, 3000); ro, zo = rc.eval_profile(fo.segs, so)[:2]
for sgn in (1, -1):
    ax.fill(sgn * ro, zo, fc="#d6dbdf", ec="#555", lw=.5); ax.fill(sgn * np.array([x for x, _ in prof]), [z for _, z in prof], fc="#aeb6bf", ec="#555", lw=.5)
    ax.add_patch(plt.Rectangle((0 if sgn > 0 else -116, -2.8), 116, 2.4, fc="#27ae60", alpha=.8)); ax.add_patch(plt.Rectangle((0 if sgn > 0 else -123, -6.0), 123, 3.0, fc="#7f8c8d"))
    ax.add_patch(plt.Rectangle((0 if sgn > 0 else -59, LEDGE_T), 59, DRUM_H - LEDGE_T, fc="#fdebd0", ec="none", alpha=.9))
ax.add_patch(plt.Rectangle((-40.2, 3.0), 80.4, 38.4 - 3.0 + 0.0, fc="#f5b7b1", ec="#c0392b", lw=1.2)); ax.add_patch(plt.Rectangle((-37.0, VZ0 + 1.2), 74.0, INNER_H, fc="#d6eaf8", ec="#1a5276", lw=1))
for k, (nm, zc, h) in enumerate((("AB1B", 9.0, 5.5), ("AB1A", 15.0, 5.5), ("CB1", 21.0, 10.2), ("PB1R", 33.0, 6.0))):
    ax.add_patch(plt.Rectangle((-35, zc), 70, 1.6, fc="#1e8449")); ax.add_patch(plt.Rectangle((-30, zc + 1.6), 60, h - 1.6, fc="#85c1e9", alpha=.8)); ax.text(0, zc + 0.3, nm, ha="center", fontsize=7, color="w")
ax.add_patch(plt.Rectangle((-63.2, DRUM_H), 126.4, 2.5, fc="#7d6608")); ax.text(0, DRUM_H + 3.2, "lid: 3 fill ports, 3 vents, 2 glands, yoke", ha="center", fontsize=7)
ax.text(-110, 36, "MnZn vault (pink)\nsilicone gel inside (blue)", fontsize=8); ax.text(-58, 46, "syntactic foam (cream) in the drum annulus", fontsize=8); ax.text(-122, -9.5, "skid + sensor board SB1", fontsize=8)
ax.set_aspect("equal"); ax.set_xlim(-128, 128); ax.set_ylim(-12, 62); ax.set_xlabel("r (mm)"); ax.set_title("PHI-FOLD 233 v6 head, meridian section: all electronics in a ferrite vault at the centre", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/head_v6_section.png", dpi=130)
json.dump(rep, open(f"{OUT}/head_v6_report.json", "w"), indent=1, default=float); print(json.dumps({k: (v["nonmanifold_edges"], v["triangles"]) if "triangles" in v else v for k, v in rep.items()}, default=float))
