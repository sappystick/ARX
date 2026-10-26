#!/usr/bin/env python3
"""Checks the KiCad 3-D model links (Step 7): every component footprint of every generated board carries a `model` line, the referenced VRML file exists and parses, each
model touches every one of its own pads in x/y (so it sits on the footprint), and its height stays within the library body envelope + 0.5 mm.
usage (in work/): python3 models3d_check.py MODEL_DIR OUT.json BOARD.kicad_pcb [...]"""
import sys, os, re, json
import numpy as np
import models3d as M3
mdir, out, boards = sys.argv[1], sys.argv[2], sys.argv[3:]
types = M3.types_by_board(); L_by_t = {}
for (src, t), L in types.items(): L_by_t.setdefault(t, L)
L_by_t.update(M3.EXTRA)
rep = {"boards": {}, "models": {}, "errors": []}
for t, L in sorted(L_by_t.items()):
    parts = M3.build(t, L)
    if not parts: continue
    lo, hi = M3.bbox(parts); px = [p[1] for p in L["pads"]]; py = [p[2] for p in L["pads"]]
    ok_xy = all(lo[0] <= p[1] + p[3] / 2 and hi[0] >= p[1] - p[3] / 2 and lo[1] <= p[2] + p[4] / 2 and hi[1] >= p[2] - p[4] / 2 for p in L["pads"])      # every terminal / lead touches its pad
    ok_z = hi[2] <= L["body"][2] + 0.5
    rep["models"][t] = dict(covers_pads=bool(ok_xy), height=round(float(hi[2]), 2), envelope_h=L["body"][2], height_ok=bool(ok_z))
    if not (ok_xy and ok_z): rep["errors"].append(f"model {t}: covers_pads={ok_xy} height_ok={ok_z}")
    f = os.path.join(mdir, f"PF233_{t}.wrl")
    txt = open(f).read() if os.path.exists(f) else ""
    if not txt.startswith("#VRML V2.0") or txt.count("IndexedFaceSet") != len(parts): rep["errors"].append(f"{f}: missing or malformed")
for b in boards:
    t = open(b).read(); fps = re.split(r"\n  \(footprint ", t)[1:]; n = nm = 0; missing = []
    for fp in fps:
        name = fp.split('"')[1]; ref = re.search(r'\(property "Reference" "([^"]+)"', fp).group(1)
        if name.startswith(("SB1R:", "PF233:", "TXJ1:", "Connector:Wire_pads", "Connector:SolderPad")): continue
        if re.search(r"\(attr (smd|through_hole)\)", fp) is None and not name.startswith("Resistor_SMD"): continue
        n += 1; m = re.search(r'\(model "\$\{KIPRJMOD\}/3dmodels/([^"]+)"', fp)
        if m and os.path.exists(os.path.join(mdir, m.group(1))): nm += 1
        else: missing.append(ref)
    rep["boards"][os.path.basename(b)] = dict(components=n, with_model=nm, missing=missing)
rep["n_errors"] = len(rep["errors"]); json.dump(rep, open(out, "w"), indent=1)
print("models3d_check:", len(rep["models"]), "model types,", sum(v["with_model"] for v in rep["boards"].values()), "linked components,", rep["n_errors"], "errors")
sys.exit(1 if rep["errors"] else 0)
