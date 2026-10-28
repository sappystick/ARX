#!/usr/bin/env python3
"""Local repair of a routed board (2026-10-28): finish the last open nets without re-routing the whole board.
Starts from the saved layout (kit_v20/route_BOARD.json, the best round of route_run.py), freezes every net outside a window around the failed
nets' pads, rips up only the signal nets inside the window and re-routes them in several orders with the board's own router settings
(route_run.py passes its Router factory, so the settings are never copied). Each attempt takes seconds instead of a full-board run.
Rules are the router's own and are not touched; the result is written only when it routes more nets, and the caller then runs
route_fix.py and the exact drc.py and keeps it only with 0 clearance violations (scripts in route_run.py REPAIR mode).
Called by route_run.py with REPAIR=1 in the environment: python3 route_run.py AU1 (REPAIR=1 [REPAIR_WIN=2.0] [REPAIR_S=240])"""
import json, math, os, time, itertools, shutil
import numpy as np
import router as RT

def _paint(R, tracks, vias):
    """put frozen copper into a fresh router: the same occupancy mark() would have written (thin tracks centre-only in the fine zone)"""
    li = {L: i for i, L in enumerate(R.layers)}
    for t in tracks:
        if t["layer"] not in li: continue
        l = li[t["layer"]]; hw = t["width"] / 2; thin = hw <= 0.1 + 1e-9; nid = R.nid[t["net"]]
        for a, b in zip(t["pts"][:-1], t["pts"][1:]) if len(t["pts"]) > 1 else [(t["pts"][0], t["pts"][0])]:
            n = max(1, int(math.dist(a, b) / (RT.GR / 4)))
            for k in range(n + 1):
                x = a[0] + (b[0] - a[0]) * k / n; y = a[1] + (b[1] - a[1]) * k / n; r, c = R.cell(x, y)
                if not (0 <= r < R.N and 0 <= c < R.N): continue
                hwc = 0 if (thin and R.finez[r, c]) else max(0, int(round(hw / RT.GR)))
                m = RT.disk(hwc) if hwc > 0 else np.ones((1, 1), bool)
                r0 = max(0, r - hwc); r1 = min(R.N, r + hwc + 1); c0 = max(0, c - hwc); c1 = min(R.N, c + hwc + 1)
                sub = m[(r0 - (r - hwc)):(r1 - (r - hwc)), (c0 - (c - hwc)):(c1 - (c - hwc))]; reg = R.own[l][r0:r1, c0:c1]; reg[sub & (reg == 0)] = nid
        R.tracks.append(t)
    vr = int(math.ceil(R.via_pad / 2 / RT.GR))
    for v in vias:
        r, c = R.cell(v[0], v[1]); nid = R.nid[v[2]]; m = RT.disk(vr)
        for l in range(R.nl):
            r0 = max(0, r - vr); r1 = min(R.N, r + vr + 1); c0 = max(0, c - vr); c1 = min(R.N, c + vr + 1)
            sub = m[(r0 - (r - vr)):(r1 - (r - vr)), (c0 - (c - vr)):(c1 - (c - vr))]; reg = R.own[l][r0:r1, c0:c1]; reg[sub & (reg == 0)] = nid
        R.vias.append(tuple(v))

def repair(board, mk, front=(), win=None, budget=None):
    win = float(os.environ.get("REPAIR_WIN", win or 2.0)); budget = float(os.environ.get("REPAIR_S", budget or 240.0)); t0 = time.time()
    path = f"kit_v20/route_{board}.json"; L = json.load(open(path)); st = L["stats"]
    failed = [f[0] for f in st["failures"] if f[1] == "net"]
    if not failed: print(board, "repair: nothing open"); return st
    R0 = mk(); planes = set(R0.planes)
    bynet = {}
    for k, p in enumerate(R0.pads):
        if p["net"]: bynet.setdefault(p["net"], []).append(k)
    xs = [R0.pads[k]["x"] for n in failed for k in bynet[n]]; ys = [R0.pads[k]["y"] for n in failed for k in bynet[n]]
    def near(t, w):
        return any(min(xs) - w <= q[0] <= max(xs) + w and min(ys) - w <= q[1] <= max(ys) + w for q in t["pts"])
    # nets to rip: the failed ones plus every signal net with copper inside the window around the failed nets' pads (shrink the window if it grabs too much)
    for w in (win, win * 0.75, win * 0.5):
        rip = set(failed) | {t["net"] for t in L["tracks"] if t["net"] not in planes and near(t, w)}
        rip = {n for n in rip if n in bynet and len(bynet[n]) >= 2 and not n.endswith("_NC")}
        if len(rip) <= 10: break
    keep_t = [t for t in L["tracks"] if t["net"] not in rip]; keep_v = [v for v in L["vias"] if v[2] not in rip]
    others = sorted(rip - set(failed)); base = [n for n in front if n in rip] + [n for n in failed if n not in front] + []
    orders = []
    for perm in itertools.permutations(others) if len(others) <= 5 else [tuple(others), tuple(reversed(others))]:
        for head in (base, base[::-1]):
            o = list(dict.fromkeys(list(head) + list(perm)))
            if o not in orders: orders.append(o)
    print(f"{board} repair: open {failed}; window {w:.2f} mm; re-routing {len(rip)} nets {sorted(rip)} in up to {len(orders)} orders; frozen {len(keep_t)} tracks / {len(keep_v)} vias", flush=True)
    best = None
    for i, o in enumerate(orders):
        if time.time() - t0 > budget: print(f"{board} repair: time budget {budget:.0f} s reached after {i} orders", flush=True); break
        R = mk(); R.tracks = []; R.vias = []; _paint(R, keep_t, keep_v)
        bad = [n for n in o if not R.route_net(n, bynet[n])]
        print(f"  order {i}: open {bad}", flush=True)
        if best is None or len(bad) < len(best[0]): best = (bad, R)
        if not bad: break
    bad, R = best
    if len(bad) >= len(failed): print(f"{board} repair: no improvement ({len(bad)} open); layout unchanged"); return st
    shutil.copy(path, f"kit_v20/route_{board}_prerepair.json")
    fails = [f for f in st["failures"] if f[1] != "net"] + [(n, "net", len(bynet[n])) for n in bad]
    st2 = dict(st, nets_routed=st["nets_to_route"] - len(bad), failures=fails, tracks=len(R.tracks), vias=len(R.vias), repaired=sorted(rip))
    json.dump(dict(stats=st2, tracks=R.tracks, vias=[list(v) for v in R.vias], layers=L["layers"], planes=L["planes"], R=L["R"]), open(path, "w"))
    print(f"{board} repair: {len(failed)} -> {len(bad)} open in {time.time() - t0:.0f} s (previous layout kept as route_{board}_prerepair.json)")
    return st2
