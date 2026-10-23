#!/usr/bin/env python3
"""
PHI-FOLD 233 v2C-FINAL  --  complete printable kit (all parts in ONE shared assembly frame)
Frame: z = 0 is the flat ground-facing underside of the coil formers, axis = z, +z = toward the handle.
"""
import math, json, os, shutil
import numpy as np
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g, phi_fold_former as pf
from struct import unpack
K = "kit"; P_DIR = f"{K}/01_PRINTABLE_head"; R_DIR = f"{K}/02_PURCHASED_reference_models"; H_DIR = f"{K}/04_handle_envelope_models"
for d in (P_DIR, R_DIR, H_DIR, f"{K}/05_assembly"): os.makedirs(d, exist_ok=True)
T = v2.T_SLOPE; R_B, WIRE = v2.R_B, v2.WIRE_OD
zf = lambda r: 13.0 + (R_B - r) * T                           # golden face height (13 mm rim + slope)
report = {"parts": {}}

def read_stl(p):
    with open(p, "rb") as f:
        f.read(80); n = unpack("<I", f.read(4))[0]
        d = np.frombuffer(f.read(50 * n), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    V = d["v"].reshape(-1, 3).astype(float); return V, np.arange(len(V)).reshape(-1, 3)
def weld_clean(V, F, tol=1e-4):
    key = np.round(V / tol).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V2 = V[idx]; F2 = inv.reshape(-1)[F]
    ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    F2 = F2[ok]
    a, b, c = V2[F2[:, 0]], V2[F2[:, 1]], V2[F2[:, 2]]
    F2 = F2[np.linalg.norm(np.cross(b - a, c - a), axis=1) > 1e-12]
    return V2, F2
def emit(name, VF, folder=P_DIR, note=""):
    V, F = VF
    V, F = weld_clean(V, F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    good, bad = rc.edge_manifold_check(F)
    rc.write_stl(f"{folder}/{name}.stl", V, F, name)
    bb0, bb1 = V.min(0), V.max(0)
    report["parts"][name] = dict(triangles=int(len(F)), nonmanifold_edges=int(bad), volume_cm3=round(rc.signed_volume(V, F) / 1000, 2),
                                 bbox_mm=[round(float(x), 2) for x in (*bb0, *bb1)], note=note)
    return V, F
rev = lambda poly, n=720: g.revolve(poly, n)

# ---------------------------------------------------------------- P1 outer golden-band former (v2A, built earlier)
Vo, Fo = read_stl("out_phifold_v2/PHIFOLD233v2_A_gallery_golden_band_former.stl")
emit("P01_outer_golden_band_former", (Vo, Fo), note="r 72.004-116.5, 4 sections x 2 stacked circuits x 16 turns; print base-down")
# ---------------------------------------------------------------- P2 inner TX band former (26.0 - 60.4)
sv = (v2.R_B, v2.R_I, v2.RIM_H, v2.H_IN, dict(v2.RHO))
v2.R_B, v2.R_I, v2.RIM_H = 60.4, 26.0, zf(60.4); v2.H_IN = v2.RIM_H + (v2.R_B - v2.R_I) * T
v2.RHO.update(heel=5.0, crown=5.0, brow=4.0, foot=4.0); v2.NOTCHES = False
fm_in = v2.Former(); Vi, Fi, meta_i = v2.build_mesh(fm_in); W_in, s_in = v2.wires(fm_in)
brow_in = fm_in.off["brow"] + dict(fm_in.segs)["brow"].L / 2; th_in = float(fm_in.twist(brow_in))
turns_in = dict(circuit=fm_in.turns, per_segment={n: round(float((fm_in.twist(fm_in.off[n] + sg.L) - fm_in.twist(fm_in.off[n])) / (2 * math.pi)), 3) for n, sg in fm_in.segs})
Lw_in = sum(np.linalg.norm(np.diff(np.vstack([q, q[:1]]), axis=0), axis=1).sum() for q in W_in[0])
v2.R_B, v2.R_I, v2.RIM_H, v2.H_IN = sv[:4]; v2.RHO.clear(); v2.RHO.update(sv[4])
emit("P02_inner_TX_band_former", (Vi, Fi), note="r 26.0-60.4, 4 sections x 2 circuits x %d turns; print base-down" % fm_in.turns)
# outer-band data
fm_o = v2.Former(); W_o, s_o = v2.wires(fm_o)
brow_o = fm_o.off["brow"] + dict(fm_o.segs)["brow"].L / 2; th_o = float(fm_o.twist(brow_o))
turns_o = dict(circuit=fm_o.turns, per_segment={n: round(float((fm_o.twist(fm_o.off[n] + sg.L) - fm_o.twist(fm_o.off[n])) / (2 * math.pi)), 3) for n, sg in fm_o.segs})
Lw_o = sum(np.linalg.norm(np.diff(np.vstack([q, q[:1]]), axis=0), axis=1).sum() for q in W_o[0])
# ---------------------------------------------------------------- P3 gallery ring (lead trough) + P4 trough lid
zr = zf
ring = [(61.0, 0), (71.6, 0), (71.6, zr(71.6)), (70.6, zr(70.6)), (70.6, zr(70.6) - 1.5), (69.6, zr(70.6) - 1.5), (69.6, zr(70.6) - 7.5),
        (63.4, zr(70.6) - 7.5), (63.4, zr(62.4) - 1.5), (62.4, zr(62.4) - 1.5), (62.4, zr(62.4)), (61.0, zr(61.0))]
emit("P03_gallery_ring_lead_trough", rev(ring), note="plain ring r 61.0-71.6 joins the two bands; trough r 63.4-69.6, 7.5 mm deep holds all 16 outer-band leads")
lid = [(62.5, zr(62.4) - 1.5), (70.5, zr(70.6) - 1.5), (70.5, zr(70.6)), (62.5, zr(62.4))]
emit("P04_gallery_trough_lid", rev(lid), note="snap/epoxy lid, 8 mm x 1.5 mm, follows the 13.28 deg face")
# ---------------------------------------------------------------- P5 bay lid + yoke
ZL0, ZL1 = 35.6, 38.6
lidp = [(0.01, 33.6), (24.8, 33.6), (24.8, ZL0), (33.0, ZL0), (33.0, zf(33.0)), (36.5, zf(36.5)), (36.5, ZL1), (0.01, ZL1)]
VL, FL = rev(lidp)
def box(cx, cy, cz, lx, ly, lz):
    x = np.array([-1, 1]) * lx / 2; y = np.array([-1, 1]) * ly / 2; z = np.array([-1, 1]) * lz / 2
    V = np.array([[a, b, c] for a in x for b in y for c in z]) + [cx, cy, cz]
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
ears = [box(0, s * 21.0, ZL1 + 13.0 - 0.5, 30, 6, 27) for s in (-1, 1)]
rib = box(0, 0, ZL1 + 3.0, 30, 48, 6)                                   # base web joining the ears
VY, FY = g.merge([(VL, FL), rib] + ears)
emit("P05_bay_lid_with_yoke", (VY, FY), note="plug r 24.8 into ferrite tube; seat r 33-36.5 on face; yoke ears 6 mm, 36 mm clear span, pivot hole centre z=50 (drill 8.1 mm)")
# ---------------------------------------------------------------- P6 PCB liner sleeve (2 board slots)
Z0, Z1 = 1.0, 33.4
V6, F6 = rev([(20.7, Z0), (21.9, Z0), (21.9, Z1), (20.7, Z1)], 360)
emit("P06_pcb_liner_sleeve", (V6, F6), note="OD 43.8 / ID 41.4, slides in the ferrite tube; slot rings below")
slots = []
for zc in (10.0, 20.0):
    slots.append(rev([(19.6, zc - 0.9), (20.75, zc - 0.9), (20.75, zc + 0.9), (19.6, zc + 0.9)], 360))
emit("P07_pcb_slot_rings_x2", g.merge(slots), note="two 1.8 mm thick rings (z=10,20) glued inside the liner; hold the two Ø40 electronics boards")
# ---------------------------------------------------------------- P8 bezel ring, P9 skid plate with snap arms
BZ0, BZ1 = -3.0, 13.0
bz = [(117.0, BZ0), (121.0, BZ0), (121.0, BZ1), (117.0, BZ1)]
Vb, Fb = rev(bz, 720)
# six pockets on the outer wall (8 mm wide, 1.6 deep, z 8.5-11.5) are cut by building the ring from angular segments
def bezel_with_pockets():
    n = 720; a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pk_c = np.radians([0, 60, 120, 180, 240, 300]); hw = 4.0 / 121.0
    d = np.abs((a[:, None] - pk_c[None, :] + np.pi) % (2 * np.pi) - np.pi).min(1)
    inside = d < hw
    def prof(P): return [(117.0, BZ0), (121.0, BZ0), (121.0, 8.5), (P, 8.5), (P, 11.5), (121.0, 11.5), (121.0, BZ1), (117.0, BZ1)]
    m = 8; V = []
    for i, ang in enumerate(a):
        for (r_, z_) in prof(119.4 if inside[i] else 121.0): V.append((r_ * math.cos(ang), r_ * math.sin(ang), z_))
    V = np.array(V); I, J = np.meshgrid(np.arange(n), np.arange(m), indexing="ij"); I2, J2 = (I + 1) % n, (J + 1) % m
    F = np.concatenate([np.stack([I * m + J, I2 * m + J, I2 * m + J2], -1).reshape(-1, 3), np.stack([I * m + J, I2 * m + J2, I * m + J2], -1).reshape(-1, 3)])
    return V, F
Vb, Fb = bezel_with_pockets()
emit("P08_bezel_rim_guard", (Vb, Fb), note="r 117-121, z -3..13; epoxy to former rim (0.5 mm gap); 6 snap pockets at 0/60/..300 deg")
skid_body = rev([(0.01, -6.0), (123.0, -6.0), (123.0, -3.0), (0.01, -3.0)], 720)
arms = []
for ang in np.radians([0, 60, 120, 180, 240, 300]):
    a_ = np.array([[1.4, -4.0], [1.4, 11.4], [0.0, 11.4], [0.0, 10.2], [0.4, 10.2], [0.4, -4.0]])         # (radial offset from 121.4, z)  tooth points inward
    pts = []
    for hw in (-3.9, 3.9):
        for (dr, zz) in a_: pts.append((121.5 + dr - 1.1 * (dr < 0.2 and zz > 10) , hw, zz))
    # build as extruded polygon in (r,z) with width 8 mm along tangent
    poly = np.array([(121.5, -3.0), (122.9, -3.0), (122.9, 11.4), (120.2, 11.4), (120.2, 10.0), (121.5, 10.0)])
    n = len(poly); w = 8.0
    V = np.concatenate([np.c_[poly[:, 0], np.full(n, -w / 2), poly[:, 1]], np.c_[poly[:, 0], np.full(n, w / 2), poly[:, 1]]])
    F = []
    for i in range(1, n - 1): F += [[0, i, i + 1], [n, n + i + 1, n + i]]
    for i in range(n): j = (i + 1) % n; F += [[i, n + i, n + j], [i, n + j, j]]
    F = np.array(F); c, s_ = math.cos(ang), math.sin(ang)
    V = V @ np.array([[c, s_, 0], [-s_, c, 0], [0, 0, 1]]) .T if False else np.c_[V[:, 0] * c - V[:, 1] * s_, V[:, 0] * s_ + V[:, 1] * c, V[:, 2]]
    arms.append((V, F if rc.signed_volume(V, F) > 0 else F[:, ::-1]))
emit("P09_skid_plate_with_snap_arms", g.merge([skid_body] + arms), note="Ø246 x 3 mm wear plate, 6 flexure arms (1.4 x 8 mm) click into bezel pockets; VHB tape on the board side")
# ---------------------------------------------------------------- reference (purchased) parts
emit("R01_ferrite_tube_OD50_ID44_L33", rev([(22.0, 0.5), (25.0, 0.5), (25.0, 33.5), (22.0, 33.5)], 360), R_DIR, "MnZn, mu_r >= 2000, loss ~0 in 5-300 us window")
emit("R02_ferrite_cap_bottom_disc_OD44_t3", rev([(4.0, 0.5), (22.0, 0.5), (22.0, 3.5), (4.0, 3.5)], 360), R_DIR)
emit("R03_ferrite_cap_top_disc_OD44_t3", rev([(4.0, 30.5), (22.0, 30.5), (22.0, 33.5), (4.0, 33.5)], 360), R_DIR)
pcbs = [rev([(4.5, z0), (20.0, z0), (20.0, z0 + 1.6), (4.5, z0 + 1.6)], 180) for z0 in (9.2, 19.2)]
emit("R04_electronics_boards_x2_OD40", g.merge(pcbs), R_DIR, "main board (z=9.2) + analog/ADC board (z=19.2)")
Vs, Fs = read_stl("out_board/PF233-SB1_board_ASSEMBLY.stl")
emit("R05_PF233-SB1_sensor_board_with_copper", (Vs, Fs), R_DIR, "8-layer board model (order from Gerbers in 03_PCB)")
Vw1 = g.merge([rc.tube_mesh(q[::2], WIRE / 2, 8) for sec in W_o for q in sec])
emit("R06_outer_band_Litz_windings_ABCD", Vw1, R_DIR, "wire-path model (8 circuits)")
Vw2 = g.merge([rc.tube_mesh(q[::2], WIRE / 2, 8) for sec in W_in for q in sec])
emit("R07_inner_band_Litz_windings_ABCD", Vw2, R_DIR, "wire-path model (8 circuits)")

# ---------------------------------------------------------------- electrical numbers from the real paths
def sec_segs(sec, dz=0.0, step=3):
    m, d = [], []
    for L in sec:
        mm, dd = pf.segs_closed(L[::step] + np.array([0, 0, dz])); m.append(mm); d.append(dd)
    return np.concatenate(m), np.concatenate(d)
gmr = 0.7788 * WIRE / 2; elec = {}
for nm, W, Lw in (("outer", W_o, Lw_o), ("inner", W_in, Lw_in)):
    m0, d0 = sec_segs(W[0]); mo, do = sec_segs(W[0], gmr); L1 = g.neumann(m0, d0, mo, do)
    m1, d1 = sec_segs(W[1]); M12 = g.neumann(m0, d0, m1, d1)
    R1 = 0.0172 / 0.50 * Lw / 1000
    elec[nm] = dict(L_section_uH=round(L1 * 1e6, 1), M_uH=round(M12 * 1e6, 1), k=round(M12 / L1, 2), R_section_ohm=round(R1, 3),
                    wire_per_section_m=round(Lw / 1000, 2), all4_parallel_L_uH=round((L1 + 3 * M12) / 4 * 1e6, 1), all4_parallel_R_ohm=round(R1 / 4, 3))
# ---------------------------------------------------------------- lane azimuths at the brow (lead exit points)
lead = {}
for nm, th in (("outer_band", th_o), ("inner_band", th_in)):
    lead[nm] = {c: round(math.degrees(j * math.pi / 2 + th) % 360, 2) for j, c in enumerate("ABCD")}
report["electrical"] = elec; report["lead_exit_azimuth_deg_at_brow"] = lead
report["turns"] = dict(outer=turns_o, inner=turns_in, outer_circuit_turns=turns_o["circuit"], inner_circuit_turns=turns_in["circuit"])
report["wire"] = dict(litz="1.20 mm OD finished, ~0.50 mm2 Cu (e.g. 100/38 served)", outer_per_section_m=elec["outer"]["wire_per_section_m"],
                      inner_per_section_m=elec["inner"]["wire_per_section_m"],
                      total_with_0p35m_leads_per_section_m=round(elec["outer"]["wire_per_section_m"] + elec["inner"]["wire_per_section_m"] + 0.7, 1))
json.dump(report, open(f"{K}/BUILD_DATA.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in report.items() if k != "parts"}, indent=1, default=float))
print({k: (v["triangles"], v["nonmanifold_edges"], v["bbox_mm"]) for k, v in report["parts"].items()})
