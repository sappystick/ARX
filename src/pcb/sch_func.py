#!/usr/bin/env python3
"""Functional KiCad schematics (Step 7), generated from the board design databases (pw_design / afe_design): the part list, values and netlist are the SAME objects the layouts,
the BOM and the netlists are made from, so the schematic cannot drift from the boards.
What makes it readable: parts are grouped into FUNCTIONAL BLOCKS (src/pcb/sch_blocks.py: a title and a few lines of what the block does), drawn with real symbols (resistor, capacitor,
polarised can, diode, fuse, boxes with named pins for ICs / FETs / LEDs / connectors, power pins top and bottom, inputs left, outputs right), and every pin ends in a short wire
with a net label, so a net is followed by its name across blocks (the way a multi-sheet schematic is read). LED chains are wired directly pin to pin.
Checks (all in this script, result JSON): every part is placed exactly once; `kicad-cli sch export netlist` of the generated file is compared node by node with the design netlist
(independent of this script's geometry); `kicad-cli sch erc` is run and its counts are recorded; a PDF is exported.
What it is not: not hand-drawn, and the ICs' pin functions are the ones in the library (items marked VERIFY in docs/ASSUMPTIONS.md stay unverified).
usage (in work/):  PW=R python3 sch_func.py PB1R OUT_DIR     |  BOARD=A python3 sch_func.py AB1A OUT_DIR   (CB1D needs DISC=1)"""
import os, sys, re, json, math, uuid, subprocess, datetime
BOARD_NAME, OUT = sys.argv[1], sys.argv[2]
if BOARD_NAME.startswith("AB1"):
    os.environ["BOARD"] = BOARD_NAME[-1]; sys.argv = ["x"]; import afe_design as D
else:
    import pw_design as D
import sch_blocks as SB
G, PL, STUB = 2.54, 2.54, 2.54
CW, CWS = 1.25, 1.05                                   # estimated mm per character of 1.27 mm (labels) and 1.0 mm (values, pin names) text
ROOT = str(uuid.uuid5(uuid.NAMESPACE_URL, "arx/schf/" + BOARD_NAME))
def U(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, f"arx/schf/{BOARD_NAME}/{s}"))
def q(s): return s.replace("\\", "\\\\").replace('"', "'")
PARTS = {p["ref"]: p for p in D.PARTS}; LIB = D.LIB
PINNET = {}
for n, pins in D.NETS.items():
    for r, k in pins: PINNET[(r, str(k))] = n
NETCOUNT = {n: len(p) for n, p in D.NETS.items()}
KIND2 = {"R0402": "R", "R0603": "R", "R0805": "R", "R1206": "R", "R2512": "R", "C0402": "C", "C0603": "C", "C0805": "C", "C1210": "C", "CAN10": "CP", "FUSE1206B": "F", "FUSE1812": "F",
         "FB1812": "FB", "DSOD": "D", "DSMB": "D", "DSMC": "D"}
# pin side maps for the box symbols: by pin number; anything not listed goes left/right by number
SIDES = {"BMI270": dict(left=["14", "13", "12", "1"], right=["4", "9", "2", "3", "10", "11"], top=["5", "8"], bottom=["6", "7"]), "SK9822EC20": dict(left=["3", "4"], right=["1", "6"], top=["5"], bottom=["2"]), "LED2020": dict(left=["4"], right=["2"], top=["1"], bottom=["3"]), "D2PAK": dict(left=["1"], top=["2"], bottom=["3"]), "PMOS_SO8": dict(left=["4"], top=["5", "6", "7", "8"], bottom=["1", "2", "3"]),
         "OKI3": dict(left=["1"], right=["3"], bottom=["2"]), "SOT223": dict(left=["3"], right=["2"], bottom=["1"], top=["4"]),
         "LM393": dict(left=["2", "3", "5", "6"], right=["1", "7"], top=["8"], bottom=["4"]), "TC4420": dict(left=["2", "3"], right=["6", "7"], top=["1", "8"], bottom=["4", "5"]),
         "HC4051": dict(left=["11", "10", "9", "6", "3"], right=["13", "14", "15", "12", "1", "5", "2", "4"], top=["16"], bottom=["8", "7"]),
         "HALL_SW": dict(left=["1"], right=["3"], bottom=["2"]), "SOT23-5": dict(left=["2", "1"], right=["4"], top=["5"], bottom=["3"]),
         "SW1G66": dict(left=["1"], right=["2"], top=["5"], bottom=["3", "4"]), "AD7389": dict(left=["13", "12", "11", "10", "9", "8", "7", "6"], right=["22", "18", "19", "20", "21", "23", "24"], top=["4", "2", "3", "17", "15"], bottom=["1", "5", "14", "16", "25"]), "ADS8860": dict(left=["3", "4", "1"], right=["7", "8", "6"], top=["2", "9"], bottom=["5", "10"]),
         "OPA2211": dict(left=["3", "2", "5", "6"], right=["1", "7"], top=["8"], bottom=["4"]), "OPA2365": dict(left=["3", "2", "5", "6"], right=["1", "7"], top=["8"], bottom=["4"]),
         "REF5041": dict(left=["2", "5"], right=["6", "3"], top=["1", "7", "8"], bottom=["4"]), "BAV199": dict(left=["1"], right=["2"], bottom=["3"])}
