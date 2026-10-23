#!/usr/bin/env python3
"""
Analog front-end checks for the 5-channel receiving module (GX, GY, X8, Y8, MONO).
Component noise/GBW numbers are datasheet-class values taken from memory (no datasheet access here):
every one is listed in the verification table of the build report.
"""
import io, contextlib, math, json, numpy as np
from scipy.special import ellipk, ellipe
mu0 = 4e-7 * math.pi; KB = 1.380649e-23; T = 300.0
ant = json.load(open("out_board/antenna_model.json"))
# ------------------------------------------------------------ circuit values (single source of truth, also used by the schematic generator)
CIRC = dict(VDD=5.0, VREF=4.096, VCM=2.048, ADC_FS=4.096, ADC_BITS=16, FS_SPS=1.0e6, ADC_SNR_dB=91.0,
            en_nV=1.1, in_pA=1.7, GBW_MHz=45.0, Rg=10.0, Rf=390.0, Cf_pF=22.0, Raaf=200.0, Caaf_nF=2.0, Riso=22.0, Ciso_nF=1.0,
            Rs={"GX": 47.0, "GY": 47.0, "X8": 1000.0, "Y8": 1000.0, "MONO": 1000.0})
G1 = 1 + CIRC["Rf"] / CIRC["Rg"]
fc_aaf = 1 / (2 * math.pi * CIRC["Raaf"] * CIRC["Caaf_nF"] * 1e-9)
def vn(R): return math.sqrt(4 * KB * T * R)
out = {"gain_stage1": G1, "gain_dB": round(20 * math.log10(G1), 1), "AAF_fc_kHz": round(fc_aaf / 1e3, 1),
       "stage1_closed_loop_BW_MHz": round(CIRC["GBW_MHz"] / G1, 2)}
# ---------------------------------------------------------------- noise budget per channel
Rcoil = {"GX": ant["GX"]["R_dc_ohm"], "GY": ant["GY"]["R_dc_ohm"], "X8": ant["X8"]["R_dc_ohm"], "Y8": ant["Y8"]["R_dc_ohm"], "MONO": 0.4}
noise = {}
ENBW = fc_aaf * math.pi / 2
adc_noise_rms = CIRC["ADC_FS"] / (2 * math.sqrt(2)) / 10 ** (CIRC["ADC_SNR_dB"] / 20)       # V rms over fs/2
for ch in ("GX", "GY", "X8", "Y8", "MONO"):
    Rsrc = Rcoil[ch] + CIRC["Rs"][ch]; Rpar = CIRC["Rg"] * CIRC["Rf"] / (CIRC["Rg"] + CIRC["Rf"])
    e2 = dict(coil=vn(Rcoil[ch]) ** 2, Rs=vn(CIRC["Rs"][ch]) ** 2, opamp_en=(CIRC["en_nV"] * 1e-9) ** 2,
              opamp_in=(CIRC["in_pA"] * 1e-12 * Rsrc) ** 2, Rg_Rf=vn(Rpar) ** 2 + (CIRC["in_pA"] * 1e-12 * Rpar) ** 2)
    tot = math.sqrt(sum(e2.values()))
    n_an = tot * math.sqrt(ENBW)                                  # input-referred rms in the AAF noise bandwidth
    n_adc = adc_noise_rms / G1
    n_all = math.hypot(n_an, n_adc)
    row = {k: round(math.sqrt(v) * 1e9, 3) for k, v in e2.items()}
    row.update(total_input_nV_rtHz=round(tot * 1e9, 3), analog_rms_uV=round(n_an * 1e6, 3), adc_rms_input_uV=round(n_adc * 1e6, 3),
              total_rms_per_sample_uV=round(n_all * 1e6, 3),
              gate_noise_uV={f"{g} us": round(n_all * 1e6 / math.sqrt(max(1, g)), 3) for g in (5, 10, 20, 40, 80, 160)},
              avg64_gate_noise_uV={f"{g} us": round(n_all * 1e6 / math.sqrt(max(1, g) * 64), 3) for g in (5, 10, 20, 40, 80, 160)})
    noise[ch] = row
out["noise"] = noise
# ---------------------------------------------------------------- dynamic range / clipping
swing = CIRC["ADC_FS"] / 2 * 0.95
out["dynamic_range"] = dict(max_input_before_clip_mV=round(swing / G1 * 1e3, 1), LSB_input_uV=round(CIRC["ADC_FS"] / 2 ** 16 / G1 * 1e6, 2),
                            dynamic_range_dB=round(20 * math.log10(swing / G1 / (noise["GX"]["total_rms_per_sample_uV"] * 1e-6)), 1))
