#!/usr/bin/env python3
"""Regression: reads results written into work/ by the make targets and compares with the expected numbers. Missing result files are reported as SKIP, not PASS."""
import json, os, sys, glob
W="work"; res=[]
def rd(p):
    try: return json.load(open(os.path.join(W,p)))
    except Exception:
        try: return json.load(open(os.path.join("data","results",os.path.basename(p))))        # clean clone: the published copy of the result (scripts/publish_data.py; --check lists stale ones)
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
if d: st=d["stats"]; chk("LB1-v6 routed 136/136 nets (clocked chain: data + clock per LED), no failures",st["nets_routed"]==st["nets_to_route"]==136 and not st["failures"],str(st))
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
_e={b:rd(f"kit_v22/gerber_edge_{b}.json") for b in ("CB1D","LB1","PB1R","PM2","HB2","HTA","AB1A","AB1B")}
if all(_e.values()): chk("Gerber copper read back from the files: nothing outside the outline (notch included) and >= 0.5 mm to the edge on every layer of CB1D, LB1, PB1R, PM2, HB2, HTA",all(v["ok"] for v in _e.values()),str({b:min(r["min_edge_gap_mm"] for r in v["sets"][list(v["sets"])[0]]["layers"].values() if r["min_edge_gap_mm"] is not None) for b,v in _e.items()}))
else: skip("Gerber edge read-back")
_idrc={b:(json.load(open(f"data/results/indep_drc/{b}.json")) if os.path.exists(f"data/results/indep_drc/{b}.json") else None) for b in ("TXJ1","SB1R-QA","SB1R-QB","HTA")}
_ctl=json.load(open("data/results/indep_drc_controls.json")) if os.path.exists("data/results/indep_drc_controls.json") else None
_bsc=json.load(open("data/results/board_sch/board_sch_check.json")) if os.path.exists("data/results/board_sch/board_sch_check.json") else None
if all(_idrc.values()) and _ctl and _bsc:
    chk("independent geometric DRC (src/pcb/indep_drc.py, not KiCad's engine) on the four boards the router does not touch: TXJ1, SB1R-QA, SB1R-QB, HTA: 0 fails (widths, via and ring, clearance with HV 1.0 mm, holes, edge, connectivity)",
        all(v["n_fail"]==0 and v["zones_checked"] for v in _idrc.values()), str({b:v["fails"] or "none" for b,v in _idrc.items()}))
    chk("independent DRC negative controls: the checker catches a 0.10 mm track, an HV spacing of 0.4 mm, a split net and a pad over the edge, and passes the untouched board",
        _ctl["all_caught"], str([(c["control"][:30], c["caught"]) for c in _ctl["cases"]]))
    chk("board schematics TXJ1, SB1R-QA, SB1R-QB: drawn nets equal the board's pad-to-net assignment, KiCad re-reads the netlist, ERC 0 errors, PDF exported",
        all(v["drawn_check"] and v["kicad_netlist_ok"] and v["pdf"] and v["erc_errors"]==0 for v in _bsc.values()), str({b:(v["parts"],v["nets"],v["erc_errors"]) for b,v in _bsc.items()}))
else: skip("independent DRC / board schematics (run the indep-drc step)")
try: _pc=json.load(open("data/results/print_check.json"))
except Exception: _pc=None
KNOWN_OPEN=set()                                                      # Step 8 locked 15 non-manifold shells; closed by the closing union of src/mech/solid_union.py (0.005 mm dilation + snap): the list is now EMPTY and any open shell FAILS
KNOWN_BIG=set()                                                       # U8_SEPTUM_extended (446 mm) is a REFERENCE; the printable parts are U8_SEPTUM_extended_SEG_A / _B
if _pc:
    _nm=lambda p: p["file"].rsplit("/",1)[-1][:-4]
    _open={_nm(p) for p in _pc["parts"] if not p["closed"]}; _big={_nm(p) for p in _pc["parts"] if not p["fits_build_cube"]}
    chk("print check: every PRINT STL is oriented (outward normals), every PRINT STL is watertight (the 15 shells that were open are closed by the closing union) and fits a 250 mm cube (the 446 mm septum is a REFERENCE, printed as two segments); any open or oversize file FAILS",
        all(p["oriented"] for p in _pc["parts"]) and _open==KNOWN_OPEN and _big==KNOWN_BIG, f"open {len(_open)} (new {sorted(_open-KNOWN_OPEN)}, gone {sorted(KNOWN_OPEN-_open)}), big {sorted(_big)}")
