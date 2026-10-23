"""Ferrite hood v3: 13 radial spokes, each spoke one stepped pocket holding the inner and outer MnZn tile butted end to end (design joint 0.2 mm
adhesive). v2 (hood_v19.py) held the two tiles in separate pocket frames with a 2.0 mm radial air gap; the axisymmetric model (src/sim/hood_axi.py)
puts the v3 gain at +13.0-14.1 % at 200 mm (v2 +9.8 %) for 9 g more ferrite (modeled, docs/ASSUMPTIONS.md 8, 23).
Placement: spoke k at azimuth k x 360/13 deg (k = 0..12, head frame), inner tile r57.0-84.0, outer tile r84.2-112.5; tiles 2.5 mm, z30.4-32.9.
Carrier: base ring r52.6-116.1 z29.4-30.4 + a stepped pocket frame per spoke (wall 1.2, clearance 0.15 per side) z30.4-33.4. Print flat (base ring on
the bed, pockets up, no supports); tiles bonded into the pockets after printing."""
import math, json, csv, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
OUT = "kit_v18/PARTS"; rep = {}
N, GAP, BUTT, TT, Z0, Z1, Z2 = 13, 1.7, 0.2, 2.5, 29.4, 30.4, 33.4
R_IN0, R_IN1, R_OUT1 = 57.0, 84.0, 112.5; R_OUT0 = R_IN1 + BUTT; WALL, CLR = 1.2, 0.15
CARRIER_R = (52.6, 116.1)

def circ(r, m=360): t = np.linspace(0, 2 * np.pi, m, endpoint=False); return np.c_[r * np.cos(t), r * np.sin(t)]
def ring(outer, inner, z0, z1):
    m = len(outer); V = np.concatenate([np.c_[outer, np.full(m, z0)], np.c_[outer, np.full(m, z1)], np.c_[inner, np.full(m, z0)], np.c_[inner, np.full(m, z1)]]); O0, O1, I0, I1 = (np.arange(m) + k * m for k in range(4)); n = np.roll(np.arange(m), -1); F = []
    for i in range(m): j = n[i]; F += [[O0[i], O0[j], O1[j]], [O0[i], O1[j], O1[i]], [I0[j], I0[i], I1[i]], [I0[j], I1[i], I1[j]], [O0[j], O0[i], I0[i]], [O0[j], I0[i], I0[j]], [O1[i], O1[j], I1[j]], [O1[i], I1[j], I1[i]]]
    F = np.array(F); return (V, F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
def extrude(poly, z0, z1):
    P = np.asarray(poly); m = len(P); T = tri2d(P); ar = (P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]).sum(); V = np.concatenate([np.c_[P, np.full(m, z0)], np.c_[P, np.full(m, z1)]]); F = []
    for t in T: F.append([m + t[0], m + t[1], m + t[2]] if ar > 0 else [m + t[0], m + t[2], m + t[1]]); F.append([t[0], t[2], t[1]] if ar > 0 else [t[0], t[1], t[2]])
    for i in range(m): j = (i + 1) % m; F += [[i, j, m + j], [i, m + j, m + i]] if ar > 0 else [[i, m + j, j], [i, m + i, m + j]]
    F = np.array(F); return (V, F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
def emit(name, shells, note):
    bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells); V, F = g.merge(shells); rc.write_stl(f"{OUT}/{name}.stl", V, F, name)
    rep[name] = dict(shells=len(shells), tris=int(len(F)), nonmanifold_edges=int(bad), bbox=[round(float(x), 2) for x in (*V.min(0), *V.max(0))], note=note)
def sat_gap(A, B):
    best = -1e9
    for Q in (A, B):
        for i in range(len(Q)):
            e = Q[(i + 1) % len(Q)] - Q[i]; n = np.array([-e[1], e[0]]) / np.linalg.norm(e); a = A @ n; b = B @ n; best = max(best, max(b.min() - a.max(), a.min() - b.max()))
    return best
