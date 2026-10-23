import numpy as np, math, json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import phi_fold_former as pf, rodin_core_v4 as rc, golden_cone_head as g
from zrender_lib import render, rot
fm=pf.Former(); d=json.load(open("out_phifold/PHIFOLD233_spec.json"))
# 1 cut-away 3D render (low-res mesh, 300 deg sector shown via face culling by angle)
V,F,_=pf.build_mesh(fm,du=0.10,narc=5,nfill=2)
W,_=pf.wires(fm,du=0.08)
Vt,Ft=g.merge([g.open_tube(P[::2],pf.WIRE_OD/2,6) for P in W])
cen=V[F].mean(1); keep=np.ones(len(F),bool)
cent=Vt[Ft].mean(1); keept=np.ones(len(Ft),bool)
VA,FA=g.merge([(V,F[keep]),(Vt,Ft[keept])]); col=np.r_[np.zeros(keep.sum()),np.ones(keept.sum())]
render(VA,FA,rot(-58,30),1500,1050,5.2,np.array([0,0,10]),"out_phifold/render_former.png","PHI-FOLD 233: grooved former + sections A–D (face side, ground is below)",col)
# 2 meridian section drawing
s=np.linspace(0,fm.L,6000); r,z,h,k,idx=rc.eval_profile(fm.segs,s)
fig,ax=plt.subplots(figsize=(11,3.6))
ax.fill(r,z,color="#c9ced6"); ax.fill(-r,z,color="#c9ced6")
ax.add_patch(plt.Rectangle((-pf.R_BORE+0.15,-2),2*(pf.R_BORE-0.15),pf.H_TOT,color="#555"))
ax.text(0,pf.H_TOT/2,"ferrite\nrod",color="w",ha="center",va="center",fontsize=7)
ax.fill_between([-pf.R_B,pf.R_B],-6.2,-3.2,color="#adb5bd"); ax.text(60,-5.4,"skid plate",fontsize=7)
ax.fill_between([-pf.R_B+1,pf.R_B-1],-3.2,-0.4,color="#86c5a3",alpha=.7); ax.text(-110,-2.3,"X/Y figure-8 board",fontsize=7)
ax.annotate("",(pf.R_B,-8),(-pf.R_B,-8),arrowprops=dict(arrowstyle="<->"));ax.text(0,-10.5,"OD 233.000 (9.173 in, F13)",ha="center",fontsize=8)
ax.annotate("",(pf.R_T,pf.H_TOT+3),(-pf.R_T,pf.H_TOT+3),arrowprops=dict(arrowstyle="<->"));ax.text(0,pf.H_TOT+4.5,"plateau Ø34 (F9) = OD/φ⁴",ha="center",fontsize=8)
ax.text(55,24,f"slope {math.degrees(pf.ALPHA):.4f}°  (tan = φ⁻³)",fontsize=8)
ax.text(pf.R_B+2,3,"rim 8 (F6)",fontsize=7); ax.text(pf.R_B+2,pf.H_TOT-3,f"H {pf.H_TOT:.3f}",fontsize=7)
ax.text(-40,-1.2+0.6,"underside spiral OUT",fontsize=7); ax.text(-75,22,"face spiral IN",fontsize=7)
ax.text(-9,pf.H_TOT+9,"bore Ø13 (F7)",fontsize=7)
ax.set_aspect("equal"); ax.set_xlim(-125,132); ax.set_ylim(-12,42); ax.set_xlabel("mm")
ax.set_title("Meridian section — ground side is DOWN. Windings: face → plateau → bore (around ferrite) → underside → rim",fontsize=9)
fig.tight_layout(); fig.savefig("out_phifold/drawing_section.png",dpi=160); plt.close()
# 3 top view of one section's path + X/Y layer
fig,axs=plt.subplots(1,2,figsize=(11,5.4))
ss=np.linspace(fm.off["crown"],fm.off["lip"],4000); rr=rc.eval_profile(fm.segs,ss)[0]; th=fm.twist(ss)
cols=["#c0392b","#e67e22","#2471a3","#27ae60"]
for j in range(4): axs[0].plot(rr*np.cos(th+j*np.pi/2),rr*np.sin(th+j*np.pi/2),lw=.35,color=cols[j],label="ABCD"[j])
axs[0].set_title("Face layer, top view: 4 interleaved sections (13 turns each on the slope)",fontsize=9); axs[0].legend(fontsize=7,loc="upper right")
for ax_,zz,c in (("X",pf.XY_Z[0],"#8e44ad"),("Y",pf.XY_Z[1],"#16a085")):
    for P in pf.figure8(ax_,zz)[::2]: axs[1].plot(P[:,0],P[:,1],lw=.5,color=c)
axs[1].set_title("X (purple) and Y (teal) figure-8 quadrature layers",fontsize=9)
for a in axs: a.set_aspect("equal"); a.axis("off")
fig.tight_layout(); fig.savefig("out_phifold/drawing_top_views.png",dpi=150); plt.close()
# 4 field chart
f=d["fields_uT_per_amp"]; dep=f["depth_mm_below_base"]
fig,ax=plt.subplots(figsize=(7.5,4.2))
ax.semilogy(dep,f["Z_all4_sections_Bz"],"o-",label="Z: sections A–D together, 1 A each")
ax.semilogy(dep,f["X_figure8_Bx"],"s-",label="X figure-8 layer, 1 A (Y identical, rotated 90°)")
ax.set_xlabel("depth below base (mm)"); ax.set_ylabel("|B| (µT per amp)"); ax.grid(True,which="both",alpha=.3); ax.legend(fontsize=8)
ax2=ax.twinx(); ax2.plot(dep,d["precession"]["cone_half_angle_deg"],"k--",lw=1); ax2.set_ylabel("precession cone half-angle (°) at I_xy = 3·I_z",fontsize=8)
ax.set_title("Field vs depth and 'tornado' precession angle",fontsize=10)
fig.tight_layout(); fig.savefig("out_phifold/chart_fields.png",dpi=150); plt.close()
print("ok")
