#!/usr/bin/env python3
"""
PHI-FOLD 233 v3 ONE-PIECE head body.
Outer golden band + gallery ring + inner band are printed as ONE solid.
Wire path: each section crosses the wall facing the gallery ring at ONE fixed azimuth (zero-twist zone),
so the ring can be fused solid to the bands everywhere except 8 small windows (4 per band) where the wire runs.
"""
import math, json, os, time, sys
import numpy as np
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g, phi_fold_former as pf
OUT = "kit_v3"; os.makedirs(OUT, exist_ok=True)
T = v2.T_SLOPE; zf = lambda r: 13.0 + (116.5 - r) * T
t0 = time.time(); rep = {}
THETA0 = math.radians(65.0)          # body rotated so no wire window sits on the 90 deg cable path
def rotz(V, a=THETA0):
    c, s = math.cos(a), math.sin(a); V = np.asarray(V, float); return np.c_[V[:, 0] * c - V[:, 1] * s, V[:, 0] * s + V[:, 1] * c, V[:, 2]]
def build_band(R_B, R_I, RIM_H, zone, tag):
    sv = (v2.R_B, v2.R_I, v2.RIM_H, v2.H_IN, dict(v2.RHO), v2.ZONE_SEGS, v2.NOTCHES)
    v2.R_B, v2.R_I, v2.RIM_H = R_B, R_I, RIM_H; v2.H_IN = RIM_H + (R_B - R_I) * T
    v2.RHO.update(heel=5.0, crown=5.0, brow=4.0, foot=4.0); v2.NOTCHES = False; v2.ZONE_SEGS = zone
    try:
        fm = v2.Former(); V, F, meta = v2.build_mesh(fm); W, _ = v2.wires(fm)
    finally:
        v2.R_B, v2.R_I, v2.RIM_H, v2.H_IN = sv[:4]; v2.RHO.clear(); v2.RHO.update(sv[4]); v2.ZONE_SEGS, v2.NOTCHES = sv[5], sv[6]
    print(tag, "built", fm.turns, "turns  %.0fs" % (time.time() - t0), flush=True)
    return fm, V, F, meta, W
fo, Vo, Fo, mo, Wo = build_band(116.5, 72.004, 13.0, ("brow", "inner", "foot"), "outer")
fi, Vi, Fi, mi, Wi = build_band(60.4, 26.0, zf(60.4), ("heel", "rim", "crown"), "inner")
def segmid(fm, name): return fm.off[name] + dict(fm.segs)[name].L / 2
az_o = [(j * math.pi / 2 + float(fo.twist(segmid(fo, "inner"))) + THETA0) % (2 * math.pi) for j in range(4)]
az_i = [(j * math.pi / 2 + float(fi.twist(segmid(fi, "rim"))) + THETA0) % (2 * math.pi) for j in range(4)]
rep["window_azimuth_deg"] = dict(outer_band_inner_wall=[round(math.degrees(a), 2) for a in az_o], inner_band_outer_wall=[round(math.degrees(a), 2) for a in az_i])
# ---- gallery ring, fused (0.15 mm overlap into both band walls), with 8 windows
HW = 2.4                                   # window half-width (mm along the wall) -> 4.8 mm wide
R_I0, R_O0 = 60.25, 72.15
prof = [(R_I0, 0.0), (R_O0, 0.0), (R_O0, 17.0), (70.6, zf(70.6)), (70.6, zf(70.6) - 1.5), (69.6, zf(70.6) - 1.5), (69.6, zf(70.6) - 7.5),
        (63.4, zf(70.6) - 7.5), (63.4, zf(62.4) - 1.5), (62.4, zf(62.4) - 1.5), (62.4, zf(62.4)), (R_I0 + 2.15, zf(R_I0 + 2.15)), (R_I0, 17.0)]
NA = 2880; ang = np.linspace(0, 2 * np.pi, NA, endpoint=False); m = len(prof)
def near(a, centres, rad_mm, R):
    d = np.abs((a[:, None] - np.array(centres)[None, :] + np.pi) % (2 * np.pi) - np.pi).min(1); return d < HW / R
win_o = near(ang, az_o, HW, 72.0); win_i = near(ang, az_i, HW, 61.0)
Vr = []
for k, a in enumerate(ang):
    for (r_, z_) in prof:
        rr = r_
        if win_o[k] and rr > 69.6: rr = 69.6            # outer wall removed -> window onto the outer-band wire groove
        if win_i[k] and rr < 63.4: rr = 63.4            # inner wall removed -> window onto the inner-band wire groove
        Vr.append((rr * math.cos(a), rr * math.sin(a), z_))