def rect_pts(cx, cy, ang, hl, hw): c, s = math.cos(ang), math.sin(ang); return np.array([(cx + x * c - y * s, cy + x * s + y * c) for x, y in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))])
def rot(P, ang): c, s = math.cos(ang), math.sin(ang); P = np.asarray(P, float); return np.c_[P[:, 0] * c - P[:, 1] * s, P[:, 0] * s + P[:, 1] * c]
def width_for(r0, r1):
    lo, hi = 4.0, 200.0; th = 2 * math.pi / N; rm = (r0 + r1) / 2
    for _ in range(50):
        w = (lo + hi) / 2
        if sat_gap(rect_pts(rm, 0, 0, (r1 - r0) / 2, w / 2), rect_pts(rm * math.cos(th), rm * math.sin(th), th, (r1 - r0) / 2, w / 2)) >= GAP: lo = w
        else: hi = w
    return math.floor(lo * 10) / 10
W_IN, W_OUT = width_for(R_IN0, R_IN1), width_for(R_OUT0, R_OUT1)
def stepped(off):
    """pocket outline in the spoke frame (x radial, y tangential), CCW, offset outward by `off` (right-angle corners -> exact mitre)"""
    a, b, c, h1, h2 = R_IN0 - off, R_IN1 + BUTT / 2, R_OUT1 + off, W_IN / 2 + off, W_OUT / 2 + off
    sx = b - off if W_OUT > W_IN else b + off                              # the step face moves inward with the offset (the wide part grows)
    return np.array([(a, -h1), (sx, -h1), (sx, -h2), (c, -h2), (c, h2), (sx, h2), (sx, h1), (a, h1)])

tiles = []; spokes = []
for k in range(N):
    t = 2 * math.pi * k / N; spokes.append(t)
    for nm, r0, r1, w in (("inner", R_IN0, R_IN1, W_IN), ("outer", R_OUT0, R_OUT1, W_OUT)): tiles.append((nm, k, (r0 + r1) / 2 * math.cos(t), (r0 + r1) / 2 * math.sin(t), t, r1 - r0, w))
shells = [ring(circ(CARRIER_R[1], 720), circ(CARRIER_R[0], 720), Z0, Z1)]
for t in spokes: shells.append(ring(rot(stepped(CLR + WALL), t), rot(stepped(CLR), t), Z1, Z2))
emit("LOTUS_HOOD_CARRIER_v3_butted", shells, f"13 radial spokes, one stepped pocket per spoke: inner tile {R_IN1-R_IN0:.1f} x {W_IN}, outer {R_OUT1-R_OUT0:.1f} x {W_OUT} x {TT} mm MnZn butted (joint {BUTT} mm); carrier r{CARRIER_R[0]}-{CARRIER_R[1]}, z{Z0}-{Z2}; print flat, no supports")
for nm, L, w in (("inner", R_IN1 - R_IN0, W_IN), ("outer", R_OUT1 - R_OUT0, W_OUT)):
    emit(f"FERRITE_TILE_{nm.upper()}_v3_reference", [extrude(np.array([(-L / 2, -w / 2), (L / 2, -w / 2), (L / 2, w / 2), (-L / 2, w / 2)]), 0.0, TT)], f"MnZn tile {L:.1f} x {w} x {TT}, 13 pieces")
# ---- audit (all measured on the generated outlines)
near = lambda a, b: math.hypot(a[2] - b[2], a[3] - b[3]) < 75
tile_gap = min(sat_gap(rect_pts(a[2], a[3], a[4], a[5] / 2, a[6] / 2), rect_pts(b[2], b[3], b[4], b[5] / 2, b[6] / 2)) for i, a in enumerate(tiles) for b in tiles[i + 1:] if near(a, b) and a[1] != b[1])
butt = min(math.hypot(b[2], b[3]) - b[5] / 2 - (math.hypot(a[2], a[3]) + a[5] / 2) for a in tiles for b in tiles if a[0] == "inner" and b[0] == "outer" and a[1] == b[1])
def poly_gap(P, Q):                                                          # min distance between two polygons (vertex-edge), stepped outlines are non-convex
    def pd(p, a, b):
        ab = b - a; L2 = ab @ ab
        return float(np.linalg.norm(p - a)) if L2 < 1e-18 else float(np.linalg.norm(p - (a + np.clip(((p - a) @ ab) / L2, 0, 1) * ab)))
    d1 = min(pd(p, Q[i], Q[(i + 1) % len(Q)]) for p in P for i in range(len(Q)))
    return d1 if len(P) < 2 else min(d1, min(pd(p, P[i], P[(i + 1) % len(P)]) for p in Q for i in range(len(P))))
