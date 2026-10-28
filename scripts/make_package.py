#!/usr/bin/env python3
"""Builds deliverables/PHIFOLD233_PACKAGE_r5 (NEXT: r6, held by the owner 2026-10-28 until the open firmware / software / integration work is done; r5 ships CB1D-B3, LB1-v5 and PB1R-v3 Gerbers, see data/gerber/*/SUPERSEDED.txt; r4 SUPERSEDED: it listed STLs and pointed at Gerber folders; r5 holds every print / review file): one folder to inspect every board, schematic, STL and the layered cut-away blueprint, with an index that states plainly what is
verified, what is open and what is NOT ready. Nothing is hand-edited: KiCad files are copied from data/kicad, schematic PDFs and board renders are produced by kicad-cli, the
blueprint by src/render/blueprint_r3.py, the STL table from stl/MANIFEST.csv (hashes) and docs/UNVERIFIED.md. Requires make setup + make formers-low (blueprint) and
optionally make formers-print (the six print formers in work/kit_v15/PRINT, about 400 MB, not stored in git).
usage (repo root): python3 scripts/make_package.py"""
import os, sys, csv, json, glob, shutil, hashlib, subprocess, re, datetime
R = "deliverables/PHIFOLD233_PACKAGE_r5"; os.makedirs(R, exist_ok=True)
for d in ("kicad", "kicad/3dmodels", "schematics", "renders/boards", "models3d", "blueprint", "manufacturing", "stl_print", "stl_reference"): os.makedirs(f"{R}/{d}", exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def run(*a, **k): return subprocess.run(a, capture_output=True, text=True, **k)
# ---------------------------------------------------------------- KiCad boards (routed files + design rules) and schematics
BOARDS = [("CB1D", "PF233-CB1D_routed", "CB1D-C2 controller, D78, 6 layers (LED clock on JLB.3, BMI270 yaw gyro)", "in the verified flow"), ("LB1", "PF233-LB1_routed", "LB1-v6 display, D78, 4 layers, 66 x SK9822-EC20 clocked", "in the verified flow"),
          ("PB1R", "PF233-PB1R_routed", "PB1R-v5 TX stage, 70 x 70, 4 layers (JL1 AWG12 solder holes, CB7-CB9 pad angle)", "in the verified flow"), ("PM2", "PF233-PM2_routed", "PM2 battery dock, 28 x 70", "in the verified flow"),
          ("HB2", "PF233-HB2_routed", "HB2-B grip board, 24 x 38 (audio link pass-through)", "in the verified flow"), ("AU1", "PF233-AU1_routed", "AU1 audio board, 36 x 44, 4 layers", "in the verified flow"), ("TXJ1", "TXJ1", "TXJ1 junction, 2 layers", "in the verified flow"),
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
GERB = {"CB1D": "data/gerber/CB1D_C2", "LB1": "data/gerber/LB1_v6", "PB1R": "data/gerber/PB1R_v5", "PM2": "data/gerber/PM2_B", "HB2": "data/gerber/HB2_B", "AU1": "data/gerber/AU1", "TXJ1": "data/gerber/TXJ1_v2",
        "SB1R-QA": "data/gerber/SB1R_QA_v2", "SB1R-QB": "data/gerber/SB1R_QB_v2", "HTA": "data/gerber/HTA_v2", "AB1A": "data/gerber/AB1A_v1", "AB1B": "data/gerber/AB1B_v1"}
# ---------------------------------------------------------------- STL classification
man = {r["file"]: r for r in csv.DictReader(open("stl/MANIFEST.csv"))}
SUPER = {m.group(1): m.group(2) for f in glob.glob("stl/*/SUPERSEDED.txt") for m in re.finditer(r"^- (\S+\.stl) -> (\S+\.stl)", open(f).read(), re.M)}   # the folder's own superseded list
def classify(p):
    n = os.path.basename(p)
    if not n.endswith(".stl"): return "NOTE", "text note kept next to the STLs (copied with them); not a print file"
    if n in SUPER: return "SUPERSEDED", f"replaced by {SUPER[n]} ({os.path.dirname(p)}/SUPERSEDED.txt); do not print"
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
r = run(sys.executable, "src/render/blueprint_r3.py", f"{R}/blueprint", env=dict(os.environ, BLUEPRINT_RECORD=f"{R}/blueprint/cutaway_faces.json")) if not os.environ.get("SKIP_BLUEPRINT") else None; print("blueprint:", (r.stdout.strip(), r.stderr[-300:]) if r else "skipped (SKIP_BLUEPRINT)")
# ---------------------------------------------------------------- manufacturing set per board (copies, not pointers): Gerber + drill zip, BOM, pick-and-place, netlist, layer PDF, bare-board STEP
import zipfile
BOMS = {b: (f"data/results/PF233-{b}_BOM.csv", f"data/results/PF233-{b}_pickplace.csv") for b in ("AB1A", "AB1B", "AU1", "CB1D", "HB2", "LB1", "PB1R", "PM2")}
BOMS.update({b: (f"docs/delivery/boards/{b}_BOM.csv", f"docs/delivery/boards/{b}_pickplace.csv") for b in ("TXJ1", "SB1R-QA", "SB1R-QB")})
NETS = {"AB1A": "data/results/PF233-AB1A.net", "AB1B": "data/results/PF233-AB1B.net", "PB1R": "data/results/PF233-PB1R.net", "CB1D": "work/kit_v18/CB1D/PF233-CB1D.net"}
mfg = []
for b, f, desc, st in BOARDS:
    d = f"{R}/manufacturing/{b}"; os.makedirs(d, exist_ok=True); pcb = f"{R}/kicad/{f}.kicad_pcb"; got = []
    gd = GERB.get(b); files = sorted(glob.glob(f"{gd}/*")) if gd else []
    if files:
        with zipfile.ZipFile(f"{d}/{b}_gerber_drill.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for g_ in files: z.write(g_, os.path.basename(g_))
        got.append(f"gerber+drill ({len(files)} files)")
    for src in BOMS.get(b, ()) + ((NETS[b],) if b in NETS else ()):
        if os.path.exists(src): shutil.copy(src, f"{d}/{os.path.basename(src)}"); got.append(os.path.basename(src).split(".")[-1] if src.endswith(".net") else os.path.basename(src).rsplit("_", 1)[-1])
    if os.path.exists(pcb):
        import re as _re
        ncu = len(set(_re.findall(r'\(\d+ "(In\d+\.Cu)" (?:signal|power|mixed|jumper)', open(pcb).read())))                         # inner copper layers declared by the board
        lay = ",".join(["F.Cu"] + [f"In{k}.Cu" for k in range(1, ncu + 1)] + ["B.Cu", "F.Silkscreen", "B.Silkscreen", "F.Mask", "B.Mask", "Edge.Cuts"])
        r_ = run("kicad-cli", "pcb", "export", "pdf", "--layers", lay, "--mode-separate", "-o", f"{d}/", pcb); got.append(f"layer PDFs ({2 + ncu} copper)" if r_.returncode == 0 else "layer PDF FAILED")
        r_ = run("kicad-cli", "pcb", "export", "step", "--subst-models", "--force", "-o", f"{d}/{b}_board.step", pcb); got.append("STEP (board)" if r_.returncode == 0 and os.path.exists(f"{d}/{b}_board.step") else "STEP FAILED")
    mfg.append((b, desc, got))
# ---------------------------------------------------------------- STL files themselves: PRINT and REFERENCE copied (SUPERSEDED listed only); the six print formers if generated (not in git)
for p_, c, note, *_ in rows:
    if p_.startswith("work/"): continue
    if c in ("PRINT", "NOTE"): dst = f"{R}/stl_print/{p_[4:]}"
    elif c == "REFERENCE": dst = f"{R}/stl_reference/{p_[4:]}"
    else: continue
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(p_, dst)
if form:
    os.makedirs(f"{R}/stl_print/formers", exist_ok=True)
    for p_ in form: shutil.copy(p_, f"{R}/stl_print/formers/{os.path.basename(p_)}")
    open(f"{R}/stl_print/formers/.gitignore", "w").write("*.stl\n")                                   # about 420 MB: in the container only; rebuild with make formers-print (hashes in STL_CLASSIFICATION.csv)
# ---------------------------------------------------------------- index
S = json.load(open("data/results/SIGNOFF_STATUS.json")); UNV = re.findall(r"^\| (U-[A-Z0-9-]+) \| ([^|]*)\|", open("docs/UNVERIFIED.md").read(), re.M)
BL = json.load(open("data/handoff/blockers.json"))["items"]
cnt = {k: sum(1 for r_ in rows if r_[1].startswith(k)) for k in ("PRINT", "REFERENCE", "SUPERSEDED")}
rel = lambda pre: sorted(glob.glob(f"releases/{pre}_r*"), key=lambda x: int(x.rsplit("_r", 1)[1]))[-1] if glob.glob(f"releases/{pre}_r*") else "none"
L = [f"# PHI-FOLD 233 prototype review package r5 (generated {datetime.date.today()} by scripts/make_package.py)", "",
 "## What this is, and what it is not", "",
 "Every file needed to REVIEW a first prototype print and board order, regenerated by the pipeline from the generators (never hand-edited). **Everything is MODELED or tool-checked: nothing has been built, printed, fabricated or measured. It is not declared ready to print or ready for fabrication**: a fabricator DRC / CAM-viewer pass (B2) and bench data (B10) are open, and the open items in section 5 stand between this package and a first article.", "",
 f"Tool status: sign-off {S['counts']['PASS']} PASS / {S['counts']['FAIL']} FAIL / {S['counts']['SKIP']} SKIP / {S['counts']['UNVERIFIED']} UNVERIFIED (docs/STATUS.md); strict regression passes. Releases with per-board CHECKS.md and hash manifests: `{rel('TX')}` (PB1R, CB1D, TXJ1, PM2, HB2) and `{rel('RX')}` (AB1A, AB1B).", "",
 "## 1. Formats in this package", "",
 "| Folder | Contents | Format |", "|---|---|---|",
 f"| `stl_print/` | every printable part ({cnt['PRINT']} files incl. the formers when generated), same folders as the repo `stl/` | binary STL, mm, closed and oriented (print_check 49/49), SHA-256 in `STL_CLASSIFICATION.csv` |",
 "| `stl_print/formers/` | the six full-resolution petal coil formers (about 70 MB each) when `make formers-print` was run; not in git | binary STL |",
 f"| `stl_reference/` | {cnt['REFERENCE']} fit references (full-length septum, upper-assembly assemblies, ferrite tile): not print files | binary STL |",
 "| `kicad/` | every board: `.kicad_pcb`, `.kicad_dru` (rule file), `.kicad_pro`, 3-D models (`3dmodels/`, VRML nominal outlines) | KiCad 9 |",
 "| `schematics/` | functional schematics | `.kicad_sch` + PDF |",
 "| `manufacturing/<board>/` | Gerber + drill zip (KiCad-written), BOM, pick-and-place (y-up), netlist where one exists, layer PDFs, bare-board STEP | Gerber RS-274X / Excellon, CSV, PDF, STEP |",
 "| `models3d/`, `renders/boards/` | each board with parts (GLB) and KiCad 3-D renders | glTF binary, PNG |",
 "| `blueprint/` | layered cut-away of the whole system; `cutaway_faces.json` = its cut faces by part | PDF, PNG, JSON |",
 "| `viewer.html` | interactive cut-away: click a part for its STL, KiCad, Gerber, BOM, pick-and-place, STEP, GLB and release files; move a part and see it checked against the section and stack_check; system simulation (TX pulse, power, runtime, rails, vault temperature) and wiring runs from src/sim/system_live.py (MODELED) | HTML (open in a browser) |", "",
 "Not available: STEP / native CAD of the PRINTED parts. The generators build meshes (Python -> STL), there is no solid-modelling kernel in the repo, so STL is the master format for printing; a STEP would be a mesh wrapped in STEP, not a feature model. Board STEP files contain the bare board (the component models are VRML).", "",
 "## 2. Boards", "", "| Board | Manufacturing files present | Status |", "|---|---|---|"]
for b, desc, got in mfg:
    row = S["boards"].get(b, {}); stt = ", ".join(f"{k} {v['state']}" for k, v in row.items()) if row else "KiCad DRC + independent DRC (no router step)"
    L.append(f"| {desc} | {', '.join(got) if got else 'KiCad file only'} | {stt} |")
L += ["", "## 3. Printed parts", "",
 f"{cnt['PRINT']} PRINT, {cnt['REFERENCE']} REFERENCE, {cnt['SUPERSEDED']} SUPERSEDED (not copied; listed in `STL_CLASSIFICATION.csv` with the reason). Geometry checks measured on the meshes: cylinder v5 47/47, head cross-check, upper assembly 64/64 (incl. the MT60 envelope from the Amass drawing and the septum half-lap joint), yoke, print check 49/49 closed / oriented / fit a 250 mm build volume. Not checked here: slicing, supports, shrinkage, tolerances of a real printer.", "",
 "## 4. Purchased parts and documents", "", "`docs/delivery/PURCHASED_PARTS.csv`, `ASSEMBLY_ORDER.md`, `POTTING_SEQUENCE.md`, `SYSTEM_MANIFEST.csv`; datasheets used are in `data/seed/datasheets/` and logged in `docs/design/DATASHEET_LOG.md` (four of them are manufacturer documents fetched from third-party hosts: re-check on the manufacturer site before ordering).", "",
 "## 5. Not ready (what stands between this package and a first article)", ""]
L += [f"- **{i}** (UNVERIFIED): {d.strip()}" for i, d in UNV]
L += [f"- **{b['id']}**: {b['what']}" for b in BL]
L += ["", "## 6. How this was made", "", "`make signoff-cold` then `python3 scripts/make_package.py` (needs KiCad 9, `make formers-low`; `make formers-print` for the six print formers).", ""]
open(f"{R}/00_INDEX.md", "w").write("\n".join(L))
r = run(sys.executable, "src/render/viewer_r2.py", R); print(r.stdout.strip() or r.stderr[-500:])            # clickable cut-away (viewer.html): every part -> its files; reads the index and the recorded cut faces
print("package:", R, "|", len(rows), "STL rows |", sum(len(g) for _, _, g in mfg), "manufacturing items |", len(os.listdir(f"{R}/schematics")), "schematic files")
