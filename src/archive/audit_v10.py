import struct, pickle, json, math, numpy as np
from scipy.interpolate import LinearNDInterpolator
D="kit_v10/PRINT"; NPHI,NR=1200,150
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]
    return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3).astype(float)
P=pickle.load(open(f"{D}/paths.pkl","rb")); out={}
for k in range(1,7):
    V=load(f"{D}/L{k}_petal_cassette.stl"); nt=2*NPHI*(NR-1); top=V[:nt*3]; uq=np.unique(np.round(top,4),axis=0); itp=LinearNDInterpolator(uq[:,:2],uq[:,2])
    a,b,la,lb=P[k]; res=dict(depth=[],width=[],center=[]); offs=np.arange(-1.6,1.601,0.05)
    for arm in (a,b):
        idx=np.arange(40,len(arm)-40,60)
        for i in idx:
            t=arm[min(i+3,len(arm)-1)]-arm[i-3]; t/=np.linalg.norm(t); n=np.array([-t[1],t[0]]); pts=arm[i][None,:]+offs[:,None]*n[None,:]; z=itp(pts[:,0],pts[:,1])
            if np.isnan(z).any(): continue
            land=np.median(np.r_[z[:6],z[-6:]]); dep=land-z.min()
            if dep>1.6 or dep<0.8: continue                                     # skip crossing pockets / mesh edges
            half=land-dep/2; below=offs[z<half]; res['depth'].append(dep); res['width'].append(below.max()-below.min()+0.05); res['center'].append(0.5*(below.max()+below.min()))
    r={k2:(round(float(np.mean(v)),3),round(float(np.std(v)),3),round(float(np.max(np.abs(v))),3)) for k2,v in res.items()}; r['samples']=len(res['depth']); out[f"L{k}"]=r; print(f"L{k}",r)
json.dump(out,open("kit_v10/groove_audit.json","w"),indent=1)
