# Fabrication rules and finishes (Advanced Circuits or TTM; final choice later, design to the stricter)

Status 2026-10-24: **UNVERIFIED**. The vendors' capability sheets have not been read yet (Step 5 cites URLs and exact numbers). These are the conservative values used by `src/pcb/dru_gen.py` and checked by `make kicad-drc` (KiCad 9, zones filled, negative control for the HV rule).

| Rule | Value | Note |
|---|---|---|
| Track / space | 0.15 mm | the router designs to 0.2 mm |
| Finished drill | >= 0.3 mm | SB1R vias 0.4 mm, CB1D/LB1 vias 0.3 mm |
| Annular ring | >= 0.15 mm | SB1R vias 0.2 mm |
| Copper to edge | checked at 0.5 mm | assumed fabricator minimum 0.3 mm |
| High voltage (COIL_A/B, DM1/2, DRAIN1, CLAMP1, TX_A/B) | 1.0 mm on every layer, planes carved pad + 2.0 mm | CLAUDE.md rule 6; verified in the Gerbers by `gerber_hv_check.py` |

| Board | Finish | Why |
|---|---|---|
| SB1R-QA, SB1R-QB, AB1A, AB1B, HTA, CB1D, LB1, TXJ1 | immersion silver (OSP is the alternative) | no nickel (magnetic) near the coil and receivers |
| PB1R, PM2, HB2 | HASL lead-free | power boards away from the head; bench comparison in OPEN_ITEMS 26 |
