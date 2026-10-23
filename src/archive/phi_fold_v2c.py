"""PHI-FOLD 233 v2C: v2A outer golden band + grooved inner tapered TX band (hub)
+ ferrite-shielded electronics bay.  Hub band: r 26.0 - 70.4, same golden slope,
continuous face with the outer band, double-stacked 1.2 mm Litz, 4 sections."""
import numpy as np, math, json, os
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g, phi_fold_former as pf
out="out_phifold_v2"
def with_hub_globals(fn):
    sv=(v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN,dict(v2.RHO))
    v2.R_B,v2.R_I,v2.RIM_H=70.4,26.0,v2.H_IN; v2.H_IN=v2.RIM_H+(v2.R_B-v2.R_I)*v2.T_SLOPE
    v2.RHO.update(heel=5.0,crown=5.0,brow=4.0,foot=4.0); v2.NOTCHES=False
    try: return fn()
    finally: v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN=sv[:4]; v2.RHO.clear(); v2.RHO.update(sv[4])
rep={}
def build():
    fm=v2.Former(); V,F,meta=v2.build_mesh(fm); W,_=v2.wires(fm)
    return fm,V,F,meta,W
fm,V,F,meta,W=with_hub_globals(build)
gd,bad=rc.edge_manifold_check(F)
rc.write_stl(f"{out}/PHIFOLD233v2C_inner_TX_band_hub.stl",V,F,"hub_band")
rep["hub_band"]=dict(triangles=len(F),nonmanifold_edges=bad,min_pitch=float(meta["pitch"].min()),
                     turns_per_circuit=fm.turns,turns_per_section=2*fm.turns,total_turns=8*fm.turns)
Lw=sum(np.linalg.norm(np.diff(np.vstack([q,q[:1]]),axis=0),axis=1).sum() for q in W[0])
rep["hub_band"]["copper_per_section_m"]=Lw/1000
Rb=[]
for q in W[0]:
    a,b,c=np.roll(q,1,0),q,np.roll(q,-1,0)
    Rb.append(np.linalg.norm(b-a,axis=1)*np.linalg.norm(c-b,axis=1)*np.linalg.norm(c-a,axis=1)/np.maximum(2*np.linalg.norm(np.cross(b-a,c-a),axis=1),1e-15))
rep["hub_band"]["min_bend_mm"]=float(np.concatenate(Rb).min())
Vt,Ft=g.merge([rc.tube_mesh(q[::2],v2.WIRE_OD/2,8) for sec in W for q in sec])
rc.write_stl(f"{out}/PHIFOLD233v2C_inner_band_windings.stl",Vt,Ft,"hubw")
# ferrite electronics bay: MnZn tube OD 50 / ID 44 (3 mm wall), with top and bottom caps, 8 mm cable hole
H=34.0
tube=g.revolve([(22.0,0.5),(25.0,0.5),(25.0,H-0.5),(22.0,H-0.5)],360)
capB=g.revolve([(4.0,0.5),(22.0,0.5),(22.0,3.5),(4.0,3.5)],360)
capT=g.revolve([(4.0,H-3.5),(22.0,H-3.5),(22.0,H-0.5),(4.0,H-0.5)],360)
for nm,(a,b) in (("ferrite_tube",tube),("ferrite_cap_bottom",capB),("ferrite_cap_top",capT)):
    rc.write_stl(f"{out}/PHIFOLD233v2C_{nm}.stl",a,b,nm)
# electronics stack placeholder (2 boards, 40 mm) for visual
pcb=[g.revolve([(4.5,z0),(20.5,z0),(20.5,z0+1.6),(4.5,z0+1.6)],180) for z0 in (10.0,20.0)]
# assembly with v2A outer former + windings + X/Y + skid
import glob
from struct import unpack
def read_stl(p):
    with open(p,"rb") as f:
        f.read(80); n=unpack("<I",f.read(4))[0]
        d=np.frombuffer(f.read(50*n),dtype=[("n","<f4",3),("v","<f4",(3,3)),("a","<u2")])
    Vv=d["v"].reshape(-1,3).astype(float); return Vv,np.arange(len(Vv)).reshape(-1,3)
outer=read_stl(f"{out}/PHIFOLD233v2_A_gallery_golden_band_former.stl")
outer_w=read_stl(f"{out}/PHIFOLD233v2_A_gallery_windings_ABCD_2layer.stl")
xy=[rc.tube_mesh(P,0.4,6) for ax,zz in (("X",-1.2),("Y",-2.4)) for P in pf.figure8(ax,zz)]
skid=g.revolve([(0.01,-6.2),(v2.R_B,-6.2),(v2.R_B,-3.2),(0.01,-3.2)],360)
rc.write_stl(f"{out}/PHIFOLD233v2C_ASSEMBLY.stl",*g.merge([outer,outer_w,(V,F),(Vt,Ft),tube,capB,capT]+pcb+[g.merge(xy),skid]),"v2C")
json.dump(rep,open(f"{out}/PHIFOLD233v2C_spec.json","w"),indent=1,default=float)
print(json.dumps(rep,indent=1,default=float))
