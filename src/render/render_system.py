import sys, csv, json, math, time, numpy as np
from scene_lib import *
import render_head as RH
XH,ZH=159.0,76.0
def tube_shell(ro,ri,z0,z1,n=64,cx=0,cy=0):
    t=np.linspace(0,2*np.pi,n,endpoint=False); c,s=np.cos(t),np.sin(t)
    V=np.concatenate([np.c_[cx+ro*c,cy+ro*s,np.full(n,z0)],np.c_[cx+ro*c,cy+ro*s,np.full(n,z1)],np.c_[cx+ri*c,cy+ri*s,np.full(n,z0)],np.c_[cx+ri*c,cy+ri*s,np.full(n,z1)]]); F=[]
    for i in range(n):
        j=(i+1)%n; O0,O1,I0,I1=i,n+i,2*n+i,3*n+i; P0,P1,Q0,Q1=j,n+j,2*n+j,3*n+j
        F+=[[O0,P0,P1],[O0,P1,O1],[I0,Q1,Q0],[I0,I1,Q1],[O0,I0,Q0],[O0,Q0,P0],[O1,P1,Q1],[O1,Q1,I1]]
    return V,np.array(F)
def arm2heel(S,alpha):
    V=S[0]; ph=math.radians(90-alpha); return (np.c_[XH+V[:,0]*math.cos(ph)+V[:,2]*math.sin(ph),V[:,1],ZH-V[:,0]*math.sin(ph)+V[:,2]*math.cos(ph)],S[1])
def A(S,alpha): return rotz(arm2heel(S,alpha),178.0)
def H(S): return rotz(S,178.0)
def stlp(p): return stl(p)
def system(alpha=47.0,ze=1304.0,full_head=True,light=True):
    P=[]
    hd=RH.head()
    for p in hd:
        if light and (p["name"].endswith("litz") or p["name"]=="pin"): continue
        P.append(p)
    # ---- yoke: hinge arm (local), lower fixed tube, neck module + PB1R, telescoping tubes, joint hardware, cassette, ribbons
    arm=stlp("kit_v19/YOKE/HINGE_ARM.stl"); P.append(PT(A(arm,alpha),COL["petg"],1.0,"HINGE_ARM"))
    P.append(PT(A(tube_shell(16.0,14.5,14.0,400.0),alpha),COL["gfrp"],1.0,"lower fixed tube (GFRP)"))
    npm=[stlp("kit_v19/SPINE/NPM_N1_body_with_tunnel.stl")]
    for S in npm: P.append(PT(A(tr(S,(0,0,400.0)),alpha),(0.55,0.60,0.68),1.0,"NPM body"))
    P.append(PT(A(tr(stlp("kit_v19/SPINE/NPM_N3_hot_zone_dam.stl"),(0,0,400.0)),alpha),(0.9,0.5,0.2),1.0,"NPM dam"))
    pb=stlp("legacy/PHIFOLD233_KIT_v6_ARCHITECTURE/PB1R/PF233-PB1R_board_with_components.stl"); V,F=pb; up=(V[F][:,:,2]>0.001).any(axis=1)
    def pbT(V): return np.c_[V[:,0],34.6-(V[:,2]+1.6),V[:,1]+42.0+400.0]
    P.append(PT(A((pbT(V),F[~up]),alpha),COL["pcb"],1.0,"PB1R board")); P.append(PT(A((pbT(V),F[up]),alpha),COL["ic"],1.0,"PB1R parts"))
    zB0,zB1=484.0,934.0; zA1=ze; zA0=ze-450.0
    P.append(PT(A(tube_shell(14.25,13.0,zB0,zB1),alpha),COL["cfrp"],1.0,"tube B (CFRP)")); P.append(PT(A(tube_shell(16.5,15.0,zA0,zA1),alpha),COL["cfrp"],1.0,"tube A (CFRP)"))
    P.append(PT(A(tr(stlp("kit_v19/YOKE/BUSHING_ON_TUBE_B.stl"),(0,0,zB1-20)),alpha),(0.95,0.85,0.45),1.0,"bushing on B")); P.append(PT(A(tr(stlp("kit_v19/YOKE/BUSHING_IN_TUBE_A.stl"),(0,0,zA0)),alpha),(0.95,0.85,0.45),1.0,"bushing in A"))
    P.append(PT(A(tr(stlp("kit_v19/YOKE/TELESCOPE_LOCK_COLLAR.stl"),(0,0,zA0+1)),alpha),(0.95,0.55,0.25),1.0,"lock collar"))
    cas=stlp("kit_v19/SPINE/CAS_R1_cassette_segment_150.stl")
    for k in range(2): P.append(PT(A(tr(cas,(0,0,zA1-150*(k+1))),alpha),(0.97,0.95,0.80),1.0,"cassette segment"))
    P.append(PT(A(tr(stlp("kit_v19/SPINE/CAS_R2_trolley.stl"),(0,0,zA1-190)),alpha),(0.85,0.40,0.20),1.0,"ribbon trolley"))
    # ribbons: lower tube bundle (P, S, J ribbons + TX pair), through the tunnel, up the shaft to the elbow
    segs=[]
    for nm,x,y,col,wd in (("P",0,9.0,COL["ribP"],12.0),("S",0,-9.0,COL["ribS"],12.0),("J",0,0.0,COL["ribJ"],8.0)):
        segs.append(PT(A(seg_box((x,y,30),(x,y,zA1),(1,0,0),wd,0.7),alpha),col,1.0,"ribbon "+nm))
    for x in (-8.0,8.0): segs.append(PT(A(cyl((x,0,60),(x,0,400),1.9,10),alpha),COL["tx"],1.0,"TX pair"))
    P+=segs
    for nm,dx,zz,col in (("P",4.0,40.2,COL["ribP"]),("S",0.0,39.4,COL["ribS"]),("J",-4.0,38.6,COL["ribJ"])):
        pts=[(XH+dx,0,60),(XH+dx,0,zz),(52.0,0,zz)]
        P.append(PT(H(merge([seg_box(a_,b_,(0,1,0),12.0 if nm!="J" else 8.0,0.7) for a_,b_ in zip(pts[:-1],pts[1:])])),col,1.0,"ribbon "+nm+" tower/bridge"))
    for y in (-3.8,3.8): P.append(PT(H(tube_poly([(XH-8,y,60),(XH-8,y,36.3),(52.0,y,36.3)],1.8,10)),COL["tx"],1.0,"TX pair (tower)"))
    # elbow, grip, trigger, joystick, cuff, battery
    ELB={n:stlp(f"kit_v19/SPINE/{n}.stl") for n in ("ELB_E1_elbow_and_grip","ELB_E2_grip_endcap","ELB_E3_trigger","ELB_E4_joystick_boss","ELB_E5_forearm_cuff","BAT_B1_drawer_sleeve","BAT_B2_end_cap_with_latch","BAT_B3_contact_plate")}
    def E(S): return A(tr(roty(S,-43.0),(0,0,ze)),alpha)
    P.append(PT(E(ELB["ELB_E1_elbow_and_grip"]),(0.72,0.76,0.86),1.0,"elbow + grip")); P.append(PT(E(ELB["ELB_E2_grip_endcap"]),(0.72,0.76,0.86),1.0,"grip cap")); P.append(PT(E(ELB["ELB_E3_trigger"]),(0.90,0.35,0.30),1.0,"trigger")); P.append(PT(E(ELB["ELB_E4_joystick_boss"]),(0.35,0.35,0.40),1.0,"joystick"))
    cuff=tr(roty(ELB["ELB_E5_forearm_cuff"],90.0),(215.0,0,20.0+55.0)); P.append(PT(E(cuff),(0.80,0.82,0.55),1.0,"forearm cuff"))
    BZ=-14.5
    for n,c in (("BAT_B1_drawer_sleeve",(0.55,0.62,0.70)),("BAT_B2_end_cap_with_latch",(0.55,0.62,0.70)),("BAT_B3_contact_plate",(0.9,0.75,0.3))): P.append(PT(E(roty(ELB[n],45.0,(20,0,BZ))),c,0.8 if n.startswith("BAT_B1") else 1.0,n))
    cells=[]
    for row,(yy,nc) in enumerate(((9.5,4),(-9.5,3))):
        for q in range(nc):
            x0=40+q*66.0; cells.append(cyl((x0,yy,BZ),(x0+65.0,yy,BZ),9.3,16))
    P.append(PT(E(roty(merge(cells),45.0,(20,0,BZ))),COL["bat"],1.0,"18650 cells (7S U-pack)"))
    pm=stlp("legacy/PHIFOLD233_FINAL_KIT_v4/03_POWER_BOARD_PM1/PF233-PM1_board_with_components.stl"); V,F=pm; up=(V[F][:,:,2]>0.001).any(axis=1)
    def pmT(V): return np.c_[100.0-V[:,1],V[:,0],20.0-5.0+V[:,2]]
    P.append(PT(E((pmT(V),F[~up])),COL["pcb"],1.0,"PM1 board")); P.append(PT(E((pmT(V),F[up])),COL["ic"],1.0,"PM1 parts"))
    return P
