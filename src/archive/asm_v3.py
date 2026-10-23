import numpy as np, math, json
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g
from struct import unpack
K="kit"; O="kit_v3"; T=v2.T_SLOPE; zf=lambda r:13.0+(116.5-r)*T
def rd(p):
    with open(p,"rb") as f:
        f.read(80); n=unpack("<I",f.read(4))[0]; d=np.frombuffer(f.read(50*n),dtype=[("n","<f4",3),("v","<f4",(3,3)),("a","<u2")])
    V=d["v"].reshape(-1,3).astype(float); return V,np.arange(len(V)).reshape(-1,3)
def rotz(V,a):
    c,s=math.cos(a),math.sin(a); return np.c_[V[:,0]*c-V[:,1]*s,V[:,0]*s+V[:,1]*c,V[:,2]]
def band(RB,RI,RIM,zone):
    sv=(v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN,dict(v2.RHO),v2.ZONE_SEGS,v2.NOTCHES)
    v2.R_B,v2.R_I,v2.RIM_H=RB,RI,RIM; v2.H_IN=RIM+(RB-RI)*T; v2.RHO.update(heel=5.0,crown=5.0,brow=4.0,foot=4.0); v2.NOTCHES=False; v2.ZONE_SEGS=zone
    try: fm=v2.Former(); V,F,_=v2.build_mesh(fm,du=0.25,narc=5,nfill=4)
    finally:
        v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN=sv[:4]; v2.RHO.clear(); v2.RHO.update(sv[4]); v2.ZONE_SEGS,v2.NOTCHES=sv[5],sv[6]
    return rotz(V,math.radians(65)),F
P={}
P["body_outer"]=band(116.5,72.004,13.0,("brow","inner","foot")); P["body_inner"]=band(60.4,26.0,zf(60.4),("heel","rim","crown"))
V,F=rd(f"{O}/P10_head_body_ONE_PIECE.stl")
# gallery ring = the middle shell (68k tris): take triangles whose centroid radius is between 59 and 73
cen=V[F].mean(1); rr=np.hypot(cen[:,0],cen[:,1]); sel=(rr>59.5)&(rr<73.0)&(cen[:,2]<30)
P["body_ring"]=(V,F[sel])
for nm in ("P04b_trough_lid_with_gap","P05b_bay_lid_with_yoke_cable_gap","P07b_pcb_slot_rings_x3","P11_lead_and_cable_cover_strip"): P[nm[:4]]=rd(f"{O}/{nm}.stl")
for nm in ("P06_pcb_liner_sleeve","P08_bezel_rim_guard","P09_skid_plate_with_snap_arms"): P[nm[:3]]=rd(f"{K}/01_PRINTABLE_head/{nm}.stl")
for nm in ("R01_ferrite_tube_OD50_ID44_L33","R02_ferrite_cap_bottom_disc_OD44_t3","R03_ferrite_cap_top_disc_OD44_t3"): P[nm[:3]]=rd(f"{K}/02_PURCHASED_reference_models/{nm}.stl")
P["SB1"]=rd("out_board/PF233-SB1_substrate.stl")
def lift(VF,dz): return (VF[0]+np.array([0,0,dz]),VF[1])
P["ABA"]=lift(rd(f"{O}/PCB_AB1A/PF233-AB1A_board_with_components.stl"),15.8+0.8)
P["ABB"]=lift(rd(f"{O}/PCB_AB1B/PF233-AB1B_board_with_components.stl"),24.8+0.8)
P["MAIN"]=lift(g.revolve([(4.5,0.0),(20.0,0.0),(20.0,-1.6),(4.5,-1.6)],120),6.8+0.8)
Va,Fa=g.merge(list(P.values())); rc.write_stl(f"{O}/PHIFOLD233_v3_ONE_PIECE_ASSEMBLY_light.stl",Va,Fa,"asm")
dz={"P09":-60,"SB1":-35,"P08":75,"P11":90,"P05b":115,"P04b":60,"P07b":20,"P06_":35,"R01":10,"R02":-10,"R03":30,"ABA":30,"ABB":55,"MAIN":0}
dz={"P09":-60,"SB1":-35,"P08":75,"P11":92,"P05b":120,"P04b":62,"P07b":22,"P06":38,"R01":10,"R02":-10,"R03":34,"ABA":30,"ABB":58,"MAIN":-4}
parts=[lift(v,dz.get(k,0)) for k,v in P.items()]
Ve,Fe=g.merge(parts); rc.write_stl(f"{O}/PHIFOLD233_v3_ONE_PIECE_EXPLODED_light.stl",Ve,Fe,"exp")
json.dump({"frame":"z=0 flat ground-facing underside; +z toward handle","parts":list(P.keys()),"exploded_dz_mm":dz},open(f"{O}/assembly_frame_v3.json","w"),indent=1)
print("ok",len(Fa),len(P))
