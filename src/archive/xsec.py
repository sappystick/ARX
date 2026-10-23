import numpy as np, math, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import rodin_core_v3 as m
c=m.Core(); V,F,vol,meta=m.build_mesh(c,m.RES["HIGH"])
s=meta["s"]; r=meta["r"]; D=meta["D_triple"]; P=meta["psi_triple"]
off=c.off
picks=[("Top face, r = %.1f mm",off["top"]+30),("Bore lip (top→bore), r = %.1f mm",off["lip_top"]+6.5),
       ("Bottom on-ramp, r = %.1f mm",off["bottom"]+6),("Bottom full ridge, r = %.1f mm",off["bottom"]+30)]
fig,axs=plt.subplots(4,1,figsize=(10,9),sharex=True)
for ax,(lab,sv) in zip(axs,picks):
    i=np.argmin(np.abs(s-sv)); x=P[i]*r[i]*c.cb
    ax.fill_between(x,D[i],-4,color="#d9dde3",step=None); ax.plot(x,D[i],color="#2c3e50",lw=1)
    pitch=m.LANE_PITCH*r[i]*c.cb
    Cc,Ff=c.tx_params(np.array([s[i]]))
    for k,(name,col,yw,rw) in enumerate([("TX-A","#c0392b",Ff[0]+0.7,0.7),("TX-B","#e67e22",Ff[0]+0.7,0.7),("RX","#2471a3",-0.4,0.4)]):
        ax.add_patch(plt.Circle((k*pitch,yw),rw,color=col,alpha=.85))
        ax.text(k*pitch,4.6,name,ha="center",fontsize=7,color=col)
    ax.set_ylim(-3.2,5.2); ax.set_aspect("equal"); ax.set_title(lab%r[i],fontsize=9,loc="left")
    ax.axhline(0,color="k",lw=.3,ls=":")
axs[-1].set_xlabel("perpendicular distance across lanes (mm)  — one 15° Rodin triple; + = outward from skin")
fig.tight_layout(); fig.savefig("out/preview_lane_cross_sections.png",dpi=160)
