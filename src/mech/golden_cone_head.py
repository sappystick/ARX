#!/usr/bin/env python3
"""
golden_cone_head.py  —  "Phyllo-34" golden-cone array search head (9.7 in)
==========================================================================
34 golden-ratio truncated cones (Fibonacci rings 13 + 21) on a 9.7" face.
Each cone is a mini toroidal (Rodin-style) bobbin: 3 independent Litz
windings (sections A, B, C) enter through the cone's bore, run outward in a
tunnel under the cone base, spiral UP the outer slope, cross the tip land,
spiral DOWN the bore wall and exit through the face plate.  Every segment of
every winding circulates the same way (dphi/ds > 0), so all turns add to the
cone's magnetic moment.  No wire is exposed: slope/bore grooves are flush
(wire top = skin) and the underside run is a tunnel closed by the face plate.

Golden cone (Kepler-triangle cross-section):
    slope angle   alpha = arccos(1/phi) = 51.8273 deg
    slant length  = R_b                 (slant/radius of full cone = phi)
    height        H   = R_b / sqrt(phi)
    tip radius    R_t = R_b / phi^2     (tip/base diameter = 0.381966)
    full-apex height H_apex = R_b*sqrt(phi), truncation H/H_apex = 1/phi
Packing: ring radii rho_n = d / (2 sin(pi/n)), n = 13, 21, bases touching
inside each ring; outer ring touches the face edge R_face.
"""
import math, json, os, struct, time
import numpy as np
from scipy.spatial import Delaunay
import rodin_core_v4 as rc        # reuse Q, Blend, Line, eval_profile, writers

PHI = (1 + 5 ** 0.5) / 2
GOLDEN_ANGLE = 2 * math.pi / PHI ** 2

# ---------------- footprint & packing ----------------
OD_IN      = 9.7
R_OUT      = OD_IN * 25.4 / 2            # 123.19 housing radius
RIM_W      = 3.19                        # rim/lip ring width
R_FACE     = R_OUT - RIM_W               # 120.00 cone field radius
N_IN, N_OUT = 13, 21                     # Fibonacci rings -> 34 cones
D_BASE     = R_FACE / (1 / (2 * math.sin(math.pi / N_OUT)) + 0.5)
R_B        = D_BASE / 2
RHO_OUT    = D_BASE / (2 * math.sin(math.pi / N_OUT))
RHO_IN     = D_BASE / (2 * math.sin(math.pi / N_IN))
IN_OFFSET  = GOLDEN_ANGLE % (2 * math.pi / N_IN)   # inner ring rotated by golden angle

# ---------------- golden cone ----------------
ALPHA = math.acos(1 / PHI)
H     = R_B / math.sqrt(PHI)
R_T   = R_B / PHI ** 2
R_BORE = 2.80
# convex-corner blend radii (min, G2 blends)
RHO_BASE, RHO_TIPO, RHO_TIPI, RHO_BOREB = 0.6, 1.6, 1.0, 0.8

# ---------------- windings ----------------
N_WIRES  = 3                       # sections A, B, C
WIRE_OD  = 0.80                    # 40/40 AWG Litz, PU (user spec)
A_SEAT   = WIRE_OD / 2 + 0.05      # 0.45 seat radius -> groove 0.90 wide
G_DEPTH  = 0.80                    # flush: wire top = skin
G_LAND   = 0.30
P_MIN    = 2 * A_SEAT + 2 * G_LAND + 0.05     # 1.55 mm min perpendicular lane pitch
DENS     = dict(bottom=0.30, slope=1.30, tip=1.30, bore=1.25)   # dphi/ds [rad/mm] (pitch-limited)

# ---------------- face plate / housing ----------------
PLATE_T  = 3.0
RIM_H, LIP_IN, LIP_T = 4.0, 1.2, 1.0
CUP_DEPTH, CUP_WALL, CUP_FLOOR, CUP_HOLE = 18.0, 2.5, 2.5, 10.0

