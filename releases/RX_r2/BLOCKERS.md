# Blockers of this release

BLOCKER 2 (interface): SDI is tied to ground (the datasheet does not say whether that is allowed) and no software reset is issued; the 2-wire readout (SDOA = channels A then C, SDOB = channel B, J2 SDO3 unused on AB1A) needs a CB1D firmware change.

BLOCKER 3 (supply): the extra +3V3D load (about 25 mA, 89 mW typical from the datasheet) is not checked against the rail budget.

OPEN: island hatch connectivity has been read back from the Gerbers (gerber_geom) and KiCad-checked, but not opened in a CAM viewer or reviewed by a fabricator (U-CAM-VIEW, U-FAB-DRC); SW1G66, OPA2365 and BAV199 pin maps stay VERIFY; nothing here is built or measured.
