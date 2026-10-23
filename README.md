# Arx: PHI-FOLD 233 detector head (design repo)
Everything from the engineering sessions in one place: parametric CAD generators, PCB tooling, simulations, verified results, documents, ready-made prompts and Claude Code / Cowork configuration.

## Quick start (Claude Code or a plain terminal)
```
pip install -r requirements.txt
make setup
make verify-quick        # about 3 minutes: v5 cylinder + base plate + parts + 47 checks + transmit-stage and field simulation
python3 tests/regress.py
```
`make verify-full` (incl. `make audit-system`: wiring audit, stress table, stack-up, voxel interference) adds the receiver simulations, hood, yoke and the display-board routing and Gerbers. Then paste prompts/P00_BOOTSTRAP_CLAUDE_CODE.md into Claude Code.

## What is where
- docs/: DESIGN_STATE (current design), CORRECTIONS (what was wrong), ASSUMPTIONS, OPEN_ITEMS, PROCESS, CONVENTIONS, HISTORY, figures, reference photos.
- prompts/: P00-P10 for Claude Code (the next engineering tasks), prompts/cowork/C00-C06 for Cowork.
- .claude/: slash commands (/status /verify /newpart /route /release), skills, subagents, settings. CLAUDE.md at the root is the project memory.
- src/: generators and simulations (current) + archive/. data/: seeds, legacy boards, results, Gerbers. stl/: curated final STLs with hashes (formers are generated: `make formers-print`).
- scripts/push_to_github.sh: publish to GitHub yourself (plain git; STLs are ordinary binary files, all under GitHub's 100 MB limit).

## Honest scope
Nothing here has been printed, wound, assembled or measured. Performance numbers are modeled from stated assumptions. SB1R-QA/QB, LB1 and CB1D now have KiCad files and Gerbers that pass the repo's own checks and independent DRC; none has been opened in KiCad or a CAM viewer. The rigid-flex spine, CAM/KiCad verification and the DSP are open; the upper assembly (S-stem, trigger, battery dock, twin-cavity shaft) is generated and checked on its meshes but not printed (docs/OPEN_ITEMS.md, docs/design/UPPER_ASSEMBLY_v1.md).
