#!/usr/bin/env python3
"""Independent checks of the upper assembly v1 (upper_v21.py), measured on the STLs in kit_v23/UPPER: closed shells, grip and hand space,
trigger gap and reach, rail fit and undercut, cell / BMS / connector bays, latch, pack insertion path, twin cavity vs the coiled cords,
telescoping overlap and sockets, voxel interference between parts, lengths, mass, centre of gravity and the static torque about the grip
(same model as shaft_calc_v20.py, head side unchanged). Purchased-part sizes come from the generator report and are ASSUMPTIONS 24-27."""
import json, math, struct, itertools, numpy as np
D = "kit_v23/UPPER"; R = json.load(open(f"{D}/upper_v21_report.json")); PRM = R["params"]; ENV = R["envelopes"]; res = []
def chk(name, value, lo=None, hi=None, note=""):
    ok = (lo is None or value >= lo - 1e-9) and (hi is None or value <= hi + 1e-9)
    res.append(dict(check=name, value=value if not isinstance(value, float) else round(value, 3), limits=[lo, hi], result="PASS" if ok else "FAIL", note=note))
def load(n):
    b = open(f"{D}/{n}.stl", "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3, 3).astype(float)
PARTS = ["U1_TOP_HOUSING", "U2_GRIP", "U3_BOTTOM_HOUSING", "U4_TRIGGER", "U5_ARMREST_CUP", "ARMREST_TUBE_CFRP_pos1", "U6_BATTERY_DOCK", "U7_BATTERY_PACK_SHELL",
         "TUBE_A_CFRP", "U8_CORD_ANCHOR", "U9_CAM_COLLAR", "TUBE_B_CFRP_extended", "U8_SEPTUM_extended", "TUBE_B_CFRP_collapsed", "U8_SEPTUM_collapsed"]
T = {n: load(n) for n in PARTS}

# ------------------------------------------------------------------ helpers measured on the meshes
def odd_edges(Tr):
    V = np.round(Tr.reshape(-1, 3), 4); _, inv = np.unique(V, axis=0, return_inverse=True); F = inv.reshape(-1, 3)
    E = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1); _, c = np.unique(E, axis=0, return_counts=True); return int((c % 2).sum())
def volume(Tr): a, b, c = Tr[:, 0], Tr[:, 1], Tr[:, 2]; return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
def centroid(Tr):
    a, b, c = Tr[:, 0], Tr[:, 1], Tr[:, 2]; v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0; return ((a + b + c) / 4.0 * v[:, None]).sum(0) / v.sum()
def section(Tr, axis, val):
    """2D segments of the plane cut  coord[axis] = val, in the remaining two coordinates (ascending axis order)"""
    keep = [i for i in range(3) if i != axis]; d = Tr[:, :, axis] - (val + 1.234e-4);     # off the vertices that lie exactly on round coordinates
    m = (d.min(1) < 0) & (d.max(1) > 0); S = []
    for tri, dd in zip(Tr[m], d[m]):
        q = [tri[i] + dd[i] / (dd[i] - dd[j]) * (tri[j] - tri[i]) for i, j in ((0, 1), (1, 2), (2, 0)) if (dd[i] < 0) != (dd[j] < 0)]
        if len(q) == 2: S.append([q[0][keep], q[1][keep]])
    return np.array(S).reshape(-1, 2, 2)
def seg_pt_dist(S, p):
    a, b = S[:, 0], S[:, 1]; ab = b - a; t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-18), 0, 1); return np.hypot(*(a + ab * t[:, None] - p).T)
def seg_seg_min(S1, S2, chunk=400):
    """exact minimum distance between two 2D segment sets (0 if any pair crosses)"""
    best = np.inf
    for P_, Q_ in ((S1, S2), (S2, S1)):
        for e in (P_[:, 0], P_[:, 1]):
            for k in range(0, len(e), chunk): best = min(best, min(seg_pt_dist(Q_, p).min() for p in e[k:k + chunk]))
    def orient(a, b, c): return (b[..., 0] - a[..., 0]) * (c[..., 1] - a[..., 1]) - (b[..., 1] - a[..., 1]) * (c[..., 0] - a[..., 0])
    for k in range(0, len(S1), chunk):
        A = S1[k:k + chunk, None]; p1, p2, q1, q2 = A[..., 0, :], A[..., 1, :], S2[None, :, 0], S2[None, :, 1]
        if ((orient(p1, p2, q1) * orient(p1, p2, q2) < 0) & (orient(q1, q2, p1) * orient(q1, q2, p2) < 0)).any(): return 0.0
    return float(best)
