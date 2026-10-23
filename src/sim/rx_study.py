import pickle, math, json, numpy as np
mu0=4e-7*math.pi; GOLD=137.50776405; PN,G,ZRX=3.6,0.8,3.2
P=pickle.load(open('kit_v15/LOW/paths.pkl','rb'))
def tx_layer(k,z_override=None,rot=0.0):
    a,b,la,lb=P[min(max(k,1),6)]; xy=np.vstack([a,b])[::4]
    if rot: c,s=math.cos(rot),math.sin(rot); xy=xy@np.array([[c,s],[-s,c]])
    z=(ZRX+(6-k)*(PN+G)+PN-0.7) if z_override is None else z_override; return np.c_[xy,np.full(len(xy),z)]*1e-3
TX={k:tx_layer(k) for k in range(1,7)}
def Bz_at(path,pt):
    d=np.diff(path,axis=0); m=(path[:-1]+path[1:])/2; r=pt-m; rn=np.linalg.norm(r,axis=1)[:,None]; return (mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0))[2]
# ---------------- TX addition candidates (per-wire efficiency relative to the current six-layer stack)
dep=(0.1,0.2,0.3); W=lambda p:float(np.sum(np.linalg.norm(np.diff(p,axis=0),axis=1)))
base=[sum(Bz_at(TX[k],np.array([0,0,-d])) for k in TX)/sum(W(TX[k]) for k in TX) for d in dep]
cand={}
for j,name in ((1,"L0 on top of L1 (z+4.4)"),(2,"L-1 (z+8.8)"),(3,"L-2 (z+13.2)")):
    z=ZRX+5*(PN+G)+j*(PN+G)+PN-0.7; p=tx_layer(1,z_override=z,rot=math.radians(GOLD*(-j)))
    cand[name]=[round((Bz_at(p,np.array([0,0,-d]))/W(p))/base[i],3) for i,d in enumerate(dep)]
# rim sleeve: 10 turns (2 columns x 5 rows) at r=114.0/115.5 over z 3..27 (hypothetical, needs the footprint)
ts=np.linspace(0,2*np.pi,720,endpoint=False)
def ring(r,z): return np.c_[np.append(r*np.cos(ts),r*np.cos(ts[0])),np.append(r*np.sin(ts),r*np.sin(ts[0])),np.full(721,z)]*1e-3
sl=[ring(rr,z) for rr in (113.5,115.5) for z in (4.5,9,13.5,18,22.5)]
cand["rim sleeve r113.5-115.5, 10 turns, z4.5-22.5 (does NOT fit: petal tips reach R116.5)"]=[round((sum(Bz_at(p,np.array([0,0,-d])) for p in sl)/sum(W(p) for p in sl))/base[i],3) for i,d in enumerate(dep)]
hub=[ring(rr,z) for rr in (51,53) for z in (6,10,14,18,22)]
cand["hub/neck ring r51-53, 10 turns (inner, z6-22)"]=[round((sum(Bz_at(p,np.array([0,0,-d])) for p in hub)/sum(W(p) for p in hub))/base[i],3) for i,d in enumerate(dep)]
cand["ferrite hood above L1 (earlier BEM study, field gain at 100/200/300; +20% L, 184 g)"]=[1.14,1.075,1.04]
# ---------------- RX geometries
def arc(rho,a0,a1,n=120): t=np.linspace(a0,a1,n); return np.c_[rho*np.cos(t),rho*np.sin(t)]
def dloop(rho,side=+1):
    a=arc(rho,-np.pi/2,np.pi/2); xy=np.vstack([a,[[0,-rho]]]) ; xy[:,0]*=side
    return xy if side>0 else xy[::-1]*1.0
def mk(xy,z): return np.c_[np.vstack([xy,xy[:1]]),np.full(len(xy)+1,z)]*1e-3
def rotz(p,ang): c,s=math.cos(ang),math.sin(ang); q=p.copy(); q[:,0]=p[:,0]*c-p[:,1]*s; q[:,1]=p[:,0]*s+p[:,1]*c; return q
ZR=2.0
def fig8(r0,r1,N,ang=0.0,z=ZR):
    pts=[]
    for rho in np.linspace(r0,r1,N):
        pts.append(rotz(mk(dloop(rho,+1),z),ang)); pts.append(rotz(mk(dloop(rho,-1)[::-1][::-1],z)[::-1][::-1],ang))
    return pts
def fig8b(r0,r1,N,ang=0.0,z=ZR):                                                   # right lobe CCW, left lobe mirrored (CW): correct figure-8 pair in series
    out=[]
    for rho in np.linspace(r0,r1,N):
        R=mk(dloop(rho,+1),z); L=R.copy(); L[:,0]*=-1                      # mirror then reverse: shared divider keeps the same direction
        out+= [rotz(R,ang),rotz(L,ang)]
    return out
