import math, json, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, solid_union as su
from render_v6 import tri2d
OUT="kit_v16/PARTS"; GOLD=137.50776405; rep={}
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
# ---------------- 1. HUB CAP for the hub-top antenna (HTA): sits on the hub roof z44.5, 4 snap hooks pass through the 4 roof vent windows
sh=[ring(circ(52.0),circ(4.0),44.5,45.4),sector(45.2,52.0,math.radians(3),math.radians(357),45.4,47.1)]
for a in (45,135,225,315):
    ar=math.radians(a); sh.append(extrude(rectp(ar,28.6,31.4,1.7),40.4,44.6)); sh.append(extrude(rectp(ar,31.3,32.4,1.7),40.4,41.2))
emit("HUB_CAP_HTA","sh" and sh,"D104 cap, 0.9 floor + recess D90.4 x 1.7 for the D90 x 1.6 HTA PCB, centre cable port D8 over the roof D20 port, 6 deg shield-drain/orientation gap in the rim at 0 deg, 4 snap hooks (3.4 x 2.8, lip 1.0) that pass through the 4 roof windows at r30 (45/135/225/315 deg) and hook under the 3.2 mm roof")
# ---------------- 2. LOTUS HOOD CARRIER: ferrite tile pockets staggered by the golden angle, bonded above L1
base=ring(circ(114.5,720),circ(52.6,720),29.4,30.4); shells=[base]; tiles=[("A",71.0,8.0,14.0,12,0.0),("B",92.0,8.0,19.0,12,(GOLD*1)%30),("C",106.5,6.5,25.0,12,(GOLD*2)%30)]; area=0.0; n_p=0
for nm,rc_,hr,ht,cnt,ph in tiles:
    for i in range(cnt):
        th=math.radians(ph+i*360/cnt); cx,cy=rc_*math.cos(th),rc_*math.sin(th); shells.append(ring(rect_c(cx,cy,th,hr+1.35,ht+1.35),rect_c(cx,cy,th,hr+0.15,ht+0.15),30.4,33.4)); n_p+=1
    area+=cnt*(2*hr)*(2*ht)
emit("LOTUS_HOOD_CARRIER",shells,"ring r52.6-114.5, z29.4-33.4 (floor 1.0, pocket walls 1.2, tile height 2.5 + 0.4 spare); 36 pockets in 3 staggered rings (A r71, B r92, C r106.5, ring phases 0 / 17.5 / 5.0 deg from the golden angle); sits on L1 (relief top 29.1), bonded with silicone")
for nm,hr,ht in (("A",8,14),("B",8,19),("C",6.5,25)): emit(f"FERRITE_TILE_{nm}_reference",[extrude(np.array([(-ht,-hr),(ht,-hr),(ht,hr),(-ht,hr)]),0.0,2.5)],f"MnZn tile {2*ht} x {2*hr} x 2.5 (order cut, 12 per ring)")
rep["hood_numbers"]=dict(tiles=36,tile_area_mm2=round(area),annulus_area_mm2=round(math.pi*(114**2-52.6**2)),coverage_pct=round(100*area/(math.pi*(114**2-52.6**2)),1),mass_g_full=round(area*2.5*4.8e-3),mass_g_rings_B_C_only=round((area-12*2*8*2*14)*2.5*4.8e-3),gain_note="earlier boundary-element study: full ideal hood +14/+7.5/+4% at 100/200/300 mm; partial coverage scales roughly with coverage (estimate, not computed)")
# ---------------- 3. RX CASSETTE BASE PLATE v2: index key, strap notch, 3 screw windows
SR=28.0; hs=[math.radians(a) for a in (22.5,157.5,247.5)]; hw=1.7/SR; shl=[]
for i in range(3):
    a0=hs[i]+hw; a1=hs[(i+1)%3]-hw; a1=a1+2*np.pi if a1<a0 else a1; shl.append(sector(5.0,116.5,a0,a1,0.0,0.8))
for a in hs: shl+=[sector(5.0,SR-1.7,a-hw-0.001,a+hw+0.001,0.0,0.8),sector(SR+1.7,116.5,a-hw-0.001,a+hw+0.001,0.0,0.8)]
dl=math.radians(1.6); shl.append(sector(114.5,116.5,math.pi+dl,3*math.pi-dl,0.0,3.2)); shl.append(sector(114.5,116.5,math.pi-dl,math.pi+dl+0.001,0.0,1.2))     # rim with a strap notch (3.6 wide, from z1.2) at 180 deg
shl.append(sector(113.3,114.6,-math.radians(2.0),math.radians(2.0),0.8,3.2))                                                                              # index key for the board at 0 deg
emit("BASE_PLATE_RX_CASSETTE_v3",shl,"floor 0.8 + PCB recess D229 x 2.4; 3 screw windows 3.4 at r28 (22.5/157.5/247.5), matching the hub bosses and the SB1R-Q board holes; index key 1.3 x 4.0 at 0 deg (SB1R notch 4.2 x 1.5 at 0 deg); 3.6 wide ground-strap notch in the rim at 180 deg above z1.2 for the shield drain")
json.dump(rep,open(f"{OUT}/report.json","w"),indent=1); print(json.dumps({k:(v.get("nonmanifold_edges"),v.get("tris"),v.get("bbox")) for k,v in rep.items() if "tris" in v})); print(rep["hood_numbers"])
