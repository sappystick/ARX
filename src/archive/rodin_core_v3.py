#!/usr/bin/env python3
"""
rodin_core_v3.py
=================
72-lane Rodin / golden-ratio toroidal coil former  (48 TX + 24 RX)
Pure NumPy/SciPy generator -> STL (binary), 3MF, OBJ, STEP (faceted B-rep),
STEP (exact cubic B-spline wire centerlines), wire-tube STL, lane map CSV,
parameter/validation JSON.

GEOMETRY MODEL (all mm, radians internally)
------------------------------------------
1. Meridian skin profile (r,z): four locked lines joined by G2 blends
     top face   z = H/2 - (R_out - r) tan(3.09 deg)
     bore       r = R_in
     bottom     z = -H/2 + (r - R_in) tan(9.18 deg)
   Inner corners: curvature-continuous blends, min radius RHO_INNER.
   Outer rim:     one G2 "nose" blend tangent to top & bottom faces whose
                  outermost point is exactly r = R_out.
   Blend curvature  k(t) = k_max * w(t),  w = quintic ramp (Q) - flat - ramp,
   so curvature AND its derivative are continuous at every junction (G2/G3).

2. Lanes = loxodromes (constant-helix-angle curves) on the surface of
   revolution:   d(theta)/ds = c / r(s)   =>   tan(beta) = c  everywhere.
   Constant beta keeps the perpendicular lane pitch  p(s) = r(s)*(2pi/72)*cos(beta)
   proportional to r: no crowding, no sharp turns, smooth across every edge.
   c is chosen so one poloidal loop advances exactly K_ADV = 27 nodes = 135 deg
   (nearest node-closing angle to the golden angle 137.5078 deg).

3. Rodin digit of node n:  d(n) = (n mod 9) + 1
     TX (doubling circuit 1-2-4-8-7-5): d in {1,2,4,5,7,8}  -> 48 lanes
     RX (3-6-9 axis):                    d in {3,6,9}         -> 24 lanes
   Advance 27 = 0 (mod 9): every coil stays on its own digit -> 9 coils x 8 loops.
   TX series order follows the doubling sequence 1->2->4->8->7->5.

4. Groove / ridge cross-section (perpendicular to the lane), offset along
   the surface normal:
     TX seat floor F(s): -2.50 (top/bore/rim)  -> +2.50 on bottom ridges
     TX ridge crown C(s): 0 -> 4.00 on bottom, quintic on/off ramps RAMP_L
     U-seat radius = wire radius + 0.05 clearance; 60 deg V-flanks.
"""
import math, json, csv, os, io, struct, time, zipfile
import numpy as np
from scipy.interpolate import make_interp_spline

# =====================================================================
# 1. LOCKED INPUT DIMENSIONS (from the user's spec, shrink-compensated)
# =====================================================================
SC      = 1.004
R_OUT   = 124.08 * SC          # 124.57632
R_IN    = 47.56  * SC          # 47.75024
H_CORE  = 24.10  * SC          # 24.19640
HALF_H  = H_CORE / 2.0         # 12.09820
W_CORE  = R_OUT - R_IN         # 76.82608
A_TOP   = math.radians(3.09)
A_BOT   = math.radians(9.18)
T_TOP   = math.tan(A_TOP)      # 0.0539828...
T_BOT   = math.tan(A_BOT)      # 0.1616057...
PHI     = (1 + 5 ** 0.5) / 2
GOLDEN_ANGLE_DEG = 360.0 / PHI ** 2   # 137.5077640

# Lane system
N_LANES    = 72
LANE_PITCH = 2 * math.pi / N_LANES    # 5 deg
K_ADV      = 27                       # nodes per poloidal loop (135 deg)
LANES_PER_TRIPLE = 3                  # [TX-A, TX-B, RX]
N_TRIPLES  = N_LANES // 3             # 24

# Wire & groove (corrected: seat radius = wire radius + clearance)
TX_OD, RX_OD = 1.40, 0.80             # 100/38 served Litz, 40/40 PU Litz
SEAT_CLR = 0.05
A_TX = TX_OD / 2 + SEAT_CLR           # 0.75 -> groove width 1.50
A_RX = RX_OD / 2 + SEAT_CLR           # 0.45 -> groove width 0.90
TX_DEPTH   = 2.50                     # locked delta-z (top recessed floor)
RIDGE_H    = 4.00                     # locked ridge height
RIDGE_SEAT = 1.50                     # locked U-scoop depth -> floor +2.50
RX_DEPTH   = 0.80
TX_LAND    = 0.50                     # crown land each side of TX seat
RX_LAND    = 0.30
FLANK_DEG  = 60.0
SQ         = math.tan(math.radians(FLANK_DEG))   # rise/run of flank = 1.7320508

