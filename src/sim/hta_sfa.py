import pickle, math, json, numpy as np
mu0=4e-7*math.pi; GOLD=137.50776405; PN,G,ZRX=3.6,0.8,3.2; P=pickle.load(open('kit_v15/LOW/paths.pkl','rb'))
TX=[np.c_[np.vstack([P[k][0],P[k][1]])[::4],np.full(len(np.vstack([P[k][0],P[k][1]])[::4]),ZRX+(6-k)*(PN+G)+PN-0.7)]*1e-3 for k in range(1,7)]
def Bz_at(path,pt):
    d=np.diff(path,axis=0); m=(path[:-1]+path[1:])/2; r=pt-m; rn=np.linalg.norm(r,axis=1)[:,None]; return (mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0))[2]
def Mutual(A,B):
    tot=0.0
    for a in A:
        da=np.diff(a,axis=0); ma=(a[:-1]+a[1:])/2
        for b in B:
            db=np.diff(b,axis=0); mb=(b[:-1]+b[1:])/2; r=np.linalg.norm(ma[:,None,:]-mb[None,:,:],axis=2); tot+=np.sum((da@db.T)/r)
    return 1e-7*tot
ts=np.linspace(0,2*np.pi,240,endpoint=False)
def ring(r,z,cx=0,cy=0,s=1): 
    x=np.append(r*np.cos(ts),r*np.cos(ts[0]))*s+cx; y=np.append(r*np.sin(ts),r*np.sin(ts[0]))+cy; return np.c_[x,y,np.full(241,z)]*1e-3
out={}
# ---- HTA (4 turns r35.5-43 at z=46.0) coupling to the six layers
hta=[ring(r,46.0) for r in (35.5,38.0,40.5,43.0)]; TXs=[t[::2] for t in TX]
M_series=Mutual(hta,TXs)                       # every layer carrying the same current
Meff=M_series/6.0                              # six layers in parallel, terminal current I
L_par=54e-6; dIdt=500.0/L_par
out["HTA"]=dict(M_to_each_layer_avg_nH=round(M_series/6*1e9,1),M_effective_all_parallel_nH=round(Meff*1e9,1),EMF_at_500V_flyback_V=round(Meff*dIdt,1),EMF_during_8A_ramp_V=round(Meff*26.0/L_par,2),note="EMF = M x dI/dt with dI/dt = 500 V / 54 uH at turn-off and 26 V / 54 uH during the ramp (all six layers in parallel, terminal current)")
# ---- sunflower differential array: 6 pairs at Vogel points (r = 100 sqrt((j-0.5)/6), theta = j x 137.508 deg), antipodal partner opposite sense, each loop 20 nested turns r3-12
def spiral_loop(cx,cy,sign,z=2.0,N=20,r0=3.0,r1=12.0):
    out=[]
    for r in np.linspace(r0,r1,N):
        l=ring(r,z,cx,cy)
        out.append(l if sign>0 else l[::-1])
    return out
pairs=[]
for j in range(1,7):
    r=100*math.sqrt((j-0.5)/6); th=math.radians((j*GOLD)%360); c=(r*math.cos(th),r*math.sin(th)); c2=(-c[0],-c[1]); pairs.append((spiral_loop(c[0],c[1],+1),spiral_loop(c2[0],c2[1],-1),r,math.degrees(th)%360))
nulls=[]
for A,B,r,th in pairs:
    MA=Mutual([p[::2] for p in A],TXs); MB=Mutual([p[::2] for p in B],TXs); nulls.append(abs(MA+MB)/(0.5*(abs(MA)+abs(MB))))
wire=sum(float(np.sum(np.linalg.norm(np.diff(p,axis=0),axis=1))) for A,B,_,_ in pairs for L in (A,B) for p in L)
mono=[ring(r,2.0) for r in np.linspace(20,110,18)]
def signal(rxloops,pt,zt): return sum(Bz_at(p,pt) for p in rxloops)*sum(Bz_at(t,pt) for t in TX)
res={}
for d in (40,100,200):
    zt=-d*1e-3; ref=signal(mono,np.array([0,0,zt]),zt); best=0.0
    for A,B,r,th in pairs:
        for x in np.arange(-110,111,10.0):
            for ang in (0,math.pi/4,math.pi/2,3*math.pi/4):
                pt=np.array([x*math.cos(ang)*1e-3,x*math.sin(ang)*1e-3,zt]); s=(sum(Bz_at(p,pt) for p in A)+sum(Bz_at(p,pt) for p in B))*sum(Bz_at(t,pt) for t in TX); best=max(best,abs(s)/abs(ref))
    res[f"best_pair_peak_vs_MONO_{d}mm"]=round(best,4)
out["sunflower_differential_array"]=dict(channels=6,loops=12,wire_m=round(wire,1),TX_null_residual_pct_per_pair=[round(100*n,3) for n in nulls],pair_radii_mm=[round(p[2],1) for p in pairs],pair_angles_deg=[round(p[3],1) for p in pairs],**res,hex_net_reference_peak_vs_MONO="1.20 (40 mm) / 0.44 (100 mm) / 0.21 (200 mm)")
json.dump(out,open("kit_v15/hta_and_sunflower_array.json","w"),indent=1); print(json.dumps(out,indent=1))
