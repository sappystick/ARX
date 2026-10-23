# Upper assembly v1: S-stem, index-finger trigger, quick-swap battery dock, twin-cavity telescoping shaft (2026-10-23)

Everything below is MODELED or measured on the generated meshes. Nothing has been printed, wired or weighed. Assumptions are numbered in docs/ASSUMPTIONS.md (24-27).

## Owner decisions this design follows
- Model the stem on the XP Metal Detectors S-Telescopic stem with armrest (D044-A), 3D printed.
- The joystick is removed.
- The boost trigger sits where the index finger rests, at the top of the grip.
- The quick-swap battery slides on rails under the handle, where the grip base meets the forearm-cuff tube.
- A shielded double cavity runs down the shaft to the head, and the shaft telescopes.
- The battery is a 7S1P Molicel P30B pack with an MT60 connector, and the third pin is the interlock loop.

## What was built (generators and checks)
| File | What it does |
|---|---|
| `src/mech/upper_v21.py` | Generates the parts below in kit_v23/UPPER. |
| `src/mech/upper_check.py` | Measures 57 checks on the STLs: closed shells, grip, hand space, trigger, rails, pack bays, latch, insertion path, twin cavity, tubes, sockets, voxel interference, board fits, mass and torque. |
| `src/pcb/pw_design.py` PW=P / PW=G | Generates the PM2 (battery-dock power path) and HB2 (grip board) netlists. `pw_export.py` places them. |
| `src/pcb/power_dock_check.py` | 12 checks: interlock truth table, gate drive, soft start and inrush, ratings, cord drop, runtime. |
| `data/seed/harness/HARNESS_MASTER_v3.csv` | 50 conductors. The two coiled cords replace the power and signal ribbons. |
| `src/render/upper_figure.py` | Draws docs/figures/UPPER_ASSEMBLY_v1.png. |

Run it with `make upper` (it also runs `pcb-pm2`), or as part of `make verify-full`.

| Part | Description | Mass (mesh x density) |
|---|---|---|
| U1 top housing | Sealed shell 46 x 48, wall 2.5. Tube A socket (44 mm bonded). Dial and power-button bosses, trigger ears. HB2 inside. | 108 g |
| U2 grip | Hollow ellipse 40 x 32 (perimeter 113 mm), raked 16 deg. Septum: front channel carries the power pair, rear channel the button pair. | 68 g |
| U3 bottom housing | Shell 46 x 40. Armrest socket with 3 detents (insertion 90 / 68 / 46 mm). PM2 bay. | 118 g |
| U4 trigger | Lever on a pin through the U1 ears. Pad 3.5 mm in front of the grip, 3 mm travel. Magnet on a 22 mm tail. | 6 g |
| U5 armrest | Cup R46 inner, 85 long, 230 deg arc, strap anchors. Clamp and saddle on a CFRP 22/19 tube (200 mm). | 79 g + 30 g tube |
| U6 battery dock | Plate 3 mm, two T rails (stem 5.0, head 11.0 x 2.8), MT60-M pedestal, latch pocket. | 101 g |
| U7 battery pack shell | 168 x 73 x 31.5 mm. Rail channels with undercut, BMS bay 41.4 x 5.9, 7 x 18650 transverse at 19.6 mm pitch, front connector bay. | 130 g |
| U8 twin cavity | Cord anchor in tube A; full-length septum strip 1.4 mm plus 6 twin-bore spacers in tube B. | 47 g |
| U9 cam-lock collar | On the tube A front end. | 18 g |
| Tubes (purchased CFRP) | A OD33/ID30 x 450, B OD28.5/ID26 x 450 (the analysed set of shaft_calc_v20.py), 80 mm minimum overlap. | 103 + 75 g |

## Decisions and why (choices stated per rule 10)
1. **Stem frame and S layout.**
   - Shaft line on top, armrest line 157 mm below, grip raked 16 deg (top forward), as on the D044-A.
   - Hand space between the housings is 118 mm (95th-percentile hand breadth about 97 mm plus a glove).
   - The cup centre sits 236 / 258 / 280 mm behind the grip centre in the 3 positions.
2. **Trigger without a slot.**
   - The lever hangs on ears outside the sealed top housing.
   - The Hall switch on HB2 reads the lever's magnet through the 2.5 mm wall, so there is no opening to seal.
   - The magnet rides on a 22 mm tail ahead of the pivot. A pad stroke of 3 mm moves the magnet 2.5 mm away from the sensor (6.6 mm at rest).
   - The lever is therefore active-low: at rest TRIG is low, pressed TRIG is high.
   - Firmware rule: enter boost on TRIG high only after TRIG was seen low since power-up, so a broken conductor cannot latch boost.
