# Blockers of this release

Closed in RX_r3 (2026-10-28): BLOCKER 2 (SDI tied low / readout): the datasheet covers it (Table 17: WR = 0, REGADDR 0 is ignored), and the 2-wire readout is modeled and tested against the netlists (src/sim/ad7389_readout.py, B6); BLOCKER 3 (+3V3D budget): AMS1117-3.3 rows in system_budget with the RML 270 ohm minimum-load bleed on CB1D (B3). Both remain MODELED: the CB1D firmware does not exist yet.

OPEN: island hatch connectivity has been read back from the Gerbers (gerber_geom) and KiCad-checked, but not opened in a CAM viewer or reviewed by a fabricator (U-CAM-VIEW, U-FAB-DRC); SW1G66 (TI SCES323R) and BAV199 (Nexperia v.3) pin maps are now datasheet-checked (B7); OPA2365 per DATASHEET_LOG U-DS-RXAMP; nothing here is built or measured.
