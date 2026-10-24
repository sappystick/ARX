# System configurations: C0 as built vs the top 3 (2026-10-23)

Modeled with `make study`, which runs `src/sim/config_study.py` and `src/sim/system_compat.py`.

The configurations are compared with the repo's own models:
- first clean gate: sbq_damp2;
- depth: sim_head1.depth_for, idealised quadrupole x 3.2 real-pattern signal, free air, no ground, 100 pulses;
- hood gain: hood_axi;
- upper-assembly mass and centroids: measured on the meshes, including a regenerated light variant;
- torque about the grip: at the v20 head reach, 47 deg;
- runtime: from system_budget.

Nothing is built or measured.

Figures:
- docs/figures/CONFIGURATIONS_v1.png (the 4 configurations side by side);
- docs/figures/SYSTEM_SCHEMATIC_v1.png (power, signal and TX paths with harness ids).

Pin-level schematics: data/kicad/sch/*.kicad_sch (9 boards, round-trip checked).

## Results
| | C0 as built | C1 light and balanced | C2 early gate | C3 endurance |
|---|---|---|---|---|
| Depth 0.1 / 1 / 5 g, worst leak (mm) | 116 / 165 / 196 | 116 / 165 / 196 | 119 / 166 / 197 | 116 / 165 / 196 |
| First clean gate, aligned / worst leak (us) | 5.14 / 7.48 | 5.14 / 7.48 | **3.98 / 6.45** | 5.14 / 7.48 |
| TX quiet (us) | 5.56 | 5.56 | 4.79 | 5.56 |
| Total mass: head + neck + lower tube + handle (kg) | 4.742 | **4.640** | 4.640 | 4.826 |
| Torque about the grip, 47 deg (kg m) | 2.883 | 2.827 | 2.827 | **2.795** |
| Boost / scan runtime per pack (h) | 9.8 / 16.1 | 9.8 / 16.1 | 9.8 / 16.1 | **13.7 / 22.5** |
| TX peak current, FET margin | 20 A, 58 % | 20 A, 58 % | 26.7 A, 44 % | 20 A, 58 % |

Averaging 400 pulses in a boost-hold mode adds +18 mm at 1 g (165 -> 183) in every configuration. It is a firmware change and costs response time.

The C0 torque here (2.883) includes the 8 g heavier v3 tiles; upper_check.py uses the v20 head mass (2.875).

## What stays, changes or is added (against what exists now)
| Item | C1 light and balanced | C2 early gate | C3 endurance |
|---|---|---|---|
| Formers (6 layers, 16 turns, 54 uH) | stay | **change**: 12 turns/layer (0.75 x, 30.4 uH), regenerate | stay |
| Hood | **change**: v4, one 55.5 mm tile per spoke (227 g, same envelope) | as C1 | as C1 |
| Vault, cylinder v5, boards CB1D/LB1/HTA | stay (CB1D JOY cleanup, OPEN_ITEMS 20) | stay | stay |
| SB1R-QA/QB + RD 680 | stay | stay; RD and Cself re-derived for the new TX waveform | stay |
| PB1R | **change**: CD1-CD6 to 50 V parts; M12 module chosen for 19.6-36 V | as C1, plus shunt/OCP reference for 26.7 A; 13.3 A per FET | as C1 |
| AB1T gain | stay (gain 100 waits for the ADC noise) | stay | stay |
| Upper housings | **change**: 2.0 mm walls, 2.5 mm dock plate (regenerated, -43 g measured) | as C1 | as C1 |
| Battery pack | stay: 7S1P P30B | stay | **change**: 7S1P P42A 21700, new U7 shell and bay; dock rails stay |
| PM2 / HB2 / harness v3 | stay | stay | stay (BMS >= 10 A) |
| Shaft | **add** U10 cord end anchor (all configurations) | add U10 | add U10 |
| Firmware | **add**: constant-current on-time, boost duty, BLANK policy, per-pulse air template, LED cap, TRIG boot rule, boost-hold N 400 | as C1 | as C1 |

## Ranking
1. **C1 light and balanced: do now.**
   - -102 g total and -0.056 kg m, with no depth loss.
   - Mostly generator changes (hood v4, wall thickness) and part values (PB1R bulk), plus firmware.
   - Lowest risk.
2. **C3 endurance: if runtime matters more than mass.**
   - +3.9 h of boost per pack, and torque drops a further 0.03 kg m because the heavier pack sits behind the grip.
   - Costs +186 g against C1 and a new pack shell.
3. **C2 early gate: after the first boards are measured.**
   - The first gate is 1.0 us earlier, but depth changes by only +1 to +3 mm in this model, because the receive-coil ring-down sets the gate.
   - The formers must be regenerated, the FET margin falls to 44 %, and the TX self-capacitance and damping chain assumed here (500 pF, 330 ohm) must be measured first.

## Compatibility (system_compat.py): 15 OK, 5 ACTION, 3 DATA, 0 incompatible
**ACTION** (known changes):
- U10 cord end anchor: two 10.4 mm cords do not fit the 17.8 mm neck tunnel side by side.
- Hood v4 generator.
- CB1D JTR.5/.6 cleanup.
- PB1R bulk at 84 % of 35 V.
- Runtime -17 % vs the v20 90.7 Wh assumption.

**DATA** (unverified part facts):
- OKI-78SR maximum input;
- PB1R 12 V module input range;
- OKI-78SR stress margin.

The full list of data to gather is in kit_v23/system_compat.json (`data_to_gather`, 12 items) and in ASSUMPTIONS 24-28.
