#!/usr/bin/env python3
"""Publish generated outputs from work/ into the committed data/ folders (replaces the ad-hoc copy scripts of Steps 1-3).
Version names live in VERSIONS: a changed design gets a NEW name there (and a SUPERSEDED.txt in the old folder), never an overwrite of a released set.
A file is rewritten only if its content differs; KiCad's Gerber creation timestamp is ignored in that comparison so an unchanged board does not churn in git.
usage: scripts/publish_data.py [--check]     --check lists stale files and exits 1 (used by scripts/release_tx.py)"""
import os, re, shutil, glob, subprocess, sys, json
W = "work"; CHECK = "--check" in sys.argv; stale = []; changed = 0
VERSIONS = {   # board -> (gerber folder in data/gerber, work gerber dir, work prefix, published prefix)
    "CB1D": ("CB1D_C2", "kit_v22/GERBER_CB1D_v2", "PF233-CB1D-v2", "PF233-CB1D-C2"),      # C2 (2026-10-28): BMI270 yaw gyro UG on I2C (Pico 21 / 22); C1 SUPERSEDED. C1 (2026-10-28): JLB.3 = LED_CLK from Pico pin 19 (clocked LB1-v6); B3 (Step 5) SUPERSEDED: 1.02 mm JA/JB pads, Bourns 1206 fuse land
    "LB1": ("LB1_v6", "kit_v22/GERBER_LB1_v2", "PF233-LB1-v2", "PF233-LB1-v6"),          # v6 (2026-10-28): 66 x SK9822-EC20 clocked chain + clock buffer U2 / RSC; v5 SUPERSEDED (SK6812MINI-E on a footprint without its cutout)
    "PB1R": ("PB1R_v4", "kit_v22/GERBER_PB1R", "PF233-PB1R", "PF233-PB1R-v4"),          # v4 (2026-10-28): CB7-CB9 pads rotated with their footprint (KiCad pad angle is absolute; v3 SUPERSEDED). v3 (Step 7 audit): parts clear of the NPM board rails and the hot-zone dam; v2 (Step 5) had 11 bodies crossing them
    "TXJ1": ("TXJ1_v2", "kit_v22/GERBER_TXJ1", "TXJ1-", "TXJ1-v2-"),
    "SB1R-QA": ("SB1R_QA_v2", "kit_v22/GERBER_SB1R_QA", "SB1R-QA-", "SB1R-QA-v2-"),
    "HTA": ("HTA_v2", "kit_v18/HTA", "PF233-HTA", "PF233-HTA-v2"),                    # v2 (Step 4): lead A reaches the outer via (the first set was an open coil)
    "PM2": ("PM2", "kit_v22/GERBER_PM2", "PF233-PM2", "PF233-PM2"),                      # first routed set (Step 4)
    "HB2": ("HB2", "kit_v22/GERBER_HB2", "PF233-HB2", "PF233-HB2"),                      # first routed set (Step 4)
    "SB1R-QB": ("SB1R_QB_v2", "kit_v22/GERBER_SB1R_QB", "SB1R-QB-", "SB1R-QB-v2-"),
    "AB1A": ("AB1A_v1", "kit_v22/GERBER_AB1A", "PF233-AB1A", "PF233-AB1A-v1"),           # AD7389-4 build with the +3V3D island (Option 1); KiCad-written hatched planes
    "AB1B": ("AB1B_v1", "kit_v22/GERBER_AB1B", "PF233-AB1B", "PF233-AB1B-v1"),
}
KICAD = {"PF233-AB1A.kicad_pcb": "kit_v3/PCB_AB1A/PF233-AB1A.kicad_pcb", "PF233-AB1B.kicad_pcb": "kit_v3/PCB_AB1B/PF233-AB1B.kicad_pcb", "PF233-CB1D_routed.kicad_pcb": "kit_v22/KICAD/PF233-CB1D_routed.kicad_pcb", "PF233-LB1_routed.kicad_pcb": "kit_v22/KICAD/PF233-LB1_routed.kicad_pcb", "PF233-PB1R_routed.kicad_pcb": "kit_v22/KICAD/PF233-PB1R_routed.kicad_pcb",
         "PF233-PB1R_placed.kicad_pcb": "kit_v6/PB1R/PF233-PB1R.kicad_pcb", "PF233-PM2_routed.kicad_pcb": "kit_v22/KICAD/PF233-PM2_routed.kicad_pcb", "PF233-HTA.kicad_pcb": "kit_v22/KICAD/PF233-HTA.kicad_pcb", "PF233-HB2_routed.kicad_pcb": "kit_v22/KICAD/PF233-HB2_routed.kicad_pcb", "TXJ1.kicad_pcb": "kit_v22/KICAD_TXJ1/TXJ1.kicad_pcb", "SB1R-QA.kicad_pcb": "kit_v22/KICAD_SBQ/SB1R-QA.kicad_pcb", "SB1R-QB.kicad_pcb": "kit_v22/KICAD_SBQ/SB1R-QB.kicad_pcb"}
