#!/usr/bin/env python3
"""Copy data/seed into work/ (called by `make setup`).
Two rules, both learned the hard way (Step 3.9):
 1. RESULT files are never taken from the seed. data/seed held stale copies of results (wiring_audit.json, system_budget.json, sim_head1.json, ...); every `make setup` overwrote fresh results with them,
    so published data silently went back to old numbers, and in a fresh container a seeded result made a missing flow look PASS. Results must be produced by their flow (make targets declare the dependency).
 2. An existing work/ file is never overwritten (a warm work/ keeps its outputs). `make clean` is the way to refresh the inputs from the seed.
usage: scripts/seed_copy.py"""
import os, shutil, sys
SEED, WORK = "data/seed", "work"
RESULTS = {   # seed files that are OUTPUTS of a flow: not copied. The producer is named so a reader knows which target regenerates it.
    "kit_v20/sim_head1.json": "sim_head1.py (make sim-head1 / verify-quick)", "kit_v20/sim_thermal.json": "sim_head2.py (make sim-head2 / sims)",
    "kit_v22/drc_CB1D.json": "drc.py (make drc-cb1d)", "kit_v22/drc_LB1.json": "drc.py (make drc-lb1)",
    "kit_v22/sbq_damping2.json": "sbq_damp2.py (make sbq-fast)", "kit_v22/sbq_sim.json": "sbq_sim.py (make sbq-fast)", "kit_v22/sbq_geometry.json": "sbq_gen2.py (make sbq-geom)",
    "kit_v22/system_budget.json": "system_budget.py (make audit-system)", "kit_v22/tx_system.json": "tx_system.py (make tx)", "kit_v22/wiring_audit.json": "wiring_audit.py (make audit-system)",
}
copied = skipped_res = kept = 0
for root, _, files in os.walk(SEED):
    for f in files:
        src = os.path.join(root, f); rel = os.path.relpath(src, SEED).replace(os.sep, "/")
        if rel in RESULTS: skipped_res += 1; continue
        dst = os.path.join(WORK, rel)
        if os.path.exists(dst): kept += 1; continue
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst); copied += 1
print(f"seed_copy: {copied} copied, {kept} already in work/ (kept), {skipped_res} result files not taken from the seed")
