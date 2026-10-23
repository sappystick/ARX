import math, csv, json, glob, os, struct, numpy as np
OUT="kit_v18/MFG"; os.makedirs(OUT,exist_ok=True)
# ============ 1. liner cut patterns (DXF, mm) ============
ln=["0","SECTION","2","ENTITIES"]
def L(x0,y0,x1,y1,layer): ln.extend(["0","LINE","8",layer,"10",f"{x0:.3f}","20",f"{y0:.3f}","30","0.0","11",f"{x1:.3f}","21",f"{y1:.3f}","31","0.0"])
def R(x,y,w,h,layer): [L(*s,layer) for s in ((x,y,x+w,y),(x+w,y,x+w,y+h),(x+w,y+h,x,y+h),(x,y+h,x,y))]
def C(x,y,r,layer): ln.extend(["0","CIRCLE","8",layer,"10",f"{x:.3f}","20",f"{y:.3f}","30","0.0","40",f"{r:.3f}"])
CIRC=2*math.pi*40.7+3.0; rows=[("piece","cup","size_mm","qty","note")]; y=0.0
cups=[("A",5.8),("B",5.8),("CD",14.4)]
for nm,h in cups:
    R(0,y,CIRC,h,f"CUP_{nm}_WALL"); rows.append(("wall strip",nm,f"{CIRC:.1f} x {h}",1,"foil / graphite / ribbon, 3 mm overlap"))
    if nm=="CD":
        xs=CIRC/2 - 1.5; R(xs-4,y+1.2,8,3.0,f"CUP_{nm}_CUT")                       # TX-lead wall slot (strip starts at 180 deg so 0 deg is the middle)
        for az in (30,150,270): xc=(math.radians((az-180)%360))*40.7; R(xc-6.4,y,12.8,1.2,f"CUP_{nm}_CUT")        # CB1D tab notches
        for az in (60,180,300): xc=(math.radians((az-180)%360))*40.7; R(xc-6.4,y+12.4,12.8,1.0,f"CUP_{nm}_CUT")   # LB1 tab notches
    y+=h+8
for k,(nm,h) in enumerate(cups):
    cx=45.0+k*92.0; C(cx,y+42,40.5,f"CUP_{nm}_FLOOR"); R(cx+33,y+42-4,6,8,f"CUP_{nm}_CUT"); R(cx-39,y+42-4,6,8,f"CUP_{nm}_CUT")
    rows.append(("floor disc (also the lid of the cell below)",nm,"D81.0 with 2 slots 6 x 8 at +/-36",1,"slot positions match the cup floor slots"))
R(0,y+90,76,5.0,"CUP_A_SHIM"); rows.append(("shim between AB1A and AB1B","A","76 x 5.0 x 0.3",1,"copper or graphite, sits between the rib pair"))
ln+=["0","ENDSEC","0","EOF"]; open(f"{OUT}/liner_patterns.dxf","w").write("\n".join(ln)); csv.writer(open(f"{OUT}/liner_cut_list.csv","w",newline="")).writerows(rows)
wall_area=2*CIRC*5.8+CIRC*14.4; floor_area=3*math.pi*40.5**2
# ============ 2. masses of the printed parts ============
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3,3).astype(np.float64)
def vol(p): T=load(p); return abs(float(np.sum(np.einsum('ij,ij->i',T[:,0],np.cross(T[:,1],T[:,2])))/6.0))/1000.0
FL="legacy/PHIFOLD233_FINAL_FLAT_SET/"
parts=[(f"FORMER_L{k}","PETG",1,FL+f"01_FORMERS/FORMER_L{k}_petal_coil_former.stl",True) for k in range(1,7)]
parts+=[("CORE_PCB_CYLINDER_v3_vault","PETG",1,"kit_v18/SET/02_CORE_PCB_CYLINDER/CORE_PCB_CYLINDER_v3_vault.stl",False),("BASE_PLATE_RX_CASSETTE_v2","PETG",1,FL+"09_HUB_CAP_HOOD_RX_CASSETTE_v2/STL/BASE_PLATE_RX_CASSETTE_v2.stl",False),
 ("HUB_CAP_HTA_v3_vault","PETG",1,"kit_v18/PARTS/HUB_CAP_HTA_v3_vault.stl",False),("LOTUS_HOOD_CARRIER_v2_spokes","PETG",1,"kit_v18/PARTS/LOTUS_HOOD_CARRIER_v2_spokes.stl",False),
 ("VAULT_CUP_A_ANALOG","PETG",1,"kit_v18/PARTS/VAULT_CUP_A_ANALOG.stl",False),("VAULT_CUP_B_ISOLATION","PETG",1,"kit_v18/PARTS/VAULT_CUP_B_ISOLATION.stl",False),("VAULT_CUP_CD_CONTROL_DISPLAY","PETG",1,"kit_v18/PARTS/VAULT_CUP_CD_CONTROL_DISPLAY.stl",False),("HEAD_SKIRT","PETG",1,"kit_v18/PARTS/HEAD_SKIRT.stl",False)]
