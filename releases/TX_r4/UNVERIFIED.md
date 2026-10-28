# UNVERIFIED register (machine-read by tests/regress.py and scripts/signoff_status.py)

A regression check may be SKIPPED only if its item is listed here with its ID. Any other missing result counts as FAIL (`python3 tests/regress.py --allow-skip` is for partial runs while developing, never for sign-off).
Closing an item means deleting its row in the same commit that adds the evidence (datasheet URL and exact number, CAM report, bench data). `scripts/signoff_status.py` enforces it: a row that is deleted while its evidence path (last column; the authoritative list is KNOWN_EVIDENCE in that script) does not exist turns the sign-off to FAIL, and a registered board ID that no board row shows is a FAIL too.

| ID | Item | Where it matters | How it closes | Evidence that must exist when the row is deleted |
|---|---|---|---|---|
| U-DS-HVTERM | PB1R JL1 (5.08 mm coil terminal block on DRAIN1, about 466 V) and the RCL1 lid resistor bank (5 k 10 W): no part with a manufacturer sheet read; Phoenix MKDS 1,5/2-5,08 is rated 250 / 400 / 630 V by overvoltage category in distributor listings only | rule 6 (630 V parts), pb1r_check 630 V row | manufacturer datasheet URL + rated voltage and its overvoltage category | docs/design/DATASHEET_LOG.md with `## U-DS-HVTERM: VERIFIED` |
| U-FAB-DRC | Fabricator's own DRC/CAM review of every board | all Gerbers | send to the vendor, attach their report | data/results/fab_drc/* |
| U-CAM-VIEW | Gerbers opened in a CAM viewer (visual check of the KiCad-written and gerber_out.py files) | all Gerbers | open each set, attach screenshots | data/results/cam_view/* |
| U-BENCH | Every bench item in docs/design/BENCH_FIRST_ARTICLE_TX.md (written in Step 6, NOT RUN) | whole transmit region | hardware | data/bench/* |
