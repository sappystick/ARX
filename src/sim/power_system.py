#!/usr/bin/env python3
"""PHI-FOLD 233 power system design basis (one-piece coil). All numbers computed here feed the board and mechanical designs."""
import math, json
OUT = {}
# ---------------------------------------------------------------- coil (from onepiece_report.json)
rep = json.load(open("kit_v3/onepiece_report.json"))["electrical"]
L1, R1 = rep["outer"]["all4_parallel_L_uH"] * 1e-6, rep["outer"]["all4_parallel_R_ohm"]
L2, R2 = rep["inner"]["all4_parallel_L_uH"] * 1e-6, rep["inner"]["all4_parallel_R_ohm"]
RATIO = 0.372
OUT["coil"] = dict(L_outer_uH=L1 * 1e6, R_outer_ohm=R1, L_inner_uH=L2 * 1e6, R_inner_ohm=R2, inner_current_ratio=RATIO)
# ---------------------------------------------------------------- battery pack
CELL = dict(name="18650 Li-ion, 3.5 Ah, 8 A cont. (Samsung 35E / LG MJ1 class)", Ah=3.5, Vmax=4.2, Vnom=3.7, Vmin=3.0, mass_g=48.0, Imax_cont=8.0, dia=18.6, length=65.0)
NS = 7
V_full, V_nom, V_cut = NS * CELL["Vmax"], NS * CELL["Vnom"], NS * CELL["Vmin"]
E_cart = NS * CELL["Ah"] * CELL["Vnom"]
OUT["pack"] = dict(cell=CELL["name"], config="7S1P per cartridge, two cartridges (A and B)", V_full=V_full, V_nom=V_nom, V_cutoff=V_cut, energy_Wh_per_cartridge=round(E_cart, 1),
                   energy_Wh_both=round(2 * E_cart, 1), cell_mass_g=NS * CELL["mass_g"], est_cartridge_mass_g=round(NS * CELL["mass_g"] + 125, 0),
                   cartridge_length_mm=NS * CELL["length"] + 30, note="24 V or higher requirement: 24.5 V (7S at 3.5 V/cell) .. 29.4 V")
# ---------------------------------------------------------------- TX stage timing and energy
def stage(I, prf, Vbat=V_nom, Vclamp=500.0, t_hold=60e-6):
    I2 = RATIO * I
    t_ramp = L1 * I / Vbat                                  # outer band ramp (inner follows with its own current limit)
    duty = (t_ramp / 3 + t_hold) * prf
    E = 0.5 * L1 * I ** 2 + 0.5 * L2 * I2 ** 2
    P_clamp = E * prf                                       # dissipative clamp
    P_cu = (I ** 2 * R1 + I2 ** 2 * R2) * duty
    t_off = L1 * I / Vclamp
    i_rms = I * math.sqrt(duty)
    q = I * (t_ramp / 2 + t_hold)
    return dict(I_peak_A=I, I_inner_A=round(I2, 2), prf_Hz=prf, ramp_us=round(t_ramp * 1e6, 1), duty_pct=round(duty * 100, 2), i_rms_A=round(i_rms, 2),
                pulse_energy_mJ=round(E * 1e3, 2), clamp_dissipation_W=round(P_clamp, 2), coil_copper_W=round(P_cu, 2),
                turn_off_time_us_at_500V=round(t_off * 1e6, 2), turn_off_time_us_at_400V=round(L1 * I / 400 * 1e6, 2),
                charge_per_pulse_mC=round(q * 1e3, 2))
OUT["tx_stage"] = {"scan_8A_800Hz": stage(8, 800), "boost_20A_800Hz": stage(20, 800), "boost_20A_300Hz": stage(20, 300), "boost_14A_800Hz": stage(14, 800)}
# ---------------------------------------------------------------- bulk capacitance (droop) in the driver can
for k, s in list(OUT["tx_stage"].items()):
    q = s["charge_per_pulse_mC"] * 1e-3
    s["bulk_droop_V"] = {f"{c} uF": round(q / (c * 1e-6), 2) for c in (470, 940)}
# ---------------------------------------------------------------- FET sizing (SiC/Si), clamp parts
OUT["fet_sizing"] = dict(
    rating_V=">= 650", I_pulse_A=">= 40 (33 A equal-depth boost case)", Rds_on_hot_budget_mohm=30,
    conduction_W_boost=round(OUT["tx_stage"]["boost_20A_300Hz"]["i_rms_A"] ** 2 * 0.030 * 1.6, 2),
    note="two 650 V devices in parallel per outer channel; inner channel needs a 100 V class device only (clamp ~60 V)")
