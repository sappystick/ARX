#!/usr/bin/python3
"""B8: BOM and pick-and-place for the boards that have no design database (TXJ1, SB1R-QA, SB1R-QB), read from their KiCad boards with pcbnew.
Origin = board centre: the circumcentre of the three mounting holes on the round SB1R boards, else the Edge.Cuts bounding-box centre (TXJ1); pick-and-place is y-UP (PosY = -(y - cy)) as docs/CONVENTIONS.md requires; Rot = KiCad orientation (CCW, deg).
Footprints that are bare pads (one pad, no value beyond the pad name: lead pads, transfer pads, mounting holes, PTH junction pads) are listed in the BOM as
'not placed' rows so the fabrication note has them, and they are left out of the pick-and-place. MODELED / tool-checked: no part on these boards is bench-checked.
usage: /usr/bin/python3 kicad_bom_pnp.py BOARD.kicad_pcb NAME OUTDIR"""
import sys, os, csv
import pcbnew
pcb, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
B = pcbnew.LoadBoard(pcb); bb = B.GetBoardEdgesBoundingBox()
cx, cy = pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y)
_mh = [(pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y)) for f in B.GetFootprints() if "MH_" in f.GetFPIDAsString()]
if len(_mh) >= 3:                                                      # round boards (SB1R): the three mounting holes sit on one bolt circle about the board centre -> circumcentre
    (ax, ay), (bx, by), (qx, qy) = _mh[:3]; d = 2 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
    cx = ((ax * ax + ay * ay) * (by - qy) + (bx * bx + by * by) * (qy - ay) + (qx * qx + qy * qy) * (ay - by)) / d
    cy = ((ax * ax + ay * ay) * (qx - bx) + (bx * bx + by * by) * (ax - qx) + (qx * qx + qy * qy) * (bx - ax)) / d
parts, bare = [], []
for f in B.GetFootprints():
    ref, val, fp = f.GetReference(), f.GetValue(), f.GetFPIDAsString(); n = len(list(f.Pads()))
    x, y = pcbnew.ToMM(f.GetPosition().x) - cx, pcbnew.ToMM(f.GetPosition().y) - cy
    row = dict(ref=ref, val=val, fp=fp, x=round(x, 3), y=round(-y, 3), rot=round(f.GetOrientationDegrees(), 1) % 360, side="bottom" if f.IsFlipped() else "top")
    (bare if n <= 1 else parts).append(row)
os.makedirs(out, exist_ok=True)
groups = {}
for p in parts: groups.setdefault((p["val"], p["fp"]), []).append(p["ref"])
with open(f"{out}/{name}_BOM.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Qty", "Refs", "Value / note", "Footprint", "Placed"])
    for (v, fp), refs in sorted(groups.items()): w.writerow([len(refs), ",".join(sorted(refs)), v, fp, "yes"])
    kinds = {}
    for b in bare: kinds.setdefault(b["fp"], []).append(b["ref"])
    for fp, refs in sorted(kinds.items()): w.writerow([len(refs), ",".join(sorted(refs)), "bare pad / hole on the board (no part; leads soldered by hand)", fp, "no"])
    w.writerow([1, name, f"bare board {name} (Gerbers: data/gerber/{name.replace('-', '_')}*)", "-", "board"])
with open(f"{out}/{name}_pickplace.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Ref", "Val", "Package", "PosX_mm", "PosY_mm", "Rot", "Side"])
    for p in sorted(parts, key=lambda r: r["ref"]): w.writerow([p["ref"], p["val"], p["fp"], p["x"], p["y"], p["rot"], p["side"]])
print(f"{name}: {len(parts)} placed parts, {len(bare)} bare pads/holes, origin ({cx:.2f}, {cy:.2f}) mm")
