# Sign-off pipeline performance (Step 3.95)

Measured on the 4-core, 15 GB container used for this work. Every time below is a wall-clock measurement of the real run, not an estimate. Outputs of the faster paths were compared with the serial path (below).

| Run | Wall time | What ran |
|---|---|---|
| Old serial `make signoff` path, as traced (`make signoff-serial` equivalent, 42 steps, one at a time) | 1953 s (32.5 min) | everything |
| Same, after the two exact speed-ups (parallel `sbq_damp2`, `publish` fast path) | about 1250 s | everything, still one step at a time |
| `make signoff-cold`, 4 jobs, first graph (bug: every step listed `work/`, so all 42 waited on each other) | 1250 s | everything, no overlap |
| `make signoff-cold`, 4 jobs, corrected graph | 680.6 s (11.3 min), 2.9x faster than the traced serial run | everything, overlapped |
| `make signoff`, nothing changed | 1.1 s | nothing (42 of 42 skipped) |
| `make signoff` after editing one script (`pb1r_check.py`) | 22.9 s | that step only; downstream steps skipped because its output was byte-identical |
| `make signoff` after tampering with one output file | 22.2 s | the producing step re-ran and restored the file; the other 41 skipped |

Warm routing state is included in these figures: the router resumes saved state when the pads and router code are unchanged (about 1 s per board). A cold clone has no saved state, so its routing steps take longer; the 680 s figure is therefore for a warm `work/` with every step forced to run, not for a fresh clone.

## Where the time goes (serial seconds)
sbq-fast 532 (now about 135 alone, 306 when overlapped), head-audit 198, baseplate 164, publish 113 (now 7.5), hood 110, v5 91, drc-cb1d 76, drc-pb1r 63, sims-rx 63, sim-head1 45, upper 32, audit-system 26. The longest dependency chain is baseplate, check, sbq-fast, head-audit, publish, controls (about 500-670 s); more cores cannot shorten it, only faster steps on that chain can.

## Changes and what each is allowed to change
| Change | Effect on results |
|---|---|
| Traced steps + content-hash cache (`scripts/pipeline.py`, `scripts/tracehook`) | none: a step is skipped only if its command, the tool versions, every file it read and every file it wrote are unchanged |
| Overlap graph (`data/pipeline/graph.json`) | none: two steps overlap only if neither writes what the other reads or writes; a conflict not covered by the graph prints `GRAPH STALE` |
| `sbq_damp2.py` solves spread over the cores (`ARX_INNER_JOBS`) | none: output files are byte-identical to the serial run when BLAS thread counts are left alone. An earlier version forced 1 BLAS thread per job and changed the last printed digit of 46 values (relative change about 1e-7, within the solver tolerance rtol 1e-8); that override was removed |
| `publish_data.py` skips the shapely Gerber comparison when the text is identical | none: identical text has identical geometry; differing text still gets the geometry comparison |
| Dropped repeats (each board generated once instead of four times, `sim_head1`/`sim_head2`/`tx-vbus` once) | none: the generators are deterministic; the repeated runs rewrote identical files |

## Differences between runs (all expected)
Between serial and parallel cold runs only these files differ: `state_*.pkl` (router state), the KiCad-written PB1R Gerbers (KiCad's export is not byte-deterministic; `publish` compares geometry), and `controls_3_9.json`. No result file a check reads differs.

## Not done / limits
- The cache trusts what the tracer sees. A tool that reads a file in a child process the tracer cannot see (non-python programs other than `kicad-cli` arguments) could hide an input. `make signoff-cold` before every release removes that risk.
- 4 cores: more parallelism would not shorten the critical chain.
- Not measured: a fresh clone (no router state, no `work/`).
