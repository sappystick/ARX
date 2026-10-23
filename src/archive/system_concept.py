#!/usr/bin/env python3
"""PHI-FOLD 233 v6 system concept numbers: head shielding, potting, thermal, ribbon cassette, masses, cavity ratings."""
import json, math, os
import numpy as np
os.makedirs("kit_v6", exist_ok=True)
mu0 = 4e-7 * math.pi; OUT = {}
ps = json.load(open("kit_v3/power_system.json")); op = json.load(open("kit_v3/onepiece_report.json"))["electrical"]
# ---------------------------------------------------------------- 1. field inside the head electronics bay and shielding
fm = np.load("out_system_v5/fieldmap_Bmag_per_A.npy"); zg = np.linspace(-0.40, 0.10, 101); rg = np.linspace(0, 0.30, 121)
def B_at(r, z): return float(fm[np.argmin(abs(zg - z)), np.argmin(abs(rg - r))])
B_bay = B_at(0.0, 0.017)                                                   # T per terminal amp, bay centre
tx = ps["tx_stage"]; t_off = {"scan_8A": tx["scan_8A_800Hz"]["turn_off_time_us_at_500V"] * 1e-6, "boost_20A": tx["boost_20A_300Hz"]["turn_off_time_us_at_500V"] * 1e-6}
shield = {}
for t in (2.0, 3.0, 5.0, 8.0):                                              # ferrite wall thickness, mm; MnZn mu_r 2000, bay radius 22 mm
    S = 1 + 2000 * t / (2 * 22.0); shield[f"{t:g} mm"] = dict(S_closed_can=round(S, 0), dB=round(20 * math.log10(S), 1))
emf = {}
for k, I in (("scan_8A", 8.0), ("boost_20A", 20.0)):
    dBdt = B_bay * I / t_off[k]
    emf[k] = dict(B_bay_mT=round(B_bay * I * 1e3, 2), dBdt_T_per_s=round(dBdt, 0), EMF_V_full_board_loop_1p26cm2=round(1.26e-3 * dBdt, 2), EMF_V_typical_loop_1cm2=round(1e-4 * dBdt, 3),
                  EMF_mV_after_40dB_shield=round(1.26e-3 * dBdt / 100 * 1e3, 1), EMF_mV_after_47dB_shield_5mm=round(1.26e-3 * dBdt / 228 * 1e3, 1))
OUT["head_bay_field"] = dict(B_bay_uT_per_A=round(B_bay * 1e6, 1), turn_off_us=dict((k, round(v * 1e6, 2)) for k, v in t_off.items()), shield_factor_vs_ferrite_wall=shield, induced_EMF_in_board_loops=emf,
    design_rules=["closed ferrite can: tube + top cap + bottom cap, all MnZn mu_r >= 2000, wall >= 5 mm for 47 dB (3 mm gives 42 dB)", "cable and flow penetrations <= 4 mm and through the SIDE wall, never through a cap centre",
                  "board loops: route returns directly under signals; keep each board's enclosed loop area under 1 cm2", "AB1 BLANK asserted from before TX turn-off until 2-3 us after (cuts the residual EMF)"],
    note="S = 1 + mu_r t / (2 a) is the transverse closed-cylinder estimate; axial shielding of a can with end caps is lower and must be measured.")
# ---------------------------------------------------------------- 2. potting materials
mat = {
 "syntactic silicone (Pt-cure 2-part + glass bubbles 35-40 vol%)": dict(density=0.75, k=0.15, eps_r=2.6, hardness="Shore A 35-50", Tmax_C=200, exotherm="very low (addition cure, <10 K in 50 cm3)", use="head bay, boards and antenna region"),
 "syntactic epoxy (low-exotherm, glass bubbles 40 vol%)": dict(density=0.75, k=0.12, eps_r=2.5, hardness="Shore D 65-75", Tmax_C=110, exotherm="moderate: pour in <=10 mm lifts", use="elbow/handle cavities, structural fill"),
 "alumina-filled epoxy or silicone (50-60 wt% Al2O3)": dict(density=1.9, k=1.2, eps_r=4.5, hardness="Shore A 70 / D 80", Tmax_C=150, exotherm="moderate", use="NPM hot zone only (FETs, clamp resistors)")}
