#!/usr/bin/env python3
"""Put the routed copper (tracks, vias) into the PLACED KiCad file of a rectangular board (PB1R). The placed file already carries the footprints, the rectangular Edge.Cuts outline and the
hatched GND / VBUS plane zones; kicad_inject.py is the disc-and-notch version for CB1D / LB1.
usage: rect_inject.py BOARD ROUTE.json PLACED.kicad_pcb OUT.kicad_pcb"""
import sys, re, json
board, rj, placed, out = sys.argv[1:5]; CX = CY = 100.0
t = open(placed).read(); r = json.load(open(rj))
nets = {n: int(i) for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', t)}
add = []
for tr in r["tracks"]:
    nid = nets[tr["net"]]; p = tr["pts"]
    for a, b in zip(p[:-1], p[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) < 1e-9: continue
        add.append(f'  (segment (start {CX+a[0]:.4f} {CY+a[1]:.4f}) (end {CX+b[0]:.4f} {CY+b[1]:.4f}) (width {tr["width"]}) (layer "{tr["layer"]}") (net {nid}))')
for v in r["vias"]: add.append(f'  (via (at {CX+v[0]:.4f} {CY+v[1]:.4f}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {nets[v[2]]}))')
t = t.rstrip(); assert t.endswith(")")
t = t[:-1] + "\n" + "\n".join(add) + "\n)\n"
assert t.count("(") == t.count(")"), "paren balance"
open(out, "w").write(t)
print(board, "segments", sum(1 for l in add if "(segment" in l), "vias", sum(1 for l in add if "(via" in l), "zones", t.count("(zone"), "->", out)
