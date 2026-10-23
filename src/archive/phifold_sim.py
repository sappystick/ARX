import numpy as np, math, json
import phi_fold_former as pf, golden_cone_head as g
mu0=4e-7*math.pi; rho_cu=1.72e-8
fm=pf.Former(); W,_=pf.wires(fm,du=0.04)
mids,dls=[],[]
for P in W:
    m,d=pf.segs_closed(P[::2]); mids.append(m); dls.append(d)
mids,dls=np.concatenate(mids),np.concatenate(dls)
z=np.array([25,50,75,100,150,200,250,300,400,500.0])
pts=np.stack([0*z,0*z,-z*1e-3],-1)
B4=g.biot_savart(mids,dls,np.ones(len(mids)),pts)[:,2]    # T, 1 A in each of 4 sections
d=json.load(open("out_phifold/PHIFOLD233_spec.json"))
Rsec=d["electrical_per_section"]["R_dc_ohm"]; Lsec=d["electrical_per_section"]["L_uH"]*1e-6; M=d["electrical_per_section"]["M_between_sections_uH"]*1e-6
Rpar=Rsec/4; Lpar=(Lsec+3*M)/4
Vcu=4*d["winding"]["length_per_winding_m"]*0.50e-6     # copper volume m^3
out={}
# ---------- 1. geometry efficiency: B per sqrt(W) vs equal-copper single loops ----------
Bpar_per_A=B4/4                                    # 4 sections in parallel, per total amp
ours=Bpar_per_A/math.sqrt(Rpar)
def loop_eff(a,zz):   # equal copper volume, optimal-turns-independent B/sqrt(P)
    return mu0*math.sqrt(Vcu)*a/(4*math.pi*math.sqrt(rho_cu)*(a*a+zz*zz)**1.5)
refs={"9.17in single-radius loop (same footprint, a=110mm)":0.110,"11in round coil (a=140mm)":0.140,"14in round coil (a=178mm)":0.178}
out["B_per_sqrtW_uT"]={"depth_mm":z.tolist(),"PHI-FOLD 233":(ours*1e6).round(3).tolist()}
for k,a in refs.items(): out["B_per_sqrtW_uT"][k]=[round(loop_eff(a,zz*1e-3)*1e6,3) for zz in z]
# ---------- 2. power / current sweep ----------
prf=1000; t_hold=60e-6; V=24.0
rows=[]
for I in (2,4,6,10,15,20):
    t_ramp=Lpar*I/V; duty=(t_ramp/3+t_hold)*prf   # rms-equivalent on-time
    Pavg=I*I*Rpar*duty
    rows.append(dict(I_pk_A=I,t_ramp_us=round(t_ramp*1e6,1),avg_copper_W=round(Pavg,2),
                     B_100mm_uT=round(Bpar_per_A[3]*I*1e6,1),B_200mm_uT=round(Bpar_per_A[5]*I*1e6,2),
                     B_300mm_uT=round(Bpar_per_A[7]*I*1e6,2),
                     depth_gain_vs_2A_pct=round(((I/2)**(1/6)-1)*100,1)))
out["power_sweep"]=rows
# ---------- 3. target detection depth (PI, conducting sphere, air test) ----------
def sphere_V(Btx,Brx,I,a,sigma,t):
    n=np.arange(1,80); tau=mu0*sigma*a*a/(n*n*math.pi**2)
    S=(6/(n*n*math.pi**2)/tau*np.exp(-t/tau)).sum()
    return Btx*I*Brx*(2*math.pi*a**3/mu0)*S
zf=np.linspace(0.02,1.5,600); ptsf=np.stack([0*zf,0*zf,-zf],-1)
B4f=g.biot_savart(mids,dls,np.ones(len(mids)),ptsf)[:,2]
Btx_perA=B4f/4; Brx_perA=B4f                       # TX parallel, RX all 4 in series
NOISE={"lab-quiet 20 nV":20e-9,"realistic field 1 uV (EMI + ground residue)":1e-6}
targets={"1 g gold nugget (a=2.3mm, 1.5e7 S/m)":(2.3e-3,1.5e7),"10 g gold nugget (a=5.0mm)":(5.0e-3,1.5e7),
         "100 g gold nugget (a=10.7mm)":(10.7e-3,1.5e7),"US quarter-size silver/copper (a=8mm, 3e7)":(8e-3,3e7)}
dep={}
for nk,Vn in NOISE.items():
  dep[nk]={}
  for name,(a,s) in targets.items():
    dep[nk][name]={}
    for tdel in (5e-6,10e-6,20e-6,40e-6):
        for I in (4,10,20):
            v=np.array([sphere_V(bt,br,I,a,s,tdel) for bt,br in zip(Btx_perA,Brx_perA)])
            ok=np.where(v>Vn)[0]; dep[nk][name][f"delay {tdel*1e6:.0f}us, {I}A"]=round(float(zf[ok.max()]*1000),0) if len(ok) else 0
out["air_test_depth_mm"]=dep
# ---------- 4. frequency: soil skin depth ----------
out["soil_skin_depth_m"]={}
for f in (1e3,5e3,20e3,100e3):
    out["soil_skin_depth_m"][f"{int(f/1e3)} kHz"]={nm:round(math.sqrt(2/(2*math.pi*f*mu0*sg)),1) for nm,sg in
        (("dry soil 1e-3 S/m",1e-3),("wet soil 1e-2",1e-2),("wet clay 0.1",0.1),("saline/salt lake 1 S/m",1.0))}
# VLF frequency response of the 10 g nugget (in-phase / quadrature of sphere)
def sphere_vlf(a,s,f):
    k=np.sqrt(1j*2*math.pi*f*mu0*s); ka=k*a
    chi=-1.5*(1+3/ka**2-3/(ka*np.tanh(ka)))   # normalized response (-1.5 = perfect conductor)
    return chi
out["vlf_quadrature_response_norm"]={nm:{f"{f/1e3:g} kHz":round(float(-np.imag(sphere_vlf(a,1.5e7,f))),3) for f in (1e3,3e3,10e3,30e3,100e3)} for nm,a in (("1 g",2.3e-3),("10 g",5e-3),("100 g",10.7e-3))}
# ---------- 5. copper placement study: equal copper, turns in an outer band [r0, Rb] ----------
band={}
for r0 in (17,40,60,72.0,90,100):
    a=np.arange(r0,116.5,1.85)*1e-3
    vals=[]
    for zz in (0.1,0.2,0.3):
        num=(a*a/(a*a+zz*zz)**1.5).sum(); den=(2*math.pi*a).sum()
        vals.append(round(mu0*math.sqrt(Vcu)/(2*math.sqrt(rho_cu))*num/den*1e6,2))
    band[f"r >= {r0:g} mm"]=vals
out["copper_band_B_per_sqrtW_uT_at_100_200_300mm"]=band
json.dump(out,open("out_phifold/simulation_results.json","w"),indent=1)
print(json.dumps(out,indent=1))
