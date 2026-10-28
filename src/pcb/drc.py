#!/usr/bin/env python3
"""Independent geometric DRC for the routed boards (does not use the router's grid): clearance by net class, connectivity of every net, edge and notch keep-out.
usage: drc.py BOARD ROUTE.json NOTCH_SIGN [HV nets comma separated]"""
import json, sys, math, numpy as np
from scipy.spatial import cKDTree
board, rj, nsign = sys.argv[1], sys.argv[2], int(sys.argv[3]); HV = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else set()
import os
PJ = f"kit_v18/{board}/pads.json" if os.path.exists(f"kit_v18/{board}/pads.json") else f"kit_v6/{board}/pads.json"
PD = json.load(open(PJ)); P = PD["pads"]
for _i, _p in enumerate(P):
    if not _p.get("net"): _p["net"] = f"~NC{_i}"
r = json.load(open(rj)); R = r["R"]; routing = r["layers"]; planes = r["planes"]; STEP = 0.1
def seg_samples(p):
    out = []
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(math.dist(a, b) / STEP)); out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1)]
    return out or [tuple(p[0])]
def pad_samples(p):
    s = []; w, h = p["w"], p["h"]
    if p.get("shape") == "circle":
        for x in np.arange(-w / 2, w / 2 + 1e-9, STEP):
            for y in np.arange(-w / 2, w / 2 + 1e-9, STEP):
                if x * x + y * y <= (w / 2) ** 2: s.append((p["x"] + x, p["y"] + y))
    else:
        for x in np.arange(-w / 2, w / 2 + 1e-9, STEP):
            for y in np.arange(-h / 2, h / 2 + 1e-9, STEP): s.append((p["x"] + x, p["y"] + y))
    return s or [(p["x"], p["y"])]
viol = []; minrow = {}; opens = []; allx = []
# clearance: exact shapes (2026-10-28). The earlier point raster (0.1 mm dots of radius 0.05 placed up to the pad edge) grew every pad by 0.05 mm per side, so two
# 0.5 mm-pitch pads at the 0.2 mm rule read 0.1 mm, and a 0.06 mm slack hid real gaps of 0.14-0.2 mm; now pads are their rectangles / circles, tracks their
# round-capped buffers, vias 0.6 mm discs, and a gap below the rule by more than 1 um is a violation (stricter than before, never looser).
from shapely.geometry import LineString, Point, box as _box
from shapely.strtree import STRtree
def pad_geom(p):
    if p.get("shape") == "circle": return Point(p["x"], p["y"]).buffer(p["w"] / 2, 32)
    return _box(p["x"] - p["w"] / 2, p["y"] - p["h"] / 2, p["x"] + p["w"] / 2, p["y"] + p["h"] / 2)
for lay in routing:
    G = []; net = []; X = []
    for tr in r["tracks"]:
        if tr["layer"] != lay: continue
        G.append(LineString(tr["pts"]).buffer(tr["width"] / 2, 16) if len(tr["pts"]) > 1 else Point(tr["pts"][0]).buffer(tr["width"] / 2, 16)); net.append(tr["net"]); X += seg_samples(tr["pts"])
    for v in r["vias"]: G.append(Point(v[0], v[1]).buffer(0.3, 32)); net.append(v[2]); X.append((v[0], v[1]))
    for p in P:
        if p["tht"] or lay == "F.Cu": G.append(pad_geom(p)); net.append(p["net"]); X += pad_samples(p)
    T = STRtree(G); worst = {}; gmin = None
    for i, g in enumerate(G):
        for j in T.query(g, predicate="dwithin", distance=1.0 + 0.01):
            j = int(j)
            if j <= i or net[i] == net[j]: continue
            gap = float(g.distance(G[j])); gmin = gap if gmin is None or gap < gmin else gmin
            req = 1.0 if (net[i] in HV or net[j] in HV) else 0.2
            key = (net[i], net[j]) if net[i] < net[j] else (net[j], net[i])
            if gap < req - 1e-3 and (key not in worst or gap < worst[key][0]):
                c = g.centroid if gap > 0 else g.intersection(G[j]).centroid
                worst[key] = (gap, req, lay, (round(c.x, 1), round(c.y, 1)))
    for k, v in worst.items(): viol.append((k, round(v[0], 3), v[1], v[2], v[3]))
    allx.append(np.array(X)); minrow[lay] = round(gmin, 3) if gmin is not None else None
