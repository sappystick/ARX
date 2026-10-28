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


_CANDS_TAG = "q(1e-3,1.5e-3,2e-3,3e-3) x o(0.3,0.5,0,0.1,0.2,0.4,0.6,0.7,0.8,0.9); q(1e-3,1.2e-3,1.5e-3,2e-3,2.5e-3) x ox(0..5/6) x oy(0,0.37,0.71) x 0.53q"   # change with the cands list below
MARGIN = 0.005                                 # mm: touching bodies are dilated by this before the union so that pinch contacts (edge-to-edge) become small overlaps; 0.025 moved the roof 0.025 mm and broke the 0.01 mm layer-stack tolerance of head_crosscheck
def position_bad_edges(F, V):
    """print_check's definition of closed on the STORED mesh: vertices rounded to 1e-4 mm (float32 STL), every undirected edge shared by exactly two faces"""
    V32 = np.asarray(V, np.float32).astype(float); Vr = np.round(V32, 4); U, inv = np.unique(Vr, axis=0, return_inverse=True); G = inv.reshape(-1)[np.asarray(F, np.int64)]
    G = G[(G[:, 0] != G[:, 1]) & (G[:, 1] != G[:, 2]) & (G[:, 0] != G[:, 2])]
    return bad_edges(G)
def dilate(V, F, r=MARGIN):
    m = M3.Manifold(M3.Mesh(vert_properties=np.asarray(V, np.float32), tri_verts=np.asarray(F, np.uint32)))
    return m.minkowski_sum(M3.Manifold.sphere(r, 8))
# ---- content-hash cache (2026-10-28): an unchanged body SET is never unioned again (whole result cached) and the winning snap grid is remembered; the per-body dilation cache
# exists but is OFF (not byte-identical, see DILATE_CACHE).
# Keys hash exactly what each computation reads (float32 / uint32 bytes as handed to manifold3d, margin, sphere segments, manifold3d version, the snap candidate list).
# Proved byte-identical to the uncached path for the whole-union and snap caches (docs/PERFORMANCE.md). SOLID_UNION_CACHE=off (or "0") runs the uncached path; the directory is work/.pipeline/solid_union_cache (git-ignored, invisible to the tracer, wiped by make clean).
import hashlib, os, json, sys
CACHE = os.environ.get("SOLID_UNION_CACHE", os.path.join(".pipeline", "solid_union_cache"))
CACHE_ON = CACHE not in ("off", "0", "")
STATS = dict(dilate_hit=0, dilate_miss=0, union_hit=0, union_miss=0, snap_hit=0, snap_miss=0)
_VER = getattr(M3, "__version__", "") or "manifold3d"
_M64 = ("vert_properties", "tri_verts", "merge_from_vert", "merge_to_vert", "run_index", "run_original_id", "run_transform", "run_flags", "face_id", "halfedge_tangent")
def _key(*parts):
    h = hashlib.sha256()
    for p in parts: h.update(p if isinstance(p, bytes) else repr(p).encode()); h.update(b"|")
    return h.hexdigest()
def _mesh_key(tag, V, F, *extra):
    V32 = np.ascontiguousarray(np.asarray(V, np.float32)); F32 = np.ascontiguousarray(np.asarray(F, np.uint32))
    return _key(tag, _VER, V32.shape, F32.shape, V32.tobytes(), F32.tobytes(), *extra)
def _path(k, kind): return os.path.join(CACHE, kind, k[:2], k + ".npz")
def _save(path, **arrs):
    os.makedirs(os.path.dirname(path), exist_ok=True); tmp = f"{path}.{os.getpid()}.tmp.npz"
    np.savez(tmp, **arrs); os.replace(tmp, path)                       # atomic: parallel pipeline jobs may write the same key
def _load(path):
    try:
        with np.load(path, allow_pickle=False) as z: return {k: z[k] for k in z.files}
    except Exception: return None
# ---- canonical rebuild (2026-10-28, viewer/su study): every dilated body is converted to a Mesh64 with its declared field dtypes and its tolerance, and the union is
# built from Manifolds rebuilt from those arrays, cached or not. A cache hit then restores exactly the arrays the uncached path builds from, so the two paths are the same
# computation (byte-identical by construction); the earlier experiment rebuilt with int64 fields and no constructor tolerance and was not. Switch: SOLID_UNION_REBUILD
# (default decided by scripts/su_proof.py, docs/PERFORMANCE.md).
M64_DT = dict(vert_properties=np.float64, tri_verts=np.uint64, merge_from_vert=np.uint64, merge_to_vert=np.uint64, run_index=np.uint64, run_original_id=np.uint32,
              run_transform=np.float64, run_flags=np.uint8, face_id=np.uint64, halfedge_tangent=np.float64)
