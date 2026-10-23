#!/usr/bin/env python3
"""
phi_fold_former.py — "PHI-FOLD 233" grooved coil former, 9.17 in
==================================================================
Shallow golden cone, base toward the ground.  Four interleaved Litz windings
(sections A-D, 90 deg apart) follow a FOLDED path:
   face spiral IN (up the 13.28 deg golden slope) -> plateau -> down the
   ferrite-cored bore -> underside spiral OUT -> up the rim -> next circuit.
d(phi)/ds > 0 on every segment, so every turn on both layers circulates the
same way and ADDS to the axial field; the body separates the two layers, so
there are no crossovers.  Pitch is held at the minimum groove+wall pitch
everywhere (maximum copper).  A flat X/Y figure-8 quadrature layer under the
base supplies the rotating (precessing, "tornado") field component.

Golden / Fibonacci dimensions (mm):
  OD 233 (F13)  plateau 34 (F9)  OD/plateau = 6.853 ~ phi^4
  slope tan(alpha) = phi^-3 -> alpha = 13.2825 deg, rise = 99.5/phi^3 = 23.489
  rim 8 (F6) -> total height 31.489 (1.240 in)   bore 13 (F7)
"""
import math, json, os, time
import numpy as np
import rodin_core_v4 as rc
import golden_cone_head as g

PHI = (1 + 5 ** .5) / 2
OD, D_PLAT, RIM_H, D_BORE = 233.0, 34.0, 8.0, 13.0
R_B, R_T, R_BORE = OD / 2, D_PLAT / 2, D_BORE / 2
T_SLOPE = PHI ** -3
ALPHA = math.atan(T_SLOPE)
RISE = (R_B - R_T) * T_SLOPE
H_TOT = RIM_H + RISE

N_W = 4                                     # sections A, B, C, D
WIRE_OD = 1.20                              # finished Litz OD (measure & set!)
A_SEAT = WIRE_OD / 2 + 0.05                 # 0.65 -> groove 1.30 wide
G_DEPTH = WIRE_OD                           # flush
G_LAND = 0.25
PITCH = 2 * A_SEAT + 2 * G_LAND + 0.05      # 1.85 mm min perpendicular pitch
# convex corner blends (min radius), CCW from bottom: bottom->rim, rim->slope, slope->plateau, plateau->bore, bore->bottom
RHO = dict(heel=3.0, crown=3.0, brow=5.0, lip=2.0, foot=2.0)

def build_profile():
    u = lambda h: np.array([math.cos(h), math.sin(h)])
    V = [np.array([R_BORE, 0.0]), np.array([R_B, 0.0]), np.array([R_B, RIM_H]),
         np.array([R_T, H_TOT]), np.array([R_BORE, H_TOT])]
    hd = [0.0, math.pi / 2, math.pi - ALPHA, math.pi, 1.5 * math.pi]     # headings of edges V_i -> V_i+1
    names = ["bottom", "rim", "slope", "plateau", "bore"]
    cn = ["heel", "crown", "brow", "lip", "foot"]                         # corner at end of each edge
    corners = []
    for i in range(5):
        ha, hb = hd[i], hd[(i + 1) % 5] + (2 * math.pi if i == 4 else 0)
        dturn = (hb - ha) % (2 * math.pi)
        L = dturn * RHO[cn[i]] / (1 - rc.BLEND_F)
        ch, _ = rc.Blend.unit_chord(ha, dturn); ch *= L
        sv = u(ha) + u(hb); d = ch.dot(sv) / sv.dot(sv)
        corners.append((dturn, L, d))
    segs = []
    for i in range(5):
        A, Bv = V[i], V[(i + 1) % 5]
        da = corners[i - 1][2]; db = corners[i][2]
        L = np.linalg.norm(Bv - A) - da - db
        assert L > 0, names[i]
        segs.append((names[i], rc.Line(A + da * u(hd[i]), hd[i], L)))
        dturn, Lb, d = corners[i]
        segs.append((cn[i], rc.Blend(Bv - d * u(hd[i]), hd[i], dturn, Lb)))
    return segs

