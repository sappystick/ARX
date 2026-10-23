#!/usr/bin/env python3
"""
phi_fold_v2.py — PHI-FOLD 233 v2: golden-band annular former
=============================================================
Changes vs v1 (all driven by the simulations):
 * Copper only in the golden band r >= R_b/phi = 72.0 mm (face AND underside):
   +15..19 % field per sqrt(W) at 200-300 mm for equal copper.
 * Former is an annulus (inner wall at r = 72.0); the fold goes over the inner
   wall instead of through a 13 mm bore.  Centre = separate hub with the
   ferrite pinpoint core.
 * Double-stacked grooves (2 wires per lane, 2 circuits per section) to put
   ~2x copper into the band.
 * Twist is zero across the heel-rim-crown zone, so each lane crosses the rim
   straight; this frees the rim for 4 lead-exit notches (one per section),
   running beside each lane from the underside edge over the rim.
"""
import math, json, os, time
import numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, phi_fold_former as pf

PHI = (1 + 5 ** .5) / 2
OD, RIM_H = 233.0, 13.0                  # rim 13 (F7) so 5 mm blends fit
R_B = OD / 2
R_I = R_B / PHI                          # 72.004 golden band inner radius
T_SLOPE = PHI ** -3; ALPHA = math.atan(T_SLOPE)
H_IN = RIM_H + (R_B - R_I) * T_SLOPE     # height at inner wall
N_W = 4
WIRE_OD = 1.20
A_SEAT = WIRE_OD / 2 + 0.05              # 0.65
N_STACK = 2
G_DEPTH = N_STACK * WIRE_OD + 0.05       # 2.45 (two wires + clearance)
G_LAND = 0.25
PITCH = 2 * A_SEAT + 2 * G_LAND + 0.05   # 1.85
RHO = dict(heel=5.0, crown=5.0, brow=4.0, foot=4.0)
RIM_ZONE = 0.0                           # mm of face/underside next to the rim with zero twist
RAMP = 12.0                              # beta-ramp length (bend radius >= ~4 mm)
NOTCHES = True
ZONE_SEGS = None                          # e.g. ("brow","inner","foot"): zero-twist zone -> wire crosses that wall at ONE azimuth per section
# exit notch (beside each lane, in the zero-twist rim zone)
NOTCH_X = (2.0, 8.0)                     # mm from lane centre (one side)
NOTCH_D = 3.0                            # depth, normal to surface

def build_profile():
    u = lambda h: np.array([math.cos(h), math.sin(h)])
    V = [np.array([R_I, 0.0]), np.array([R_B, 0.0]), np.array([R_B, RIM_H]), np.array([R_I, H_IN])]
    hd = [0.0, math.pi / 2, math.pi - ALPHA, 1.5 * math.pi]
    names = ["bottom", "rim", "face", "inner"]; cn = ["heel", "crown", "brow", "foot"]
    corners = []
    for i in range(4):
        ha, hb = hd[i], hd[(i + 1) % 4] + (2 * math.pi if i == 3 else 0)
        dturn = (hb - ha) % (2 * math.pi)
        L = dturn * RHO[cn[i]] / (1 - rc.BLEND_F)
        ch, _ = rc.Blend.unit_chord(ha, dturn); ch *= L
        sv = u(ha) + u(hb); corners.append((dturn, L, ch.dot(sv) / sv.dot(sv)))
    segs = []
    for i in range(4):
        A, Bv = V[i], V[(i + 1) % 4]
        L = np.linalg.norm(Bv - A) - corners[i - 1][2] - corners[i][2]
        assert L > 0, f"{names[i]} too short"
        segs.append((names[i], rc.Line(A + corners[i - 1][2] * u(hd[i]), hd[i], L)))
        dturn, Lb, d = corners[i]
        segs.append((cn[i], rc.Blend(Bv - d * u(hd[i]), hd[i], dturn, Lb)))
    return segs

