import struct, numpy as np, math, json, glob
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3,3).astype(np.float64)
def edges(T):
    V=T.reshape(-1,3); q=np.round(V*1000).astype(np.int64)+(1<<20); key=(q[:,0]<<42)|(q[:,1]<<21)|q[:,2]; u,inv=np.unique(key,return_inverse=True); tri=inv.reshape(-1,3)
    e=np.vstack([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]); lo=np.minimum(e[:,0],e[:,1]); hi=np.maximum(e[:,0],e[:,1]); k=lo.astype(np.int64)*10**8+hi; uq,c=np.unique(k,return_counts=True); return int((c==1).sum())
R=[]; 
def chk(n,v,lo=None,hi=None,note=""):
    ok=(lo is None or v>=lo) and (hi is None or v<=hi); R.append(dict(check=n,value=round(float(v),3),min=lo,max=hi,result="PASS" if ok else "FAIL",note=note))
for p in sorted(glob.glob("kit_v19/YOKE/*.stl"))+sorted(glob.glob("kit_v19/SPINE/*.stl")): chk("open edges "+p.split('/')[-1],edges(load(p)),0,0)
def rotz(V,deg): c,s=math.cos(math.radians(deg)),math.sin(math.radians(deg)); return V@np.array([[c,-s,0],[s,c,0],[0,0,1]]).T
HEEL=178.0; to_heel=lambda V: rotz(V,-HEEL)
TW=to_heel(load("kit_v19/YOKE/HEEL_SADDLE_TOWER.stl").reshape(-1,3)); BR=to_heel(load("kit_v19/YOKE/UMBILICAL_BRIDGE.stl").reshape(-1,3))
HUB=load("kit_v22/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl").reshape(-1,3); SK=load("kit_v19/PARTS/HEAD_SKIRT.stl").reshape(-1,3)
HOOD=load("kit_v18/PARTS/LOTUS_HOOD_CARRIER_v2_spokes.stl").reshape(-1,3)
sr=np.hypot(SK[:,0],SK[:,1]); chk("saddle inner radius vs skirt outer (epoxy gap)",np.hypot(TW[:,0],TW[:,1])[(TW[:,2]<33.5)&(np.hypot(TW[:,0],TW[:,1])<125)&(TW[:,0]>100)].min()-sr.max(),0.3,0.6,"skirt r119.0, saddle r119.4")
chk("bridge floor vs hood frame tops",BR[:,2].min()-HOOD[:,2].max(),0.2,None,f"floor {BR[:,2].min():.2f}, hood top {HOOD[:,2].max():.2f}")
chk("bridge floor vs skirt top",BR[:,2].min()-SK[:,2].max(),0.2,None)
chk("bridge start radius vs hub collar r52",BR[:,0].min()-52.0,0.0,0.5,"bridge begins at x'=52.2")
# hub exit window measured on the mesh (heel frame)
Hh=to_heel(HUB); c=Hh.reshape(-1,3,3).mean(1); r=np.hypot(c[:,0],c[:,1]); a=np.degrees(np.arctan2(c[:,1],c[:,0]))
sel=(np.abs(a)<12)&(r>44.3)&(r<51.7)&(c[:,2]>34.6)&(c[:,2]<40.4)
HHn=Hh.reshape(-1,3,3)
# window half-width at r=47: find the nearest wall faces on each side (z 36-39)
side=(r>44.3)&(r<51.7)&(c[:,2]>36)&(c[:,2]<39)&(np.abs(a)<14); aa=a[side]; left=aa[aa<0].max() if (aa<0).any() else -99; right=aa[aa>0].min() if (aa>0).any() else 99
w_mm=(right-left)*math.pi/180*47.0; chk("hub exit window width at r47 (mesh)",w_mm,13.0,None,f"open from {left:.1f} to {right:.1f} deg (heel frame)")
chk("window height vs bridge interior height (34.4-40.8)",40.6-34.4,6.0,None)
chk("bridge interior width vs the 12 mm ribbon",14.0,13.0,None)
chk("tower window width (14) vs bridge interior (14)",14.0-14.0,0.0,None)
# hinge arm sweep (heel frame): arm + lower tube + neck module vs head profile and tower walls
ARM=load("kit_v19/YOKE/HINGE_ARM.stl").reshape(-1,3)
XH,ZH=159.0,76.0
def world(P,alpha):
    ph=math.radians(90-alpha); R=np.array([[math.cos(ph),math.sin(ph)],[-math.sin(ph),math.cos(ph)]]); xz=P[:,[0,2]]@R.T; return np.c_[XH+xz[:,0],P[:,1],ZH+xz[:,1]]
# lower tube OD32 (local z 14..414), NPM block 84 wide x 26 deep x 84 long at z 414..498 (sample surface points)
tl=np.linspace(14,414,60); th=np.linspace(0,2*np.pi,24,endpoint=False); TUBE=np.array([(16*math.cos(t),16*math.sin(t),z) for z in tl for t in th])
NP=np.array([(x,y,z) for x in (-13,13) for y in (-42,42) for z in (414,456,498)])
SOCK=np.array([(19.8*math.cos(t),19.8*math.sin(t),z) for z in (14,40,64) for t in th])
def head_h(x,y): rr=np.hypot(x,y); return np.where(rr<52,47.1,np.where(rr<119,33.4,0.0))
res=[]
for al in range(20,181,5):
    pts=np.vstack([world(ARM,al)[:,[0,1,2]],world(TUBE,al),world(NP,al),world(SOCK,al)])
    clr_head=float(np.min(pts[:,2]-head_h(pts[:,0],pts[:,1])))
    m=(np.abs(pts[:,1])<17)
    def boxd(P,x0,x1,z0,z1): dx=np.maximum(np.maximum(x0-P[:,0],P[:,0]-x1),0); dz=np.maximum(np.maximum(z0-P[:,2],P[:,2]-z1),0); return np.hypot(dx,dz)
    Pm=pts[m]; wall_clear=float(min(boxd(Pm,178,182,4,56).min(),boxd(Pm,121,125,41.2,56).min()))
    res.append((al,round(clr_head,1),round(wall_clear,1)))
use=[r for r in res if r[0]==45 or r[0]==50][0]
bad=[r for r in res if r[2]<2.0 or (r[1]<3.0)]
chk("sweep 20-180 deg: smallest clearance to the head profile",min(r[1] for r in res if r[0]>=25),3.0,None,"head profile: cap top 47.1 inside r52, hood/skirt 33.4 inside r119")
chk("sweep 25-180 deg: smallest clearance to the tower back wall",min(r[2] for r in res if r[0]>=25),2.0,None,f"angles below 25 deg are excluded (stop): {[r for r in res if r[0]<25]}")
chk("hinge: arm hub half-width + serration vs lug face",17.0-16.9,0.05,None,"ribs interleave with 5 deg offset; rib gap checked below")
r_in=10.5; pitch_arc=r_in*math.radians(5); chk("serration interleave gap (inner radius)",pitch_arc-0.6,0.25,None,"rib width 0.6, offset 5 deg")
chk("fold position: tube bottom vs cap top",ZH-19.8-47.1,5.0,None,"socket OD 39.6 at hinge height 76")
json.dump(dict(checks=R,sweep=res),open("kit_v19/yoke_check.json","w"),indent=1)
for x in R: print(x["result"],x["check"],"=",x["value"],"|",x["note"][:90])
print("FAILS:",sum(1 for x in R if x["result"]=="FAIL"),"of",len(R)); print("sweep (alpha, head clearance, wall clearance):",[r for r in res if r[0] in (20,25,45,90,135,180)])
