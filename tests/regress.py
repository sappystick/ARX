#!/usr/bin/env python3
"""Regression: reads results written into work/ by the make targets and compares with the expected numbers. Missing result files are reported as SKIP, not PASS."""
import json, os, sys
W="work"; res=[]
def rd(p):
    try: return json.load(open(os.path.join(W,p)))
    except Exception: return None
def chk(name,ok,detail=""): res.append(("PASS" if ok else "FAIL",name,detail))
import re
ALLOW="--allow-skip" in sys.argv                                      # partial runs while developing; never for sign-off
try: UNV=set(re.findall(r"^\|\s*(U-[A-Z0-9-]+)\s*\|",open("docs/UNVERIFIED.md").read(),re.M))
except Exception: UNV=set()
def skip(name,uid=None):
    """a missing result is FAIL unless the item is registered as UNVERIFIED in docs/UNVERIFIED.md (then it is reported as UNVERIFIED); --allow-skip keeps the old SKIP for partial runs"""
    if uid and uid in UNV: res.append(("UNVERIFIED",name,f"{uid}: see docs/UNVERIFIED.md"))
    elif ALLOW: res.append(("SKIP",name,"result file not present: run the matching make target (--allow-skip)"))
    else: res.append(("FAIL",name,"result file missing and the item is not registered UNVERIFIED in docs/UNVERIFIED.md"))
d=rd("kit_v22/check_v22.json")
if d: bad=[c["check"] for c in d["checks"] if c["result"]!="PASS"]; chk("v5 geometry checks (47 expected: cylinder, TX-lead channel, roof, tray, septum, comb, bosses, base plate, receive-board holes, QB lead access, damping resistors)",len(d["checks"])>=47 and not bad,f"{len(d['checks'])} checks, fails={bad}")
else: skip("v5 geometry checks")
d=rd("kit_v20/sim_head1.json")
if d:
    chk("coil moment 7.96 A m2 at 20 A (+-2%)",abs(d["tx_moment"]["moment_Am2_at_20A"]-7.96)<0.16,str(d["tx_moment"]))
    g=d["first_clean_gate_us"]; x=g["100 nF C0G/film"]["X8"]; chk("first clean gate X8 film 7.94 us (+-0.5)",abs(x-7.94)<0.5,str(x))
    s=d["improvement_steps_X8_depth_mm"]["RS3 -> 100 ohm"]["1.0 g"]; chk("X8 1 g depth with 100 ohm 179 mm (+-6)",abs(s-179)<6,str(s))
else: skip("sim_head1 results")
d=rd("kit_v21/sim_tanr.json")
if d:
    pv=d["peak_volts_at_turnoff"]; chk("figure-8 off 0.5 mm leaks > 100x the quadrupole",pv["X8 figure-8"]["shift 0.5,0 mm"]>100*pv["QUAD A (quadrants)"]["shift 0.5,0 mm"],str(pv["X8 figure-8"]["shift 0.5,0 mm"]))
else: skip("sim_tanr results")
d=rd("kit_v21/sim_quadbearing.json")
if d:
    v=list(d.values()); chk("quad pair RSS flat within 3% over azimuth",all(x["amp_ratio_max_min"]<1.03 for x in v),str([x["amp_ratio_max_min"] for x in v]))
else: skip("quad bearing results")
d=rd("kit_v22/parts_report.json")
if d: chk("v5 parts closed meshes",all(v["nonmanifold_edges"]==0 for v in d.values()),str({k:v["nonmanifold_edges"] for k,v in d.items()}))
d=rd("kit_v20/route_LB1.json")
if d: st=d["stats"]; chk("LB1 routed 68/68 nets, no failures",st["nets_routed"]==st["nets_to_route"]==68 and not st["failures"],str(st))
else: skip("LB1 routing")
d=rd("kit_v18/PARTS/hood_v3_report.json")
if d: a=d["hood_v3_audit"]; chk("hood v3: 26 tiles butted 0.2 mm, spoke gap >= 1.7 mm, corner r <= 116.1, all generator checks pass",a["tiles"]==26 and a["min_tile_gap"]>=1.7 and a["outer_frame_corner_r"]<=116.1 and all(c["result"]=="PASS" for c in d["checks"]),str({k:a[k] for k in ("min_tile_gap","butt_joint","outer_frame_corner_r","mass_g","dims")}))
else: skip("hood audit")
d=rd("kit_v22/hood_axi.json")
if d:
    v=d["validation_no_hood"]; vv=d["variants"]; v3=next(k for k in vv if k.startswith("v3")); v2=next(k for k in vv if k.startswith("v2"))
    chk("hood model: no-hood axis field within 0.5 % of Biot-Savart (50-300 mm)",all(abs(v[k]["dev_pct"])<0.5 for k in ("50","100","150","200","300")),str({k:v[k]["dev_pct"] for k in v}))
    chk("hood v3 gain at 200 mm 12.5-14.5 % (series model; v2 9.5-10.2 %), tiles below 100 mT at 20 A",12.5<=vv[v3]["lower"]["200"]<=14.5 and 9.5<=vv[v2]["lower"]["200"]<=10.2 and vv[v3]["Bmax_in_tiles_mT_at_20A"]<100,f"v3 {vv[v3]['lower']['200']}-{vv[v3]['upper']['200']} %, v2 {vv[v2]['lower']['200']}-{vv[v2]['upper']['200']} %, Bmax {vv[v3]['Bmax_in_tiles_mT_at_20A']} mT")
