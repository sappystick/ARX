#!/usr/bin/env python3
"""Voxel interference audit (ray-parity solid voxelisation, 0.2 mm) of the assembled printed parts in a region of the head frame.
usage: interference_audit.py   (region = exit window, bridge and junction)"""
import struct, numpy as np, json, itertools, os
from scipy import ndimage as ndi
H = 0.2; X0, X1, Y0, Y1, Z0, Z1 = -100.0, -40.0, -16.0, 20.0, 28.0, 47.0
nx, ny, nz = [int(round((b - a) / H)) for a, b in ((X0, X1), (Y0, Y1), (Z0, Z1))]
def load(p):
    b = open(p, "rb").read(); n = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def voxelize(T):
    lo = T.min(1); hi = T.max(1); keep = (hi[:, 0] >= X0) & (lo[:, 0] <= X1) & (hi[:, 1] >= Y0) & (lo[:, 1] <= Y1)
    T = T[keep]; cols = [[] for _ in range(nx * ny)]; jx, jy = 0.0173, 0.0127
    for t in T:
        a, b, c = t; ar = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(ar) < 1e-12: continue
        i0 = max(0, int(np.floor((min(a[0], b[0], c[0]) - X0) / H))); i1 = min(nx - 1, int(np.ceil((max(a[0], b[0], c[0]) - X0) / H)))
        j0 = max(0, int(np.floor((min(a[1], b[1], c[1]) - Y0) / H))); j1 = min(ny - 1, int(np.ceil((max(a[1], b[1], c[1]) - Y0) / H)))
        if i1 < i0 or j1 < j0: continue
        gx, gy = np.meshgrid(X0 + (np.arange(i0, i1 + 1) + 0.5) * H + jx, Y0 + (np.arange(j0, j1 + 1) + 0.5) * H + jy, indexing="ij")
        w0 = ((b[0] - gx) * (c[1] - gy) - (c[0] - gx) * (b[1] - gy)) / ar; w1 = ((c[0] - gx) * (a[1] - gy) - (a[0] - gx) * (c[1] - gy)) / ar; w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any(): continue
        z = w0 * a[2] + w1 * b[2] + w2 * c[2]; ii, jj = np.nonzero(m)
        for p, q in zip(ii, jj): cols[(i0 + p) * ny + (j0 + q)].append(z[p, q])
    V = np.zeros((nx, ny, nz), bool)
    for ci, zs in enumerate(cols):
        if len(zs) < 2: continue
        zs = sorted(zs); i, j = divmod(ci, ny)
        for k in range(0, len(zs) - 1, 2):
            a = int(np.ceil((zs[k] - Z0) / H - 0.5)); b = int(np.floor((zs[k + 1] - Z0) / H - 0.5))
            if b >= a: V[i, j, max(a, 0):min(b + 1, nz)] = True
    return V
P = {"hub": "kit_v22/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl", "roof": "kit_v22/ROOF_PLATE_v5.stl", "hood_carrier": "kit_v18/PARTS/LOTUS_HOOD_CARRIER_v2_spokes.stl",
     "cradle": "kit_v22/TXJ1_CRADLE_v1.stl", "bridge": "kit_v19/YOKE/UMBILICAL_BRIDGE.stl", "bridge_lid": "kit_v19/YOKE/UMBILICAL_BRIDGE_LID.stl", "cap": "kit_v18/PARTS/HUB_CAP_HTA_v3_vault.stl"}
if os.path.exists("kit_v19/PARTS/HEAD_SKIRT.stl"): P["skirt"] = "kit_v19/PARTS/HEAD_SKIRT.stl"
vox = {}
for n, p in P.items():
    if os.path.exists(p): vox[n] = voxelize(load(p)); print(n, "voxels", int(vox[n].sum()))
res = []
for a, b in itertools.combinations(vox, 2):
    ov = vox[a] & vox[b]; core = ndi.binary_erosion(ov, iterations=1) if ov.any() else ov
    vol = float(ov.sum()) * H ** 3; cvol = float(core.sum()) * H ** 3
    gap = None
    if not ov.any():
        d = ndi.distance_transform_edt(~vox[a], sampling=H); gap = float(d[vox[b]].min()) if vox[b].any() else None
    res.append(dict(a=a, b=b, overlap_mm3=round(vol, 2), overlap_core_mm3=round(cvol, 2), min_gap_mm=None if gap is None else round(gap, 2)))
    if vol > 0 or (gap is not None and gap < 0.5): print(f"  {a:13} x {b:13} overlap {vol:8.2f} mm3 (core {cvol:6.2f})  gap {gap}")
bad = [r for r in res if r["overlap_core_mm3"] > 0.5]
json.dump(dict(region=[X0, X1, Y0, Y1, Z0, Z1], voxel_mm=H, pairs=res, interferences=bad), open("kit_v22/interference_audit.json", "w"), indent=1)
print("INTERFERENCES (core overlap > 0.5 mm3):", len(bad), [(r["a"], r["b"], r["overlap_core_mm3"]) for r in bad])
