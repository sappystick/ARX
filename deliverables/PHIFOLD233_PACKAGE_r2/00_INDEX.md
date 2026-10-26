# PHI-FOLD 233 inspection package r2 (generated 2026-10-26 by scripts/make_package.py)

## What this is, and what it is not

Everything that exists for the transmit region and the head is collected here to look at: boards, schematics, STLs, and the layered cut-away blueprint. **It is not a set of files that are "ready to print" or "ready to send to a PCB house".** Nothing has been built or measured. The open items that stand between this package and a first article are listed under "Not ready" below; every one is stated in docs/UNVERIFIED.md and docs/OPEN_ITEMS.md as well.

Tool status of the design: sign-off 55 PASS / 0 FAIL / 0 SKIP / 8 UNVERIFIED; strict regression passes (docs/STATUS.md).

## 1. Start here

| File | What it shows |
|---|---|
| `blueprint/PHIFOLD233_FULL_SYSTEM_LAYERED_CUTAWAY_r2.pdf` (and `.png`) | the full-system structure and layered cut-away: whole detector at the 47 deg use pose, head half-section and plan sections, yoke and neck module with PB1R, upper assembly v1, layer map, board renders, level schematic. Cut faces are computed from the current generated meshes. The PDF is vector (zoom in). |
| `renders/boards/*_top.png`, `*_bottom.png` | KiCad's own 3-D render of every routed board (copper, mask, pads; the generated footprints have no component 3-D models, so parts are not drawn). |
| `STL_CLASSIFICATION.csv` | every STL with its class (PRINT / REFERENCE / SUPERSEDED), size and SHA-256. |

## 2. Boards

| Board | KiCad file (open in KiCad 9) | Gerbers + drill (existing in the repo) | Status |
|---|---|---|---|
| CB1D-B controller, D78, 6 layers | `kicad/PF233-CB1D_routed.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/CB1D_B3/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK |
| LB1 display, D78, 4 layers | `kicad/PF233-LB1_routed.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/LB1_v5/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK |
| PB1R TX stage, 70 x 70, 4 layers | `kicad/PF233-PB1R_routed.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/PB1R_v2/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK |
| PM2 battery dock, 28 x 70 | `kicad/PF233-PM2_routed.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/PM2/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK |
| HB2 grip board, 24 x 38 | `kicad/PF233-HB2_routed.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/HB2/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK |
| TXJ1 junction, 2 layers | `kicad/TXJ1.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/TXJ1_v2/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK (run by hand, not in the pipeline) |
| SB1R-QA receive coil board, D228 | `kicad/SB1R-QA.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/SB1R_QA_v2/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK (run by hand, not in the pipeline) |
| SB1R-QB receive coil board, D228 | `kicad/SB1R-QB.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/SB1R_QB_v2/` | in the verified flow: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK (run by hand, not in the pipeline) |
| HTA timing-coil board, D90 | `kicad/PF233-HTA.kicad_pcb` (+ `.kicad_dru`) | `data/gerber/HTA_v2/` | in the verified flow (v2: the first Gerbers were an open coil): KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK |
| AB1A / AB1B receive analog boards (D40, 6 layers) | legacy only: `data/legacy/PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A`, `05_PCB_receiver_AB1B` | in those folders | **NOT in the verified flow**: from an earlier router run, never put through KiCad DRC here; 1.27 mm header pads have a 0.175 mm ring (under the 0.18 mm floor): OPEN_ITEMS 2 and 33 |

The release package `releases/TX_r2` (PB1R, CB1D, TXJ1, PM2, HB2) adds per-board CHECKS.md and a hash manifest; the head boards (LB1, SB1R-QA/QB, HTA) are the sets named above.

## 3. Schematics

`schematics/*.kicad_sch` and `*.pdf` exist for CB1D, LB1, PB1R, PM2, HB2, AB1A, AB1B and the superseded PM1/HB1. **They are connectivity drawings generated from the netlists**: one box per part with a net label on every pin, placed on a large sheet. They are correct (nets rebuilt from each file match the netlist exactly) but they are **not readable engineering schematics** (no functional grouping, no real symbols), and they have not been through KiCad ERC. **There is no schematic at all for TXJ1, SB1R-QA, SB1R-QB or HTA** (single-purpose boards generated straight from geometry). A human-readable functional schematic set is work that still has to be done. The system-level electrical picture is `docs/figures/LEVELS_SCHEMATIC.png` and `TX_SYSTEM_SCHEMATIC.png` (panel 9 of the blueprint).

## 4. 3-D files (54 to print, 4 reference, 8 superseded)

All paths are in `STL_CLASSIFICATION.csv`. Folders: `stl/head` (12), `stl/pins` (15), `stl/yoke` (7), `stl/upper` (12), `stl/shaft_handle` (14; the ELB_E* and BAT_B* files are SUPERSEDED), and the six full-resolution petal formers, about 66 to 70 MB each, generated into `work/kit_v15/PRINT/` by `make formers-print` (listed with hashes; not stored in git).

The mesh checks are measured on the meshes by the repo's checks (closed shells, clearances, fits: check_v22 47/47, upper_check 57/57, yoke_check). **No part has been sliced or printed here**, so overhang/support strategy, tolerances and fit are unproven; CFRP/GFRP tubes, the MnZn tiles, the 18650-class cells and the litz are purchased parts and are not in the STL set.

## 5. Not ready (what stands between this package and a first article)

- **U-DS-TXDRIVE**: Infineon IPB65R095C7 (Rds(on) vs temperature, Qg, current rating) and Microchip TC4420 (pinout, drive current): both pages refused (202 / 403), DATASHEET_LOG
- **U-DS-OKI**: Murata OKI-78SR-12/1.5-W36 and -5/1.5-W36 (input range, pinout): murata.com answered 500
- **U-DS-PACK**: Molicel P30B cell data (molicel.com 404) and the Amass MT60 body envelope (drawing not read; ratings verified)
- **U-DS-BAV199**: Nexperia BAV199 (leakage, capacitance, surge): page answered 403
- **U-DS-HVTERM**: PB1R JL1 (5.08 mm coil terminal block on DRAIN1, about 466 V) and the RCL1 lid resistor bank (5 k 10 W): no part with a manufacturer sheet read; Phoenix MKDS 1,5/2-5,08 is rated 250 / 400 / 630 V by overvoltage category in distributor listings only
- **U-FAB-DRC**: Fabricator's own DRC/CAM review of every board
- **U-CAM-VIEW**: Gerbers opened in a CAM viewer (visual check of the KiCad-written and gerber_out.py files)
- **U-BENCH**: Every bench item in docs/design/BENCH_FIRST_ARTICLE_TX.md (written in Step 6, NOT RUN)
- No fabricator DRC/CAM review and no CAM-viewer pass of any Gerber set; KiCad's DRC is not a fabricator's.
- AB1A / AB1B are not in the verified flow (above).
- No component 3-D models in the KiCad boards; no readable functional schematics for any board (above).
- The older layered figures in `docs/figures` (HEAD_CUTAWAY, ELBOW_GRIP_BATTERY_CUTAWAY, SYSTEM_USE_POSE, SYSTEM_FOLDED, NPM_CUTAWAY, SHAFT_JOINT_CUTAWAY) were drawn by a legacy renderer from the superseded elbow/battery-drawer design and an earlier PB1R: use the r2 blueprint instead.

## 6. How this was made

`python3 scripts/make_package.py` (needs KiCad 9, `make setup`, `make formers-low`; `make formers-print` for the six print formers). The blueprint: `src/render/blueprint_r2.py`.