else: skip("hood model")
d=rd("kit_v19/yoke_check.json")
if d: bad=[c["check"] for c in d["checks"] if c["result"]!="PASS"]; chk("yoke checks all pass",not bad,str(bad[:3]))
else: skip("yoke checks")
d=rd("kit_v23/upper_check.json")
if d:
    bad=[c["check"] for c in d["checks"] if c["result"]!="PASS"]; chk("upper assembly v1: all checks pass (57 expected: meshes, grip, trigger, dock rails, pack bays, latch, twin cavity, tubes, interference, balance)",len(d["checks"])>=57 and not bad,f"{len(d['checks'])} checks, fails={bad[:3]}")
    b=d["balance"]; chk("upper assembly v1: torque about the grip at the v20 head reach <= v20, mass <= 1.6 kg incl. pack",b["new_47deg_working"]<=b["baseline_v20_kg_m"] and d["mass"]["upper_total_kg"]<=1.6,f"{b['new_47deg_working']} vs {b['baseline_v20_kg_m']} kg m, {d['mass']['upper_total_kg']} kg")
else: skip("upper assembly")
d=rd("kit_v23/power_dock_check.json")
if d: bad=[c["check"] for c in d["checks"] if c["result"]!="PASS"]; chk("PM2 battery dock: interlock (on only when seated AND switched), gate drive, soft start, ratings, runtime (13 checks: battery-side and cord currents from a time-domain model)",len(d["checks"])>=13 and not bad,f"ramp {d['soft_start']['ramp_ms']} ms, inrush {d['soft_start']['inrush_A']} A, boost {d['runtime']['boost_h_one_pack']} h/pack, fails={bad[:2]}")
else: skip("PM2 battery dock")
d=rd("kit_v23/tx_vbus.json")
if d:
    tv=[r for r in d["tx_stage_vs_vbus"] if r["case"].startswith("100 nF")]; t20=[r for r in d["ton_rule"] if r["I_A"]==20]; lo=next(r for r in t20 if r["V"]==19.6); hi=next(r for r in t20 if r["V"]==29.4)
    chk("TX over the 7S range (19.6-29.4 V), 20 A: reproduces sim_head1 at 26 V; Vds peak <= 480 V (650 V FET, >= 25 % margin); turn-off quiet time independent of VBUS (+-0.05 us)",d["validation_ok"] and max(r["Vds_peak"] for r in tv)<=480 and max(r["t_quiet_us"] for r in tv)-min(r["t_quiet_us"] for r in tv)<0.05,f"Vds {min(r['Vds_peak'] for r in tv):.1f}-{max(r['Vds_peak'] for r in tv):.1f} V, quiet {tv[0]['t_quiet_us']:.2f} us")
    chk("firmware on-time for 20 A: 59.5 us at 19.6 V and 38.5 us at 29.4 V (loop R and bulk droop, +-1 us); lossless L I / V (55.1 / 36.7 us) under-delivers by > 4 %; bulk droop at 19.6 V under 5 %; bulk bank CB1-CB9 at most 60 % of 50 V",abs(lo["ton_loop_droop_us"]-59.5)<1 and abs(hi["ton_loop_droop_us"]-38.5)<1 and lo["I_if_lossless_ton_A"]<19.2 and hi["I_if_lossless_ton_A"]<19.2 and lo["droop_pct"]<5.0 and d["bulk_bank"]["util_new_pct"]<=60,f"ton {lo['ton_loop_droop_us']} / {hi['ton_loop_droop_us']} us, lossless gives {lo['I_if_lossless_ton_A']} / {hi['I_if_lossless_ton_A']} A, droop {lo['droop_pct']} %, CD {d['bulk_bank']['util_new_pct']} %")