3. **Battery dock under the bottom housing, horizontal entry.**
   - The pack slides forward along the shaft axis on two T rails. Measured on the meshes: 0.3 mm clearance and 2.7 mm undercut, and the swept pack section clears the dock along the whole path.
   - The MT60 pair mates along the slide axis at the front stop.
   - The pasted guide put the connector "facing upward". It faces rearward here, with a vertical mating face, because the dock is on the underside of the stem: upward would point into the housing.
   - A spring thumb latch rises 3 mm into a pocket in the dock plate (2.5 mm engaged, 4 mm travel).
   - The gasket and the potted pedestal follow the pasted guide.
4. **Interlock and power switch (PM2).**
   - The pack's MT60-F pin 3 is looped to pack GND.
   - Q1 (SO-8 P-MOSFET) is pulled on only through R2, the power switch on the top housing and the interlock pin. The netlist truth table confirms it conducts only with the pack seated AND the switch closed.
   - The MT60 pins are equal length, so the interlock cannot sequence the contacts. Instead the Miller soft start keeps the bus off while the contacts settle: a 19.9 ms ramp, with 2.1 A inrush into 1440 uF of bus capacitance (PM2, PB1R and CB1D).
   - Gate drive: 12.0 V at 29.4 V and 8.0 V at the BMS cut-off of 19.6 V; a 15 V zener clamps it.
5. **Fuse and wire sized to this load, not to the pasted motor-controller guide.**
   - The pasted guide specifies a 20 A fuse, 14 AWG wire and 6-8 mm copper traces; it was written for a motor controller.
   - This detector draws 0.31 A on average in boost, with pulse-recharge peaks of 3.8 A when PB1R's 940 uF bulk refills through the cord.
   - Choices: a 5 A slow-blow fuse, as in the v20 power model; AWG16 leads in the dock; AWG20 down the shaft.
   - The cord drop is 36 mV at the boost average.
   - A 7S 10-15 A BMS is enough and smaller than the 30 A BMS in the pasted BOM; the pack bay accepts 60 x 41 x 5.4 mm.
6. **Twin cavity instead of solid inserts.**
   - Solid twin-bore inserts weighed 181 g.
   - The design uses a full-length 1.4 mm septum strip, which carries a slit copper-mesh shield drained only at PM2, plus 8 mm twin-bore spacers every 75 mm: 39 g.
   - Each half-bore holds a 12.3 mm circle; the coiled cords are at most 10.4 mm.
   - Power and signal each run in their own shielded coiled cord. Telescoping is taken up by the coil (stroke 356 mm).
   - There is no closed metal loop around the axis (eddy rule).
7. **Tubes.**
   - The CFRP pair already analysed for stiffness and sway in shaft_calc_v20.py is kept.
   - The lower 0.40 m stays GFRP (non-conductive near the coil), and the neck module PB1R stays at the shaft base.
8. **Metal at the handle.** The steel latch, the MT60 brass and optional aluminium rails sit more than 1 m from the coil. The field there is far below the 6 % found at the neck module (shaft_calc_v20.py).

## Balance, mass and length (modeled)
- **Mass:** the upper assembly weighs 1.43 kg including the 0.53 kg pack (printed parts by mesh volume; purchased parts are estimates, ASSUMPTIONS 27).
- **Comparison with the D044-A:** the XP S-telescopic stem alone is 370 g per the XP manual. The difference is the pack, the electronics, the cords and the twin cavity.
- **Static torque about the grip at 47 deg, at the same head reach as v20 (0.97 m):** 2.875 kg m, against 2.88 for v20. At 40 deg it is 3.14 kg m, at 55 deg 2.52 kg m.
- **Moving the pack back under the cup** would give 2.82 kg m: only 0.05 kg m better, and it is not where the owner placed it.
- **Lengths:** the upper assembly is 1171 mm extended and 815 mm collapsed. From the cup back to the head hinge it is 1655 mm extended and 1299 mm collapsed.
- **Runtime:** one pack holds 75.6 Wh, which gives 9.8 h in boost or 16.1 h in scan (the v20 90.7 Wh pack gave 11.8 h in boost). Two packs give 19.6 h in boost.

## Still unproven, and next
- **D044-A dimensions.** Only the stem weight (370 g) and the 3 armrest positions are published. Everything else is scaled from photos and ergonomics: measure a D044-A or the owner's arm, and print a trial grip.
- **Datasheets not opened in this container:** MT60 size and pinout; the P30B envelope and ratings (retailer copies give 30 A continuous and 47 g); the SO-8 P-FET pinout and Rds(on); BMS size; coiled-cord OD and stroke; Hall switch operate and release points with the chosen magnet.
- **CB1D still has the joystick inputs** (JTR.5/.6 have no conductor). Tie or depopulate RJX/RJY and CJX/CJY in the CB1D revision, together with the head work.
- **Lighter options not yet taken** (estimates):
  - housing walls 2.5 -> 2.0 mm, about -45 g;
  - pack shell walls 2.5 -> 2.0 mm, about -25 g;
  - a pocketed dock plate, about -30 g.
