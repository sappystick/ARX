# Handoff for the next Claude Code thread (written 2026-10-24, end of Step 3.9)

Read this first, then CLAUDE.md's read-first list. It tells you where the work stands, what is left, the order to do it in and why, and the traps already paid for. Everything in this repo is **MODELED or tool-checked; nothing is built or measured**. Never write "proven", "ready for fabrication" or "will detect".

## 0. Resume in five commands

```bash
cd /home/user/ARX            # branch claude/hopeful-bell-wms3xo, push only here, never force, never open a PR unless asked
git status --short | wc -l; git log -3 --format='%h %s'          # expect 0 and the Step 3.95 commit (or later)
scripts/bootstrap.sh | tail -1                                    # "environment OK" (also the SessionStart hook)
python3 tests/regress.py | tail -1                                # strict: expect FAILS 0 SKIPS 0, 63 PASS
python3 scripts/publish_data.py --check | head -1                 # expect 0 stale file(s)
```
If any of these differs from the numbers above, stop and report the difference before doing anything else. Then read docs/STATUS.md (generated sign-off table), docs/UNVERIFIED.md (open evidence), docs/OPEN_ITEMS.md.

## 1. Standing rules from the owner (do not ask again)

- **Pause after each numbered step**: report what changed, what passed (counts), what is unproven, the regress count and the sign-off counts; wait for the word "go". One paragraph plus one table per step; quiet output; counts and failures only.
- **Git**: WIP source-only checkpoint commits whenever the stop hook demands; ONE final commit per step with source + data + docs and the trailers below; push only to `claude/hopeful-bell-wms3xo`; never force-push; no PR unless asked. This overrides the generic release skill's "do not push".
  Trailers: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01T7iU5pGiBfkKRBbe2JcTJx` (use the trailer the current session reminder gives).
- **Files**: create/edit under src/, tests/, scripts/, docs/, data/, work/ through generators; delete/regenerate only inside work/; never `rm -rf` or glob deletes; never hand-edit STLs, Gerbers or KiCad files; new versions get new names and a `SUPERSEDED.txt` (with the reason) in the old folder.
- **Network/dependencies**: apt, pip and the KiCad 9 PPA are approved (install only into the container or an isolated `--target` folder, never remove system packages). Fetch manufacturer datasheets and fabricator pages; **cite the URL and the exact number for every rating; if a page is unreachable mark it UNVERIFIED, never fill from memory.**
- **Decisions**: design-changing decisions: choose, state the choice and the reason, proceed; ask only if it cannot be undone. Regressions you cause: fix without asking and report them.
- **Fabricators**: Advanced Circuits or TTM (final choice later; design to the stricter). Floor in `src/pcb/dru_gen.py`: track/space 0.15, finished drill >= 0.3, annular >= 0.15, edge checked at 0.5, HV 1.0 mm (all UNVERIFIED until Step 5 reads their sheets).
- **Finishes**: no ENIG near the coil/receivers (nickel is magnetic): immersion silver (or OSP) on CB1D, LB1, AB1A/B, SB1R-QA/QB, HTA, TXJ1; HASL lead-free on PB1R, PM2, HB2. Bench comparison is OPEN_ITEMS 26.
- **Approved design changes**: CB1D-B (MONO 460 V tap and joystick parts removed). JB.10 0R (RJB10) is FITTED. RJ5/RJ6 (JTR.5/.6 to ground) are DNP. Hatched planes only (eddy rule); a solid plane on PB1R was shown to return 8x a 1 g nugget and is rejected.
- **Do NOT start** the system simulation, firmware, audio, LED tuning, improvement review or epoxy-chamber work until the owner approves it and pastes the "Steps 7-13" prompt (section 6 is only a proposal for how to scope it).

## 2. State snapshot (Step 3.95)

| Item | State |
|---|---|
| Strict `tests/regress.py` | 63 PASS, 0 FAIL, 0 SKIP |
| `make signoff` (docs/STATUS.md) | 55 PASS, 0 FAIL, 0 SKIP, 8 UNVERIFIED (after Step 4). `make signoff` is now incremental and parallel (section 13): no-change run 1 s, one-script edit about 23 s, forced full run 11 min (was 32.5 min). Before Step 3.95: cold run in a fresh clone reproduced every committed data file. |
| Controls (`tests/release_signoff_controls.py`) | 12/12: release-tx refusals (existing revision, sign-off FAIL, stale data), evidence rule (file and datasheet-section), vanishing rows, idempotent output; the vanish/evidence controls run on fixture folders (Step 5), so closing production IDs does not silence them |
| Boards, KiCad 9.0.9 DRC with HV negative control | CB1D (61 parts, 44/44 nets), LB1, PB1R (15 nets + planes), TXJ1, SB1R-QA, SB1R-QB: 0 errors, 0 unconnected |
| Boards | all nine boards (CB1D, LB1, PB1R, PM2, HB2, TXJ1, SB1R-QA/QB, HTA) are in the KiCad 9 DRC flow with 0 errors / 0 unconnected; PM2/HB2/HTA were added in Step 4 |
| Release package | `releases/TX_r3` (hash manifest verified, per-board CHECKS.md; PB1R_v3, CB1D, TXJ1, PM2, HB2); `TX_r2` and `TX_r1` are SUPERSEDED (plane copper in the notch). `stl/MANIFEST.csv` 60 files, 0 changed |
| Open evidence (docs/UNVERIFIED.md, 8 rows) | U-DS-TXDRIVE, U-DS-OKI, U-DS-PACK, U-DS-BAV199, U-DS-HVTERM, U-FAB-DRC, U-CAM-VIEW, U-BENCH (Step 4 closed U-ROUTE-PM2, U-ROUTE-HB2, U-KICAD-HTA) |

Key MODELED numbers (assumptions in docs/ASSUMPTIONS.md, so you do not re-derive them):
- TX stage over 7S 19.6-29.4 V at 20 A: turn-off identical (zero 3.76 us, quiet 5.56 us, RCL1 3.81 W); Vds peak 456 / 462 / 466 V at 19.6 / 26 / 29.4 V (650 V FET, film clamp).
- Firmware on-time for 20 A (loop R 113 mohm + bulk sag): 59.5 us at 19.6 V, 43.8 us at 26 V, 38.5 us at 29.4 V; the lossless L I/V (55.1 / 36.7 us) under-delivers by 4-7 %; coil L +-5 % moves the current +-5 %. Table: data/results/TX_ONTIME_LUT.csv.
- Bulk bank droop at the BMS cut-off with -20 % capacitance: 0.85 V = 4.3 % of 19.6 V (budget 5 %): each 50 V capacitor needs >= 130 uF.
- PM2 chain at the cut-off: F1 peak 1.2-2.5 A, RMS 0.4-0.6 A; cord peak 4.4 A, RMS 0.66 A.
- PB1R: pulse-path copper 4.9 mohm, turn-off stray-L spike 7.5 V, Kelvin sense track 0.3 mm, comparator ground reference 15.5 mV (+-8 % over-current trip tolerance), HV pads >= 1.000 mm from plane copper (Gerbers read back), neck-module eddy: solid plane 8x a 1 g nugget (rejected), hatched border ring 4.7e-5.
- Receive (unchanged this session): first clean gate 5.1-7.5 us with RD 680 ohm; leak 0.01-10 mV.

## 3. Tooling built this session (use it, do not duplicate it)

| Tool | Purpose |
|---|---|
| `scripts/bootstrap.sh`, `.claude/hooks/session-start.sh` | identical environment in a fresh container (KiCad 9 PPA by hand, pip incl. gerbonara + shapely, make setup, self-test). Cold KiCad install is untested (U-COLD-BOOTSTRAP). |
| `make signoff` | every board flow + every check -> `docs/STATUS.md` and `data/results/SIGNOFF_STATUS.json` (generated, never hand-edited, deterministic). 30-60 min: ONE background job. |
| `make publish` (`scripts/publish_data.py`) | work/ -> data/ with version names in its VERSIONS table; Gerber layers compared by copper geometry; `--check` lists stale files |
| `make release-tx REV=rN` (`scripts/release_tx.py`) | versioned package + hash manifest; refuses on a FAIL, stale data or an existing revision |
| `src/pcb/kicad_drc.py` | KiCad 9 DRC: zones filled with the rules loaded, automatic 50 mm HV negative control (`rules_loaded` must be true) |
| `src/pcb/dru_gen.py` | per-board `.kicad_dru`, generic rule FIRST (KiCad: the last matching rule wins) |
| `src/pcb/kicad_gerber.py`, `rect_inject.py` | KiCad-written Gerbers/drill for rectangular boards (PB1R); routed copper into the placed KiCad file |
| `src/pcb/gerber_geom.py`, `gerber_plane_check.py`, `gerber_hv_check.py` | compare Gerber layers by geometry; read plane layers back and measure HV distances (with control) |
| `src/pcb/pb1r_check.py` | PB1R vs the TX stage: pulse path R/L, return vias, Kelvin, part ratings, connectors, neck-module eddy |
| `src/pcb/viafarm.py`, `route_fix.py` (nearest-pad stubs, duplicate vias, Kelvin ECO) | post-route steps |
| `scripts/seed_copy.py` | `make setup` copies INPUT seeds only; never results; never overwrites a warm work/ |

Make targets worth knowing: `pcb-cb1d route-cb1d kicad-cb1d drc-cb1d gerber-cb1d`, same pattern for lb1; `pcb-pb1r route-pb1r drc-pb1r kicad-pb1r gerber-pb1r check-pb1r`; `kicad-drc` (all six KiCad boards: CB1D, LB1, PB1R, TXJ1, SB1R-QA, SB1R-QB), `pcb-release`, `sbq-fast` (about 10 min), `verify-full` (about 12 min), `head-audit` (needs `formers-low`, done automatically), `sim-head1`, `sim-head2`, `tx`, `tx-vbus`, `pcb-hta`.

## 4. Traps already paid for (read before touching the flow)

1. **KiCad's Gerber export is not byte-deterministic** (aperture/flash order): never compare Gerbers by hash or text; use `gerber_geom.same_geometry`. A hash manifest identifies a release, it does not detect change.
2. **KiCad custom rules: the LAST matching rule wins.** The old shipped `.kicad_dru` files ended with an unconditional rule that disabled the HV rule. `kicad-cli` loads `<name>.kicad_dru` only if `<name>.kicad_pro` exists. Zones must be filled AFTER the rules are installed.
3. **Net names ending `_NC` are skipped by the router**: option nets use `_OPT`.
4. **Router state is keyed to a hash of pads + router.py + route_run.py**; route recipes loop past the 270 s budget (CB1D needs several passes). `route_fix.py` must run before any export; the `viafarm` and Kelvin ECO live there.
5. **`make setup` must not copy results from data/seed** (it did, and republished stale numbers four times). Results exist only if their target ran.
6. **Plane layers**: a through-hole pad has its own inner-layer flash: remove it before measuring the distance to the plane.
7. **Round pads need a circle test** in `route_fix`; a track end must connect to the NEAREST same-net pad.
8. **pcbnew module** lives in the system python (`/usr/bin/python3`, 3.12); the project python is 3.13. gerbonara needs `pip install --ignore-installed blinker` first (Debian owns blinker).
9. **Sandbox/permissions**: `rm -rf` and glob deletes are blocked; write background scripts with the file tool (not a heredoc containing `rm`); run long jobs with `run_in_background` and ONE Monitor (its 30-minute window expires: re-arm once, that is only the timer). Never sleep-poll. `infineon.com` answered HTTP 202 and a guessed `ti.com` PDF URL gave 404: find real datasheet links with WebSearch first.
10. **Stop hook** demands a commit+push whenever the tree is dirty: make a WIP source-only checkpoint, then the single final commit for the step.
11. **Controls used to hard-code production IDs**: RESOLVED in Step 5. `signoff_status.py` takes `--work` and `--evidence-root`; the controls build symlink fixtures (one result or evidence file removed, or a datasheet section marked UNVERIFIED). Datasheet evidence is per group: `docs/design/DATASHEET_LOG.md#U-DS-...` needs a `## U-DS-...: VERIFIED` heading. `rm -rf` stays blocked: build scratch work in new folders.

