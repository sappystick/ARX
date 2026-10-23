import pickle, math, json, numpy as np, time
from scipy.integrate import quad
mu0=4e-7*math.pi; MU=2000.0; TH=2.5; ZC=30.4+TH/2
P=pickle.load(open('kit_v15/LOW/paths.pkl','rb')); PN,G,ZRX=3.6,0.8,3.2
TX=[np.c_[np.vstack([P[k][0],P[k][1]])[::4],np.full(len(np.vstack([P[k][0],P[k][1]])[::4]),ZRX+(6-k)*(PN+G)+PN-0.7)]*1e-3 for k in range(1,7)]
def Bcoil(pt):
    b=np.zeros(3)
    for p in TX:
        d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2; r=pt-m; rn=np.sqrt((r**2).sum(1)+1e-9)[:,None]; b+=mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0)
    return b/6.0
def Bcoil_many(pts):
    out=np.zeros_like(pts)
    for p in TX:
        d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2
        for i,pt in enumerate(pts):
            r=pt-m; rn=np.sqrt((r**2).sum(1)+1e-9)[:,None]; out[i]+=mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0)
    return out/6.0
_demag={}
def demag(a,b,c):
    key=(round(a,2),round(b,2),round(c,2))
    if key in _demag: return _demag[key]
    def N(ai):
        f=lambda s: 1.0/((s+ai**2)*math.sqrt((s+a*a)*(s+b*b)*(s+c*c)))
        return a*b*c/2*quad(f,0,np.inf)[0]
    r=(N(a),N(b),N(c)); _demag[key]=r; return r
def rect(cx,cy,ang,hl,hw):
    c,s=math.cos(ang),math.sin(ang); return np.array([(cx+x*c-y*s,cy+x*s+y*c) for x,y in ((-hl,-hw),(hl,-hw),(hl,hw),(-hl,hw))])
def sat_gap(A,B):
    best=-1e9
    for Q in (A,B):
        for i in range(4):
            e=Q[(i+1)%4]-Q[i]; n=np.array([-e[1],e[0]])/np.linalg.norm(e); a=A@n; b=B@n; best=max(best,max(b.min()-a.max(),a.min()-b.max()))
    return best
# tile = (cx,cy,ang,L,W): L along the radial/long axis (local x), W across
def tiles_gap(T): 
    mn=1e9
    for i in range(len(T)):
        for j in range(i+1,len(T)):
            if math.hypot(T[i][0]-T[j][0],T[i][1]-T[j][1])>80: continue
            mn=min(mn,sat_gap(rect(T[i][0],T[i][1],T[i][2],T[i][3]/2,T[i][4]/2),rect(T[j][0],T[j][1],T[j][2],T[j][3]/2,T[j][4]/2)))
    return mn
def corner_r(T): return max(np.hypot(*c) for t in T for c in rect(t[0],t[1],t[2],t[3]/2,t[4]/2))
def inner_r(T): return min(np.hypot(*c) for t in T for c in rect(t[0],t[1],t[2],t[3]/2,t[4]/2))
def spokes(N,segs,gap=1.7,phase=0.0):
    T=[]
    for (r0,r1) in segs:
        L=r1-r0; lo,hi=4.0,200.0
        for _ in range(40):
            w=(lo+hi)/2; ok=True
            for k in range(2):
                A=rect((r0+r1)/2,0,0,L/2,w/2); th=2*math.pi/N; c,s=math.cos(th),math.sin(th); B=rect(((r0+r1)/2)*c,((r0+r1)/2)*s,th,L/2,w/2)
                if sat_gap(A,B)<gap: ok=False
            if ok: lo=w
            else: hi=w
        w=lo
        for i in range(N):
            th=phase+2*math.pi*i/N; T.append((((r0+r1)/2)*math.cos(th),((r0+r1)/2)*math.sin(th),th,L,w))
    return T
def vogel(N,L,W,rmin,rmax,gap=1.7):
    T=[]; c=rmax/math.sqrt(N)
    for n in range(1,N+1):
        r=c*math.sqrt(n); th=n*math.radians(137.50776405)
        if r<rmin: continue
        t=(r*math.cos(th),r*math.sin(th),th,L,W)
        if all(sat_gap(rect(t[0],t[1],t[2],L/2,W/2),rect(u[0],u[1],u[2],u[3]/2,u[4]/2))>=gap for u in T) and corner_r([t])<=rmax+8: T.append(t)
    return T