else: skip("print check (src/mech/print_check.py)")
_m3=rd("kit_v22/models3d_check.json")
if _m3:
    _bs=_m3["boards"]; chk("KiCad 3-D models: every component footprint of CB1D, LB1, PB1R, PM2, HB2 and SB1R-QA/QB links an existing VRML model (bare wire pads excepted), each model touches all its pads and stays within its library height + 0.5 mm",_m3["n_errors"]==0 and all(v["with_model"]==v["components"] for v in _bs.values()) and len(_bs)>=7,str({k:(v["with_model"],v["components"]) for k,v in _bs.items()}))
else: skip("KiCad 3-D model links")
_sf={b:rd(f"kit_v22/SCHF/PF233-{b}_functional_check.json") for b in ("PB1R","PM2","HB2","CB1D","LB1","AB1A","AB1B")}
if all(_sf.values()): chk("functional schematics (7 boards): the KiCad netlist exported from each generated schematic equals the design netlist node by node, KiCad ERC reports 0 errors, PDF exported",all(v["n_errors"]==0 and v["pdf"] for v in _sf.values()),str({b:(v["parts"],v["n_errors"]) for b,v in _sf.items()}))
else: skip("functional schematics")
for _b in ("A","B"):                                                  # AB1A / AB1B, AD7389-4 build with the +3V3D island on In4 (afe_layout.py BOARD_CFG7, afe_export.py, kicad_drc.py, indep_drc.py, ab1_island_check.py)
    _il=rd(f"kit_v22/ab1_island_check_AB1{_b}.json"); _kd=rd(f"kit_v22/kicad_drc_AB1{_b}.json"); _id=rd(f"kit_v22/indep_drc_AB1{_b}.json"); _lay=rd(f"out_board/AB1{_b}_layout.json")
    if _il and _kd and _id and _lay:
        _rp=_lay["rep"]
        chk(f"AB1{_b} routing: 0 unrouted nets, 0 fan-out failures, 0 placement errors (incl. same-net slivers) with the committed BOARD_CFG7",not _rp["unrouted"] and not _rp["fanout_failed"] and not _rp["placement_errors"],f"tracks {_rp['tracks']} vias {_rp['vias']}")
        chk(f"AB1{_b} island and zones: 0 opens, 0 shorts, island inside the board, >= 3 mm from the antenna inputs and the OPA2211 pads, no +5VA item inside it, every zone hatched",_il["pass"],f"island {_il['island']} area {_il['island_area_mm2']} mm2, to antenna {_il['island_to_antenna_inputs_mm']} mm, to OPA2211 {_il['island_to_opa2211_mm']} mm")
        chk(f"AB1{_b} KiCad DRC (dru_gen AB1{_b} rules, zones filled): 0 errors, 0 unconnected",not _kd["errors"] and _kd["unconnected"]==0,str(_kd["warnings"]))
        chk(f"AB1{_b} independent DRC (zone-net exemption): 0 fails",_id["n_fail"]==0,f"clearance min {_id['checks']['clearance']['min_gap_mm']} mm")
    else: skip(f"AB1{_b} AD7389-4 build checks")
    _gb=rd(f"kit_v22/gerber_ab1_AB1{_b}.json")
    if _gb:
        _i4=_gb["layers"].get("In4_island",{})
        chk(f"AB1{_b} Gerber read-back (KiCad-written, hatched; gerber_geom): every GND, +5VA and island +3V3D via / pad is copper-connected to its hatch, the island is not joined to the +5VA pour (gap >= 0.16 mm), foreign vias in the island have antipads",_gb["pass"] and _gb["control"]["foreign_vias_not_connected"]==_gb["control"]["foreign_vias_in_island"],f"island copper {_i4.get('island_copper_mm2')} mm2, gap {_i4.get('pour_to_island_gap_mm')} mm, island vias {_i4.get('connected')}/{_i4.get('items')}")
    else: skip(f"AB1{_b} Gerber read-back")
    chk(f"AB1{_b} old Gerbers marked SUPERSEDED (solid planes)",os.path.exists("data/legacy/PHIFOLD233_FINAL_KIT_v3/"+("04_PCB_receiver_AB1A" if _b=="A" else "05_PCB_receiver_AB1B")+"/SUPERSEDED.txt"),"")
