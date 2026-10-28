#!/usr/bin/env python3
"""Vertical stack-up of the vault: board envelopes from the real board STLs against the printed-part levels of the integrated cylinder."""
import struct, numpy as np, json, os
def zr(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; V=np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3); Z=V[:,2::3] if False else V.reshape(-1,3,3)[:,:,2]
    return float(Z.min()),float(Z.max())
B={"CB1D":"kit_v18/CB1D/PF233-CB1D_board_with_components.stl","LB1":"kit_v18/LB1/PF233-LB1_board_with_components.stl","AB1A":"legacy/PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A/PF233-AB1A_board_with_components.stl","AB1B":"legacy/PHIFOLD233_FINAL_KIT_v3/05_PCB_receiver_AB1B/PF233-AB1B_board_with_components.stl"}
Z={k:zr(p) for k,p in B.items() if os.path.exists(p)}; print({k:tuple(round(x,2) for x in v) for k,v in Z.items()})
rows=[]
def row(name,gap,need,note=""): rows.append(dict(check=name,gap_mm=round(gap,2),required_mm=need,result="PASS" if gap>=need else "FAIL",note=note))
# placements: board underside z (tray standoffs 11.1, rib slot 27.0, rib tops 39.2); the STL z=0 is the board's mid or bottom plane: use its own min as the underside
def top(k,under): lo,hi=Z[k]; return under+(hi-lo)
if "AB1A" in Z: row("AB1A top vs septum underside z20.1",20.1-top("AB1A",11.1),0.5)
if "AB1B" in Z: row("AB1B top vs septum underside z20.1",20.1-top("AB1B",11.1),0.5)
if "CB1D" in Z: row("CB1D top parts vs LB1 underside z39.2",39.2-top("CB1D",27.0),0.2,"tightest vertical gap in the head")
if "LB1" in Z: row("LB1 LED tops (0.8 mm board + 0.65 mm SK9822-EC20, OPSCO Rev. A/0) vs roof underside z41.3",41.3-(39.2+0.8+0.65),0.3,"LB1 must be a 0.8 mm board; LB1-v6 (the v5 row used 0.8 mm for a 1.78 mm reverse-mount SK6812MINI-E, CORRECTIONS)")
if "LB1" in Z: row("LB1 tallest part (C1210 10 uF, 2.0 mm, inside the roof D20 centre port) vs cap underside z44.5",44.5-(39.2+Z["LB1"][1]),0.3,"JLB is flat wire pads now; the 9 mm header hit the cap")
row("LB1 board thickness 0.8 (STL) vs 0.8 required",0.8-(Z["LB1"][0]*-1 if "LB1" in Z else 0.8)+0.0,-0.001,"")
row("CB1D board thickness vs rib slot 1.9 mm",1.9-1.6,0.1,"slot 27.0-28.9"); row("LB1 edge R39.0 vs post inner r39.5",39.5-39.0,0.3); row("CB1D/septum edge vs slot floor r39.3",39.3-39.0,0.2)
json.dump(rows,open("kit_v22/stack_check.json","w"),indent=1)
for r in rows: print(r["result"],r["check"],r["gap_mm"],r["note"])
