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
