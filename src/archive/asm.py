import numpy as np, math, json, os
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g
from struct import unpack
K="kit"
def rd(p):
    with open(p,"rb") as f:
        f.read(80); n=unpack("<I",f.read(4))[0]; d=np.frombuffer(f.read(50*n),dtype=[("n","<f4",3),("v","<f4",(3,3)),("a","<u2")])
    V=d["v"].reshape(-1,3).astype(float); return V,np.arange(len(V)).reshape(-1,3)
v2.NOTCHES=False; T=v2.T_SLOPE
fo=v2.Former(); Vo,Fo,_=v2.build_mesh(fo,du=0.25,narc=5,nfill=4)
sv=(v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN,dict(v2.RHO)); v2.R_B,v2.R_I,v2.RIM_H=60.4,26.0,13+(116.5-60.4)*T; v2.H_IN=v2.RIM_H+(60.4-26.0)*T; v2.RHO.update(heel=5.0,crown=5.0,brow=4.0,foot=4.0)
fh=v2.Former(); Vh,Fh,_=v2.build_mesh(fh,du=0.25,narc=5,nfill=4)
P={"P01":(Vo,Fo),"P02":(Vh,Fh)}
for nm in ("P03_gallery_ring_lead_trough","P04_gallery_trough_lid","P05_bay_lid_with_yoke","P06_pcb_liner_sleeve","P07_pcb_slot_rings_x2","P08_bezel_rim_guard","P09_skid_plate_with_snap_arms"):
    P[nm[:3]]=rd(f"{K}/01_PRINTABLE_head/{nm}.stl")
for nm in ("R01_ferrite_tube_OD50_ID44_L33","R02_ferrite_cap_bottom_disc_OD44_t3","R03_ferrite_cap_top_disc_OD44_t3","R04_electronics_boards_x2_OD40"):
    P[nm[:3]]=rd(f"{K}/02_PURCHASED_reference_models/{nm}.stl")
P["R05"]=rd("out_board/PF233-SB1_substrate.stl")
def sh(VF,dz): return (VF[0]+np.array([0,0,dz]),VF[1])
Va,Fa=g.merge(list(P.values())); rc.write_stl(f"{K}/05_assembly/PHIFOLD233_v2C_FINAL_ASSEMBLY_light.stl",Va,Fa,"asm")
dz={"P09":-60,"R05":-35,"P08":75,"P03":40,"P04":55,"P05":95,"P06":45,"P07":45,"R01":20,"R02":-8,"R03":28,"R04":45}
parts=[sh(v,dz.get(k,0)) for k,v in P.items()]
Ve,Fe=g.merge(parts); rc.write_stl(f"{K}/05_assembly/PHIFOLD233_v2C_FINAL_EXPLODED_light.stl",Ve,Fe,"exp")
json.dump({"frame":"z=0 flat ground-facing underside of both formers; z up toward handle; axis = z",
 "exploded_z_offsets_mm":dz},open(f"{K}/05_assembly/assembly_frame.json","w"),indent=1)
print("ok",len(Fa),len(Fe))
