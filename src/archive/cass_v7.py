#!/usr/bin/env python3
"""PHI-FOLD 233 v7: six removable TX cassettes (double-spiral, mirror return, 20 deg shift) + RX tray cassette, 6 guide posts, vault tube; same footprint D233 and max height 44.5."""
import math, json, os, sys, numpy as np
from scipy.spatial import cKDTree
import rodin_core_v4 as rc, golden_cone_head as g
LOD = sys.argv[1] if len(sys.argv) > 1 else "print"
OUT = "kit_v7/CASSETTES" if LOD == "print" else "kit_v7/CASSETTES_LOW"; os.makedirs(OUT, exist_ok=True)
NPHI, NR = (1200, 150) if LOD == "print" else (540, 70)
R_RIM, R_IN, PITCH = 116.5, 52.0, 7.0
EPS, M, GOLD, OUTER_MARGIN = 0.06, 3, 137.50776405, 4.5                  # petal modulation depth, 3 petals (Fibonacci), golden angle between layers
R_W1 = (R_RIM - OUTER_MARGIN) / (1 + EPS); R_W0 = 60.5 / (1 - EPS)                 # footprint, opening, winding band, radial pitch per arm turn
PN, ZRX, HMAX = 3.0, 3.2, 44.5                                                 # cassette normal thickness, RX tray top, height limit
s = 0.34
for _ in range(50): s = (HMAX - ZRX - 6 * PN * math.sqrt(1 + s * s)) / (R_RIM - R_IN)
BETA = math.atan(s); TV = PN / math.cos(BETA)
RP, TXP, RXP = 53.8, (90, 210, 330), (30, 150, 270)
W_HALF, D1, D2 = 0.7, 1.3, 2.3                                                 # groove half-width, normal and crossing-pocket depth
A = 2 * math.pi / PITCH
def arms(k):
    th = math.radians(GOLD * k)                                               # layer k (0..5) rotated by k x golden angle
    r1 = R_W1 + 0.078; rr = np.linspace(R_W0, r1, 4000)
    pa = th + A * (rr - R_W0); pb = pa[-1] + A * (r1 - rr[::-1]); ra = rr * (1 + EPS * np.cos(M * (pa - th))); rb = rr[::-1] * (1 + EPS * np.cos(M * (pb - th)))
    def xy(r, p): return np.c_[r * np.cos(p), r * np.sin(p)]
    a = xy(ra, pa); b = xy(rb, pb)
    # leads: from r=62 inward to the flange ring, then along an arc to the assigned post
    post = math.radians(TXP[k % 3]); leads = []
    for pt_r, pt_p, rr_flange in ((ra[0], pa[0], 58.8), (rb[-1], pb[-1], 57.2)):
        ph0 = pt_p % (2 * math.pi); d = (post - ph0 + math.pi) % (2 * math.pi) - math.pi
        seg1 = np.c_[np.linspace(pt_r, rr_flange, 40) * math.cos(ph0), np.linspace(pt_r, rr_flange, 40) * math.sin(ph0)]
        ph = ph0 + np.linspace(0, d * (1 - 0.0), 400); seg2 = np.c_[rr_flange * np.cos(ph), rr_flange * np.sin(ph)]
        leads.append(np.vstack([seg1, seg2]))
    return a, b, leads[0], leads[1]
def dens(P, step=0.2):
    out = [P[0]]
    for q in P[1:]:
        d = np.linalg.norm(q - out[-1]);
        if d > 1e-9: n = max(1, int(d / step)); out += [out[-1] + (q - out[-1]) * (i / n) for i in range(1, n + 1)]
    return np.array(out)
