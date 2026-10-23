import numpy as np, math, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import rodin_core_v3 as m
c=m.Core(); V,Fc,vol,meta=m.build_mesh(c,m.RES["HIGH"])
def render(V,Fc,R,W,H,scale,center,fname,title,sel=None):
    P=(V-center)@R.T
    T=P[Fc] if sel is None else P[Fc[sel]]
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); n/=np.linalg.norm(n,axis=1)[:,None]
    keep=n[:,2]>0; T=T[keep]; n=n[keep]
    L=np.array([-0.35,0.45,0.82]);L/=np.linalg.norm(L)
    shade=0.18+0.82*np.clip(n@L,0,1)
    X=T[...,0]*scale+W/2; Y=H/2-T[...,1]*scale; Z=T[...,2]
    zb=np.full((H,W),-1e9); img=np.ones((H,W))
    x0=np.clip(np.floor(X.min(1)).astype(int),0,W-1); x1=np.clip(np.ceil(X.max(1)).astype(int),0,W-1)
    y0=np.clip(np.floor(Y.min(1)).astype(int),0,H-1); y1=np.clip(np.ceil(Y.max(1)).astype(int),0,H-1)
    for i in range(len(T)):
        if x1[i]<x0[i] or y1[i]<y0[i]: continue
        xs=np.arange(x0[i],x1[i]+1)+.5; ys=np.arange(y0[i],y1[i]+1)+.5
        gx,gy=np.meshgrid(xs,ys)
        (ax,bx,cx),(ay,by,cy)=X[i],Y[i]
        d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(d)<1e-12: continue
        l1=((by-cy)*(gx-cx)+(cx-bx)*(gy-cy))/d; l2=((cy-ay)*(gx-cx)+(ax-cx)*(gy-cy))/d; l3=1-l1-l2
        ins=(l1>=-1e-6)&(l2>=-1e-6)&(l3>=-1e-6)
        if not ins.any(): continue
        zz=l1*Z[i,0]+l2*Z[i,1]+l3*Z[i,2]
        sub=zb[y0[i]:y1[i]+1,x0[i]:x1[i]+1]; im=img[y0[i]:y1[i]+1,x0[i]:x1[i]+1]
        upd=ins&(zz>sub); sub[upd]=zz[upd]; im[upd]=shade[i]
    fig=plt.figure(figsize=(W/150,H/150),dpi=150); plt.imshow(img,cmap="gray",vmin=0,vmax=1); plt.axis("off"); plt.title(title,fontsize=9)
    plt.tight_layout(); plt.savefig(fname,dpi=150); plt.close()
def rot(elev,azim):
    a=math.radians(azim); e=math.radians(elev)
    Rz=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
    Rx=np.array([[1,0,0],[0,math.cos(e),-math.sin(e)],[0,math.sin(e),math.cos(e)]])
    return Rx@Rz
cen=V[Fc].mean(1); ang=np.degrees(np.arctan2(cen[:,1],cen[:,0]))
sel=(np.abs(ang-90)<16)
# close-up: view the bottom face (looking up), sector at +90 deg
render(V,Fc,rot(-125,0),1500,1000,15,np.array([0,88,-6]),"out/preview_closeup_bottom.png","Bottom face close-up: TX saddle ridges (A,B pairs) + RX grooves, on/off ramps",sel)
render(V,Fc,rot(-55,0),1500,1000,15,np.array([0,88,4]),"out/preview_closeup_top.png","Top face close-up: TX (1.50 wide) and RX (0.90 wide) U-seat grooves",sel)
print("done")
