#!/usr/bin/env python3
"""KiCad pad geometry = placement model (pads.json), pad by pad, on the boards whose exporters rotate footprints (lb1_export, pw_export, cb1d_export).
Found 2026-10-28 (CORRECTIONS): KiCad stores a pad's angle ABSOLUTE (footprint rotation included); the exporters wrote pads without it, so on a 90 / 270 deg
footprint KiCad drew every non-square pad unrotated while the router, drc.py and gerber_out.py used the rotated pads. Checked per pad: centre within 0.005 mm
and bounding-box width / height within 0.005 mm of pads.json, on the routed KiCad boards (the files KiCad DRC, kicad_gerber.py and fab_margin.py read).
usage (in work/): /usr/bin/python3 pad_orient_check.py [OUT.json]"""
import sys, json, os
import pcbnew
BOARDS = {"LB1": ("kit_v22/KICAD/PF233-LB1_routed.kicad_pcb", "kit_v18/LB1/pads.json"), "CB1D": ("kit_v22/KICAD/PF233-CB1D_routed.kicad_pcb", "kit_v18/CB1D/pads.json"),
          "PB1R": ("kit_v22/KICAD/PF233-PB1R_routed.kicad_pcb", "kit_v6/PB1R/pads.json"), "PM2": ("kit_v22/KICAD/PF233-PM2_routed.kicad_pcb", "kit_v6/PM2/pads.json"),
          "HB2": ("kit_v22/KICAD/PF233-HB2_routed.kicad_pcb", "kit_v6/HB2/pads.json"), "AU1": ("kit_v22/KICAD/PF233-AU1_routed.kicad_pcb", "kit_v6/AU1/pads.json")}
TOL = 0.005
out = {}
for name, (brd, pj) in BOARDS.items():
    if not (os.path.exists(brd) and os.path.exists(pj)): out[name] = dict(missing=True, ok=False); continue
    b = pcbnew.LoadBoard(brd); model = {(p["ref"], p["num"]): p for p in json.load(open(pj))["pads"]}
    kp = {(f.GetReference(), pd.GetNumber()): pd for f in b.GetFootprints() for pd in f.Pads()}
    # the exporters shift the model frame to the sheet: take the offset from the mean over all pads (a constant translation)
    common = [k for k in model if k in kp]
    ox = sum(pcbnew.ToMM(kp[k].GetPosition().x) - model[k]["x"] for k in common) / len(common); oy = sum(pcbnew.ToMM(kp[k].GetPosition().y) - model[k]["y"] for k in common) / len(common)
    bad = []
    for k in common:
        pd, m = kp[k], model[k]; bb = pd.GetBoundingBox(); w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
        dx, dy = pcbnew.ToMM(pd.GetPosition().x) - ox - m["x"], pcbnew.ToMM(pd.GetPosition().y) - oy - m["y"]
        if max(abs(dx), abs(dy), abs(w - m["w"]), abs(h - m["h"])) > TOL: bad.append(dict(pad=f"{k[0]}.{k[1]}", model_wh=[m["w"], m["h"]], kicad_wh=[round(w, 4), round(h, 4)], dxy=[round(dx, 4), round(dy, 4)]))
    out[name] = dict(pads_compared=len(common), pads_missing=sorted(f"{a}.{n}" for a, n in model if (a, n) not in kp)[:10], mismatches=len(bad), examples=bad[:6], ok=not bad and len(common) == len(model))
    print(name, out[name]["pads_compared"], "pads, mismatches", out[name]["mismatches"], "OK" if out[name]["ok"] else "FAIL")
json.dump(dict(status="tool-checked: KiCad pad geometry vs the placement model", tol_mm=TOL, boards=out), open(sys.argv[1] if len(sys.argv) > 1 else "kit_v22/pad_orient_check.json", "w"), indent=1)
