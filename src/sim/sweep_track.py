#!/usr/bin/env python3
"""Sweep tracking and pinpoint (owner idea 2026-10-28): as the head sweeps over a target the LED marker should travel from one side, through the centre,
to the other; the user centres the target, then holds the trigger (boost) over it. MODELED with the receive-coil model of sim_quadbearing.py (TX field x
reciprocal RX-Q weighting, QUAD-A and QUAD-B rotated 45 deg, the only active receive channels: X8 / Y8 are spare and MONO idle, DESIGN_STATE).
Per sample: A, B (quad outputs), axis = 0.5 atan2(B, A) + 45 deg (mod 180; ENHANCEMENT_REVIEW s.6), RSS = hypot(A, B).
Findings checked here:
(1) a pass rotates the axis continuously through 180 deg (LED marker moves around and across the ring without jumps, except the 180 deg flip of a target
    passing exactly under the centre, which the display shows on the centre ring);
(2) the quad pair alone cannot tell which side of the sweep line a target is on: rotating the whole scene (target and motion) by 180 deg gives identical A, B
    at every instant (mod-180 bearing). With the sweep direction known (the CB1D-C2 BMI270 yaw gyro), the rotation sense of the axis gives the side:
    the target moves at -vx relative to the head, so dphi/dt = +y vx / rho^2;
(3) pinpoint: the quad response is ZERO directly under the centre (null between two peaks); the centre estimate = the RSS minimum between the two peaks;
(4) trigger boost: 20 A vs 8 A scan -> dipole moment 7.96 vs 3.19 A m^2 (sim_head1 moment), signal x 2.5 (+8 dB) at the same depth, MODELED.
Writes kit_v23/sweep_track.json and kit_v23/sweep_track.png. usage (in work/): python3 sweep_track.py"""
import sys, json, math
import numpy as np
src = open("sim_quadbearing.py").read().split("out={}")[0]; ns = {}; exec(src, ns)
TXB, Bvec_many, quadA, quadB = ns["TXB"], ns["Bvec_many"], ns["quadA"], ns["quadB"]
STEP = 0.005; XS = np.arange(-0.25, 0.25 + 1e-9, STEP)
def response(x_rel, y_rel, depth):
    pts = np.c_[x_rel, y_rel, np.full(len(x_rel), -depth)]; Bt = TXB(pts)
    A = np.einsum("ij,ij->i", Bt, Bvec_many(quadA, pts)); B = np.einsum("ij,ij->i", Bt, Bvec_many(quadB, pts)); return A, B
def axis_deg(A, B): return (0.5 * np.degrees(np.arctan2(B, A)) + 45.0) % 180.0
def unwrap180(a): return np.degrees(np.unwrap(np.radians(a) * 2) / 2)
def resolve(A, B, vx):
    """full bearing (deg, 0..360) of the target relative to the head, from the mod-180 axis and the sweep direction sign vx (+1 / -1): side from the axis rate"""
    ax = unwrap180(axis_deg(A, B)); rate = np.gradient(ax); side = np.sign(np.median(rate[np.abs(rate) > 1e-6])) * np.sign(vx)   # sign(y) of the target
    full = np.where(np.sin(np.radians(ax)) * side >= 0, ax, ax + 180.0) % 360.0
    return full, int(side)
def pinpoint(rss, smooth=1):
    """centre estimate (index): smooth, take the largest peak, then the largest peak on the other side at least 60 mm away (the two quad lobes sit
    +-50..110 mm from the centre for 100-200 mm depth), and return the RSS minimum between them; with one peak only, the peak (closest approach)"""
    r = np.convolve(rss, np.ones(smooth) / smooth, "same") if smooth > 1 else rss
    i1 = int(np.argmax(r)); far = [i for i in range(len(r)) if abs(i - i1) * STEP >= 0.06]
    if not far: return i1
    i2 = max(far, key=lambda i: r[i])
    if r[i2] < 0.25 * r[i1]: return i1
    a, b = sorted((i1, i2)); return a + int(np.argmin(r[a:b + 1]))
