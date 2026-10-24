#!/usr/bin/env python3
"""Close the grid-quantisation gap between a track end and its pad: append the pad centre to any track end that lies near (but not on) a pad of the same net.
usage: route_fix.py BOARD ROUTE.json"""
import json, sys, math
board, rj = sys.argv[1], sys.argv[2]
P = json.load(open(f"kit_v18/{board}/pads.json"))["pads"]; r = json.load(open(rj)); added = 0
def inside(p, q, m):
    # the track end must lie on the pad copper with the track's own half-width to spare: round pads need a circle test (a square test accepted the corners of the bounding box,
    # leaving the CS track on CB1D grazing U1.6 by 0.005 mm: a hairline open that KiCad's DRC reported)
    if p.get("shape") == "circle": return math.dist(q, (p["x"], p["y"])) <= p["w"] / 2 - 0.1 + m
    return abs(q[0] - p["x"]) <= p["w"] / 2 + m and abs(q[1] - p["y"]) <= p["h"] / 2 + m
for tr in r["tracks"]:
    for end in (0, -1):
        q = tr["pts"][end]
        for p in P:
            if p.get("net") != tr["net"]: continue
            if not (p["tht"] or tr["layer"] == "F.Cu"): continue
            if math.dist(q, (p["x"], p["y"])) > max(p["w"], p["h"]) / 2 + 0.7: continue
            if inside(p, q, 0.0): break                                  # already on the pad copper
            c = [p["x"], p["y"]]
            if end == 0: tr["pts"].insert(0, c)
            else: tr["pts"].append(c)
            added += 1; break
ECO = {"CB1D": [dict(net="GND", layer="F.Cu", width=0.2, pts=[[4.775, 9.5], [4.25, 8.9]])]}     # C5B.2 had no plane stub from the router: tie it to the existing GND via at (4.25, 8.45)
for e in ECO.get(board, []):
    if not any(e["pts"][0] == t["pts"][0] and e["net"] == t["net"] for t in r["tracks"]): r["tracks"].append(e); added += 1
json.dump(r, open(rj, "w")); print(board, "stubs added:", added)
