# First-article bench procedure, transmit region (Step 6, written 2026-10-25)

**Every item below is NOT RUN.** Nothing in this repository is built or measured: every number quoted here is MODELED (assumptions in docs/ASSUMPTIONS.md, the model files named in each row) or read from a datasheet (docs/design/DATASHEET_LOG.md). This document says what to measure, with what, in what order, and what result would pass or fail the model. `data/bench/` does not exist and stays empty until real data does: U-BENCH closes only when files exist there (`scripts/signoff_status.py` enforces it). Record raw captures, not summaries.

Boards in scope: **PB1R** (neck-module TX stage), **CB1D-B** (controller, D78), **TXJ1** (junction), **PM2** (battery dock), **HB2** (grip board). Coil: six petals in parallel, modeled 54 uH, loop resistance modeled 113 mohm (ASSUMPTIONS 28). Release: `releases/TX_r2` (from `make release-tx REV=r2`).

## 0. Rules for the bench

- Fused, current-limited supply for every first power-up (7S pack range 19.6 to 29.4 V). Start at 12 V and 0.2 A.
- Flyback nets (DRAIN1, CLAMP1, COIL_A/B, DM1/2, TX_A/B) reach about 460 V: 630 V-rated probes, one hand, nothing touching the board while pulsing. No ENIG parts near the coil (nickel is magnetic).
- Log the board revision (data/gerber folder name), the fabricator and the finish for every board. Photograph both sides before power.
- Pass limits below come from the model; when a measured value misses, the model assumption is what is wrong: add a CORRECTIONS row, do not widen the limit.

## 1. Order of work

1. Visual and continuity (no power): section 2.
2. Power rails with a current limit: section 3.
3. TX stage into a dummy load, then the coil, in the order of section 4.
4. Receive-side interactions (leak, damping, finishes): section 5.
5. Handle board, dock, junction and mechanical items: sections 6 to 8.
6. Close-out: section 9.

## 2. Continuity against the netlists and fabrication inspection

| # | Item | Instrument | Pass | Model / source | Status |
|---|---|---|---|---|---|
| 2.1 | Every net of PB1R, CB1D, TXJ1, PM2, HB2 beeps to its netlist; no shorts between nets, no opens | DMM, netlist printout (`data/results/PF233-*.net`, KiCad files) | 0 opens, 0 shorts | route and KiCad DRC results (0 unconnected) | NOT RUN |
| 2.2 | HV spacing: DRAIN1 / CLAMP1 / COIL_A/B / DM1/2 / TX_A/B to any other net | 1 kV insulation tester at 500 V, 1 min | > 100 Mohm, no breakdown | rule 6, 1.0 mm clearance (gerber_hv_check, KiCad HV rule with control) | NOT RUN |
| 2.3 | Via-in-pad on PB1R (shunt, bulk and decoupling pads): vias filled and plated over, no solder wicking | microscope, cross-section of a coupon or a sacrificial board | vias capped, no void under the pad | FAB_RULES_VERIFIED (both vendors offer filled, plated-over vias); OPEN_ITEMS 28a | NOT RUN |
| 2.4 | Finishes as ordered: immersion silver (or OSP) on CB1D, LB1, AB1A/B, SB1R-QA/QB, HTA, TXJ1; HASL lead-free on PB1R, PM2, HB2 | order paperwork, XRF if available | no nickel on the coil-side boards (a magnet does not pick up a bare coupon) | OPEN_ITEMS 26 | NOT RUN |
| 2.5 | JA/JB header and Hall TO-92 holes: pad ring and drill as designed (ring 0.185 mm, margin 5 um over the 0.18 mm floor) | microscope, caliper | no breakout on any plated hole | OPEN_ITEMS 35 | NOT RUN |
| 2.6 | Parts: bulk cans are Panasonic EEHZC1H101P (100 uF, 50 V, polarity), TVS SMCJ30A, US3M, Bourns SF-1206S500-2 fuse, Si4401FDY, DRV5023BIQLPG | visual, marking | match DATASHEET_LOG | docs/design/DATASHEET_LOG.md | NOT RUN |

## 3. Power-up (current limited)

| # | Item | Instrument | Pass | Model / source | Status |
|---|---|---|---|---|---|
| 3.1 | PM2 interlock truth table (switch open / closed, pack absent / seated) | bench supply 24 V through the dock, DMM on VBUS | VBUS present only with pack seated AND switch closed | power_dock_check (interlock table) | NOT RUN |
| 3.2 | PM2 soft start | scope on VBUS, 1 A limit | ramp 5 to 50 ms (modeled about 20 ms), inrush under 2 A (modeled 1.58 A) | power_dock_check | NOT RUN |
| 3.3 | PM2 gate drive and Vgs | DMM | Vgs under 15.6 V at 29.4 V (BZT52C15 max) | DATASHEET_LOG | NOT RUN |
| 3.4 | AUX12 (OKI-78SR-12) and +5V rails under load | DMM, scope for ripple | 12 V +-5 %, 5 V +-5 %, input range 15 to 36 V holds at 19.6 V | OKI sheet NOT read (U-DS-OKI) | NOT RUN |
| 3.5 | Idle supply current of PB1R and CB1D | bench supply | record (no model value) | none | NOT RUN |
| 3.6 | LED rail hardware current limit (OPEN_ITEMS 0): worst-case 66 LEDs full white | supply with current meter | firmware cap 0.35 A holds; the hardware limit (PTC or eFuse at CB1D JLB.1) trips before the rail row of the stress table fails | system_budget (the one documented FAIL row) | NOT RUN |

