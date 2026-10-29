# RF2 clean-sheet side experiment: transmit formation in a 1-inch head (MODELED)

Question (owner, 2026-10-29): inside the existing diameter and a 1-inch (25.4 mm) height, which layered / stacked / dense transmit-coil formation gives
the most depth together with the best signature data, with the dual-quadrupole receiver (RX-Q) and a central rigid-flex compute bay?
Nothing here touches the baseline. All numbers are MODELED: noise-limited, gold spheres, no ground, no bench data.

`rf2_coil_search.py` (about 20 s) -> `results/rf2_coil_search.json`; `rf2_figure.py` -> `results/rf2_coil_search.png`.

## Method
- Same physics as `src/sim/sim_head1.py`, re-parametrised: RX-Q geometry and noise, sphere step-off response, gate schedule, SNR 3, lateral search grid,
  the turn-off circuit and the first clean gate from the nulled turn-off tail (floor 6 us).
- **Fair comparison:** every candidate gets the baseline's energy per pulse at boost (1/2 x 54 uH x 20 A^2 = 10.8 mJ) and 20 A per switch. With the energy
  fixed, depth depends on the winding geometry through B / sqrt(L) only; the series / parallel split just trades current for inductance, and more switches
  (more total current at the same energy) make the turn-off faster.
- Coil: circular turns (exact elliptic-integral fields and inductances), litz 1.2 mm OD on a dense 1.6 mm grid, window z 3.2-21.9 mm (RX-Q boards below,
  lid + ferrite sheet + clearance above; the display sits in the centre bay), r up to 113.4 mm.
- **Validation:** the built coil through this chain: L 51.5 uH (model 54), 25.0 uT/A at 100 mm (24.56), moment 7.97 A m2 at 20 A (7.96), depth
  0.1 / 1 / 20 g = 90 / 134 / 188 mm (sim_head1: 91 / 136 / 189).

## Results (1 g / 0.1 g gold sphere, RX-Q)
| Formation | 1 g | 0.1 g | Notes |
|---|---|---|---|
| Built coil (25.6 mm tall, does not fit 1 in) | 134 | 90 | first gate 7.1 us |
| 1 in, dense window r 62-113 (spread) ... r 100-113 (rim), 1 switch | 136 | 91-92 | geometry changes depth by <= 1 mm at fixed energy |
| 1 in, rim r 100-113, 2 or 4 switches | 137 | 94 | turn-off 3.8 -> 1.9 us; first gate reaches the 6 us receiver floor |
| + ideal ferrite plane above (UPPER BOUND) | 143 | 98 | the real hood v3 model gave about half of an ideal plane's gain |
| Quadrant set, X mode (horizontal field, shape probe) | 131 | 93 | nearly as deep as the vertical mode with RX-Q |
| Built coil with the figure-8 receiver (sim_head1) | 152 | 99 | the receiver, not the transmit formation, is the largest depth lever |

First-gate sensitivity (4-switch rim coil): 6 / 4 / 3 / 2 us -> 0.05 g 79 / 85 / 88 / 91 mm, 0.1 g 94 / 98 / 100 / 102 mm, 1 g 137 / 139 / 139 / 140 mm.

## Reading
1. **A 1-inch head costs no depth.** At the same pulse energy the dense 1-inch windings match or beat the 25.6 mm stacked coil (136-137 vs 134 mm).
2. **No transmit formation is a big depth lever in this footprint.** Spreading or concentrating the turns, stacking or not: <= 2 mm. Depth moves with
   pulse energy (signal ~ sqrt(E): 2 x energy -> about +7 %), the receiver (figure-8 152 vs RX-Q 136 mm: RX-Q trades about 11 % depth for bearing and
   pinpoint), noise and averaging.
3. **Best formation for depth + signature:** a dense rim winding (r about 100-113 mm, full window height) split into interleaved full-ring branches on
   2-4 switches: fastest turn-off at the same energy (better small / fast targets once the receiver recovers sooner), same depth, frees the centre bay.
