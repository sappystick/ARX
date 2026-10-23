#!/usr/bin/env python3
"""Fine (0.2 mm) interference test of the CB1D and LB1 component bodies against the cylinder in the vault zone."""
import struct, numpy as np, csv, json, math
H=0.2; X0=Y0=-48.0; Z0=26.0; nx=ny=int(96/H); nz=int(16/H)
def load(p):
    b=open(p,"rb").read(); n=struct.unpack("<I",b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]),count=n,offset=84)["v"].reshape(-1,3,3).astype(float)
T=load("kit_v22/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl"); lo=T.min(1); hi=T.max(1); T=T[(hi[:,0]>=X0)&(lo[:,0]<=-X0)&(hi[:,1]>=Y0)&(lo[:,1]<=-Y0)]
ci=[];cz=[]
for t in T:
    a,b,c=t; ar=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1])
    if abs(ar)<1e-12: continue
    i0=max(0,int(np.floor((min(a[0],b[0],c[0])-X0)/H))); i1=min(nx-1,int(np.ceil((max(a[0],b[0],c[0])-X0)/H))); j0=max(0,int(np.floor((min(a[1],b[1],c[1])-Y0)/H))); j1=min(ny-1,int(np.ceil((max(a[1],b[1],c[1])-Y0)/H)))
    if i1<i0 or j1<j0: continue
    gx,gy=np.meshgrid(X0+(np.arange(i0,i1+1)+0.5)*H+0.0173,Y0+(np.arange(j0,j1+1)+0.5)*H+0.0127,indexing="ij")
    w0=((b[0]-gx)*(c[1]-gy)-(c[0]-gx)*(b[1]-gy))/ar; w1=((c[0]-gx)*(a[1]-gy)-(a[0]-gx)*(c[1]-gy))/ar; w2=1-w0-w1; m=(w0>=0)&(w1>=0)&(w2>=0)
    if not m.any(): continue
    z=w0*a[2]+w1*b[2]+w2*c[2]; ii,jj=np.nonzero(m); ci.append((ii+i0)*ny+(jj+j0)); cz.append(z[ii,jj])
ci=np.concatenate(ci); cz=np.concatenate(cz); o=np.lexsort((cz,ci)); ci=ci[o]; cz=cz[o]; st=np.r_[0,np.nonzero(np.diff(ci))[0]+1]; cnt=np.diff(np.r_[st,len(ci)]); rk=np.arange(len(ci))-np.repeat(st,cnt)
hi_=np.nonzero(rk%2==1)[0]; lo_=hi_-1; ok=ci[lo_]==ci[hi_]; lo_=lo_[ok]; hi_=hi_[ok]
za=np.ceil((cz[lo_]-Z0)/H-0.5).astype(int); zb=np.floor((cz[hi_]-Z0)/H-0.5).astype(int); k=zb>=za; za=np.clip(za[k],0,nz-1); zb=np.clip(zb[k],0,nz-1); cc=ci[lo_][k]
D=np.zeros((nx*ny,nz+1),np.int32); np.add.at(D,(cc,za),1); np.add.at(D,(cc,zb+1),-1); HUB=(np.cumsum(D[:,:nz],axis=1)>0).reshape(nx,ny,nz)
LIB=json.load(open("kit_v19/lib_bodies.json")); xs=X0+(np.arange(nx)+0.5)*H; ys=Y0+(np.arange(ny)+0.5)*H; zs=Z0+(np.arange(nz)+0.5)*H; out=[]
for board,zb_,th,flip in (("CB1D",27.0,1.6,True),("LB1",39.2,0.8,False)):
    typ={}
    for r in list(csv.reader(open(f"kit_v18/{board}/PF233-{board}_BOM.csv")))[1:]:
        for ref in r[1].split(","): typ[ref.strip()]=r[2]
    tot=0; bad=[]
    NW=7.6; m=((xs[:,None]**2+ys[None,:]**2)<=39.0**2)&~((np.abs(xs)[:,None]<NW)&(ys[None,:]>36.5)); zm=(zs>=zb_)&(zs<=zb_+th); disc=m[:,:,None]&zm[None,None,:]; ov=(disc&HUB).sum()*H**3; out.append((board+" board disc",round(float(ov),2)))
    for r in csv.DictReader(open(f"kit_v18/{board}/PF233-{board}_pickplace.csv")):
        t=typ.get(r["Ref"])
        if t is None or t not in LIB: continue
        bw,bh,bz=LIB[t]; x,y,rot=float(r["PosX_mm"]),float(r["PosY_mm"]),float(r["Rot"])
        if int(rot)%180==90: bw,bh=bh,bw
        if flip: x,y=-x,-y
        bx=((xs>=x-bw/2)&(xs<=x+bw/2))[:,None,None]&((ys>=y-bh/2)&(ys<=y+bh/2))[None,:,None]&((zs>=zb_+th)&(zs<=zb_+th+bz))[None,None,:]; v=(bx&HUB).sum()*H**3
        if v>0.05: bad.append((r["Ref"],t,round(float(v),2)))
    out.append((board+" component bodies intersecting the cylinder (0.2 mm voxels)",bad))
for o in out: print(o)
json.dump(out,open("kit_v22/fine_check.json","w"),default=str)
