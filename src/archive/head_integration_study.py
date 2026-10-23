#!/usr/bin/env python3
"""
Can the whole electronics stack live inside the search head?
1. Visibility of metal inside the head: a conductive object at (r,z) responds ~ B_tx(r,z) * B_rx(r,z) = |B|^2 (same coil transmits and receives).
   Compared with the reference target (1 g gold nugget at 200 mm below the coil).
2. Closed ferrite vault: shielding factor S (field inside / field outside) -> signal reduced by S^2.
3. Heat budget and potting materials.
"""
import math, json, os
import numpy as np
from scipy.special import ellipk, ellipe
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
os.makedirs("kit_v6", exist_ok=True)
mu0 = 4e-7 * math.pi
exec(open("band_study.py").read().split("A=0.5e-6")[0])               # TX (outer band, one-piece geometry) ring set in SI units
RINGS = np.array([(a, zc, n / 4.0) for a, zc, n in TX])                # per terminal amp, 4 sections in parallel
def ring_B(a, zc, r, z):
    dz = z - zc; rr = np.maximum(r, 1e-9); k2 = 4 * a * rr / ((a + rr) ** 2 + dz ** 2); K = ellipk(k2); E = ellipe(k2)
    den = np.sqrt((a + rr) ** 2 + dz ** 2); d2 = (a - rr) ** 2 + dz ** 2 + 1e-18
    return (mu0 / (2 * np.pi) * dz / (rr * den) * (-K + (a * a + rr * rr + dz * dz) / d2 * E), mu0 / (2 * np.pi) / den * (K + (a * a - rr * rr - dz * dz) / d2 * E))
def B(r, z):
    br = np.zeros_like(r, float); bz = np.zeros_like(r, float)
    for a, zc, n in RINGS:
        x, y = ring_B(a, zc, r, z); br += n * x; bz += n * y
    return br, bz
# ------------------------------------------------------------ 1. field / visibility map
rr = np.linspace(0, 0.16, 81); zz = np.linspace(-0.01, 0.20, 106); R_, Z_ = np.meshgrid(rr, zz)
br, bz = B(R_, Z_); Bm = np.hypot(br, bz)
_br, _bz = B(np.array([1e-6]), np.array([-0.2])); b_ref = float(np.hypot(_br[0], _bz[0]))                # 1 g nugget at 200 mm
vis = (Bm / b_ref) ** 2                                                         # relative visibility factor per unit object response
res = {"B_ref_uT_per_A_at_200mm": round(b_ref * 1e6, 3)}
pts = {"centre of the old bay (r0,z17)": (0.0, 0.017), "inside the head, r 40 mm z 20": (0.04, 0.020), "lid level above centre (r0,z45)": (0.0, 0.045),
       "head rim outside the winding (r125,z10)": (0.125, 0.010), "neck 100 mm above head (r0,z100)": (0.0, 0.100), "neck 150 mm (r0,z150)": (0.0, 0.150),
       "spine electronics 700 mm up (r0,z700)": (0.0, 0.700)}
res["field_uT_per_A_and_visibility_vs_1g_nugget_field_ratio_squared"] = {}
for k, (r, z) in pts.items():
    x, y = B(np.array([r]), np.array([z])); bb = float(np.hypot(x[0], y[0])); res["field_uT_per_A_and_visibility_vs_1g_nugget_field_ratio_squared"][k] = dict(B_uT_per_A=round(bb * 1e6, 2), field_ratio_sq=round((bb / b_ref) ** 2, 1))
# ------------------------------------------------------------ 2. object visibility (relative to a 1 g nugget at 200 mm), at the 10 us gate
sig_cu = 5.8e7; sig_au = 1.5e7
def tau_disc(a, d, sig=sig_cu): return mu0 * sig * d * a / 5.0                  # slowest eddy mode of a thin disc, approximate (+-50 %)
def tau_sph(a, sig=sig_au): return mu0 * sig * a * a / math.pi ** 2
def kern(tau, t):
    n = np.arange(1, 60); tn = tau / n ** 2; return float((6 / (n * n * math.pi ** 2) / tn * np.exp(-t / tn)).sum())