def rect_clear(S, y0, y1, z0, z1, n=12):
    """clearance between a rectangle and the segments (negative if a segment enters the rectangle)"""
    P = np.r_[[(y, z0) for y in np.linspace(y0, y1, n)], [(y, z1) for y in np.linspace(y0, y1, n)], [(y0, z) for z in np.linspace(z0, z1, n)], [(y1, z) for z in np.linspace(z0, z1, n)]]
    pts = (S[:, :1] + (S[:, 1:] - S[:, :1]) * np.linspace(0, 1, 8)[None, :, None]).reshape(-1, 2)
    inside = ((pts[:, 0] > y0) & (pts[:, 0] < y1) & (pts[:, 1] > z0) & (pts[:, 1] < z1)).any()
    return -1.0 if inside else float(min(seg_pt_dist(S, p).min() for p in P))
def hull_perimeter(P):
    P = np.unique(np.round(P, 6), axis=0); P = P[np.lexsort((P[:, 1], P[:, 0]))]
    def half(Q):
        h = []
        for p in Q:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0: h.pop()
            h.append(p)
        return h
    H = half(P)[:-1] + half(P[::-1])[:-1]; H = np.array(H); return float(np.hypot(*(np.roll(H, -1, 0) - H).T).sum())

# ------------------------------------------------------------------ 1 closed meshes
for n in PARTS: chk(f"closed shells: {n} (odd edges after welding)", odd_edges(T[n]), 0, 0)
# ------------------------------------------------------------------ 2 grip and hand space
ug, un = np.array(PRM["ug"]), np.array(PRM["un"]); G = T["U2_GRIP"]; e1 = un; e2 = np.array([0, 1.0, 0])
Gp = np.einsum("ijk,k->ij", G, ug); d = Gp - 0.0; m = (d.min(1) < 0) & (d.max(1) > 0); pts = []
for tri, dd in zip(G[m], d[m]):
    for i, j in ((0, 1), (1, 2), (2, 0)):
        if (dd[i] < 0) != (dd[j] < 0): q = tri[i] + dd[i] / (dd[i] - dd[j]) * (tri[j] - tri[i]); pts.append((q @ e1, q @ e2))
