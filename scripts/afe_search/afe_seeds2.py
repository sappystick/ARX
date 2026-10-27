import os, subprocess, json, sys
B=sys.argv[1]; lo,hi=int(sys.argv[2]),int(sys.argv[3]); extra=json.loads(sys.argv[4]) if len(sys.argv)>4 else {}
rows=[]; bestrow=None
for sd in range(lo,hi):
    env=dict(os.environ, BOARD=B, AFE_SEED=str(sd), **extra)
    r=subprocess.run(["python3","afe_layout.py","--route"],env=env,capture_output=True,text=True,timeout=900)
    t=r.stdout; i=t.find("{"); rep=json.loads(t[i:t.rfind("}")+1])
    n=len(rep["unrouted"])+len(rep["fanout_failed"]); row=dict(seed=sd,unrouted=len(rep["unrouted"]),fanout=len(rep["fanout_failed"]),place=len(rep["placement_errors"]),nets=rep["unrouted"][:4])
    rows.append(row); print(row,flush=True)
    if bestrow is None or n<bestrow[0]: bestrow=(n,sd)
    if n==0 and row["place"]==0: print("FOUND seed",sd,extra,flush=True); break
print("BEST",bestrow)
json.dump(rows,open(f"afe_seeds2_{B}.json","w"),indent=1)