t_gate = 10e-6
m_nug = 2 * math.pi * (2.3e-3) ** 3 * kern(tau_sph(2.3e-3), t_gate)             # dipole response of the reference nugget (per unit H)
def disc(a, d, sig=sig_cu):
    tau = tau_disc(a, d, sig); return (8 / 3) * a ** 3 / tau * math.exp(-t_gate / tau), tau      # dm/dt (what the receiver sees), same quantity as the nugget kernel
objs = {"PCB ground plane, solid Cu 1 oz, disc 40 mm": (20e-3, 35e-6), "same plane cut into 16 sectors (eddy loop ~ 5 mm; response x16 sectors)": (2.5e-3, 35e-6),
        "plane under all boards: Cu 2 oz, disc 70 mm": (35e-3, 70e-6), "IC lead-frame, 3 mm": (1.5e-3, 100e-6), "MLCC / 2512 resistor terminations, 2 mm": (1.0e-3, 50e-6), "TO-263 FET tab, 10 mm Cu": (5e-3, 1.0e-3)}
loc = {"vault at the centre of the head (r0,z17)": (0.0, 0.017)}
x, y = B(np.array([0.0]), np.array([0.017])); b_c = float(np.hypot(x[0], y[0]))
rows = {}
for name, (a, d) in objs.items():
    m, tau = disc(a, d); ratio_bare = (m / m_nug) * (b_c / b_ref) ** 2 * (16 if 'sectors' in name else 1)
    rows[name] = dict(tau_us=round(tau * 1e6, 2), signal_vs_1g_nugget_bare=float(f"{ratio_bare:.3g}"))
res["metal_in_the_head_centre_signal_ratio_vs_1g_nugget_at_200mm_10us_gate"] = rows
# ------------------------------------------------------------ 3. ferrite vault shielding
V_box = 80e-3 * 80e-3 * 30e-3; R_eq = (3 * V_box / (4 * math.pi)) ** (1 / 3)
def S_box(mur, t): return 1 + 2 * mur * t / (3 * R_eq)
vault = {"MnZn mur 2000, 3 mm": S_box(2000, 3e-3), "MnZn mur 2000, 2 mm": S_box(2000, 2e-3), "NiZn mur 400, 3 mm": S_box(400, 3e-3), "NiZn mur 400, 5 mm": S_box(400, 5e-3), "polymer ferrite mur 10, 5 mm": S_box(10, 5e-3)}
res["vault_shielding"] = {k: dict(S=round(v, 1), dB=round(20 * math.log10(v), 1), signal_reduction_factor=round(v * v)) for k, v in vault.items()}
res["vault_equivalent_radius_mm"] = round(R_eq * 1e3, 1)
for name in rows:
    rows[name]["with_MnZn_3mm_vault"] = float(f"{rows[name]['signal_vs_1g_nugget_bare'] / vault['MnZn mur 2000, 3 mm'] ** 2:.2e}")
    rows[name]["with_NiZn_3mm_vault"] = float(f"{rows[name]['signal_vs_1g_nugget_bare'] / vault['NiZn mur 400, 3 mm'] ** 2:.2e}")
# ------------------------------------------------------------ 4. heat budget (steady state)
heat = {"scan": dict(clamp_W=2.23, tx_fet_W=0.25, regulators_W=0.35, MCU_BT_W=0.55, analog_W=0.64, shunt_other_W=0.05),
        "boost_300Hz": dict(clamp_W=5.23, tx_fet_W=0.60, regulators_W=0.45, MCU_BT_W=0.65, analog_W=0.64, shunt_other_W=0.25)}
A_top = math.pi * 0.1165 ** 2 * 1.03; A_side = 2 * math.pi * 0.1165 * 0.03; hA = 10.0 * (A_top + A_side)      # natural convection + radiation, W/K
for m, d in heat.items():
    P = sum(d.values()); d["total_W"] = round(P, 2); d["head_surface_rise_K"] = round(P / hA, 1)
res["heat_budget"] = heat; res["head_conductance_W_per_K"] = round(hA, 2)
def Rth(L, k, A): return L / (k * A)
res["conduction_resistance_K_per_W"] = {"vault -> lid through 18 mm syntactic foam (k 0.2), 80 cm2": round(Rth(0.018, 0.2, 0.008), 1), "same through conductive silicone (k 1.5)": round(Rth(0.018, 1.5, 0.008), 1),
                                         "clamp resistors bonded to the lid underside with 1 mm conductive silicone (k 1.5), 12 cm2": round(Rth(0.001, 1.5, 0.0012), 2)}