else: skip("TX voltage sweep")
try: bom=open(os.path.join(W,"kit_v6/PB1R/PF233-PB1R_BOM.csv")).read()
except Exception: bom=None
if bom: chk("PB1R generated BOM: bulk bank CB1-CB9 are the verified 50 V hybrid part (Panasonic EEHZC1H101P), M12 module listed with the 15-36 V input range",all(f"CB{n}" in bom for n in range(1,10)) and bom.count("EEHZC1H101P")>=1 and "100u 50V hybrid" in bom and "35V" not in bom and "15-36 V" in bom,"100u 50V x9")
else: skip("PB1R BOM")
d=rd("kit_v22/sbq_sim.json")
if d:
    L=d["leak"]; worst=max(v["peak_V"] for b in L.values() for k,v in b.items() if "lobes only" not in k and "0.5" in k)
    chk("SB1R-Q modeled leak at 0.5 mm offset below 20 mV (figure-8: 630 mV)",worst<0.02,f"{worst*1e3:.1f} mV")
    chk("SB1R-Q inductance 176 uH (+-10%) and R 10.4 ohm 1 oz",abs(d["L_uH"]-176)<18 and abs(d["R_1oz_ohm"]-10.4)<1.5,f"L {d['L_uH']} uH, R {d['R_1oz_ohm']}")
    chk("SB1R-Q pair flat within 7% and bearing scatter under 2 deg",all(v["rss_flat_max_over_min"]<1.07 and v["bearing_scatter_deg"]<2.0 for v in d["pattern"].values()),str([(v["rss_flat_max_over_min"],v["bearing_scatter_deg"]) for v in d["pattern"].values()]))
else: skip("SB1R-Q simulation")
d=rd("kit_v22/sbq_geometry.json")
if d: chk("SB1R-Q geometry: via margin >= 0.3, hole margin >= 0.5, equal lobe area-turns",d["via_margin_mm"]>=0.3 and d["hole_margin_mm"]>=0.5 and len({abs(a) for a in d["area_turns_mm2"]})==1,str((d["via_margin_mm"],d["hole_margin_mm"],d["area_turns_mm2"])))
if d: chk("SB1R-Q damping: RD1/RD2 fitted, QB transfer pads clear of QA copper",all(k in d.get("rd",{}) for k in ("RD1","RD2")) and d.get("transfer_margin_mm",-1)>=0 and min(d.get("rd_margin_mm",[-1]))>=0,str((d.get("transfer_margin_mm"),d.get("rd_margin_mm"))))
d=rd("kit_v22/sbq_damping2.json")
if d:
    fc=d["first_clean_gate_us"]; w=[k for k in fc if k.startswith("worst modeled") and "blank release 0 us" in k]; a=[k for k in fc if k.startswith("A aligned") and "blank release 0 us" in k]
    chk("SB1R-Q first clean gate with Rd 680, no blanking: A aligned 5.1-5.5 us, worst real leak <= 7.6 us (Cself 50-200 pF)",all(5.0<=fc[k]["Rd 680"]<=5.6 for k in a) and all(fc[k]["Rd 680"]<=7.6 for k in w) and all(fc[k]["no Rd"]>=59 for k in a+w),str([fc[k]["Rd 680"] for k in a+w]))
    n=d["gate_noise_nV_rtHz"]; chk("SB1R-Q gated noise with Rd 680 within 6% of no Rd (Cself 100 pF, gates 6-40 us)",all(v["Rd 680"]<=1.06*v["no Rd"] for k,v in n.items() if k.startswith("Cself 100")),str({k.split(", ")[1]:v["Rd 680"] for k,v in n.items() if k.startswith("Cself 100")}))
else: skip("SB1R-Q damping")
for b in ("LB1","CB1D","PB1R","PM2","HB2"):
    d=rd(f"kit_v22/drc_{b}.json")
    if d: chk(f"{b} independent DRC: 0 clearance violations, 0 open nets, edge and notch clean",d["clearance_violations"]==0 and d["open_nets"]==0 and d["edge_samples"]==0 and d["notch_samples"]==0,str({k:d[k] for k in ('clearance_violations','open_nets','min_gap_by_layer')}))
    else: skip(f"{b} DRC")
