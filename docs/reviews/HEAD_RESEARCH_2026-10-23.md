# Head redesign research: the earlier enhancement list revisited, and new directions (2026-10-23)

Everything here is MODELED with the repo's own models (`src/sim/config_study.py`, `make study`) or taken from published sources. No result is measured.

**How depth is modeled.** Depths use `sim_head1.depth_for`:
- idealised quadrupole receive rings, scaled by the 3.2x real-pattern signal as in DESIGN_STATE 6;
- 100 pulses at 20 A ampere-turns;
- free air, no ground.

They are for comparing options with each other, not for predicting field results.

**First gate and depth**, at the worst real modeled leak (10.3 mV):

| | value |
|---|---|
| First clean gate (sbq_damp2.py, RD 680 ohm, Cself 100 pF) | 7.48 us |
| Depth, as built (C0) | 116 / 165 / 196 mm for 0.1 / 1 / 5 g gold |

## 1. The earlier list (docs/reviews/ENHANCEMENT_REVIEW_2026-10-23.md), re-scored
| # | Item | Then | Now (modeled here) | Verdict |
|---|---|---|---|---|
| 1 | Firmware rules: constant-current on-time, boost duty, BLANK policy, per-pulse-type air template, LED cap, TRIG boot rule | recommended | No hardware cost. The 19.6-29.4 V pack range makes the on-time rule necessary: 55.1 us at 19.6 V vs 36.7 us at 29.4 V for 20 A. | **keep, first** |
| 2 | Pulse-width interleaving for discrimination | recommended | Firmware only. A discrimination gain, not a depth gain, so not in the depth model. | keep (simulate in P05) |
| 3 | Hood v3 | done | +12.9-14.2 % at 200 mm costs 286 g of tiles. One 55.5 mm tile per spoke (v4) gives +13.9-14.1 % with 227 g. Removing the tiles lowers torque by 0.28 kg m and loses 3 mm at 1 g (165 -> 162). | **change to v4** |
| 4 | 12 turns per layer at 26.7 A | study | First gate 7.48 -> 6.45 us (worst leak), 5.14 -> 3.98 us (aligned); depth +1 mm at 1 g, +3 mm at 0.1 g; FET margin 58 -> 44 %. The receive-coil ring-down, not the TX, sets the gate. | worth it only together with RX damping work (C2) |
| 5 | Amplifier gain 40 -> 100 | after the ADC datasheet | Not modeled: the ADC noise is unknown. | data needed |
| 6 | Sequential layer firing, second TX coil, mono receive channel, 40 A pulses | not recommended | Unchanged. | no |
| - | Averaging 4x longer (N 100 -> 400) | +12-15 % | +18 mm at 1 g (165 -> 183) in this model: the largest single depth lever. It costs response time; the audio latency target is about 50 ms. | **keep as a boost-hold mode** |

