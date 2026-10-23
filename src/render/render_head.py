import sys, time, pickle, csv, json, math, numpy as np
from scene_lib import *
t0=time.time()
R=json.load(open("kit_v15/LOW/report.json")); pins=json.load(open("kit_v15/SET/06_DATA/pins_and_base_plate.json"))["pins"]
Ppaths=pickle.load(open("kit_v15/LOW/paths.pkl","rb")); px=list(csv.DictReader(open("kit_v19/SET/02_CORE_PCB_CYLINDER/PIXEL_MAP_66.csv")))
ringcol=[None,(0.62,0.35,0.95),(0.25,0.85,0.95),(1.0,0.72,0.15),(0.35,0.95,0.40)]
def head(exploded=False):
    P=[]; DZ=(lambda g:{"rx":-46,"base":-60,"form":0,"hub":0,"cupA":0,"cupB":0,"cupCD":0,"hood":0,"cap":0,"skirt":0}[g]) if False else None
    P.append(PT(stl("kit_v16/PARTS/BASE_PLATE_RX_CASSETTE_v2.stl"),COL["base"],1.0,"base plate v2"))
    P.append(PT(disc(114.0,0.8,3.2,180),COL["pcb"],1.0,"SB1R receive board"))
    for k in range(1,7):
        S=tr(stl(f"kit_v15/LOW/FORMER_L{k}_petal_coil_former.stl"),(0,0,R[f"L{k}"]["assembly_z_offset"])); P.append(PT(S,LAYER[k],1.0,f"L{k} former"))
        z=3.2+(6-k)*4.4+3.6-0.7; W=[]
        for arr in Ppaths[k][:2]:
            a=np.asarray(arr)[::5]; W.append(tube_poly(np.c_[a[:,0],a[:,1],np.full(len(a),z)],0.55,5))
        P.append(PT(merge(W),COL["copper"],1.0,f"L{k} litz"))
    for p in pins: P.append(PT(tr(stl("kit_v15/SET/03_PINS/"+p["file"]),(0,0,p["assembly_z_stem_bottom"])),(0.95,0.78,0.25),1.0,"pin"))
    P.append(PT(stl("kit_v19/SET/02_CORE_PCB_CYLINDER/CORE_PCB_CYLINDER_v4_heel_exit.stl"),COL["hub"],1.0,"hub"))
    for n,al in (("A_ANALOG",0.55),("B_ISOLATION",0.55),("CD_CONTROL_DISPLAY",0.40)): P.append(PT(stl(f"kit_v19/PARTS/VAULT_CUP_{n}.stl"),COL["cup"],al,"cup "+n))
    P.append(PT(disc(40.2,17.8,23.6,96),(0.30,0.30,0.34),0.35,"absorber (cup B)"))
    for nm,cx in (("AB1A",-20.3),("AB1B",20.3)):
        V,F=stl(f"legacy/PHIFOLD233_FINAL_KIT_v3/{'04_PCB_receiver_AB1A' if nm=='AB1A' else '05_PCB_receiver_AB1B'}/PF233-{nm}_board_with_components.stl")
        T=V[F]; up=(T[:,:,2]>0.001).any(axis=1); V2=V+np.array([cx,0,12.7])
        P.append(PT((V2,F[~up]),COL["pcb"],1.0,nm+" board")); P.append(PT((V2,F[up]),COL["ic"],1.0,nm+" parts"))
    lb=json.load(open("kit_v19/lib_bodies.json"))
    P+=board_parts("CB1D","kit_v18/CB1D/PF233-CB1D_pickplace.csv","kit_v18/CB1D/PF233-CB1D_BOM.csv","kit_v19/lib_bodies.json",28.6,rot180=True)
    P+=board_parts("LB1","kit_v18/LB1/PF233-LB1_pickplace.csv","kit_v18/LB1/PF233-LB1_BOM.csv","kit_v19/lib_bodies.json",40.0,board_r=39.0,thick=0.8,led_colors=lambda ref: ringcol[int(px[int(ref[2:])-1]["ring"])])
    P.append(PT(merge([cyl((float(r["x_mm"]),float(r["y_mm"]),40.9),(float(r["x_mm"]),float(r["y_mm"]),47.1),0.75,8) for r in px]),COL["pipe"],1.0,"light pipes"))
    P.append(PT(stl("kit_v18/PARTS/HUB_CAP_HTA_v3_vault.stl"),COL["cap"],1.0,"cap"))
    P.append(PT(disc(45.0,45.4,47.0,120),COL["pcb"],1.0,"HTA board"))
    NT=1.915; th=np.linspace(0,NT*2*math.pi,300); r=43.0+(35.5-43.0)*th/(NT*2*math.pi); P.append(PT(tube_poly(np.c_[r*np.cos(th),r*np.sin(th),np.full(300,47.15)],0.3,5),COL["copper"],1.0,"HTA coil"))
    P.append(PT(stl("kit_v18/PARTS/LOTUS_HOOD_CARRIER_v2_spokes.stl"),COL["hood"],1.0,"hood carrier"))
    tl=[]
    for r in csv.DictReader(open("kit_v18/PARTS/hood_tile_cut_list.csv")):
        a=float(r["azimuth_deg"]); rc_=float(r["centre_r_mm"]); L=float(r["length_mm"]); W=float(r["width_mm"]); S=rotz(box(rc_,0,31.65,L,W,2.5),a); tl.append(S)
    P.append(PT(merge(tl),COL["tile"],1.0,"MnZn tiles"))
    P.append(PT(stl("kit_v19/PARTS/HEAD_SKIRT.stl"),COL["skirt"],0.30,"skirt"))
    for n,c in (("HEEL_SADDLE_TOWER",COL["petg"]),("UMBILICAL_BRIDGE",COL["gfrp"])): P.append(PT(stl(f"kit_v19/YOKE/{n}.stl"),c,1.0,n))
    return P