# =====================================================================
# cone meridian profile (closed, CCW): bottom -> base blend -> slope ->
# tip-out blend -> tip -> tip-in blend -> bore -> bore-bottom blend
# =====================================================================
def build_cone_profile():
    V0 = np.array([R_BORE, 0.0]); V1 = np.array([R_B, 0.0])
    V2 = np.array([R_T, H]);      V3 = np.array([R_BORE, H])
    hb, hs, ht, hd = 0.0, math.pi - ALPHA, math.pi, 1.5 * math.pi
    u = lambda h: np.array([math.cos(h), math.sin(h)])
    def corner(ha, hb_, rho):
        dturn = (hb_ - ha) % (2 * math.pi)
        L = dturn * rho / (1 - rc.BLEND_F)
        ch, _ = rc.Blend.unit_chord(ha, dturn); ch *= L
        s = u(ha) + u(hb_); d = ch.dot(s) / s.dot(s)
        return dturn, L, d
    c0 = corner(hd, hb + 2 * math.pi, RHO_BOREB)
    c1 = corner(hb, hs, RHO_BASE)
    c2 = corner(hs, ht, RHO_TIPO)
    c3 = corner(ht, hd, RHO_TIPI)
    segs = []
    def line(name, A, Bv, h, da, db):
        L = np.linalg.norm(Bv - A) - da - db
        assert L > 0, f"segment {name} too short"
        segs.append((name, rc.Line(A + da * u(h), h, L)))
    line("bottom", V0, V1, hb, c0[2], c1[2])
    segs.append(("base_blend", rc.Blend(V1 - c1[2] * u(hb), hb, c1[0], c1[1])))
    line("slope", V1, V2, hs, c1[2], c2[2])
    segs.append(("tip_out_blend", rc.Blend(V2 - c2[2] * u(hs), hs, c2[0], c2[1])))
    line("tip", V2, V3, ht, c2[2], c3[2])
    segs.append(("tip_in_blend", rc.Blend(V3 - c3[2] * u(ht), ht, c3[0], c3[1])))
    line("bore", V3, V0, hd, c3[2], c0[2])
    segs.append(("bore_blend", rc.Blend(V0 - c0[2] * u(hd), hd, c0[0], c0[1])))
    return segs

class Cone:
    def __init__(self):
        self.segs = build_cone_profile()
        self.off, self.L = rc.seg_offsets(self.segs)
        sf = np.linspace(0, self.L, 200001)
        r = rc.eval_profile(self.segs, sf)[0]
        # target twist density per section, smoothly ramped across blends
        sec = {"bottom": "bottom", "slope": "slope", "tip": "tip", "bore": "bore"}
        dens = {n: DENS[n] for n in sec}
        order = [n for n, _ in self.segs]
        g = np.zeros_like(sf)
        for i, (name, sg) in enumerate(self.segs):
            o = self.off[name]; m = (sf >= o) & (sf <= o + sg.L)
            if name in dens:
                g[m] = dens[name]
            else:   # blend: quintic ramp between neighbours
                a = dens[order[i - 1]]; b = dens[order[(i + 1) % len(order)]]
                t = (sf[m] - o) / sg.L
                g[m] = a + (b - a) * rc.Q(t)
        c = np.concatenate([[0], np.cumsum((g[1:] + g[:-1]) / 2 * np.diff(sf))])
        # closure: total twist must be a multiple of 2pi/3 -> scale bottom density
        total = c[-1]; step = 2 * math.pi / N_WIRES
        target = round(total / step) * step
        mb = np.zeros_like(sf, bool)
        o = self.off["bottom"]; mb |= (sf >= o) & (sf <= o + dict(self.segs)["bottom"].L)
        extra = (target - total) / dict(self.segs)["bottom"].L
        g = g + np.where(mb, extra, 0.0)
        c = np.concatenate([[0], np.cumsum((g[1:] + g[:-1]) / 2 * np.diff(sf))])
        self.sf, self.g, self.c, self.r_f = sf, g, c, r
        self.total_twist = c[-1]
        self.k_shift = int(round(self.total_twist / step))
        self.net_turns = self.total_twist / (2 * math.pi)

    def twist(self, s):  return np.interp(s, self.sf, self.c)
    def dens(self, s):   return np.interp(s, self.sf, self.g)

    def rows(self, ds_line, ds_blend):
        out = []
        for name, sg in self.segs:
            ds = ds_blend if isinstance(sg, rc.Blend) else ds_line
            n = max(3, int(math.ceil(sg.L / ds)))
            out.append(self.off[name] + np.linspace(0, sg.L, n, endpoint=False))
        return np.unique(np.concatenate(out))

