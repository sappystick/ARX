import sys, csv, json, math, numpy as np
from scene_lib import *
from render_head import mpn_map, px, ringcol
lb=json.load(open("kit_v19/lib_bodies.json"))
def vault(offs):
    P=[]
    for n,al,dz in (("A_ANALOG",0.35,offs[0]),("B_ISOLATION",0.35,offs[1]),("CD_CONTROL_DISPLAY",0.25,offs[2])):
        P.append(PT(tr(stl(f"kit_v19/PARTS/VAULT_CUP_{n}.stl"),(0,0,dz)),COL["cup"],al,"cup "+n))
    for nm,cx in (("AB1A",-20.3),("AB1B",20.3)):
        V,F=stl(f"legacy/PHIFOLD233_FINAL_KIT_v3/{'04_PCB_receiver_AB1A' if nm=='AB1A' else '05_PCB_receiver_AB1B'}/PF233-{nm}_board_with_components.stl")
        up=(V[F][:,:,2]>0.001).any(axis=1); V2=V+np.array([cx,0,12.7+offs[0]]); P.append(PT((V2,F[~up]),COL["pcb"],1.0,nm)); P.append(PT((V2,F[up]),COL["ic"],1.0,nm+" parts"))
    P.append(PT(disc(40.2,17.8+offs[1],23.6+offs[1],96),(0.30,0.30,0.34),0.55,"absorber"))
    P+=[dict(p,V=p["V"]+np.array([0,0,offs[2]])) for p in board_parts("CB1D","kit_v18/CB1D/PF233-CB1D_pickplace.csv","kit_v18/CB1D/PF233-CB1D_BOM.csv","kit_v19/lib_bodies.json",28.6,rot180=True)]
    P+=[dict(p,V=p["V"]+np.array([0,0,offs[3]])) for p in board_parts("LB1","kit_v18/LB1/PF233-LB1_pickplace.csv","kit_v18/LB1/PF233-LB1_BOM.csv","kit_v19/lib_bodies.json",40.0,thick=0.8,led_colors=lambda ref: ringcol[int(px[int(ref[2:])-1]["ring"])])]
    P.append(PT(tr(merge([cyl((float(r["x_mm"]),float(r["y_mm"]),40.9),(float(r["x_mm"]),float(r["y_mm"]),47.1),0.75,8) for r in px]),(0,0,offs[4])),COL["pipe"],1.0,"light pipes"))
    P.append(PT(tr(stl("kit_v18/PARTS/HUB_CAP_HTA_v3_vault.stl"),(0,0,offs[5])),COL["cap"],0.9,"cap"))
    P.append(PT(disc(45.0,45.4+offs[5],47.0+offs[5],120),COL["pcb"],1.0,"HTA board"))
    return P
if __name__=="__main__":
    offs=(0,40,80,125,150,172)
    P=vault(offs)
    pp={r["Ref"]:r for r in csv.DictReader(open("kit_v18/CB1D/PF233-CB1D_pickplace.csv"))}; M=mpn_map("kit_v18/CB1D/PF233-CB1D_BOM.csv")
    def pos(ref,dz,top):
        r=pp[ref]; return (-float(r["PosX_mm"]),-float(r["PosY_mm"]),top+dz)
    names={"U1":"Pico 2 W module (RP2350)","M5":"OKI-78SR 5 V module","UM":"74HC4051 analog mux","UL":"AMS1117 3.3 V LDO","F1":"5 A fuse","JPW":"power in (VBUS)","JPB":"to PB1R driver (8-way)","JCL":"TX coil leads (JCL)","JTR":"handle ribbon (JTR)","JA":"to AB1A (2x6)","JB":"to AB1B (2x6)","JHTA":"antenna pair (JHTA)","JLB":"to LB1 (JLB)","RDM1":"damping chain 110 ohm (R2512)","CMON":"630 V MONO coupling cap"}
    labels=[(f"CB1D {names[k]}",pos(k,offs[2],28.6+2.0),0) for k in ("U1","M5","UM","F1","JPW","JPB","JCL","JTR","JA","JHTA","JLB","RDM1")]
    labels+=[("AB1A analog board (AD7389-4, OPA2211)",(-20.3,0,12.7+4+offs[0]),0),("AB1B analog board",(20.3,0,12.7+4+offs[0]),0),("cup B absorber",(0,0,20+offs[1]),0),("LB1 66 SK6812 LEDs",(26,0,40.8+offs[3]),0),("light pipes D1.5",(10,5,44+offs[4]),0),("HTA 4-layer antenna board",(30,0,47+offs[5]),0)]
    render(P,"kit_v19/VAULT_COMPONENTS_EXPLODED.png",az=50,el=36,centre=(0,0,95),scale=5.6,size=(2200,1500),title="Vault stack exploded: the real boards and parts",caption="cup A holds AB1A + AB1B (analog), cup B is the absorber cell, cup CD holds CB1D (controller, 64 parts) and LB1 (66 LEDs); light pipes, antenna board and cap on top",labels=labels,SS=1,layout="cols")
    print("ok")