pins=sorted(glob.glob(FL+"03_PINS/*.stl")); pv=sum(vol(p) for p in pins)
rho={"PETG":1.27}; M=[]; tot=0
for nm,mat,q,p,exact in parts:
    v=vol(p); m=v*rho[mat]*q; tot+=m; M.append((nm,mat,q,round(v,1),round(m),"exact (single solid)" if exact else "upper bound (overlapping shells counted twice)"))
M.append(("15 stepped pins","PETG",15,round(pv,1),round(pv*1.27),"exact")); tot+=pv*1.27
csv.writer(open(f"{OUT}/printed_parts_mass.csv","w",newline="")).writerows([("part","material","qty","volume_cm3","mass_g_100pct_infill","note")]+M)
# ============ 3. master BOM ============
B=[("section","item","qty","spec / value","where","note")]
for r in M: B.append(("printed",r[0],r[2],f"{r[1]}, solid infill, {r[3]} cm3, about {r[4]} g",r[5],""))
B+=[("material","MnZn ferrite tile inner",13,"27.0 x 26.2 x 2.5 mm, mur >= 2000 (3C90 class), cut to size","hood","see hood_tile_cut_list.csv"),
 ("material","MnZn ferrite tile outer",13,"26.5 x 40.5 x 2.5 mm","hood","about 278 g in total"),
 ("material","litz wire",6,"1.2 mm OD, about 9 m per layer (53.8 m total)","formers","already specified"),
 ("material","light pipe, acrylic rod",66,"D1.5 x 6.2 mm, black heat-shrink sleeve","roof / cap / HTA board","pipe runs z40.9 to z47.1"),
 ("material","nanocrystalline ribbon 0.12 mm (optional) / foil",1,f"liners: walls {wall_area/100:.0f} cm2 + floors {floor_area/100:.0f} cm2","cups","cut with liner_patterns.dxf"),
 ("material","graphite sheet 25 um (optional)",1,"same patterns as the foil","cups","thermal spreading only; weak magnetic shield"),
 ("material","syntactic silicone potting",1,"about 37 cm3 gross for cup A, 81 cm3 for cup CD (net about 70-80% after boards)","cups A, CD","pot each cup before the next goes on"),
 ("material","carbonyl-iron silicone absorber",1,"about 37 cm3 gross","cup B",""),
 ("material","clear silicone",1,"a few cm3 over the LEDs","cup CD",""),
 ("material","M3 heat-set insert D4.0 x 5",3,"brass","hub bosses",""),("material","screw M3 x 8",3,"stainless","base plate to hub",""),
 ("material","acrylic or PETG lens disc (optional)",1,"D90 x 0.8, opal","cap top","")]
for nm,p in (("AB1A","PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A/PF233-AB1A_BOM.csv"),("AB1B","PHIFOLD233_FINAL_KIT_v3/05_PCB_receiver_AB1B/PF233-AB1B_BOM.csv"),("PB1R","PHIFOLD233_KIT_v6_ARCHITECTURE/PB1R/PF233-PB1R_BOM.csv"),("PM1","PHIFOLD233_FINAL_KIT_v4/03_POWER_BOARD_PM1/PF233-PM1_BOM.csv"),("HB1","PHIFOLD233_KIT_v6_ARCHITECTURE/HB1/PF233-HB1_BOM.csv")):
    for r in list(csv.reader(open("legacy/"+p)))[1:]: B.append(("pcb "+nm,r[1],r[0],f"{r[3]} {r[4]}"[:70],nm,r[5][:40]))
for nm,p in (("CB1D","kit_v18/CB1D/PF233-CB1D_BOM.csv"),("LB1","kit_v18/LB1/PF233-LB1_BOM.csv"),("HTA","kit_v18/HTA/PF233-HTA_BOM.csv")):
    for r in list(csv.reader(open(p)))[1:]: B.append(("pcb "+nm,r[1] if nm!="HTA" else r[1],r[0],(r[3]+" "+r[4])[:70] if nm!="HTA" else r[2]+" "+r[3],nm,(r[5] if nm!="HTA" else "")[:40]))
csv.writer(open(f"{OUT}/BOM_MASTER.csv","w",newline="")).writerows(B)
# ============ 4. KiCad design rules for the two unrouted boards ============
dru=lambda nets,hv,pw: f'(version 1)\n(rule "HV nets {hv} mm"\n  (condition "{nets}")\n  (constraint clearance (min {hv}mm)))\n(rule "power track width"\n  (condition "{pw}")\n  (constraint track_width (min 0.6mm)))\n(rule "min track / space"\n  (constraint track_width (min 0.127mm))\n  (constraint clearance (min 0.127mm)))\n'
open(f"{OUT}/PF233-CB1D.kicad_dru","w").write(dru("A.NetName == 'COIL_A' || A.NetName == 'COIL_B' || A.NetName == 'DM1' || A.NetName == 'DM2' || A.NetName == 'MONO_IN'",1.0,"A.NetName == 'VBUS' || A.NetName == 'VBUS_IN' || A.NetName == '+5V'"))
open(f"{OUT}/PF233-LB1.kicad_dru","w").write(dru("A.NetName == 'NONE'",0.2,"A.NetName == '+5V' || A.NetName == 'GND'"))
print("masses (g):",{r[0]:r[4] for r in M}, "total",round(tot)); print("BOM rows",len(B)-1)
