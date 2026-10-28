# START HERE - Arx / PHI-FOLD 233 (attach this file to a new Claude Code thread; generated, do not edit by hand)

## A. What the owner types (one line; nothing else is needed)
`Read the attached START_HERE.md and follow it exactly. MODE: A.`   (MODE does not matter any more: all steps are done)

## B. Instructions to Claude (follow in order, do not ask the owner to repeat anything in this file)
1. Get the work. It is on branch `claude/hopeful-bell-wms3xo` of sappystick/arx and is NOT merged into the default branch:
   `git fetch origin claude/hopeful-bell-wms3xo && git checkout claude/hopeful-bell-wms3xo` (if this session designates a different branch, create it from origin/claude/hopeful-bell-wms3xo, say so in your first message, never push the default branch). The repo copy of this material is docs/HANDOFF_NEXT_THREAD.md; if it is missing you are on the wrong branch. The progress log (section 11) names the latest step.
2. Run `scripts/bootstrap.sh | tail -1`, then verify the state with the commands in section 0 below (counts only). If anything differs, stop and report the difference.
3. Everything below (standing rules, default decisions, contingencies) is pre-approved. Ask a question only if a decision cannot be undone and has no default.
4. MODE from the owner's line: A = after each numbered step stop and wait for "go". B = nothing is left to run or on (a) a regression you cannot fix, (b) a conflict with a CLAUDE.md rule, (c) an irreversible decision with no default. No mode given = A.
5. Order: Steps 3.95, 5, 4 and 6 are done (release r2 cut). The transmit-region sign-off is complete as far as tools can take it; what remains is hardware (docs/design/BENCH_FIRST_ARTICLE_TX.md), the open evidence rows, and the owner's Steps 7-13 program. Resume where the progress log (section 11) says.
6. Do NOT start system simulation, firmware, audio, LED, improvement review or epoxy-chamber work (Steps 7-13): the owner pastes that program separately from prompts/HANDOFF_PROMPTS.md (prompt 2).
7. Reporting: per step one paragraph + one table (what changed, what passed with counts, what is unproven, strict regress count, sign-off counts). Quiet output. One final commit per step (source + data + docs + progress-log row), push only to the working branch, no PR, no force-push. Commit trailers: the Co-Authored-By and Claude-Session lines the current session's harness gives.
8. Claims: everything is MODELED or tool-checked; nothing is built or measured. Never write proven, ready for fabrication, record, will detect.

## C. Fast pipeline (use it; it replaces re-running everything)
- `make signoff` = incremental + parallel (4 jobs): every step is traced; an unchanged step is skipped, independent steps overlap. `make pipeline-plan` shows what would run and why (nothing runs). `J=2 make signoff` changes the job count.
- `make signoff-cold` re-runs every step in parallel (use before `make release-tx`). `make signoff-serial` is the original one-at-a-time path (reference). `make pipeline-graph` re-learns which steps may overlap (needed only after a step is added or its files change).
- After editing one board or script, just run `make signoff`: only the affected steps and the checks that read their outputs re-run. Logs: work/.pipeline/logs/<step>.log, times: work/.pipeline/timing.json. A `GRAPH STALE` line means two steps that conflict overlapped: run `make pipeline-graph`, then `make signoff`.
- Never skip a check to save time. Cached results are valid only while every input file hash, the command and the tool versions are unchanged.
- Dev loop for one board: edit generator -> `make signoff` (partial) -> read the status table. Full strict gate before any release: `make signoff-cold`, `python3 tests/regress.py`, `make release-tx REV=<n>`.

---

# D. THE FULL HANDOFF (docs/HANDOFF_NEXT_THREAD.md, verbatim)

# Handoff for the next thread (updated 2026-10-28: B1, B3-B9 closed, TX_r4 / RX_r3, package r5)

Everything in this repo is **MODELED or tool-checked; nothing is built or measured**. Never write "proven", "ready for fabrication" or "will detect". Old handoff (step log, default-decision table, contingency matrix): `docs/HANDOFF_ARCHIVE_step7.md` sections 9-11; open it only when a situation there applies.

## 1. Resume (2 commands, ~1 s, then stop and read the output)
```bash
cd /home/user/ARX && scripts/bootstrap.sh | tail -1     # "environment OK" (also the SessionStart hook)
make state                                              # git, sign-off counts, FAILs, open blockers (data/handoff/blockers.json)
```
Expect: branch `claude/hopeful-bell-wms3xo`, clean tree, sign-off 71 PASS / 0 FAIL / 4 UNVERIFIED. If it differs, report the difference before doing anything. `make state-deep` (30 s) adds stale steps and the publish check; strict `python3 tests/regress.py` is run once at the END of a change, not at the start.
Wrong branch / dirty tree / push rejected: archive section 10.

## 2. Standing rules (do not ask again)
- Branch `claude/hopeful-bell-wms3xo` only; never force-push; no PR unless asked; one commit per finished stage (source + data + docs). Trailers: the ones the session reminder gives (`Co-Authored-By: Claude ... <noreply@anthropic.com>`, `Claude-Session: ...`).
- CLAUDE.md rules apply: generators only (never hand-edit STL, Gerber, KiCad); every geometry claim is a regress check; wording "modeled / tool-checked"; eddy rule (hatched planes, no closed loops); HV >= 1.0 mm; no fabricated datasheet facts (UNVERIFIED + URL tried); a wrong earlier statement gets a CORRECTIONS row.
- **Never loosen a design rule, clearance, via size or tolerance to make a check pass.** Stop at the first failed gate.
- Efficiency (docs/PROCESS.md): cheap test first; save the failing input; fix once; one background job at a time with a log; no sleep loops; status <= 5 lines, final report <= 15 lines; images/packages last.
- Safety: no `rm -rf`/glob deletes (delete only inside work/); no `pkill -f` (killed the shell: use `pgrep -x`/PID); `git commit` hook dirty-tree: one-line WIP commit.
- Do not start without the owner: system simulation, firmware beyond a Python model, audio, LED tuning, epoxy chambers, any printed-geometry change (the approved one is task "solid_union after release", section 4).

## 3. State (2026-10-28)
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

