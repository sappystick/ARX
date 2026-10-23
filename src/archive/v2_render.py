import numpy as np, math, json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g
from zrender_lib import render, rot
for notch,tag,title in ((False,"A_gallery","v2A golden band + centre lead gallery (recommended)"),(True,"B_rim_notches","v2B golden band + 4 rim exit notches")):
    v2.NOTCHES=notch; fm=v2.Former()
    V,F,_=v2.build_mesh(fm,du=0.09,narc=5,nfill=10,nnotch=4)
    Hv,Hf=v2.hub(gallery=not notch)
    VA,FA=g.merge([(V,F),(Hv,Hf)]); col=np.r_[np.zeros(len(F)),np.zeros(len(Hf))]
    render(VA,FA,rot(-55,15),1400,1000,5.3,np.array([0,0,8]),f"out_phifold_v2/render_{tag}.png",title,col)
# close-up of a rim notch on B
v2.NOTCHES=True; fm=v2.Former(); V,F,_=v2.build_mesh(fm,du=0.05,narc=7,nfill=16)
th=fm.twist(fm.off["rim"]); a=th
c=np.array([v2.R_B*math.cos(a),v2.R_B*math.sin(a),6.5])
cen=V[F].mean(1); sel=np.linalg.norm(cen-c,axis=1)<26
render(V,F,rot(-75,-math.degrees(a)+90),1200,900,22,c,"out_phifold_v2/render_B_notch_closeup.png","v2B rim exit notch beside lane A (lead channel, 6 × 3 mm)",None,sel)
print("ok")