fr_out = [rot(stepped(CLR + WALL), t) for t in spokes]; pk = [rot(stepped(CLR), t) for t in spokes]
frame_into_pocket = min(poly_gap(fr_out[i], pk[(i + 1) % N]) for i in range(N))  # neighbour's frame wall must not cut into this pocket (walls may merge)
corner = max(float(np.hypot(*p)) for P in fr_out for p in P); inner_r = min(float(np.hypot(*p)) for P in fr_out for p in P)
# every tile lies inside its pocket with the clearance on all sides
def inside_margin(tile, pocket):
    pts = rect_pts(tile[2], tile[3], tile[4], tile[5] / 2, tile[6] / 2); return min(poly_gap(pts[[i]], pocket) for i in range(4))
fit = min(inside_margin(a, pk[a[1]]) for a in tiles)
area = sum(a[5] * a[6] for a in tiles); mass = area * TT * 4.8e-3
rep["hood_v3_audit"] = dict(tiles=len(tiles), spokes=N, spoke_azimuths_deg=[round(math.degrees(t), 4) for t in spokes], min_tile_gap=round(tile_gap, 2), butt_joint=round(butt, 3),
    tile_to_pocket_wall_min=round(fit, 3), frame_into_neighbour_pocket_gap=round(frame_into_pocket, 2), outer_frame_corner_r=round(corner, 2), inner_frame_r=round(inner_r, 2),
    tile_area_mm2=round(area), mass_g=round(mass), dims=dict(inner=[round(R_IN1 - R_IN0, 1), W_IN], outer=[round(R_OUT1 - R_OUT0, 1), W_OUT]), tiles_z=[Z1, Z1 + TT],
    print="flat on the base ring, pockets up, no supports; bond tiles after printing (joint 0.2 mm, adhesive)")
rep["checks"] = [dict(check=n, value=v, result="PASS" if ok else "FAIL") for n, v, ok in (
    ("carrier and tiles closed meshes (open edges)", sum(r["nonmanifold_edges"] for k, r in rep.items() if isinstance(r, dict) and "nonmanifold_edges" in r), sum(r["nonmanifold_edges"] for k, r in rep.items() if isinstance(r, dict) and "nonmanifold_edges" in r) == 0),
    ("tile gap between neighbouring spokes >= 1.7 mm", round(tile_gap, 2), tile_gap >= GAP - 1e-6),
    ("butt joint inner/outer tile 0.2 mm", round(butt, 3), abs(butt - BUTT) < 1e-6),
    ("every tile inside its pocket with >= 0.15 mm clearance", round(fit, 3), fit >= CLR - 1e-6),
    ("neighbour frame wall clear of the next pocket", round(frame_into_pocket, 2), frame_into_pocket >= 0.0),
    ("outer frame corner within the carrier r116.1", round(corner, 2), corner <= CARRIER_R[1]),
    ("inner frame edge outside the carrier inner r52.6", round(inner_r, 2), inner_r >= CARRIER_R[0]),
    ("tile top below the bridge floor z33.7 (yoke clearance)", Z1 + TT, Z1 + TT < 33.7))]
with open(f"{OUT}/hood_v3_tile_cut_list.csv", "w", newline="") as f:
    w_ = csv.writer(f); w_.writerow(["id", "segment", "spoke", "length_mm", "width_mm", "thick_mm", "centre_r_mm", "azimuth_deg", "z_bottom_mm"])
    [w_.writerow([f"T{k+1:02d}", a[0], a[1] + 1, round(a[5], 1), a[6], TT, round(math.hypot(a[2], a[3]), 2), round(math.degrees(a[4]) % 360, 4), Z1]) for k, a in enumerate(tiles)]
