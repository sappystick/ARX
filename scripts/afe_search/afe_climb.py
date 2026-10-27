"""Greedy part-nudge search for the AB1 receive stage (Step 12). Starts from the given nudges, tries +-0.3 / +-0.6 mm moves of candidate parts in parallel,
accepts the best move that lowers (unrouted + 3*fanout + 5*placement errors), stops at 0 or when no move helps.
usage: python3 afe_climb.py BOARD 'REF,REF,...' 'start nudges' [UAROTS]"""
import os, sys, json, subprocess, itertools
from concurrent.futures import ThreadPoolExecutor
B = sys.argv[1]; cands = sys.argv[2].split(","); nud = {k.split(":")[0]: (float(k.split(":")[1]), float(k.split(":")[2])) for k in sys.argv[3].split(",") if k}
rots = sys.argv[4] if len(sys.argv) > 4 else ""
def spec(n): return ",".join(f"{r}:{dx:.2f}:{dy:.2f}" for r, (dx, dy) in n.items() if abs(dx) > 1e-9 or abs(dy) > 1e-9)
def run(n):
    env = dict(os.environ, BOARD=B, AFE_NUDGE=spec(n)); 
    if rots: env["AFE_UAROTS"] = rots
    r = subprocess.run(["python3", "afe_layout.py", "--route", "--diag"], env=env, capture_output=True, text=True, timeout=900)
    t = r.stdout; i = t.find("{")
    try: rep = json.loads(t[i:t.find("\nDIAG") if "\nDIAG" in t else t.rfind("}") + 1] if False else t[i:t.rfind("}") + 1])
    except Exception: return (999, 0), ["error"], n
    import re
    reach = sum(int(m) for m in re.findall(r"DIAG [^\n]*?reach=(\d+)", t))               # trapped-pocket sizes: bigger = closer to free
    return (len(rep["unrouted"]) + 3 * len(rep["fanout_failed"]) + 5 * len(rep["placement_errors"]), -reach), rep["unrouted"], n
best = run(nud); print("start", best[0], best[1], spec(nud), flush=True)
STEPS = [(0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)]
for sweep in range(8):
    trials = []
    for ref in cands:
        for dx, dy in STEPS:
            n2 = dict(nud); ox, oy = n2.get(ref, (0.0, 0.0)); n2[ref] = (ox + dx, oy + dy); trials.append(n2)
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(run, trials))
    res.sort(key=lambda t: t[0])
    print("sweep", sweep, "best of", len(res), ":", res[0][0], res[0][1], spec(res[0][2]), flush=True)
    if res[0][0] >= best[0]: break
    best = res[0]; nud = best[2]
    if best[0][0] == 0: break
json.dump(dict(score=best[0], unrouted=best[1], nudges=spec(best[2])), open(f"afe_climb_{B}.json", "w"), indent=1)
print("FINAL", best[0], best[1], spec(best[2]))
