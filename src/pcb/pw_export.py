#!/usr/bin/env python3
"""PM1 / PB1 export: hand-set placement + placement DRC (assembly gap, edge, HV clearance) -> KiCad PCB (placed, UNROUTED), custom DRC rules, BOM, pick&place, STL, preview.
Routing of the power nets is intentionally left for a layout engineer (HV / high-current)."""
import os, sys, json, math, csv
import numpy as np
import pw_design as D
import rodin_core_v4 as rc, golden_cone_head as g
PW = D.PW; NAME = {"M": "PM1", "T": "PB1", "C": "CB1", "R": "PB1R", "H": "HB1", "P": "PM2", "G": "HB2"}[PW]; OUT = f"kit_v6/{NAME}"; os.makedirs(OUT, exist_ok=True)
SIZE = {"M": (28.0, 136.0), "T": (28.0, 224.0), "C": (70.0, 70.0), "R": (70.0, 70.0), "H": (24.0, 60.0), "P": (28.0, 70.0), "G": (24.0, 38.0)}[PW]; CX, CY = 100.0, 100.0
HV = ({"DRAIN1", "CLAMP1"} if PW in ("R", "T") else ({"COIL_B", "DM1", "DM2"} if PW == "C" else set())); MV = {"DRAIN2", "CLAMP2"}
PL = {}
def put(ref, x, y, rot=0): PL[ref] = (x, y, rot)
def rotxy(px, py, rot): return {0: (px, py), 90: (py, -px), 180: (-px, -py), 270: (-py, px)}[rot % 360]
if PW == "M":
    put("JA", -7, -51); put("JB", 7, -51); put("FA", -7, -35); put("FB", 7, -35); put("DOA", -7, -27); put("DOB", 7, -27)
    put("RPA", -7, -19); put("RPB", 7, -19); put("DPA", -7, -12); put("DPB", 7, -12); put("DTVS", 0, -4)
    put("CB1", -6.7, 8); put("CB2", 6.7, 8); put("CM1", -7, 20); put("CM2", 7, 20); put("RBL", 0, 26)
    put("RS1", -8, 32); put("RS2", 0, 32); put("CS1", 8, 32); put("JBK", -9, 40); put("FB1", 3, 40); put("CAUX", 5, 46); put("CAUX2", 11, 46)
    put("RSH", -8, 47); put("CSH", -2, 47); put("JR", 7, 52); put("JP", -7, 58); put("JS", 8, 61)
else:
    put("JP", -7, -100); put("CB1", -6.7, -84); put("CB2", 6.7, -84)
    for i, x in enumerate((-9, -3, 3, 9), 1): put(f"CM{i}", x, -76)
    put("RCL1", 0, -69); put("DC1", 0, -60); put("CL1A", -7, -54); put("CL1B", 7, -54); put("JL1", 0, -50)
    put("Q1A", -7, -34, 90); put("Q1B", 7, -34, 90); put("RGQ1A", -7, -22); put("RGQ1B", 7, -22); put("RS1S", 0, -18); put("RNTC", 11, -14)
    put("U1", 0, -8); put("CD1", -8, -4); put("CE1", 8, -4); put("RIN1", -5, 1); put("DOC1", 5, 1); put("RGP1", 0, 3); put("RK1", -8, -12); put("CK1", -8, -15)
    put("U3", 0, 12); put("CU3", 9, 12); put("RPU1", -7, 18); put("RF1", -7, 21); put("RPU2", 7, 18); put("RF2", 7, 21)
    put("RK2", -8, 26); put("CK2", -4, 26); put("RS2S", 0, 31); put("Q2A", 0, 44, 90); put("RGQ2A", -9, 36); put("DC2", 0, 56); put("CL2A", 0, 62); put("RCL2", 0, 68); put("JL2", 0, 78)
    put("U2", 0, 90); put("CD2", -9, 86); put("CE2", 9, 86); put("RIN2", -7, 96); put("DOC2", -1, 94); put("RGP2", 0, 98); put("JC", 7, 100)

def bbox_of(ref, x, y, rot):
    lib = D.LIB[D.BYREF[ref]["type"]]; xs = []; ys = []
    for n, px, py, w, h, shp in lib["pads"]:
        qx, qy = rotxy(px, py, rot); ww, hh = (h, w) if rot % 180 == 90 else (w, h); xs += [x + qx - ww / 2, x + qx + ww / 2]; ys += [y + qy - hh / 2, y + qy + hh / 2]
    bw, bh, _ = lib["body"]
    if rot % 180 == 90: bw, bh = bh, bw
    return (min(min(xs), x - bw / 2), min(min(ys), y - bh / 2), max(max(xs), x + bw / 2), max(max(ys), y + bh / 2))
