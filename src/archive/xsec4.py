import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import rodin_core_v4 as m
c=m.Core()
fig,axs=plt.subplots(3,2,figsize=(12,8.5),sharex=True)
for col,name in enumerate(m.VARIANTS):
    m.PATTERN=m.VARIANTS[name]
    V,F,vol,meta=m.build_mesh(c,m.RES["HIGH"])
    s=meta["s"]; r=meta["r"]; D=meta["D_triple"]; P=meta["psi_triple"]
    picks=[("Top face",c.off["top"]+30),("Bottom on-ramp",c.off["bottom"]+6),("Bottom full ridge",c.off["bottom"]+30)]
    for row,(lab,sv) in enumerate(picks):
        ax=axs[row,col]; i=np.argmin(np.abs(s-sv)); x=P[i]*r[i]*c.cb
        pitch=m.LANE_PITCH*r[i]*c.cb
        # show 1.33 triples for context
        xx=np.concatenate([x-3*pitch,x,x+3*pitch]); dd=np.concatenate([D[i]]*3)
        ax.fill_between(xx,dd,-4,color="#d9dde3"); ax.plot(xx,dd,color="#2c3e50",lw=1)
        Cc,Ff=c.tx_params(np.array([s[i]]))
        for k in range(-3,6):
            role=m.PATTERN[k%3]
            if role=="TX": ax.add_patch(plt.Circle((k*pitch,Ff[0]+0.7),0.7,color="#c0392b"))
            else: ax.add_patch(plt.Circle((k*pitch,-0.4),0.4,color="#2471a3"))
            if -1.6*pitch<k*pitch<4.6*pitch: ax.text(k*pitch,4.7,role,ha="center",fontsize=7,color="#c0392b" if role=="TX" else "#2471a3")
        ax.set_xlim(-1.6*pitch,4.6*pitch); ax.set_ylim(-3.2,5.4); ax.set_aspect("equal")
        ax.set_title(f"{'A: TX on 1-2-4-8-7-5, RX on 3-6-9' if col==0 else 'B: RX on 1-2-4-8-7-5, TX on 3-6-9'}\n{lab}, r = {r[i]:.1f} mm" if row==0 else f"{lab}, r = {r[i]:.1f} mm",fontsize=9,loc="left")
for ax in axs[-1]: ax.set_xlabel("distance across lanes (mm); + = outward from skin")
fig.tight_layout(); fig.savefig("out_v4/compare_lane_cross_sections.png",dpi=150)
