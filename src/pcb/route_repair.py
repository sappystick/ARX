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
    fstub = [f[2] for f in st["failures"] if f[1] == "stub"]                 # plane pads whose stub / via failed (they are opens too: 2026-10-28)
    if not failed and not fstub: print(board, "repair: nothing open"); return st
    R0 = mk(); planes = set(R0.planes); front = list(front)
    bynet = {}
    for k, p in enumerate(R0.pads):
        if p["net"]: bynet.setdefault(p["net"], []).append(k)
    # window = discs around each pad of the failed nets (a bounding box of a long net covered half of AU1 and took 21 nets): the copper crowding its ends
    pidx = {R0.pads[k]["ref"] + "." + R0.pads[k]["num"]: k for k in range(len(R0.pads))}
    stub_k = [pidx[x] for x in fstub if x in pidx]
    fp = [(R0.pads[k]["x"], R0.pads[k]["y"]) for n in failed for k in bynet[n]] + [(R0.pads[k]["x"], R0.pads[k]["y"]) for k in stub_k]
    def near(t, w):
        pts = t["pts"]; segs = list(zip(pts[:-1], pts[1:])) or [(pts[0], pts[0])]
        def dseg(p, a, b):
            ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1e-12
            u = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2)); return math.hypot(ax + u * dx - p[0], ay + u * dy - p[1])
        return any(dseg(p, a, b) <= w for p in fp for a, b in segs)
    # nets to rip: the failed ones plus every signal net with copper inside the window around the failed nets' pads (shrink the window if it grabs too much)
    for w in (win, win * 0.75, win * 0.5, win * 0.35):
        rip = set(failed) | {t["net"] for t in L["tracks"] if t["net"] not in planes and near(t, w)}
        rip = {n for n in rip if n in bynet and len(bynet[n]) >= 2 and not n.endswith("_NC")}
        if len(rip) <= 8: break
    keep_t = [t for t in L["tracks"] if t["net"] not in rip]; keep_v = [v for v in L["vias"] if v[2] not in rip]
    others = sorted(rip - set(failed)); base = [n for n in front if n in rip] + [n for n in failed if n not in front] + []
    orders = []
    for perm in itertools.permutations(others) if len(others) <= 5 else [tuple(others), tuple(reversed(others))]:
        for head in (base, base[::-1]):
            o = list(dict.fromkeys(list(head) + list(perm)))
            if o not in orders: orders.append(o)
    print(f"{board} repair: open {failed} stubs {fstub}; window {w:.2f} mm; re-routing {len(rip)} nets {sorted(rip)} in up to {len(orders)} orders; frozen {len(keep_t)} tracks / {len(keep_v)} vias", flush=True)
    best = None
    for i, o in enumerate(orders):
        if time.time() - t0 > budget: print(f"{board} repair: time budget {budget:.0f} s reached after {i} orders", flush=True); break
        R = mk(); R.tracks = []; R.vias = []; _paint(R, keep_t, keep_v)
        sbad = [R.pads[k]["ref"] + "." + R.pads[k]["num"] for k in stub_k if not R.plane_stub(R.pads[k]["net"], k)]     # failed stubs first: a pad, then the nets around it
        bad = [n for n in o if not R.route_net(n, bynet[n])]
        print(f"  order {i}: open {bad} stubs {sbad}", flush=True)
        if best is None or len(bad) + len(sbad) < len(best[0]) + len(best[2]): best = (bad, R, sbad)
        if not bad and not sbad: break
    if best is None: print(f"{board} repair: no order tried; layout unchanged"); return st
    bad, R, sbad = best
    if len(bad) + len(sbad) >= len(failed) + len(fstub): print(f"{board} repair: no improvement ({len(bad)} open, {len(sbad)} stubs); layout unchanged"); return st
    shutil.copy(path, f"kit_v20/route_{board}_prerepair.json")
    fails = [f for f in st["failures"] if f[1] not in ("net", "stub")] + [(R0.pads[pidx[x]]["net"], "stub", x) for x in sbad] + [(n, "net", len(bynet[n])) for n in bad]
    st2 = dict(st, nets_routed=st["nets_to_route"] - len(bad), failures=fails, tracks=len(R.tracks), vias=len(R.vias), repaired=sorted(rip))
    write_layout(board, st2, R.tracks, R.vias, L["layers"], L["planes"], L["R"], PADS)
    print(f"{board} repair: {len(failed)} -> {len(bad)} open nets, {len(fstub)} -> {len(sbad)} failed stubs in {time.time() - t0:.0f} s (previous layout kept as route_{board}_prerepair.json)")
    return st2


# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# layouts with their base (2026-10-28): every finished layout is written with the pad file it was routed against and a fingerprint of the router code,
# so the next run can re-route only what changed (incremental) instead of the whole board
PADS = None                      # pad file of the board being routed (set by route_run.py)
CODE = None                      # fingerprint of what decides the copper (set by route_run.py): router.py, the board's router factory, the grid
def code_hash():
    import hashlib
    return CODE or hashlib.sha1(open("router.py", "rb").read()).hexdigest()

def write_layout(board, st, tracks, vias, layers, planes, Rr, pads_path):
    st = dict(st); st["failures_net"] = len([f for f in st.get("failures", []) if f[1] == "net"])
    json.dump(dict(stats=st, tracks=tracks, vias=[list(v) for v in vias], layers=layers, planes=planes, R=Rr), open(f"kit_v20/route_{board}.json", "w"))
    pads_path = pads_path or PADS
    if pads_path: json.dump(dict(code=code_hash(), pads_file=pads_path, pads=json.load(open(pads_path))), open(f"kit_v20/route_{board}_base.json", "w"))
    return st

def _key(p): return (p["ref"], str(p["num"]))
def _sig(p): return (round(p["x"], 4), round(p["y"], 4), round(p["w"], 4), round(p["h"], 4), p.get("net"), bool(p["tht"]), p.get("shape"), round(p.get("drill", 0) or 0, 3))

def _geom(t):
    from shapely.geometry import LineString, Point
    return LineString(t["pts"]).buffer(t["width"] / 2, 16) if len(t["pts"]) > 1 else Point(t["pts"][0]).buffer(t["width"] / 2, 16)
def _pgeom(p):
    from shapely.geometry import Point, box
    return Point(p["x"], p["y"]).buffer(p["w"] / 2, 32) if p.get("shape") == "circle" else box(p["x"] - p["w"] / 2, p["y"] - p["h"] / 2, p["x"] + p["w"] / 2, p["y"] + p["h"] / 2)

