import numpy as np, math, json, pickle, time
from scipy.integrate import solve_ivp
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
mu0=4e-7*math.pi; t0=time.time(); OUT={}
# ======================= S1: TX power stage (real topology: coil || 330 ohm damping chain, DC1 -> CL1A/B || RCL1 to VBUS, 2 FETs) =======================
L=54e-6; Rc=0.045; Cn=500e-12; Rd=330.0; Vbus=26.0; Vf=1.2; Ron=0.05; RCL=5e3
def pulse(I0,CL,f=400.0,derate=False,Cn=Cn):
    T=1/f; ton=L*I0/Vbus; vc0=0.0; Vk=462.0
    Cfun=(lambda v: CL/(1+(abs(v)/Vk)**2)) if derate else (lambda v: CL)
    for it in range(10):
        def rhs(t,y):
            i,vd,vc=y; iD=max(0.0,vd-vc-Vf)/Ron
            return [(-vd-Rc*i)/L,(i-vd/Rd-iD)/Cn,(iD-vc/RCL)/Cfun(vc)]
        te=np.linspace(0,60e-6,6000)
        s=solve_ivp(rhs,[0,60e-6],[I0,0.0,vc0],t_eval=te,method="Radau",rtol=1e-7,atol=[1e-6,1e-4,1e-4],max_step=2e-8)
        t,i,vd,vc=s.t,s.y[0],s.y[1],s.y[2]
        rest=T-60e-6-ton; vc_end=vc[-1]*math.exp(-rest/(RCL*CL)) if not derate else vc[-1]*math.exp(-rest/(RCL*CL))
        if abs(vc_end-vc0)<0.5: break
        vc0=vc_end
    iD=np.maximum(0,vd-vc-Vf)/Ron; dt=t[1]-t[0]
    nz=np.where(i<=0)[0]; t_zero=t[nz[0]] if len(nz) else float('nan')
    # time after which the coil is quiet: |vd|<1 V and |i|<2 mA
    bad=np.where((np.abs(vd)>1.0)|(np.abs(i)>2e-3))[0]; t_quiet=t[bad[-1]+1] if len(bad) else 0.0
    E=dict(damp=float(np.sum(vd**2/Rd)*dt),diode=float(np.sum(iD*Vf)*dt),coilR=float(np.sum(i**2*Rc)*dt)+ (I0**2/3*Rc*ton))
    # clamp-resistor energy over the whole period: off phase numeric + decay over the rest of the period
    Ercl=float(np.sum(vc**2/RCL)*dt)+ (vc[-1]**2*RCL*CL/(2*RCL)*(1-math.exp(-2*rest/(RCL*CL)))/(RCL*CL)*(RCL*CL)/RCL if False else vc[-1]**2/RCL*(RCL*CL/2)*(1-math.exp(-2*rest/(RCL*CL))))
    return dict(I0=I0,CL_nF=CL*1e9,derated=derate,f=f,ton_us=ton*1e6,vd_peak=float(vd.max()),vc_peak=float(vc.max()),vc_min=float(vc0),Vds_peak=float(vd.max()+Vbus),t_zero_us=t_zero*1e6,t_quiet_us=t_quiet*1e6,
        E_half_LI2_mJ=0.5*L*I0**2*1e3,P_damp_W=E["damp"]*f,P_diode_W=E["diode"]*f,P_RCL_W=Ercl*f,P_coil_W=E["coilR"]*f,peak_i_diode=float(iD.max())),(t,i,vd,vc)
cases=[("as built: 2 x 100 nF X7R, nominal",20,200e-9,False),("as built: 2 x 100 nF X7R, with DC-bias derating",20,200e-9,True),("100 nF C0G/film",20,100e-9,False),("68 nF film",20,68e-9,False),("150 nF film",20,150e-9,False)]
rows=[]; wf={}
for nm,I0,C,dr in cases:
    r,w=pulse(I0,C,derate=dr); r["case"]=nm; rows.append(r); wf[nm]=w
for I0 in (8,14):
    for C in (200e-9,100e-9):
        r,w=pulse(I0,C,f=800 if I0==8 else 600); r["case"]=f"{I0} A, {int(C*1e9)} nF"; rows.append(r)
