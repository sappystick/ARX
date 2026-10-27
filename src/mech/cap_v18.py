import math, json, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, solid_union as su
from render_v6 import tri2d
OUT="kit_v18/PARTS"; GOLD=137.50776405; rep={}
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
PX=[(12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,7.5)]; HR=0.85
def hole_ints(r,cnt,ph): return sorted([(math.radians(ph+i*360/cnt)-HR/r,math.radians(ph+i*360/cnt)+HR/r) for i in range(cnt)])
def band(r0,r1,forb,z0,z1):
    if not forb: return [ring(circ(r1,720),circ(r0,720),z0,z1)]
    forb=sorted(forb); out=[]
    for i in range(len(forb)):
        a0=forb[i][1]; a1=forb[(i+1)%len(forb)][0]+(2*np.pi if i==len(forb)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
cuts=[4.0,PX[0][0]-HR,PX[0][0]+HR,PX[1][0]-HR,PX[1][0]+HR,PX[2][0]-HR,PX[2][0]+HR,PX[3][0]-HR,PX[3][0]+HR,52.0]
sh=[]
for i in range(len(cuts)-1):
    ri=None
    if i in (1,3,5,7): ri=(i-1)//2
    sh+=band(cuts[i],cuts[i+1],hole_ints(*PX[ri]) if ri is not None else [],44.5,45.4)
sh.append(sector(45.2,52.0,math.radians(3),math.radians(357),45.4,47.1))
for a in (45,135,225,315):
    ar=math.radians(a); sh.append(extrude(rectp(ar,28.6,31.4,1.7),40.4,44.6)); sh.append(extrude(rectp(ar,31.3,32.4,1.7),40.4,41.2))
emit("HUB_CAP_HTA_v3_vault",sh,"v16 cap + 66 light-pipe holes D1.7 in the 0.9 floor (same polar grid as the roof); the HTA board needs the same 66 holes")
json.dump(rep,open(f"{OUT}/cap_report.json","w"),indent=1); print({k:(v['nonmanifold_edges'],v['tris']) for k,v in rep.items()})