class Former:
    def __init__(self):
        self.segs = build_profile()
        self.off, self.L = rc.seg_offsets(self.segs)
        sf = np.linspace(0, self.L, 400001)
        r = rc.eval_profile(self.segs, sf)[0]
        # maximum-density twist: perpendicular pitch exactly PITCH everywhere
        sector = 2 * math.pi / N_W
        x = (r * sector / PITCH) ** 2 - 1
        assert np.all(x > 0), "radius too small for pitch"
        gg = np.sqrt(x) / r
        c = np.concatenate([[0], np.cumsum((gg[1:] + gg[:-1]) / 2 * np.diff(sf))])
        # closure: each lane must close on itself -> total twist = integer turns.  Round DOWN (keeps pitch >= PITCH)
        turns = math.floor(c[-1] / (2 * math.pi))
        scale = turns * 2 * math.pi / c[-1]
        self.sf, self.g, self.c = sf, gg * scale, c * scale
        self.turns = turns
        self.k_shift = turns * N_W            # lanes advanced = full turns * lanes

    def twist(self, s): return np.interp(s, self.sf, self.c)
    def dens(self, s): return np.interp(s, self.sf, self.g)

    def rows(self, du=0.035, ds_max=0.25):
        """rows uniform in twist (du rad) so every quad spans <= du of azimuth."""
        u = np.arange(0, self.c[-1], du)
        s_u = np.interp(u, self.c, self.sf)
        s_lin = np.arange(0, self.L, ds_max)
        s = np.unique(np.concatenate([s_u, s_lin]))
        # add blend boundaries
        return s

def build_mesh(fm, du=0.035, narc=9, nfill=4):
    s = fm.rows(du); NR = len(s)
    r, z, h, k, _ = rc.eval_profile(fm.segs, s)
    nr, nz = np.sin(h), -np.cos(h)
    th = fm.twist(s)
    cb = 1 / np.sqrt(1 + (r * fm.dens(s)) ** 2)
    sig = 1 / (r * cb)
    X = rc.core_x(A_SEAT, G_LAND, narc)
    cut = np.abs(X) < A_SEAT
    D = np.where(cut, rc.seat(X, A_SEAT, -G_DEPTH), 0.0)[None, :].repeat(NR, 0)
    reff = r[:, None] + D * nr[:, None]
    sector = 2 * math.pi / N_W
    blocks, Ds = [], []
    for j in range(N_W):
        blocks.append(j * sector + X[None, :] / (reff * cb[:, None])); Ds.append(D)
        eL = j * sector + X[-1] * sig; eR = (j + 1) * sector + X[0] * sig
        assert np.all(eR > eL), "lanes overlap"
        lam = (np.arange(1, nfill + 1) / (nfill + 1))[None, :]
        f = eL[:, None] + lam * (eR - eL)[:, None]
        blocks.append(f); Ds.append(np.zeros_like(f))
    psi = np.concatenate(blocks, 1); DD = np.concatenate(Ds, 1)
    NC = psi.shape[1]; cpl = NC // N_W
    phi = psi + th[:, None]
    rv = r[:, None] + DD * nr[:, None]; zv = z[:, None] + DD * nz[:, None]
    V = np.stack([rv * np.cos(phi), rv * np.sin(phi), zv], -1).reshape(-1, 3)
    I, J = np.meshgrid(np.arange(NR), np.arange(NC), indexing="ij")
    J2 = (J + 1) % NC; I2 = (I + 1) % NR
    sh = fm.k_shift * cpl
    Jw = np.where(I == NR - 1, (J + sh) % NC, J); Jw2 = np.where(I == NR - 1, (J2 + sh) % NC, J2)
    v00 = I * NC + J; v01 = I * NC + J2; v10 = I2 * NC + Jw; v11 = I2 * NC + Jw2
    F = np.concatenate([np.stack([v00, v10, v11], -1).reshape(-1, 3), np.stack([v00, v11, v01], -1).reshape(-1, 3)])
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F, dict(pitch=r * sector * cb, rows=NR, cols=NC)

