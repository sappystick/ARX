#!/usr/bin/env python3
"""Independent check of the PLANE layers of KiCad-written Gerbers (PB1R): re-read the .gbr files with gerbonara, rebuild the copper of each plane layer with shapely (every primitive in file order:
dark = add, clear = subtract) and measure the distance from every HV through-hole pad and via to the plane copper. The 1.0 mm rule (CLAUDE.md rule 6) needs >= 1.0 mm from the pad's copper edge.
CONTROL: the same reconstruction must find plane copper touching the pads of the plane's own net, otherwise the rebuild is empty or mis-placed and the result is void.
usage: PYTHONPATH=<gerbonara dir> gerber_plane_check.py BOARD GERBER_DIR PREFIX HV_NETS(comma) PLANE_LAYER:NET[,..]   e.g. In1:GND,In2:VBUS     -> kit_v22/gerber_plane_<BOARD>.json"""
import sys, os, json, math, re
from shapely.geometry import Point
from gerber_geom import layer_geometry as layer_copper
board, d, prefix, hv, planes = sys.argv[1], sys.argv[2], sys.argv[3], set(sys.argv[4].split(",")), dict(x.split(":") for x in sys.argv[5].split(","))
PJ = f"kit_v18/{board}/pads.json" if os.path.exists(f"kit_v18/{board}/pads.json") else f"kit_v6/{board}/pads.json"
P = json.load(open(PJ))["pads"]; RT = json.load(open(f"kit_v20/route_{board}.json")); CX = CY = 100.0
res = []; ctl = []
for ly, net in planes.items():
    path = os.path.join(d, f"{prefix}-{ly}_Cu.gbr"); cu, n = layer_copper(path)
    # board coordinates of the KiCad file: x = CX + x, y = CY + y (y down in both pads.json and the file); gerber y is up -> mirror
    def pt(x, y): return (CX + x, -(CY + y))
    for p in P:
        if not p["tht"]: continue
        c = pt(p["x"], p["y"]); r = max(p["w"], p["h"]) / 2
        # a through-hole pad has its own copper flash on the inner layers: remove that disc before measuring the distance to the PLANE copper
        if p["net"] in hv: res.append(dict(layer=ly, item=f"{p['ref']}.{p['num']} ({p['net']})", distance_mm=round(max(cu.difference(Point(c).buffer(r + 0.02)).distance(Point(c)) - r, 0.0), 3)))
        if p["net"] == net: ctl.append(dict(layer=ly, item=f"{p['ref']}.{p['num']}", plane_within_mm=round(cu.distance(Point(c)), 3)))
    for v in RT["vias"]:
        c = pt(v[0], v[1])
        if v[2] in hv: res.append(dict(layer=ly, item=f"via {v[2]}", distance_mm=round(max(cu.difference(Point(c).buffer(0.32)).distance(Point(c)) - 0.3, 0.0), 3)))
bad = [x for x in res if x["distance_mm"] < 1.0 - 0.01]
control_ok = len(ctl) > 0 and sum(1 for x in ctl if x["plane_within_mm"] < 0.7) >= 0.8 * len(ctl)
out = dict(board=board, hv_checks=len(res), failures=len(bad), failing=bad[:10], min_distance_mm=min((x["distance_mm"] for x in res), default=None), control_pads=len(ctl), control_ok=control_ok)
json.dump(out, open(f"kit_v22/gerber_plane_{board}.json", "w"), indent=1)
print(f"{board}: KiCad Gerber plane layers: {len(res)} HV pad/via checks, {len(bad)} closer than 1.0 mm to plane copper, min {out['min_distance_mm']} mm; control (plane copper reaches its own net's pads): {control_ok} ({len(ctl)} pads)")