def incremental(board, mk, pads_path, code=None, max_frac=0.35):
    """re-route only what changed since the saved layout. Returns the stats when done (failures_net 0), a dict with failures_net > 0 when the
    incremental result is not clean (the caller then routes the full board), or None when no incremental re-route applies (no base, router code
    changed, outline changed, or more than max_frac of the pads changed)."""
    global PADS; PADS = pads_path; t0 = time.time()
    lay, basef = f"kit_v20/route_{board}.json", f"kit_v20/route_{board}_base.json"
    if not (os.path.exists(lay) and os.path.exists(basef)): print(board, "incremental: no saved layout with a base: full route"); return None
    base = json.load(open(basef)); new = json.load(open(pads_path)); L = json.load(open(lay))
    if base["code"] != (code or code_hash()): print(board, "incremental: router code / settings changed: full route"); return None
    if base["pads"].get("R") != new.get("R") or base["pads"].get("rect") != new.get("rect"): print(board, "incremental: board outline changed: full route"); return None
    old = {_key(p): p for p in base["pads"]["pads"]}; nw = {_key(p): p for p in new["pads"]}
    changed = {k for k in set(old) | set(nw) if k not in old or k not in nw or _sig(old[k]) != _sig(nw[k])}
    if not changed:
        if L["stats"].get("failures_net", 0) == 0 and not [f for f in L["stats"].get("failures", []) if f[1] == "net"]:
            print(board, "incremental: pads unchanged, saved layout complete: nothing to route"); return dict(L["stats"], failures_net=0)
        return None
    if len(changed) > max_frac * len(nw): print(board, f"incremental: {len(changed)} of {len(nw)} pads changed: full route"); return None
    R = mk(); planes = set(R.planes); hv = set(R.hv)
    clr = lambda a, b: (R.hv_clr if (a in hv or b in hv) else R.clr)
    bynet = {}
    for k, p in enumerate(R.pads):
        if p["net"]: bynet.setdefault(p["net"], []).append(k)
    sig_nets = {n for n, ks in bynet.items() if n not in planes and len(ks) >= 2 and not n.endswith("_NC")}
    aff = {p.get("net") for k in changed for p in (old.get(k), nw.get(k)) if p and p.get("net")} 
    rip_nets = {n for n in aff if n in sig_nets}
    newg = [(nw[k].get("net"), _pgeom(nw[k]), nw[k]["tht"]) for k in changed if k in nw]
    oldg = [(old[k].get("net"), _pgeom(old[k])) for k in changed if k in old]
    tracks = [t for t in L["tracks"] if t["net"] in R.nid]; vias = [v for v in L["vias"] if v[2] in R.nid]
    tg = [_geom(t) for t in tracks]
    from shapely.geometry import Point
    vg = [Point(v[0], v[1]).buffer(R.via_pad / 2, 32) for v in vias]
    while True:                                                    # rip until no kept copper collides with a changed pad (a ripped signal net goes whole)
        grow = False; drop_t = set(); drop_v = set()
        for i, t in enumerate(tracks):
            if t["net"] in rip_nets: drop_t.add(i); continue
            for (n, g, tht) in newg:
                if n != t["net"] and (tht or t["layer"] == "F.Cu") and tg[i].distance(g) < clr(n, t["net"]) - 1e-3:
                    if t["net"] in sig_nets: rip_nets.add(t["net"]); grow = True
                    drop_t.add(i)
            if t["net"] in planes:                                 # plane stubs of a changed plane pad (old position)
                for (n, g) in oldg:
                    if n == t["net"] and tg[i].distance(g) < 1e-3: drop_t.add(i)
        for j, v in enumerate(vias):
            if v[2] in rip_nets: drop_v.add(j); continue
            for (n, g, tht) in newg:
                if n != v[2] and vg[j].distance(g) < clr(n, v[2]) - 1e-3:
                    if v[2] in sig_nets: rip_nets.add(v[2]); grow = True
                    drop_v.add(j)
            if v[2] in planes and any(tracks[i]["net"] == v[2] and any(math.dist(q, v[:2]) < 1e-6 for q in (tracks[i]["pts"][0], tracks[i]["pts"][-1])) for i in drop_t): drop_v.add(j)
        if not grow: break
    keep_t = [t for i, t in enumerate(tracks) if i not in drop_t]; keep_v = [v for j, v in enumerate(vias) if j not in drop_v]
    R.tracks = []; R.vias = []; _paint(R, keep_t, keep_v)
    # plane pads (SMD) that are new / moved or lost their stub: stub them again
    kept_ends = {(round(q[0], 4), round(q[1], 4)) for t in keep_t for q in (t["pts"][0], t["pts"][-1])}
    restub = []
    for k, p in enumerate(R.pads):
        if p["net"] in planes and not p["tht"]:
            if _key(p) in changed or not any(abs(q[0] - p["x"]) <= p["w"] / 2 + 1e-3 and abs(q[1] - p["y"]) <= p["h"] / 2 + 1e-3 for q in kept_ends): restub.append(k)
    stub_fail = [(R.pads[k]["net"], "stub", R.pads[k]["ref"] + "." + R.pads[k]["num"]) for k in restub if not R.plane_stub(R.pads[k]["net"], k)]
    pri = list(getattr(R, "priority", []))
    order = sorted(rip_nets, key=lambda n: (0 if n in hv else 1, pri.index(n) if n in pri else len(pri), n))
    bad = [n for n in order if not R.route_net(n, bynet[n])]
    print(f"{board} incremental: {len(changed)} pads changed; re-routed {len(order)} nets {order[:12]}{' ...' if len(order) > 12 else ''}; "
          f"re-stubbed {len(restub)} plane pads; kept {len(keep_t)} of {len(tracks)} tracks; open {bad}; {time.time() - t0:.1f} s", flush=True)
    # exact clearance of everything new against all copper, and of the kept copper against the changed pads
    newcopper = [(t["net"], t["layer"], _geom(t)) for t in R.tracks[len(keep_t):]] + [(v[2], None, Point(v[0], v[1]).buffer(R.via_pad / 2, 32)) for v in R.vias[len(keep_v):]]
    allc = [(t["net"], t["layer"], _geom(t)) for t in R.tracks] + [(v[2], None, Point(v[0], v[1]).buffer(R.via_pad / 2, 32)) for v in R.vias] + \
           [(p["net"], None if p["tht"] else "F.Cu", _pgeom(p)) for p in R.pads if p.get("net")]
    viol = 0
    for (n, l, g) in newcopper + [(p["net"], None if p["tht"] else "F.Cu", _pgeom(p)) for p in R.pads if _key(p) in changed and p.get("net")]:
        for (n2, l2, g2) in allc:
            if n2 == n or (l and l2 and l != l2): continue
            if g.distance(g2) < clr(n, n2) - 1e-3: viol += 1; break
    if viol: print(f"{board} incremental: {viol} items under the clearance rule: full route instead"); return dict(failures_net=len(bad) or viol)
    nets_total = len(sig_nets)
    st = dict(finished=True, nets_to_route=nets_total, nets_routed=nets_total - len(bad), plane_nets=list(planes),
              failures=stub_fail + [(n, "net", len(bynet[n])) for n in bad], tracks=len(R.tracks), vias=len(R.vias), incremental=dict(changed_pads=len(changed), rerouted=order))
    st = write_layout(board, st, R.tracks, R.vias, L["layers"], L["planes"], L["R"], pads_path)
    if bad or stub_fail:                                           # a few nets or plane stubs open: local repair of this layout first
        st = repair(board, mk, pri, budget=120)
        st["failures_net"] = len([f for f in st.get("failures", []) if f[1] == "net"])
    return st

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
def _round(args):
    i, order = args
    import route_run_cfg as C                                     # the factory of the calling route_run (set before the fork)
    R = C.MK(); R.priority = list(order); st = R.run(budget=1e9, state=None)
    return i, st, R.tracks, R.vias, R.layers, R.planes, R.R

