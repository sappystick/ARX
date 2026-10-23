import numpy as np, math, pickle
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from render_v6 import render, load_stl, clip_y
D="kit_v9/LOW"; cols={1:(0.20,0.68,0.70),2:(0.33,0.60,0.88),3:(0.55,0.52,0.92),4:(0.76,0.48,0.86),5:(0.92,0.48,0.68),6:(0.96,0.62,0.42)}
def parts(cut=False,explode=False):
    P=[]; dz={1:0,2:-52,3:-104,4:-156,5:-208,6:-260,7:-312,8:-364} if explode else {k:0 for k in range(1,9)}
    def add(S,c,name,k):
        V,F=S; V=V+[0,0,dz[k]]; S2=clip_y((V,F),0.0) if cut else (V,F); P.append(dict(V=S2[0],F=S2[1],c=c,a=1.0,name=name))
    for k in range(1,7): add(load_stl(f"{D}/L{k}_petal_cassette.stl"),cols[k],f"L{k}",k)
    add(load_stl(f"{D}/L7_RX_tray_cassette.stl"),(0.15,0.55,0.35),"L7",7); add(load_stl(f"{D}/L1_hub_foundation_with_tracks_lanes_PCB_slots.stl"),(0.30,0.30,0.36),"hub",1); add(load_stl(f"{D}/V2_floor_plate_and_lock_seat.stl"),(0.30,0.30,0.36),"floor",8)
    return P
render(parts(),"kit_v9/RENDER/10_ASSEMBLED.png",az=58,el=46,centre=(0,0,18),scale=3.9,size=(1700,1100),title="v9: six petal cassettes slide over the central PCB hub",caption="no outer posts; each layer is keyed to its numbered hub track; 12 petals, golden-angle offsets, flatter slightly domed faces")
render(parts(explode=True),"kit_v9/RENDER/11_EXPLODED_SLIDE_ORDER.png",az=62,el=14,centre=(0,0,-150),scale=1.6,size=(1300,1500),title="Slide order: L2 first, then L3 ... L6, then the RX tray (they slide up the hub from below)",caption="L1 stays fused to the hub; each layer slides up its own numbered track; the tray clamps the stack with 3 M3 screws")
render(parts(cut=True),"kit_v9/RENDER/12_CUTAWAY.png",az=88,el=14,centre=(0,0,24),scale=4.1,size=(1800,1000),title="Cut-away: nested layers on the hub, PCB slots inside",caption="layers rest directly on each other (no gaps); the hub holds 4 PCB discs at 8 mm pitch")
# hub track / lane map
HUB_R=49.5; fig,ax=plt.subplots(figsize=(9,9)); ax.set_aspect("equal"); ax.axis("off")
m=1440; a=np.linspace(0,2*np.pi,m,endpoint=False); wrap=lambda x:(x+np.pi)%(2*np.pi)-np.pi; ro=np.full(m,HUB_R)
def notch(ang,w,d): mk=np.abs(wrap(a-ang))*HUB_R<w/2; ro[mk]=HUB_R-d
PSI=lambda k: math.radians(60*(k-1))
for k in range(1,7): notch(PSI(k),4.0,3.0); notch(PSI(k)+math.radians(9),1.8,1.4); notch(PSI(k)+math.radians(15),1.8,1.4); notch(PSI(k)+math.radians(36),1.8,1.4)
ax.fill(ro*np.cos(a),ro*np.sin(a),color="#d9dde6",ec="k",lw=1.2); t=np.linspace(0,2*np.pi,200); ax.fill(44*np.cos(t),44*np.sin(t),color="white",ec="k",lw=1)
for k in range(1,7):
    c=cols[k]; ang=PSI(k); ax.plot([46.5*math.cos(ang)],[46.5*math.sin(ang)],"s",color=c,ms=11); ax.text(57*math.cos(ang),57*math.sin(ang),f"{k}",ha="center",va="center",fontsize=15,weight="bold",color=c)
    for off,mk in ((9,"o"),(15,"o")): ax.plot([48*math.cos(ang+math.radians(off))],[48*math.sin(ang+math.radians(off))],mk,color=c,ms=5)
    ax.plot([48*math.cos(ang+math.radians(36))],[48*math.sin(ang+math.radians(36))],"^",color="#2f5fe3",ms=6)
ax.set_xlim(-66,66); ax.set_ylim(-66,66); ax.set_title("Hub cross-section (plan): numbered tracks (squares, layer key teeth), TX lanes (dots, pair per layer), RX lanes (blue triangles)\nlayer k slides up track k only; tooth 3.6 x 2.6 in a 4.0 x 3.0 groove",fontsize=9)
plt.savefig("kit_v9/RENDER/13_HUB_TRACKS_AND_LANES.png",dpi=120,bbox_inches="tight")
# individual layer plan, 6 small multiples
P=pickle.load(open(f"{D}/paths.pkl","rb")); fig,axs=plt.subplots(2,3,figsize=(13,8.6)); th=np.linspace(0,2*np.pi,300)
for k,ax in zip(range(1,7),axs.ravel()):
    aa,bb,la,lb=P[k]; ax.set_aspect("equal"); ax.axis("off"); ax.plot(aa[:,0],aa[:,1],color=np.array(cols[k])*0.85,lw=0.9); ax.plot(bb[:,0],bb[:,1],color="#555",lw=0.7); ax.plot(la[:,0],la[:,1],"r",lw=1.6); ax.plot(lb[:,0],lb[:,1],"r",lw=1.6)
    ax.plot(116.5*np.cos(th),116.5*np.sin(th),"k",lw=1); ax.plot(49.9*np.cos(th),49.9*np.sin(th),"gray",lw=0.8,ls="--"); ax.set_title(f"L{k}: petals rotated {(137.50776*(k-1))%360:.1f} deg; track at {60*(k-1)} deg; leads straight to lane",fontsize=8)
plt.tight_layout(); plt.savefig("kit_v9/RENDER/14_LAYERS_INDIVIDUAL.png",dpi=95)