# ---------------------------------------------------------------- clamp survivability using the antenna model's induced voltages
surv = {}
for ch in ("GX", "GY", "X8", "Y8"):
    Rs = CIRC["Rs"][ch]
    v_norm = ant[ch].get("Vinduced_at_turnoff_V_(20A,1us,0.5mm_shift)", 0.0)
    v_gx = max(v_norm, ant["GX" if ch[0] == "G" else "X8"].get("Vinduced_at_turnoff_V_(20A,1us,0.5mm_shift)", 0.0))   # worst direction (GY null is first-order zero along x only)
    v_fault = ant[ch]["Vinduced_one_lobe_uncancelled_V"]
    i_clamp_norm = max(v_gx - 0.7 - 2.5, 0) / Rs; i_fault = max(v_fault - 3.2, 0) / Rs
    surv[ch] = dict(Rs_ohm=Rs, V_turnoff_at_0p5mm_misalign=round(v_gx, 2), clamp_current_mA_normal=round(i_clamp_norm * 1e3, 1),
                    V_fault_one_lobe_uncancelled=round(v_fault, 1), clamp_peak_current_A_fault_1us=round(i_fault, 2),
                    verdict=("OK" if i_fault < 4.0 else "FAULT CASE EXCEEDS BAV199 4.5 A 1 us SURGE - needs bigger Rs or TVS") + (" / normal OK" if i_clamp_norm < 0.1 else " / normal EXCEEDS 100 mA"))
out["clamp_survivability"] = surv
# ---------------------------------------------------------------- frequency response (stage 1 + AAF + isolation network), antenna low-pass
f = np.logspace(3, 7.2, 400); s = 2j * np.pi * f
def H(ch):
    L = ant[ch]["L_uH"] * 1e-6; Rc = Rcoil[ch]; C = ant[ch].get("C_eff_pF_est", 20) * 1e-12 + 10e-12   # + op-amp / clamp pin capacitance
    Rs = CIRC["Rs"][ch]
    Hant = 1 / (1 + s * (Rc + Rs) * C + s ** 2 * L * C)                                        # open-circuit coil -> pin
    Hamp = G1 / (1 + s * G1 / (2 * np.pi * CIRC["GBW_MHz"] * 1e6))
    Haaf = 1 / (1 + s * CIRC["Raaf"] * CIRC["Caaf_nF"] * 1e-9)
    Hbuf = 1 / (1 + s * CIRC["Riso"] * CIRC["Ciso_nF"] * 1e-9)
    return Hant * Hamp * Haaf * Hbuf
resp = {}
for ch in ("GX", "X8"):
    h = np.abs(H(ch)); k3 = f[np.argmax(h < h[0] / math.sqrt(2))]
    resp[ch] = dict(gain_dB_1kHz=round(20 * math.log10(h[0]), 1), f3dB_kHz=round(k3 / 1e3, 0),
                    peak_dB=round(20 * math.log10(h.max() / h[0]), 2), f_at_peak_kHz=round(f[np.argmax(h)] / 1e3, 0))
out["response"] = resp
# time-domain step response of the whole chain (settling for the first gate)
t = np.arange(0, 20e-6, 1e-9)
def step_response(ch):
    # discretise with scipy.signal
    from scipy import signal
    L = ant[ch]["L_uH"] * 1e-6; Rc = Rcoil[ch]; C = ant[ch].get("C_eff_pF_est", 20) * 1e-12 + 10e-12; Rs = CIRC["Rs"][ch]
    den = np.polymul([L * C, (Rc + Rs) * C, 1], np.polymul([G1 / (2 * np.pi * CIRC["GBW_MHz"] * 1e6), 1],
          np.polymul([CIRC["Raaf"] * CIRC["Caaf_nF"] * 1e-9, 1], [CIRC["Riso"] * CIRC["Ciso_nF"] * 1e-9, 1])))
    sys_ = signal.TransferFunction([G1], den); tt, y = signal.step(sys_, T=t); return tt, y / y[-1]
steps = {}
for ch in ("GX", "X8"):
    tt, y = step_response(ch)
    steps[ch] = dict(t_10_90_us=round((tt[np.argmax(y > .9)] - tt[np.argmax(y > .1)]) * 1e6, 3),
                     t_settle_1pct_us=round(float(tt[np.where(np.abs(y - 1) > .01)[0][-1]] * 1e6), 2),
                     t_settle_0p01pct_us=round(float(tt[np.where(np.abs(y - 1) > 1e-4)[0][-1]] * 1e6), 2), overshoot_pct=round(float((y.max() - 1) * 100), 2))
out["step_response"] = steps
# ---------------------------------------------------------------- link budget with the real antenna numbers and real noise
exec(open("band_study.py").read().split("A=0.5e-6")[0])      # TX, HUB ring sets (ring model of the real build)
def loop_BrBz(a, zc, r, z):
    dz = z - zc; r = np.maximum(r, 1e-9); k2 = 4 * a * r / ((a + r) ** 2 + dz ** 2); K, E = ellipk(k2), ellipe(k2)
    den = np.sqrt((a + r) ** 2 + dz ** 2); d2 = (a - r) ** 2 + dz ** 2
    return (mu0 / (2 * np.pi) * dz / (r * den) * (-K + (a * a + r * r + dz * dz) / d2 * E),
            mu0 / (2 * np.pi) / den * (K + (a * a - r * r - dz * dz) / d2 * E))