def wires(fm, du=0.02):
    s = fm.rows(du, 0.2)
    r, z, h, _, _ = rc.eval_profile(fm.segs, s)
    nr, nz = np.sin(h), -np.cos(h)
    off = -G_DEPTH + WIRE_OD / 2
    rv, zv = r + off * nr, z + off * nz
    th = fm.twist(s)
    W = []
    for j in range(N_W):
        ph = j * 2 * math.pi / N_W + th
        W.append(np.stack([rv * np.cos(ph), rv * np.sin(ph), zv], -1))
    return W, s

# ---------------- X/Y figure-8 quadrature layer (flat, under the base) ----------------
XY_Z = (-1.2, -2.4)         # board layers (X on upper, Y on lower), mm below base
XY_TURNS, XY_PITCH, XY_RMAX, XY_GAP = 18, 2.4, 112.0, 6.0
def d_lobe(sign, k):
    """k-th concentric D-shaped loop of one lobe (half-disc x>0 if sign=+1), CCW for sign>0."""
    inset = k * XY_PITCH
    R = XY_RMAX - inset; xg = XY_GAP / 2 + inset
    if R - xg < 4: return None
    a0 = math.acos(xg / R)
    a = np.linspace(-(math.pi / 2 - (math.pi/2 - a0)), 0, 2)
    arc = np.linspace(-a0 + 0, a0, 1)  # placeholder
    th = np.linspace(-math.asin(min(1, math.sqrt(R*R - xg*xg) / R)), math.asin(min(1, math.sqrt(R*R - xg*xg) / R)), 200)
    y_max = math.sqrt(R * R - xg * xg)
    arcp = np.stack([np.sqrt(np.maximum(R * R - (y := np.linspace(-y_max, y_max, 240)) ** 2, 0)), y], -1)
    arcp[:, 0] = np.maximum(arcp[:, 0], xg)
    chord = np.stack([np.full(60, xg), np.linspace(y_max, -y_max, 60)], -1)
    P = np.concatenate([arcp, chord])            # CCW for x>0 lobe
    # remove duplicate / near-duplicate consecutive points (arc end == chord start, etc.)
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-6]
    P = P[keep]
    if np.linalg.norm(P[0] - P[-1]) < 1e-6: P = P[:-1]
    if sign < 0: P = P * np.array([-1, 1])       # mirror -> lobe at x<0, now CW
    return P

def figure8(axis="X", z=XY_Z[0]):
    """Two lobes with opposite circulation -> horizontal field on axis below centre."""
    loops = []
    for k in range(XY_TURNS):
        for sgn in (+1, -1):
            P = d_lobe(sgn, k)
            if P is None: continue
            P3 = np.c_[P, np.full(len(P), z)]
            if axis == "Y": P3 = P3 @ np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]).T
            loops.append(P3)
    return loops

def segs_closed(P):
    Q2 = np.roll(P, -1, 0); return (P + Q2) / 2 * 1e-3, (Q2 - P) * 1e-3

