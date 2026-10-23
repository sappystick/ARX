import struct, pickle, json, math, numpy as np
from scipy.interpolate import LinearNDInterpolator
D="kit_v11/PRINT"; NR=330; GOLD=137.50776405
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]
    return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3).astype(float), n
P=pickle.load(open(f"{D}/paths.pkl","rb")); out={}
def runs(mask):
    idx=np.where(mask)[0]; 
    if len(idx)==0: return []
    sp=np.split(idx,np.where(np.diff(idx)>1)[0]+1); return [(s[0],s[-1]) for s in sp]
for k in (2,4,6):
    V,n=load(f"{D}/FORMER_L{k}_petal_coil_former.stl"); NP=n//(2*(NR+2)); nt=2*NP*(NR-1); top=V[:nt*3]; uq=np.unique(np.round(top,4),axis=0); itp=LinearNDInterpolator(uq[:,:2],uq[:,2])
    a,b,la,lb=P[k]; res=dict(depth=[],width=[],center=[]); offs=np.arange(-1.6,1.601,0.04)
    for arm,step,lo in ((a,50,40),(b,50,40),(la,3,2),(lb,3,2)):
        for i in range(lo,len(arm)-lo,step):
            t=arm[min(i+2,len(arm)-1)]-arm[i-2]; t/=np.linalg.norm(t); nrm=np.array([-t[1],t[0]]); pts=arm[i][None,:]+offs[:,None]*nrm[None,:]; z=itp(pts[:,0],pts[:,1])
            if np.isnan(z).any(): continue
            m_=np.abs(offs)>1.05; co=np.polyfit(offs[m_],z[m_],1); rs=z-np.polyval(co,offs); dep=-rs.min()
            if dep>1.8 or dep<0.8: continue
            below=offs[rs<-dep/2]; res['depth'].append(dep); res['width'].append(below.max()-below.min()+0.04); res['center'].append(0.5*(below.max()+below.min()))
    r={k2:(round(float(np.mean(v)),3),round(float(np.std(v)),3),round(float(np.max(np.abs(v))),3)) for k2,v in res.items()}; r['samples']=len(res['depth'])
    # bore, tooth and pin notches from the bottom inner ring
    bot=V[nt*3:(nt+2*NP)*3]; rr=np.hypot(bot[:,0],bot[:,1]); m=rr<54; ring=np.unique(np.round(bot[m],4),axis=0); ph=np.arctan2(ring[:,1],ring[:,0]); o=np.argsort(ph); ph=ph[o]; rad=np.hypot(ring[o,0],ring[o,1])
    base_r=np.median(rad); tooth=runs(rad<base_r-1.0); notch=runs(rad>base_r+1.0)
    r['bore_r']=round(float(base_r),3); 
    if k>1 and tooth: s0,s1=tooth[0]; r['tooth_width_mm']=round(float((ph[s1]-ph[s0])*base_r),2); r['tooth_height_mm']=round(float(base_r-rad[s0:s1+1].min()),2); r['tooth_center_deg']=round(math.degrees(0.5*(ph[s0]+ph[s1]))%360,2)
    r['n_pin_notches']=len(notch); r['notch_depth_mm']=round(float(rad.max()-base_r),2) if notch else 0
    r['expected_track_deg']=round((GOLD*(k-1))%360,2); r['outer_r_max']=round(float(np.hypot(V[:,0],V[:,1]).max()),2); r['z_range']=[round(float(V[:,2].min()),2),round(float(V[:,2].max()),2)]
    out[f"FORMER_L{k}"]=r; print(f"L{k}",r)
H,_=load(f"{D}/CORE_PCB_CYLINDER_central_former.stl"); sel=H[(np.abs(H[:,2]-6.0)<0.01)]; rr=np.hypot(sel[:,0],sel[:,1]); sel=sel[rr>46.0]; ph=np.arctan2(sel[:,1],sel[:,0]); o=np.argsort(ph); ph=ph[o]; rad=np.hypot(sel[o,0],sel[o,1])
ph,u_=np.unique(np.round(ph,7),return_index=True); rad=rad[u_]; nt_=runs(rad<49.45); hub=[]
for s0,s1 in nt_:
    w=(ph[s1]-ph[s0])*49.5; hub.append(dict(center_deg=round(math.degrees(0.5*(ph[s0]+ph[s1]))%360,2),width_mm=round(float(w),2),depth_mm=round(float(49.5-rad[s0:s1+1].min()),2)))
hub.sort(key=lambda d:d['center_deg']); out['hub_notches']=hub; out['hub_outer_r']=round(float(np.median(rad[rad>49.4])),3); print("hub notches",len(hub)); [print(h) for h in hub]
json.dump(out,open("kit_v11/audit_groove_detrended.json","w"),indent=1)
