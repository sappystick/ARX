#!/usr/bin/env python3
"""Whole-system delivery manifest (docs/delivery/SYSTEM_MANIFEST.csv) and the assembly-order document (docs/delivery/ASSEMBLY_ORDER.md, written once by hand from DESIGN_STATE and UPPER_ASSEMBLY_v1).
Every board (CB1D, LB1, PB1R, PM2, HB2, TXJ1, SB1R-QA, SB1R-QB, HTA, AB1A, AB1B) with Gerber / drill, KiCad, BOM and pick-and-place; every STL folder (head, pins, yoke, upper, shaft_handle) with its class and
print_check state; the six formers (generated, not stored); purchased parts (BOM_MASTER.csv with the superseded AB1 rows replaced by the AD7389-4 BOMs); items that do not exist are MISSING.
usage (repo root): python3 scripts/system_manifest.py"""
import os, sys, csv, glob, json, hashlib
sys.path.insert(0, "src/mech"); os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import print_check as pc
rows = [("category", "item", "path", "status", "bytes", "sha256", "note")]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def add(cat, item, path, note=""):
    if path and os.path.exists(path): rows.append((cat, item, path, "PRESENT", os.path.getsize(path), sha(path), note))
    else: rows.append((cat, item, path or "-", "MISSING", 0, "", note))
BOARDS = {   # board: (gerber dir, kicad file, bom, pick-and-place, schematic)
 "CB1D": ("data/gerber/CB1D_C1", "data/kicad/PF233-CB1D_routed.kicad_pcb", "data/results/PF233-CB1D_BOM.csv", "data/results/PF233-CB1D_pickplace.csv", "data/kicad/sch/PF233-CB1D.kicad_sch"),
 "LB1": ("data/gerber/LB1_v6", "data/kicad/PF233-LB1_routed.kicad_pcb", "data/results/PF233-LB1_BOM.csv", "data/results/PF233-LB1_pickplace.csv", "data/kicad/sch/PF233-LB1.kicad_sch"),
 "PB1R": ("data/gerber/PB1R_v3", "data/kicad/PF233-PB1R_routed.kicad_pcb", "data/results/PF233-PB1R_BOM.csv", "data/results/PF233-PB1R_pickplace.csv", "data/kicad/sch/PF233-PB1R.kicad_sch"),
 "PM2": ("data/gerber/PM2", "data/kicad/PF233-PM2_routed.kicad_pcb", "data/results/PF233-PM2_BOM.csv", "data/results/PF233-PM2_pickplace.csv", "data/kicad/sch/PF233-PM2.kicad_sch"),
 "HB2": ("data/gerber/HB2", "data/kicad/PF233-HB2_routed.kicad_pcb", "data/results/PF233-HB2_BOM.csv", "data/results/PF233-HB2_pickplace.csv", "data/kicad/sch/PF233-HB2.kicad_sch"),
 "TXJ1": ("data/gerber/TXJ1_v2", "data/kicad/TXJ1.kicad_pcb", "docs/delivery/boards/TXJ1_BOM.csv", "docs/delivery/boards/TXJ1_pickplace.csv", None),
 "SB1R-QA": ("data/gerber/SB1R_QA_v2", "data/kicad/SB1R-QA.kicad_pcb", "docs/delivery/boards/SB1R-QA_BOM.csv", "docs/delivery/boards/SB1R-QA_pickplace.csv", None),
 "SB1R-QB": ("data/gerber/SB1R_QB_v2", "data/kicad/SB1R-QB.kicad_pcb", "docs/delivery/boards/SB1R-QB_BOM.csv", "docs/delivery/boards/SB1R-QB_pickplace.csv", None),
 "HTA": ("data/gerber/HTA_v2", "data/kicad/PF233-HTA.kicad_pcb", "data/gerber/HTA_v2/PF233-HTA-v2_BOM.csv", None, None),
 "AB1A": ("data/gerber/AB1A_v1", "data/kicad/PF233-AB1A.kicad_pcb", "data/results/PF233-AB1A_BOM.csv", "data/results/PF233-AB1A_pickplace.csv", "data/results/PF233-AB1A_functional.pdf"),
 "AB1B": ("data/gerber/AB1B_v1", "data/kicad/PF233-AB1B.kicad_pcb", "data/results/PF233-AB1B_BOM.csv", "data/results/PF233-AB1B_pickplace.csv", "data/results/PF233-AB1B_functional.pdf"),
}
for b, (gd, kc, bom, pp, sch) in BOARDS.items():
    g = sorted(glob.glob(gd + "/*.gbr")); d = sorted(glob.glob(gd + "/*.drl")) + sorted(glob.glob(gd + "/*.txt")) if os.path.isdir(gd) else []
    if g: rows.append(("board", f"{b} Gerber", gd, "PRESENT", sum(os.path.getsize(x) for x in g), "", f"{len(g)} .gbr + {len([x for x in d if x.endswith('.drl')])} drill files"))
    else: rows.append(("board", f"{b} Gerber", gd, "MISSING", 0, "", ""))
    add("board", f"{b} KiCad board", kc); add("board", f"{b} BOM", bom); add("board", f"{b} pick-and-place", pp); add("board", f"{b} schematic", sch)
