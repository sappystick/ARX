#!/usr/bin/env python3
"""PHI-FOLD 233 v6 concept renders: full system and dissected (cut-away) views.  Real part STLs + board models; head body, windings and potting volumes are dimensioned proxies."""
import math, os, struct, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
FD = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
def font(sz, b=False): return ImageFont.truetype(os.path.join(FD, "DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), sz)
def load_stl(p):
    b = open(p, "rb").read(); n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n, offset=84)
    V = a["v"].reshape(-1, 3).astype(float); return V, np.arange(len(V)).reshape(-1, 3)
# ------------------------------------------------------------------ primitives
def tri2d(poly):
    poly = np.asarray(poly, float)
    if (np.cross(np.roll(poly, -1, 0) - poly, np.roll(poly, -2, 0) - np.roll(poly, -1, 0)).sum()) < 0 and ((poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]).sum() < 0): poly = poly[::-1]
    idx = list(range(len(poly))); tris = []
    a2 = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    guard = 0
    while len(idx) > 3 and guard < 5000:
        guard += 1; ear = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]; a, b, c = poly[i0], poly[i1], poly[i2]
            if a2(a, b, c) <= 1e-12: continue
            if any(min(a2(a, b, poly[j]), a2(b, c, poly[j]), a2(c, a, poly[j])) >= 0 for j in idx if j not in (i0, i1, i2)): continue
            tris.append((i0, i1, i2)); idx.pop(k); ear = True; break
        if not ear: break
    if len(idx) == 3: tris.append(tuple(idx))
    return tris
def revolve(profile, a0=0.0, a1=2 * math.pi, n=96):
    P = np.asarray(profile, float); m = len(P); full = (a1 - a0) >= 2 * math.pi - 1e-6; steps = n if full else max(8, int(n * (a1 - a0) / (2 * math.pi)))
    ang = np.linspace(a0, a1, steps + (0 if full else 1), endpoint=not full)
    V = np.array([(r * math.cos(a), r * math.sin(a), z) for a in ang for r, z in P]); F = []; ns = len(ang)
    for i in range(ns - (0 if full else 1)):
        i2 = (i + 1) % ns
        for j in range(m): j2 = (j + 1) % m; F += [[i * m + j, i2 * m + j, i2 * m + j2], [i * m + j, i2 * m + j2, i * m + j2]]
    if not full:
        T = tri2d(P)
        for t in T: F.append([t[0], t[1], t[2]]); F.append([(ns - 1) * m + t[0], (ns - 1) * m + t[2], (ns - 1) * m + t[1]])
    return V, np.array(F)
def box(cx, cy, cz, lx, ly, lz):
    x = np.array([-1, 1]) * lx / 2; y = np.array([-1, 1]) * ly / 2; z = np.array([-1, 1]) * lz / 2
    V = np.array([[a, b, c] for a in x for b in y for c in z]) + [cx, cy, cz]
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]); return V, F
def cyl(p0, p1, r, n=20):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); ax = p1 - p0; L = np.linalg.norm(ax); ax /= L
    t = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0]); u = np.cross(ax, t); u /= np.linalg.norm(u); v = np.cross(ax, u)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False); ring = np.array([np.cos(a) * u + np.sin(a) * v for a in th]) * r
    V = np.concatenate([p0 + ring, p1 + ring, [p0], [p1]]); F = []
    for i in range(n): j = (i + 1) % n; F += [[i, j, n + j], [i, n + j, n + i], [2 * n, j, i], [2 * n + 1, n + i, n + j]]
    return V, np.array(F)
def torus(R, r, z, a0=0.0, a1=2 * math.pi, n1=120, n2=8):
    full = (a1 - a0) >= 2 * math.pi - 1e-6; A = np.linspace(a0, a1, n1, endpoint=not full); B = np.linspace(0, 2 * np.pi, n2, endpoint=False)
    V = np.array([((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), z + r * math.sin(b)) for a in A for b in B]); F = []; na = len(A)
    for i in range(na - (0 if full else 1)):
        i2 = (i + 1) % na
        for j in range(n2): j2 = (j + 1) % n2; F += [[i * n2 + j, i2 * n2 + j, i2 * n2 + j2], [i * n2 + j, i2 * n2 + j2, i * n2 + j2]]
    return V, np.array(F)
