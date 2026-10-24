#!/usr/bin/env python3
"""Rebuild the copper of a Gerber layer as a shapely geometry (gerbonara reads the file; every primitive is applied in file order: dark = add, clear = subtract), and compare two layers by geometry.
Why: KiCad's Gerber export is NOT byte-deterministic (two exports of the same board differ in aperture / flash order in 7 of 12 files even with the timestamps removed), so a hash or a text diff cannot tell
a real change from noise. Used by gerber_plane_check.py (HV distances) and scripts/publish_data.py (is this layer really different from the published one?)."""
import math
from gerbonara import GerberFile
from shapely.geometry import Point, LineString, Polygon, box
from shapely import affinity
def _geom(pr):
    n = type(pr).__name__
    if n == "Circle": return Point(pr.x, pr.y).buffer(pr.r, 16)
    if n == "Rectangle": return affinity.rotate(box(pr.x - pr.w / 2, pr.y - pr.h / 2, pr.x + pr.w / 2, pr.y + pr.h / 2), math.degrees(pr.rotation) if pr.rotation else 0)
    if n == "Line": return LineString([(pr.x1, pr.y1), (pr.x2, pr.y2)]).buffer(pr.width / 2, 8)
    if n == "ArcPoly": return Polygon(pr.outline).buffer(0)
    return None
def layer_geometry(path):
    g = GerberFile.open(path); cu = Polygon(); n = 0
    for o in g.objects:
        for pr in o.to_primitives("mm"):
            s = _geom(pr)
            if s is None or s.is_empty: continue
            cu = cu.union(s) if pr.polarity_dark else cu.difference(s); n += 1
    return cu, n
def same_geometry(path_a, path_b, tol_mm2=1e-4):
    """True if the two layers describe the same copper (symmetric difference area below tol_mm2). Returns (bool, difference area)."""
    a, _ = layer_geometry(path_a); b, _ = layer_geometry(path_b); d = a.symmetric_difference(b).area
    return d < tol_mm2, d