pts = np.array(pts); r = np.hypot(pts[:, 0] / 20.0, pts[:, 1] / 16.0); outer = pts[r > 0.9]
chk("grip circumference in the plane normal to the grip axis (mm)", hull_perimeter(outer), 100, 125, "power-grip range for adult hands, 40 x 32 ellipse")
S1 = section(T["U1_TOP_HOUSING"], 1, 0.0); S3 = section(T["U3_BOTTOM_HOUSING"], 1, 0.0)
u1_bot = S1[(S1[:, :, 0].mean(1) > -20) & (S1[:, :, 0].mean(1) < 40)][:, :, 1].min(); u3_top = S3[(S3[:, :, 0].mean(1) > -40) & (S3[:, :, 0].mean(1) < 10)][:, :, 1].max()
chk("hand space between the housings along the grip axis (mm)", (u1_bot - u3_top) / ug[2], 110, 130, "95th percentile hand breadth about 97 mm + glove")
# ------------------------------------------------------------------ 3 trigger
ST = section(T["U4_TRIGGER"], 1, 0.0); SG = section(G, 1, 0.0)
pad = ST[ST[:, :, 1].max(1) < u1_bot - 12.0]; gap = seg_seg_min(pad, SG[SG[:, :, 0].mean(1) > 0])
chk("trigger pad to grip front at rest (mm)", gap, PRM["trigger_travel"] + 0.3, 6.0, f"travel {PRM['trigger_travel']} mm to the stop")
chk("trigger pad top below the top housing (index finger directly under it, mm)", u1_bot - pad[:, :, 1].max(), 2.0, 20.0)
chk("trigger pad height on the grip (mm from the grip top along the axis)", (u1_bot - pad[:, :, 1].mean()) / ug[2], 15.0, 45.0, "index-finger pad zone")
mg = ENV["trigger_magnet"]; wall_out = u1_bot; mz_top = mg["centre"][2] + mg["h"] / 2
chk("trigger magnet clear of the housing wall (mm)", wall_out - mz_top, 0.2, 2.0)
hall_z = wall_out + 2.5 + 1.0 + 0.8; piv = np.array(PRM["pivot"]); pc = np.array(PRM["pad_centre"]); phi = PRM["trigger_travel"] / abs(pc[2] - piv[2])   # pad pushed rearward: rotation about the pivot
mag_drop = phi * (mg["centre"][0] - piv[0])
chk("magnet to Hall sensor at rest (mm, wall 2.5 + 1 mm air + half the 1.6 mm board)", hall_z - mg["centre"][2], 4.0, 8.0)
chk("magnet travel away from the Hall sensor for the full pad stroke (mm)", mag_drop, 2.0, None, "Hall switch operate/release points and magnet grade to be set on the first article (ASSUMPTIONS 22)")
for bd, part, zc in (("HB2_board", "U1_TOP_HOUSING", "ZT"), ("PM2_board", "U3_BOTTOM_HOUSING", "ZB")):
    e = ENV[bd]; ztop = e["z_board"][1] + e["parts_height"]
    chk(f"{bd.split('_')[0]} board and parts inside its housing (min clearance over the board length, mm)",
        min(rect_clear(section(T[part], 0, x), e["y"][0], e["y"][1], e["z_board"][0], ztop) for x in np.linspace(e["x"][0] + 0.5, e["x"][1] - 0.5, 9)), 0.2, None)
e = ENV["HB2_board"]; chk("Hall sensor on HB2 directly above the trigger magnet (x offset, mm)", abs(e["hall_x"] - mg["centre"][0]), 0.0, 1.0)
chk("HB2 clear of the tube A socket sleeve (mm)", PRM["tube_A"]["x"][0] - e["x"][1], 0.5, None)
chk("trigger tail clear of the top housing at rest (mm)", wall_out - float(T["U4_TRIGGER"][:, :, 2].max()), 0.3, None)
# ------------------------------------------------------------------ 4 battery dock and pack
S6 = section(T["U6_BATTERY_DOCK"], 0, -80.0); S7 = section(T["U7_BATTERY_PACK_SHELL"], 0, -80.0)
chk("rail fit: minimum clearance dock rails to pack channels at x = -80 (mm)", seg_seg_min(S6, S7), 0.25, 0.5)
zpt = PRM["dock"]["z_pack_top"]; ry = PRM["dock"]["rail_y"]; eng = []
for s in (-1, 1):
    hd = S6[(S6[:, :, 1].min(1) >= zpt - 5.61) & (S6[:, :, 1].max(1) <= zpt - 2.79) & (np.sign(S6[:, :, 0].mean(1)) == s)][:, :, 0].ravel()
    lip = S7[(S7[:, :, 1].min(1) >= zpt - 2.51) & (np.abs(S7[:, :, 0].mean(1) - s * ry) < 12)][:, :, 0].ravel()
    lo_edge = lip[lip < s * ry].max(); hi_edge = lip[lip > s * ry].min(); eng += [lo_edge - hd.min(), hd.max() - hi_edge]
