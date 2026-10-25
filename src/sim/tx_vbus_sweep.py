#!/usr/bin/env python3
"""TX stage over the whole 7S pack range (19.6-29.4 V) and the firmware on-time rule (upgrade list, transmit coil and driver).
sim_head1.py runs the TX stage at a fixed Vbus = 26 V. This script reuses its physics (same topology, same part values) with Vbus as a parameter, checks
that it reproduces the stored 26 V rows, and adds (a) the constant-current on-time ton(V), with and without loop resistance and bulk-capacitor droop,
(b) the sensitivity of the delivered peak current to the firmware's knowledge of V, L and R, (c) the PB1R bulk capacitor voltage and droop budget.
Everything is MODELED; the assumptions are docs/ASSUMPTIONS.md 28-29."""
import json, math, csv
import numpy as np
from scipy.integrate import solve_ivp

L = 54e-6; Rc = 0.045; Cn = 500e-12; Rd = 330.0; Vf = 1.2; Ron = 0.05; RCL = 5e3          # as sim_head1.py
R_SHUNT = 0.010                                                                           # RS1S 10 mohm Kelvin shunt (PB1R BOM)
R_WIRE = 0.008                                                                            # AWG12 pair 0.8 m (5.2 mohm/m each way) + TXJ1/lead joints, ASSUMPTIONS 28
R_LOOP = Rc + Ron + R_SHUNT + R_WIRE
N_BULK = 9; C_BULK_NOM = N_BULK * 100e-6; C_BULK_TOL = 0.8                                                 # CB1-CB9 Panasonic EEHZC1H101P (DATASHEET_LOG), -20 % tolerance/ageing, ASSUMPTIONS 28
V_MIN, V_MAX, V_REF = 19.6, 29.4, 26.0                                                    # 7S1P: BMS cut-off 2.8 V/cell, full charge 4.2 V/cell
DROOP_BUDGET = 0.05                                                                       # fraction of VBUS (system_budget.py)
CD_RATING_OLD, CD_RATING_NEW = 35.0, 50.0

def pulse(I0, CL, Vbus, f=400.0, derate=False, ton=None):
    """turn-off of the coil from I0, identical to sim_head1.pulse() except that Vbus is an argument"""
    T = 1 / f; ton = L * I0 / Vbus if ton is None else ton; vc0 = 0.0; Vk = 462.0
    Cfun = (lambda v: CL / (1 + (abs(v) / Vk) ** 2)) if derate else (lambda v: CL)
    for it in range(10):
        def rhs(t, y):
            i, vd, vc = y; iD = max(0.0, vd - vc - Vf) / Ron
            return [(-vd - Rc * i) / L, (i - vd / Rd - iD) / Cn, (iD - vc / RCL) / Cfun(vc)]
        te = np.linspace(0, 60e-6, 6000)
        s = solve_ivp(rhs, [0, 60e-6], [I0, 0.0, vc0], t_eval=te, method="Radau", rtol=1e-7, atol=[1e-6, 1e-4, 1e-4], max_step=2e-8)
        t, i, vd, vc = s.t, s.y[0], s.y[1], s.y[2]
        rest = T - 60e-6 - ton; vc_end = vc[-1] * math.exp(-rest / (RCL * CL))
        if abs(vc_end - vc0) < 0.5: break
        vc0 = vc_end
    iD = np.maximum(0, vd - vc - Vf) / Ron; dt = t[1] - t[0]
    nz = np.where(i <= 0)[0]; t_zero = t[nz[0]] if len(nz) else float("nan")
    bad = np.where((np.abs(vd) > 1.0) | (np.abs(i) > 2e-3))[0]; t_quiet = t[bad[-1] + 1] if len(bad) else 0.0
    Ercl = float(np.sum(vc ** 2 / RCL) * dt) + vc[-1] ** 2 / RCL * (RCL * CL / 2) * (1 - math.exp(-2 * rest / (RCL * CL)))
    return dict(Vbus=Vbus, I0=I0, CL_nF=CL * 1e9, derated=derate, ton_us=ton * 1e6, vd_peak=float(vd.max()), vc_peak=float(vc.max()), Vds_peak=float(vd.max() + Vbus),
                t_zero_us=t_zero * 1e6, t_quiet_us=t_quiet * 1e6, P_RCL_W=Ercl * f, P_damp_W=float(np.sum(vd ** 2 / Rd) * dt) * f, peak_i_diode=float(iD.max()))

def ton_lossless(I, V, Lc=L): return Lc * I / V

def _ramp(V, R, C, Lc):
    def rhs(t, y): i, q = y; return [(V - (q / C if C else 0.0) - R * i) / Lc, i]
    return rhs

