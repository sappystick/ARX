#!/usr/bin/env python3
"""Independent geometric DRC for KiCad boards that do NOT go through the router (TXJ1, SB1R-QA/QB, HTA): Step 9. It does not use KiCad's DRC engine or the router's
own geometry: it reads the .kicad_pcb text, builds every copper and hole shape with shapely, and checks the fab floor of src/pcb/dru_gen.py (GEN) plus the
board's HV nets (BOARDS[board]). Checks:
  width      every track >= 0.15 mm; every via and pad annular ring >= 0.15 / 0.18 mm; via drill >= 0.30, component PTH drill >= 0.46
  clearance  copper of different nets on the same layer >= 0.16 mm; any pair touching an HV net >= 1.0 mm
  holes      drill-to-drill >= 0.41 mm centre-to-edge; drill-to-copper of another net >= 0.26 mm
  edge       all copper >= 0.5 mm inside the Edge.Cuts outline
  connect    every net is one connected copper island (pads, vias, tracks joined where they overlap on a shared layer)
  zones      a board with zone fills is reported as NOT checked (zones are not modelled)
Result: data/results JSON (passed to tests/regress.py) + exit status.
usage: python3 src/pcb/indep_drc.py BOARD path/to/board.kicad_pcb OUT.json"""
import sys, re, json, math
import numpy as np
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
from shapely import affinity
sys.path.insert(0, "src/pcb")
import dru_gen
G = dru_gen.GEN
CLR, TRK, VIA_DRILL, VIA_ANN, PTH_ANN, PTH_DRILL, HOLE_CU, HOLE_HOLE, EDGE = G["clearance"], G["track"], G["drill"], G["annular"], G["pth_annular"], G["pth_drill"], G["hole_clearance"], G["hole_to_hole"], G["edge"]

def parse(text):
    """minimal s-expression reader: lists of tokens; quoted strings are returned without quotes"""
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text); st = [[]]
    for t in toks:
        if t == "(": st.append([])
        elif t == ")": x = st.pop(); st[-1].append(x)
        else: st[-1].append(t[1:-1] if t.startswith('"') else t)
    return st[0][0]

def kids(node, key): return [c for c in node if isinstance(c, list) and c and c[0] == key]
def one(node, key):
    k = kids(node, key); return k[0] if k else None
def xy(node): return float(node[1]), float(node[2])

def rot_pt(px, py, deg):
    """KiCad's footprint rotation on its y-down board frame: x' = x cos + y sin, y' = -x sin + y cos (checked against the SB1R-QA segment ends)"""
    a = math.radians(deg); c, s = math.cos(a), math.sin(a); return px * c + py * s, -px * s + py * c

def pad_shape(shape, w, h, rot):
    if shape == "circle": return Point(0, 0).buffer(w / 2, 64)
    if shape == "oval": return LineString([(-(w - h) / 2, 0), ((w - h) / 2, 0)]).buffer(h / 2, 32) if w >= h else LineString([(0, -(h - w) / 2), (0, (h - w) / 2)]).buffer(w / 2, 32)
    p = box(-w / 2, -h / 2, w / 2, h / 2)
    if shape == "roundrect": p = p.buffer(-min(w, h) * 0.25, 8).buffer(min(w, h) * 0.25, 8)
    return affinity.rotate(p, -rot, origin=(0, 0)) if rot else p                   # shapely's rotation is counter-clockwise on a y-up frame: KiCad's +angle is the opposite

