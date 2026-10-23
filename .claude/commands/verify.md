---
description: Run the full verification for one subsystem (mech, pcb, sim, all)
argument-hint: [mech|pcb|sim|all]
allowed-tools: Bash(make:*), Bash(python3:*), Read
---
Verify "$ARGUMENTS" (default all). mech: `make v5 check hood yoke`; pcb: `make route-lb1 gerber-lb1` and inspect the stats; sim: `make sims`. Then run `python3 tests/regress.py`. Compare to docs/DESIGN_STATE.md and list every difference with the file that produced it. Use the mech-checker, pcb-checker or sim-reviewer subagents for an independent second look.
