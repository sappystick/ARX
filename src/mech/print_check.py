#!/usr/bin/env python3
"""Print and mould readiness of every PRINT-class STL in stl/ (Step 8 of the in-house prototype plan). Numpy only: no mesh library is installed.
Per file (STL as stored, z up = build direction):
  closed    every undirected edge is shared by exactly two faces with opposite directions (watertight, manifold edges)
  oriented  signed volume > 0 (outward normals)
  bbox      size in mm; fits a 250 mm cube (typical desktop FDM / SLA build volume)
  overhang  area fraction of faces facing down more than 45 deg (need support in FDM) that are above the first 0.3 mm of height
  wall      sampled wall-thickness estimate: from points on large faces, the distance to the opposite surface along the inward normal
            (ray cast). Reported as the 10th percentile (a thin-wall estimate, not a full medial-axis analysis). Flag below 1.2 mm.
  draft     for injection-mould candidates: area fraction of near-vertical faces (side walls, |nz| < 0.1 w.r.t. the z pull) with draft below 1 deg
Limits: the checks read the meshes as stored; they do not slice, do not simulate warp, and do not know the printer. Print settings and the first article decide the rest.
usage (repo root): python3 src/mech/print_check.py OUT.json"""
import sys, csv, json, struct, math
import numpy as np
MAX_BUILD = 250.0; OVERHANG_DEG = 45.0; WALL_FLAG = 1.2; DRAFT_DEG = 1.0; FLOOR_MM = 0.3

def superseded_names():
    """file names listed as superseded in the STL folders' SUPERSEDED.txt (the same list the package uses)"""
    import glob, re
    names = set()
    for f in glob.glob("stl/*/SUPERSEDED.txt"):
        for line in open(f):
            m = re.match(r"- ([A-Za-z0-9_]+\.stl) ->", line)                             # only the superseded name (left of the arrow)
            if m: names.add(m[1])
    return names

SUPER = superseded_names()
def classify(p):
    """same classes as scripts/make_package.py, plus the SUPERSEDED.txt lists"""
    n = p.rsplit("/", 1)[-1]
    if n.startswith(("ELB_E", "BAT_B")) or "SUPERSEDED" in p or n in SUPER: return "SUPERSEDED"
    if "reference" in n or n.startswith("UPPER_ASSEMBLY") or n in ("U8_SEPTUM_extended.stl", "U8_SEPTUM_collapsed.stl"): return "REFERENCE"       # the full-length septum is a fit reference; the printable parts are U8_SEPTUM_extended_SEG_A / _B (each under 250 mm)
    return "PRINT"

def read(p):
    b = open(p, "rb").read()
    k = struct.unpack("<I", b[80:84])[0]
    rec = np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)
    return rec["v"].reshape(-1, 3, 3).astype(float)

def closed_oriented(T):
    V = np.round(T.reshape(-1, 3), 4); idx = {}
    ids = np.array([idx.setdefault(tuple(v), len(idx)) for v in V]).reshape(-1, 3)
    E = np.vstack([ids[:, [0, 1]], ids[:, [1, 2]], ids[:, [2, 0]]])
    und = {}
    for a, b in E:
        key = (min(a, b), max(a, b)); und[key] = und.get(key, 0) + 1
    counts = np.array(list(und.values()))
    closed = bool(np.all(counts == 2))
    vol = float(np.sum(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2]))) / 6.0)
    return closed, vol > 0, vol, int(np.sum(counts != 2))

def normals(T):
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); a = np.linalg.norm(n, axis=1) / 2.0
    u = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return u, a

def overhang(T, u, a):
    zmin = T[:, :, 2].min(); c = T.mean(1)[:, 2]
    down = (u[:, 2] < -math.cos(math.radians(90 - OVERHANG_DEG)) ) & (c > zmin + FLOOR_MM)    # normal more than 45 deg below horizontal
    return float(a[down].sum() / a.sum())

