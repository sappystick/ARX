# PHI-FOLD 233 design state (read this first)

Status date: end of the session that produced this repo. Everything below is MODELED unless it says "built". Nothing has been printed, wound, assembled or measured.

## 1. Transmit coil (six golden-angle petal formers, flat-face, v15)
- Six formers L1..L6, R 116.5 mm, layer 3.6 mm, gap 0.8 mm, pitch 4.4 mm, stack z 3.2-28.8 (z = 0 at the underside of the base plate).
- Winding: Fermat/sunflower spiral rho^2 = R0^2 + (R1^2-R0^2) t, R0 62.0, R1 109.6, 8 turns out + 8 mirrored back (16 turns/layer). Petal ripple r = rho + 2.4 (rho/R1)^2 cos(12 (theta - alpha_k)); face z_top = z_bottom + 3.6 + 0.30 (r/116.5)^2 cos(12 (theta - alpha_k)). alpha_k = (k-1) x 137.50776405 deg (the same step for every layer, 17.508 deg mod 30 for the petals).
- Groove 1.5 top / 1.2 floor / 1.3 deep (2.4 at crossings) for litz up to 1.2 mm OD. Lead A = track+6 deg, B = +11, RX = +16. 15 stepped pins (interfaces 1-5, 3 each) at r51.7, angle n x 137.508 deg. L1 has 6 bond-key notches.
- All six layers in parallel: L = 54 uH (modeled), R about 45 mohm, 53.8 m litz, moment 7.96 A m2 at 20 A (3.19 at 8 A). Axis field at 20 A: 1136 / 491 / 231 / 122 / 44 / 20 / 11 uT at 50 / 100 / 150 / 200 / 300 / 400 / 500 mm below the head.
- Audited on the print-resolution meshes: flat undersides (0.000 mm), layer gap 0.81 mm mean (min 0.53), key teeth and notches at the exact angles.

## 2. Ferrite hood v3 (modeled gain, not measured)
13 radial spokes at k x 360/13 deg (head frame, spoke 1 at 0 deg), one stepped pocket per spoke holding two 2.5 mm MnZn tiles butted end to end (design joint 0.2 mm, adhesive): inner 27.0 x 26.2 (r57.0-84.0), outer 28.3 x 39.7 (r84.2-112.5), tiles z30.4-32.9; 1.7 mm between neighbouring spokes, 0.15 mm pocket clearance; carrier r52.6-116.1, z29.4-33.4 (outer frame corner r115.81), 286 g of ferrite; print flat on the base ring, no supports, tiles bonded after printing (src/mech/hood_v20.py, 8/8 checks, docs/figures/HOOD_V3_LAYOUT.png).
Field (src/sim/hood_axi.py, axisymmetric magnetostatic model, coil validated against Biot-Savart within 0.1 % at 50-500 mm; Wiener bounds on the tile/air homogenisation; image-method limit reproduced to 96-97 % at 100-200 mm; grid refinement changes the gain by 0.2 points): v3 +17.0-18.5 / +13.0-14.1 / +10.3-11.2 % on the axis at 100 / 200 / 300 mm (range = butt joint as a series gap .. no gap); v2 (2 mm radial gap between separate pockets) +12.7 / +9.8 / +7.8 %; continuous plate limit +22 / +17 / +13 %. The hood does not steer the field sideways: it returns the upward flux and pushes the field lines down; the gain sits inside r150 mm of the axis (at 200 mm depth B_z 138 / 134 / 122 uT at 20 A for v3 / v2 / no hood) and the return field outside r200 mm is slightly stronger. Peak flux density in the tiles at 20 A 52-56 mT (far below MnZn saturation). Thicker tiles (5 mm, 556 g: +11.8 %) or more spokes (21: unchanged) gain less per gram than closing the radial gap. Hood v2 and its STLs are superseded (src/archive/hood_v19.py).

## 3. Central cylinder v5 and the vault levels (hub frame: z up, heel at 178 deg)
| Level | z (mm) | Content |
|---|---|---|
| L0 | 0-3.2 | base plate v3 + SB1R-QA and SB1R-QB receive boards (two stacked 4-layer D228 boards) |
| L1 | 3.2-9.0 | gallery: RX leads (4 twisted pairs), spine flex start, 3 M3 bosses at r28 (22.5/157.5/247.5 deg) under the floor |
| L2 | 9.8-20.0 | analog cell: tray + AB1A/AB1B (D40 each, x = -/+20.3), 0.3 mm shim |
| L3 | 20.0-21.9 | septum frame + copper cloth (D62 window) |
| L4 | 21.9-27.0 | absorber cell (carbonyl-iron silicone) |
| L5 | 27.0-38.8 | CB1D controller (D78) in the rib slot, parts up to 10.2 mm |
| L6 | 39.2-40.8 | LB1 display (D78), 66 LEDs under the pixel holes |
| L7 | 41.3-44.5 | removable roof plate (nylon M3 into 8 posts at r42.5) |
| L8 | 44.5-47.1 | cap D104 + HTA antenna board |
Cylinder features: tube r44-49.5 with lanes/tracks/18 lead ports (z38-40), 6 low RX ports (z4.3-6.3), exit window at 178 deg (z34.4-40.6, 13.3-15 wide), collar r49.5-52, floor z9.0-9.8 with a 12 mm spine slot (r28-37 at 90 deg), 8 ribs at 24/48/109/135/225/244/300/317 deg (moved from 28/48/112/130/235/255/305/355 because the JPW terminal block and a 0603 capacitor on CB1D collided with the 130 and 235 deg ribs) (z19.0-39.2, slots 20.0-21.9 and 27.0-28.9), spine channel walls at 90 deg, 66 pixel holes in the roof.
Checks: 22/22 pass (check_v22.py). Print upright; rib undersides need supports.

