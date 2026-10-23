#!/usr/bin/env python3
"""v13 high-precision petal coil formers: Fermat/sunflower spiral, golden-angle layer phase, 0.15 mm radial grid across the winding band, flared lead mouths into the hub lanes, lead anchor pockets, A/B markers, fiducials, bore lead-in chamfer, L1 bond-key notches."""
import math, json, os, sys, csv, pickle, numpy as np
from scipy.spatial import cKDTree
from matplotlib.path import Path
import rodin_core_v4 as rc
LOD = sys.argv[1] if len(sys.argv) > 1 else "low"
OUT = "kit_v14/PRINT" if LOD == "print" else "kit_v14/LOW"; os.makedirs(OUT, exist_ok=True)
R_RIM, MARGIN, M_PET, A_RIP, N_ARM, GOLD = 116.5, 4.5, 12, 2.4, 8, 137.50776405
D_DOME, PN, ZRX, RELIEF, G = 10.0, 3.6, 3.2, 0.48, 0.8
R1 = R_RIM - MARGIN - A_RIP; R0 = 62.0; W_HALF, D1, D2 = 0.75, 1.3, 2.4; RAMP = 0.15
HUB_R, BORE, TOOTH_W, TOOTH_H = 49.5, 49.9, 3.6, 2.6; PIN_C, NOTCH_R = 51.7, 1.9; LUG_C, LUG_NR = 50.0, 1.8; CHAMF_W, CHAMF_H = 0.5, 1.0
dome = lambda r: D_DOME * (1 - (r / R_RIM) ** 2); wrap = lambda a: (a + np.pi) % (2 * np.pi) - np.pi
PSI = lambda k: math.radians((GOLD * (k - 1)) % 360); LA = lambda k: PSI(k) + math.radians(6); LB = lambda k: PSI(k) + math.radians(11); LRX = lambda k: PSI(k) + math.radians(16)
def rip(j, R, phi): return RELIEF * (R / R_RIM) ** 2 * np.cos(M_PET * (phi - math.radians(GOLD * (j - 1))))
def zb(k, R, phi):
    z = ZRX + dome(R) + (6 - k) * (PN + G)
    for j in range(k + 1, 7): z = z + rip(j, R, phi)
    return z
v11 = json.load(open("kit_v11/PRINT/report.json")); NOTCH = {k: [] for k in range(1, 8)}
for p in v11["pin_table"]: NOTCH[p["interface"]].append(p["theta_deg"]); NOTCH[p["interface"] + 1].append(p["theta_deg"])
def lug_angles():
    wins = [math.degrees(LA(1)), math.degrees(LB(1)), math.degrees(LRX(1))] + NOTCH[1]; out = []; n = 30
    while len(out) < 6:
        n += 1; th = (n * GOLD) % 360
        if all(abs((th - w + 180) % 360 - 180) > 9 for w in wins) and all(abs((th - o + 180) % 360 - 180) > 40 for o in out): out.append(th)
    return sorted(out)
LUGS = lug_angles()
def arms(k):
    al = math.radians(GOLD * (k - 1)); t = np.linspace(0, 1, 4000); dl = LB(k) - LA(k); th0 = LA(k); bore = BORE
    pa = np.sqrt(R0 ** 2 + (R1 ** 2 - R0 ** 2) * t); tha = th0 + 2 * np.pi * N_ARM * t; ra = pa + A_RIP * (pa / R1) ** 2 * np.cos(M_PET * (tha - al))
    pb = np.sqrt(R1 ** 2 - (R1 ** 2 - R0 ** 2) * t); thb = tha[-1] + dl + 2 * np.pi * N_ARM * t; rb = pb + A_RIP * (pb / R1) ** 2 * np.cos(M_PET * (thb - al))
    xy = lambda r, p: np.c_[r * np.cos(p), r * np.sin(p)]; a = xy(ra, tha); b = xy(rb, thb)
    la = xy(np.linspace(ra[0], bore - 0.2, 60), np.full(60, th0)); lb = xy(np.linspace(rb[-1], bore - 0.2, 60), np.full(60, thb[-1])); return a, b, la, lb
def dens(P, step=0.15):
    out = [P[0]]
    for q in P[1:]:
        d = np.linalg.norm(q - out[-1])
        if d > 1e-9: n = max(1, int(d / step)); out += [out[-1] + (q - out[-1]) * (i / n) for i in range(1, n + 1)]
    return np.array(out)