if os.path.isdir("releases/RX_r1"):                                   # receive-board release (scripts/release_rx.py): blockers carried, manifest hashes verify, no fabrication-ready wording
    import hashlib, csv as _csv
    _rm=open("releases/RX_r1/RELEASE.md").read()+open("releases/RX_r1/BLOCKERS.md").read()
    _bad=[]
    for _r in _csv.reader(open("releases/RX_r1/MANIFEST.csv")):
        if _r and len(_r)>2 and len(_r[2])==64 and (not os.path.exists(_r[0]) or hashlib.sha256(open(_r[0],"rb").read()).hexdigest()!=_r[2]): _bad.append(_r[0])
    _nman=sum(1 for _ in open("releases/RX_r1/MANIFEST.csv"))-1
    chk("release RX_r1: exposed-pad BLOCKER carried, manifest hashes verify, wording is not 'ready for fabrication'","BLOCKER 1" in _rm and "exposed pad" in _rm and not _bad and "ready for fabrication" not in _rm.replace("not ready for fabrication",""),f"{_nman} files hashed, {len(_bad)} mismatches")
else: skip("release RX_r1")
if os.path.isdir("releases/RX_r2"):                                   # B1: the exposed-pad blocker is closed in RX_r2; RX_r1 stays as written and is marked SUPERSEDED
    import hashlib, csv as _csv
    _rm=open("releases/RX_r2/RELEASE.md").read()+open("releases/RX_r2/BLOCKERS.md").read()
    _bad=[_r[0] for _r in _csv.reader(open("releases/RX_r2/MANIFEST.csv")) if _r and len(_r)>2 and len(_r[2])==64 and (not os.path.exists(_r[0]) or hashlib.sha256(open(_r[0],"rb").read()).hexdigest()!=_r[2])]
    chk("release RX_r2: BLOCKER 1 (exposed pad) removed, RX_r1 marked SUPERSEDED, manifest hashes verify, wording is not 'ready for fabrication'","BLOCKER 1" not in _rm and "PLACEHOLDER" not in _rm and os.path.exists("releases/RX_r1/SUPERSEDED.txt") and not _bad and "ready for fabrication" not in _rm.replace("not ready for fabrication",""),f"{len(_bad)} mismatches")
else: chk("release RX_r2 exists once RX_r1 is marked SUPERSEDED (no silent gap between revisions)",not os.path.exists("releases/RX_r1/SUPERSEDED.txt"),"RX_r2 not cut yet")
if os.path.isdir("releases/TX_r5"):                                   # 2026-10-28: TX_r5 = PB1R-v4 (CB7-CB9 pad angle) + CB1D-C1 (LED_CLK); TX_r4 stays as written and is marked SUPERSEDED
    import hashlib, csv as _csv, glob as _g
    _rm=open("releases/TX_r5/RELEASE.md").read(); _man=list(_csv.reader(open("releases/TX_r5/MANIFEST.csv")))
    _bad=[_r[0] for _r in _man if _r and len(_r)>2 and len(_r[2])==64 and (not os.path.exists(_r[0]) or hashlib.sha256(open(_r[0],"rb").read()).hexdigest()!=_r[2])]
    _po=json.load(open("releases/TX_r5/shared/pad_orient_check.json"))["boards"]
    _ok=(not _bad and os.path.exists("releases/TX_r4/SUPERSEDED.txt") and _g.glob("releases/TX_r5/PB1R/gerber/PF233-PB1R-v4-*") and _g.glob("releases/TX_r5/CB1D/gerber/PF233-CB1D-C1-*")
         and not _g.glob("releases/TX_r5/PB1R/gerber/*-v3-*") and all(_po[b]["ok"] for b in ("PB1R","CB1D","PM2","HB2")) and "ready for fabrication" not in _rm.replace("not ready for fabrication",""))
    chk("release TX_r5: PB1R-v4 and CB1D-C1 Gerbers, KiCad pads = model on every TX board, TX_r4 marked SUPERSEDED, manifest hashes verify",bool(_ok),f"{len(_man)-1} files, {len(_bad)} hash mismatches")
