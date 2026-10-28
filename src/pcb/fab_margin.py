#!/usr/bin/python3
"""Manufacturing margin audit (FINAL_INTEGRATION_PLAN P1): how far above the fabrication floor every board sits, not only whether it passes.
Reads each released .kicad_pcb with pcbnew (KiCad's own copper geometry: tracks, arcs, pads, vias, filled zones, via TransformShapeToPolygon / filled polys),
and measures with shapely, per copper layer:
  min copper gap between different nets (HV nets against their 1.0 mm rule), with every place closer than floor + 0.02 mm and floor + 0.05 mm listed (x, y);
  copper to board edge (Edge.Cuts outline), drill to drill (edge to edge), drill to other-net copper, via and component-PTH annular ring, min track width.
Floors: src/pcb/dru_gen.py GEN / BOARDS (docs/design/FAB_RULES_VERIFIED.md). The router itself designs to 0.2 mm except on AB1A/AB1B (0.16 floor, Step 12).
This is an independent measurement next to KiCad DRC and drc.py: it does not replace a fabricator's DRC (U-FAB-DRC).
usage (repo root, /usr/bin/python3 for pcbnew): src/pcb/fab_margin.py [OUT.json]"""
import sys, os, json, math, itertools
import pcbnew
from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from shapely.ops import unary_union, nearest_points, polygonize
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import dru_gen as DG
BOARDS = {"CB1D": "data/kicad/PF233-CB1D_routed.kicad_pcb", "LB1": "data/kicad/PF233-LB1_routed.kicad_pcb", "PB1R": "data/kicad/PF233-PB1R_routed.kicad_pcb",
          "PM2": "data/kicad/PF233-PM2_routed.kicad_pcb", "HB2": "data/kicad/PF233-HB2_routed.kicad_pcb", "AU1": "data/kicad/PF233-AU1_routed.kicad_pcb", "TXJ1": "data/kicad/TXJ1.kicad_pcb", "HTA": "data/kicad/PF233-HTA.kicad_pcb",
          "SB1R-QA": "data/kicad/SB1R-QA.kicad_pcb", "SB1R-QB": "data/kicad/SB1R-QB.kicad_pcb", "AB1A": "data/kicad/PF233-AB1A.kicad_pcb", "AB1B": "data/kicad/PF233-AB1B.kicad_pcb"}
MM = 1e-6; ERR = int(0.002 / MM)                                                    # nm -> mm; 2 um arc approximation error
TIGHT, NEAR = 0.02, 0.05

def sps_to_shapely(sps):
    polys = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i); ext = [(o.CPoint(k).x * MM, -o.CPoint(k).y * MM) for k in range(o.PointCount())]
        holes = []
        for h in range(sps.HoleCount(i)):
            hh = sps.Hole(i, h); holes.append([(hh.CPoint(k).x * MM, -hh.CPoint(k).y * MM) for k in range(hh.PointCount())])
        if len(ext) >= 3:
            p = Polygon(ext, holes)
            polys.append(p if p.is_valid else p.buffer(0))
    return unary_union(polys) if polys else None

def item_poly(it, layer):
    s = pcbnew.SHAPE_POLY_SET(); it.TransformShapeToPolygon(s, layer, 0, ERR, pcbnew.ERROR_INSIDE); return sps_to_shapely(s)

def board_outline(b):
    segs = []
    for d in b.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts: continue
        s = pcbnew.SHAPE_POLY_SET(); d.TransformShapeToPolygon(s, pcbnew.Edge_Cuts, 0, ERR, pcbnew.ERROR_INSIDE); g = sps_to_shapely(s)
        if g is not None: segs.append(g)
    ol = pcbnew.SHAPE_POLY_SET()
    if b.GetBoardPolygonOutlines(ol): g = sps_to_shapely(ol)
    else: g = None
    return g