def dxf_rect(lines, x, y, L, W, layer):
    for (x0, y0, x1, y1) in ((x, y, x + L, y), (x + L, y, x + L, y + W), (x + L, y + W, x, y + W), (x, y + W, x, y)): lines += ["0", "LINE", "8", layer, "10", f"{x0:.3f}", "20", f"{y0:.3f}", "30", "0.0", "11", f"{x1:.3f}", "21", f"{y1:.3f}", "31", "0.0"]
ln = ["0", "SECTION", "2", "ENTITIES"]; y = 5.0
for nm, L, w in (("inner", R_IN1 - R_IN0, W_IN), ("outer", R_OUT1 - R_OUT0, W_OUT)):
    x = 5.0
    for k in range(N):
        if x + L > 300: x = 5.0; y += w + 4
        dxf_rect(ln, x, y, L, w, "TILE_" + nm.upper()); x += L + 4
    y += w + 10
ln += ["0", "ENDSEC", "0", "EOF"]; open(f"{OUT}/hood_v3_tile_cut_sheet.dxf", "w").write("\n".join(ln))
json.dump(rep, open(f"{OUT}/hood_v3_report.json", "w"), indent=1, default=float)
# ---- layout drawing: plan view (head frame, top view), pockets, tiles and spoke azimuths; the print/assembly reference
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 10)); th = np.linspace(0, 2 * np.pi, 400)
for r_ in CARRIER_R: ax.plot(r_ * np.cos(th), r_ * np.sin(th), color="#777", lw=0.8)
for P in fr_out: ax.fill(*np.vstack([P, P[:1]]).T, fc="#dde3ee", ec="#5a6b8c", lw=0.6)
for P in pk: ax.plot(*np.vstack([P, P[:1]]).T, color="#5a6b8c", lw=0.5)
for a in tiles: ax.fill(*np.vstack([rect_pts(a[2], a[3], a[4], a[5] / 2, a[6] / 2)] * 1)[[0, 1, 2, 3, 0]].T, fc="#222" if a[0] == "outer" else "#444", ec="none")
for k, t in enumerate(spokes): ax.text(121 * math.cos(t), 121 * math.sin(t), f"S{k+1}\n{math.degrees(t):.2f}", ha="center", va="center", fontsize=7)
for ang, lab in ((178.0, "heel / bridge 178"), (90.0, "spine 90")): ax.plot([0, 135 * math.cos(math.radians(ang))], [0, 135 * math.sin(math.radians(ang))], "--", color="#c33", lw=0.8); ax.text(138 * math.cos(math.radians(ang)), 138 * math.sin(math.radians(ang)), lab, color="#c33", fontsize=8, ha="center")
ax.set_aspect(1); ax.set_xlim(-150, 150); ax.set_ylim(-150, 150); ax.grid(alpha=0.2)
ax.set_title(f"Ferrite hood v3 (plan, head frame): 13 spokes at k x 360/13 deg, inner tile r{R_IN0:.0f}-{R_IN1:.0f} ({R_IN1-R_IN0:.1f} x {W_IN}), outer r{R_OUT0:.1f}-{R_OUT1:.1f} ({R_OUT1-R_OUT0:.1f} x {W_OUT}) x {TT} mm,\n"
             f"butt joint {BUTT} mm, spoke gap {GAP} mm, {round(mass)} g MnZn; carrier z{Z0}-{Z2}, print flat (base ring down, no supports), bond tiles after printing", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/HOOD_V3_LAYOUT.png", dpi=80)
for c in rep["checks"]: print(c["result"], c["check"], "=", c["value"])
print(rep["hood_v3_audit"]); print("FAILS", sum(c["result"] == "FAIL" for c in rep["checks"]), "of", len(rep["checks"]))
