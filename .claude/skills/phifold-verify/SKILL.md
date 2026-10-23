---
name: phifold-verify
description: Run and interpret the PHI-FOLD verification suite (mesh checks, fit checks, simulations, routing stats). Use after any change to a generator, board, or simulation in this repo, or before reporting results.
---
# Verification procedure
1. `make setup` if work/ is missing; `make verify-quick`; `python3 tests/regress.py`.
2. For a changed part: open-edge count 0, every interface clearance measured from the meshes, fits against real components (boards, tiles, tubes, screws).
3. For a changed board: placement check JSON, ERC/net count, routing stats (nets routed vs required), HV clearance, planes hatched, notch at 90 deg. Independent DRC is not available here: say so.
4. For a changed simulation: reproduce the previous baseline first, then the change; vary one parameter at a time; state which assumption dominates.
5. Report: what passed, what moved (old -> new), what is still unproven. Add new expectations to tests/regress.py.