# Blends / ramps
RHO_INNER = 6.0       # min skin radius at both bore lips
BLEND_F   = 0.30      # fraction of each blend used for curvature ramp
RAMP_L    = 12.0      # ridge on/off ramp length along the meridian
EPS_WALL  = 1e-3      # vertical-wall sample offset

RES = {
    "HIGH":   dict(ds_face=1.00, ds_blend=0.20, ds_ramp=0.30, ds_bore=0.40, tx_arc=9, rx_arc=7, nfill=4),
    "MEDIUM": dict(ds_face=3.00, ds_blend=0.80, ds_ramp=1.00, ds_bore=1.50, tx_arc=5, rx_arc=3, nfill=1),
}

# =====================================================================
# 2. SMOOTH FUNCTIONS
# =====================================================================
def Q(u):
    u = np.clip(u, 0.0, 1.0); return u ** 3 * (10 - 15 * u + 6 * u * u)
def IQ(u):  # integral of Q from 0..u
    u = np.clip(u, 0.0, 1.0); return u ** 4 * (2.5 - 3 * u + u * u)
def blend_w(t, f=BLEND_F):
    t = np.asarray(t, float)
    return np.where(t < f, Q(t / f), np.where(t <= 1 - f, 1.0, Q((1 - t) / f)))
def blend_W(t, f=BLEND_F):  # normalized cumulative turning, 0..1
    t = np.asarray(t, float)
    c = np.where(t < f, f * IQ(t / f),
        np.where(t <= 1 - f, f / 2 + (t - f), (1 - f) - f * IQ((1 - t) / f)))
    return c / (1 - f)

# =====================================================================
# 3. MERIDIAN PROFILE (closed, CCW in r-z plane)
# =====================================================================
class Line:
    def __init__(s, p0, h, L): s.p0, s.h, s.L = np.array(p0, float), h, L
    def eval(s, u):
        u = np.asarray(u, float)
        return (s.p0[0] + u * math.cos(s.h), s.p0[1] + u * math.sin(s.h),
                np.full_like(u, s.h), np.zeros_like(u))

class Blend:
    _n = 40001
    def __init__(s, p0, h0, dturn, L):
        s.p0, s.h0, s.dt, s.L = np.array(p0, float), h0, dturn, L
        t = np.linspace(0, 1, s._n); h = h0 + dturn * blend_W(t)
        dx, dy = np.cos(h), np.sin(h)
        s.t = t
        s.x = np.concatenate([[0], np.cumsum((dx[1:] + dx[:-1]) / 2) / (s._n - 1)])
        s.y = np.concatenate([[0], np.cumsum((dy[1:] + dy[:-1]) / 2) / (s._n - 1)])
    @staticmethod
    def unit_chord(h0, dturn):
        b = Blend((0, 0), h0, dturn, 1.0); return np.array([b.x[-1], b.y[-1]]), b
    def eval(s, u):
        t = np.asarray(u, float) / s.L
        r = s.p0[0] + s.L * np.interp(t, s.t, s.x)
        z = s.p0[1] + s.L * np.interp(t, s.t, s.y)
        h = s.h0 + s.dt * blend_W(t)
        k = s.dt * blend_w(t) / ((1 - BLEND_F) * s.L)
        return r, z, h, k