def Btx(r, z):
    br = np.zeros_like(r, float); bz = np.zeros_like(r, float)
    for rings, I in ((TX, 1.0), (HUB, 0.56)):
        for a, zc, n in rings:
            b1, b2 = loop_BrBz(a, zc, r, z); br += n * I * b1; bz += n * I * b2
    return br / 4.0, bz / 4.0                                    # per terminal amp (4 sections in parallel)
src_b = open("rx_board.py").read().split("# ---------------- writers ----------------")[0]
ns = {}
with contextlib.redirect_stdout(io.StringIO()): exec(src_b, ns)
pats, LAYER_Z = ns["pats"], ns["LAYER_Z"]
def series_path(n):
    P = pats[n]; La, Lb = P["layers"]
    return np.concatenate([np.c_[tr, np.full(len(tr), LAYER_Z[L])] for tr, L in ((P["tracks"][La][0], La), (P["tracks"][Lb][0], Lb), (P["tracks"][La][1], La))])
def seg_mid(P, ds=0.8):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]; tq = np.arange(0, s[-1], ds)
    Q = np.c_[[np.interp(tq, s, P[:, k]) for k in range(3)]].T; return (Q[1:] + Q[:-1]) / 2 * 1e-3, (Q[1:] - Q[:-1]) * 1e-3
SEG = {n: seg_mid(series_path(n)) for n in pats}
def Bant(n, pts):
    m, d = SEG[n]; B = np.zeros((len(pts), 3))
    for i in range(0, len(m), 5000):
        R = pts[:, None] - m[None, i:i + 5000]; Rn = np.linalg.norm(R, axis=-1)[..., None]
        B += (np.cross(d[None, i:i + 5000], R) / Rn ** 3).sum(1)
    return mu0 / (4 * math.pi) * B
def Skern(tau, tt):
    n = np.arange(1, 60); tn = tau / n ** 2
    return (6 / (n * n * math.pi ** 2) / tn * np.exp(-np.asarray(tt)[..., None] / tn)).sum(-1)
TARG = {"gold 1 g": (2.3e-3, 1.5e7), "gold 10 g": (5.0e-3, 1.5e7), "silver coin": (8.0e-3, 3.0e7)}
I_TX = 8.0; GATE_T = {"GX": 5e-6, "GY": 5e-6, "X8": 20e-6, "Y8": 20e-6}
depths_scan = np.array([25, 50, 75, 100, 150, 200, 250, 300.0])
link = {}
for ch in ("GX", "X8"):
    link[ch] = {}
    for tn, (ra, sg) in TARG.items():
        tau = mu0 * sg * ra ** 2 / math.pi ** 2; best = {}
        for z in depths_scan:
            lat = np.linspace(0, 1.3 * z, 14) * 1e-3
            pts = np.array([[x, y, -z * 1e-3] for x in lat for y in (0.0,)] + [[0.0, y, -z * 1e-3] for y in lat[1:]])
            r_ = np.hypot(pts[:, 0], pts[:, 1]); br, bz = Btx(r_, pts[:, 2])
            ph = np.arctan2(pts[:, 1], pts[:, 0]); btx = np.stack([br * np.cos(ph), br * np.sin(ph), bz], -1)
            bn = np.linalg.norm(btx, axis=1); bhat = btx / bn[:, None]
            ba = Bant(ch, pts); c = np.abs(np.einsum("ij,ij->i", ba, bhat))
            V = (2 * math.pi * ra ** 3 / mu0) * bn * I_TX * c * Skern(tau, GATE_T[ch]) * 1.0
            best[z] = float(V.max())
        gate_us = GATE_T[ch] * 1e6; key = f"{int(gate_us)} us"
        n_gate = noise[ch]["avg64_gate_noise_uV"][key] * 1e-6; n_gate1 = noise[ch]["gate_noise_uV"][key] * 1e-6
        d1 = max([z for z in depths_scan if best[z] > 3 * n_gate1] or [0]); d64 = max([z for z in depths_scan if best[z] > 3 * n_gate] or [0])
        link[ch][tn] = dict(V_uV_by_depth={int(z): round(best[z] * 1e6, 4) for z in depths_scan}, depth_SNR3_single_frame_mm=int(d1), depth_SNR3_64frames_mm=int(d64))
        print(ch, tn, link[ch][tn]["depth_SNR3_single_frame_mm"], link[ch][tn]["depth_SNR3_64frames_mm"], flush=True)
out["link_budget_8A_scan"] = link
out["power_analog_board_mW"] = dict(opamps=round(5 * 2 * 3.6e-3 * 5 * 1e3, 0), adcs=round(5 * 16, 0), reference_and_buffers=round(8e-3 * 5 * 1e3 + 4 * 5, 0), total=None)
out["power_analog_board_mW"]["total"] = sum(v for k, v in out["power_analog_board_mW"].items() if k != "total")
json.dump(out, open("out_board/afe_analysis.json", "w"), indent=1, default=float)
print(json.dumps({k: out[k] for k in ("gain_stage1", "AAF_fc_kHz", "dynamic_range", "response", "step_response", "clamp_survivability", "power_analog_board_mW")}, indent=1, default=float))
print({ch: {k: noise[ch][k] for k in ("total_input_nV_rtHz", "total_rms_per_sample_uV")} for ch in noise})