def mpn_map(bom):
    d={}
    for r in list(csv.reader(open(bom)))[1:]:
        for ref in r[1].split(","): d[ref.strip()]=(r[3],r[4])
    return d
if __name__=="__main__":
    which=sys.argv[1] if len(sys.argv)>1 else "cut"
    if which=="cut":
        P=clipall(head())
        labels=[("SB1R receive board",(95,0,2.0),0),("L6 former + litz winding",(88,0,5.2),0),("L3 former",(88,0,16.5),0),("L1 former",(88,0,27.0),0),("MnZn ferrite tile in pocket",(84,0,31.7),0),("hub = vault wall",(46.8,0,20),0),
         ("cup A: AB1A + AB1B",(-20,0,13.5),0),("cup B: absorber",(-30,0,20),0),("CB1D controller",(-20,0,29.5),0),("LB1: 66 RGB LEDs",(-26,0,40.5),0),("66 light pipes",(20,0,44),0),("HTA board + coil",(-34,0,47.2),0),("cap",(49,0,45.8),0),("skirt",(118,0,16),0),("umbilical bridge",(-88,0,38),0),("yoke tower + saddle",(-150,0,40),0)]
        render(P,"kit_v19/HEAD_CUTAWAY.png",az=90,el=17,centre=(-18,0,26),scale=5.3,size=(2100,1150),title="Head cut-away: every layer with its real parts",caption="half section at y = 0: receive board, six formers with litz, hub vault with three cups and the real boards, hood tiles, cap, antenna and light pipes, skirt, yoke",labels=labels,SS=1)
    else:
        offs=[("base plate",-44),("SB1R",-44),("L6",0),("L5",16),("L4",32),("L3",48),("L2",64),("L1",80),("hood",104),("MnZn",104),("hub",138),("cup A",212),("AB1",212),("cup B",234),("absorber",234),("cup CD",256),("CB1D",256),("LB1",296),("light pipes",330),("cap",342),("HTA",342),("skirt",0),("HEEL",0),("UMBIL",0)]
        P=[p for p in head() if p["name"]!="pin"]
        def dz(n):
            for k,v in offs:
                if n.startswith(k) or n.startswith(k.replace("L","L",1)): return v
            return 0
        for p in P: p["V"]=p["V"]+np.array([0,0,dz(p["name"])])
        labels=[("SB1R receive board (8 layers)",(100,0,-41),0),("L6 former",(100,0,5),0),("L5",(100,0,21),0),("L4",(100,0,37),0),("L3",(100,0,53),0),("L2",(100,0,69),0),("L1 former + litz",(100,0,85),0),("hood carrier + 26 MnZn tiles",(90,0,136),0),("hub (vault wall)",(46,0,165),0),("cup A: AB1A + AB1B",(0,0,226),0),("cup B: absorber",(30,0,250),0),("cup CD: CB1D controller",(30,0,290),0),("LB1 display, 66 LEDs",(30,0,336),0),("66 light pipes",(10,0,372),0),("cap + HTA antenna",(40,0,390),0),("base plate v2",(105,0,-58),0)]
        render(P,"kit_v19/HEAD_LAYERS_EXPLODED.png",az=35,el=22,centre=(0,0,170),scale=2.05,size=(1700,1750),title="Head: layers exploded along the axis",caption="receive board and base plate at the bottom, the six formers, ferrite hood, hub, the three vault cups with their boards, display board, light pipes and cap on top",labels=labels,SS=1)
    print("ok")
