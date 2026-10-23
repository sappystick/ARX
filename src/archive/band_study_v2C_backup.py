import numpy as np, math, json
from scipy.special import ellipk, ellipe
import phi_fold_v2 as v2, rodin_core_v4 as rc
mu0=4e-7*math.pi; rho=1.72e-8
def ring_B(a,zc,zp): return mu0*a*a/(2*(a*a+(zp-zc)**2)**1.5)
def ring_M(a,za,b,zb):
    k2=4*a*b/((a+b)**2+(za-zb)**2); k2=min(k2,1-1e-12); k=math.sqrt(k2)
    return mu0*math.sqrt(a*b)*((2/k-k)*ellipk(k2)-2/k*ellipe(k2))
def band_rings(RB,RI,RIM,ODw,nsec,nstack,pitch_extra=0.05,ds=0.5):
    """ring model of a folded maximum-density band (per section-sum, all sections in series)"""
    sv=(v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN,v2.WIRE_OD,v2.A_SEAT,v2.G_DEPTH,v2.PITCH,v2.N_W,v2.NOTCHES)
    v2.R_B,v2.R_I,v2.RIM_H=RB,RI,RIM; v2.H_IN=RIM+(RB-RI)*v2.T_SLOPE; v2.WIRE_OD=ODw
    v2.A_SEAT=ODw/2+0.05; v2.G_DEPTH=nstack*ODw+0.05; v2.PITCH=2*v2.A_SEAT+2*v2.G_LAND+pitch_extra; v2.N_W=nsec; v2.NOTCHES=False
    v2.RHO.update(heel=min(5,RIM/2.7),crown=min(5,RIM/2.7))
    fm=v2.Former(); s=np.arange(0,fm.L,ds); r,z,h,_,_=rc.eval_profile(fm.segs,s)
    nr,nz=np.sin(h),-np.cos(h); off=-v2.G_DEPTH/2; r=r+off*nr; z=z+off*nz
    n=fm.dens(s)*ds/(2*math.pi)*nsec*nstack            # turns represented by each ring
    length=float((n*2*math.pi*r).sum())*1e-3
    (v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN,v2.WIRE_OD,v2.A_SEAT,v2.G_DEPTH,v2.PITCH,v2.N_W,v2.NOTCHES)=sv
    return np.c_[r*1e-3,z*1e-3,n], length
TX,LTX=band_rings(116.5,72.004,13.0,1.2,4,2)
HUB,LH=band_rings(60.4,26.0,26.244,1.2,4,2)              # inner tapered band, same TX wire
HUBRX,LHRX=band_rings(60.4,26.0,26.244,0.8,4,1)          # inner band as RX, 0.8 mm Litz
def Bz(R,zp): return sum(n*ring_B(a,zc,zp) for a,zc,n in R)
A=0.5e-6; zs=[-0.1,-0.2,-0.3]
out={}
# validate ring model against v2A full Biot-Savart (36.14 uT/sqrtW @200mm, parallel drive)
B=Bz(TX,-0.2); R=rho*LTX/A
out["ringmodel_check_v2A_BpsW_200"]=round(B/math.sqrt(R)*1e6/4*1/math.sqrt(1/16)/4*1,2)   # series-all equiv -> same B/sqrtP
out["v2A_series_BpsW"]={f"{-z*1000:.0f}mm":round(Bz(TX,z)/math.sqrt(R)*1e6,2) for z in zs}
# 1. hub band as additional TX, series same current
R2=rho*(LTX+LH)/A
out["TX+hub_series_BpsW"]={f"{-z*1000:.0f}mm":round((Bz(TX,z)+Bz(HUB,z))/math.sqrt(R2)*1e6,2) for z in zs}
# 2. optimal current split between zones (Lagrange: I_i ~ b_i/R_i) -> B/sqrtP = sqrt(sum b_i^2/R_i)
Rh=rho*LH/A
out["TX+hub_optimal_split_BpsW"]={f"{-z*1000:.0f}mm":round(math.sqrt(Bz(TX,z)**2/R+Bz(HUB,z)**2/Rh)*1e6,2) for z in zs}
out["hub_current_ratio_optimal_200mm"]=round((Bz(HUB,-0.2)/Rh)/(Bz(TX,-0.2)/R),3)
# 3. sequential base->tip: field at 200 mm, outer band alone / hub alone / together (same currents)
out["sequential_vs_simultaneous_200mm_uT_per_A"]=dict(outer_alone=round(Bz(TX,-0.2)*1e6,2),hub_alone=round(Bz(HUB,-0.2)*1e6,2),together=round((Bz(TX,-0.2)+Bz(HUB,-0.2))*1e6,2))
# 4. receivers.  target: conducting sphere on axis; V = B_tx(z) I * B_rx(z) * (2 pi a^3/mu0) * S(t)
def S(a,sig,t):
    n=np.arange(1,80); tau=mu0*sig*a*a/(n*n*math.pi**2); return float((6/(n*n*math.pi**2)/tau*np.exp(-t/tau)).sum())
