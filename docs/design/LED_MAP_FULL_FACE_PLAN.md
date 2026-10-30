# Full-face LED map: feasibility and work plan (2026-10-30)

Status: PLAN ONLY. Nothing here is generated, built or measured. Numbers marked (U) are unverified and need a datasheet (ASSUMPTIONS 28-31).

## 1. What the repo has today (origin/main, commit 7b4fc6f)
- LB1: D78 board at z39.2-41.3 (0.8 mm FR4 + 0.8 mm LED), 66 SK6812-MINI-E class pixels in 4 rings (r12.5 / 20 / 26.5 / 34 mm: 12 / 18 / 24 / 12), 1.7 mm light-pipe holes in the roof (hub_v22.py PX, PIXEL_MAP_66.csv). Three rings are depth tiers, one is a noise ring. All 66 sit inside the D104 cap; the hood annulus (r52.6-116.1) has no LEDs.
- One data line: CB1D 74AHCT1G125 -> JLB.2 LED_IN, 4-wire JLB flat pads. Rail: OKI-78SR 1.5 A; 66 x 60 mA = 3.96 A fails by design, firmware cap 0.35 A (OPEN_ITEMS 0, still open).
- Free space for a face map: the hood carrier top is z33.4 and the skirt stops at z33.4. Above r52.6 the only occupants are the heel bridge/cradle (z33.7-42.0 at 178 deg), the TX wall-top channel (r45.6-48.6, up to z43.5) and the 90 deg spine. Roof z41.3-44.5 and cap z40.4-47.1 cover r < 52 only.
- NOT in the repo: the rigid-flex spine (OPEN_ITEMS 3 is only prompt P03), any lowered-height redesign, any remapped/rerouted flex boards. The vault is still L0-L8 = 47.1 mm with rigid CB1D/LB1/AB1x. If that work exists it was not pushed to sappystick/ARX: send the branch or files before the LED work starts, because the flex outline sets the LED data/power path.

## 2. Pixel budget (geometry only; pitch is centre-to-centre)
| Layout | LEDs |
|---|---|
| 12 mm pitch, 9 rings, r10-110 | 283 |
| 10 mm pitch, 11 rings, r10-110 | 415 |
| 8 mm pitch, 13 rings, r10-110 | 612 |
| Proposed: dense centre r6-30 at 6 mm (5 rings) + outer map r40-112 at 10 mm (8 rings) | 94 + 382 = 476 |
Pixel size: the Adafruit Flora v3 (SK6812, 4 sew-tab pads, PDF) is a hand-sewn wearable pixel, roughly 10-13 mm round from the photo (U, no dimensions in the PDF). It is fine for a bench prototype of the firmware (same SK6812 protocol) but not for the head: 4 hand-wired pads per pixel x 400+ pixels is not buildable, and each pad is loose copper. Production uses the bare SK6812-MINI-E/2020 on our own flex.

## 3. Constraints that decide the design
1. Eddy rule (rule 5): a 232 mm LED board over the transmit coil is the largest conductive sheet in the head. Power/ground must be hatched or traces-only, no pour, no closed loop around the axis; LED power as radial spokes with a break in every ring bus. Needs a model before layout (tau and nugget-equivalent signal, as for the D78 plane at 17.8 us).
2. Receive timing: the SK6812 data stream (800 kHz, 30 us/pixel: 476 pixels = 14.3 ms in one line) runs through receive gates (first gate 5-7 us after turn-off, 400-800 Hz pulses). Options: (a) clocked LEDs (SK9822/APA102 class, pausable mid-frame) written only in dead time; (b) 8-16 parallel SK6812 chains from RP2350 PIO so a frame fits one inter-pulse gap (8 chains x 60 pixels = 1.8 ms). Both are firmware + CB1D changes. Verify against the air leak on the bench (OPEN_ITEMS 11/15).
3. Current: capped by firmware, not by pixel count. 476 pixels at idle (U ~0.5-1 mA each) could cost 0.25-0.5 A before any light, which breaks the 0.5 A budget in system_budget.py: either a switched LED rail (high-side switch on CB1D) or a larger 5 V converter.
4. Height: a 0.4-0.8 mm flex annulus plus a 1.5-2.5 mm diffuser/light-pipe layer adds about 3-4 mm above z33.4 outside r52: head height at the rim stays below the 44.5 roof, so no new tallest point. Heel (178 deg), spine (90 deg) and the TX channel need cut-outs.
5. Heat: LEDs are capped, so this is small; re-run sim_head2 with the new LED power.
6. HV rule: LED nets are 5 V logic; keep them off the coil flyback nets, no routing under the connector lanes.

