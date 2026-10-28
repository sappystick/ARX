#!/usr/bin/env python3
"""PHI-FOLD 233 receive DSP: Python reference of the firmware chain (OPEN_ITEMS 5; owner request 2026-10-28). MODELED: synthetic gate data from the
physics below, no bench data. The C firmware core (fw/dsp/pf_dsp.c) is tested against this file's vectors (fw/tests).

Per pulse and per quadrupole channel (QUAD-A, QUAD-B) the ADC frames inside each of the 9 golden-ratio gates (fw_timeline.json: t_first 5.91 us x 1.618^k)
are averaged: g_k. Noise of a gate mean scales as 1/sqrt(frames in the gate) (frame 0.84 us), so the gate weights are w_k = n_k.
Signal model per channel (gate means):  g_k = a * phi_k(tau) + b * psi_k + air_k + noise
  phi_k(tau) = mean of exp(-t / tau) over gate k   (a conductive target: first-order eddy decay)
  psi_k      = mean of 1 / t over gate k           (magnetically viscous ground: the 1/t law of superparamagnetic soils)
  air_k      = the no-target response (TX leak / ring residual), tracked as a running mean while nothing is detected.
Ground balance: the ground amplitudes b_A / b_B are TRACKED slowly (exponential average of the free 2-term fit over frames without a target) and HELD in the
per-frame fit; refitting b every frame lets the 1/t term absorb short-tau targets (foil, small gold: their early-gate shape is close to 1/t).
Fit: for every tau of a log-spaced bank (2 us .. 3 ms, 64 values) a_A, a_B are closed-form weighted least squares on g - b PSI (shared tau); the tau with the
least summed weighted residual wins and is refined by a parabola in log(tau).
Outputs per averaged frame: tau, amplitudes a_A / a_B, SNR = |a| / sigma_a (sigma from the LS covariance), bearing axis = 0.5 atan2(a_B, a_A) + 45 deg
(mod 180, ENHANCEMENT_REVIEW s.6), class from tau windows (ASSUMPTIONS 40), and, over a pass, side (axis rotation sense x gyro yaw sign, sweep_track.py),
pinpoint (RSS null between two peaks) and depth from the peak spacing (lobe offset vs depth from the coil model: sweep_track passes).
Evaluation (written to kit_v23/dsp_ref.json): tau estimation error vs SNR, class confusion, ground rejection (a strongly viscous ground with no target must
not fire), bearing error, and the test vectors for the C port.
usage (in work/): python3 dsp_ref.py"""
import sys, json, math
import numpy as np
TL = json.load(open("kit_v23/fw_timeline.json")); GATES = np.array(TL["inputs"]["gates_us"]) * 1e-6; FRAME = TL["inputs"]["adc_frame_us"] * 1e-6
NK = np.maximum(1, np.floor((GATES[:, 1] - GATES[:, 0]) / FRAME)); W = NK / NK.sum()          # gate weights (frames per gate)
TAUS = np.geomspace(2e-6, 3e-3, 64)
CLASSES = [("foil / tiny", 0, 10e-6), ("small gold or pull-tab zone", 10e-6, 40e-6), ("medium gold", 40e-6, 200e-6), ("large gold / coin", 200e-6, 700e-6), ("iron", 700e-6, 1.0)]
def phi(tau, g=GATES):
    t0, t1 = g[:, 0], g[:, 1]; return tau / (t1 - t0) * (np.exp(-t0 / tau) - np.exp(-t1 / tau))
def psi(g=GATES):
    t0, t1 = g[:, 0], g[:, 1]; return np.log(t1 / t0) / (t1 - t0) * 1e-6        # scaled to O(1) per gate
PSI = psi(); PHI = np.array([phi(t) for t in TAUS])                               # bank: 64 x 9
def fit_channel(g, P):
    """weighted LS of g = a P + b PSI; returns a, b, residual for one basis row P"""
    S11 = np.sum(W * P * P); S12 = np.sum(W * P * PSI); S22 = np.sum(W * PSI * PSI); r1 = np.sum(W * P * g); r2 = np.sum(W * PSI * g)
    det = S11 * S22 - S12 * S12; a = (r1 * S22 - r2 * S12) / det; b = (S11 * r2 - S12 * r1) / det
    res = g - a * P - b * PSI; return a, b, float(np.sum(W * res * res)), S22 / det    # last: var factor of a
