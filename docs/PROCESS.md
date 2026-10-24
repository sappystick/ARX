# Engineering loop and claims policy
## The loop (every change)
1. State the requirement and the failure it fixes (one sentence, measurable).
2. Change the PARAMETRIC GENERATOR, never an STL by hand.
3. Verify geometry: closed mesh, interface clearances measured from the meshes, fit of real parts (boards, tiles, tubes), print constraints.
4. Verify electronics: ERC/placement/routing/DRC, connector pin-by-pin against neighbouring boards, ratings versus simulated stress.
5. Simulate with stated assumptions; run a sensitivity or convergence check; compare to an analytic limit when one exists.
6. Red-team: ask what would make the result wrong; look for the opposite sign, units, and a frame mix-up.
7. Update docs/DESIGN_STATE.md, CORRECTIONS.md if something earlier was wrong, ASSUMPTIONS.md, OPEN_ITEMS.md, and the regression numbers in tests/regress.py.
8. Package: new versioned files, manifest with hashes, superseded notes.
## Claims policy
- "Modeled" means a simulation with listed assumptions; "built" means printed/wound; "measured" means a bench measurement. Never use a stronger word than the evidence.
- A performance claim needs: the model, the assumptions, the sensitivity, and what measurement would confirm it. "Record" claims are not allowed without comparative measurements.
- If a simulation contradicts an earlier statement, add a row to CORRECTIONS.md and say so plainly in the report.
## Validation ladder
analytic check -> mesh/geometry check -> circuit/field simulation -> independent re-derivation (another method) -> bench test -> field test. Most items here sit at rungs 1-3.
## Definition of done for a part or board
Generator committed; checks pass in tests/regress.py; assumptions listed; superseded files marked; STL/Gerber manifest updated; a figure exists that a reviewer can read in one minute.

## Sign-off flow (2026-10-24)
- `scripts/bootstrap.sh` (also the SessionStart hook) makes a fresh container identical: KiCad 9 PPA, pip requirements (gerbonara and shapely are required), make setup, self-test.
- `make signoff` runs every board flow and every check (30-40 min cold: one background job) and writes docs/STATUS.md and data/results/SIGNOFF_STATUS.json (generated, never hand-edited). `make publish` copies work/ outputs into data/ (version names in scripts/publish_data.py; Gerber layers compared by geometry). `make release-tx REV=rN` packages the transmit-region boards with a hash manifest and per-board check lists; it refuses on a FAIL, on stale data, or on an existing revision.
- Failure policy: a missing result is a FAIL unless the item is registered in docs/UNVERIFIED.md. Close an item by deleting its row in the commit that adds the evidence.
- Seed rule: data/seed holds INPUTS only. `make setup` (scripts/seed_copy.py) never takes a result from it and never overwrites a file already in work/; `make clean` refreshes the inputs. A result exists only if its make target ran. Idempotence is a tested property: `make signoff` from a committed state leaves `git status` clean.

