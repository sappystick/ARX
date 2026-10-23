---
description: Package a versioned release with manifest and hashes
allowed-tools: Bash(make:*), Bash(python3:*), Bash(git:*), Read
---
Run `make verify-full` and `python3 tests/regress.py`. If everything passes, refresh stl/MANIFEST.csv hashes, update docs/DESIGN_STATE.md and docs/CORRECTIONS.md, and commit with a message that lists what changed, which checks moved and what is still unproven. Do not push.
