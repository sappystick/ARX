"""solid_union study on dumped union inputs: profile of the current path, batch union, and the Mesh64 round-trip ("save-and-rebuild") path.
For each dump: timings per stage, output hashes, and geometric deviation of each variant from the current output (symmetric-difference volume / area, max vertex distance)."""
import sys, os, time, json, hashlib, glob, io
import numpy as np
sys.path.insert(0, "/home/user/ARX/src/mech"); import solid_union as su, manifold3d as M3
from scipy.spatial import cKDTree
D = sys.argv[1]; res = {}
def load(p):
    z = np.load(p); n = int(z["n"]); return float(z["margin"]), [(z[f"V{k}"], z[f"F{k}"]) for k in range(n)]
def finish(u):
    u = u.simplify(su.SIMPLIFY); m = u.to_mesh(); return np.asarray(m.vert_properties, float)[:, :3], np.asarray(m.tri_verts, np.int64)
def snapc(V, F):
    t = time.time()
    cands = [(q, o * q) for q in (1e-3, 1.5e-3, 2e-3, 3e-3) for o in (0.3, 0.5, 0.0, 0.1, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9)]
    cands += [(q, np.array([ox * q, oy * q, 0.53 * q])) for q in (1e-3, 1.2e-3, 1.5e-3, 2e-3, 2.5e-3) for ox in (0.0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6) for oy in (0.0, 0.37, 0.71)]
    for i, (q, off) in enumerate(cands):
        Vq = np.round((V - off) / q) * q + off; U_, inv = np.unique(Vq, axis=0, return_inverse=True); G = inv.reshape(-1)[F]; G = G[(G[:, 0] != G[:, 1]) & (G[:, 1] != G[:, 2]) & (G[:, 0] != G[:, 2])]
        if su.position_bad_edges(G, U_) == 0: return U_, su.canonical_faces(G), i, time.time() - t
    return None, None, -1, time.time() - t
DT = dict(vert_properties=np.float64, tri_verts=np.uint64, merge_from_vert=np.uint64, merge_to_vert=np.uint64, run_index=np.uint64, run_original_id=np.uint32,
          run_transform=np.float64, run_flags=np.uint8, face_id=np.uint64, halfedge_tangent=np.float64)
def rebuild(d):
    """what a per-body cache must store and restore: every Mesh64 field with its declared dtype, plus the tolerance (constructor and set_tolerance)"""
    m = d.to_mesh64(); tol = float(d.get_tolerance()); b = io.BytesIO(); np.savez(b, **{k: np.asarray(getattr(m, k)) for k in DT}); b.seek(0); z = np.load(b)
    kw = {k: np.ascontiguousarray(z[k].astype(DT[k])) for k in DT if z[k].size}
    return M3.Manifold(M3.Mesh64(tolerance=tol, **kw)).set_tolerance(tol)
def h(V, F): return hashlib.sha256(np.ascontiguousarray(np.asarray(V, np.float32)).tobytes() + np.ascontiguousarray(np.asarray(F, np.uint32)).tobytes()).hexdigest()[:16]
def man(V, F): return M3.Manifold(M3.Mesh(vert_properties=np.asarray(V, np.float32), tri_verts=np.asarray(F, np.uint32)))
def area(V, F): T = V[F]; return float(np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2)
def p2t(P, V, F, k=12, n=3_000_000):
    """exact distance from each point to the surface (V, F): candidate triangles = owners of the k nearest of an area-proportional surface sample
    (every triangle also contributes its centroid), then the exact point-triangle distance"""
    T = V[F]; ar = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    tid = np.random.default_rng(0).choice(len(F), n, p=ar / ar.sum()); r1, r2 = np.random.default_rng(1).random((2, n)); s_ = np.sqrt(r1)
    S = T[tid, 0] * (1 - s_)[:, None] + T[tid, 1] * (s_ * (1 - r2))[:, None] + T[tid, 2] * (s_ * r2)[:, None]
    S = np.vstack([S, T.mean(1)]); tid = np.concatenate([tid, np.arange(len(F))])
    _, idx = cKDTree(S).query(P, k=k); best = np.full(len(P), np.inf)
    for j in range(k):
        t = T[tid[idx[:, j]]]; best = np.minimum(best, _pt(P, t[:, 0], t[:, 1], t[:, 2]))
    return best