def cells(T,dx=8.0):
    C=[]
    for (cx,cy,ang,L,W) in T:
        nL=max(1,int(round(L/dx))); nW=max(1,int(round(W/dx))); dL=L/nL; dW=W/nW; c,s=math.cos(ang),math.sin(ang)
        for i in range(nL):
            for j in range(nW):
                x=-L/2+(i+0.5)*dL; y=-W/2+(j+0.5)*dW; C.append((cx+x*c-y*s,cy+x*s+y*c,ang,dL,dW))
    return C
def solve(T,targets=(100,200,300)):
    C=cells(T); n=len(C); pos=np.array([[x*1e-3,y*1e-3,ZC*1e-3] for x,y,_,_,_ in C]); V=np.array([d*w*TH*1e-9 for *_,d,w in C])
    H0=Bcoil_many(pos)/mu0
    # per-cell demag tensor in the global frame
    Nt=np.zeros((n,3,3))
    for i,(x,y,ang,dL,dW) in enumerate(C):
        nl,nw,nz=demag(dL/2,dW/2,TH/2); c,s=math.cos(ang),math.sin(ang); R=np.array([[c,-s,0],[s,c,0],[0,0,1]]); Nt[i]=R@np.diag([nl,nw,nz])@R.T
    r=pos[:,None,:]-pos[None,:,:]; d=np.linalg.norm(r,axis=2)+np.eye(n); rh=r/d[:,:,None]
    Gm=(3*rh[:,:,:,None]*rh[:,:,None,:]-np.eye(3)[None,None])/(4*np.pi*d[:,:,None,None]**3)*V[None,:,None,None]      # H_i = sum_j Gm[i,j] M_j
    for i in range(n): Gm[i,i]=0
    chi=MU-1
    A=np.zeros((3*n,3*n)); 
    for i in range(n):
        A[3*i:3*i+3,3*i:3*i+3]+=np.eye(3)+chi*Nt[i]
    A-=chi*Gm.transpose(0,2,1,3).reshape(3*n,3*n)
    M=np.linalg.solve(A,chi*H0.reshape(-1)).reshape(n,3); m=M*V[:,None]
    out={}
    for dd in targets:
        pt=np.array([0,0,-dd*1e-3]); r=pt-pos; rn=np.linalg.norm(r,axis=1)[:,None]; rh=r/rn
        Bd=mu0/(4*np.pi)*np.sum((3*rh*np.sum(m*rh,axis=1,keepdims=True)-m)/rn**3,axis=0); Bc=Bcoil(pt)
        out[dd]=round(100*Bd[2]/Bc[2],2)
    area=sum(t[3]*t[4] for t in T); return out,len(T),round(area),round(area*TH*4.8e-3), n
GOLD=137.50776405
RI,RO=57.0,112.5
layouts={
 "v1 rings, tangential tiles (as built - OVERLAPPING)":[(rc*math.cos(math.radians(ph+i*30)),rc*math.sin(math.radians(ph+i*30)),math.radians(ph+i*30)+math.pi/2,2*ht,2*hr) for rc,hr,ht,ph in ((71,8,14,0),(92,8,19,(GOLD)%30),(106.5,6.5,25,(2*GOLD)%30)) for i in range(12)],
 "radial spokes N=12, 2 segments":spokes(12,[(RI,84.0),(86.0,RO-0.0)]),
 "radial spokes N=13 (Fibonacci), 2 segments":spokes(13,[(RI,84.0),(86.0,RO-0.0)]),
 "radial spokes N=21 (Fibonacci), 3 segments":spokes(21,[(RI,79.0),(80.8,96.0),(97.8,RO)]),
 "radial spokes N=8, 2 segments":spokes(8,[(RI,84.0),(86.0,RO)]),
 "sunflower (Vogel) radial tiles 34x16":vogel(60,34,16,RI+6,RO-3),
 "sunflower (Vogel) radial tiles 26x14":vogel(90,26,14,RI+6,RO-3),
}
res={}
for nm,T in layouts.items():
    t0=time.time()
    try:
        # keep inside radius limits
        cr=corner_r(T); ir=inner_r(T); gp=tiles_gap(T)
        g,nt,area,mass,nc=solve(T); res[nm]=dict(tiles=nt,area_mm2=area,mass_g=mass,gain_pct=g,gain_per_100g_at_200=round(g[200]/mass*100,2),min_tile_gap_mm=round(gp,2),outer_corner_r=round(cr,1),inner_r=round(ir,1),cells=nc,sec=round(time.time()-t0))
    except Exception as e: res[nm]=dict(error=str(e))
    print(nm,res[nm],flush=True)
json.dump(res,open("kit_v18/hood_layout_study.json","w"),indent=1)