if __name__=="__main__":
    which=sys.argv[1]; t0=time.time()
    if which=="use":
        P=system(47.0,1304.0); 
        pts=lambda z,a=47.0,x=0.0,y=0.0: A((np.array([[x,y,z]]),np.zeros((1,3),int)),a)[0][0]
        labels=[("head: six formers, hub vault, hood, cap",(0,0,40),0),("heel saddle + tower + hinge",pts(0),0),("lower fixed tube (GFRP, 0.40 m)",pts(200),0),("neck module: PB1R TX driver",pts(442),0),("tube B (CFRP, OD 28.5)",pts(700),0),("lock collar + bushings",pts(870),0),("tube A (CFRP, OD 33) + cassette",pts(1100),0),("elbow (47 deg bend)",pts(1304),0),("grip + trigger + joystick",pts(1304,47.0,120,0),0),("battery drawer at 45 deg: 7 x 18650",pts(1304,47.0,200,-60),0)]
        render(P,"kit_v19/SYSTEM_USE_POSE.png",az=90,el=6,centre=(-480,0,520),scale=0.95,size=(2200,1350),title="Whole detector, extended, shaft at 47 degrees",caption="head with yoke at the heel, lower fixed GFRP tube, neck module, telescoping carbon tubes with ribbon cassette, elbow with horizontal grip, battery drawer at 45 degrees",labels=labels,SS=1)
    elif which=="fold":
        P=system(180.0,980.0)
        pts=lambda z,a=180.0,x=0.0,y=0.0: A((np.array([[x,y,z]]),np.zeros((1,3),int)),a)[0][0]
        labels=[("head",(0,0,40),0),("hinge at the heel (folded 180 deg)",pts(0),0),("neck module",pts(442),0),("collapsed carbon tubes (0.45 m)",pts(760),0),("elbow + grip + battery",pts(980),0)]
        render(P,"kit_v19/SYSTEM_FOLDED.png",az=90,el=14,centre=(250,0,70),scale=1.9,size=(2200,900),title="Folded for the backpack: shaft collapsed and hinged over the head",caption="hinge at 180 degrees: the shaft lies over the head with 9 mm clearance over the cap",labels=labels,SS=1)
    print("ok",round(time.time()-t0))