def parallel_rounds(board, mk, front, write, n=4):
    """full route of a board with several router orders at once (one process per core); deterministic orders: round 0 the learned front,
    round 1 the front reversed, rounds 2.. the front then the other nets in a seeded shuffle; the best (fewest open, then lowest round) is written"""
    import multiprocessing as mp, random, sys, types
    t0 = time.time(); R0 = mk(); rest = sorted({p["net"] for p in R0.pads if p["net"] and p["net"] not in R0.planes and p["net"] not in front})
    orders = [list(front), list(front)[::-1]]
    for i in range(2, n): r = list(rest); random.Random(i).shuffle(r); orders.append(list(front) + r)
    mod = types.ModuleType("route_run_cfg"); mod.MK = mk; sys.modules["route_run_cfg"] = mod
    res = []; deadline = t0 + float(os.environ.get("ROUND_BUDGET_S", 600))                  # step cap 900 s: stop waiting at 600 s and keep the best finished round
    pool = mp.get_context("fork").Pool(min(n, os.cpu_count() or 1))
    try:
        it = pool.imap_unordered(_round, list(enumerate(orders)))
        while len(res) < len(orders):
            left = deadline - time.time()
            if left <= 0: print(f"{board} parallel rounds: 600 s budget reached with {len(res)} of {len(orders)} rounds finished", flush=True); break
            try: res.append(it.next(timeout=left))
            except mp.TimeoutError: continue
    finally: pool.terminate(); pool.join()
    if not res: raise RuntimeError(f"{board}: no routing round finished inside the budget")
    for i, st, *_ in sorted(res): print(f"{board} round {i} routed {st['nets_routed']} of {st['nets_to_route']} failures {len(st['failures'])}", flush=True)
    i, st, tr, vi, la, pl, Rr = min(res, key=lambda r: (len(r[1]["failures"]), r[0]))
    st = write_layout(board, dict(st, round=i), tr, vi, la, pl, Rr, PADS)
    print(f"{board} parallel rounds: best round {i}, {st['failures_net']} nets open, {time.time() - t0:.0f} s wall for {len(orders)} rounds", flush=True)
    return st
