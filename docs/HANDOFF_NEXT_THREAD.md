# Handoff for the next thread (updated 2026-10-28 late: output modes / audio / gyro close-out; AU1, CB1D-C2, PB1R-v5, PM2-B, HB2-B signed off; package r6 HELD)

Everything in this repo is **MODELED or tool-checked; nothing is built or measured**. Never write "proven", "ready for fabrication" or "will detect". Old handoff (step log, default-decision table, contingency matrix): `docs/HANDOFF_ARCHIVE_step7.md` sections 9-11; open it only when a situation there applies.

## 1. Resume (2 commands, ~1 s, then stop and read the output)
```bash
cd /home/user/ARX && scripts/bootstrap.sh | tail -1     # "environment OK" (also the SessionStart hook)
make state                                              # git, sign-off counts, FAILs, open blockers (data/handoff/blockers.json)
```
Expect: branch `claude/hopeful-bell-wms3xo`, clean tree, sign-off 76 PASS / 0 FAIL / 4 UNVERIFIED, strict regress 117 PASS / 0 FAIL (incl. the process-guard, potting-map, single-matrix and owner-product rows). If it differs, report the difference before doing anything. `make state-deep` (30 s) adds stale steps and the publish check; strict `python3 tests/regress.py` is run once at the END of a change, not at the start.
Wrong branch / dirty tree / push rejected: archive section 10.

## 2. Standing rules (do not ask again)
- Branch `claude/hopeful-bell-wms3xo` only; never force-push; no PR unless asked; one commit per finished stage (source + data + docs). Trailers: the ones the session reminder gives (`Co-Authored-By: Claude ... <noreply@anthropic.com>`, `Claude-Session: ...`).
- CLAUDE.md rules apply: generators only (never hand-edit STL, Gerber, KiCad); every geometry claim is a regress check; wording "modeled / tool-checked"; eddy rule (hatched planes, no closed loops); HV >= 1.0 mm; no fabricated datasheet facts (UNVERIFIED + URL tried); a wrong earlier statement gets a CORRECTIONS row.
- **Never loosen a design rule, clearance, via size or tolerance to make a check pass.** Stop at the first failed gate.
- Efficiency (docs/PROCESS.md): cheap test first; save the failing input; fix once; one background job at a time with a log; no sleep loops; status <= 5 lines, final report <= 15 lines; images/packages last.
- Safety: no `rm -rf`/glob deletes (delete only inside work/); no `pkill -f` (killed the shell: use `pgrep -x`/PID); `git commit` hook dirty-tree: one-line WIP commit.
- Do not start without the owner: system simulation, firmware beyond a Python model, audio, LED tuning, epoxy chambers, any printed-geometry change (the approved one is task "solid_union after release", section 4).

## 3. State (2026-10-28)
**Close-out of the output-modes / audio / gyro work (late 2026-10-28)**: sign-off 76 PASS / 0 FAIL / 4 UNVERIFIED; strict regress 115 / 0 (process guards included); release controls 12 / 12; publish 0 stale.
- AU1 audio board (new): 36 x 60 mm, 8 layers (5 signal), MSPM0G3507 + TPA2005D1 + TPA6132A2 + BMI270 yaw gyro (moved from CB1D); routed 38 / 38 on a 0.125 mm grid
  (4 deterministic rounds + local repair, route_repair.py); exact DRC 0 / 0; au1_check 20 / 20; fits over PM2 in the bottom housing (1.8 mm side, 5.1 mm above PM2, 5.0 mm end margin).
- CB1D-C2: AUD_LINK on JTR.5, gyro removed, all joints hardwired (solder holes), JCL AWG22 holes; 46 / 46, DRC 0 / 0. PB1R-v5: JL1 AWG12 solder holes (the 5.08 mm
  terminal was 250 V / AWG 26-14 against 460 V / AWG12). PM2-B fused AU1 tap, HB2-B link pass-through. Superseded Gerber sets marked.
- Tools: exact-geometry drc.py (no raster slack), router exact fine-pitch keep-out + 0.15 mm neck-down, per-board grid, local repair, routing checkpoints and 600 s round budget,
  board-to-harness interface check (65 ends, 0 FAIL), non-destructive router reset (*_stale). Firmware host tests 40 / 10 / 13 with the yaw in the AU1 link reply.
