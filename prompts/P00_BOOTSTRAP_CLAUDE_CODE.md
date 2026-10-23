# P00 Bootstrap (paste into Claude Code at the repo root)
Read CLAUDE.md, then docs/DESIGN_STATE.md, docs/CORRECTIONS.md, docs/ASSUMPTIONS.md and docs/OPEN_ITEMS.md. Do not change any file yet.
1. Run `make setup` then `make verify-quick` then `python3 tests/regress.py`. Report every PASS/FAIL/SKIP.
2. Open stl/MANIFEST.csv and confirm the hashes match the files.
3. List anything in the repo that contradicts docs/CORRECTIONS.md (old numbers in comments, old file names, stale figures).
4. Summarise in 15 lines: what exists, what is modeled, what is built (nothing), the three riskiest assumptions, and the first task you would do from docs/OPEN_ITEMS.md and why.
Then stop and wait.