def fit_fixed(gA, gB, bA, bB):
    """per-frame target fit with the ground amplitudes HELD at the tracked values (ground balance): g - b PSI = a phi(tau); 1 parameter per channel and tau.
    Refitting b on every frame lets the 1/t ground term absorb short-tau targets (foil, small gold), whose early-gate shape is close to 1/t."""
    hA = gA - bA * PSI; hB = gB - bB * PSI
    def one(P):
        S = np.sum(W * P * P); aA = np.sum(W * P * hA) / S; aB = np.sum(W * P * hB) / S
        return aA, aB, float(np.sum(W * (hA - aA * P) ** 2) + np.sum(W * (hB - aB * P) ** 2)), 1.0 / S
    costs = np.empty(len(TAUS)); fits = []
    for i, P in enumerate(PHI): f = one(P); costs[i] = f[2]; fits.append(f)
    i = int(np.argmin(costs))
    if 0 < i < len(TAUS) - 1:
        y0, y1, y2 = costs[i - 1], costs[i], costs[i + 1]; den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if den > 0 else 0.0; tau = math.exp(math.log(TAUS[i]) + d * math.log(TAUS[1] / TAUS[0]))
    else: tau = TAUS[i]
    aA, aB, res, v = one(phi(tau)); return tau, aA, aB, bA, bB, res, v
def fit_ridge(gA, gB, bA, bB, sig0, sb):
    """per-frame target fit with the ground HELD at the tracked b and a Gaussian prior on its deviation delta_b ~ N(0, sb^2) (sb: expected ground change
    along the sweep): minimise sum_k W r_k^2 + lam delta_b^2, lam = sig0^2 / (N sb^2) (the weighted chi^2 with frame noise sig0). Small ground drift is
    absorbed by delta_b; a short-tau target is not, because the prior keeps delta_b near zero. Returns tau, aA, aB, var factor of a (posterior)."""
    lam = sig0 ** 2 / (NK.sum() * max(sb, 1e-12) ** 2); hA = gA - bA * PSI; hB = gB - bB * PSI
    S22 = np.sum(W * PSI * PSI) + lam
    def one(P):
        S11 = np.sum(W * P * P); S12 = np.sum(W * P * PSI); det = S11 * S22 - S12 * S12; tot = 0.0; a = []
        for h in (hA, hB):
            r1 = np.sum(W * P * h); r2 = np.sum(W * PSI * h); ai = (r1 * S22 - r2 * S12) / det; di = (S11 * r2 - S12 * r1) / det
            tot += float(np.sum(W * (h - ai * P - di * PSI) ** 2) + lam * di * di); a.append(ai)
        return a[0], a[1], tot, S22 / det
    costs = np.empty(len(TAUS))
    for i, P in enumerate(PHI): costs[i] = one(P)[2]
    i = int(np.argmin(costs)); tau = golden(lambda lt: one(phi(math.exp(lt)))[2], math.log(TAUS[max(i - 1, 0)]), math.log(TAUS[min(i + 1, len(TAUS) - 1)]))
    aA, aB, res, v = one(phi(tau)); return tau, aA, aB, v
GR_ = (math.sqrt(5) - 1) / 2
def golden(f, lo, hi, it=24):
    """golden-section minimum of f on [lo, hi] (log tau): the grid gives the bracket, this the maximum-likelihood tau to 1e-5 in log tau"""
    a, b = lo, hi; c = b - GR_ * (b - a); d = a + GR_ * (b - a); fc, fd = f(c), f(d)
    for _ in range(it):
        if fc < fd: b, d, fd = d, c, fc; c = b - GR_ * (b - a); fc = f(c)
        else: a, c, fc = c, d, fd; d = a + GR_ * (b - a); fd = f(d)
    return math.exp((a + b) / 2)
def crb_tau_rel(tau, snr):
    """Cramer-Rao bound on the relative tau error for a known-shape exponential in the 9 gates (amplitude unknown): Fisher matrix of (a, ln tau)"""
    P = phi(tau); dP = (phi(tau * 1.001) - phi(tau / 1.001)) / (2 * math.log(1.001)); n = NK
    F = np.array([[np.sum(n * P * P), np.sum(n * P * dP)], [np.sum(n * P * dP), np.sum(n * dP * dP)]]) * (snr ** 2 / np.sum(n * P * P))
    return math.sqrt(np.linalg.inv(F)[1, 1])
class GroundTracker:
    """slow ground balance: the ground amplitude per channel from the free 2-term fit of frames without a target, exponential average (alpha per frame)"""
    def __init__(s, alpha=0.05): s.alpha = alpha; s.bA = 0.0; s.bB = 0.0
    def update(s, gA, gB):
        """target-free frame: ground only (1-term weighted LS on PSI); the free 2-term fit splits the 1/t ground between both terms and biases b"""
        S = np.sum(W * PSI * PSI); bA = np.sum(W * PSI * gA) / S; bB = np.sum(W * PSI * gB) / S
        s.bA += s.alpha * (bA - s.bA); s.bB += s.alpha * (bB - s.bB)
