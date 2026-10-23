#!/usr/bin/env python3
"""
PF233-SB1 antenna characterisation (from the REAL generated track geometry)
  - series path per pattern (pad+ -> lobe R inward -> via -> lobe R outward -> bridge -> lobe L inward -> via -> lobe L outward -> pad-)
  - R_dc (copper), L (Neumann + GMR), C_eff (distributed estimate), SRF, Johnson noise
  - mutual inductance matrix between the four patterns (crosstalk)
  - flux linkage with the transmitter and null ratio vs board misalignment (gradiometer rejection)
  - receive sensitivity (T per amp on axis) used by the front-end sensitivity budget
"""
import io, contextlib, math, json, sys, time
import numpy as np
from scipy.special import ellipk, ellipe
mu0 = 4e-7 * math.pi; RHO = 1.72e-8; KB = 1.380649e-23
src = open("rx_board.py").read().split("# ---------------- writers ----------------")[0]
ns = {}
with contextlib.redirect_stdout(io.StringIO()): exec(src, ns)
pats, LAYER_Z = ns["pats"], ns["LAYER_Z"]
CU_T = {"X8": 70e-6, "Y8": 70e-6, "GX": 35e-6, "GY": 35e-6}      # 2 oz on the TX-capable figure-8, 1 oz on the gradiometers
W_M = {n: pats[n]["width"] * 1e-3 for n in pats}

def series_path(name):
    P = pats[name]; La, Lb = P["layers"]
    segs = [(P["tracks"][La][0], La), (P["tracks"][Lb][0], Lb), (P["tracks"][La][1], La)]
    pts = []
    for tr, L in segs:
        q = np.c_[tr, np.full(len(tr), LAYER_Z[L])]
        pts.append(q)
    return np.concatenate(pts)                                    # mm; layer changes appear as vertical jumps (vias)
def resample(P, ds):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    t = np.arange(0, s[-1], ds); return np.c_[[np.interp(t, s, P[:, k]) for k in range(3)]].T, float(s[-1])
def segs_of(P): return (P[1:] + P[:-1]) / 2 * 1e-3, (P[1:] - P[:-1]) * 1e-3
def neumann(m1, d1, m2, d2, chunk=400):
    t = 0.0
    for i in range(0, len(m1), chunk):
        R = np.linalg.norm(m1[i:i + chunk, None] - m2[None], axis=-1)
        R = np.maximum(R, 1e-6)
        t += float(((d1[i:i + chunk] @ d2.T) / R).sum())
    return mu0 / (4 * math.pi) * t

res = {}; paths = {}
t0 = time.time()
for n in pats:
    P = series_path(n); paths[n] = P
    ds = 0.5 if n[0] == "G" else 1.0
    Q, Ltot = resample(P, ds)
    m, d = segs_of(Q)
    gmr = 0.2235 * (W_M[n] + CU_T[n])
    Qo = Q + np.array([0, 0, gmr * 1e3])
    mo, do = segs_of(Qo)
    L = neumann(m, d, mo, do)
    R = RHO * (Ltot * 1e-3) / (W_M[n] * CU_T[n])
    res[n] = dict(track_length_m=round(Ltot * 1e-3, 3), R_dc_ohm=round(R, 3), L_uH=round(L * 1e6, 2),
                  thermal_noise_nV_rtHz=round(math.sqrt(4 * KB * 300 * R) * 1e9, 3))
    print(n, res[n], "%.0fs" % (time.time() - t0), flush=True)

# ---- self-capacitance (distributed estimate): same-layer turn-to-turn + broadside layer-to-layer
EPS0 = 8.854e-12; ER = 4.3; EEFF = (1 + ER) / 2
def cap_estimate(n):
    w, t = W_M[n], CU_T[n]; P = pats[n]; pitch = P_[n][3] * 1e-3
    s = pitch - w
    c_same = EPS0 * EEFF * (t / s) * 2 + EPS0 * EEFF * 2.0            # per metre of facing pair (parallel plate + fringe)
    h = 0.30e-3                                                       # prepreg between the two layers of a pair (assumed)
    c_layer = EPS0 * ER * w / h * 1.3
    Ltot = res[n]["track_length_m"]; nturn = PAT_[n][5] * 2 * 2       # turns (2 lobes x 2 layers)
    l_turn = Ltot / nturn
    f_same = (l_turn / Ltot) ** 2                                     # adjacent turns differ by one turn of potential
    f_layer = 0.15                                                    # mean (dV/V)^2 between the aligned traces of the two layers
    return (c_same * Ltot * f_same + c_layer * Ltot / 2 * f_layer)
PAT_ = ns["PAT"]; P_ = PAT_
for n in pats:
    C = cap_estimate(n); res[n]["C_eff_pF_est"] = round(C * 1e12, 2)
    res[n]["SRF_MHz_est"] = round(1 / (2 * math.pi * math.sqrt(res[n]["L_uH"] * 1e-6 * C)) / 1e6, 2)
    res[n]["note_C"] = "+-50 % (distributed estimate, FR-4 er 4.3, 0.30 mm prepreg assumed)"

# ---- mutual inductance matrix (crosstalk)
names = list(pats); M = {}
for i, a in enumerate(names):
    for b in names[i + 1:]:
        Qa, _ = resample(paths[a], 2.0); Qb, _ = resample(paths[b], 2.0)
        ma, da = segs_of(Qa); mb, db = segs_of(Qb)
        Mab = neumann(ma, da, mb, db)
        k = Mab / math.sqrt(res[a]["L_uH"] * res[b]["L_uH"] * 1e-12)
        M[f"{a}-{b}"] = dict(M_nH=round(Mab * 1e9, 3), k=float(f"{k:.2e}"))
        print(a, b, M[f"{a}-{b}"], flush=True)