class Former:
    def __init__(self):
        self.segs = build_profile(); self.off, self.L = rc.seg_offsets(self.segs)
        S = dict(self.segs)
        sf = np.linspace(0, self.L, 400001); r = rc.eval_profile(self.segs, sf)[0]
        sector = 2 * math.pi / N_W
        gmax = np.sqrt(np.maximum((r * sector / PITCH) ** 2 - 1, 0)) / r
        # zero-twist rim zone: from (end of bottom - RIM_ZONE) to (face start + RIM_ZONE)
        z0 = self.off["bottom"] + S["bottom"].L - RIM_ZONE
        z1 = self.off["face"] + RIM_ZONE
        self.zone = (z0, z1)
        w = np.ones_like(sf)
        if NOTCHES:
            w = np.where(sf < z0, rc.Q((z0 - sf) / RAMP), w)
            w = np.where((sf >= z0) & (sf <= z1), 0.0, w)
            w = np.where(sf > z1, rc.Q((sf - z1) / RAMP), w)
        # ramp the lane ANGLE beta (not the twist rate) -> bounded in-surface bend radius
        if ZONE_SEGS:
            za = self.off[ZONE_SEGS[0]]; zb = self.off[ZONE_SEGS[-1]] + S[ZONE_SEGS[-1]].L; Lt = self.L
            d = np.minimum((za - sf) % Lt, (sf - zb) % Lt)
            w = np.where((sf >= za) & (sf <= zb), 0.0, rc.Q(d / RAMP))
        bmax = np.arctan(r * gmax)
        gg = np.tan(bmax * w) / r
        c = np.concatenate([[0], np.cumsum((gg[1:] + gg[:-1]) / 2 * np.diff(sf))])
        turns = math.floor(c[-1] / (2 * math.pi)); sc = turns * 2 * math.pi / c[-1]
        self.sf, self.g, self.c, self.turns = sf, gg * sc, c * sc, turns
        self.w = w
    def twist(self, s): return np.interp(s, self.sf, self.c)
    def dens(self, s): return np.interp(s, self.sf, self.g)
    def zone_w(self, s):   # 1 inside notch zone, ramps to 0 over RAMP
        return 1 - np.interp(s, self.sf, self.w)
    def rows(self, du=0.035, ds=0.2):
        u = np.arange(0, self.c[-1], du)
        return np.unique(np.concatenate([np.interp(u, self.c, self.sf), np.arange(0, self.L, ds)]))

def seat_stack(x, a, depth):
    """U slot: semicircular floor radius a at 'depth', vertical walls to surface."""
    return -depth + a - np.sqrt(np.maximum(a * a - x * x, 0.0))

def build_mesh(fm, du=0.035, narc=9, nfill=16, nnotch=6):
    s = fm.rows(du); NR = len(s)
    r, z, h, _, _ = rc.eval_profile(fm.segs, s)
    nr, nz = np.sin(h), -np.cos(h)
    th = fm.twist(s); cb = 1 / np.sqrt(1 + (r * fm.dens(s)) ** 2); sig = 1 / (r * cb)
    zw = fm.zone_w(s) if NOTCHES else np.zeros_like(s)   # 1 in notch rows
    X = rc.core_x(A_SEAT, G_LAND, narc); cut = np.abs(X) < A_SEAT
    Dc = np.where(cut, seat_stack(X, A_SEAT, G_DEPTH), 0.0)[None, :].repeat(NR, 0)
    reff = r[:, None] + Dc * nr[:, None]
    sector = 2 * math.pi / N_W
    # notch columns: edges (+-eps) and interior, in mm from lane centre
    e = 1e-3
    nx = np.concatenate([[NOTCH_X[0] - e, NOTCH_X[0] + e], np.linspace(NOTCH_X[0], NOTCH_X[1], nnotch + 2)[1:-1],
                         [NOTCH_X[1] - e, NOTCH_X[1] + e]])
    blocks, Ds, chk = [], [], []
    for j in range(N_W):
        pc = j * sector + X[None, :] / (reff * cb[:, None])
        blocks.append(pc); Ds.append(Dc); chk.append(j * sector + X[None, :] * sig[:, None])
        eL = pc[:, -1]; eR = (j + 1) * sector + X[0] * sig
        span = eR - eL; assert np.all(span > 0)
        # target lambdas: notch rows -> notch positions; other rows -> uniform
        lam_u = (np.arange(1, len(nx) + nfill + 1) / (len(nx) + nfill + 1))[None, :].repeat(NR, 0)
        psi_n = j * sector + nx[None, :] * sig[:, None]                 # notch col positions (in notch rows)
        lam_n = (psi_n - eL[:, None]) / span[:, None]
        lam_f = np.linspace(0, 1, nfill + 2)[1:-1][None, :]
        lam_tail = lam_n[:, -1:] + lam_f * (1 - lam_n[:, -1:])
        lam_notch = np.concatenate([lam_n, lam_tail], 1)
        ok = np.all(np.diff(np.concatenate([np.zeros((NR, 1)), lam_notch, np.ones((NR, 1))], 1), axis=1) > 0, axis=1)
        wz = np.where(ok, zw, 0.0)[:, None]
        lam = wz * lam_notch + (1 - wz) * lam_u
        pf_ = eL[:, None] + lam * span[:, None]
        # depth: notch only where fully in zone (smoothly ramped)
        xcol = (pf_ - j * sector) / sig[:, None]                         # mm from lane centre
        inside = (xcol > NOTCH_X[0]) & (xcol < NOTCH_X[1])
        Dn = np.where(inside, -NOTCH_D * rc.Q((zw[:, None] - 0.5) / 0.5), 0.0)
        blocks.append(pf_); Ds.append(Dn); chk.append(pf_)
    psi = np.concatenate(blocks, 1); DD = np.concatenate(Ds, 1)
    assert np.all(np.diff(np.concatenate(chk, 1), axis=1) > 0), "column order"
    NC = psi.shape[1]
    phi = psi + th[:, None]
    rv = r[:, None] + DD * nr[:, None]; zv = z[:, None] + DD * nz[:, None]
    V = np.stack([rv * np.cos(phi), rv * np.sin(phi), zv], -1).reshape(-1, 3)
    I, J = np.meshgrid(np.arange(NR), np.arange(NC), indexing="ij"); J2 = (J + 1) % NC; I2 = (I + 1) % NR
    F = np.concatenate([np.stack([I * NC + J, I2 * NC + J, I2 * NC + J2], -1).reshape(-1, 3),
                        np.stack([I * NC + J, I2 * NC + J2, I * NC + J2], -1).reshape(-1, 3)])
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F, dict(pitch=r * sector * cb, rows=NR, cols=NC)

