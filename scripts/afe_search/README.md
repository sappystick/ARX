# AB1 router search tools (Step 12)

Run from `work/` after `make setup` (they call `afe_layout.py --route --diag` as a subprocess; the environment variables below are read by `src/pcb/afe_layout.py`).
They only explore: a result becomes real only when its settings are written into `BOARD_CFG` / the placement in `afe_layout.py` and the board is exported and checked.

| tool | what it does |
|---|---|
| `afe_grid.py BOARD 'JSON list of env dicts' [workers]` | evaluates many environment configurations in parallel, prints the best |
| `afe_sweep.py BOARD 'REF,REF,..' 'base nudges' UAROTS` | one greedy round of +-0.2 / +-0.5 mm part nudges |
| `afe_climb.py`, `afe_iter.py`, `afe_seeds2.py` | repeated greedy rounds, failed-net-first iteration, random net orders |

Overrides (environment only, unset = the committed behaviour): `AFE_UAROTS` (per-ADC rotation, row order), `AFE_NUDGE` ("REF:dx:dy,.."), `AFE_PRE` / `AFE_MID` / `AFE_POST` (nets routed
before everything / after the capacitor vias / after the plane vias), `AFE_FANFIRST=1` (all plane connections before any signal), `AFE_STAGGER=1` + `AFE_PASSLEN` (staggered via fan-out on the ADC rows),
`AFE_EXACTVIA=1` (true-distance via keep-out), `AFE_VIA` / `AFE_VDRILL` / `AFE_TRACK`, `AFE_SEED`, `AFE_PRIO=1` (old hidden priority file).
Do NOT use `pkill -f` with a pattern that appears in your own command line: it kills the shell. Use `pgrep -f "^python3 afe_"`.
