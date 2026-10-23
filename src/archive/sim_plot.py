import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=json.load(open("out_phifold/simulation_results.json"))
fig,ax=plt.subplots(2,2,figsize=(12,8.5))
# A field vs depth for drive currents
dep=d["B_per_sqrtW_uT"]["depth_mm"]
for r in d["power_sweep"]:
    I=r["I_pk_A"]; s=r["B_100mm_uT"]/d["power_sweep"][0]["B_100mm_uT"]*2
ps=d["power_sweep"]; z=np.array([100,200,300])
for r in ps: ax[0,0].semilogy(z,[r["B_100mm_uT"],r["B_200mm_uT"],r["B_300mm_uT"]],"o-",label=f'{r["I_pk_A"]} A peak ({r["avg_copper_W"]} W avg)')
ax[0,0].set_title("A. Field at turn-off vs depth for each drive current",fontsize=10); ax[0,0].set_xlabel("depth (mm)"); ax[0,0].set_ylabel("Bz (µT)"); ax[0,0].legend(fontsize=7); ax[0,0].grid(alpha=.3,which="both")
# B detection depth vs current (realistic noise)
rn=d["air_test_depth_mm"]["realistic field 1 uV (EMI + ground residue)"]
for t,v in rn.items():
    ax[0,1].plot([4,10,20],[v["delay 10us, 4A"],v["delay 10us, 10A"],v["delay 10us, 20A"]],"o-",label=t.split(" (")[0])
ax[0,1].set_title("B. Air-test detection depth vs peak current\n(10 µs sample delay, 1 µV noise floor)",fontsize=10); ax[0,1].set_xlabel("peak current (A)"); ax[0,1].set_ylabel("depth (mm)"); ax[0,1].legend(fontsize=7); ax[0,1].grid(alpha=.3)
# C VLF quadrature response vs frequency
fq=[1,3,10,30,100]
for nm,v in d["vlf_quadrature_response_norm"].items(): ax[1,0].semilogx(fq,list(v.values()),"o-",label=f"{nm} gold nugget")
ax[1,0].set_title("C. Target response vs frequency (VLF quadrature, normalised)\nsmall gold peaks high, big gold peaks low",fontsize=10); ax[1,0].set_xlabel("frequency (kHz)"); ax[1,0].legend(fontsize=8); ax[1,0].grid(alpha=.3,which="both")
# D B per sqrt W comparison
for k,v in d["B_per_sqrtW_uT"].items():
    if k=="depth_mm": continue
    ax[1,1].semilogy(dep,v,"o-" if "PHI" in k else "--",label=k,lw=2 if "PHI" in k else 1)
ax[1,1].set_title("D. Field per √watt, equal copper volume (geometry efficiency)",fontsize=10); ax[1,1].set_xlabel("depth (mm)"); ax[1,1].set_ylabel("µT/√W"); ax[1,1].legend(fontsize=7); ax[1,1].grid(alpha=.3,which="both")
fig.tight_layout(); fig.savefig("out_phifold/simulation_dashboard.png",dpi=140)