def place(S, O, ex, ey, ez): V = S[0]; return np.asarray(O) + np.outer(V[:, 0], ex) + np.outer(V[:, 1], ey) + np.outer(V[:, 2], ez), S[1]
def clip_y(S, y0=0.0):
    """keep y <= y0 (no caps)"""
    V, F = S; T = V[F]; d = T[:, :, 1] - y0; out = []
    keep = (d <= 0).all(1); out.append(T[keep]); mixed = np.where(~keep & ~(d > 0).all(1))[0]
    for k in mixed:
        P = T[k]; dd = d[k]; inside = [i for i in range(3) if dd[i] <= 0]; outside = [i for i in range(3) if dd[i] > 0]
        def cut(i, j): t = dd[i] / (dd[i] - dd[j]); return P[i] + t * (P[j] - P[i])
        if len(inside) == 1:
            a = inside[0]; b, c = outside; out.append(np.array([[P[a], cut(a, b), cut(a, c)]]))
        else:
            a, b = inside; c = outside[0]; pa, pb = cut(a, c), cut(b, c); out.append(np.array([[P[a], P[b], pb], [P[a], pb, pa]]))
    T2 = np.concatenate(out) if out else np.zeros((0, 3, 3)); return T2.reshape(-1, 3), np.arange(len(T2) * 3).reshape(-1, 3)