_HVREFS = set(r for name, v in D.NETS.items() if name in HV for (r, pin) in v)
def is_hv(ref): return ref in _HVREFS
def autoplace(fixed, anchors, rots=None):
    rots = rots or {}; placed = {}
    for ref, (x, y, rot) in fixed.items(): placed[ref] = (x, y, rot)
    order = sorted([p["ref"] for p in D.PARTS if p["ref"] not in fixed], key=lambda r: -((lambda b: (b[2] - b[0]) * (b[3] - b[1]))(bbox_of(r, 0, 0, 0))))
    boxes = {r: bbox_of(r, *placed[r]) for r in placed}
    def free(ref, x, y, rot):
        b = bbox_of(ref, x, y, rot)
        if b[0] < -SIZE[0] / 2 + 0.8 or b[2] > SIZE[0] / 2 - 0.8 or b[1] < -SIZE[1] / 2 + 0.8 or b[3] > SIZE[1] / 2 - 0.8: return False
        for r2, b2 in boxes.items():
            m = 1.2 if (is_hv(ref) != is_hv(r2)) else 0.5
            if not (b[2] + m < b2[0] or b[0] - m > b2[2] or b[3] + m < b2[1] or b[1] - m > b2[3]): return False
        return True
    for ref in order:
        ax, ay = anchors.get(ref, (0.0, 0.0)); rot = rots.get(ref, 0); done = False
        for rad in np.arange(0, 80, 0.5):
            n = max(1, int(rad * 6))
            for k in range(n):
                a = 2 * math.pi * k / n; x = round((ax + rad * math.cos(a)) * 2) / 2; y = round((ay + rad * math.sin(a)) * 2) / 2
                if free(ref, x, y, rot): placed[ref] = (x, y, rot); boxes[ref] = bbox_of(ref, x, y, rot); done = True; break
            if done: break
        if not done: print("could not place", ref)
    return placed
if PW == "C":
    fixed = {"U1": (-22.0, 0.0, 0), "JPW": (30.0, 24.0, 0), "JTR": (31.5, -24.0, 0), "JA": (-3.0, -31.0, 90), "JB": (-3.0, 31.0, 90), "JPB": (12.0, -29.0, 0), "JCL": (31.0, -2.0, 0)}
    anchors = {"M5": (12, 8), "UL": (2, 14), "UM": (-3, -17), "F1": (22, 31), "DTV": (21, 25), "CI1": (14, 31), "CI2": (14, 27), "C5A": (4, 8), "C5B": (4, 12),
               "FB2": (5, 0), "CV1": (9, 0), "CV2": (9, 3), "CV3": (5, 3), "CL1": (-2, 19), "CL2": (-2, 23), "CP1": (-12, -8), "CP2": (-12, -11), "CM1": (2, -12), "RMO": (-7, -13), "CMO": (-7, -9),
               "RR1": (-8, -25), "RR2": (-8, -21), "CR1": (-11, -23), "CR2": (-11, -19), "RV1": (22, 14), "RV2": (22, 18), "CV4": (25, 16), "RSH": (26, -20), "CSH": (22, -20), "RT1": (24, -14), "RD1": (24, -17),
               "DH1": (20, -14), "DL1": (20, -17), "CQ1": (18, -20), "RP1": (22, -22), "DH2": (14, -14), "DL2": (14, -17), "CQ2": (16, -20), "RP2": (12, -22), "JDBG": (-12, 25),
               "RDM1": (23, -9), "RDM2": (23, -4), "RDM3": (23, 1), "CMON": (31, -11), "RBI": (31, -14.5), "RJX": (21, -26), "RJY": (21, -29), "CJX": (25, -26), "CJY": (25, -29), "RUS": (17, -33), "CUS": (21, -33)}
    PL = autoplace(fixed, anchors)
elif PW == "R":
    fixed = {"JP": (-31.0, 24.0, 0), "Q1A": (-14.0, -20.0, 180), "Q1B": (-14.0, -6.0, 180), "JL1": (31.0, -20.0, 0), "JC": (28.0, 24.0, 0), "M12": (14.0, -27.0, 0)}
    anchors = {"U1": (3, -13), "CD7": (8, -9), "CE1": (8, -16), "RIN1": (3, -6), "DOC1": (-2, -6), "RGP1": (3, -19), "RGQ1A": (-5, -18), "RGQ1B": (-5, -8), "RS1S": (-3, 2), "RK1": (6, 2), "CK1": (10, 2),
               "U3": (14, 10), "CU3": (20, 10), "RPU1": (14, 17), "RF1": (18, 17), "RNTC": (0, -26), "DC1": (-30, -12), "CL1A": (-30, -3), "CL1B": (-30, 5), "RCL1": (-30, 14),
               "C12A": (24, -27), "C12B": (24, -31), "RUS": (28, 17)}
    for i in range(1, 7): anchors[f"CD{i}"] = (-18 + (i - 1) * 8.5, 30)
    for i in range(1, 5): anchors[f"CM{i}"] = (-22 + (i - 1) * 6, 22)
    PL = autoplace(fixed, anchors, rots={})
