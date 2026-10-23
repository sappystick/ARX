import numpy as np, math, pickle
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from render_v6 import render, load_stl, clip_y, cyl
D="kit_v7/CASSETTES_LOW"
cols={1:(0.20,0.68,0.70),2:(0.33,0.60,0.88),3:(0.55,0.52,0.92),4:(0.76,0.48,0.86),5:(0.92,0.48,0.68),6:(0.96,0.62,0.42)}
def parts(cut=False,explode=False):
    P=[]; dz={7:0,6:26,5:52,4:78,3:104,2:130,1:156} if explode else {k:0 for k in range(1,8)}
    def add(S,c,name,k=0,a=1.0):
        V,F=S; V=V+[0,0,dz.get(k,0)]; S2=clip_y((V,F),0.0) if cut else (V,F); P.append(dict(V=S2[0],F=S2[1],c=c,a=a,name=name))
    for k in range(1,7): add(load_stl(f"{D}/L{k}_tx_cassette.stl"),cols[k],f"L{k}",k)
    add(load_stl(f"{D}/L7_RX_tray_cassette.stl"),(0.15,0.55,0.35),"L7",7)
    add(load_stl(f"{D}/L1_vault_tube_and_roof.stl"),(0.28,0.28,0.33),"vault",1); add(load_stl(f"{D}/V2_vault_floor_plate.stl"),(0.28,0.28,0.33),"floor",7)
    for f,c in (("POST_TX_1_at_90deg",(0.92,0.45,0.15)),("POST_TX_2_at_210deg",(0.92,0.45,0.15)),("POST_TX_3_at_330deg",(0.92,0.45,0.15)),("POST_RX_1_at_30deg",(0.2,0.4,0.9)),("POST_RX_2_at_150deg",(0.2,0.4,0.9)),("POST_RX_3_at_270deg",(0.2,0.4,0.9))):
        S=load_stl(f"{D}/{f}.stl")
        if explode:
            V=S[0].copy(); V[V[:,2]>10,2]+=156; S=(V,S[1])
        add(S,c,"post",0)
    return P
render(parts(),"kit_v7/RENDER/10_STACK_ASSEMBLED.png",az=58,el=50,centre=(0,0,20),scale=3.9,size=(1700,1150),title="Six removable TX cassettes + RX tray, assembled in the D233 footprint",caption="3-petal formers, golden-angle offsets (137.5 deg x layer); TX posts orange, RX posts blue; vault housing hangs under the top cassette; height 44.5 mm at the opening")
render(parts(explode=True),"kit_v7/RENDER/11_STACK_EXPLODED.png",az=62,el=24,centre=(0,0,90),scale=2.0,size=(1500,1300),title="Exploded: RX tray (bottom) then L6 ... L1 (top, with vault housing)",caption="each cassette is wound separately and slides down the posts; no spacers needed because the cassettes nest cone-on-cone")
render(parts(cut=True),"kit_v7/RENDER/12_STACK_CUTAWAY.png",az=88,el=14,centre=(0,0,24),scale=4.1,size=(1800,1000),title="Cut-away: nested cone cassettes over the RX tray, vault in the centre",caption="the wedge below L6 is filled with syntactic foam; the vault stands on the RX tray and hangs from L1")
P=pickle.load(open(f"{D}/paths.pkl","rb")); fig,ax=plt.subplots(figsize=(9,9)); ax.set_aspect("equal"); ax.axis("off")
for k in range(1,7):
    a,b,la,lb=P[k]; xy=np.vstack([a,b]); ax.plot(xy[:,0],xy[:,1],lw=0.7,color=cols[k],label=f"L{k} ({(137.50776*(k-1))%360:.1f} deg)")
    ax.plot(la[:,0],la[:,1],lw=1.4,color=cols[k]); ax.plot(lb[:,0],lb[:,1],lw=1.4,color=cols[k])
th=np.linspace(0,2*np.pi,300); ax.plot(116.5*np.cos(th),116.5*np.sin(th),"k",lw=2); ax.plot(52*np.cos(th),52*np.sin(th),"gray",lw=1,ls="--")
for a_,c,m in ((90,"#e8730f","s"),(210,"#e8730f","s"),(330,"#e8730f","s"),(30,"#2f5fe3","o"),(150,"#2f5fe3","o"),(270,"#2f5fe3","o")): ax.scatter([53.8*math.cos(math.radians(a_))],[53.8*math.sin(math.radians(a_))],c=c,marker=m,s=90,zorder=5)
ax.legend(loc="lower center",ncol=3,fontsize=8,frameon=False,bbox_to_anchor=(0.5,-0.06)); ax.set_title("Top view: six petal double-spiral layers (3 petals, mirror return), golden-angle offsets 137.5 deg\norange squares = TX posts, blue circles = RX posts, dashed = vault opening",fontsize=10)
plt.savefig("kit_v7/RENDER/13_FLOWER_PLAN.png",dpi=120,bbox_inches="tight")
