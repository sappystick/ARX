import numpy as np, math, json
src=open('sim_head1.py').read().split("# ======================= S4")[0]; ns={}; exec(src,ns)
Mutual=ns["Mutual"]; TXs=ns["TXs"]; M_mono=ns["M_mono"]
G=json.load(open("kit_v22/sbq_geometry.json")); ZA=[3.18,3.00,2.62,2.44]
CENT=[(50.,50.),(-50.,50.),(-50.,-50.),(50.,-50.)]
grp={k:{l:[] for l in range(4)} for k in range(4)}
for li,polys in G["layers"].items():
    for p in polys:
        p=np.asarray(p); 
        if len(p)<20: continue
        c=p.mean(0); k=int(np.argmin([math.dist(c,q) for q in CENT])); grp[k][int(li)].append(np.c_[p[:,0]*1e-3,p[:,1]*1e-3,np.full(len(p),ZA[int(li)]*1e-3)])
for k in range(4):
    row=[]
    for l in range(4):
        M=Mutual(TXs,grp[k][l])/6.0 if grp[k][l] else 0.0; row.append(M/abs(M_mono))
    print("lobe",k+1,"per layer rel M:",[f"{x:+.4f}" for x in row],"sum",f"{sum(row):+.4f}")
# signed area of each lobe (turns x area) 
for k in range(4):
    ar=0
    for l in range(4):
        for p in grp[k][l]: ar+=0.5*np.sum(p[:-1,0]*p[1:,1]-p[1:,0]*p[:-1,1])
    print("lobe",k+1,"signed area-turns (mm2 x1e6 m2):",round(ar*1e6,1))
