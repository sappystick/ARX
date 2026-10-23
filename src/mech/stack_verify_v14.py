import struct, json, math, sys, numpy as np
from scipy.spatial import cKDTree
from scipy.interpolate import LinearNDInterpolator
LOD=sys.argv[1] if len(sys.argv)>1 else "print"; D="kit_v14/PRINT" if LOD=="print" else "kit_v14/LOW"; R=json.load(open(f"{D}/report.json")); GOLD=137.50776405
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3,3).astype(float)
top,bot,meta={},{},{}
for k in range(1,7):
    T=load(f"{D}/FORMER_L{k}_petal_coil_former.stl"); f=R[f"L{k}"]["features"]; NP,NR,NRb=f["nphi"],f["nr"],f["nrb"]; nt=2*NP*(NR-1); nb=2*NP*(NRb-1)
    tv=np.unique(np.round(T[:nt].reshape(-1,3),4),axis=0); bv=np.unique(np.round(T[nt:nt+nb].reshape(-1,3),4),axis=0)
    top[k]=(cKDTree(tv[:,:2]),tv[:,2]); bot[k]=LinearNDInterpolator(bv[:,:2],bv[:,2]); meta[k]=(NP,NR,NRb)
rng=np.random.default_rng(1); N=60000; r=rng.uniform(55.0,108.0,N); th=rng.uniform(0,2*np.pi,N); pts=np.c_[r*np.cos(th),r*np.sin(th)]
res={}
for k in range(1,6):
    d,idx=top[k+1][0].query(pts,k=70); land=top[k+1][1][idx].max(1); b=bot[k](pts[:,0],pts[:,1]); ok=~np.isnan(b)&(d.max(1)<2.6); gap=(b-land)[ok]
    res[f"gap_L{k}_to_L{k+1}"]=dict(min=round(float(gap.min()),3),p1=round(float(np.percentile(gap,1)),3),mean=round(float(gap.mean()),3),max=round(float(gap.max()),3),samples=int(ok.sum()))
th_=[]
for k in range(1,7):
    d,idx=top[k][0].query(pts,k=70); land=top[k][1][idx].max(1); b=bot[k](pts[:,0],pts[:,1]); ok=~np.isnan(b)&(d.max(1)<2.6); t=(land-b)[ok]; th_.append((k,round(float(t.min()),3),round(float(t.mean()),3),round(float(t.max()),3)))
res["layer_thickness_min_mean_max"]=th_
pin=json.load(open("kit_v11/PRINT/report.json"))["pin_table"]; pe=[]
for p in pin:
    i=p["interface"]
    if i>=6: continue
    t=math.radians(p["theta_deg"]); xy=np.array([[51.7*math.cos(t),51.7*math.sin(t)]]); 
    # land of layer i+1 near the pin: use the ring just outside the notch (r 54.2) at the same angle
    q=np.array([[54.2*math.cos(t),54.2*math.sin(t)]]); d,idx=top[i+1][0].query(q,k=70); land=float(top[i+1][1][idx].max()); pe.append(round(p["z_shoulder"][0]-land,3))
res["pin_shoulder_vs_mesh_land_mm (design - mesh, should be ~0)"]=dict(min=min(pe),max=max(pe))
json.dump(res,open(f"kit_v14/stack_verification_{LOD}.json","w"),indent=1); print(json.dumps(res,indent=1))
