# AB1A / AB1B receive-board routing: state at the pause (2026-10-27)

Everything here is MODELED / tool-checked. Nothing is built. Source of truth: `src/pcb/afe_layout.py` (placement + router), `src/pcb/afe_export.py` (KiCad + Gerbers), `src/pcb/dru_gen.py` (rules).

## Where it stands

| board | routed | KiCad 9.0.9 DRC (rule set `dru_gen` AB1B / AB1A) | independent DRC | Gerbers / publish / sign-off row |
|---|---|---|---|---|
| **AB1B** (2 channels) | **complete: 0 open nets, 0 plane-via failures, 0 placement errors** (504 tracks, 50 vias) | **0 errors, 0 unconnected**, 20 dangling-track warnings (stubs; sign-off counts errors only) | not run yet (`src/pcb/indep_drc.py` needs a zone-net exemption: the GND / +5VA planes are zone fills) | not done |
| **AB1A** (3 channels) | **NOT complete: 3 open nets** in the best configurations (two different sets, below) | not run | not run | not done |

AB1B's result is reproduced by the committed defaults: `BOARD=B python3 afe_layout.py --route` (in `work/` after `make setup`), then `BOARD=B python3 afe_export.py`, then
`python3 ../src/pcb/kicad_drc.py kit_v3/PCB_AB1B/PF233-AB1B.kicad_pcb kit_v22/kicad_drc_AB1B.json AB1B`.
Defaults that make it work: via 0.508 / drill 0.254, clearance 0.16, track 0.15 (grid 0.1), `BOARD_CFG["B"]["pre"] = "FB_MONO"`, original ADC rotation 90.

## What was found (in the order it was found; each is a CORRECTIONS row)

1. **FB_MONO (AB1B)** failed only because the earlier VCM trace walled in the RG2.1 pad pocket (88 cells). Routing FB_MONO first removes it. Not a geometry problem.
2. **Hidden state:** the router read and rewrote `work/prio_<board>.json` (git-ignored). Fresh clones routed differently. Now read/written only with `AFE_PRIO=1`.
3. **Router bug:** the via keep-out omitted the track half-width, so tracks sat 0.135 mm from vias (KiCad: 0.1349 against the 0.16 floor). Fixed (`VR` includes `TRACK / 2`). **My first "AB1B: 0 open" depended on this bug and was not manufacturable.** With the fix, AB1B at the 0.60 mm via left 2-3 open.
4. **AB1 via rule:** with the corrected keep-out, AB1B routes completely only at the vendors' documented Standard via (TTM [T-HDI] 10 mil drill and 10 mil pad-over-drill ring; AdvancedPCB [A-TOL] ring >= 0.005"): drill 0.254, ring 0.127, via 0.508 (the sign-off floor for every other board stays 0.30 / 0.15). `dru_gen` has `via_drill` / `via_annular` overrides for AB1A and AB1B only. **WATCH:** three AdvancedPCB facilities list a 0.216 mm no-breakout ring (FAB_RULES_VERIFIED): settle with the chosen facility (U-FAB-DRC).
5. **AB1 was never checked against the sourced floor:** the key was missing from `dru_gen.BOARDS`, so KiCad used the 0.20 mm default embedded in the exported file. Now registered.

## AB1A: the two best configurations (3 open each), exact settings

Run in `work/`. All use via 0.508 (now the default) and the corrected keep-out.

- **A1** `AFE_UAROTS=90,270,90 AFE_NUDGE="D2:-0.5:0"` -> open: `CS UA2.6`, `CS UA3.6`, `VCM_DIV CDF.1`.
  Flipping only the middle ADC halves the pin-row crowding between UA1/UA2 (7 -> 4 open); nudging D2 0.5 mm left opens the VCM pocket at SW2.2 (4 -> 3).
- **A2** `AFE_STAGGER=1 AFE_PASSLEN=1.0 (or 1.4) AFE_FANFIRST=1 AFE_UAROTS=90,270,90 AFE_NUDGE="D2:-0.5:0"` -> open: `+3V3D UA2.9`, `+3V3D CDV2.1`, `VREF_RAW RD1.1`.
  Staggered via fan-out on the ADC rows routes both CS pins; the open set moves to +3V3D / VREF_RAW.
- Tried without success (see `data/results/afe_search/` and `scripts/afe_search/`): per-ADC rotations (8 combinations), row pitch 10-13, decoupling position and side, ADC on the front side, random net orders (50+), plane-first plus ordering of the shared digital nets (48 samples), single part nudges (+-0.2 / +-0.5 mm, 16 parts, 2 rounds), failed-net-first iteration (oscillates between two near-solutions).

## Cause of what remains (AB1A)

Each remaining pad is the end pin of an ADC digital pin row (or a 0402 pad) inside a pocket that the neighbouring pins' traces and the plane vias close. The router is a greedy single-pass A* with no rip-up, and the pockets are only 0.5-1.0 mm wide.

## Next options, cheapest first (not started)

1. **Combine A1 + A2**: A2's stagger with a placement that also gives +3V3D room (move CDV2 / CAV2 / UA2 by hand-picked amounts from the pocket maps; `/tmp`-style map script is in this session's history: print `core` / `blk` around the failing pad per layer).
2. **Rip-up and reroute** (negotiated congestion) in `afe_layout.py`: rebuild the grid from the pad stamps, rip the nets that bound a failed pad's pocket, route the failed net first, re-route the ripped ones. Needs the grid rebuilt from scratch per attempt.
3. **Accept AB1A as a placement change** (OPEN_ITEMS 38, option a: J2 to x = 17.5 mm with CB1D JA/JB and the housing) if 1-2 do not close it.
4. Whatever closes AB1A: set it in `BOARD_CFG["A"]` (or the placement), export, KiCad DRC (`AB1A`), independent DRC, then stack_check / wiring_audit / full regress; publish and add AB1A / AB1B to the sign-off table; regenerate the package.

## Do not

- Do not edit the exported `.kicad_pcb`, Gerbers or STLs by hand. Do not loosen `dru_gen` to make a result pass.
- Do not call AB1B fabrication-ready: KiCad's DRC is not the fabricator's (U-FAB-DRC), no CAM-viewer pass (U-CAM-VIEW), and the ADS8860 / SW1G66 / REF5041 pin maps are marked VERIFY in `afe_design.py` and not checked against datasheets.
