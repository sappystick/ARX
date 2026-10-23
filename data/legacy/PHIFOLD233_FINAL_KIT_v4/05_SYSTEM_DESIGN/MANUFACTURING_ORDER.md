# Manufacturing order sheet (v3 + v4 kits)
| # | Item | Qty | Spec | Files | Status |
|---|---|---|---|---|---|
| 1 | Antenna board PF233-SB1 | 1 | 8-layer, Ø232 x 2.4 mm, buried vias (sequential lamination), 0.15/0.15 mm | v3 `03_PCB_antenna_board_PF233-SB1` | Gerbers ready; no manufacturer CAM review yet |
| 2 | Receiver board AB1A | 1 | 6-layer 1.6 mm, Ø40, ENIG, via 0.2/0.45, track/space 0.127/0.1 | v3 `04_PCB_receiver_AB1A` | Routed, 0 opens/shorts (own checker). 2 spots at 0.085 mm clearance to nudge |
| 3 | Receiver board AB1B | 1 | same | v3 `05_PCB_receiver_AB1B` | Routed, 0 opens/shorts |
| 4 | **PM1** power path | 1 | 4-layer 1.6 mm, 28 x 136, 2 oz outer / 1 oz inner, ENIG | `03_POWER_BOARD_PM1` | **Placement only. Do NOT order until routed** |
| 5 | **PB1** TX driver | 1 | 4-layer 1.6 mm, 28 x 224, 2 oz outer, ENIG, conformal coat + potting for the 500 V nets | `04_POWER_BOARD_PB1` (+ `.kicad_dru`) | **Placement only. Do NOT order until routed** |
| 6 | One-piece head body and companions | 1 set | PETG/ASA/unfilled PA12, no carbon fibre | v3 `01_PRINTABLE_head` | Print-ready |
| 7 | Shaft spine parts | see README section 5 | PETG/ASA | `01_SHAFT_printable` | Print-ready |
| 8 | 18650 cells | 14 | 3.5 Ah, 8 A continuous, matched | - | purchase |
| 9 | 7S 30 A BMS | 2 | OVP/UVP/OCP/SCP/balance, temperature | - | purchase |
| 10 | Litz wire 1.20 mm OD | 62 m + leads | about 0.5 mm2 Cu | - | purchase |
| 11 | 35 um self-adhesive copper foil | about 1.5 m2 | for septum/compartment shielding | - | purchase |
| 12 | Assembly BOMs | - | PM1/PB1 `_BOM.csv`, AB1A/B `_BOM.csv`, pick-and-place per board | in each board folder | MPNs flagged "verify" |