## 4. TX stage (PB1R, CB1D, TXJ1 and the coil)

Run first into a resistive dummy load of the same loop resistance (about 113 mohm in series with a 54 uH air inductor) so a wrong on-time cannot damage the coil or the FETs, then into the coil.

| # | Item | Instrument | Pass | Model / source | Status |
|---|---|---|---|---|---|
| 4.1 | **On-time calibration against `TX_ONTIME_LUT.csv`**: for 8, 14 and 20 A at 19.6, 26 and 29.4 V, set the table on-time and measure the delivered peak current | current probe on the TX pair (or the 10 mohm shunt via the Kelvin tap), scope | peak current within +-5 % of the target (modeled: 20 A needs 59.5 / 43.8 / 38.5 us at 19.6 / 26 / 29.4 V; the lossless L I/V under-delivers by 4 to 7 %) | tx_vbus_sweep.py; the loop R and coil L are ASSUMPTIONS 28 (coil L +-5 % moves the current +-5 %). Fit L and R_loop from the data and regenerate the table | NOT RUN |
| 4.2 | Bulk-bank droop per 20 A pulse at the BMS cut-off | scope on VBUS at PB1R, AC coupled | under 5 % of VBUS (modeled 0.85 V = 4.3 % of 19.6 V at -20 % capacitance) | tx_vbus.json (9 x 100 uF) | NOT RUN |
| 4.3 | Vds peak and turn-off timing | 630 V probe on DRAIN1 to the source, scope | Vds peak 456 / 462 / 466 V at 19.6 / 26 / 29.4 V (650 V FET, film clamp); current zero at about 3.8 us, quiet at about 5.6 us | sim_head1, tx_vbus.json | NOT RUN |
| 4.4 | Clamp: US3M reverse voltage (1000 V part) and film clamp capacitor (use C0G or film, not X7R); US3M reverse recovery (trr 85 ns max vs 35 ns for the earlier ES3J, not in the model, ASSUMPTIONS 45): drain ring-down after current zero | scope | clamp node peak at most 466 V (US3M under 47 %); no added ring-down tail at the first gate vs the model | system_budget; DATASHEET_LOG U-DS-PB1R | NOT RUN |
| 4.5 | RCL1 (5 kohm, 10 W bank) and the damping chain (3 x 110 ohm CRCW2512) heating | thermocouple or IR camera over 10 min at 400 Hz | RCL1 under 3.8 W (modeled), chain 0.46 W | system_budget; resistor bodies must not touch grounded metal (insulation 300 V) | NOT RUN |
| 4.6 | Over-current trip (LM393 on the shunt, REF_I1) | scope on FAULT1_N while stepping the on-time | trip at the set current within the modeled +-8 % (comparator ground reference 15.5 mV, 200 mV shunt signal) | pb1r_check | NOT RUN |
| 4.7 | Neck-module eddy offset: pulse with PB1R in the NPM and a 1 g nugget in air at 150 mm, then without PB1R | receive chain | record the difference; the nine aluminium cans are modeled at about 0.5 x the nugget on-axis (WARN) | pb1r_check, OPEN_ITEMS 34 | NOT RUN |
| 4.8 | Thermal: PB1R FET case temperature at 20 A, 400 Hz | thermocouple on the FET tab, 30 min | under 80 C in the pot (stress table 58 % margin rows) | system_budget, sim_thermal | NOT RUN |
| 4.9 | TXJ1 hipot 1 kV between bus A and bus B (OPEN_ITEMS 13) | 1 kV hipot, 60 s | no breakdown, leakage under 1 mA | stress table (3.0 mm edge gap for 460 V peak) | NOT RUN |
| 4.10 | TXJ1 fit: litz bend 4 mm in the window, cradle fit under the lid | caliper, visual | no kinked litz, lid closes | OPEN_ITEMS 13 | NOT RUN |

## 5. Receive-side interactions