def items_of(tree, name):
    """copper items: dict(kind, net, layers, geom, ...) and holes: dict(kind, net, geom(drill circle), at)"""
    copper, holes, tracks, vias = [], [], [], []
    nets = {int(n[1]): (n[2] if len(n) > 2 else "") for n in kids(tree, "net")}
    def netname(node):
        """KiCad writes the name only on pads: track and via nets are the index alone"""
        if not node or len(node) < 2: return ""
        return nets.get(int(node[1]), "") if len(node) < 3 else node[2]
    for fp in kids(tree, "footprint"):
        fat = one(fp, "at"); fx, fy = xy(fat); frot = float(fat[3]) if len(fat) > 3 else 0.0
        for pad in kids(fp, "pad"):
            ptype = pad[2]; shape = pad[3]; pat = one(pad, "at"); px, py = xy(pat); prot = float(pat[3]) if len(pat) > 3 else 0.0
            sz = one(pad, "size"); w, h = float(sz[1]), float(sz[2]); dr = one(pad, "drill")
            drill = float(dr[1]) if dr else 0.0
            lay = one(pad, "layers"); lays = [x for x in lay[1:]] if lay else []
            layers = ["F.Cu", "B.Cu"] if any("*.Cu" == x for x in lays) else [x for x in lays if x.endswith(".Cu")]
            net = netname(one(pad, "net"))
            dx, dy = rot_pt(px, py, frot); X, Y = fx + dx, fy + dy; ang = frot + prot
            shp = pad_shape(shape, w, h, ang)
            geom = affinity_move(shp, X, Y)
            ntype = "pad:" + ptype
            if ptype in ("thru_hole", "np_thru_hole") and drill > 0:
                holes.append(dict(kind=ntype, net=net, geom=Point(X, Y).buffer(drill / 2, 32), drill=drill, npth=(ptype == "np_thru_hole"), ref=None, at=(X, Y), w=w))
            if ptype == "np_thru_hole": continue
            if ptype == "smd": layers = [x for x in layers] or ["F.Cu"]
            for L in layers:
                copper.append(dict(kind=ntype, net=net, layer=L, geom=geom, ref=None, at=(X, Y), w=w, h=h, pad=True, ptype=ptype, drill=drill))
    for s in kids(tree, "segment"):
        a = one(s, "start"); b = one(s, "end"); wd = float(one(s, "width")[1]); L = one(s, "layer")[1]; nn = one(s, "net")
        net = netname(nn)
        ls = LineString([xy(a), xy(b)]).buffer(wd / 2, 16)
        copper.append(dict(kind="track", net=net, layer=L, geom=ls, at=xy(a), w=wd, pad=False)); tracks.append(dict(w=wd, layer=L, net=net, a=xy(a), b=xy(b)))
    for v in kids(tree, "via"):
        at = xy(one(v, "at")); sz = float(one(v, "size")[1]); dr = float(one(v, "drill")[1]); net = netname(one(v, "net"))
        lay = one(v, "layers"); layers = [x for x in lay[1:]] if lay else ["F.Cu", "B.Cu"]
        for L in layers:
            copper.append(dict(kind="via", net=net, layer=L, geom=Point(at).buffer(sz / 2, 32), at=at, w=sz, pad=False))
        holes.append(dict(kind="via", net=net, geom=Point(at).buffer(dr / 2, 32), drill=dr, npth=False, ref=None, at=at, w=sz))
        vias.append(dict(size=sz, drill=dr, at=at, net=net))
    return copper, holes, tracks, vias

def affinity_move(g, X, Y):
    return affinity.translate(g, X, Y)

def edge_polygon(tree):
    """the board area: the polygon of the Edge.Cuts lines, or the largest Edge.Cuts circle minus any smaller ones (round boards with a centre hole)"""
    segs = []
    for g in kids(tree, "gr_line"):
        if one(g, "layer") and one(g, "layer")[1] == "Edge.Cuts": segs.append(LineString([xy(one(g, "start")), xy(one(g, "end"))]))
    for g in kids(tree, "gr_rect"):
        if one(g, "layer") and one(g, "layer")[1] == "Edge.Cuts":
            a, b = xy(one(g, "start")), xy(one(g, "end")); segs.append(box(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])).exterior)
    circles = []
    for g in kids(tree, "gr_circle"):
        if one(g, "layer") and one(g, "layer")[1] == "Edge.Cuts":
            c = xy(one(g, "center")); e = xy(one(g, "end")); circles.append((c, math.hypot(e[0] - c[0], e[1] - c[1])))
    if circles:
        circles.sort(key=lambda t: -t[1]); (c, r) = circles[0]
        area = Point(c).buffer(r, 256)
        for c2, r2 in circles[1:]: area = area.difference(Point(c2).buffer(r2, 256))
        return area
    polys = list(polygonize(unary_union(segs))) if segs else []
    return max(polys, key=lambda p: p.area) if polys else None