OUT["tx_stage"]=[{k:(round(v,3) if isinstance(v,float) else v) for k,v in r.items()} for r in rows]
for r in OUT["tx_stage"][:5]: print("TX",r["case"],"Vds_pk",r["Vds_peak"],"t_zero_us",r["t_zero_us"],"t_quiet_us",r["t_quiet_us"],"P_RCL",r["P_RCL_W"],"P_damp",r["P_damp_W"])
# ======================= S2: projected field and TX moment =======================
P=pickle.load(open('kit_v15/LOW/paths.pkl','rb')); PN,G,ZRX=3.6,0.8,3.2
TXL=[np.c_[np.vstack([P[k][0],P[k][1]])[::8],np.full(len(np.vstack([P[k][0],P[k][1]])[::8]),ZRX+(6-k)*(PN+G)+PN-0.7)]*1e-3 for k in range(1,7)]
def Bvec_many(paths,pts,chunk=150):
    out=np.zeros((len(pts),3))
    for p in paths:
        d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2
        for a in range(0,len(pts),chunk):
            q=pts[a:a+chunk]; r=q[:,None,:]-m[None,:,:]; rn=np.sqrt((r**2).sum(2)+1e-10)[:,:,None]; out[a:a+chunk]+=mu0/(4*np.pi)*np.sum(np.cross(d[None,:,:],r)/rn**3,axis=1)
    return out
TXB=lambda pts: Bvec_many(TXL,pts)/6.0                      # tesla per terminal ampere (six layers in parallel)
mz=0.0
for p in TXL: xy=p[:,:2]; mz+=0.5*np.sum(xy[:-1,0]*xy[1:,1]-xy[1:,0]*xy[:-1,1])
m_per_A=abs(mz)/6.0*1.0                                      # each layer carries I/6; area-turns summed over layers
OUT["tx_moment"]=dict(area_turns_sum_m2=round(abs(mz),3),moment_Am2_at_20A=round(m_per_A*20,2),moment_Am2_at_8A=round(m_per_A*8,2))
depths=np.array([0.05,0.1,0.15,0.2,0.3,0.4,0.5]); axis=np.c_[np.zeros_like(depths),np.zeros_like(depths),-depths]
Bax=TXB(axis); OUT["axis_field_uT_per_A"]={f"{int(d*1000)}mm":round(float(abs(b[2])*1e6),2) for d,b in zip(depths,Bax)}
OUT["axis_field_uT_at_20A"]={k:round(v*20,1) for k,v in OUT["axis_field_uT_per_A"].items()}
OUT["dBdt_T_per_s_at_100mm_20A_turnoff"]=round(float(abs(Bax[1][2])*20/(OUT["tx_stage"][2]["t_zero_us"]*1e-6)),1)
print("moment",OUT["tx_moment"],"axis",OUT["axis_field_uT_at_20A"])
# ======================= S3: coupling and pickup (TX -> RX channels) =======================
ts=np.linspace(0,2*np.pi,60,endpoint=False)
def ring(r,cx,cy,sgn,z=2.0e-3):
    x=r*np.cos(ts)+cx; y=r*np.sin(ts)+cy; l=np.c_[np.append(x,x[0]),np.append(y,y[0]),np.full(61,z)]*1e-3; return l if sgn>0 else l[::-1]
mono=[ring(r,0,0,1) for r in np.linspace(20,110,18)]; x8=[ring(r,55,0,1) for r in np.linspace(20,52,12)]+[ring(r,-55,0,-1) for r in np.linspace(20,52,12)]
quad=[ring(r,cx,cy,sg) for (cx,cy,sg) in ((50,50,1),(-50,50,-1),(-50,-50,1),(50,-50,-1)) for r in np.linspace(15,45,6)]
def Mutual(A,B):
    tot=0.0
    for a in A:
        da=np.diff(a,axis=0); ma=(a[:-1]+a[1:])/2
        for b in B:
            db=np.diff(b,axis=0); mb=(b[:-1]+b[1:])/2; r=np.linalg.norm(ma[:,None,:]-mb[None,:,:],axis=2); tot+=np.sum((da@db.T)/r)
    return 1e-7*tot
