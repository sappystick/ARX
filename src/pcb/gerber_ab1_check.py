#!/usr/bin/env python3
"""Gerber read-back of the AB1A / AB1B plane layers (KiCad-written, hatched fills), rebuilt with gerber_geom (gerbonara + shapely; never a hash or a text diff).
In4: the +5VA pour, the +3V3D island and the clearance between them; every +3V3D via and through-hole pad inside the island must be copper-connected to the island hatch (its copper polygon is
larger than its own ring), every +5VA via and pad must be connected to the pour, and no polygon may join the island to the pour. In1: every GND via and pad connected to the GND hatch.
CONTROL: a via that is deliberately not in the layer's net must NOT be connected to the pour (its antipad), otherwise the rebuild is void.
usage (in work/, after afe_layout.py / afe_export.py / kicad_gerber.py): BOARD=A python3 gerber_ab1_check.py OUT.json"""
import os, sys, json, math
out = sys.argv[1]; B = os.environ.get("BOARD", "A"); sys.argv = ["x"]
import afe_layout as A
from gerber_geom import layer_geometry
from shapely.geometry import Point, Polygon, box
CX = CY = 100.0; d = f"kit_v22/GERBER_AB1{B}"; pre = f"PF233-AB1{B}"
lay = json.load(open(f"out_board/AB1{B}_layout.json")); NAMES = {v: k for k, v in A.NETID.items()}
def pt(x, y): return Point(CX + x, -(CY + y))                      # file frame: x = CX + x, gerber y is up
def parts(cu): return list(cu.geoms) if hasattr(cu, "geoms") else [cu]
def poly_of(cu, p):
    for q in parts(cu):
        if q.contains(p) or q.distance(p) < 1e-6: return q
    return None
res = dict(board=f"AB1{B}", island=A.ISL, layers={})
ring = A.VIA_D / 2
def check_layer(layer, net, region=None):
    cu, n = layer_geometry(os.path.join(d, f"{pre}-{layer}_Cu.gbr")); items = []
    for x, y, nid in lay["VIAS"]:
        if NAMES.get(nid) == net: items.append(("via", x, y, ring))
    for p in A.PADS:
        if p["tht"] and p["net"] == net: items.append((f"{p['ref']}.{p['num']}", p["x"], p["y"], p["w"] / 2))
    rows = []
    for k, x, y, r in items:
        if region == "island" and not A.in_isl(x, y): continue
        if region == "outside" and A.ISL is not None and A.in_isl(x, y, -0.3): continue
        q = poly_of(cu, pt(x, y)); area = q.area if q is not None else 0.0
        rows.append(dict(item=k, at=(round(x, 2), round(y, 2)), polygon_area=round(area, 2), connected=bool(q is not None and area > math.pi * r * r * 3.0)))
    return cu, rows
for layer, net in (("In1", "GND"), ("In4", "+5VA")):
    cu, rows = check_layer(layer, net, "outside" if layer == "In4" else None)
    res["layers"][layer] = dict(net=net, items=len(rows), connected=sum(r["connected"] for r in rows), unconnected=[r for r in rows if not r["connected"]][:10], n_primitives=0)
if A.ISL is not None:
    cu, rows = check_layer("In4", "+3V3D", "island"); r = A.ISL
    isl_box = box(CX + r[0], -(CY + r[3]), CX + r[1], -(CY + r[2]))
    inside = [q for q in parts(cu) if isl_box.buffer(0.02).contains(q)]; outside = [q for q in parts(cu) if not isl_box.buffer(0.02).contains(q)]
    from shapely.ops import unary_union
    isl_cu = unary_union(inside) if inside else Polygon(); rest = unary_union(outside) if outside else Polygon(); gap = isl_cu.distance(rest) if not isl_cu.is_empty and not rest.is_empty else None
    joined = [q.area for q in parts(cu) if q.intersects(isl_box.buffer(-0.05)) and q.difference(isl_box.buffer(0.001)).area > 1.0]
    res["layers"]["In4_island"] = dict(net="+3V3D", items=len(rows), connected=sum(x["connected"] for x in rows), unconnected=[x for x in rows if not x["connected"]], island_copper_mm2=round(isl_cu.area, 2), island_box_mm2=round(isl_box.area, 2),
                                         pour_to_island_gap_mm=None if gap is None else round(gap, 3), island_joined_to_pour=bool(joined), plus5va_pour_mm2=round(rest.area, 1))
    ctl = [(x, y) for x, y, nid in lay["VIAS"] if NAMES.get(nid) not in ("+3V3D", "+5VA") and A.in_isl(x, y, -0.3)]
    res["control"] = dict(foreign_vias_in_island=len(ctl), foreign_vias_not_connected=sum(1 for x, y in ctl if (poly_of(cu, pt(x, y)) is None or poly_of(cu, pt(x, y)).area < math.pi * ring * ring * 3.0)))
L4 = res["layers"].get("In4_island", {})
res["pass"] = bool(all(v["items"] > 0 and v["connected"] == v["items"] for v in res["layers"].values()) and (A.ISL is None or (L4.get("pour_to_island_gap_mm") is not None and L4["pour_to_island_gap_mm"] >= A.CLEAR - 1e-6 and not L4["island_joined_to_pour"])))
json.dump(res, open(out, "w"), indent=1, default=str); print(json.dumps({k: v for k, v in res.items() if k != "island"}, default=str)[:900])
