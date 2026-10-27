#!/usr/bin/env python3
"""v12: central PCB cylinder with 18 lead ports + 3 M3 boss posts + roof vent ports, clamp flange with lock collar, fit coupons, verification."""
import math, json, os, csv, hashlib, shutil, glob, struct, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, solid_union as su
from render_v6 import tri2d
OUT="kit_v22/SET"; D={"form":f"{OUT}/01_FORMERS","hub":f"{OUT}/02_CORE_PCB_CYLINDER","pins":f"{OUT}/03_PINS_AND_CLAMP","tray":f"{OUT}/04_RX_TRAY","cpn":f"{OUT}/05_TEST_COUPONS","data":f"{OUT}/06_DATA"}
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
    bad=sum(rc.edge_manifold_check(F)[1] for V,F in shells); V,F,info=su.merge_closed(shells,g.merge(shells)); rc.write_stl(path,V,F,name)
    rep[name]=dict(file=path,tris=int(len(F)),nonmanifold_edges=int(bad),bbox=[round(float(x),2) for x in (*V.min(0),*V.max(0))],note=note,solid_union=info)
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
RX_DEG=sorted([(PSI(k)+16)%360 for k in range(1,7)]); RZ0,RZ1=4.3,6.3
EX=178.0; EXH=7.5; EZ0,EZ1=34.4,40.6                                                  # umbilical exit window at 178 deg: 15 wide (13.3 at the inner face) x 6.2 tall (z34.4-40.6)
GZ0,GIN,GOUT=39.6,45.6,48.6                                                          # TX-lead channel in the wall top: r45.6..48.6, z39.6..41.3; the roof carries the other half (analytic arcs: no notch steps in the outer skin above z39.6)
shells=[ring(outer,inner,3.2,RZ0),ring(outer,inner,RZ1,EZ0),ring(circ(GIN,m),inner,EZ1,41.3),ring(circ(HUB_R,m),circ(GOUT,m),EZ1,41.3)]
for i in range(6):                                                                    # 6 low RX entry windows 2.0 x 2.0 at z4.3-6.3 (RX leads enter right above the receive board)
    a0=math.radians(RX_DEG[i])+HW; a1=math.radians(RX_DEG[(i+1)%6])-HW
    if a1<a0: a1+=2*np.pi
    span=a1-a0; d=(angs-a0)%(2*np.pi); idx=np.where(d<=span)[0]; idx=idx[np.argsort(d[idx])]; shells.append(extrude(np.vstack([outer[idx],inner[idx][::-1]]),RZ0-0.1,RZ1+0.1))
def piece(a0,a1,z0,z1,chunk=150):
    if a1<a0: a1+=2*np.pi
    span=a1-a0; d=(angs-a0)%(2*np.pi); idx=np.where(d<=span)[0]; idx=idx[np.argsort(d[idx])]; out=[]; k=0
    while k<len(idx)-1:
        c=idx[k:k+chunk+1]; out.append(extrude(np.vstack([outer[c],inner[c][::-1]]),z0,z1)); k+=chunk
    return out
def grooved(a0,a1,z0,z1):
    """wall segment z0..z1 with the lead channel removed above GZ0"""
    if a1<a0: a1+=2*np.pi
    out=[]
    if z0<GZ0: out+=piece(a0,a1,z0,min(z1,GZ0))
    if z1>GZ0: zz=max(z0,GZ0); out+=[sector(HUB_RI,GIN,a0,a1,zz,z1),sector(GOUT,HUB_R,a0,a1,zz,z1)]
    return out
win=sorted([(p,1.0) for p in port_deg]+[(EX,EXH)])                                   # 18 lead ports (2 mm) + the exit window (13 mm)
for i in range(len(win)):
    a0=math.radians(win[i][0])+win[i][1]/HUB_R; a1=math.radians(win[(i+1)%len(win)][0])-win[(i+1)%len(win)][1]/HUB_R; shells+=grooved(a0,a1,Z_P0-0.1,Z_P1+0.1)