OUT["potting_materials_typical_datasheet_class"] = mat
C_grad = 15.0
def Cscale(eps_pot, eps_brd=4.3): return round(((eps_brd + eps_pot) / 2) / ((eps_brd + 1) / 2), 2)
OUT["potting_effect_on_antenna_capacitance"] = {k.split(" (")[0]: dict(C_gradiometer_pF=round(C_grad * Cscale(v["eps_r"]), 1), SRF_gradiometer_MHz=round(3.5 / math.sqrt(Cscale(v["eps_r"])), 2), SRF_X8_MHz=round(0.35 / math.sqrt(Cscale(v["eps_r"])), 3)) for k, v in mat.items()}
OUT["glass_bubble_truth"] = ("Hollow glass microspheres LOWER density, dielectric constant and shrinkage, and soften the exotherm, but they are thermal INSULATORS (k about 0.12-0.15 W/mK). "
                            "They do not improve heat dissipation; heat is handled by low head dissipation, solid printed walls, and alumina-filled potting only where a hot part sits.")
# volumes: bay free volume, wire grooves
bay_free = math.pi * 2.2 ** 2 * 3.34 - 2 * math.pi * 2.0 ** 2 * 0.16 * 3 - 0.9 * 2.5            # cm3 (ID 44 x 33.4, minus boards ~, parts)
wire_len = (op["outer"]["wire_per_section_m"] + op["inner"]["wire_per_section_m"]) * 4
groove_void = wire_len * 1000 * (1.30 * 2.45 - 2 * math.pi * 0.6 ** 2 / 2 * 1.0) / 1000       # cm3
OUT["head_potting"] = dict(bay_free_volume_cm3=round(bay_free, 1), bay_fill_mass_g=round(bay_free * 0.75, 0), groove_void_cm3=round(groove_void, 0), groove_fill_mass_g=round(groove_void * 0.75, 0),
    procedure=["1 conformal coat boards (silicone or parylene), fit ferrite can parts", "2 vacuum-pot the bay module (3 boards + septum) in its sleeve through the lid port, vent opposite, 3 lifts max",
               "3 wipe-fill the winding grooves on face, rim, underside and inner walls BEFORE bonding the sensor board", "4 bond SB1 with epoxy film, bezel with epoxy, skid with VHB", "5 final cure and leak test (pressure decay 20 kPa)"])
# ---------------------------------------------------------------- 3. thermal budget (head)
head_W = dict(AB1A_AB1B=0.32, MCU_240MHz=0.35, LDO_losses=0.14, misc=0.15); P_head = sum(head_W.values())
k_solid = 0.27; R_cond = math.log(116 / 25) / (2 * math.pi * k_solid * 0.033); R_cond_infill = math.log(116 / 25) / (2 * math.pi * 0.12 * 0.033)
OUT["head_thermal"] = dict(dissipation_W=head_W, total_W=round(P_head, 2), radial_R_solid_PETG_K_per_W=round(R_cond, 1), dT_bay_solid_K=round(P_head * R_cond, 1),
    dT_bay_if_40pct_infill_K=round(P_head * R_cond_infill, 1), rule="print the head body SOLID (100% infill); keep head dissipation <= 1 W; regulation losses live outside the head (pre-regulated 5.5 V / 3.6 V rails)",
    NPM_dissipation_W=dict(clamp_scan=2.23, clamp_boost_300Hz=5.23, FET_and_shunt_boost=1.1, damping=0.5), NPM_dT_boost_K=round((5.23 + 1.1 + 0.5) / (10 * 0.037), 1))
# ---------------------------------------------------------------- 4. ribbon cassette and wiring
S = 450.0
rho = 1.72e-8; A28 = 0.0804e-6
OUT["ribbon"] = dict(type="12-conductor flat silicone ribbon, 1.0 mm pitch, AWG 28 (12 mm wide x 0.5 mm), two ribbons (POWER and SIGNAL) in separate chambers",
    telescoping_stroke_mm=S, trolley_travel_mm=S / 2, extra_ribbon_length_mm=S, loop_radius_mm=3.5, chamber_inner_mm="15.6 wide x 7.0 high", cassette_envelope_mm="18 x 18 (fits a 26 mm bore)",
    POWER_ribbon_pins=["VBUS", "VBUS", "VBUS", "GND", "GND", "GND", "+12V", "+5V5", "+3V6", "GND", "EN_MAIN", "spare"],
    SIGNAL_ribbon_pins=["TRIG", "JOY_X", "JOY_Y", "DIAL", "AUDIO", "GND", "GND", "SHIELD", "spare", "spare", "spare", "spare"],
    VBUS_drop_V_at_2A_1p1m=round(2 * 1.1 * rho / (3 * A28) * 2, 3), note="3 conductors in parallel per rail leg; AWG28 is rated about 0.7 A each")