def build_profile():
    V_ti = np.array([R_IN, HALF_H - W_CORE * T_TOP])   # top face meets bore
    V_bi = np.array([R_IN, -HALF_H])                    # bottom face meets bore
    h_top  = math.atan2(-T_TOP, -1.0)                   # heading inward along top
    h_bore = -math.pi / 2
    h_bot  = math.atan2(T_BOT, 1.0)
    u = lambda h: np.array([math.cos(h), math.sin(h)])
    u_top, u_bore, u_bot = u(h_top), u(h_bore), u(h_bot)

    def inner(V, ha, hb):
        dturn = (hb - ha) % (2 * math.pi)
        L = dturn * RHO_INNER / (1 - BLEND_F)
        ch, _ = Blend.unit_chord(ha, dturn); ch *= L
        s = u(ha) + u(hb); d = ch.dot(s) / s.dot(s)
        return dturn, L, d
    dt1, L1, d1 = inner(V_ti, h_top, h_bore)
    dt2, L2, d2 = inner(V_bi, h_bore, h_bot)

    # nose: start on bottom line at V_bi + tau*u_bot, end on top line, r_max = R_OUT
    dtn = 2 * math.pi - dt1 - dt2
    cn, bn = Blend.unit_chord(h_bot, dtn)
    mn = bn.x.max()
    cross = lambda a, b: a[0] * b[1] - a[1] * b[0]
    A = np.array([[cross(u_bot, u_top), cross(cn, u_top)], [u_bot[0], mn]])
    rhs = np.array([-cross(V_bi - V_ti, u_top), R_OUT - V_bi[0]])
    tau, Ln = np.linalg.solve(A, rhs)
    B0 = V_bi + tau * u_bot
    E = B0 + Ln * cn
    top_len = np.linalg.norm(V_ti - E) - d1
    bore_len = np.linalg.norm(V_bi - V_ti) - d1 - d2
    bot_len = tau - d2
    assert min(top_len, bore_len, bot_len) > 0, "blends overlap"
    segs = [
        ("top",       Line(E, h_top, top_len)),
        ("lip_top",   Blend(V_ti - d1 * u_top, h_top, dt1, L1)),
        ("bore",      Line(V_ti + d1 * u_bore, h_bore, bore_len)),
        ("lip_bot",   Blend(V_bi - d2 * u_bore, h_bore, dt2, L2)),
        ("bottom",    Line(V_bi + d2 * u_bot, h_bot, bot_len)),
        ("nose",      Blend(B0, h_bot, dtn, Ln)),
    ]
    info = dict(V_top_inner=V_ti.tolist(), V_bot_inner=V_bi.tolist(),
                lip_top=dict(turn_deg=math.degrees(dt1), length=L1, tangent_len=d1, rho_min=RHO_INNER),
                lip_bot=dict(turn_deg=math.degrees(dt2), length=L2, tangent_len=d2, rho_min=RHO_INNER),
                nose=dict(turn_deg=math.degrees(dtn), length=Ln, rho_min=Ln * (1 - BLEND_F) / dtn,
                          start=B0.tolist(), end=E.tolist()),
                top_straight=top_len, bore_straight=bore_len, bottom_straight=bot_len)
    return segs, info

def seg_offsets(segs):
    off, acc = {}, 0.0
    for name, sg in segs: off[name] = acc; acc += sg.L
    return off, acc

def eval_profile(segs, s):
    off, Ltot = seg_offsets(segs)
    s = np.mod(np.asarray(s, float), Ltot)
    r = np.empty_like(s); z = np.empty_like(s); h = np.empty_like(s); k = np.empty_like(s)
    name_idx = np.empty(s.shape, int)
    for i, (name, sg) in enumerate(segs):
        m = (s >= off[name]) & (s < off[name] + sg.L + 1e-12)
        if i == len(segs) - 1: m |= s >= off[name]
        rr, zz, hh, kk = sg.eval(s[m] - off[name])
        r[m], z[m], h[m], k[m], name_idx[m] = rr, zz, hh, kk, i
    return r, z, h, k, name_idx

# =====================================================================
# 4. LOXODROME TWIST + RIDGE RAMPS
# =====================================================================
class Core:
    def __init__(self):
        self.segs, self.pinfo = build_profile()
        self.off, self.Ltot = seg_offsets(self.segs)
        # fine integral of ds/r
        sf = np.linspace(0, self.Ltot, 400001)
        rf = eval_profile(self.segs, sf)[0]
        inv = 1.0 / rf
        self.sf = sf
        self.If = np.concatenate([[0], np.cumsum((inv[1:] + inv[:-1]) / 2 * np.diff(sf))])
        self.I_loop = self.If[-1]
        self.c = K_ADV * LANE_PITCH / self.I_loop          # = tan(beta)
        self.beta = math.atan(self.c); self.cb = math.cos(self.beta)
        # theta = 0 at the outer-rim apex (r = R_OUT)
        n0 = self.off["nose"]; nose = self.segs[-1][1]
        ss = np.linspace(0, nose.L, 20001); rr = nose.eval(ss)[0]
        self.s_apex = n0 + ss[np.argmax(rr)]
        self.theta_apex = self.c * np.interp(self.s_apex, sf, self.If)

    def theta(self, s):
        return self.c * np.interp(s, self.sf, self.If) - self.theta_apex

    def ramp(self, s):
        """ridge factor g(s): 0 off-ridge, 1 full ridge (bottom straight only)"""
        b0 = self.off["bottom"]; Lb = self.segs[4][1].L
        u = np.asarray(s) - b0
        g = Q(u / RAMP_L) * Q((Lb - u) / RAMP_L)
        return np.where((u >= 0) & (u <= Lb), g, 0.0)

    def tx_params(self, s):
        g = self.ramp(s)
        C = RIDGE_H * g
        F = -TX_DEPTH + (TX_DEPTH + RIDGE_H - RIDGE_SEAT) * g   # -2.5 -> +2.5
        return C, F

    def rows(self, cfg):
        out = []
        for name, sg in self.segs:
            o = self.off[name]
            if name == "bottom":
                Lb = sg.L
                a = np.arange(0, RAMP_L, cfg["ds_ramp"])
                b = np.arange(RAMP_L, Lb - RAMP_L, cfg["ds_face"])
                c = np.arange(Lb - RAMP_L, Lb, cfg["ds_ramp"])
                u = np.concatenate([a, b, c])
            else:
                ds = cfg["ds_blend"] if isinstance(sg, Blend) else (cfg["ds_bore"] if name == "bore" else cfg["ds_face"])
                n = max(2, int(math.ceil(sg.L / ds)))
                u = np.linspace(0, sg.L, n, endpoint=False)
            out.append(o + u)
        s = np.unique(np.concatenate(out))
        return s

