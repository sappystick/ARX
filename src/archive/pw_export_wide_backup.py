#!/usr/bin/env python3
"""PM1 / PB1 export: hand-set placement + placement DRC (assembly gap, edge, HV clearance) -> KiCad PCB (placed, UNROUTED), custom DRC rules, BOM, pick&place, STL, preview.
Routing of the power nets is intentionally left for a layout engineer (HV / high-current)."""
import os, sys, json, math, csv
import numpy as np
import pw_design as D
import rodin_core_v4 as rc, golden_cone_head as g
PW = D.PW; NAME = {"M": "PM1", "T": "PB1"}[PW]; OUT = f"kit_v4/{NAME}"; os.makedirs(OUT, exist_ok=True)
SIZE = {"M": (96.0, 54.0), "T": (140.0, 74.0)}[PW]; CX, CY = 100.0, 100.0
PL = {}
def put(ref, x, y, rot=0): PL[ref] = (x, y, rot)
def rotxy(px, py, rot): return (-px, -py) if rot == 180 else (px, py)
if PW == "M":
    put("JA", -43, -14); put("JB", -43, 14); put("FA", -33, -14); put("FB", -33, 14); put("DOA", -21, -14); put("DOB", -21, 14)
    put("RPA", -32, -22.5); put("RPB", -32, 22.5); put("DPA", -19, -22.5); put("DPB", -19, 22.5)
    put("CB1", -2, -10); put("CB2", -2, 10); put("CM1", 8, -20); put("CM2", 8, 20); put("DTVS", 8, 0)
    put("RBL", 17, 8); put("RS1", 17, -12); put("RS2", 21, -12); put("CS1", 25, -12)
    put("JBK", 23, 2); put("FB1", 33, -2); put("CAUX", 33, 8); put("CAUX2", 33, 14)
    put("JP", 42, -14); put("JS", 41, 14); put("JR", 30, 21); put("RSH", 18, 21); put("CSH", 22, 21)
else:
    put("JP", -64, -24); put("CB1", -50, -26); put("CB2", -50, -12)
    for i, x in enumerate((-41, -35.5, -30, -24.5), 1): put(f"CM{i}", x, -27)
    put("Q1A", -46, 2, 180); put("Q1B", -46, 20, 180); put("RS1S", -31, 11); put("RGQ1A", -36, 7); put("RGQ1B", -36, 25)
    put("U1", -22, 17); put("CD1", -14, 13); put("CE1", -14, 18); put("RIN1", -22, 25); put("DOC1", -28, 25); put("RGP1", -16, 25); put("RK1", -22, 8); put("CK1", -17, 8)
    put("DC1", -60, 4); put("CL1A", -58, 14); put("CL1B", -58, 22); put("RCL1", -58, 31); put("JL1", -66, 11); put("RNTC", -30, 0)
    put("Q2A", -2, -8, 180); put("JL2", -14, -10); put("DC2", -2, -20); put("CL2A", 6, -20); put("RCL2", 16, -26); put("RS2S", 13, -14); put("RGQ2A", 9, -5.5)
    put("U2", 24, -6); put("CD2", 32, -11); put("CE2", 32, -6); put("RIN2", 24, 1); put("DOC2", 18, 1); put("RGP2", 30, 1); put("RK2", 18, -21); put("CK2", 23, -21)
    put("U3", 42, 10); put("CU3", 50, 10); put("RPU1", 36, 18); put("RF1", 40, 18); put("RPU2", 46, 18); put("RF2", 50, 18); put("JC", 62, 0)
# remove refs not in design
PL = {k: v for k, v in PL.items() if k in D.BYREF}
missing = [p["ref"] for p in D.PARTS if p["ref"] not in PL]
def pads_of(ref):
    lib = D.LIB[D.BYREF[ref]["type"]]; x0, y0, rot = PL[ref]; own = {}
    for k, v in D.NETS.items():
        for r, n in v: own[(r, n)] = k
    return [dict(ref=ref, num=str(n), x=x0 + rotxy(px, py, rot)[0], y=y0 + rotxy(px, py, rot)[1], w=w, h=h, net=own.get((ref, str(n))), tht=bool(lib.get("tht")), drill=lib.get("drill", 0), shape=shp) for n, px, py, w, h, shp in lib["pads"]]
PADS = [pd for p in D.PARTS if p["ref"] in PL for pd in pads_of(p["ref"])]
HV = {"DRAIN1", "CLAMP1"}; MV = {"DRAIN2", "CLAMP2"}
def gap(a, b):
    dx = abs(a["x"] - b["x"]) - (a["w"] + b["w"]) / 2; dy = abs(a["y"] - b["y"]) - (a["h"] + b["h"]) / 2
    return math.hypot(max(dx, 0), max(dy, 0)) if (dx > 0 and dy > 0) else max(dx, dy)