rows.append(("board", "rigid-flex spine (OPEN_ITEMS 3)", "-", "MISSING", 0, "", "not designed: stackup, bend radius, shield hatch, connector footprints"))
rows.append(("board", "AB1A / AB1B fabrication", "releases/RX_r3", "BLOCKED", 0, "", "exposed pad closed (B1), BLOCKERS 2 and 3 closed in RX_r3; still open: U-FAB-DRC / U-CAM-VIEW (fabricator DRC, CAM viewer) and bench data (releases/RX_r3/BLOCKERS.md)"))
man = {r["file"]: r for r in csv.DictReader(open("stl/MANIFEST.csv"))}
pcr = {p["file"]: p for p in json.load(open("data/results/print_check.json"))["parts"]}
for f in sorted(glob.glob("stl/*/*.stl")):
    c = pc.classify(f); p = pcr.get(f, {}); st = "PRESENT"
    rows.append(("stl " + f.split("/")[1], os.path.basename(f), f, st, os.path.getsize(f), man.get(f, {}).get("sha256", sha(f)), f"{c}; closed={p.get('closed')}; fits 250 mm cube={p.get('fits_build_cube')}"))
for k in range(1, 7):
    cand = glob.glob(f"work/kit_v15/PRINT/FORMER_L{k}*.stl")
    rows.append(("former", f"FORMER_L{k}", cand[0] if cand else f"work/kit_v15/PRINT/FORMER_L{k}_petal_coil_former.stl", "PRESENT" if cand else "MISSING", os.path.getsize(cand[0]) if cand else 0, "", "generated, not stored (about 70 MB each): make formers-print"))
bm = list(csv.reader(open("data/results/BOM_MASTER.csv"))); head, body = bm[0], bm[1:]
CUR = ("AB1A", "AB1B", "CB1D", "HB2", "LB1", "PB1R", "PM2")                  # boards with a BOM generated from the current routed board (data/results/PF233-<B>_BOM.csv)
body = [r for r in body if r[0] not in [f"pcb {b}" for b in CUR] + ["pcb HB1", "pcb PM1"]]   # BOM_MASTER rows of these boards are older builds (ADS8860 AB1, OKI 12/1.5 M12); HB1 / PM1 are superseded by HB2 / PM2
for b in CUR:
    for r in list(csv.reader(open(f"data/results/PF233-{b}_BOM.csv")))[1:]: body.append([f"pcb {b}", r[1], r[0], f"{r[3]} {r[4]}".strip()[:70], b, r[5][:40]])
for b in ("TXJ1", "SB1R-QA", "SB1R-QB"):                                    # B8: regenerated from the KiCad boards (src/pcb/kicad_bom_pnp.py)
    for r in list(csv.reader(open(f"docs/delivery/boards/{b}_BOM.csv")))[1:]: body.append([f"pcb {b}", r[1], r[0], r[2][:70], b, r[3][:40]])
os.makedirs("docs/delivery", exist_ok=True)
with open("docs/delivery/PURCHASED_PARTS.csv", "w", newline="") as f: w = csv.writer(f); w.writerow(head); w.writerows(body)
add("purchased", "purchased parts and printed-part list (BOM_MASTER.csv with every routed board's rows replaced by the BOM generated from that board)", "docs/delivery/PURCHASED_PARTS.csv", f"{len(body)} rows; the board rows of data/results/BOM_MASTER.csv list older builds (ADS8860 AB1, OKI 12/1.5 M12, HB1, PM1)")
add("purchased", "shaft / yoke / upper-assembly bill of materials", "data/results/BOM_SHAFT_YOKE.csv")
add("document", "assembly order", "docs/delivery/ASSEMBLY_ORDER.md")
add("document", "potting sequence (B8: order, keep-outs; resins NOT SPECIFIED)", "docs/delivery/POTTING_SEQUENCE.md")
for _b in ("TXJ1", "SB1R-QA", "SB1R-QB"):                                              # B8: boards with no design database, read from their KiCad boards (src/pcb/kicad_bom_pnp.py)
    add("board", f"{_b} BOM", f"docs/delivery/boards/{_b}_BOM.csv"); add("board", f"{_b} pick-and-place (y-up)", f"docs/delivery/boards/{_b}_pickplace.csv")
for k, f in (("bench procedure (transmit region)", "docs/design/BENCH_FIRST_ARTICLE_TX.md"), ("fabricator DRC evidence (U-FAB-DRC)", "data/results/fab_drc/"), ("CAM viewer evidence (U-CAM-VIEW)", "data/results/cam_view/"), ("bench data (U-BENCH)", "data/bench/")):
    rows.append(("document", k, f, "PRESENT" if os.path.exists(f) else "MISSING", 0, "", ""))
with open("docs/delivery/SYSTEM_MANIFEST.csv", "w", newline="") as f: csv.writer(f).writerows(rows)
miss = [r for r in rows[1:] if r[3] == "MISSING"]; print(f"manifest: {len(rows) - 1} rows, {len(miss)} MISSING: " + "; ".join(f"{r[1]}" for r in miss)[:600])
