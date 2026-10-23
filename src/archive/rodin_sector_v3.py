"""PHI-FOLD 233 v3 — Sector-Rodin vortex former (experimental).
Same golden annulus as v2A.  72 Rodin lanes (5 deg), each poloidal circuit
advances 27 nodes = 135 deg as a loxodrome (dphi/ds = kappa/r), two stacked wires
per lane.  Lanes are wired in FOUR 90-degree sector coils (18 lanes each) through
a jumper ring; sector currents I_q = I0[b + cos(wt - q*pi/2)] give a smoothly
precessing ("tornado") field."""
import numpy as np, math, json, os
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g, phi_fold_former as pf
v2.NOTCHES=False
N, K = 72, 27
class RodinFormer:
    def __init__(self):
        self.segs = v2.Former().segs; self.off, self.L = rc.seg_offsets(self.segs)
        sf = np.linspace(0, self.L, 200001); r = rc.eval_profile(self.segs, sf)[0]
        I = np.concatenate([[0], np.cumsum((1/r[1:] + 1/r[:-1]) / 2 * np.diff(sf))])
        self.kap = (K * 2 * math.pi / N) / I[-1]; self.sf, self.I = sf, I
        self.k_shift = K; self.net_turns = K / N
    def twist(self, s): return self.kap * np.interp(s, self.sf, self.I)
    def dens(self, s): return self.kap / rc.eval_profile(self.segs, np.asarray(s))[0]
    def rows(self, ds_line, ds_blend):
        out = [self.off[n] + np.linspace(0, sg.L, max(3, int(math.ceil(sg.L / (ds_blend if isinstance(sg, rc.Blend) else ds_line)))), endpoint=False) for n, sg in self.segs]
        return np.unique(np.concatenate(out))
# configure the generic lane-mesh builder for 72 double-stacked lanes
g.N_WIRES, g.A_SEAT, g.G_DEPTH, g.G_LAND = N, v2.A_SEAT, v2.G_DEPTH, v2.G_LAND
fm = RodinFormer()
out = "out_phifold_v2"; rep = {}
V, F, meta = g.build_cone_mesh(fm, ds_line=0.25, ds_blend=0.12, narc=5, nfill=2)
gd, bad = rc.edge_manifold_check(F)
rc.write_stl(f"{out}/PHIFOLD233v3_sector_rodin_former.stl", V, F, "v3")
rep["former"] = dict(triangles=len(F), nonmanifold_edges=bad, volume_cm3=rc.signed_volume(V, F)/1000,
                     min_pitch_mm=float(meta["pitch"].min()), min_wall_mm=float(meta["pitch"].min() - 2*v2.A_SEAT),
                     beta_deg=math.degrees(math.atan(fm.kap)), kappa=fm.kap)
# lanes (two stacked layers) and sector coils
s = fm.rows(0.1, 0.05); r, z, h, _, _ = rc.eval_profile(fm.segs, s); nr, nz = np.sin(h), -np.cos(h); c = fm.twist(s)
def lane(n, layer):
    off = -v2.G_DEPTH + 0.05 + v2.WIRE_OD/2 + layer*v2.WIRE_OD
    ph = n*2*math.pi/N + c; rv, zv = r + off*nr, z + off*nz
    return np.stack([rv*np.cos(ph), rv*np.sin(ph), zv], -1)
lanes = {(n, L): lane(n, L) for n in range(N) for L in range(2)}
sector = {q: [n for n in range(N) if (n*5)//90 == q] for q in range(4)}
tubes = [rc.tube_mesh(P[::2], v2.WIRE_OD/2, 6) for P in lanes.values()]
Vt, Ft = g.merge(tubes); rc.write_stl(f"{out}/PHIFOLD233v3_rodin_windings_72x2.stl", Vt, Ft, "w")
Hv, Hf = v2.hub(gallery=True)
rc.write_stl(f"{out}/PHIFOLD233v3_ASSEMBLY.stl", *g.merge([(V, F), (Hv, Hf), (Vt, Ft)]), "v3asm")
# fields
def seg(Ps):
    mm, dd = [], []
    for P in Ps: m, d = pf.segs_closed(P[::2]); mm.append(m); dd.append(d)
    return np.concatenate(mm), np.concatenate(dd)
depths = np.array([100, 200, 300.0]); pts = np.stack([0*depths, 0*depths, -depths*1e-3], -1)
Bq = []; Lq = []
for q in range(4):
    m, d = seg([lanes[(n, L)] for n in sector[q] for L in range(2)])
    Bq.append(g.biot_savart(m, d, np.ones(len(m)), pts)); Lq.append(float(np.linalg.norm(d, axis=1).sum()))
Bq = np.array(Bq); Rq = 1.72e-8*Lq[0]/0.5e-6
Ball = Bq.sum(0)
rep["sector_coils"] = dict(lanes_per_sector=18, copper_per_sector_m=Lq[0], R_per_sector_ohm=Rq,
    Bxy_per_amp_uT=[float(np.hypot(Bq[0, k, 0], Bq[0, k, 1])*1e6) for k in range(3)],
    Bz_per_amp_uT=[float(Bq[0, k, 2]*1e6) for k in range(3)],
    horizontal_angle_deg_200mm=[round(math.degrees(math.atan2(Bq[q, 1, 1], Bq[q, 1, 0])), 1) for q in range(4)])
# smooth precession: I_q = I0 (b + cos(wt - q pi/2)); amplitude of rotating horizontal = 2*|Bxy_q|*I0, Bz = 4 b Bz_q I0
for b in (0.0, 0.5, 1.0):
    hz = 2*rep["sector_coils"]["Bxy_per_amp_uT"][1]; vz = 4*b*rep["sector_coils"]["Bz_per_amp_uT"][1]
    rep[f"precession_b={b}"] = dict(rotating_horizontal_uT_per_A=hz, steady_Bz_uT_per_A=vz,
                                     cone_half_angle_deg=round(math.degrees(math.atan2(hz, vz)), 1) if vz else 90.0)
# depth efficiency vs v2A, all sectors together, equal copper volume
dA = json.load(open(f"{out}/PHIFOLD233v2_A_gallery_spec.json"))
Ltot = 4*Lq[0]; Rall = 1.72e-8*Ltot/0.5e-6
eff3 = Ball[1, 2]/math.sqrt(Rall)*1e6/math.sqrt(Ltot*0.5e-6)
effA = dA["field"]["B_per_sqrtW_uT"][4]/math.sqrt(dA["winding"]["total_length_m"]*0.5e-6)
rep["Z_depth_efficiency_vs_v2A_equal_copper"] = round(eff3/effA, 3)
rep["copper_total_m"] = Ltot
# wiring map: every lane is one 135-deg circuit; its two ends land 27 nodes apart -> jumper ring
rep["wiring"] = {f"sector_{q}": [dict(lane=n, entry_deg=n*5, exit_deg=((n+K) % N)*5, rodin_digit=n % 9 + 1) for n in sector[q]] for q in range(4)}
json.dump(rep, open(f"{out}/PHIFOLD233v3_spec.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in rep.items() if k != "wiring"}, indent=1, default=float))