# ------------------------------------------------------------------ colours
C_PETG = (0.70, 0.76, 0.84); C_CF = (0.13, 0.13, 0.15); C_CU = (0.86, 0.50, 0.28); C_PCB = (0.10, 0.52, 0.28); C_FERR = (0.24, 0.24, 0.29); C_FOAM = (0.97, 0.88, 0.52); C_ALU = (0.93, 0.47, 0.16)
C_GEL = (0.40, 0.80, 0.92); C_ORG = (0.85, 0.30, 0.20); C_BLU = (0.20, 0.40, 0.85); C_BAT = (0.95, 0.78, 0.20); C_GRIP = (0.20, 0.22, 0.26); C_ACC = (0.88, 0.40, 0.10); C_GOLD = (0.85, 0.70, 0.25)
AL = math.radians(55.0); D = np.array([math.cos(AL), 0, math.sin(AL)]); E = np.array([math.sin(AL), 0, -math.cos(AL)]); EY = np.array([0, 1.0, 0]); P0 = np.array([0, 0, 58.0])
S_NPM, S_ELB, S_UP = 467.0, 1185.0, 573.0
def build(cut):
    P = []
    def add(S, c, a=1.0, cuty=None, name=""):
        if cut and cuty is not None: S = clip_y(S, cuty)
        P.append(dict(V=S[0], F=S[1], c=c, a=a, name=name))
    hs = (math.pi, 2 * math.pi) if cut else (0.0, 2 * math.pi)
    # ---------------- head (proxies)
    T = 0.359
    body = [(52.5, 0), (116.5, 0), (116.5, 13), (62.4, 13 + 54.1 * T), (62.4, 42), (59, 42), (59, 3), (52.5, 3)]
    add(revolve(body, *hs, n=120), C_PETG, 1.0, name="head body")
    add(revolve([(0, -2.8), (116, -2.8), (116, -0.4), (0, -0.4)], *hs, n=120), C_PCB, 1.0, name="SB1 antenna board")
    add(revolve([(0, -4.5), (112, -4.5), (112, -2.8), (0, -2.8)], *hs, n=120), (0.30, 0.31, 0.34), 1.0, name="skid")
    add(revolve([(116.5, -4.5), (120.5, -4.5), (120.5, 13.5), (116.5, 13.5)], *hs, n=120), (0.22, 0.23, 0.26), 1.0, name="bezel")
    if cut:
        for k in range(8):                                                                # outer band: 8 turns x 2 stacked, inside the grooves (shown only in the section)
            r = 74 + k * 5.7; z0 = 13 + (116.5 - r) * T
            for dz in (-1.6, 0.6): add(torus(r + 1.0, 0.7, z0 + dz, *hs, n1=140), C_CU, 1.0, name="winding")
    add(revolve([(0, 3), (58.8, 3), (58.8, 41.8), (0, 41.8)], *hs, n=96), C_FOAM, 0.30, name="syntactic foam in the drum")
    add(revolve([(0, 42), (64, 42), (64, 45.2), (0, 45.2)], *hs, n=96), C_PETG, 1.0, name="lid")
    for sx in (-1, 1): add(box(sx * 22, 0, 57, 6, 34, 26), C_PETG, 1.0, 0.0 if cut else None, name="yoke")
    add(cyl((-30, 0, 58), (30, 0, 58), 5, 24), (0.7, 0.7, 0.72), 1.0, 0.0 if cut else None, name="pivot")
    # ferrite vault (closed MnZn box, 3 mm) and what is inside
    vz0, vz1 = 3.0, 39.0
    cy = (-0.0 if not cut else 0.0)
    walls = [box(0, 0, 4.5, 80, 80, 3), box(0, 0, 37.5, 80, 80, 3)] + [box(sx * 38.5, 0, 21, 3, 80, 33) for sx in (-1, 1)] + [box(0, sy * 38.5, 21, 74, 3, 33) for sy in (-1, 1)]
    for W in walls: add(W, C_FERR, 1.0, 0.0 if cut else None, name="ferrite vault")
    gel = box(0, -18.5 if cut else 0, 21, 74, 37 if cut else 74, 30); add(gel, C_GEL, 0.22, name="silicone gel in the vault")
    for z, name in ((8.0, "AB1A"), (14.3, "AB1B")):
        add(cyl((0, 0, z), (0, 0, z + 1.6), 20, 40), C_PCB, 1.0, 0.0 if cut else None, name=name)
        add(box(8, -6, z + 3, 8, 6, 3), (0.1, 0.1, 0.1), 1.0, 0.0 if cut else None, name=name + " parts")
    add(box(0, 0, 19.4, 70, 70, 0.6), C_CU, 1.0, 0.0 if cut else None, name="foil septum")
    try:
        cb = load_stl("kit_v6/CB1/PF233-CB1_board_with_components.stl"); add((cb[0] + [0, 0, 21.0], cb[1]), C_PCB, 1.0, 0.0 if cut else None, name="CB1")
    except Exception: add(box(0, 0, 22, 70, 70, 1.6), C_PCB, 1.0, name="CB1")
    # ---------------- shaft
    def tube_world(s0, s1, ro, ri, c, name, n=36):
        prof = [(ro, 0), (ro, s1 - s0), (ri, s1 - s0), (ri, 0)]; V, F = revolve(prof, *hs, n=n)           # axis z, shift and align to D
        A = np.array([EY, np.cross(D, EY), D]).T                                                          # local z -> D, local x -> -E ... orthonormal
        W = (V @ np.array([np.cross(EY, D), EY, D])) if False else None
        ex = np.cross(EY, D); Vw = P0 + (s0) * D + np.outer(V[:, 0], ex) + np.outer(V[:, 1], EY) + np.outer(V[:, 2], D)
        return Vw, F
    def tube_cut(s0, s1, ro, ri, c, name):
        # full tube, cut with the world plane y = 0 (the tube axis lies in that plane)
        prof = [(ro, 0), (ro, s1 - s0), (ri, s1 - s0), (ri, 0)]; V, F = revolve(prof, 0.0, 2 * math.pi, n=40); ex = np.cross(EY, D)
        Vw = P0 + s0 * D + np.outer(V[:, 0], ex) + np.outer(V[:, 1], EY) + np.outer(V[:, 2], D); return Vw, F
    add(tube_cut(0, 445, 16.0, 14.5, C_CF, "lower tube"), (0.20, 0.21, 0.25), 1.0, 0.0 if cut else None, name="lower shaft tube D32")
    add(tube_cut(S_UP, S_UP + 500, 16.0, 14.5, C_CF, "outer tube"), (0.20, 0.21, 0.25), 1.0, 0.0 if cut else None, name="upper outer tube D32")
    add(tube_cut(S_UP + 500, S_ELB - 40, 14.25, 13.0, C_CF, "inner tube"), (0.30, 0.31, 0.35), 1.0, 0.0 if cut else None, name="inner tube D28.5")
    # ---------------- NPM
    O_npm = P0 + S_NPM * D
    def npm(S, c, a=1.0, nm=""):
        add(place(S, O_npm, -E, -EY, D), c, a, None, nm)
    for nme, col in (("NPM_N1_body_with_tunnel", C_PETG), ("NPM_N2_lid_with_fill_ports", (0.62, 0.70, 0.80)), ("NPM_N3_hot_zone_dam", (0.55, 0.55, 0.6))):
        S = load_stl(f"kit_v6/SPINE/{nme}.stl"); S = place(S, O_npm, -E, -EY, D)
        if cut and nme != "NPM_N3_hot_zone_dam": S = clip_y(S, -15.0)
        P.append(dict(V=S[0], F=S[1], c=col, a=1.0, name=nme))
    pb = load_stl("kit_v6/PB1R/PF233-PB1R_board_with_components.stl"); Vb = np.c_[pb[0][:, 0], 34.0 - pb[0][:, 2], 42.0 + pb[0][:, 1]]
    Sb = place((Vb, pb[1]), O_npm, -E, -EY, D); Sb = clip_y(Sb, -15.0) if cut else Sb; P.append(dict(V=Sb[0], F=Sb[1], c=C_PCB, a=1.0, name="PB1R"))
    hotz = place(box(-23, 26.0 if cut else 25.5, 42, 36, 22.0 if cut else 23, 76), O_npm, -E, -EY, D); P.append(dict(V=hotz[0], F=hotz[1], c=C_ALU, a=0.40, name="alumina hot zone"))
    mainz = place(box(18, 26.0 if cut else 25.5, 42, 58, 22.0 if cut else 23, 76), O_npm, -E, -EY, D); P.append(dict(V=mainz[0], F=mainz[1], c=C_FOAM, a=0.30, name="syntactic main zone"))
    # ---------------- cassettes, ribbons and trolleys inside the shaft (visible only in the cut)
    if cut:
        nrm = np.cross(D, EY); cas = load_stl("kit_v6/SPINE/CAS_R1_cassette_segment_150.stl"); tr = load_stl("kit_v6/SPINE/CAS_R2_trolley.stl")
        cp = lambda S, s: clip_y(place(S, P0 + s * D, EY, nrm, D), 0.0)
        for s in list(np.arange(80, 380, 150)) + list(np.arange(S_UP + 20, S_UP + 560, 150)):
            S = cp(cas, s); P.append(dict(V=S[0], F=S[1], c=(0.82, 0.84, 0.88), a=1.0, name="cassette"))
        for nm, yy, col in (("power ribbon", 4.1, C_ORG), ("signal ribbon", -4.1, C_BLU)):
            for (a, b) in ((60, 440), (S_UP, S_ELB - 60)):
                Sx = box(0, yy, (b - a) / 2, 12, 0.6, b - a); S = cp(Sx, a); P.append(dict(V=S[0], F=S[1], c=col, a=1.0, name=nm))
        for s in (S_UP + 230, S_UP + 350):
            for yy, col in ((4.1, C_ACC), (-4.1, C_ACC)):
                Sx = (tr[0] + [0, yy, 0], tr[1]); S = cp(Sx, s); P.append(dict(V=S[0], F=S[1], c=col, a=1.0, name="trolley"))
    # ---------------- elbow, grip, battery drawer
    O_e = P0 + S_ELB * D; mp = lambda S: place(S, O_e, E, EY, D)
    for nme, col, cutit in (("ELB_E1_elbow_and_grip", C_GRIP, True), ("ELB_E2_grip_endcap", C_GRIP, False), ("ELB_E3_trigger", C_ACC, False), ("ELB_E4_joystick_boss", C_ACC, False),
                            ("ELB_E5_forearm_cuff", (0.30, 0.32, 0.36), False), ("BAT_B1_drawer_sleeve", (0.35, 0.38, 0.44), True), ("BAT_B2_end_cap_with_latch", C_ACC, False), ("BAT_B3_contact_plate", C_GOLD, True)):
        S = mp(load_stl(f"kit_v6/SPINE/{nme}.stl"))
        if nme == "ELB_E4_joystick_boss": S = place((load_stl(f"kit_v6/SPINE/{nme}.stl")[0] + [95, 0, 20 + 18.0], load_stl(f"kit_v6/SPINE/{nme}.stl")[1]), O_e, E, EY, D)
        if nme == "ELB_E5_forearm_cuff":
            V0, F0 = load_stl(f"kit_v6/SPINE/{nme}.stl"); V0 = np.c_[V0[:, 2] + 215.0, V0[:, 1], -V0[:, 0] + 55.0]; S = place((V0, F0), O_e, E, EY, D)
        if cut and cutit: S = clip_y(S, 0.0)
        P.append(dict(V=S[0], F=S[1], c=col, a=1.0, name=nme))
    BZ = 20.0 - 18.0 - 1.5 - 15.0
    for k, x0 in enumerate((70.0, 135.0, 200.0, 265.0)):                                         # U-pack row of 4
        Sx = cyl((x0, -9.5, BZ), (x0 + 64, -9.5, BZ), 9.3, 20); P.append(dict(V=place(Sx, O_e, E, EY, D)[0], F=Sx[1], c=C_BAT, a=1.0, name="18650"))
    for k, x0 in enumerate((135.0, 200.0, 265.0)):
        Sx = cyl((x0, 9.5, BZ), (x0 + 64, 9.5, BZ), 9.3, 20); S = place(Sx, O_e, E, EY, D)
        if cut: S = clip_y(S, 0.0)
        P.append(dict(V=S[0], F=S[1], c=C_BAT, a=1.0, name="18650"))
    pm = load_stl("kit_v4/POWER/PM1.stl") if os.path.exists("kit_v4/POWER/PM1.stl") else None
    try: pm = load_stl("legacy/PHIFOLD233_FINAL_KIT_v4/03_POWER_BOARD_PM1/PF233-PM1_board_with_components.stl")
    except Exception: pm = None
    if pm is not None:
        Vp = np.c_[40.0 + (pm[0][:, 1] + 68.0), pm[0][:, 0], 20.0 - 6.0 + pm[0][:, 2]]; S = place((Vp, pm[1]), O_e, E, EY, D); S = clip_y(S, 0.0) if cut else S; P.append(dict(V=S[0], F=S[1], c=C_PCB, a=1.0, name="PM1"))
    hb = load_stl("kit_v6/HB1/PF233-HB1_board_with_components.stl"); Vh = np.c_[95.0 + hb[0][:, 1], hb[0][:, 0], 20.0 + 10.5 - hb[0][:, 2]]; S = place((Vh, hb[1]), O_e, E, EY, D); S = clip_y(S, 0.0) if cut else S; P.append(dict(V=S[0], F=S[1], c=C_PCB, a=1.0, name="HB1"))
    for i in range(5):
        for j in (-1, 1):
            Sx = cyl((-10, 7.5 * j, -2 + 10 * i), (10, 7.5 * j, -2 + 10 * i), 5, 14); S = place(Sx, O_e, E, EY, D); S = clip_y(S, 0.0) if cut else S; P.append(dict(V=S[0], F=S[1], c=(0.20, 0.45, 0.30), a=1.0, name="supercap"))
    gp = place(box(70, -8.5 if cut else 0, 20, 136, 17 if cut else 34, 29), O_e, E, EY, D); S = gp
    P.append(dict(V=S[0], F=S[1], c=C_FOAM, a=0.28, name="syntactic fill in the grip"))
    ep = place(box(0, -10 if cut else 0, 21, 48, 20 if cut else 40, 62), O_e, E, EY, D); S = ep; P.append(dict(V=S[0], F=S[1], c=C_FOAM, a=0.28, name="syntactic fill in the elbow"))
    return P
