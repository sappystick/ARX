import numpy as np, math, pickle
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from render_v6 import render, load_stl, clip_y
D="kit_v10/LOW"; cols={1:(0.20,0.68,0.70),2:(0.33,0.60,0.88),3:(0.55,0.52,0.92),4:(0.76,0.48,0.86),5:(0.92,0.48,0.68),6:(0.96,0.62,0.42)}
def parts(cut=False,explode=False):
    P=[]; dz={1:0,2:-52,3:-104,4:-156,5:-208,6:-260,7:-312,8:-364} if explode else {k:0 for k in range(1,9)}
    def add(S,c,name,k):
        V,F=S; V=V+[0,0,dz[k]]; S2=clip_y((V,F),0.0) if cut else (V,F); P.append(dict(V=S2[0],F=S2[1],c=c,a=1.0,name=name))
    for k in range(1,7): add(load_stl(f"{D}/L{k}_petal_cassette.stl"),cols[k],f"L{k}",k)
    add(load_stl(f"{D}/L7_RX_tray_cassette.stl"),(0.15,0.55,0.35),"L7",7); add(load_stl(f"{D}/L1_hub_foundation_with_tracks_lanes_PCB_slots.stl"),(0.30,0.30,0.36),"hub",1); add(load_stl(f"{D}/V2_lock_collar_ring.stl"),(0.30,0.30,0.36),"floor",8)
    for i in range(1,7):
        import glob
        for f in glob.glob(f"{D}/PINS_interface_{i}_x3*.stl"): add(load_stl(f),(0.95,0.78,0.25),"pins",1)
    return P
render(parts(),"kit_v10/RENDER/10_ASSEMBLED.png",az=58,el=46,centre=(0,0,18),scale=3.9,size=(1700,1100),title="v9: six petal cassettes slide over the central PCB hub",caption="0.8 mm gaps, 18 stepped pins at golden-sequence angles, tracks at k x 137.5 deg")
#render(parts(explode=True),"kit_v10/RENDER/11_EXPLODED_SLIDE_ORDER.png",az=62,el=14,centre=(0,0,-150),scale=1.6,size=(1300,1500),title="Slide order: L2 first, then L3 ... L6, then the RX tray (they slide up the hub from below)",caption="L1 stays fused to the hub; each layer slides up its own numbered track; the tray clamps the stack with 3 M3 screws")
render(parts(cut=True),"kit_v10/RENDER/12_CUTAWAY.png",az=88,el=14,centre=(0,0,24),scale=4.1,size=(1800,1000),title="Cut-away: nested layers with 0.8 mm gaps and pins, hub PCB slots inside",caption="0.8 mm gap between layers held by stepped pins; the hub holds 4 PCB discs at 8 mm pitch")
