import numpy as np, math, json, itertools
src=open('sim_head1.py').read().split("# ======================= S4")[0]; ns={}; exec(src,ns)
Mutual=ns["Mutual"]; TXs=ns["TXs"]; M_mono=ns["M_mono"]
import sbq_gen2 as g
ZA=[3.18,3.00,2.62,2.44]
def xyz(p,z): p=g.rot(np.asarray(p,float),DEG); return np.c_[p[:,0]*1e-3,p[:,1]*1e-3,np.full(len(p),z*1e-3)]
import sys
BOARD=sys.argv[1] if len(sys.argv)>1 else 'A'; ZB=[2.08,1.90,1.52,1.34]; Z=ZA if BOARD=='A' else ZB; DEG=0.0 if BOARD=='A' else 45.0
PADS=(g.P1,g.P2) if BOARD=='A' else (g.P1B,g.P2B)          # board B terminals end at r23 (sbq_gen2.PB_R)
layers,vias=g.build(pads=PADS); S=[];E=[]
for k in range(4): _,_,s,e=g.lobe(k); S.append(s); E.append(e)
# lobes (spirals + stubs only): paths of length > 40 points
Ml=0.0
for li,polys in layers.items():
    for p in polys:
        if len(p)>40 and not any(abs(p[0]-np.array(q)).max()<1e-9 for q in [PADS[0]]): 
            if np.hypot(*(p.mean(0)))>20: Ml+=Mutual(TXs,[xyz(p,Z[int(li)])])/6.0
print("lobe sum rel M:",Ml/abs(M_mono))
close=Mutual(TXs,[xyz([PADS[1],PADS[0]],Z[0])])/6.0
radii=[6,7,8,9,10,11,12,13,14,16,18,20]
def term(name,r):
    rad=dict(g.RAD); rad[{"l1":"a","l2":"b","l3":"c","t1":"t1","t2":"t2"}[name]]=r; lp=g.link_paths(S,E,rad,PADS)
    z={"l1":Z[3],"l2":Z[0],"l3":Z[3],"t1":Z[0],"t2":Z[0]}[name]; p=lp[name]
    if name=="t1": p=p[::-1]
    return Mutual(TXs,[xyz(p,z)])/6.0
T={n:{r:term(n,r) for r in radii} for n in ("l1","l2","l3","t1","t2")}
best=(1e9,None)
for ra,rb,rc,r1,r2 in itertools.product(radii,repeat=5):
    if not (r2<r1-3): continue
    tot=Ml+close+T["l1"][ra]+T["l2"][rb]+T["l3"][rc]+T["t1"][r1]+T["t2"][r2]
    if abs(tot)<best[0]: best=(abs(tot),(ra,rb,rc,r1,r2))
print("best |M|/M_mono",best[0]/abs(M_mono),"radii",best[1])
ra,rb,rc,r1,r2=best[1]
try: J=json.load(open("kit_v22/sbq_radii.json")); J=J if "A" in J or "B" in J else {}
except Exception: J={}
J[BOARD]=dict(a=ra,b=rb,c=rc,t1=r1,t2=r2); json.dump(J,open("kit_v22/sbq_radii.json","w")); print("saved",J)