def rot_poly(ang, pts): c, s = math.cos(ang), math.sin(ang); return np.array([(x * c - y * s, x * s + y * c) for x, y in pts])
def far_r(phi, th_deg, c, R):
    d = wrap(phi - math.radians(th_deg)); off = c * np.sin(d); ins = (np.abs(off) < R) & (np.cos(d) > 0)
    return np.where(ins, c * np.cos(d) + np.sqrt(np.maximum(R ** 2 - off ** 2, 0)), 0.0)
def make_layer(k):
    a, b, la, lb = arms(k); al = math.radians(GOLD * (k - 1)); TA = cKDTree(np.vstack([dens(a), dens(la)])); TB = cKDTree(np.vstack([dens(b), dens(lb)]))
    # features: pits (numbering, A/B markers, fiducials), lead anchor pockets, flared mouths
    P_r = lambda r, ang: (r * math.cos(ang), r * math.sin(ang)); pits = {}
    pits["numbering"] = [P_r(55.0, PSI(k) - math.radians(5 + 3.4 * i)) for i in range(k)]
    pits["marker_A"] = [P_r(60.8, LA(k) - math.radians(3.6))]; pits["marker_B"] = [P_r(60.8, LB(k) + math.radians(3.6 + 3.5 * i)) for i in range(2)]
    pits["fiducials"] = [P_r(56.5, PSI(k) + math.radians(d)) for d in (130, 250, 310)]
    allp = np.array([p for v in pits.values() for p in v]); TP = cKDTree(allp)
    ID_ANG = [PSI(k) + math.radians(4.2 * (i - (k - 1) / 2)) for i in range(k)]                  # k layer-ID notches on the rim, centred on the track direction
    pockets = {"anchor_A": rot_poly(LA(k), [(54.0, -1.5), (59.5, -1.5), (59.5, 1.5), (54.0, 1.5)]), "anchor_B": rot_poly(LB(k), [(54.0, -1.5), (59.5, -1.5), (59.5, 1.5), (54.0, 1.5)]),
               "mouth_A": rot_poly(LA(k), [(BORE - 0.3, -1.3), (53.4, -0.75), (53.4, 0.75), (BORE - 0.3, 1.3)]), "mouth_B": rot_poly(LB(k), [(BORE - 0.3, -1.3), (53.4, -0.75), (53.4, 0.75), (BORE - 0.3, 1.3)])}
    pdepth = {"anchor_A": 1.6, "anchor_B": 1.6, "mouth_A": D1, "mouth_B": D1}; paths_ = {n: Path(p) for n, p in pockets.items()}; bnd = {n: cKDTree(dens(np.vstack([p, p[:1]]), 0.08)) for n, p in pockets.items()}
    sm = lambda x: (lambda u: u * u * (3 - 2 * u))(np.clip(x, 0, 1))
    def depth(X, Y):
        q = np.c_[X.ravel(), Y.ravel()]; dA, _ = TA.query(q); dB, _ = TB.query(q); dP, _ = TP.query(q); gA, gB = sm((W_HALF - dA) / RAMP), sm((W_HALF - dB) / RAMP)
        dep = D1 * np.maximum(gA, gB) + (D2 - D1) * np.minimum(gA, gB); dep = np.maximum(dep, 0.8 * sm((1.2 - dP) / RAMP))
        for n, pa_ in paths_.items():
            ins = pa_.contains_points(q); db, _ = bnd[n].query(q); dep = np.maximum(dep, pdepth[n] * np.where(ins, sm(db / RAMP), 0.0))
        return dep.reshape(X.shape)
    NP0 = 720; base = np.linspace(0, 2 * np.pi, NP0, endpoint=False); ex = []
    if LOD == "print":
        wins = [(LA(k), 2.2, 0.04), (LB(k), 2.2, 0.04)] + ([(PSI(k), 2.6, 0.05)] if k > 1 else []) + [(math.radians(t), 3.2, 0.1) for t in NOTCH[k]] + ([(math.radians(t), 3.2, 0.1) for t in LUGS] if k == 1 else []) + [(math.atan2(p[1], p[0]), 1.9, 0.15) for p in allp] + [(c, 2.4, 0.1) for c in ID_ANG]
        for c, hw, st in wins: ex.append(np.arange(c - math.radians(hw), c + math.radians(hw), math.radians(st)))
    phi = np.unique(np.round(np.mod(np.concatenate([base] + ex), 2 * np.pi), 9)); NP = len(phi)
    rn = np.r_[np.arange(BORE, 58.0, 0.4), np.arange(58.0, 114.0, 0.15), 114.0] if LOD == "print" else np.linspace(BORE, 114.0, 70)
    u = (rn - BORE) / (114.0 - BORE); u[-1] = 1.0; NR = len(u)
    rin_v = np.full(NP, 49.3 if k == 1 else BORE)
    if k > 1: rin_v = np.where(np.abs(wrap(phi - PSI(k))) * BORE < TOOTH_W / 2, BORE - TOOTH_H, rin_v)
    for th in NOTCH[k]: rin_v = np.maximum(rin_v, far_r(phi, th, PIN_C, NOTCH_R))
    if k == 1:
        for th in LUGS: rin_v = np.maximum(rin_v, far_r(phi, th, LUG_C, LUG_NR))
    R_outv = np.minimum(R_RIM, R1 + A_RIP * np.cos(M_PET * (phi - al)) + MARGIN)
    for th in ID_ANG:
        c_ = min(R_RIM, R1 + A_RIP * math.cos(M_PET * (th - al)) + MARGIN); d_i = wrap(phi - th); off_i = c_ * np.sin(d_i); in_i = (np.abs(off_i) < 1.5) & (np.cos(d_i) > 0)
        R_outv = np.where(in_i, np.minimum(R_outv, c_ * np.cos(d_i) - np.sqrt(np.maximum(1.5 ** 2 - off_i ** 2, 0))), R_outv)
    R = rin_v[:, None] + (R_outv[:, None] - rin_v[:, None]) * u[None, :]; X = R * np.cos(phi)[:, None]; Y = R * np.sin(phi)[:, None]; PH = phi[:, None] + 0 * R
    Z = zb(k, R, PH) + PN + rip(k, R, PH) - depth(X, Y); Vt = np.c_[X.ravel(), Y.ravel(), Z.ravel()]; cs, sn = np.cos(phi), np.sin(phi)
    NRb = 56 if LOD == "print" else 24; ub = np.linspace(0, 1, NRb); r0b = rin_v + CHAMF_W                      # FULL underside grid that follows the true dome + relief nesting surface
    Rb = r0b[:, None] + (R_outv[:, None] - r0b[:, None]) * ub[None, :]; PHb = phi[:, None] + 0 * Rb; Zbg = zb(k, Rb, PHb)
    Vb = np.c_[(Rb * np.cos(PHb)).ravel(), (Rb * np.sin(PHb)).ravel(), Zbg.ravel()]; Bm = np.c_[rin_v * cs, rin_v * sn, zb(k, rin_v, phi) + CHAMF_H]
    V = np.vstack([Vt, Vb, Bm]); nT = NP * NR; nB = NP * NRb; I = np.arange(NP); I2 = (I + 1) % NP; F = []
    ii, jj = np.meshgrid(I, np.arange(NR - 1), indexing="ij"); i2 = (ii + 1) % NP; a_ = ii * NR + jj; b_ = ii * NR + jj + 1; c_ = i2 * NR + jj + 1; d_ = i2 * NR + jj
    F += [np.c_[a_.ravel(), b_.ravel(), c_.ravel()], np.c_[a_.ravel(), c_.ravel(), d_.ravel()]]
    ib, jbb = np.meshgrid(I, np.arange(NRb - 1), indexing="ij"); ib2 = (ib + 1) % NP; A_ = nT + ib * NRb + jbb; B_ = A_ + 1; C_ = nT + ib2 * NRb + jbb + 1; D_ = nT + ib2 * NRb + jbb
    F += [np.c_[A_.ravel(), C_.ravel(), B_.ravel()], np.c_[A_.ravel(), D_.ravel(), C_.ravel()]]                 # underside (normal down)
    iB, oB, mB = nT + I * NRb, nT + I * NRb + NRb - 1, nT + nB + I; iB2, oB2, mB2 = nT + I2 * NRb, nT + I2 * NRb + NRb - 1, nT + nB + I2
    F += [np.c_[oB, oB2, I2 * NR + NR - 1], np.c_[oB, I2 * NR + NR - 1, I * NR + NR - 1]]                          # outer wall
    F += [np.c_[iB, mB, mB2], np.c_[iB, mB2, iB2]]                                                                 # bore chamfer
    F += [np.c_[mB, I * NR, I2 * NR], np.c_[mB, I2 * NR, mB2]]                                                      # inner wall
    info = dict(pits={n: [[round(float(x), 3), round(float(y), 3)] for x, y in v] for n, v in pits.items()}, pockets={n: np.round(p, 3).tolist() for n, p in pockets.items()}, nphi=int(NP), nr=int(NR), nrb=int(NRb), id_notch_deg=[round(math.degrees(c) % 360, 2) for c in ID_ANG])
    return V, np.vstack(F), (a, b, la, lb), info
