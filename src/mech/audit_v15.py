import struct, json, math, sys, numpy as np
from scipy.spatial import cKDTree
from scipy.interpolate import LinearNDInterpolator
D="kit_v15/PRINT"; R=json.load(open(f"{D}/report.json")); GOLD=137.50776405; R0,R1=62.0,109.6; M,A_RIP,MARGIN,R_RIM=12,2.4,4.5,116.5
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3).astype(np.float64)
def uniq(V):
    q=np.round(V*1000).astype(np.int64)+(1<<20); key=(q[:,0]<<42)|(q[:,1]<<21)|q[:,2]; u,i=np.unique(key,return_index=True); return V[i]
def runs_nodes(mask,ang,gap=1.2):
    idx=np.where(mask)[0]; out=[]
    if len(idx)==0: return out
    s=idx[0]; p=idx[0]
    for i in idx[1:]:
        if i!=p+1 or ang[i]-ang[p]>math.radians(gap): out.append((s,p)); s=i
        p=i
    out.append((s,p)); return out
audit={}; tops={}; offs={}
for k in range(1,7):
    f=R[f"L{k}"]["features"]; NP,NR,NRb=f["nphi"],f["nr"],f["nrb"]; V=load(f"{D}/FORMER_L{k}_petal_coil_former.stl"); nt=2*NP*(NR-1)*3; nb=2*NP*(NRb-1)*3
    top=uniq(V[:nt]); bot=uniq(V[nt:nt+nb]); off=R[f"L{k}"]["assembly_z_offset"]; tops[k]=(cKDTree(top[:,:2]),top[:,2]); offs[k]=off
    rr=np.hypot(top[:,0],top[:,1]); ph=np.arctan2(top[:,1],top[:,0]); o_=np.argsort(ph); ps=ph[o_]; brk=np.where(np.diff(ps)>3e-5)[0]+1; starts=np.r_[0,brk]; cid=np.zeros(len(ph),dtype=np.int64); cid[starts[1:]]=1; cid=np.cumsum(cid); inv=np.empty(len(ph),dtype=np.int64); inv[o_]=cid; u=np.add.reduceat(ps,starts)/np.diff(np.r_[starts,len(ps)])
    rmin=np.full(len(u),np.inf); rmax=np.zeros(len(u)); np.minimum.at(rmin,inv,rr); np.maximum.at(rmax,inv,rr)
    base=float(np.median(rmin)); out={}; out["bore_r"]=round(base,2); al=math.radians((GOLD*(k-1))%360)
    tooth=runs_nodes(rmin<base-1.0,u); notch=runs_nodes(rmin>base+1.0,u)
    if k>1 and tooth: s0,s1=max(tooth,key=lambda t:u[t[1]]-u[t[0]]); out["key_tooth"]=dict(width_mm=round(float((u[s1]-u[s0])*base),2),height_mm=round(float(base-rmin[s0:s1+1].min()),2),angle_deg=round(math.degrees(0.5*(u[s0]+u[s1]))%360,2),expected_deg=round((GOLD*(k-1))%360,2))
    out["bore_notches"]=dict(count=len(notch),expected=9 if k==1 else 6,angles_deg=[round(math.degrees(0.5*(u[a]+u[b]))%360,1) for a,b in notch],far_radius=sorted({round(float(rmin[a:b+1].max()),1) for a,b in notch}))
    exp=np.minimum(R_RIM,R1+A_RIP*np.cos(M*(u-al))+MARGIN); idn=runs_nodes(rmax<exp-0.6,u)
    out["rim_ID_notches"]=dict(count=len(idn),expected=k,angles_deg=[round(math.degrees(0.5*(u[a]+u[b]))%360,1) for a,b in idn],expected_deg=f["id_notch_deg"])
    out["outer_radius_max"]=round(float(rr.max()),2); out["bottom_flatness_mm"]=round(float(bot[:,2].max()-bot[:,2].min()),3); out["bottom_z_bed"]=round(float(bot[:,2].min()),3)
    pit_ok=0; dp=[]
    for name,pts in f["pits"].items():
        for p in pts:
            d=np.hypot(top[:,0]-p[0],top[:,1]-p[1]); inn=top[d<0.5,2]; ring_=top[(d>2.2)&(d<3.4),2]
            if len(inn) and len(ring_): dep=float(np.median(ring_)-inn.min()); dp.append(dep); pit_ok+=dep>0.5
    out["marker_pits"]=dict(found=int(pit_ok),expected=k+6,mean_depth=round(float(np.mean(dp)),2))
    LA=math.radians((GOLD*(k-1))%360+6); LB=LA+math.radians(5)
    def across(ang,rad,half):
        c=np.array([rad*math.cos(ang),rad*math.sin(ang)]); t=np.array([-math.sin(ang),math.cos(ang)]); sel=np.hypot(top[:,0]-c[0],top[:,1]-c[1])<half+4
        itp=LinearNDInterpolator(top[sel][:,:2],top[sel][:,2]); o=np.arange(-half,half+1e-6,0.03); pts=c[None,:]+o[:,None]*t[None,:]; z=itp(pts[:,0],pts[:,1]); m_=np.abs(o)>half-0.5; co=np.polyfit(o[m_],z[m_],1); rs=z-np.polyval(co,o); dep=-np.nanmin(rs); bl=o[rs<-dep/2]
        return dict(depth=round(float(dep),2),width=round(float(bl.max()-bl.min()+0.03),2),center_offset=round(float(0.5*(bl.max()+bl.min())),2))
    out["lead_A_r61"]=across(LA,61.0,1.6); out["anchor_A_r56.75"]=across(LA,56.75,2.6); out["anchor_B_r56.75"]=across(LB,56.75,2.6); out["mouth_A_r50.6"]=across(LA,50.6,2.0); out["mouth_A_r52.5"]=across(LA,52.5,2.0)
    land=np.sort(top[:,2])[-int(len(top)*0.05):]; out["land_height_above_bed_median"]=round(float(np.median(land)),2); out["thickness_nominal_3.6_plus_relief"]=round(float(np.percentile(top[:,2],99.5)),2)
    audit[f"L{k}"]=out; print(f"L{k}",json.dumps(out)[:600],flush=True)
# stack gaps from meshes
rng=np.random.default_rng(2); N=60000; r=rng.uniform(55,108,N); th=rng.uniform(0,2*np.pi,N); pts=np.c_[r*np.cos(th),r*np.sin(th)]; gaps={}
for k in range(1,6):
    d,idx=tops[k+1][0].query(pts,k=70); land=tops[k+1][1][idx].max(1)+offs[k+1]; ok=d.max(1)<2.6; g=(offs[k]-land)[ok]; gaps[f"L{k}_to_L{k+1}"]=dict(min=round(float(g.min()),3),p1=round(float(np.percentile(g,1)),3),mean=round(float(g.mean()),3),design_min=round(0.8-0.30*(108/116.5)**2,3))
audit["stack_gaps_mm"]=gaps; print(json.dumps(gaps))
json.dump(audit,open("kit_v15/audit_formers_v15.json","w"),indent=1)
