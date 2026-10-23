#!/usr/bin/env python3
"""PHI-FOLD 233 v8: six petal cassettes from the uploaded R1 formulas rescaled to D233; Fermat/sunflower radial spacing, golden-angle layer offsets, flatter slightly domed faces, L1 = base foundation hub with PCB slots."""
import math, json, os, sys, pickle, numpy as np
from scipy.spatial import cKDTree
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
LOD = sys.argv[1] if len(sys.argv) > 1 else "low"
OUT = "kit_v8/PRINT" if LOD == "print" else "kit_v8/LOW"; os.makedirs(OUT, exist_ok=True)
NPHI, NR = (1200, 150) if LOD == "print" else (540, 70)
R_RIM, R_IN, MARGIN, RP = 116.5, 52.0, 4.5, 53.8
M_PET, A_RIP, N_ARM, GOLD = 12, 2.4, 8, 137.50776405          # R1 used 12 petals, ripple 3 mm at r=138 (scaled 0.8); 8+8 arm turns = 16 turns
D_DOME, PN, GAP, ZRX, HMAX, RELIEF = 10.0, 3.6, 0.6, 3.2, 44.5, 0.48
PV = PN + GAP; R1 = R_RIM - MARGIN - A_RIP; R0 = 62.0
TXP, RXP = (90, 210, 330), (30, 150, 270); W_HALF, D1, D2 = 0.7, 1.3, 2.3
dome = lambda r: D_DOME * (1 - (r / R_RIM) ** 2)
zb_k = lambda k, r: ZRX + (6 - k) * PV + dome(r)
def arms(k):
    al = math.radians(GOLD * k); t = np.linspace(0, 1, 4000); dl = 0.14
    pa_ = np.sqrt(R0 ** 2 + (R1 ** 2 - R0 ** 2) * t); tha = al + 2 * np.pi * N_ARM * t; ra = pa_ + A_RIP * (pa_ / R1) ** 2 * np.cos(M_PET * (tha - al))
    pb_ = np.sqrt(R1 ** 2 - (R1 ** 2 - R0 ** 2) * t); thb = tha[-1] + dl + 2 * np.pi * N_ARM * t; rb = pb_ + A_RIP * (pb_ / R1) ** 2 * np.cos(M_PET * (thb - al))
    xy = lambda r, p: np.c_[r * np.cos(p), r * np.sin(p)]; a = xy(ra, tha); b = xy(rb, thb); post = math.radians(TXP[k % 3]); leads = []
    for pr, pp, rf in ((ra[0], tha[0], 58.8), (rb[-1], thb[-1], 57.2)):
        ph0 = pp % (2 * math.pi); d = (post - ph0 + math.pi) % (2 * math.pi) - math.pi
        s1 = np.c_[np.linspace(pr, rf, 40) * math.cos(ph0), np.linspace(pr, rf, 40) * math.sin(ph0)]; ph = ph0 + np.linspace(0, d, 400); leads.append(np.vstack([s1, np.c_[rf * np.cos(ph), rf * np.sin(ph)]]))
    return a, b, leads[0], leads[1]
def dens(P, step=0.2):
    out = [P[0]]
    for q in P[1:]:
        d = np.linalg.norm(q - out[-1])
        if d > 1e-9: n = max(1, int(d / step)); out += [out[-1] + (q - out[-1]) * (i / n) for i in range(1, n + 1)]
    return np.array(out)
post_ang = np.radians(list(TXP) + list(RXP))
def rin_f(phi):
    r = np.full_like(phi, R_IN)
    for pa_ in post_ang:
        dphi = (phi - pa_ + np.pi) % (2 * np.pi) - np.pi; c2 = np.sqrt(np.maximum(2.8 ** 2 - (RP * np.sin(dphi)) ** 2, 0)); lo = RP * np.cos(dphi) - c2
        m = (np.abs(RP * np.sin(dphi)) < 2.8) & (lo < R_IN + 1.2) & (RP * np.cos(dphi) > 0); r = np.where(m & (lo < r + 1e-9), np.minimum(r, np.maximum(lo, 49.8)), r)
    return r
