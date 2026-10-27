"""Failed-net-first iteration for the AB1 router (Step 12): run, move every net that failed to the front of the order, rerun; keep the best result.
usage: python3 afe_iter.py BOARD MODE(PRE|MID) MAXIT"""
import os, sys, json, subprocess
B, MODE, MAXIT = sys.argv[1], sys.argv[2], int(sys.argv[3])
order = []; best = None; hist = []
for it in range(MAXIT):
    env = dict(os.environ, BOARD=B); env["AFE_" + MODE] = ",".join(order); env.update({k: v for k, v in os.environ.items() if k.startswith("AFE_") and k != "AFE_" + MODE})
    r = subprocess.run(["python3", "afe_layout.py", "--route"], env=env, capture_output=True, text=True, timeout=900)
    t = r.stdout; i = t.find("{"); rep = json.loads(t[i:t.rfind("}") + 1])
    failed = list(dict.fromkeys([f.split(":")[0] for f in rep["unrouted"]]))
    fan = rep["fanout_failed"]; score = len(rep["unrouted"]) + 3 * len(fan) + 5 * len(rep["placement_errors"])
    hist.append(dict(it=it, order=list(order), unrouted=rep["unrouted"], fanout_failed=fan, score=score))
    print(it, MODE, ",".join(order) or "-", "| unrouted", len(rep["unrouted"]), "fanout", len(fan), "score", score, rep["unrouted"][:4], flush=True)
    if best is None or score < best["score"]: best = hist[-1]
    if score == 0: break
    new = [n for n in failed + [f.split(":")[0] for f in fan if ":" in f] if n]
    nxt = list(dict.fromkeys(new + order))
    if nxt == order: break
    order = nxt
json.dump(dict(best=best, history=hist), open(f"afe_iter_{B}_{MODE}.json", "w"), indent=1)
print("BEST", best["score"], best["order"])