def ton_loop(I, V, R=R_LOOP, C=None, Lc=L):
    """time for the coil current to reach I from a supply V through the loop resistance R; with C the bulk capacitor sags as it delivers the charge. Returns (ton, charge drawn from the bank)"""
    ev = lambda t, y: y[0] - I; ev.terminal = True; ev.direction = 1
    s = solve_ivp(_ramp(V, R, C, Lc), [0, 200e-6], [0.0, 0.0], events=ev, rtol=1e-9, atol=1e-12, max_step=1e-7)
    return float(s.t_events[0][0]), float(s.y_events[0][0][1])

def peak_current(ton, V, R=R_LOOP, C=None, Lc=L):
    """coil current reached after a fixed on-time ton"""
    s = solve_ivp(_ramp(V, R, C, Lc), [0, ton], [0.0, 0.0], rtol=1e-9, atol=1e-12, max_step=1e-7); return float(s.y[0][-1])

out = dict(assumptions=dict(L_uH=L * 1e6, R_loop_mohm=R_LOOP * 1e3, R_parts_mohm=dict(coil=Rc * 1e3, fets=Ron * 1e3, shunt=R_SHUNT * 1e3, wire=R_WIRE * 1e3), C_bulk_nom_uF=C_BULK_NOM * 1e6, C_bulk_tol=C_BULK_TOL, V_range=[V_MIN, V_MAX]))

# 1. validation: the 26 V rows of sim_head1
ref = {r["case"]: r for r in json.load(open("kit_v20/sim_head1.json"))["tx_stage"]}
chk = {}
for nm, C, dr in (("100 nF C0G/film", 100e-9, False), ("as built: 2 x 100 nF X7R, with DC-bias derating", 200e-9, True)):
    r = pulse(20, C, V_REF, derate=dr); q = ref[nm]
    chk[nm] = dict(Vds_new=round(r["Vds_peak"], 2), Vds_sim_head1=round(q["Vds_peak"], 2), t_quiet_new=round(r["t_quiet_us"], 3), t_quiet_sim_head1=round(q["t_quiet_us"], 3), P_RCL_new=round(r["P_RCL_W"], 3), P_RCL_sim_head1=round(q["P_RCL_W"], 3))
out["validation_vs_sim_head1_26V"] = chk
out["validation_ok"] = all(abs(v["Vds_new"] - v["Vds_sim_head1"]) < 0.5 and abs(v["t_quiet_new"] - v["t_quiet_sim_head1"]) < 0.05 and abs(v["P_RCL_new"] - v["P_RCL_sim_head1"]) < 0.05 for v in chk.values())

# 2. TX stage over the pack range at 20 A (constant current: the turn-off sees the same I0 at every V)
rows = []
for V in (V_MIN, V_REF, V_MAX):
    for nm, C, dr in (("100 nF C0G/film (design)", 100e-9, False), ("2 x 100 nF X7R derated (as built)", 200e-9, True)):
        r = pulse(20, C, V, derate=dr); r["case"] = nm; rows.append(r)
out["tx_stage_vs_vbus"] = rows

# 3. on-time rule
tab = []
for I, f in ((8, 800.0), (14, 600.0), (20, 400.0)):
    for V in (V_MIN, V_REF, V_MAX):
        ton_l = ton_lossless(I, V); ton_r = ton_loop(I, V)[0]; ton_c, Q = ton_loop(I, V, C=C_BULK_NOM * C_BULK_TOL)
        tab.append(dict(I_A=I, f_Hz=f, V=V, ton_lossless_us=round(ton_l * 1e6, 2), ton_loop_us=round(ton_r * 1e6, 2), ton_loop_droop_us=round(ton_c * 1e6, 2),
                        I_if_lossless_ton_A=round(peak_current(ton_l, V, C=C_BULK_NOM * C_BULK_TOL), 2), duty_pct=round(ton_c * f * 100, 3),
                        charge_uC=round(Q * 1e6, 1), droop_V=round(Q / (C_BULK_NOM * C_BULK_TOL), 3), droop_pct=round(Q / (C_BULK_NOM * C_BULK_TOL) / V * 100, 2),
                        supply_energy_mJ=round(V * Q * 1e3, 3), half_LI2_mJ=round(0.5 * L * I * I * 1e3, 3)))
out["ton_rule"] = tab