for b in ("CB1D","LB1","PB1R","TXJ1","SB1R-QA","SB1R-QB","PM2","HB2","HTA"):
    d=rd(f"kit_v22/kicad_drc_{b}.json")
    if d: chk(f"{b} KiCad 9 DRC (zones filled, fab-floor rules from dru_gen.py): 0 errors, 0 unconnected"+(", HV rules proven live by the negative control" if "rules_loaded" in d else ""),not d["errors"] and d["unconnected"]==0 and d.get("rules_loaded",True) and (not d["warnings"] or b not in ("CB1D","LB1")),str({k:d[k] for k in ("errors","unconnected","warnings")}))
    else: skip(f"{b} KiCad DRC")
d=rd("kit_v22/controls_3_9.json")
if d: chk("release-tx and sign-off controls: refusals (existing revision, FAIL, stale data), evidence rule, vanishing rows, idempotent output",d["all_ok"] and len(d["cases"])>=11,f"{sum(c['ok'] for c in d['cases'])}/{len(d['cases'])}")
else: skip("release / sign-off controls")
d=rd("kit_v20/route_PB1R.json")
if d: st=d["stats"]; chk("PB1R routed: all nets, no failures (70 x 70 mm rectangular board, hatched GND/VBUS planes)",st["nets_routed"]==st["nets_to_route"]>=15 and not st["failures"],str(st))
else: skip("PB1R routing")
d=rd("kit_v22/gerber_plane_PB1R.json")
if d: chk("PB1R KiCad-written Gerbers: HV pads and vias >= 1.0 mm from the plane copper (rebuilt with gerbonara/shapely, control reaches the plane's own pads)",d["failures"]==0 and d["control_ok"] and d["hv_checks"]>=4,f"{d['hv_checks']} checks, min {d['min_distance_mm']} mm, control {d['control_pads']} pads")
else: skip("PB1R Gerber plane check (gerbonara + shapely, requirements.txt)")
d=rd("kit_v22/pb1r_check.json")
if d: bad=[c["check"][:60] for c in d["checks"] if c["result"]=="FAIL"]; chk("PB1R cross-check vs the TX stage: pulse path R/L, return vias, Kelvin tap, connectors vs CB1D/PM2/TXJ1, neck-module eddy (solid plane rejected, hatched ring negligible)",not bad and d["eddy"]["ratio_solid"]>1 and d["eddy"]["ratio_hatch_ring"]<1e-3,f"{len(d['checks'])} checks, fails {bad}, solid plane {d['eddy']['ratio_solid']:.1f}x a 1 g nugget, hatched ring {d['eddy']['ratio_hatch_ring']:.1e}")
else: skip("PB1R cross-check")
d=rd("kit_v22/gerber_hv_CB1D.json")
if d: chk("CB1D Gerbers: every HV through-hole pad and via has a plane keep-out of pad + 2.0 mm (1.0 mm rule)",d["failures"]==0 and d["checked"]>=8,f"{d['checked']} checks, {d['failures']} failures")
else: skip("CB1D Gerber HV check")
d=rd("kit_v22/tx_system.json")
if d: chk("TX system: lead routing, TXJ1 and cradle checks all pass",all(c["result"]=="PASS" for c in d["checks"]),f"{len(d['checks'])} checks")
else: skip("TX system")
d=rd("kit_v22/wiring_audit.json")
if d: chk("wiring audit: every inter-board pin and harness conductor matches the netlists",not d["errors"],f"{d['link_pins']} link pins, {d['harness_conductors']} conductors, errors {len(d['errors'])}")
else: skip("wiring audit")
d=rd("kit_v22/system_budget.json")
if d: bad=[r for r in d["rows"] if r["status"]=="FAIL"]; chk("stress table: only the documented LED-rail row (needs the firmware cap) fails",len(bad)==1 and "LED" in bad[0]["part"],str([(r["part"],r["margin_pct"]) for r in bad]))
else: skip("stress table")
d=rd("kit_v22/stack_check.json")
if d: chk("board stack-up gaps all pass",all(r["result"]=="PASS" for r in d),f"{len(d)} checks")
else: skip("stack check")
d=rd("kit_v22/interference_audit.json")
if d: chk("voxel interference audit (window, bridge, junction): 0 interferences",len(d["interferences"])==0,f"{len(d['pairs'])} pairs")
else: skip("interference audit")
d=rd("kit_v22/sch_check.json")
if d: chk("KiCad schematics: 9 boards (incl. HB2, PM2), nets rebuilt from each .kicad_sch match the netlist exactly",len([v for v in d.values() if "check" in v])==9 and all(v["check"]["ok"] for v in d.values() if "check" in v),str({k:(v["check"]["nodes"] if "check" in v else "skipped") for k,v in d.items()}))
else: skip("KiCad schematics")
d=rd("kit_v22/trigger_check.json")
if d: bad=[c["check"] for c in d["checks"] if c["result"]=="FAIL"]; chk("handle inputs: trigger chain, sensor type vs GPIO, TRIG levels and time constant, dial ladder, boost stress",not bad,f"{d['levels']}, fails {bad}")
else: skip("trigger check")
d=rd("kit_v22/head_crosscheck.json")
if d: chk("full head cross-check: 0 failures (layers, radial fits, 3D interference, LED, TX, RX, wiring)",d["fails"]==0,f"{len(d['checks'])} checks, warns {d['warns']}")
else: skip("head cross-check")
d=rd("kit_v22/fine_check.json")
if d: chk("0.2 mm test: CB1D and LB1 discs and bodies clear of the cylinder",d[0][1]==0 and d[1][1]==[] and d[2][1]==0 and d[3][1]==[],str(d)[:120])
else: skip("fine check")
# --- pipeline: the incremental runner must run every script the original serial sign-off runs, and its overlap graph must cover every step
import re as _re, subprocess as _sp
_dry=_sp.run(["make","-n","signoff-serial"],capture_output=True,text=True).stdout
_serial=set(_re.findall(r"[A-Za-z0-9_]+\.py",_dry))-{"seed_copy.py"}
sys.path.insert(0,"scripts"); import pipeline as _pl
_pipe=set(_re.findall(r"[A-Za-z0-9_]+\.py"," ".join(c for _,c,_t in _pl.STEPS)))
chk("pipeline runs every script of the serial sign-off (no step silently dropped)",_serial<=_pipe,f"{len(_serial)} scripts, missing {sorted(_serial-_pipe)}")
_g=_pl.load_graph()
chk("pipeline overlap graph (data/pipeline/graph.json) covers all steps",all(n in _g for n in _pl.NAMES if n not in _pl.OPEN_ENDED),f"{len(_g)} of {len(_pl.NAMES)} steps recorded; missing {[n for n in _pl.NAMES if n not in _g and n not in _pl.OPEN_ENDED]}")
# --- Step 5 guards: the fabricator floor read from the vendors (docs/design/FAB_RULES_VERIFIED.md), through-hole rings of the generated boards, the verified fuse land, a fixed netlist date
sys.path.insert(0,"src/pcb"); import dru_gen as _dg
_rules=_dg.rules("PB1R")
chk("fab floor = the vendor-derived values (clearance 0.16, track 0.15, via drill 0.30 / ring 0.15, component PTH ring 0.18 / hole 0.46, drill-copper 0.26, drill-drill 0.41, edge 0.5) and every floor rule is (severity error)",
    _dg.GEN==dict(clearance=0.16,track=0.15,drill=0.3,annular=0.15,edge=0.5,hole_clearance=0.26,hole_to_hole=0.41,pth_annular=0.18,pth_drill=0.46) and _rules.count("(severity error)")==2 and "hole_to_hole (min 0.41mm)" in _rules,str(_dg.GEN))
