# PHI-FOLD 233 v11 - individual petal coil formers + central PCB cylinder (print sheet)
Units mm. Every part is its own STL. Print the formers flat with the grooved face UP. Non-conductive filament only (PETG / ASA / PA12); NO carbon-fibre or metal-filled material. Print a fit coupon (pin stem in half-hole, tooth in track) first.

## Parts
| File | Qty | Note |
|---|---|---|
| FORMER_L1_petal_coil_former.stl ... FORMER_L6_petal_coil_former.stl | 1 each | six different formers; L1 is the top (base) former, bond it to the central cylinder |
| CORE_PCB_CYLINDER_central_former.stl | 1 | hub: tube r44.0-49.5, roof to z44.5 with D20 port, 6 numbered tracks, 18 wire lanes, 4 PCB ledges (print upright) |
| PINS_interface_1_x3.stl ... PINS_interface_5_x3.stl | 1 each | 3 stepped pins per interface (print upright) |
| PINS_interface_6_x3_lock_collar.stl + V2_lock_collar_ring.stl | 1 each | bottom interface |
| V2_floor_plate_and_lock_seat.stl, L7_RX_tray_cassette.stl | 1 each | floor plate and receive tray |
| FORMER_Lk_winding_centerline.csv | 6 | x, y, wire-centre z per segment (lead_A_in, out_arm, return_arm, lead_B_out) |

## Winding groove (all six formers identical, rotated by (k-1) x 137.508 deg)
Wire: 1.2 mm insulated diameter MAX. Groove: 1.5 top width, 1.2 floor width, 1.3 deep (wire sits 0.1 below the land). Arm crossings have a 2.4 deep pocket so two wires stack. 8 turns out + 8 turns mirror return = 16 turns per layer, same circulation (moments add). Fermat spiral: rho^2 = R0^2 + (R1^2 - R0^2) t, R0 = 62.0, R1 = 109.6; petal ripple 2.4 (rho/R1)^2 cos(12 (theta - alpha)), alpha = (k-1) x 137.508. About 8.96 m of wire per layer plus leads. Wind from lead A (inner end of the out-arm) to lead B; both leads are straight radial grooves to the bore.

## Tracks, lanes, key teeth (degrees from +x axis, counter-clockwise)
| Layer | track / key tooth | TX lanes A / B | RX lane | dimples | hub stop plug z |
|---|---|---|---|---|---|
| L1 | 0.00 | 6.00 / 11.00 | 16.00 | 1 | None |
| L2 | 137.51 | 143.51 / 148.51 | 153.51 | 2 | 33.08 |
| L3 | 275.02 | 281.02 / 286.02 | 291.02 | 3 | 28.72 |
| L4 | 52.52 | 58.52 / 63.52 | 68.52 | 4 | 24.32 |
| L5 | 190.03 | 196.03 / 201.03 | 206.03 | 5 | 19.88 |
| L6 | 327.54 | 333.54 / 338.54 | 343.54 | 6 | 15.55 |
Key tooth 3.6 wide x 2.6 high; hub track 4.0 wide x 3.0 deep, closed (blind) above the stop plug. Bore 49.9 on L2-L6, 49.3 on L1 (bonded to the hub). Hub lanes 1.8 wide x 1.4 deep.

## Pins (3 per interface, angle = n x 137.508 deg, centre radius 51.7)
| Interface | n | angle | stem bottom z | shoulder z | stem top z |
|---|---|---|---|---|---|
| 1 | 2 | 275.02 | 29.09 | 32.41-33.21 | 36.46 |
| 1 | 3 | 52.52 | 29.01 | 32.46-33.26 | 36.46 |
| 1 | 4 | 190.03 | 29.01 | 32.41-33.21 | 36.36 |
| 2 | 5 | 327.54 | 24.69 | 28.09-28.89 | 32.04 |
| 2 | 6 | 105.05 | 24.6 | 27.95-28.75 | 32.03 |
| 2 | 7 | 242.55 | 24.63 | 28.11-28.91 | 32.02 |
| 3 | 8 | 20.06 | 20.18 | 23.67-24.47 | 27.57 |
| 3 | 9 | 157.57 | 20.27 | 23.57-24.37 | 27.65 |
| 3 | 15 | 262.62 | 20.2 | 23.69-24.49 | 27.61 |
| 4 | 16 | 40.12 | 15.75 | 19.24-20.04 | 23.16 |
| 4 | 17 | 177.63 | 15.93 | 19.24-20.04 | 23.29 |
| 4 | 18 | 315.14 | 15.75 | 19.2-20.0 | 23.2 |
| 5 | 19 | 92.65 | 11.43 | 14.88-15.68 | 18.88 |
| 5 | 20 | 230.16 | 11.43 | 14.83-15.63 | 18.78 |
| 5 | 21 | 7.66 | 11.43 | 14.78-15.58 | 18.86 |
| 6 | 22 | 145.17 | 6.0 | 10.0-11.23 | 14.11 |
| 6 | 23 | 282.68 | 6.0 | 10.0-11.23 | 14.11 |
| 6 | 24 | 60.19 | 6.0 | 10.0-11.23 | 14.11 |
Layer gap 0.8 (shoulder height; interface 6 is taller). Stem D3.0 in a D3.8 half-hole, shoulder D4.2, 0.4 radial clearance: glue or press-fit after the coupon.

## Assembly order
L1 is bonded to the hub. Slide L2 up the hub with its tooth in track 2 (137.5 deg) and put interface-1 pins through L2 into L1, then L3 ... L6 the same way (interface i pins go through layer i+1 into layer i), then the lock collar with interface-6 pins, then the floor plate and receive tray. Wind each layer on the bench first and route lead A and lead B down their two lanes to the roof.

## Verified from the print meshes (audit_*.json)
Hub: 24 of 24 notches at the intended angles; tracks 3.9-4.0 wide (spec 4.0) and 3.0 deep; lanes 1.73 wide (spec 1.8) and 1.4 deep. Formers: key tooth 3.57 x 2.60 at the exact track angle; outer radius 116.5; bore 49.9 / 49.3. Grooves (slope-corrected, layers 2, 4, 6): width at half depth 1.37 +/- 0.30 (spec 1.35), centreline offset 0.00 +/- 0.15 (max 0.5 near crossings), depth 1.22 (spec 1.3). Mesh grid is 0.2 mm radial: treat features as accurate to about +/-0.15 mm.
