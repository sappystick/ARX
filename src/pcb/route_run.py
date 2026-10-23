import sys, json, time
from router import Router
board=sys.argv[1]
if board=="LB1":
    R=Router("kit_v18/LB1/pads.json",["F.Cu","B.Cu"],{"GND":"In1.Cu","+5V":"In2.Cu"},{"+5V":0.4,"GND":0.4},clr=0.2)
else:
    wid={"VBUS_IN":0.8,"+5V":0.6,"+5VA":0.5,"P3V3":0.3,"+3V3D":0.4,"VCM_OUT":0.3}
    R=Router("kit_v18/CB1D/pads.json",["F.Cu","In2.Cu","In3.Cu","B.Cu"],{"GND":"In1.Cu","P3V3":"In4.Cu"},wid,hv={"COIL_B","DM1","DM2","COIL_A"},clr=0.2)
R.priority=['MUX_S0','MUX_S1','MUX_S2','TRIG_IN','VCM_OUT','HTA_P','DIAL_IN','JOY_YF','SDOA1','SDOA3','SCLK','JOY_XF','HTA_IN','JOY_X']
st=R.run(budget=270,state=f'kit_v20/state_{board}.pkl'); print(board,st,"length_mm",round(R.length()))
if st.get("finished"): json.dump(dict(stats=st,tracks=R.tracks,vias=R.vias,layers=R.layers,planes=R.planes,R=R.R),open(f"kit_v20/route_{board}.json","w"))
