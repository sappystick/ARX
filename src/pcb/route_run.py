import sys, json, time, os, hashlib
from router import Router
board=sys.argv[1]
# a saved router state is only valid for the netlist/pads, router code and configuration it was made with (a stale state produced stale routes twice): key it to a hash of all three
_pads={"LB1":"kit_v18/LB1/pads.json","PB1R":"kit_v6/PB1R/pads.json","PM2":"kit_v6/PM2/pads.json","HB2":"kit_v6/HB2/pads.json"}.get(board,"kit_v18/CB1D/pads.json")
_h=hashlib.sha1(b"".join(open(f,"rb").read() for f in (_pads,"router.py","route_run.py"))).hexdigest()
_shaf=f"kit_v20/state_{board}.sha"; _old=open(_shaf).read().strip() if os.path.exists(_shaf) else None
if _old != _h:
    for _f in (f"kit_v20/state_{board}.pkl", f"kit_v20/route_{board}.json"):
        if os.path.exists(_f): os.remove(_f)
    os.makedirs("kit_v20",exist_ok=True); open(_shaf,"w").write(_h); print(board,"router state reset (pads / router / config changed)" if _old else "router state: new")
if board=="LB1":
    R=Router("kit_v18/LB1/pads.json",["F.Cu","B.Cu"],{"GND":"In1.Cu","+5V":"In2.Cu"},{"+5V":0.4,"GND":0.4},clr=0.2)
elif board=="PB1R":
    # 70 x 70 neck-module board, rectangular outline, F/B signal layers, hatched GND (In1) and VBUS (In2) planes (eddy rule: no solid planes); flyback nets DRAIN1/CLAMP1 keep 1.0 mm
    wid={"DRAIN1":1.5,"CLAMP1":1.5,"SRC1":1.5,"VBUS":0.5,"GND":0.5,"AUX12":0.5}      # GND / VBUS ride the planes and the via farm (viafarm.py): their stubs are narrow; the 20 A surface copper is DRAIN1, SRC1 (and CLAMP1)
    R=Router("kit_v6/PB1R/pads.json",["F.Cu","B.Cu"],{"GND":"In1.Cu","VBUS":"In2.Cu"},wid,hv={"DRAIN1","CLAMP1"},clr=0.2)
elif board=="PM2":
    # 28 x 70 battery-dock board: F/B signal layers, hatched GND (In1) and VBUS (In2); the pack current (5 A fuse) rides BAT_P / BAT_F at 1.5 mm and VBUS / GND at 1.0 mm
    wid={"BAT_P":1.5,"BAT_F":1.5,"VBUS":1.0,"GND":1.0}
    R=Router("kit_v6/PM2/pads.json",["F.Cu","B.Cu"],{"GND":"In1.Cu","VBUS":"In2.Cu"},wid,clr=0.2)
elif board=="HB2":
    # 24 x 38 grip board: F/B signal layers, hatched GND (In1); trigger and dial signals only
    R=Router("kit_v6/HB2/pads.json",["F.Cu","B.Cu"],{"GND":"In1.Cu"},{"P3V3":0.3},clr=0.2)
else:
    wid={"VBUS_IN":0.8,"+5V":0.6,"+5VA":0.5,"P3V3":0.3,"+3V3D":0.4,"VCM_OUT":0.3}
    R=Router("kit_v18/CB1D/pads.json",["F.Cu","In2.Cu","In3.Cu","B.Cu"],{"GND":"In1.Cu","P3V3":"In4.Cu"},wid,hv={"COIL_B","DM1","DM2","COIL_A"},clr=0.2)
R.priority=['MUX_S0','MUX_S1','MUX_S2','TRIG_IN','VCM_OUT','HTA_P','DIAL_IN','JOY_YF','SDOA1','SDOA3','SCLK','JOY_XF','HTA_IN','JOY_X']
st=R.run(budget=270,state=f'kit_v20/state_{board}.pkl'); print(board,st,"length_mm",round(R.length()))
if st.get("finished"): json.dump(dict(stats=st,tracks=R.tracks,vias=R.vias,layers=R.layers,planes=R.planes,R=R.R),open(f"kit_v20/route_{board}.json","w"))