chk("rail undercut engagement (head beyond the slot edge, each side, mm)", min(eng), 2.0, None, "keeps the pack captured vertically")
xs = sorted({round(float(x), 1) for x in np.linspace(-177.0, -3.0, 59)}); sweep = min(seg_seg_min(section(T["U6_BATTERY_DOCK"], 0, x), S7) for x in xs if len(section(T["U6_BATTERY_DOCK"], 0, x)))
chk("insertion path: pack section swept along the rails clears the dock everywhere (mm)", sweep, 0.25, None, "latch depressed while sliding")
SY = section(T["U7_BATTERY_PACK_SHELL"], 1, 0.0); c = ENV["cells"]
chk("cells: 7 x 18650 fit the cell bay, radial clearance in the y = 0 section (mm)", min(seg_pt_dist(SY, np.array([q["x"], q["z"]])).min() - c["d"] / 2 for q in c["centres"]), 0.2, None)
chk("cells: length clearance to the side walls (mm)", min(rect_clear(section(T["U7_BATTERY_PACK_SHELL"], 0, q["x"]), -c["l"] / 2, c["l"] / 2, q["z"] - c["d"] / 2, q["z"] + c["d"] / 2) for q in c["centres"]), 0.2, None)
b = ENV["BMS"]; chk("BMS bay accepts the 60 x 41 x 5.4 envelope (mm)", rect_clear(section(T["U7_BATTERY_PACK_SHELL"], 0, -60.0), *b["y"], *b["z"]), 0.1, None, "part to be chosen to fit")
for nm, part, x in (("MT60-M in the pedestal", "U6_BATTERY_DOCK", ENV["MT60_M"]["x"][0] + 10.0), ("MT60-F in the pack front wall", "U7_BATTERY_PACK_SHELL", -1.25)):
    e = ENV["MT60_M" if "M in" in nm else "MT60_F"]; chk(f"{nm}: envelope clearance (mm)", rect_clear(section(T[part], 0, x), *e["y"], *e["z"]), 0.15, None, "MT60 envelope from the Amass V1.2 drawing (ASSUMPTIONS 25)")