- Routing speed-ups (2026-10-28, defaults): incremental re-routing (only nets touching changed pads; bases kit_v20/route_<B>_base.json; one moved resistor
  7.9 s on AU1 / 11.4 s on CB1D instead of 10 / 6 min; unchanged boards 1 s per route step), parallel AU1 rounds with a 600 s budget (full route 197 s instead of
  about 650 s), local repair of open nets and failed plane stubs. `FULL=1` forces a full route. The pipeline controls step now writes a fresh board table first.
- Potting map (docs/design/POTTING_MAP.md, data/results/potting_map.json / .png, step potting-map): 7 fill zones (head 116.0, neck 114.9, upper 29.9 cm3, exact
  mesh volumes, lower bounds where parts are boxes), compound classes ASSUMED (ASSUMPTIONS 43); **no pour on the TX windings** (any fill pushes the quiet time past
  the first gate in the model: air margin 0.35 us, lightest syntactic -0.04 us); bench tests PT1-PT9 list the data that replaces the assumptions.
- Owner-supplied products (2026-10-28, DATASHEET_LOG, POTTING_MAP.md last section, product_fit in potting_matrix_eval.json): 3M iM30K = filler for the NPM main / U3 / U1 / L1 fills;
  MG 832TC epoxy (0.7 W/mK, er 3.7, Tg 50 C) = NPM hot-zone candidate and, with iM30K after a trial mix, the NPM main / U3 / U1 fill; never on the windings, L2 or L1;
  MG 841AR nickel paint = ferromagnetic (mu_r >= 100): never in the head; option on the neck-module wall, slit, after PT9.
- Owner decisions open: package r6 (HELD until the owner says the integration work is done), the potting compound products (PT1), the C path search (not built), TX steering / split (DEFERRED).

| Area | State |
|---|---|
| Sign-off (`docs/STATUS.md`, generated) | 71 PASS, 0 FAIL, 4 UNVERIFIED (U-DS-HVTERM, U-FAB-DRC, U-CAM-VIEW, U-BENCH); `make signoff-cold` 60/60 steps in 1196 s; strict regress 0 FAIL; `publish_data --check` 0 stale; pipeline graph 60 steps |
| Transmit region | `releases/TX_r4` (CB1D with RML 270 ohm bleed, PB1R M12 = OKI-78SR-12/1.0); TX_r3 SUPERSEDED. TX releases carry no CB1D BOM / pick-and-place (gap since TX_r1): package r5 has them |
| Receive (AB1A, AB1B) | land = Ultra Librarian CP-24-25_ADI (EP 0.6096 SQ); CRF nudge; router enforces hole-to-hole 0.41; `releases/RX_r3` (no blockers left; U-FAB-DRC / U-CAM-VIEW open); RX_r1, RX_r2 SUPERSEDED |
| Router | single-pass default; rip-up `src/pcb/afe_ripup.py` wins 12 / 23 vs 9 / 23 perturbed cases (data/results/studies/router_study_b9.json); chip orientations fail for both (B11) |
| Printed parts | 65 curated STLs (`stl/`), cold rebuild byte-identical (canonical face order in solid_union); print check 49/49; upper_check 64/64 (MT60 from the Amass drawing, septum half-lap); six print formers 66-72 MB, closed, 233 mm (data/results/formers_print_check.json, not in git); pins regenerate identical (15/15, pins_tray_v15.py is not a step) |
| Cache | `work/.pipeline/solid_union_cache`: whole-union + snap results, proven byte-identical (docs/PERFORMANCE.md); v5 cold 778 s -> warm 114 s |
| Deliverables | `deliverables/PHIFOLD233_PACKAGE_r5` (every PRINT / REFERENCE STL, formers in the container only, KiCad + Gerber zip + BOM + PnP + netlist + layer PDFs + STEP per board, regenerated index); r4 SUPERSEDED |

## 4. What is left (data/handoff/blockers.json is the live list; `make state` prints it)
Owner: **B2** fabricator DRC + CAM viewer, **B10** bench. Without the owner: **B7** U-DS-HVTERM (630 V-class JL1, RCL1 part), **B12** move J2 / JA / JB to the duct edges as FFC connectors (changes AB1A, AB1B, CB1D), **B11** placement that rotates the decoupling group with the chip. Approved for after the release (task list): solid_union profile, batch union, save-and-rebuild path so the per-body cache becomes byte-identical (changes printed geometry once: measure surface distance, re-run every geometry check).