elif PW == "H":
    fixed = {"JH": (-8.0, -17.0, 0), "JJOY": (8.0, -17.0, 0), "JDIAL": (8.0, 4.0, 0), "HS1": (-8.0, 10.0, 0)}
    anchors = {"CH1": (-8, 15), "RH1": (-8, 19), "RSW": (3, -8), "RD0": (-2, 0), "RD2": (-2, 4), "RD3": (-2, 8), "RD4": (-2, 12), "RSHH": (-8, 24)}
    PL = autoplace(fixed, anchors)
elif PW == "P":
    fixed = {"J1": (-7.0, -27.0, 0), "JP": (7.0, 25.0, 0), "JS": (-8.0, 30.0, 0), "J3": (-9.0, 12.0, 0), "CB1": (6.0, 4.0, 0)}
    anchors = {"F1": (6, -27), "Q1": (5, -16), "R1": (-4, -14), "DZ1": (-4, -9), "R2": (-4, -4), "R3": (-9, -4), "C1": (-9, 1), "DTVS": (5, -8), "CM1": (-5, 18), "RBL": (5, 14), "RSH": (-4, 24), "CSH": (-9, 24)}
    PL = autoplace(fixed, anchors)
elif PW == "G":
    fixed = {"JH": (-7.0, -6.0, 0), "JDIAL": (6.0, -10.0, 0), "HS1": (0.0, 15.0, 0)}     # HS1 at the board end under the trigger magnet
    anchors = {"CH1": (-6, 14), "RH1": (6, 14), "RD0": (2, 2), "RD2": (6, 2), "RD3": (-2, 7), "RD4": (6, 7), "RSHH": (-8, 10)}
    PL = autoplace(fixed, anchors)
# remove refs not in design
PL = {k: v for k, v in PL.items() if k in D.BYREF}
missing = [p["ref"] for p in D.PARTS if p["ref"] not in PL]
def pads_of(ref):
    lib = D.LIB[D.BYREF[ref]["type"]]; x0, y0, rot = PL[ref]; own = {}
    for k, v in D.NETS.items():
        for r, n in v: own[(r, n)] = k
    return [dict(ref=ref, num=str(n), x=x0 + rotxy(px, py, rot)[0], y=y0 + rotxy(px, py, rot)[1], w=(h if rot % 180 == 90 else w), h=(w if rot % 180 == 90 else h), net=own.get((ref, str(n))), tht=bool(lib.get("tht")), drill=lib.get("drill", 0), shape=shp) for n, px, py, w, h, shp in lib["pads"]]
PADS = [pd for p in D.PARTS if p["ref"] in PL for pd in pads_of(p["ref"])]
HV = ({"DRAIN1", "CLAMP1"} if PW in ("R", "T") else ({"COIL_B", "DM1", "DM2"} if PW == "C" else set())); MV = {"DRAIN2", "CLAMP2"}
def gap(a, b):
    dx = abs(a["x"] - b["x"]) - (a["w"] + b["w"]) / 2; dy = abs(a["y"] - b["y"]) - (a["h"] + b["h"]) / 2
    return math.hypot(max(dx, 0), max(dy, 0)) if (dx > 0 and dy > 0) else max(dx, dy)
errs = []
for i, a in enumerate(PADS):
    if abs(a["x"]) + a["w"] / 2 > SIZE[0] / 2 - 0.5 or abs(a["y"]) + a["h"] / 2 > SIZE[1] / 2 - 0.5: errs.append(f"edge {a['ref']}.{a['num']}")
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
     '(layer "dielectric 2" (type "core") (thickness 1.0)) (layer "In2.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 3" (type "prepreg") (thickness 0.2)) (layer "B.Cu" (type "copper") (thickness 0.07)) (copper_finish "HASL lead-free")))', '  (net 0 "")']
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
        L.append(f'  (zone (net {NETID[nm]}) (net_name "{nm}") (layer "{lyr}") (hatch edge 0.5) (connect_pads (clearance 0.3)) (min_thickness 0.25) (fill yes (mode hatch) (hatch_thickness 0.3) (hatch_gap 1.5) (hatch_orientation 0) (hatch_smoothing_level 0) (hatch_smoothing_value 0.1) (hatch_border_algorithm hatch_thickness) (hatch_min_hole_area 0.3) (thermal_gap 0.3) (thermal_bridge_width 0.5)) (polygon (pts {poly})))')
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
