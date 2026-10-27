"""Parallel evaluation of environment configurations for the AB1 router (Step 12).
usage: python3 afe_grid.py BOARD 'JSON list of env dicts' [workers]"""
import os, sys, json, subprocess, re
from concurrent.futures import ThreadPoolExecutor
B = sys.argv[1]; cfgs = json.loads(sys.argv[2]); W = int(sys.argv[3]) if len(sys.argv) > 3 else 4
def run(c):
    env = dict(os.environ, BOARD=B, **{k: str(v) for k, v in c.items()})
    r = subprocess.run(["python3", "afe_layout.py", "--route", "--diag"], env=env, capture_output=True, text=True, timeout=1200)
    t = r.stdout; i = t.find("{")
    try: rep = json.loads(t[i:t.rfind("}") + 1])
    except Exception: return (999, 0), c, ["error"]
    reach = sum(int(m) for m in re.findall(r"DIAG [^\n]*?reach=(\d+)", t))
    return (len(rep["unrouted"]) + 3 * len(rep["fanout_failed"]) + 5 * len(rep["placement_errors"]), -reach), c, rep["unrouted"]
with ThreadPoolExecutor(W) as ex: res = sorted(ex.map(run, cfgs), key=lambda t: t[0])
for sc, c, u in res[:12]: print(sc, c, u[:4])
json.dump([dict(score=list(sc), cfg=c, unrouted=u) for sc, c, u in res], open(f"afe_grid_{B}.json", "w"), indent=1)