def M_set(R1,R2): return sum(n1*n2*ring_M(a1,z1,a2,z2) for a1,z1,n1 in R1 for a2,z2,n2 in R2)
Mtx_hub=M_set(TX[::4],HUBRX[::4])*16
# bucking: reverse turns on hub outer wall top (r=69.5, z=23 mm): M per turn
buck=np.array([[0.0595,0.0262,1.0]])
Mb=M_set(TX[::2],buck)*2
Nb=Mtx_hub/Mb
HUBRX_nulled=np.vstack([HUBRX,np.c_[buck[:,:2],-Nb*np.ones(1)]])
# TX: v2A in parallel, I_pk 10 A total ; B_tx per total amp = Bz(TX)/... (series-equivalent per section): use series string current I/4 per section *4 sections -> per-section field
def depth(Rrx,t,a,sig,Vn,I=10.0):
    zz=np.linspace(0.03,1.2,500)
    v=[Bz(TX,-z)/(4*2)*I*abs(Bz(Rrx,-z))*(2*math.pi*a**3/mu0)*S(a,sig,t) for z in zz]
    # Bz(TX)/(4*2): TX in parallel -> each section carries I/4; TX rings sum 4 sections x 2 layers per series string
    ok=[z for z,vv in zip(zz,v) if vv>Vn]; return round(max(ok)*1000) if ok else 0
targets={"1 g gold":(2.3e-3,1.5e7),"10 g gold":(5e-3,1.5e7),"coin":(8e-3,3e7)}
Vn=1e-6
mono=TX                                                 # receive on all 4 sections in series (both layers)
rx={}
for nm,(a,sg) in targets.items():
    rx[nm]=dict(mono_TX_coil_at_10us=depth(mono,10e-6,a,sg,Vn),
                hub_RX_nulled_at_4us=depth(HUBRX_nulled,4e-6,a,sg,Vn),
                hub_RX_nulled_at_10us=depth(HUBRX_nulled,10e-6,a,sg,Vn),
                combined_mono10us_plus_hub4us="max of both channels")
out["receiver_depth_mm (10 A, 1 uV)"]=rx
out["hub_RX"]=dict(copper_m=round(LHRX,1),turns=round(float(HUBRX[:,2].sum()),1),bucking_turns_required=round(float(Nb),2),
                   coupling_before_null_uH=round(Mtx_hub*1e6,2),
                   sensitivity_loss_from_bucking_pct=round(100*(1-abs(Bz(HUBRX_nulled,-0.2))/abs(Bz(HUBRX,-0.2))),1))
# 5. ferrite tube (MnZn mu_r 2000, OD 50, wall 3, L 30): magnetostatic shielding + moment boost
mur,Rt,t=2000,0.025,0.003
out["ferrite_tube"]=dict(transverse_shielding_factor=round(1+mur*t/(2*Rt),0),shielding_dB=round(20*math.log10(1+mur*t/(2*Rt)),1),
    note="axial shielding of a short open tube is much weaker (end openings); add ferrite end caps")
# moment boost: tube in near-uniform centre field ~ B0; induced moment m = V*chi_eff*B0/mu0, chi_eff ~ 1/N_axial (short tube N~0.4)
V_tube=math.pi*(Rt**2-(Rt-t)**2)*0.030; B0=Bz(TX,0.017)                  # field at centre per series amp
m_ferr=V_tube*(1/0.4)*B0/mu0; m_tx=sum(n*math.pi*a*a for a,zc,n in TX)
out["ferrite_tube"]["moment_boost_pct"]=round(100*m_ferr/m_tx,2)
json.dump(out,open("out_phifold_v2/band_study.json","w"),indent=1); print(json.dumps(out,indent=1))
