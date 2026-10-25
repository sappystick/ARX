#!/usr/bin/env python3
"""Copper-to-board-edge check read back from the Gerber files (not from the generator): the board outline is rebuilt from Edge_Cuts, every copper layer is rebuilt
with gerber_geom (dark adds, clear subtracts) and measured: copper area outside the outline (the notch included) and the smallest gap from copper to the outline.
Floor: dru_gen.GEN["edge"] (0.5 mm; AdvancedPCB requires 0.015" = 0.381 mm on inner layers, 0.010" outer). KiCad's DRC does not see these files when they are written by
gerber_out.py / sbq_export.py (it fills its own zones), which is how a circle-clipped plane that ran into the notch and to 0.1 mm of the edge went unnoticed until Step 5.
usage: gerber_edge_check.py OUT.json GERBER_DIR PREFIX [GERBER_DIR PREFIX ...]"""
import sys, os, glob, json
from shapely.geometry import Polygon
from gerber_geom import layer_geometry
import dru_gen
FLOOR = dru_gen.GEN["edge"]
def outline(path):
    ring, _ = layer_geometry(path)                       # the 0.1 mm Edge_Cuts stroke as a thin ring
    parts = list(ring.geoms) if hasattr(ring, "geoms") else [ring]
    inner = max((Polygon(h) for p in parts for h in p.interiors), key=lambda q: q.area)
    return inner.buffer(0.05)                             # back out to the stroke centre line = the board edge
out = {}
args = sys.argv[2:]
for d, pre in zip(args[0::2], args[1::2]):
    board = outline(os.path.join(d, f"{pre}-Edge_Cuts.gbr")); rows = {}
    for f in sorted(glob.glob(os.path.join(d, f"{pre}-*_Cu.gbr"))):
        cu, _ = layer_geometry(f); ly = os.path.basename(f)[len(pre) + 1:-4]
        outside = cu.difference(board).area; gap = board.exterior.distance(cu) if not cu.is_empty else None
        rows[ly] = dict(outside_mm2=round(outside, 4), min_edge_gap_mm=None if gap is None else round(gap, 3), ok=outside < 1e-3 and (gap is None or gap >= FLOOR - 1e-3))
    out[os.path.basename(d.rstrip("/"))] = dict(layers=rows, ok=all(r["ok"] for r in rows.values()))
res = dict(floor_mm=FLOOR, sets=out, ok=all(v["ok"] for v in out.values()))
json.dump(res, open(sys.argv[1], "w"), indent=1)
for k, v in out.items(): print(k, "OK" if v["ok"] else "FAIL", {ly: (r["outside_mm2"], r["min_edge_gap_mm"]) for ly, r in v["layers"].items()})
sys.exit(0 if res["ok"] else 1)
