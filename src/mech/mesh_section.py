"""Mesh / plane section shared by the renderers and checks (blueprint_r3, cutaway_receive, pb1r_check NPM fit).
Each triangle edge that crosses the plane is interpolated from its lexicographically smaller vertex, so the two triangles sharing an edge compute the SAME point to the bit
and the segments join exactly. The earlier per-copy versions interpolated from whichever end came first in each triangle: with a different vertex order in the neighbour
(solid_union's canonical face order since 2026-10-28, and some meshes before that) the endpoints differed in the last bits, polygonize found few or no closed faces, and
sections came back empty or partial (CORRECTIONS).
section(T, axis, val) -> shapely geometry of the cut (even-odd filled) in the two remaining axes (ascending order), or None."""
import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union, polygonize

def section(T, axis, val):
    keep = [i for i in range(3) if i != axis]; d = T[:, :, axis] - (val + 1.234e-4); m = (d.min(1) < 0) & (d.max(1) > 0); segs = []
    for tri, dd in zip(T[m], d[m]):
        q = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if (dd[i] < 0) != (dd[j] < 0):
                a, b = (i, j) if tuple(tri[i]) < tuple(tri[j]) else (j, i)
                q.append(tri[a] + dd[a] / (dd[a] - dd[b]) * (tri[b] - tri[a]))
        if len(q) == 2 and np.linalg.norm(q[0] - q[1]) > 1e-9: segs.append(LineString([tuple(q[0][keep]), tuple(q[1][keep])]))
    if not segs: return None
    faces = list(polygonize(unary_union(segs)))
    if not faces: return None
    g = faces[0]
    for f in faces[1:]: g = g.symmetric_difference(f)
    return g