def fit(gA, gB):
    """joint free fit over the bank (target and ground both free; used by the ground tracker); returns tau, aA, aB, bA, bB, residual, var factor"""
    best = None; costs = np.empty(len(TAUS))
    for i, P in enumerate(PHI):
        aA, bA, rA, vA = fit_channel(gA, P); aB, bB, rB, vB = fit_channel(gB, P); costs[i] = rA + rB
        if best is None or costs[i] < best[0]: best = (costs[i], i, aA, aB, bA, bB, vA)
    i = best[1]
    if 0 < i < len(TAUS) - 1:                                                     # parabola in log tau
        y0, y1, y2 = costs[i - 1], costs[i], costs[i + 1]; den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if den > 0 else 0.0; lt = math.log(TAUS[i]) + d * math.log(TAUS[1] / TAUS[0])
        tau = math.exp(lt); P = phi(tau); aA, bA, rA, vA = fit_channel(gA, P); aB, bB, rB, vB = fit_channel(gB, P)
        return tau, aA, aB, bA, bB, rA + rB, vA
    return TAUS[i], best[2], best[3], best[4], best[5], best[0], best[6]
def classify(tau): return next(c for c, lo, hi in CLASSES if lo <= tau < hi)
def axis_deg(aA, aB): return (0.5 * math.degrees(math.atan2(aB, aA)) + 45.0) % 180.0
def synth(rng, tau, amp, bearing_deg, ground, sigma, air=None):
    """gate means of one averaged frame for QUAD-A / QUAD-B: a target at bearing (quad response cos / sin of 2 (bearing - 45)), viscous ground (equal in
    both quads x a small residual: the quad pair nulls a uniform half-space; 2 % imbalance ASSUMED), gate noise sigma / sqrt(n_k), and an air term"""
    th = math.radians(2 * (bearing_deg - 45.0)); P = phi(tau); air = np.zeros(9) if air is None else air
    gA = amp * math.cos(th) * P + 0.02 * ground * PSI + air + rng.normal(0, 1, 9) * sigma / np.sqrt(NK)
    gB = amp * math.sin(th) * P + 0.02 * ground * PSI + air + rng.normal(0, 1, 9) * sigma / np.sqrt(NK)
    return gA, gB
def snr_of(aA, aB, v, sigma):
    """detection statistic |a| / sigma_a; with W = n_k / N the LS variance of a is sigma0^2 / (N S) = sigma0^2 v / N (sigma0: noise of ONE frame)"""
    return math.hypot(aA, aB) / (sigma * math.sqrt(v / NK.sum()) + 1e-30)
def sigma_for(snr, tau, amp=1.0):
    """frame noise sigma0 that gives the matched-filter SNR^2 = sum_k (amp phi_k)^2 n_k / sigma0^2 for this target"""
    return amp * math.sqrt(float(np.sum(phi(tau) ** 2 * NK))) / snr