4. **Quadrant windings (Z + X / Y modes) give a strong shape channel (X mode 131 mm at 1 g) but a 1 % current mismatch between quadrants puts about
   0.49 V into RX-Q at turn-off** (the built coil's aligned leak is 0.01 mV). The vertical mode must stay on symmetric full-ring branches; X / Y needs
   its own matched pair winding and a receiver that recovers from that leak. Not yet modeled: the pairs' turn-off, X-mode energy, recovery.
5. **Small targets:** the remaining limit is the receiver recovery floor, not the coil: 6 -> 2 us adds about 15 % depth on 0.05 g.

## Not modeled
Ground (mineralisation: the early gates that help small gold also see more ground), coil self-capacitance, litz AC resistance, eddy currents in the head
and the compute bay, the real (finite) ferrite sheet, thermal. Next if pursued: figure-8 / DD / concentric receive options in the same chain with the
rim coil, a matched X / Y pair winding with its turn-off and leak, a finite ferrite sheet, and ground.

## Step 2: receiver architecture, light coil, mass, and an SDC 2300-class comparison (`rf2_receiver_combo.py`, `results/rf2_receiver_combo.{json,png}`)
Owner: targets of 1 g and up only. Same physics and equal energy per pulse (10.8 mJ); every receive channel read with the same preamp noise (1.7 nV/rtHz).

| Architecture (1-inch head, rim transmit coil) | 1 g | 5 g | 20 g | Uniform-ground coupling (rel. CN) |
|---|---|---|---|---|
| QUAD only (built receiver) | 137 | 165 | 190 | 0 by symmetry |
| Figure-8 only (check: sim_head1 at the same noise gives 179 mm at 1 g) | 181 | 223 | 262 | 0 by symmetry |
| Concentric nulled (12 turns r 80-95, 26 bucking turns r 65) | 231 | 284 | 337 | 1.0 |
| **Proposed: rim mono (26 turns, 321 uH, 8.2 A) + QUAD board, mono channel, 15 us gate** | **345** | **439** | **>= 500** | 1.44 |
| same, QUAD channel (bearing, pinpoint, depth ratio) | 131 | 162 | 189 | 0 by symmetry |
| SDC 2300-class 8 in mono at EQUAL electronics, 10 us gate (internals ASSUMED) | 330 | 413 | 494 | 1.40 |

- **Light transmit winding:** 24 turns (16.9 m of litz) give the same depth as the 99-turn dense window (66.6 m): at fixed energy only B / sqrt(L) counts.
- **Depth readout:** the QUAD / mono peak-signal ratio falls monotonically with depth (0.118 / 0.026 / 0.0094 / 0.0043 / 0.0019 at 50 / 100 / 150 / 200 / 300 mm),
  independent of target size for a sphere: depth from the ratio, then size from the amplitude at that depth, type from the decay time constant.
- **Head mass estimate: about 0.53 kg** (component estimates, not weighed; baseline head estimate 2.22 kg). The SDC 2300 is 2.3-2.4 kg as a whole
  detector without batteries; its coil mass is not published, so no head-to-head mass comparison is made.
- **SDC 2300 published facts used:** 8 in round mono, hardwired; Multi Period Fast PI; 2.3-2.4 kg without batteries; 4 x C cells, about 7 h; no
  discrimination, depth readout or pinpoint mode; LED indicator + audio; waterproof 3 m. Not published: turns, inductance, current, timing, noise, depth.
  The SDC row is therefore an 8 in mono with OUR electronics, not the real detector.
- **Reading:** the mono channel is the deepest receive option for >= 1 g (the full transmit coil is the receiver: the largest area); the proposed
  head's mono is about 4-5 % deeper than an 8 in mono at equal electronics, from the larger diameter only. What the proposed head adds is the QUAD
  channel (bearing, peak-null-peak pinpoint, a ground-symmetric second channel) and the ratio depth readout.
- **The bucking-turn cap:** an unconstrained concentric search chose 1239 turns at r 12 mm (cannot be laid out; capacitance and resistance noise not
  modeled); the search caps the bucking winding at 30 board-trace turns (0.3 mm pitch, 4 layers, a 6 mm band holds about 80).
- **Not modeled, and decisive in the field:** real ground. The mono and CN channels see a uniform viscous ground strongly and need ground balance
  (as the SDC has); the QUAD and figure-8 cancel uniform ground only while the head stays level and at constant height. Hot rocks, layering and
  sweep tilt are not modeled. Also not modeled: the mono's damping-resistor noise and preamp overload recovery (the 1.7 nV/rtHz is generous to both
  monos), self-capacitance, eddy currents in the compute bay.