Vr = np.array(Vr); I, J = np.meshgrid(np.arange(NA), np.arange(m), indexing="ij"); I2, J2 = (I + 1) % NA, (J + 1) % m
Fr = np.concatenate([np.stack([I * m + J, I2 * m + J, I2 * m + J2], -1).reshape(-1, 3), np.stack([I * m + J, I2 * m + J2, I * m + J2], -1).reshape(-1, 3)])
def weld_clean(V, F, tol=1e-4):
    key = np.round(V / tol).astype(np.int64); _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V2 = V[idx]; F2 = inv.reshape(-1)[F]; ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2]); F2 = F2[ok]
    a, b, c = V2[F2[:, 0]], V2[F2[:, 1]], V2[F2[:, 2]]; F2 = F2[np.linalg.norm(np.cross(b - a, c - a), axis=1) > 1e-12]
    if rc.signed_volume(V2, F2) < 0: F2 = F2[:, ::-1]
    return V2, F2
Vr, Fr = weld_clean(Vr, Fr)
shells = {"outer_band": (rotz(Vo), Fo), "gallery_ring_with_windows": (Vr, Fr), "inner_band": (rotz(Vi), Fi)}
for nm, (V, F) in shells.items():
    gd, bad = rc.edge_manifold_check(F); rep.setdefault("shells", {})[nm] = dict(triangles=int(len(F)), nonmanifold_edges=int(bad), volume_cm3=round(rc.signed_volume(V, F) / 1000, 2))
Vb, Fb = g.merge(list(shells.values()))
rc.write_stl(f"{OUT}/P10_head_body_ONE_PIECE.stl", Vb, Fb, "onepiece")
rep["body"] = dict(triangles=int(len(Fb)), bbox_mm=[round(float(x), 2) for x in (*Vb.min(0), *Vb.max(0))])
# ---- wire models + electrics
def tubes(W): return g.merge([rc.tube_mesh(rotz(q[::2]), v2.WIRE_OD / 2, 8) for sec in W for q in sec])
rc.write_stl(f"{OUT}/R10_outer_band_windings.stl", *tubes(Wo), "wo"); rc.write_stl(f"{OUT}/R11_inner_band_windings.stl", *tubes(Wi), "wi")
def sec_segs(sec, dz=0.0, step=3):
    mm, dd = [], []
    for L in sec:
        a, b = pf.segs_closed(L[::step] + np.array([0, 0, dz])); mm.append(a); dd.append(b)
    return np.concatenate(mm), np.concatenate(dd)
gmr = 0.7788 * v2.WIRE_OD / 2; el = {}; Bk = {}
dep = np.array([100, 200, 300.0]); pts = np.stack([0 * dep, 0 * dep, -dep * 1e-3], -1)
for nm, W, fm in (("outer", Wo, fo), ("inner", Wi, fi)):
    Lw = sum(np.linalg.norm(np.diff(np.vstack([q, q[:1]]), axis=0), axis=1).sum() for q in W[0])
    m0, d0 = sec_segs(W[0]); mo_, do_ = sec_segs(W[0], gmr); L1 = g.neumann(m0, d0, mo_, do_)
    m1, d1 = sec_segs(W[1]); M12 = g.neumann(m0, d0, m1, d1)
    R1 = 0.0172 / 0.50 * Lw / 1000
    mm, dd = [], []
    for sec in W: a, b = sec_segs(sec); mm.append(a); dd.append(b)
    mm, dd = np.concatenate(mm), np.concatenate(dd)
    B4 = g.biot_savart(mm, dd, np.ones(len(mm)), pts)[:, 2]
    Bk[nm] = (B4 / 4, R1 / 4)
    per = {n: round(float((fm.twist(fm.off[n] + sg.L) - fm.twist(fm.off[n])) / (2 * math.pi)), 3) for n, sg in fm.segs}
    el[nm] = dict(turns_per_circuit=fm.turns, turns_per_section=2 * fm.turns, turns_by_segment=per, wire_per_section_m=round(Lw / 1000, 2), L_section_uH=round(L1 * 1e6, 1),
                  k=round(M12 / L1, 2), R_section_ohm=round(R1, 3), all4_parallel_L_uH=round((L1 + 3 * M12) / 4 * 1e6, 1), all4_parallel_R_ohm=round(R1 / 4, 3),
                  min_pitch_mm=round(float(mo["pitch"].min() if nm == "outer" else mi["pitch"].min()), 3))
Bo, Ro = Bk["outer"]; Bi, Ri = Bk["inner"]
el["field_per_sqrtW_uT"] = dict(depth_mm=dep.tolist(), outer_only=[round(float(b / math.sqrt(Ro) * 1e6), 2) for b in Bo],
                               both_bands_optimal_split=[round(float(math.sqrt(bo ** 2 / Ro + bi ** 2 / Ri) * 1e6), 2) for bo, bi in zip(Bo, Bi)],
                               inner_current_ratio_200mm=round(float((Bi[1] / Ri) / (Bo[1] / Ro)), 3))
rep["electrical"] = el; rep["time_s"] = round(time.time() - t0, 1)
json.dump(rep, open(f"{OUT}/onepiece_report.json", "w"), indent=1, default=float)
print(json.dumps(rep, indent=1, default=float))
