"""PHI-FOLD 233 collapsible handle + full-system assembly (STL)."""
import numpy as np, math, os, json
import golden_cone_head as g, rodin_core_v4 as rc, phi_fold_v2 as v2
OUT="out_handle"; os.makedirs(OUT,exist_ok=True)
def box(cx,cy,cz,lx,ly,lz):
    x=np.array([-1,1])*lx/2; y=np.array([-1,1])*ly/2; z=np.array([-1,1])*lz/2
    V=np.array([[a,b,c] for a in x for b in y for c in z])+[cx,cy,cz]
    F=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    if rc.signed_volume(V,F)<0: F=F[:,::-1]
    return V,F
def tube(r_out,r_in,L,n=48):        # along +x from 0..L
    V,F=g.revolve([(r_in,0),(r_out,0),(r_out,L),(r_in,L)] if r_in>0 else [(0.01,0),(r_out,0),(r_out,L),(0.01,L)],n)
    V=V[:,[2,1,0]]*np.array([1,1,1]);  return V,F[:,::-1] if rc.signed_volume(V,F)<0 else F
def place(VF,R,t):
    V,F=VF; V2=V@R.T+t; return (V2,F if rc.signed_volume(V2,F)>0 else F[:,::-1])
ang=math.radians(35)                                     # shaft elevation
Rs=np.array([[math.cos(ang),0,-math.sin(ang)],[0,1,0],[math.sin(ang),0,math.cos(ang)]])   # local x -> up-rear
pivot=np.array([0,0,48.0])                               # yoke bolt above the hub plateau
def along(s): return pivot+Rs@np.array([s,0,0])
parts={}
parts["yoke_ears"]=[box(0,y,40,30,6,26) for y in (-21.0,21.0)]
parts["yoke_bolt_PEEK_M8"]=[place(tube(4,0,52),np.array([[0,-1,0],[1,0,0],[0,0,1]]),np.array([0,26,48]))]
parts["shaft_lower_CF_22x19x480"]=[place(tube(11,9.5,480),Rs,along(0))]
parts["shaft_middle_CF_19x16.5x430"]=[place(tube(9.4,8.2,430),Rs,along(330))]
parts["shaft_upper_CF_25x22x430"]=[place(tube(12.5,11,430),Rs,along(640))]
parts["cam_lock_collars"]=[place(tube(15,12.6,26),Rs,along(s)) for s in (470,630)]
parts["grip_EVA_34x130"]=[place(tube(17,12.6,130),Rs,along(840))]
gp=along(905)
parts["trigger_lever"]=[place(box(0,0,0,18,10,30),Rs,gp+Rs@np.array([0,0,-26]))]
parts["control_pod"]=[place(box(0,0,0,70,44,30),Rs,along(790)+Rs@np.array([0,0,28]))]
kn=along(780)+Rs@np.array([0,0,48])
parts["rotary_dial_4pos"]=[place(tube(11,0,12),np.array([[0,0,-1],[0,1,0],[1,0,0]])@np.eye(3),kn)]
parts["power_toggle"]=[place(box(0,0,0,8,6,12),Rs,along(815)+Rs@np.array([0,15,48]))]
parts["armrest_cuff"]=[place(box(0,0,0,110,70,8),Rs,along(1060)+Rs@np.array([0,0,22]))]+[place(box(0,0,0,110,6,40),Rs,along(1060)+Rs@np.array([0,s*34,40])) for s in (-1,1)]
parts["battery_4S1P_18650_pack_in_armrest"]=[place(box(0,0,0,80,42,72),Rs,along(1050)+Rs@np.array([0,0,-40]))]
for k,lst in parts.items():
    V,F=g.merge(lst); rc.write_stl(f"{OUT}/HANDLE_{k}.stl",V,F,k)
VH,FH=g.merge([p for lst in parts.values() for p in lst]); rc.write_stl(f"{OUT}/HANDLE_ASSEMBLY.stl",VH,FH,"handle")
# light head for the full-system view: low-res formers + board + skid + ferrite bay
v2.NOTCHES=False
fo=v2.Former(); Vo,Fo,_=v2.build_mesh(fo,du=0.25,narc=5,nfill=4)
sv=(v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN); v2.R_B,v2.R_I,v2.RIM_H=70.4,26.0,v2.H_IN; v2.H_IN=v2.RIM_H+(v2.R_B-v2.R_I)*v2.T_SLOPE
fh=v2.Former(); Vh,Fh,_=v2.build_mesh(fh,du=0.25,narc=5,nfill=4); v2.R_B,v2.R_I,v2.RIM_H,v2.H_IN=sv
board=g.revolve([(0.01,-2.8),(116,-2.8),(116,-0.4),(0.01,-0.4)],240); skid=g.revolve([(0.01,-6.2),(116.5,-6.2),(116.5,-3.2),(0.01,-3.2)],240)
bay=g.revolve([(22,0.5),(25,0.5),(25,33.5),(22,33.5)],120)
VS,FS_=g.merge([(Vo,Fo),(Vh,Fh),board,skid,bay,(VH,FH)]); rc.write_stl(f"{OUT}/PHIFOLD233_FULL_SYSTEM_light.stl",VS,FS_,"full")
# mass estimate
dens=dict(PA12_print=1.01*0.55, CF=1.55, EVA=0.12, ABS=1.05)
def vol(lst): return sum(rc.signed_volume(*p) for p in lst)/1000
m={"shafts (carbon fibre)":round(dens["CF"]*sum(vol(parts[k]) for k in parts if k.startswith("shaft")),0),
   "grip, pod, trigger, dial, cuff, collars, yoke (ABS/EVA)":round(1.05*sum(vol(parts[k]) for k in ("control_pod","trigger_lever","rotary_dial_4pos","power_toggle","armrest_cuff","cam_lock_collars","yoke_ears"))+0.12*vol(parts["grip_EVA_34x130"]),0),
   "battery 4S1P 18650 (4 cells + BMS)":200,
   "head: formers (PA12, 55% infill)":round(dens["PA12_print"]*(352+190),0),
   "head: Litz copper 74 m + 42 m (0.5 mm2)":round(116*0.5*8.96,0),
   "head: sensor board, skid, ferrite bay, electronics":260}
m["TOTAL"]=sum(v for k,v in m.items())
dims=dict(collapsed_length_mm=round(480+150),extended_length_mm=round(640+430+90),shaft_angle_deg=35)
json.dump(dict(mass_g=m,dims=dims),open(f"{OUT}/handle_mass_dims.json","w"),indent=1); print(json.dumps(dict(mass_g=m,dims=dims),indent=1))
