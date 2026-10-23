import os, re, json, csv, struct, numpy as np, glob
os.environ["PW"]="C"; os.environ["DISC"]="1"
import importlib, pw_design as D
OUT="kit_v18"; res={}
# ---- heights of the placed controller parts (board top at z28.6 on the cup tabs; LB1 underside at z38.2 => 9.6 mm... compute exact budget)
BOARD_TOP=25.8+1.2+1.6; LB1_BOTTOM=39.2-1.0                       # CB1D on tabs at z27.0 (1.6 board); LB1 tab top 39.2 minus tab thickness 1.0 = underside at 38.2 (tab top is the board underside)
LB1_UNDER=39.2
rows=[]
for p in D.PARTS:
    h=D.LIB[p["type"]]["body"][2]; rows.append((p["ref"],p["type"],h))
tall=sorted([r for r in rows if r[2]>4.0],key=lambda r:-r[2])
res["CB1D_height_budget"]=dict(board_top_z=27.0+1.6,LB1_underside_z=LB1_UNDER,room_mm=round(LB1_UNDER-(27.0+1.6),1),tallest_parts=[(r[0],r[1],r[2]) for r in tall[:8]],all_fit=bool(all(r[2]<=LB1_UNDER-(27.0+1.6) for r in rows)))
# ---- analog boards: heights/outline from the earlier STLs
for nm,p in (("AB1A","PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A/PF233-AB1A_board_with_components.stl"),("AB1B","PHIFOLD233_FINAL_KIT_v3/05_PCB_receiver_AB1B/PF233-AB1B_board_with_components.stl")):
    b=open("legacy/"+p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; T=np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3).astype(float)
    res[nm]=dict(x=[round(T[:,0].min(),1),round(T[:,0].max(),1)],y=[round(T[:,1].min(),1),round(T[:,1].max(),1)],z=[round(T[:,2].min(),2),round(T[:,2].max(),2)],height_above_board_mm=round(T[:,2].max(),2),fits_cup_A=bool(T[:,2].max()<=6.0))
res["old_CB1"]=dict(outline="70x70 square, diagonal 99 mm",fits_D78=False,reason="diagonal 99 mm > 78 mm; the 63-part disc re-placement replaces it")
# ---- wiring map from the real netlists
def parse(path):
    t=open(path).read(); nets={}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)\n    \)',t,re.S):
        for n in re.finditer(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)',m.group(2)): nets.setdefault((n.group(1),n.group(2)),m.group(1))
    return nets
rows=[("board","connector","pin","net")]
for nm,p in (("AB1A","PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A/PF233-AB1A.net"),("AB1B","PHIFOLD233_FINAL_KIT_v3/05_PCB_receiver_AB1B/PF233-AB1B.net")):
    nets=parse("legacy/"+p)
    for (ref,pin),net in sorted(nets.items(),key=lambda k:(k[0][0],int(k[0][1]) if k[0][1].isdigit() else 0)):
        if ref in("J1","J2"): rows.append((nm,ref,pin,net))
for ref in ("JA","JB","JPB","JTR","JPW","JCL","JHTA","JDBG"):
    for net,pins in D.NETS.items():
        for r,pin in pins:
            if r==ref: rows.append(("CB1D",ref,pin,net))
rows[1:]=sorted(rows[1:],key=lambda r:(r[0],r[1],int(r[2]) if r[2].isdigit() else 0))
csv.writer(open(f"{OUT}/WIRING_MAP_connectors.csv","w",newline="")).writerows(rows)
res["wiring_rows"]=len(rows)-1
json.dump(res,open(f"{OUT}/fit_check.json","w"),indent=1); print(json.dumps(res,indent=1)[:2600])