REBUILD = os.environ.get("SOLID_UNION_REBUILD", "0") == "1"
def to_arrays(d):
    m = d.to_mesh64(); return {k: np.ascontiguousarray(np.asarray(getattr(m, k)).astype(t)) for k, t in M64_DT.items()}, float(d.get_tolerance())
def from_arrays(arrs, tol):
    return M3.Manifold(M3.Mesh64(tolerance=tol, **{k: v for k, v in arrs.items() if v.size})).set_tolerance(tol)
def dilate_rebuilt(V, F, r=MARGIN):
    """dilation in canonical (rebuilt) form; with the cache on, the arrays are stored per body and reused when the body is unchanged"""
    p = _path(_mesh_key(b"dilate-v2", V, F, float(r), 8), "dilate") if CACHE_ON else None; z = _load(p) if p else None
    if z is not None:
        STATS["dilate_hit"] += 1; return from_arrays({k: z[k] for k in M64_DT}, float(z["tolerance"]))
    STATS["dilate_miss"] += 1; d = dilate(V, F, r)
    if d.status() != M3.Error.NoError: return d
    arrs, tol = to_arrays(d)
    if p: _save(p, tolerance=np.float64(tol), **arrs)
    return from_arrays(arrs, tol)
DILATE_CACHE = os.environ.get("SOLID_UNION_DILATE_CACHE") == "1"         # EXPERIMENTAL, off: a Manifold rebuilt from a cached Mesh64 (every field, IDs, set_tolerance) does not union + simplify like the
                                                                          # in-memory one (ROOF_PLATE 104536 vs 134436 triangles, CORE 216916 vs 398556), so it is NOT byte-identical: never use it for a release
def dilate_cached(V, F, r=MARGIN):
    if not (CACHE_ON and DILATE_CACHE): return dilate(V, F, r)
    p = _path(_mesh_key(b"dilate-v1", V, F, float(r), 8), "dilate"); z = _load(p)
    if z is not None:
        STATS["dilate_hit"] += 1
        kw = {k: z[k] for k in _M64 if k in z and z[k].size}
        return M3.Manifold(M3.Mesh64(**kw)).set_tolerance(float(z["tolerance"]))
    STATS["dilate_miss"] += 1; d = dilate(V, F, r)
    if d.status() == M3.Error.NoError:
        m = d.to_mesh64(); _save(p, tolerance=np.float64(d.get_tolerance()), **{k: np.asarray(getattr(m, k)) for k in _M64})
    return d
def canonical_faces(F):
    """same triangles, deterministic order: each face rotated so its smallest vertex index is first (orientation kept), then the faces sorted"""
    F = np.asarray(F, np.int64); k = np.argmin(F, axis=1); idx = (k[:, None] + np.arange(3)[None, :]) % 3; R = np.take_along_axis(F, idx, axis=1)
    return R[np.lexsort((R[:, 2], R[:, 1], R[:, 0]))]