else: chk("release TX_r5 exists once TX_r4 is marked SUPERSEDED (no silent gap between revisions)",not os.path.exists("releases/TX_r4/SUPERSEDED.txt"),"TX_r5 not cut yet")
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
# B1: AD7389-4 land = the saved Ultra Librarian CP-24-25_ADI footprint (nominal), pad by pad; EP inside ADI Fig. 43 (0.40-0.60 SQ max land 0.6096)
import zipfile as _zf
_z="data/seed/footprints/UltraLibrarian_AD7389-4BCPZ_CP-24-25_ADI.zip"
if os.path.exists(_z):
    _t=_zf.ZipFile(_z).read("KiCADv6/footprints.pretty/CP-24-25_ADI.kicad_mod").decode()
    _ul={m[0]:(float(m[1]),float(m[2]),float(m[4]),float(m[5])) if m[3]=="90" else (float(m[1]),float(m[2]),float(m[4]),float(m[5])) for m in re.findall(r'pad "(\d+)" smd rect \(at (\S+) (\S+)(?: (\d+))?\) \(size (\S+) (\S+)\)',_t)}
    _ulr={k:((x,y,h,w) if (k!="25" and abs(abs(x)-1.9685)<1e-3) else (x,y,w,h)) for k,(x,y,w,h) in _ul.items()}        # rotated 90: KiCad size is (w,h) before rotation
    _o=_sp.run([sys.executable,"-c","import sys,json; sys.path.insert(0,'src/pcb'); import afe_design as D; print(json.dumps([(n,x,y,w,h) for n,x,y,w,h,s in D.LIB['AD7389']['pads']]))"],capture_output=True,text=True).stdout
    _ours={n:(x,y,w,h) for n,x,y,w,h in json.loads(_o)} if _o.strip() else {}
    _bad=[k for k in _ulr if k not in _ours or max(abs(a-b) for a,b in zip(_ulr[k],_ours[k]))>1e-3]
    chk("AB1 AD7389-4 land equals the Ultra Librarian CP-24-25_ADI footprint pad by pad (24 terminals 0.254 x 0.762 at 1.9685, EP 0.6096 SQ = Fig. 43 EP max)",len(_ulr)==25 and not _bad and len(_ours)==25,f"mismatch {_bad[:5]}")
else: chk("AB1 AD7389-4 land source on disk",False,_z+" missing")
# B4: input series resistors: signal channels (GX/GY = QUAD-A/B) 100 ohm as in sbq_damp2; spare/idle X8, Y8, MONO 1 kohm
_o=_sp.run([sys.executable,"-c","import sys,json; sys.path.insert(0,'src/pcb'); import afe_design as D; print(json.dumps(D.RS))"],capture_output=True,text=True).stdout
_rs=json.loads(_o) if _o.strip() else {}
_sd=re.search(r"^L, Rc, RS, .*?=\s*[0-9.e-]+,\s*[0-9.]+,\s*([0-9.]+)",open("src/sim/sbq_damp2.py").read(),re.M)
chk("AB1 RS: GX/GY 100 ohm (= sbq_damp2 RS), X8/Y8/MONO 1 kohm (B4 decision, CORRECTIONS)",_rs=={"GX":100,"GY":100,"X8":1000,"Y8":1000,"MONO":1000} and _sd is not None and float(_sd.group(1))==100,f"{_rs} sbq_damp2 {_sd.group(1) if _sd else 'n/a'}")
# B6: AD7389-4 2-wire readout model (CB1D firmware side), checked against the board netlists
_r=_sp.run([sys.executable,"src/sim/ad7389_readout.py"],capture_output=True,text=True)
chk("AD7389-4 readout model (B6): 2-wire SDOA = A then C, SDOB = B; channel mapping and SDO/SDI wiring read from afe_design; one-frame latency; no data before 5 ms, settled from 11 ms; SDI low writes nothing",_r.returncode==0,f"{_r.stdout.count('PASS')} pass, {_r.stdout.count('FAIL')} fail")
# B5: physical JA/JB -> J2 link path on the meshes (src/mech/link_path_check.py, run in work/): straight up is blocked; the decided FFC concept passes every passage row
if all(os.path.exists(os.path.join(W,f)) for f in ("kit_v22/SEPTUM_FRAME_v5.stl","kit_v22/SPINE_COMB_v5.stl","out_board/AB1A_layout.json","kit_v18/CB1D/PF233-CB1D_pickplace.csv")):
    _lp=os.path.join(W,".link_path_check.json"); _r=_sp.run([sys.executable,os.path.abspath("src/mech/link_path_check.py"),os.path.abspath(_lp)],cwd=W,capture_output=True,text=True)
    _d=json.load(open(_lp)) if _r.returncode==0 and os.path.exists(_lp) else {}
    _dec=_d.get("decision",{}); _ffc=_d.get(_dec.get("choice",""),{})
    _blk=[c for c in _ffc.get("checks",[]) if "straight vertical" in c["check"]]
    chk("B5 link path (CB1D JA/JB -> AB1 J2): straight up blocked by the septum / cloth window, the FFC concept through the 90 deg spine duct passes every row on the meshes; the header + IDC ribbon concept does not",bool(_dec) and _ffc.get("n_fail",1)==0 and len(_blk)==2 and _dec.get("header_ribbon_fails",0)>0,f"FFC fails {_ffc.get('n_fail')}, ribbon fails {_dec.get('header_ribbon_fails')}")
