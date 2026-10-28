#!/usr/bin/env python3
"""PM1 / PB1 export: hand-set placement + placement DRC (assembly gap, edge, HV clearance) -> KiCad PCB (placed, UNROUTED), custom DRC rules, BOM, pick&place, STL, preview.
Routing of the power nets is intentionally left for a layout engineer (HV / high-current)."""
import os, sys, json, math, csv
import models3d as M3
import numpy as np
import pw_design as D
import rodin_core_v4 as rc, golden_cone_head as g
PW = D.PW; NAME = "CB1D"; OUT = "kit_v18/CB1D"; os.makedirs(OUT, exist_ok=True)
SIZE = {"M": (28.0, 136.0), "T": (28.0, 224.0), "C": (78.0, 78.0), "R": (70.0, 70.0), "H": (24.0, 60.0)}[PW]; CX, CY = 100.0, 100.0
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
R_RIB = 37.2                                              # inner radius of the cylinder ribs (head_crosscheck.py rib_polys)
REL = {}   # satellite -> (parent, dx, dy): anchored to where the parent was actually placed (decoupling capacitors at their IC's supply pins)
def autoplace(fixed, anchors, rots=None):
    rots = rots or {}; placed = {}
    for ref, (x, y, rot) in fixed.items(): placed[ref] = (x, y, rot)
    order = sorted([p["ref"] for p in D.PARTS if p["ref"] not in fixed], key=lambda r: -((lambda b: (b[2] - b[0]) * (b[3] - b[1]))(bbox_of(r, 0, 0, 0))))
    order = [r for r in order if r not in REL]; [order.insert(order.index(par) + 1 + k, sat) for par in dict.fromkeys(v[0] for v in REL.values()) if par in order for k, sat in enumerate(s for s, v in REL.items() if v[0] == par)]
    boxes = {r: bbox_of(r, *placed[r]) for r in placed}
    def free(ref, x, y, rot):
        b = bbox_of(ref, x, y, rot)
        if max(math.hypot(b[i], b[j]) for i in (0, 2) for j in (1, 3)) > min(SIZE[0] / 2 - 0.8, R_RIB - 0.3): return False       # bodies stay inside the rib annulus (r >= 37.2 in the vault): clear of every rib, wherever the ribs sit
        for r2, b2 in boxes.items():
            m = 1.2 if (is_hv(ref) != is_hv(r2)) else 0.5
            if not (b[2] + m < b2[0] or b[0] - m > b2[2] or b[3] + m < b2[1] or b[1] - m > b2[3]): return False
        return True
    for ref in order:
        ax, ay = anchors.get(ref, (0.0, 0.0)); rot = rots.get(ref, 0); done = False
        if ref in REL and REL[ref][0] in placed: ax, ay = placed[REL[ref][0]][0] + REL[ref][1], placed[REL[ref][0]][1] + REL[ref][2]
        for rad in np.arange(0, 80, 0.5):
            n = max(1, int(rad * 6))
            for k in range(n):
                a = 2 * math.pi * k / n; x = round((ax + rad * math.cos(a)) * 2) / 2; y = round((ay + rad * math.sin(a)) * 2) / 2
                if free(ref, x, y, rot): placed[ref] = (x, y, rot); boxes[ref] = bbox_of(ref, x, y, rot); done = True; break
            if done: break
        if not done: print("could not place", ref)
    return placed
