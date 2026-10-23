import math, json, pickle, numpy as np, os
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
OUT="kit_v7/CASSETTES"; os.makedirs(OUT,exist_ok=True); os.makedirs("kit_v7/CASSETTES_LOW",exist_ok=True)
exec(open("cass_v7.py").read().split("def dens(")[0].split("LOD = sys.argv")[0])    # imports only
R_RIM,R_IN,PN,ZRX,HMAX=116.5,52.0,3.0,3.2,44.5
s=0.34
for _ in range(50): s=(HMAX-ZRX-6*PN*math.sqrt(1+s*s))/(R_RIM-R_IN)
TV=PN/math.cos(math.atan(s)); RP=53.8
def circ(r,m=96,cx=0.0,cy=0.0): t=np.linspace(0,2*np.pi,m,endpoint=False); return np.c_[cx+r*np.cos(t),cy+r*np.sin(t)]
def ring(outer,inner,z0,z1):
    m=len(outer); V=np.concatenate([np.c_[outer,np.full(m,z0)],np.c_[outer,np.full(m,z1)],np.c_[inner,np.full(m,z0)],np.c_[inner,np.full(m,z1)]]); O0,O1,I0,I1=(np.arange(m)+k*m for k in range(4)); n=np.roll(np.arange(m),-1); F=[]
    for i in range(m):
        j=n[i]; F+=[[O0[i],O0[j],O1[j]],[O0[i],O1[j],O1[i]],[I0[j],I0[i],I1[i]],[I0[j],I1[i],I1[j]],[O0[j],O0[i],I0[i]],[O0[j],I0[i],I0[j]],[O1[i],O1[j],I1[j]],[O1[i],I1[j],I1[i]]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def extrude(poly,z0,z1):
    P=np.asarray(poly); m=len(P); T=tri2d(P)
    ar=(P[:,0]*np.roll(P[:,1],-1)-np.roll(P[:,0],-1)*P[:,1]).sum()
    V=np.concatenate([np.c_[P,np.full(m,z0)],np.c_[P,np.full(m,z1)]]); F=[]
    for t in T:
        F.append([m+t[0],m+t[1],m+t[2]] if ar>0 else [m+t[0],m+t[2],m+t[1]]); F.append([t[0],t[2],t[1]] if ar>0 else [t[0],t[1],t[2]])
    for i in range(m): j=(i+1)%m; F+=[[i,j,m+j],[i,m+j,m+i]] if ar>0 else [[i,m+j,j],[i,m+i,m+j]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def post_profile(r=2.5,nd=1.2,w=1.4,m=120):
    pts=[]
    for a in np.linspace(0,2*np.pi,m,endpoint=False):
        rr=r
        for c in (0,np.pi/2,np.pi,1.5*np.pi):
            da=abs((a-c+np.pi)%(2*np.pi)-np.pi)
            if da*r<w/2: rr=r-nd
        pts.append((rr*math.cos(a),rr*math.sin(a)))
    return np.array(pts)
rep={}
def emit(name,shells,note=""):
    bad=sum(rc.edge_manifold_check(F)[1] for V,F in shells); V,F=g.merge(shells)
    for d in ("kit_v7/CASSETTES","kit_v7/CASSETTES_LOW"): rc.write_stl(f"{d}/{name}.stl",V,F,name)
    rep[name]=dict(tris=int(len(F)),nonmanifold_edges=int(bad),bbox=[round(float(x),1) for x in (*V.min(0),*V.max(0))],note=note)
ztop_post=ZRX+6*TV+s*(R_RIM-RP)+4.0
for nm,angs in (("TX",(90,210,330)),("RX",(30,150,270))):
    for i,a in enumerate(angs):
        V,F=extrude(post_profile(),ZRX,ztop_post); V=V+[RP*math.cos(math.radians(a)),RP*math.sin(math.radians(a)),0]; emit(f"POST_{nm}_{i+1}_at_{a}deg",[(V,F)],"D5 guide post, 4 open wire channels 1.4 x 1.2 mm, rests on the RX board; length %.1f"%(ztop_post-ZRX))
# vault tube + roof integrated with L1 (print L1 with these fused), floor plate separate
emit("L1_vault_tube_and_roof",[ring(circ(49.5),circ(46.5),6.0,41.3),ring(circ(52.0),circ(10.0),41.3,44.5)],"PCB housing hung under the top cassette: tube r46.5-49.5, roof with D20 gland/fill port; fuse to L1; inner height 35.3 mm")
emit("V2_vault_floor_plate",[ring(circ(49.5),circ(8.0),3.4,6.0)],"floor seat for the ferrite/nanocrystalline bottom plate")
emit("L7_RX_tray_cassette",[ring(circ(116.5),circ(5.0),0.0,0.8),ring(circ(116.5),circ(114.5),0.0,ZRX)],"RX tray: 0.8 mm floor, PCB recess D229 x 2.4 mm for the SB1R receive board (rim wall 2 mm); open back; no metal in the tray")
# ---------------- physics from the generated winding paths
P=pickle.load(open("kit_v7/CASSETTES_LOW/paths.pkl","rb")); mu0=4e-7*math.pi
zt=lambda k,r: ZRX+(6-k)*TV+s*(R_RIM-r)+TV
paths3={}
for k in range(1,7):
    a,b,la,lb=P[k]; xy=np.vstack([a,b]); r=np.hypot(xy[:,0],xy[:,1]); z=zt(k,r)-1.3+0.6; paths3[k]=np.c_[xy,z]*1e-3
def Bz(path,pt,dec=4):
    p=path[::dec]; d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2; rr=pt-m; rn=np.linalg.norm(rr,axis=1)[:,None]; return (mu0/(4*np.pi)*np.sum(np.cross(d,rr)/rn**3,axis=0))[2]
W={k:float(np.sum(np.linalg.norm(np.diff(paths3[k],axis=0),axis=1))) for k in paths3}
depths=(0.1,0.2,0.3); Bk={k:[Bz(paths3[k],np.array([0,0,-d])) for d in depths] for k in paths3}
zf=lambda r:13+(116.5-r)*0.359
cur=[(74+i*5.7,zf(74+i*5.7)-dz) for i in range(8) for dz in (1.0,3.4)]
Bb=[sum(mu0*(r*1e-3)**2/(2*((r*1e-3)**2+(d+h*1e-3)**2)**1.5) for r,h in cur) for d in depths]; Wb=sum(2*math.pi*r*1e-3 for r,h in cur)
tot=[sum(Bk[k][i] for k in Bk) for i in range(3)]; Wt=sum(W.values())
Fb=[Bb[i]/Wb for i in range(3)]
# inductance and mutual (Neumann on decimated segments)
def seg(path,dec=8): p=path[::dec]; d=np.diff(p,axis=0); return (p[:-1]+p[1:])/2,d
S={k:seg(paths3[k]) for k in paths3}; a_w=0.6e-3; gm=0.7788*a_w
def M(k,l):
    m1,d1=S[k]; m2,d2=S[l]; tot_=0.0
    for i0 in range(0,len(m1),400):
        r=np.linalg.norm(m1[i0:i0+400,None,:]-m2[None,:,:],axis=2); 
        if k==l: r=np.sqrt(r**2+gm**2)
        tot_+=np.sum((d1[i0:i0+400]@d2.T)/r)
    return 1e-7*tot_
L={}; Mx=np.zeros((6,6))
for k in range(1,7):
    for l in range(k,7):
        v=M(k,l)
        if k==l: lens=np.linalg.norm(S[k][1],axis=1); v+=float(np.sum(mu0*lens/(2*math.pi)*(np.log(2*lens/a_w)-0.75)))
        Mx[k-1,l-1]=Mx[l-1,k-1]=v
Ld=np.diag(Mx).copy(); kc=Mx/np.sqrt(np.outer(Ld,Ld))
res=dict(stack=dict(slope_deg=round(math.degrees(math.atan(s)),2),layer_thickness_vertical_mm=round(TV,2),rim_height_mm=round(ZRX+6*TV,1),opening_top_mm=HMAX,post_length_mm=round(ztop_post-ZRX,1)),
  wire_per_layer_m=[round(W[k],2) for k in W],total_wire_m=round(Wt,1),
  Bz_uT_per_A_single_layer_at_100_200_300mm=[[round(x*1e6,2) for x in Bk[k]] for k in (1,3,6)],
  all_six_in_series_Bz_uT_per_A=[round(x*1e6,2) for x in tot],
  per_wire_vs_current_band=[round((tot[i]/Wt)/Fb[i],2) for i in range(3)],
  single_layer_vs_all_copper_vs_current_band=[round((Bk[6][i]/Wt)/Fb[i],2) for i in range(3)],
  self_inductance_uH_per_layer=[round(x*1e6,1) for x in Ld],coupling_k_adjacent=[round(kc[i,i+1],2) for i in range(5)],coupling_k_L1_L6=round(kc[0,5],2),
  all_six_series_L_uH=round(float(Mx.sum())*1e6,0),all_six_parallel_L_uH=round(float(1/np.sum(np.linalg.inv(Mx)))*1e6,1))
json.dump(dict(parts=rep,physics=res),open("kit_v7/cassette_parts_and_physics.json","w"),indent=1); print(json.dumps(res,indent=1)); print({k:(v["nonmanifold_edges"],v["bbox"]) for k,v in rep.items()})
