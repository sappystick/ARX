#!/usr/bin/env python3
"""Add extra plane vias INSIDE the pads that carry the 20 A pulse return (shunt ground pad, bulk and decoupling capacitor pads), after route_fix.py.
The router puts one 0.6 / 0.3 via per plane stub; one via cannot carry a 20 A pulse return and adds inductance. Vias are placed on a 0.9 mm grid inside the pad copper, nearest the pad centre first,
only where they stay 0.5 mm (0.2 clearance + 0.3 via radius) from every other-net track, via and pad. Via-in-pad on SMD lands: the vias must be filled/plugged or the solder wicks (fabricator item, FAB_RULES.md).
usage: viafarm.py BOARD ROUTE.json      (idempotent: counts the vias already inside each pad)"""
import sys, json, math, os
board, rj = sys.argv[1:3]
SPEC = {   # (ref, pin) -> number of vias wanted inside the pad
    "PB1R": {("RS1S", "2"): 6, **{(f"CD{i}", "1"): 3 for i in range(1, 7)}, **{(f"CD{i}", "2"): 3 for i in range(1, 7)}, **{(f"CM{i}", "1"): 2 for i in range(1, 5)}, **{(f"CM{i}", "2"): 2 for i in range(1, 5)}},
}[board]
PJ = f"kit_v18/{board}/pads.json" if os.path.exists(f"kit_v18/{board}/pads.json") else f"kit_v6/{board}/pads.json"
P = json.load(open(PJ))["pads"]; r = json.load(open(rj)); VP, CL = 0.3, 0.2
def seg_d(q, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / L2)); return math.hypot(q[0] - ax - t * dx, q[1] - ay - t * dy)
def clear_ok(q, net):
    for t in r["tracks"]:
        if t["net"] == net: continue
        for a, b in zip(t["pts"][:-1], t["pts"][1:]):
            if seg_d(q, a, b) < t["width"] / 2 + VP + CL: return False
    for v in r["vias"]:
        if v[2] != net and math.dist(q, v[:2]) < 2 * VP + CL: return False
    for p in P:
        if p["net"] == net: continue
        dx = max(abs(q[0] - p["x"]) - p["w"] / 2, 0); dy = max(abs(q[1] - p["y"]) - p["h"] / 2, 0)
        if math.hypot(dx, dy) < VP + CL: return False
    return True
added = 0
for (ref, num), want in SPEC.items():
    p = next(x for x in P if x["ref"] == ref and x["num"] == num); net = p["net"]
    have = [v for v in r["vias"] if v[2] == net and abs(v[0] - p["x"]) <= p["w"] / 2 - VP and abs(v[1] - p["y"]) <= p["h"] / 2 - VP]
    cands = []
    nx, ny = int((p["w"] - 2 * VP) / 0.9), int((p["h"] - 2 * VP) / 0.9)
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = p["x"] - (nx * 0.9) / 2 + i * 0.9; y = p["y"] - (ny * 0.9) / 2 + j * 0.9
            if abs(x - p["x"]) <= p["w"] / 2 - VP + 1e-9 and abs(y - p["y"]) <= p["h"] / 2 - VP + 1e-9: cands.append((round(x, 3), round(y, 3)))
    cands.sort(key=lambda c: math.dist(c, (p["x"], p["y"])))
    for c in cands:
        if len(have) >= want: break
        if any(math.dist(c, v[:2]) < 0.85 for v in r["vias"]): continue
        if not clear_ok(c, net): continue
        v = [c[0], c[1], net]; r["vias"].append(v); have.append(v); added += 1
json.dump(r, open(rj, "w")); print(board, "via-farm vias added:", added)
