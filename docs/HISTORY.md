# Build history (condensed)
1. Domed petal formers v11-v14 (superseded: straight-chord undersides, gap not mesh-verified). v15 flat-face set: six formers, hub (lanes/ports/tracks), base plate, 15 pins, coupons; mesh audits.
2. Receive study: figure-8 net (X8/W8/V8) + QUAD, nulls, hub-top antenna (HTA) idea; TX additions study (no extra TX layers; optional ferrite hood).
3. Head systems: hub cap (HTA seat, snap hooks), 66-pixel light-pipe roof, ferrite hood v1 (replaced), receive cassette base plate v2.
4. Vault v1: cups A/B/CD, skirt, CB1D (64 parts, Pico 2 W) and LB1 (66 LEDs) placements; connector/netlist audit; earlier boards AB1A/AB1B/PB1R/PM1/HB1 reused.
5. Audit round: four defects fixed (hood overlap, hook-LED collision, cup wall touching the ledge, pipe length); hood v2 (13 spokes).
6. Shaft and yoke: telescoping CFRP + GFRP lower tube, neck module at 0.4 m, ribbon cassette/trolley, heel yoke with serrated hinge, umbilical bridge, hub exit window; elbow tilt; harness master, test plan, layered cut-away renders.
7. Head simulations: real TX stage (snubber topology found), field/moment, target response and noise-limited depth, thermal; routing tools (grid router, Gerber writer); LB1 routed, CB1D 45/46.
8. Vault v2/v5: card-cage concept, eddy-plane finding, quadrupole receiver platform RX-Q (analog trim dropped), integrated cylinder v5 with removable roof, level-by-level drawings.
9. Handoff package (this repo).
10. Release 5.1: SB1R-QA/QB generated from scratch (three failed geometries caught by simulation), damping requirement found, independent DRC found grid-gap opens and a router via-clearance bug, CB1D routed 46/46 and DRC-clean, LB1 re-exported with stubs, bosses moved to r28 with base plate v3, KiCad files with routed copper.
11. Release 5.2: transmit lead channel and TXJ1 junction (leads had no route), wiring audit against the real netlists, stress/margin table, stack-up and voxel interference audits, LB1 0.8 mm and flat wire pads, harness v2.
