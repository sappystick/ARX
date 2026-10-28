"""Geometric comparison of two closed meshes (scripts/su_proof.py): symmetric-difference volume (exact booleans, manifold3d), mean deviation = that volume / area,
and the maximum vertex-to-surface distance both ways (candidate triangles from an area-proportional surface sample plus every centroid, then the exact
point-triangle distance, Ericson 5.1.5). A max distance of a few um with a mean in the nm range means the same solid with a different triangulation."""
import numpy as np
import manifold3d as M3
from scipy.spatial import cKDTree

def man(V, F): return M3.Manifold(M3.Mesh(vert_properties=np.asarray(V, np.float32), tri_verts=np.asarray(F, np.uint32)))
def area(V, F): T = np.asarray(V, float)[F]; return float(np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2)

def _pt(p, a, b, c):
    ab, ac, ap = b - a, c - a, p - a; d1 = (ab * ap).sum(1); d2 = (ac * ap).sum(1)
    bp = p - b; d3 = (ab * bp).sum(1); d4 = (ac * bp).sum(1); cp = p - c; d5 = (ab * cp).sum(1); d6 = (ac * cp).sum(1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc; den = np.where(np.abs(den) < 1e-300, 1e-300, den); v = vb / den; w = vc / den; q = a + ab * v[:, None] + ac * w[:, None]
    nz = lambda x: np.where(x == 0, 1e-300, x)
    m = (d1 <= 0) & (d2 <= 0); q[m] = a[m]
    m = (d3 >= 0) & (d4 <= d3); q[m] = b[m]
    m = (d6 >= 0) & (d5 <= d6); q[m] = c[m]
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0) & ~((d1 <= 0) & (d2 <= 0)); t = d1 / nz(d1 - d3); q[m] = (a + ab * t[:, None])[m]
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0) & ~((d1 <= 0) & (d2 <= 0)); t = d2 / nz(d2 - d6); q[m] = (a + ac * t[:, None])[m]
    m = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0); t = (d4 - d3) / nz((d4 - d3) + (d5 - d6)); q[m] = (b + (c - b) * t[:, None])[m]
    return np.linalg.norm(p - q, axis=1)

def point_to_surface(P, V, F, k=12, n=3_000_000):
    V = np.asarray(V, float); T = V[F]; ar = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    tid = np.random.default_rng(0).choice(len(F), n, p=ar / ar.sum()); r1, r2 = np.random.default_rng(1).random((2, n)); s = np.sqrt(r1)
    S = T[tid, 0] * (1 - s)[:, None] + T[tid, 1] * (s * (1 - r2))[:, None] + T[tid, 2] * (s * r2)[:, None]
    S = np.vstack([S, T.mean(1)]); tid = np.concatenate([tid, np.arange(len(F))])
    _, idx = cKDTree(S).query(np.asarray(P, float), k=k); best = np.full(len(P), np.inf)
    for j in range(k):
        t = T[tid[idx[:, j]]]; best = np.minimum(best, _pt(np.asarray(P, float), t[:, 0], t[:, 1], t[:, 2]))
    return best

def compare(VA, FA, VB, FB):
    a, b = man(VA, FA), man(VB, FB); x = (a - b).volume() + (b - a).volume(); A = area(VA, FA)
    dA = point_to_surface(VA, VB, FB).max(); dB = point_to_surface(VB, VA, FA).max()
    return dict(symdiff_mm3=round(x, 6), area_mm2=round(A, 1), mean_dev_um=round(x / A * 1e3, 5), max_dev_um=round(max(dA, dB) * 1e3, 3),
                vol_a_mm3=round(a.volume(), 3), vol_b_mm3=round(b.volume(), 3), tris_a=int(len(FA)), tris_b=int(len(FB)))
