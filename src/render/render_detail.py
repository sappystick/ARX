import sys, time, math, csv, json, numpy as np
from scene_lib import *
import render_system as RS
from render_system import system, tube_shell, A, H, arm2heel
XH,ZH=159.0,76.0
def clip_ge(P,y1):
    out=[]
    for p in P:
        V=p["V"].copy(); V[:,1]*=-1; V2,F2=clip_y((V,p["F"][:,::-1]),-y1)
        if len(F2): V2=V2.copy(); V2[:,1]*=-1; out.append(dict(p,V=V2,F=F2[:,::-1]))
    return out
hp=lambda x,y,z: H((np.array([[x,y,z]]),np.zeros((1,3),int)))[0][0]
ap=lambda z,a=47.0,x=0.0,y=0.0: A((np.array([[x,y,z]]),np.zeros((1,3),int)),a)[0][0]
which=sys.argv[1]; t0=time.time()
if which=="yoke":
    P=system(47.0,1304.0,light=True)
    keep=("hub","skirt","base plate","hood","cap","UMBILICAL","HEEL","HINGE","lower fixed","NPM","PB1R","ribbon P","ribbon S","ribbon J","TX pair","SB1R","L1 former","L2 former","L3 former","L4 former","L5 former","L6 former","cup CD","cup B","cup A","MnZn")
    P=[p for p in P if any(p["name"].startswith(k) for k in keep) and not p["name"].startswith("cup")]
    P=clipall(P)
    labels=[("hinge pin axis (nylon M10)",hp(XH,0,ZH),0),("hinge arm: 36 serrations (10 deg)",ap(-0.0,47.0,0,15),0),("hinge lug + serrations",hp(XH,-20,ZH),0),("tower: ribbons drop through the passage",hp(XH,0,50),0),("umbilical bridge (14 x 6.4)",hp(95,0,38),0),("hub exit window at 178 deg",hp(49,0,38),0),("heel saddle bonded to the skirt",hp(121,-12,16),0),("lower fixed tube (GFRP) with P, S, J ribbons + TX pair",ap(150),0),("neck module: PB1R driver",ap(442),0),("skirt",hp(118,-8,20),0),("hood tile",hp(-84,0,31.6),0),("L1 former",hp(-85,0,27),0)]
    render(P,"kit_v19/YOKE_CUTAWAY.png",az=90,el=14,centre=hp(120,0,60),scale=7.0,size=(2200,1300),title="Yoke and hinge cut-away (use position 47 degrees)",caption="saddle bonded on the skirt, hollow tower with the ribbon passage, serrated hinge, umbilical bridge to the hub exit window, lower fixed tube with ribbons and TX pair, neck module",labels=labels,SS=1)
elif which=="joint":
    P=[p for p in system(47.0,1304.0,light=True) if any(p["name"].startswith(k) for k in ("tube A","tube B","bushing","lock collar","cassette","ribbon trolley","ribbon P","ribbon S","ribbon J")) and "tower" not in p["name"]]
    xh=159.0+960*math.cos(math.radians(47.0)); y0=xh*math.sin(math.radians(2.0))+11.0
    for p in P:
        if p["name"].startswith("tube"): p["c"]=(0.42,0.46,0.55); p["a"]=0.45
    P=clipall(P,y0)
    labels=[("tube A (CFRP) OD 33 / ID 30",ap(1050,47.0,0,-16.5),0),("tube B (CFRP) OD 28.5 / ID 26",ap(700,47.0,0,-14.25),0),("bushing in the mouth of A",ap(865,47.0,0,-15.0),0),("bushing on the end of B",ap(925,47.0,0,-14.8),0),("split lock collar (nylon M4)",ap(870,47.0,0,-22),0),("cassette: power chamber and signal chamber",ap(1200,47.0,0,0),0),("ribbon trolley (U-loop post)",ap(1114,47.0,0,0),0),("power ribbon (12-way)",ap(1000,47.0,0,9),0),("signal ribbon (12-way)",ap(1000,47.0,0,-9),0),("8-way umbilical ribbon",ap(600,47.0,0,0),0)]
    render(P,"kit_v19/SHAFT_JOINT_CUTAWAY.png",az=90,el=10,centre=ap(1085),scale=4.7,size=(2200,900),title="Telescoping joint and ribbon track: cut-away",caption="carbon tube B slides in tube A on two printed bushings; the split collar locks it; the cassette (two chambers) holds the trolley whose U-loop takes up the ribbon slack",labels=labels,SS=1,rolly=-47.0)
