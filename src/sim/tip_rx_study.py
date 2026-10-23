import numpy as np, math, json
from scipy.special import ellipk, ellipe
import phi_fold_v2 as v2, rodin_core_v4 as rc
mu0=4e-7*math.pi
src=open("band_study.py").read().split("A=0.5e-6")[0]      # reuse ring helpers + band models
exec(src)
def loop_field(cx,cy,cz,a,n,P,nseg=64):
    """Biot-Savart of an n-turn circular loop (radius a) at (cx,cy,cz) at points P (m)"""
    t=np.linspace(0,2*np.pi,nseg,endpoint=False); Q=np.stack([cx+a*np.cos(t),cy+a*np.sin(t),np.full(nseg,cz)],-1)
    d=np.roll(Q,-1,0)-Q; m=(Q+np.roll(Q,-1,0))/2
    R=P[:,None,:]-m[None]; Rn=np.linalg.norm(R,axis=-1)[...,None]
    return mu0/(4*np.pi)*n*(np.cross(d[None],R)/Rn**3).sum(1)
def S(a,sig,t):
    k=np.arange(1,80); tau=mu0*sig*a*a/(k*k*math.pi**2); return float((6/(k*k*math.pi**2)/tau*np.exp(-t/tau)).sum())
def Btx(P):  # v2A + inner band (v2C, series), per amp of series string -> use ring model on axis/off-axis
    B=np.zeros((len(P),3))
    for R_ in (TX,HUB):
        for a,zc,n in R_[::3]:
            B+=loop_field(0,0,zc,a,n*3,P,48)
    return B
# RX candidates (PCB: 4 copper layers x 12 turns per cell, spiral equivalent radius)
N_cell=48
def array(kind,z0):
    if kind=="single Ø30 loop": return [(0,0,z0,0.015,N_cell,+1)]
    if kind=="2x2 quadrupole gradiometer (cells Ø14, + - + -)":
        c=0.0085; return [(sx*c,sy*c,z0,0.007,N_cell,sx*sy) for sx in (-1,1) for sy in (-1,1)]
    if kind=="2-cell dipole gradiometer (Ø14, + -)":
        c=0.0085; return [(-c,0,z0,0.007,N_cell,+1),(c,0,z0,0.007,N_cell,-1)]
    if kind=="3x3 imaging grid (cells Ø9.5, read individually)":
        c=0.0105; return [(i*c,j*c,z0,0.0047,N_cell,1) for i in (-1,0,1) for j in (-1,0,1)]
I=10.0; Vn=1e-6; tgt={"1 g gold":(2.3e-3,1.5e7),"10 g gold":(5e-3,1.5e7)}; tdel=4e-6
res={}
places={"tip plateau (z = +34 mm)":0.034,"ground side, base centre (z = -1 mm)":-0.001}
# primary coupling: flux of TX field through each array (per TX amp) incl. 0.1 mm placement error
for pl,z0 in places.items():
    res[pl]={}
    for kind in ("single Ø30 loop","2-cell dipole gradiometer (Ø14, + -)","2x2 quadrupole gradiometer (cells Ø14, + - + -)","3x3 imaging grid (cells Ø9.5, read individually)"):
        cells=array(kind,z0)
        # primary flux (sum with signs) with a 0.1 mm lateral misplacement
        flux=0
        for (cx,cy,cz,a,n,sgn) in cells:
            g=np.linspace(-a,a,9); X,Y=np.meshgrid(g,g); m=X**2+Y**2<=a*a
            P=np.stack([X[m]+cx+1e-4,Y[m]+cy+1e-4,np.full(m.sum(),cz)],-1)
            flux+=sgn*n*Btx(P)[:,2].mean()*math.pi*a*a
        # target response: scan target laterally at depth z, take best position; channel = signed sum (or best single cell for grid)
        dep={}
        for nm,(ra,sg) in tgt.items():
            best=0
            for z in np.linspace(0.03,0.5,48):
                rr=np.linspace(0,max(0.02,z),7); ang=np.radians([0,45])
                xs=np.concatenate([rr*np.cos(a) for a in ang]); ys=np.concatenate([rr*np.sin(a) for a in ang])
                Pt=np.stack([xs,ys,np.full(len(xs),-z)],-1)
                bt=Btx(Pt)                                    # TX field at target (per amp), dipole along it
                mt=(2*math.pi*ra**3/mu0)*bt*I*S(ra,sg,tdel)   # dm/dt magnitude-equivalent
                if kind.startswith("3x3"):
                    v=max(abs(np.einsum("ij,ij->i",loop_field(cx,cy,cz,a,n,Pt),mt)).max() for (cx,cy,cz,a,n,s) in cells)
                else:
                    br=sum(s*loop_field(cx,cy,cz,a,n,Pt) for (cx,cy,cz,a,n,s) in cells)
                    v=abs(np.einsum("ij,ij->i",br,mt)).max()
                if v>Vn: best=z
            dep[nm]=round(best*1000)
        res[pl][kind]=dict(primary_flux_per_TX_amp_uWb=round(flux*1e6,4),air_depth_mm_at_4us_10A=dep)
# mono reference (main windings as RX, 10 us) from band_study
res["reference: main TX windings as RX (mono, 10 us)"]={"1 g gold":286,"10 g gold":419}
json.dump(res,open("out_phifold_v2/tip_rx_study.json","w"),indent=1); print(json.dumps(res,indent=1))
