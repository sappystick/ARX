#!/usr/bin/env python3
"""
PHI-FOLD 233 — full-system simulation (v2C head + PF233-SB1 sensor board)
=========================================================================
1. Fields: Z mode (outer + inner TX bands, optimal 0.63 split) normal vs
   trigger-boost; X/Y rotating mode; XZ field map; precession angle.
2. Receiver channels vs targets (gold 0.1/1/10 g, coin, foil, pull-tab, nail)
   in magnetic (viscous) ground.
3. DSP: 6 time gates, dual-pair ground balance (no hole), tau fit with ground
   term, ferrous flag from rotating-field in-phase channel, two-sensor depth.
4. Classifier Monte Carlo -> confusion matrix for ALL-METAL and GOLD modes.
5. Power / battery / thermal for normal and boost.
All models are physics-based but simplified; see notes in the report.
"""
import math, json, numpy as np
from scipy.special import ellipk, ellipe
import phi_fold_former as pf, golden_cone_head as g
mu0 = 4e-7 * math.pi
rng = np.random.default_rng(7)
exec(open("band_study.py").read().split("A=0.5e-6")[0])          # TX, HUB ring models + helpers
OUT = "out_system"; import os; os.makedirs(OUT, exist_ok=True)

# ---------------- 1. fields ----------------
def loop_BrBz(a, zc, r, z):
    """exact off-axis field of a circular loop (per amp), cylindrical components"""
    dz = z - zc; r = np.maximum(r, 1e-9)
    k2 = 4 * a * r / ((a + r) ** 2 + dz ** 2); K, E = ellipk(k2), ellipe(k2)
    den = np.sqrt((a + r) ** 2 + dz ** 2)
    Bz = mu0 / (2 * np.pi) / den * (K + (a * a - r * r - dz * dz) / ((a - r) ** 2 + dz ** 2) * E)
    Br = mu0 / (2 * np.pi) * dz / (r * den) * (-K + (a * a + r * r + dz * dz) / ((a - r) ** 2 + dz ** 2) * E)
    return Br, Bz
def Bz_field(r, z, i1=1.0, i2=0.56):
    Br = np.zeros_like(r, float); Bz = np.zeros_like(r, float)
    for rings, I in ((TX, i1), (HUB, i2)):
        for a, zc, n in rings:
            br, bz = loop_BrBz(a, zc, r, z); Br += n * I * br; Bz += n * I * bz
    return Br, Bz
MODES = {"normal": dict(I_tx=8.0, I_xy=0.0, prf=800), "boost": dict(I_tx=20.0, I_xy=1.0, prf=800)}
# per-section-string convention: TX/HUB ring sets represent all sections in series; a parallel drive of total
# current I gives each section I/4 -> divide by 4 (and by 2 for the 2 stacked circuits already inside the set? no:
# the set already counts both circuits as turns) -> factor 1/4
SCALE = 1 / 4
r = np.linspace(0, 0.30, 121); z = np.linspace(-0.40, 0.10, 101); RR, ZZ = np.meshgrid(r, z)
Br, Bz = Bz_field(RR, ZZ); Bmag = np.hypot(Br, Bz) * SCALE                         # T per amp (total TX current)
np.save(f"{OUT}/fieldmap_Bmag_per_A.npy", Bmag)
xy = pf.figure8("X"); xm, xd = [], []
for P in xy: m, d = pf.segs_closed(P); xm.append(m); xd.append(d)
xm, xd = np.concatenate(xm), np.concatenate(xd)
depths = np.array([0.05, 0.1, 0.15, 0.2, 0.3, 0.4])
ax_pts = np.stack([0 * depths, 0 * depths, -depths], -1)
Bx_axis = g.biot_savart(xm, xd, np.ones(len(xm)), ax_pts)[:, 0]               # T per amp, X layer
Bz_axis = np.array([Bz_field(np.array([1e-6]), np.array([-d]))[1][0] for d in depths]) * SCALE
field = {}
for mname, M in MODES.items():
    field[mname] = dict(Bz_uT=[round(float(b * M["I_tx"] * 1e6), 2) for b in Bz_axis],
                        Bxy_rotating_uT=[round(float(abs(b) * M["I_xy"] * 1e6), 2) for b in Bx_axis],
                        precession_half_angle_deg=[round(math.degrees(math.atan2(abs(bx) * M["I_xy"], abs(bz) * M["I_tx"])), 1)
                                                   for bx, bz in zip(Bx_axis, Bz_axis)])