else: skip("B5 link path check (needs v5, parts, pcb-ab1, pcb-cb1d)")
# B9: rip-up router study and the RS 33 / differential option (static evidence in data/results/studies)
try:
    _st=json.load(open("data/results/studies/router_study_b9.json"))["summary"]["both"]; _dv=json.load(open("data/results/studies/ab1_drive_option.json"))
    chk("B9 router study: rip-up router passes the production gates on at least as many perturbed placements as the single-pass router, and the default stays single-pass",_st["ripup_wins"]>=_st["single_pass_wins"] and _st["valid_cases"]>=20,f"single {_st['single_pass_wins']}/{_st['valid_cases']}, rip-up {_st['ripup_wins']}/{_st['valid_cases']}")
    chk("B9 drive option modeled from datasheet ratings (BAV199, 74LVC1G66): the clamp never conducts in a modeled case at RS 33, the first clean gate does not move, the default is unchanged",_dv["verdict"]["default_changed"] is False and _dv["clamp"]["RS 33"]["overvoltage_for_IF_160mA_V"]>100*_dv["inputs"]["worst_modeled_leak_V"] and max(_dv["first_clean_gate_us_worst_leak"].values())-min(_dv["first_clean_gate_us_worst_leak"].values())<0.2,str(_dv["verdict"]["noise_gain_pct"])+" % EIN")
except FileNotFoundError: chk("B9 study evidence on disk (data/results/studies)",False,"missing")
# B8: TXJ1 / SB1R-QA / SB1R-QB BOM and pick-and-place regenerate from the KiCad boards exactly as committed (src/pcb/kicad_bom_pnp.py)
import tempfile as _tf, filecmp as _fc
_td=_tf.mkdtemp(); _ok=[]
for _b in ("TXJ1","SB1R-QA","SB1R-QB"):
    _r=_sp.run(["/usr/bin/python3","src/pcb/kicad_bom_pnp.py",f"data/kicad/{_b}.kicad_pcb",_b,_td],capture_output=True,text=True)
    _ok.append(_r.returncode==0 and all(os.path.exists(f"docs/delivery/boards/{_b}_{k}.csv") and _fc.cmp(f"{_td}/{_b}_{k}.csv",f"docs/delivery/boards/{_b}_{k}.csv",shallow=False) for k in ("BOM","pickplace")))
chk("B8 BOM + pick-and-place for TXJ1, SB1R-QA, SB1R-QB regenerate identically from data/kicad (y-up, board-centre origin)",all(_ok),str(_ok))
_fp=rd("../data/results/formers_print_check.json") or (json.load(open("data/results/formers_print_check.json")) if os.path.exists("data/results/formers_print_check.json") else None)
chk("six print-resolution formers (make formers-print, not in git): closed, oriented, inside a 250 mm build volume (data/results/formers_print_check.json)",bool(_fp) and len(_fp["formers"])==6 and _fp["all_ok"],str([f["bbox_mm"][0] for f in _fp["formers"]]) if _fp else "missing")
# mesh/plane sections (src/mech/mesh_section.py, used by blueprint_r3, cutaway_receive, pb1r_check): the cut must not depend on the vertex order inside a triangle
sys.path.insert(0,"src/mech"); import mesh_section as _ms, numpy as _np, struct as _struct
def _tris(p):
    b=open(p,"rb").read(); k=_struct.unpack("<I",b[80:84])[0]
    return _np.frombuffer(b,dtype=_np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]),count=k,offset=84)["v"].reshape(-1,3,3).astype(float)
_sec=[]
for _f,_ax,_v in (("stl/head/CORE_CYLINDER_v5_integrated.stl",1,0.0),("stl/head/LOTUS_HOOD_CARRIER_v3_butted.stl",2,31.0),("stl/shaft_handle/NPM_N1_body_with_tunnel_v2.stl",2,20.0)):
    _T=_tris(_f); _a=[(_g.area if _g is not None else 0.0) for _g in (_ms.section(_T,_ax,_v),_ms.section(_np.roll(_T,1,axis=1),_ax,_v),_ms.section(_T[:,::-1],_ax,_v))]
    _sec.append((os.path.basename(_f),round(_a[0],2),_a[0]>1.0 and max(_a)-min(_a)<1e-6*max(_a)))