def draft(T, u, a):
    side = np.abs(u[:, 2]) < 0.1                                  # near-vertical faces
    if a[side].sum() <= 0: return None
    small = side & (np.abs(u[:, 2]) < math.sin(math.radians(DRAFT_DEG)))
    return float(a[small].sum() / a[side].sum())

def wall(T, u, a, nsamp=400, rng=np.random.default_rng(7)):
    """sample points on the large faces, cast the inward normal, take the distance to the first hit"""
    big = np.argsort(-a)[: max(1, len(a) // 3)]
    pick = rng.choice(big, size=min(nsamp, len(big)), replace=False)
    P = T[pick].mean(1) - 1e-3 * u[pick]; D = -u[pick]
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]; e1 = v1 - v0; e2 = v2 - v0; out = []
    for p, d in zip(P, D):
        h = np.cross(d, e2); det = np.einsum("ij,ij->i", e1, h); ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0); s = p - v0
        uu = np.einsum("ij,ij->i", s, h) * inv; q = np.cross(s, e1); vv = np.einsum("j,ij->i", d, q) * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        hit = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (t > 0.02)
        if hit.any(): out.append(float(t[hit].min()))
    return float(np.percentile(out, 10)) if out else None

def main(out_path):
    rows = list(csv.DictReader(open("stl/MANIFEST.csv"))); res = []
    for r in rows:
        f = r["file"]
        if classify(f) != "PRINT": continue
        T = read(f); closed, oriented, vol, bad_edges = closed_oriented(T); u, a = normals(T)
        lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0); size = hi - lo
        ov = overhang(T, u, a); dr = draft(T, u, a); wl = wall(T, u, a)
        fits = bool(np.all(size <= MAX_BUILD))
        flags = []
        if not closed: flags.append(f"open shell: {bad_edges} edges not shared by two faces")
        if not oriented: flags.append("inward normals (negative volume)")
        if not fits: flags.append(f"larger than {MAX_BUILD:.0f} mm build cube")
        if wl is not None and wl < WALL_FLAG: flags.append(f"thin wall estimate {wl:.2f} mm (< {WALL_FLAG} mm)")
        res.append(dict(file=f, faces=len(T), size_mm=[round(float(x), 2) for x in size], volume_cm3=round(vol / 1000.0, 2), closed=closed, oriented=oriented,
                        fits_build_cube=fits, overhang_area_fraction=round(ov, 3), wall_p10_mm=None if wl is None else round(wl, 2),
                        draft_fraction_below_1deg=None if dr is None else round(dr, 3), flags=flags, ok=closed and oriented and fits))
    summary = dict(files=len(res), closed=sum(x["closed"] for x in res), oriented=sum(x["oriented"] for x in res), fits=sum(x["fits_build_cube"] for x in res),
                   thin_wall_flags=sum(1 for x in res if any("thin wall" in f for f in x["flags"])), notes=[
                       "closed/oriented/fits: regress.py locks the known open list (15) and the known oversize part (1); any other open or oversize file FAILS. Wall estimates on open (non-manifold) shells are unreliable: rays pass through overlapping shells",
                       f"overhang: area fraction of faces more than {OVERHANG_DEG:.0f} deg below horizontal above the first {FLOOR_MM} mm, as stored (z up)",
                       "wall: sampled 10th percentile, not a medial axis; a sampled estimate can miss a thin feature that no sample hits",
                       "draft: near-vertical faces with less than 1 deg draft against a z pull, only meaningful for mould candidates"])
    json.dump(dict(summary=summary, parts=res), open(out_path, "w"), indent=1)
    print(f"print_check: {summary['files']} PRINT files: closed {summary['closed']}, oriented {summary['oriented']}, fits {summary['fits']}, thin-wall flags {summary['thin_wall_flags']}")
    return res

if __name__ == "__main__":
    res = main(sys.argv[1] if len(sys.argv) > 1 else "data/results/print_check.json")
    sys.exit(0)                                                       # the verdict is tests/regress.py's (known list, Step 8); this step only measures