field["depth_mm"] = (depths * 1000).tolist()

# ---------------- 2. targets, ground, channels ----------------
def tau1(a, s): return mu0 * s * a * a / math.pi ** 2
def S_t(tau, t):                         # normalised sphere decay-rate kernel, any tau (series in n)
    n = np.arange(1, 60); tn = tau / n ** 2
    return (6 / (n * n * math.pi ** 2) / tn * np.exp(-np.asarray(t)[..., None] / tn)).sum(-1)
TARGETS = {  # name: (equivalent sphere radius m, conductivity S/m, ferrous)
    "gold 0.1 g": (1.07e-3, 1.2e7, False), "gold 1 g": (2.3e-3, 1.5e7, False), "gold 10 g": (5.0e-3, 1.5e7, False),
    "gold 50 g": (8.5e-3, 1.5e7, False), "aluminium foil": (3.0e-3, 2.0e6, False), "pull-tab": (4.0e-3, 7.0e6, False),
    "silver coin": (8.0e-3, 3.0e7, False), "iron nail": (3.0e-3, 2.0e6, True)}
GATES = np.array([5, 10, 20, 40, 80, 160]) * 1e-6
VN = 1.0e-6                                                     # per-gate noise (field, after averaging)
def channel_coupling(depth, lateral=0.0):
    """B_tx (per A, at target) and receive couplings per channel (V per unit dm/dt):
       mono = both TX bands as RX (series); grad = |GX| best orientation; xy = X fig-8"""
    p = np.array([[lateral, 0, -depth]])
    br, bz = Bz_field(np.array([abs(lateral) + 1e-6]), np.array([-depth]))
    btx = np.array([br[0], 0, bz[0]]) * SCALE
    mono = np.array([br[0], 0, bz[0]])                         # all turns series as receiver
    return btx, mono
GRAD_CACHE = {}
def grad_rx(depth):
    if depth in GRAD_CACHE: return GRAD_CACHE[depth]
    # best-case lateral position for the Ø44 gradiometer (peak response) -> use cached loop model
    c, a = 0.011, 0.01045
    def lf(cx, P):
        t = np.linspace(0, 2 * np.pi, 48, endpoint=False); Q = np.stack([cx + a * np.cos(t), a * np.sin(t), np.full(48, -0.0022)], -1)
        d = np.roll(Q, -1, 0) - Q; m = (Q + np.roll(Q, -1, 0)) / 2; R = P[:, None] - m[None]; Rn = np.linalg.norm(R, axis=-1)[..., None]
        return mu0 / (4 * np.pi) * 48 * (np.cross(d[None], R) / Rn ** 3).sum(1)
    xs = np.linspace(0, max(0.02, depth), 9); P = np.stack([xs, 0 * xs, np.full(9, -depth)], -1)
    G = lf(-c, P) - lf(c, P)
    GRAD_CACHE[depth] = (xs, G); return xs, G
def target_signal(name, depth, I, t, channel="mono"):
    a, s, fe = TARGETS[name]; tau = tau1(a, s)
    btx, mono = channel_coupling(depth)
    amp = (2 * math.pi * a ** 3 / mu0) * np.linalg.norm(btx) * I
    if channel == "mono": c = np.linalg.norm(mono)
    else:
        xs, G = grad_rx(round(depth, 4)); c = float(np.abs(G[:, 0]).max() + np.abs(G[:, 2]).max())
    k = 1.0 if not fe else 0.6                                    # nail: weaker eddy part, plus magnetic tail
    v = amp * c * S_t(tau, t) * k
    if fe: v = v + amp * c * 3e4 * (t / 20e-6) ** -0.5 * np.exp(-t / 400e-6) * 0.15   # magnetic relaxation tail
    return v
def ground_signal(t, mineral):              # viscous magnetic soil: ~1/t, amplitude by mineralisation class
    G0 = {"mild": 0.3e-6, "moderate": 3e-6, "heavy": 30e-6}[mineral]
    return G0 * (10e-6 / t)