mM, mF = ENV["MT60_M"], ENV["MT60_F"]; chk("MT60 pair axis alignment (mm)", math.hypot(np.mean(mM["y"]) - np.mean(mF["y"]), np.mean(mM["z"]) - np.mean(mF["z"])), 0.0, 0.2)
chk("MT60 mating faces: pedestal face to pack face (mm)", mM["mating_face_x"] - mF["x"][1], 0.0, 1.0, "connector float takes up the rest")
L, P_ = ENV["latch"], ENV["latch_pocket"]; Sp = section(T["U6_BATTERY_DOCK"], 0, float(np.mean(P_["x"])))
chk("latch pocket open through the dock plate (mm of free width)", 2 * min(abs(Sp[(Sp[:, :, 1].min(1) >= P_["z"][0] - 0.01)][:, :, 0]).ravel()), 2 * (L["y"][1]) + 1.0, None)
chk("latch engagement in the pocket (mm)", L["z_rest"][1] - P_["z"][0], 2.0, None); chk("latch travel exceeds engagement (mm)", L["travel"] - (L["z_rest"][1] - P_["z"][0]), 0.5, None)
chk("latch inside the pocket in x (clearance each side, mm)", min(L["x"][0] - P_["x"][0], P_["x"][1] - L["x"][1]), 0.3, None)
# ------------------------------------------------------------------ 5 twin cavity and tubes
zt = PRM["ZT"]; tb = PRM["tube_B"]; xm = tb["extended"][0] + 2.0 + 75.0 / 2 + 8.0 / 2
SB = section(T["TUBE_B_CFRP_extended"], 0, xm); SS = section(T["U8_SEPTUM_extended"], 0, xm)
rin = float(np.hypot(SB[:, :, 0], SB[:, :, 1] - zt).min()); t2 = float(np.abs(SS[:, :, 0]).max())
chk("twin cavity between spacers: largest cord circle per half-bore (mm dia)", rin - t2, PRM["cord_od"] + 0.6, None, f"tube B ID {2*rin:.2f}, septum {2*t2:.2f}")
SSp = section(T["U8_SEPTUM_extended"], 0, tb["extended"][0] + 2.0 + 4.0)
chk("twin cavity at a spacer: bore radius minus cord radius (mm)", min(seg_pt_dist(SSp, np.array([s * PRM["bore_y"], zt])).min() for s in (-1, 1)) - PRM["cord_od"] / 2, 0.3, None)
SA = section(T["TUBE_A_CFRP"], 0, 300.0); ra_in = float(np.hypot(SA[:, :, 0], SA[:, :, 1] - zt).min()); rb_out = float(np.hypot(SB[:, :, 0], SB[:, :, 1] - zt).max())
chk("tube B in tube A radial clearance (mm)", ra_in - rb_out, 0.5, 1.5)
a1 = float(T["TUBE_A_CFRP"][:, :, 0].max()); be0 = float(T["TUBE_B_CFRP_extended"][:, :, 0].min()); bc0 = float(T["TUBE_B_CFRP_collapsed"][:, :, 0].min())
chk("telescoping overlap at full extension (mm)", a1 - be0, 80.0, None, "about 2.8 x tube OD")
chk("collapsed: tube B clear of the cord anchor (mm)", bc0 - float(T["U8_CORD_ANCHOR"][:, :, 0].max()), 0.5, None)
stroke = float(T["TUBE_B_CFRP_extended"][:, :, 0].max() - T["TUBE_B_CFRP_collapsed"][:, :, 0].max()); chk("telescoping stroke (mm)", stroke, 300.0, None)
Ssock = section(T["U1_TOP_HOUSING"], 0, 90.0); rs = np.hypot(Ssock[:, :, 0], Ssock[:, :, 1] - zt); ra_out = float(np.hypot(SA[:, :, 0], SA[:, :, 1] - zt).max())
chk("tube A in the top-housing socket: radial clearance (mm)", float(rs[rs < 18.0].min()) - ra_out, 0.1, 0.4)
zb = PRM["ZB"]; Sas = section(T["U3_BOTTOM_HOUSING"], 0, PRM["bottom_housing_x"][0] + 40.0); Sat = section(T["ARMREST_TUBE_CFRP_pos1"], 0, PRM["bottom_housing_x"][0] + 40.0)
rr = np.hypot(Sas[:, :, 0], Sas[:, :, 1] - zb); chk("armrest tube in its socket: radial clearance (mm)", float(rr[rr < 12.5].min()) - float(np.hypot(Sat[:, :, 0], Sat[:, :, 1] - zb).max()), 0.1, 0.4)
ins = float(PRM["bottom_housing_x"][0] + PRM["armrest"]["socket"]) - float(T["ARMREST_TUBE_CFRP_pos1"][:, :, 0].max())
chk("armrest tube insertion at position 1 inside the socket (mm, tube end short of the socket end)", ins, 0.0, None)
chk("armrest positions: shortest insertion >= 2 x tube OD (mm)", min(PRM["armrest"]["insertion_depths"]), 2 * PRM["armrest"]["od"], None)
cc = [-v for v in PRM["armrest"]["cup_centre_x"]]; chk("cup centre behind the grip centre, positions 1-3 (mm)", f"{cc[0]:.0f} / {cc[1]:.0f} / {cc[2]:.0f}", note="covers about 5th-95th percentile forearm lengths with the cup 60-90 mm in front of the elbow (estimate)")
res[-1]["result"] = "PASS" if 220 <= cc[0] and cc[2] <= 300 else "FAIL"
# ------------------------------------------------------------------ 6 voxel interference between parts (pairwise, bounding-box limited, 0.25 mm)
H = 0.25
def vox(Tr, lo, hi):
    nx, ny, nz = [max(1, int(math.ceil((hi[i] - lo[i]) / H))) for i in range(3)]; keep = (Tr[:, :, 0].max(1) >= lo[0]) & (Tr[:, :, 0].min(1) <= hi[0]) & (Tr[:, :, 1].max(1) >= lo[1]) & (Tr[:, :, 1].min(1) <= hi[1])
    cols = {}; jx, jy = 0.0173 * H, 0.0127 * H
    for a, b_, c_ in Tr[keep]:
        ar = (b_[0] - a[0]) * (c_[1] - a[1]) - (c_[0] - a[0]) * (b_[1] - a[1])
        if abs(ar) < 1e-12: continue
        i0 = max(0, int(np.floor((min(a[0], b_[0], c_[0]) - lo[0]) / H))); i1 = min(nx - 1, int(np.ceil((max(a[0], b_[0], c_[0]) - lo[0]) / H)))
        j0 = max(0, int(np.floor((min(a[1], b_[1], c_[1]) - lo[1]) / H))); j1 = min(ny - 1, int(np.ceil((max(a[1], b_[1], c_[1]) - lo[1]) / H)))
        if i1 < i0 or j1 < j0: continue
        gx, gy = np.meshgrid(lo[0] + (np.arange(i0, i1 + 1) + 0.5) * H + jx, lo[1] + (np.arange(j0, j1 + 1) + 0.5) * H + jy, indexing="ij")
        w0 = ((b_[0] - gx) * (c_[1] - gy) - (c_[0] - gx) * (b_[1] - gy)) / ar; w1 = ((c_[0] - gx) * (a[1] - gy) - (a[0] - gx) * (c_[1] - gy)) / ar; w2 = 1 - w0 - w1
        mm = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not mm.any(): continue
        z = w0 * a[2] + w1 * b_[2] + w2 * c_[2]
        for p, q in zip(*np.nonzero(mm)): cols.setdefault((i0 + p, j0 + q), []).append(z[p, q])
    V = np.zeros((nx, ny, nz), bool)
    for (i, j), zs in cols.items():
        zs = sorted(zs)
        for k in range(0, len(zs) - 1, 2):
            a0 = int(np.ceil((zs[k] - lo[2]) / H - 0.5)); b0 = int(np.floor((zs[k + 1] - lo[2]) / H - 0.5))
            a0, b0 = max(a0, 0), min(b0, nz - 1)                                     # clamp both ends (an interval wholly outside the box must add nothing)
            if b0 >= a0: V[i, j, a0:b0 + 1] = True
    return V