def quad(r0,r1,N,z=ZR):
    out=[]
    for rho in np.linspace(r0,r1,N):
        for q,sg in enumerate((+1,-1,+1,-1)):
            a0=q*np.pi/2; xy=np.vstack([[0,0],arc(rho,a0,a0+np.pi/2,60)]); p=mk(xy,z); out.append(p if sg>0 else p[::-1])
    return out
def mono(r0,r1,N,z=ZR): return [ring(r,z) for r in np.linspace(r0,r1,N)]
def hexnet(r0,r1,N): return {f"fig8 at {a} deg":fig8b(r0,r1,N,math.radians(a)) for a in (0,60,120)}
RX={"MONO full-aperture (18 loops r20-110)":mono(20,110,18),"X8 figure-8 D-lobes (18 loops r20-110)":fig8b(20,110,18),"Y8 figure-8 (rotated 90)":fig8b(20,110,18,math.pi/2),"Quadrupole + - + - (12 loops r20-110)":quad(20,110,12),
    "tip GX gradiometer D44 (24 loops r6-22)":fig8b(6,22,24),"tip GQ quadrupole D32 (16 loops r4-16)":quad(4,16,16),"fig8 at 60 deg (hex net, 18 loops)":fig8b(20,110,18,math.radians(60))}
def Mutual(A,B,stride=1):
    tot=0.0
    for a in A:
        da=np.diff(a,axis=0); ma=(a[:-1]+a[1:])/2
        for b in B:
            db=np.diff(b,axis=0); mb=(b[:-1]+b[1:])/2; r=np.linalg.norm(ma[:,None,:]-mb[None,:,:],axis=2); tot+=np.sum((da@db.T)/r)
    return 1e-7*tot
TXall=[TX[k][::2] for k in TX]
def lobes(rx,half):                                                                 # split a figure-8 list into its two lobes (even/odd)
    return rx[0::2],rx[1::2]
res={}
for name,rx in RX.items():
    rxs=[p[::3] for p in rx]
    if name.startswith("MONO") or name.startswith("Quad") or "quadrupole D32" in name:
        M_net=Mutual(rxs,TXall); M_ref=sum(abs(Mutual([p],TXall)) for p in rxs[:6]) if False else None
        if name.startswith("MONO"): M_lobe=abs(M_net); null=1.0
        else:
            parts=[Mutual(rxs[q::4],TXall) for q in range(4)]; M_lobe=sum(abs(x) for x in parts)/2; null=abs(M_net)/M_lobe
    else:
        MR=Mutual(rxs[0::2],TXall); ML=Mutual(rxs[1::2],TXall); M_net=MR+ML; M_lobe=0.5*(abs(MR)+abs(ML)); null=abs(M_net)/M_lobe
    res[name]=dict(M_net_nH=round(M_net*1e9,3),M_one_lobe_nH=round(M_lobe*1e9,2),TX_null_residual_pct=round(100*null,3),wire_m=round(sum(W(p) for p in rx),2))
# assembly tolerance: shift the X8 by 0.5 mm in x and y
for nm,key in (("X8 figure-8 D-lobes (18 loops r20-110)","X8"),):
    for dx,dy in ((0.5,0.0),(0.0,0.5)):
        sh=[]
        for p in RX[nm]: q=p.copy(); q[:,0]+=dx*1e-3; q[:,1]+=dy*1e-3; sh.append(q[::3])
        MR=Mutual(sh[0::2],TXall); ML=Mutual(sh[1::2],TXall); res[nm][f"residual_pct_if_shifted_{dx}x_{dy}y_mm"]=round(100*abs(MR+ML)/(0.5*(abs(MR)+abs(ML))),3)
# ---------------- target sensitivity profiles (reciprocity): S = Bz_RX(target) * Bz_TX(target); relative to MONO on-axis, per sqrt(wire length)
xs=np.arange(-140,141,10.0); prof={}
for d in (100,200):
    mono_ax=sum(Bz_at(p,np.array([0,0,-d*1e-3])) for p in RX["MONO full-aperture (18 loops r20-110)"])*sum(Bz_at(TX[k],np.array([0,0,-d*1e-3])) for k in TX)
    for name,rx in RX.items():
        sx=[];sy=[]
        for x in xs:
            for lst,axis in ((sx,0),(sy,1)):
                pt=np.array([x*1e-3,0,-d*1e-3]) if axis==0 else np.array([0,x*1e-3,-d*1e-3])
                lst.append(sum(Bz_at(p,pt) for p in rx)*sum(Bz_at(TX[k],pt) for k in TX)/mono_ax)
        prof[(d,name)]=(np.array(sx),np.array(sy))
json.dump(dict(TX_addition_candidates_per_wire_vs_current_stack_100_200_300=cand,RX=res),open("kit_v15/rx_study.json","w"),indent=1)
print(json.dumps(cand,indent=1)); print(json.dumps(res,indent=1))
pickle.dump((xs,prof),open("kit_v15/rx_profiles.pkl","wb"))
