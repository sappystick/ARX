import pickle, math, json, numpy as np
mu0=4e-7*math.pi; P=pickle.load(open('kit_v15/LOW/paths.pkl','rb')); PN,G,ZRX=3.6,0.8,3.2
TX=[np.c_[np.vstack([P[k][0],P[k][1]])[::3],np.full(len(np.vstack([P[k][0],P[k][1]])[::3]),ZRX+(6-k)*(PN+G)+PN-0.7)]*1e-3 for k in range(1,7)]
def B(pt):
    b=np.zeros(3)
    for p in TX:
        d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2; r=pt-m; rn=np.sqrt((r**2).sum(1)+1e-9)[:,None]; b+=mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0)
    return b/6.0                                   # per ampere of terminal current (six layers in parallel)
out={}; dIdt=500.0/54e-6
for z in (9.8,17.8,25.8,33.8,37.5):
    row={}
    for r in (0,20,40):
        vals=[np.linalg.norm(B(np.array([r*1e-3*math.cos(a),r*1e-3*math.sin(a),z*1e-3]))) for a in (0,math.pi/2,math.pi)]
        b=float(np.mean(vals)); row[f"r{r}"]=dict(B_uT_per_A=round(b*1e6,1),EMF_mV_per_cm2_unshielded_500V_flyback=round(b*dIdt*1e-4*1e3,1))
    out[f"z{z}"]=row
json.dump(out,open("kit_v17/vault_field_by_slot.json","w"),indent=1); print(json.dumps(out))
