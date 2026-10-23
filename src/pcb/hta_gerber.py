import math, csv, os, json, numpy as np
from scipy.special import ellipk, ellipe
OUT="kit_v18/HTA"; os.makedirs(OUT,exist_ok=True)
px=list(csv.DictReader(open("kit_v18/SET/02_CORE_PCB_CYLINDER/PIXEL_MAP_66.csv"))); holes=[(float(p["x_mm"]),float(p["y_mm"])) for p in px]
R_OUT,R_IN,TW=43.0,35.5,0.5
def spiral(r0,r1,th0,th1,n=400): th=np.linspace(th0,th1,n); r=r0+(r1-r0)*(th-th0)/(th1-th0); return np.c_[r*np.cos(th),r*np.sin(th)]
def clear(pts,minr=1.45): return min(np.min(np.hypot(pts[:,0]-hx,pts[:,1]-hy)) for hx,hy in holes)
def _clr(pts): return min(np.min(np.hypot(pts[:,0]-hx,pts[:,1]-hy)) for hx,hy in holes)
def _route(NT):
    azB=math.degrees(2*NT*2*math.pi)%360; b=(R_OUT*math.cos(math.radians(azB)),R_OUT*math.sin(math.radians(azB))); m=(10*math.cos(math.radians(azB)),10*math.sin(math.radians(azB)))
    return np.vstack([np.linspace(b,m,300),np.linspace(m,(6.0,-0.9),80)])
best=None
for NT in np.arange(1.80,2.0001,0.0025):
    th=np.linspace(0,NT*2*math.pi,300); r=R_OUT+(R_IN-R_OUT)*th/(NT*2*math.pi); c1=np.c_[r*np.cos(th),r*np.sin(th)]
    sc=min(_clr(_route(NT)),_clr(c1))
    if best is None or sc>best[0]: best=(sc,NT)
NT=float(best[1])
# L1: outer(43.0, az0) -> inner CCW; L2: inner -> outer CCW (same sense, fields add). turns per layer NT; end azimuth of L2 = 2*NT*360 mod 360
L1=spiral(R_OUT,R_IN,0.0,NT*2*math.pi); th_in=NT*2*math.pi; L2=spiral(R_IN,R_OUT,th_in,2*th_in)
azB=math.degrees(2*th_in)%360
# traces on inner layers to the centre pads
A_line=np.array([[R_OUT,0.0],[6.0,0.0]]); A_line[:,1]=0.9                                  # In2: along y=+0.9 from the outer via to pad A
bx,by=R_OUT*math.cos(math.radians(azB)),R_OUT*math.sin(math.radians(azB))
radial=np.array([[R_OUT*math.cos(math.radians(azB)),R_OUT*math.sin(math.radians(azB))],[10*math.cos(math.radians(azB)),10*math.sin(math.radians(azB))],[6.0,-0.9]])   # B.Cu: radial in, then to pad B
rep=dict(L1_end_radius=round(float(np.hypot(*L1[-1])),2),B_azimuth_deg=round(azB,1),min_dist_coil_to_pixel_hole_mm=round(min(clear(L1),clear(L2)),2),
         min_dist_B_route_to_pixel_hole_mm=round(clear(np.vstack([np.linspace(radial[0],radial[1],200),np.linspace(radial[1],radial[2],50)])),2),min_dist_A_route_to_pixel_hole_mm=round(clear(np.linspace(A_line[0],A_line[1],200)),2))
# inductance estimate: 4 turns as coaxial circular loops (mean radii per turn), layer gap 0.2+0.035+... = 0.55 mm between L1 and L2 copper centres
def Mloop(a,b,d):
    k2=4*a*b/((a+b)**2+d**2); k=math.sqrt(k2); return 4e-7*math.pi*math.sqrt(a*b)*((2/k-k)*ellipk(k2)-2/k*ellipe(k2))
radii=[(R_OUT+(R_IN-R_OUT)*(t+0.5)/NT) for t in range(2)]; loops=[(r*1e-3,0.0) for r in radii]+[(r*1e-3,0.55e-3) for r in radii]
L=sum((4e-7*math.pi*a*(math.log(8*a/0.25e-3)-2) if i==j else Mloop(a,b,abs(z1-z2))) for i,(a,z1) in enumerate(loops) for j,(b,z2) in enumerate(loops))
rep["inductance_estimate_uH"]=round(L*1e6,2)
# ---------------- Gerber writer (RS-274X, mm, 4.6)
def fmt(v): return "%d"%round(v*1e6)
APS={"trace":(10,TW),"pad":(11,1.6),"via":(12,0.6),"edge":(13,0.1),"maskpad":(14,1.9),"maskvia":(15,0.0)}
def gerber(path,draw):
    L_=["G04 PHI-FOLD 233 HTA board*","%FSLAX46Y46*%","%MOMM*%","%LPD*%"]+[f"%ADD{a[0]}C,{a[1]:.3f}*%" for k,a in APS.items() if a[1]>0]+["G75*"]
    draw(L_); L_.append("M02*"); open(path,"w").write("\n".join(L_)+"\n")