# =====================================================================
# 5. CROSS-SECTION FUNCTIONS
# =====================================================================
def core_x(a, land, narc):
    ang = np.linspace(-np.pi / 2, np.pi / 2, narc + 2)[1:-1]
    return np.concatenate([[-(a + land), -(a + EPS_WALL), -(a - EPS_WALL)], a * np.sin(ang),
                           [a - EPS_WALL, a + EPS_WALL, a + land]])

def seat(x, a, floor):
    return floor + a - np.sqrt(np.maximum(a * a - x * x, 0.0))

def lane_class(n):
    d = n % 9 + 1
    if d in (3, 6, 9): return d, "RX", "RX"
    return d, "TX", ("A" if d in (1, 4, 7) else "B")

# =====================================================================
# 6. MESH BUILDER (single watertight torus-topology grid)
# =====================================================================
def build_mesh(core, cfg):
    s = core.rows(cfg); NR = len(s)
    r, z, h, k, _ = eval_profile(core.segs, s)
    nr, nz = np.sin(h), -np.cos(h)              # outward normal (CCW profile)
    th = core.theta(s)
    C, F = core.tx_params(s)
    cb, D_ = core.cb, LANE_PITCH
    xtx = core_x(A_TX, TX_LAND, cfg["tx_arc"])
    xrx = core_x(A_RX, RX_LAND, cfg["rx_arc"])
    nf = cfg["nfill"]

    def core_cols(xs, lane_off, kind):
        X = np.broadcast_to(xs, (NR, len(xs)))
        cut = np.abs(X) < (A_TX if kind == "TX" else A_RX)
        if kind == "TX":
            Dc = np.where(cut, seat(X, A_TX, F[:, None]), C[:, None] * np.ones_like(X))
        else:
            Dc = np.where(cut, seat(X, A_RX, -RX_DEPTH), 0.0)
        reff = r[:, None] + Dc * nr[:, None]
        psi = lane_off * D_ + X / (reff * cb)
        psi_skin = lane_off * D_ + X / (r[:, None] * cb)
        return psi, Dc, cut, psi_skin

    pA, dA, cA, sA = core_cols(xtx, 0, "TX")
    pB, dB, cB, sB = core_cols(xtx, 1, "TX")
    pR, dR, cR, sR = core_cols(xrx, 2, "RX")
    sig = 1.0 / (r * cb)

    def fillers(eL, eR, sp):
        w = eR - eL
        assert np.all(w > 0), "lane cores overlap"
        sp = np.clip(sp, eL + 0.05 * w, eR - 0.05 * w)
        lam = (np.arange(1, nf + 1) / (nf + 1))[None, :]
        left = eL[:, None] + lam * (sp - eL)[:, None]
        right = sp[:, None] + lam * (eR - sp)[:, None]
        return np.concatenate([left, sp[:, None], right], axis=1)

    foot = (A_TX + TX_LAND + C / SQ) * sig
    fAB = fillers(pA[:, -1], pB[:, 0], np.full(NR, 0.5 * D_))
    fBR = fillers(pB[:, -1], pR[:, 0], D_ + foot)
    fRA = fillers(pR[:, -1], 3 * D_ + pA[:, 0], 3 * D_ - foot)

    psi = np.concatenate([pA, fAB, pB, fBR, pR, fRA], axis=1)
    Dl = np.concatenate([dA, np.zeros_like(fAB), dB, np.zeros_like(fBR), dR, np.zeros_like(fRA)], axis=1)
    cut = np.concatenate([cA, np.zeros(fAB.shape, bool), cB, np.zeros(fBR.shape, bool), cR,
                          np.zeros(fRA.shape, bool)], axis=1)
    # ordering check at skin level (walls are exactly perpendicular to the skin,
    # so their angular position legitimately shifts by microns with depth)
    psi_chk = np.concatenate([sA, fAB, sB, fBR, sR, fRA], axis=1)
    assert np.all(np.diff(psi_chk, axis=1) > 0), "column order violated"
    # ridge flanks from TX lanes at 0, D, 3D
    fl = np.zeros_like(psi)
    for c0 in (0.0, D_, 3 * D_):
        x = (psi - c0) / sig[:, None]
        hgt = C[:, None] - SQ * np.maximum(np.abs(x) - (A_TX + TX_LAND), 0.0)
        fl = np.maximum(fl, hgt)
    D = np.where(cut, Dl, np.maximum(Dl, fl))
    cpt = psi.shape[1]
    # replicate around 24 triples
    psiG = np.concatenate([psi + t * 3 * D_ for t in range(N_TRIPLES)], axis=1)
    DG = np.tile(D, (1, N_TRIPLES))
    NC = psiG.shape[1]
    phi = psiG + th[:, None]
    rv = r[:, None] + DG * nr[:, None]
    zv = z[:, None] + DG * nz[:, None]
    V = np.stack([rv * np.cos(phi), rv * np.sin(phi), zv], axis=-1).reshape(-1, 3)
    # faces
    I, J = np.meshgrid(np.arange(NR), np.arange(NC), indexing="ij")
    J2 = (J + 1) % NC
    I2 = (I + 1) % NR
    shift = (K_ADV // 3) * cpt
    Jw = np.where(I == NR - 1, (J + shift) % NC, J)
    Jw2 = np.where(I == NR - 1, (J2 + shift) % NC, J2)
    v00 = I * NC + J; v01 = I * NC + J2
    v10 = I2 * NC + Jw; v11 = I2 * NC + Jw2
    Fc = np.concatenate([np.stack([v00, v10, v11], -1).reshape(-1, 3),
                         np.stack([v00, v11, v01], -1).reshape(-1, 3)])
    vol = signed_volume(V, Fc)
    if vol < 0: Fc = Fc[:, ::-1]; vol = -vol
    meta = dict(rows=NR, cols=NC, cols_per_triple=cpt, s=s, r=r, z=z, nr=nr, nz=nz, th=th,
                C=C, F=F, kappa=k, D_triple=D, psi_triple=psi)
    return V.astype(np.float64), Fc.astype(np.int64), vol, meta

def signed_volume(V, F):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)