TXs=[p[::2] for p in TXL]
M_mono=Mutual(TXs,[l[::2] for l in mono])/6.0               # per terminal ampere
OUT["coupling"]=dict(M_TX_to_unnulled_disc_coil_uH=round(M_mono*1e6,2))
# ======================= S4: target response (sphere in a step-off field) with the real gate start from S1 =======================
sig=4.1e7; rho=19300.0
noise={"X8":4.2e-9,"QUAD":1.7e-9}                              # V/rtHz: RS3=1k (X8) / RS=100 ohm (QUAD) + OPA2211 1.1 nV + coil
null={"X8":2.5e-4,"QUAD":3e-5}; null_ecc={"X8":8e-3,"QUAD":3e-4}
Navg=100
def sphere_a(mass_g): return (3*mass_g*1e-3/(4*np.pi*rho))**(1/3)
def vt(t,a,K): tau=mu0*sig*a**2/np.pi**2; n=np.arange(1,40)[:,None]; return K/tau*np.sum(np.exp(-(n**2)*t[None,:]/tau),axis=0),tau
def best_channel_snr(a,chan,t_first,Iamp,Bt,Br):
    K=(2*np.pi*a**3/mu0)*(6/np.pi**2)*Iamp*float(Bt@Br); gates=[t_first*1.618**k for k in range(9)]; best=0.0
    for tc in gates:
        if tc<t_first: continue
        Tg=0.5*tc; tt=np.linspace(tc-Tg/2,tc+Tg/2,40); v,_=vt(tt,a,K); sig_v=abs(v.mean()); nv=noise[chan]*math.sqrt(1/(2*Tg))/math.sqrt(Navg); best=max(best,sig_v/nv)
    return best
latx=np.array([-150,-100,-60,-30,0,30,60,100,150])*1e-3; grid=np.array([[x,y] for x in latx for y in latx])
res={}; tails={}
def tail_t_first(tr,chan,case):
    t,i,vd,vc=wf[case]; didt=np.abs(np.gradient(i,t)); emf=null[chan]*M_mono*didt                      # volts on the nulled channel
    ok=np.where(emf>noise[chan]*math.sqrt(1/(2*0.5*t[1:]+1e-12).mean()) if False else emf>1e-6)[0]
    # tail must be below 100 nV (about 2x the gated noise floor of the weakest channel) before the first gate
    bad=np.where(emf>1e-7)[0]; return (t[bad[-1]+1] if len(bad) else 0.0)
for case in ("as built: 2 x 100 nF X7R, with DC-bias derating","100 nF C0G/film"):
    tails[case]={ch:round(tail_t_first(None,ch,case)*1e6,2) for ch in ("X8","QUAD")}
OUT["first_clean_gate_us"]=tails; print("first clean gate (us)",tails)
for case in tails:
    for chan,rxl in (("X8",x8),("QUAD",quad)):
        for mass in (0.1,0.5,1.0,5.0,20.0):
            a=sphere_a(mass); tf=max(tails[case][chan]*1e-6,6e-6); depth_ok=0
            snr_by_depth=[]
            for d in depths:
                pts=np.c_[grid[:,0],grid[:,1],np.full(len(grid),-d)]; Bt=TXB(pts); Br=Bvec_many(rxl,pts)
                s=max(best_channel_snr(a,chan,tf,20.0,Bt[k],Br[k]) for k in range(len(pts)))
                snr_by_depth.append(s)
            sn=np.array(snr_by_depth); ld=np.log(sn+1e-30); 
            dd=None
            for k in range(len(depths)-1):
                if sn[k]>=3 and sn[k+1]<3: f=(ld[k]-math.log(3))/(ld[k]-ld[k+1]); dd=depths[k]+f*(depths[k+1]-depths[k]); break
            if dd is None: dd=depths[-1] if sn[-1]>=3 else (0.0 if sn[0]<3 else depths[-1])
            res[f"{case} | {chan} | {mass} g"]=dict(detect_depth_mm=round(dd*1000),snr_at=[round(float(x),1) for x in sn])
OUT["gold_nugget_depth_noise_limited"]=res
print({k:v["detect_depth_mm"] for k,v in res.items()})
# pickup on the receive channels at turn-off (volts)
didt_peak=max(np.max(np.abs(np.gradient(wf[c][1],wf[c][0]))) for c in wf)
OUT["rx_pickup_peak_V"]=dict(unnulled_disc=round(M_mono*didt_peak,1),X8_nominal=round(null["X8"]*M_mono*didt_peak,4),X8_eccentric=round(null_ecc["X8"]*M_mono*didt_peak,3),QUAD_nominal=round(null["QUAD"]*M_mono*didt_peak,5))
print("pickup",OUT["rx_pickup_peak_V"])
json.dump(OUT,open("kit_v20/sim_head1.json","w"),indent=1,default=float)