def main(out="out_phifold"):
    os.makedirs(out, exist_ok=True)
    fm = Former(); rep = {}
    V, F, meta = build_mesh(fm)
    good, bad = rc.edge_manifold_check(F)
    rc.write_stl(f"{out}/PHIFOLD233_grooved_former.stl", V, F, "phifold233")
    rep["former"] = dict(triangles=len(F), nonmanifold_edges=bad, volume_cm3=rc.signed_volume(V, F) / 1000,
                         min_pitch_mm=float(meta["pitch"].min()), min_wall_mm=float(meta["pitch"].min() - 2 * A_SEAT),
                         rows=meta["rows"], cols=meta["cols"])
    W, sW = wires(fm)
    # bend radius & lengths
    Rb = []
    for P in W:
        a, b, c = np.roll(P, 1, 0), P, np.roll(P, -1, 0)
        ab = np.linalg.norm(b - a, axis=1); bc = np.linalg.norm(c - b, axis=1); ca = np.linalg.norm(c - a, axis=1)
        Rb.append(ab * bc * ca / np.maximum(2 * np.linalg.norm(np.cross(b - a, c - a), axis=1), 1e-15))
    Rb = np.concatenate(Rb)
    Lw = float(np.linalg.norm(np.diff(np.vstack([W[0], W[0][:1]]), axis=0), axis=1).sum())
    per = {}
    for n, sg in fm.segs:
        o = fm.off[n]; per[n] = round((fm.twist(o + sg.L) - fm.twist(o)) / (2 * math.pi), 3)
    rep["winding"] = dict(turns_per_section_winding=fm.turns, turns_by_segment=per, total_turns_all=4 * fm.turns,
                          length_per_winding_m=Lw / 1000, total_length_m=4 * Lw / 1000,
                          min_bend_radius_mm=float(Rb.min()), min_bend_xOD=float(Rb.min() / WIRE_OD))
    # tubes
    tubes = [rc.tube_mesh(P[::2], WIRE_OD / 2, 8) for P in W]
    Vt, Ft = g.merge(tubes); rc.write_stl(f"{out}/PHIFOLD233_litz_windings_ABCD.stl", Vt, Ft, "windings")
    # ferrite core rod (pinpoint/flux concentrator), clears flush wires in bore
    rod = g.revolve([(0.01, -2.0), (R_BORE - 0.15, -2.0), (R_BORE - 0.15, H_TOT - 2.0), (0.01, H_TOT - 2.0)], 180)
    rc.write_stl(f"{out}/PHIFOLD233_ferrite_core_rod.stl", *rod, "ferrite_rod")
    # X/Y figure-8 layers as wire tubes + carrier board
    xy = []
    for ax, zz in (("X", XY_Z[0]), ("Y", XY_Z[1])):
        for P in figure8(ax, zz):
            xy.append(rc.tube_mesh(P, 0.4, 6))
    rc.write_stl(f"{out}/PHIFOLD233_XY_quadrature_layer.stl", *g.merge(xy), "xy")
    board = g.revolve([(R_BORE + 0.5, -3.2), (R_B - 1.0, -3.2), (R_B - 1.0, -0.4), (R_BORE + 0.5, -0.4)], 360)
    skid = g.revolve([(0.01, -6.2), (R_B, -6.2), (R_B, -3.2), (0.01, -3.2)], 360)
    rc.write_stl(f"{out}/PHIFOLD233_skid_plate.stl", *skid, "skid")
    # assembly
    VA, FA = g.merge([(V, F), (Vt, Ft), rod, g.merge(xy), skid])
    rc.write_stl(f"{out}/PHIFOLD233_ASSEMBLY.stl", VA, FA, "assembly")
    # ---------- electromagnetics ----------
    gmr = 0.7788 * WIRE_OD / 2
    m0, d0 = segs_closed(W[0][::3])
    # self inductance via offset copy along surface normal
    s3 = sW[::3]; r3, z3, h3, _, _ = rc.eval_profile(fm.segs, s3)
    ph = np.arctan2(W[0][::3, 1], W[0][::3, 0])
    off = np.stack([np.sin(h3) * np.cos(ph), np.sin(h3) * np.sin(ph), -np.cos(h3)], -1) * gmr
    mo, do = segs_closed(W[0][::3] + off)
    L1 = g.neumann(m0, d0, mo, do)
    m1, d1 = segs_closed(W[1][::3]); M12 = g.neumann(m0, d0, m1, d1)
    mom = float(0.5 * np.cross(m0, d0)[:, 2].sum())
    Rdc = 0.0172 / 0.50 * Lw / 1000            # ~0.50 mm^2 copper (e.g. 100/40 or 105/40 served Litz)
    rep["electrical_per_section"] = dict(L_uH=L1 * 1e6, M_between_sections_uH=M12 * 1e6, k=M12 / L1,
                                          R_dc_ohm=Rdc, tau_us=L1 / Rdc * 1e6, moment_per_amp_Am2=mom)
    Lpar = (L1 + 3 * M12) / 4; Lser = 4 * L1 + 12 * M12
    rep["drive_options"] = dict(all4_parallel_L_uH=Lpar * 1e6, all4_parallel_R_ohm=Rdc / 4,
                                all4_series_L_uH=Lser * 1e6, all4_series_R_ohm=4 * Rdc,
                                total_moment_per_amp_each_section_Am2=4 * mom)
    # fields at depth: Z (all 4 sections 1 A) vs X figure-8 (1 A), and flat-spiral reference with equal copper
    depths = np.array([25, 50, 100, 150, 200, 300.0])
    pts = np.stack([np.zeros_like(depths), np.zeros_like(depths), -depths], -1) * 1e-3
    mids, dls = [], []
    for P in W:
        m, d = segs_closed(P[::3]); mids.append(m); dls.append(d)
    mids, dls = np.concatenate(mids), np.concatenate(dls)
    Bz = g.biot_savart(mids, dls, np.ones(len(mids)), pts)
    xm, xd = [], []
    for P in figure8("X"): m, d = segs_closed(P); xm.append(m); xd.append(d)
    xm, xd = np.concatenate(xm), np.concatenate(xd)
    Bx = g.biot_savart(xm, xd, np.ones(len(xm)), pts)
    Lx = float(np.linalg.norm(xd, axis=1).sum())
    # flat pancake reference with the same copper length as all four windings
    Ltot = 4 * Lw / 1000
    rr = np.arange(R_T, R_B, PITCH / 4)          # same 4-wire packing in one plane
    rr = rr[np.cumsum(2 * np.pi * rr / 1000) <= Ltot]
    Bflat = np.array([sum(4e-7 * math.pi * (a * 1e-3) ** 2 / (2 * ((a * 1e-3) ** 2 + (d * 1e-3) ** 2) ** 1.5) for a in rr) for d in depths])
    Ltot_flat = float((2 * np.pi * rr).sum() / 1000)
    rep["fields_uT_per_amp"] = dict(depth_mm_below_base=depths.tolist(),
        Z_all4_sections_Bz=(Bz[:, 2] * 1e6).tolist(),
        flat_pancake_same_copper_Bz=(Bflat * 1e6).tolist(),
        flat_pancake_turns=int(len(rr)), flat_pancake_copper_m=Ltot_flat,
        X_figure8_Bx=(Bx[:, 0] * 1e6).tolist(), X_copper_m=Lx)
    # precession ("tornado") cone half-angle when X,Y driven in quadrature with I_xy and Z with I_z
    Ixy_over_Iz = 3.0
    ang = np.degrees(np.arctan2(np.abs(Bx[:, 0]) * Ixy_over_Iz, np.abs(Bz[:, 2])))
    rep["precession"] = dict(I_xy_over_I_z=Ixy_over_Iz, cone_half_angle_deg=ang.tolist())
    rep["geometry"] = dict(OD=OD, OD_in=OD / 25.4, plateau_d=D_PLAT, bore_d=D_BORE, rim_h=RIM_H, rise=RISE,
                           total_h=H_TOT, total_h_in=H_TOT / 25.4, slope_deg=math.degrees(ALPHA), tan_slope=T_SLOPE,
                           slant_length=(R_B - R_T) / math.cos(ALPHA), OD_over_plateau=OD / D_PLAT, phi4=PHI ** 4,
                           corner_rho=RHO, groove_w=2 * A_SEAT, groove_depth=G_DEPTH, pitch=PITCH, wire_od=WIRE_OD,
                           profile_perimeter=fm.L)
    json.dump(rep, open(f"{out}/PHIFOLD233_spec.json", "w"), indent=1, default=float)
    return fm, rep

if __name__ == "__main__":
    t0 = time.time(); fm, rep = main()
    print(json.dumps(rep, indent=1, default=float)); print("%.1fs" % (time.time() - t0))
