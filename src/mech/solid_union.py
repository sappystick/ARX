"""Boolean union of the bodies a generator emits (Step 8). Before this, every generator joined its bodies with golden_cone_head.merge(), which only concatenates
the triangle lists: where two bodies overlap (or touch), the shared faces stay in the file, every edge there is shared by four faces, and the STL is not a solid
(data/results/print_check.json lists 15 such files). union_shells() runs the bodies through manifold3d (exact boolean on closed manifolds) and returns ONE closed
oriented mesh. Each input must be a closed, outward-oriented shell; otherwise it raises, naming the shell, so a generator cannot silently union a broken body.
STATUS (Step 9): the union is closed by topology (bad_edges 0 on the indexed output). It does NOT yet give a consumer-closed STL for hub_v22's
CORE cylinder: 223 bodies meet along edges (pinch contacts), which become 611 position-level open edges (print_check method). No generator uses this module yet.
Closing it needs the touching bodies overlapped by a small margin before the union, a geometry change to be re-checked (check_v22, head_crosscheck).
usage: V, F = union_shells([(V1, F1), (V2, F2), ...])"""
import numpy as np
import manifold3d as M3

def bad_edges(F):
    """number of undirected edges not shared by exactly two faces (0 = watertight)"""
    e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    return int(np.sum(np.unique(e, axis=0, return_counts=True)[1] != 2))

SIMPLIFY = 1e-3
GRID = 1e-4                                   # mm: the STL stores float32, and manifold3d can leave vertices closer than that; snapping keeps them distinct and exact

def snap(V, F, q=GRID):
    """snap vertices to a q-mm grid, weld the duplicates, drop triangles that collapse. Returns (V, F) with the same closure as the input (not repaired)."""
    Vq = np.round(np.asarray(V, float) / q) * q
    U, inv = np.unique(Vq, axis=0, return_inverse=True); G = inv.reshape(-1)[np.asarray(F, np.int64)]
    keep = (G[:, 0] != G[:, 1]) & (G[:, 1] != G[:, 2]) & (G[:, 0] != G[:, 2])
    return U, G[keep]

def _manifold(V, F, k):
    if bad_edges(F): raise ValueError(f"solid_union: shell {k} has {bad_edges(F)} bad edges: fix its generator before unioning")
    m = M3.Manifold(M3.Mesh(vert_properties=np.asarray(V, np.float32), tri_verts=np.asarray(F, np.uint32)))
    if m.status() != M3.Error.NoError: raise ValueError(f"solid_union: shell {k} rejected by manifold3d: {m.status()}")
    return m

def union_shells(shells):
    """shells: list of (V, F). Returns (V, F) of the single closed union, outward-oriented."""
    shells = [(np.asarray(V, float), np.asarray(F, np.int64)) for V, F in shells]
    ms = [_manifold(V, F, k) for k, (V, F) in enumerate(shells)]
    u = ms[0]
    for m in ms[1:]: u = u + m
    if u.status() != M3.Error.NoError: raise ValueError(f"solid_union: union failed: {u.status()}")
    u = u.simplify(SIMPLIFY)                                        # collapse features below 1 um (manifold keeps the solid closed; moves no face by more than SIMPLIFY)
    if u.status() != M3.Error.NoError: raise ValueError(f"solid_union: simplify failed: {u.status()}")
    mesh = u.to_mesh()
    V, F = np.asarray(mesh.vert_properties, float)[:, :3], np.asarray(mesh.tri_verts, np.int64)
    if bad_edges(F): raise ValueError(f"solid_union: the union is not closed ({bad_edges(F)} bad edges)")
    return V, F

def report(shells, V, F):
    """what a generator records: bodies in, bad edges in the concatenated input, bad edges in the union (must be 0), volume"""
    V_ = np.asarray(V, float)
    return dict(bodies=len(shells), bad_edges_in=sum(bad_edges(Fi) for _, Fi in shells), bad_edges_out=bad_edges(F),
                volume_mm3=round(float(np.einsum("ij,ij->i", V_[F[:, 0]], np.cross(V_[F[:, 1]], V_[F[:, 2]])).sum() / 6.0), 2), tris=int(len(F)))