DRU = {"PF233-AB1A": "AB1A", "PF233-AB1B": "AB1B", "PF233-CB1D_routed": "CB1D", "PF233-LB1_routed": "LB1", "PF233-PB1R_routed": "PB1R", "PF233-PM2_routed": "PM2", "PF233-HTA": "HTA", "PF233-HB2_routed": "HB2", "TXJ1": "TXJ1", "SB1R-QA": "SB1R-QA", "SB1R-QB": "SB1R-QB"}
RESULTS = ["kit_v18/CB1D/PF233-CB1D_BOM.csv", "kit_v18/CB1D/PF233-CB1D_pickplace.csv", "kit_v18/LB1/PF233-LB1_BOM.csv", "kit_v18/LB1/PF233-LB1_pickplace.csv", "kit_v6/PM2/PF233-PM2_BOM.csv", "kit_v6/PM2/PF233-PM2_pickplace.csv", "kit_v6/HB2/PF233-HB2_BOM.csv", "kit_v6/HB2/PF233-HB2_pickplace.csv", "kit_v22/SCHF/PF233-AB1A_functional.pdf", "kit_v22/SCHF/PF233-AB1B_functional.pdf", "kit_v22/kicad_drc_AB1A.json", "kit_v22/indep_drc_AB1A.json", "kit_v22/ab1_island_check_AB1A.json", "kit_v22/gerber_ab1_AB1A.json", "kit_v22/gerber_edge_AB1A.json", "out_board/AB1A_layout.json", "kit_v3/PCB_AB1A/PF233-AB1A_BOM.csv", "kit_v3/PCB_AB1A/PF233-AB1A_pickplace.csv", "kit_v3/PCB_AB1A/PF233-AB1A.net", "kit_v3/PCB_AB1A/PF233-AB1A_check.json", "kit_v22/SCHF/PF233-AB1A_functional_check.json", "kit_v22/kicad_drc_AB1B.json", "kit_v22/indep_drc_AB1B.json", "kit_v22/ab1_island_check_AB1B.json", "kit_v22/gerber_ab1_AB1B.json", "kit_v22/gerber_edge_AB1B.json", "out_board/AB1B_layout.json", "kit_v3/PCB_AB1B/PF233-AB1B_BOM.csv", "kit_v3/PCB_AB1B/PF233-AB1B_pickplace.csv", "kit_v3/PCB_AB1B/PF233-AB1B.net", "kit_v3/PCB_AB1B/PF233-AB1B_check.json", "kit_v22/SCHF/PF233-AB1B_functional_check.json", "kit_v20/route_CB1D.json", "kit_v20/route_LB1.json", "kit_v20/route_PB1R.json", "kit_v22/drc_CB1D.json", "kit_v22/drc_LB1.json", "kit_v22/drc_PB1R.json", "kit_v22/kicad_drc_CB1D.json", "kit_v22/kicad_drc_LB1.json",
           "kit_v22/kicad_drc_PB1R.json", "kit_v22/kicad_drc_TXJ1.json", "kit_v22/models3d_check.json", "kit_v22/kicad_drc_SB1R-QA.json", "kit_v22/kicad_drc_SB1R-QB.json", "kit_v22/gerber_hv_CB1D.json", "kit_v22/gerber_plane_PB1R.json", "kit_v22/gerber_edge_CB1D.json", "kit_v22/gerber_edge_LB1.json", "kit_v22/gerber_edge_PB1R.json", "kit_v22/gerber_edge_PM2.json", "kit_v22/gerber_edge_HTA.json", "kit_v22/kicad_drc_HTA.json", "kit_v22/gerber_edge_HB2.json", "kit_v20/route_PM2.json", "kit_v20/route_HB2.json", "kit_v22/drc_PM2.json", "kit_v22/drc_HB2.json", "kit_v22/kicad_drc_PM2.json", "kit_v22/kicad_drc_HB2.json", "kit_v22/pb1r_check.json",
           "kit_v22/head_crosscheck.json", "kit_v22/fine_check.json", "kit_v22/sch_check.json", "kit_v22/stack_check.json", "kit_v22/system_budget.json", "kit_v22/SYSTEM_STRESS_MARGINS.csv", "kit_v22/wiring_audit.json",
           "kit_v22/trigger_check.json", "kit_v22/tx_system.json", "kit_v22/sbq_geometry.json", "kit_v23/tx_vbus.json", "kit_v23/system_live.json", "kit_v23/hood_tolerance.json", "kit_v23/fw_timeline.json", "kit_v22/pad_orient_check.json", "kit_v23/pf233_timing.h", "kit_v23/output_modes.json", "kit_v23/pf233_output.h", "kit_v23/output_modes.png", "kit_v23/sweep_track.json", "kit_v23/sweep_track.png", "kit_v23/tx_steer_study.json", "kit_v23/TX_ONTIME_LUT.csv", "kit_v23/power_dock_check.json",
           "kit_v6/PB1R/PF233-PB1R_BOM.csv", "kit_v6/PB1R/PF233-PB1R_pickplace.csv", "kit_v6/PB1R/PF233-PB1R.net"]