def core_x(a, land, narc):
    return rc.core_x(a, land, narc)

def build_cone_mesh(cone, ds_line=0.12, ds_blend=0.06, narc=9, nfill=6):
    s = cone.rows(ds_line, ds_blend); NR = len(s)
    r, z, h, k, _ = rc.eval_profile(cone.segs, s)
    nr, nz = np.sin(h), -np.cos(h)
    th = cone.twist(s)
    cb = 1 / np.sqrt(1 + (r * cone.dens(s)) ** 2)        # cos(beta) per row
    sig = 1 / (r * cb)
    X = core_x(A_SEAT, G_LAND, narc)
    cut = np.abs(X) < A_SEAT
    D = np.where(cut, rc.seat(X, A_SEAT, -G_DEPTH), 0.0)[None, :].repeat(NR, 0)
    reff = r[:, None] + D * nr[:, None]
    sector = 2 * math.pi / N_WIRES
    blocks, Ds = [], []
    for j in range(N_WIRES):
        p = j * sector + X[None, :] / (reff * cb[:, None])
        blocks.append(p); Ds.append(D)
        eL = j * sector + X[-1] * sig
        eR = (j + 1) * sector + X[0] * sig
        assert np.all(eR > eL), "lanes overlap"
        lam = (np.arange(1, nfill + 1) / (nfill + 1))[None, :]
        f = eL[:, None] + lam * (eR - eL)[:, None]
        blocks.append(f); Ds.append(np.zeros_like(f))
    psi = np.concatenate(blocks, 1); DD = np.concatenate(Ds, 1)
    cpl = psi.shape[1] // N_WIRES
    NC = psi.shape[1]
    phi = psi + th[:, None]
    rv = r[:, None] + DD * nr[:, None]; zv = z[:, None] + DD * nz[:, None]
    V = np.stack([rv * np.cos(phi), rv * np.sin(phi), zv], -1).reshape(-1, 3)
    I, J = np.meshgrid(np.arange(NR), np.arange(NC), indexing="ij")
    J2 = (J + 1) % NC; I2 = (I + 1) % NR
    sh = cone.k_shift * cpl
    Jw = np.where(I == NR - 1, (J + sh) % NC, J); Jw2 = np.where(I == NR - 1, (J2 + sh) % NC, J2)
    v00 = I * NC + J; v01 = I * NC + J2; v10 = I2 * NC + Jw; v11 = I2 * NC + Jw2
    F = np.concatenate([np.stack([v00, v10, v11], -1).reshape(-1, 3), np.stack([v00, v11, v01], -1).reshape(-1, 3)])
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    pitch = r * sector * cb
    return V, F, dict(s=s, r=r, pitch=pitch, NR=NR, NC=NC)

def cone_wires(cone, ds=0.1):
    """3 winding centrelines; wire centre = groove floor + wire radius (flush)."""
    s = cone.rows(ds, ds / 2)
    s = s[s <= cone.off["bore"] + dict(cone.segs)["bore"].L]
    r, z, h, _, _ = rc.eval_profile(cone.segs, s)
    nr, nz = np.sin(h), -np.cos(h)
    off = -G_DEPTH + WIRE_OD / 2
    rv, zv = r + off * nr, z + off * nz
    th = cone.twist(s)
    # wire path: starts at bore bottom (end of bore_blend wraps to s=0 bottom), i.e. the s order
    W = []
    for j in range(N_WIRES):
        ph = j * 2 * math.pi / N_WIRES + th
        W.append(np.stack([rv * np.cos(ph), rv * np.sin(ph), zv], -1))
    return W, s

# =====================================================================
# layout
# =====================================================================
def layout():
    pos = []
    for i in range(N_OUT):
        a = 2 * math.pi * i / N_OUT; pos.append(("outer", i, RHO_OUT * math.cos(a), RHO_OUT * math.sin(a), a))
    for i in range(N_IN):
        a = IN_OFFSET + 2 * math.pi * i / N_IN; pos.append(("inner", i, RHO_IN * math.cos(a), RHO_IN * math.sin(a), a))
    # global index sorted by polar angle (for the golden-stride firing order)
    order = sorted(range(len(pos)), key=lambda k: pos[k][4] % (2 * math.pi))
    return pos, order

