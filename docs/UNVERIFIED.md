# UNVERIFIED register (machine-read by tests/regress.py and scripts/signoff_status.py)

A regression check may be SKIPPED only if its item is listed here with its ID. Any other missing result counts as FAIL (`python3 tests/regress.py --allow-skip` is for partial runs while developing, never for sign-off).
Closing an item means deleting its row in the same commit that adds the evidence (datasheet URL and exact number, CAM report, bench data). `scripts/signoff_status.py` enforces it: a row that is deleted while its evidence path (last column; the authoritative list is KNOWN_EVIDENCE in that script) does not exist turns the sign-off to FAIL, and a registered board ID that no board row shows is a FAIL too.

| ID | Item | Where it matters | How it closes | Evidence that must exist when the row is deleted |
|---|---|---|---|---|
| U-DS-PARTS | Part ratings (IPB65R095C7, ES3J/ES3K, TC4420, LM393, OKI-78SR-12/-5, SMCJ33A, R2512, MT60, P30B, BAV199, 74HC4051, OPA2365, OPA2211, 50 V bulk capacitor, four-terminal shunt) | system_budget.py, tx_vbus_sweep.py, ASSUMPTIONS 9/19/25-29 | Step 5: manufacturer datasheet URL + exact rating | docs/design/DATASHEET_LOG.md |
| U-FAB-RULES | Advanced Circuits / TTM capability, via-in-pad/filled-via and finish pages vs the dru_gen.py floor | dru_gen.py, FAB_RULES.md | Step 5: vendor URL + exact numbers | docs/design/FAB_RULES_VERIFIED.md |
| U-FAB-DRC | Fabricator's own DRC/CAM review of every board | all Gerbers | send to the vendor, attach their report | data/results/fab_drc/* |
| U-CAM-VIEW | Gerbers opened in a CAM viewer (visual check of the KiCad-written and gerber_out.py files) | all Gerbers | open each set, attach screenshots | data/results/cam_view/* |
| U-ROUTE-PM2 | PM2 routed, KiCad-DRC'd, Gerbers | PM2 | Step 4 | route, DRC, KiCad DRC, Gerbers (board row turns PASS) |
| U-ROUTE-HB2 | HB2 routed, KiCad-DRC'd, Gerbers | HB2 | Step 4 | route, DRC, KiCad DRC, Gerbers (board row turns PASS) |
| U-KICAD-HTA | HTA in the KiCad DRC flow | HTA | Step 4 (if a KiCad file can be generated) | data/results/kicad_drc_HTA.json (board row turns PASS) |
| U-COLD-BOOTSTRAP | scripts/bootstrap.sh cold path (KiCad install in a bare container) tested end to end; the warm path and the PPA key/source steps are tested | scripts/bootstrap.sh | run it in a fresh container | data/results/bootstrap_cold.json |
| U-BENCH | Every bench item in docs/design/BENCH_FIRST_ARTICLE_TX.md (written in Step 6, NOT RUN) | whole transmit region | hardware | data/bench/* |
