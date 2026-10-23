import numpy as np, glob, json, math
from render_v6 import render, load_stl, clip_y
GOLD=137.50776405; cols={1:(0.20,0.68,0.70),2:(0.33,0.60,0.88),3:(0.55,0.52,0.92),4:(0.76,0.48,0.86),5:(0.92,0.48,0.68),6:(0.96,0.62,0.42)}
R=json.load(open("kit_v15/LOW/report.json")); pins=json.load(open("kit_v15/SET/06_DATA/pins_and_base_plate.json"))["pins"]
def tile(cx,cy,ang,hr,ht,z0,z1):
    c,s=math.cos(ang),math.sin(ang); pts=[(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(hr,-ht),(hr,ht),(-hr,ht),(-hr,-ht)]]; V=np.array([(x,y,z) for z in (z0,z1) for x,y in pts]); F=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]); return V,F
def parts(cut=False,hood=True):
    P=[]
    def add(S,c,name,dz=0.0):
        V,F=S; S2=(V+[0,0,dz],F); S2=clip_y(S2,0.0) if cut else S2; P.append(dict(V=S2[0],F=S2[1],c=c,a=1.0,name=name))
    for k in range(1,7): add(load_stl(f"kit_v15/LOW/FORMER_L{k}_petal_coil_former.stl"),cols[k],f"L{k}",R[f"L{k}"]["assembly_z_offset"])
    add(load_stl("kit_v15/SET/02_CORE_PCB_CYLINDER/CORE_PCB_CYLINDER_central_former.stl"),(0.30,0.30,0.36),"hub")
    add(load_stl("kit_v16/PARTS/BASE_PLATE_RX_CASSETTE_v2.stl"),(0.15,0.55,0.35),"base")
    for p in pins: add(load_stl("kit_v15/SET/03_PINS/"+p["file"]),(0.95,0.78,0.25),"pin",p["assembly_z_stem_bottom"])
    add(load_stl("kit_v16/PARTS/HUB_CAP_HTA.stl"),(0.88,0.88,0.92),"cap")
    if hood:
        add(load_stl("kit_v16/PARTS/LOTUS_HOOD_CARRIER.stl"),(0.62,0.66,0.78),"hood")
        for nm,rc_,hr,ht,cnt,ph in (("A",71.0,8,14,12,0.0),("B",92.0,8,19,12,(GOLD*1)%30),("C",106.5,6.5,25,12,(GOLD*2)%30)):
            for i in range(cnt):
                th=math.radians(ph+i*360/cnt); V,F=tile(rc_*math.cos(th),rc_*math.sin(th),th,hr,ht,30.4,32.9); add((V,F),(0.12,0.12,0.14),"tile")
    return P
render(parts(),"kit_v16/assembled_cap_hood.png",az=58,el=44,centre=(0,0,22),scale=3.9,size=(1700,1100),title="Final stack with the hub cap (antenna), ferrite lotus hood and receive cassette v2",caption="dark tiles = MnZn ferrite in the staggered pockets; light cap on the hub roof carries the hub-top antenna")
render(parts(cut=True),"kit_v16/cutaway_cap_hood.png",az=88,el=14,centre=(0,0,24),scale=4.1,size=(1800,1000),title="Cut-away: receive cassette, six formers, hood, hub, cap",caption="hood above L1; cap hooks pass through the roof windows; vault inside the hub")
print("rendered")
