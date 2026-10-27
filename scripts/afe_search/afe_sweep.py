"""One greedy sweep of part nudges for the AB1 router (Step 12); prints the best trials and writes the best nudge set to afe_sweep_<board>.json.
usage: python3 afe_sweep.py BOARD 'REF,REF,...' 'base nudges' UAROTS"""
import os, sys, json, subprocess, re
from concurrent.futures import ThreadPoolExecutor
B, cands, base, rots = sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4]
def parse(s): return {k.split(":")[0]: (float(k.split(":")[1]), float(k.split(":")[2])) for k in s.split(",") if k}
def spec(n): return ",".join(f"{r}:{dx:.2f}:{dy:.2f}" for r, (dx, dy) in n.items() if abs(dx) > 1e-9 or abs(dy) > 1e-9)
def run(n):
    env = dict(os.environ, BOARD=B, AFE_NUDGE=spec(n), AFE_UAROTS=rots)
    r = subprocess.run(["python3", "afe_layout.py", "--route", "--diag"], env=env, capture_output=True, text=True, timeout=1200)
    t = r.stdout; i = t.find("{")
    try: rep = json.loads(t[i:t.rfind("}") + 1])
    except Exception: return (999, 0), ["error"], n
    reach = sum(int(m) for m in re.findall(r"DIAG [^\n]*?reach=(\d+)", t))
    return (len(rep["unrouted"]) + 3 * len(rep["fanout_failed"]) + 5 * len(rep["placement_errors"]), -reach), rep["unrouted"], n
base_n = parse(base); trials = [base_n]
for ref in cands:
    for dx, dy in [(0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)]:
        n2 = dict(base_n); ox, oy = n2.get(ref, (0.0, 0.0)); n2[ref] = (ox + dx, oy + dy); trials.append(n2)
with ThreadPoolExecutor(4) as ex: res = list(ex.map(run, trials))
b0 = res[0]; res.sort(key=lambda t: t[0])
print("base", b0[0], b0[1])
for sc, u, n in res[:5]: print(sc, u, spec(n))
json.dump(dict(score=list(res[0][0]), unrouted=res[0][1], nudges=spec(res[0][2]), base_score=list(b0[0])), open(f"afe_sweep_{B}.json", "w"), indent=1)