def firing_order(order=None):
    """Outer ring stepped by 13 (21/13 ~ phi), inner ring by 8 (13/8 ~ phi);
    the two rings are interleaved in Fibonacci proportion 21:13 (Beatty/golden
    word), so consecutive pulses are always far apart -> minimal residual
    coupling of one cone's decay into the next cone's receive window."""
    outer = [(13 * k) % N_OUT for k in range(N_OUT)]
    inner = [N_OUT + (8 * k) % N_IN for k in range(N_IN)]
    seq, io, ii = [], 0, 0
    for k in range(N_OUT + N_IN):
        # golden (Sturmian) word: inner slot when floor((k+1)/phi^2) increments
        if math.floor((k + 1) / PHI ** 2) > math.floor(k / PHI ** 2) and ii < N_IN:
            seq.append(inner[ii]); ii += 1
        elif io < N_OUT:
            seq.append(outer[io]); io += 1
        else:
            seq.append(inner[ii]); ii += 1
    return seq

# =====================================================================
# simple solids
# =====================================================================
def revolve(poly, nseg=720):
    poly = np.asarray(poly, float); m = len(poly)
    a = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    V = np.stack([poly[None, :, 0] * np.cos(a)[:, None], poly[None, :, 0] * np.sin(a)[:, None],
                  np.broadcast_to(poly[None, :, 1], (nseg, m))], -1).reshape(-1, 3)
    I, J = np.meshgrid(np.arange(nseg), np.arange(m), indexing="ij")
    I2, J2 = (I + 1) % nseg, (J + 1) % m
    F = np.concatenate([np.stack([I * m + J, I2 * m + J, I2 * m + J2], -1).reshape(-1, 3),
                        np.stack([I * m + J, I2 * m + J2, I * m + J2], -1).reshape(-1, 3)])
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F

def plate_with_holes(holes, R, z0, z1, n_out=720, n_hole=40, grid=2.5):
    """Disc with circular through-holes: Delaunay of boundary + interior points,
    holes carved, then extruded.  holes = [(x, y, r)]."""
    ao = np.linspace(0, 2 * np.pi, n_out, endpoint=False)
    loops = [np.stack([R * np.cos(ao), R * np.sin(ao)], -1)]
    for (x, y, r) in holes:
        ah = np.linspace(0, 2 * np.pi, n_hole, endpoint=False)[::-1]
        loops.append(np.stack([x + r * np.cos(ah), y + r * np.sin(ah)], -1))
    gx = np.arange(-R, R + grid, grid)
    G = np.stack(np.meshgrid(gx, gx), -1).reshape(-1, 2)
    G = G + (np.random.default_rng(1).random(G.shape) - 0.5) * 0.15 * grid
    keep = np.hypot(G[:, 0], G[:, 1]) < R - 0.9 * grid
    for (x, y, r) in holes:
        keep &= np.hypot(G[:, 0] - x, G[:, 1] - y) > r + 0.9 * grid
    P2 = np.concatenate(loops + [G[keep]])
    tri = Delaunay(P2).simplices
    cen = P2[tri].mean(1)
    ok = np.hypot(cen[:, 0], cen[:, 1]) < R
    for (x, y, r) in holes:
        ok &= np.hypot(cen[:, 0] - x, cen[:, 1] - y) > r
    tri = tri[ok]
    # boundary edges must all be present
    nb = 0; starts = []
    for L in loops: starts.append(nb); nb += len(L)
    edges = set(map(tuple, np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), 1)))
    for st, L in zip(starts, loops):
        n = len(L)
        for i in range(n):
            e = tuple(sorted((st + i, st + (i + 1) % n)))
            assert e in edges, "boundary edge missing in triangulation"
    nP = len(P2)
    V = np.concatenate([np.c_[P2, np.full(nP, z1)], np.c_[P2, np.full(nP, z0)]])
    # orient top up
    a, b, c = P2[tri[:, 0]], P2[tri[:, 1]], P2[tri[:, 2]]
    cr = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    tri = np.where(cr[:, None] > 0, tri, tri[:, ::-1])
    F = [tri, tri[:, ::-1] + nP]
    for st, L in zip(starts, loops):
        n = len(L); i = np.arange(n); j = (i + 1) % n
        t0, t1, b0, b1 = st + i, st + j, st + i + nP, st + j + nP
        F.append(np.stack([t0, b0, b1], -1)); F.append(np.stack([t0, b1, t1], -1))
    F = np.concatenate(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F

def merge(parts):
    Vs, Fs, o = [], [], 0
    for V, F in parts:
        Vs.append(V); Fs.append(F + o); o += len(V)
    return np.concatenate(Vs), np.concatenate(Fs)

def place(V, x, y, a, dz=0.0):
    c, s_ = math.cos(a), math.sin(a)
    R = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])
    return V @ R.T + np.array([x, y, dz])

