import numpy as np, math, json, re
from scipy.special import ellipk, ellipe
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
mu0=4e-7*math.pi; OUT={}
# ---------- (1) first clean gate vs null depth (real TX stage, as-built and film clamp)
src=open('sim_head1.py').read().split("# ======================= S2")[0]; ns={}; exec(src,ns)
wf=ns["wf"]; M_mono_uH=290.4/max(np.max(np.abs(np.gradient(wf["100 nF C0G/film"][1],wf["100 nF C0G/film"][0]))),1)*1e6   # from the earlier unnulled pickup: V/(A/s)
Mm=290.4/max(max(np.max(np.abs(np.gradient(w[1],w[0]))) for w in wf.values()),1)
def t_first(case,null,thr=1e-7):
    t,i,vd,vc=wf[case]; emf=null*Mm*np.abs(np.gradient(i,t)); bad=np.where(emf>thr)[0]; return float(t[bad[-1]+1]*1e6) if len(bad) else 0.0
nulls=[8e-3,2.5e-4,5e-5,1e-5,2e-6]; rows={}
for case in ("as built: 2 x 100 nF X7R, with DC-bias derating","100 nF C0G/film"): rows[case]={f"{n:g}":round(t_first(case,n),2) for n in nulls}
OUT["first_clean_gate_us_vs_null"]=rows; print(rows)
# trim DAC residual
OUT["adaptive_null"]=dict(leak_range=0.04,residual_12bit=round(0.04/4096/2,7),residual_14bit=round(0.04/16384/2,8),note="trim range +/-2% of the unnulled coupling; residual = half an LSB")
# ---------- (2) noise matching: depth multiplier from the model's own slope (0.22 power of SNR)
for nd in (4.2,1.7,1.2,0.8): OUT.setdefault("depth_multiplier_vs_input_noise",{})[f"{nd} nV/rtHz"]=round((4.2/nd)**0.22,2)
# ---------- (3) eddy decay of a full copper plane on a board (concentric ring network)
def plane_modes(a_mm,t_um,rho=1.72e-8,N=24):
    a=a_mm*1e-3; t=t_um*1e-6; dr=a/N; r=(np.arange(N)+0.5)*dr; R=rho*2*np.pi*r/(t*dr)
    L=np.zeros((N,N))
    for i in range(N):
        for j in range(N):
            if i==j: L[i,j]=mu0*r[i]*(math.log(8*r[i]/(dr/4))-2)
            else:
                k2=4*r[i]*r[j]/((r[i]+r[j])**2); k=math.sqrt(k2); L[i,j]=mu0*math.sqrt(r[i]*r[j])*((2/k-k)*ellipk(k2)-2/k*ellipe(k2))
    w,V=np.linalg.eig(np.linalg.solve(L,np.diag(R))); o=np.argsort(w.real); w=w.real[o]; V=V[:,o].real
    flux=np.pi*r**2; I0=-np.linalg.solve(L,flux)                       # per tesla step
    c=np.linalg.solve(V,I0); m0=float(abs(np.sum(I0*np.pi*r**2)))
    return dict(tau_us=round(1e6/w[0],2),second_mode_us=round(1e6/w[1],2),m0_Am2_per_T=m0), (w,V,c,r)
for nm,(a,t) in {"1 oz plane D78":(39,35),"2 oz plane D78":(39,70),"cup foil D81, 50 um":(40.5,50)}.items():
    res,_=plane_modes(a,t); a_g=(3*1e-3/(4*math.pi*19300))**(1/3); m_nug=2*math.pi*a_g**3/mu0
    res["moment_vs_1g_gold_nugget"]=round(res["m0_Am2_per_T"]/m_nug); OUT.setdefault("plane_eddy",{})[nm]=res
print(OUT["plane_eddy"])
# a 12-slice plane: each slice behaves like a disc whose loop size is about half the slice width at mid radius
for nm,(a,t) in {"1 oz, 12 radial slits (loop radius about 5 mm)":(5,35),"1 oz, meshed (loop radius about 1 mm)":(1,35)}.items():
    res,_=plane_modes(a,t,N=12); OUT["plane_eddy"][nm]=dict(tau_us=res["tau_us"],note="scaling estimate: slits limit the loop size")
# ---------- (4) thermal K/W with better potting
t=open('sim_head2.py').read().split("cases=")[0].replace("kr=kz=0.25                                           # syntactic silicone","kr=kz=KPOT").replace("def build(","KPOT=0.25\ndef build(",1); th={}; exec(t,th)
rows={}
for nm,k in (("syntactic silicone 0.25 W/mK",0.25),("alumina-filled silicone 1.0 W/mK",1.0),("alumina-filled epoxy 1.8 W/mK",1.8)):
    th["KPOT"]=k; T=th["build"](0.12,0.30,0.46,0.25,25.0); rows[nm]=dict(max_C=round(float(np.nanmax(T)),1),K_per_W=round((float(np.nanmax(T))-25)/1.13,2))
OUT["thermal_potting"]=rows; print(rows)
json.dump(OUT,open("kit_v21/sim_cage_rx.json","w"),indent=1,default=float)
# ---------- figure
fig,ax=plt.subplots(1,3,figsize=(18,5))
for case,c in (("as built: 2 x 100 nF X7R, with DC-bias derating","tab:red"),("100 nF C0G/film","tab:green")): ax[0].semilogx(nulls,[t_first(case,n) for n in nulls],marker="o",color=c,label=case[:28])
ax[0].set_xlabel("residual null (relative to the unnulled coupling)"); ax[0].set_ylabel("first clean gate (us)"); ax[0].invert_xaxis(); ax[0].legend(); ax[0].grid(alpha=.3,which="both"); ax[0].set_title("What an adaptive null buys")
res,(w,V,c,r)=plane_modes(39,35); tt=np.linspace(0,60e-6,300); m=np.array([abs(np.sum((V@(c*np.exp(-w*x)))*np.pi*r**2)) for x in tt]); ax[1].semilogy(tt*1e6,m/m[0]+1e-9); ax[1].set_ylim(1e-3,1.1); ax[1].set_title("eddy decay of one full 1 oz copper plane, D78 (tau %.0f us)"%res["tau_us"]); ax[1].set_xlabel("us"); ax[1].grid(alpha=.3,which="both")
ax[2].bar(range(3),[OUT["thermal_potting"][k]["K_per_W"] for k in OUT["thermal_potting"]]); ax[2].set_xticks(range(3)); ax[2].set_xticklabels(["silicone\n0.25","alumina\nsilicone 1.0","alumina\nepoxy 1.8"]); ax[2].set_ylabel("K per W (vault hot spot)"); ax[2].set_title("heat path: potting conductivity")
plt.tight_layout(); plt.savefig("kit_v21/SIM_CAGE_RX.png",dpi=90); print("ok")