_rings={}
for _b in "RPGC":
    _o=_sp.run([sys.executable,"-c","import os,sys; sys.path.insert(0,'src/pcb'); import pw_design as D; T={p['type'] for p in D.PARTS if D.LIB[p['type']].get('tht')}; print(round(min((min(min(w,h) for n,x,y,w,h,s in D.LIB[t]['pads'])-D.LIB[t]['drill'])/2 for t in T),3), round(min(D.LIB[t]['drill'] for t in T),3))"],capture_output=True,text=True,env={**os.environ,"PW":_b}).stdout.split()
    _rings[{"R":"PB1R","P":"PM2","G":"HB2","C":"CB1D"}[_b]]=tuple(map(float,_o)) if len(_o)==2 else None
chk("through-hole parts of PB1R, PM2, HB2, CB1D: ring >= 0.18 mm and finished hole >= 0.46 mm (AdvancedPCB 0.007\" / 0.018\" for component holes)",all(v and v[0]>=0.18 and v[1]>=0.46 for v in _rings.values()),str(_rings))
_fo=_sp.run([sys.executable,"-c","import sys; sys.path.insert(0,'src/pcb'); import pw_design as D; a,b=D.LIB['FUSE1206B']['pads']; print(round(b[1]-a[1]-a[3],3), round(b[1]-a[1]+a[3],3), a[3], a[4])"],capture_output=True,text=True,env={**os.environ,"PW":"P"}).stdout.split()
chk("PM2 / CB1D fuse land = Bourns SF-1206S recommended layout (gap 2.2, overall 4.7, pad height 1.65 mm)",_fo==["2.2","4.7","1.25","1.65"],str(_fo))
_net=os.path.join(W,"kit_v6/PB1R/PF233-PB1R.net")
_nd=re.search(r'\(date "([0-9-]+)"\)',open(_net).read()).group(1) if os.path.exists(_net) else None
chk("generated netlists carry the fixed design date (not the wall clock), so a regenerated netlist is byte-identical on any day",_nd=="2026-10-24" and "date.today()" not in open("src/pcb/pw_design.py").read(),str(_nd))
_e={b:rd(f"kit_v22/gerber_edge_{b}.json") for b in ("CB1D","LB1","PB1R","PM2","HB2","HTA")}
if all(_e.values()): chk("Gerber copper read back from the files: nothing outside the outline (notch included) and >= 0.5 mm to the edge on every layer of CB1D, LB1, PB1R, PM2, HB2, HTA",all(v["ok"] for v in _e.values()),str({b:min(r["min_edge_gap_mm"] for r in v["sets"][list(v["sets"])[0]]["layers"].values() if r["min_edge_gap_mm"] is not None) for b,v in _e.items()}))
else: skip("Gerber edge read-back")
_m=open("src/mech/mech_v20.py").read()
chk("NPM cable window in mech_v20.py is still x -26..-14 (the numbers pb1r_check.py measures PB1R's JL1 / JP / JC against)","plate(-34, 12.5, NZ / 2, 16.0, 3.0, NZ), plate(14, 12.5, NZ / 2, 56.0, 3.0, NZ)" in _m,"back-wall plates")
d=rd("kit_v22/pb1r_check.json")
if d:
    _w=[c for c in d["checks"] if c["check"].startswith("NPM cable window")]
    chk("PB1R JL1 and JP leave the board within 10 mm of the NPM cable window",bool(_w) and _w[0]["result"]=="PASS",str(_w[0]["value"]) if _w else "missing")
