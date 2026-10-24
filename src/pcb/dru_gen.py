#!/usr/bin/env python3
"""KiCad custom design rules (.kicad_dru) per board, in the order KiCad evaluates them: the LAST matching rule wins, so the generic rule comes first and the specific
rules (HV clearance, power track width) after it. The earlier shipped files (mfg_v19.py) ended with an unconditional 0.127 mm rule that overrode both specific rules,
so KiCad never enforced the 1.0 mm high-voltage clearance (negative control in kicad_drc.py history: a 5 mm HV rule produced no violations).
usage: dru_gen.py BOARD OUT.kicad_dru      boards: CB1D LB1 PB1R PM2 HB2 TXJ1   (CLAUDE.md rule 6: coil flyback nets need >= 1.0 mm)"""
import sys
GEN = dict(clearance=0.2, track=0.15)                       # the router rule (clr 0.2) and a conservative minimum track
BOARDS = {
    # CB1D-B: the MONO_IN coupling tap was removed (it carried the flyback pulse onto a 1.27 mm header and could not meet 1.0 mm)
    "CB1D": dict(hv=["COIL_A", "COIL_B", "DM1", "DM2"], hv_mm=1.0, power={"VBUS_IN": 0.8, "+5V": 0.6, "+5VA": 0.5}),
    "LB1": dict(hv=[], hv_mm=1.0, power={"+5V": 0.4, "GND": 0.4}),
    "PB1R": dict(hv=["DRAIN1", "CLAMP1"], hv_mm=1.0, power={"DRAIN1": 1.5, "SRC1": 1.5, "VBUS": 1.5, "GND": 1.5}),
    "PM2": dict(hv=[], hv_mm=1.0, power={"BAT_P": 1.5, "BAT_F": 1.5, "VBUS": 1.5, "GND": 1.5}),
    "HB2": dict(hv=[], hv_mm=1.0, power={}),
    "TXJ1": dict(hv=["TX_A", "TX_B"], hv_mm=1.0, power={"TX_A": 3.0, "TX_B": 3.0}),
}
def rules(board):
    b = BOARDS[board]; q = lambda ns: " || ".join(f"A.NetName == '{n}'" for n in ns)
    s = ["(version 1)", f'(rule "general {GEN["clearance"]} mm / {GEN["track"]} mm"', f'  (constraint clearance (min {GEN["clearance"]}mm))', f'  (constraint track_width (min {GEN["track"]}mm)))']
    for n, w in b["power"].items(): s += [f'(rule "power width {n}"', f'  (condition "A.NetName == \'{n}\'")', f'  (constraint track_width (min {w}mm)))']
    if b["hv"]: s += [f'(rule "HV flyback nets {b["hv_mm"]} mm"', f'  (condition "{q(b["hv"])}")', f'  (constraint clearance (min {b["hv_mm"]}mm)))']
    return "\n".join(s) + "\n"
if __name__ == "__main__":
    open(sys.argv[2], "w").write(rules(sys.argv[1])); print("wrote", sys.argv[2])
