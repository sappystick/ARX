#!/usr/bin/env python3
"""make su-proof: proof for the solid_union canonical rebuild path (SOLID_UNION_REBUILD=1) on the heaviest build, v5 (hub_v22.py + parts_v22.py), on scratch
copies of work/ (nothing in the repo or in work/ is touched). Runs, each from the same inputs:
  ref        the committed path (REBUILD=0, uncached)              -> what the STLs in stl/ were built with
  rb_off     rebuild path, uncached
  rb_cold    rebuild path, empty cache (fills it)
  rb_warm    rebuild path, same cache (whole unions from the cache)
  rb_bodies  rebuild path, union cache removed, per-body dilation cache kept (= the cost when every body set changed but no body did)
Every STL / JSON the build writes is byte-compared with rb_off (cached and uncached must be identical), and every STL of rb_off is compared geometrically with
ref (src/mech/mesh_compare.py): the rebuild path may only change the triangulation, not the solid. Writes data/results/studies/su_proof.json.
usage: python3 scripts/su_proof.py [SCRATCH_DIR]"""
import os, sys, shutil, subprocess, time, json, hashlib, glob, struct
import numpy as np
R = os.path.abspath("."); S = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "work/.pipeline/su_proof"); os.makedirs(S, exist_ok=True)
sys.path.insert(0, os.path.join(R, "src/mech")); import mesh_compare as MC
OUTS = ["kit_v22/SET/02_CORE_PCB_CYLINDER/*.stl", "kit_v22/*.stl", "kit_v22/*report*.json"]
RUNS = [("ref", dict(SOLID_UNION_REBUILD="0", SOLID_UNION_CACHE="off"), None), ("rb_off", dict(SOLID_UNION_REBUILD="1", SOLID_UNION_CACHE="off"), None),
        ("rb_cold", dict(SOLID_UNION_REBUILD="1"), "fresh"), ("rb_warm", dict(SOLID_UNION_REBUILD="1"), "keep"), ("rb_bodies", dict(SOLID_UNION_REBUILD="1"), "drop-union")]
cache = os.path.join(S, "cache"); res = dict(runs={})
def stl_tris(p):
    b = open(p, "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    T = np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3).astype(float)
    U, inv = np.unique(T, axis=0, return_inverse=True); return U, inv.reshape(-1, 3)
def files(D):
    out = {}
    for pat in OUTS:
        for f in glob.glob(os.path.join(D, pat)):
            if os.path.isfile(f): out[os.path.relpath(f, D)] = hashlib.sha256(open(f, "rb").read()).hexdigest()
    return out
for name, env_, mode in RUNS:
    D = os.path.join(S, name)
    if not os.path.exists(D): shutil.copytree(os.path.join(R, "work"), D, ignore=shutil.ignore_patterns(".pipeline", "__pycache__"), symlinks=True)
    shutil.copy(os.path.join(R, "src/mech/solid_union.py"), os.path.join(D, "solid_union.py"))
    for p in [f for pat in OUTS[:2] for f in glob.glob(os.path.join(D, pat))]: os.remove(p)                     # this build's outputs only, scratch copy
    stamp = time.strftime("%Y%m%d%H%M%S")                                                                      # set aside, never deleted
    if mode == "fresh" and os.path.isdir(cache): os.rename(cache, f"{cache}.prev.{stamp}")
    if mode == "drop-union" and os.path.isdir(os.path.join(cache, "union")): os.rename(os.path.join(cache, "union"), os.path.join(cache, f"union.prev.{stamp}"))
    env = dict(os.environ, ARX_INNER_JOBS="1", **env_)
    if "SOLID_UNION_CACHE" not in env_: env["SOLID_UNION_CACHE"] = cache
    t0 = time.time(); rc = 0
    for scr in ("hub_v22.py", "parts_v22.py"):
        p = subprocess.run([sys.executable, scr], cwd=D, env=env, capture_output=True, text=True); open(os.path.join(S, f"{name}.{scr}.log"), "w").write(p.stdout + p.stderr); rc |= p.returncode
    res["runs"][name] = dict(rc=rc, wall_s=round(time.time() - t0, 1)); print(name, res["runs"][name], flush=True)
F = {n: files(os.path.join(S, n)) for n, _, _ in RUNS}
for n in ("rb_cold", "rb_warm", "rb_bodies"):
    res["runs"][n]["differ"] = sorted(k for k in F["rb_off"] if F[n].get(k) != F["rb_off"][k]); res["runs"][n]["identical_to_rb_off"] = not res["runs"][n]["differ"]
geo = {}
for k in sorted(F["ref"]):
    if not k.endswith(".stl"): continue
    a, b = os.path.join(S, "ref", k), os.path.join(S, "rb_off", k)
    if F["ref"][k] == F["rb_off"].get(k): geo[k] = dict(identical=True); continue
    VA, FA = stl_tris(a); VB, FB = stl_tris(b); geo[k] = MC.compare(VA, FA, VB, FB); print(k, geo[k], flush=True)
res["geometry_ref_vs_rebuild"] = geo
res["max_dev_um"] = max([g.get("max_dev_um", 0.0) for g in geo.values()] + [0.0]); res["files_compared"] = len(F["rb_off"])
res["cache_mb"] = round(sum(os.path.getsize(f) for f in glob.glob(cache + "/**/*", recursive=True) if os.path.isfile(f)) / 1e6, 1)
os.makedirs("data/results/studies", exist_ok=True); json.dump(res, open("data/results/studies/su_proof.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "geometry_ref_vs_rebuild"}, indent=1))
