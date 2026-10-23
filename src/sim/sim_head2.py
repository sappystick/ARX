import numpy as np, math, json
import scipy.sparse as sp, scipy.sparse.linalg as sla
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
dr,dz=1.0,0.5; nr,nz=120,100                                    # r 0..120 mm, z 0..50 mm (axisymmetric)
rc=(np.arange(nr)+0.5)*dr; zc=(np.arange(nz)+0.5)*dz; ri=np.arange(nr)*dr; ro=ri+dr
def build(P_ab,P_cb,P_damp,P_led,Tamb,h_top=10.0,h_side=8.0,h_bot=6.0):
    k_r=np.full((nr,nz),np.nan); k_z=np.full((nr,nz),np.nan); Q=np.zeros((nr,nz))
    for i in range(nr):
        r=rc[i]
        for j in range(nz):
            z=zc[j]; kr=kz=None
            if r>119.0: continue
            if z<0.8 and r<116.5: kr=kz=0.2                          # base plate
            elif z<3.2 and r<114.5: kr=kz=0.5                        # SB1R receive board
            elif z<3.2: kr=kz=0.2                                    # base plate rim
            elif r<44.0 and z<41.3:                                  # vault interior
                kr=kz=0.25                                           # syntactic silicone
                if 17.8<=z<23.6: kr=kz=1.2                           # absorber cell (carbonyl iron silicone)
            elif r<49.5 and z<41.3: kr=kz=0.2                        # hub wall
            elif r<52.0 and 29.2<=z<41.3: kr=kz=0.2                  # collar
            elif r<52.0 and z<44.5: kr=kz=0.2                        # roof
            elif r<52.0 and z<47.1: kr=kz=0.25                       # cap + antenna board
            elif 50.0<=r<=116.5 and 3.2<=z<28.8: kr=kz=0.2           # formers with gaps
            elif 52.6<=r<=116.1 and 29.4<=z<33.4: kr=kz=1.5          # hood: ferrite tiles in carrier
            elif 116.5<r<=119.0 and z<33.4: kr=kz=0.2                # skirt + silicone
            if kr is None: continue
            k_r[i,j]=kr; k_z[i,j]=kz
    # boards: thin high in-plane conductivity (copper planes) at the real heights
    for (z0,z1,rr,krv) in ((11.1,12.7,40.0,8.0),(27.0,28.6,39.0,17.0),(39.2,40.0,39.0,17.0)):
        for i in range(nr):
            for j in range(nz):
                if rc[i]<rr and z0<=zc[j]<z1 and not np.isnan(k_r[i,j]): k_r[i,j]=krv
    def put(z0,z1,r0,r1,Pw):
        cells=[(i,j) for i in range(nr) for j in range(nz) if r0<=rc[i]<r1 and z0<=zc[j]<z1 and not np.isnan(k_r[i,j])]
        vol=sum(math.pi*(ro[i]**2-ri[i]**2)*dz for i,j in cells)
        for i,j in cells: Q[i,j]+=Pw*math.pi*(ro[i]**2-ri[i]**2)*dz/vol
    put(11.1,15.0,0,40,P_ab); put(28.6,36.0,0,39,P_cb); put(28.6,29.6,30,36,P_damp); put(40.0,40.9,12,35,P_led)
    idx=-np.ones((nr,nz),int); act=~np.isnan(k_r); n=int(act.sum()); idx[act]=np.arange(n)
    rows=[];cols=[];vals=[]; b=np.zeros(n); diag=np.zeros(n)
    def link(a,bb,G): rows.extend([a,bb]); cols.extend([bb,a]); vals.extend([-G,-G]); diag[a]+=G; diag[bb]+=G
    for i in range(nr):
        for j in range(nz):
            if not act[i,j]: continue
            a=idx[i,j]
            if i+1<nr and act[i+1,j]:
                k1,k2=k_r[i,j],k_r[i+1,j]; link(a,idx[i+1,j],2*math.pi*ro[i]*dz*(2*k1*k2/(k1+k2))*1e-3/dr)
            if j+1<nz and act[i,j+1]:
                k1,k2=k_z[i,j],k_z[i,j+1]; link(a,idx[i,j+1],math.pi*(ro[i]**2-ri[i]**2)*(2*k1*k2/(k1+k2))*1e-3/dz)
            area_t=math.pi*(ro[i]**2-ri[i]**2)*1e-6
            if j==0: diag[a]+=h_bot*area_t; b[a]+=h_bot*area_t*Tamb
            if j+1>=nz or not act[i,j+1]: diag[a]+=h_top*area_t; b[a]+=h_top*area_t*Tamb
            if i+1>=nr or not act[i+1,j]: Ga=h_side*2*math.pi*ro[i]*dz*1e-6; diag[a]+=Ga; b[a]+=Ga*Tamb
            if i+1<nr and act[i+1,j]==False and i+1<nr and j>=0 and False: pass
            b[a]+=Q[i,j]
    A=sp.csr_matrix((vals,(rows,cols)),shape=(n,n))+sp.diags(diag)
    T=sla.spsolve(A.tocsc(),b); Tf=np.full((nr,nz),np.nan); Tf[act]=T; return Tf
def probe(T,r0,r1,z0,z1):
    s=T[(rc>=r0)&(rc<r1)][:, (zc>=z0)&(zc<z1)]; return float(np.nanmax(s))
cases={"scan (8 A, 800 Hz): damping 0.15 W, LED 0.1 W":(0.12,0.30,0.15,0.10),"boost (20 A, 400 Hz): damping 0.46 W, LED 0.25 W":(0.12,0.30,0.46,0.25),"worst: boost + LED 0.5 W":(0.12,0.30,0.46,0.50)}
OUT={}
for nm,(a,c,d,l) in cases.items():
    for Tamb in (25.0,40.0):
        T=build(a,c,d,l,Tamb); OUT[f"{nm} | ambient {int(Tamb)} C"]=dict(total_W=round(a+c+d+l,2),CB1D_parts_C=round(probe(T,0,39,28.6,36),1),damping_chain_C=round(probe(T,30,36,28.6,29.6),1),AB1_boards_C=round(probe(T,0,40,11.1,15),1),LB1_LEDs_C=round(probe(T,12,35,40,40.9),1),hub_wall_C=round(probe(T,44,49.5,10,30),1),cap_top_C=round(probe(T,0,52,46.5,47.1),1),RX_board_C=round(probe(T,0,114,0.8,3.2),1),max_C=round(float(np.nanmax(T)),1))
for k,v in OUT.items(): print(k,v)
T=build(0.12,0.30,0.46,0.25,25.0)
fig,ax=plt.subplots(figsize=(14,5)); im=ax.imshow(np.rot90(T),extent=[0,120,0,50],aspect="equal",cmap="inferno"); plt.colorbar(im,label="temperature C (ambient 25 C)"); ax.set_xlabel("r mm"); ax.set_ylabel("z mm"); ax.set_title("Head thermal map, boost mode, 1.13 W in the vault (axisymmetric finite-volume model)")
plt.tight_layout(); plt.savefig("kit_v20/SIM_THERMAL.png",dpi=90); json.dump(OUT,open("kit_v20/sim_thermal.json","w"),indent=1)
