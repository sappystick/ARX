#!/usr/bin/env python3
"""Builds START_HERE.md: ONE self-contained file to attach to a new Claude Code thread. It concatenates the entry instructions, the pipeline quick-reference and the full
handoff (docs/HANDOFF_NEXT_THREAD.md) so nothing has to be typed or explained. Regenerate after every step: python3 scripts/make_start_file.py
The only thing the owner types in the new thread is the line in section A (or `Read START_HERE.md and follow it. MODE B.`)."""
import os, re, subprocess
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ho = open(os.path.join(R, "docs", "HANDOFF_NEXT_THREAD.md")).read()
head = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=R, capture_output=True, text=True).stdout.strip()
out = f"""# START HERE - Arx / PHI-FOLD 233 (attach this file to a new Claude Code thread; generated, do not edit by hand)

## A. What the owner types (one line; nothing else is needed)
`Read the attached START_HERE.md and follow it exactly. MODE: A.`   (or `MODE: B.` to run Steps 5, 4, 6 straight through; A pauses for "go" after each step)

## B. Instructions to Claude (follow in order, do not ask the owner to repeat anything in this file)
1. Get the work. It is on branch `claude/nice-turing-8i4gkt` of sappystick/arx and is NOT merged into the default branch:
   `git fetch origin claude/nice-turing-8i4gkt && git checkout claude/nice-turing-8i4gkt` (if this session designates a different branch, create it from origin/claude/nice-turing-8i4gkt, say so in your first message, never push the default branch). The repo copy of this material is docs/HANDOFF_NEXT_THREAD.md; if it is missing you are on the wrong branch. The progress log (section 11) names the latest step.
2. Run `scripts/bootstrap.sh | tail -1`, then verify the state with the commands in section 0 below (counts only). In a brand-new container the strict regress FAILs (missing results) and publish shows ~38 stale: that is expected. Run `make signoff` once in the background (one Monitor), then re-check; stop only if the counts still differ afterwards.
3. Everything below (standing rules, default decisions, contingencies) is pre-approved. Ask a question only if a decision cannot be undone and has no default.
4. MODE from the owner's line: A = after each numbered step stop and wait for "go". B = run Step 5, Step 4, Step 6 in that order, one table per step, stop only after Step 6 or on (a) a regression you cannot fix, (b) a conflict with a CLAUDE.md rule, (c) an irreversible decision with no default. No mode given = A.
5. Order: Step 3.95 (pipeline, already built: see section C) is done; next is Step 5 (datasheets, vendor sheets) -> Step 4 (PM2/HB2/HTA routing and audits) -> Step 6 (bench procedure, final sign-off, release r2, regroup summary). Resume where the progress log (section 11) says.
6. Do NOT start system simulation, firmware, audio, LED, improvement review or epoxy-chamber work (Steps 7-13): the owner pastes that program separately from prompts/HANDOFF_PROMPTS.md (prompt 2).
7. Reporting: per step one paragraph + one table (what changed, what passed with counts, what is unproven, strict regress count, sign-off counts). Quiet output. One final commit per step (source + data + docs + progress-log row), push only to the working branch, no PR, no force-push. Commit trailers: the Co-Authored-By line for the model this session actually runs on, plus the session trailer given by the harness.
8. Claims: everything is MODELED or tool-checked; nothing is built or measured. Never write proven, ready for fabrication, record, will detect.

## C. Fast pipeline (use it; it replaces re-running everything)
- `make signoff` = incremental + parallel (4 jobs): every step is traced; an unchanged step is skipped, independent steps overlap. `make pipeline-plan` shows what would run and why (nothing runs). `J=2 make signoff` changes the job count.
- `make signoff-cold` re-runs every step in parallel (use before `make release-tx`). `make signoff-serial` is the original one-at-a-time path (reference). `make pipeline-graph` re-learns which steps may overlap (needed only after a step is added or its files change).
- After editing one board or script, just run `make signoff`: only the affected steps and the checks that read their outputs re-run. Logs: work/.pipeline/logs/<step>.log, times: work/.pipeline/timing.json. A `GRAPH STALE` line means two steps that conflict overlapped: run `make pipeline-graph`, then `make signoff`.
- Never skip a check to save time. Cached results are valid only while every input file hash, the command and the tool versions are unchanged.
- Dev loop for one board: edit generator -> `make signoff` (partial) -> read the status table. Full strict gate before any release: `make signoff-cold`, `python3 tests/regress.py`, `make release-tx REV=<n>`.

---

# D. THE FULL HANDOFF (docs/HANDOFF_NEXT_THREAD.md, verbatim)

"""
open(os.path.join(R, "START_HERE.md"), "w").write(out + ho)
print("START_HERE.md written", len((out + ho).splitlines()), "lines")