# ---------------- S4b: what moves the noise-limited depth (film clamp, X8 channel, best lateral position)
def depth_for(mass,nd,N,gain=1.0,chan="X8",rxl=x8,tf=7.94e-6):
    a=sphere_a(mass); sn=[]
    for d in depths:
        pts=np.c_[grid[:,0],grid[:,1],np.full(len(grid),-d)]; Bt=TXB(pts); Br=Bvec_many(rxl,pts); best=0.0
        for k in range(len(pts)):
            K=(2*np.pi*a**3/mu0)*(6/np.pi**2)*20.0*gain*float(Bt[k]@Br[k])
            for kk in range(9):
                tc=tf*1.618**kk; Tg=0.5*tc; tt=np.linspace(tc-Tg/2,tc+Tg/2,30); v,_=vt(tt,a,K); best=max(best,abs(v.mean())/(nd*math.sqrt(1/(2*Tg))/math.sqrt(N)))
        sn.append(best)
    sn=np.array(sn); dd=depths[-1] if sn[-1]>=3 else 0.0
    for k in range(len(depths)-1):
        if sn[k]>=3 and sn[k+1]<3: f=(math.log(sn[k])-math.log(3))/(math.log(sn[k])-math.log(sn[k+1])); dd=depths[k]+f*(depths[k+1]-depths[k]); break
    return round(dd*1000)
scen={"baseline (RS3 = 1 kohm, 100 pulses, no hood)":(4.2e-9,100,1.0),"RS3 -> 100 ohm":(1.7e-9,100,1.0),"RS3 -> 100 ohm + 400 pulses (1 s)":(1.7e-9,400,1.0),"+ ferrite hood (+5%)":(1.7e-9,400,1.053)}
OUT["improvement_steps_X8_depth_mm"]={k:{f"{m} g":depth_for(m,*v) for m in (0.1,1.0,5.0)} for k,v in scen.items()}
print(OUT["improvement_steps_X8_depth_mm"])
json.dump(OUT,open("kit_v20/sim_head1.json","w"),indent=1,default=float)
# ---------------- figures
fig,ax=plt.subplots(2,2,figsize=(16,10))
for nm in ("as built: 2 x 100 nF X7R, with DC-bias derating","100 nF C0G/film","68 nF film"):
    t,i,vd,vc=wf[nm]; ax[0,0].plot(t*1e6,i,label=nm); ax[0,1].plot(t*1e6,vd,label=nm)
ax[0,0].set_xlim(0,25); ax[0,0].set_title("coil current after turn-off (20 A, 54 uH)"); ax[0,0].set_xlabel("us"); ax[0,0].set_ylabel("A"); ax[0,0].legend(fontsize=7); ax[0,0].grid(alpha=.3)
ax[0,1].set_xlim(0,25); ax[0,1].set_title("drain voltage above the 26 V bus (FET rating 650 V)"); ax[0,1].set_xlabel("us"); ax[0,1].set_ylabel("V"); ax[0,1].grid(alpha=.3)
t,i,vd,vc=wf["100 nF C0G/film"]; ax[1,0].semilogy(t*1e6,np.abs(vd)+1e-6,label="|v drain|"); ax[1,0].semilogy(t*1e6,np.abs(i)+1e-9,label="|i coil|"); ax[1,0].set_xlim(0,30); ax[1,0].set_ylim(1e-5,1e3); ax[1,0].set_title("ring-down to the first gate (100 nF film clamp)"); ax[1,0].legend(); ax[1,0].grid(alpha=.3,which="both"); ax[1,0].set_xlabel("us")
for k,v in res.items():
    if "| X8 |" in k and "C0G" in k: ax[1,1].semilogy(depths*1000,np.array(v["snr_at"])+1e-9,marker="o",label=k.split("|")[2])
ax[1,1].axhline(3,color="r",ls="--"); ax[1,1].set_title("X8 channel SNR vs depth, gold nuggets (noise only, no ground)"); ax[1,1].set_xlabel("depth mm"); ax[1,1].legend(fontsize=8); ax[1,1].grid(alpha=.3,which="both")
plt.tight_layout(); plt.savefig("kit_v20/SIM_TX_STAGE_AND_TARGET.png",dpi=90); print("done",round(time.time()-t0),"s")