errs = []
for i, a in enumerate(PADS):
    if abs(a["x"]) + a["w"] / 2 > SIZE[0] / 2 - 1.0 or abs(a["y"]) + a["h"] / 2 > SIZE[1] / 2 - 1.0: errs.append(f"edge {a['ref']}.{a['num']}")
    for b in PADS[i + 1:]:
        if a["ref"] == b["ref"]: continue
        gp = gap(a, b)
        need = 0.3
        if (a["net"] in HV) != (b["net"] in HV) or (a["net"] in HV and b["net"] != a["net"] and (b["net"] not in HV)): need = 1.0
        if a["net"] in HV and b["net"] in HV and a["net"] != b["net"]: need = 1.0
        if (a["net"] in MV) != (b["net"] in MV) and a["net"] != b["net"]: need = max(need, 0.5)
        if gp < need and a["net"] != b["net"]: errs.append(f"gap {gp:.2f} < {need}: {a['ref']}.{a['num']}({a['net']}) - {b['ref']}.{b['num']}({b['net']})")
        elif gp < 0.0 and a["net"] == b["net"] and a["ref"] != b["ref"]: pass
chk = dict(board=NAME, parts=len(D.PARTS), unplaced=missing, placement_errors=errs[:40], n_errors=len(errs))
print(json.dumps({k: chk[k] for k in ("board", "parts", "unplaced", "n_errors")})); [print("  ", e) for e in errs[:30]]
if errs or missing: sys.exit(1)
# --------------------------------------------------------------- KiCad PCB (placed, unrouted)
NETID = {n: i for i, n in enumerate(sorted(D.NETS), 1)}
def K(x, y): return f"{CX + x:.4f} {CY + y:.4f}"
W, H = SIZE
L = ["(kicad_pcb (version 20221018) (generator \"pf233_power_export\")", f"  (general (thickness 1.6) (legacy_teardrops no))", '  (paper "A4")', "  (layers",
     '    (0 "F.Cu" signal) (1 "In1.Cu" signal) (2 "In2.Cu" signal) (31 "B.Cu" signal) (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")',
     '    (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments") (44 "Edge.Cuts" user) (47 "F.CrtYd" user "F.Courtyard") (49 "F.Fab" user))',
     '  (setup (pad_to_mask_clearance 0.05) (stackup (layer "F.Cu" (type "copper") (thickness 0.07)) (layer "dielectric 1" (type "prepreg") (thickness 0.2)) (layer "In1.Cu" (type "copper") (thickness 0.035)) '
     '(layer "dielectric 2" (type "core") (thickness 1.0)) (layer "In2.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 3" (type "prepreg") (thickness 0.2)) (layer "B.Cu" (type "copper") (thickness 0.07)) (copper_finish "ENIG")))', '  (net 0 "")']
for n, i in NETID.items(): L.append(f'  (net {i} "{n}")')
own = {}
for k, v in D.NETS.items():
    for r, n in v: own[(r, n)] = k
