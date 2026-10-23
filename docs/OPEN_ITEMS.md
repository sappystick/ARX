# Backlog in priority order (each item has an acceptance test)
0. **LED rail protection.** Add a firmware LED-current cap (0.35 A) and a hardware current limit (PTC or eFuse at CB1D JLB.1); recompute the rail budget.
1. **Coil damping resistor.** A 470-680 ohm resistor across each SB1R coil is required (docs/CORRECTIONS.md). No board carries it. Decide the site (SMD footprint on each SB1R board across P1/P2, or on AB1T-A J1) and add it to the generator; re-run sbq_damp.py with the real network including RS = 100 ohm and the BAV199 clamp. Accept: first clean gate and noise recomputed with the real network.
2. **CAM / KiCad verification.** Open the SB1R-QA/QB, LB1 v3, CB1D v2, HTA Gerbers in a viewer, import the .kicad_pcb files into KiCad, run its DRC and compare with drc.py; fill the hatched zones. Check AB1A/AB1B Gerbers for the same pad-gap issue (they came from an earlier router run). Accept: KiCad DRC 0 errors on every board.
3. **Rigid-flex spine** (stackup, Z-fold bend radius >= 10x thickness, shield hatch, connector footprints, stubs on AB1T/CB1D/LB1). Accept: drawing + Gerbers + bend calculation.
4. **Handle, knuckle and battery pod from the reference photos** (docs/reference/photos). Accept: STLs with checks, balance table, updated harness.
5. **DSP in Python first**: air-template subtraction, adaptive filter on the HTA, matched-filter bank, bearing, ground balance. Accept: detection curves vs the simulated waveforms.
6. **Simulation validation:** convergence, Monte Carlo on tolerances (offset, layer gap, etch width, self-capacitance), ground model, finite turn-off, non-spherical targets. Accept: stated uncertainty on every depth number.
7. **TX stage:** C0G/film clamp part selection, RCL1 rating, hard-clamp alternatives, avalanche margin, EMI.
8. **Mass reduction** (torque 2.88 -> under 2.2 kg m).
9. **KiCad schematics** (.kicad_sch) for CB1D, LB1, AB1T, PB1R, PM1, HB1: only netlists and PNG schematics exist.
10. **Printing trials:** coupons, then cylinder (insert fit, rib supports), then formers.
11. **Prototype the receive boards** (QA/QB) and measure leak, L, R, self-resonance, then re-tune sbq_tune radii.
12. GitHub publication (scripts/push_to_github.sh).
13. **TXJ1 prototype and wire dressing**: build the junction with real litz and the real bridge cable bundle; hipot 1 kV; confirm the 4 mm lead bend in the window and the fit under the lid.
14. **Datasheet verification** of every rating in system_budget.py and ASSUMPTIONS 19 (prompt C05).
15. **Dual-PCB bench checks**: first articles of SB1R-QA/QB, LB1 (0.8 mm), CB1D, TXJ1: continuity against the netlists, then power-up with a current-limited supply.
18. **Hood v3 first article**: cut 26 tiles (27.0 x 26.2 and 28.3 x 39.7 x 2.5 mm MnZn), print the v3 carrier, bond; measure the axis field with and without the tiles and the receive ring-down with the hood fitted (ASSUMPTIONS 8, 23).