def make_layer(k):
    a, b, la, lb = arms(k - 1); al = math.radians(GOLD * (k - 1)); TA = cKDTree(np.vstack([dens(a), dens(la)])); TB = cKDTree(np.vstack([dens(b), dens(lb)]))
    def depth(X, Y):
        q = np.c_[X.ravel(), Y.ravel()]; dA, _ = TA.query(q); dB, _ = TB.query(q); f = lambda d: (lambda u: u * u * (3 - 2 * u))(np.clip((W_HALF - d) / 0.25, 0, 1))
        gA, gB = f(dA), f(dB); return (D1 * np.maximum(gA, gB) + (D2 - D1) * np.minimum(gA, gB)).reshape(X.shape)
    phi = np.linspace(0, 2 * np.pi, NPHI, endpoint=False); rin_v = rin_f(phi); u = np.linspace(0, 1, NR)
    R_outv = np.minimum(R_RIM, R1 + A_RIP * np.cos(M_PET * (phi - al)) + MARGIN)                      # petal-shaped former outline
    R = rin_v[:, None] + (R_outv[:, None] - rin_v[:, None]) * u[None, :]; X = R * np.cos(phi)[:, None]; Y = R * np.sin(phi)[:, None]
    rip = RELIEF * (R / R_RIM) ** 2 * np.cos(M_PET * (phi[:, None] - al))                              # R1 face relief: (r/R)^2 cos(12(theta-alpha)), scaled
    Z = zb_k(k, R) + PN + rip - depth(X, Y); Vt = np.c_[X.ravel(), Y.ravel(), Z.ravel()]; cs, sn = np.cos(phi), np.sin(phi)
    Bi = np.c_[rin_v * cs, rin_v * sn, zb_k(k, rin_v)]; Bo = np.c_[R_outv * cs, R_outv * sn, zb_k(k, R_outv)]; V = np.vstack([Vt, Bi, Bo]); nT = NPHI * NR; I = np.arange(NPHI); I2 = (I + 1) % NPHI; F = []
    ii, jj = np.meshgrid(I, np.arange(NR - 1), indexing="ij"); i2 = (ii + 1) % NPHI; a_ = ii * NR + jj; b_ = ii * NR + jj + 1; c_ = i2 * NR + jj + 1; d_ = i2 * NR + jj
    F += [np.c_[a_.ravel(), b_.ravel(), c_.ravel()], np.c_[a_.ravel(), c_.ravel(), d_.ravel()]]
    F += [np.c_[nT + I, nT + NPHI + I2, nT + NPHI + I], np.c_[nT + I, nT + I2, nT + NPHI + I2]]
    F += [np.c_[nT + NPHI + I, nT + NPHI + I2, I2 * NR + NR - 1], np.c_[nT + NPHI + I, I2 * NR + NR - 1, I * NR + NR - 1]]
    F += [np.c_[nT + I, I * NR, I2 * NR], np.c_[nT + I, I2 * NR, nT + I2]]
    F = np.vstack(F); return V, F, (a, b, la, lb)
def dir_edges_ok(F):
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]); key = e[:, 0].astype(np.int64) * 10 ** 7 + e[:, 1]; rkey = e[:, 1].astype(np.int64) * 10 ** 7 + e[:, 0]
    return int((~np.isin(key, rkey)).sum()), int(len(key) - len(np.unique(key)))