def edge_manifold_check(F):
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e.sort(axis=1)
    key = e[:, 0] * (int(e.max()) + 1) + e[:, 1]
    _, cnt = np.unique(key, return_counts=True)
    return int((cnt == 2).sum()), int((cnt != 2).sum())

def min_triangle_area(V, F):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.linalg.norm(np.cross(b - a, c - a), axis=1).min() / 2)

# =====================================================================
# 7. WIRE CENTERLINES (9 Rodin coils x 8 loops)
# =====================================================================
def wire_centerlines(core, cfg):
    s = core.rows(cfg)
    r, z, h, _, _ = eval_profile(core.segs, s)
    nr, nz = np.sin(h), -np.cos(h)
    th = core.theta(s); C, F = core.tx_params(s)
    coils = {}
    for d in range(1, 10):
        n0 = d - 1
        _, kind, fam = lane_class(n0)
        Dw = (F + TX_OD / 2) if kind == "TX" else np.full_like(s, -RX_DEPTH + RX_OD / 2)
        pts, lanes = [], []
        for m in range(8):
            n = (n0 + K_ADV * m) % N_LANES
            lanes.append(n)
            phi = n * LANE_PITCH + th
            rv = r + Dw * nr; zv = z + Dw * nz
            pts.append(np.stack([rv * np.cos(phi), rv * np.sin(phi), zv], -1))
        coils[d] = dict(kind=kind, family=fam, lanes=lanes, pts=np.concatenate(pts),
                        nrm_r=np.tile(nr, 8), nrm_z=np.tile(nz, 8), phi=None)
    return coils

def curvature_radius(P):
    a, b, c = np.roll(P, 1, 0), P, np.roll(P, -1, 0)
    ab = np.linalg.norm(b - a, axis=1); bc = np.linalg.norm(c - b, axis=1); ca = np.linalg.norm(a - c, axis=1)
    area2 = np.linalg.norm(np.cross(b - a, c - a), axis=1)
    with np.errstate(divide="ignore"):
        R = ab * bc * ca / np.maximum(2 * area2, 1e-15)
    return R