for p in D.PARTS:
    ref = p["ref"]; lib = D.LIB[p["type"]]; x0, y0, rot = PL[ref]
    L.append(f'  (footprint "{lib["fp"]}" (layer "F.Cu") (at {K(x0, y0)}{" " + str(rot) if rot else ""})')
    L.append(f'    (property "Reference" "{ref}" (at 0 -2.5 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    L.append(f'    (property "Value" "{p["value"]}" (at 0 2.5 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    L.append(f'    (attr {"through_hole" if lib.get("tht") else "smd"})')
    for n, px, py, w, h, shp in lib["pads"]:
        net = own.get((ref, str(n))); nid = NETID.get(net, 0) if net else 0
        if lib.get("tht"): L.append(f'    (pad "{n}" thru_hole {"circle" if shp == "circle" else "rect"} (at {px:.3f} {py:.3f}) (size {w} {h}) (drill {lib["drill"]}) (layers "*.Cu" "*.Mask") (net {nid} "{net or ""}"))')
        else: L.append(f'    (pad "{n}" smd {"rect" if shp == "rect" else "roundrect"} (at {px:.3f} {py:.3f}) (size {w:.3f} {h:.3f}) (layers "F.Cu" "F.Paste" "F.Mask") (net {nid} "{net or ""}"))')
    L.append("  )")
L.append(f'  (gr_rect (start {CX - W / 2:.3f} {CY - H / 2:.3f}) (end {CX + W / 2:.3f} {CY + H / 2:.3f}) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts"))')
for nm, lyr in (("GND", "In1.Cu"), ("VBUS", "In2.Cu")):
    if nm in NETID:
        poly = f"(xy {CX - W / 2 + 0.5:.2f} {CY - H / 2 + 0.5:.2f}) (xy {CX + W / 2 - 0.5:.2f} {CY - H / 2 + 0.5:.2f}) (xy {CX + W / 2 - 0.5:.2f} {CY + H / 2 - 0.5:.2f}) (xy {CX - W / 2 + 0.5:.2f} {CY + H / 2 - 0.5:.2f})"
        L.append(f'  (zone (net {NETID[nm]}) (net_name "{nm}") (layer "{lyr}") (hatch edge 0.5) (connect_pads (clearance 0.3)) (min_thickness 0.25) (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.5)) (polygon (pts {poly})))')
L.append(")"); open(f"{OUT}/PF233-{NAME}.kicad_pcb", "w").write("\n".join(L))
print("paren balance", sum(l.count("(") - l.count(")") for l in L))
if PW == "T":
    open(f"{OUT}/PF233-{NAME}.kicad_dru", "w").write('(version 1)\n(rule "HV clamp nets 1.0 mm (coated)"\n  (condition "A.NetName == \'DRAIN1\' || A.NetName == \'CLAMP1\'")\n  (constraint clearance (min 1.0mm)))\n'
        '(rule "MV nets 0.5 mm"\n  (condition "A.NetName == \'DRAIN2\' || A.NetName == \'CLAMP2\'")\n  (constraint clearance (min 0.5mm)))\n(rule "Power track width"\n  (condition "A.NetName == \'VBUS\' || A.NetName == \'DRAIN1\' || A.NetName == \'DRAIN2\' || A.NetName == \'GND\'")\n  (constraint track_width (min 1.5mm)))\n')
D.kicad_netlist(f"{OUT}/PF233-{NAME}.net")
with open(f"{OUT}/PF233-{NAME}_BOM.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Qty", "Refs", "Type", "Value", "MPN / note", "Footprint"]); [w.writerow([r["qty"], r["refs"], r["type"], r["value"], r["mpn"], r["footprint"]]) for r in D.bom()]
with open(f"{OUT}/PF233-{NAME}_pickplace.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Ref", "Val", "Package", "PosX_mm", "PosY_mm", "Rot", "Side"]); [w.writerow([p["ref"], p["value"], D.LIB[p["type"]]["fp"].split(":")[1], PL[p["ref"]][0], -PL[p["ref"]][1], PL[p["ref"]][2], "top"]) for p in D.PARTS]
# --------------------------------------------------------------- STL + preview
def boxm(cx, cy, z0, lx, ly, lz):
    x = np.array([-1, 1]) * lx / 2; y = np.array([-1, 1]) * ly / 2
    V = np.array([[a, b, z0 + c * lz] for a in x for b in y for c in (0, 1)]) + [cx, cy, 0]
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
parts = [boxm(0, 0, -1.6, W, H, 1.6)]
for p in D.PARTS:
    bw, bh, bz = D.LIB[p["type"]]["body"]; x0, y0, _ = PL[p["ref"]]; parts.append(boxm(x0, -y0, 0.0, bw, bh, bz))
Vs, Fs = g.merge(parts); rc.write_stl(f"{OUT}/PF233-{NAME}_board_with_components.stl", Vs, Fs, NAME)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(W / 8, H / 8 + 0.6)); ax.add_patch(plt.Rectangle((-W / 2, -H / 2), W, H, fc="#0b3d2e", ec="w")); ax.set_aspect("equal"); ax.set_xlim(-W / 2 - 2, W / 2 + 2); ax.set_ylim(H / 2 + 2, -H / 2 - 2)
for pd in PADS:
    col = "#e74c3c" if pd["net"] in HV else ("#f39c12" if pd["net"] in MV else "#ecf0f1")
    ax.add_patch(plt.Rectangle((pd["x"] - pd["w"] / 2, pd["y"] - pd["h"] / 2), pd["w"], pd["h"], fc=col, ec="k", lw=0.2))
for p in D.PARTS: ax.text(PL[p["ref"]][0], PL[p["ref"]][1], p["ref"], color="w", fontsize=6, ha="center", va="center")
ax.set_title(f"PF233-{NAME} placement (UNROUTED)  red = 500 V clamp nets (>=1.0 mm), orange = ~100 V nets (>=0.5 mm)", fontsize=8); fig.tight_layout(); fig.savefig(f"{OUT}/PF233-{NAME}_placement_preview.png", dpi=110)
json.dump(chk, open(f"{OUT}/PF233-{NAME}_placement_check.json", "w"), indent=1); print("exported", OUT)
