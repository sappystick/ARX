import math, json, pickle, numpy as np
import math, json, pickle, numpy as np
R_RIM,PN,ZRX,D_DOME=116.5,3.6,3.2,10.0; PV=PN; GOLD=137.50776405
dome=lambda r: D_DOME*(1-(r/R_RIM)**2); zb_k=lambda k,r: ZRX+(6-k)*PV+dome(r)
P=pickle.load(open("kit_v9/LOW/paths.pkl","rb")); mu0=4e-7*math.pi
p3={}
for k in range(1,7):
    a,b,la,lb=P[k]; xy=np.vstack([a,b]); r=np.hypot(xy[:,0],xy[:,1]); p3[k]=np.c_[xy,zb_k(k,r)+PN-1.3+0.6]*1e-3
def Bv(path,pt,dec=4):
    p=path[::dec]; d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2; rr=pt-m; rn=np.linalg.norm(rr,axis=1)[:,None]; return mu0/(4*np.pi)*np.sum(np.cross(d,rr)/rn**3,axis=0)
W={k:float(np.sum(np.linalg.norm(np.diff(p3[k],axis=0),axis=1))) for k in p3}; deps=(0.1,0.2,0.3)
Bk={k:[Bv(p3[k],np.array([0,0,-d])) for d in deps] for k in p3}
zf=lambda r:13+(116.5-r)*0.359; cur=[(74+i*5.7,zf(74+i*5.7)-dz) for i in range(8) for dz in (1.0,3.4)]
Bb=[sum(mu0*(r*1e-3)**2/(2*((r*1e-3)**2+(d+h*1e-3)**2)**1.5) for r,h in cur) for d in deps]; Wb=sum(2*math.pi*r*1e-3 for r,h in cur)
tot=[sum(Bk[k][i][2] for k in Bk) for i in range(3)]; Wt=sum(W.values())
S={k:(lambda p:((p[:-1]+p[1:])/2,np.diff(p,axis=0)))(p3[k][::8]) for k in p3}; a_w=0.6e-3; gm=0.7788*a_w
def M(k,l):
    m1,d1=S[k]; m2,d2=S[l]; t=0.0
    for i0 in range(0,len(m1),400):
        r=np.linalg.norm(m1[i0:i0+400,None,:]-m2[None,:,:],axis=2); r=np.sqrt(r**2+gm**2) if k==l else r; t+=np.sum((d1[i0:i0+400]@d2.T)/r)
    return 1e-7*t
Mx=np.zeros((6,6))
for k in range(1,7):
    for l in range(k,7):
        v=M(k,l)
        if k==l: ln=np.linalg.norm(S[k][1],axis=1); v+=float(np.sum(mu0*ln/(2*math.pi)*(np.log(2*ln/a_w)-0.75)))
        Mx[k-1,l-1]=Mx[l-1,k-1]=v
Ld=np.diag(Mx); kc=Mx/np.sqrt(np.outer(Ld,Ld))
tilt={int(d*1000):[(round(100*math.hypot(*Bk[k][i][:2])/abs(Bk[k][i][2]),1),round(math.degrees(math.atan2(Bk[k][i][1],Bk[k][i][0]))%360)) for k in range(1,7)] for i,d in enumerate(deps)}
res=dict(wire_per_layer_m=[round(W[k],2) for k in W],total_wire_m=round(Wt,1),all_six_series_Bz_uT_per_A=[round(x*1e6,2) for x in tot],per_wire_vs_current_band=[round((tot[i]/Wt)/(Bb[i]/Wb),2) for i in range(3)],
 self_L_uH=[round(x*1e6,1) for x in Ld],k_adjacent=[round(kc[i,i+1],2) for i in range(5)],k_L1_L6=round(kc[0,5],2),all_parallel_L_uH=round(float(1/np.sum(np.linalg.inv(Mx)))*1e6,1),all_series_L_uH=round(float(Mx.sum())*1e6),
 single_layer_Bz_uT_per_A=[round(Bk[1][i][2]*1e6,2) for i in range(3)],tilt_pct_and_azimuth_per_layer=tilt)
json.dump(res,open("kit_v9/physics.json","w"),indent=1); print(json.dumps(res))