res["mutual"] = M

# ---- transmitter coupling and null ratio (axisymmetric TX from the ring model of the real build)
exec(open("band_study.py").read().split("A=0.5e-6")[0].replace("import phi_fold_v2 as v2, rodin_core_v4 as rc", "import phi_fold_v2 as v2, rodin_core_v4 as rc"))
def loop_BrBz(a, zc, r, z):
    dz = z - zc; r = np.maximum(r, 1e-9); k2 = 4 * a * r / ((a + r) ** 2 + dz ** 2); K, E = ellipk(k2), ellipe(k2)
    den = np.sqrt((a + r) ** 2 + dz ** 2)
    return mu0 / (2 * np.pi) / den * (K + (a * a - r * r - dz * dz) / ((a - r) ** 2 + dz ** 2) * E)
def TXBz(x, y, z, i2=0.56):                      # per terminal amp, 4 sections in parallel (1/4 per section), both bands
    r = np.hypot(x, y); B = np.zeros_like(r)
    for rings, I in ((TX, 1.0), (HUB, i2)):
        for a, zc, n in rings: B += n * I * loop_BrBz(a, zc, r, z)
    return B / 4.0
def lobe_flux(Rmax, gap, pitch, turns, cx, cy, ang, z, sign, layers=2, step=0.5):
    """flux (per TX amp) through one lobe: sum over nested D-turns of Bz, board shifted by (cx,cy)"""
    xs = np.arange(gap / 2, Rmax, step); ys = np.arange(-Rmax, Rmax, step); X, Y = np.meshgrid(xs, ys)
    rr = np.hypot(X, Y); k_x = np.floor((X - gap / 2) / pitch); k_r = np.floor((Rmax - rr) / pitch)
    nenc = np.clip(np.minimum(k_x, k_r) + 1, 0, turns); nenc[(rr > Rmax)] = 0
    xr = (sign * X) * math.cos(ang) - Y * math.sin(ang) + cx; yr = (sign * X) * math.sin(ang) + Y * math.cos(ang) + cy
    B = TXBz(xr * 1e-3, yr * 1e-3, z * 1e-3)
    return layers * float((nenc * B).sum()) * (step * 1e-3) ** 2
null = {}
for n, (Rmax, gap, pitch, turns, ang) in {"GX": (22.0, 3.0, 0.3, 24, 0.0), "GY": (22.0, 3.0, 0.3, 24, math.pi / 2),
                                         "X8": (110.0, 6.0, 2.4, 18, 0.0), "Y8": (110.0, 6.0, 2.4, 18, math.pi / 2)}.items():
    zc = LAYER_Z[PAT_[n][0][0]]; zc2 = LAYER_Z[PAT_[n][0][1]]
    z_mid = (zc + zc2) / 2
    row = {}
    for d in (0.0, 0.1, 0.25, 0.5, 1.0):
        pr = lobe_flux(Rmax, gap, pitch, turns, d, 0, ang, z_mid, +1); pl = lobe_flux(Rmax, gap, pitch, turns, d, 0, ang, z_mid, -1)
        row[f"shift_{d}mm"] = dict(flux_R_nWb_per_A=round(pr * 1e9, 3), flux_net_nWb_per_A=round((pr - pl) * 1e9, 5))
    single = row["shift_0.0mm"]["flux_R_nWb_per_A"]
    for d in (0.1, 0.25, 0.5, 1.0):
        row[f"shift_{d}mm"]["null_ratio"] = float(f"{abs(row[f'shift_{d}mm']['flux_net_nWb_per_A']) / max(abs(single) * 2, 1e-12):.2e}")
    null[n] = row; print(n, "null", {k: v.get("null_ratio") for k, v in row.items()}, flush=True)
res["tx_coupling_and_null"] = null
# turn-off induced voltage for a 20 A, 1 us ramp-down (worst case) at 0.5 mm misalignment
for n in null:
    f = abs(null[n]["shift_0.5mm"]["flux_net_nWb_per_A"]) * 1e-9
    res[n]["Vinduced_at_turnoff_V_(20A,1us,0.5mm_shift)"] = round(f * 20 / 1e-6, 3)
    # worst-case direct (no cancellation, e.g. one lobe only / board tilt): single-lobe flux * 20A/1us
    res[n]["Vinduced_one_lobe_uncancelled_V"] = round(abs(null[n]["shift_0.0mm"]["flux_R_nWb_per_A"]) * 1e-9 * 20 / 1e-6, 2)
# ---- receive sensitivity: B on axis per amp of the antenna (reciprocity) at target depths
def bs_axis(P, depths):
    m, d = segs_of(resample(P, 0.8)[0]); pts = np.stack([0 * depths, 0 * depths, -depths * 1e-3], -1); B = np.zeros((len(depths), 3))
    for i in range(0, len(m), 4000):
        R = pts[:, None] - m[None, i:i + 4000]; Rn = np.linalg.norm(R, axis=-1)[..., None]
        B += (np.cross(d[None, i:i + 4000], R) / Rn ** 3).sum(1)
    return mu0 / (4 * math.pi) * B
dep = np.array([25, 50, 100, 150, 200, 300.0]); sens = {}
for n in pats:
    B = bs_axis(paths[n], dep); sens[n] = dict(depth_mm=dep.tolist(), Bz_uT_per_A=[round(float(b[2] * 1e6), 5) for b in B], Bx_uT_per_A=[round(float(b[0] * 1e6), 5) for b in B], By_uT_per_A=[round(float(b[1] * 1e6), 5) for b in B])
res["receive_sensitivity_on_axis"] = sens
json.dump(res, open("out_board/antenna_model.json", "w"), indent=1, default=float); print("done %.0fs" % (time.time() - t0))
