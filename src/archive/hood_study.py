#!/usr/bin/env python3
"""
Ferrite hood over the search coil: field redirection, leakage, inductance change.
Model: hood = thin high-permeability shell (mu_r -> infinity) following the golden face at offset d.
In the magnetic scalar-potential picture it is an EQUIPOTENTIAL body with zero net magnetic charge -> solve ring charges (axisymmetric BEM).
Validated against the exact image-plane solution for a very large flat plate.
"""
import math, json
import numpy as np
from scipy.special import ellipk, ellipe
exec(open("band_study.py").read().split("A=0.5e-6")[0])           # TX, HUB ring sets of the one-piece coil (SI units)
mu0 = 4e-7 * math.pi; T_SL = 0.2360679
RINGS = [(a, zc, n / 4.0) for a, zc, n in TX] + [(a, zc, 0.374 * n / 4.0) for a, zc, n in HUB]      # per terminal amp, 4 sections in parallel
RINGS = np.array(RINGS)
def ring_field(a, zc, r, z):
    dz = z - zc; rr = np.maximum(r, 1e-9); k2 = 4 * a * rr / ((a + rr) ** 2 + dz ** 2); K = ellipk(k2); E = ellipe(k2)
    den = np.sqrt((a + rr) ** 2 + dz ** 2); d2 = (a - rr) ** 2 + dz ** 2 + 1e-18
    bz = mu0 / (2 * np.pi) / den * (K + (a * a - rr * rr - dz * dz) / d2 * E)
    br = mu0 / (2 * np.pi) * dz / (rr * den) * (-K + (a * a + rr * rr + dz * dz) / d2 * E)
    return br / mu0, bz / mu0
def H_coil(r, z, rings=RINGS):
    Hr = np.zeros_like(r, float); Hz = np.zeros_like(r, float)
    for a, zc, n in rings:
        hr, hz = ring_field(a, zc, r, z); Hr += n * hr; Hz += n * hz
    return Hr, Hz
def phi_unit(a, zq, r, z):                       # potential of a unit ring charge
    dz = z - zq; k2 = 4 * a * np.maximum(r, 1e-9) / ((a + r) ** 2 + dz ** 2); return (1 / (4 * np.pi)) * (2 / np.pi) * ellipk(np.minimum(k2, 1 - 1e-12)) / np.sqrt((a + r) ** 2 + dz ** 2)
def phi_ext(pts):
    """scalar potential of the coil on hood points: integral of Hz from infinity down to the point along the vertical line"""
    out = []
    u = np.linspace(0, 1, 41)[1:]; w = np.diff(np.r_[0, u])
    for r, z in pts:
        t = 0.02 * (np.exp(7.0 * u) - 1.0)                   # 0..~21 m, dense near the point
        zz = z + t; dt = np.gradient(t)
        Hr, Hz = H_coil(np.full_like(zz, r), zz); out.append(float((Hz * dt).sum()))
    return np.array(out)
def solve(pts, ds):
    N = len(pts); r = pts[:, 0]; z = pts[:, 1]; A = np.zeros((N + 1, N + 1))
    for j in range(N):
        A[:N, j] = phi_unit(r[j], z[j], r, z + 0.0)
    for i in range(N): A[i, i] = phi_unit(r[i], z[i], r[i], z[i] + 0.35 * ds[i])        # self term regularised
    A[:N, N] = -1.0; A[N, :N] = 1.0
    b = np.r_[-phi_ext(pts), 0.0]; sol = np.linalg.solve(A, b); return sol[:N]
def H_sigma(Q, pts, r, z, d=2e-5):
    def phi(rr, zz): return sum(Q[j] * phi_unit(pts[j, 0], pts[j, 1], rr, zz) for j in range(len(Q)))
    Hr = -(phi(r + d, z) - phi(np.maximum(r - d, 0), z)) / (2 * d if r > d else d + r)
    Hz = -(phi(r, z + d) - phi(r, z - d)) / (2 * d); return Hr, Hz
def cone_points(r0, r1, off, N, h_flat=None):
    r = r0 + (r1 - r0) * 0.5 * (1 - np.cos(np.linspace(0, np.pi, N)))          # cosine spacing: finer at the edges
    z = (13.0 + (116.5 - r * 1e3) * T_SL + off * 1e3) * 1e-3 if h_flat is None else np.full_like(r, h_flat)
    pts = np.c_[r, z]; ds = np.gradient(r) * np.sqrt(1 + (np.gradient(z) / np.gradient(r)) ** 2); return pts, ds