elif which=="npm":
    npm=stl("kit_v19/SPINE/NPM_N1_body_with_tunnel.stl"); dam=stl("kit_v19/SPINE/NPM_N3_hot_zone_dam.stl")
    pb=stl("kit_v6/PB1R/PF233-PB1R_board_with_components.stl"); V,F=pb; up=(V[F][:,:,2]>0.001).any(axis=1)
    pbT=lambda V: np.c_[V[:,0],34.6-(V[:,2]+1.6),V[:,1]+42.0]
    P=[PT(npm,(0.55,0.60,0.68),1.0,"NPM body"),PT(dam,(0.9,0.5,0.2),1.0,"dam"),PT((pbT(V),F[~up]),COL["pcb"],1.0,"PB1R board"),PT((pbT(V),F[up]),COL["ic"],1.0,"PB1R parts")]
    P.append(PT(tube_shell(16.0,14.5,-120,0),COL["gfrp"],1.0,"lower tube")); P.append(PT(tube_shell(14.25,13.0,84,200),COL["cfrp"],1.0,"tube B"))
    P.append(PT(box(-22,20,28,22,36,2*38)[0:2],(0.9,0.5,0.2),0.18,"alumina zone")); 
    P.append(PT(box(21,20,28,36,36,76),(0.3,0.7,0.4),0.15,"syntactic zone"))
    for nm,x,y,col in (("P",0,9.0,COL["ribP"]),("S",0,-9.0,COL["ribS"]),("J",0,0.0,COL["ribJ"])): P.append(PT(seg_box((x,y,-110),(x,y,190),(1,0,0),12.0 if nm!="J" else 8.0,0.7),col,1.0,"ribbon "+nm))
    P=clip_ge(P,15.0)
    lab=[("PB1R (TX driver, 70 x 70, routed 2026-10-25; pb1r_check)",(0,24,42),0),("2 x IPB65R095C7 650 V FETs (D2PAK)",(-14,22,22),0),("9 x 100 uF / 50 V hybrid cans (EEHZC1H101P)",(-18,23,70),0),("clamp diode + 5 k / 10 W bank (hot zone)",(-30,22,60),0),("hot zone: alumina-filled epoxy",(-25,26,10),0),("main zone: syntactic silicone",(25,28,60),0),("straight ribbon tunnel",(0,12,40),0),("lower fixed tube (GFRP) to the hinge",(0,0,-60),0),("tube B (CFRP) from the neck module up",(0,0,150),0),("TX pair + P, S, J ribbons pass straight through",(8,0,-100),0)]
    render(P,"kit_v19/NPM_CUTAWAY.png",az=-90,el=12,centre=(0,22,45),scale=6.2,size=(2000,1400),title="Neck power module cut-away (seen from the component side)",caption="back wall removed: PB1R stands in the pocket with its parts facing the camera; the hot zone is separated by the dam; the ribbons run straight through the tunnel",labels=lab,SS=1)
