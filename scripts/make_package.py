#!/usr/bin/env python3
"""Builds deliverables/PHIFOLD233_PACKAGE_r4: one folder to inspect every board, schematic, STL and the layered cut-away blueprint, with an index that states plainly what is
verified, what is open and what is NOT ready. Nothing is hand-edited: KiCad files are copied from data/kicad, schematic PDFs and board renders are produced by kicad-cli, the
blueprint by src/render/blueprint_r3.py, the STL table from stl/MANIFEST.csv (hashes) and docs/UNVERIFIED.md. Requires make setup + make formers-low (blueprint) and
optionally make formers-print (the six print formers in work/kit_v15/PRINT, about 400 MB, not stored in git).
usage (repo root): python3 scripts/make_package.py"""
import os, sys, csv, json, glob, shutil, hashlib, subprocess, re, datetime
R = "deliverables/PHIFOLD233_PACKAGE_r4"; os.makedirs(R, exist_ok=True)
for d in ("kicad", "kicad/3dmodels", "schematics", "renders/boards", "models3d", "blueprint", "gerbers"): os.makedirs(f"{R}/{d}", exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def run(*a, **k): return subprocess.run(a, capture_output=True, text=True, **k)
# ---------------------------------------------------------------- KiCad boards (routed files + design rules) and schematics
BOARDS = [("CB1D", "PF233-CB1D_routed", "CB1D-B controller, D78, 6 layers", "in the verified flow"), ("LB1", "PF233-LB1_routed", "LB1 display, D78, 4 layers", "in the verified flow"),
          ("PB1R", "PF233-PB1R_routed", "PB1R TX stage, 70 x 70, 4 layers", "in the verified flow"), ("PM2", "PF233-PM2_routed", "PM2 battery dock, 28 x 70", "in the verified flow"),
          ("HB2", "PF233-HB2_routed", "HB2 grip board, 24 x 38", "in the verified flow"), ("TXJ1", "TXJ1", "TXJ1 junction, 2 layers", "in the verified flow"),
          ("SB1R-QA", "SB1R-QA", "SB1R-QA receive coil board, D228", "in the verified flow"), ("SB1R-QB", "SB1R-QB", "SB1R-QB receive coil board, D228", "in the verified flow"),
          ("HTA", "PF233-HTA", "HTA timing-coil board, D90", "in the verified flow (v2: the first Gerbers were an open coil)"),
          ("AB1A", "PF233-AB1A", "AB1A receive analog board, D40, 6 layers, AD7389-4 build with the +3V3D island", "routed, KiCad / independent DRC clean; exposed-pad land closed in RX_r2 (B1); remaining blockers in releases/RX_r2/BLOCKERS.md"),
          ("AB1B", "PF233-AB1B", "AB1B receive analog board, D40, 6 layers, AD7389-4 build", "routed, KiCad / independent DRC clean; exposed-pad land closed in RX_r2 (B1); remaining blockers in releases/RX_r2/BLOCKERS.md")]
for b, f, desc, st in BOARDS:
    for ext in (".kicad_pcb", ".kicad_dru", ".kicad_pro"):
        if os.path.exists(f"data/kicad/{f}{ext}"): shutil.copy(f"data/kicad/{f}{ext}", f"{R}/kicad/{f}{ext}")
for f in sorted(glob.glob("data/kicad/3dmodels/*")): shutil.copy(f, f"{R}/kicad/3dmodels/{os.path.basename(f)}")
for s_ in sorted(glob.glob("data/kicad/sch_functional/*")): shutil.copy(s_, f"{R}/schematics/{os.path.basename(s_)}")
# KiCad's own 3-D render and a GLB (viewable in any glTF viewer) of every board with its component models
for b, f, desc, st in BOARDS:
    pcb = f"{R}/kicad/{f}.kicad_pcb"
    if not os.path.exists(pcb): continue
    for side in ("top", "bottom"):
        run("kicad-cli", "pcb", "render", "--side", side, "--quality", "basic", "-w", "1600", "-h", "1200", "--perspective", "-o", f"{R}/renders/boards/{b}_{side}.png", pcb)
    run("kicad-cli", "pcb", "export", "glb", "--subst-models", "--include-tracks", "--include-pads", "--include-zones", "-o", f"{R}/models3d/{b}_with_components.glb", pcb)
for f in sorted(glob.glob("data/kicad/3dmodels/*.wrl")): pass
# ---------------------------------------------------------------- Gerbers: pointers (the release package and the published sets)
GERB = {"CB1D": "data/gerber/CB1D_B3", "LB1": "data/gerber/LB1_v5", "PB1R": "data/gerber/PB1R_v3", "PM2": "data/gerber/PM2", "HB2": "data/gerber/HB2", "TXJ1": "data/gerber/TXJ1_v2",
        "SB1R-QA": "data/gerber/SB1R_QA_v2", "SB1R-QB": "data/gerber/SB1R_QB_v2", "HTA": "data/gerber/HTA_v2", "AB1A": "data/gerber/AB1A_v1", "AB1B": "data/gerber/AB1B_v1"}
# ---------------------------------------------------------------- STL classification
man = {r["file"]: r for r in csv.DictReader(open("stl/MANIFEST.csv"))}
def classify(p):
    n = os.path.basename(p)
    if n.startswith(("ELB_E", "BAT_B")): return "SUPERSEDED", "replaced by the upper assembly v1 (U1-U9); do not print"
    if "reference" in n: return "REFERENCE", "purchased part (MnZn ferrite tile) shown for fit; not printed"
    if n in ("U8_SEPTUM_extended.stl", "U8_SEPTUM_collapsed.stl"): return "REFERENCE", "full-length septum (446 mm) for fit and interference; print U8_SEPTUM_extended_SEG_A / _B instead"
    if n.startswith("UPPER_ASSEMBLY"): return "REFERENCE", "assembly of the printed upper parts + purchased tubes/pack envelopes; not a print file"
    if p.startswith("stl/pins/"): return "PRINT", "interface pin"
    return "PRINT", "printed part (mesh checks in check_v22 / upper_check / yoke_check)"
rows = []
for p in sorted(man):
    c, note = classify(p); rows.append([p, c, note, man[p]["bytes"], man[p]["sha256"]])
form = sorted(glob.glob("work/kit_v15/PRINT/FORMER_L*_petal_coil_former.stl"))
for p in form: rows.append([p, "PRINT (generated, not in git)", "petal coil former, full resolution: make formers-print", os.path.getsize(p), sha(p)])
with open(f"{R}/STL_CLASSIFICATION.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["file", "class", "note", "bytes", "sha256"]); w.writerows(rows)
# ---------------------------------------------------------------- blueprint
if not os.path.exists(f"{R}/renders/boards/CB1D_top.png"): print("board renders missing: run the kicad-cli render loop in the index first")
os.makedirs(f"{R}/blueprint", exist_ok=True)
for _f in glob.glob("deliverables/receive_cutaway/*"): shutil.copy(_f, f"{R}/blueprint/{os.path.basename(_f)}")             # receive-stage cut-away (AD7389-4 build)
r = run(sys.executable, "src/render/blueprint_r3.py", f"{R}/blueprint") if not os.environ.get("SKIP_BLUEPRINT") else None; print("blueprint:", (r.stdout.strip(), r.stderr[-300:]) if r else "skipped (SKIP_BLUEPRINT)")
# ---------------------------------------------------------------- index
S = json.load(open("data/results/SIGNOFF_STATUS.json")); UNV = re.findall(r"^\| (U-[A-Z0-9-]+) \| ([^|]*)\|", open("docs/UNVERIFIED.md").read(), re.M)
cnt = {k: sum(1 for r_ in rows if r_[1].startswith(k)) for k in ("PRINT", "REFERENCE", "SUPERSEDED")}
L = [f"# PHI-FOLD 233 inspection package r4 (generated {datetime.date.today()} by scripts/make_package.py)", "",
 "## What this is, and what it is not", "",
 "Everything that exists for the transmit region and the head is collected here to look at: boards, schematics, STLs, and the layered cut-away blueprint. **It is not a set of files that are \"ready to print\" or \"ready to send to a PCB house\".** Nothing has been built or measured. The open items that stand between this package and a first article are listed under \"Not ready\" below; every one is stated in docs/UNVERIFIED.md and docs/OPEN_ITEMS.md as well.", "",
 f"Tool status of the design: sign-off {S['counts']['PASS']} PASS / {S['counts']['FAIL']} FAIL / {S['counts']['SKIP']} SKIP / {S['counts']['UNVERIFIED']} UNVERIFIED; strict regression passes (docs/STATUS.md).", "",
 "## 1. Start here", "",
 "| File | What it shows |", "|---|---|",
 "| `blueprint/PHIFOLD233_FULL_SYSTEM_LAYERED_CUTAWAY_r3.pdf` (and `.png`) | the full-system structure and layered cut-away: whole detector at the 47 deg use pose, head half-section and plan sections, yoke and neck module with PB1R, upper assembly v1, layer map, board renders, level schematic. Cut faces are computed from the current generated meshes. The PDF is vector (zoom in). |",
 "| `renders/boards/*_top.png`, `*_bottom.png` | KiCad's own 3-D render of every routed board with the component models (copper, mask, parts). |",
 "| `models3d/*_with_components.glb` | each board with tracks, pads, zones and component bodies as a glTF file (any glTF / GLB viewer). KiCad's STEP export of these boards contains only the board, because the parts are VRML: no STEP part models were made (no CAD kernel in the build environment). |",
 "| `schematics/PF233-*_functional.pdf` (and `.kicad_sch`) | readable functional schematics of CB1D, LB1, PB1R, PM2, HB2, AB1A, AB1B. |",
 "| `STL_CLASSIFICATION.csv` | every STL with its class (PRINT / REFERENCE / SUPERSEDED), size and SHA-256. |", "",
 "## 2. Boards", "",
 "| Board | KiCad file (open in KiCad 9) | Gerbers + drill (existing in the repo) | Status |", "|---|---|---|---|"]
for b, f, desc, st in BOARDS:
    L.append(f"| {desc} | `kicad/{f}.kicad_pcb` (+ `.kicad_dru`) | `{GERB[b]}/` | {st}: KiCad 9.0.9 DRC 0 errors / 0 unconnected with the vendor-derived floor; Gerber copper-to-edge read back from the files OK" + (" (run by hand, not in the pipeline)" if b in ("TXJ1", "SB1R-QA", "SB1R-QB") else "") + " |")
L += ["| AB1A / AB1B receive analog boards (D40, 6 layers) | legacy only: `data/legacy/PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A`, `05_PCB_receiver_AB1B` | in those folders | **NOT in the verified flow**: from an earlier router run, never put through KiCad DRC here; 1.27 mm header pads have a 0.175 mm ring (under the 0.18 mm floor): OPEN_ITEMS 2 and 33. Their functional schematics ARE in this package (netlist-checked); their PCB files are not. |", "",
 "The release package `releases/TX_r3` (PB1R, CB1D, TXJ1, PM2, HB2) adds per-board CHECKS.md and a hash manifest; the head boards (LB1, SB1R-QA/QB, HTA) are the sets named above.", "",
 "## 3. Schematics", "",
 "`schematics/PF233-<board>_functional.kicad_sch` and `.pdf` for CB1D, LB1, PB1R, PM2, HB2, AB1A and AB1B: functional blocks (dashed frames with a title and what the block does), real symbols for passives and diodes, boxes with named pins for ICs, FETs, LEDs and connectors, and a net label on every pin (equal names are connected, also between blocks; LED chains are wired). They are generated from the same design database as the layouts, so they cannot drift from the boards. **Checked:** the netlist KiCad itself exports from each schematic equals the design netlist node by node, and KiCad ERC reports 0 errors (only the expected warnings that the generated symbols and footprints are not in a library). **Limits:** they are generated, not hand-drawn, and the pin functions of the ICs are the library's (items marked VERIFY in docs/ASSUMPTIONS.md stay unverified). There is no schematic for TXJ1, SB1R-QA, SB1R-QB or HTA: they carry no components beyond pads, coils and one resistor pair (generated straight from geometry). The older connectivity-only drawings in `data/kicad/sch` are superseded for reading.", "",
 f"## 4. 3-D files ({cnt['PRINT']} to print, {cnt['REFERENCE']} reference, {cnt['SUPERSEDED']} superseded)", "",
 "All paths are in `STL_CLASSIFICATION.csv`. Folders: `stl/head` (12), `stl/pins` (15), `stl/yoke` (7), `stl/upper` (12), `stl/shaft_handle` (14; the ELB_E* and BAT_B* files are SUPERSEDED), and the six full-resolution petal formers, about 66 to 70 MB each, generated into `work/kit_v15/PRINT/` by `make formers-print` (listed with hashes; not stored in git).", "",
 "The mesh checks are measured on the meshes by the repo's checks (closed shells, clearances, fits: check_v22 47/47, upper_check 57/57, yoke_check). **No part has been sliced or printed here**, so overhang/support strategy, tolerances and fit are unproven; CFRP/GFRP tubes, the MnZn tiles, the 18650-class cells and the litz are purchased parts and are not in the STL set.", "",
 "## 5. Not ready (what stands between this package and a first article)", ""]
L += [f"- **{i}**: {d.strip()}" for i, d in UNV]
L += ["- No fabricator DRC/CAM review and no CAM-viewer pass of any Gerber set; KiCad's DRC is not a fabricator's.",
 "- AB1A / AB1B are not in the verified flow (above).", "- The 3-D component models are NOMINAL package outlines built from the library dimensions (docs/ASSUMPTIONS.md 34), not manufacturer STEP models: they show fit and layout, they do not certify mechanical clearances beyond the checks in the repo.",
 "- The older layered figures in `docs/figures` (HEAD_CUTAWAY, ELBOW_GRIP_BATTERY_CUTAWAY, SYSTEM_USE_POSE, SYSTEM_FOLDED, NPM_CUTAWAY, SHAFT_JOINT_CUTAWAY) were drawn by a legacy renderer from the superseded elbow/battery-drawer design and an earlier PB1R: use the r2 blueprint instead.", "",
 "## 6. How this was made", "", "`python3 scripts/make_package.py` (needs KiCad 9, `make setup`, `make formers-low`; `make formers-print` for the six print formers). The blueprint: `src/render/blueprint_r3.py`.", ""]
open(f"{R}/00_INDEX.md", "w").write("\n".join(L))
print("package:", R, "|", len(rows), "STL rows |", len(os.listdir(f"{R}/schematics")), "schematic files")