| # | Item | Instrument | Pass | Model / source | Status |
|---|---|---|---|---|---|
| 5.1 | Receive leak at turn-off with the quadrupole receivers (SB1R-QA/QB) | scope on the AB1 inputs | 0.01 to 10 mV (modeled); first clean gate 5.1 to 7.5 us with RD 680 ohm | sbq_sim, sbq_damp2 | NOT RUN |
| 5.2 | Damping resistors RD1/RD2 (680 ohm) retained gated noise within 6 % of no Rd | noise measurement with and without | within 6 % | sbq_damp2 | NOT RUN |
| 5.3 | **Finish comparison (OPEN_ITEMS 26)**: immersion silver vs OSP on SB1R-QA/QB: leak, ring-down, noise; magnet pull test on a bare coupon of each finish (silver, OSP, HASL) | receive chain, magnet | no measurable difference between silver and OSP, and no magnetic pickup on any | none (open bench question) | NOT RUN |
| 5.4 | AB1 reference and common-mode buffers with 10 uF and 1 uF loads (OPEN_ITEMS 30) and the OPA2211 input range on the 5 V rail (OPEN_ITEMS 31) | scope on VREF, VCM and the ADC input | no ringing on the buffers, no input-range clipping on a full-scale step | OPA2365 sheet: stable to about 1 nF at unity gain; OPA2211 range 2.0 to 3.6 V | NOT RUN |

## 6. Handle board and trigger (HB2, CB1D)

| # | Item | Instrument | Pass | Model / source | Status |
|---|---|---|---|---|---|
| 6.1 | Trigger polarity: rest = TRIG low (magnet near), pressed = TRIG high | scope or DMM on the CB1D TRIG input | low at rest, high pressed, levels below 0.8 V and above 2.0 V | trigger_check | NOT RUN |
| 6.2 | **Hall magnet field at the sensor** (OPEN_ITEMS 32): field at rest and pressed | Gauss meter at the HS1 position | at least 24 mT at rest and at most 3 mT pressed guarantees the DRV5023BI over temperature; typical thresholds are 14.5 / 6 mT. Choose the magnet or travel from the data | DRV5023 sheet; modeled field ratio about 3.4 only | NOT RUN |
| 6.3 | Dial ladder levels | DMM on the ADC pin per position | P1 0.0, P2 1.20, P3 2.17, P4 2.85 V, open 3.3 V, each 0.3 V apart | trigger_check | NOT RUN |
| 6.4 | JTR.5/.6 at the handle end (OPEN_ITEMS 25): the cord is 5-core; confirm no conductor, RJ5/RJ6 not fitted | continuity on the first cord | JH5_NC / JH6_NC open | DESIGN_STATE | NOT RUN |

## 7. Dock and power path (PM2)

| # | Item | Instrument | Pass | Model / source | Status |
|---|---|---|---|---|---|
| 7.1 | Battery-side currents at the BMS cut-off (19.6 V): F1 peak and RMS, cord peak and RMS | current probe on BAT_P and on the cord | F1 peak under 3.1 A and RMS under 0.7 A (modeled 3.09 / 0.64 A), cord RMS 0.64 A; well under the 5 A fuse and cord rating | power_dock_check | NOT RUN |
| 7.2 | Q1 and fuse temperature, MT60 contact drop | thermocouple, millivolt meter | Q1 dissipation about 6 mW (modeled), contact resistance near 0.45 mohm (Amass sheet) | power_dock_check | NOT RUN |
| 7.3 | TVS behaviour on a deliberate 36 V transient from a current-limited supply | scope | clamps at or under 48.4 V at 31 A (SMCJ30A); the stand-off margin to 29.4 V is 2 % (WATCH): no leakage heating at 29.4 V | DATASHEET_LOG | NOT RUN |

## 8. Mechanical and wiring items tied to the boards

| # | Item | Pass | Status |
|---|---|---|---|
| 8.1 | PB1R in the NPM: JL1 and JP leave through the 12 mm back-wall window (modeled 5.0 mm from it); the JC umbilical runs across the pocket (about 41 mm) over the 12 mm cans: cables fit, bend radii kept | fits without strain (ASSUMPTIONS 33) | NOT RUN |
| 8.2 | Bulk cans: rigid mounting, can axes across the head field (OPEN_ITEMS 34) | no motion when the neck is flexed | NOT RUN |
| 8.3 | TXJ1 cosmetic warnings: 2 silk-over-copper and 1 back-side text, known from KiCad | confirm on the board; fix in the next revision, no function effect | NOT RUN |
| 8.4 | HTA (v2 Gerbers only: the first set had an open coil): continuity pad A to pad B, inductance | LCR meter at 100 kHz | continuous, about 2.8 uH (modeled) | NOT RUN |

## 9. Data sheet and close-out

For each board, one dated sheet in `data/bench/<board>_<date>.md` with: revision and fabricator, instrument list with calibration dates, every row above with measured value, pass or fail, and the raw capture file names (`data/bench/raw/`). After the first article: regenerate `TX_ONTIME_LUT.csv` from the fitted loop R and coil L, add a CORRECTIONS row for every modeled number that moved, and only then delete U-BENCH from docs/UNVERIFIED.md (the sign-off requires files under `data/bench/`). Items 4.1 and 6.2 are the two most likely to change the design.
