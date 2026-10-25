#!/usr/bin/env python3
"""Close the grid-quantisation gap between a track end and its pad: append the pad centre to any track end that lies near (but not on) a pad of the same net.
usage: route_fix.py BOARD ROUTE.json"""
import json, sys, math
board, rj = sys.argv[1], sys.argv[2]
import os
PJ = f"kit_v18/{board}/pads.json" if os.path.exists(f"kit_v18/{board}/pads.json") else f"kit_v6/{board}/pads.json"
P = json.load(open(PJ))["pads"]; r = json.load(open(rj)); added = 0
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
# Kelvin ECO: the shunt voltage must be sensed AT the shunt pad over its own narrow track, not through the 20 A copper. Remove the router's connection to the sense resistor pad and run a direct track.
KELVIN = {"PB1R": [(("RK1", "1"), ("RS1S", "1"), 0.3)]}
padd = {(p["ref"], p["num"]): p for p in P}
for a, b, w in KELVIN.get(board, []):
    ca = [padd[a]["x"], padd[a]["y"]]; cb = [padd[b]["x"], padd[b]["y"]]; net = padd[a]["net"]
    if any(t["net"] == net and len(t["pts"]) == 2 and t["pts"][0] == ca and t["pts"][1] == cb for t in r["tracks"]): continue          # already applied
    keep = [t for t in r["tracks"] if not (t["net"] == net and (math.dist(t["pts"][0], ca) < 0.01 or math.dist(t["pts"][-1], ca) < 0.01))]
    removed = len(r["tracks"]) - len(keep); r["tracks"] = keep + [dict(net=net, layer="F.Cu", width=w, pts=[ca, cb])]; added += 1; print(f"Kelvin ECO {a} -> {b}: removed {removed} router track(s), added a {w} mm sense track")
seen = set(); uniq = []
for v in r["vias"]:                                            # the router can drop two identical vias on one spot (KiCad: holes_co_located): keep one
    k = (round(v[0], 3), round(v[1], 3), v[2])
    if k not in seen: seen.add(k); uniq.append(v)
dup = len(r["vias"]) - len(uniq); r["vias"] = uniq
# drill-to-drill floor (dru_gen.GEN["hole_to_hole"], TTM 16 mil same-net guideline, docs/design/FAB_RULES_VERIFIED.md): the router can drop two same-net vias closer than that.
# Merge them: drop the later via and tie every track vertex that sat on it to the kept via with a stub on that track's layer. The stub is no wider than the via pad, so its
# copper stays inside the hull of the two via pads; that hull can reach nearer to other copper than the pads did, so the KiCad DRC that follows is the check (Step 5: 0 errors).
# The kept via carries the layer change and the plane connection.
import dru_gen
VIA_DRILL = 0.3; c2c = dru_gen.GEN["hole_to_hole"] + VIA_DRILL; kept = []; merged = 0
for v in r["vias"]:
    near = next((k for k in kept if k[2] == v[2] and math.dist(k[:2], v[:2]) < c2c), None)
    if near is None: kept.append(v); continue
    for layer in sorted({t["layer"] for t in r["tracks"] if t["net"] == v[2] and any(math.dist(q, v[:2]) < 1e-6 for q in t["pts"])}):
        w = min(0.6, max(t["width"] for t in r["tracks"] if t["net"] == v[2] and t["layer"] == layer and any(math.dist(q, v[:2]) < 1e-6 for q in t["pts"])))
        r["tracks"].append(dict(net=v[2], layer=layer, width=w, pts=[list(v[:2]), list(near[:2])])); added += 1
    merged += 1
r["vias"] = kept
json.dump(r, open(rj, "w")); print(board, "stubs added:", added, "duplicate vias removed:", dup, "close same-net vias merged:", merged)