def wires(fm, du=0.02):
    """2 stacked circuits per section: layer 1 (bottom of slot) then layer 2 (flush)."""
    s = fm.rows(du, 0.2); r, z, h, _, _ = rc.eval_profile(fm.segs, s)
    nr, nz = np.sin(h), -np.cos(h); th = fm.twist(s)
    out = []
    for j in range(N_W):
        loops = []
        for layer in range(N_STACK):
            off = -G_DEPTH + 0.05 + WIRE_OD / 2 + layer * WIRE_OD
            rv, zv = r + off * nr, z + off * nz; ph = j * 2 * math.pi / N_W + th
            loops.append(np.stack([rv * np.cos(ph), rv * np.sin(ph), zv], -1))
        out.append(loops)
    return out, s

def hub(gallery=True):
    """Centre hub: continues the golden face to the 34 mm plateau, 16 mm bore for the
    ferrite pinpoint core.  gallery=True adds an annular lead trough (r 62-71, 5 mm
    deep) at the inner wall: leads leave the grooves at the brow straight into it."""
    zf = lambda rr: RIM_H + (R_B - rr) * T_SLOPE
    rb, rh = 8.0, R_I - 0.6
    if gallery:
        g0, g1, gd = 62.0, rh - 1.5, 5.0
        poly = [(rb, 0.0), (rh, 0.0), (rh, zf(rh)), (g1, zf(g1)), (g1, zf(g1) - gd), (g0, zf(g1) - gd),
                (g0, zf(g0)), (17.0, zf(17.0)), (rb, zf(17.0))]
    else:
        poly = [(rb, 0.0), (rh, 0.0), (rh, zf(rh)), (17.0, zf(17.0)), (rb, zf(17.0))]
    return g.revolve(poly, 720)

