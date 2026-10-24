#!/usr/bin/env python3
"""Put the routed copper into a KiCad board: segments, vias, hatched plane zones, and the notched outline. usage: kicad_inject.py BOARD ROUTE.json OUT.kicad_pcb NOTCH_SIGN [six]"""
import json, math, re, sys, numpy as np
board, rj, out, nsign = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]); six = "six" in sys.argv
t = open(f"kit_v18/{board}/PF233-{board}.kicad_pcb").read(); r = json.load(open(rj)); R = r["R"]; CX = CY = 100.0
nets = {n: int(i) for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', t)}
if six:
    t = t.replace('(0 "F.Cu" signal) (1 "In1.Cu" signal) (2 "In2.Cu" signal) (31 "B.Cu" signal)', '(0 "F.Cu" signal) (1 "In1.Cu" signal) (2 "In2.Cu" signal) (3 "In3.Cu" signal) (4 "In4.Cu" signal) (31 "B.Cu" signal)')
    t = re.sub(r'\(stackup .*?\(copper_finish "[^"]*"\)\)\)', '(stackup (layer "F.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 1" (type "prepreg") (thickness 0.12)) (layer "In1.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 2" (type "core") (thickness 0.4)) (layer "In2.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 3" (type "prepreg") (thickness 0.35)) (layer "In3.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 4" (type "core") (thickness 0.4)) (layer "In4.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 5" (type "prepreg") (thickness 0.12)) (layer "B.Cu" (type "copper") (thickness 0.035)) (copper_finish "Immersion silver")))', t, flags=re.S)
t = "\n".join(l for l in t.split("\n") if not l.strip().startswith("(zone") and not ("Edge.Cuts\"))" in l and "gr_circle" in l))   # drop the template zones and the template circle outline (the earlier "A and B or C" kept every zone)
def outline(Rr, s):
    w = 7.6; yb = 36.5; yc = math.sqrt(Rr * Rr - w * w); A = math.atan2(s * yc, w); B = math.atan2(s * yc, -w)
    a0, a1 = (A, B + 2 * math.pi) if s < 0 else (B, A + 2 * math.pi); a = np.linspace(a0, a1, 180); pts = [(Rr * math.cos(x), Rr * math.sin(x)) for x in a]
    S, E = pts[0], pts[-1]; return pts + [(E[0], s * yb), (S[0], s * yb), S]
ol = outline(R, nsign); add = []
for a, b in zip(ol[:-1], ol[1:]): add.append(f'  (gr_line (start {CX+a[0]:.3f} {CY+a[1]:.3f}) (end {CX+b[0]:.3f} {CY+b[1]:.3f}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts"))')
for tr in r["tracks"]:
    nid = nets[tr["net"]]; p = tr["pts"]
    for a, b in zip(p[:-1], p[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) < 1e-9: continue
        add.append(f'  (segment (start {CX+a[0]:.4f} {CY+a[1]:.4f}) (end {CX+b[0]:.4f} {CY+b[1]:.4f}) (width {tr["width"]}) (layer "{tr["layer"]}") (net {nid}))')
for v in r["vias"]: add.append(f'  (via (at {CX+v[0]:.4f} {CY+v[1]:.4f}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {nets[v[2]]}))')
inner = ol[:]   # zone polygon: the outline inset by 0.3 mm
for net, lay in r["planes"].items():
    poly = outline(R - 0.4, nsign); pts = " ".join(f"(xy {CX+x:.3f} {CY+y:.3f})" for x, y in poly[:-1])
    add.append(f'  (zone (net {nets[net]}) (net_name "{net}") (layer "{lay}") (hatch edge 0.5) (connect_pads (clearance 0.3)) (min_thickness 0.25) (fill yes (mode hatch) (hatch_thickness 0.4) (hatch_gap 1.2) (hatch_orientation 0) (hatch_smoothing_level 0) (hatch_smoothing_value 0.1) (hatch_border_algorithm hatch_thickness) (hatch_min_hole_area 0.3) (thermal_gap 0.3) (thermal_bridge_width 0.5)) (polygon (pts {pts})))')
t = t.rstrip()
assert t.endswith(")"); t = t[:-1] + "\n" + "\n".join(add) + "\n)\n"
assert t.count("(") == t.count(")"), "paren balance"; open(out, "w").write(t); print(board, "segments", sum(1 for l in add if "(segment" in l), "vias", sum(1 for l in add if "(via" in l), "zones", len(r["planes"]), "->", out)