def zt_fn(k): return lambda r: ZRX + (6 - k) * TV + s * (R_RIM - r)             # k = 1..6 top surface of layer k (1 = top)
def zb_fn(k): return lambda r: ZRX + (6 - k) * TV + s * (R_RIM - r) - TV + TV * 0.0 + (TV - TV)  # placeholder replaced below
def make_layer(k):                                                              # k = 1..6, 1 = top (away from ground)
    a, b, la, lb = arms(k - 1); TA = cKDTree(np.vstack([dens(a), dens(la)])); TB = cKDTree(np.vstack([dens(b), dens(lb)]))
    post_ang = np.radians(list(TXP) + list(RXP)); rin = lambda ph: R_IN + 0.0 * ph
    def rin_f(phi):
        r = np.full_like(phi, R_IN)
        for pa_ in post_ang:
            dphi = (phi - pa_ + np.pi) % (2 * np.pi) - np.pi; x = RP * np.sin(dphi); y = RP * np.cos(dphi) - 0.0
            # circle of radius 2.8 centred at (RP, pa_): lowest radius where the notch cuts the inner edge
            c2 = np.sqrt(np.maximum(2.8 ** 2 - (RP * np.sin(dphi)) ** 2, 0)); lo = RP * np.cos(dphi) - c2
            m = (np.abs(RP * np.sin(dphi)) < 2.8) & (lo < R_IN + 1.2); r = np.where(m & (lo < r + 1e-9) & (RP * np.cos(dphi) > 0), np.minimum(r, np.maximum(lo, 49.8)), r)
        return r
    def depth(X, Y):
        dA, _ = TA.query(np.c_[X.ravel(), Y.ravel()]); dB, _ = TB.query(np.c_[X.ravel(), Y.ravel()])
        sm = lambda d: np.clip((W_HALF - d) / 0.25, 0, 1); sm = (lambda f: (lambda d: f(d) * f(d) * (3 - 2 * f(d))))(sm)
        gA, gB = sm(dA), sm(dB); dep = D1 * np.maximum(gA, gB); both = np.minimum(gA, gB); dep = dep + (D2 - D1) * both
        return dep.reshape(X.shape)
    zt = lambda r: ZRX + (6 - k) * TV + s * (R_RIM - r) + TV; zb = lambda r: ZRX + (6 - k) * TV + s * (R_RIM - r)
    # top surface of layer k sits one TV above its bottom; layer 6 bottom is at ZRX at the rim
    phi = np.linspace(0, 2 * np.pi, NPHI, endpoint=False); rin_v = rin_f(phi); u = np.linspace(0, 1, NR)
    R_outv = np.minimum(R_RIM, R_W1 * (1 + EPS * np.cos(M * (phi - math.radians(GOLD * (k - 1))))) + OUTER_MARGIN)       # petal-shaped former outline
    R = rin_v[:, None] + (R_outv[:, None] - rin_v[:, None]) * u[None, :]; X = R * np.cos(phi)[:, None]; Y = R * np.sin(phi)[:, None]
    Z = zt(R) - depth(X, Y); Vt = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    cs, sn = np.cos(phi), np.sin(phi)
    Bi = np.c_[rin_v * cs, rin_v * sn, zb(rin_v)]; Bo = np.c_[R_outv * cs, R_outv * sn, zb(R_outv)]
    V = np.vstack([Vt, Bi, Bo]); nT = NPHI * NR; I = np.arange(NPHI); I2 = (I + 1) % NPHI; F = []
    j = np.arange(NR - 1); ii, jj = np.meshgrid(I, j, indexing="ij"); i2 = (ii + 1) % NPHI
    a_ = ii * NR + jj; b_ = ii * NR + jj + 1; c_ = i2 * NR + jj + 1; d_ = i2 * NR + jj
    F += [np.c_[a_.ravel(), b_.ravel(), c_.ravel()], np.c_[a_.ravel(), c_.ravel(), d_.ravel()]]
    ai, bi, ci, di = nT + I, nT + NPHI + I, nT + NPHI + I2, nT + I2                    # bottom (normal down)
    F += [np.c_[ai, ci, bi], np.c_[ai, di, ci]]
    Bo_i = nT + NPHI + I; Bo_i2 = nT + NPHI + I2; To_i = I * NR + NR - 1; To_i2 = I2 * NR + NR - 1                    # outer wall
    F += [np.c_[Bo_i, Bo_i2, To_i2], np.c_[Bo_i, To_i2, To_i]]
    Bi_i = nT + I; Bi_i2 = nT + I2; Ti_i = I * NR; Ti_i2 = I2 * NR                                                    # inner wall
    F += [np.c_[Bi_i, Ti_i, Ti_i2], np.c_[Bi_i, Ti_i2, Bi_i2]]
    F = np.vstack(F); return V, F, (a, b, la, lb)
def dir_edges_ok(F):
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]); key = e[:, 0].astype(np.int64) * 10 ** 7 + e[:, 1]; rkey = e[:, 1].astype(np.int64) * 10 ** 7 + e[:, 0]
    return int((~np.isin(key, rkey)).sum()), int(len(key) - len(np.unique(key)))
rep = {"slope_tan": round(s, 4), "slope_deg": round(math.degrees(BETA), 2), "layer_vertical_thickness_mm": round(TV, 3), "top_height_at_opening_mm": round(ZRX + 6 * TV + s * (R_RIM - R_IN), 2), "rim_height_mm": round(ZRX + 6 * TV, 2), "lod": LOD}
paths = {}
for k in range(1, 7):
    V, F, P = make_layer(k); open_e, dup = dir_edges_ok(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    rc.write_stl(f"{OUT}/L{k}_tx_cassette.stl", V, F, f"L{k}"); paths[k] = P
    rep[f"L{k}"] = dict(tris=int(len(F)), open_edges=open_e, duplicate_directed_edges=dup, bbox=[round(float(x), 1) for x in (*V.min(0), *V.max(0))], shift_deg=round((GOLD * (k - 1)) % 360, 2), shift_mod_120=round((GOLD * (k - 1)) % 120, 2), post=f"TX post {k % 3}")
np.save(f"{OUT}/paths.npy", np.array([[np.vstack([paths[k][0], paths[k][1]]).shape] for k in paths], dtype=object), allow_pickle=True)
json.dump(rep, open(f"{OUT}/cassette_report.json", "w"), indent=1); print(json.dumps(rep)[:1500])
import pickle; pickle.dump(paths, open(f"{OUT}/paths.pkl", "wb"))