## 2. New directions from outside metal detecting
| Direction | What the source shows | What it would mean here | Modeled here | Verdict |
|---|---|---|---|---|
| Negative-capacitance receive damping | A metal-detector patent cancels part of the receive coil and cable capacitance and reports the critically damped time constant falling to about 0.5-0.7x ([US9547065](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9547065)) | An active stage on AB1T ahead of RS | Halving Cself (100 -> 50 pF): first gate 7.48 -> 7.14 us at RD 680; with RD re-tuned to 1000 ohm, 7.54 us | Small here, because the leak tail and the input network dominate. Research only. |
| Coil-response correction / zero-flux receive (airborne TEM) | SkyTEM removes the coil response from the first gates; zero-flux receive coils move the usable time earlier ([Copernicus GI 13/27](https://gi.copernicus.org/articles/13/27/2024/), [EarthDoc](https://www.earthdoc.org/content/journals/10.1111/1365-2478.12104), [CSIRO ASEG2012](https://publish.csiro.au/ex/ASEG2012AB321)) | The same idea as the quadrupole null plus the per-pulse air template referenced to the HTA | - | **keep**: makes the air template and HTA time-stamping first-class (P05) |
| Damping-resistor noise dominates TEM sensors | A UXO TEM sensor study finds the damping resistor's thermal noise dominates the sensor noise (same search) | RD sets both the first gate and the noise | sbq_damp2: RD 680 adds 4 % noise at a 6 us gate | **keep** RD 680; re-check if Cself changes |
| Slotted Faraday (electrostatic) shield over the receive coils | Patents use an electrostatic screen against capacitive ground coupling as the head moves, and slot it so it does not carry eddy currents ([US11474274](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11474274), [US11517283](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11517283)) | A slit conductive layer under the base plate, drained at one point (fits the eddy rule) | Not yet: needs the eddy decay of the slit pattern (sim_cage_rx.py method) | **study in the head redesign** |
| Bipolar (alternating) pulses | Patents use bipolar pulses so there is no net magnetic field ([US9285496](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9285496)). The sources did not show viscous-ground cancellation directly. | An H-bridge on PB1R (2 more 650 V FETs, a clamp per polarity) | - | study, hardware change |
| Target-field / stream-function winding design (MRI gradient coils) | Field targets plus energy/power penalties give winding patterns systematically ([Frontiers in Physics 2025](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2025.1579043/full), [ISMRM 2010](https://cds.ismrm.org/protected/10MProceedings/PDFfiles/1528_869.PDF)) | Optimise turn density per layer for field at 150-300 mm per unit stored energy, which generalises "turns at the rim" | **Done (target_field_study.py, 2026-10-24):** the as-built Fermat petal winding is within about 2 % of the target-field optimum for this band and groove spacing; the best design changes the field at 200 mm by -0.9 to +0.3 % at equal stored energy and the depth by 0 mm (figures TARGET_FIELD_WINDING.png, TARGET_FIELD_LAYERS_3D.png) | **closed: keep the as-built winding**; a gain would need a wider band or tighter grooves |
| Ground balance with PI | PI is less affected by mineralised ground than VLF; ground balance cancels magnetic-soil response ([US7701337](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7701337), [US11474274](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11474274)) | Gate-ratio ground balance (P05) | - | keep (P05) |
| Polymer-tantalum derating | About 80 % of rated voltage is the common polymer-Ta guideline ([KEMET derating note](https://bitsavers.mirrorservice.org/components/kemet/Derating_Polymer-Tanalum_Capacitors_200008.pdf), [Accendo](https://accendoreliability.com/different-way-consider-derating-guidelines/)) | PB1R CD1-CD6 are 35 V parts at 29.4 V (84 %) | system_compat.py | **change to 50 V parts** (new finding, CORRECTIONS) |
| Larger cells (21700) | P42A: 4.2 Ah, 70 g max, 45 A (retailer copies of the datasheet, [akkuteile](https://www.akkuteile.de/en/lithium-ionen-battery/size-21700/molicel/molicel-inr21700-p42a-4200mah-30a-to-max-45a-li-ion-battery-3-6v-3-7v_100813_3180)) | 7S1P 105.8 Wh: boost 13.7 h. The heavier pack sits behind the grip, so torque drops 0.03 kg m. | config_study | option (C3) |

## 3. Isolation zones and shielding in the head (what exists, what to add)
- **Exists:**
  - the TX driver at the neck, away from the coil;
  - hatched planes on the vault boards;
  - a copper-mesh septum between the analog and digital levels;
  - slit liners;
  - the quadrupole receive null;
  - the blank switch at the amplifier input.
- **Add (head redesign):**
  - a slotted electrostatic shield over the receive boards (above);
  - the LED-rail current limit (OPEN_ITEMS 0), which removes the largest digital current from the 5 V rail;
  - a cord end anchor (U10) at the tube B front, so the twin cavity ends before the neck-module tunnel (17.8 mm square; two 10.4 mm cords do not fit through it side by side).

## 4. Ranked list for the head redesign
1. Firmware rules and a boost-hold mode at N = 400 (+18 mm at 1 g, modeled).
2. Hood v4: one tile per spoke (same gain, -59 g, -0.06 kg m).
3. PB1R bulk capacitors to 50 V; choose the PB1R 12 V module for 19.6-36 V input.
4. Slotted electrostatic shield over the receive boards (model its eddy decay first).
5. Measure the coil self-capacitance and receive ring-down on the first boards, then decide on 12 turns per layer (C2) and any negative-capacitance stage.
6. ~~Target-field winding study~~: done, the as-built winding is at the optimum within about 2 % (keep it).
7. Bipolar pulses. Both 6 and 7 are larger studies.

Not recommended now: sequential layer firing, a second TX coil, a mono receive channel, 40 A pulses.