def merge_closed(shells, concat, margin=MARGIN):
    """generators call this in place of golden_cone_head.merge(): if the plain concatenation already has no open edge (print_check's definition) it is returned unchanged;
    otherwise the bodies are each dilated by `margin` mm and unioned (manifold3d) into ONE closed mesh. Returns (V, F, info) with info = dict(method, bodies, margin, volume_in_mm3, volume_out_mm3)."""
    V0, F0 = concat; vol = lambda V, F: float(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6.0)
    if position_bad_edges(F0, V0) == 0: return V0, F0, dict(method="concatenated", bodies=len(shells), margin=0.0)
    if os.environ.get("SOLID_UNION_DUMP"):                                 # studies only (scripts/su_proof.py): the exact bodies of this union, numbered in call order
        d_ = os.environ["SOLID_UNION_DUMP"]; os.makedirs(d_, exist_ok=True); n_ = len([f for f in os.listdir(d_) if f.endswith(".npz")])
        np.savez(os.path.join(d_, f"u{n_:03d}_{os.path.basename(sys.argv[0])}.npz"), margin=np.float64(margin), n=np.int64(len(shells)), **{f"V{k}": np.asarray(V, float) for k, (V, _) in enumerate(shells)}, **{f"F{k}": np.asarray(F, np.int64) for k, (_, F) in enumerate(shells)})
    ku = None
    if CACHE_ON:                                                           # whole result: same bodies, same margin -> the stored (V, F, info)
        ku = _key(b"union-v3-rebuild" if REBUILD else b"union-v2", _VER, float(margin), SIMPLIFY, repr(_CANDS_TAG), *[_key(b"body64", np.ascontiguousarray(np.asarray(V, float)).tobytes(), np.ascontiguousarray(np.asarray(F, np.int64)).tobytes(), np.shape(V)) for V, F in shells]); z = _load(_path(ku, "union"))
        if z is not None: STATS["union_hit"] += 1; return z["V"], z["F"], json.loads(str(z["info"]))
        STATS["union_miss"] += 1
    u = None
    for k, (V, F) in enumerate(shells):
        d = dilate_rebuilt(V, F, margin) if REBUILD else dilate_cached(V, F, margin)
        if d.status() != M3.Error.NoError: raise ValueError(f"solid_union: dilation of shell {k} failed: {d.status()}")
        u = d if u is None else u + d
    u = u.simplify(SIMPLIFY); mesh = u.to_mesh(); V, F = np.asarray(mesh.vert_properties, float)[:, :3], np.asarray(mesh.tri_verts, np.int64)
    snapped = None
    cands = [(q, o * q) for q in (1e-3, 1.5e-3, 2e-3, 3e-3) for o in (0.3, 0.5, 0.0, 0.1, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9)]
    cands += [(q, np.array([ox * q, oy * q, 0.53 * q])) for q in (1e-3, 1.2e-3, 1.5e-3, 2e-3, 2.5e-3) for ox in (0.0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6) for oy in (0.0, 0.37, 0.71)]      # per-axis offsets: the CORE union (111k vertices) needs (q 1.5 um, off 0.17 q, 0, 0.53 q)
    best = None
    ks = _key(b"snap-v1", np.ascontiguousarray(V).tobytes(), np.ascontiguousarray(F).tobytes(), repr(_CANDS_TAG)) if CACHE_ON else None
    zs = _load(_path(ks, "snap")) if ks else None
    if zs is not None:                                                     # the first closing candidate of this exact union; re-checked, else the full search runs
        i = int(zs["i"]); q, off = cands[i]
        Vq = np.round((V - off) / q) * q + off; U_, inv = np.unique(Vq, axis=0, return_inverse=True); G = inv.reshape(-1)[F]; G = G[(G[:, 0] != G[:, 1]) & (G[:, 1] != G[:, 2]) & (G[:, 0] != G[:, 2])]
        if position_bad_edges(G, U_) == 0: STATS["snap_hit"] += 1; cands = [cands[i]]
    if ks and zs is None: STATS["snap_miss"] += 1
    for ci, (q, off) in enumerate(cands):                                                   # vertices closer than the STL's float32 / 4-decimal resolution look like pinch edges to print_check: snap to a grid until none is left
        Vq = np.round((V - off) / q) * q + off; U_, inv = np.unique(Vq, axis=0, return_inverse=True); G = inv.reshape(-1)[F]; G = G[(G[:, 0] != G[:, 1]) & (G[:, 1] != G[:, 2]) & (G[:, 0] != G[:, 2])]
        nb = position_bad_edges(G, U_)
        if best is None or nb < best[0]: best = (nb, q, off)
        if nb == 0:
            V, F, snapped = U_, G, (q, off)
            if ks and zs is None: _save(_path(ks, "snap"), i=np.int64(ci))
            break
    if snapped is None: np.savez("solid_union_failed.npz", V=V, F=F)
    if snapped is None: raise ValueError(f"solid_union: no snap grid closes the union at the STL's stored resolution (best: {best[0]} open edges at grid {best[1]} offset {best[2]}); the union was saved to solid_union_failed.npz")
    F = canonical_faces(F)                                                 # manifold3d's parallel boolean returns the triangles in a run-dependent order (same set): fix the order so every run, cached or not, writes the same bytes
    info = dict(snap_grid_mm=float(snapped[0]), snap_offset_mm=[round(float(x), 6) for x in np.atleast_1d(snapped[1])], method="dilated union", bodies=len(shells), margin=margin, volume_in_mm3=round(sum(vol(np.asarray(V_, float), np.asarray(F_, np.int64)) for V_, F_ in shells), 2), volume_out_mm3=round(vol(V, F), 2), open_edges_after=position_bad_edges(F, V))
    if ku: _save(_path(ku, "union"), V=V, F=F, info=np.array(json.dumps(info)))
    return V, F, info
