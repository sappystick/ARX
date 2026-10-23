import math, json, os, numpy as np
import rodin_core_v4 as rc
from render_v6 import tri2d
GOLD=137.50776405; PN,G,ZRX,REL=3.6,0.8,3.2,0.30
for d in ("kit_v15/SET/03_PINS","kit_v15/SET/04_BASE_PLATE_RX_TRAY","kit_v15/SET/06_DATA"): os.makedirs(d,exist_ok=True)
rip=lambda j,R,th: REL*(R/116.5)**2*math.cos(12*(th-math.radians(GOLD*(j-1))))
zbase=lambda k: ZRX+(6-k)*(PN+G)
def revolve_solid(profile,n=64):
    ang=np.linspace(0,2*np.pi,n,endpoint=False); V=[]; idx=[]
    for r,z in profile:
        if r==0: idx.append(np.full(n,len(V))); V.append((0,0,z))
        else: idx.append(len(V)+np.arange(n)); V+=[(r*math.cos(a),r*math.sin(a),z) for a in ang]
    F=[]; m=len(profile)
    for j in range(m):
        j2=(j+1)%m; r0,r1=profile[j][0],profile[j2][0]
        if r0==0 and r1==0: continue
        for i in range(n):
            i2=(i+1)%n; a,b,c,d=idx[j][i],idx[j2][i],idx[j2][i2],idx[j][i2]
            if r0==0: F.append([a,b,c])
            elif r1==0: F.append([a,c,d])
            else: F+=[[a,b,c],[a,c,d]]
    V=np.array(V); F=np.array(F)
    if rc.signed_volume(V,F)<0: F=F[:,::-1]
    return V,F
def edges_ok(F):
    e=np.vstack([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]); k=e[:,0].astype(np.int64)*10**7+e[:,1]; rk=e[:,1].astype(np.int64)*10**7+e[:,0]; return int((~np.isin(k,rk)).sum()),int(len(k)-len(np.unique(k)))
v11=json.load(open("kit_v11/PRINT/report.json")); tab=[]
for p in v11["pin_table"]:
    i=p["interface"]
    if i>=6: continue
    th=math.radians(p["theta_deg"]); zb_low=zbase(i+1); top_low=zb_low+PN+rip(i+1,51.7,th); zb_up=zbase(i); top_up=zb_up+PN+rip(i,51.7,th)
    z0=zb_low+0.2; zs0=top_low; zs1=zb_up; zt=top_up-0.4
    prof=[(0,z0),(1.5,z0),(1.5,zs0),(2.1,zs0),(2.1,zs1),(1.5,zs1),(1.5,zt),(0,zt)]
    V,F=revolve_solid([(r,z-z0) for r,z in prof]); oe,dup=edges_ok(F); name=f"PIN_interface{i}_n{p['n']}_{p['theta_deg']:.1f}deg"
    rc.write_stl(f"kit_v15/SET/03_PINS/{name}.stl",V,F,name)
    tab.append(dict(file=name+".stl",interface=i,n=p["n"],theta_deg=round(p["theta_deg"],2),radius=51.7,length_mm=round(zt-z0,2),stem_lower_mm=round(zs0-z0,2),shoulder_mm=round(zs1-zs0,2),stem_upper_mm=round(zt-zs1,2),assembly_z_stem_bottom=round(z0,2),open_edges=oe,dup_edges=dup,bodies=1))
# base plate / RX tray with 3 M3 clearance windows (r41, 90/210/330) for the hub clamp screws
def sector(r0,r1,a0,a1,z0,z1):
    n=max(8,int(abs(a1-a0)*r1/0.4)); ang=np.linspace(a0,a1,n); P=np.vstack([np.c_[r1*np.cos(ang),r1*np.sin(ang)],np.c_[r0*np.cos(ang),r0*np.sin(ang)][::-1]]); T=tri2d(P); m=len(P)
    ar=(P[:,0]*np.roll(P[:,1],-1)-np.roll(P[:,0],-1)*P[:,1]).sum(); V=np.concatenate([np.c_[P,np.full(m,z0)],np.c_[P,np.full(m,z1)]]); F=[]
    for t in T: F.append([m+t[0],m+t[1],m+t[2]] if ar>0 else [m+t[0],m+t[2],m+t[1]]); F.append([t[0],t[2],t[1]] if ar>0 else [t[0],t[1],t[2]])
    for i in range(m): j=(i+1)%m; F+=[[i,j,m+j],[i,m+j,m+i]] if ar>0 else [[i,m+j,j],[i,m+i,m+j]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def ring(outer,inner,z0,z1):
    m=len(outer); V=np.concatenate([np.c_[outer,np.full(m,z0)],np.c_[outer,np.full(m,z1)],np.c_[inner,np.full(m,z0)],np.c_[inner,np.full(m,z1)]]); O0,O1,I0,I1=(np.arange(m)+k*m for k in range(4)); n=np.roll(np.arange(m),-1); F=[]
    for i in range(m): j=n[i]; F+=[[O0[i],O0[j],O1[j]],[O0[i],O1[j],O1[i]],[I0[j],I0[i],I1[i]],[I0[j],I1[i],I1[j]],[O0[j],O0[i],I0[i]],[O0[j],I0[i],I0[j]],[O1[i],O1[j],I1[j]],[O1[i],I1[j],I1[i]]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
circ=lambda r,m=720: np.c_[r*np.cos(np.linspace(0,2*np.pi,m,endpoint=False)),r*np.sin(np.linspace(0,2*np.pi,m,endpoint=False))]
hs=[math.radians(a) for a in (90,210,330)]; hw=1.7/41.0; shells=[]
for i in range(3):
    a0=hs[i]+hw; a1=hs[(i+1)%3]-hw; a1=a1+2*np.pi if a1<a0 else a1; shells.append(sector(5.0,116.5,a0,a1,0.0,0.8))
for a in hs: shells+= [sector(5.0,39.3,a-hw-0.001,a+hw+0.001,0.0,0.8),sector(42.7,116.5,a-hw-0.001,a+hw+0.001,0.0,0.8)]
shells.append(ring(circ(116.5),circ(114.5),0.0,3.2))
import golden_cone_head as g
bad=sum(rc.edge_manifold_check(F)[1] for V,F in shells); V,F=g.merge(shells); rc.write_stl("kit_v15/SET/04_BASE_PLATE_RX_TRAY/BASE_PLATE_RX_TRAY.stl",V,F,"tray")
json.dump(dict(pins=tab,base_plate=dict(file="BASE_PLATE_RX_TRAY.stl",nonmanifold_edges=int(bad),shells=len(shells),bbox=[round(float(x),2) for x in (*V.min(0),*V.max(0))],note="floor 0.8 thick with PCB recess D229 x 2.4 (rim wall 2.0 wide, 3.2 tall); 3 clearance windows 3.4 x 3.4 at r41, 90/210/330 deg for the hub M3 screws; keep the SB1R PCB copper clear of these 3 spots")),open("kit_v15/SET/06_DATA/pins_and_base_plate.json","w"),indent=1)
print(len(tab),"pins; all single-body:",all(t["open_edges"]==0 and t["dup_edges"]==0 for t in tab),"; base plate nonmanifold",bad)
print(tab[0])
