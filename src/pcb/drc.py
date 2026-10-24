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
for lay in routing:
    X = []; rad = []; net = []; kind = []
    for tr in r["tracks"]:
        if tr["layer"] != lay: continue
        sm = seg_samples(tr["pts"]); X += sm; rad += [tr["width"] / 2] * len(sm); net += [tr["net"]] * len(sm); kind += ["trk"] * len(sm)
    for v in r["vias"]: X.append((v[0], v[1])); rad.append(0.3); net.append(v[2]); kind.append("via")
    for p in P:
        if p["tht"] or lay == "F.Cu":
            sm = pad_samples(p); X += sm; rad += [STEP / 2] * len(sm); net += [p["net"]] * len(sm); kind += ["pad"] * len(sm)
    X = np.array(X); rad = np.array(rad); T = cKDTree(X); worst = {}
    for a, b in T.query_pairs(1.6 + 0.2):
        if net[a] == net[b]: continue
        gap = float(np.linalg.norm(X[a] - X[b]) - rad[a] - rad[b]); req = 1.0 if (net[a] in HV or net[b] in HV) else 0.2
        key = (net[a], net[b]) if net[a] < net[b] else (net[b], net[a])
        if gap < req - 0.06 and (key not in worst or gap < worst[key][0]): worst[key] = (gap, req, lay, tuple(np.round(X[a], 1)))
    for k, v in worst.items(): viol.append((k, round(v[0], 3), v[1], v[2], v[3]))
    allx.append(X)
    gaps = [np.linalg.norm(X[a] - X[b]) - rad[a] - rad[b] for a, b in T.query_pairs(0.9) if net[a] != net[b]]
    minrow[lay] = round(min(gaps), 3) if gaps else None
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
