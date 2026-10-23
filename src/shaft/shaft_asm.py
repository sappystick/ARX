import numpy as np, math, json
import rodin_core_v4 as rc, golden_cone_head as g
from struct import unpack
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import shaft_build as S
OUT="kit_v4/SHAFT"
def rd(p):
    with open(p,"rb") as f:
        f.read(80); n=unpack("<I",f.read(4))[0]; d=np.frombuffer(f.read(50*n),dtype=[("n","<f4",3),("v","<f4",(3,3)),("a","<u2")])
    V=d["v"].reshape(-1,3).astype(float); return V,np.arange(len(V)).reshape(-1,3)
def T(VF,dx=0,dy=0,dz=0): return (VF[0]+np.array([dx,dy,dz]),VF[1])
def cyl(r,z0,z1,cx,cy=0,m=48): return S.tube(r,0.01,z0,z1,cx,cy,m)
P={}
z=0.0; P["front_cap"]=T(rd(f"{OUT}/SH05_front_cap_cartridge_entry.stl"),dz=z); z+=38.0
for k in (1,2,3): P[f"battery{k}"]=T(rd(f"{OUT}/SH0{k}_battery_segment_165.stl"),dz=z); z+=165.0
P["electronics"]=T(rd(f"{OUT}/SH04_electronics_segment_232.stl"),dz=z); z_e=z; z+=232.0
P["rear_cap"]=T(rd(f"{OUT}/SH06_rear_cap_cable_exit.stl"),dz=z); total=z+30+12
# cartridges: plug end at electronics bulkhead (z_e+3), 485 mm long toward the head
for sx in (-1,1):
    zc0=z_e+3-455-30
    for i in range(7): P[f"cell{sx}_{i}"]=cyl(9.3,zc0+i*65.0,zc0+i*65.0+64.5,sx*S.BORE_X)
    for i in range(4): P[f"sleeve{sx}_{i}"]=T(rd(f"{OUT}/CT01_cartridge_sleeve_segment_121.stl"),dx=sx*S.BORE_X,dz=zc0-6+i*121.0)
    P[f"plug{sx}"]=T(rd(f"{OUT}/CT02_cartridge_contact_plug.stl"),dx=sx*S.BORE_X,dz=z_e+3-30+0)
    P[f"rearcap{sx}"]=T(rd(f"{OUT}/CT03_cartridge_rear_cap.stl"),dx=sx*S.BORE_X,dz=zc0-12)
# boards (PM1 upper, PB1 lower) from their component STLs; board frame y->shaft z, board z->shaft y
def board(path,L,ysign,ybase):
    V,F=rd(path); V=V.copy(); x=V[:,0]; yb=V[:,1]; zb=V[:,2]
    out=np.c_[x, ybase+ysign*(zb+0.8+3.5), z_e+8+(yb+L/2)]    # board plane at ybase+/-(sled+standoff)
    F2=F if ysign>0 else F[:,::-1]; return out,F2
P["PM1"]=board("kit_v4/PM1/PF233-PM1_board_with_components.stl",136.0,+1,1.2)
P["PB1"]=board("kit_v4/PB1/PF233-PB1_board_with_components.stl",224.0,-1,-1.2)
P["sled_PM1"]=T(rd(f"{OUT}/SL01_sled_PM1_136.stl"),dy=2.0,dz=z_e+8+69)
Vs,Fs=g.merge(list(P.values())); rc.write_stl(f"{OUT}/SPINE_ASSEMBLY_light.stl",Vs,Fs,"spine")
# --------------- fit report
fit=dict(cartridge_OD_with_heatshrink_mm=21.2+0.4, bore_mm=S.BORE_D, radial_clearance_mm=round((S.BORE_D-21.6)/2,2),
         compartment_height_mm=round((36.0-2.4)/2,2), stack_PM1_mm=dict(sled=1.5,standoff=2.0,board=1.6,tallest_part_can=10.5,total=15.6),
         stack_ok=bool(15.6<(36.0-2.4)/2), spine_length_mm=round(total,1), envelope_mm=[S.W,S.H], cartridge_length_mm=485)
json.dump(fit,open(f"{OUT}/spine_fit_check.json","w"),indent=1); print(json.dumps(fit))
# --------------- cross-sections
fig,ax=plt.subplots(1,2,figsize=(13,4.6))
def draw(a,title,mode):
    o=S.rrect(S.W,S.H,S.RR); a.fill(o[:,0],o[:,1],fc="#d6dbdf",ec="k"); i=S.rrect(S.IW,36.0,15.0); a.fill(i[:,0],i[:,1],fc="w",ec="k")
    if mode=="bat":
        for sx in (-1,1):
            a.add_patch(plt.Circle((sx*S.BORE_X,0),S.BORE_D/2+2.0,fc="#aeb6bf",ec="k")); a.add_patch(plt.Circle((sx*S.BORE_X,0),S.BORE_D/2,fc="w",ec="k")); a.add_patch(plt.Circle((sx*S.BORE_X,0),9.3,fc="#2e86c1",ec="k"))
            a.text(sx*S.BORE_X,0,"cartridge\n7S 18650",ha="center",va="center",fontsize=7,color="w")
        a.add_patch(plt.Rectangle((-1.2,-18),2.4,36,fc="#e67e22")); a.text(0,-16.5,"foil\nseptum",ha="center",fontsize=6)
        a.add_patch(plt.Rectangle((-3.9,-6),7.8,12,fc="#fdebd0",ec="k")); a.text(0,0,"cable\nraceway",ha="center",va="center",fontsize=6)
    else:
        a.add_patch(plt.Rectangle((-26,-1.2),52,2.4,fc="#e67e22")); a.text(0,0,"foil septum",ha="center",va="center",fontsize=6,color="w")
        a.add_patch(plt.Rectangle((-14,2.7),28,1.6,fc="#1e8449")); a.add_patch(plt.Rectangle((-14,4.3),28,10.5,fc="#7fb3d5",alpha=.8)); a.text(0,9.5,"PM1 (components up)",ha="center",fontsize=7)
        a.add_patch(plt.Rectangle((-14,-4.3),28,1.6,fc="#1e8449")); a.add_patch(plt.Rectangle((-14,-14.8),28,10.5,fc="#f5b7b1",alpha=.8)); a.text(0,-9.5,"PB1 (components down)",ha="center",fontsize=7)
    a.set_aspect("equal"); a.set_title(title,fontsize=9); a.set_xlim(-32,32); a.set_ylim(-23,23)
draw(ax[0],"Battery segment (x3): two isolated cartridge chambers","bat"); draw(ax[1],"Electronics segment: PM1 and PB1 in separate shielded compartments","el")
fig.tight_layout(); fig.savefig(f"{OUT}/spine_cross_sections.png",dpi=130); print("ok")