## 5. Where things are
| Need | Go to |
|---|---|
| Receive board placement / router / config | `src/pcb/afe_layout.py` (`BOARD_CFG7`), `afe_design.py` (parts, `_ad7389()` footprint), `afe_export.py` (KiCad + Gerbers); state: `docs/design/AB1_ROUTING_STATE.md` (top note says what is superseded) |
| Rules | `src/pcb/dru_gen.py` (floor), `indep_drc.py`, `kicad_drc.py` |
| Cylinder / parts | `src/mech/hub_v22.py`, `parts_v22.py`, `check_v22.py`; mesh union `solid_union.py`; print classes `print_check.py` |
| Pipeline | `scripts/pipeline.py` (STEPS, 58 steps), `data/pipeline/graph.json`, logs `work/.pipeline/logs/` |
| Evidence | `docs/UNVERIFIED.md`, `docs/design/DATASHEET_LOG.md`, `docs/ASSUMPTIONS.md`, `docs/CORRECTIONS.md` |
| Release / package | `scripts/release_rx.py`, `release_tx.py`, `make_package.py`, `system_manifest.py`, `curate_stl.py` |

## 6. Surgical loop (full table in docs/PROCESS.md)
`make touch-check` (what is stale) -> smallest test (`make rx-board` for AB1, `make step S=<name>` for one step) -> `make signoff` (only stale steps) -> strict regress once -> `publish_data --check` -> commit. Whole-pipeline reruns (`make signoff-cold`, 11 min) only before a release. Measured this session: rx-board 61 s, incremental signoff after an AB1 change 140 s, no change ~1 s.

## 7. Traps already paid for (new ones first)
0. (2026-10-28) **Generators that are not pipeline steps** leave a fresh work/ with seed copies: mech_v20 (NPM, now `mech-npm`) and cap_v18 (cap, now `cap-v18`) were found this way; pins_tray_v15 is still not a step (output identical). **manifold3d's union returns a run-dependent triangle order**: solid_union now writes a canonical order. **A Manifold rebuilt from a cached Mesh64 does not union like the original** (per-body dilation cache OFF). **Concatenated reference STLs** (U8_SEPTUM_extended) double-count overlaps in signed volume and confuse ray-parity voxels: compare in single-solid windows. `pgrep -f NAME` matches its own wait loop; `/usr/bin/time` is not installed.
1. **Studies overwrite production files**: `AFE_*` sweeps and `scripts/afe_search/` rewrite `work/out_board/*_layout.json`; finish with `make rx-board` or the cache and published data disagree (`publish --check` shows AB1x_layout.json stale).
2. **Import tracing**: fixed in `scripts/tracehook` (pyc reads map to the source). If a dependent step still looks cached after editing a shared module, `make step S=<name>` once and report it.
3. **Sign-off controls chicken-and-egg**: after a control count changes run `python3 scripts/signoff_status.py --no-regress --ignore-controls` once.
4. **Non-manifold unions**: `solid_union.py` writes `solid_union_failed.npz` on failure; fix offline, do not re-run the 8-minute build. Margin 0.025 broke the 0.01 mm roof stack; keep 0.005. JSON-dump only floats/lists (a numpy array in a report cost a rerun).
5. **AB1 router**: single-pass A*; a lone open pad moves when anything changes. The +3V3D island (Option 1) is the committed fix; do not remove it. Island must stay >= 3 mm from OPA2211 pads. Via 0.508 / drill 0.254 (vendor standard); never go smaller.
6. **AD7389-4**: SDI tied low is safe (Table 17: WR=0, addr 0 is NOP) but no software reset: wait >= 11 ms after power-up. 2-wire default: SDOA = A then C, SDOB = B.
7. Stale `BOM_MASTER.csv` AB1 rows (ADS8860/REF5041) cannot be regenerated; `docs/delivery/PURCHASED_PARTS.csv` is the truth.
8. `render_vault.py` fails on a missing legacy input (pre-existing).
9. Earlier traps still valid: KiCad Gerbers are not byte-deterministic (compare with `gerber_geom.same_geometry`); KiCad DRU last matching rule wins; `_NC` nets are skipped by the router (use `_OPT`); `route_fix.py` before any export; `make setup` copies inputs only; pcbnew lives in `/usr/bin/python3`; background jobs die on container restart.

## 8. Paste-ready starter prompt
```
Resume Arx / PHI-FOLD 233. Run `make state` and read docs/HANDOFF_NEXT_THREAD.md (sections 1-4 only) and docs/PROCESS.md. Keep the standing rules in section 2. If `make state` differs from the expected line, stop and report. Then take the first non-owner item in section 4 (B4), state the choice, do it with the surgical loop (touch-check, smallest test, signoff, strict regress once, one commit), and report in <= 15 lines. Ask nothing unless the decision cannot be undone.
```

