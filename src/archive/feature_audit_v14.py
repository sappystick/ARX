import struct, json, math, sys, numpy as np
from scipy.interpolate import LinearNDInterpolator
D="kit_v14/PRINT"; R=json.load(open(f"{D}/report.json")); GOLD=137.50776405
R0,R1=62.0,109.6; M,A_RIP,MARGIN,R_RIM=12,2.4,4.5,116.5
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3).astype(np.float64)
def uniq(V):
    q=np.round(V*1000).astype(np.int64)+(1<<20); key=(q[:,0]<<42)|(q[:,1]<<21)|q[:,2]; u,i=np.unique(key,return_index=True); return V[i]
def runs(mask):
    idx=np.where(mask)[0]
    return [] if len(idx)==0 else [(s[0],s[-1]) for s in np.split(idx,np.where(np.diff(idx)>1)[0]+1)]
hub=json.load(open("kit_v13/SET/06_DATA/audit.json")) if False else None
for k in map(int,sys.argv[1:]):
    f=R[f"L{k}"]["features"]; NP,NR,NRb=f["nphi"],f["nr"],f["nrb"]; V=load(f"{D}/FORMER_L{k}_petal_coil_former.stl"); nt=2*NP*(NR-1)*3; nb=2*NP*(NRb-1)*3
    top=uniq(V[:nt]); bot=uniq(V[nt:nt+nb]); rr=np.hypot(top[:,0],top[:,1]); ph=np.arctan2(top[:,1],top[:,0]); al=math.radians((GOLD*(k-1))%360); out={}
    NB=7200; bi=((ph+np.pi)/(2*np.pi)*NB).astype(int)%NB; rmin=np.full(NB,np.inf); np.minimum.at(rmin,bi,rr); rmax=np.full(NB,0.0); np.maximum.at(rmax,bi,rr); cen=(np.arange(NB)+0.5)/NB*2*np.pi-np.pi
    ok=np.isfinite(rmin)&(rmax>0); base=np.median(rmin[ok]); out["bore_r"]=round(float(base),2)
    tooth=runs(ok&(rmin<base-1.0)); notch=runs(ok&(rmin>base+1.0))
    if k>1 and tooth:
        s0,s1=max(tooth,key=lambda t:t[1]-t[0]); out["key_tooth"]=dict(width_mm=round(float((cen[s1]-cen[s0])*base),2),height_mm=round(float(base-rmin[s0:s1+1].min()),2),angle_deg=round(math.degrees(0.5*(cen[s0]+cen[s1]))%360,2),expected_deg=round((GOLD*(k-1))%360,2))
    out["pin_or_bond_notches"]=dict(count=len(notch),angles_deg=[round(math.degrees(0.5*(cen[a]+cen[b]))%360,1) for a,b in notch])
    # rim ID notches: outer boundary dips relative to the smooth petal outline
    exp=np.minimum(R_RIM,R1+A_RIP*np.cos(M*(cen-al))+MARGIN); dip=ok&(rmax<exp-0.6); idn=runs(dip)
    out["rim_ID_notches"]=dict(count=len(idn),expected=k,angles_deg=[round(math.degrees(0.5*(cen[a]+cen[b]))%360,1) for a,b in idn],expected_deg=f["id_notch_deg"])
    # chamfer: bottom-surface minimum radius vs top minimum radius
    br=np.hypot(bot[:,0],bot[:,1]); out["chamfer_bottom_ring_minus_top_bore_mm"]=round(float(np.median(br[br<base+1.5]) if (br<base+1.5).any() else np.nan)-float(base),2)
    # pits
    top_xy=top[:,:2]; pit_ok=0; pit_depths=[]
    for name,pts in f["pits"].items():
        for p in pts:
            d=np.hypot(top[:,0]-p[0],top[:,1]-p[1]); inn=top[d<0.5,2]; ring_=top[(d>2.2)&(d<3.4),2]
            if len(inn)==0 or len(ring_)==0: continue
            dep=float(np.median(ring_)-inn.min()); pit_depths.append(dep); pit_ok+=dep>0.5
    out["marker_pits"]=dict(found=int(pit_ok),expected=k+6,mean_depth=round(float(np.mean(pit_depths)),2))
    # leads: profiles across lead A/B at r=61 (groove), r=56.75 (anchor), r=50.6 and 52.5 (mouth)
    LA=math.radians((GOLD*(k-1))%360+6); LB=LA+math.radians(5)
    def across(ang,rad,half):
        c=np.array([rad*math.cos(ang),rad*math.sin(ang)]); t=np.array([-math.sin(ang),math.cos(ang)]); sel=np.hypot(top[:,0]-c[0],top[:,1]-c[1])<half+4
        itp=LinearNDInterpolator(top[sel][:,:2],top[sel][:,2]); o=np.arange(-half,half+1e-6,0.03); pts=c[None,:]+o[:,None]*t[None,:]; z=itp(pts[:,0],pts[:,1]); m_=np.abs(o)>half-0.5; co=np.polyfit(o[m_],z[m_],1); rs=z-np.polyval(co,o); dep=-np.nanmin(rs); bl=o[rs<-dep/2]
        return dict(depth=round(float(dep),2),width=round(float(bl.max()-bl.min()+0.03),2),center_offset=round(float(0.5*(bl.max()+bl.min())),2))
    out["lead_A_groove_r61"]=across(LA,61.0,1.6); out["lead_B_groove_r61"]=across(LB,61.0,1.6); out["anchor_A_r56.75"]=across(LA,56.75,2.6); out["anchor_B_r56.75"]=across(LB,56.75,2.6); out["mouth_A_r50.6"]=across(LA,50.6,2.0); out["mouth_A_r52.5"]=across(LA,52.5,2.0)
    out["z_range_assembled"]=[round(float(V[:,2].min()),2),round(float(V[:,2].max()),2)]; out["underside_relief_mm"]=round(float(bot[:,2].max()-bot[:,2].min()),2)
    json.dump(out,open(f"kit_v14/features_L{k}.json","w"),indent=1); print(f"L{k}",json.dumps(out)[:700],flush=True)
