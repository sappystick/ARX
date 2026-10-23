import numpy as np, math, json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import golden_cone_head as g, rodin_core_v4 as rc
from zrender_lib import render, rot
cone=g.Cone(); pos,order=g.layout(); fo=g.firing_order(); d=json.load(open("out_cones/phyllo34_spec.json"))
# 1 layout drawing
fig,ax=plt.subplots(figsize=(8,8))
ax.add_patch(plt.Circle((0,0),g.R_OUT,fc="#e9ecef",ec="k"))
ax.add_patch(plt.Circle((0,0),g.R_FACE,fc="#f8f9fa",ec="#555",ls="--"))
rank={c:k+1 for k,c in enumerate(fo)}
for i,(rg,_,x,y,a) in enumerate(pos):
    ax.add_patch(plt.Circle((x,y),g.R_B,fc="#f5c06b" if rg=="outer" else "#9ec5fe",ec="k",lw=.8))
    ax.add_patch(plt.Circle((x,y),g.R_T,fc="#ffffff",ec="#888",lw=.5))
    ax.add_patch(plt.Circle((x,y),g.R_BORE,fc="#333",ec="none"))
    ax.text(x,y-g.R_B*0.62,str(rank[i]),ha="center",va="center",fontsize=7,color="#b00")
for k,lab in enumerate("ABC"):
    a=math.radians(90+120*k); ax.annotate(f"Section {lab} rail",(g.R_OUT*math.cos(a),g.R_OUT*math.sin(a)),
        (1.12*g.R_OUT*math.cos(a),1.12*g.R_OUT*math.sin(a)),ha="center",fontsize=9,arrowprops=dict(arrowstyle="->"))
ax.set_xlim(-150,150);ax.set_ylim(-150,150);ax.set_aspect("equal");ax.axis("off")
ax.set_title("PHYLLO-34 face layout (9.7 in): 21 outer + 13 inner golden cones\nred numbers = golden-stride firing order",fontsize=10)
fig.tight_layout();fig.savefig("out_cones/drawing_layout_firing_order.png",dpi=150);plt.close()
# 2 cone section drawing
s=np.linspace(0,cone.L,4000);r,z,h,k,idx=rc.eval_profile(cone.segs,s)
fig,ax=plt.subplots(figsize=(9,5))
ax.fill(np.r_[r,-r[::-1]],np.r_[z,z[::-1]],color="#d9dde3")
ax.fill(r,z,color="#c9ced6"); ax.fill(-r,z,color="#c9ced6")
W,sw=g.cone_wires(cone,0.05); P=W[0]; rr=np.hypot(P[:,0],P[:,1])
ax.plot(rr,P[:,2],color="#c0392b",lw=1.2,label="winding A centreline (r,z)")
ax.axhline(0,color="k",lw=.6); ax.fill_between([-20,20],-3,0,color="#adb5bd",alpha=.6)
geo=d["geometry"]
ax.annotate("",(g.R_B,-1.2),(-g.R_B,-1.2),arrowprops=dict(arrowstyle="<->"));ax.text(0,-2.3,f"base Ø {2*g.R_B:.3f}",ha="center",fontsize=8)
ax.annotate("",(g.R_T,g.H+1.2),(-g.R_T,g.H+1.2),arrowprops=dict(arrowstyle="<->"));ax.text(0,g.H+1.7,f"tip Ø {2*g.R_T:.3f} (= base/φ²)",ha="center",fontsize=8)
ax.annotate("",(17.5,g.H),(17.5,0),arrowprops=dict(arrowstyle="<->"));ax.text(17.9,g.H/2,f"H {g.H:.3f}\n(= R_b/√φ)",fontsize=8)
ax.text(-15,6,f"slope {math.degrees(g.ALPHA):.4f}°\n= arccos(1/φ)",fontsize=8)
ax.text(-2.6,4,f"bore\nØ{2*g.R_BORE:.1f}",fontsize=7,color="w",ha="center")
ax.text(7,-2.4,"face plate 3.0",fontsize=7)
ax.set_aspect("equal");ax.set_xlim(-21,24);ax.set_ylim(-3.5,15.5);ax.legend(fontsize=8,loc="upper right")
ax.set_title("Golden cone bobbin, meridian section (mm). Wire: tunnel under base → up slope → tip → down bore",fontsize=9)
fig.tight_layout();fig.savefig("out_cones/drawing_cone_section.png",dpi=160);plt.close()
# 3 field chart
f=d["field_uT_per_amp_vs_depth_below_tips_mm"];dep=f["depths"]
fig,ax=plt.subplots(figsize=(8,4.6))
for kk,v in f.items():
    if kk=="depths" or "on axis" in kk and "M1" not in kk: continue
    ax.semilogy(dep,v,marker="o",ms=3,label=kk.replace(" | "," — "))
ax.set_xlabel("depth below cone tips (mm)");ax.set_ylabel("|B| per amp per winding (µT)")
ax.grid(True,which="both",alpha=.3);ax.legend(fontsize=7);ax.set_title("Field vs depth by drive pattern (Biot–Savart on real winding paths)",fontsize=10)
fig.tight_layout();fig.savefig("out_cones/chart_field_vs_depth.png",dpi=150);plt.close()
# 4 3D renders
Vc,Fc,_=g.build_cone_mesh(cone,0.12,0.06,7,5)
Wt=g.merge([g.open_tube(P_,g.WIRE_OD/2,8) for P_ in g.cone_wires(cone,0.08)[0]])
V,F=g.merge([(Vc,Fc),Wt]); col=np.r_[np.zeros(len(Fc)),np.ones(len(Wt[1]))]
render(V,F,rot(-55,25),1200,900,26,np.array([0,0,6]),"out_cones/render_single_cone.png","Golden cone bobbin with 3 flush Litz windings (A, B, C)",col)
Va,Fa,_=g.build_cone_mesh(cone,0.7,0.35,3,2)
parts=[(g.place(Va,x,y,a),Fa) for (_,_,x,y,a) in pos]
plate=g.plate_with_holes([(x,y,g.R_BORE) for (_,_,x,y,a) in pos],g.R_OUT,-3,0,n_out=360,n_hole=16,grid=6)
rim=g.revolve([(g.R_FACE,0),(g.R_OUT,0),(g.R_OUT,4),(g.R_FACE-1.2,4),(g.R_FACE-1.2,3),(g.R_FACE,3)],nseg=360)
V,F=g.merge([plate,rim]+parts)
render(V,F,rot(-50,20),1400,1050,4.4,np.array([0,0,0]),"out_cones/render_search_head.png","PHYLLO-34 search head face (cones point toward the ground)",None)
print("ok")
