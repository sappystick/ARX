#!/usr/bin/env python3
"""PF233-AB1{A,B} schematic: KiCad 7 .kicad_sch (net-label style, generated symbols) + PNG drawing, both from the design database."""
import os, uuid, math, sys
import importlib
D = importlib.import_module(os.environ.get("DESIGN", "afe_design"))
B = D.BOARD; NAME = os.environ.get("NAME", f"AB1{B}"); TITLE = os.environ.get("TITLE", "analog receiving board")
OUT = os.environ.get("OUTDIR", f"kit_v3/SCH_{NAME}"); os.makedirs(OUT, exist_ok=True)
NS = uuid.UUID("12345678-1234-5678-1234-567812345678")
def uid(s): return str(uuid.uuid5(NS, f"{B}-{s}"))
owner = {}
for n, pins in D.NETS.items():
    for pr in pins: owner[pr] = n
# ---------------------------------------------------------------- symbol geometry
def geom(typ):
    pins = D.LIB[typ]["pins"]; n = len(pins)
    if n == 2: left, right = pins[:1], pins[1:]
    elif typ in ("BAV199",): left, right = pins[:2], pins[2:]
    elif typ == "SW1G66": left, right = pins[:3], pins[3:]
    else:
        h = (n + 1) // 2; left, right = pins[:h], pins[h:]
    rows = max(len(left), len(right)); w = 7.62 if n == 2 else 17.78
    h = max(rows, 2) * 2.54 + 2.54
    return left, right, rows, w, h
def pin_pos(typ, num):
    left, right, rows, w, h = geom(typ)
    for side, lst in (("L", left), ("R", right)):
        for i, (pn, name, et) in enumerate(lst):
            if pn == num:
                y = (rows - 1) / 2 * 2.54 - i * 2.54 if rows > 1 else 0.0
                y = round(y / 1.27) * 1.27
                return (-(w / 2 + 2.54) if side == "L" else (w / 2 + 2.54)), y, side
    raise KeyError(num)
ETYPE = {"passive": "passive", "input": "input", "output": "output", "power_in": "power_in", "power_out": "power_out", "no_connect": "no_connect"}
# ---------------------------------------------------------------- placement on the sheet
ROW_ORDER = ["RS", "D", "SW", "CSW", "RG", "RF", "CF", "RAAF", "CAAF", "UA", "CAV", "CDV", "CRF"]
def split_ref(ref):
    i = 0
    while i < len(ref) and not ref[i].isdigit(): i += 1
    return ref[:i], ref[i:]
place = {}; PITCH_X = 62.0; ROW_H = 78.0
for r, ch in enumerate(D.CH, 1):
    for c, pre in enumerate(ROW_ORDER):
        ref = f"{pre}{r}"
        if ref in D.BYREF: place[ref] = (40 + c * PITCH_X, 50 + (r - 1) * ROW_H)
