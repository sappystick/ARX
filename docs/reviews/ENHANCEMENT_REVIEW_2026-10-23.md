# Enhancement review: field, coils, waveform, receive, processing (2026-10-23)

Everything here is MODELED. Nothing has been built or measured. Each estimate names the model it comes from, and the assumptions are in docs/ASSUMPTIONS.md.

**How depth gains are estimated.** Near the detection limit, the noise-limited SNR in sim_head1.py falls as about depth^-5.1. For a 1 g gold sphere, SNR drops 25.7 -> 3.2 between 100 and 150 mm. So a signal factor k buys a depth factor of about k^(1/5.1):
- +10 % signal -> +1.9 % depth
- 2x signal -> +14.6 % depth

The repo's own improvement table agrees: 100 -> 400 pulses (2x SNR) took 1 g from 179 to 200 mm (+12 %). This rule ignores ground. Mineralised soil usually costs more depth than any lever below adds.

## 1. Condensing (size and mass)
- **Mass.** The head is estimated at 2.22 kg and the static torque at 2.88 kg m, against a target under 2.2 kg m (OPEN_ITEMS 8).
- **Hood v3** adds 286 g of MnZn for +12.9-14.2 % field at 200 mm (PR #6, hood_axi.py). That is roughly +2.5 % depth from the transmit side alone. Per gram it is the weakest lever here.
  - If balance matters more than the last 2-4 % of depth, keep the hood optional: the carrier can be printed without tiles.
- **Former mass** (infill, lightening with the flat faces and grooves kept) is the largest lever left. Prompt P08 holds the method.
- **The vault** (L0-L8, 47.1 mm) is already tight. The stack check's tightest gap is 0.4 mm (CB1D parts to LB1). Shrinking it would mean moving parts off CB1D, not squeezing the levels.

## 2. Stronger projected field for depth
| Lever | Signal factor | Depth factor | Cost / limit |
|---|---|---|---|
| Boost 20 A at 400 Hz instead of scan 8 A at 800 Hz | 2.5 x moment, sqrt(1/2) for half the pulses -> 1.77 | +12 % | 7.7 W instead of 4.7 W; 11.8 h on 90.7 Wh; FET 10 A per device (58 % margin) |
| Averaging 4 x longer (100 -> 400 pulses) | 2 | +12-15 % | response time 4 x slower (sweep speed) |
| Hood v2 -> v3 (butted tiles) | 1.13 / 1.10 | +0.6 % over v2, +2.5 % over no hood | +8 g over v2 (286 vs 278 g) |
| Turns concentrated at the rim (same count, r 95-110 instead of 62-110) | about 1.3-1.4 per ampere at depth (Sigma r^2) | +5-7 % | higher L and slower turn-off unless the turns or current are rebalanced (see 4); the shallow field under the centre drops |
| 40 A pulses (2 FETs at 20 A each) | 2 | +14.6 % | FET margin 17 % (30 % required); I^2 losses x 4; clamp/RCL1 stress (P07); not recommended without new FETs |

Notes:
- Field geometry: on the axis the field falls from 1136 uT at 50 mm to 11 uT at 500 mm (20 A). Depth is set by the moment and the averaging, not by the field near the coil.
- Hood v3 field lines (docs/figures/HOOD_AXI.png): the hood does not steer the field sideways. It returns the upward flux and pushes the lines down inside r150 mm.

## 3. Trigger, boost and sustainability
- **Wiring** (fixed in PR #5): HB1 now uses a digital Hall switch on CB1D's digital-only TRIG_IN, with RP1 47k. Modeled levels are 0.52 V low and 3.25 V high, with a 0.47 ms time constant.
- **Boost is a firmware mode.** TRIG selects 20 A at 400 Hz. Four firmware rules keep it sustainable:
  1. **Constant current as the battery sags.** The on-time must follow VBUS: ton = L I / VBUS, so 41.5 us at 26 V and 44.3 us at 24.4 V. VBUS_SENSE is already on ADC2.
  2. **Duty limit.** Boost holds while the trigger is held, then returns to scan. Also limit the time-averaged boost fraction so the vault stays under its modeled 35.6 C worst case.
  3. **Low-battery fallback.** Drop to 14 A, then 8 A, below set VBUS levels, so turn-off and clamp timing stay inside the modeled range.
  4. **Soft entry.** Ramp the pulse current over about 10 pulses on entering boost. This avoids an air-template step, because the leak scales with current.
- **Handle redesign (owner decision, 2026-10-23).** The joystick is removed from the design, which closes OPEN_ITEMS 16 (its push switch had no cable conductor). The grip and forearm cuff are redesigned: the boost trigger sits where the index finger rests on the grip, and the quick-swap battery rails sit on the underside where the grip meets the forearm cuff. The trigger chain (HS1 -> TRIG_IN) is unchanged; the cable loses the two joystick axes, so the HB1 netlist, the harness and the dial ladder must be regenerated in that work (OPEN_ITEMS 4).

## 4. Transmit coil: winding density and pattern
Modeled with the real TX stage (sim_head1 S1, one 100 nF film clamp), at the same moment (turns x current constant):

| Turns vs today | L | I | ton | Vds peak | current zero | quiet | RCL1 | per-FET current |
|---|---|---|---|---|---|---|---|---|
| 0.5 | 13.5 uH | 40 A | 20.8 us | 474 V | 1.84 us | 4.15 us | 4.0 W | 20 A |
| 0.75 | 30.4 uH | 26.7 A | 31.2 us | 468 V | 2.79 us | 4.79 us | 3.9 W | 13.3 A |
| 1 (today) | 54 uH | 20 A | 41.5 us | 462 V | 3.76 us | 5.56 us | 3.8 W | 10 A |
| 1.5 | 122 uH | 13.3 A | 62.3 us | 451 V | 5.92 us | 7.17 us | 3.6 W | 6.7 A |

How the rows were made: sim_head1.py S1 `pulse()` with L = 54 uH x n^2 and I = 20 / n A (n = turns factor), 100 nF film clamp; this reproduces every row (no committed script). Held fixed in every row: the coil self-capacitance (500 pF), the 330 ohm damping chain and the coil resistance (45 mohm). All three change with the turn count in a real coil (the best damping resistance goes as sqrt(L / C)), so the quiet times are modeled under that assumption only. Coil copper loss stays about 0.11 W only if the fewer turns use thicker litz that fills the same winding window (R scales with n^2); with the same litz, R scales with n and the loss at 0.75 x turns is 1.33 x.

**Recommendation: 0.75 x turns (12 per layer instead of 16) at 26.7 A.**
- It quiets the TX 0.8 us earlier, and an earlier gate matters most for small gold.
- It keeps 44 % FET margin.
- Its cost is a higher pulse current (ribbon, battery peak), and the formers need regenerating.
- Before deciding, re-derive the self-capacitance and the damping chain for 12 turns, then run it through sbq_damp2 / sim_head1: the receive ring-down (5.1-7.5 us) may then set the first gate instead of the TX.

**Series vs parallel.** The six layers in series give about 36 x the inductance at 1/6 of the current. That is 6 x the flux linkage per pulse, so 6 x slower turn-off at the same clamp voltage. Parallel is right for early gates.

**The 12-fold petal ripple** (2.4 mm) averages out of the field at depth. Its value is mechanical (groove interlock) and in spreading the turns, not in projecting field.

**"Radio coils"** is read as additional coils. For transmit, a second, smaller concentric TX coil only pays off if it is driven separately for depth or size discrimination. It costs a second driver and adds leak, so it is not recommended before the single-coil system is measured.

## 5. Waveform and sequential six-layer activation
- **Firing layers one at a time** cuts the moment per pulse to 1/6, with six times the switches.
- The layers are near-identical apart from height. The top layer's field at depth is only 0.69 / 0.70 / 0.77 / 0.83 / 0.88 of the bottom layer's at 50 / 100 / 200 / 300 / 500 mm on the axis (Biot-Savart over the real layer paths of sim_head1.py S2, kit_v15/LOW/paths.pkl; no committed script).
- That ratio does carry depth information. But near the detection limit (SNR about 3-10) the ratio noise is about +-0.1-0.3, which is ten times the change per 100 mm. **Not recommended**; keep all six layers in parallel.
- **Better for discrimination: pulse-width interleaving.** Alternate long (41.5 us, 20 A) and short (about 10 us at the same peak) pulses. Short pulses favour short-tau targets (small gold), long pulses large or long-tau targets. The ratio of the two responses is a conductivity / size class.
  - This is firmware only (TX1_IN timing). The air template must then be kept per pulse type.
- **Bipolar pulses** (reversing the coil current every other pulse) would cancel the Earth's-field/remanence term and the ground's viscous component more symmetrically. They need an H-bridge in PB1R: a hardware change, worth a separate study.

## 6. Receive coils, coding and the antenna array
- **RX-Q** (two quadrupoles rotated 45 deg):
  - Bearing = 0.5 atan2(B, A) + 45 deg, with 0.3-0.5 deg modeled scatter.
  - Amplitude RSS is flat within +-2.5 %.
  - Leak is 0.01-10 mV depending on board and offset.
  - With RD 680 ohm (PR #3) the first clean gate is 5.1-7.5 us.
- **Coding.** The quadrupoles alone give bearing but not depth. A depth class comes from the ratio of early to late gates (the matched-filter bank tau = t1 x 1.618^n), together with amplitude. A mono (disc) receive channel would add a second spatial weighting for depth, but it is first-order sensitive to the TX: the unnulled disc sees 290 V. Keep it out.
- **The HTA** (hub-top antenna, about 2.8 uH):
  - **Timing:** it is the TX timing and EMI reference, so use it to time-stamp turn-off on every pulse. The real turn-off moves with VBUS and temperature.
  - **Interference:** it feeds the adaptive filter (LMS/RLS) for mains/VLF interference.
  - A second HTA turn ring at a different radius would make the EMI reference more complete. This is the useful form of an "antenna array" here.

## 7. Computing, filtering and processing
**Analog front end** (AB1T, modeled):
- RS 100 ohm -> BAV199 -> blank switch -> OPA2211 x40 -> 362 kHz RC anti-alias -> ADS8860.
- Input noise is 1.73 nV/rtHz with RD 680, so 69 nV/rtHz at the amplifier output.
- An ADS8860-class 16-bit converter on a 5 V range is of the same order (tens of nV/rtHz; datasheet value unverified). The ADC therefore adds noticeably in quadrature.
- **Options:**
  - **(a)** Gain 100. Headroom at the input drops from about 62 to 25 mV, still above the 10 mV worst modeled leak.
  - **(b)** Keep gain 40 and rely on averaging.
  - Decide after the ADC noise is read from the datasheet (C05) and the first boards' leak is measured.
- **BLANK:** keep it open through turn-off (PR #3). Close it only when the air leak would exceed the headroom.

**Processing order** (prompt P05, Python first):
1. TX-synchronous capture (time-stamped by the HTA)
2. Per-pulse-type air template subtraction (rolling)
3. Adaptive filter on the HTA reference
4. Matched-filter gates tau = t1 x 1.618^n
5. Ground balance (ratio of gates)
6. Bearing from A/B
7. Depth/size class from gate ratios and amplitude
8. Confidence = SNR

Compute is not the limit: at 800 Hz, 3 channels x about 60 samples per pulse is trivial for the RP2350.

**Audio library.**
- Pitch from the conductivity/tau class (low = long tau / large or ferrous, high = short tau / small gold), loudness from the SNR above threshold, and a short "ground" tone when ground balance moves.
- Latency should stay under about 50 ms. That limits the averaging window in scan mode, so trade it against the depth gain from averaging in section 2.

**LED library (66 pixels).**
- Bearing on the ring, depth class as the radius or ring, confidence as brightness.
- The rail needs the 0.35 A firmware cap (OPEN_ITEMS 0): 66 LEDs at full white draw 3.96 A on a 1.5 A rail.

## 8. Ranked recommendations
1. **Firmware rules from sections 3 and 7** (constant-current on-time from VBUS, boost duty limit, BLANK policy, per-pulse-type air templates). These cost nothing and protect every modeled number.
2. **Pulse-width interleaving** for discrimination (section 5): firmware only, then simulate it in P05.
3. **Hood v3** is done (PR #6). Fit it if the extra 286 g is acceptable for balance.
4. **Study 12 turns per layer at 26.7 A** (section 4): an earlier TX quiet by 0.8 us. It needs regenerated formers and a re-run of the damping/gate models.
5. **Gain 40 -> 100** after the ADC datasheet and first-board leak (section 7).
6. **Not recommended now:** sequential layer firing, a second TX coil, a mono receive channel, 40 A pulses.

What would confirm all of this: first-article bench tests (OPEN_ITEMS 10, 11, 15, 18), meaning coil L/R/self-resonance, receive ring-down with RD, the hood axis field, and TX turn-off at 8/14/20 A.
