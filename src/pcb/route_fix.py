#!/usr/bin/env python3
"""Close the grid-quantisation gap between a track end and its pad: append the pad centre to any track end that lies near (but not on) a pad of the same net.
usage: route_fix.py BOARD ROUTE.json"""
import json, sys, math
board, rj = sys.argv[1], sys.argv[2]
P = json.load(open(f"kit_v18/{board}/pads.json"))["pads"]; r = json.load(open(rj)); added = 0
def edge_dist(p, q):
    """distance from the point q to the copper of pad p (0 inside a rectangle; the circle test keeps the track's half-width of 0.1 mm on the pad)"""
    if p.get("shape") == "circle": return math.dist(q, (p["x"], p["y"])) - (p["w"] / 2 - 0.1)
    return math.hypot(max(abs(q[0] - p["x"]) - p["w"] / 2, 0.0), max(abs(q[1] - p["y"]) - p["h"] / 2, 0.0))
for tr in r["tracks"]:
    for end in (0, -1):
        q = tr["pts"][end]
        # every same-net pad this track can reach (through-hole pads on any layer, SMD pads on F.Cu): connect to the NEAREST one by edge distance; an end that already lies on one needs nothing.
        # (the earlier version took the first pad in file order within reach, so a track ending 0.8 mm from RV1.1 was stubbed to a larger VBUS pad 2.3 mm away and RV1.1 stayed open)
        cand = [(edge_dist(p, q), p) for p in P if p.get("net") == tr["net"] and (p["tht"] or tr["layer"] == "F.Cu")]
        if not cand: continue
        d, p = min(cand, key=lambda t: t[0])
        if d <= 0.0 or d > 0.7: continue
        c = [p["x"], p["y"]]
        if end == 0: tr["pts"].insert(0, c)
        else: tr["pts"].append(c)
        added += 1
ECO = {"CB1D": [dict(net="GND", layer="F.Cu", width=0.2, pts=[[4.775, 9.5], [4.25, 8.9]])]}     # C5B.2 had no plane stub from the router: tie it to the existing GND via at (4.25, 8.45)
for e in ECO.get(board, []):
    if not any(e["pts"][0] == t["pts"][0] and e["net"] == t["net"] for t in r["tracks"]): r["tracks"].append(e); added += 1
seen = set(); uniq = []
for v in r["vias"]:                                            # the router can drop two identical vias on one spot (KiCad: holes_co_located): keep one
    k = (round(v[0], 3), round(v[1], 3), v[2])
    if k not in seen: seen.add(k); uniq.append(v)
dup = len(r["vias"]) - len(uniq); r["vias"] = uniq
json.dump(r, open(rj, "w")); print(board, "stubs added:", added, "duplicate vias removed:", dup)
