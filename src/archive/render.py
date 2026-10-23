import numpy as np, math, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import rodin_core_v3 as m
c=m.Core()
# 1 cross-section
s=np.linspace(0,c.Ltot,20000); r,z,h,k,idx=m.eval_profile(c.segs,s); nr,nz=np.sin(h),-np.cos(h)
C,F=c.tx_params(s)
fig,ax=plt.subplots(figsize=(11,4.2))
ax.fill(r,z,color="#d9dde3",label="core skin (G2 profile)")
ax.plot(r+F*nr,z+F*nz,color="#c0392b",lw=1.2,label="TX seat floor F(s)")
ax.plot(r+(F+0.7)*nr,z+(F+0.7)*nz,color="#e67e22",lw=1,ls="--",label="TX wire centre (100/38, OD 1.40)")
ax.plot(r+C*nr,z+C*nz,color="#2c3e50",lw=1,label="TX ridge crown C(s)")
ax.plot(r-0.4*nr,z-0.4*nz,color="#2471a3",lw=1,ls=":",label="RX wire centre (40/40, OD 0.80)")
ax.axvline(m.R_IN,color="k",lw=.4,ls=":");ax.axvline(m.R_OUT,color="k",lw=.4,ls=":")
ax.set_aspect("equal");ax.set_xlabel("r (mm)");ax.set_ylabel("z (mm)");ax.set_title("Meridian section: G2 lips, R_out nose, ridge on/off ramps")
ax.legend(fontsize=7,loc="upper center",ncol=3);ax.set_xlim(40,130);fig.tight_layout();fig.savefig("out/preview_cross_section.png",dpi=160)
# 2 top/bottom wire map
coils=m.wire_centerlines(c,m.RES["MEDIUM"])
col={"A":"#c0392b","B":"#e67e22","RX":"#2471a3"}
fig,axs=plt.subplots(1,2,figsize=(12,6))
for side,ax in zip(("top (z>0 half)","bottom (z<0 half)"),axs):
    for d,cl in coils.items():
        P=cl["pts"]; msk=P[:,2]>0 if side.startswith("top") else P[:,2]<=0
        Q=P.copy(); Q[~msk]=np.nan
        ax.plot(Q[:,0],Q[:,1],color=col[cl["family"]],lw=.6)
    for n in range(72):
        a=n*m.LANE_PITCH; ax.text(129*math.cos(a),129*math.sin(a),str(n%9+1),fontsize=5,ha="center",va="center")
    ax.set_aspect("equal");ax.axis("off");ax.set_title("Wire centrelines, "+side+"\nred=TX A(1,4,7) orange=TX B(2,5,8) blue=RX(3,6,9)",fontsize=9)
fig.tight_layout(rect=(0,0,1,0.95));fig.savefig("out/preview_lane_map.png",dpi=160)
# 3 3D sector render
V,Fc,vol,meta=m.build_mesh(c,m.RES["HIGH"])
cen=V[Fc].mean(1); ang=np.degrees(np.arctan2(cen[:,1],cen[:,0]))
sel=(ang>-12)&(ang<12)
tri=V[Fc[sel]]
n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); n/=np.linalg.norm(n,axis=1)[:,None]
L=np.array([0.4,-0.5,0.75]);L/=np.linalg.norm(L)
sh=np.clip(n@L,0,1)*0.75+0.25
for view,elev in (("top",38),("bottom",-38)):
    fig=plt.figure(figsize=(10,7));ax=fig.add_subplot(projection="3d")
    pc=Poly3DCollection(tri,facecolors=plt.cm.Greys(0.25+0.6*sh if view=="top" else 0.25+0.6*np.clip(n@np.array([0.4,-0.5,-0.75])/1.0,0,1)),linewidths=0)
    ax.add_collection3d(pc)
    ax.set_xlim(45,128);ax.set_ylim(-28,28);ax.set_zlim(-20,15);ax.set_box_aspect((83,56,35))
    ax.view_init(elev=elev,azim=-150);ax.axis("off")
    ax.set_title(f"24-degree sector, {view} face (HIGH mesh)")
    fig.tight_layout();fig.savefig(f"out/preview_sector_{view}.png",dpi=150)
print("ok", sel.sum())