chk("mesh sections non-empty and identical under vertex rotation / reversal (CORRECTIONS: empty or partial sections before mesh_section.py)",all(x[2] for x in _sec),str([x[:2] for x in _sec]))
# package: no STL that its folder's SUPERSEDED.txt lists is shipped as a print file; the clickable viewer links only files that exist
_PK="deliverables/PHIFOLD233_PACKAGE_r5"
_sup=sorted({m for f in glob.glob("stl/*/SUPERSEDED.txt") for m in re.findall(r"^- (\S+\.stl) ->",open(f).read(),re.M)})
_bad=[m for m in _sup if glob.glob(f"{_PK}/stl_print/*/{m}")]
chk("package stl_print holds no STL listed in a SUPERSEDED.txt",bool(_sup) and not _bad,f"{len(_sup)} superseded, shipped: {_bad}")
if os.path.exists(f"{_PK}/viewer.html"):
    _m=re.search(r"const D = (\{.*?\});\n",open(f"{_PK}/viewer.html").read(),re.S); _D=json.loads(_m.group(1).replace("<\\/","</"))
    _hr=[f["href"] for i in _D["items"] for f in i["files"]]+[f["href"] for f in _D["docs"]]+[t for i in _D["items"] for t in i.get("thumbs",[])]
    _miss=[h for h in _hr if not os.path.exists(os.path.join(_PK,h))]; _incut={i["id"] for i in _D["items"] if i["in_cut"]}
    chk("cut-away viewer: every file link resolves, every board has KiCad + Gerber links, every cut face belongs to an item",not _miss and all(any(f["fmt"]=="Gerber + drill" for f in i["files"]) and any(f["fmt"]=="KiCad board" for f in i["files"]) for i in _D["items"] if i["kind"]=="board") and all(f["id"] in _incut for P in _D["panels"].values() for f in P["faces"]),f"{len(_hr)} links, {len(_miss)} missing, {len(_D['items'])} items")
else: skip("cut-away viewer (python3 src/render/viewer_r2.py after make_package.py)")
# viewer r2 system model: the JavaScript twin reproduces every Python golden case (src/sim/system_live.py) within 0.5 % (1 % for the current-zero time, read on a 10 ns grid)
if os.path.exists("data/results/system_live.json"):
    _r=_sp.run(["node","tests/system_live_golden.js",os.path.abspath("src/render/system_live.js"),os.path.abspath("data/results/system_live.json")],capture_output=True,text=True)
    _w=json.loads(_r.stdout.strip().splitlines()[-1])["worst_pct"] if _r.returncode==0 and _r.stdout.strip() else None
    chk("system model: JavaScript (viewer) = Python reference on every golden case (21 cases: 3 pack voltages x 3 modes x 2 clamp cases + 3 L/R sweeps)",bool(_w) and all(v<=(1.0 if k=="t_zero_us" else 0.5) for k,v in _w.items()),str(_w) if _w else (_r.stderr[-300:] or "node failed"))
    _sl=json.load(open("data/results/system_live.json")); _sb=json.load(open("data/results/system_budget.json"))
    chk("system_budget power comes from the system model (no hard-coded watts)",isinstance(_sb.get("power",{}).get("model"),str) and "system_live" in _sb["power"]["model"],str({k:v for k,v in _sb.get("power",{}).items() if k!="model"}))
else: skip("system model golden replay (make step S=system-live)")
# solid_union study: the default stays the committed path (rebuild and batch both changed the solid by more than 1 um on the replayed unions)
try:
    _su=json.load(open("data/results/studies/su_study.json")); _mx=max((v.get("roundtrip_dev") or {}).get("max_vertex_to_surface_um",0) for v in _su.values())
    _src=open("src/mech/solid_union.py").read()
    chk("solid_union: canonical-rebuild path stays OFF by default (study max deviation over 1 um; docs/PERFORMANCE.md)",'os.environ.get("SOLID_UNION_REBUILD", "0") == "1"' in _src and _mx>1.0 and len(_su)==15,f"{len(_su)} unions, rebuild max {_mx} um")
except FileNotFoundError: chk("solid_union study evidence (data/results/studies/su_study.json)",False,"missing")
# P1 manufacturing margin audit (src/pcb/fab_margin.py): every released board measured at or above every fabrication floor; margins are reported, not gated
try:
    _fm=json.load(open("data/results/fab_margin_audit.json"))["boards"]
    chk("fab margin audit: all 12 released boards at or above every floor (copper gap, HV 1.0 mm, edge, drill-drill, drill-copper, via / PTH ring, track)",len(_fm)==12 and all(b["pass"] for b in _fm.values()),
        "; ".join(f"{k} {b['min_margin_mm']} ({b['min_margin_of']})" for k,b in _fm.items()))
except FileNotFoundError: chk("fab margin audit evidence (data/results/fab_margin_audit.json)",False,"missing")
# output modes step 1 (src/sim/output_modes.py): audio / LED renderers from one descriptor; idle slot, latency, LED rail cap, silent search, distinct voices and colours
d=rd("kit_v23/output_modes.json")
if d: chk("output modes (AUDIO_ONLY / LED_ONLY / COMBINED): LED and link bursts only in the idle slot, latency <= 50 ms, LED rail <= 0.35 A, silent below threshold, distinct voices / colours, grayscale 0 / 255",
          d["ok"] and set(d["prf"])=={"scan","mid","boost"} and all(len(p["schedule"])==3 for p in d["prf"].values()),
          f"worst LED {d['checks']['worst_led_A']} A (uncapped {d['constants']['worst_uncapped_A']}), latency {[p['latency_ms'] for p in d['prf'].values()]} ms")