## 9. Progress log (append a row per finished stage)
| Date | Stage | Commit | Strict regress | Sign-off | Notes |
|---|---|---|---|---|---|
| 2026-10-25/26 | Steps 4-7: PM2/HB2/HTA routed, datasheets, releases TX_r2/r3, 3-D models, schematics | see archive sec. 11 | 67 | 55/0/0/8 | older rows: archive |
| 2026-10-27 | AD7389-4 integration, +3V3D island, RX_r1, print STLs, package r4, options model | 801b9f5 | 0 fail | 67/0/0/8 | AB1A and AB1B closed |
| 2026-10-27 | Process streamlining: tracer fix, `make state/step/rx-board/touch-check`, blockers.json, handoff rewrite | (this commit) | see state | 67/0/0/8 | PROCESS.md recipes |
| 2026-10-28 | B1 land (Ultra Librarian CP-24-25_ADI), RX_r2 | a024c8a | 0 fail | 67/0/0/8 | EP 0.6096 SQ; CRF nudge; hole-to-hole in router |
| 2026-10-28 | B4 RS per channel | effbdce | 0 fail | 67/0/0/8 | no value changed |
| 2026-10-28 | solid_union cache (byte-identical), canonical face order | e0722d4 | 0 fail | - | v5 778 -> 114 s warm |
| 2026-10-28 | B9 rip-up router + RS 33 / differential model | e0a052b | 0 fail | - | default unchanged; B11 opened |
| 2026-10-28 | B3, B5, B6, B7 (narrowed), B8; cap-v18, mech-npm steps | f2f0d5c | 0 fail | 71/0/0/4 | datasheets on disk; M12 and MT60 corrected |
| 2026-10-28 | signoff-cold, formers-print, TX_r4, RX_r3, package r5 | (this commit) | 0 fail | 71/0/0/4 | final delivery of this thread |

| 2026-10-28 | Clickable cut-away viewer (package r5 viewer.html, `make viewer`); shared mesh_section.py (empty/partial sections fixed, blueprint + receive cut-away regenerated, NPM fit re-run on full sections); superseded NPM v1 STLs removed from stl_print; PURCHASED_PARTS board rows from the current BOMs | (this commit) | 96 PASS / 0 fail | 71/0/0/4 | CORRECTIONS: 4 rows |
| 2026-10-28 | Viewer r2 (placement edit + live section/stack checks, system simulation from system_live.py with a JS twin, wiring runs), +5VA budget row, model-derived power (5.26 / 7.18 / 8.51 W), solid_union study (rebuild/batch rejected) | (this commit) | 99 PASS / 0 fail | 71/0/0/4 | CORRECTIONS 3 rows, OPEN_ITEMS 39 |
| 2026-10-28 | Plan P1-P3/P5 (fab margin audit, potting volumes, hood tolerance, firmware timeline + pf233_timing.h); clocked LEDs: LB1-v6 = 66 x SK9822-EC20 fed in the idle slot, dark during sweeps (0 dropped pulses, modeled), chain-rotated LEDs route 136/136; CB1D-C1 (JLB.3 LED_CLK), harness v4; KiCad pad-angle exporter bug found and fixed (PB1R-v4 supersedes v3: CB7-CB9 pads), pad_orient_check | (this commit) | 105 PASS / 0 fail | 71/0/0/4 | CORRECTIONS 6 rows, OPEN_ITEMS 40 |
| 2026-10-28 | Output modes / audio / gyro close-out: AU1 (8 layers, 38 / 38, gyro moved from CB1D, yaw in the link reply), CB1D-C2, PB1R-v5 (AWG12 solder holes), PM2-B, HB2-B; hardwired joints; interface check; exact DRC + router fine-pitch fixes + local repair; sign-off 76 / 0, regress 114 / 0; process guards in regress, PROCESS.md section |
| 2026-10-28 | Owner datasheets (iM30K, 832TC, 841AR x2) read and saved; product fit per zone in potting_matrix_eval (832TC off windings, 841AR out of the head: ferromagnetic); PT9; regress 117 / 0 |
| 2026-10-28 | Incremental re-routing + parallel rounds + plane-stub repair (defaults); potting map (7 zones, no winding pour, PT1-PT8); controls step writes a fresh table; sign-off 76 / 0, regress 115 / 0, controls 12 / 12 |