def vlf_inphase(name):                     # rotating-field (5 kHz) in-phase response sign: + ferrous, - conductor
    a, s, fe = TARGETS[name]
    if fe: return +1.0
    k = np.sqrt(1j * 2 * math.pi * 5e3 * mu0 * s); x = k * a
    chi = -1.5 * (1 + 3 / x ** 2 - 3 / (x * np.tanh(x)))
    return float(np.real(chi))
# detection depth per channel / mode (air and ground)
def det_depth(name, mode, channel, mineral=None):
    I = MODES[mode]["I_tx"]; best = 0
    for d in np.linspace(0.02, 0.9, 89):
        v = target_signal(name, d, I, GATES, channel)
        if mineral:   # after dual ground balance: residual ground 2 % (imperfect) + full noise
            snr = np.abs(v).max() / (VN + 0.02 * ground_signal(GATES, mineral).max())
        else: snr = np.abs(v).max() / VN
        if snr > 3.0: best = d
    return round(best * 1000)
detect = {}
for nm in TARGETS:
    detect[nm] = {f"{ch} {md}{' ' + mn if mn else ''}": det_depth(nm, md, ch, mn)
                  for ch in ("mono", "grad") for md in ("normal", "boost") for mn in (None, "moderate")}

# ---------------- 3. DSP chain ----------------
# ground balance with two gate pairs (holes at different tau) -> combined channel has no hole
def gb_pair(G, i, j): return G[i] - (GATES[j] / GATES[i]) * G[j]     # cancels A/t exactly
def tau_hole(i, j): return (GATES[j] - GATES[i]) / math.log(GATES[j] / GATES[i])
holes = {"pair 10/20 us": round(tau_hole(1, 2) * 1e6, 1), "pair 40/80 us": round(tau_hole(3, 4) * 1e6, 1)}
TAU_GRID = np.logspace(np.log10(1e-6), np.log10(1e-3), 160)
BASIS = np.array([S_t(tq, GATES) for tq in TAU_GRID])                 # (ntau, ngates)
def fit_tau(G):
    """least squares: G = A*S(tau,t) + Gnd/t ; scan tau, solve linear (A, Gnd)"""
    best = (1e99, None)
    Xg = 1 / GATES
    for k, tq in enumerate(TAU_GRID):
        M = np.c_[BASIS[k], Xg]; coef, *_ = np.linalg.lstsq(M / VN, G / VN, rcond=None)
        res = np.sum(((M @ coef) - G) ** 2)
        if res < best[0] and coef[0] > 0: best = (res, (tq, coef[0], coef[1]))
    return best[1]
CLASSES = ["iron", "foil / tiny", "small gold or pull-tab zone", "medium gold", "large gold / coin"]
def classify(tau, ferrous):
    if ferrous: return "iron"
    if tau < 3e-6: return "foil / tiny"
    if tau < 25e-6: return "small gold or pull-tab zone"
    if tau < 120e-6: return "medium gold"
    return "large gold / coin"
def gold_accept(cls): return cls in ("small gold or pull-tab zone", "medium gold", "large gold / coin")
def two_sensor_depth(vm, vg):
    """depth from gradiometer/mono ratio (size-independent): invert pre-computed ratio curve"""
    return None
# depth-ratio calibration curve
dgrid = np.linspace(0.03, 0.5, 40)
ratio = []
for d in dgrid:
    btx, mono = channel_coupling(d); xs, G = grad_rx(round(d, 4))
    ratio.append((np.abs(G[:, 0]).max() + np.abs(G[:, 2]).max()) / np.linalg.norm(mono))
ratio = np.array(ratio)
# Monte Carlo
TRUE = {"gold 0.1 g": "gold", "gold 1 g": "gold", "gold 10 g": "gold", "gold 50 g": "gold", "aluminium foil": "trash",
        "pull-tab": "trash", "silver coin": "non-gold metal", "iron nail": "iron"}