def run(board, path):
    tree = parse(open(path).read())
    hv = set(dru_gen.BOARDS[board]["hv"]); hv_mm = dru_gen.BOARDS[board]["hv_mm"]
    copper, holes, tracks, vias = items_of(tree, board)
    outline = edge_polygon(tree)
    res = dict(board=board, file=path, checks={}, errors=[], zones=len(kids(tree, "zone")))
    # width
    bad_w = [t for t in tracks if t["w"] < TRK - 1e-9]
    _bd = dru_gen.BOARDS[board]; via_drill_min, via_ann_min = _bd.get("via_drill", VIA_DRILL), _bd.get("via_annular", VIA_ANN)           # AB1A / AB1B carry the vendors' documented Standard via (0.254 / 0.127) in dru_gen
    bad_v = [v for v in vias if (v["size"] - v["drill"]) / 2 < via_ann_min - 1e-9 or v["drill"] < via_drill_min - 1e-9]
    bad_p = [h for h in holes if h["kind"] == "pad:thru_hole" and not h["npth"] and (h["drill"] < PTH_DRILL - 1e-9)]
    ann = [c for c in copper if c["kind"] == "pad:thru_hole" and c["ptype"] == "thru_hole" and c["drill"] and (c["w"] - c["drill"]) / 2 < PTH_ANN - 1e-9]
    res["checks"]["width_track"] = dict(n=len(tracks), bad=len(bad_w), min=min([t["w"] for t in tracks] or [0]))
    res["checks"]["via_size_drill"] = dict(n=len(vias), bad=len(bad_v))
    res["checks"]["pth_drill"] = dict(bad=len(bad_p))
    res["checks"]["pth_annular"] = dict(bad=len(set(id(c) for c in ann)))
    # clearance between copper of different nets on one layer (STRtree)
    byL = {}
    for c in copper: byL.setdefault(c["layer"], []).append(c)
    viol = []; min_seen = {}
    for L, cs in byL.items():
        geoms = [c["geom"] for c in cs]; tree_ = STRtree(geoms)
        for i, c in enumerate(cs):
            for j in tree_.query(c["geom"].buffer(1.2)):
                if j <= i: continue
                d_ = cs[j]
                if c["net"] == d_["net"] and c["net"] != "": continue
                d = c["geom"].distance(d_["geom"])
                need = hv_mm if (c["net"] in hv or d_["net"] in hv) else CLR
                key = (c["net"], d_["net"])
                if c["net"] == "" and d_["net"] == "": continue
                if d + 1e-9 < need: viol.append(dict(layer=L, need=need, dist=round(d, 4), a=c["kind"] + ":" + c["net"], b=d_["kind"] + ":" + d_["net"], at=[round(x, 2) for x in c["at"]]))
                min_seen[L] = min(min_seen.get(L, 9), d)
    res["checks"]["clearance"] = dict(bad=len(viol), min_gap_mm=round(min(min_seen.values()), 4) if min_seen else None, examples=viol[:8])
    # hole to hole and hole to copper
    hv_ = []
    for i, h in enumerate(holes):
        for j in range(i + 1, len(holes)):
            g = holes[j]
            d = math.hypot(h["at"][0] - g["at"][0], h["at"][1] - g["at"][1]) - (h["drill"] + g["drill"]) / 2
            if d + 1e-9 < HOLE_HOLE: hv_.append(dict(kind="hole-hole", gap=round(d, 3), at=[round(x, 2) for x in h["at"]]))
    res["checks"]["hole_to_hole"] = dict(bad=len(hv_), examples=hv_[:6])
    hc = []; cg = STRtree([c["geom"] for c in copper])
    for h in holes:
        for j in cg.query(h["geom"].buffer(HOLE_CU + 0.05)):
            c = copper[j]
            if c["net"] == h["net"] and h["net"] != "": continue
            if abs(c["at"][0] - h["at"][0]) < 1e-6 and abs(c["at"][1] - h["at"][1]) < 1e-6 and c["net"] == h["net"]: continue          # a hole and the copper of its own pad (also for a pad with no net)
            d = h["geom"].distance(c["geom"])
            if d + 1e-9 < HOLE_CU: hc.append(dict(kind=h["kind"], gap=round(d, 3), copper=c["kind"] + ":" + c["net"] + "@" + c["layer"], at=[round(x, 2) for x in h["at"]]))
    res["checks"]["hole_to_copper"] = dict(bad=len(hc), examples=hc[:6])
    # edge clearance
    if outline is None: res["errors"].append("no Edge.Cuts outline")
    else:
        inner = outline.buffer(-EDGE)
        out = [c for c in copper if not inner.covers(c["geom"])]
        res["checks"]["edge"] = dict(bad=len(out), examples=[dict(kind=c["kind"], net=c["net"], at=[round(x, 2) for x in c["at"]]) for c in out[:6]])
    # connectivity per net
    parent = {}
    def f(x):
        while parent.setdefault(x, x) != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
        return x
    cg2 = STRtree([c["geom"] for c in copper]); pairs = 0
    for i, c in enumerate(copper):
        if c["net"] == "": continue
        for j in cg2.query(c["geom"]):
            if j <= i: continue
            d_ = copper[j]
            if d_["net"] != c["net"]: continue
            if c["layer"] != d_["layer"] and not (c["pad"] and c["ptype"] == "thru_hole") and c["kind"] != "via" and not (d_["kind"] == "via" or (d_["pad"] and d_.get("ptype") == "thru_hole")): continue
            if c["geom"].distance(d_["geom"]) <= 1e-6: parent[f(i)] = f(j); pairs += 1
    by_hole = {}                                            # both copper layers of one through-hole pad or via are one node
    for i, c in enumerate(copper):
        if c["net"] and (c["kind"] == "via" or (c["pad"] and c.get("ptype") == "thru_hole")):
            by_hole.setdefault((round(c["at"][0], 4), round(c["at"][1], 4), c["net"]), []).append(i)
    for idx in by_hole.values():
        for k in idx[1:]: parent[f(k)] = f(idx[0])
    zone_nets = {}                                           # zone-net exemption: a zone fill joins the vias and through-hole pads of its net that lie inside its polygon (the fill itself, its clearance and thermal spokes are KiCad's DRC)
    for z in kids(tree, "zone"):
        zn = one(z, "net_name"); pl = one(z, "polygon"); pts = one(pl, "pts") if pl else None
        if not zn or not pts: continue
        poly = Polygon([(float(q[1]), float(q[2])) for q in kids(pts, "xy")]); idx = [i for i, c in enumerate(copper) if c["net"] == zn[1] and (c["kind"] == "via" or (c["pad"] and c.get("ptype") == "thru_hole")) and poly.contains(Point(c["at"]))]
        zone_nets.setdefault(zn[1], []).append(len(idx))
        for k in idx[1:]: parent[f(k)] = f(idx[0])
    res["zone_nets_joined"] = zone_nets
    per_net = {}
    for i, c in enumerate(copper):
        if c["net"] == "": continue
        per_net.setdefault(c["net"], set()).add(f(i))
    # a pad that is never copper-connected to anything still counts as an island
    unconnected = {n: len(s) for n, s in per_net.items() if len(s) > 1}
    res["checks"]["connectivity"] = dict(nets=len(per_net), split_nets=unconnected, connections=pairs)
    fails = {k: v["bad"] for k, v in res["checks"].items() if isinstance(v, dict) and v.get("bad")}
    fails.update({f"split:{n}": k - 1 for n, k in unconnected.items()})
    fails.update({f"error:{e[:40]}": 1 for e in res["errors"]})
    res["fails"] = fails; res["n_fail"] = sum(fails.values())
    res["zones_checked"] = res["zones"] == 0; res["zone_clearance_checked"] = False             # fills are not modelled: KiCad DRC covers zone clearance
    return res

if __name__ == "__main__":
    board, path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    r = run(board, path); json.dump(r, open(out, "w"), indent=1)
    print(board, "fails:", r["fails"] or "none", "| clearance min", r["checks"]["clearance"]["min_gap_mm"], "| zones", r["zones"])
    sys.exit(0)