def _pt(p, a, b, c):
    """exact point-triangle distance, vectorised (Ericson, Real-Time Collision Detection 5.1.5)"""
    ab, ac, ap = b - a, c - a, p - a; d1 = (ab * ap).sum(1); d2 = (ac * ap).sum(1)
    bp = p - b; d3 = (ab * bp).sum(1); d4 = (ac * bp).sum(1); cp = p - c; d5 = (ab * cp).sum(1); d6 = (ac * cp).sum(1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc; den = np.where(np.abs(den) < 1e-300, 1e-300, den); v = vb / den; w = vc / den; q = a + ab * v[:, None] + ac * w[:, None]
    m = (d1 <= 0) & (d2 <= 0); q[m] = a[m]
    m = (d3 >= 0) & (d4 <= d3); q[m] = b[m]
    m = (d6 >= 0) & (d5 <= d6); q[m] = c[m]
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0) & ~((d1 <= 0) & (d2 <= 0)); t_ = d1 / np.where(d1 - d3 == 0, 1e-300, d1 - d3); q[m] = (a + ab * t_[:, None])[m]
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0) & ~((d1 <= 0) & (d2 <= 0)); t_ = d2 / np.where(d2 - d6 == 0, 1e-300, d2 - d6); q[m] = (a + ac * t_[:, None])[m]
    m = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0); t_ = (d4 - d3) / np.where((d4 - d3) + (d5 - d6) == 0, 1e-300, (d4 - d3) + (d5 - d6)); q[m] = (b + (c - b) * t_[:, None])[m]
    return np.linalg.norm(p - q, axis=1)
def dev(VA, FA, VB, FB):
    a, b = man(VA, FA), man(VB, FB); x = (a - b).volume() + (b - a).volume(); A = area(VA, FA)
    # max distance: every vertex of each mesh to the exact nearest triangle of the other (16 candidate triangles by centroid, exact point-triangle distance)
    dA = p2t(VA, VB, FB).max(); dB = p2t(VB, VA, FA).max()
    return dict(symdiff_mm3=round(x, 5), area_mm2=round(A, 1), mean_dev_um=round(x / A * 1e3, 4), max_vertex_to_surface_um=round(max(dA, dB) * 1e3, 2))
for p in sorted(glob.glob(f"{D}/*.npz")):
    mg, shells = load(p); r = dict(bodies=len(shells), tris_in=int(sum(len(F) for _, F in shells))); t0 = time.time()
    ds = [su.dilate(V, F, mg) for V, F in shells]; r["t_dilate"] = round(time.time() - t0, 2)
    t = time.time(); u = ds[0]
    for d in ds[1:]: u = u + d
    V, F = finish(u); r["t_union_seq"] = round(time.time() - t, 2)
    V0, F0, i0, ts = snapc(V, F); r["t_snap"] = round(ts, 2); r["snap_i"] = i0; r["hash_seq"] = h(V0, F0); r["tris_out"] = int(len(F0))
    t = time.time(); V, F = finish(M3.Manifold.batch_boolean(ds, M3.OpType.Add)); r["t_union_batch"] = round(time.time() - t, 2)
    Vb, Fb, ib, _ = snapc(V, F); r["hash_batch"] = h(Vb, Fb) if Vb is not None else None; r["batch_identical"] = r["hash_batch"] == r["hash_seq"]
    if Vb is not None and not r["batch_identical"]: r["batch_dev"] = dev(V0, F0, Vb, Fb)
    # save-and-rebuild: every dilation goes through Mesh64 (what a cache would store) before the union, cached or not
    t = time.time(); rb = []
    for d in ds: rb.append(rebuild(d))
    r["t_roundtrip"] = round(time.time() - t, 2)
    u = rb[0]
    for d in rb[1:]: u = u + d
    V, F = finish(u); Vr, Fr, ir, _ = snapc(V, F); r["hash_roundtrip"] = h(Vr, Fr) if Vr is not None else None; r["roundtrip_closed"] = Vr is not None
    # repeat the round-trip from a second rebuild (what a warm cache does) to see if the path is reproducible
    rb2 = [rebuild(rebuild(x)) for x in ds]                                  # a rebuilt body rebuilt again: does the round-trip reach a fixed point?
    u = rb2[0]
    for d in rb2[1:]: u = u + d
    V, F = finish(u); V2, F2, _, _ = snapc(V, F); r["roundtrip_reproducible"] = (h(V2, F2) == r["hash_roundtrip"]) if V2 is not None else False
    if Vr is not None: r["roundtrip_dev"] = dev(V0, F0, Vr, Fr); r["tris_roundtrip"] = int(len(Fr))
    np.savez(f"{D}/../out_{os.path.basename(p)}", V0=V0, F0=F0, Vb=Vb if Vb is not None else np.zeros((0, 3)), Fb=Fb if Fb is not None else np.zeros((0, 3), np.int64), Vr=Vr if Vr is not None else np.zeros((0, 3)), Fr=Fr if Fr is not None else np.zeros((0, 3), np.int64))
    res[os.path.basename(p)] = r; print(os.path.basename(p), json.dumps(r), flush=True)
json.dump(res, open(f"{D}/../study.json", "w"), indent=1)