if PW == "C":
    fixed = {"U1": (0.0, -16.0, 90)}
    S = 0.82
    anchors = {"JPW": (13, 29), "JTR": (-13, 30), "JA": (-33, -2), "JB": (-33, 8), "JPB": (-26, 18), "JCL": (33, 6), "JHTA": (33, -14), "JLB": (-33, -20), "UG": (7, -30.5), "RGA": (11.5, -30.5), "RGL": (14, -30.5), "M5": (12, 6), "UL": (2, 14), "UM": (-3, -2), "F1": (22, 24), "DTV": (21, 20), "CI1": (14, 24), "CI2": (14, 20), "C5A": (4, 6), "C5B": (4, 10),
               "FB2": (5, 0), "CV1": (9, 0), "CV2": (9, 3), "CV3": (5, 3), "CL1": (-2, 17), "CL2": (-2, 21), "RML": (-2, 24), "CP1": (-12, -2), "CP2": (-12, -5), "CM1": (2, -3), "RMO": (-7, -3), "CMO": (-7, 0),
               "RR1": (-14, 4), "RR2": (-14, 8), "CR1": (-17, 6), "CR2": (-17, 10), "RV1": (22, 12), "RV2": (22, 15), "CV4": (25, 14), "RSH": (26, -3), "CSH": (22, -3), "RT1": (24, -8), "RD1": (24, -11),
               "DH1": (20, -8), "DL1": (20, -11), "CQ1": (18, -14), "RP1": (22, -14), "DH2": (14, -8), "DL2": (14, -11), "CQ2": (16, -14), "RP2": (12, -14), "JDBG": (-12, 20),
               "RJB10": (4, 27), "RJ5": (-8, 24), "RJ6": (-8, 21), "RDM1": (28, -2), "RDM2": (28, 3), "RDM3": (28, 8), "CMON": (30, -12), "RBI": (30, -9), "RJX": (21, -17), "RJY": (21, -20), "CJX": (25, -17), "CJY": (25, -20), "RUS": (17, -22), "CUS": (21, -22),
               "RHTA": (30, -18), "CHTA": (27, -21), "DHA1": (24, -24), "DHA2": (20, -26)}
    rots = {"JA": 0, "JB": 0, "JPW": 90, "JTR": 90, "JPB": 0, "JCL": 0, "JHTA": 0, "JLB": 0, "UG": 180}
    # gyro cluster (CB1D-C2): in the free band above the Pico's top header, turned 180 deg so pins 12-14 (CSB, SCL, SDA) face the Pico I2C pins 26 / 27;
    # 100 nF at VDDIO (pin 5) and VDD (pin 8). History 2026-10-28: in the right-hand corner (28, -16) the perimeter routes left 44/47 routed
    REL.update({"CG1": ("UG", 1.0, -2.4), "CG2": ("UG", -2.2, -2.4)})     # UG at 180 deg: pins 5 / 8 face away from the Pico; the pull-ups may sit anywhere on SDA / SCL
    PL = autoplace(fixed, anchors, rots)
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
    if math.hypot(abs(a["x"]) + a["w"] / 2, abs(a["y"]) + a["h"] / 2) > SIZE[0] / 2 - 0.5: errs.append(f"edge {a['ref']}.{a['num']}")
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
     '(layer "dielectric 2" (type "core") (thickness 1.0)) (layer "In2.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 3" (type "prepreg") (thickness 0.2)) (layer "B.Cu" (type "copper") (thickness 0.07)) (copper_finish "Immersion silver")))', '  (net 0 "")']
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
    _m = M3.model_line(p["type"]); _m and L.append(_m)
    for n, px, py, w, h, shp in lib["pads"]:
        net = own.get((ref, str(n))); nid = NETID.get(net, 0) if net else 0
        if lib.get("tht"): L.append(f'    (pad "{n}" thru_hole {"circle" if shp == "circle" else "rect"} (at {px:.3f} {py:.3f}{" " + str(rot) if rot else ""}) (size {w} {h}) (drill {lib["drill"]}) (layers "*.Cu" "*.Mask") (net {nid} "{net or ""}"))')
        else: L.append(f'    (pad "{n}" smd {"rect" if shp == "rect" else "roundrect"} (at {px:.3f} {py:.3f}{" " + str(rot) if rot else ""}) (size {w:.3f} {h:.3f}) (layers "F.Cu" "F.Paste" "F.Mask") (net {nid} "{net or ""}"))')
    L.append("  )")
L.append(f'  (gr_circle (center {CX:.3f} {CY:.3f}) (end {CX + W / 2:.3f} {CY:.3f}) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts"))')
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
    x0, y0, rot = PL[p["ref"]]; pm = M3.placed_mesh(p["type"], D.LIB[p["type"]], x0, y0, rot)
    if pm is not None: parts.append(pm)
Vs, Fs = g.merge(parts); rc.write_stl(f"{OUT}/PF233-{NAME}_board_with_components.stl", Vs, Fs, NAME)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(W / 8, H / 8 + 0.6)); ax.add_patch(plt.Circle((0, 0), W / 2, fc="#0b3d2e", ec="w")); ax.set_aspect("equal"); ax.set_xlim(-W / 2 - 2, W / 2 + 2); ax.set_ylim(H / 2 + 2, -H / 2 - 2)
for pd in PADS:
    col = "#e74c3c" if pd["net"] in HV else ("#f39c12" if pd["net"] in MV else "#ecf0f1")
    ax.add_patch(plt.Rectangle((pd["x"] - pd["w"] / 2, pd["y"] - pd["h"] / 2), pd["w"], pd["h"], fc=col, ec="k", lw=0.2))
for p in D.PARTS: ax.text(PL[p["ref"]][0], PL[p["ref"]][1], p["ref"], color="w", fontsize=6, ha="center", va="center")
ax.set_title(f"PF233-{NAME} placement (UNROUTED)  red = 500 V clamp nets (>=1.0 mm), orange = ~100 V nets (>=0.5 mm)", fontsize=8); fig.tight_layout(); fig.savefig(f"{OUT}/PF233-{NAME}_placement_preview.png", dpi=110)
json.dump(chk, open(f"{OUT}/PF233-{NAME}_placement_check.json", "w"), indent=1); print("exported", OUT)

import json as _j
_j.dump(dict(R=SIZE[0]/2,pads=PADS,parts=[dict(ref=q["ref"],type=q["type"],x=PL[q["ref"]][0],y=PL[q["ref"]][1],rot=PL[q["ref"]][2]) for q in D.PARTS if q["ref"] in PL]),open(OUT+"/pads.json","w"))