# connectivity (union-find over tracks, vias, pads)
nodes = []; par = {}
def f(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
def u(a, b): par[f(a)] = f(b)
items = {}
for i, tr in enumerate(r["tracks"]): items[("t", i)] = (tr["net"], tr["layer"], np.array(seg_samples(tr["pts"])), tr["width"] / 2)
for i, v in enumerate(r["vias"]): items[("v", i)] = (v[2], None, np.array([[v[0], v[1]]]), 0.3)
for i, p in enumerate(P): items[("p", i)] = (p["net"], None if p["tht"] else "F.Cu", np.array(pad_samples(p)), STEP / 2)
for k in items: par[k] = k
bynet = {}
for k, it in items.items(): bynet.setdefault(it[0], []).append(k)
for net, ks in bynet.items():
    if net in planes:
        pl = [k for k in ks if k[0] == "v" or (k[0] == "p" and items[k][1] is None)]
        for k in pl[1:]: u(pl[0], k)
    trees = {k: cKDTree(items[k][2]) for k in ks}
    for a in range(len(ks)):
        for b in range(a + 1, len(ks)):
            ka, kb = ks[a], ks[b]; la, lb = items[ka][1], items[kb][1]
            if la is not None and lb is not None and la != lb: continue          # different layers: only vias/through pads join layers
            d, _ = trees[ka].query(items[kb][2], k=1); 
            if d.min() <= items[ka][3] + items[kb][3] + 0.02: u(ka, kb)
for net, ks in bynet.items():
    padk = [k for k in ks if k[0] == "p"]
    if len(padk) > 1 and len({f(k) for k in padk}) > 1:
        comps = {}
        for k in padk: comps.setdefault(f(k), []).append(f"{P[k[1]]['ref']}.{P[k[1]]['num']}")
        small = sorted(comps.values(), key=len)[0]; opens.append((net, len(comps), small[:4]))
# edge and notch
edge = []; bad = 0
for X, in [(x,) for x in allx]:
    if PD.get('rect'): bad += int(np.sum((np.abs(X[:, 0]) > PD['rect'][0] / 2 - 0.35) | (np.abs(X[:, 1]) > PD['rect'][1] / 2 - 0.35)))     # rectangular outline (PB1R)
    else: rr = np.hypot(X[:, 0], X[:, 1]); bad += int(np.sum(rr > R - 0.35))
notch = 0 if (nsign == 0 or PD.get('rect')) else sum(int(np.sum((np.abs(X[:, 0]) < 8.1) & (nsign * X[:, 1] > 35.9))) for X in allx)
print(f"{board}: clearance violations (different nets, gap below class minus 0.06 sampling tolerance): {len(viol)}; open nets: {len(opens)}; copper samples within 0.35 mm of the edge: {bad}; copper samples in the notch keep-out: {notch}")
print("  minimum gap per routed layer (mm):", minrow)
for v in viol[:8]: print("  VIOLATION", v)
for o in opens[:8]: print("  OPEN", o)
json.dump(dict(board=board, clearance_violations=len(viol), open_nets=len(opens), edge_samples=bad, notch_samples=notch, min_gap_by_layer=minrow, violations=[list(map(str, v)) for v in viol[:50]], opens=[list(map(str, o)) for o in opens[:50]]), open(f"kit_v22/drc_{board}.json", "w"), indent=1)
