import pickle, math, json, numpy as np
mu0=4e-7*math.pi; rho=1.72e-8; Lw=8.97; out={}
# ---- A. litz options (copper area is typical packing: ~0.5 of OD circle area)
rows=[]
for od in (1.2,1.5,1.8):
    A=0.5*math.pi*(od/2)**2; Rl=rho*Lw/(A*1e-6); Rp=Rl/6
    need_t=2*od+1.2; pitch_outer_ret=(109.6**2-62**2)/(16*109.6)/2
    rows.append(dict(od=od,cu_mm2=round(A,2),R_layer_mohm=round(Rl*1e3),R_six_parallel_mohm=round(Rp*1e3,1),layer_thickness_needed=round(need_t,1),stack_height=round(3.2+6*(need_t+0.8),1),wire_to_wire_pitch_at_rim=round(pitch_outer_ret,2),groove_wall_left_at_rim=round(pitch_outer_ret-(od+0.3),2),field_per_sqrtW_vs_1p2=round(math.sqrt(A/(0.5*math.pi*0.36)),2)))
out["litz"]=rows
# coil heating and energy: L = 54 uH (six layers in parallel)
L=54e-6; V=26.0; res=[]
for nm,I,f in (("scan 8 A / 800 Hz",8,800),("mid 14 A / 600 Hz",14,600),("boost 20 A / 400 Hz",20,400),("boost 20 A / 800 Hz",20,800)):
    t=L*I/V; E=0.5*L*I*I; Pclamp=E*f; Irms2=I*I/3*t*f; Pcu=Irms2*(rho*Lw/(0.5*math.pi*0.36e-6)/6)
    P=Pclamp+3.27+Pcu; res.append(dict(mode=nm,ramp_us=round(t*1e6,1),turnoff_us_at_500V=round(L*I/500*1e6,2),pulse_mJ=round(E*1e3,2),clamp_W=round(Pclamp,2),copper_W=round(Pcu,3),total_W=round(P,2),hours_90p7Wh=round(90.7/P,1)))
out["power"]=res
# ---- C. alignment error budget
out["tolerance"]=dict(tooth_vs_track_play_mm=0.4,angular_play_deg=round(math.degrees(0.2/49.9),2),shift_at_rim_mm=round(0.2/49.9*116.5,2),ripple_phase_error_deg=round(12*math.degrees(0.2/49.9),1),bore_radial_play_mm=0.2,worst_stack_eccentricity_mm=0.65,X8_null_residual_at_0p5mm=0.66)
# ---- D. central tip array vs big figure-8 (approximate geometry): signal ~ Brx x Btx at a point target
P=pickle.load(open('kit_v15/LOW/paths.pkl','rb')); PN,G,ZRX=3.6,0.8,3.2
TX=[np.c_[np.vstack([P[k][0],P[k][1]])[::4],np.full(len(np.vstack([P[k][0],P[k][1]])[::4]),ZRX+(6-k)*(PN+G)+PN-0.7)]*1e-3 for k in range(1,7)]
def Bz(path,pt):
    d=np.diff(path,axis=0); m=(path[:-1]+path[1:])/2; r=pt-m; rn=np.sqrt((r**2).sum(1)+1e-12)[:,None]; return (mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0))[2]
ts=np.linspace(0,2*np.pi,120,endpoint=False)
def ring(r,cx,cy,sgn=1): x=r*np.cos(ts)+cx; y=r*np.sin(ts)+cy; l=np.c_[np.append(x,x[0]),np.append(y,y[0]),np.full(121,2.0)]*1e-3; return l if sgn>0 else l[::-1]
tip=[ring(r,11,0,+1) for r in np.linspace(3,9.5,20)]+[ring(r,-11,0,-1) for r in np.linspace(3,9.5,20)]
x8=[ring(r,55,0,+1) for r in np.linspace(20,52,12)]+[ring(r,-55,0,-1) for r in np.linspace(20,52,12)]
mono=[ring(r,0,0) for r in np.linspace(20,110,18)]
def best(rx,d):
    zt=-d*1e-3; b=0
    for x in np.arange(-120,121,4.0):
        pt=np.array([x*1e-3,0,zt]); s=abs(sum(Bz(p,pt) for p in rx)*sum(Bz(t,pt) for t in TX)); b=max(b,s)
    return b
tipr={}
for d in (10,20,40,100):
    ref=abs(sum(Bz(p,np.array([0,0,-d*1e-3])) for p in mono)*sum(Bz(t,np.array([0,0,-d*1e-3])) for t in TX)); tipr[d]=dict(tip_vs_MONO=round(best(tip,d)/ref,3),X8_vs_MONO=round(best(x8,d)/ref,3))
wire_tip=sum(float(np.sum(np.linalg.norm(np.diff(p,axis=0),axis=1))) for p in tip)
out["tip_vs_X8"]=tipr; out["tip_wire_m"]=round(wire_tip,2)
json.dump(out,open("kit_v15/eval_v17.json","w"),indent=1); print(json.dumps(out))
