# RF1: rigid-flex redesign, side experiment (started 2026-10-29)

**Status: MODELED side experiment, phase 1 done.** Not part of the sign-off, the pipeline, the regress suite or any release. The baseline design is read and never written: every input the study reads is recorded with its sha256 in `results/rf1_phase1.json` together with the baseline commit. Any generator that a later phase changes is first copied into `experiments/RF1_rigidflex/src/` and changed there.

**Fixed (owner, 2026-10-29):** receive coils SB1R-QA/QB, the HTA antenna, the six TX formers and their litz, every printed part. **Free:** how the electronics are split into boards and how they connect: flex, rigid-flex or the circular rigid boards.

## Concepts

| | A: catalog FFC (B12 decision) | B: soldered flex jumpers | C: head rigid-flex (RF1 main line) |
|---|---|---|---|
| What | separate rigid boards, 0.5 mm FFC + connectors at the duct edges | separate rigid boards, custom 2-layer flex strips soldered / hot-bar bonded to pads (no connector) | AB1A + AB1B + CB1D + LB1 one rigid-flex panel (6L rigid sections, 2L flex core), HTA a flex tail, SB1R leads a soldered flex jumper |
| Hand joints in the head (today 66) | 18 (LB1, HTA and SB1R wires stay; the link becomes 4 reflowed connectors) | 12 bonded ends | 5 |
| Boards testable alone | yes | yes | no (panel test + test pads) |
| Fab | standard | standard + simple flex | rigid-flex vendor, every change re-spins the panel |

## Phase 1 results (`rf1_study.py`, MODELED / mesh-checked)

| Question | Result |
|---|---|
| AB1 <-> CB1D link fit on the meshes (link_path_check, imported unchanged) | baseline IDC ribbon 6 / 16 FAIL; catalog FFC 0 / 14; rigid-flex hinge (0.2 mm, no connector) 0 / 14 |
| Headroom (rigid-flex hinge) | 10.4 mm under LB1 (ribbon -4.4, FFC 8.4), 7.2 mm under the septum (ribbon -2.6, FFC 5.2) |
| CB1D -> LB1 hinge, CB1D -> HTA tail | rise 10.6 / 15.9 mm, S-fold needs 8.0 mm at a 2.0 mm fold radius (10 x 0.2 mm): both fit; flex about 15 / 21 mm |
| Receive-coil lead pair, 60 mm | loop area 10.2 mm2 (AWG36 touching) to 60 mm2 (loose 1 mm) today, 3.0 mm2 fixed on a broadside flex pair; capacitance about 5 pF either way |
| Eddy rule 5 | the board graph is a tree (no closed loop around the axis); hatched planes in the hinges; FR4 / polyimide stiffeners only (the vendor also offers stainless and aluminium: excluded) |
| Vendor (Rigiflex pages, `ds/`) | D228 fits the 18 x 24 in panel; 0.10 / 0.10 mm trace / space covers our finest; 6L 1.6 mm rigid-flex with 1 oz is a listed build; polyimide er 4, DF 0.04, water absorption 2.9 % |

What this does **not** show yet: any change in leak, noise or detection. The loop-area ratio is geometry only; the pickup needs the TX field along the lead path (phase 2).

## Where the real improvement is

1. **Build quality and repeatability (large, near certain):** 66 -> 5 hand joints in the head; the receive-lead loop area becomes a fixed 3 mm2 instead of 10-60 mm2 that depends on dressing, so the air leak becomes a calibratable constant instead of a per-unit variable. This is the gain RF1 can deliver for sure.
2. **Receive chain clean-sheet (large, MODELED next):** the AB1 sections are laid out from scratch in RF1, so the known receive defects go in at the same time: VREF / VCM buffer stability (OPEN_ITEMS 30), OPA2211 input range (31), chip-orientation robustness (B11), header pad rings (33). These are performance items; the flex is what lets the layout start over without the header constraint.
3. **Digital noise next to the receive coils (medium, to be modeled):** the ADC SPI (SCLK >= 27.2 MHz) runs between hatched ground layers in the hinge instead of an open ribbon.
4. **Not changed by RF1:** TX (litz, 20 A, 460 V taps stay wire, rules 5 / 6), the shaft cords (a 356 mm telescoping stroke needs dynamic flex: not proposed), the neck and handle boards.

## Phases

1. **Done:** census, mesh fit, fold radii, lead loop area, loop check, vendor fit (`results/rf1_phase1.json`, `results/rf1_head_concept.png`).
2. Receive-lead pickup: copy `sbq_sim.py` into `src/`, add the flex-tail path and the TX field along it; leak and its spread (wire dress Monte Carlo vs fixed flex). Hinge crosstalk SCLK -> RX input.
3. Clean-sheet AB1 section: copy `afe_design.py` / `afe_layout.py` into `src/`, apply items 30 / 31 (isolation resistor or reference driver; VCM / amplifier choice) and the rotating decoupling group (B11); route with the repo router.
4. Rigid-flex board definition: one outline with rigid and flex regions, stackup drawing (6L rigid, 2L flex core, coverlay, FR4 stiffeners), hinge routing with hatched GND, fold-line keep-outs (no vias or pads within 1 mm of a fold); DRC with drc.py per region; KiCad 9 has no per-region stackup, so the fab drawing carries it.
5. Compare A / B / C on the same table (fit, leak, noise, joints, test, cost from real quotes) and decide; only then does anything move into the main design (B12).

## Files

- `rf1_study.py` phase 1 study; `rf1_figure.py` the figure; `results/` outputs; `ds/` the Rigiflex pages (owner-supplied, 2026-10-29).
