#!/usr/bin/env python3
"""Gerbers and drill files written by KiCad itself (kicad-cli), from a board whose zones were filled WITH the design rules of dru_gen.py loaded, so the plane layers carry the
same HV carve-out that kicad_drc.py checks. Used for the rectangular PB1R (gerber_out.py is the disc writer for CB1D / LB1).
usage: kicad_gerber.py board.kicad_pcb BOARD_KEY OUTDIR PREFIX      -> OUTDIR/PREFIX-<layer>.gbr, PREFIX-PTH.drl, PREFIX-NPTH.drl, a manifest line"""
import sys, os, subprocess, shutil, tempfile, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dru_gen
src, key, outdir, prefix = sys.argv[1:5]
tmp = tempfile.mkdtemp(); dst = os.path.join(tmp, "b.kicad_pcb"); shutil.copy(src, dst)
open(os.path.join(tmp, "b.kicad_dru"), "w").write(dru_gen.rules(key)); open(os.path.join(tmp, "b.kicad_pro"), "w").write("{}")
code = f"import pcbnew; b=pcbnew.LoadBoard({dst!r}); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard({dst!r}, b)"
r = subprocess.run(["/usr/bin/python3", "-c", code], capture_output=True, text=True)
if r.returncode: print("fill failed", r.stderr[-300:]); sys.exit(2)
os.makedirs(outdir, exist_ok=True); g = os.path.join(tmp, "g"); os.makedirs(g)
layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.Silkscreen,Edge.Cuts"
a = subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--no-protel-ext", "-o", g + "/", dst], capture_output=True, text=True)
b = subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm", "--excellon-separate-th", "--drill-origin", "absolute", "-o", g + "/", dst], capture_output=True, text=True)
files = sorted(glob.glob(g + "/*"))
for f in files:
    nm = os.path.basename(f); nm = nm[2:] if nm.startswith(("b-", "b.")) else nm            # strip the temporary board name only at the start
    shutil.copy(f, os.path.join(outdir, f"{prefix}-{nm}"))
print(json.dumps(dict(board=key, files=[os.path.basename(f) for f in files], gerber_rc=a.returncode, drill_rc=b.returncode)))
if a.returncode or b.returncode: print(a.stderr[-300:], b.stderr[-300:])
