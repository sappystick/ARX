# SUPERSEDED by src/sim/sbq_damp2.py (2026-10-23): bare coil || Rd without the AB1T input network, and its "worst modeled leak 12 mV" rows were computed at 187 mV (the lobes-only diagnostic row of sbq_sim.json). Kept for provenance; see docs/CORRECTIONS.md.
import numpy as np, json, math
from scipy.integrate import solve_ivp
src=open('sim_head1.py').read().split("# ======================= S2")[0]; ns={}; exec(src,ns); wf=ns["wf"]
t,i,vd,vc=wf["100 nF C0G/film"]; g=np.gradient(i,t); g=g/np.max(np.abs(g)); L=176e-6; Rc=10.4
def first_clean(e_pk,Rd,C,thr=1e-7):
    e=lambda tt: e_pk*np.interp(tt,t,g,left=0,right=0)
    def f(tt,y): il,v=y; return [(e(tt)-Rc*il-v)/L,(il-(v/Rd if Rd else 0.0))/C]
    tt=np.arange(0,60e-6,5e-9); s=solve_ivp(f,(0,60e-6),[0,0],t_eval=tt,method="Radau",rtol=1e-8,atol=1e-12,max_step=5e-8)
    v=s.y[1]; bad=np.where(np.abs(v)>thr)[0]; return float(s.t[bad[-1]]*1e6) if len(bad) else 0.0, float(np.max(np.abs(v)))
J=json.load(open("kit_v22/sbq_sim.json")); worst=max(max(r["peak_V"] for r in J["leak"][b].values()) for b in J["leak"])
out={}
for lab,epk in (("board A aligned leak 0.01 mV",1e-5),("worst modeled leak 12 mV",worst)):
    for C in (50e-12,100e-12,200e-12):
        row={}
        for Rd in (None,2200,1000,680,470,330,220):
            tf,pk=first_clean(epk,Rd,C); row["no damping" if Rd is None else f"{Rd} ohm"]=round(tf,1)
        out[f"{lab}, Cself {int(C*1e12)} pF"]=row; print(lab,int(C*1e12),"pF",row)
out["critical damping Rd = 0.5 sqrt(L/C)"]={f"{int(C*1e12)} pF":round(0.5*math.sqrt(L/C)) for C in (50e-12,100e-12,200e-12)}
json.dump(out,open("kit_v22/sbq_damping.json","w"),indent=1); print(out["critical damping Rd = 0.5 sqrt(L/C)"])
