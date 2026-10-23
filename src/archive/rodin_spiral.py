import numpy as np, math, json, csv
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
mu0=4e-7*math.pi
zf=lambda r:13+(116.5-r)*0.359
R_OUT,R_IN=114.0,65.0; N_TURN=6.5; NS=3000
def arm_pts(phi0,mirror_return=True):
    t=np.linspace(0,1,NS)
    r_in=R_OUT-(R_OUT-R_IN)*t; ph_in=phi0+2*np.pi*N_TURN*t                       # in-spiral: phi increases going inward
    r_out=R_IN+(R_OUT-R_IN)*t; ph_out=ph_in[-1]+(2*np.pi*N_TURN*t if mirror_return else -2*np.pi*N_TURN*t)   # return: mirror shape, same circulation (phi keeps increasing)
    r=np.r_[r_in,r_out]; ph=np.r_[ph_in,ph_out]; return np.c_[r*np.cos(ph)*1e-3,r*np.sin(ph)*1e-3,zf(r)*1e-3]
def B(path,P):
    d=np.diff(path,axis=0); m=(path[:-1]+path[1:])/2; r=P[None,:]-m; rn=np.linalg.norm(r,axis=1)[:,None]
    return mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0)
res={}
secs=[arm_pts(math.radians(120*k)) for k in range(3)]
for z in (0.1,0.2,0.3):
    P=np.array([0,0,-z]); Bs=[B(s,P) for s in secs]; tot=sum(Bs)
    res[f"z={int(z*1000)}mm"]=dict(per_section_Bz_uT_per_A=[round(b[2]*1e6,2) for b in Bs],per_section_horizontal_over_vertical_pct=[round(100*math.hypot(b[0],b[1])/abs(b[2]),1) for b in Bs],all_three_Bz_uT_per_A=round(tot[2]*1e6,2))
# cancel test: mirror return with REVERSED circulation (what a literal mirror gives)
canc=[arm_pts(math.radians(120*k),mirror_return=False) for k in range(3)]
P=np.array([0,0,-0.2]); res["literal mirror (circulation reversed) Bz uT/A at 200mm"]=round(B(canc[0],P)[2]*1e6,3)
res["wire_per_arm_m"]=round(float(np.sum(np.linalg.norm(np.diff(secs[0],axis=0),axis=1))),2)
json.dump(res,open("kit_v6/rodin_spiral_test.json","w"),indent=1); print(json.dumps(res,indent=1))
with open("kit_v6/rodin_cone_spiral_paths_mm.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["section","x_mm","y_mm","z_mm"])
    for k,s in enumerate(secs): 
        for p in s[::6]: w.writerow([k+1,round(p[0]*1e3,3),round(p[1]*1e3,3),round(p[2]*1e3,3)])
fig=plt.figure(figsize=(14,6.5),facecolor="white"); ax=fig.add_subplot(121); ax.set_aspect("equal")
for s,c in zip(secs,("#d62728","#1f77b4","#2ca02c")): ax.plot(s[:,0]*1e3,s[:,1]*1e3,c,lw=0.9)
th=np.linspace(0,2*np.pi,400); ax.plot(116.5*np.cos(th),116.5*np.sin(th),"k",lw=2); ax.plot(62.4*np.cos(th),62.4*np.sin(th),"gray",lw=1,ls="--")
ax.set_title("3 intertwined sections: in-spiral + mirror-shaped return\n(same circulation, so the moments ADD); red/blue/green = sections 9/6/3",fontsize=10); ax.axis("off")
ax3=fig.add_subplot(122,projection="3d")
for s,c in zip(secs,("#d62728","#1f77b4","#2ca02c")): ax3.plot(s[::4,0]*1e3,s[::4,1]*1e3,s[::4,2]*1e3,c,lw=0.7)
ax3.set_box_aspect((1,1,0.35)); ax3.view_init(28,-55); ax3.set_title("on the cone surface z = 13 + (116.5 - r) x 0.359",fontsize=10)
plt.tight_layout(); plt.savefig("kit_v6/RENDER/09_RODIN_CONE_SPIRAL.png",dpi=110)