# ---------------------------------------------------------------- 5. battery and holdup (handle, under the elbow)
OUT["handle_power"] = dict(pack="7S1P 18650 folded 4+3 in a U-pack, 290 x 38 x 20 mm, about 460 g, 90.7 Wh", holdup="supercap bridge 1 F / 27 V (10 x 10 F 2.7 V cells in series, balanced) on the PM1 cartridge-B input: about 40 s of scan-mode operation during a swap",
    swap_time_s="< 10 typical; boost mode is not guaranteed through a swap", runtime_h=ps["runtime"])
# ---------------------------------------------------------------- 6. mass and balance (approximate)
m = {"head body + windings + SB1 + bezel/skid + bay + potting": 1.25, "neck power module (PB1 + housing + potting)": 0.55, "shaft tubes + cassettes + ribbons": 0.45, "elbow + grip + PM1 + HB1": 0.40, "U-pack battery": 0.46, "supercap bridge": 0.06}
pos = {"head body + windings + SB1 + bezel/skid + bay + potting": 1.15, "neck power module (PB1 + housing + potting)": 0.75, "shaft tubes + cassettes + ribbons": 0.55, "elbow + grip + PM1 + HB1": 0.05, "U-pack battery": 0.05, "supercap bridge": 0.05}
tot = sum(m.values()); torque = sum(m[k] * pos[k] for k in m)
OUT["mass_and_balance"] = dict(masses_kg=m, total_kg=round(tot, 2), swing_moment_about_hand_kg_m=round(torque, 2), typical_detector_kg_m="about 1.3-1.7",
    warning="head-heavy: about 2.0 kg.m about the hand. Shorten the shaft, move the hand forward, or drop the 2nd potting lift in the NPM to reduce it. Measure with a pendulum test.")
# ---------------------------------------------------------------- 7. cavity rating register
OUT["cavities"] = [
 dict(id="C1 head bay (ferrite can)", contents="AB1A, AB1B, septum, CB1", V_max="30 V", I_max="1 A", T_max_C=85, potting="syntactic silicone", IP_target="IP68 (potted, no openings except side cable port)", shield="closed MnZn can 5 mm + copper-foil E-shield", ports="1 fill D6 + 1 vent D4 in the lid"),
 dict(id="C2 winding grooves + antenna layer", contents="Litz windings, SB1", V_max="600 V transient (flyback)", I_max="20 A pulse", T_max_C=85, potting="syntactic silicone/epoxy wipe-fill", IP_target="IP68 (sealed by bezel + skid)", shield="none (magnetically open by design)", ports="open-face fill"),
 dict(id="C3 NPM power chamber (PB1)", contents="PB1, 2 bulk caps, clamp resistors", V_max="600 V (HV zone), 30 V (LV zone)", I_max="33 A pulse", T_max_C=100, potting="alumina-filled hot zone + syntactic remainder", IP_target="IP67", shield="foil septum, single-point ground", ports="2 fill D8 + 2 vent D4"),
 dict(id="C4 ribbon chamber A (power)", contents="12-way power ribbon on trolley", V_max="30 V", I_max="3 A", T_max_C=70, potting="none (dry, vented and gasketed)", IP_target="IP65", shield="copper-foil lining, drain wire", ports="breather membrane"),
 dict(id="C5 ribbon chamber B (signal)", contents="12-way signal ribbon on trolley", V_max="12 V", I_max="0.2 A", T_max_C=70, potting="none", IP_target="IP65", shield="copper-foil lining, drain wire", ports="breather membrane"),
 dict(id="C6 elbow electronics (PM1)", contents="PM1, buck modules", V_max="30 V", I_max="5 A", T_max_C=80, potting="syntactic epoxy", IP_target="IP67", shield="foil", ports="1 fill + 1 vent"),
 dict(id="C7 grip electronics (HB1)", contents="HB1, hall sensor, joystick", V_max="12 V", I_max="0.3 A", T_max_C=70, potting="syntactic silicone", IP_target="IP65", shield="foil", ports="1 fill"),
 dict(id="C8 battery drawer", contents="U-pack, supercap bridge", V_max="30 V", I_max="10 A", T_max_C=60, potting="none (removable)", IP_target="IP65 (O-ring)", shield="none", ports="pressure-relief membrane")]
OUT["ratings_note"] = "IP targets are design goals for a sealed, potted, gasketed build; none is certified. Dielectric strength of potting spacing is design-checked only."
json.dump(OUT, open("kit_v6/system_concept.json", "w"), indent=1, default=float)
print(json.dumps({k: OUT[k] for k in ("head_bay_field", "potting_effect_on_antenna_capacitance", "head_potting", "head_thermal", "mass_and_balance")}, indent=1, default=float)[:6500])
