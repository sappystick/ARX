import math, json, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, solid_union as su
from render_v6 import tri2d
OUT="kit_v21"; GOLD=137.50776405; rep={}
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

def pieces_ring(r0,r1,z0,z1,gaps=None):
    if not gaps: return [ring(circ(r1,720),circ(r0,720),z0,z1)]
    g=sorted(gaps); out=[]
    for i in range(len(g)):
        a0=g[i][1]; a1=g[(i+1)%len(g)][0]+(2*np.pi if i==len(g)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
SP=math.radians(90.0); TXA=math.radians(178.0)
sh=[]
# floor (rests on the hub ledge at z9): disc, band with the 12 mm spine slot at 90 deg, outer flange r43.8
sh.append(extrude(circ(33.0,720),9.0,9.8)); sh+=pieces_ring(33.0,39.0,9.0,9.8,[(SP-6.0/36.0,SP+6.0/36.0)]); sh+=pieces_ring(39.0,43.8,9.0,9.8)
# wall r40.2-41.3 up to z40.2 with the 10 mm TX-lead slot at 178 deg (z27-30)
sh+=pieces_ring(40.2,41.3,9.8,27.0); sh+=pieces_ring(40.2,41.3,27.0,30.0,[(TXA-5.0/40.7,TXA+5.0/40.7)]); sh+=pieces_ring(40.2,41.3,30.0,40.2)
# 8 guide ribs (6 mm wide, protrude to r37.2) with card slots; slots cut r37.2-39.3 (board edge r39.0)
SLOTS=[(20.0,21.9,"septum"),(27.0,28.9,"CB1D")]; zs=[9.8]+[v for a,b,_ in SLOTS for v in (a,b)]+[39.2]
RIBS=[22.5+45*k for k in range(8)]
for a in RIBS:
    hw=3.0/38.7; a0=math.radians(a)-hw; a1=math.radians(a)+hw
    for k in range(0,len(zs),2): sh.append(sector(37.2,40.2,a0,a1,zs[k],zs[k+1]))
    for (z0,z1,_) in SLOTS: sh.append(sector(39.3,40.2,a0,a1,z0,z1))
# spine channel guide walls at 90 deg (12 mm clear channel, 1.2 thick walls, protrude to r37.2)
for sgn in (1,-1):
    a_in=SP+sgn*6.0/38.7; a_out=SP+sgn*7.2/38.7; sh.append(sector(37.2,40.2,min(a_in,a_out),max(a_in,a_out),9.8,39.2))
emit("VAULT_CAGE_concept",sh,"card-cage insert for the hub bore: floor + flange r43.8 on the ledge, wall r40.2-41.3 to z40.2, 8 guide ribs with slots (septum disc z20.0-21.9, CB1D z27.0-28.9, LB1 rests on the rib tops z39.2), 12 mm spine channel at 90 deg for the rigid-flex spine, 10 mm TX-lead slot at 178 deg")
import csv
json.dump(rep,open("kit_v21/cage_report.json","w"),indent=1,default=float); print({k:(v["nonmanifold_edges"],v["tris"],v["bbox"]) for k,v in rep.items()})