# 4. sensitivity of the delivered peak current to what the firmware assumes (rule: on-time from the loop model at nominal L and R, with the measured V)
Cb = C_BULK_NOM * C_BULK_TOL; sens = []
for V in (V_MIN, V_MAX):
    ton = ton_loop(20, V, C=Cb)[0]
    cases = (("nominal", dict()), ("V measured 1 % high (ton too short)", dict(ton=ton_loop(20, V * 1.01, C=Cb)[0])), ("V measured 1 % low (ton too long)", dict(ton=ton_loop(20, V * 0.99, C=Cb)[0])),
             ("coil L +5 %", dict(Lc=L * 1.05)), ("coil L -5 %", dict(Lc=L * 0.95)), ("R_loop +25 % (hot FETs, joints)", dict(R=R_LOOP * 1.25)), ("ton timer 1 us late", dict(ton=ton + 1e-6)),
             ("lossless rule L I / V used instead", dict(ton=ton_lossless(20, V))))
    for what, kw in cases:
        Ia = peak_current(kw.get("ton", ton), V, R=kw.get("R", R_LOOP), C=Cb, Lc=kw.get("Lc", L))
        sens.append(dict(V=V, case=what, ton_us=round(kw.get("ton", ton) * 1e6, 2), I_peak_A=round(Ia, 2), error_pct=round((Ia / 20 - 1) * 100, 2)))
out["current_sensitivity"] = sens

# 5. PB1R bulk bank: voltage derating and droop
Qmax = max(r["charge_uC"] for r in tab if r["I_A"] == 20) * 1e-6
need = {str(V): round(max(r["charge_uC"] for r in tab if r["I_A"] == 20 and r["V"] == V) * 1e-6 / (DROOP_BUDGET * V) * 1e6, 0) for V in (V_MIN, V_REF, V_MAX)}
out["bulk_bank"] = dict(CD_rating_old_V=CD_RATING_OLD, CD_rating_new_V=CD_RATING_NEW, util_old_pct=round(V_MAX / CD_RATING_OLD * 100, 1), util_new_pct=round(V_MAX / CD_RATING_NEW * 100, 1),
                        min_effective_uF_for_5pct_droop=need, bank_effective_uF=C_BULK_NOM * C_BULK_TOL * 1e6, bank_nominal_uF=C_BULK_NOM * 1e6,
                        n_caps=N_BULK, min_nominal_uF_per_cap=round(max(need.values()) / N_BULK / C_BULK_TOL, 0))

# 6. firmware look-up table (V in 0.5 V steps), for the Python-first DSP/firmware work (OPEN_ITEMS 5)
with open("kit_v23/TX_ONTIME_LUT.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["V_bus", "ton_8A_us", "ton_14A_us", "ton_20A_us"])
    for V in np.arange(19.5, 29.51, 0.5): w.writerow([f"{V:.1f}"] + [f"{ton_loop(I, V, C=C_BULK_NOM * C_BULK_TOL)[0] * 1e6:.2f}" for I in (8, 14, 20)])
json.dump(out, open("kit_v23/tx_vbus.json", "w"), indent=1, default=float)

try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    Vs = np.linspace(V_MIN, V_MAX, 40); fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    ax[0].plot(Vs, [ton_lossless(20, v) * 1e6 for v in Vs], label="L I / V"); ax[0].plot(Vs, [ton_loop(20, v, C=C_BULK_NOM * C_BULK_TOL)[0] * 1e6 for v in Vs], label="with loop R and bulk droop")
    ax[0].set(xlabel="VBUS (V)", ylabel="on-time for 20 A (us)", title="Firmware on-time rule"); ax[0].legend(); ax[0].grid(alpha=.3)
    for nm in ("100 nF C0G/film (design)", "2 x 100 nF X7R derated (as built)"):
        ax[1].plot([r["Vbus"] for r in rows if r["case"] == nm], [r["Vds_peak"] for r in rows if r["case"] == nm], "o-", label=nm)
    ax[1].axhline(650, color="r", ls="--", lw=1); ax[1].set(xlabel="VBUS (V)", ylabel="Vds peak (V)", title="Drain peak, 20 A (FET 650 V)"); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig("kit_v23/TX_VBUS_SWEEP.png", dpi=130)
except Exception as e: print("figure skipped:", e)

print("validation vs sim_head1 (26 V):", out["validation_ok"], chk)
for r in rows: print(f"V {r['Vbus']:5} {r['case'][:34]:34} Vds {r['Vds_peak']:6.1f}  zero {r['t_zero_us']:.2f}  quiet {r['t_quiet_us']:.2f} us  RCL {r['P_RCL_W']:.2f} W  damp {r['P_damp_W']:.2f} W")
for r in tab: print(r)
for r in sens: print(r)
print(out["bulk_bank"])