def audit(name, path):
    b = pcbnew.LoadBoard(path); cfg = DG.BOARDS[name]; gen = DG.GEN; hv = set(cfg["hv"])
    via_ring_floor = cfg.get("via_annular", gen["annular"]); via_drill_floor = cfg.get("via_drill", gen["drill"])
    layers = [l for l in b.GetEnabledLayers().CuStack()]
    out = dict(board=name, file=path, layers=[b.GetLayerName(l) for l in layers], floors=dict(clearance=gen["clearance"], hv=cfg["hv_mm"], edge=gen["edge"], hole_to_hole=gen["hole_to_hole"],
               hole_clearance=gen["hole_clearance"], via_annular=via_ring_floor, pth_annular=gen["pth_annular"], track=gen["track"]), hv_nets=sorted(hv))
    netname = lambda it: it.GetNetname() or f"<nonet:{it.m_Uuid.AsString()}>"          # unconnected copper: one pseudo-net per item (stable KiCad UUID)
    per_layer = {}; allnet = {}
    items = list(b.GetTracks()) + [p for f in b.GetFootprints() for p in f.Pads()]
    for L in layers:
        geo = {}
        for it in items:
            if not it.IsOnLayer(L): continue
            if isinstance(it, pcbnew.PAD) and not it.IsOnCopperLayer(): continue
            g = item_poly(it, L)
            if g is not None and not g.is_empty: geo.setdefault(netname(it), []).append(g)
        for z in b.Zones():
            if z.GetIsRuleArea() or not z.IsOnLayer(L): continue
            g = sps_to_shapely(z.GetFilledPolysList(L))
            if g is not None and not g.is_empty: geo.setdefault(z.GetNetname() or f"<nonet:{z.m_Uuid.AsString()}>", []).append(g)
        per_layer[b.GetLayerName(L)] = {n: unary_union(v) for n, v in geo.items()}
        for n, g in per_layer[b.GetLayerName(L)].items(): allnet.setdefault(n, []).append(g)
    allnet = {n: unary_union(v) for n, v in allnet.items()}
    # 1. copper gaps per layer
    gaps = []; mins = {}
    for ln, geo in per_layer.items():
        names = list(geo); tree = STRtree([geo[n] for n in names]); worst = None
        for i, n in enumerate(names):
            for j in tree.query(geo[n].buffer(max(cfg["hv_mm"], gen["clearance"]) + NEAR + 0.01)):
                if j <= i: continue
                m = names[j]; d = geo[n].distance(geo[m]); fl = cfg["hv_mm"] if (n in hv or m in hv) else gen["clearance"]
                if worst is None or d - fl < worst[0]: worst = (d - fl, d, fl, n, m)
                if d < fl + NEAR:
                    p, q = nearest_points(geo[n], geo[m]); gaps.append(dict(layer=ln, a=n, b=m, gap_mm=round(d, 4), floor_mm=fl, margin_mm=round(d - fl, 4), at=[round((p.x + q.x) / 2, 2), round((p.y + q.y) / 2, 2)], tight=d < fl + TIGHT))
        if worst: mins[ln] = dict(gap_mm=round(worst[1], 4), floor_mm=worst[2], margin_mm=round(worst[0], 4), nets=[worst[3], worst[4]])
    out["copper_min_by_layer"] = mins
    out["near_floor"] = sorted(gaps, key=lambda g: g["margin_mm"]); out["tight_count"] = sum(g["tight"] for g in gaps); out["near_count"] = len(gaps)
    hvg = [dict(layer=ln, a=a, b=c, gap_mm=round(per_layer[ln][a].distance(per_layer[ln][c]), 4)) for ln in per_layer for a in per_layer[ln] if a in hv for c in per_layer[ln] if c != a]
    out["hv_min"] = min(hvg, key=lambda g: g["gap_mm"]) if hvg else None
    # 2. copper to board edge
    ol = board_outline(b); out["edge"] = None
    if ol is not None:
        bd = ol.boundary; e = min(((bd.distance(g), n) for n, g in allnet.items()), default=None)
        if e: out["edge"] = dict(min_mm=round(e[0], 4), net=e[1], margin_mm=round(e[0] - gen["edge"], 4))
    # 3. holes: drill to drill, drill to other-net copper, annular rings
    holes = []
    for it in b.GetTracks():
        if isinstance(it, pcbnew.PCB_VIA):
            c = it.GetPosition(); holes.append(dict(kind="via", net=netname(it), x=c.x * MM, y=-c.y * MM, r=it.GetDrillValue() * MM / 2, ring=(it.GetWidth(pcbnew.F_Cu) - it.GetDrillValue()) * MM / 2))
    for f in b.GetFootprints():
        for p in f.Pads():
            ds = p.GetDrillSize()
            if ds.x <= 0: continue
            c = p.GetPosition(); sz = p.GetSize(pcbnew.F_Cu) if hasattr(p, "GetSize") else p.GetSize()
            npth = p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            holes.append(dict(kind="npth" if npth else "pth", net=netname(p), ref=f.GetReference() + "." + p.GetNumber(), x=c.x * MM, y=-c.y * MM, r=min(ds.x, ds.y) * MM / 2,
                              ring=None if npth else (min(sz.x, sz.y) - max(ds.x, ds.y)) * MM / 2))
    hh = min(((math.hypot(a["x"] - c["x"], a["y"] - c["y"]) - a["r"] - c["r"], a, c) for a, c in itertools.combinations(holes, 2)), default=None, key=lambda t: t[0])
    out["hole_to_hole"] = dict(min_mm=round(hh[0], 4), margin_mm=round(hh[0] - gen["hole_to_hole"], 4), at=[round(hh[1]["x"], 2), round(hh[1]["y"], 2)]) if hh else None
    hc = None
    for h in holes:
        circ = Point(h["x"], h["y"]).buffer(h["r"], 32)
        for n, g in allnet.items():
            if n == h["net"]: continue
            d = circ.distance(g)
            if hc is None or d < hc[0]: hc = (d, h, n)
    out["hole_to_copper"] = dict(min_mm=round(hc[0], 4), margin_mm=round(hc[0] - gen["hole_clearance"], 4), hole=hc[1].get("ref", "via"), other_net=hc[2], at=[round(hc[1]["x"], 2), round(hc[1]["y"], 2)]) if hc else None
    vr = [h["ring"] for h in holes if h["kind"] == "via"]; pr = [h for h in holes if h["kind"] == "pth"]
    out["via_annular"] = dict(min_mm=round(min(vr), 4), margin_mm=round(min(vr) - via_ring_floor, 4), n=len(vr)) if vr else None
    if pr:
        w = min(pr, key=lambda h: h["ring"]); out["pth_annular"] = dict(min_mm=round(w["ring"], 4), margin_mm=round(w["ring"] - gen["pth_annular"], 4), pad=w["ref"], n=len(pr))
    tw = [t.GetWidth() * MM for t in b.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    out["track_min_mm"] = round(min(tw), 4) if tw else None
    # verdict: every measured minimum at or above its floor (the gate); margins are the information
    named = [(f"copper gap {k}", m["margin_mm"]) for k, m in mins.items()] + [(k, out[k]["margin_mm"]) for k in ("edge", "hole_to_hole", "hole_to_copper", "via_annular", "pth_annular") if out.get(k)]
    ms = [m for _, m in named]; out["margins"] = {k: v for k, v in named}
    out["min_margin_mm"] = round(min(ms), 4) if ms else None; out["min_margin_of"] = min(named, key=lambda t: t[1])[0] if named else None; out["pass"] = all(m >= -1e-3 for m in ms) and (out["track_min_mm"] is None or out["track_min_mm"] >= gen["track"] - 1e-3)
    if out["hv_min"]: out["pass"] = out["pass"] and out["hv_min"]["gap_mm"] >= cfg["hv_mm"] - 1e-3
    # the same minimums against the vendors' published Standard numbers (FAB_RULES_VERIFIED.md): what is left before a fabricator would reject
    V = dict(clearance=0.152, via_annular=0.127, pth_annular=0.178, edge=0.381, hole_to_hole=0.381, hole_to_copper=0.254)
    cu = min((m["gap_mm"] for m in mins.values()), default=None)
    out["vendor_margins"] = {k: round(v - V[k], 4) for k, v in (("clearance", cu), ("via_annular", out["via_annular"] and out["via_annular"]["min_mm"]), ("pth_annular", out.get("pth_annular") and out["pth_annular"]["min_mm"]),
                             ("edge", out["edge"] and out["edge"]["min_mm"]), ("hole_to_hole", out["hole_to_hole"] and out["hole_to_hole"]["min_mm"]), ("hole_to_copper", out["hole_to_copper"] and out["hole_to_copper"]["min_mm"])) if v is not None}
    return out

if __name__ == "__main__":
    res = {}
    for n, p in BOARDS.items():
        r = audit(n, p); res[n] = r
        print(f"{n:8} pass {r['pass']}  min margin {r['min_margin_mm']} mm ({r['min_margin_of']})  copper {min((m['margin_mm'] for m in r['copper_min_by_layer'].values()), default=None)}  tight {r['tight_count']}  near {r['near_count']}  edge {r['edge'] and r['edge']['min_mm']}  "
              f"h2h {r['hole_to_hole'] and r['hole_to_hole']['min_mm']}  h2cu {r['hole_to_copper'] and r['hole_to_copper']['min_mm']}  hv {r['hv_min'] and r['hv_min']['gap_mm']}", flush=True)
    json.dump(dict(note="MODELED/tool-measured margins above the fabrication floor (src/pcb/fab_margin.py); not a fabricator DRC", boards=res), open(sys.argv[1] if len(sys.argv) > 1 else "data/results/fab_margin_audit.json", "w"), indent=1)