else: skip("output modes model")
# sweep tracking and pinpoint (src/sim/sweep_track.py): axis turns continuously over a pass, centre null, side needs the sweep direction, pinpoint under noise
d=rd("kit_v23/sweep_track.json")
if d: _c=d["checks"]; chk("sweep track: axis turns continuously, centre null, mod-180 ambiguity confirmed and resolved with the sweep direction, pinpoint median <= 15 mm at SNR 10",
          d["ok"] and _c["mirror_scene_identical_without_direction"] and _c["side_resolved_with_sweep_direction"] and _c["centre_null"],
          f"boost x{_c['boost_signal_ratio']} ({_c['boost_gain_dB']} dB); noisy p95 {max(v['p95_mm'] for v in d['pinpoint_noise'].values())} mm")
else: skip("sweep tracking model")
# TX steering study (src/sim/tx_steer_study.py): single offset coils leak volts into RX-Q; push-pull pairs are nulled by symmetry and make a horizontal field
d=rd("kit_v23/tx_steer_study.json")
if d: _c=d["checks"]; chk("TX steering study: full coil nulled, single offset coil steers but leaks >= 10 V, push-pull pairs null to both quads with a horizontal field below the centre",
          d["ok"] and _c["single_coil_leak_V_min"]>=10, f"single leak {_c['single_coil_leak_V_min']} V; pair field / full at 100-300 mm {_c['pair_field_rel_full']}")
else: skip("TX steering study")
# AU1 audio board cross-check (src/pcb/au1_check.py): buck / LDO / amplifier operating points against the datasheet limits, link, fuse, harness ends
d=rd("kit_v23/au1_check.json")
if d: chk("AU1 audio board: every electrical cross-check passes (buck 5 V, inductor peak, LDO dropout, amp swing, fuse, harness ends)",all(c["result"]=="PASS" for c in d["checks"]) and len(d["checks"])>=20,
          f"{len(d['checks'])} checks; buck {d['operating']['buck_V']} V, L peak {d['operating']['ipk_A']} A, input {d['operating']['iin_A']} A")
else: skip("AU1 cross-check")
# receive DSP reference (src/sim/dsp_ref.py): tau estimator at the Cramer-Rao bound, class / bearing at SNR 10, ground rejection with the held-ground ridge fit
d=rd("kit_v23/dsp_ref.json")
if d: _a=d["accuracy_vs_snr"]; chk("DSP reference: tau error within 1.5 x Cramer-Rao at SNR 30, class >= 80 % and bearing <= 5 deg at SNR 10, 0 false detections over varying ground, small gold over ground found",
          d["ok"], f"tau/CRB {_a['30']['tau_err_rms_over_crb']}, class {_a['10']['class_correct_pct']} %, bearing {_a['10']['bearing_err_median_deg']} deg, ground false {d['ground_rejection']['false_rate_pct']} %")
else: skip("DSP reference")
# firmware host tests (fw/, make -C fw test): C core = Python reference, AU1 voice, end-to-end head <-> link <-> AU1
d=rd("kit_v23/fw_test.json")
if d: chk("firmware host tests: C DSP = Python reference, AU1 voice, end-to-end (silent over ground, class, side, one centre event, mode rules), all with -Werror",d["ok"] and d["total_checks"]>=60,
          "; ".join(f"{k.split()[0]} {v['checks']}/{v['fails']} fail" for k,v in d["tests"].items()))
else: skip("firmware host tests")
# KiCad pad geometry = placement model, pad by pad (src/pcb/pad_orient_check.py): the KiCad pad angle is absolute; a missing angle left rotated pads unrotated
d=rd("kit_v22/pad_orient_check.json")
if d: _b=d["boards"]; chk("KiCad pads = placement model on LB1, CB1D, PB1R, PM2, HB2, AU1 (centre and size within 0.005 mm)",len(_b)==6 and all(v["ok"] for v in _b.values()),"; ".join(f"{k} {v.get('pads_compared')} pads {v.get('mismatches')} off" for k,v in _b.items()))
else: skip("KiCad pad orientation check")
# LB1-v6 clocked LEDs (src/pcb/led_upgrade_check.py): SK9822-EC20 at the placed positions and chain rotations, pad gap and body gap floors, 0.3 mm under the roof
try:
    _lu=json.load(open("data/results/led_upgrade_check.json")); _f=_lu["fit"]["SK9822-EC20, as placed"]
    chk("LB1-v6 LEDs: SK9822-EC20 fits as placed (pad gap >= 0.16, body gap >= 0.2, roof gap >= 0.3 mm)",_lu["chosen_ok"] and _f["ok"] and _lu["height"]["SK9822-EC20"]["gap_mm"]>=0.3,f"pad gap {_f['min_pad_gap_mm']} body gap {_f['min_body_gap_mm']} roof {_lu['height']['SK9822-EC20']['gap_mm']}")