# ------------------------------------------------------------------ B8: septum split joint (half-lap), measured on the two printable segments against the full-length reference
SG = {k: load(f"U8_SEPTUM_extended_SEG_{k}") for k in "AB"}; SPL = R.get("septum_split", {})
for k in "AB":
    ext = SG[k][:, :, 0].max() - SG[k][:, :, 0].min(); chk(f"septum segment {k}: printable length (mm)", float(ext), None, 250.0, "250 mm build volume")
    chk(f"septum segment {k}: closed shell (odd edges)", odd_edges(SG[k]), 0, 0)
vA, vB, vF = volume(SG["A"]), volume(SG["B"]), volume(T["U8_SEPTUM_extended"])
chk("septum segments A + B = the full-length reference (volume difference, %)", abs(vA + vB - vF) / vF * 100.0, None, 0.5, f"A {vA:.0f} + B {vB:.0f} vs {vF:.0f} mm3 (dilated unions: 0.005 mm margin each)")
xa, xb = SG["A"][:, :, 0].max(), SG["B"][:, :, 0].min(); chk("septum split: half-lap overlap along x (mm)", float(xa - xb), 9.5, 10.5, f"lap {SPL.get('lap')} mm at x {SPL.get('cut')}")
if SPL:
    lo = np.array([SPL["cut"] - 1.0, -2.0, SPL["z_split"] - 6.0]); hi = np.array([SPL["cut"] + SPL["lap"] + 1.0, 2.0, SPL["z_split"] + 6.0])
    chk("septum split: segments A and B do not overlap in the joint (voxel mm3)", float((vox(SG["A"], lo, hi) & vox(SG["B"], lo, hi)).sum() * H ** 3), 0.0, 0.5, "0.25 mm voxels: the 0.005 mm dilation of both faces can share one voxel row")
