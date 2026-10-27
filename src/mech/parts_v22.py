import math, json, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, solid_union as su
from render_v6 import tri2d
OUT="kit_v22"; GOLD=137.50776405; rep={}
def circ(r,m=360): t=np.linspace(0,2*np.pi,m,endpoint=False); return np.c_[r*np.cos(t),r*np.sin(t)]
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
def rectp(ang,r0,r1,half): c,s=math.cos(ang),math.sin(ang); return np.array([(x*c-y*s,x*s+y*c) for x,y in [(r0,-half),(r1,-half),(r1,half),(r0,half)]])
def rect_c(cx,cy,ang,hr,ht): c,s=math.cos(ang),math.sin(ang); return np.array([(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(hr,-ht),(hr,ht),(-hr,ht),(-hr,-ht)]])
def emit(name,shells,note):
    bad=sum(rc.edge_manifold_check(F)[1] for V,F in shells); V, F, _su = su.merge_closed(shells, g.merge(shells)); rc.write_stl(f"{OUT}/{name}.stl",V,F,name); rep[name]=dict(shells=len(shells),tris=int(len(F)),nonmanifold_edges=int(bad),bbox=[round(float(x),2) for x in (*V.min(0),*V.max(0))],note=note)

def pring(r0,r1,z0,z1,gaps=None):
    if not gaps: return [ring(circ(r1,720),circ(r0,720),z0,z1)]
    g=sorted(gaps); out=[]
    for i in range(len(g)):
        a0=g[i][1]; a1=g[(i+1)%len(g)][0]+(2*np.pi if i==len(g)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
PX=[(12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,7.5)]; HR=0.85
def hole_ints(r,cnt,ph): return sorted([(math.radians(ph+i*360/cnt)-HR/r,math.radians(ph+i*360/cnt)+HR/r) for i in range(cnt)])
RIBS=[24.0,48.0,109.0,135.0,225.0,244.0,300.0,317.0]; vents=[(math.radians(a)-2.0/30.0,math.radians(a)+2.0/30.0) for a in (45,135,225,315)]
# ---------------- 1. removable roof plate (z41.3-44.5): pixel holes, vent windows, D20 port, 8 slotted counterbores over the insert posts
sh=[]
sc=[(math.radians(a)-3.1/42.5,math.radians(a)+3.1/42.5) for a in RIBS]; sl=[(math.radians(a)-1.7/42.5,math.radians(a)+1.7/42.5) for a in RIBS]
bands=[(10.0,PX[0][0]-HR,None),(PX[0][0]-HR,PX[0][0]+HR,hole_ints(*PX[0])),(PX[0][0]+HR,PX[1][0]-HR,None),(PX[1][0]-HR,PX[1][0]+HR,hole_ints(*PX[1])),(PX[1][0]+HR,PX[2][0]-HR,None),(PX[2][0]-HR,PX[2][0]+HR,hole_ints(*PX[2])),(PX[2][0]+HR,28.0,None),(28.0,32.0,vents),(32.0,PX[3][0]-HR,None),(PX[3][0]-HR,PX[3][0]+HR,hole_ints(*PX[3])),(PX[3][0]+HR,39.5,None)]
for r0,r1,f in bands: sh+=pring(r0,r1,41.3,44.5,f)
sh+=pring(39.5,45.5,41.3,42.1,sl); sh+=pring(39.5,45.5,42.1,44.5,sc); sh+=pring(45.5,45.6,41.3,44.5); sh+=pring(45.6,48.6,43.5,44.5); sh+=pring(48.6,52.0,41.3,44.5)     # TX-lead channel r45.6-48.6 z41.3-43.5 under the roof (mates the wall-top groove)
emit("ROOF_PLATE_v5",sh,"removable roof r52, z41.3-44.5: 66 pixel holes D1.7, 4 vent windows at r28-32, D20 port, 8 screw slots 6.0 x 3.4 with 6.0 x 6.2 counterbores (M3 nylon, 2.4 deep) at r42.5 over the 8 rib insert posts; TX-lead channel r45.6-48.6 under the roof (mates the wall-top groove); seal with silicone on the collar top r49.6-52 and pot after wiring")
# ---------------- 2. analog tray (z9.8-10.6): two D40 board seats, shim ribs, 12 mm spine notch
tr=[extrude(circ(28.0,720),9.8,10.6)]+pring(28.0,38.8,9.8,10.6,[(math.radians(90)-8.0/33.4,math.radians(90)+8.0/33.4)])
for cx in (-20.3,20.3):
    for k in range(3):
        a=math.radians(90+120*k); tr.append(extrude(circ(1.5,24)+[cx+17.0*math.cos(a),17.0*math.sin(a)],10.6,11.1))
for x in (-0.45,0.45): tr.append(extrude(np.array([(x-0.25,-34),(x+0.25,-34),(x+0.25,34),(x-0.25,34)]),10.6,12.2))
emit("ANALOG_TRAY_v5",tr,"D77.6 tray on the floor: seats for AB1A (x=-20.3) and AB1B (x=+20.3), 3 standoffs each (0.5 above the tray, board bottom z11.1), shim rib pair for the 0.3 mm mesh/graphite partition, 16 mm notch at 90 deg over the floor slot (clears the spine walls)")
# ---------------- 3. septum frame (z20.1-21.8): ring r31-39 (tabs in the rib slots) + outer sectors to r43.6 between the ribs and the spine channel
gaps=[(math.radians(a)-3.5/41.3,math.radians(a)+3.5/41.3) for a in RIBS]+[(math.radians(90)-7.8/41.3,math.radians(90)+7.8/41.3)]
sp=pring(31.0,39.0,20.1,21.8,[(math.radians(90)-8.0/35.0,math.radians(90)+8.0/35.0)])+pring(39.0,43.6,20.1,21.8,gaps)
emit("SEPTUM_FRAME_v5",sp,"septum frame: ring r31-39 whose edge sits in the rib slots (z20.0-21.9, 0.1 mm each side), outer sectors to r43.6 with gaps at the 8 ribs and the spine channel; bond copper cloth over the D62 window and seal the rim with silicone")
# ---------------- 4. spine comb: 11.6 wide bar in the 12 mm channel with four flex windows
cb=[]; zs=[(9.8,12.0),(14.0,19.5),(22.5,26.5),(29.5,38.0)]
for z0,z1 in zs: cb.append(extrude(np.array([(-5.8,37.4),(5.8,37.4),(5.8,40.0),(-5.8,40.0)]),z0,z1))
emit("SPINE_COMB_v5",cb,"clip-in comb for the 12 mm spine channel at 90 deg: 11.6 x 2.6 bar segments with 2.0-3.0 mm windows at z12-14, z19.5-22.5, z26.5-29.5, z38-39.2 for the rigid-flex tails; holds the Z-fold radius and gives strain relief")
json.dump(rep,open("kit_v22/parts_report.json","w"),indent=1,default=float); print({k:(v["nonmanifold_edges"],v["tris"]) for k,v in rep.items()})
