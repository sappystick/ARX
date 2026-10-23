#!/usr/bin/env python3
"""PHI-FOLD 233 v9: six petal cassettes slide over the central PCB hub. Each has ONE key tooth for its numbered blind track, short radial lead grooves aligned to closed wire lanes in the hub wall, k dimples = layer number."""
import math, json, os, sys, pickle, numpy as np
from scipy.spatial import cKDTree
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
LOD = sys.argv[1] if len(sys.argv) > 1 else "low"
OUT = "kit_v10/PRINT" if LOD == "print" else "kit_v10/LOW"; os.makedirs(OUT, exist_ok=True)
NPHI, NR = (1200, 150) if LOD == "print" else (540, 70)
R_RIM, MARGIN, M_PET, A_RIP, N_ARM, GOLD = 116.5, 4.5, 12, 2.4, 8, 137.50776405
D_DOME, PN, ZRX, HMAX, RELIEF, G = 10.0, 3.6, 3.2, 44.5, 0.48, 0.8
R1 = R_RIM - MARGIN - A_RIP; R0 = 62.0; W_HALF, D1, D2 = 0.7, 1.3, 2.3
HUB_R, HUB_RI, BORE = 49.5, 44.0, 49.9; TOOTH_H, TOOTH_W, TRACK_W, TRACK_D = 2.6, 3.6, 4.0, 3.0
dome = lambda r: D_DOME * (1 - (r / R_RIM) ** 2)
PSI = lambda k: math.radians((GOLD * (k - 1)) % 360); LA = lambda k: PSI(k) + math.radians(6); LB = lambda k: PSI(k) + math.radians(11); LRX = lambda k: PSI(k) + math.radians(16)
PIN_C, PIN_R, NOTCH_R, STEM_R, SH_R = 51.7, 1.9, 1.9, 1.5, 2.1
def rip(j, R, phi): return RELIEF * (R / R_RIM) ** 2 * np.cos(M_PET * (phi - math.radians(GOLD * (j - 1))))
def zb(k, R, phi):                                                                  # layer k bottom = top lands of layer k+1 (perfect nesting, GAP 0)
    z = ZRX + dome(R) + (6 - k) * (PN + G)
    for j in range(k + 1, 7): z = z + rip(j, R, phi)
    return z
def arms(k):                                                                         # k = layer 1..6
    al = math.radians(GOLD * (k - 1)); t = np.linspace(0, 1, 4000); dl = LB(k) - LA(k); th0 = LA(k); bore = HUB_R if k == 1 else BORE
    pa = np.sqrt(R0 ** 2 + (R1 ** 2 - R0 ** 2) * t); tha = th0 + 2 * np.pi * N_ARM * t; ra = pa + A_RIP * (pa / R1) ** 2 * np.cos(M_PET * (tha - al))
    pb = np.sqrt(R1 ** 2 - (R1 ** 2 - R0 ** 2) * t); thb = tha[-1] + dl + 2 * np.pi * N_ARM * t; rb = pb + A_RIP * (pb / R1) ** 2 * np.cos(M_PET * (thb - al))
    xy = lambda r, p: np.c_[r * np.cos(p), r * np.sin(p)]; a = xy(ra, tha); b = xy(rb, thb)
    la = xy(np.linspace(ra[0], bore - 0.2, 60), np.full(60, th0)); lb = xy(np.linspace(rb[-1], bore - 0.2, 60), np.full(60, thb[-1]))
    return a, b, la, lb
def dens(P, step=0.2):
    out = [P[0]]
    for q in P[1:]:
        d = np.linalg.norm(q - out[-1])
        if d > 1e-9: n = max(1, int(d / step)); out += [out[-1] + (q - out[-1]) * (i / n) for i in range(1, n + 1)]
    return np.array(out)