# ------------------------------------------------------------------ renderer
def render(P, out, az=70.0, el=22.0, centre=(300, 0, 500), scale=0.9, size=(1900, 1150), title="", labels=(), SS=2, bg=((236, 240, 246), (252, 253, 255)), caption="", rolly=0.0, drop=(), layout="cols"):
    w, h = size; W, H = w * SS, h * SS
    ph = math.radians(rolly); Ry = np.array([[math.cos(ph), 0, math.sin(ph)], [0, 1, 0], [-math.sin(ph), 0, math.cos(ph)]])
    P = [dict(p, V=p["V"] @ Ry.T) for p in P if p["name"] not in drop]; centre = np.asarray(centre, float) @ Ry.T; labels = [(t, np.asarray(q, float) @ Ry.T, o) for t, q, o in labels]; img = Image.new("RGB", (W, H)); dr = ImageDraw.Draw(img)
    for y in range(H): t = y / H; dr.line([(0, y), (W, y)], fill=tuple(int(bg[0][i] * (1 - t) + bg[1][i] * t) for i in range(3)))
    a, e = math.radians(az), math.radians(el); c = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)]); f = -c
    right = np.cross(f, [0, 0, 1.0]); right /= np.linalg.norm(right); up = np.cross(right, f)
    cen = np.asarray(centre, float); s = scale * SS
    proj = lambda V: np.c_[W / 2 + s * ((V - cen) @ right), H / 2 - s * ((V - cen) @ up)]
    L = -f * 0.55 + up * 0.75 - right * 0.55; L /= np.linalg.norm(L)
    tris, cols, alph, dep = [], [], [], []
    for p in P:
        V = p["V"]; F = p["F"]
        if len(F) == 0: continue
        T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(n, axis=1) + 1e-12; n = n / ln[:, None]
        sh = 0.32 + 0.68 * np.abs(n @ L); sh = np.where(ln < 1e-9, 0.5, sh)
        col = np.clip(np.array(p["c"])[None, :] * sh[:, None], 0, 1) * 255
        S2 = proj(T.reshape(-1, 3)).reshape(-1, 3, 2); tris.append(S2); cols.append(col); alph.append(np.full(len(F), p["a"])); dep.append(((T.mean(1) - cen) @ f))
    tris = np.concatenate(tris); cols = np.concatenate(cols); alph = np.concatenate(alph); dep = np.concatenate(dep)
    order = np.argsort(-dep)
    # ground shadow of the head
    sh_img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh_img)
    ang = np.linspace(0, 2 * np.pi, 90); Vs = np.c_[130 * np.cos(ang), 130 * np.sin(ang), np.full(90, -4.6)]
    sd.polygon([tuple(q) for q in proj(Vs @ Ry.T)], fill=(40, 50, 70, 70)) if rolly == 0 else None; img.paste(Image.alpha_composite(img.convert("RGBA"), sh_img).convert("RGB"))
    dr = ImageDraw.Draw(img, "RGBA")
    for i in order:
        t = tris[i]; cc = cols[i]; al = alph[i]; fill = (int(cc[0]), int(cc[1]), int(cc[2]), int(255 * al))
        dr.polygon([(t[0, 0], t[0, 1]), (t[1, 0], t[1, 1]), (t[2, 0], t[2, 1])], fill=fill, outline=(fill[0], fill[1], fill[2], fill[3]) if al >= 1 else None)
    img = img.resize((w, h), Image.LANCZOS); d2 = ImageDraw.Draw(img)
    d2.text((26, 18), title, fill=(20, 28, 45), font=font(30, True))
    if caption:
        import textwrap
        for k, ln in enumerate(textwrap.wrap(caption, width=int((w - 50) / 9.6))): d2.text((26, 58 + 23 * k), ln, fill=(70, 80, 100), font=font(17))
    pr = lambda p3: ((w / 2 + scale * ((np.asarray(p3, float) - cen) @ right)), (h / 2 - scale * ((np.asarray(p3, float) - cen) @ up)))
    fnt = font(17); items = []
    for txt, pt, off in labels:
        x, y = pr(pt); bb = d2.textbbox((0, 0), txt, font=fnt); items.append(dict(t=txt, x=x, y=y, tw=bb[2] - bb[0], th=bb[3] - bb[1]))
    if layout == "rows":
        placed = {"T": [], "B": []}
        for it in sorted(items, key=lambda it: it["x"]):
            band = "T" if it["y"] < h / 2 else "B"; tx = int(min(max(it["x"] - it["tw"] / 2, 24), w - it["tw"] - 24)); lvl = 0
            while True:
                ty = (100 + lvl * 44) if band == "T" else (h - 70 - lvl * 44)
                if all(not (abs(ty - q[1]) < 36 and tx < q[0] + q[2] + 16 and q[0] < tx + it["tw"] + 16) for q in placed[band]): break
                lvl += 1
            placed[band].append((tx, ty, it["tw"])); ex = ty + it["th"] + 10 if band == "T" else ty - 4
            d2.line([(it["x"], it["y"]), (tx + it["tw"] / 2, ex)], fill=(30, 40, 60), width=2); d2.ellipse([it["x"] - 4, it["y"] - 4, it["x"] + 4, it["y"] + 4], fill=(30, 40, 60))
            d2.rectangle([tx - 6, ty - 4, tx + it["tw"] + 6, ty + it["th"] + 8], fill=(255, 255, 255), outline=(30, 40, 60)); d2.text((tx, ty), it["t"], fill=(15, 20, 35), font=fnt)
    else:
      for side in ("L", "R"):
          grp = sorted([it for it in items if ((it["x"] < w / 2) == (side == "L"))], key=lambda it: it["y"]); prev = 90
          for it in grp:
              ty = max(prev + 40, min(h - 60, it["y"] - 12)); prev = ty; tx = 30 if side == "L" else w - 30 - it["tw"]
              ex = tx + it["tw"] + 6 if side == "L" else tx - 6
              d2.line([(it["x"], it["y"]), (ex, ty + it["th"] / 2 + 3)], fill=(30, 40, 60), width=2); d2.ellipse([it["x"] - 4, it["y"] - 4, it["x"] + 4, it["y"] + 4], fill=(30, 40, 60))
              d2.rectangle([tx - 6, ty - 4, tx + it["tw"] + 6, ty + it["th"] + 8], fill=(255, 255, 255), outline=(30, 40, 60)); d2.text((tx, ty), it["t"], fill=(15, 20, 35), font=fnt)
    img.save(out); return pr