res = {}
# ------------------------------------------------ validation: very large flat plate vs image method
h = 0.05
pts, ds = cone_points(0.001, 3.0, 0, 90, h_flat=h)
pts[:, 0] = np.geomspace(0.004, 3.0, 90); pts[:, 1] = h; ds = np.gradient(pts[:, 0])
Q = solve(pts, ds)
zq = -0.2
for_val = {}
for zq in (-0.1, -0.2, -0.3):
    hr, hz = H_coil(np.array([0.0]), np.array([zq])); hsr, hsz = H_sigma(Q, pts, np.array([1e-6]), np.array([zq]))
    mir = np.array([(a, 2 * h - zc, n) for a, zc, n in RINGS]); hri, hzi = H_coil(np.array([0.0]), np.array([zq]), mir)
    for_val[f"{int(-zq*1000)}mm"] = dict(BEM_gain=round(float((hz[0] + hsz[0]) / hz[0]), 3), image_method_gain=round(float((hz[0] + hzi[0]) / hz[0]), 3))
res["validation_large_plate_h50mm"] = for_val; print("validation", for_val, flush=True)
# ------------------------------------------------ hood variants
V = {"A: ring r 72-118 on the face (offset 4 mm)": (0.072, 0.118, 0.004), "B: ring r 30-118 on the face (offset 4 mm)": (0.030, 0.118, 0.004),
     "C: ring r 72-118, offset 10 mm": (0.072, 0.118, 0.010), "D: ring r 30-118, offset 10 mm": (0.030, 0.118, 0.010)}
depths = [0.1, 0.2, 0.3, 0.4]
for name, (r0, r1, off) in V.items():
    pts, ds = cone_points(r0, r1, off, 70); Q = solve(pts, ds)
    row = {"axis_gain_below": {}, "axis_B_above": {}}
    for zq in depths:
        hr, hz = H_coil(np.array([0.0]), np.array([-zq])); hsr, hsz = H_sigma(Q, pts, np.array([1e-6]), np.array([-zq])); row["axis_gain_below"][f"{int(zq*1000)}mm"] = round(float((hz[0] + hsz[0]) / hz[0]), 3)
    for zz in (0.017, 0.060, 0.150):                                    # inside the bay, above the lid, higher up the shaft
        hr, hz = H_coil(np.array([0.0]), np.array([zz])); hsr, hsz = H_sigma(Q, pts, np.array([1e-6]), np.array([zz])); row["axis_B_above"][f"z=+{int(zz*1000)}mm"] = dict(without_uT_per_A=round(float(mu0 * hz[0] * 1e6), 2), with_hood_uT_per_A=round(float(mu0 * (hz[0] + hsz[0]) * 1e6), 2))
    # inductance change: flux of the induced field through the outer-band turns
    gl = np.polynomial.legendre.leggauss(10); phi_tot = 0.0
    for a, zc, n in TX[::6]:
        rn = 0.5 * a * (gl[0] + 1); wn = 0.5 * a * gl[1]
        bz = np.array([mu0 * H_sigma(Q, pts, np.array([x]), np.array([zc]))[1][0] for x in rn]); phi_tot += float(n * 6 * (2 * np.pi * rn * bz * wn).sum())
    row["delta_L_percent_of_outer_band_102.6uH"] = round(float(100 * (phi_tot / 4.0) / 102.6e-6), 1)
    res[name] = row; print(name, row, flush=True)
# ------------------------------------------------ finite-permeability reality check for thin plates
def beta(mur, t_mm, L_mm=46.0): return round(mur * t_mm / (mur * t_mm + L_mm), 2)
res["finite_mu_efficiency_beta (1.0 = ideal)"] = {"MnZn tile mur 2000, 2.5 mm": beta(2000, 2.5), "NiZn tile mur 400, 3 mm": beta(400, 3), "NiZn flexible sheet mur 100, 1 mm x2": beta(100, 2),
                                                 "ferrite-polymer injection moulding mur 10, 4 mm": beta(10, 4)}
mu0v = mu0
def tau_us(mur, sigma, t_mm): return round(mu0v * mur * sigma * (t_mm * 1e-3) ** 2 / math.pi ** 2 * 1e6, 3)
res["ferrite_eddy_decay_time_us"] = {"MnZn (sigma 0.5 S/m) mur 2000, 2.5 mm": tau_us(2000, 0.5, 2.5), "NiZn (sigma 1e-4) mur 400, 3 mm": tau_us(400, 1e-4, 3), "polymer ferrite (insulating) mur 10": tau_us(10, 1e-6, 4)}
json.dump(res, open("kit_v5/hood_study.json", "w") if __import__("os").makedirs("kit_v5", exist_ok=True) is None else None, indent=1)
print(json.dumps(res.get("finite_mu_efficiency_beta (1.0 = ideal)")), json.dumps(res["ferrite_eddy_decay_time_us"]))
