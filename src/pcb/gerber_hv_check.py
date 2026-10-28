#!/usr/bin/env python3
"""Check the plane-layer Gerbers written by gerber_out.py: every through-hole pad and via of an HV net must have a clear (LPC) flash of at least pad + 2 x 1.0 mm on every plane layer.
usage: gerber_hv_check.py BOARD GERBER_DIR PREFIX HV_NETS(comma)  -> prints a summary and writes kit_v22/gerber_hv_<BOARD>.json. Independent of the writer: it re-reads the .gbr files."""
import sys, re, json, glob, math
board, d, prefix, hv = sys.argv[1], sys.argv[2], sys.argv[3], set(sys.argv[4].split(","))
import os
PJ = f"kit_v18/{board}/pads.json" if os.path.exists(f"kit_v18/{board}/pads.json") else f"kit_v6/{board}/pads.json"
P = json.load(open(PJ))["pads"]; r = json.load(open(f"kit_v20/route_{board}.json"))
targets = [(p["x"], p["y"], max(p["w"], p["h"]), f"{p['ref']}.{p['num']}") for p in P if p["tht"] and p["net"] in hv] + [(v[0], v[1], 0.6, f"via {v[2]}") for v in r["vias"] if v[2] in hv]
res = []
for ly in set(r["planes"].values()):
    f = f"{d}/{prefix}-{ly.replace('.', '_')}.gbr"; txt = open(f).read(); ap = {int(m[1]): float(m[2]) for m in re.finditer(r"%ADD(\d+)C,([\d.]+)\*%", txt)}
    clear = []; pol = "D"; cur = None
    for line in txt.split("\n"):
        if line.startswith("%LP"): pol = line[3]; continue
        m = re.match(r"D(\d+)\*$", line)
        if m: cur = int(m[1]); continue
        m = re.match(r"X(-?\d+)Y(-?\d+)D03\*", line)
        if m and pol == "C": clear.append((int(m[1]) / 1e6, -int(m[2]) / 1e6, ap[cur]))
    for x, y, size, name in targets:
        best = max((dia for cx, cy, dia in clear if math.hypot(cx - x, cy - y) < 0.01), default=0.0)
        need = size + 2.0
        res.append(dict(layer=ly, item=name, clear_dia=best, need=need, ok=best >= need - 1e-3))
bad = [x for x in res if not x["ok"]]
npl = len(set(r["planes"].values())); n_pad = sum(1 for t in targets if not t[3].startswith("via"))
json.dump(dict(board=board, checked=len(res), expected=len(targets) * npl, hv_tht_pads=n_pad, hv_vias=len(targets) - n_pad, plane_layers=npl, failures=len(bad), failing=bad[:20]),
          open(f"kit_v22/gerber_hv_{board}.json", "w"), indent=1)
print(f"{board}: HV plane keep-out in the Gerbers: {len(res)} pad/via x plane-layer checks, {len(bad)} below pad + 2.0 mm"); [print("  ", b) for b in bad[:6]]
