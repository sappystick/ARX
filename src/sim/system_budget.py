#!/usr/bin/env python3
"""System stress and margin table: simulated stresses (sim_head1, sim_thermal, tx_system) against part ratings. Ratings are from memory of typical datasheets: UNVERIFIED (docs/ASSUMPTIONS.md 9); margins are only as good as those ratings."""
import json, csv, math
S = json.load(open("kit_v20/sim_head1.json"))["tx_stage"]; T = json.load(open("kit_v20/sim_thermal.json")); tx = json.load(open("kit_v22/tx_system.json"))
film = [x for x in S if x["case"] == "100 nF C0G/film"][0]; x7r = [x for x in S if "DC-bias" in x["case"]][0]
rows = []
def R(part, what, stress, rating, unit, minmargin, note, higher_is_worse=True):
    margin = (rating - stress) / rating * 100 if higher_is_worse else (stress - rating) / rating * 100
    st = "PASS" if margin >= minmargin else ("WATCH" if margin >= 0 else "FAIL"); rows.append(dict(part=part, stress=what, value=round(stress, 3), rating=rating, unit=unit, margin_pct=round(margin, 1), required_margin_pct=minmargin, status=st, note=note))
R("IPB65R095C7 (2 in parallel)", "Vds peak, design case (one 100 nF C0G/film)", film["Vds_peak"], 650, "V", 20, "drain peak at turn-off; X7R as built is lower (379 V) but loses capacitance with bias")
R("IPB65R095C7", "Vds peak, as-built 2 x X7R derated", x7r["Vds_peak"], 650, "V", 20, "")
R("IPB65R095C7", "drain current per FET at 20 A peak", 20 / 2, 24, "A", 30, "continuous rating at 25 C used as a conservative pulse reference (datasheet check needed)")
R("ES3J clamp diode", "reverse voltage (capacitor peak)", film["vc_peak"], 600, "V", 20, "")
R("ES3J clamp diode", "repetitive peak current", film["peak_i_diode"], 100, "A", 50, "datasheet IFSM is non-repetitive 8.3 ms: repetitive 4 us pulses at 400 Hz must be confirmed")
R("CL1A/B clamp capacitor 630 V", "voltage", film["vc_peak"], 630, "V", 20, "C0G/film only; X7R loses 65 percent of capacitance at this bias")
R("RCL1 5 kohm 10 W", "power", film["P_RCL_W"], 10, "W", 30, "x7r case 4.7 W")
R("3 x 110 ohm R2512 chain", "voltage per resistor at flyback peak", film["vd_peak"] / 3, 200, "V", 20, "assumed 200 V working voltage for R2512")
R("3 x 110 ohm R2512 chain", "power per resistor", film["P_damp_W"] / 3, 1.0, "W", 50, "")
R("MONO coupling cap 100 nF / 630 V", "voltage", film["vd_peak"], 630, "V", 20, "")
R("BAV199 input clamp (MONO path)", "peak clamp current through RS 1 kohm", (film["vd_peak"] - 5) / 1000, 4.0, "A", 50, "1 us surge rating assumed 4 A; average power negligible")
R("TXJ1 bus A to B", "creepage gap for 460 V peak", 460, 460 * 3.0 / 2.5, "V", 0, "3.0 mm edge gap vs about 2.5 mm needed (IEC 60664-1 style estimate, pollution 2); plus 1.6 mm FR4 between layers", True)
R("TX pair AWG12 600 V", "voltage", film["vd_peak"], 600, "V", 20, "")
R("SMCJ33A TVS", "VBUS maximum (7S full charge 29.4 V)", 29.4, 33, "V", 5, "standoff voltage")
R("OKI-78SR-5 module", "input voltage maximum", 29.4, 36, "V", 20, "")
R("TX coil litz", "rms current at 20 A / 400 Hz (Ipk sqrt(D/3))", 20 * math.sqrt(41.538e-6 * 400 / 3), 3.0, "A", 30, "about 3 A rms for 1.2 mm litz is conservative")
R("Vault", "worst-case hot spot (boost + 0.5 W LEDs, 25 C ambient)", max(v["max_C"] for k, v in T.items() if "worst" in k and "25 C" in k), 80, "C", 30, "PETG Tg about 80 C; FR4 85 C")
R("Vault", "hot spot at 40 C ambient", max(v["max_C"] for k, v in T.items() if "worst" in k and "40 C" in k), 80, "C", 30, "")
bulk = 6 * 150e-6; dv = (10 * 41.5e-6) / bulk; R("PB1R bulk capacitors 6 x 150 uF", "voltage droop per pulse (charge 415 uC)", dv, 26 * 0.05, "V", 0, "5 percent of VBUS allowed")
R("Power ribbon AWG28 x 3", "average current in boost (7.7 W / 26 V / 0.85)", 7.7 / 26 / 0.85, 1.5, "A", 50, "3 conductors in parallel, 0.5 A each continuous")
R("LED rail (OKI-78SR 1.5 A)", "66 LEDs at full white 60 mA each", 66 * 0.06, 1.5, "A", 0, "FAILS unless the firmware caps the LED current: REQUIREMENT firmware limit 0.35 A total (about 1.75 W)")
R("LED rail with the firmware cap", "capped LED current + Pico + ADC (0.35 + 0.15)", 0.50, 1.5, "A", 30, "requires the firmware cap")
R("TX lead channel", "litz fill ratio", tx["bundle_area_mm2"] / tx["channel_area_mm2"], 0.7, "ratio", 15, "wall-top groove + roof channel")
R("TX layers", "DC current sharing deviation", max(abs(v - 1) for v in tx["current_share"].values()), 0.05, "fraction", 50, "lead length differences")
R("TC4420 gate driver (2 FETs)", "gate charge per turn-off (2 x 45 nC, UNVERIFIED) at 12 V: peak current with 2.2 ohm gate resistors", 12 / (2.2 + 1.0), 6.0, "A", 30, "turn-off in about 20 ns, negligible against the 3.8 us flyback; datasheet Qg and RG values must be confirmed")
R("TC4420 gate driver", "average drive power 90 nC x 12 V x 400 Hz", 90e-9 * 12 * 400 * 1e3, 200, "mW", 50, "")
fails = [r for r in rows if r["status"] == "FAIL"]; watch = [r for r in rows if r["status"] == "WATCH"]
with open("kit_v22/SYSTEM_STRESS_MARGINS.csv", "w", newline="") as f: w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
power = {"scan 8 A / 800 Hz": dict(W=4.7, hours=round(90.7 / 4.7, 1)), "boost 20 A / 400 Hz": dict(W=7.7, hours=round(90.7 / 7.7, 1))}
json.dump(dict(rows=rows, fails=len(fails), watch=len(watch), power=power), open("kit_v22/system_budget.json", "w"), indent=1)
for r in rows: print(f"{r['status']:5} {r['part'][:34]:34} {r['stress'][:52]:52} {r['value']:>8} / {r['rating']} {r['unit']}  margin {r['margin_pct']}%")
print("FAIL", len(fails), "WATCH", len(watch), "of", len(rows))