# =====================================================================
# electromagnetics (Neumann / Biot-Savart on real centrelines)
# =====================================================================
MU0 = 4e-7 * math.pi
def segs(P, closed=False):
    Q2 = np.roll(P, -1, 0) if closed else P[1:]
    P1 = P if closed else P[:-1]
    return (P1 + Q2) / 2 * 1e-3, (Q2 - P1) * 1e-3

def neumann(m1, d1, m2, d2, chunk=800):
    t = 0.0
    for i in range(0, len(m1), chunk):
        R = np.linalg.norm(m1[i:i + chunk, None] - m2[None], axis=-1)
        t += float(((d1[i:i + chunk] @ d2.T) / R).sum())
    return MU0 / (4 * math.pi) * t

def biot_savart(mids, dls, w, pts):
    B = np.zeros((len(pts), 3))
    for k in range(0, len(mids), 4000):
        m, d, ww = mids[k:k + 4000], dls[k:k + 4000], w[k:k + 4000]
        R = pts[:, None, :] - m[None]
        Rn = np.linalg.norm(R, axis=-1)[..., None]
        B += (np.cross(d[None], R) / Rn ** 3 * ww[None, :, None]).sum(1)
    return MU0 / (4 * math.pi) * B

# =====================================================================
def main(out="out_cones"):
    os.makedirs(out, exist_ok=True)
    cone = Cone()
    rep = {}
    # ---- single cone high-res
    Vc, Fc, mc = build_cone_mesh(cone, 0.08, 0.04, 11, 8)
    good, bad = rc.edge_manifold_check(Fc)
    rc.write_stl(f"{out}/golden_cone_bobbin_HIGH.stl", Vc, Fc, "golden_cone")
    W, sW = cone_wires(cone, 0.05)
    wt = merge([rc.tube_mesh(P[:-1] if np.allclose(P[0], P[-1]) else P, WIRE_OD / 2, 10) for P in W]) if False else None
    rep["single_cone"] = dict(triangles=len(Fc), nonmanifold_edges=bad, volume_mm3=rc.signed_volume(Vc, Fc),
                              min_lane_pitch_mm=float(mc["pitch"].min()),
                              min_groove_wall_mm=float(mc["pitch"].min() - 2 * A_SEAT))
    # wire bend radius (open polylines)
    Rb_all = []
    for P in W:
        a, b, c = P[:-2], P[1:-1], P[2:]
        ab = np.linalg.norm(b - a, axis=1); bc = np.linalg.norm(c - b, axis=1); ca = np.linalg.norm(c - a, axis=1)
        ar = np.linalg.norm(np.cross(b - a, c - a), axis=1)
        Rb_all.append(ab * bc * ca / np.maximum(2 * ar, 1e-15))
    Rb_all = np.concatenate(Rb_all)
    rep["wire"] = dict(min_bend_radius_mm=float(Rb_all.min()), min_bend_xOD=float(Rb_all.min() / WIRE_OD),
                       length_per_winding_mm=float(np.linalg.norm(np.diff(W[0], axis=0), axis=1).sum()),
                       net_azimuthal_turns=float(cone.net_turns))
    # ---- assembly
    pos, order = layout()
    Va, Fa, _ = build_cone_mesh(cone, 0.22, 0.11, 5, 4)
    cones = [(place(Va, x, y, a), Fa) for (_, _, x, y, a) in pos]
    Wlow, _ = cone_wires(cone, 0.25)
    wire_tubes = []
    for (_, _, x, y, a) in pos:
        for P in Wlow:
            Pp = place(P, x, y, a)
            # open tube: build closed-loop tube then it's fine visually; use RMF tube on open path
            wire_tubes.append(open_tube(Pp, WIRE_OD / 2, 8))
    plate = plate_with_holes([(x, y, R_BORE) for (_, _, x, y, a) in pos], R_OUT, -PLATE_T, 0.0)
    rim = revolve([(R_FACE, 0.0), (R_OUT, 0.0), (R_OUT, RIM_H), (R_FACE - LIP_IN, RIM_H),
                   (R_FACE - LIP_IN, RIM_H - LIP_T), (R_FACE, RIM_H - LIP_T)])
    zc0 = -PLATE_T
    cup = revolve([(CUP_HOLE, zc0 - CUP_DEPTH), (R_OUT - 2.0, zc0 - CUP_DEPTH), (R_OUT, zc0 - CUP_DEPTH + 2.0),
                   (R_OUT, zc0), (R_OUT - CUP_WALL, zc0), (R_OUT - CUP_WALL, zc0 - CUP_DEPTH + CUP_FLOOR),
                   (CUP_HOLE, zc0 - CUP_DEPTH + CUP_FLOOR)])
    for nm, (V, F) in [("face_plate", plate), ("rim_lip", rim), ("back_housing", cup)]:
        g, b = rc.edge_manifold_check(F)
        rep[nm] = dict(triangles=len(F), nonmanifold_edges=b, volume_mm3=rc.signed_volume(V, F))
        rc.write_stl(f"{out}/{nm}.stl", V, F, nm)
    Vcs, Fcs = merge(cones)
    rc.write_stl(f"{out}/cone_array_34.stl", Vcs, Fcs, "cone_array")
    Vw, Fw = merge(wire_tubes)
    rc.write_stl(f"{out}/litz_windings_102.stl", Vw, Fw, "windings")
    VA, FA = merge([plate, rim, cup, (Vcs, Fcs)])
    rc.write_stl(f"{out}/PHYLLO34_search_head_ASSEMBLY.stl", VA, FA, "phyllo34")
    VW, FW = merge([(VA, FA), (Vw, Fw)])
    rc.write_stl(f"{out}/PHYLLO34_search_head_with_windings.stl", VW, FW, "phyllo34_w")
    # packing check
    P = np.array([[p[2], p[3]] for p in pos])
    dm = np.linalg.norm(P[:, None] - P[None], axis=-1) + np.eye(len(P)) * 1e9
    rep["packing"] = dict(n_cones=len(pos), base_d=D_BASE, min_centre_distance=float(dm.min()),
                          touching_pairs=int(((dm - D_BASE) < 1e-6).sum() // 2),
                          max_outer_extent=float(np.hypot(P[:, 0], P[:, 1]).max() + R_B))
    # ---- electromagnetics on real geometry (one cone at origin)
    gmr = 0.7788 * WIRE_OD / 2
    m0, d0 = segs(W[0])
    # offset copy for self inductance
    Woff, _ = cone_wires_offset(cone, 0.05, gmr)
    m0o, d0o = segs(Woff[0])
    L1 = neumann(m0, d0, m0o, d0o)
    m1_, d1_ = segs(W[1])
    M12 = neumann(m0, d0, m1_, d1_)
    # neighbour coupling (outer ring adjacent cones, centre distance = D_BASE)
    nb = W[0] + np.array([D_BASE, 0, 0])
    mn, dn = segs(nb)
    Mnb = neumann(m0, d0, mn, dn)
    mom = float(0.5 * np.cross(m0, d0)[:, 2].sum())
    Rdc = 0.0172 / (40 * math.pi * (0.0799 / 2) ** 2) * 1.03 * rep["wire"]["length_per_winding_mm"] / 1000
    rep["electrical_per_winding"] = dict(L_uH=L1 * 1e6, R_dc_mOhm=Rdc * 1e3, tau_us=L1 / Rdc * 1e6,
                                          M_within_cone_uH=M12 * 1e6, k_within_cone=M12 / L1,
                                          M_neighbour_uH=Mnb * 1e6, k_neighbour=Mnb / L1,
                                          moment_per_amp_Am2=mom)
    # ---- field vs depth for drive modes (all 102 windings, Biot-Savart)
    mids, dls, cid, ring, ang = [], [], [], [], []
    Wf, _ = cone_wires(cone, 0.3)
    for ci, (rg, _, x, y, a) in enumerate(pos):
        for P_ in Wf:
            mm, dd = segs(place(P_, x, y, a))
            mids.append(mm); dls.append(dd)
            cid.append(np.full(len(mm), ci)); ring.append(np.full(len(mm), rg == "inner")); ang.append(np.full(len(mm), math.atan2(y, x)))
    mids, dls, cid, ring, ang = map(np.concatenate, (mids, dls, cid, ring, ang))
    depths = np.array([10, 25, 50, 75, 100, 150, 200, 300.0])
    tipz = H * 1e-3
    axis = np.stack([np.zeros_like(depths), np.zeros_like(depths), tipz + depths * 1e-3], -1)
    under_c = np.array(pos[0][2:4]) * 1e-3
    under = np.stack([np.full_like(depths, under_c[0]), np.full_like(depths, under_c[1]), tipz + depths * 1e-3], -1)
    n_in, n_out = N_IN, N_OUT
    modes = {
        "M0_all_in_phase": np.ones_like(cid, float),
        "M_ring_diff (inner +1, outer -13/21)": np.where(ring, 1.0, -n_in / n_out),
        "M1_rotating_dipole (w=cos phi)": np.cos(ang),
        "single_cone_#0": (cid == 0).astype(float),
    }
    fields = {}
    for nm, w in modes.items():
        if not nm.startswith("single"):
            fields[nm + " | on axis"] = (np.linalg.norm(biot_savart(mids, dls, w, axis), axis=1) * 1e6).tolist()
        fields[nm + " | under outer cone #0"] = (np.linalg.norm(biot_savart(mids, dls, w, under), axis=1) * 1e6).tolist()
    rep["field_uT_per_amp_vs_depth_below_tips_mm"] = dict(depths=depths.tolist(), **fields)
    # ---- timing model numbers (PI)
    L = L1; R = Rdc
    rep["timing_example"] = pi_timing(3 * L1 + 6 * M12, 3 * Rdc)
    fo = firing_order()
    PP = np.array([[p[2], p[3]] for p in pos])
    dcons = [float(np.linalg.norm(PP[fo[k]] - PP[fo[(k + 1) % len(fo)]])) for k in range(len(fo))]
    rep['firing_consecutive_distance_mm'] = dict(min=min(dcons), mean=float(np.mean(dcons)))
    rep["firing_order_golden_stride21"] = fo
    rep["layout"] = [dict(idx=i, ring=p[0], ring_index=p[1], x_mm=round(p[2], 4), y_mm=round(p[3], 4),
                          angle_deg=round(math.degrees(p[4]) % 360, 4)) for i, p in enumerate(pos)]
    rep["geometry"] = dict(OD_mm=2 * R_OUT, R_face=R_FACE, base_diameter=D_BASE, base_radius=R_B, height=H,
                           height_in=H / 25.4, tip_radius=R_T, tip_diameter=2 * R_T, tip_over_base=R_T / R_B,
                           slope_angle_deg=math.degrees(ALPHA), half_apex_angle_deg=90 - math.degrees(ALPHA),
                           slant_length=(R_B - R_T) / math.cos(ALPHA), full_apex_height=R_B * math.sqrt(PHI),
                           bore_radius=R_BORE, rho_inner_ring=RHO_IN, rho_outer_ring=RHO_OUT,
                           ring_ratio=RHO_OUT / RHO_IN, inner_ring_offset_deg=math.degrees(IN_OFFSET),
                           profile_perimeter=cone.L, twist_total_turns=cone.net_turns)
    with open(f"{out}/phyllo34_spec.json", "w") as f: json.dump(rep, f, indent=1, default=float)
    return cone, rep, pos, W

def cone_wires_offset(cone, ds, off_extra):
    s = cone.rows(ds, ds / 2)
    s = s[s <= cone.off["bore"] + dict(cone.segs)["bore"].L]
    r, z, h, _, _ = rc.eval_profile(cone.segs, s)
    nr, nz = np.sin(h), -np.cos(h)
    off = -G_DEPTH + WIRE_OD / 2 + off_extra
    rv, zv = r + off * nr, z + off * nz
    th = cone.twist(s)
    return [np.stack([rv * np.cos(j * 2 * math.pi / 3 + th), rv * np.sin(j * 2 * math.pi / 3 + th), zv], -1) for j in range(3)], s

def open_tube(P, rad, nseg=8):
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    ref = np.array([0, 0, 1.0]); N = np.zeros_like(P)
    n0 = np.cross(T[0], ref); n0 /= max(np.linalg.norm(n0), 1e-9); N[0] = n0
    for i in range(len(P) - 1):
        v1 = P[i + 1] - P[i]; c1 = v1 @ v1
        if c1 < 1e-20: N[i + 1] = N[i]; continue
        rL = N[i] - (2 / c1) * (v1 @ N[i]) * v1; tL = T[i] - (2 / c1) * (v1 @ T[i]) * v1
        v2 = T[i + 1] - tL; c2 = v2 @ v2
        N[i + 1] = rL - (2 / c2) * (v2 @ rL) * v2 if c2 > 1e-20 else rL
    B = np.cross(T, N)
    a = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    V = (P[:, None] + rad * (np.cos(a)[None, :, None] * N[:, None] + np.sin(a)[None, :, None] * B[:, None])).reshape(-1, 3)
    n = len(P); I, J = np.meshgrid(np.arange(n - 1), np.arange(nseg), indexing="ij"); J2 = (J + 1) % nseg
    F = [np.stack([I * nseg + J, (I + 1) * nseg + J, (I + 1) * nseg + J2], -1).reshape(-1, 3),
         np.stack([I * nseg + J, (I + 1) * nseg + J2, I * nseg + J2], -1).reshape(-1, 3)]
    c0 = len(V); c1 = c0 + 1
    V = np.vstack([V, P[0], P[-1]])
    j = np.arange(nseg); j2 = (j + 1) % nseg
    F.append(np.stack([np.full(nseg, c0), j2, j], -1))
    F.append(np.stack([np.full(nseg, c1), (n - 1) * nseg + j, (n - 1) * nseg + j2], -1))
    F = np.concatenate(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F

def pi_timing(Ls, Rs, V_supply=12.0, I_pk=4.0, V_clamp=200.0, C_par=50e-12, t_hold=50e-6, t_delay=4e-6):
    """Pulse-induction timing for one cone, its 3 windings in series (L = 3L1 + 6M).
    Pulse = linear ramp at V_supply, PWM current-regulated flat top t_hold,
    clamped fast turn-off, critically damped, then RX gates from t_delay."""
    t_ramp = Ls * I_pk / V_supply                         # linear ramp (R*I << V)
    t_flyback = Ls * I_pk / V_clamp
    R_damp = 0.5 * math.sqrt(Ls / C_par)
    t_settle = 6 * 2 * Ls / R_damp                        # ~6 time constants of the damped coil
    t_rx = 60e-6
    T_cone = t_ramp + t_hold + t_flyback + max(t_settle, t_delay) + t_rx + 10e-6
    pwm_duty = I_pk * Rs / V_supply
    return dict(L_series_uH=Ls * 1e6, R_series_mOhm=Rs * 1e3, I_pk_A=I_pk, V_supply=V_supply,
                t_ramp_us=t_ramp * 1e6, t_hold_us=t_hold * 1e6, pwm_hold_duty=pwm_duty, first_sample_delay_us=t_delay * 1e6, V_clamp=V_clamp, t_flyback_us=t_flyback * 1e6,
                R_damp_ohm=R_damp, t_settle_us=t_settle * 1e6, t_rx_window_us=t_rx * 1e6,
                T_per_cone_us=T_cone * 1e6, frame_34_us=34 * T_cone * 1e6,
                frame_rate_Hz=1 / (34 * T_cone), energy_per_pulse_uJ=0.5 * Ls * I_pk ** 2 * 1e6)

if __name__ == "__main__":
    t0 = time.time()
    cone, rep, pos, W = main()
    print(json.dumps({k: v for k, v in rep.items() if k not in ("layout", "firing_order_golden_stride21")}, indent=1, default=float))
    print("time %.1fs" % (time.time() - t0))
