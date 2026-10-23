import numpy as np, math, json
src=open('sim_head1.py').read().split("# ======================= S3")[0]; ns={}; exec(src,ns)
Bvec_many=ns["Bvec_many"]; TXB=ns["TXB"]
ts=np.linspace(0,2*np.pi,60,endpoint=False)
def ring(r,cx,cy,sgn,z=2.0e-3):
    x=r*np.cos(ts)+cx; y=r*np.sin(ts)+cy; l=np.c_[np.append(x,x[0]),np.append(y,y[0]),np.full(61,z)]*1e-3; return l if sgn>0 else l[::-1]
quadA=[ring(r,cx,cy,sg) for (cx,cy,sg) in ((50,50,1),(-50,50,-1),(-50,-50,1),(50,-50,-1)) for r in np.linspace(15,45,6)]
def rot(loops,deg):
    c,s=math.cos(math.radians(deg)),math.sin(math.radians(deg)); return [np.c_[l[:,0]*c-l[:,1]*s,l[:,0]*s+l[:,1]*c,l[:,2]] for l in loops]
quadB=rot(quadA,45.0)
x8=[ring(r,55,0,1) for r in np.linspace(20,52,12)]+[ring(r,-55,0,-1) for r in np.linspace(20,52,12)]
out={}
for depth,rho in ((0.10,0.06),(0.10,0.10),(0.20,0.08)):
    phis=np.radians(np.arange(0,360,15)); pts=np.c_[rho*np.cos(phis),rho*np.sin(phis),np.full(len(phis),-depth)]
    Bt=TXB(pts); A=np.einsum('ij,ij->i',Bt,Bvec_many(quadA,pts)); B=np.einsum('ij,ij->i',Bt,Bvec_many(quadB,pts)); X=np.einsum('ij,ij->i',Bt,Bvec_many(x8,pts))
    est=(0.5*np.degrees(np.arctan2(B,A)))%180; true=np.degrees(phis)%180; err=((est-true+90)%180)-90
    amp=np.hypot(A,B)
    out[f"depth {int(depth*1000)} mm, radius {int(rho*1000)} mm"]=dict(bearing_error_deg_rms_mod180=round(float(np.sqrt(np.mean(err**2))),1),bearing_error_max=round(float(np.max(np.abs(err))),1),amp_ratio_max_min=round(float(amp.max()/max(amp.min(),1e-30)),2),quadpair_rss_vs_X8_peak=round(float(amp.max()/np.max(np.abs(X))),2),A_over_B_pattern=[round(float(a),3) for a in (A/np.max(amp))[:6]])
for k,v in out.items(): print(k,v)
json.dump(out,open("kit_v21/sim_quadbearing.json","w"),indent=1)