except (FileNotFoundError, KeyError): chk("LB1-v6 LED fit evidence (data/results/led_upgrade_check.json)",False,"missing")
# P2 exact potting volumes (src/mech/potting_volumes.py): positive, inside their envelopes, lower <= upper bound, every zone with a fill port and a vent
try:
    _pv=json.load(open("data/results/potting_volumes.json")); _n=_pv["npm"]; _a=_pv["l4_absorber"]
    _ok=all(0<_n[z]["free_cm3_lower"]<=_n[z]["free_cm3_upper_no_parts"]<_n["envelope_cm3"] and _n["fill_vent"][z]["fill"] and _n["fill_vent"][z]["vent"] for z in ("hot_zone","main_zone")) and 0<_a["free_cm3"]<_a["envelope_cm3"]
    chk("potting volumes from exact mesh booleans: NPM hot / main zone and L4 absorber cell positive, bounded, filled and vented",_ok,f"NPM hot {_n['hot_zone']['free_cm3_lower']}-{_n['hot_zone']['free_cm3_upper_no_parts']} cm3, main {_n['main_zone']['free_cm3_lower']}-{_n['main_zone']['free_cm3_upper_no_parts']} cm3, L4 {_a['free_cm3']} cm3")
except FileNotFoundError: chk("potting volume evidence (data/results/potting_volumes.json)",False,"missing")
# P3 hood placement tolerance (src/sim/hood_tolerance.py): baseline reproduces the hood v3 gain, every sweep has a slope and a tolerance
_ht=rd("kit_v23/hood_tolerance.json")
if _ht:
    _g=_ht["baseline_gain_pct"]; _sw=_ht["sweeps"]
    chk("hood tolerance: baseline = hood v3 upper-bound gain (12.9-14.2 % at 200 mm) and a field slope / placement tolerance for each of 5 placement errors",12.9<=float(_g["200"])<=14.2 and len(_sw)==5 and all(v["tolerance_mm_for_0p5pct_at_200"] for v in _sw.values()),
        "; ".join(f"{v['param']} {v['slope_pct_per_mm_at_200']} %/mm -> +-{v['tolerance_mm_for_0p5pct_at_200']} mm" for v in _sw.values()))
else: skip("hood tolerance study (make step S=hood-tol)")
# P5 firmware timing model (src/sim/fw_timeline.py): every mode fits its period, no LED stream inside a receive window, >= 3 ADC frames in the first gate, header in step
_ft=rd("kit_v23/fw_timeline.json")
if _ft:
    _hdr=open("work/kit_v23/pf233_timing.h").read() if os.path.exists("work/kit_v23/pf233_timing.h") else open("data/results/pf233_timing.h").read()
    _okh=f"#define PF_N_GATES {len(_ft['inputs']['gates_us'])}u" in _hdr and f"#define PF_FIRST_GATE_NS {round(_ft['inputs']['first_gate_us']*1000)}u" in _hdr and (_ft.get("led_policy")!="dark_during_sweep" or "#define PF_LED_DARK_DURING_SWEEP 1u" in _hdr)
    chk("firmware timeline: 3 modes fit their period with >= 10 % spare, LED stream only in a quiet slot, LEDs dark during sweeps, >= 3 ADC frames in the first gate, generated header matches the model",_ft["ok"] and _okh and _ft["inputs"]["sclk_min_hz_for_3_frames"]<_ft["inputs"]["adc_sclk_max_hz"],
        "; ".join(f"{k} spare {v['spare_pct']} %, LED cost {v['led']['prf_cost_pct']} %" for k,v in _ft["modes"].items())+f"; SCLK >= {_ft['inputs']['sclk_min_hz_for_3_frames']/1e6:.1f} MHz")
else: skip("firmware timeline (make step S=fw-timeline)")
for r in res: print(*r)
f=sum(1 for r in res if r[0]=="FAIL"); print("FAILS",f,"SKIPS",sum(1 for r in res if r[0]=="SKIP"),"UNVERIFIED",sum(1 for r in res if r[0]=="UNVERIFIED")); sys.exit(1 if f else 0)
