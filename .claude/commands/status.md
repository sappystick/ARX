---
description: Summarise the repo state and run the quick regression
allowed-tools: Bash(make:*), Bash(python3:*), Read
---
Read CLAUDE.md and docs/DESIGN_STATE.md. If work/ does not exist run `make setup`. Run `make verify-quick` and `python3 tests/regress.py`. Report: which checks passed, any number that moved, the top three open items from docs/OPEN_ITEMS.md, and anything in the repo that contradicts docs/CORRECTIONS.md. Change no files.