## Step 3: mineralised ground and how to cancel it (`rf2_ground.py`, `results/rf2_ground.{json,png}`)
Ground model (Born approximation, uniform magnetically viscous half-space, ASSUMED parameters swept): emf = I chi_v / mu0 x G(h, tilt) x [t^-a - (t+T)^-a];
G = integral of Bt . Br over the ground. Varies while sweeping: height 15-45 mm, tilt about 3 deg, exponent a = 1 +- 0.03, patchy amplitude x lognormal(0, 0.3).
chi_v 2e-6 / 2e-5 / 2e-4 (mild / moderate / severe) is an ASSUMED order of magnitude, not a measured soil. Optimal linear detectors (SINR = s' R^-1 s).

| 1 g depth (mm) | none | mild | moderate | severe |
|---|---|---|---|---|
| D1 mono, no ground balance | 362 | 0 | 0 | 0 |
| D2 mono, time-domain balance | 366 | 244 | 221 | 204 |
| **D3 mono, multi-period (PWM flat-top) balance** | 367 | **249** | **228** | **221** |
| D4 quadrupole pair only, no balance | 137 | 128 | 88 | 0 |
| D5 / D6 mono + QA + QB space-time (with / without multi-period) | = D2 / D3 | | | |
| D7 + dual transmit (inner coil, alternate pulses) | 350 | 239 | 220 | 212 |
| SDC 2300-class 8 in mono, multi-period (equal electronics) | 342 | 235 | 216 | 209 |

- The quadrupole sees uniform ground only through tilt, at second order (level ground: 1e-29 vs the mono's 4e-11; 3 deg tilt about 1e-3 of the mono).
- In uniform ground the time signature does the work: multi-period (two PWM on-times) is the best method; the quadrupole array and dual transmit add nothing
  (dual transmit splits the pulses and loses a little).
- What costs depth is the spread of the ground's decay exponent: tracking it (severe ground, 1 g) 0.03 -> 0.01 -> 0.003 -> 0: 221 -> 227 -> 249 -> 274 mm.
  Even a perfectly known exponent leaves about 25 % loss against no ground: the unknown 1/t amplitude overlaps the target's decay.

## Step 4: a firmware-style ground-tracking detector on simulated sweeps (`rf2_ground_dsp.py`, `results/rf2_ground_dsp.json`)
Frames of 36 numbers (mono at both PWM periods, QA / QB with both periods averaged: every pulse is received by every coil); ground learned as a low-rank
subspace per receiver (eigen-directions above the electronic noise, EWMA, an 80-frame "ground pump" at switch-on, a guard window so a target's flanks are
not learned, an anti-lock rule); GLRT over a bank of 12 decay constants, silent below the chi-square threshold (false-alarm rate 1e-5 per frame).
- **0 false-alarm frames** on target-free sweeps over severe and moderate ground.
- 1 g detected at 100, 150, 200 mm (severe and moderate); decay constant 27.3 us against 27.9 us true -> "small gold". 5 g at 250-280 mm and 20 g at
  300 mm were NOT detected in one pass (peak statistic 20-24 vs threshold 25.9): the adaptive detector with a strict false-alarm rate reaches less than
  the oracle study above.
- Readouts, honestly: the quadrupole's single-pass range for 1 g is about 80-100 mm (noise-only check: SNR 29 / 4 / 0.5 at 60 / 100 / 150 mm), so bearing
  and ratio depth only work close in; the mono response width resolves depth only beyond about 160 mm (the 230 mm coil sets a floor); between, depth
  is "<= 160 mm" and size an upper bound. Next: a trigger-held pinpoint (boost + averaging) for bearing / depth / size, and the 100-160 mm gap.
- Mistakes found and fixed on the way: rank 3 ground subspace (the ground needs about 7 directions: 79 of 81 frames falsely triggered); a quadrupole
  "signal" that was the best of 81 noise frames (gate raised to SNR 5); a tracker that learned the target's flanks (guard window); quadrupole fed only
  half the pulses.

## Step 5: is every coil fully off when the receivers listen? (`rf2_timing.py`, `results/rf2_timing.json`)
Two coupled coils with node capacitance, damping, clamp diode / capacitor and the switch's body diode; nonlinear part by ODE, linear tail exact (matrix
exponential, resolved to 100 nV); preamp recovery 2 us and coil capacitance 500 pF ASSUMED.

| Case (first clean gate, us) | mono | QUAD | current induced in idle coil B |
|---|---|---|---|
| rim coil alone, critical damping | **16.3** | 9.2 | - |
| rim coil alone, baseline damping ratio (underdamped) | 24.8 | 13.5 | - |
| + idle B wound the same sense | 21.7 | 11.6 | 0.34 A (through its damping only) |
| + idle B wound the opposite sense | **36.7** | 24.0 | **1.5 A** (its switch's body diode conducts) |
| + idle B, clamp not yet charged (first pulses) | 27.2 | 17.1 | 1.6 A |

- The assumed 15 us mono gate holds for a critically damped mono (16.3 us): 1 g depth 363 vs 367 mm, severe ground 221 either way. Use critical damping.
- Dual transmit needs: both coils wound the same sense, clamps pre-charged before the first pulse, and about 5 us more delay from the idle coil's damping.
- Nothing is left at the 2.5 ms period (residual about 0).
