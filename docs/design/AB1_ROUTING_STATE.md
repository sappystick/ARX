> B9 (2026-10-28): rip-up router `src/pcb/afe_ripup.py` (rounds of the single-pass router from an empty board: failed nets first after the plane connections, escape stubs that wall a failed pad dropped, history cost on the failed paths, plane-first order when a fanout fails). Study `scripts/afe_search/router_study.py` -> data/results/studies/router_study_b9.json, same gates as production (KiCad 0 errors / 0 unconnected, independent DRC 0, island): single-pass 9 / 23 valid cases, rip-up 12 / 23 (AB1A 6 / 10 vs 6 / 10, AB1B 3 / 13 vs 6 / 13; 5 invalid placements). Part nudges +-0.3 mm: single-pass 7 / 11, rip-up 10 / 11. Chip orientations: only the committed 270 / back routes, with either router (the decoupling capacitors and the +3V3D island do not rotate with the chip). The single-pass router stays the default: the acceptance (0 open on every perturbation including the 8 orientations) is not met by either; on the committed layout rip-up stops at round 0 with the identical result.
> CURRENT (B1, 2026-10-28): AD7389-4 land = Ultra Librarian CP-24-25_ADI nominal (terminals 0.254 x 0.762 at 1.9685 mm, EP 0.6096 SQ, one centre via). Three router/placement changes came with it, none loosens a rule: (1) the longer UA1.17 toe walled VREF_RAW in (a one-cell diagonal squeeze between CRF and the CS stub; net order and a 2M search budget did not help, the least-density land did not either): CRF moved 0.3 mm away from UA1 on both boards (BOARD_CFG7 nudges CRF:0:-0.3); (2) the router now enforces the dru_gen 0.41 mm hole-to-hole gap for every via, any net (two +3V3D vias had 0.346 mm, KiCad hole_to_hole error); (3) that took J2.3's island via site on AB1A, so plane_connect gained a last-resort 7 mm track search to an existing plane via (PLANE_WIN, only after the 4 mm track and the new-via fanout fail; a 7 mm window for every pad opened 3 nets per board). Result: AB1A 541 tracks / 51 vias, AB1B 422 / 39; both 0 unrouted, KiCad 0 errors / 0 unconnected, independent DRC 0 fails, island 3.025 mm from the OPA2211 pads, Gerber read-back pass.

> HISTORY: the first part of this file (AB1A "3 open") is SUPERSEDED by the "Update: AD7389-4 ... +3V3D island" section below and by docs/HANDOFF_NEXT_THREAD.md. Current state: AB1A and AB1B both routed, KiCad 0 errors / 0 unconnected.

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


## Update: AD7389-4 build with a +3V3D island on In4 (tool-checked, modeled; nothing built)

Cause that survived every search: the AD7389-4's VCC (pin 4) and VLOGIC (pin 2) are +3V3D at 0.5 mm pitch beside REGCAP (pin 3) and GND (pin 5); a surface trace could not leave that pocket, and each fix moved the failure to another pad (SCLK UA1.22, REGCAP CRG.1).
Fix: +3V3D is a hatched copper island on In4 (x 7.0 to 12.6 mm, y 2.0 to 3.6 mm in the board frame, chip at (9.5, 0)), joined by a 0.8 mm stub and a via at the tip of pins 2 and 4, like the ground pins; +5VA vias are kept out of the island, +3V3D vias inside it; J2.3 reaches the island by one routed trace and a via. All AB1 zones are now hatched (CORRECTIONS).

| Option | Open pads | KiCad DRC (9.0.9) | Independent DRC | Runtime / parts touched | Result |
|---|---|---|---|---|---|
| ADS8860 build (old) | AB1A 3 nets, AB1B 0 (before the AD7389 work) | AB1B 0 errors | - | - | superseded |
| AD7389, plain routing (stub, stagger, ground stubs, net order, capacitor nudges) | 1 per board, moves to another pad | - | - | 6 to 25 s | closed, not adopted |
| **Option 1: +3V3D island** | **AB1A 0, AB1B 0** (two identical runs each: AB1A 544 tracks 53 vias, AB1B 435 tracks 40 vias) | **0 errors, 0 unconnected** (AB1A 24 and AB1B 18 dangling-track warnings) | **0 fails** both | 8 s per board; afe_layout / afe_export / indep_drc / tests; no part changes | **adopted** |
| Option 2: rip-up and reroute | not started | - | - | - | not needed |
| Option 3: move J2 to x = 17.5 mm | not started | - | - | CB1D JA/JB, housing, harness | not needed |

Committed configuration (BOARD_CFG7 in afe_layout.py): chip (9.5, 0.0) rotation 270 back side; AB1A nudges SW2:0.4:0, CBD:-0.3:0 and capacitors CRG (+0.1, 4.0) rot 90, CVC (-1.8, 4.6), CVL (+2.0, 4.6); AB1B nudge RD2:0.4:0 and capacitors CRG (-0.3, 4.0) rot 90, CVC (-1.8, 5.0), CVL (+2.0, 5.0). The island is 5.6 x 1.6 mm (8.96 mm2), 3.025 mm from the OPA2211 pads, 20.3 mm (AB1A) or 3.085 mm (AB1B, MONO input pad) from the antenna inputs.
New risks: hatch connectivity of the island (KiCad filled zones report 0 unconnected, but the island is small: a fabricator CAM check is open); the island hatch gap stays 1.5 mm; exposed pad size of the LFCSP is a placeholder; SDI tied low; +3V3D rail budget (about 25 mA more) unchecked.
