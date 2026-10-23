import numpy as np, math
from scipy.special import ellipk, ellipe
mu0=4e-7*math.pi
def Bz_axis(r,d): return mu0*r*r/(2*(r*r+d*d)**1.5)                   # per amp, filament radius r, axial distance d
def M(r1,r2,d):
    k2=4*r1*r2/((r1+r2)**2+d*d); k=math.sqrt(k2); return mu0*math.sqrt(r1*r2)*((2/k-k)*ellipk(k2)-2/k*ellipe(k2))
def Lself(r,a=0.6e-3): return mu0*r*(math.log(8*r/a)-2)
def zf(r): return 13+(116.5-r)*0.359
Z=[0.100,0.200,0.300]
def metrics(fil):                                                       # fil = list of (r_mm, h_mm)
    r=np.array([f[0] for f in fil])*1e-3; h=np.array([f[1] for f in fil])*1e-3; W=2*np.pi*r.sum()
    B=[sum(Bz_axis(ri,z+hi) for ri,hi in zip(r,h)) for z in Z]
    L=sum(Lself(ri) for ri in r)+sum(M(r[i],r[j],abs(h[i]-h[j]))*2 for i in range(len(r)) for j in range(i+1,len(r)))
    return dict(B_uT_per_A=[round(b*1e6,2) for b in B],F=[b/W for b in B],L_uH=L*1e6,W_m=W)
cur=[(74+k*5.7,zf(74+k*5.7)-dz) for k in range(8) for dz in (1.0,3.4)]
rim=[(116.5-1.3-c*2.6,1.3+rw*2.6) for c in range(4) for rw in range(5)]
rim=sorted(rim,key=lambda f:(-f[0]+f[1]*0.01))[:16]
rim_out=[(r+4.0,h) for r,h in rim]                                       # same block moved 4 mm outward onto the bezel
band2=[(116.5-1.3-c*2.6,1.3+rw*2.6) for c in range(2) for rw in range(8)]
res={}
base=metrics(cur)
def row(name,m):
    res[name]=dict(B_uT_per_A=m["B_uT_per_A"],per_wire_vs_current=[round(m["F"][i]/base["F"][i],2) for i in range(3)],per_amp_vs_current=[round(m["B_uT_per_A"][i]/base["B_uT_per_A"][i],2) for i in range(3)],L_vs_current=round(m["L_uH"]/base["L_uH"],2),wire_m=round(m["W_m"],2))
row("current band (8 radial x 2 stacked, 16 turns)",base); row("rim block 4 x 4 (r 105-115)",metrics(rim)); row("rim column 2 x 8 (r 110-115, 21 mm tall)",metrics(band2)); row("rim block moved 4 mm out (bezel)",metrics(rim_out))
# petals / flower of life by numeric Biot-Savart on axis
def loop_Bz(xc,yc,rho,z,n=360):
    t=np.linspace(0,2*np.pi,n,endpoint=False); x=xc+rho*np.cos(t); y=yc+rho*np.sin(t); dx=-rho*np.sin(t)*2*np.pi/n; dy=rho*np.cos(t)*2*np.pi/n
    rx,ry,rz=-x,-y,z*np.ones(n); r3=(rx**2+ry**2+rz**2)**1.5
    return (mu0/(4*np.pi))*np.sum((dx*ry-dy*rx)/r3)
def petal(cs,rho,h=3e-3): 
    W=sum(2*np.pi*rho for _ in cs); B=[sum(loop_Bz(x,y,rho,z+h) for x,y in cs) for z in Z]; return B,W
for name,N,rho,Rc in (("8 petals r38.5 on ring 75.5",8,0.0385,0.0755),):
    cs=[(Rc*math.cos(2*math.pi*k/N),Rc*math.sin(2*math.pi*k/N)) for k in range(N)]; B,W=petal(cs,rho)
    res[name]=dict(B_uT_per_A=[round(b*1e6,2) for b in B],per_wire_vs_current=[round((B[i]/W)/base["F"][i],2) for i in range(3)],wire_m=round(W,2))
# flower of life: centre + 6 + 12 circles, spacing = radius, outer extent 3r=116.5 -> r=38.8
r=0.0388; cs=[(0,0)]+[(r*math.cos(math.pi/3*k),r*math.sin(math.pi/3*k)) for k in range(6)]
cs+=[(2*r*math.cos(math.pi/3*k),2*r*math.sin(math.pi/3*k)) for k in range(6)]+[(math.sqrt(3)*r*math.cos(math.pi/3*k+math.pi/6),math.sqrt(3)*r*math.sin(math.pi/3*k+math.pi/6)) for k in range(6)]
B,W=petal(cs,r); res["flower of life 19 circles r38.8, all same sense"]=dict(B_uT_per_A=[round(b*1e6,2) for b in B],per_wire_vs_current=[round((B[i]/W)/base["F"][i],2) for i in range(3)],wire_m=round(W,2))
import json; print(json.dumps(res,indent=1)); print("baseline L_uH (16 series turns, lumped)",round(base["L_uH"],1),"B",base["B_uT_per_A"])