def tube_mesh(P, radius, nseg=10):
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0); T /= np.linalg.norm(T, axis=1)[:, None]
    # rotation-minimizing frame (double reflection)
    N = np.zeros_like(P); ref = np.array([0, 0, 1.0])
    n0 = np.cross(T[0], ref); n0 /= np.linalg.norm(n0); N[0] = n0
    for i in range(len(P) - 1):
        v1 = P[i + 1] - P[i]; c1 = v1 @ v1
        rL = N[i] - (2 / c1) * (v1 @ N[i]) * v1; tL = T[i] - (2 / c1) * (v1 @ T[i]) * v1
        v2 = T[i + 1] - tL; c2 = v2 @ v2
        N[i + 1] = rL - (2 / c2) * (v2 @ rL) * v2 if c2 > 1e-20 else rL
    B = np.cross(T, N)
    # close the frame twist: distribute the residual angle
    ang_end = math.atan2(np.dot(np.cross(N[-1], N[0]), T[0]), np.dot(N[-1], N[0]))
    a = np.linspace(0, ang_end, len(P), endpoint=False)[:, None]
    N2 = N * np.cos(a) + B * np.sin(a); B2 = np.cross(T, N2)
    ang = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    V = (P[:, None, :] + radius * (np.cos(ang)[None, :, None] * N2[:, None, :] +
                                   np.sin(ang)[None, :, None] * B2[:, None, :])).reshape(-1, 3)
    n = len(P); I, J = np.meshgrid(np.arange(n), np.arange(nseg), indexing="ij")
    I2, J2 = (I + 1) % n, (J + 1) % nseg
    a0 = I * nseg + J; a1 = I * nseg + J2; b0 = I2 * nseg + J; b1 = I2 * nseg + J2
    Fc = np.concatenate([np.stack([a0, b0, b1], -1).reshape(-1, 3), np.stack([a0, b1, a1], -1).reshape(-1, 3)])
    if signed_volume(V, Fc) < 0: Fc = Fc[:, ::-1]
    return V, Fc

# =====================================================================
# 8. EXPORTERS
# =====================================================================
def write_stl(path, V, F, name="rodin_core"):
    tri = V[F].astype(np.float32)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-30)[:, None]
    rec = np.zeros(len(F), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n; rec["v"] = tri
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b"\0")); f.write(struct.pack("<I", len(F))); f.write(rec.tobytes())

def _fmt_rows(arr, fmt):
    return "\n".join(fmt % tuple(row) for row in arr)

def write_3mf(path, V, F):
    vx = "".join('<vertex x="%.6f" y="%.6f" z="%.6f"/>' % tuple(v) for v in V)
    tr = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(t) for t in F)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<resources><object id="1" type="model"><mesh><vertices>' + vx + '</vertices><triangles>' + tr +
             '</triangles></mesh></object></resources><build><item objectid="1"/></build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct); zf.writestr("_rels/.rels", rels); zf.writestr("3D/3dmodel.model", model)

def write_obj(path, V, F, header=""):
    with open(path, "w") as f:
        f.write("# " + header + "\n")
        f.write(_fmt_rows(V, "v %.6f %.6f %.6f")); f.write("\n")
        f.write(_fmt_rows(F + 1, "f %d %d %d")); f.write("\n")