if __name__ == "__main__":
    out = dict(status="MODELED: noise-free coil model, straight sweep, point target; sweep direction from the CB1D-C2 BMI270 yaw gyro (in the design 2026-10-28, not built)", passes=[], checks={})
    side_ok = True; mirror_identical = True; cont_ok = True; pin_err = []; mirror_max = 0.0
    for depth in (0.10, 0.20):
        for y0 in (-0.06, -0.03, 0.0, 0.03, 0.06):
            for vx in (1, -1):                                   # head sweep direction along x; the target moves -vx relative to the head
                xr = -vx * XS                                    # relative x over time
                A, B = response(xr, np.full_like(xr, y0), depth); rss = np.hypot(A, B)
                Am, Bm = response(-xr, np.full_like(xr, -y0), depth)            # 180-deg rotated scene
                mdiff = float(np.max(np.hypot(A - Am, B - Bm)) / np.max(np.hypot(A, B))); mirror_max = max(mirror_max, mdiff); mirror_identical &= mdiff < 1e-3   # 6 golden-angle petals: tiny residual
                ax = unwrap180(axis_deg(A, B)); sig = rss > 0.05 * rss.max()
                jumps = np.abs(np.diff(ax))[sig[1:] & sig[:-1]]
                if abs(y0) > 1e-9:
                    cont_ok &= bool(jumps.max() < 15.0) and abs(ax[sig][-1] - ax[sig][0]) > 120
                    full, side = resolve(A[sig], B[sig], vx); side_ok &= side == int(np.sign(y0))
                ic = pinpoint(rss); x_hat = xr[ic]; pin_err.append(abs(x_hat) * 1e3)
                out["passes"].append(dict(depth_mm=int(depth * 1e3), offset_mm=round(y0 * 1e3), sweep=vx, rss_centre_over_peak=round(float(rss[np.argmin(np.abs(xr))] / rss.max()), 3),
                                          peak_x_mm=round(float(xr[np.argmax(rss)] * 1e3)), axis_turn_deg=round(float(abs(ax[sig][-1] - ax[sig][0])), 1), max_step_deg=round(float(jumps.max()), 2) if len(jumps) else None,
                                          pinpoint_err_mm=round(float(abs(x_hat) * 1e3), 1)))
    # pinpoint under receive noise: white noise on A and B (sigma = pass peak / SNR), 200 passes, 3-point smoothing; centred target (offset 0) and 30 mm off
    rng = np.random.default_rng(233); noisy = {}
    for depth in (0.10, 0.20):
        for y0 in (0.0, 0.03):
            A, B = response(XS, np.full_like(XS, y0), depth); pk = np.hypot(A, B).max()
            for snr in (10, 30):
                e = []
                for _ in range(200):
                    An = A + rng.normal(0, pk / snr, len(A)); Bn = B + rng.normal(0, pk / snr, len(B))
                    e.append(abs(XS[pinpoint(np.hypot(An, Bn), smooth=5)]) * 1e3)
                noisy[f"depth {int(depth * 1e3)} mm, offset {int(y0 * 1e3)} mm, SNR {snr}"] = dict(p50_mm=round(float(np.percentile(e, 50)), 1), p95_mm=round(float(np.percentile(e, 95)), 1))
    out["pinpoint_noise"] = noisy; out["pinpoint_noise_note"] = "per-sample SNR after the firmware averaging; samples every 5 mm of head travel; 5-sample (25 mm) smoothing"
    # sweep direction from the CB1D-C2 yaw gyro (BMI270, DATASHEET_LOG): zero-rate offset +-0.5 dps at 25 C, +-0.015 dps/K -> +-1.1 dps worst over 0-65 C (40 K);
    # a swing of 0.3-1.5 m/s at the head on a 1.2 m radius (ASSUMED) is 14-72 dps, so the sign of the yaw rate is known with >= 12x margin before any filtering
    off = 0.5 + 0.015 * 40; rates = [math.degrees(v / 1.2) for v in (0.3, 1.5)]
    out["gyro"] = dict(part="BMI270 (CB1D-C2 UG)", offset_worst_dps=off, sweep_rate_dps=[round(r, 1) for r in rates], sign_margin=round(rates[0] / off, 1))
    moment = dict(scan_8A=3.19, boost_20A=7.96)
    cont_ok, mirror_identical, side_ok = bool(cont_ok), bool(mirror_identical), bool(side_ok); pin_err = [float(e) for e in pin_err]
    out["checks"] = dict(axis_continuous_and_turns=cont_ok, mirror_scene_identical_without_direction=mirror_identical, mirror_max_rel_diff=round(mirror_max, 6), side_resolved_with_sweep_direction=side_ok,
                         centre_null=bool(all(p["rss_centre_over_peak"] < 1e-3 for p in out["passes"] if p["offset_mm"] == 0)),
                         pinpoint_err_max_mm=max(pin_err), pinpoint_within_10mm=bool(max(pin_err) <= 10.0),
                         pinpoint_noisy_median_le_15mm=bool(all(v['p50_mm'] <= 15 for v in noisy.values())), gyro_sign_margin_ge_5=bool(out['gyro']['sign_margin'] >= 5), boost_signal_ratio=round(moment["boost_20A"] / moment["scan_8A"], 2), boost_gain_dB=round(20 * math.log10(moment["boost_20A"] / moment["scan_8A"]), 1))
    out["ok"] = all(v for v in out["checks"].values() if isinstance(v, bool))
    json.dump(out, open("kit_v23/sweep_track.json", "w"), indent=1)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax2 = plt.subplots(1, 2, figsize=(10, 3.4))
    for y0, c in ((0.0, "k"), (0.03, "tab:blue"), (0.06, "tab:green"), (-0.03, "tab:red")):
        A, B = response(XS, np.full_like(XS, y0), 0.10); r = np.hypot(A, B)
        ax2[0].plot(XS * 1e3, r / np.hypot(*response(XS, np.full_like(XS, 0.0), 0.10)).max(), c, label=f"offset {y0 * 1e3:+.0f} mm")
        s = r > 0.05 * r.max(); ax2[1].plot((XS * 1e3)[s], unwrap180(axis_deg(A, B))[s], c, label=f"offset {y0 * 1e3:+.0f} mm")
    ax2[0].set(xlabel="target x relative to the head centre (mm)", ylabel="quad RSS (rel.)", title="depth 100 mm: null under the centre, a peak each side"); ax2[0].legend(fontsize=7)
    ax2[1].set(xlabel="target x relative to the head centre (mm)", ylabel="axis bearing (deg, unwrapped)", title="axis turns through 180 deg; side flips the sense"); ax2[1].legend(fontsize=7)
    fig.suptitle("Sweep over a point target (MODELED, sim_quadbearing coil model)", fontsize=9); fig.tight_layout(); fig.savefig("kit_v23/sweep_track.png", dpi=110)
    for k, v in out["checks"].items(): print(f"{k:42s} {v}")
    print("OK" if out["ok"] else "FAIL"); sys.exit(0 if out["ok"] else 1)
