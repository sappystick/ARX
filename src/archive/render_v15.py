import numpy as np, glob, json
from render_v6 import render, load_stl, clip_y
cols={1:(0.20,0.68,0.70),2:(0.33,0.60,0.88),3:(0.55,0.52,0.92),4:(0.76,0.48,0.86),5:(0.92,0.48,0.68),6:(0.96,0.62,0.42)}
pins=json.load(open("kit_v15/SET/06_DATA/pins_and_base_plate.json"))["pins"]; R=json.load(open("kit_v15/LOW/report.json"))
def parts(cut=False):
    P=[]
    def add(S,c,name,dz=0.0):
        V,F=S; S2=(V+[0,0,dz],F); S2=clip_y(S2,0.0) if cut else S2; P.append(dict(V=S2[0],F=S2[1],c=c,a=1.0,name=name))
    for k in range(1,7): add(load_stl(f"kit_v15/LOW/FORMER_L{k}_petal_coil_former.stl"),cols[k],f"L{k}",R[f"L{k}"]["assembly_z_offset"])
    add(load_stl("kit_v15/SET/02_CORE_PCB_CYLINDER/CORE_PCB_CYLINDER_central_former.stl"),(0.30,0.30,0.36),"hub")
    add(load_stl("kit_v15/SET/04_BASE_PLATE_RX_TRAY/BASE_PLATE_RX_TRAY.stl"),(0.15,0.55,0.35),"base")
    for p in pins: add(load_stl("kit_v15/SET/03_PINS/"+p["file"]),(0.95,0.78,0.25),"pin",p["assembly_z_stem_bottom"])
    return P
render(parts(),"kit_v15/stack_assembled_flat.png",az=58,el=46,centre=(0,0,16),scale=3.9,size=(1700,1100),title="Flat-face final design: six formers, hub, pins and base plate assembled",caption="12 petals, golden-angle rotation per layer, rim ID notches 1-6, flat undersides, 0.8 mm gaps held by 15 stepped pins")
render(parts(cut=True),"kit_v15/stack_cutaway_flat.png",az=88,el=14,centre=(0,0,22),scale=4.1,size=(1800,1000),title="Cut-away: flat formers on the hub, PCB vault inside",caption="every layer is a flat 3.6 mm plate at a 4.4 mm pitch; hub bosses, lanes and ports are above and inside the stack")
print("rendered")