elif which=="elbow":
    E={n:stl(f"kit_v19/SPINE/{n}.stl") for n in ("ELB_E1_elbow_and_grip","ELB_E2_grip_endcap","ELB_E3_trigger","ELB_E4_joystick_boss","ELB_E5_forearm_cuff","BAT_B1_drawer_sleeve","BAT_B2_end_cap_with_latch","BAT_B3_contact_plate")}
    BZ=-14.5; Bz=lambda S: roty(S,45.0,(20,0,BZ))
    P=[PT(E["ELB_E1_elbow_and_grip"],(0.72,0.76,0.86),0.6,"elbow + grip"),PT(E["ELB_E2_grip_endcap"],(0.72,0.76,0.86),1.0,"grip cap"),PT(E["ELB_E3_trigger"],(0.90,0.35,0.30),1.0,"trigger"),PT(E["ELB_E4_joystick_boss"],(0.35,0.35,0.40),1.0,"joystick"),PT(tr(roty(E["ELB_E5_forearm_cuff"],90.0),(215.0,0,75.0)),(0.80,0.82,0.55),0.8,"forearm cuff")]
    P+=[PT(Bz(E["BAT_B1_drawer_sleeve"]),(0.55,0.62,0.70),0.45,"drawer"),PT(Bz(E["BAT_B2_end_cap_with_latch"]),(0.55,0.62,0.70),1.0,"end cap"),PT(Bz(E["BAT_B3_contact_plate"]),(0.9,0.75,0.3),1.0,"contacts")]
    cells=[cyl((40+q*66.0,yy,BZ),(40+q*66.0+65.0,yy,BZ),9.3,16) for yy,nc in ((9.5,4),(-9.5,3)) for q in range(nc)]
    P.append(PT(Bz(merge(cells)),COL["bat"],1.0,"18650 cells"))
    sc=[cyl((-8+ (q%5)*9.5, -6+(q//5)*12.0, 12.0),(-8+(q%5)*9.5,-6+(q//5)*12.0,52.0),4.2,12) for q in range(10)]; P.append(PT(merge(sc),(0.15,0.2,0.55),1.0,"supercap cells"))
    pm=stl("legacy/PHIFOLD233_FINAL_KIT_v4/03_POWER_BOARD_PM1/PF233-PM1_board_with_components.stl"); V,F=pm; up=(V[F][:,:,2]>0.001).any(axis=1); pmT=lambda V: np.c_[100.0-V[:,1],V[:,0],15.0+V[:,2]]
    P+=[PT((pmT(V),F[~up]),COL["pcb"],1.0,"PM1"),PT((pmT(V),F[up]),COL["ic"],1.0,"PM1 parts")]
    hb=stl("legacy/PHIFOLD233_KIT_v6_ARCHITECTURE/HB1/PF233-HB1_board_with_components.stl"); V,F=hb; up=(V[F][:,:,2]>0.001).any(axis=1); hbT=lambda V: np.c_[170.0-V[:,1],V[:,0],15.0+V[:,2]]
    P+=[PT((hbT(V),F[~up]),COL["pcb"],1.0,"HB1"),PT((hbT(V),F[up]),(0.9,0.6,0.2),1.0,"HB1 parts")]
    P=clipall(P)
    lab=[("shaft socket D33.4 tilted 43 deg (tube A bonds here)",(-10,0,-20),0),("elbow cavity: supercap bridge (10 cells)",(0,-5,30),0),("grip tube: PM1 power board (28 x 136)",(95,0,15),0),("HB1 handle board: Hall sensor, dial, joystick",(160,0,16),0),("trigger lever (magnet in the tip)",(62,0,-4),0),("thumb joystick boss",(95,0,48),0),("forearm cuff D86",(215,0,75),0),("battery drawer at 45 deg",(150,0,-80),0),("7 x 18650 (7S1P, 90.7 Wh)",(120,0,-95),0),("contact plate",(40,0,-26),0),("end cap with push latch",(290,0,-210),0)]
    render(P,"kit_v19/ELBOW_GRIP_BATTERY_CUTAWAY.png",az=90,el=8,centre=(130,0,-60),scale=3.9,size=(2200,1250),title="Elbow, grip, trigger, forearm cuff and the 45 degree battery drawer",caption="PM1 and HB1 sit in the grip tube; the supercap bridge in the elbow; the 4+3 U-pack hangs in the drawer under the forearm",labels=lab,SS=1)
print("ok",which,round(time.time()-t0))
