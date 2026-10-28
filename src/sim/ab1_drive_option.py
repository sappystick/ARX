#!/usr/bin/env python3
"""B9 option: differential ADC drive and/or RS 100 -> 33 ohm on the AB1A signal channels (GX = QUAD-A, GY = QUAD-B; AB1B carries no signal channel in RX-Q).
MODELED. Run in work/ (reuses sbq_damp2.first_clean / gate_noise and ab1_options_model.noise_case). Datasheet values used (files in data/seed/datasheets/):
  BAV199 (Nexperia v.3, 2020-09-01, Table 5): IF 160 mA continuous, IFRM 500 mA repetitive, IFSM 4 A (1 us square); VF <= 0.9 V at 1 mA, 1.0 V at 10 mA, 1.1 V at 50 mA
  74LVC1G66 (TI SCES323R, Sep 2025): ron 5.5 typ / 10 max ohm at VCC 4.5 V, IS 32 mA (DBV); ON-state switch current IT +-50 mA abs. max; switch I/O -0.5 .. VCC + 0.5 V
Questions: (1) clamp and switch current at RS 33 vs 100 for an input above the rails; (2) first clean gate and gated noise (sbq_damp2 network) at RS 33 vs 100 and
ron typ / max; (3) front-end noise and range, single-ended vs fully differential (ab1_options_model with the verified ron); (4) parts and area added by differential
drive on AB1A. The default (RS 100, single-ended) changes only if the model clearly wins (rule stated in docs/design/RECEIVE_OPTIONS_MODEL.md)."""
import json, sys, math
RAIL, RC = 5.0, 10.4
BAV = dict(IF=0.160, IFRM=0.500, IFSM_1us=4.0, VF_1mA=0.9, VF_50mA=1.1)
SW = dict(ron_typ=5.5, ron_max=10.0, IT=0.050, vio_over=0.5)

def clamp_rows():
    rows = {}
    for rs in (100.0, 33.0):
        R = RC + rs
        rows[f"RS {rs:.0f}"] = dict(
            overvoltage_for_IF_160mA_V=round(RAIL + BAV["VF_50mA"] + BAV["IF"] * R, 2),            # source voltage (coil EMF) at which the continuous rating is reached
            overvoltage_for_IFRM_500mA_V=round(RAIL + 1.25 + BAV["IFRM"] * R, 2),                   # VF 1.25 V max at 150 mA used as a floor for 500 mA (not given above 150 mA)
            surge_for_IFSM_4A_1us_V=round(RAIL + 1.25 + BAV["IFSM_1us"] * R, 1),
            blank_switch_IT_50mA_at_V=round(SW["IT"] * (R + SW["ron_max"]), 2),                       # EMF across coil + RS + ron that drives 50 mA through the closed blank switch
            clamp_mA_per_V_above_clamp=round(1000.0 / R, 1))
    return rows