BONDED = {frozenset(("U2_GRIP", "U1_TOP_HOUSING")), frozenset(("U2_GRIP", "U3_BOTTOM_HOUSING"))}   # grip ends bonded 2 mm into the housing walls
inter = []
for cfg in ("extended", "collapsed"):
    names = [n for n in PARTS if not n.endswith("extended" if cfg == "collapsed" else "collapsed")]
    for a_, b2 in itertools.combinations(names, 2):
        A_, B_ = T[a_], T[b2]; lo = np.maximum(A_.reshape(-1, 3).min(0), B_.reshape(-1, 3).min(0)); hi = np.minimum(A_.reshape(-1, 3).max(0), B_.reshape(-1, 3).max(0))
        if (hi - lo).min() <= 0: continue
        ov = float((vox(A_, lo, hi) & vox(B_, lo, hi)).sum() * H ** 3)
        if ov > 0.0: inter.append(dict(config=cfg, a=a_, b=b2, overlap_mm3=round(ov, 2), bonded=frozenset((a_, b2)) in BONDED))
bad = [x for x in inter if not x["bonded"] and x["overlap_mm3"] > 1.0]
chk("voxel interference between parts, extended and collapsed (pairs over 1 mm3, bonded grip joints excluded)", len(bad), 0, 0, str([(x["a"], x["b"], x["overlap_mm3"]) for x in bad][:6]))

# ------------------------------------------------------------------ 7 lengths, mass, centre of gravity, torque about the grip
SC = json.load(open("kit_v19/shaft_calc_v20.json")); mh = SC["head_mass_kg"]["total"]; NPMH, LOWER = 0.084, 0.40
ext = {k: v for k, v in T.items() if not k.endswith("collapsed")}; col = {k: v for k, v in T.items() if not k.endswith("extended")}
L_ext = float(max(v[:, :, 0].max() for v in ext.values()) - min(v[:, :, 0].min() for v in ext.values()))
L_col = float(max(v[:, :, 0].max() for v in col.values()) - min(v[:, :, 0].min() for v in col.values()))
bfront_e, bfront_c = float(T["TUBE_B_CFRP_extended"][:, :, 0].max()), float(T["TUBE_B_CFRP_collapsed"][:, :, 0].max())
cup_back = float(T["U5_ARMREST_CUP"][:, :, 0].min())
rows = dict(upper_assembly_extended_mm=round(L_ext), upper_assembly_collapsed_mm=round(L_col),
            cup_back_to_hinge_extended_mm=round(bfront_e + (NPMH + LOWER) * 1000 - cup_back), cup_back_to_hinge_collapsed_mm=round(bfront_c + (NPMH + LOWER) * 1000 - cup_back))
DENS = {n: R["parts"][n]["mass_g"] / R["parts"][n]["volume_cm3"] for n in R["parts"] if R["parts"][n]["volume_cm3"] > 0}
items = []                                                                                           # (name, mass_kg, stem-frame point, source)
for n in [k for k in PARTS if not k.endswith("collapsed")]:
    items.append((n, volume(T[n]) / 1000.0 * DENS[n] / 1000.0, centroid(T[n]), "mesh volume x density"))
zpt = PRM["dock"]["z_pack_top"]
purchased = [("7 x Molicel P30B (47 g max each, datasheet value via retailer copies, unverified)", 0.329, (-85.0, 0, zpt - 19.3)), ("BMS 7S (estimate)", 0.020, (-60.0, 0, zpt - 5.7)),
             ("MT60 pair + gasket (estimate)", 0.010, (0.0, 0, zpt - 20.0)), ("nickel strip, pack wiring, insulation, heat-shrink (estimate)", 0.030, (-85.0, 0, zpt - 15.0)),
             ("spring thumb latch, steel (estimate)", 0.012, (-171.0, 0, zpt - 5.0)), ("PM2 board, populated (estimate)", 0.030, (-50.0, 0, PRM["ZB"] - 12.0)),
             ("HB2 board, dial switch, power button, magnet (estimate)", 0.020, (0.0, 0, PRM["ZT"] - 18.0)), ("power coiled cord 2 x AWG20 shielded (estimate)", 0.045, (300.0, 0, PRM["ZT"])),
             ("signal coiled cord 5-core AWG28 shielded (estimate)", 0.035, (300.0, 0, PRM["ZT"])), ("forearm strap + cup liner (estimate)", 0.020, (PRM["armrest"]["cup_centre_x"][0], 0, PRM["armrest"]["cup_axis_z"]))]