def main(out="out_phifold_v2", tag="A_gallery"):
    os.makedirs(out, exist_ok=True); t0 = time.time()
    fm = Former(); rep = {}
    V, F, meta = build_mesh(fm)
    gd, bad = rc.edge_manifold_check(F)
    rc.write_stl(f"{out}/PHIFOLD233v2_{tag}_golden_band_former.stl", V, F, "phifold233v2")
    rep["former"] = dict(triangles=len(F), nonmanifold_edges=bad, volume_cm3=rc.signed_volume(V, F) / 1000,
                         min_pitch_mm=float(meta["pitch"].min()), min_wall_mm=float(meta["pitch"].min() - 2 * A_SEAT),
                         rows=meta["rows"], cols=meta["cols"])
    Hv, Hf = hub(gallery=not NOTCHES); rc.write_stl(f"{out}/PHIFOLD233v2_{tag}_centre_hub.stl", Hv, Hf, "hub")
    rod = g.revolve([(0.01, 1.0), (7.9, 1.0), (7.9, 35.0), (0.01, 35.0)], 180)
    rc.write_stl(f"{out}/PHIFOLD233v2_{tag}_ferrite_pinpoint_core.stl", *rod, "ferrite")
    W, sW = wires(fm)
    tubes = [rc.tube_mesh(L[::2], WIRE_OD / 2, 8) for sec in W for L in sec]
    Vt, Ft = g.merge(tubes); rc.write_stl(f"{out}/PHIFOLD233v2_{tag}_windings_ABCD_2layer.stl", Vt, Ft, "w")
    xy = [rc.tube_mesh(P, 0.4, 6) for ax, zz in (("X", -1.2), ("Y", -2.4)) for P in pf.figure8(ax, zz)]
    skid = g.revolve([(0.01, -6.2), (R_B, -6.2), (R_B, -3.2), (0.01, -3.2)], 360)
    rc.write_stl(f"{out}/PHIFOLD233v2_{tag}_ASSEMBLY.stl", *g.merge([(V, F), (Hv, Hf), rod, (Vt, Ft), g.merge(xy), skid]), "asm")
    # bends & lengths
    Rb = []; Lw = 0
    for L in W[0]:
        a, b, c = np.roll(L, 1, 0), L, np.roll(L, -1, 0)
        ab = np.linalg.norm(b - a, axis=1); bc = np.linalg.norm(c - b, axis=1); ca = np.linalg.norm(c - a, axis=1)
        Rb.append(ab * bc * ca / np.maximum(2 * np.linalg.norm(np.cross(b - a, c - a), axis=1), 1e-15))
        Lw += np.linalg.norm(np.diff(np.vstack([L, L[:1]]), axis=0), axis=1).sum()
    Rb = np.concatenate(Rb)
    per = {n: round((fm.twist(fm.off[n] + sg.L) - fm.twist(fm.off[n])) / (2 * math.pi), 3) for n, sg in fm.segs}
    rep["winding"] = dict(turns_per_circuit=fm.turns, circuits_per_section=N_STACK, turns_per_section=fm.turns * N_STACK,
                          total_turns=4 * fm.turns * N_STACK, turns_by_segment_per_circuit=per,
                          length_per_section_m=Lw / 1000, total_length_m=4 * Lw / 1000,
                          min_bend_radius_mm=float(Rb.min()), min_bend_xOD=float(Rb.min() / WIRE_OD))
    # electromagnetics: per section = both layers in series
    gmr = 0.7788 * WIRE_OD / 2
    def sec_segs(sec, dz=0.0):
        m, d = [], []
        for L in sec:
            P = L[::3] + np.array([0, 0, dz]); mm, dd = pf.segs_closed(P); m.append(mm); d.append(dd)
        return np.concatenate(m), np.concatenate(d)
    m0, d0 = sec_segs(W[0]); mo, do = sec_segs(W[0], gmr)
    L1 = g.neumann(m0, d0, mo, do); m1, d1 = sec_segs(W[1]); M12 = g.neumann(m0, d0, m1, d1)
    mom = float(0.5 * np.cross(m0, d0)[:, 2].sum())
    Rdc = 0.0172 / 0.50 * Lw / 1000
    rep["electrical_per_section"] = dict(L_uH=L1 * 1e6, M_uH=M12 * 1e6, k=M12 / L1, R_ohm=Rdc,
                                          moment_per_amp_Am2=mom)
    Lpar = (L1 + 3 * M12) / 4; Rpar = Rdc / 4
    rep["all4_parallel"] = dict(L_uH=Lpar * 1e6, R_ohm=Rpar)
    # field per sqrt(W) on axis (parallel drive), compare with v1
    z = np.array([25, 50, 100, 150, 200, 300, 400.0]); pts = np.stack([0 * z, 0 * z, -z * 1e-3], -1)
    mm, dd = [], []
    for sec in W:
        a, b = sec_segs(sec); mm.append(a); dd.append(b)
    mm, dd = np.concatenate(mm), np.concatenate(dd)
    B4 = g.biot_savart(mm, dd, np.ones(len(mm)), pts)[:, 2]
    rep["field"] = dict(depth_mm=z.tolist(), Bz_uT_per_amp_each_section=(B4 * 1e6).tolist(),
                        B_per_sqrtW_uT=((B4 / 4) / math.sqrt(Rpar) * 1e6).tolist())
    rep["geometry"] = dict(OD=OD, R_band_inner=R_I, rim_h=RIM_H, h_inner_wall=H_IN, slope_deg=math.degrees(ALPHA),
                           groove_w=2 * A_SEAT, groove_depth=G_DEPTH, pitch=PITCH, notch_width=NOTCH_X[1] - NOTCH_X[0],
                           notch_depth=NOTCH_D, rim_zone_mm=RIM_ZONE, hub_bore_d=16.0, plateau_d=34.0)
    json.dump(rep, open(f"{out}/PHIFOLD233v2_{tag}_spec.json", "w"), indent=1, default=float)
    print(json.dumps(rep, indent=1, default=float)); print("%.1fs" % (time.time() - t0))
    return fm, rep

if __name__ == "__main__":
    import sys
    NOTCHES = (sys.argv[1] == "notches") if len(sys.argv) > 1 else False
    main(tag="B_rim_notches" if NOTCHES else "A_gallery")