OUT["inner_channel"] = dict(clamp_V=round(L2 * RATIO * 20 / (L1 * 20 / 500.0), 1), note="inner band L is 7x smaller: equal turn-off time needs only ~1/20 of the clamp voltage")
# ---------------------------------------------------------------- hot swap / precharge
Cb = 1.5e-3; R_pre = 22.0; dV = V_full - 5.0
OUT["hot_swap"] = dict(bulk_C_mF=Cb * 1e3, precharge_R_ohm=R_pre, peak_inrush_A=round(dV / R_pre, 2), precharge_tau_ms=round(R_pre * Cb * 1e3, 1), energy_in_resistor_J=round(0.5 * Cb * dV ** 2, 2),
                       resistor_power_rating_W=">= 2 W pulse-rated (0.6 J per event, 5 s repeat)", contact_mate_sequence="PACK- (1.5 mm longer) -> PRECHARGE+ via 22 ohm (0.8 mm longer) -> PACK+ main -> ID/1-wire",
                       swap_rule="the cartridge with the higher terminal voltage carries the load; the other idles through its OR-ing diode")
# ---------------------------------------------------------------- aux loads and runtime
aux = dict(analog_boards_W=0.32 * 2, controller_W=1.2, audio_W=0.5, xy_drive_W_trigger=3.93, losses_pct=12)
def runtime(scan_mode, E_Wh):
    s = OUT["tx_stage"]["scan_8A_800Hz"] if scan_mode else OUT["tx_stage"]["boost_20A_300Hz"]
    P = s["clamp_dissipation_W"] + s["coil_copper_W"] + aux["analog_boards_W"] + aux["controller_W"] + aux["audio_W"] + (0 if scan_mode else aux["xy_drive_W_trigger"])
    P *= 1 + aux["losses_pct"] / 100
    return round(P, 2), round(E_Wh / P, 1)
for nm, sc in (("scan", True), ("trigger_boost_300Hz", False)):
    P, h1 = runtime(sc, E_cart); OUT.setdefault("runtime", {})[nm] = dict(battery_W=P, hours_one_cartridge=h1, hours_two_cartridges=round(2 * h1, 1))
# ---------------------------------------------------------------- cable / wiring
rho = 1.72e-8; A16 = 1.31e-6
OUT["wiring"] = dict(vbat_pair="2 x AWG16 (1.31 mm2) + 2 x AWG16 return, 0.9 m", drop_at_2A_mV=round(2 * 0.9 * rho / A16 * 2 * 1e3, 1), coil_leads="4 x AWG12 equivalent per band bundle, 0.15 m (driver can at the neck)",
                     coil_cable_L_uH_est=round(2 * 0.15 * 0.5, 2), rs485="1 twisted pair AWG26", aux="+12 V AWG24 pair", shield="overall braid, one-end grounded at the driver can")
# ---------------------------------------------------------------- protection coordination
OUT["protection"] = dict(
    cell_level="BMS 7S per cartridge: OVP 4.25 V/cell, UVP 2.8 V/cell (pack 19.6 V hard cut, soft warning 21.0 V), OCP 12 A (>2 s), SCP 40 A / 200 us, OTP 60 C, balance 60 mA",
    cartridge_fuse="5 A slow-blow, 32 V DC rated, in the PM1 board per cartridge path",
    load_dump="TVS SMDJ33A on the OR-ed bus (stand-off 33 V, clamp 53 V), 1.5 kW 10/1000 us",
    reverse="OR-ing Schottky diodes block reverse; contact keying prevents reverse insertion",
    inrush="22 ohm precharge via early contact",
    undervoltage_lockout="supervisor releases the TX driver only when the bus is between 21 V and 30 V",
    tx_fault="hardware current limit (comparator, 30 A) removes the gate drive within 300 ns; MCU watchdog disables TX if pulses stop or timing is wrong",
    thermal="NTC on the FET heat spreader (trip 90 C) and in each cartridge")
# ---------------------------------------------------------------- shielding physics (honest)
mu0 = 4e-7 * math.pi; sig = 5.8e7
def skin(f): return 1 / math.sqrt(math.pi * f * mu0 * sig)
sh = {}
for f in (5e3, 20e3, 100e3, 1e6, 10e6):
    d = skin(f); t = 35e-6
    sh[f"{f/1e3:g} kHz"] = dict(skin_depth_mm=round(d * 1e3, 3), absorption_dB_35um_Cu=round(8.686 * t / d, 2))
OUT["shielding"] = dict(copper_foil_35um=sh, conclusion="35 um copper foil is an effective ELECTRIC-field/RF shield above ~1 MHz but gives almost no magnetic shielding at the 5-100 kHz pulse frequencies; "
                        "isolation of the pulsed power stage therefore relies on distance, twisted/coaxial routing, local bulk capacitors, a closed current loop in the driver can, "
                        "and keeping the analog board AB1 gate-blanked during TX edges")
json.dump(OUT, open("kit_v3/power_system.json", "w"), indent=1, default=float)
print(json.dumps({k: OUT[k] for k in ("pack", "tx_stage", "hot_swap", "runtime")}, indent=1, default=float))