else: skip("PB1R NPM window")
_bd="docs/design/BENCH_FIRST_ARTICLE_TX.md"
if os.path.exists(_bd):
    _t=open(_bd).read(); _rows=[l for l in _t.splitlines() if re.match(r"^\| (\d+\.\d+) \|",l)]
    _bad=[l[:12] for l in _rows if not l.rstrip().endswith("NOT RUN |")]
    _data=[f for f in __import__("glob").glob("data/bench/**/*",recursive=True) if os.path.isfile(f)]
    chk("bench procedure written, every item marked NOT RUN, and data/bench holds no files while U-BENCH is open (no bench claim without bench data)",len(_rows)>=35 and not _bad and (not _data or "U-BENCH" not in UNV),f"{len(_rows)} items, not NOT RUN: {_bad}, bench files {len(_data)}")
else: chk("bench procedure present (docs/design/BENCH_FIRST_ARTICLE_TX.md)",False,"missing")
d=rd("kit_v22/pb1r_check.json")
if d:
    _f=[c for c in d["checks"] if c["check"].startswith("NPM fit")]
    chk("PB1R fits the neck module: no component body intersects the NPM body v2 (rails, walls, tunnel), the lid or the hot-zone dam v2 (11 bodies did before the Step 7 audit)",bool(_f) and _f[0]["result"]=="PASS",str(_f[0]["value"]) if _f else "missing")
_sd=[n for n in ("NPM_N1_body_with_tunnel_v2","NPM_N3_hot_zone_dam_v2") if os.path.exists(f"stl/shaft_handle/{n}.stl")]
chk("curated STLs carry the NPM v2 parts (body with edge rails, dam at x -5..-3) and the superseded ones are marked",len(_sd)==2 and os.path.exists("stl/shaft_handle/SUPERSEDED.txt"),str(_sd))
for r in res: print(*r)
f=sum(1 for r in res if r[0]=="FAIL"); print("FAILS",f,"SKIPS",sum(1 for r in res if r[0]=="SKIP"),"UNVERIFIED",sum(1 for r in res if r[0]=="UNVERIFIED")); sys.exit(1 if f else 0)