## 2b. Eddy rule (critical)
A solid 1 oz copper plane D78 decays with tau = 17.8 us (2 oz 35.6, 50 um foil 26.4) and carries about 2000x the signal of a 1 g gold nugget per tesla. All vault boards need hatched/meshed planes; septa are copper mesh; liners are slit; there is no closed metal ring around the axis.

## 4. Boards
| Board | State |
|---|---|
| AB1A / AB1B (D40, 6-layer) | routed earlier (0 opens/shorts), legacy kits; relabelled for RX-Q; RS3 1k -> 100 ohm |
| CB1D (D78, 64 parts) | placed, ERC 0; routed 46/46 nets on 6 layers (GND In1 and P3V3 In4 hatched, HV nets 1.0 mm); one net needed a manual tie (route_fix ECO); independent DRC 0 violations, 0 opens, min gap 0.17 mm (rule 0.2); notch at 90 deg; Gerbers + routed KiCad file; not opened in KiCad/CAM |
| LB1 (D78, 81 parts) | routed 68/68 with pad stubs; independent DRC 0/0, min gap 0.25 mm; hatched planes; notch at 90 deg; Gerbers v3 + routed KiCad file; not opened in KiCad/CAM. The earlier Gerbers (v2, no stubs) are DEFECTIVE: do not use |
| HTA (D90, 4-layer) | Gerber + drill generated; coil 2 x 1.915 turns r35.5-43, about 2.8 uH; not opened in a CAM viewer |
| SB1R-QA / SB1R-QB (D228, 4-layer each, through vias only) | generated (src/pcb/sbq_*.py): KiCad + Gerbers; 4 lobes x 4 series stepped spirals of 6 full rings, 24 turns/lobe, 16.9 m copper, 0.8 mm trace, L 176 uH, R 10.4 ohm (1 oz); B = A rotated 45 deg; hole margin 2.4 mm, via margin 0.9 mm; no external DRC |
| PB1R / PM1 / HB1 | neck driver / power path / handle sensors: placed, not routed (legacy kits) |

## 5. Transmit stage (simulated from the real PB1R/CB1D netlists)
Topology: coil 54 uH || 330 ohm damping chain (3 x 110 ohm R2512, on CB1D); 2 x IPB65R095C7 (650 V); clamp = ES3J -> 2 x 100 nF 630 V (CL1A/B) || RCL1 5 kohm 10 W to VBUS (a capacitor snubber, NOT a hard voltage clamp); VBUS 26 V.
As built (2 x 100 nF X7R, derated): Vds peak 341-379 V, current zero 4.7-5.0 us, quiet 6.4-6.7 us, RCL1 3.9-4.7 W, damping chain 0.33-0.36 W. With ONE 100 nF C0G/film: 462 V (29 % margin), 3.8 us, 5.6 us, 0.46 W in the damping chain. 68 nF: 549 V (15 % margin, too tight).
Power: scan 8 A/800 Hz about 4.7 W, boost 20 A/400 Hz about 7.7 W (11.8 h on 90.7 Wh), coil copper loss 0.1 W.

## 6. Receiver platform RX-Q (modeled from the real Gerber copper)
Two rotated quadrupole boards (SB1R-QA, SB1R-QB) replace the figure-8 net. Leak at turn-off with the 100 nF film clamp: figure-8 off 0.5 mm 630 mV; QA 0.01 mV aligned, 0.02 / 0.13 / 3.9 mV at 0.1 mm / 0.5 mm x / 0.5 mm y; QB about 0, 0.85 / 4.4 / 11 mV. The aligned nulls come partly from tuned link radii (sbq_tune.py), so real leak will be set by fabrication tolerance: keep the digital air template. Pattern: sin 2phi / cos 2phi, RSS flat within +-2.5%, bearing = 0.5 atan2(B,A) + 45 deg (scatter 0.3-0.5 deg). Signal 3.2x the earlier idealised quadrupole. The coil (176 uH, 10.4 ohm) rings for more than 60 us without a damping resistor; with 470-680 ohm across it the first clean gate is 5.2 us (A aligned) to about 8.3 us (11 mV leak), 100 pF self-capacitance. Input noise about 1.7 nV/rtHz with RS = 100 ohm. Scaled depth estimate about 115 / 170 / 205 mm for 0.1 / 1 / 5 g gold (free air, no ground; scaled from the earlier simulation, unverified). The analog trim is dropped.

