import struct, pickle, json, math, numpy as np
from scipy.interpolate import LinearNDInterpolator
D="kit_v13/PRINT"; R=json.load(open(f"{D}/report.json")); GOLD=137.50776405; P=pickle.load(open(f"{D}/paths.pkl","rb")); out={}
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3).astype(float), n
def runs(mask):
    idx=np.where(mask)[0]
    if len(idx)==0: return []
    return [(s[0],s[-1]) for s in np.split(idx,np.where(np.diff(idx)>1)[0]+1)]
def profile(itp,c,dirv,offs):
    pts=c[None,:]+offs[:,None]*dirv[None,:]; return itp(pts[:,0],pts[:,1])
for k in (1,3):
    f=R[f"L{k}"]["features"]; NP,NR=f["nphi"],f["nr"]; V,n=load(f"{D}/FORMER_L{k}_petal_coil_former.stl"); nt=2*NP*(NR-1); uq=np.unique(np.round(V[:nt*3],4),axis=0); itp=LinearNDInterpolator(uq[:,:2],uq[:,2]); a,b,la,lb=P[k]; res=dict(depth=[],width=[],center=[]); offs=np.arange(-1.6,1.601,0.04)
    if k==3:
        for arm,step,lo in ((a,50,40),(b,50,40)):
            for i in range(lo,len(arm)-lo,step):
                t=arm[min(i+2,len(arm)-1)]-arm[i-2]; t/=np.linalg.norm(t); nrm=np.array([-t[1],t[0]]); z=profile(itp,arm[i],nrm,offs)
                if np.isnan(z).any(): continue
                m_=np.abs(offs)>1.05; co=np.polyfit(offs[m_],z[m_],1); rs=z-np.polyval(co,offs); dep=-rs.min()
                if dep>1.8 or dep<0.8: continue
                bl=offs[rs<-dep/2]; res['depth'].append(dep); res['width'].append(bl.max()-bl.min()+0.04); res['center'].append(0.5*(bl.max()+bl.min()))
    r={kk:(round(float(np.mean(v)),3),round(float(np.std(v)),3),round(float(np.max(np.abs(v))),3)) for kk,v in res.items() if v}; r['samples']=len(res['depth'])
    LA=math.radians((GOLD*(k-1))%360+6); LB=LA+math.radians(5)
    def across(ang,rad,half):                                                  # tangential profile across a lead at radius rad
        c=np.array([rad*math.cos(ang),rad*math.sin(ang)]); tdir=np.array([-math.sin(ang),math.cos(ang)]); o=np.arange(-half,half+0.001,0.03); z=profile(itp,c,tdir,o); m_=np.abs(o)>half-0.5; co=np.polyfit(o[m_],z[m_],1); rs=z-np.polyval(co,o); dep=-np.nanmin(rs); bl=o[rs<-dep/2]; return round(float(dep),2),round(float(bl.max()-bl.min()+0.03),2),round(float(0.5*(bl.max()+bl.min())),2)
    r['anchor_pocket_A_depth_width_center@r56.75']=across(LA,56.75,2.6); r['anchor_pocket_B']=across(LB,56.75,2.6); r['lead_groove_A@r61']=across(LA,61.0,1.6); r['mouth_A@r50.5']=across(LA,50.5,2.0); r['mouth_A@r52.5']=across(LA,52.5,2.0)
    bot=V[nt*3:(nt+2*NP)*3]; rr=np.hypot(bot[:,0],bot[:,1]); mm=rr<57; ring=np.unique(np.round(bot[mm],4),axis=0); ph=np.arctan2(ring[:,1],ring[:,0]); o=np.argsort(ph); ph=ph[o]; rad=np.hypot(ring[o,0],ring[o,1])
    base=np.median(rad); r['bottom_ring_median_r']=round(float(base),2); r['chamfer_expected_r']=round((49.3 if k==1 else 49.9)+0.5,2)
    allv=V; ri=np.hypot(allv[:,0],allv[:,1]); mid=allv[(ri<(52 if k==1 else 50.3))&(allv[:,2]>-1)]; 
    notch=runs(rad>base+1.0); r['n_radial_features_at_bore']=len(notch); r['notch_far_radii']=sorted({round(float(rad[s:e+1].max()),1) for s,e in notch})
    if k>1:
        tooth=runs(rad<base-1.0)
        if tooth: s0,s1=tooth[0]; r['tooth_width']=round(float((ph[s1]-ph[s0])*base),2)
    r['L1_lug_notches_expected_deg']=R['spec']['L1_bond_key_notches_deg'] if k==1 else None
    out[f"L{k}"]=r; print(f"L{k}",r)
json.dump(out,open("kit_v13/audit_v13.json","w"),indent=1)
