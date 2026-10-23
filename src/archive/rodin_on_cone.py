import numpy as np, math, json
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g, phi_fold_former as pf
v2.NOTCHES=False
fm=v2.Former()                       # same annular golden-band profile as v2A
segs=fm.segs; off,Ltot=rc.seg_offsets(segs)
sf=np.linspace(0,Ltot,200001); r=rc.eval_profile(segs,sf)[0]
I_r=np.concatenate([[0],np.cumsum((1/r[1:]+1/r[:-1])/2*np.diff(sf))])
results={}
def rodin_paths(N=72,K=27,extra_turns=0):
    adv=K*2*math.pi/N + 2*math.pi*extra_turns
    kap=adv/I_r[-1]
    s=np.linspace(0,Ltot,1200,endpoint=False)
    rr,zz,h,_,_=rc.eval_profile(segs,s); nr,nz=np.sin(h),-np.cos(h)
    c=kap*np.interp(s,sf,I_r); off_=-0.6; rv,zv=rr+off_*nr,zz+off_*nz
    coils={}
    for d in range(1,10):
        n0=d-1; P=[]
        for m in range(8):
            n=(n0+K*m)%N; ph=n*2*math.pi/N+c+ (2*math.pi*extra_turns*0)
            P.append(np.stack([rv*np.cos(ph),rv*np.sin(ph),zv],-1))
        coils[d]=np.concatenate(P)
    return coils
def field(Ps,pts):
    mm,dd=[],[]
    for P in Ps: m,d=pf.segs_closed(P); mm.append(m); dd.append(d)
    mm,dd=np.concatenate(mm),np.concatenate(dd)
    return g.biot_savart(mm,dd,np.ones(len(mm)),pts), float(np.linalg.norm(dd,axis=1).sum())
pt=np.array([[0,0,-0.2]]); A=0.5e-6; rho=1.72e-8
# v2A reference: B/sqrtW/sqrt(V)
dA=json.load(open("out_phifold_v2/PHIFOLD233v2_A_gallery_spec.json"))
VA=dA["winding"]["total_length_m"]*A
refA=dA["field"]["B_per_sqrtW_uT"][4]/math.sqrt(VA)
for label,extra in (("classic Rodin 72/27 (135 deg per circuit)",0),("Rodin 72/27 + 3 extra turns per circuit",3),("Rodin 72/27 + 6 extra turns per circuit",6)):
    coils=rodin_paths(extra_turns=extra)
    B,Lc=field(list(coils.values()),pt)
    R=rho*Lc/A; eff=abs(B[0,2])/math.sqrt(R)*1e6/math.sqrt(Lc*A)
    results[label]=dict(copper_m=round(Lc,1),net_azimuthal_turns=round(72*(27/72+extra),1),
                        Bz_200mm_per_sqrtW_per_sqrtV_rel_to_v2A=round(eff/refA,3))
# virtual spinning test: fire each Rodin digit coil alone in doubling order; field direction under centre and under rim
order=[1,2,4,8,7,5]; coils=rodin_paths()
pts=np.array([[0,0,-0.2],[0.09,0,-0.1]])
spin=[]
for d in order:
    B,_=field([coils[d]],pts)
    spin.append(dict(coil=d,centre_Bxy_over_Bz=round(float(np.hypot(B[0,0],B[0,1])/abs(B[0,2])),4),
                     offaxis_azimuth_deg=round(math.degrees(math.atan2(B[1,1],B[1,0])),1),
                     offaxis_Bz_uT=round(B[1,2]*1e6,3)))
results["doubling_sequence_firing"]=spin
# quadrant-sector Rodin: lanes grouped by entry angle into 4 quadrants
quad=[]
s=np.linspace(0,Ltot,1200,endpoint=False); rr,zz,h,_,_=rc.eval_profile(segs,s); nr,nz=np.sin(h),-np.cos(h)
kap=(27*2*math.pi/72)/I_r[-1]; c=kap*np.interp(s,sf,I_r); rv,zv=rr-0.6*nr,zz-0.6*nz
for q in range(4):
    Ps=[np.stack([rv*np.cos(n*5*math.pi/180+c),rv*np.sin(n*5*math.pi/180+c),zv],-1) for n in range(72) if (n*5)//90==q]
    B,_=field(Ps,np.array([[0,0,-0.2]]))
    quad.append(dict(quadrant=q,Bx=round(B[0,0]*1e6,3),By=round(B[0,1]*1e6,3),Bz=round(B[0,2]*1e6,3),
                     horizontal_angle_deg=round(math.degrees(math.atan2(B[0,1],B[0,0])),1)))
results["quadrant_sector_rodin_at_200mm"]=quad
json.dump(results,open("out_phifold_v2/rodin_mapping_results.json","w"),indent=1)
print(json.dumps(results,indent=1))
