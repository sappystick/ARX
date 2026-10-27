# Engineering loop (surgical, cached, one job at a time)

The sign-off pipeline traces every step, so unchanged work is skipped. The rule is: **never re-run what the cache can tell you is unchanged, and never run the whole thing to test one change.**

## Always (cost in brackets)
1. `make state` [1 s]: git, sign-off counts, open blockers. `make state-deep` [30 s] adds stale steps and the publish check.
2. Edit a generator (never a result).
3. `make touch-check` [15 s]: lists exactly what the edit made stale. Nothing runs.
4. Run the smallest thing that tests the edit (table below), then `make signoff` [seconds to ~3 min]: only stale steps and their readers re-run.
5. Strict `python3 tests/regress.py` once, at the end. `python3 scripts/publish_data.py --check` must say 0 stale.
6. One commit per finished stage (source + data + docs), push to the branch only.

## Which command for which change
| You changed | Run | Typical time |
|---|---|---|
| AB1A/AB1B placement or router (`afe_layout.py`, `afe_export.py`, `afe_design.py`) | `make rx-board`, then `make signoff` | 1 + 2.5 min |
| One other board generator (`pw_design`, `pw_export`, `cb1d_export`, ...) | `make signoff` (the graph picks its steps) | 25 s - 3 min |
| One check script | `make step S=<name>` then `make signoff` | 25 s |
| Cylinder / parts geometry (`hub_v22`, `parts_v22`) | `make signoff` (v5 and check re-run, the rest by what they read) | ~4 min |
| Before a release only | `make signoff-cold` | ~11 min warm |
| A new step or new files in a step | `make pipeline-graph`, then `make signoff` | serial, once |

## Rules that save time and tokens
- **Cheap test first.** Reproduce a failure on the smallest input (one board, one net, one level) before a long build. Save the failing input (the generators already write `*_failed.npz`/JSON) and fix offline instead of re-running the whole step.
- **Fix once, re-run once.** Read the whole failure, fix every cause you can see, then run. Do not iterate a 5-minute step to learn one fact at a time.
- **One background job at a time, with a log** (`work/.pipeline/logs/<step>.log`). No sleep/wait loops: the harness notifies on exit. Do not pipe a long run into `head`/`tail` that can break the pipe.
- **Studies never write production files.** Router and placement sweeps (`scripts/afe_search/`, `AFE_*` env hooks) overwrite `work/out_board/*_layout.json`; finish every study with `make rx-board` so the cache and the published data agree.
- **Do not re-derive facts that are written down:** read `docs/HANDOFF_NEXT_THREAD.md` sections 1-3, `docs/DESIGN_STATE.md` for geometry, `docs/design/*_STATE.md` for a board. Do not read the archive unless a trap sends you there.
- **Surgical commits:** when the stop hook fires on a dirty tree mid-stage, make a one-line WIP commit; the real commit is per finished stage.
- **Status updates <= 5 lines, final report <= 15 lines.** Images and packages last, after every gate passes.
- Safety: no `rm -rf` or glob deletes, no `pkill -f` (use `pgrep -x`/PID), never loosen a rule, clearance or tolerance to make a check pass; anything unconfirmed is UNVERIFIED.

## Tracer note
`scripts/tracehook` records imports served from `__pycache__` as reads of the source `.py` (fixed 2026-10-27: an edit to an imported module such as `solid_union.py` used to leave dependent steps cached; they needed `--cold --only`). Non-python programs other than `kicad-cli` arguments are still invisible: `make signoff-cold` before a release.

## Bootstrapping the controls row
A fresh table needs `python3 scripts/signoff_status.py --no-regress --ignore-controls` once (the controls read the previous table; the table reads the controls). Only after a new board or step changes the control count.