STEP_HEAD = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('{desc}'),'2;1');
FILE_NAME('{name}','{date}',('rodin_core_v3.py'),(''),'numpy','rodin_core_v3','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN {{ 1 0 10303 214 1 1 1 1 }}'));
ENDSEC;
DATA;
#1=APPLICATION_CONTEXT('core data for automotive mechanical design processes');
#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);
#3=PRODUCT_CONTEXT('',#1,'mechanical');
#4=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');
#5=PRODUCT('{pname}','{pname}','',(#3));
#6=PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,(#5));
#7=PRODUCT_DEFINITION_FORMATION('','',#5);
#8=PRODUCT_DEFINITION('design','',#7,#4);
#9=PRODUCT_DEFINITION_SHAPE('','',#8);
#10=SHAPE_DEFINITION_REPRESENTATION(#9,#11);
#11={rep}('{pname}',(#100,#20),#30);
#20=AXIS2_PLACEMENT_3D('',#21,#22,#23);
#21=CARTESIAN_POINT('',(0.,0.,0.));
#22=DIRECTION('',(0.,0.,1.));
#23=DIRECTION('',(1.,0.,0.));
#30=(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#34))GLOBAL_UNIT_ASSIGNED_CONTEXT((#31,#32,#33))REPRESENTATION_CONTEXT('',''));
#31=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));
#32=(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));
#33=(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT());
#34=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-06),#31,'distance_accuracy_value','');
"""

def _r(v): return ("%.6f" % v).rstrip("0").rstrip(".") + ("" if "." in ("%.6f" % v).rstrip("0").rstrip(".") else ".")

def write_step_faceted(path, V, F):
    """AP214 FACETED_BREP: one planar FACE_SURFACE per triangle (mesh-exact)."""
    date = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = [STEP_HEAD.format(desc="Rodin 72-lane coil former - faceted B-rep", name=os.path.basename(path),
                            date=date, pname="rodin_core", rep="FACETED_BREP_SHAPE_REPRESENTATION")]
    nV, nF = len(V), len(F)
    p0 = 1000
    out.append("\n".join("#%d=CARTESIAN_POINT('',(%.6f,%.6f,%.6f));" % (p0 + i, *V[i]) for i in range(nV)))
    tri = V[F]; nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-30)[:, None]
    base = p0 + nV
    lines, face_ids = [], []
    for i in range(nF):
        b = base + 6 * i
        a, c, d = F[i]
        lines.append("#%d=DIRECTION('',(%.9f,%.9f,%.9f));" % (b, *nrm[i]))
        lines.append("#%d=AXIS2_PLACEMENT_3D('',#%d,#%d,$);" % (b + 1, p0 + a, b))
        lines.append("#%d=PLANE('',#%d);" % (b + 2, b + 1))
        lines.append("#%d=POLY_LOOP('',(#%d,#%d,#%d));" % (b + 3, p0 + a, p0 + c, p0 + d))
        lines.append("#%d=FACE_OUTER_BOUND('',#%d,.T.);" % (b + 4, b + 3))
        lines.append("#%d=FACE_SURFACE('',(#%d),#%d,.T.);" % (b + 5, b + 4, b + 2))
        face_ids.append(b + 5)
    out.append("\n".join(lines))
    sh = base + 6 * nF
    out.append("#%d=CLOSED_SHELL('',(%s));" % (sh, ",".join("#%d" % f for f in face_ids)))
    out.append("#100=FACETED_BREP('rodin_core',#%d);" % sh)
    out.append("ENDSEC;\nEND-ISO-10303-21;\n")
    with open(path, "w") as f: f.write("\n".join(out))

def write_step_wires(path, coils):
    """AP214 wireframe: each Rodin coil = one closed periodic cubic B-spline."""
    date = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = [STEP_HEAD.format(desc="Rodin coil wire centerlines - cubic B-splines", name=os.path.basename(path),
                            date=date, pname="rodin_wire_paths",
                            rep="GEOMETRICALLY_BOUNDED_WIREFRAME_SHAPE_REPRESENTATION")]
    eid = 1000; curve_ids = []
    for d, cl in coils.items():
        P = cl["pts"]; Pc = np.vstack([P, P[:1]])
        u = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Pc, axis=0), axis=1))])
        spl = make_interp_spline(u, Pc, k=3, bc_type="periodic")
        t, c = spl.t, spl.c
        ncp = len(t) - 4
        cp_ids = []
        for p in c[:ncp]:
            out.append("#%d=CARTESIAN_POINT('',(%.6f,%.6f,%.6f));" % (eid, *p)); cp_ids.append(eid); eid += 1
        kn = ",".join("%.9f" % v for v in t); ml = ",".join("1" for _ in t)
        out.append("#%d=B_SPLINE_CURVE_WITH_KNOTS('coil_%d_%s',3,(%s),.UNSPECIFIED.,.T.,.F.,(%s),(%s),.UNSPECIFIED.);"
                   % (eid, d, cl["kind"], ",".join("#%d" % i for i in cp_ids), ml, kn))
        curve_ids.append(eid); eid += 1
    out.append("#100=GEOMETRIC_CURVE_SET('rodin_coils',(%s));" % ",".join("#%d" % i for i in curve_ids))
    out.append("ENDSEC;\nEND-ISO-10303-21;\n")
    with open(path, "w") as f: f.write("\n".join(out))

# =====================================================================
# 9. REPORTS
# =====================================================================
def lane_table(core):
    rows = []
    for n in range(N_LANES):
        d, kind, fam = lane_class(n)
        nxt = (n + K_ADV) % N_LANES
        coil_seq = [((d - 1) + K_ADV * m) % N_LANES for m in range(8)]
        rows.append(dict(lane=n, entry_angle_deg=round(n * 5.0, 4), rodin_digit=d, role=kind, phase=fam,
                         exit_node=nxt, exit_angle_deg=round(nxt * 5.0, 4),
                         loop_in_coil=coil_seq.index(n) + 1, coil=f"C{d}",
                         groove_width_mm=round(2 * (A_TX if kind == 'TX' else A_RX), 3),
                         seat_radius_mm=A_TX if kind == "TX" else A_RX,
                         wire=("100/38 Litz Type 2 served, OD 1.40" if kind == "TX" else "40/40 Litz Type 1 PU, OD 0.80")))
    return rows

def validation(core, meta, coils):
    s, r, C = meta["s"], meta["r"], meta["C"]
    pitch = r * LANE_PITCH * core.cb
    rep = {}
    rep["lane_pitch_perp_min_mm"] = float(pitch.min())
    rep["lane_pitch_perp_max_mm"] = float(pitch.max())
    rep["wall_TX_TX_min_mm"] = float((pitch - 2 * A_TX).min())
    rep["wall_TX_RX_min_mm"] = float((pitch - A_TX - A_RX).min())
    m = C > 0.05
    rep["ridge_crown_gap_min_mm"] = float((pitch[m] - 2 * (A_TX + TX_LAND)).min()) if m.any() else None
    for kind in ("TX", "RX"):
        Rs = np.concatenate([curvature_radius(cl["pts"]) for cl in coils.values() if cl["kind"] == kind])
        od = TX_OD if kind == "TX" else RX_OD
        rep[f"wire_min_bend_radius_{kind}_mm"] = float(Rs.min())
        rep[f"wire_min_bend_radius_{kind}_xOD"] = float(Rs.min() / od)
        rep[f"wire_loop_length_{kind}_mm"] = float(np.linalg.norm(np.diff(
            np.vstack([cl['pts'] for cl in coils.values() if cl['kind'] == kind][:1][0][:len(s) + 1]), axis=0), axis=1).sum())
    return rep

# =====================================================================
# 10. MAIN
# =====================================================================
def main(outdir="out"):
    os.makedirs(outdir, exist_ok=True)
    core = Core()
    print("loop integral ds/r = %.9f  tan(beta)=c=%.9f  beta=%.6f deg" % (core.I_loop, core.c, math.degrees(core.beta)))
    results = {}
    for lvl in ("HIGH", "MEDIUM"):
        t0 = time.time()
        V, F, vol, meta = build_mesh(core, RES[lvl])
        good, bad = edge_manifold_check(F)
        results[lvl] = dict(vertices=len(V), triangles=len(F), volume_mm3=vol,
                            edges_shared_by_2=good, nonmanifold_edges=bad,
                            min_triangle_area_mm2=min_triangle_area(V, F),
                            bbox_min=V.min(0).tolist(), bbox_max=V.max(0).tolist(),
                            build_s=round(time.time() - t0, 1))
        print(lvl, results[lvl])
        if lvl == "HIGH":
            write_stl(f"{outdir}/rodin_core_HIGH.stl", V, F)
            write_3mf(f"{outdir}/rodin_core_HIGH.3mf", V, F)
            meta_hi = meta
        else:
            write_obj(f"{outdir}/rodin_core_MEDIUM.obj", V, F, "Rodin 72-lane core, mm")
            write_step_faceted(f"{outdir}/rodin_core_MEDIUM_faceted.step", V, F)
            write_stl(f"{outdir}/rodin_core_MEDIUM.stl", V, F)
    coils = wire_centerlines(core, RES["HIGH"])
    write_step_wires(f"{outdir}/rodin_wire_centerlines.step", coils)
    for kind, od in (("TX", TX_OD), ("RX", RX_OD)):
        Vs, Fs, off = [], [], 0
        for cl in coils.values():
            if cl["kind"] != kind: continue
            v, f = tube_mesh(cl["pts"], od / 2); Vs.append(v); Fs.append(f + off); off += len(v)
        write_stl(f"{outdir}/rodin_wires_{kind}.stl", np.vstack(Vs), np.vstack(Fs), f"wires_{kind}")
    with open(f"{outdir}/wire_centerlines.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["coil", "role", "point", "x_mm", "y_mm", "z_mm"])
        for d, cl in coils.items():
            for i, p in enumerate(cl["pts"]): w.writerow([f"C{d}", cl["kind"], i, *("%.6f" % v for v in p)])
    lt = lane_table(core)
    with open(f"{outdir}/lane_map_72.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lt[0].keys())); w.writeheader(); w.writerows(lt)
    val = validation(core, meta_hi, coils)
    params = dict(
        locked=dict(R_out=R_OUT, R_in=R_IN, H_core=H_CORE, W_core=W_CORE, tan_3_09=T_TOP, tan_9_18=T_BOT,
                    z_top_skin_at_R_in=HALF_H - W_CORE * T_TOP,
                    z_bot_skin_at_R_out=-HALF_H + W_CORE * T_BOT),
        golden=dict(phi=PHI, golden_angle_deg=GOLDEN_ANGLE_DEG, R_out_over_R_in=R_OUT / R_IN, phi_squared=PHI ** 2,
                    loop_advance_deg=K_ADV * 5.0, golden_angle_error_pct=100 * (K_ADV * 5.0 - GOLDEN_ANGLE_DEG) / GOLDEN_ANGLE_DEG),
        twist=dict(loop_integral_ds_over_r=core.I_loop, tan_beta=core.c, beta_deg=math.degrees(core.beta),
                   theta_top_face_deg=math.degrees(core.c * (np.interp(core.off['lip_top'], core.sf, core.If) - 0)),
                   profile_perimeter_mm=core.Ltot),
        profile=core.pinfo,
        floors=dict(top_floor_vertical_offset=TX_DEPTH / math.cos(A_TOP), bottom_floor_vertical_offset=(RIDGE_H - RIDGE_SEAT) / math.cos(A_BOT)),
        validation=val, meshes=results)
    with open(f"{outdir}/parameters_and_validation.json", "w") as f: json.dump(params, f, indent=2, default=float)
    print(json.dumps(val, indent=2))
    return core, params

if __name__ == "__main__":
    main()