conf = {nm: {c: 0 for c in CLASSES + ["not detected"]} for nm in TARGETS}
gold_mode = {nm: dict(sounded=0, trials=0) for nm in TARGETS}
depth_err = []
for nm in TARGETS:
    for trial in range(120):
        d = rng.uniform(0.03, 0.25); mineral = rng.choice(["mild", "moderate"])
        I = MODES["boost"]["I_tx"]
        v = target_signal(nm, d, I, GATES) * rng.uniform(0.6, 1.6)      # size/shape spread
        G = v + ground_signal(GATES, mineral) * rng.uniform(0.7, 1.3) + rng.normal(0, VN, len(GATES))
        gb = max(abs(gb_pair(G, 1, 2)), abs(gb_pair(G, 3, 4)))
        gold_mode[nm]["trials"] += 1
        if gb < 4 * VN: conf[nm]["not detected"] += 1; continue
        fit = fit_tau(G)
        if fit is None: conf[nm]["not detected"] += 1; continue
        fe = vlf_inphase(nm) + rng.normal(0, 0.3) > 0.4
        cls = classify(fit[0], fe); conf[nm][cls] += 1
        if gold_accept(cls): gold_mode[nm]["sounded"] += 1
        vg = target_signal(nm, d, I, GATES, "grad")
        rr = np.abs(vg).max() / max(np.abs(v).max(), 1e-30)
        d_est = float(np.interp(rr, ratio[::-1], dgrid[::-1]))
        depth_err.append(abs(d_est - d))
gold_mode_pct = {nm: round(100 * v["sounded"] / v["trials"]) for nm, v in gold_mode.items()}

# ---------------- 5. power / battery / thermal ----------------
L1, R1 = 222.6e-6, 0.16        # outer band, 4 sections in parallel (from wire paths)
L2, R2 = 59.2e-6, 0.073        # inner band 26-60.4 mm, 4 sections in parallel (from wire paths)
pw = {}
for mname, M in MODES.items():
    I = M["I_tx"]; prf = M["prf"]; Vs = 24.0
    E = 0.5 * L1 * I ** 2 + 0.5 * L2 * (0.56 * I) ** 2
    t_ramp = L1 * I / Vs; duty = (t_ramp / 3 + 60e-6) * prf
    p_cu = (I ** 2 * R1 + (0.56 * I) ** 2 * R2) * duty
    p_tx = E * prf * (1 - 0.75) + p_cu                     # 75 % flyback energy recovery
    R_xy = 1.72e-8 * 28.8 / (1.8e-3 * 70e-6)               # per axis: 28.8 m of 1.8 mm, 2 oz trace (~3.9 ohm)
    p_xy = 2 * 0.5 * M["I_xy"] ** 2 * R_xy                  # two axes, sine drive (rms = peak/sqrt2)
    p_sys = 1.6                                            # MCU+ADC+preamps+audio
    P = p_tx + p_xy + p_sys
    pw[mname] = dict(I_peak_A=I, ramp_us=round(t_ramp * 1e6, 1), pulse_energy_mJ=round(E * 1e3, 2), copper_W=round(p_cu, 2),
                     tx_W=round(p_tx, 2), xy_W=round(p_xy, 2), system_W=round(P, 2),
                     hours_on_4S1P_50Wh=round(50 / P, 1), hours_on_4S2P_100Wh=round(100 / P, 1), R_xy_ohm=round(R_xy,2))
report = dict(field=field, detection_depth_mm=detect, ground_balance_holes_us=holes,
              classifier_confusion=conf, gold_mode_sound_pct=gold_mode_pct,
              depth_estimate_mean_abs_error_mm=round(1000 * float(np.mean(depth_err)), 1), power=pw,
              notes=["Target signals use an equivalent conducting-sphere model; foil and pull-tabs are flat in reality.",
                     "Ferrous flag uses the rotating-field (5 kHz) in-phase sign; nail model is empirical.",
                     "Noise floor 1 uV per gate; residual ground after balancing 2 %.",
                     "Pull-tabs overlap small gold in decay time - GOLD mode cannot reject them by physics alone."])
json.dump(report, open(f"{OUT}/system_simulation.json", "w"), indent=1, default=float)
print(json.dumps({k: report[k] for k in ("field", "ground_balance_holes_us", "gold_mode_sound_pct", "depth_estimate_mean_abs_error_mm", "power")}, indent=1))
print(json.dumps(detect, indent=1))
