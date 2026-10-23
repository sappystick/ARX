---
description: Create a new parametric part generator with checks and a figure
argument-hint: <part name and purpose>
---
Create a new generator in src/mech/ for: $ARGUMENTS. Steps: (1) state the requirement and the interface dimensions it must meet, taken from the existing meshes in work/kit_*; (2) write the generator by extending the helpers in hub_v22.py / parts_v22.py (ring, sector, extrude, emit); (3) write checks in a new check_*.py or extend check_v22.py: open edges = 0, every interface clearance, printability; (4) add the expected numbers to tests/regress.py; (5) render one figure; (6) update docs/DESIGN_STATE.md and OPEN_ITEMS.md. Report what is modeled versus unverified.
