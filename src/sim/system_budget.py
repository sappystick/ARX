#!/usr/bin/env python3
"""System stress and margin table: simulated stresses (sim_head1, sim_thermal, tx_system) against part ratings. Ratings read from a manufacturer datasheet in Step 5 cite docs/design/DATASHEET_LOG.md in their note; every other rating is from memory: UNVERIFIED (docs/ASSUMPTIONS.md 9, 19); margins are only as good as those ratings."""
import json, csv, math
S = json.load(open("kit_v20/sim_head1.json"))["tx_stage"]; T = json.load(open("kit_v20/sim_thermal.json")); tx = json.load(open("kit_v22/tx_system.json"))
film = [x for x in S if x["case"] == "100 nF C0G/film"][0]; x7r = [x for x in S if "DC-bias" in x["case"]][0]
V_PACK_MAX, V_PACK_MIN = 29.4, 19.6                                                        # 7S1P: 4.2 V full charge, 2.8 V BMS cut-off
rows = []
def R(part, what, stress, rating, unit, minmargin, note, higher_is_worse=True):
    margin = (rating - stress) / rating * 100 if higher_is_worse else (stress - rating) / rating * 100
    st = "PASS" if margin >= minmargin else ("WATCH" if margin >= 0 else "FAIL"); rows.append(dict(part=part, stress=what, value=round(stress, 3), rating=rating, unit=unit, margin_pct=round(margin, 1), required_margin_pct=minmargin, status=st, note=note))