CONN = ("HDR", "TERM", "WIRE")
def sides_of(t, pins):
    if t in SIDES:
        s = {k: list(v) for k, v in SIDES[t].items()}; used = {p for v in s.values() for p in v}
        rest = [p for p in pins if p not in used]; s["left"] = s.get("left", []) + rest[:(len(rest) + 1) // 2]; s["right"] = s.get("right", []) + rest[(len(rest) + 1) // 2:]
        return {k: s.get(k, []) for k in ("left", "right", "top", "bottom")}
    if t.startswith(CONN): return dict(left=[], right=list(pins), top=[], bottom=[])
    if t == "PICO": return dict(left=pins[:20], right=pins[20:][::-1], top=[], bottom=[])
    h = (len(pins) + 1) // 2; return dict(left=pins[:h], right=pins[h:], top=[], bottom=[])
def snap(v, m=G): return math.ceil(v / m - 1e-9) * m
def box_geom(t):
    L = LIB[t]; pins = [str(p[0]) for p in L["pins"]]; names = {str(p[0]): p[1] for p in L["pins"]}; s = sides_of(t, pins)
    nl, nr, nt, nb = (len(s[k]) for k in ("left", "right", "top", "bottom"))
    wl = max([len(names[p]) for p in s["left"]] or [0]) * CWS; wr = max([len(names[p]) for p in s["right"]] or [0]) * CWS
    H = snap(max(nl, nr, 1) * G + G, 5.08); H = max(H, 5.08 if (nt or nb) else H)
    W = snap(max(15.24, wl + wr + 5.08, nt * 2 * G + G, nb * 2 * G + G), 5.08)
    pos = {}                                                                                  # pin -> (x, y, angle) of the connection point, symbol frame (y up)
    for i, p in enumerate(s["left"]): pos[p] = (-W / 2 - PL, H / 2 - G / 2 - G * i, 0)
    for i, p in enumerate(s["right"]): pos[p] = (W / 2 + PL, H / 2 - G / 2 - G * i, 180)
    for i, p in enumerate(s["top"]): pos[p] = ((i - (nt - 1) / 2) * 2 * G, H / 2 + PL, 270)
    for i, p in enumerate(s["bottom"]): pos[p] = ((i - (nb - 1) / 2) * 2 * G, -H / 2 - PL, 90)
    return dict(t=t, pins=pins, names=names, sides=s, W=W, H=H, pos=pos)
def lib_box(g):
    t, W, H = g["t"], g["W"], g["H"]; nm = f"PF233F:BOX_{t}"
    o = [f'    (symbol "{nm}" (pin_names (offset 0.762)) (exclude_from_sim no) (in_bom yes) (on_board yes)',
         f'      (property "Reference" "U" (at 0 {H/2 + 1.27:.2f} 0) (effects (font (size 1.27 1.27))))', f'      (property "Value" "{t}" (at 0 {-H/2 - 1.27:.2f} 0) (effects (font (size 1.0 1.0))))',
         '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'      (symbol "BOX_{t}_0_1" (rectangle (start {-W/2:.2f} {H/2:.2f}) (end {W/2:.2f} {-H/2:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))', f'      (symbol "BOX_{t}_1_1"']
    for p in g["pins"]:
        x, y, a = g["pos"][p]; o.append(f'        (pin passive line (at {x:.3f} {y:.3f} {a}) (length {PL}) (name "{q(g["names"][p])}" (effects (font (size 1.0 1.0)))) (number "{q(p)}" (effects (font (size 0.9 0.9)))))')
    o.append("      )\n    )"); return "\n".join(o)
H2 = "(pin_names hide) (pin_numbers hide)"
def lib2(kind):
    nm = f"PF233F:{kind}_H"; hd = [f'    (symbol "{nm}" {H2} (exclude_from_sim no) (in_bom yes) (on_board yes)', f'      (property "Reference" "R" (at 0 3.0 0) (effects (font (size 1.27 1.27))))',
                                   f'      (property "Value" "" (at 0 -3.0 0) (effects (font (size 1.0 1.0))))', '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))']
    st = "(stroke (width 0.254) (type default))"; pin = lambda n, x, a, ln: f'        (pin passive line (at {x} 0 {a}) (length {ln}) (name "~" (effects (font (size 1.0 1.0)))) (number "{n}" (effects (font (size 1.0 1.0)))))'
    if kind in ("R", "FB", "F"):
        g = [f'(rectangle (start -2.54 1.016) (end 2.54 -1.016) {st} (fill (type {"outline" if kind == "FB" else "none"})))']
        if kind == "F": g.append(f'(polyline (pts (xy -2.54 0) (xy 2.54 0)) {st} (fill (type none)))')
        pins = [pin("1", -3.81, 0, 1.27), pin("2", 3.81, 180, 1.27)]
    elif kind in ("C", "CP"):
        g = [f'(polyline (pts (xy -0.508 -2.032) (xy -0.508 2.032)) (stroke (width 0.381) (type default)) (fill (type none)))', f'(polyline (pts (xy 0.508 -2.032) (xy 0.508 2.032)) (stroke (width 0.381) (type default)) (fill (type none)))']
        if kind == "CP": g.append('(text "+" (at -2.4 1.9 0) (effects (font (size 1.27 1.27))))')
        pins = [pin("1", -3.81, 0, 3.302), pin("2", 3.81, 180, 3.302)]
    elif kind == "D":                                                                         # pin 2 = anode (left), pin 1 = cathode (right): the library names them A / K
        g = [f'(polyline (pts (xy -1.27 -1.27) (xy -1.27 1.27) (xy 1.27 0) (xy -1.27 -1.27)) {st} (fill (type outline)))', f'(polyline (pts (xy 1.27 -1.27) (xy 1.27 1.27)) {st} (fill (type none)))']
        pins = [pin("2", -3.81, 0, 2.54), pin("1", 3.81, 180, 2.54)]
    hd.append(f'      (symbol "{kind}_H_0_1" ' + " ".join(g) + ")"); hd.append(f'      (symbol "{kind}_H_1_1"'); hd += pins; hd.append("      )\n    )"); return "\n".join(hd)
# ---------------------------------------------------------------------------------------------------- cells
def lab_w(n): return len(n) * CW + 1.0
class Cell: pass
def make_cell(ref):
    p = PARTS[ref]; t = p["type"]; c = Cell(); c.ref, c.t, c.p = ref, t, p; c.out = []; c.kind = KIND2.get(t)
    if c.kind:
        c.pins = {"1": (-3.81, 0, 0), "2": (3.81, 0, 180)} if c.kind != "D" else {"2": (-3.81, 0, 0), "1": (3.81, 0, 180)}
        ln = {pn: PINNET.get((ref, pn), "") for pn in ("1", "2")}; left = "2" if c.kind == "D" else "1"; right = "1" if c.kind == "D" else "2"
        c.lw, c.rw = lab_w(ln[left]), lab_w(ln[right]); c.w = max(c.lw + c.rw + 7.62 + 2 * STUB, len(p["value"][:28]) * CWS + 2.0, 20.0); c.h = 11.0; c.cx = c.lw + STUB + 3.81 + (c.w - c.lw - c.rw - 2 * STUB - 7.62) / 2; c.cy = 5.5
        c.gm = None
    else:
        g = box_geom(t); c.gm = g; s = g["sides"]; mx = lambda ps: max([lab_w(PINNET.get((ref, k), "")) for k in ps] or [0])
        c.lw, c.rw = mx(s["left"]), mx(s["right"]); vt = mx(s["top"]); vb = mx(s["bottom"])
        c.w = max(c.lw + c.rw + g["W"] + 2 * (PL + STUB), len(p["value"][:30]) * CWS + 2.0, len(ref) * CW + 2.0) + 2.54
        top_ext = (PL + STUB + vt) if s["top"] else 0; bot_ext = (PL + STUB + vb) if s["bottom"] else 0
        c.h = g["H"] + top_ext + bot_ext + 8.0; c.cx = c.lw + PL + STUB + g["W"] / 2 + (c.w - 2.54 - (c.lw + c.rw + g["W"] + 2 * (PL + STUB))) / 2 + 1.27; c.cy = 4.0 + top_ext + g["H"] / 2
        c.pins = g["pos"]
    return c
def place(c, X, Y, link_in=None, link_out=None, out=None):
    """emit the symbol instance, stubs and labels of cell c at the top-left corner (X, Y) of its cell; link_in / link_out = pin numbers wired directly (no label)"""
    ox, oy = X + c.cx, Y + c.cy; ref, p = c.ref, c.p; o = out
    ox, oy = round(ox / 1.27) * 1.27, round(oy / 1.27) * 1.27
    lib = f"PF233F:{c.kind}_H" if c.kind else f"PF233F:BOX_{c.t}"; hy = 3.0 if c.kind else (c.gm["H"] / 2 + 1.27); vy = -3.0 if c.kind else (-c.gm["H"] / 2 - 1.27)
    o.append(f'  (symbol (lib_id "{lib}") (at {ox:.3f} {oy:.3f} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{U(ref)}")')
    ry = oy - hy if c.kind else Y + 1.5; vyy = oy - vy if c.kind else Y + c.h - 1.5
    o.append(f'    (property "Reference" "{ref}" (at {ox:.3f} {ry:.3f} 0) (effects (font (size 1.27 1.27))))')
    o.append(f'    (property "Value" "{q(p["value"])[:44]}" (at {ox:.3f} {vyy:.3f} 0) (effects (font (size 1.0 1.0))))')
    o.append(f'    (property "Footprint" "{q(LIB[c.t]["fp"])}" (at {ox:.3f} {oy:.3f} 0) (effects (font (size 1.27 1.27)) hide))')
    for pn in c.pins: o.append(f'    (pin "{q(pn)}" (uuid "{U(ref + "/" + pn)}"))')
    o.append(f'    (instances (project "PF233-{BOARD_NAME}" (path "/{ROOT}" (reference "{ref}") (unit 1))))\n  )')
    for pn, (px, py, a) in c.pins.items():
        wx, wy = ox + px, oy - py; net = PINNET.get((ref, pn))
        dx, dy = {0: (-1, 0), 180: (1, 0), 270: (0, -1), 90: (0, 1)}[a]; ex, ey = wx + dx * STUB, wy + dy * STUB      # outward direction in sheet coordinates
        c.out.append((pn, wx, wy, ex, ey, dx, dy, net))
        if (link_in and pn == link_in) or (link_out and pn == link_out): continue
        o.append(f'  (wire (pts (xy {wx:.3f} {wy:.3f}) (xy {ex:.3f} {ey:.3f})) (stroke (width 0) (type default)) (uuid "{U(ref + "/w" + pn)}"))')
        if net is None or NETCOUNT.get(net, 0) < 2:
            o.append(f'  (no_connect (at {ex:.3f} {ey:.3f}) (uuid "{U(ref + "/nc" + pn)}"))')
            if net: o.append(f'  (text "{q(net)}" (exclude_from_sim no) (at {ex + (1.5 if dx >= 0 else -1.5):.3f} {ey - 1.0:.3f} 0) (effects (font (size 1.0 1.0)) (justify {"left" if dx >= 0 else "right"})) (uuid "{U(ref + "/nt" + pn)}"))')
        else:
            ang, just = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"), (0, 1): (270, "left")}[(dx, dy)]
            o.append(f'  (label "{q(net)}" (at {ex:.3f} {ey:.3f} {ang}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{U(ref + "/l" + pn)}"))')
def txt(o, s, x, y, size=1.27, bold=False, key=""):
    o.append(f'  (text "{q(s)}" (exclude_from_sim no) (at {x:.3f} {y:.3f} 0) (effects (font (size {size} {size}){" bold" if bold else ""}) (justify left top)) (uuid "{U("t/" + key + s[:20] + str(round(x)) + str(round(y)))}"))')
def main():
    blocks = SB.blocks(BOARD_NAME, PARTS, PINNET)
    placed = [r for b in blocks for r in b["refs"]]; dup = {r for r in placed if placed.count(r) > 1}; miss = [r for r in PARTS if r not in placed]
    if miss: blocks.append(dict(title="Other parts", note=["parts not assigned to a function above"], refs=miss)); placed += miss
    assert not dup, f"parts in two blocks: {sorted(dup)}"
    cells = {r: make_cell(r) for r in placed}
    # block internal layout: shelf packing of the cells, MAXW wide
    out = []; MARG, HEAD = 5.08, 0
    lay = []
    for b in blocks:
        cs = [cells[r] for r in b["refs"]]; link = b.get("link"); maxw = b.get("width", 190.0); cols = b.get("cols")
        rows, cur, cw = [], [], 0.0
        for c in cs:
            gap = (14.0 if link else 5.08)
            if cur and ((cols and len(cur) >= cols) or (not cols and cw + c.w > maxw)): rows.append(cur); cur, cw = [], 0.0
            cur.append(c); cw += c.w + gap
        if cur: rows.append(cur)
        head = 6.0 + 3.2 * len(b["note"]) + 2.0; y = head + MARG; w = 0; items = []
        for row in rows:
            x = MARG; rh = max(c.h for c in row)
            for i, c in enumerate(row):
                items.append((c, x, y, i)); x += c.w + (14.0 if link else 5.08)
            w = max(w, x); y += rh + 2.54
        lay.append(dict(b=b, items=items, w=max(w + MARG - 5.08, len(b["title"]) * 2.2 + 12, 90.0, max(len(n) for n in b["note"]) * 1.25 + 8), h=y + MARG - 2.54, rows=rows))
    # block placement on the sheet: shelf packing, sheet width chosen from the total area
    area = sum(l["w"] * l["h"] for l in lay); SW = max(max(l["w"] for l in lay) + 40, math.sqrt(area * 2.6)); X0, Y0 = 20.32, 38.1; x, y, rh = X0, Y0, 0; bpos = []
    for l in lay:
        if x > X0 and x + l["w"] > X0 + SW: x = X0; y += rh + 12.7; rh = 0
        bpos.append((x, y)); x += l["w"] + 12.7; rh = max(rh, l["h"])
    SWf = max(bp[0] + l["w"] for bp, l in zip(bpos, lay)) + 20.32; SH = y + rh + 40
    pw, ph = round(SWf / 25.4 + 1) * 25.4, round(SH / 25.4 + 1) * 25.4
    libs = {}; o = []
    for bp, l in zip(bpos, lay):
        b = l["b"]; bx, by = bp
        o.append(f'  (rectangle (start {bx:.2f} {by:.2f}) (end {bx + l["w"]:.2f} {by + l["h"]:.2f}) (stroke (width 0.3) (type dash)) (fill (type none)) (uuid "{U("frame/" + b["title"])}"))')
        txt(o, b["title"], bx + 2.54, by + 2.0, 2.54, True, "title")
        for i, s in enumerate(b["note"]): txt(o, s, bx + 2.54, by + 6.0 + 3.2 * i, 1.4, False, f"n{i}")
        link = b.get("link"); items = l["items"]
        for k, (c, ix, iy, col) in enumerate(items):
            nxt = items[k + 1] if k + 1 < len(items) else None; prv = items[k - 1] if k else None
            lo = link[1] if link and nxt and abs(nxt[2] - iy) < 0.01 else None; li = link[0] if link and prv and abs(prv[2] - iy) < 0.01 else None
            # `link` = (output pin number, input pin number) of the daisy chain: this cell's output goes straight to the next cell's input
            place(c, bx + ix, by + iy, link_in=(link[1] if li else None), link_out=(link[0] if lo else None), out=o)
            if c.t not in libs: libs[c.t] = (lib_box(c.gm) if c.gm else None)
        if link:
            for k, (c, ix, iy, col) in enumerate(items[:-1]):
                n2 = items[k + 1]
                if abs(n2[2] - iy) > 0.01: continue
                a = next(t for t in c.out if t[0] == link[0]); bb = next(t for t in n2[0].out if t[0] == link[1])
                o.append(f'  (wire (pts (xy {a[1]:.3f} {a[2]:.3f}) (xy {bb[1]:.3f} {bb[2]:.3f})) (stroke (width 0) (type default)) (uuid "{U("chain/" + c.ref)}"))')
    kinds = sorted({c.kind for c in cells.values() if c.kind}); lib_text = [lib2(k) for k in kinds] + [v for v in libs.values() if v]
    desc = SB.TITLE[BOARD_NAME]
    head = [f'(kicad_sch (version 20231120) (generator "arx_sch_func") (generator_version "1") (uuid "{ROOT}") (paper "User" {pw:.1f} {ph:.1f})',
            f'  (title_block (title "PF233-{BOARD_NAME}  functional schematic") (date "{SB.DATE}") (rev "r3") (company "ARX / PHI-FOLD 233") (comment 1 "{q(desc)}") (comment 2 "MODELED design: not built, not bench-tested.") (comment 3 "Generated: src/pcb/sch_func.py; checked against the netlist."))',
            "  (lib_symbols"] + lib_text + ["  )"]
    legend = []
    txt(legend, "How to read: parts sit in functional blocks (dashed frames). Every pin ends in a short wire with its NET NAME; equal names are connected (also between blocks). A cross = intentionally unconnected pin.", X0, 10.16, 1.4, False, "legend1")
    txt(legend, "Diode symbols point anode to cathode. Pin names are those of the library; items marked VERIFY in docs/ASSUMPTIONS.md are unverified. MODELED design: not built, not bench-tested.", X0, 14.0, 1.4, False, "legend2")
    txt(legend, f"PF233-{BOARD_NAME}: {desc}", X0, 4.0, 2.5, True, "sheet")
    tail = ['  (sheet_instances (path "/" (page "1")))', ")"]; txtall = "\n".join(head + legend + o + tail)
    _bare = re.sub(r'"(?:[^"\\]|\\.)*"', "", txtall); assert _bare.count("(") == _bare.count(")"), "paren balance"
    os.makedirs(OUT, exist_ok=True); f = f"{OUT}/PF233-{BOARD_NAME}_functional.kicad_sch"; open(f, "w").write(txtall)
    return f, len(placed), blocks
def sx(t):
    """minimal s-expression parser for the kicad netlist export"""
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', t); st = [[]]
    for k in tok:
        if k == "(": st.append([])
        elif k == ")": x = st.pop(); st[-1].append(x)
        else: st[-1].append(k.strip('"') if k.startswith('"') else k)
    return st[0][0]
def check(f, nparts):
    base = f[:-10]; res = dict(board=BOARD_NAME, parts=nparts, errors=[])
    net = base + ".net"; r = subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, f], capture_output=True, text=True)
    if r.returncode: res["errors"].append("netlist export failed: " + r.stderr[-200:])
    else:
        t = sx(open(net).read()); nets = [x for x in next(y for y in t if isinstance(y, list) and y and y[0] == "nets")[1:]]
        got = {}
        for n in nets:
            name = next(y for y in n if isinstance(y, list) and y[0] == "name")[1].lstrip("/"); nodes = frozenset((next(z for z in y if isinstance(z, list) and z[0] == "ref")[1] if False else y[1][1], y[2][1]) for y in n if isinstance(y, list) and y[0] == "node")
            got[nodes] = name
        want = {frozenset((r_, str(k)) for r_, k in pins): n for n, pins in D.NETS.items() if len(pins) >= 2}
        for nodes, n in want.items():
            if nodes not in got: res["errors"].append(f"net {n}: node set differs in the KiCad netlist")
            elif not got[nodes].startswith("Net-(") and got[nodes] != n and not got[nodes].endswith("/" + n): res["errors"].append(f"net {n}: named {got[nodes]} in KiCad")
        extra = [n for nodes, n in got.items() if nodes not in want and len(nodes) >= 2]; res["errors"] += [f"extra KiCad net {n}" for n in extra]
        res["nets_compared"] = len(want)
    er = base + "_erc.json"; r = subprocess.run(["kicad-cli", "sch", "erc", "--format", "json", "--severity-all", "-o", er, f], capture_output=True, text=True)
    if os.path.exists(er):
        j = json.load(open(er)); v = [x for s in j.get("sheets", []) for x in s.get("violations", [])]; c = {}
        for x in v: c[(x["severity"], x["type"])] = c.get((x["severity"], x["type"]), 0) + 1
        res["erc"] = {f"{a}:{b}": n for (a, b), n in sorted(c.items())}; res["erc_errors"] = sum(n for (a, b), n in c.items() if a == "error")
    else: res["errors"].append("ERC did not run: " + r.stderr[-200:])
    r = subprocess.run(["kicad-cli", "sch", "export", "pdf", "-o", base + ".pdf", f], capture_output=True, text=True); res["pdf"] = os.path.exists(base + ".pdf")
    res["n_errors"] = len(res["errors"]) + res.get("erc_errors", 0)
    json.dump(res, open(base + "_check.json", "w"), indent=1); print(BOARD_NAME, "parts", nparts, "net mismatches", len(res["errors"]), "ERC", res.get("erc"), "pdf", res["pdf"])
    return res
if __name__ == "__main__":
    f, n, blocks = main(); r = check(f, n); sys.exit(1 if r["n_errors"] else 0)
