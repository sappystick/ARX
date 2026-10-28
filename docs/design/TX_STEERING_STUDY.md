# TX field steering: separately driven coils (study 2026-10-28, MODELED; src/sim/tx_steer_study.py, regress row)

Owner question: drive the six petals separately, timed in sequence, to "spin" the field; the petals were meant to have their own wiring.

## What the built coil is
The six v15 layers are concentric full-ring spirals (R0 62 -> R1 109.6 mm) stacked at z 3.2-28.8 mm, all in parallel (54 uH). The golden-angle step
(137.5 deg per layer) rotates a 2.4 mm 12-fold ripple and the lead exits, not the coil centre. Each layer makes nearly the same round field, so firing
them one at a time changes the strength by height (top layer 0.69-0.88 of the bottom one on the axis), never the direction (ENHANCEMENT_REVIEW s.5).
Separate wiring per layer is possible with the existing lead tracks, but it cannot spin the field.

## What a steerable TX needs, and what it costs (Biot-Savart, 16 turns per coil, 20 A)
| Option | Field below the centre | Strength vs the main coil (100 / 200 / 300 mm) | Coupling into RX-Q |
|---|---|---|---|
| Main coil (today) | vertical | 1 | nulled (0 nH) |
| One offset coil (r 20-50 mm, 55 mm off axis), six fired in turn | tilted 40 / 22 / 15 deg toward the firing coil: turns with the sequence | 0.23 / 0.19 / 0.18 | about 4-5 uH: 22-25 V at turn-off (today 0.01 mV) |
| Push-pull pair (opposite coils, opposite current), three pairs | horizontal along the pair axis: 0 / 60 / 120 deg (sign gives the opposite ones) | 0.30 / 0.15 / 0.10 | ZERO by symmetry (quadrupole even, pair odd under 180 deg) |

## Reading
- A single-coil "spinning" field is incompatible with the dual-quadrupole receiver: every pulse would put tens of volts into the receive input.
- Push-pull pairs are the version that fits RX-Q: a field that steps round (horizontal, three axes) with the receiver still nulled. It is a near-range
  orientation / shape probe (it falls faster than the main field), not a depth gain. With the main (vertical) coil it gives two independent excitation
  directions, the basis of a target polarizability estimate (flat vs round, edge-on targets), and the response pattern over the pairs also carries the
  target's side.
- Cost if built: new former geometry (e.g. the top layer, which contributes least at depth, replaced by six offset windings wired as three pairs), three
  more driver stages (FET, clamp, gate drive, 630 V parts, >= 1 mm HV clearance), three more lead pairs in the wall-top channel to TXJ1, and interleaved
  pulses (each needs its own 449 us receive window, so the main PRF drops). Not modeled yet: the target response to the horizontal field through RX-Q, the
  pairs' self-inductance / turn-off, their leak with real winding tolerances, and the hood.
- Recommendation: keep the main coil as it is; treat push-pull steering as a phase-2 study (OPEN_ITEMS 44). For the user-facing goals now (left / right
  display, centring), the yaw gyro and the quad null do the job without a TX change.