def stroke(L_,d,pts):
    L_.append(f"D{d}*"); L_.append(f"X{fmt(pts[0][0])}Y{fmt(pts[0][1])}D02*")
    for p in pts[1:]: L_.append(f"X{fmt(p[0])}Y{fmt(p[1])}D01*")
def flash(L_,d,p): L_.append(f"D{d}*"); L_.append(f"X{fmt(p[0])}Y{fmt(p[1])}D03*")
padA=(6.0,0.9); padB=(6.0,-0.9); viaA=(R_OUT,0.0); viaB=(bx,by); viaM=tuple(L1[-1])
def fcu(L_): stroke(L_,10,L1); flash(L_,12,viaA); flash(L_,12,viaM)
def in1(L_): stroke(L_,10,L2); flash(L_,12,viaM); flash(L_,12,viaB)
def in2(L_): stroke(L_,10,A_line); flash(L_,12,viaA); flash(L_,11,padA)
def bcu(L_): stroke(L_,10,radial); flash(L_,12,viaB); flash(L_,11,padB)
def fmask(L_): flash(L_,14,padA); flash(L_,14,padB)
def edge(L_):
    t=np.linspace(0,2*math.pi,361); stroke(L_,13,np.c_[45*np.cos(t),45*np.sin(t)]); t2=np.linspace(0,2*math.pi,100); stroke(L_,13,np.c_[4*np.cos(t2),4*np.sin(t2)])
    for hx,hy in holes: t3=np.linspace(0,2*math.pi,41); stroke(L_,13,np.c_[hx+0.85*np.cos(t3),hy+0.85*np.sin(t3)])
gerber(f"{OUT}/PF233-HTA-F_Cu.gbr",fcu); gerber(f"{OUT}/PF233-HTA-In1_Cu.gbr",in1); gerber(f"{OUT}/PF233-HTA-In2_Cu.gbr",in2); gerber(f"{OUT}/PF233-HTA-B_Cu.gbr",bcu)
gerber(f"{OUT}/PF233-HTA-F_Mask.gbr",fmask); gerber(f"{OUT}/PF233-HTA-B_Mask.gbr",fmask); gerber(f"{OUT}/PF233-HTA-Edge_Cuts.gbr",edge)
ex=lambda tools,name: open(f"{OUT}/{name}","w").write("M48\nMETRIC,TZ\n"+"".join(f"T{i+1}C{d:.3f}\n" for i,(d,_) in enumerate(tools))+"%\nG90\n"+"".join(f"T{i+1}\n"+"".join(f"X{x:.3f}Y{y:.3f}\n" for x,y in pts) for i,(d,pts) in enumerate(tools))+"M30\n")
ex([(0.3,[viaA,viaB,viaM]),(0.8,[padA,padB])],"PF233-HTA-PTH.drl"); ex([(1.7,holes),(8.0,[(0.0,0.0)])],"PF233-HTA-NPTH.drl")
with open(f"{OUT}/PF233-HTA_BOM.csv","w",newline="") as f: w=csv.writer(f); w.writerow(["Qty","Ref","Value","Note"]); w.writerow([1,"PCB","4-layer 1.6 mm D90 FR-4, 1 oz outer/inner, ENIG, mask both sides","no components; the coil is the copper"]); w.writerow([1,"wires","twisted pair AWG30, 130 mm","solder to pads A and B, down the D8 port to JHTA on CB1D"])
json.dump(dict(spec=dict(board="D90 x 1.6, 4 layers (F.Cu, In1, In2, B.Cu), trace 0.5, via 0.3/0.6, 66 NPTH 1.7 (light pipes), centre NPTH 8.0, 2 PTH pads 0.8/1.6",coil="2 x 1.95 turns, r35.5-43.0, F.Cu inward then In1 outward (same sense, 3.9 turns total)"),**rep),open(f"{OUT}/hta_report.json","w"),indent=1); print(json.dumps(rep))
# preview
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(8,8)); ax.set_aspect(1); ax.add_patch(plt.Circle((0,0),45,fc="#0b3d2e",ec="w"))
ax.plot(*L1.T,color="#f2c94c",lw=1.6,label="F.Cu coil"); ax.plot(*L2.T,color="#ffb347",lw=1.6,label="In1 coil"); ax.plot(*A_line.T,color="#7fd4ff",lw=1.2,label="In2 lead A"); ax.plot(*radial.T,color="#ff7f7f",lw=1.2,label="B.Cu lead B")
for hx,hy in holes: ax.add_patch(plt.Circle((hx,hy),0.85,fc="k",ec="w",lw=0.3))
ax.add_patch(plt.Circle((0,0),4,fc="k",ec="w")); [ax.add_patch(plt.Circle(p,0.8,fc="#e8f1ff")) for p in (padA,padB)]; ax.set_xlim(-47,47); ax.set_ylim(-47,47); ax.legend(loc="lower right",fontsize=7); ax.set_title("PF233-HTA preview (from the Gerber geometry)",fontsize=9); fig.savefig(f"{OUT}/PF233-HTA_preview.png",dpi=100)