items += [(n, m, np.array(p, float), "estimate") for n, m, p in purchased]
m_up = sum(m for _, m, _, _ in items); cg = sum(m * np.asarray(p) for _, m, p, _ in items) / m_up
m_pack = sum(m for n, m, _, _ in items if ("PACK" in n or "P30B" in n or "BMS" in n or "latch" in n or "nickel" in n)) + 0.005
def torque(alpha, bfront, battery_dx=0.0):
    a = math.radians(alpha); wx = lambda p: (p[0] * math.cos(a) + p[2] * math.sin(a)) / 1000.0
    hinge = np.array([bfront + (NPMH + LOWER) * 1000.0, 0, PRM["ZT"]])
    t = (mh + 0.35) * (wx(hinge) + 0.154) + 0.55 * wx(np.array([bfront + NPMH * 500.0, 0, PRM["ZT"]])) + 0.18 * wx(np.array([bfront + NPMH * 1000 + LOWER * 500.0, 0, PRM["ZT"]]))
    for n, m, p, _ in items:
        p = np.array(p, float)
        if n.startswith("TUBE_B") or n.startswith("U8_SEPTUM"): p = p + np.array([bfront - float(T["TUBE_B_CFRP_extended"][:, :, 0].max()), 0, 0])
        if battery_dx and ("PACK" in n or "P30B" in n or "BMS" in n or "latch" in n or "nickel" in n): p = p + np.array([battery_dx, 0, 0])
        t += m * wx(p)
    return round(t, 3), round(wx(hinge) + 0.154, 3)
# working length: tube B set so the head sits at the same horizontal reach as the v20 baseline at 47 deg (shaft_calc_v20.py)
reach = SC["balance"]["head_horizontal_distance_m"]; a47 = math.radians(47); hz = PRM["ZT"] * math.sin(a47) / 1000.0
b_work = ((reach - 0.154 - hz) / math.cos(a47)) * 1000.0 - (NPMH + LOWER) * 1000.0
bal = dict(baseline_v20_kg_m=SC["balance"]["baseline_kg_m"], new_47deg_working=torque(47, b_work)[0], head_horizontal_m=torque(47, b_work)[1], new_40deg=torque(40, b_work)[0], new_55deg=torque(55, b_work)[0],
           new_47deg_full_extension=torque(47, bfront_e)[0], new_47deg_collapsed=torque(47, bfront_c)[0],
           option_pack_moved_back_under_the_cup=torque(47, b_work, battery_dx=PRM["armrest"]["cup_centre_x"][0] + 84.0)[0])
chk("static torque about the grip at 47 deg, same head reach as v20 (kg m)", bal["new_47deg_working"], None, SC["balance"]["baseline_kg_m"], f"v20 design {SC['balance']['baseline_kg_m']} at reach {reach} m; typical detectors 1.3-1.7")
chk("working length is inside the telescoping range (tube B front between collapsed and extended, mm)", b_work, bfront_c, bfront_e)
chk("upper assembly mass incl. battery pack (kg)", round(m_up, 3), None, 1.6, "XP S-telescopic stem alone is 370 g (XP manual); this adds the pack, electronics, cords and the twin cavity")
out = dict(checks=res, lengths_mm=rows, balance=bal, mass=dict(upper_total_kg=round(m_up, 3), battery_pack_kg=round(m_pack, 3), cg_stem_frame_mm=[round(float(v), 1) for v in cg],
           items=[dict(item=n, mass_g=round(m * 1000, 1), at_mm=[round(float(v), 1) for v in p], source=s) for n, m, p, s in items]), interference_pairs=inter)
json.dump(out, open("kit_v23/upper_check.json", "w"), indent=1, default=float)
for c_ in res: print(f"{c_['result']}  {c_['check']} = {c_['value']}  {c_['note'][:70]}")
print("lengths", rows); print("balance", bal); print("mass", out["mass"]["upper_total_kg"], "kg, pack", out["mass"]["battery_pack_kg"], "kg, CG", out["mass"]["cg_stem_frame_mm"])
print("FAILS", sum(c_["result"] == "FAIL" for c_ in res), "of", len(res))
