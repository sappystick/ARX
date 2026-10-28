# Potting sequence (B8, 2026-10-28): order of operations for the first build

MODELED design, nothing built or potted. This file fixes the ORDER and the KEEP-OUTS that the geometry and the checks in this repository already define. Resin products, mix ratios, cure schedules and the final adhesive are NOT SPECIFIED: no material datasheet is on disk, so none is quoted here (rule 7). Every pour is irreversible: each step starts only after the bench items it covers are done (docs/design/BENCH_FIRST_ARTICLE_TX.md, all NOT RUN today).

## Rules for every pour
1. Eddy rule (CLAUDE.md rule 5): no conductive filler that can form a closed loop around the head axis; the absorber is carbonyl iron dispersed in silicone (a powder in an insulating binder), the hot-zone filler is alumina (insulating).
2. HV rule (rule 6): the flyback nets (DRAIN1, CLAMP1, the TX pair) keep their 1.0 mm board clearance; potting must wet them without voids (vacuum degas), and nothing is potted before the flyback-node bench checks are done.
3. Never pot a connector body, a test point needed later, or a cable passage (keep-outs below). Mask them with removable inserts.
4. Before each pour: continuity against the netlist and the bench items of that sub-assembly. After cure: repeat continuity (stress from shrinkage) and re-run the leak / ring-down bench items.

## Order
| # | Sub-assembly | What is poured, where | Keep-outs (must stay open) | Starts only after |
|---|---|---|---|---|
| 1 | Neck module (NPM, src/mech/mech_v20.py) | PB1R in the pocket, components toward the back wall; hot-zone dam v2 (x -5..-3) bonded; alumina-filled silicone in the hot zone (50.3-57.2 cm3, exact mesh volume, P2), syntactic silicone in the rest (62.0-70.6 cm3) through the lid fill ports (NPM_N2_lid_with_fill_ports: 2 fill tubes + 2 vents) | JL1 (TX pair), JP (power), JC (umbilical) bodies and the 12 mm cable window at x -26..-14; the shunt Kelvin test points | PB1R bench items (continuity, current-limited power-up, ton calibration, Vds / flyback timing, damping, thermal) |
| 2 | Head gallery L1 and analog cell L2 (potting map 2026-10-28) | soft silicone gel (GEL class) in L1 (34.8 cm3) and L2 (52.3 cm3, exact mesh booleans): locks the RX leads, the AB1 boards and the FFC links against vibration (microphonics) without hard-resin stress | spine duct and comb windows (masked insert), AB1 test points used on the bench | RX and AB1 bench items; PT3 microphonics baseline unpotted |
| 3 | Link cables (B5 decision) | two FFCs placed from the AB1 boards through the AB1-level comb window, up the 90 deg spine duct, out through the CB1D-level window (link_path_check.py) | the whole duct x -6..6, y 40..44, z 12..29.5 and the four comb windows | AB1 receive bring-up (readout model: docs/design and src/sim/ad7389_readout.py) |
| 4 | Septum L3 | septum frame bonded in the rib slots; copper cloth over the D62 window, rim sealed with silicone (parts_v22 SEPTUM_FRAME_v5 note) | the spine gap of the frame (+-8 mm at 90 deg) | step 3 |
| 5 | Absorber cell L4 (z 21.9-27.0) | carbonyl-iron silicone cast on the septum, inside the bore r < 44 (28.9 cm3 exact: 31.0 envelope minus core ribs 1.75, comb 0.12 and the duct insert 0.24) | the spine duct and its windows (masked insert); the rib slots CB1D sits in; 0.2 mm under the CB1D bottom face | step 4 cured; leak measured with and without the absorber is a bench item (U-BENCH) |
| 6 | CB1D L5, LB1 L6, receive boards L0, cap L8 | conformal coat only (potting map): CB1D (Pico antenna, tall parts under LB1) + wire staking, LB1 clear coat (LEDs), SB1R coat only (a pour adds RX-coil capacitance) | CB1D JDBG pads, LED windows | step 5 cured |
| 7 | Roof, cap | roof plate on nylon M3 (removable); cap with HTA: final bond NOT SPECIFIED | - | all head bench items |
| 8 | Upper assembly (potting map) | SYN syntactic silicone in the U3 PM2 bay up to 1 mm under AU1 (27.0 cm3, lower bound) and in a pocket around HB2 in U1 (2.9 cm3); AU1 coated + staked | grip channels, shaft twin cavity (moving cords), battery pack and dock (removable pack, cell venting), AU1 SWD pads, trigger / dial / button / latch | AU1 programmed and PM2 / HB2 bench items done |

**Coil windings (potting map 2026-10-28): no pour.** The transmit model shows that any fill around the turns raises the coil self-capacitance enough to push the
quiet time past the first receive gate (air margin 0.35 us; SYN at er 1.6 and phi 0.3 already -0.04 us): lock the turns with thin SYN beads at the winding ends only
and confirm C_self / t_quiet on the bench (PT2) before anything else touches a former. Full map: docs/design/POTTING_MAP.md, data/results/potting_map.json.

## Volumes
Exact mesh booleans (src/mech/potting_volumes.py -> data/results/potting_volumes.json, pipeline step potting): cavity envelope minus the printed parts, the board and the
41 PB1R component bounding boxes (so the lower number is a lower bound on the free volume; the upper number ignores the components). NPM hot zone 50.3-57.2 cm3
(about 96-109 g at the ASSUMED 1.9 g/cm3), main zone 62.0-70.6 cm3 (46-53 g at 0.75 g/cm3), L4 absorber 28.9 cm3 (about 101 g at an ASSUMED 3.5 g/cm3).
The earlier box estimates (28 / 58 / 31 cm3) under-stated the hot zone by about half (CORRECTIONS). Mix 10-15 % above the upper number for losses and
weigh the first part to replace the densities and the component envelopes with measured values.