def wrap(a): return (a + np.pi) % (2 * np.pi) - np.pi
NOTCH = {k: [] for k in range(1, 8)}; PINS = []
def wrap_deg(a): return (a + 180) % 360 - 180
def windows(k): return [(math.degrees(PSI(k)), 5.0), (math.degrees(LA(k)), 3.5), (math.degrees(LB(k)), 3.5), (math.degrees(LRX(k)), 3.5)] if k <= 6 else []
n = 0
for i in range(1, 7):                                                              # interface i = between layer i (above) and layer i+1 (below); i = 6 is the lock collar
    chosen = []
    while len(chosen) < 3:
        n += 1; th = (n * GOLD) % 360; ok = True
        for kk in (i, i + 1):
            for c, w in windows(kk):
                if abs(wrap_deg(th - c)) < w + 2.4: ok = False
        for p in PINS:
            if p['interface'] in (i - 1, i + 1) and abs(wrap_deg(th - p['theta'])) < 8: ok = False
        for c in chosen:
            if abs(wrap_deg(th - c[1])) < 60: ok = False
        if ok: chosen.append((n, th))
    for nn, th in chosen: PINS.append(dict(interface=i, n=nn, theta=th)); NOTCH[i].append(th); NOTCH[i + 1].append(th)
def far_r(phi, th_deg):
    d = wrap(phi - math.radians(th_deg)); off = PIN_C * np.sin(d); inside = (np.abs(off) < NOTCH_R) & (np.cos(d) > 0)
    return np.where(inside, PIN_C * np.cos(d) + np.sqrt(np.maximum(NOTCH_R ** 2 - off ** 2, 0)), 0.0)
def make_layer(k):
    a, b, la, lb = arms(k); al = math.radians(GOLD * (k - 1)); TA = cKDTree(np.vstack([dens(a), dens(la)])); TB = cKDTree(np.vstack([dens(b), dens(lb)]))
    pits = np.array([[55 * math.cos(PSI(k) - math.radians(5 + 3.2 * i)), 55 * math.sin(PSI(k) - math.radians(5 + 3.2 * i))] for i in range(k)]); TP = cKDTree(pits)
    f = lambda d, w: (lambda u: u * u * (3 - 2 * u))(np.clip((w - d) / 0.25, 0, 1))
    def depth(X, Y):
        q = np.c_[X.ravel(), Y.ravel()]; dA, _ = TA.query(q); dB, _ = TB.query(q); dP, _ = TP.query(q); gA, gB = f(dA, W_HALF), f(dB, W_HALF)
        dep = D1 * np.maximum(gA, gB) + (D2 - D1) * np.minimum(gA, gB); dep = np.maximum(dep, 0.8 * f(dP, 0.8)); return dep.reshape(X.shape)
    phi = np.linspace(0, 2 * np.pi, NPHI, endpoint=False); u = np.linspace(0, 1, NR)
    rin_v = np.full(NPHI, 49.3 if k == 1 else BORE)
    if k > 1: rin_v = np.where(np.abs(wrap(phi - PSI(k))) * BORE < TOOTH_W / 2, BORE - TOOTH_H, rin_v)          # ONE key tooth
    for th in NOTCH[k]: rin_v = np.maximum(rin_v, far_r(phi, th))                                                  # pin half-holes open to the bore, closed by the hub wall
    R_outv = np.minimum(R_RIM, R1 + A_RIP * np.cos(M_PET * (phi - al)) + MARGIN)
    R = rin_v[:, None] + (R_outv[:, None] - rin_v[:, None]) * u[None, :]; X = R * np.cos(phi)[:, None]; Y = R * np.sin(phi)[:, None]; PH = phi[:, None] + 0 * R
    Z = zb(k, R, PH) + PN + rip(k, R, PH) - depth(X, Y); Vt = np.c_[X.ravel(), Y.ravel(), Z.ravel()]; cs, sn = np.cos(phi), np.sin(phi)
    Bi = np.c_[rin_v * cs, rin_v * sn, zb(k, rin_v, phi)]; Bo = np.c_[R_outv * cs, R_outv * sn, zb(k, R_outv, phi)]; V = np.vstack([Vt, Bi, Bo]); nT = NPHI * NR; I = np.arange(NPHI); I2 = (I + 1) % NPHI; F = []
    ii, jj = np.meshgrid(I, np.arange(NR - 1), indexing="ij"); i2 = (ii + 1) % NPHI; a_ = ii * NR + jj; b_ = ii * NR + jj + 1; c_ = i2 * NR + jj + 1; d_ = i2 * NR + jj
    F += [np.c_[a_.ravel(), b_.ravel(), c_.ravel()], np.c_[a_.ravel(), c_.ravel(), d_.ravel()]]
    F += [np.c_[nT + I, nT + NPHI + I2, nT + NPHI + I], np.c_[nT + I, nT + I2, nT + NPHI + I2]]
    F += [np.c_[nT + NPHI + I, nT + NPHI + I2, I2 * NR + NR - 1], np.c_[nT + NPHI + I, I2 * NR + NR - 1, I * NR + NR - 1]]
    F += [np.c_[nT + I, I * NR, I2 * NR], np.c_[nT + I, I2 * NR, nT + I2]]
    return V, np.vstack(F), (a, b, la, lb)
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
def rect(ang, r0, r1, half):                                                          # rotated rectangle (radial r0..r1, tangential +-half) as a polygon
    c, s = math.cos(ang), math.sin(ang); pts = [(r0, -half), (r1, -half), (r1, half), (r0, half)]; return np.array([(x * c - y * s, x * s + y * c) for x, y in pts])
