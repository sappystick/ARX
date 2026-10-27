# Handoff for the next thread (rewritten 2026-10-27, after the AD7389-4 receive integration)

Everything in this repo is **MODELED or tool-checked; nothing is built or measured**. Never write "proven", "ready for fabrication" or "will detect". Old handoff (step log, default-decision table, contingency matrix): `docs/HANDOFF_ARCHIVE_step7.md` sections 9-11; open it only when a situation there applies.

## 1. Resume (2 commands, ~1 s, then stop and read the output)
```bash
cd /home/user/ARX && scripts/bootstrap.sh | tail -1     # "environment OK" (also the SessionStart hook)
make state                                              # git, sign-off counts, FAILs, open blockers (data/handoff/blockers.json)
```
Expect: branch `claude/hopeful-bell-wms3xo`, clean tree, sign-off 67 PASS / 0 FAIL / 8 UNVERIFIED. If it differs, report the difference before doing anything. `make state-deep` (30 s) adds stale steps and the publish check; strict `python3 tests/regress.py` is run once at the END of a change, not at the start.
Wrong branch / dirty tree / push rejected: archive section 10.

## 2. Standing rules (do not ask again)
- Branch `claude/hopeful-bell-wms3xo` only; never force-push; no PR unless asked; one commit per finished stage (source + data + docs). Trailers: the ones the session reminder gives (`Co-Authored-By: Claude ... <noreply@anthropic.com>`, `Claude-Session: ...`).
- CLAUDE.md rules apply: generators only (never hand-edit STL, Gerber, KiCad); every geometry claim is a regress check; wording "modeled / tool-checked"; eddy rule (hatched planes, no closed loops); HV >= 1.0 mm; no fabricated datasheet facts (UNVERIFIED + URL tried); a wrong earlier statement gets a CORRECTIONS row.
- **Never loosen a design rule, clearance, via size or tolerance to make a check pass.** Stop at the first failed gate.
- Efficiency (docs/PROCESS.md): cheap test first; save the failing input; fix once; one background job at a time with a log; no sleep loops; status <= 5 lines, final report <= 15 lines; images/packages last.
- Safety: no `rm -rf`/glob deletes (delete only inside work/); no `pkill -f` (killed the shell: use `pgrep -x`/PID); `git commit` hook dirty-tree: one-line WIP commit.
- Do not start without the owner: system simulation, firmware beyond a Python model, audio, LED tuning, epoxy chambers, rip-up router, differential drive + 33 ohm (B9).

## 3. State (2026-10-27)
| Area | State |
|---|---|
| Sign-off (`docs/STATUS.md`, generated) | 67 PASS, 0 FAIL, 8 UNVERIFIED; strict regress 0 FAIL; `publish_data --check` 0 stale |
| Transmit region (CB1D, LB1, PB1R, PM2, HB2, TXJ1, HTA) | routed, KiCad 9 DRC 0 errors, independent DRC, Gerber read-back; `releases/TX_r3` |
| Receive (AB1A, AB1B, AD7389-4, `BOARD_CFG7`) | both routed (0 unrouted, twice), +3V3D hatched island on In4; KiCad 0 errors / 0 unconnected; `releases/RX_r1` **with BLOCKER 1** (exposed-pad placeholder) |
| SB1R-QA/QB | KiCad DRC + Gerbers only (no router step) |
| Cylinder v5 | 47 geometry checks; head cross-check 42 checks / 1 warning; 49/49 print STLs closed and fit (`solid_union.py`, margin 0.005 mm); septum split 235 + 211 mm |
| Wiring | point-to-point headers + harness (53 link pins, 50 conductors). There is NO central bus/rod: the 90 deg "spine channel" + comb are printed geometry for a rigid-flex that is not designed (B5) |
| Deliverables | `deliverables/PHIFOLD233_PACKAGE_r4`, `receive_cutaway`, `options_model` (docs/design/RECEIVE_OPTIONS_MODEL.md), `docs/delivery/` (ASSEMBLY_ORDER, PURCHASED_PARTS, SYSTEM_MANIFEST) |

## 4. What is left (data/handoff/blockers.json is the live list; `make state` prints it)
Owner input needed: **B1** ADI CP-24-25 land pattern (blocks ordering AB1A/AB1B), **B2** fabricator DRC + CAM viewer, **B10** bench. Can be done without the owner, in this order: **B4** RS 100 ohm vs 1 k (decide, CORRECTIONS row, re-export AB1: `make rx-board`) -> **B3** AMS1117 rating + `system_budget.py` +3V3D/+5V rows + SDI Table 17 into DATASHEET_LOG/ASSUMPTIONS -> **B7** retry the refused datasheets via WebSearch for the real PDF -> **B6** AD7389 readout model in Python -> **B5** link-path 3D check JA/JB to J2 and the spine decision -> **B8** BOMs/pick-and-place, potting. Close a blocker by editing the JSON in the same commit that closes it.

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