def dir_edges_ok(F):
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]); key = e[:, 0].astype(np.int64) * 10 ** 7 + e[:, 1]; rkey = e[:, 1].astype(np.int64) * 10 ** 7 + e[:, 0]
    return int((~np.isin(key, rkey)).sum()), int(len(key) - len(np.unique(key)))
rep = dict(lod=LOD, spec=dict(groove="top 1.5 / floor 1.2 / depth 1.3 (crossing 2.4), wire 1.2 max", bore=BORE, chamfer="%.1f x %.1f at the bottom edge of bore, tooth and notches" % (CHAMF_W, CHAMF_H), anchors="3.0 x 5.5 x 1.6 pockets at r54-59.5 on both leads", mouth="flared 2.6 to 1.5 over r49.6-53.4", L1_bond_key_notches_deg=[round(x, 2) for x in LUGS], bond_key_notch="R1.8 centred at r50.0"))
paths = {}
for k in range(1, 7):
    V, F, Pp, info = make_layer(k); oe, dup = dir_edges_ok(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    rc.write_stl(f"{OUT}/FORMER_L{k}_petal_coil_former.stl", V, F, f"L{k}"); paths[k] = Pp
    rep[f"L{k}"] = dict(tris=int(len(F)), open_edges=oe, duplicate_edges=dup, phase_deg=round((GOLD * (k - 1)) % 360, 2), lead_A_deg=round(math.degrees(LA(k)) % 360, 2), lead_B_deg=round(math.degrees(LB(k)) % 360, 2), features=info)
    a, b, la, lb = Pp
    with open(f"{OUT}/FORMER_L{k}_winding_centerline.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["segment", "x_mm", "y_mm", "z_wire_center_mm"])
        for nm, arr in (("lead_A_in", la[::-1]), ("out_arm", a), ("return_arm", b), ("lead_B_out", lb)):
            for p in arr[::2 if nm.endswith("arm") else 1]:
                r_ = float(np.hypot(*p)); ph_ = float(np.arctan2(p[1], p[0])); w.writerow([nm, round(float(p[0]), 3), round(float(p[1]), 3), round(float(zb(k, np.array(r_), np.array(ph_))) + PN + float(rip(k, np.array(r_), np.array(ph_))) - D1 + 0.6, 3)])
    print(k, len(F), info["nphi"], info["nr"], flush=True)
rep["rotation_table"] = {f"L{k}": dict(hub_track_and_key_tooth_deg=round((GOLD * (k - 1)) % 360, 3), petal_phase_deg=round((GOLD * (k - 1)) % 360, 3), petal_phase_mod_30=round((GOLD * (k - 1)) % 30, 3), lead_A_deg=round(math.degrees(LA(k)) % 360, 3), lead_B_deg=round(math.degrees(LB(k)) % 360, 3), TX_lanes_deg=[round(math.degrees(LA(k)) % 360, 3), round(math.degrees(LB(k)) % 360, 3)], RX_lane_deg=round(math.degrees(LRX(k)) % 360, 3), pin_notches_deg=[round(x, 2) for x in NOTCH[k]], rim_ID_notches=k) for k in range(1, 7)}
rep["formulas"] = dict(golden_angle_deg=GOLD, layer_rotation="alpha_k = (k-1) x 137.50776405 deg, applied to key tooth, petal ripple, lead angles, pins", spiral="rho^2 = R0^2 + (R1^2 - R0^2) t, theta = theta0 + 2 pi 8 t (out arm); mirror return: rho^2 = R1^2 - (R1^2-R0^2) t, theta continues increasing", R0=R0, R1=round(R1, 3), ripple="r = rho + 2.4 (rho/R1)^2 cos(12 (theta - alpha_k))", face="z_top = z_bottom + 3.6 + 0.48 (r/116.5)^2 cos(12 (theta - alpha_k)); z_bottom,k = 3.2 + 10 (1-(r/116.5)^2) + (6-k)(3.6+0.8) + sum_{j>k} 0.48 (r/116.5)^2 cos(12 (theta - alpha_j))")
json.dump(rep, open(f"{OUT}/report.json", "w"), indent=1, default=float); pickle.dump(paths, open(f"{OUT}/paths.pkl", "wb")); print("done", LUGS)
