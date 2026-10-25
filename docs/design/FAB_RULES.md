# Fabrication rules and finishes (Advanced Circuits or TTM; final choice later, design to the stricter)

Status 2026-10-25 (Step 5a): the floor is now read from the vendors' published pages: numbers, URLs and the per-facility table are in `FAB_RULES_VERIFIED.md` (U-FAB-RULES closed). These are the values `src/pcb/dru_gen.py` writes (every rule `(severity error)`) and `make kicad-drc` checks (KiCad 9, zones filled, negative control for the HV rule). A fabricator's own review of our files is still open (U-FAB-DRC).

| Rule | Value | Vendor basis (worst case) |
|---|---|---|
| Copper clearance | 0.16 mm | AdvancedPCB standard outer space 0.006" (Orange County); the router designs to 0.20 mm (premium below 0.007") |
| Track width | 0.15 mm | AdvancedPCB standard outer width 0.0055" |
| Via drill / ring | >= 0.30 mm / >= 0.15 mm | TTM standard drill 10 mil; ring 0.005" (both vendors); no-breakout ring 0.127-0.216 mm depends on the facility |
| Component PTH ring / hole | >= 0.18 mm / >= 0.46 mm | AdvancedPCB 0.007" ring; smallest standard component PTH 0.018" |
| Drill to copper | >= 0.26 mm | AdvancedPCB 0.010" |
| Drill to drill (edge) | >= 0.41 mm | TTM 16 mil same-net guideline |
| Copper to edge | 0.5 mm | AdvancedPCB inner 0.015" required, 0.020" preferred |
| High voltage (COIL_A/B, DM1/2, DRAIN1, CLAMP1, TX_A/B) | 1.0 mm on every layer, planes carved pad + 2.0 mm | CLAUDE.md rule 6 (no vendor rule published); verified in the Gerbers by `gerber_hv_check.py` |

| Board | Finish | Why |
|---|---|---|
| SB1R-QA, SB1R-QB, AB1A, AB1B, HTA, CB1D, LB1, TXJ1 | immersion silver (OSP is the alternative) | no nickel (magnetic) near the coil and receivers |
| PB1R, PM2, HB2 | HASL lead-free | power boards away from the head; bench comparison in OPEN_ITEMS 26 |

Via-in-pad (PB1R shunt, bulk and decoupling pads, `viafarm.py`): 0.3 mm vias inside SMD pads must be filled with non-conductive material and plated over; both vendors offer it (FAB_RULES_VERIFIED.md). The fabrication notes must call for it; the first article must show it (OPEN_ITEMS 28a).
TTM offers LF-HASL at "limited sites": if TTM is chosen, PB1R/PM2/HB2 need such a site or move to OSP.
