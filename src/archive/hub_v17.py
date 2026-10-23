#!/usr/bin/env python3
"""v12: central PCB cylinder with 18 lead ports + 3 M3 boss posts + roof vent ports, clamp flange with lock collar, fit coupons, verification."""
import math, json, os, csv, hashlib, shutil, glob, struct, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
OUT="kit_v17/SET"; D={"form":f"{OUT}/01_FORMERS","hub":f"{OUT}/02_CORE_PCB_CYLINDER","pins":f"{OUT}/03_PINS_AND_CLAMP","tray":f"{OUT}/04_RX_TRAY","cpn":f"{OUT}/05_TEST_COUPONS","data":f"{OUT}/06_DATA"}
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
shells=[ring(outer,inner,3.2,Z_P0),ring(outer,inner,Z_P1,41.3)]
for i in range(18):                                                                   # tube-wall band between port windows (2.0 wide x 2.0 tall windows at the lane angles)
    a0=math.radians(port_deg[i])+HW; a1=math.radians(port_deg[(i+1)%18])-HW
    if a1<a0: a1+=2*np.pi
    span=a1-a0; d=(angs-a0)%(2*np.pi); idx=np.where(d<=span)[0]; idx=idx[np.argsort(d[idx])]
    pts=outer[idx]; ins=inner[idx][::-1]; shells.append(extrude(np.vstack([pts,ins]),Z_P0-0.1,Z_P1+0.1))
roof_win=[45,135,225,315]; hwr=2.0/30.0; edges=[math.radians(a) for a in roof_win]
PX=[(12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,15.0)]; HR=0.85          # pixel rings (radius, count, phase deg): 3 depth rings + 1 noise ring
def hole_ints(r,cnt,ph): return sorted([(math.radians(ph+i*360/cnt)-HR/r,math.radians(ph+i*360/cnt)+HR/r) for i in range(cnt)])
def band(r0,r1,forb,z0,z1):
    if not forb: return [ring(circ(r1,720),circ(r0,720),z0,z1)]
    forb=sorted(forb); out=[]
    for i in range(len(forb)):
        a0=forb[i][1]; a1=forb[(i+1)%len(forb)][0]+(2*np.pi if i==len(forb)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
vents=[(a-hwr,a+hwr) for a in edges]
bands=[(10.0,PX[0][0]-HR,[]),(PX[0][0]-HR,PX[0][0]+HR,hole_ints(*PX[0])),(PX[0][0]+HR,PX[1][0]-HR,[]),(PX[1][0]-HR,PX[1][0]+HR,hole_ints(*PX[1])),(PX[1][0]+HR,PX[2][0]-HR,[]),(PX[2][0]-HR,PX[2][0]+HR,hole_ints(*PX[2])),(PX[2][0]+HR,28.0,[]),(28.0,32.0,vents),(32.0,PX[3][0]-HR,[]),(PX[3][0]-HR,PX[3][0]+HR,hole_ints(*PX[3])),(PX[3][0]+HR,52.0,[])]
for r0,r1,f in bands: shells+=band(r0,r1,f,41.3,44.5)
# LB1 display-board posts under the roof: 3 posts D4 (z37.3-41.3) with a D1.7 pilot hole from below, at the angles furthest from the 18 lead ports
free=[];
for a in np.arange(0,360,0.5): free.append((min(abs(((a-p)+180)%360-180) for p in port_deg),a))
chosen=[]
for _ in range(3):
    cand=[(d,a) for d,a in free if all(abs(((a-c)+180)%360-180)>=100 for c in chosen)]; chosen.append(max(cand)[1])
POST_DEG=sorted(chosen)
for a in POST_DEG:
    cx,cy=39.0*math.cos(math.radians(a)),39.0*math.sin(math.radians(a)); V,F=ring(circ(2.0,40),circ(0.85,40),37.3,40.9); shells.append((V+[cx,cy,0],F)); V,F=extrude(circ(2.0,40),40.9,41.3); shells.append((V+[cx,cy,0],F))
shells.append(ring(circ(52.0),circ(HUB_R),29.2,41.3))                                    # L1 collar
shells+=[ring(circ(HUB_RI),circ(41.5),z-1.2,z) for z in (9.0,17.0,25.0,33.0)]            # 4 PCB ledges, 8 mm pitch
BOSS_DEG=(90,210,330); BOSS_R=41.0; boss_xy=[(BOSS_R*math.cos(math.radians(a)),BOSS_R*math.sin(math.radians(a))) for a in BOSS_DEG]
for cx,cy in boss_xy:                                                                   # M3 heat-set insert boss: D6.8 post, D4.0 x 9 deep hole from below, 2 mm cap
    V,F=ring(circ(3.4,40),circ(2.0,40),3.2,12.2); shells.append((V+[cx,cy,0],F)); V,F=extrude(circ(3.4,40),12.2,14.2); shells.append((V+[cx,cy,0],F))
f13=json.load(open("kit_v15/PRINT/report.json")); LUG_DEG=f13["spec"]["L1_bond_key_notches_deg"]
ripf=lambda j,R,ph:0.30*(R/116.5)**2*math.cos(12*(ph-math.radians(GOLD*(j-1))))
def zb1(R,ph): return 3.2+5*(3.6+0.8)
lug_tab=[]
for th in LUG_DEG:
    ph=math.radians(th); z0=zb1(50.0,ph)-0.2; z1=zb1(50.0,ph)+3.6+ripf(1,50.0,ph)+0.3; V,F=extrude(circ(1.4,28),z0,z1); shells.append((V+[50.0*math.cos(ph),50.0*math.sin(ph),0],F)); lug_tab.append(dict(theta_deg=round(th,2),z=[round(z0,2),round(z1,2)]))
for k in range(2,7):
    zs=3.2+(6-k)*4.4+3.6+0.1+0.5; p=math.radians(PSI(k))
    if zs<41.3: shells.append(extrude(rect(p,HUB_R-TRACK_D-0.2,HUB_R+0.1,TRACK_W/2+0.05),zs,41.3))
    shells.append(extrude(rect(p,HUB_R-TRACK_D-0.1,HUB_R-TRACK_D+1.1,1.5),zs-3.4,zs-2.2))
emit(f"{D['hub']}/CORE_PCB_CYLINDER_v2_display.stl","CORE_PCB_CYLINDER_v2",shells,"v15 hub + 66 light-pipe holes (D1.7) in the roof in 4 polar rings + 3 LB1 posts under the roof")
import csv
px=[]
for ri,(r,c,ph) in enumerate(PX):
    for i in range(c): a=(ph+i*360/c)%360; px.append((ri+1,i,round(a,3),r,round(r*math.cos(math.radians(a)),3),round(r*math.sin(math.radians(a)),3)))
csv.writer(open(f"{D['hub']}/PIXEL_MAP_66.csv","w")).writerows([("ring","index","azimuth_deg","radius_mm","x_mm","y_mm")]+px)
json.dump(dict(rings=PX,hole_dia=1.7,post_deg=POST_DEG,post_radius=39.0,pixels=len(px),report=rep),open(f"{D['hub']}/hub_v2_report.json","w"),indent=1,default=float)
print(json.dumps({k:(v["nonmanifold_edges"],v["tris"],v["bbox"]) for k,v in rep.items()},default=float),POST_DEG,len(px))