## 4. The "Halbach shield" question
A Halbach array concentrates the field of its own permanent magnets on one side. It does not redirect an external field, and the pulse-induction transmit field is produced by the coil current, not by magnets. Permanent magnets would also hurt: NdFeB is conductive (eddy loss and a target-like signal at turn-off) and any magnet adds a static bias, microphonics and mass. Sintered ferrite magnets are insulating but their permeability is near 1, so they would not shield anything. What actually does the job:
- Above the coil, steer flux down: MnZn ferrite hood v3 (already modeled +12.9-14.2 % at 200 mm). It returns the upward flux; it does not push the field sideways.
- Between the coil and the LED board, a thin slit/segmented ferrite or nanocrystalline layer (high mu, low conductivity) keeps field out of the LED copper. Candidate: reuse the hood tiles' footprint, with the LED flex on top.
- The LEDs do not need magnetic shielding (silicon, no ferromagnetic parts except the SK6812 lead frame (U)). The real risk is copper, switching noise and ferromagnetic parts in the LED stack: check nickel finish on pads and any steel parts.
Decision for the owner: I recommend dropping the Halbach layer and using hood v3 plus a mesh/segmented LED board; I will model both layouts first.

## 5. To-do list (in order; each has an acceptance test)
A. Baseline and tools (done 2026-10-30): requirements, shapely, trimesh, networkx, rtree, pytest, gerbonara, pyclipper (pip); KiCad 7.0.11 (kicad-cli), OpenSCAD, ngspice, gerbv (apt). Accept: make setup, make verify-quick, python3 tests/regress.py all pass.
B. Get the missing redesign: owner supplies the lowered-height / rigid-flex work (branch, files or Cowork folder); import it as the new baseline and re-run the regression. Accept: DESIGN_STATE shows the new stack and heights.
C. LED requirements: owner chooses pixel pitch/count (section 2), the display grammar (location = azimuth/radius, depth = brightness/ring, colour = material, size = blob radius, centre pinpoint zone, trigger intensify) and the maximum average LED power. Accept: one page in docs/design with numbers.
D. Eddy model of the LED board over the coils: solid vs hatched vs spoke-only, with and without a ferrite spacer. Accept: modeled nugget-equivalent signal and decay time per option, stated assumptions, sim-reviewer pass.
E. LED technology trade: SK6812-MINI-E vs SK6812 2020 vs SK9822/APA102-class (clocked), with datasheet pins, heights, idle current, PWM frequency. Accept: ASSUMPTIONS rows 28-31 verified from datasheets (need browsing; the Adafruit PDF has no dimensions).
F. Power and data architecture: chains, level shifter, switched LED rail, CB1D revision (merge with OPEN_ITEMS 0 and 20). Accept: updated netlist, system_budget rows, wiring_audit 0 errors.
G. Mechanics: LED annulus plate/diffuser generator (new version name, e.g. lbmap_v1.py), pixel holes or a one-piece diffuser, cut-outs at 90/178 deg and the TX channel, fits to hood and roof. Accept: new checks in check_v22-style script and tests/regress.py; head_crosscheck 0 fail.
H. Board generator: LB2 flex annulus (pixel map CSV -> placement -> routing -> route_fix -> drc.py -> KiCad import/DRC via kicad-cli). Accept: independent DRC 0, KiCad DRC 0 errors (this also advances OPEN_ITEMS 2).
I. Firmware in Python first (OPEN_ITEMS 5): detection -> display mapping, frame-timing rule, power cap. Accept: simulated waveforms drive the map; no LED write inside a receive window.
J. Bench items for the future first article: LED-on versus LED-off receive noise and air leak; thermal; light-pipe brightness in daylight.
K. Docs: DESIGN_STATE section, CORRECTIONS row (the earlier "3 rings x 24 = 72" concept in led_map.py vs the built 66), OPEN_ITEMS 22-26, regression numbers.
