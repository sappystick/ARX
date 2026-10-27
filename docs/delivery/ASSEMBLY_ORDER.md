# Assembly order (first experimental build; MODELED design, nothing built)

Sources: docs/DESIGN_STATE.md section 3 (vault levels), docs/design/UPPER_ASSEMBLY_v1.md, docs/design/BENCH_FIRST_ARTICLE_TX.md, releases/TX_r2, releases/RX_r1, docs/delivery/SYSTEM_MANIFEST.csv.
Steps marked NOT SPECIFIED have no source in the repository: they are listed so nobody assumes they were designed.

## 0. Before anything is assembled
1. Print every PRINT-class STL of stl/head, stl/pins, stl/yoke, stl/upper, stl/shaft_handle (classes and print-check state: SYSTEM_MANIFEST.csv). Print upright; rib undersides of the cylinder need supports (DESIGN_STATE section 3). Generate the six formers with `make formers-print` (about 70 MB each, not stored).
2. Order the boards: transmit region from releases/TX_r2 (PB1R, CB1D, TXJ1, PM2, HB2); LB1, HTA and SB1R-QA / SB1R-QB from data/gerber; AB1A / AB1B from releases/RX_r1 ONLY AFTER BLOCKER 1 (exposed-pad land pattern) is closed. Fabricator DRC and a CAM-viewer pass are open (U-FAB-DRC, U-CAM-VIEW).
3. Purchased parts: docs/delivery/PURCHASED_PARTS.csv (the AB1 rows are the AD7389-4 build) and data/results/BOM_SHAFT_YOKE.csv. Datasheets that were refused are listed in docs/UNVERIFIED.md.

## 1. Head, bottom up (hub frame, z up; heel at 178 deg)
| Level | z (mm) | Step |
|---|---|---|
| L0 | 0-3.2 | base plate v3 with SB1R-QA and SB1R-QB (two stacked 4-layer D228 boards) in the recess |
| formers | 3.2-28.8 | six petal formers L1..L6 (pitch 4.4 mm) wound with litz and connected in parallel (54 uH); lead path through the lane ports (z 38-40) and the wall-top channel to the 178 deg window |
| L1 | 3.2-9.0 | gallery: RX leads (4 twisted pairs), spine flex start (NOT SPECIFIED: rigid-flex spine), 3 M3 bosses |
| L2 | 9.8-20.0 | analog cell: tray, then AB1A and AB1B (D40, x = -/+20.3 mm) with the 0.3 mm shim; J2 links to CB1D |
| L3 | 20.0-21.9 | septum frame with the copper cloth (D62 window) |
| L4 | 21.9-27.0 | absorber cell (carbonyl-iron silicone) |
| L5 | 27.0-38.8 | CB1D controller (D78) in the rib slot, parts up to 10.2 mm |
| L6 | 39.2-40.8 | LB1 display (D78), 66 LEDs under the pixel holes |
| L7 | 41.3-44.5 | removable roof plate (nylon M3 into 8 posts at r42.5) |
| L8 | 44.5-47.1 | cap D104 with the HTA antenna board |
Eddy rule while assembling: no solid copper plane, foil ring or closed metal loop around the axis inside the vault; planes hatched, septa mesh, liners slit.

## 2. Transmit region and yoke
1. TXJ1 board in its cradle; transmit leads run in the wall-top channel to the 178 deg window and TXJ1 (never inside the vault past the posts).
2. Umbilical bridge and lid; heel saddle tower on the skirt (0.4 mm epoxy gap); hinge to the arm.
3. Neck module: PB1R in the pocket with its 9 hybrid cans toward the back wall, hot-zone dam, lid, fill (alumina-filled silicone / syntactic silicone as in the NPM notes).
4. Flyback nets (hundreds of volts): 1.0 mm clearance on boards, 630 V parts, no routing under the connector lanes.

## 3. Shaft and upper assembly (UPPER_ASSEMBLY_v1)
S-stem with armrest cup, grip, index-finger boost trigger (HB2 grip board), top and bottom housings (PM2 under the bottom housing), quick-swap battery dock on T rails (7S1P Molicel P30B, MT60 with the interlock loop), twin-cavity telescoping shaft (tube A OD33 / tube B OD28.5, cam collar), cord anchor and extended septum (U8_SEPTUM_extended is oversize for a 250 mm build volume: print split, NOT SPECIFIED).

## 4. Fill, potting and closing
Potting / epoxy sequence, cure times and the final bonding of the roof and cap: NOT SPECIFIED (materials research for the vault was requested but not completed).

## 5. First bring-up
Follow docs/design/BENCH_FIRST_ARTICLE_TX.md for the transmit stage. Receive chain bring-up (AD7389-4 readout, 2-wire mode: SDOA = channels A then C, SDOB = channel B; SDI tied low; +3V3D budget) is NOT SPECIFIED and needs a CB1D firmware change; every performance number stays MODELED until measured.
