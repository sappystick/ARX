import sys, json, time, os, hashlib
from router import Router
import router as _rt
if sys.argv[1] == "AU1": _rt.GR = 0.125      # 0.5 mm-pitch MCU / gyro / headphone amp: a 0.125 mm grid puts every escape on its pin's centre line (2026-10-28);
                                               # CB1D back on 0.15 mm since the gyro moved to AU1 (no fine-pitch part left; on 0.125 it lost TRIG_EXT)
board=sys.argv[1]
_pads={"LB1":"kit_v18/LB1/pads.json","PB1R":"kit_v6/PB1R/pads.json","PM2":"kit_v6/PM2/pads.json","HB2":"kit_v6/HB2/pads.json","AU1":"kit_v6/AU1/pads.json"}.get(board,"kit_v18/CB1D/pads.json")

# ---- one router factory per board (2026-10-28): full routes, local repair and incremental re-routes all build the router here, so the settings exist once
CB1D_PRIORITY=['MUX_S0','MUX_S1','MUX_S2','TRIG_IN','VCM_OUT','HTA_P','DIAL_IN','JOY_YF','SDOA1','SDOA3','SCLK','JOY_XF','HTA_IN','JOY_X']
# AU1 learned order (2026-10-28 runs): the MCU right-column nets that lost in earlier runs go first, pin order 19 / 17 / 21, then the gyro clock and the amp input;
# BSL_INV from UM.21 otherwise runs down past pins 20 / 19 and walls them in
AU1_FRONT=["SPK_SD","PWM_AU","BSL_INV","GYR_SCL","US_INN"]
def mk():
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
    elif board=="AU1":
        # 36 x 60 audio board (battery side), 8 layers since 2026-10-28: F / In2 / In5 / In6 / B signal, hatched planes GND (In1), +5V_AU (In3), +3V3_AU (In4); 0.5 mm on the pack
        # input, the buck switch node and the speaker outputs; plane stubs 0.2 mm (a 0.5 mm +5V_AU track could not reach the amplifier VDD pin: CB1D-style plane instead)
        wid={"VBUS_AU":0.5,"SW_AU":0.6,"SPK_P":0.5,"SPK_N":0.5,"GND":0.2,"+5V_AU":0.2,"+3V3_AU":0.2}
        R=Router("kit_v6/AU1/pads.json",["F.Cu","In2.Cu","In5.Cu","In6.Cu","B.Cu"],{"GND":"In1.Cu","+5V_AU":"In3.Cu","+3V3_AU":"In4.Cu"},wid,clr=0.2)      # 8 layers (pw_export)
        R.fine_order="span"; R.priority=list(AU1_FRONT)
        R.stub_first={"UM.7"}            # learned (2026-10-28, parallel rounds): the MCU VDD pin loses its plane via to the left-column escapes unless stubbed first
        return R
    elif board=="HB2":
        # 24 x 38 grip board: F/B signal layers, hatched GND (In1); trigger and dial signals only
        R=Router("kit_v6/HB2/pads.json",["F.Cu","B.Cu"],{"GND":"In1.Cu"},{"P3V3":0.3},clr=0.2)
    else:
        wid={"VBUS_IN":0.8,"+5V":0.6,"+5VA":0.5,"P3V3":0.3,"+3V3D":0.4,"VCM_OUT":0.3}
        R=Router("kit_v18/CB1D/pads.json",["F.Cu","In2.Cu","In3.Cu","B.Cu"],{"GND":"In1.Cu","P3V3":"In4.Cu"},wid,hv={"COIL_B","DM1","DM2","COIL_A"},clr=0.2)
        R.stub_first={"UG.6","UG.7"}   # learned (2026-10-28 exact fine-zone keep-out): the gyro GND pads lost their plane via (no such pads since the gyro moved: no effect)
    R.priority=list(CB1D_PRIORITY)
    return R

import route_repair
route_repair.PADS=_pads
def write(st, R):
    """every finished layout is written with the pad file it was routed against (the base of the next incremental re-route)"""
    route_repair.write_layout(board, st, R.tracks, R.vias, R.layers, R.planes, R.R, _pads)

# ---- modes: REPAIR=1 local repair of the saved layout; otherwise an incremental re-route when only pads / nets changed; otherwise (or FULL=1) a full route
# what decides the copper (2026-10-28): router.py, this board's factory and the grid; orchestration (rounds, repair, incremental) does not invalidate a layout
import inspect
_code=hashlib.sha1(open("router.py","rb").read()+inspect.getsource(mk).encode()+repr((board,_rt.GR,CB1D_PRIORITY,AU1_FRONT)).encode()).hexdigest()
route_repair.CODE=_code
if "--fingerprint" in sys.argv: print(_code); sys.exit(0)        # the layout fingerprint for this board (used to write bases; same computation as routing)
_padh=hashlib.sha1(open(_pads,"rb").read()).hexdigest()
if os.environ.get("REPAIR"):                                     # local repair of the saved layout: only the nets around the open ones are re-routed (route_repair.py)
    route_repair.repair(board, mk, AU1_FRONT if board=="AU1" else CB1D_PRIORITY); sys.exit(0)
if not os.environ.get("FULL"):
    st=route_repair.incremental(board, mk, _pads, _code)
    if st is not None and not st.get("failures_net"): sys.exit(0)   # done incrementally (or nothing changed); otherwise fall through to a full route
# a saved router state is only valid for the netlist / pads, router code and configuration it was made with (a stale state produced stale routes twice): key it to all three
_h=hashlib.sha1((_padh+_code).encode()).hexdigest()
_shaf=f"kit_v20/state_{board}.sha"; _old=open(_shaf).read().strip() if os.path.exists(_shaf) else None
if _old != _h:
    for _f in (f"kit_v20/state_{board}.pkl", f"kit_v20/route_{board}.json"):   # never delete a finished layout: keep it as *_stale (a stale state produced stale routes twice)
        if os.path.exists(_f): os.replace(_f, _f.replace(f"_{board}.", f"_{board}_stale."))
    os.makedirs("kit_v20",exist_ok=True); open(_shaf,"w").write(_h); print(board,"router state reset (pads / router / config changed)" if _old else "router state: new")
if board=="AU1":
    # full route: rounds in parallel (route_repair.parallel_rounds: 4 processes, deterministic orders, best kept), then local repair of the best if nets stay open
    st=route_repair.parallel_rounds(board, mk, AU1_FRONT, write)
    if st["failures"]: route_repair.repair(board, mk, AU1_FRONT, budget=200)      # open nets or failed plane stubs
    sys.exit(0)
R=mk()
st=R.run(budget=270,state=f'kit_v20/state_{board}.pkl'); print(board,st,"length_mm",round(R.length()))
if st.get("finished"): write(st, R)