def norm(b):
    try: t = b.decode()
    except UnicodeDecodeError: return b
    t = re.sub(r"%TF\.CreationDate,[^*]*\*%", "", t); t = re.sub(r"G04 Created by KiCad[^\n]*\n", "", t); t = re.sub(r"; DRILL file[^\n]*\n", "", t)
    t = re.sub(r"; #@! TF\.CreationDate[^\n]*\n", "", t); t = re.sub(r'"CreationDate": "[^"]*"', "", t)
    return t.encode()
sys.path.insert(0, "src/pcb")
def same_file(dst, data):
    """Gerber layers: same copper geometry (KiCad's export is not byte-deterministic); everything else: same text apart from the timestamps"""
    if norm(open(dst, "rb").read()) == norm(data): return True        # identical text apart from timestamps: same geometry, skip the (slow) shapely comparison
    if dst.endswith(".gbr"):
        import tempfile
        from gerber_geom import same_geometry
        with tempfile.NamedTemporaryFile(suffix=".gbr", delete=False) as t: t.write(data)
        try: return same_geometry(dst, t.name)[0]
        finally: os.remove(t.name)
    return norm(open(dst, "rb").read()) == norm(data)
def put(src, dst, transform=None):
    global changed
    if not os.path.exists(src): stale.append(f"missing source {src}"); return
    data = open(src, "rb").read()
    if transform: data = transform(data)
    if os.path.exists(dst) and same_file(dst, data): return
    stale.append(dst)
    if not CHECK: os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, "wb").write(data); changed += 1
for b, (dest, wd, wp, pp) in VERSIONS.items():
    for f in sorted(glob.glob(f"{W}/{wd}/*")):
        n = os.path.basename(f)
        if n.endswith("jogbrjob") or not n.startswith(wp): continue
        put(f, f"data/gerber/{dest}/{pp}{n[len(wp):]}", lambda d, wp=wp, pp=pp: d.replace(wp.encode(), pp.encode()) if wp != pp else d)
for dst, src in KICAD.items(): put(f"{W}/{src}", f"data/kicad/{dst}")
sys.path.insert(0, "src/pcb"); import dru_gen
for base, key in DRU.items():                                    # rule files are generated text (dru_gen.py), not copied
    p = f"data/kicad/{base}.kicad_dru"; want = dru_gen.rules(key); have = open(p).read() if os.path.exists(p) else None
    if have != want:
        stale.append(p)
        if not CHECK: open(p, "w").write(want); changed += 1
for base in DRU:                                                 # empty KiCad project next to each board: ${KIPRJMOD}/3dmodels/ (the package models) resolves only inside a project
    p = f"data/kicad/{base}.kicad_pro"
    if not os.path.exists(p) or open(p).read() != "{}\n":
        stale.append(p)
        if not CHECK: open(p, "w").write("{}\n"); changed += 1
for r in RESULTS: put(f"{W}/{r}", f"data/results/{os.path.basename(r)}")
for f in glob.glob(f"{W}/kit_v22/SCH/*.kicad_sch"): put(f, f"data/kicad/sch/{os.path.basename(f)}")
for f in glob.glob(f"{W}/kit_v22/SCHF/*"):
    if f.endswith((".kicad_sch", ".pdf")): put(f, f"data/kicad/sch_functional/{os.path.basename(f)}")
    elif f.endswith("_check.json"): put(f, f"data/results/{os.path.basename(f)}")
for f in glob.glob(f"{W}/kit_v22/3dmodels/*"): put(f, f"data/kicad/3dmodels/{os.path.basename(f)}")        # VRML package models the KiCad boards link by ${KIPRJMOD}/3dmodels/ (src/pcb/models3d.py)
print(f"publish_data: {len(stale)} {'stale' if CHECK else 'updated'} file(s)" + ("" if CHECK else f", {changed} written"))
for s in stale[:12]: print("  ", s)
sys.exit(1 if (CHECK and stale) else 0)
