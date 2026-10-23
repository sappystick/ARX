import numpy as np, math, json
exec(open("tip_rx_study.py").read().split("# RX candidates")[0])
I=10.0; Vn=1e-6; tdel=4e-6
def grad_cells(D,z0):
    a=D/4*0.95; c=D/4; return [(-c,0,z0,a,48,+1),(c,0,z0,a,48,-1)]
out={}
for D in (0.032,0.044,0.050):
    cells=grad_cells(D,-0.0015)
    flux=0
    for (cx,cy,cz,a,n,sgn) in cells:
        g_=np.linspace(-a,a,11); X,Y=np.meshgrid(g_,g_); m=X**2+Y**2<=a*a
        P=np.stack([X[m]+cx+1e-4,Y[m]+cy+1e-4,np.full(m.sum(),cz)],-1)
        flux+=sgn*n*Btx(P)[:,2].mean()*math.pi*a*a
    single=48*Btx(np.array([[0,0,-0.0015]]))[0,2]*math.pi*(D/2)**2
    dep={}
    for nm,(ra,sg) in {"1 g gold":(2.3e-3,1.5e7),"10 g gold":(5e-3,1.5e7)}.items():
        best=0
        for z in np.linspace(0.03,0.5,48):
            rr=np.linspace(0,max(0.02,z),7); Pt=np.stack([rr,0*rr,np.full(7,-z)],-1)
            mt=(2*math.pi*ra**3/mu0)*Btx(Pt)*I*S(ra,sg,tdel)
            br=sum(s*loop_field(cx,cy,cz,a,n,Pt) for (cx,cy,cz,a,n,s) in cells)
            if abs(np.einsum("ij,ij->i",br,mt)).max()>Vn: best=z
        dep[nm]=round(best*1000)
    out[f"Ø{D*1000:.0f} mm"]=dict(rejection_vs_plain_loop=round(abs(single/flux) if flux else 1e9),depth_mm=dep)
print(json.dumps(out,indent=1))