def circ(r, m=96): t = np.linspace(0, 2 * np.pi, m, endpoint=False); return np.c_[r * np.cos(t), r * np.sin(t)]
def ring(outer, inner, z0, z1):
    m = len(outer); V = np.concatenate([np.c_[outer, np.full(m, z0)], np.c_[outer, np.full(m, z1)], np.c_[inner, np.full(m, z0)], np.c_[inner, np.full(m, z1)]]); O0, O1, I0, I1 = (np.arange(m) + k * m for k in range(4)); n = np.roll(np.arange(m), -1); F = []
    for i in range(m): j = n[i]; F += [[O0[i], O0[j], O1[j]], [O0[i], O1[j], O1[i]], [I0[j], I0[i], I1[i]], [I0[j], I1[i], I1[j]], [O0[j], O0[i], I0[i]], [O0[j], I0[i], I0[j]], [O1[i], O1[j], I1[j]], [O1[i], I1[j], I1[i]]]
    F = np.array(F); return (V, F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
def extrude(poly, z0, z1):
    Pp = np.asarray(poly); m = len(Pp); T = tri2d(Pp); ar = (Pp[:, 0] * np.roll(Pp[:, 1], -1) - np.roll(Pp[:, 0], -1) * Pp[:, 1]).sum(); V = np.concatenate([np.c_[Pp, np.full(m, z0)], np.c_[Pp, np.full(m, z1)]]); F = []
    for t in T: F.append([m + t[0], m + t[1], m + t[2]] if ar > 0 else [m + t[0], m + t[2], m + t[1]]); F.append([t[0], t[2], t[1]] if ar > 0 else [t[0], t[1], t[2]])
    for i in range(m): j = (i + 1) % m; F += [[i, j, m + j], [i, m + j, m + i]] if ar > 0 else [[i, m + j, j], [i, m + i, m + j]]
    F = np.array(F); return (V, F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
def post_profile(r=2.5, nd=1.2, w=1.4, m=120):
    pts = []
    for a in np.linspace(0, 2 * np.pi, m, endpoint=False):
        rr = r
        for c in (0, np.pi / 2, np.pi, 1.5 * np.pi):
            if abs((a - c + np.pi) % (2 * np.pi) - np.pi) * r < w / 2: rr = r - nd
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return np.array(pts)
rep = dict(lod=LOD, formulas=dict(spiral="Fermat/sunflower: rho^2 = R0^2 + (R1^2-R0^2) t, theta = alpha + 2 pi 8 t (8 turns out + 8 turns mirror return = 16)", ripple="r = rho + 2.4 (rho/R1)^2 cos(12 (theta - alpha))  [R1 file: 3 (rho/138)^2 cos(12..)]", face="z = dome(r) + 0.48 (r/116.5)^2 cos(12 (theta - alpha)),  dome = 10 (1-(r/116.5)^2)", layer_offset_deg="alpha_k = k x 137.508", R0=R0, R1=round(R1, 2)),
           stack=dict(layer_thickness=PN, pitch=PV, top_at_opening=round(ZRX + 5 * PV + PN + dome(R_IN), 1), rim_top=round(ZRX + 5 * PV + PN + dome(R_RIM), 1)))
paths = {}
for k in range(1, 7):
    V, F, Pp = make_layer(k); oe, dup = dir_edges_ok(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    rc.write_stl(f"{OUT}/L{k}_petal_cassette.stl", V, F, f"L{k}"); paths[k] = Pp
    rep[f"L{k}"] = dict(tris=int(len(F)), open_edges=oe, duplicate_edges=dup, alpha_deg=round((GOLD * (k - 1)) % 360, 2), mod_30=round((GOLD * (k - 1)) % 30, 2), post=f"TX post {TXP[(k - 1) % 3]} deg")
# parts
def emit(name, shells, note=""):
    bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells); V, F = g.merge(shells); rc.write_stl(f"{OUT}/{name}.stl", V, F, name); rep[name] = dict(tris=int(len(F)), nonmanifold_edges=int(bad), bbox=[round(float(x), 1) for x in (*V.min(0), *V.max(0))], note=note)
ztop_post = zb_k(1, RP) + PN + RELIEF + 3.0
for nm, angs in (("TX", TXP), ("RX", RXP)):
    for i, a in enumerate(angs):
        V, F = extrude(post_profile(), ZRX, ztop_post); emit(f"POST_{nm}_{i + 1}_at_{a}deg", [(V + [RP * math.cos(math.radians(a)), RP * math.sin(math.radians(a)), 0], F)], "D5 post, 4 open wire channels 1.4 x 1.2, length %.1f" % (ztop_post - ZRX))
slots = (9.0, 17.0, 25.0, 33.0)
emit("L1_foundation_hub_with_PCB_slots", [ring(circ(49.5), circ(46.5), 6.0, 41.3), ring(circ(52.0), circ(10.0), 41.3, HMAX), ring(circ(52.0), circ(49.5), 30.0, 41.3)] + [ring(circ(46.5), circ(44.0), z - 1.2, z) for z in slots],
     "base foundation hub fused to L1: tube r46.5-49.5 (35.3 mm inner height), roof with D20 gland/fill port, 4 PCB slot ledges for D88 discs at z=9/17/25/33 (8 mm pitch)")
emit("V2_vault_floor_plate", [ring(circ(49.5), circ(8.0), 3.4, 6.0)], "floor seat for the ferrite / nanocrystalline bottom plate")
emit("L7_RX_tray_cassette", [ring(circ(116.5), circ(5.0), 0.0, 0.8), ring(circ(116.5), circ(114.5), 0.0, ZRX)], "RX tray: 0.8 mm floor, PCB recess D229 x 2.4, 2 mm rim wall, open back")
rep["feedthrough_drill_table"] = "13 lead ports (6 TX drains, 1 VBUS common, 6 RX) at z=38 around the hub tube wall, grouped by the three TX and three RX posts; drill/pot after fitting"
json.dump(rep, open(f"{OUT}/report.json", "w"), indent=1, default=float); pickle.dump(paths, open(f"{OUT}/paths.pkl", "wb"))
print(json.dumps({k: (v.get("open_edges"), v.get("tris")) for k, v in rep.items() if k.startswith("L")}), rep["stack"])