## 5. What is left, in the recommended order (and why)

**Recommended order: 5 (datasheets) -> 4 (routing) -> 6 (bench) -> sign-off + release r2.** The owner's numbering was 4, 5, 6. Datasheet work can change footprints and rules (50 V capacitor case/value, four-terminal shunt, ES3J->ES3K, PM2 MOSFET/fuse/TVS, HB2 Hall switch, the vendor rule floor), and routing PM2/HB2 first would force PB1R, PM2 and HB2 to be routed twice. Confirm the reorder with the owner in the first message of the new thread (it does not change the design; one line).

### 5.1 Step 5 - datasheets and fabricator sheets (do first)
Deliverables the sign-off enforces: `docs/design/DATASHEET_LOG.md` (evidence file for U-DS-PARTS) and `docs/design/FAB_RULES_VERIFIED.md` (U-FAB-RULES). Each rating: manufacturer URL + exact number + the page/table; unreachable -> stays UNVERIFIED.
Order inside the step:
- **5a Vendor sheets** (Advanced Circuits / 4pcb.com and TTM capability, via-in-pad / filled-via, finishes, minimum drill, annular ring, edge, track/space, HV spacing advice): compare with the dru_gen floor, tighten or relax it, then re-run `make kicad-drc` and the board DRCs. Cheap and independent.
- **5b Parts that change layout** (decide, state the choice, update the generators): a real 50 V bulk capacitor (>= 130 uF each at 19.6 V; the 150 uF 50 V 7343-43 is unverified; may need a new footprint or hybrid-Al can; PM2's CB1 470 uF 50 V hybrid can too); a four-terminal shunt option for RS1S (removes the plane-drop term); ES3J is 600 V against the 630 V rule: pick and verify a replacement (e.g. ES3K, same SMC package); JL1 terminal block and the RCL1 bank voltage ratings; PM2 SO-8 P-MOSFET pinout/ratings, fuse DC rating, TVS; the HB2 Hall switch (part not yet chosen).
- **5c Rating-only parts** (no layout impact): IPB65R095C7 (Rds(on) vs temperature feeds R_LOOP and the on-time table), TC4420, LM393, OKI-78SR-12 and -5, SMCJ33A (clamp voltage vs the 50 V capacitors), R2512 working voltage, MT60, Molicel P30B, BAV199, 74HC4051, **OPA2365 drive into RS2 + the idle MONO amplifier (OPEN_ITEMS 27) and OPA2211 input bias**.
- **5d Propagate**: ASSUMPTIONS 9/19/25-29/31/32, `system_budget.py`, `tx_vbus_sweep.py` inputs (then regenerate `TX_ONTIME_LUT.csv`), CORRECTIONS for every number that differs, FAB_RULES.md.
- **Gate**: re-run PB1R/CB1D flows if any footprint changed (`make signoff` cold router), regress strict. Close UNVERIFIED rows only for what was really verified: **split U-DS-PARTS into per-group IDs** (edit docs/UNVERIFIED.md and KNOWN_EVIDENCE in `scripts/signoff_status.py` together) so a partial close is possible.

### 5.2 Step 4 - PM2 and HB2 routing (+ HTA, + checks): DONE 2026-10-25 (see the progress log; the text below is kept as the record of what was asked)
- PM2 is 28 x 70 mm, HB2 24 x 38 mm (`SIZE` in `src/pcb/pw_export.py`; both placed, with zones from the placed-file template). `pw_export.py` writes `pads.json` only for PB1R: generalise to `PW in ("R","P","G")` with `rect=SIZE`.
- Add `route_run.py` configs (F/B signal layers, GND In1 and VBUS In2 hatched for PM2; GND only for HB2, widths 1.0-1.5 mm on BAT_P/BAT_F/VBUS/GND for PM2), Makefile targets `route-/drc-/kicad-/gerber-pm2|hb2` mirroring PB1R, entries in `kicad-drc`, `pcb-release`, `scripts/publish_data.py` (VERSIONS/KICAD/RESULTS), `scripts/release_tx.py` (BOARDS), `dru_gen.py` widths consistent with the router, regress guards, `signoff_status.py` already switches PM2/HB2 from UNVERIFIED to real checks when `route_<B>.json` exists; its cross-check column for them currently reads the wiring audit, so change it to PM2 -> `power_dock_check.json` and HB2 -> `trigger_check.json` in the same commit.
- Delete `U-ROUTE-PM2` / `U-ROUTE-HB2` from docs/UNVERIFIED.md in the SAME commit that adds the results.
- **HTA**: `src/pcb/hta_gerber.py` makes Gerbers only (D90, 4-layer, 2 x 1.915 turns r35.5-43, about 2.8 uH). To enter the KiCad flow write a small generator (`hta_kicad.py`: coil polylines as tracks, two through-hole lead pads, circular Edge.Cuts, add a key to `dru_gen.py`), run `kicad_drc.py`, then delete `U-KICAD-HTA`. If that proves unreasonable, keep the row.
- `make sch head-audit` has not been re-run since the PB1R re-placement (it runs inside `make signoff`); fix any regression it shows. Update the stale `head_crosscheck` warning text ("PB1R, PM1, HB1 ... not routed (legacy)").
- **NPM cable window (OPEN_ITEMS 28c)**: `src/mech/mech_v20.py` (NPM section, about lines 59-68) holds PB1R in a 78 x 20 x 78 pocket with a 12 mm cable window; JL1 moved from the right edge to the left edge. Measure the connector positions against the window and the ribbon tunnel and add a regress check; if it fails, either move the connectors in `pw_export.py` or the window in the NPM generator (state the choice).
- **JTR.5/.6 wording (OPEN_ITEMS 25)**: resolve to "CB1D RJ5/RJ6 DNP; HB2 JH.5/.6 are no-connect nets (JH5_NC/JH6_NC); the signal cord is 5-core; confirm on the first cord; fit RJ5/RJ6 only with a 7-core cable and then ground at one end only". Put it in DESIGN_STATE and in the bench doc.
- **Retarget the controls first** (trap 11): give `signoff_status.py` a work-folder override and make `tests/release_signoff_controls.py` use a fixture (a temp work folder missing a result, and a fixture register) instead of production IDs, otherwise closing U-ROUTE-PM2 / U-KICAD-HTA / U-DS-PARTS breaks the controls.

### 5.3 Step 6 - bench procedure and the closing sign-off
- `docs/design/BENCH_FIRST_ARTICLE_TX.md`: ordered procedure, instruments, pass criteria, data sheet per board (PB1R, CB1D, TXJ1, PM2, HB2): continuity vs netlist; current-limited power-up; **ton calibration against `TX_ONTIME_LUT.csv`** (the loop R and coil L are assumptions); Vds/flyback timing; damping; trigger chain; thermal; finish comparison (silver vs OSP; OPEN_ITEMS 26); over-current trip tolerance (+-8 % modeled); via-in-pad inspection (filled/plugged vias, OPEN_ITEMS 28a); TXJ1 hipot 1 kV (OPEN_ITEMS 13). **Every item marked NOT RUN**; `data/bench/` stays empty until real data exists (U-BENCH).
- Include the open hardware items: LED rail hardware current limit (OPEN_ITEMS 0), JTR.5/.6 handle-end check, TXJ1 cosmetic silk warnings (2 silk-over-copper, 1 back-side text), and the render scripts that still say "ENIG" in drawing text (`src/render/blueprint_rx_v15.py` line about 25, `src/render/draw_rx_schem.py` line about 48: fix the wording and regenerate their figures).
- Then ONE background `make signoff`, `make release-tx REV=r2`, and the regroup summary: verified by tool / modeled / needs hardware / open risks / UNVERIFIED list.

## 6. After Step 6: proposed scope for the owner's "Steps 7-13" (NOT approved, NOT started)

The owner's goals: maximum signal clarity at maximum capable depth for metal nuggets from 3 g to 50 oz (1.55 kg), with the firmware tuned to the receive side, audio signatures and the LED display; better components, smaller footprints, closed-up spaces; chambers for epoxy infill and shielding. A systematic order, by dependency:
1. **Target library and baseline model**: gold/nugget responses from 3 g to 50 oz (sphere + non-spherical, mass-dependent time constant), ground model (mineralisation, viscosity), noise budget with the datasheet values from Step 5; Monte Carlo on tolerances (OPEN_ITEMS 6) so every depth number carries an uncertainty. Reuse `sim_head1.py`, `sbq_*`, `tx_vbus_sweep.py`.
2. **Receive-chain decisions**: gain 40 vs 100 (needs the ADC noise from the datasheet), BLANK policy, damping retained (680 ohm), slotted electrostatic shield study, the free AB1B channel (OPEN_ITEMS 24).
3. **DSP and firmware in Python first (OPEN_ITEMS 5)**: HTA time-stamping, per-pulse-type air template, adaptive filter, matched-filter bank (tau = t1 x 1.618^n), ground balance, bearing from A/B, depth/size class, confidence; firmware rules (on-time LUT, boost duty limit, trigger boot rule, 400-pulse hold-trigger averaging, long/short pulse interleave); LED current cap 0.35 A + hardware limit (OPEN_ITEMS 0).
4. **Audio signature and LED map** driven by the class/confidence outputs (latency under about 50 ms).
5. **Joint tuning** of pulse widths, averaging, gates against a clarity metric across 3 g - 50 oz; sensitivity; what measurement would confirm each modeled gain.
6. **Improvement review**: hood v4 (one tile per spoke), 2.0 mm walls + 2.5 mm dock plate, U10 cord anchor, optional P42A pack, component and footprint upgrades.
7. **Epoxy-infill and shielding chambers**: designed in the generators with the eddy rule checked (hatched/mesh only, no solid planes, no closed loops, no metal heat sinks) and mesh checks in regress.
Propose this to the owner and wait for their prompt; their text replaces this list.

## 7. Open risks to keep visible

- Everything numeric is modeled (ground, finite turn-off and non-spherical targets are not yet in the depth numbers).
- The loop resistance / coil inductance behind the on-time table are assumptions: +-5 % coil L is +-5 % peak current.
- Via-in-pad on the PB1R power pads needs a filled/plugged-via option from the vendor, or the farm moves beside the pads.
- Cold bootstrap (KiCad install in a bare container) is not tested end to end.
- No CAM viewer review and no fabricator DRC exists for any board.
- CB1D, LB1, TXJ1, SB1R Gerbers come from the repo's own writer (`gerber_out.py`/`sbq_export.py`); only PB1R's are KiCad-written. Unifying them is optional and would change every published Gerber set (new version names).

## 8. Paste-ready starter prompt for the new thread

```
Resume the Arx / PHI-FOLD 233 transmit-region sign-off. Read docs/HANDOFF_NEXT_THREAD.md, then CLAUDE.md's read-first list. Verify the state with the five commands in section 0 (counts only); if anything differs, stop and report. Keep all CLAUDE.md rules and the standing rules in the handoff (pause after each numbered step, one final commit per step with source + data + docs, push only to claude/hopeful-bell-wms3xo, cite URL + exact number for every rating, never fill from memory, nothing is built or measured).
First message: confirm the recommended order 5 -> 4 -> 6 (datasheets and vendor sheets before routing PM2/HB2), in one line, then start Step 5a. Do not start the system simulation, firmware, audio, LED, improvement review or epoxy-chamber work until I paste the Steps 7-13 prompt.
```

## 9. Default decisions (already approved: apply them, state the choice in the step report, do not ask)

| Situation | Default |
|---|---|
| A datasheet or fabricator page is unreachable, blocked, or only a marketing page exists | Mark the item UNVERIFIED, keep its register row, record the URL tried and the failure in `docs/design/DATASHEET_LOG.md`, carry on. Never fill a rating from memory. Try WebSearch for the real PDF link before giving up; try the distributor copy only if it is the manufacturer's own PDF. |
| Two sources disagree | Use the manufacturer's PDF; record both numbers and the revision/date; take the more conservative one for margins. |
| The 150 uF / 50 V polymer-Ta in 7343-43 does not exist | Choose a verified 50 V part giving >= 130 uF each at 19.6 V (derated): polymer-aluminium hybrid can, or more/larger polymer-Ta, or a re-sized bank (total effective >= 625 uF at 19.6 V, droop <= 5 %). Re-place PB1R (`pw_export.py`), re-route, re-run the cross-check. Same for PM2's CB1 470 uF. |
| ES3J (600 V) vs the 630 V rule | Switch to a verified >= 630 V ultrafast diode in the same SMC footprint (ES3K or equivalent). If none is verified, keep ES3J and show the rule-6 deviation as an explicit WATCH row for the owner; do not hide it. |
| Four-terminal shunt | Adopt it only if a manufacturer datasheet gives the footprint and pad function; otherwise keep the two-pad R2512 with the Kelvin sense track and record why. |
| Vendor rule is stricter than the dru_gen floor | Tighten `dru_gen.py`, fix the designs (generators, not files), re-run every DRC. |
| Vendor rule is looser than the floor | Keep the floor (it is the design margin); record the vendor number. Never relax below the router's 0.2 mm clearance or the 1.0 mm HV rule without the owner. |
| Vendor offers no filled/plugged via-in-pad | Move the via farm beside the pads (new variant of `viafarm.py`), re-route, re-check. |
| HB2 Hall switch (part not chosen) | Choose a digital open-drain Hall switch for 3.3 V with a verified pinout and operate/release points that fit the 2.5 mm magnet travel; update `pw_design.py` and the trigger check. |
| The router cannot route a net | (1) nudge the placement anchors in `pw_export.py`; (2) allow the other signal layer; (3) report with the failing net and what was tried. Never edit a KiCad file by hand. |
| KiCad DRC reports an error | Fix the generator, regenerate, re-run; never edit the board file. A new warning class: record it, decide if cosmetic, list it in OPEN_ITEMS. |
| A sign-off check FAILs after your change | It is your regression: fix it without asking and say so in the step report. |
| A number moves | Report it in the step report with before/after; add a CORRECTIONS row if an earlier statement was wrong. |
| A design-changing decision with no default here | Choose, state the choice and the reason, proceed, and list it in the step report as a decision the owner may overrule. Ask only if it cannot be undone. |

## 10. Contingency matrix (what to do if the environment or session differs)

| If | Then |
|---|---|
| `docs/HANDOFF_NEXT_THREAD.md` is missing | You are on the wrong branch. `git fetch origin claude/hopeful-bell-wms3xo && git checkout claude/hopeful-bell-wms3xo`. This work is NOT merged into the default branch. |
| The session designates a different branch | Work on the designated branch, but start it from `origin/claude/hopeful-bell-wms3xo` (`git checkout -B <designated> origin/claude/hopeful-bell-wms3xo`), say so in the first message, never push to the default branch, never force-push. |
| `git status` is dirty at the start | Read `git diff --stat`. If it is yours from an interrupted step, finish or checkpoint it; if you cannot tell, stop and report. Never discard changes. |
| The branch is behind or diverged from origin | `git fetch`, fast-forward if possible; if it diverged, stop and report (never force-push, never rebase published commits). |
| A push is rejected | Retry up to 4 times with 2 s, 4 s, 8 s, 16 s waits only for network errors; otherwise fetch, look at why, and report. |
| `scripts/bootstrap.sh` fails or KiCad is missing | Re-run it and read the failing line; KiCad 9 comes from the PPA with the Launchpad key fetched by hand (steps are in the script). If the network is blocked, say which steps are blocked, run only what does not need KiCad (`--allow-skip` partial regress), and mark the rest UNVERIFIED. |
| No network at all | Datasheet and vendor items stay UNVERIFIED; do the offline work (routing, generators, bench document, handoff); report what was blocked. |
| `make signoff` exceeds the Monitor window | The 30-minute Monitor expiry is only the timer: re-arm once; the job continues. Never sleep-poll. |
| A background job died (container restarted) | Router states and results survive only in `work/` of the same container; in a fresh container re-run `make signoff` from scratch (60 min cold). |
| The strict regression shows a missing result | Run the matching make target (the flow produces results; the seed does not). Do not use `--allow-skip` for sign-off. |
| `publish_data.py --check` reports stale files | `make publish`, review `git diff --stat`, commit with the step; a Gerber that differs only in KiCad's ordering is not a change (geometry comparison handles it). |
| `release-tx` refuses | Read the message: existing revision -> new name (r2, r3); sign-off FAIL -> fix; stale data -> publish. Never edit the script to get past it. |
| The owner pastes evidence or a new decision | Use prompt 4 in `prompts/HANDOFF_PROMPTS.md`. |
| Context is getting large | At the end of the current step update section 11 and the state snapshot, commit, push, and tell the owner the thread can be restarted with prompt 1. |

## 11. Progress log (living: append a row in every step's final commit; refresh sections 0 and 2)

| Date | Step | Commit | Strict regress | Sign-off | Notes |
|---|---|---|---|---|---|
| 2026-10-24 | 1: external KiCad 9 DRC, CB1D-B, HV plane keep-out | a2b9cfb | 39 | n/a | MONO tap + joystick parts removed; KiCad 7 cannot load the files, KiCad 9 can |
| 2026-10-24 | 2: CB1D options, SB1R vias, TXJ1 pads, fab floor, finishes | 268a96f | 42 | n/a | SB1R vias had no annular ring (0.8 mm drill in 0.8 mm pad) |
| 2026-10-24 | 3: PB1R routed (rectangular), KiCad-written Gerbers, cross-check | a82e93e | 47 | n/a | cross-check forced a re-placement (JL1 left edge, Kelvin ECO, via farm) |
| 2026-10-24 | 3.5: bootstrap, hook, signoff, strict policy, release-tx | 50a51c3 | 47 | 37/0/0/17 | first release releases/TX_r1 |
| 2026-10-24 | 3.9: controls, evidence rule, seed clobbering fixed | fbfef49 | 48 | 38/0/0/17 | warm run idempotent; cold clone reproduced all committed data |
| 2026-10-24 | handoff written | e218427 | 48 | 38/0/0/17 | this file |
| 2026-10-24 | 3.95: incremental parallel sign-off pipeline | 63140fe | 50 | 38/0/0/17 | forced full run 680 s (was 1953 s), no-change 1 s; see docs/PERFORMANCE.md |
| 2026-10-25 | 5: datasheets + vendor sheets (branch claude/hopeful-bell-wms3xo, started from 63140fe on claude/nice-turing-8i4gkt) | (this step's final commit) | 55 | 44/0/0/19 | vendor floor tightened (0.16 clearance, 0.18 PTH ring, 0.26 drill-copper, 0.41 drill-drill, all severity error); PB1R bank 9 x 100 uF hybrid (re-placed, PB1R_v2), CB1D_B3, LB1_v5; SMCJ30A, Si4401FDY, SF-1206S500-2, DRV5023BI; cans are eddy targets (OPEN_ITEMS 34); controls on fixtures; cold bootstrap closed; Gerber planes were in the notch since r1 (fixed, read back) |
| 2026-10-25 | 4: PM2/HB2 routed, HTA in the KiCad flow, NPM window, JTR wording | (this step's final commit) | 62 | 55/0/0/8 | HTA Gerbers were an open coil (fixed, HTA_v2); pipeline graph re-learned (50 steps; graph now written when only reporting steps fail); controls/status cycle broken with `signoff_status.py --ignore-controls --no-regress` once |
| 2026-10-25 | 6: bench procedure, wording fixes, cold sign-off, release r2 | (this step's final commit) | 63 | 55/0/0/8 | cold run (50 steps, 729 s, no GRAPH STALE) reproduced every committed data file; releases/TX_r2 written; bench doc has 37 items, all NOT RUN (U-BENCH open) |
| 2026-10-26 | 7: PB1R/NPM fit fix, KiCad 3-D component models, functional schematics, release r3, package r3 | (this step's final commit) | 67 | 55/0/0/8 | PB1R vs NPM interference found and fixed (NPM v2, PB1R_v3); every footprint links a nominal VRML model (ASSUMPTIONS 34); 7 functional schematics netlist-checked with KiCad; SOIC body boxes were 90 deg off (CORRECTIONS) |

## 12. Prompts that go with this file

`prompts/HANDOFF_PROMPTS.md` holds five paste-ready prompts: (1) start/resume (two modes: pause after each step, or run 5 -> 4 -> 6 without pausing), (2) the Steps 7-13 program (paste only after the Step 6 regroup summary), (3) recovery when something is off, (4) ingest evidence or a new owner decision, (5) read-only status brief. They assume this file and nothing else.

## 13. Fast pipeline (Step 3.95): how to run the checks quickly and correctly

- `make signoff` is incremental and parallel (4 jobs, `J=2 make signoff` to change). Every step is traced, so an unchanged step is skipped and independent steps overlap. After editing one script or generator just run `make signoff`: only the affected steps and the checks that read their outputs re-run (about 23 s for a one-script edit). `make pipeline-plan` lists what would run and why.
- Before any `make release-tx`: `make signoff-cold` (forces every step), then the strict `tests/regress.py`. `make signoff-serial` is the original one-at-a-time path, kept as the reference.
- `GRAPH STALE` in the output means two conflicting steps overlapped: `make pipeline-graph` (serial run that re-learns `data/pipeline/graph.json`), then `make signoff`. Adding a step to `STEPS` in `scripts/pipeline.py` also needs `make pipeline-graph`; the regress guards fail until the graph covers every step and every script the serial path runs.
- Logs `work/.pipeline/logs/<step>.log`, times `work/.pipeline/timing.json`, cache `work/.pipeline/cache/` (wiped by `make clean`). Performance figures and limits: docs/PERFORMANCE.md.
- Do not force BLAS/OpenMP thread counts in steps: the stiff-ODE solves change their last digit with the thread count. Steps with an internal pool read `ARX_INNER_JOBS`.
