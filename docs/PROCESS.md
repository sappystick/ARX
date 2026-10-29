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

## Run guards (2026-10-28)
- No pipeline step may run longer than 15 min (`PIPELINE_STEP_TIMEOUT`, default 900 s; the longest real step is sbq-fast at about 9.5 min, then route-cb1d 7 min, head-audit 5 min). Past it the step's whole process group is killed and the step FAILs with rc 124 and `TIMEOUT` in its log.
- One run at a time: `work/.pipeline/run.json` holds pid, start and argv; a second run is refused (rc 3). `make pipeline-ps` shows the active run and its age.
- Background runs: `make signoff-bg`, then `scripts/wait_run.sh 1800 work/.pipeline/signoff_bg.log` (waits on the pid, ends with the run, gives up at the limit with rc 124).
- Never wait with `pgrep -f <pattern>` in a loop: the waiting shell's own command line contains the pattern, so the loop never ends. This is what kept three waiters alive for 15-30 min after their sign-offs had finished (2026-10-28); they used no CPU but looked like hour-long jobs. Never leave a `tail -F` watcher running after its run's SIGNOFF_RC line.
- Normal costs: incremental `make signoff` 1 s to about 11 min, depending on what changed; `make signoff-cold` about 11 min on 4 cores; `make pipeline-graph` (serial, cold, re-learns which steps may overlap) about 43 min, and only after a step is added or its files change; adding one step needs only `pipeline.py run --only STEP --update-graph`.

## Routing and checking tools (2026-10-28, defaults for every future run)
- **Exact DRC**: `src/pcb/drc.py` measures clearance on exact shapes (shapely), no raster, no slack. A gap below the rule by more than 1 um is a violation.
- **Fine-pitch boards** (pads with LIB `fine=True`): the router blocks cells by the exact distance to the pad shapes inside a 1.5 mm zone, takes only orthogonal steps there,
  marks thin tracks by their centre line and necks them to 0.15 mm (fab minimum, dru_gen GEN track); route_fix.py writes the same neck-down and rebuilds pad escapes
  along the pad axis. Boards with 0.5 mm-pitch rows route on a 0.125 mm grid (`route_run.py`, per board: AU1); every other board keeps 0.15 mm.
- **Router run guards**: each full-route round checkpoints the best layout to `kit_v20/route_<B>.json`; no round starts after 600 s (step cap 900 s). The config-change
  reset never deletes a layout: it moves it to `route_<B>_stale.json`.
- **Local repair, not full re-runs**: when a few nets stay open, `REPAIR=1 python3 route_run.py <B>` (in work/) freezes the saved layout, rips up only the signal nets
  with copper within 1.5 mm of the open nets' pads (shrinks the disc until <= 8 nets) and re-routes them in several orders (seconds, cap 240 s); it writes only when more
  nets route, keeps `route_<B>_prerepair.json`, and the exact DRC decides. AU1's route step runs 4 deterministic rounds and then this repair automatically.
- **Incremental re-routing (default)**: every finished layout is saved with a base (`kit_v20/route_<B>_base.json`: the pad file it was routed against and a
  fingerprint of what decides the copper: router.py, the board's router factory `mk()` in route_run.py, the grid). `route_run.py <B>` then: pads unchanged -> nothing to
  route (0.5 s); a few pads changed (<= 35 %) -> re-routes only the nets touching changed pads plus any frozen copper that now collides with them, re-stubs changed plane
  pads, checks the result with exact clearances and falls back to local repair, then to a full route (seconds instead of minutes: AU1 one resistor moved 7.9 s,
  CB1D 11.4 s, both still exact DRC 0 / 0). A changed fingerprint or outline means a full route. `FULL=1` forces a full route; `python3 route_run.py <B> --fingerprint`
  prints the fingerprint (use it, never recompute it elsewhere, when writing a base by hand).
- **Parallel full routes**: AU1's full route runs its rounds in 4 processes at once (route_repair.parallel_rounds, fixed orders, best kept) and then local repair
  (nets and failed plane stubs): 197 s instead of about 650 s. Learned settings (net order, stub-first pads such as UM.7) live in the board's factory.
- **Freerouting step (2026-10-29)**: `src/pcb/freeroute.py IN.kicad_pcb OUT.kicad_pcb [--rip NETS | --strip] [--hv NETS]`: writes the repo rules into the board's
  net classes (default 0.15 track / 0.16 clearance / 0.508-0.254 via; `--hv` nets get an HV class at >= 1.0 mm, rule 6, and lower is refused), exports Specctra DSN,
  runs Freerouting 2.4.1 headless (jar from Maven Central with a pinned SHA-256: `make freeroute-fetch`; Java 25+), imports the SES, refills zones and writes a report.
  It is a scripted generator step: the output is reproduced from the input board and the arguments, and it is checked exactly like the repo router's output
  (kicad_drc.py, indep_drc.py, KiCad Gerbers, gerber_edge_check.py). Use it to close the last nets after the repo router (`--rip` the stuck net: its old dead-end stub
  is what blocks it); a full `--strip` route of a dense fine-pitch board is not better (AB1A: worse). Ripping a plane net (GND) let Freerouting neck tracks below
  0.15 mm: never rip plane nets. Self-test: pipeline step `freeroute-selftest` (data/results/freeroute_selftest.json). First use: RF1 AB1A (1 open -> 0).
- **Board-to-harness interface**: pipeline step `interface-check` (src/pcb/interface_check.py): every harness wire end vs its pad / terminal (fit, gauge range,
  current density <= 10 A/mm2, pitch) and every screw terminal vs its net voltage. Terminals and connectors are read from each board's BOM type.
- **Hardwired joints**: plug-on headers / terminal blocks are not used inside the enclosed system: use the `WIRE*` part types (footprints `Connector:Wire_pads*`,
  no 3-D body), except the MT60 battery connector and the AB1 links. New wire-hole parts must keep the `Wire_pads` footprint family (the 3-D model check exempts it).
- **Counted checks**: a check that guards against passing on nothing counts what it SHOULD have checked from the design (example: gerber_hv_check writes `expected`
  = HV through-hole pads and vias x plane layers; the sign-off requires checked == expected), never a fixed number taken from an earlier route.
- **New board or new per-board file read by a check**: after adding a board, run `python3 scripts/pipeline.py run --jobs 1 --cold --only <steps that read it> --update-graph`
  so the graph learns the new inputs (pad-orient and models3d-check missed the AU1 files until traced; models3d.py builds models for the boards in its PW list: add the board there).

## Tracer note
`scripts/tracehook` records imports served from `__pycache__` as reads of the source `.py` (fixed 2026-10-27: an edit to an imported module such as `solid_union.py` used to leave dependent steps cached; they needed `--cold --only`). Non-python programs other than `kicad-cli` arguments are still invisible: `make signoff-cold` before a release.

## Bootstrapping the controls row
A fresh table needs `python3 scripts/signoff_status.py --no-regress --ignore-controls` once (the controls read the previous table; the table reads the controls). Only after a new board or step changes the control count.