ea0=math.radians(EX)+EXH/HUB_R; ea1=math.radians(EX)-EXH/HUB_R+2*np.pi
shells+=piece(ea0,ea1,EZ0-0.0,Z_P0+0.1); shells+=grooved(ea0,ea1,Z_P1-0.1,EZ1+0.0)      # exit-window bands below and above the port band
roof_win=[45,135,225,315]; hwr=2.0/30.0; edges=[math.radians(a) for a in roof_win]
PX=[(12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,7.5)]; HR=0.85          # pixel rings (radius, count, phase deg): 3 depth rings + 1 noise ring
def hole_ints(r,cnt,ph): return sorted([(math.radians(ph+i*360/cnt)-HR/r,math.radians(ph+i*360/cnt)+HR/r) for i in range(cnt)])
def band(r0,r1,forb,z0,z1):
    if not forb: return [ring(circ(r1,720),circ(r0,720),z0,z1)]
    forb=sorted(forb); out=[]
    for i in range(len(forb)):
        a0=forb[i][1]; a1=forb[(i+1)%len(forb)][0]+(2*np.pi if i==len(forb)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
vents=[(a-hwr,a+hwr) for a in edges]
bands=[(10.0,PX[0][0]-HR,[]),(PX[0][0]-HR,PX[0][0]+HR,hole_ints(*PX[0])),(PX[0][0]+HR,PX[1][0]-HR,[]),(PX[1][0]-HR,PX[1][0]+HR,hole_ints(*PX[1])),(PX[1][0]+HR,PX[2][0]-HR,[]),(PX[2][0]-HR,PX[2][0]+HR,hole_ints(*PX[2])),(PX[2][0]+HR,28.0,[]),(28.0,32.0,vents),(32.0,PX[3][0]-HR,[]),(PX[3][0]-HR,PX[3][0]+HR,hole_ints(*PX[3])),(PX[3][0]+HR,52.0,[])]
pass  # roof is a separate removable plate in v5
ecw=EXH/50.0
shells+=[ring(circ(52.0,720),circ(HUB_R,720),29.2,EZ0),ring(circ(52.0,720),circ(HUB_R,720),EZ1,41.3),]   # L1 collar with the exit window
ca0=math.radians(EX)+ecw; ca1=math.radians(EX)-ecw+2*np.pi; nch=int(math.ceil((ca1-ca0)/math.radians(15))); cb=np.linspace(ca0,ca1,nch+1)
shells+=[sector(HUB_R,52.0,cb[q],cb[q+1],EZ0,EZ1) for q in range(nch)]                                    # L1 collar
pass
pass
BOSS_DEG=(22.5,157.5,247.5); BOSS_R=28.0; boss_xy=[(BOSS_R*math.cos(math.radians(a)),BOSS_R*math.sin(math.radians(a))) for a in BOSS_DEG]
for cx,cy in boss_xy:                                                                   # M3 heat-set insert boss: D6.8 post, D4.0 x 9 deep hole from below, 2 mm cap
    V,F=ring(circ(3.4,40),circ(2.0,40),3.2,8.6); shells.append((V+[cx,cy,0],F)); V,F=extrude(circ(3.4,40),8.6,9.6); shells.append((V+[cx,cy,0],F))

SPD=math.radians(90.0)
def pring(r0,r1,z0,z1,gaps=None):
    if not gaps: return [ring(circ(r1,720),circ(r0,720),z0,z1)]
    g=sorted(gaps); out=[]
    for i in range(len(g)):
        a0=g[i][1]; a1=g[(i+1)%len(g)][0]+(2*np.pi if i==len(g)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
FZ0,FZ1=9.0,9.8
shells.append(extrude(circ(28.0,720),FZ0,FZ1)); shells+=pring(28.0,37.0,FZ0,FZ1,[(SPD-6.0/32.5,SPD+6.0/32.5)]); shells+=pring(37.0,44.3,FZ0,FZ1)     # floor with the 12 mm spine slot at r28-37
RIBS=[24.0,48.0,109.0,135.0,225.0,244.0,300.0,317.0]; SLOTS=[(20.0,21.9),(27.0,28.9)]; ZR=19.0; ZP=35.0; ZTOP=39.2
POST_R=42.5
for a in RIBS:
    hw=3.0/40.8; a0=math.radians(a)-hw; a1=math.radians(a)+hw
    shells.append(sector(37.2,44.5,a0,a1,ZR,20.0)); shells.append(sector(37.2,44.5,a0,a1,21.9,27.0)); shells.append(sector(37.2,44.5,a0,a1,28.9,ZP))
    for (z0,z1) in SLOTS: shells.append(sector(39.3,44.5,a0,a1,z0,z1))
    shells.append(sector(37.2,39.5,a0,a1,ZP,ZTOP))
    cx,cy=POST_R*math.cos(math.radians(a)),POST_R*math.sin(math.radians(a)); V,F=ring(circ(3.0,40),circ(2.0,40),ZP,41.3); shells.append((V+[cx,cy,0],F))      # M3 insert post D6 / D4, 5 mm deep
for sg in (1,-1):
    ai=SPD+sg*6.0/38.7; ao=SPD+sg*7.2/38.7; shells.append(sector(37.2,44.5,min(ai,ao),max(ai,ao),FZ1,ZTOP))
f13=json.load(open("kit_v15/PRINT/report.json")); LUG_DEG=f13["spec"]["L1_bond_key_notches_deg"]
ripf=lambda j,R,ph:0.30*(R/116.5)**2*math.cos(12*(ph-math.radians(GOLD*(j-1))))
def zb1(R,ph): return 3.2+5*(3.6+0.8)
lug_tab=[]
for th in LUG_DEG:
    ph=math.radians(th); z0=zb1(50.0,ph)-0.2; z1=zb1(50.0,ph)+3.6+ripf(1,50.0,ph)+0.3; V,F=extrude(circ(1.4,28),z0,z1); shells.append((V+[50.0*math.cos(ph),50.0*math.sin(ph),0],F)); lug_tab.append(dict(theta_deg=round(th,2),z=[round(z0,2),round(z1,2)]))
for k in range(2,7):
    zs=3.2+(6-k)*4.4+3.6+0.1+0.5; p=math.radians(PSI(k))
    if zs<GZ0-0.2: shells.append(extrude(rect(p,HUB_R-TRACK_D-0.2,HUB_R+0.1,TRACK_W/2+0.05),zs,GZ0-0.2))
    shells.append(extrude(rect(p,HUB_R-TRACK_D-0.1,HUB_R-TRACK_D+1.1,1.5),zs-3.4,zs-2.2))
emit(f"{D['hub']}/CORE_CYLINDER_v5_integrated.stl","CORE_PCB_CYLINDER_v3",shells,"v15 hub + 66 light-pipe holes in the roof + 6 low RX entry ports (z4.3-6.3) + 4th ledge notched at 0 deg for the TX lead corridor; no posts")
import csv
px=[]
for ri,(r,c,ph) in enumerate(PX):
    for i in range(c): a=(ph+i*360/c)%360; px.append((ri+1,i,round(a,3),r,round(r*math.cos(math.radians(a)),3),round(r*math.sin(math.radians(a)),3)))
csv.writer(open(f"{D['hub']}/PIXEL_MAP_66.csv","w")).writerows([("ring","index","azimuth_deg","radius_mm","x_mm","y_mm")]+px)
json.dump(dict(rings=PX,hole_dia=1.7,rx_port_deg=RX_DEG,pixels=len(px),report=rep),open(f"{D['hub']}/hub_v2_report.json","w"),indent=1,default=float)
print(json.dumps({k:(v["nonmanifold_edges"],v["tris"],v["bbox"]) for k,v in rep.items()},default=float),RX_DEG)