if __name__ == "__main__":
    rng = np.random.default_rng(233); out = dict(status="MODELED: synthetic gate data (exponential target + 1/t ground + gate noise), no bench data",
                                                gates_us=(GATES * 1e6).round(3).tolist(), frames_per_gate=NK.astype(int).tolist(), taus=len(TAUS), classes=[(c, lo, hi) for c, lo, hi in CLASSES])
    # 1 tau accuracy vs SNR (sigma chosen so the requested SNR results), bearing error
    acc = {}
    for snr_t in (5, 10, 30, 100):
        errs, berr, cls_ok = [], [], 0; trials = 0
        for tau in (6e-6, 18e-6, 95e-6, 300e-6, 1.2e-3):
            for _ in range(60):
                b = rng.uniform(0, 180); sg = sigma_for(snr_t, tau); gA, gB = synth(rng, tau, 1.0, b, 0.0, sg)
                t, aA, aB, _v = fit_ridge(gA, gB, 0.0, 0.0, sg, 1e-4); errs.append(abs(math.log(t / tau))); be = (axis_deg(aA, aB) - b + 90) % 180 - 90; berr.append(abs(be))
                cls_ok += classify(t) == classify(tau); trials += 1
        crb = float(np.median([crb_tau_rel(t_, snr_t) for t_ in (6e-6, 18e-6, 95e-6, 300e-6, 1.2e-3)]))
        E = np.array(errs).reshape(5, 60); eff = [float(np.sqrt(np.mean(E[j] ** 2))) / crb_tau_rel(t_, snr_t) for j, t_ in enumerate((6e-6, 18e-6, 95e-6, 300e-6, 1.2e-3))]
        acc[snr_t] = dict(crb_tau_rel_median_pct=round(100 * crb, 2), tau_err_rms_over_crb_per_tau=[round(e, 2) for e, in zip(eff)], tau_err_rms_over_crb=round(max(eff), 2), tau_err_median_pct=round(100 * (math.exp(float(np.median(errs))) - 1), 2), tau_err_p90_pct=round(100 * (math.exp(float(np.percentile(errs, 90))) - 1), 2),
                          bearing_err_median_deg=round(float(np.median(berr)), 2), bearing_err_p90_deg=round(float(np.percentile(berr, 90)), 2), class_correct_pct=round(100 * cls_ok / trials, 1))
    out["accuracy_vs_snr"] = acc
    # 2 ground rejection: strong viscous ground, no target: the fitted target amplitude must stay below the 4-sigma threshold
    fires = 0; N = 300; sigma = 1e-3; gt = GroundTracker()
    for _ in range(200): gA, gB = synth(rng, 50e-6, 0.0, 0.0, ground=5.0, sigma=sigma); gt.update(gA, gB)          # settle over target-free ground
    for k in range(N):
        gr = 5.0 * (1 + 0.1 * math.sin(2 * math.pi * k / 150))                                                     # ground varying +-10 % along the sweep
        gA, gB = synth(rng, 50e-6, 0.0, 0.0, ground=gr, sigma=sigma)
        t, aA, aB, v = fit_ridge(gA, gB, gt.bA, gt.bB, sigma, 0.1 * math.hypot(gt.bA, gt.bB) + 1e-4); hit = snr_of(aA, aB, v, sigma) >= 4.0; fires += hit
        if not hit: gt.update(gA, gB)
    # small gold over strong ground with the ground held: still found
    found = 0
    for _ in range(100):
        gA, gB = synth(rng, 18e-6, 0.05, 30.0, ground=5.0, sigma=sigma); t, aA, aB, v = fit_ridge(gA, gB, gt.bA, gt.bB, sigma, 0.1 * math.hypot(gt.bA, gt.bB) + 1e-4)
        found += snr_of(aA, aB, v, sigma) >= 4.0 and classify(t) == "small gold or pull-tab zone"
    sg_snr = 0.05 * math.sqrt(float(np.sum(phi(18e-6) ** 2 * NK))) / sigma
    out["ground_rejection"] = dict(ground_scale=5.0, ground_variation_pct=10, trials=N, false_detections=int(fires), false_rate_pct=round(100 * fires / N, 2),
                                   small_gold_over_ground_found_pct=found, small_gold_snr=round(sg_snr, 1))
    # 3 test vectors for the C port (fixed seed): inputs and the reference outputs
    vec = []
    for k, (tau, amp, b, gr) in enumerate([(6e-6, 1.0, 20, 0), (18e-6, 0.5, 100, 1), (95e-6, 0.3, 300 % 180, 2), (300e-6, 1.0, 60, 0), (1.2e-3, 0.8, 150, 3), (50e-6, 0.0, 0, 5)]):
        bA = bB = 0.02 * gr; sb = 0.1 * math.hypot(bA, bB) + 1e-4
        gA, gB = synth(rng, tau, amp, b, gr, 2e-3); t, aA, aB, v = fit_ridge(gA, gB, bA, bB, 2e-3, sb)
        vec.append(dict(gA=gA.tolist(), gB=gB.tolist(), bA=bA, bB=bB, sig0=2e-3, sb=sb, tau=t, aA=aA, aB=aB, v=v, axis=axis_deg(aA, aB), snr=snr_of(aA, aB, v, 2e-3), cls=classify(t)))
    out["vectors"] = vec
    c = out["accuracy_vs_snr"]
    out["checks"] = dict(tau_estimator_within_1p5x_crb_at_snr30=c[30]["tau_err_rms_over_crb"] <= 1.5, class_correct_ge_80pct_at_snr10=c[10]["class_correct_pct"] >= 80.0,
                         bearing_err_median_le_5deg_at_snr10=c[10]["bearing_err_median_deg"] <= 5.0, ground_false_rate_le_1pct=out["ground_rejection"]["false_rate_pct"] <= 1.0,
                         small_gold_over_ground_ge_90pct=out["ground_rejection"]["small_gold_over_ground_found_pct"] >= 90)
    out["ok"] = all(out["checks"].values())
    json.dump(out, open("kit_v23/dsp_ref.json", "w"), indent=1)
    for k, v in acc.items(): print("SNR", k, v)
    print("ground", out["ground_rejection"]); print(out["checks"]); print("OK" if out["ok"] else "FAIL"); sys.exit(0 if out["ok"] else 1)
