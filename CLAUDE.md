# Arx / PHI-FOLD 233: pulse-induction detector head, theory-grade design repo

Parametric CAD (Python -> STL), PCB placement/routing/Gerber tooling, physics simulation and verification for a pulse-induction metal/gemstone detector head: six golden-angle petal coil formers in parallel (54 uH), integrated central cylinder (vault) v5, dual rotated quadrupole receiver RX-Q, ferrite hood, shaft/yoke. Owner works with this repo from Claude Code and Claude Cowork.

## Read first (in order)
1. docs/DESIGN_STATE.md  2. docs/CORRECTIONS.md  3. docs/ASSUMPTIONS.md  4. docs/OPEN_ITEMS.md  5. docs/PROCESS.md  6. docs/CONVENTIONS.md

## Layout
- src/{mech,pcb,sim,render,shaft}: current generators. src/archive: older versions, kept for provenance only.
- data/seed: small intermediates the generators read. data/legacy: earlier board kits (netlists, BOMs, KiCad files, Gerber zips). data/results: sim/check JSON + CSV outputs. data/gerber: Gerbers produced here.
- stl/: curated final STLs + MANIFEST.csv (hashes). Formers (70 MB each) are generated, not stored: `make formers-print`.
- work/ is created by `make setup` (flattened scripts + kit_vNN output folders); it is git-ignored. Scripts use relative kit_vNN paths and must run inside work/.
- prompts/: ready-made task prompts (P*, C*). .claude/: commands, skills, agents, settings.

## Commands
- Fresh container: `scripts/bootstrap.sh` (KiCad 9 PPA, pip requirements incl. gerbonara + shapely, make setup, self-test; also the SessionStart hook).
- `make setup` then `make verify-quick` (v5 cylinder, parts, 47 geometry checks, transmit-stage/field sim; about 2 min) then `python3 tests/regress.py --allow-skip` (partial run). Plain `python3 tests/regress.py` is strict: a missing result FAILs unless the item is registered UNVERIFIED in docs/UNVERIFIED.md.
- `make signoff` = every board flow + every check + the table (docs/STATUS.md and data/results/SIGNOFF_STATUS.json are generated; 30-40 min cold: run it as one background job); `make publish` copies work/ outputs into data/; `make release-tx REV=r1` packages the transmit-region boards with a hash manifest (refuses on a FAIL or stale data).
- `make verify-full` adds the quadrupole/receiver sims, hood, yoke and the display-board PCB flow (routing 52 s).
- Single steps: make v5 | check | hood | yoke | yoke-check (after v5, hood, yoke) | sims | pcb-lb1 | route-lb1 | gerber-lb1 | pcb-cb1d | route-cb1d | formers-low | formers-print.
- Python 3.12+, numpy, scipy, matplotlib, pillow (requirements.txt). Linux/macOS (or WSL) for the Makefile. Full pipeline checked on Python 3.13 with numpy 2.1 and 2.5 (scipy 1.14 and 1.18): same outputs. numpy 2.x rejects 2D vectors in np.cross, so write 2D cross products out.

## Rules of engagement (non-negotiable)
1. Change generators, never STLs by hand. New versions get new names; superseded files are marked.
2. Every geometry claim is measured from the meshes (closed shell, clearances, fits) and written into a check that is added to tests/regress.py.
3. Every performance number is MODELED and carries its assumptions (docs/ASSUMPTIONS.md). Never say "record", "proven" or "will detect" without bench data. Say modeled / built / measured precisely.
4. If you find an earlier statement was wrong, say so plainly and add a row to docs/CORRECTIONS.md. Do not defend an old number.
5. Eddy-current rule: no solid copper planes, foil rings or closed metal loops around the axis inside the vault or head; use hatched planes, mesh septa, slit liners; no metal heat sinks.
6. High-voltage rule: coil flyback nets (hundreds of volts) need >= 1.0 mm clearance on boards, 630 V parts, and no routing under the connector lanes.
7. Do not fabricate datasheet facts (pinouts, ratings, heights). Mark them unverified and put them in ASSUMPTIONS.md; verify with the manufacturer datasheet when browsing is available.
8. Run the regression suite before and after every change; report any number that moved.
9. Keep outputs small and reviewable: one figure per decision, one JSON of results, one paragraph of what changed and what is still unproven.
10. Ask one question only when a decision changes the design; otherwise choose, state the choice, and proceed.

## Conventions (details in docs/CONVENTIONS.md)
mm / deg; z up from the underside of the base plate; azimuth CCW from +x; heel (shaft side) at 178 deg; spine channel at 90 deg; board exporter frames are y-DOWN, pickplace files y-UP; CB1D mounted rotated 180 deg.

## Known traps
- Paths: absolute /mnt/... paths were rewritten to legacy/; keep new scripts relative.
- audit_v20.py and cups_v20.py describe the superseded vault cups; the v5 checks are check_v22.py.
- Router quantises to 0.15 mm: track ends stop short of pads. ALWAYS run route_fix.py (stubs) before any Gerber/KiCad export, then drc.py (independent geometric DRC). drc.py is not KiCad's DRC: do not call a board fabrication-ready until KiCad or a CAM viewer agrees.
- Transmit leads must run in the wall-top channel to the 178 deg window and TXJ1 (never inside the vault past the posts). LB1 is 0.8 mm with flat wire pads. Run `make audit-system` after any change to boards, harness, cylinder or bridge.
- Receive boards: sbq_gen2.py (geometry) -> sbq_tune.py A/B (link radii) -> sbq_export.py (KiCad + Gerber) -> sbq_sim.py / sbq_damp.py. Lobes MUST be exact full rings with identical relative angles; continuous spirals leak volts (see docs/CORRECTIONS.md).
- Simulations that load kit_v15/LOW/paths.pkl need `make formers-low` or the seed copy (already in work/ after setup).

## Current priorities
See docs/OPEN_ITEMS.md (2 CAM/KiCad verification, 3 rigid-flex spine, 4 and 19 upper assembly first article, 5 DSP in Python, 20 CB1D revision for the joystick removal).