O_NPM = P0 + S_NPM * D; O_ELB = P0 + S_ELB * D
npm_pt = lambda x, y, z: O_NPM + x * (-E) + y * (-EY) + z * D
elb_pt = lambda x, y, z: O_ELB + x * E + y * EY + z * D
sh_pt = lambda s, n=0.0: P0 + s * D
def final():
    os.makedirs("kit_v6/RENDER", exist_ok=True)
    Pc = build(False); Pd = build(True); far = ("lower shaft tube D32", "cassette", "power ribbon", "signal ribbon", "trolley", "upper outer tube D32", "inner tube D28.5")
    render(Pc, "kit_v6/RENDER/01_FULL_CONCEPT.png", az=62, el=15, centre=(330, 0, 560), scale=0.95, size=(1800, 1280), title="PHI-FOLD 233 v6 - finished concept (extended)",
           caption="sealed head (receive + controller, ferrite vault)  |  neck power module  |  dual-chamber telescoping shaft  |  elbow handle with quick-swap battery",
           labels=[("Search head D233: ferrite-vaulted receive + controller, potted", (60, 0, 20), 0), ("Neck power module (PB1R TX stage), potted", npm_pt(0, 30, 40), 0), ("Telescoping shaft: 2 ribbon chambers on tracks", sh_pt(850), 0),
                   ("Elbow + grip: PM1, HB1, supercap bridge", elb_pt(40, 0, 40), 0), ("Quick-swap battery drawer, hangs behind the hand", elb_pt(300, 0, -15), 0), ("Joystick", elb_pt(95, 0, 40), 0), ("Trigger", elb_pt(62, 0, -10), 0)])
    render(Pc, "kit_v6/RENDER/02_HEAD_CLOSEUP.png", az=38, el=30, centre=(0, 0, 25), scale=4.3, size=(1700, 1100), drop=far, title="Search head - sealed, finished (D233 x 33 mm, yoke on top)", caption="no connectors on the head: one sealed cable (power + trigger/dial/joystick) leaves at the yoke")
    render(Pd, "kit_v6/RENDER/03_DISSECTED_SYSTEM.png", az=90, el=0, centre=(330, 0, 560), scale=0.95, size=(1800, 1280), title="PHI-FOLD 233 v6 - dissected (section through the axis plane)",
           caption="yellow = glass-bubble syntactic foam | orange = alumina hot zone | cyan = silicone gel | dark = closed MnZn ferrite vault | copper = winding | orange/blue strips = ribbons",
           labels=[("Head: AB1A, AB1B, CB1 in a closed ferrite vault", (0, 0, 22), 0), ("Outer-band winding in the cone", (96, 0, 21), 0), ("Neck power module: PB1R (alumina hot zone)", npm_pt(-20, 26, 40), 0),
                   ("Dual-chamber cassettes + ribbons", sh_pt(750), 0), ("Fixed lower tube D32", sh_pt(250), 0), ("Elbow: PM1, HB1, supercap bridge", elb_pt(40, 0, 25), 0), ("Grip (syntactic-filled)", elb_pt(140, 0, 20), 0), ("U-pack battery drawer", elb_pt(220, 0, -15), 0), ("Trigger", elb_pt(62, 0, -12), 0)])
    render(Pd, "kit_v6/RENDER/04_DISSECTED_HEAD.png", az=80, el=22, centre=(0, 0, 22), scale=4.6, size=(1800, 1180), drop=far, title="Dissected head: closed ferrite vault, three-board stack, potting",
           caption="stack bottom to top: AB1A, AB1B, copper-foil septum, CB1 (controller + coil interface); gel inside the vault, foam around it, winding in the cone",
           labels=[("MnZn ferrite vault wall, 3 mm closed box", (-38.5, 0, 21), 0), ("CB1 controller + coil interface", (10, 0, 26), 0), ("foil septum (E-shield)", (30, 0, 19.4), 0), ("AB1B receiver", (14, 0, 15), 0), ("AB1A receiver", (14, 0, 8.8), 0),
                   ("silicone gel in the vault", (-30, -12, 28), 0), ("syntactic foam in the drum", (-55, -10, 36), 0), ("outer-band Litz winding", (96, 0, 21), 0), ("SB1 antenna board (8 layers)", (100, 0, -1.6), 0), ("lid + yoke", (22, 0, 66), 0)])
    render(Pd, "kit_v6/RENDER/05_DISSECTED_NPM.png", az=90, el=0, rolly=-35, centre=tuple(npm_pt(0, 25, 40)), scale=7.0, size=(1500, 1250), title="Dissected neck power module (shaft base)", caption="PB1R potted: alumina-filled hot zone (FETs, clamp bank) + syntactic remainder; section plane 15 mm off the axis shows the board",
           drop=("cassette", "trolley"), labels=[("PB1R TX power stage", npm_pt(0, 30, 42), 0), ("alumina-filled hot zone", npm_pt(-24, 26, 55), 0), ("syntactic main zone", npm_pt(20, 26, 30), 0), ("fill / vent ports (lid)", npm_pt(-25, 42, 40), 0),
                   ("fixed lower tube D32", sh_pt(S_NPM - 90), 0), ("upper outer tube D32", sh_pt(S_NPM + 125), 0), ("hot-zone dam", npm_pt(-5, 28, 40), 0)])
    render(Pd, "kit_v6/RENDER/06_DISSECTED_TELESCOPE.png", az=90, el=0, rolly=55, centre=tuple(sh_pt(S_UP + 330)), scale=2.7, size=(1800, 760), layout="rows", drop=("NPM_N1_body_with_tunnel", "NPM_N2_lid_with_fill_ports", "NPM_N3_hot_zone_dam", "PB1R", "alumina hot zone", "syntactic main zone"),
           title="Dissected telescoping section: two ribbon chambers on tracks", caption="each cassette has chamber A (power ribbon, upper) and chamber B (signal ribbon, lower) split by a foil septum; the U-loop trolley rides on guide ribs and travels at half the stroke",
           labels=[("D32 outer tube (fixed to the NPM)", sh_pt(S_UP + 60), 0), ("D28.5 inner tube (slides out 450 mm)", sh_pt(S_UP + 620), 0), ("cassette segment, 2 chambers + septum", sh_pt(S_UP + 330), 0), ("trolley + U-loop post", sh_pt(S_UP + 235), 0), ("power ribbon, chamber A", sh_pt(S_UP + 450), 0), ("signal ribbon, chamber B", sh_pt(S_UP + 140), 0)])
    render(Pd, "kit_v6/RENDER/07_DISSECTED_ELBOW_HANDLE.png", az=90, el=0, rolly=-35, centre=tuple(elb_pt(150, 0, 0)), scale=3.9, size=(1800, 1100), drop=far, title="Dissected elbow, grip and battery drawer", caption="PM1 + HB1 potted in the grip, supercap bridge in the elbow, battery drawer under the grip (counterweight behind the hand)",
           labels=[("PM1 power path", elb_pt(110, 0, 14), 0), ("HB1: Hall trigger, joystick, dial ladder", elb_pt(95, 0, 30), 0), ("1 F / 27 V supercap bridge", elb_pt(0, 0, 25), 0), ("U-pack 7S 18650, 90.7 Wh", elb_pt(200, 0, -15), 0), ("battery contact plate", elb_pt(30, 0, -15), 0), ("trigger (magnet over Hall)", elb_pt(62, 0, -12), 0), ("syntactic fill", elb_pt(160, 0, 20), 0)])
if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "final": final(); sys.exit()
if __name__ == "__main__":
    os.makedirs("kit_v6/RENDER", exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    if mode == "test":
        import time; t0 = time.time(); P = build(False); print("build", round(time.time() - t0, 1), "s", sum(len(p["F"]) for p in P), "tris")
        t0 = time.time(); render(P, "kit_v6/RENDER/test_full.png", scale=0.5, size=(1000, 700), SS=1, title="test"); print("render", round(time.time() - t0, 1), "s")