rep = dict(lod=LOD, hub=dict(outer_r=HUB_R, inner_r=HUB_RI, layer_bore_r=BORE, tooth="%.1f wide x %.1f high" % (TOOTH_W, TOOTH_H), track="%.1f wide x %.1f deep blind groove" % (TRACK_W, TRACK_D)),
           lane_map={f"layer_{k}": dict(track_deg=60 * (k - 1), TX_lane_A_deg=60 * (k - 1) + 9, TX_lane_B_deg=60 * (k - 1) + 15, RX_lane_deg=60 * (k - 1) + 36, dimples=k) for k in range(1, 7)},
           stack=dict(layer_thickness=PN, nested_gap=G, top_at_bore=round(ZRX + 5 * (PN + G) + PN + dome(BORE), 1), rim_top=round(ZRX + 5 * (PN + G) + PN, 1)))
paths = {}
for k in range(1, 7):
    V, F, Pp = make_layer(k); oe, dup = dir_edges_ok(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    rc.write_stl(f"{OUT}/L{k}_petal_cassette.stl", V, F, f"L{k}"); paths[k] = Pp
    rep[f"L{k}"] = dict(tris=int(len(F)), open_edges=oe, duplicate_edges=dup, petal_phase_deg=round((GOLD * (k - 1)) % 360, 2))
def emit(name, shells, note=""):
    bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells); V, F = g.merge(shells); rc.write_stl(f"{OUT}/{name}.stl", V, F, name); rep[name] = dict(tris=int(len(F)), nonmanifold_edges=int(bad), bbox=[round(float(x), 1) for x in (*V.min(0), *V.max(0))], note=note)
m = 1440; angs = np.linspace(0, 2 * np.pi, m, endpoint=False); ro = np.full(m, HUB_R)
def notch(ang, w, d):
    mask = np.abs(wrap(angs - ang)) * HUB_R < w / 2; ro[mask] = HUB_R - d
for k in range(1, 7): notch(PSI(k), TRACK_W, TRACK_D); notch(LA(k), 1.8, 1.4); notch(LB(k), 1.8, 1.4); notch(LRX(k), 1.8, 1.4)
shells = [ring(np.c_[ro * np.cos(angs), ro * np.sin(angs)], circ(HUB_RI, m), 6.0, 41.3), ring(circ(52.0), circ(10.0), 41.3, HMAX), ring(circ(52.0), circ(HUB_R), 38.6, 41.3)]
shells += [ring(circ(HUB_RI), circ(41.5), z - 1.2, z) for z in (9.0, 17.0, 25.0, 33.0)]
for k in range(2, 7):                                                                  # blind-end stop plugs above each layer's tooth + snap bumps
    zs = float(zb(k, np.array(BORE), np.array(PSI(k)))) + PN + float(rip(k, np.array(BORE), np.array(PSI(k)))) + 0.5
    if zs < 41.3: shells.append(extrude(rect(PSI(k), HUB_R - TRACK_D - 0.2, HUB_R + 0.1, TRACK_W / 2 + 0.05), zs, 41.3))
    shells.append(extrude(rect(PSI(k), HUB_R - TRACK_D - 0.1, HUB_R - TRACK_D + 1.1, 1.5), zs - 3.4, zs - 2.2))
    rep["lane_map"][f"layer_{k}"]["stop_z"] = round(zs, 2)
