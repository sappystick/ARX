#!/usr/bin/env python3
"""v12: central PCB cylinder with 18 lead ports + 3 M3 boss posts + roof vent ports, clamp flange with lock collar, fit coupons, verification."""
import math, json, os, csv, hashlib, shutil, glob, struct, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
OUT="kit_v12"; D={"form":f"{OUT}/01_FORMERS","hub":f"{OUT}/02_CORE_PCB_CYLINDER","pins":f"{OUT}/03_PINS_AND_CLAMP","tray":f"{OUT}/04_RX_TRAY","cpn":f"{OUT}/05_TEST_COUPONS","data":f"{OUT}/06_DATA"}
for d in D.values(): os.makedirs(d,exist_ok=True)
GOLD=137.50776405; HUB_R,HUB_RI,BORE,TOOTH_W,TOOTH_H,TRACK_W,TRACK_D=49.5,44.0,49.9,3.6,2.6,4.0,3.0
PSI=lambda k: (GOLD*(k-1))%360; wrap=lambda a:(a+np.pi)%(2*np.pi)-np.pi
def circ(r,m=96,cx=0.0,cy=0.0): t=np.linspace(0,2*np.pi,m,endpoint=False); return np.c_[cx+r*np.cos(t),cy+r*np.sin(t)]
def ring(outer,inner,z0,z1):
    m=len(outer); V=np.concatenate([np.c_[outer,np.full(m,z0)],np.c_[outer,np.full(m,z1)],np.c_[inner,np.full(m,z0)],np.c_[inner,np.full(m,z1)]]); O0,O1,I0,I1=(np.arange(m)+k*m for k in range(4)); n=np.roll(np.arange(m),-1); F=[]
    for i in range(m): j=n[i]; F+=[[O0[i],O0[j],O1[j]],[O0[i],O1[j],O1[i]],[I0[j],I0[i],I1[i]],[I0[j],I1[i],I1[j]],[O0[j],O0[i],I0[i]],[O0[j],I0[i],I0[j]],[O1[i],O1[j],I1[j]],[O1[i],I1[j],I1[i]]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def extrude(poly,z0,z1):
    P=np.asarray(poly); m=len(P); T=tri2d(P); ar=(P[:,0]*np.roll(P[:,1],-1)-np.roll(P[:,0],-1)*P[:,1]).sum(); V=np.concatenate([np.c_[P,np.full(m,z0)],np.c_[P,np.full(m,z1)]]); F=[]
    for t in T: F.append([m+t[0],m+t[1],m+t[2]] if ar>0 else [m+t[0],m+t[2],m+t[1]]); F.append([t[0],t[2],t[1]] if ar>0 else [t[0],t[1],t[2]])
    for i in range(m): j=(i+1)%m; F+=[[i,j,m+j],[i,m+j,m+i]] if ar>0 else [[i,m+j,j],[i,m+i,m+j]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def sector(r0,r1,a0,a1,z0,z1):
    n=max(8,int(abs(a1-a0)*r1/0.4)); ang=np.linspace(a0,a1,n); return extrude(np.vstack([np.c_[r1*np.cos(ang),r1*np.sin(ang)],np.c_[r0*np.cos(ang),r0*np.sin(ang)][::-1]]),z0,z1)
def rect(ang,r0,r1,half): c,s=math.cos(ang),math.sin(ang); return np.array([(x*c-y*s,x*s+y*c) for x,y in [(r0,-half),(r1,-half),(r1,half),(r0,half)]])
rep={}
def emit(path,name,shells,note=""):
    bad=sum(rc.edge_manifold_check(F)[1] for V,F in shells); V,F=g.merge(shells); rc.write_stl(path,V,F,name)
    rep[name]=dict(file=path,tris=int(len(F)),nonmanifold_edges=int(bad),bbox=[round(float(x),2) for x in (*V.min(0),*V.max(0))],note=note)
v11=json.load(open("kit_v11/PRINT/report.json")); lane=v11["lane_map"]
# ------------------------------------------------------------------ central PCB cylinder
m=4320; angs=np.linspace(0,2*np.pi,m,endpoint=False); ro=np.full(m,HUB_R)
def notch(a,w,d): mk=np.abs(wrap(angs-a))*HUB_R<w/2; ro[mk]=HUB_R-d
port_deg=[]
for k in range(1,7):
    p=PSI(k); notch(math.radians(p),TRACK_W,TRACK_D)
    for off in (6,11,16): notch(math.radians(p+off),1.8,1.4); port_deg.append((p+off)%360)
outer=np.c_[ro*np.cos(angs),ro*np.sin(angs)]; inner=circ(HUB_RI,m); port_deg=sorted(port_deg); HW=1.0/HUB_R
Z_P0,Z_P1=38.0,40.0
shells=[ring(outer,inner,6.0,Z_P0),ring(outer,inner,Z_P1,41.3)]
for i in range(18):                                                                   # tube-wall band between port windows (2.0 wide x 2.0 tall windows at the lane angles)
    a0=math.radians(port_deg[i])+HW; a1=math.radians(port_deg[(i+1)%18])-HW
    if a1<a0: a1+=2*np.pi
    span=a1-a0; d=(angs-a0)%(2*np.pi); idx=np.where(d<=span)[0]; idx=idx[np.argsort(d[idx])]
    pts=outer[idx]; ins=inner[idx][::-1]; shells.append(extrude(np.vstack([pts,ins]),Z_P0-0.1,Z_P1+0.1))
roof_win=[45,135,225,315]; hwr=2.0/30.0                                                  # roof: 4 vent/fill windows 4 x 4 at r=30
r_lo,r_hi=28.0,32.0; edges=[math.radians(a) for a in roof_win]
for i in range(4):
    a0=edges[i]+hwr; a1=edges[(i+1)%4]-hwr; a1=a1+2*np.pi if a1<a0 else a1; shells.append(sector(10.0,52.0,a0,a1,41.3,44.5))
for a in edges:
    shells.append(sector(10.0,r_lo,a-hwr-0.001,a+hwr+0.001,41.3,44.5)); shells.append(sector(r_hi,52.0,a-hwr-0.001,a+hwr+0.001,41.3,44.5))
shells.append(ring(circ(52.0),circ(HUB_R),38.6,41.3))                                    # L1 collar
shells+=[ring(circ(HUB_RI),circ(41.5),z-1.2,z) for z in (9.0,17.0,25.0,33.0)]            # 4 PCB ledges, 8 mm pitch
BOSS_DEG=(90,210,330); BOSS_R=41.0; boss_xy=[(BOSS_R*math.cos(math.radians(a)),BOSS_R*math.sin(math.radians(a))) for a in BOSS_DEG]
for cx,cy in boss_xy:                                                                   # M3 heat-set insert boss: D6.8 post, D4.0 x 9 deep hole from below, 2 mm cap
    V,F=ring(circ(3.4,40),circ(2.0,40),6.0,15.0); shells.append((V+[cx,cy,0],F)); V,F=extrude(circ(3.4,40),15.0,17.0); shells.append((V+[cx,cy,0],F))
for k in range(2,7):
    zs=lane[f"layer_{k}"]["stop_z"]; p=math.radians(PSI(k))
    if zs<41.3: shells.append(extrude(rect(p,HUB_R-TRACK_D-0.2,HUB_R+0.1,TRACK_W/2+0.05),zs,41.3))
    shells.append(extrude(rect(p,HUB_R-TRACK_D-0.1,HUB_R-TRACK_D+1.1,1.5),zs-3.4,zs-2.2))
emit(f"{D['hub']}/CORE_PCB_CYLINDER_central_former.stl","CORE_PCB_CYLINDER",shells,"tube r44-49.5 z6-41.3; 6 numbered blind tracks; 18 closed wire lanes ending in 18 lead-port windows (2.0 x 2.0 at z38-40); 3 M3 heat-set bosses at 90/210/330 deg r41; 4 PCB ledges; roof with D20 port + 4 vent/fill windows 4x4 at r30")
# ------------------------------------------------------------------ clamp flange + lock collar (replaces floor plate and collar ring)
H_R,H_HALF=41.0,1.8/41.0; sh=[]; hs=[math.radians(a) for a in BOSS_DEG]
for i in range(3):
    a0=hs[i]+H_HALF; a1=hs[(i+1)%3]-H_HALF; a1=a1+2*np.pi if a1<a0 else a1; sh.append(sector(8.0,57.0,a0,a1,3.4,6.1))
for a in hs:
    sh.append(sector(8.0,H_R-1.8,a-H_HALF-0.001,a+H_HALF+0.001,3.4,6.1)); sh.append(sector(H_R+1.8,57.0,a-H_HALF-0.001,a+H_HALF+0.001,3.4,6.1))
sh.append(ring(circ(57.0,120),circ(49.7,120),6.0,10.0))
emit(f"{D['pins']}/CLAMP_FLANGE_with_lock_collar.stl","CLAMP_FLANGE",sh,"flange r8-57 z3.4-6.1 with 3 M3 clearance windows 3.6 x 3.6 at r41 (90/210/330), lock collar r49.7-57 z6-10 carrying the interface-6 pins")
# ------------------------------------------------------------------ test coupons (same dimensions as the real parts)
a=np.radians(np.arange(-12,12.01,0.1)); rr=np.full(len(a),HUB_R)
rr[np.abs(a)*HUB_R<TRACK_W/2]=HUB_R-TRACK_D; rr[np.abs(a-math.radians(7))*HUB_R<0.9]=HUB_R-1.4
emit(f"{D['cpn']}/COUPON_hub_segment_track_lane.stl","COUPON_hub",[extrude(np.vstack([np.c_[rr*np.cos(a),rr*np.sin(a)],np.c_[HUB_RI*np.cos(a),HUB_RI*np.sin(a)][::-1]]),0.0,15.0)],"24 deg hub segment: one 4.0 x 3.0 track at 0 deg, one 1.8 x 1.4 lane at 7 deg")
ph=np.radians(np.arange(-12,12.01,0.1)); rin=np.full(len(ph),BORE); rin[np.abs(ph)*BORE<TOOTH_W/2]=BORE-TOOTH_H
d_=ph-math.radians(8); off=51.7*np.sin(d_); ins=(np.abs(off)<1.9)&(np.cos(d_)>0); far=51.7*np.cos(d_)+np.sqrt(np.maximum(1.9**2-off**2,0)); rin=np.where(ins,np.maximum(rin,far),rin)
emit(f"{D['cpn']}/COUPON_layer_segment_tooth_notch.stl","COUPON_layer",[extrude(np.vstack([np.c_[62*np.cos(ph),62*np.sin(ph)],np.c_[rin*np.cos(ph),rin*np.sin(ph)][::-1]]),0.0,3.6)],"24 deg layer segment: bore 49.9, key tooth 3.6 x 2.6 at 0 deg, pin half-hole at 8 deg")
V1,F1=extrude(circ(1.5,28),0.0,3.6); V2,F2=extrude(circ(2.1,28),3.6,4.4); V3,F3=extrude(circ(1.5,28),4.4,8.0)
emit(f"{D['cpn']}/COUPON_pin_single.stl","COUPON_pin",[(V1,F1),(V2,F2),(V3,F3)],"one stepped pin: stem D3.0 x 3.6, shoulder D4.2 x 0.8, stem D3.0 x 3.6")
# ------------------------------------------------------------------ copy proven parts from v11
for k in range(1,7):
    for ext in ("petal_coil_former.stl","winding_centerline.csv"): shutil.copy(f"kit_v11/PRINT/FORMER_L{k}_{ext}",f"{D['form']}/FORMER_L{k}_{ext}")
for i in range(1,7):
    for f in glob.glob(f"kit_v11/PRINT/PINS_interface_{i}_x3*.stl"): shutil.copy(f,D['pins']+"/"+os.path.basename(f))
shutil.copy("kit_v11/PRINT/L7_RX_tray_cassette.stl",f"{D['tray']}/RX_TRAY_cassette.stl")
# ------------------------------------------------------------------ verification table
pt=v11["pin_table"]; ver={}
ver["lead_ports"]=dict(count=18,window_mm="2.0 wide x 2.0 tall",z_range=[Z_P0,Z_P1],angles_deg=[round(x,2) for x in port_deg],wall_thickness_at_lane_mm=round(HUB_R-1.4-HUB_RI,2),match_lane_angles=all(any(abs(((port_deg[i]-(PSI(k)+o))+180)%360-180)<0.01 for k in range(1,7) for o in (6,11,16)) for i in range(18)))
ver["m3_bosses"]=dict(angles_deg=list(BOSS_DEG),radius_mm=BOSS_R,post_dia=6.8,insert_hole_dia=4.0,hole_depth=9.0,z_range=[6.0,17.0],note="PCB disc in slot 1 (z=9) needs 3 relief notches R4.5 at these angles; flange windows 3.6 square at the same positions; use M3x8 screws into heat-set inserts")
ver["fit_clearances_mm"]=dict(layer_bore_vs_hub_radial=round(BORE-HUB_R,2),tooth_vs_track_width=round(TRACK_W-TOOTH_W,2),tooth_vs_track_depth=round(TRACK_D-TOOTH_H,2),pin_stem_in_notch_radial=round(1.9-1.5,2),pin_shoulder_to_hub=round(51.7-2.1-HUB_R,2),collar_inner_vs_hub_radial=round(49.7-HUB_R,2),layer_gap=0.8)
ver["boss_vs_lane_angle_gaps_deg"]=[round(min(abs(((b-(PSI(k)+o))+180)%360-180) for k in range(1,7) for o in (0,6,11,16)),1) for b in BOSS_DEG]
ver["stack"]=v11["stack"]; ver["layer_audit_ref"]="06_DATA/audit.json, audit_groove_detrended.json"
json.dump(dict(parts=rep,verification=ver),open(f"{D['data']}/hub_flange_coupons_report.json","w"),indent=1,default=float)
for f in ("kit_v11/audit.json","kit_v11/audit_groove_detrended.json","kit_v11/PRINT/report.json"): shutil.copy(f,D['data']+"/"+os.path.basename(f).replace("report.json","formers_report.json"))
print(json.dumps({k:(v["nonmanifold_edges"],v["tris"],v["bbox"]) for k,v in rep.items()},default=float)); print(json.dumps(ver,default=float)[:1500])
