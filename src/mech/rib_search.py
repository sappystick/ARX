import csv, json, math, numpy as np, itertools, os
LIB=json.load(open("kit_v19/lib_bodies.json"))
def boxes(board,bom,zb,thick,flip):
    typ={}
    for r in list(csv.reader(open(bom)))[1:]:
        for ref in r[1].split(","): typ[ref.strip()]=r[2]
    out=[]
    for r in csv.DictReader(open(f"kit_v18/{board}/PF233-{board}_pickplace.csv")):
        t=typ.get(r["Ref"])
        if t is None or t not in LIB: continue
        bw,bh,bz=LIB[t]; x,y,rot=float(r["PosX_mm"]),float(r["PosY_mm"]),float(r["Rot"])
        if int(rot)%180==90: bw,bh=bh,bw
        if flip: x,y=-x,-y
        out.append((r["Ref"],x-bw/2,x+bw/2,y-bh/2,y+bh/2,zb+thick,zb+thick+bz))
    return out
B=boxes("CB1D","kit_v18/CB1D/PF233-CB1D_BOM.csv",27.0,1.6,True)+boxes("LB1","kit_v18/LB1/PF233-LB1_BOM.csv",39.2,0.8,False)
def rot_poly(pts,a): c,s=math.cos(math.radians(a)),math.sin(math.radians(a)); return np.array([(x*c-y*s,x*s+y*c) for x,y in pts])
def sat(A,Bp):
    for P in (A,Bp):
        for k in range(len(P)):
            e=P[(k+1)%len(P)]-P[k]; n=np.array([-e[1],e[0]]); pa=A@n; pb=Bp@n
            if pa.max()<pb.min() or pb.max()<pa.min(): return False
    return True
def conflict(a):
    rib=rot_poly([(37.2,-3.2),(44.5,-3.2),(44.5,3.2),(37.2,3.2)],a); c=(42.5*math.cos(math.radians(a)),42.5*math.sin(math.radians(a))); bad=[]
    for ref,x0,x1,y0,y1,z0,z1 in B:
        R=np.array([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])
        if z1>28.9 and z0<35.0 and sat(R,rib): bad.append(ref)
        dx=max(x0-c[0],0,c[0]-x1); dy=max(y0-c[1],0,c[1]-y1)
        if z1>35.0 and z0<41.3 and math.hypot(dx,dy)<3.4: bad.append(ref)
    return bad
G=137.50776405; ports=[((G*(k-1))%360+o)%360 for k in range(1,7) for o in (6,11,16)]
def ang(a,b): return abs(((a-b)+180)%360-180)
free=[a for a in range(360) if not conflict(float(a))]
ok=[a for a in free if min(ang(a,p) for p in ports)>=8.0 and ang(a,178)>=14.0 and ang(a,90)>=16.0]
def runs(L):
    L=sorted(L); out=[]; s=p=L[0]
    for x in L[1:]:
        if x!=p+1: out.append((s,p)); s=x
        p=x
    out.append((s,p)); return out
print("no board conflict:",runs(free)); print("port/window/spine clear too:",runs(ok)); print("130 blocked by",conflict(130.0),"235 blocked by",conflict(235.0))
best=None
for n in (8,7,6):
    for t0 in np.arange(0,360/n,0.5):
        pick=[]; good=True
        for k in range(n):
            ideal=t0+360/n*k; c=[a for a in ok if ang(a,ideal)<=26]
            if not c: good=False; break
            pick.append(min(c,key=lambda x:ang(x,ideal)))
        if not good or len(set(pick))<n: continue
        pick=sorted(pick); g=[(pick[(i+1)%n]-pick[i])%360 for i in range(n)]
        if min(g)>=14 and max(g)<=125:
            sc=max(g)
            if best is None or sc<best[1]: best=(n,sc,pick)
    if best: break
print("BEST",best)
if best: json.dump(dict(ribs=[float(a) for a in best[2]]),open("kit_v22/rib_angles.json","w"))