R("IPB65R095C7 (2 in parallel)", "Vds peak, design case (one 100 nF C0G/film)", film["Vds_peak"], 650, "V", 20, "drain peak at turn-off; X7R as built is lower (379 V) but loses capacitance with bias")
R("IPB65R095C7", "Vds peak, as-built 2 x X7R derated", x7r["Vds_peak"], 650, "V", 20, "")
R("IPB65R095C7", "drain current per FET at 20 A peak", 20 / 2, 24, "A", 30, "ID 24 A at TC 25 C, 15 A at TC 100 C, ID,pulse 100 A (Infineon IPB65R095C7 Rev. 2.0, DATASHEET_LOG)")
R("ES3J clamp diode", "reverse voltage (capacitor peak)", film["vc_peak"], 600, "V", 20, "VRRM 600 V (Good-Ark ES3x, DATASHEET_LOG); below the 630 V rule: no verified >= 630 V ultrafast SMC part (WATCH in DATASHEET_LOG)")
R("ES3J clamp diode", "repetitive peak current", film["peak_i_diode"], 100, "A", 50, "IFSM 100 A is non-repetitive 8.3 ms (Good-Ark ES3x): repetitive 4 us pulses at 400 Hz are not rated by the sheet")
R("CL1A/B clamp capacitor 630 V", "voltage", film["vc_peak"], 630, "V", 20, "C0G/film only; X7R loses 65 percent of capacitance at this bias")
R("RCL1 5 kohm 10 W", "power", film["P_RCL_W"], 10, "W", 30, "x7r case 4.7 W")
R("3 x 110 ohm R2512 chain", "voltage per resistor at flyback peak", film["vd_peak"] / 3, 500, "V", 20, "Vishay CRCW2512 e3 Umax 500 V (document 20035, DATASHEET_LOG; was assumed 200 V); insulation against ambient 300 V for 1 min")
R("3 x 110 ohm R2512 chain", "power per resistor", film["P_damp_W"] / 3, 1.0, "W", 50, "")
R("TXJ1 bus A to B", "creepage gap for 460 V peak", 460, 460 * 3.0 / 2.5, "V", 0, "3.0 mm edge gap vs about 2.5 mm needed (IEC 60664-1 style estimate, pollution 2); plus 1.6 mm FR4 between layers", True)
R("TX pair AWG12 600 V", "voltage", film["vd_peak"], 600, "V", 20, "")
R("SMCJ30A TVS (PM2, CB1D)", "VBUS maximum (7S full charge 29.4 V)", V_PACK_MAX, 30, "V", 5, "rated stand-off VWM (IR <= 1 uA at VWM, Vishay 88394); chosen over SMCJ33A because its 48.4 V clamp stays under the 50 V capacitors (SMCJ33A: 53.3 V)")
R("OKI-78SR-5 module", "input voltage maximum", V_PACK_MAX, 36, "V", 20, "36 V continuous absolute maximum (Murata MDC_OKI-78SR-W36.C05, DATASHEET_LOG)")
R("TX coil litz", "rms current at 20 A / 400 Hz (Ipk sqrt(D/3))", 20 * math.sqrt(41.538e-6 * 400 / 3), 3.0, "A", 30, "about 3 A rms for 1.2 mm litz is conservative")
R("Vault", "worst-case hot spot (boost + 0.5 W LEDs, 25 C ambient)", max(v["max_C"] for k, v in T.items() if "worst" in k and "25 C" in k), 80, "C", 30, "PETG Tg about 80 C; FR4 85 C")
R("Vault", "hot spot at 40 C ambient", max(v["max_C"] for k, v in T.items() if "worst" in k and "40 C" in k), 80, "C", 30, "")
tv = json.load(open("kit_v23/tx_vbus.json")); bb = tv["bulk_bank"]; w20 = [r for r in tv["ton_rule"] if r["I_A"] == 20]; wd = max(w20, key=lambda r: r["droop_pct"])
R(f"PB1R bulk capacitors {bb['n_caps']} x 100 uF -20 %", f"voltage droop per 20 A pulse at {wd['V']} V (charge {wd['charge_uC']} uC, loop R and sag included; tx_vbus_sweep.py)", wd["droop_V"], wd["V"] * 0.05, "V", 10, "5 percent of VBUS allowed; the earlier row used 415 uC at 26 V and 900 uF nominal (CORRECTIONS)")
R("PB1R bulk capacitors CB1-CB9 (50 V)", "voltage at the 7S full charge", V_PACK_MAX, 50.0, "V", 30, "Panasonic EEHZC1H101P 50 V 100 uF (ZC technical data, DATASHEET_LOG); each part must supply >= %d uF at 19.6 V (-20 %%)" % bb["min_nominal_uF_per_cap"])
R("PB1R 12 V module M12", "input voltage maximum", V_PACK_MAX, 36, "V", 15, "Murata OKI-78SR-12/1.0-W36-C: 36 V continuous absolute maximum, Vin 15-36 V (MDC_OKI-78SR-W36.C05, DATASHEET_LOG)")
R("PB1R 12 V module M12", "pack voltage at the BMS cut-off vs the module minimum input (15 V)", V_PACK_MIN, 15.0, "V", 15, "datasheet minimum input (UNVERIFIED, ASSUMPTIONS 29)", False)
import system_live as SL
P_BOOST_MIN = SL.power(V_PACK_MIN, "boost", dict(P_tx_W=SL.tx_supply(V_PACK_MIN, "boost")[2]))["P_total_W"]
R("Power cord AWG20 pair (upper v1)", f"average current in boost ({P_BOOST_MIN:.2f} W battery side at the 19.6 V BMS cut-off, system_live.py)", P_BOOST_MIN / V_PACK_MIN, 5.0, "A", 50, "coiled cord in the shaft power cavity; 5 A continuous assumed for enclosed AWG20 silicone (ASSUMPTIONS 27); replaces the AWG28 x 3 ribbon")
R("PM2 fuse F1 5 A slow", "battery-side peak through F1 at the BMS cut-off (time-domain chain, power_dock_check.py)", json.load(open("kit_v23/power_dock_check.json"))["currents_A"]["recharge_peak"], 5.0, "A", 20, "slow-blow: carries the rated current continuously; peaks last about a millisecond")
R("Battery pack 7S1P Molicel P30B", "average current in boost", P_BOOST_MIN / V_PACK_MIN, 30.0, "A", 50, "30 A continuous, 80 C cut-off (Molicel INR-18650-P30B PDS v1.0, DATASHEET_LOG)")
R("LED rail (OKI-78SR 1.5 A)", "66 LEDs at full white 60 mA each", 66 * 0.06, 1.5, "A", 0, "FAILS unless the firmware caps the LED current: REQUIREMENT firmware limit 0.35 A total (about 1.75 W)")
R("LED rail with the firmware cap", "capped LED current + Pico + ADC (0.35 + 0.15)", 0.50, 1.5, "A", 30, "requires the firmware cap")
# ---- B3 (2026-10-28): +3V3D (CB1D UL, AMS1117-3.3, Advanced Monolithic DS1117) feeding both AD7389-4 (Rev. 0 p. 4: IVCC 21 / 23 mA, IVLOGIC 3.7 / 4.1 mA, static IVCC 1.7 / 2.0 mA) plus the RML 270 ohm minimum-load bleed
I3_ADC_MAX, I3_ADC_STATIC, I_RML, IQ_AMS = 2 * (0.023 + 0.0041), 2 * 0.0020, 3.3 / 270.0, 0.011
R("AMS1117-3.3 (CB1D UL)", "+3V3D output current: 2 x AD7389-4 operational max + RML bleed", I3_ADC_MAX + I_RML, 0.8, "A", 50, "0.8 A is the dropout specification point (DS1117 Note 4); 1 A rated")
R("AMS1117-3.3 (CB1D UL)", "minimum load with both ADCs static (2 x 2.0 mA) + RML", I3_ADC_STATIC + I_RML, 0.010, "A", 20, "10 mA max minimum load for regulation (DS1117 Note 5); RML alone (AB1 boards unplugged) 12.2 mA", higher_is_worse=False)
R("AMS1117-3.3 (CB1D UL)", "minimum load with the AB1 boards unplugged (RML only)", I_RML, 0.010, "A", 20, "the case the bleed exists for", higher_is_worse=False)
R("AMS1117-3.3 (CB1D UL)", "dropout 1.3 V max vs the 5.0 - 3.3 = 1.7 V available (M5 nominal)", 1.3, 1.7, "V", 15, "DS1117 1.1 typ / 1.3 V max at 0.8 A; less at 66 mA")
R("AMS1117-3.3 (CB1D UL)", "dissipation (5.0 - 3.3) x load + 5.0 x Iq 11 mA max", (5.0 - 3.3) * (I3_ADC_MAX + I_RML) + 5.0 * IQ_AMS, 1.2, "W", 50, "1.2 W SOT-223 guaranteed (DS1117 Note 2); theta-JA 90 C/W -> about 15 C rise")
R("AD7389-4 VCC (+3V3D)", "AMS1117-3.3 output high limit 3.399 V vs VCC max 3.6 V", 3.399, 3.6, "V", 3, "DS1117 full-temperature 3.201-3.399 V at VIN 4.8 V; AD7389-4 VCC 3.0-3.6 V")
R("AD7389-4 VCC (+3V3D)", "AMS1117-3.3 output low limit 3.201 V vs VCC min 3.0 V", 3.201, 3.0, "V", 3, "", higher_is_worse=False)
R("RML 270 ohm 0603 (CB1D)", "power 3.3^2 / 270", 3.3 ** 2 / 270.0, 0.10, "W", 50, "CRCW0603 e3 P70 0.10 W (Vishay 20035)")
# +5VA (CB1D FB2 from +5V, pw_design.py) feeds the AB1 analog parts: OPA2211 IQ 3.6 typ / 4.5 max mA per channel at 25 C, 6 mA over -40..125 C (TI SBOS377L, POWER SUPPLY);
# OPA2365 IQ 4.6 typ / 5 max mA per amplifier (TI SBOS365G); AB1A 2 x OPA2211 + 1 x OPA2365, AB1B 1 x OPA2211 + 1 x OPA2365 (PF233-AB1A/B_BOM.csv); 74LVC1G66 supply current is in the uA range and is left out
N_OPA2211_CH, N_OPA2365_CH = 2 * (2 + 1), 2 * (1 + 1); I5A_MAX = N_OPA2211_CH * 0.0045 + N_OPA2365_CH * 0.005; I5A_HOT = N_OPA2211_CH * 0.006 + N_OPA2365_CH * 0.005
R("+5VA (AB1A + AB1B analog, via CB1D FB2)", "6 OPA2211 channels x 4.5 mA max + 4 OPA2365 amplifiers x 5 mA max (25 C)", I5A_MAX, 1.0, "A", 50, f"FB2 bead 1 A; over temperature {I5A_HOT * 1e3:.0f} mA (OPA2211 6 mA per channel)")
R("+5V rail (CB1D M5, 1.5 A)", "LED firmware cap 0.35 A + Pico / CB1D logic 0.15 A (estimate) + AMS1117 input (+3V3D load + 11 mA Iq) + +5VA analog (over temperature)", 0.35 + 0.15 + I3_ADC_MAX + I_RML + IQ_AMS + I5A_HOT, 1.5, "A", 30, "M5 OKI-78SR-5/1.5-W36-C 1.5 A (Murata C05); the 0.15 A logic share is an estimate; the +5VA term was missing before 2026-10-28 (CORRECTIONS)")
R("TX lead channel", "litz fill ratio", tx["bundle_area_mm2"] / tx["channel_area_mm2"], 0.7, "ratio", 15, "wall-top groove + roof channel")
R("TX layers", "DC current sharing deviation", max(abs(v - 1) for v in tx["current_share"].values()), 0.05, "fraction", 50, "lead length differences")
R("TC4420 gate driver (2 FETs)", "gate charge per turn-off (2 x 45 nC, Infineon Rev. 2.0) at 12 V: peak current with 2.2 ohm gate resistors (TC4420 6 A peak, DS21419D)", 12 / (2.2 + 1.0), 6.0, "A", 30, "turn-off in about 20 ns, negligible against the 3.8 us flyback; datasheet Qg and RG values must be confirmed")
R("TC4420 gate driver", "average drive power 90 nC x 12 V x 400 Hz", 90e-9 * 12 * 400 * 1e3, 200, "mW", 50, "")
fails = [r for r in rows if r["status"] == "FAIL"]; watch = [r for r in rows if r["status"] == "WATCH"]
with open("kit_v22/SYSTEM_STRESS_MARGINS.csv", "w", newline="") as f: w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
PACK_WH = 7 * 3.6 * 3.0                                                  # upper assembly v1: one 7S1P Molicel P30B pack (75.6 Wh; v20 assumed 90.7 Wh)
import system_live as SL                                               # 2026-10-28: battery-side power from the traceable model (TX V Q f + rails / 0.85), replacing the 4.7 / 7.7 W constants (CORRECTIONS)
V_NOM = 7 * 3.6
def _pw(mode, V): return SL.power(V, mode, dict(P_tx_W=SL.tx_supply(V, mode)[2]))
power = {f"{nm} {SL.MODES[m]['I']:.0f} A / {SL.MODES[m]['f']:.0f} Hz": dict(W=round(_pw(m, V_NOM)["P_total_W"], 2), hours=round(PACK_WH / _pw(m, V_NOM)["P_total_W"], 1), at_V=V_NOM)
         for nm, m in (("scan", "scan"), ("mid", "mid"), ("boost", "boost"))}; power["pack_Wh"] = PACK_WH; power["model"] = "src/sim/system_live.py (MODELED; efficiency 0.85 and the 0.10 W M12 load ASSUMED)"
json.dump(dict(rows=rows, fails=len(fails), watch=len(watch), power=power), open("kit_v22/system_budget.json", "w"), indent=1)
for r in rows: print(f"{r['status']:5} {r['part'][:34]:34} {r['stress'][:52]:52} {r['value']:>8} / {r['rating']} {r['unit']}  margin {r['margin_pct']}%")
print("FAIL", len(fails), "WATCH", len(watch), "of", len(rows))