def main(out):
    sys.path.insert(0, ".")
    import sbq_damp2 as M, ab1_options_model as O
    J = json.load(open("kit_v22/sbq_sim.json")); worst = max(v["peak_V"] for bd in J["leak"].values() for k, v in bd.items() if "lobes only" not in k)
    lobes = max(v["peak_V"] for bd in J["leak"].values() for k, v in bd.items() if "lobes only" in k)
    res = dict(inputs=dict(worst_modeled_leak_V=worst, lobes_only_diagnostic_V=lobes), clamp=clamp_rows())
    # (2) first clean gate and gated noise in the sbq_damp2 network (Rd 680, Cself 100 pF, blank release 0 and 5 us)
    fc = {}; gn = {}
    for rs in (100.0, 33.0):
        for ron in (SW["ron_typ"], SW["ron_max"]):
            M.RS = rs; M.RON = ron
            for tb in (0.0, 5e-6):
                t, pk = M.first_clean(worst, 680, 100e-12, tb, Ron=ron); fc[f"RS {rs:.0f}, ron {ron}, blank release {tb * 1e6:.0f} us"] = round(t, 2)
            gn[f"RS {rs:.0f}"] = {f"gate {tc * 1e6:.0f} us": round(M.gate_noise(680, 100e-12, tc)[0] * 1e9, 3) for tc in (6e-6, 20e-6)}
    M.RS = 100.0; M.RON = 8.0
    res["first_clean_gate_us_worst_leak"] = fc; res["gated_noise_nV_rtHz"] = gn
    # (3) front end noise and range with the verified ron (the options model assumed 3 ohm)
    cases = {}
    for nm, kw in (("single-ended RS 100 (committed)", dict(rs=100.0)), ("single-ended RS 33", dict(rs=33.0)),
                   ("differential RS 100", dict(rs=100.0, swing_v=2.5)), ("differential RS 33", dict(rs=33.0, swing_v=2.5))):
        c = O.noise_case(nm, sw_ohm=SW["ron_typ"], **kw); cases[nm] = dict(EIN_nV_rtHz=c["EIN_nV_rtHz"], max_input_mV_peak=c["max_input_mV_peak"], dynamic_range_dB=c["dynamic_range_dB"])
    res["front_end"] = cases
    # (4) parts and area for differential drive on AB1A: one inverting stage per signal channel (GX, GY) into AINx- instead of the VCM tie
    import os; os.environ["BOARD"] = "A"; import afe_design as D
    body = lambda t: D.LIB[t]["body"][0] * D.LIB[t]["body"][1]
    add = [("OPA2211", 1, "second half of U2 (spare today) + one new OPA2211 for the second channel")] + [("R0402", 2 * 3, "RG/RF of each inverting stage + RAAF of the minus path"), ("C0402", 2, "CF of each stage"), ("C0603", 2, "CAAF of the minus path")]
    area = sum(body(t) * n for t, n, _ in add); res["differential_parts_AB1A"] = dict(parts=[dict(type=t, n=n, note=s) for t, n, s in add], body_area_mm2=round(area, 1), board_area_mm2=round(math.pi * 20.0 ** 2, 1),
                                                                                       note="bodies only; the AB1A routing is already at the fab floor (B1 needed a placement nudge): a re-route is required and not attempted here")
    se, sd = cases["single-ended RS 100 (committed)"], cases["differential RS 33"]
    res["verdict"] = dict(
        noise_gain_pct=round((1 - sd["EIN_nV_rtHz"] / se["EIN_nV_rtHz"]) * 100, 1), range_gain_dB=round(sd["dynamic_range_dB"] - se["dynamic_range_dB"], 1),
        worst_leak_vs_clamp_threshold=f"{worst * 1e3:.2f} mV modeled vs {res['clamp']['RS 33']['overvoltage_for_IF_160mA_V']} V to reach IF 160 mA at RS 33: the clamp does not conduct in any modeled case",
        blank_switch_margin=f"RS 33: 50 mA through the closed switch needs {res['clamp']['RS 33']['blank_switch_IT_50mA_at_V']} V of EMF (RS 100: {res['clamp']['RS 100']['blank_switch_IT_50mA_at_V']} V)",
        default_changed=False,
        why=("RS 33 alone is a value change (no layout change): EIN and gated noise drop by about 16-17 %, the first clean gate does not move, and in every modeled case the clamp never "
             "conducts. Its cost is fault robustness: 2.5x more clamp and switch current per volt of overload (hot-plug or ESD on the hand-soldered coil harness is not modeled). "
             "Differential drive adds 6 dB of input range at the same noise but needs one more OPA2211 and 10 passives on AB1A, whose routing has no slack. "
             "Neither clearly wins with the fault case unmodeled and no bench data: the default stays RS 100, single-ended; RS 33 is the first bench A/B (swap RS1/RS2 on AB1A)."))
    json.dump(res, open(out, "w"), indent=1); print(json.dumps(res["verdict"], indent=1)); print(json.dumps(res["front_end"], indent=1)); print(json.dumps(fc, indent=1))

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "kit_v22/ab1_drive_option.json")