emit("L1_hub_foundation_with_tracks_lanes_PCB_slots", shells, "central PCB cylinder fused to L1: 6 numbered blind tracks (4x3), 18 closed wire lanes (12 TX + 6 RX, 1.8x1.4), 4 PCB ledges for D83 discs at 8 mm pitch, stop plugs and snap bumps, roof with D20 port")
emit("V2_floor_plate_and_lock_seat", [ring(circ(HUB_R), circ(8.0), 3.4, 6.0)], "floor plate seat; clamp the tray to the hub with 3 M3 screws (bosses to be added)")
emit("L7_RX_tray_cassette", [ring(circ(116.5), circ(5.0), 0.0, 0.8), ring(circ(116.5), circ(114.5), 0.0, ZRX)], "RX tray, PCB recess D229 x 2.4, open back")
def zt_at(k, r, th): return float(zb(k, np.array(r), np.array(math.radians(th)))) + PN + float(rip(k, np.array(r), np.array(math.radians(th))))
def zbt_at(k, r, th): return float(zb(k, np.array(r), np.array(math.radians(th))))
pin_tab = []
for i in range(1, 7):
    shells = []
    for p in [q for q in PINS if q['interface'] == i]:
        th = p['theta']; cx, cy = PIN_C * math.cos(math.radians(th)), PIN_C * math.sin(math.radians(th))
        if i < 6: z0, zs, zt_up = zbt_at(i + 1, PIN_C, th) + 0.2, zt_at(i + 1, PIN_C, th), zt_at(i, PIN_C, th) - 0.4; zs1 = zs + G
        else: z0, zs, zt_up = 6.0, 10.0, zt_at(6, PIN_C, th) - 0.4 if False else zbt_at(6, PIN_C, th) + PN * 0.8; zs1 = zbt_at(6, PIN_C, th)
        for (r_, za, zb_) in ((STEM_R, z0, zs), (SH_R, zs, zs1), (STEM_R, zs1, zt_up)):
            V, F = extrude(circ(r_, 28), za, zb_); shells.append((V + [cx, cy, 0], F))
        pin_tab.append(dict(interface=i, n=p['n'], theta_deg=round(th, 2), z_stem_bottom=round(z0, 2), z_shoulder=[round(zs, 2), round(zs1, 2)], z_stem_top=round(zt_up, 2), shoulder_height=round(zs1 - zs, 2)))
    emit(f"PINS_interface_{i}_x3" + ("_lock_collar" if i == 6 else ""), shells, "3 stepped pins: lower stem through layer %d, shoulder sets the gap, upper stem into layer %d" % (i + 1, i) if i < 6 else "3 pins on the lock collar into layer 6")
rep["pin_table"] = pin_tab; rep["gap_mm"] = G; rep["tracks_deg"] = {f"layer_{k}": round(math.degrees(PSI(k)), 2) for k in range(1, 7)}
rep["lane_map"] = {f"layer_{k}": dict(track_deg=round(math.degrees(PSI(k)), 2), TX_lane_A_deg=round(math.degrees(LA(k)), 2), TX_lane_B_deg=round(math.degrees(LB(k)), 2), RX_lane_deg=round(math.degrees(LRX(k)), 2), dimples=k, stop_z=rep["lane_map"].get(f"layer_{k}", {}).get("stop_z")) for k in range(1, 7)}
emit("V2_lock_collar_ring", [ring(circ(57.0), circ(49.7), 6.0, 10.0)], "bottom lock collar r49.7-57 under layer 6; 3 M3 screws through the floor plate into hub bosses (not yet modelled); carries the interface-6 pins")
rep["feedthrough"] = "18 lane exits (12 TX, 6 RX) pass through the hub wall at z=38..40 into the vault; drill 2 mm ports at the lane angles after fitting, then pot"
json.dump(rep, open(f"{OUT}/report.json", "w"), indent=1, default=float); pickle.dump(paths, open(f"{OUT}/paths.pkl", "wb"))
print(json.dumps({k: (v.get("open_edges"), v.get("tris")) for k, v in rep.items() if k.startswith("L") and "tris" in v}), rep["stack"])