# ------------------------------------------------------------ 5. potting materials (typical datasheet-class values; verify per product)
res["potting_options"] = {
    "syntactic epoxy foam (epoxy + 25-35 vol % glass bubbles)": dict(density_g_cc="0.55-0.75", k_W_mK="0.12-0.20", CTE_ppm_K="40-60", cure="low exotherm, pour in 10-15 mm lifts, <=60 C", use="winding voids, cavity filler, buoyancy and stiffness", warning="thermal insulator: keep it away from heat sources; rigid, not re-enterable"),
    "unfilled epoxy, low viscosity": dict(density_g_cc="1.1", k_W_mK="0.2", CTE_ppm_K="60-70", use="wire locking in the grooves (thin film)", warning="exotherm in thick sections; use thin lifts"),
    "two-part silicone gel / soft elastomer (Shore 00-30 to A10)": dict(density_g_cc="0.95-1.1", k_W_mK="0.2 unfilled / 1.0-2.0 alumina-filled", CTE_ppm_K="200-300", use="inside the ferrite vault around electronics: stress-free, re-enterable (gel), waterproof", warning="avoid red/black pigmented grades (iron oxide / carbon): they show up as a target"),
    "polyurethane": dict(density_g_cc="1.0-1.2", k_W_mK="0.2-0.4", CTE_ppm_K="100-200", use="optional outer encapsulation", warning="moisture sensitive during cure"),
    "forbidden fillers": "iron oxide, ferrite, carbon black, graphite, aluminium or copper powder, any metal flake; check each product with a magnet and a bench test coil"}
json.dump(res, open("kit_v6/head_integration_study.json", "w"), indent=1, default=float)
# ------------------------------------------------------------ figure
fig, ax = plt.subplots(1, 2, figsize=(13.5, 5))
cs = ax[0].contourf(R_ * 1e3, Z_ * 1e3, np.log10(np.maximum(vis, 1e-3)), levels=np.linspace(-3, 4, 29), cmap="magma"); plt.colorbar(cs, ax=ax[0], label="log10 (|B|/|B_ref|)^2")
ax[0].add_patch(plt.Rectangle((72, 0), 44.5, 22, fc="none", ec="c", lw=1.2)); ax[0].add_patch(plt.Rectangle((-0.0, 4), 40, 30, fc="none", ec="w", ls="--", lw=1.2))
ax[0].text(75, 24, "outer band", color="c", fontsize=8); ax[0].text(2, 36, "vault (r<40, z 4-34)", color="w", fontsize=8)
ax[0].set_xlabel("r (mm)"); ax[0].set_ylabel("z (mm)"); ax[0].set_title("Visibility of a metal object vs 1 g gold at 200 mm (field^2 ratio)", fontsize=9)
names = list(rows.keys()); y = np.arange(len(names)); bare = [rows[n]["signal_vs_1g_nugget_bare"] for n in names]; mn = [rows[n]["with_MnZn_3mm_vault"] for n in names]; nz = [rows[n]["with_NiZn_3mm_vault"] for n in names]
ax[1].barh(y + 0.27, bare, 0.27, color="#c0392b", label="bare (no vault)"); ax[1].barh(y, nz, 0.27, color="#e67e22", label="NiZn 3 mm vault"); ax[1].barh(y - 0.27, mn, 0.27, color="#27ae60", label="MnZn 3 mm vault")
ax[1].axvline(1.0, color="k", lw=1); ax[1].text(1.1, len(names) - 0.4, "= 1 g nugget at 200 mm", fontsize=8)
ax[1].set_xscale("log"); ax[1].set_yticks(y); ax[1].set_yticklabels([n[:44] for n in names], fontsize=7); ax[1].set_xlabel("signal relative to a 1 g gold nugget at 200 mm (10 us gate)"); ax[1].legend(fontsize=8)
ax[1].set_title("Metal in the head centre, with and without a closed ferrite vault", fontsize=9)
fig.tight_layout(); fig.savefig("kit_v6/head_integration_study.png", dpi=130)
print(json.dumps({k: res[k] for k in ("field_uT_per_A_and_visibility_vs_1g_nugget_field_ratio_squared", "metal_in_the_head_centre_signal_ratio_vs_1g_nugget_at_200mm_10us_gate", "vault_shielding", "heat_budget", "conduction_resistance_K_per_W")}, indent=1, default=float))
