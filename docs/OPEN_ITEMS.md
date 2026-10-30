# Backlog in priority order (each item has an acceptance test)
0. **LED rail protection.** Add a firmware LED-current cap (0.35 A) and a hardware current limit (PTC or eFuse at CB1D JLB.1); recompute the rail budget.
1. **Coil damping resistor: done in the generator (2026-10-23).** RD1/RD2 680 ohm on the QA top, QB leads through QA transfer pads, sbq_damp2.py with the real input network. Remaining: the firmware BLANK rule (release at turn-off unless the air leak exceeds the amplifier headroom) goes into the DSP/firmware work (item 5); measure ring-down on the first boards (item 11).
2. **CAM / KiCad verification.** Open the SB1R-QA/QB, LB1 v3, CB1D v2, HTA Gerbers in a viewer, import the .kicad_pcb files into KiCad, run its DRC and compare with drc.py; fill the hatched zones. Check AB1A/AB1B Gerbers for the same pad-gap issue (they came from an earlier router run). Accept: KiCad DRC 0 errors on every board.
3. **Rigid-flex spine** (stackup, Z-fold bend radius >= 10x thickness, shield hatch, connector footprints, stubs on AB1T/CB1D/LB1). Accept: drawing + Gerbers + bend calculation.
4. **Upper assembly v1: generated (2026-10-23)** (docs/design/UPPER_ASSEMBLY_v1.md, `make upper`): D044-A-style S-stem, index-finger trigger, MT60 battery dock and P30B pack, twin-cavity telescoping shaft, PM2/HB2. Remaining: measure a D044-A (ASSUMPTIONS 24), lighter walls and dock plate (about -100 g), knuckle at the head end. Accept: first article (item 19) within the modeled mass and torque.
5. **DSP in Python first**: air-template subtraction, adaptive filter on the HTA, matched-filter bank, bearing, ground balance. Accept: detection curves vs the simulated waveforms.
6. **Simulation validation:** convergence, Monte Carlo on tolerances (offset, layer gap, etch width, self-capacitance), ground model, finite turn-off, non-spherical targets. Accept: stated uncertainty on every depth number.
7. **TX stage:** C0G/film clamp part selection, RCL1 rating, hard-clamp alternatives, avalanche margin, EMI.
8. **Mass reduction** (torque 2.88 -> under 2.2 kg m).
9. **KiCad schematics: generated (2026-10-23)** for CB1D, LB1, AB1A, AB1B, PB1R, PM1, HB1 (`make sch`, round-trip checked). Remaining: open them in KiCad and run its ERC (with item 2); TXJ1, HTA and SB1R-QA/QB have no netlist yet.
10. **Printing trials:** coupons, then cylinder (insert fit, rib supports), then formers.
11. **Prototype the receive boards** (QA/QB) and measure leak, L, R, self-resonance, then re-tune sbq_tune radii.
12. GitHub publication: done (github.com/sappystick/ARX).
13. **TXJ1 prototype and wire dressing**: build the junction with real litz and the real bridge cable bundle; hipot 1 kV; confirm the 4 mm lead bend in the window and the fit under the lid.
14. **Datasheet verification** of every rating in system_budget.py and ASSUMPTIONS 19 (prompt C05).
15. **Dual-PCB bench checks**: first articles of SB1R-QA/QB, LB1 (0.8 mm), CB1D, TXJ1: continuity against the netlists, then power-up with a current-limited supply.
16. Joystick push switch: closed, the joystick is removed (owner decision 2026-10-23); see item 20 for the CB1D inputs.
17. **BOM_MASTER.csv is stale** for HB1 HS1 (still SS49E) and CB1D RP1 (still 10k): mfg_v19.py, which builds it, reads legacy/PHIFOLD233_FINAL_FLAT_SET meshes that are not in the repo. Move it to the current BOMs (kit_v6/HB1, kit_v18) and regenerate.
18. **Hood v3 first article**: cut 26 tiles (27.0 x 26.2 and 28.3 x 39.7 x 2.5 mm MnZn), print the v3 carrier, bond; measure the axis field with and without the tiles and the receive ring-down with the hood fitted (ASSUMPTIONS 8, 23).
19. **Upper assembly first article**: print U1-U9 (PETG/ASA; pack shell PC), source the two coiled cords (OD <= 10.4 mm, stroke 356 mm) and a 7S 10-15 A BMS that fits 60 x 41 x 5.4 mm, build one pack; tune the Hall trigger (magnet grade, operate/release), check rail slide and latch, socket bond and drop test; weigh it and measure the torque about the grip.
20. **CB1D revision for the joystick removal**: JTR.5/.6 (JOY_X/JOY_Y) have no conductor; tie or depopulate RJX/RJY, CJX/CJY and free the pins, re-route and re-run DRC (with the head work).
21. **Tool fixes**: interference_audit.py voxeliser line (see CORRECTIONS: clamp both slice ends); sch_export.py truncates part values at 60 characters and can split parentheses (keep values short until fixed).
22. **Full-face LED map** (docs/design/LED_MAP_FULL_FACE_PLAN.md): 280-600 pixels from the centre to the rim over the hood, dense central pinpoint zone, trigger intensify. Accept: plan steps B-I done, eddy model of the LED board, LB2 flex DRC 0 in KiCad.
23. **Import the lowered-height / rigid-flex redesign.** It is not in origin/main (OPEN_ITEMS 3 is still only prompt P03). Accept: the files are in the repo and the regression runs on them.
24. **LED power switch and data architecture**: switched 5 V LED rail, multi-chain or clocked-LED data path, firmware frame rule (no write in a receive window). Merge with items 0 and 20.
25. **LED part datasheets**: SK6812-MINI-E / 2020 / SK9822 pinout, height, idle current, PWM frequency, finish (ferromagnetic nickel?) (ASSUMPTIONS 28-31).
26. **Flora NeoPixel v3 bench prototype** of the display grammar (same SK6812 protocol) before the flex is designed.
