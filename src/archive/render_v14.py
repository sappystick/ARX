import numpy as np, glob
from render_v6 import render, load_stl, clip_y
cols={1:(0.20,0.68,0.70),2:(0.33,0.60,0.88),3:(0.55,0.52,0.92),4:(0.76,0.48,0.86),5:(0.92,0.48,0.68),6:(0.96,0.62,0.42)}
def parts(cut=False):
    P=[]
    def add(S,c,name):
        S2=clip_y(S,0.0) if cut else S; P.append(dict(V=S2[0],F=S2[1],c=c,a=1.0,name=name))
    for k in range(1,7): add(load_stl(f"kit_v14/LOW/FORMER_L{k}_petal_coil_former.stl"),cols[k],f"L{k}")
    add(load_stl("kit_v13/SET/02_CORE_PCB_CYLINDER/CORE_PCB_CYLINDER_central_former.stl"),(0.30,0.30,0.36),"hub")
    add(load_stl("kit_v13/SET/03_PINS_AND_CLAMP/CLAMP_FLANGE_with_lock_collar.stl"),(0.30,0.30,0.36),"clamp")
    for f in glob.glob("kit_v13/SET/03_PINS_AND_CLAMP/PINS_interface_*.stl"): add(load_stl(f),(0.95,0.78,0.25),"pins")
    add(load_stl("kit_v13/SET/04_RX_TRAY/RX_TRAY_cassette.stl"),(0.15,0.55,0.35),"tray")
    return P
render(parts(),"kit_v14/stack_assembled.png",az=58,el=46,centre=(0,0,18),scale=3.9,size=(1700,1100),title="Six formers stacked on the hub, each rotated by its hub assignment (k x 137.508 deg)",caption="rim ID notches (1-6) sit on each layer's track direction; layers are separated by the 0.8 mm pin shoulders")
render(parts(cut=True),"kit_v14/stack_cutaway.png",az=88,el=14,centre=(0,0,24),scale=4.1,size=(1800,1000),title="Cut-away of the stacked formers (rebuilt undersides)",caption="constant 0.8 mm gap follows the dome and the petal relief")