shared = [p["ref"] for p in D.PARTS if p["ref"] not in place]
y0 = 50 + len(D.CH) * ROW_H
for i, ref in enumerate(shared): place[ref] = (40 + (i % 13) * PITCH_X, y0 + (i // 13) * 62.0)
W_SHEET = 40 + 13 * PITCH_X + 40; H_SHEET = y0 + ((len(shared) + 12) // 13) * 62.0 + 40
# ---------------------------------------------------------------- KiCad schematic
L = ["(kicad_sch (version 20230121) (generator pf233_export)", f'  (uuid "{uid("sheet")}")', '  (paper "User" %d %d)' % (math.ceil(W_SHEET / 10) * 10, math.ceil(H_SHEET / 10) * 10),
     f'  (title_block (title "PF233-{NAME} {TITLE}") (rev "1") (comment 1 "Generated from afe_design.py; IC pin maps marked VERIFY must be checked against datasheets"))', "  (lib_symbols"]
for typ in sorted({p["type"] for p in D.PARTS}):
    left, right, rows, w, h = geom(typ); lib = D.LIB[typ]
    L.append(f'    (symbol "PF233:{typ}" (pin_names (offset 0.762)) (in_bom yes) (on_board yes)')
    L.append(f'      (property "Reference" "U" (at 0 {h / 2 + 1.5:.2f} 0) (effects (font (size 1.27 1.27))))')
    L.append(f'      (property "Value" "{typ}" (at 0 {-h / 2 - 1.5:.2f} 0) (effects (font (size 1.27 1.27))))')
    L.append(f'      (property "Footprint" "{lib["fp"]}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    L.append(f'      (symbol "{typ}_0_1" (rectangle (start {-w / 2:.2f} {h / 2:.2f}) (end {w / 2:.2f} {-h / 2:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))')
    L.append(f'      (symbol "{typ}_1_1"')
    for pn, name, et in lib["pins"]:
        px, py, side = pin_pos(typ, pn); ang = 0 if side == "L" else 180
        L.append(f'        (pin {ETYPE.get(et, "passive")} line (at {px:.2f} {py:.2f} {ang}) (length 2.54) (name "{name}" (effects (font (size 1.0 1.0)))) (number "{pn}" (effects (font (size 1.0 1.0)))))')
    L.append("      )"); L.append("    )")
L.append("  )")
for p in D.PARTS:
    ref = p["ref"]; typ = p["type"]; X, Y = place[ref]; left, right, rows, w, h = geom(typ)
    L.append(f'  (symbol (lib_id "PF233:{typ}") (at {X:.2f} {Y:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid("sym" + ref)}")')
    L.append(f'    (property "Reference" "{ref}" (at {X:.2f} {Y - h / 2 - 1.5:.2f} 0) (effects (font (size 1.27 1.27))))')
    L.append(f'    (property "Value" "{p["value"]}" (at {X:.2f} {Y + h / 2 + 1.5:.2f} 0) (effects (font (size 1.27 1.27))))')
    L.append(f'    (property "Footprint" "{D.LIB[typ]["fp"]}" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) hide))')
    L.append(f'    (property "MPN" "{p["mpn"]}" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) hide))')
    for pn, name, et in D.LIB[typ]["pins"]: L.append(f'    (pin "{pn}" (uuid "{uid(f"pin{ref}.{pn}")}"))')
    L.append("  )")
    for pn, name, et in D.LIB[typ]["pins"]:
        net = owner.get((ref, pn))
        px, py, side = pin_pos(typ, pn); ax, ay = X + px, Y - py
        if net is None:
            L.append(f'  (no_connect (at {ax:.2f} {ay:.2f}) (uuid "{uid(f"nc{ref}.{pn}")}"))'); continue
        dx = -3.81 if side == "L" else 3.81
        L.append(f'  (wire (pts (xy {ax:.2f} {ay:.2f}) (xy {ax + dx:.2f} {ay:.2f})) (stroke (width 0) (type default)) (uuid "{uid(f"w{ref}.{pn}")}"))')
        L.append(f'  (label "{net}" (at {ax + dx:.2f} {ay:.2f} {180 if side == "L" else 0}) (effects (font (size 1.27 1.27)) (justify {"right" if side == "L" else "left"} bottom)) (uuid "{uid(f"l{ref}.{pn}")}"))')
L.append('  (sheet_instances (path "/" (page "1")))'); L.append(")")
open(f"{OUT}/PF233-{NAME}.kicad_sch", "w").write("\n".join(L))
bal = sum(l.count("(") - l.count(")") for l in L); print("kicad_sch paren balance:", bal)
# ---------------------------------------------------------------- PNG drawing
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig = plt.figure(figsize=(W_SHEET / 14, H_SHEET / 14)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W_SHEET); ax.set_ylim(H_SHEET, 0); ax.axis("off")
NETCOL = {"GND": "#444", "+5VA": "#c0392b", "+3V3D": "#d35400", "VCM": "#8e44ad", "VREF": "#16a085", "VREF_RAW": "#16a085", "BLANK": "#2c3e50"}
for r, ch in enumerate(D.CH, 1): ax.text(8, 50 + (r - 1) * ROW_H - 26, f"Channel {r}: {ch}   (input -> series R -> clamp + blanking switch -> x40 low-noise amp -> 400 kHz filter -> 16-bit ADC)", fontsize=11, weight="bold", color="#1a5276")
ax.text(8, y0 - 26, "Shared: op-amps, AD7389-4 quad ADC with its internal 2.5 V reference, VCM divider and buffer, bulk decoupling, connectors", fontsize=11, weight="bold", color="#1a5276")
ax.text(8, 12, f"PF233-{NAME}  {TITLE}  -  net-label schematic (every pin label = net name; same net name = connected)", fontsize=13, weight="bold")
for p in D.PARTS:
    ref = p["ref"]; typ = p["type"]; X, Y = place[ref]; left, right, rows, w, h = geom(typ)
    ax.add_patch(plt.Rectangle((X - w / 2, Y - h / 2), w, h, fc="#fdfefe", ec="#154360", lw=1.2))
    ax.text(X, Y - h / 2 - 1.8, f"{ref}  {p['value']}", ha="center", va="bottom", fontsize=7.5, weight="bold", color="#1b4f72")
    for pn, name, et in D.LIB[typ]["pins"]:
        px, py, side = pin_pos(typ, pn); ax_, ay_ = X + px, Y - py; net = owner.get((ref, pn)); d = -3.81 if side == "L" else 3.81
        ibx = X + (-w / 2 if side == "L" else w / 2)
        ax.plot([ax_, ibx], [ay_, ay_], color="#154360", lw=1)
        ax.text(ibx + (1.0 if side == "L" else -1.0), ay_, f"{pn} {name}" if len(D.LIB[typ]["pins"]) > 2 else pn, ha="left" if side == "L" else "right", va="center", fontsize=5.2, color="#555")
        if net:
            ax.plot([ax_, ax_ + d], [ay_, ay_], color="#154360", lw=1)
            ax.text(ax_ + d + (-0.8 if side == "L" else 0.8), ay_, net, ha="right" if side == "L" else "left", va="center", fontsize=6.4, color=NETCOL.get(net, "#1e8449"))
        else: ax.text(ax_, ay_, "x", color="r", fontsize=7, ha="center", va="center")
fig.savefig(f"{OUT}/PF233-{NAME}_schematic.png", dpi=110); print("schematic", OUT)