## 6b. Transmit coil system and how it fits the head (modeled)
Path of the 12 litz leads (6 layers x A and B, ports at track +6 / +11 deg): lane port (z38-40) -> wall-top channel (hub groove r45.6-48.6 z39.6-41.3 + roof channel r45.6-48.6 z41.3-43.5, 3.0 wide, 3.9 tall) -> 178 deg exit window (15 wide) -> TXJ1 junction board in the umbilical bridge -> AWG12 TX pair (0.8 m) -> PB1R JL1 (JL1.1 DRAIN1 = bus B, JL1.2 VBUS = bus A). Six leads per side reach the window; litz bundle fills 58 percent of the channel; longest lead 162 mm; DC current sharing between layers within 1.4 percent; lead-loop inductance 0.12 uH (0.2 percent of 54 uH). TXJ1: 23 x 11 mm 2-layer 2 oz board, bus A on top and bus B on the bottom (3 mm bars, 3 mm edge gap, 1.6 mm FR4 between layers), 12 PTH lead pads, two 4.2 mm AWG12 pads, two tap pads (AWG22 to CB1D JCL.2 = COIL_A and JCL.1 = COIL_B). Printed cradle TXJ1_CRADLE_v1 (14 x 25 mm footprint, divider rib) sits on the bridge floor at x' 53-78 (heel frame, x' outward along 178 deg). Blind-track fillers in the wall stop at z39.4 so the channel is clear. Schematics: docs/figures/TX_SYSTEM_SCHEMATIC.png (electrical) and TX_LEAD_ROUTING.png (plan).

## 6c. System audits (all modeled/geometric; none replaces bench or CAM verification)
- Wiring: 53 inter-board link pins checked against the real netlists and 59 harness conductors (HARNESS_MASTER_v2), 0 errors; spare inputs AB1A.J1.3 and AB1B.J1.1 are tied to VCM (no floating inputs).
- Stress table (data/results/SYSTEM_STRESS_MARGINS.csv): 24 pass, 1 watch (OKI-78SR 18 percent input margin), 1 fail by design: 66 LEDs at full white would draw 3.96 A on a 1.5 A rail, so firmware must cap LED current at 0.35 A and a hardware current limit is recommended. Ratings are from memory of datasheets: UNVERIFIED.
- Stack-up: boards vs printed levels all pass (tightest: CB1D parts to LB1 0.4 mm). LB1 must be a 0.8 mm board (1.6 mm put the LEDs into the roof) and JLB is flat wire pads (a header is 9 mm tall).
- Voxel interference (window, bridge, junction region, 0.2 mm): 0 interferences among hub, roof, hood carrier, bridge, lid, cradle, cap.

## 6d. Full head cross-check (release 5.3)
head_crosscheck.py assembles all 26 solids (formers, base plate, cylinder, tray, septum, comb, roof, cap, hood carrier, skirt, bridge, lid, cradle, boards with real rotated component bodies, receive boards, HTA, 66 pipes) and checks: layer stack, radial fits, 3D interference (0.5 mm), exact polygon tests of every CB1D/LB1 body against ribs, posts and spine walls, LED chain and holes (66/66), TX ports (12/12), SB1R pads in the floor slot, wiring and DRC results: 42 checks, 0 fail, 3 warnings (open items). fine_check.py repeats the board-vs-cylinder test at 0.2 mm: 0 intersections. Board notch (spine) widened to 7.6 mm half-width on CB1D and LB1 (spine wall outer face at 7.24 mm at r39). Drawings: docs/figures/SEARCH_HEAD_FULL_SCHEMATIC.png, HEAD_CUTAWAY_A_HEEL.png, HEAD_CUTAWAY_B_SPINE.png, HEAD_EXPLODED_LAYERS.png.

## 7. Thermal (axisymmetric finite volume, assumed conductivities and h)
Vault 1.13 W (boost): hot spot 34.2 C at 25 C ambient (8.1 K/W; 5.8 with alumina-filled silicone). Worst case with 0.5 W of LEDs 35.6 C.

## 8. Shaft, yoke, handle
Lower fixed GFRP tube OD32/ID29, 0.40 m; neck module PB1R at 0.40-0.484 m (field there about 6 % of the target-depth field); telescoping CFRP A OD33/ID30 (hand end) and B OD28.5/ID26, 0.45 m each, stroke 0.37 m, collapsed hinge-to-elbow 0.98 m, extended 1.35 m; ribbon cassette + trolley; bushings and nylon lock collar; serrated hinge (10 deg steps) at the heel; hinge axis x'=159, z=76 (heel frame); umbilical bridge to the hub exit window. Elbow socket tilted 43 deg (grip horizontal at a 47 deg shaft). Battery 7S1P 90.7 Wh. Head mass est. 2.22 kg; static torque about the grip 2.88 kg m (typical detectors 1.3-1.7; levers: steeper shaft, lighter formers, no hood, rear battery boom).
NOT DONE: redesign of the handle, knuckle and battery pod from the reference photos in docs/reference/photos (Minelab-style carbon telescoping shaft with a pivoting knuckle head mount; crutch-style armrest/grip with the quick-swap battery in the side pod where the yellow control box sits).
