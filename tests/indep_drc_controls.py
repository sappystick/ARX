#!/usr/bin/env python3
"""Negative controls for src/pcb/indep_drc.py (Step 9): a DRC that passes everything is not evidence. Each control copies TXJ1 and breaks it in one way; the checker must
report exactly that failure, and the untouched board must pass. Writes data/results/indep_drc_controls.json (read by tests/regress.py).
usage (repo root): python3 tests/indep_drc_controls.py"""
import sys, re, json, subprocess, os, tempfile
SRC = "data/kicad/TXJ1.kicad_pcb"; OUT = "data/results/indep_drc_controls.json"
text = open(SRC).read()
def run(name, body):
    d = tempfile.mkdtemp(); p = os.path.join(d, "b.kicad_pcb"); open(p, "w").write(body)
    r = subprocess.run([sys.executable, "src/pcb/indep_drc.py", "TXJ1", p, os.path.join(d, "r.json")], capture_output=True, text=True)
    res = json.load(open(os.path.join(d, "r.json")))
    return dict(control=name, fails=res["fails"], n_fail=res["n_fail"])
CASES = []
CASES.append(("untouched TXJ1 passes", text, lambda f: f == {}))
# 1. track narrower than the 0.15 mm fab floor
CASES.append(("track 0.10 mm (below 0.15 floor) is caught", re.sub(r'\(width 3\.0\) \(layer "F\.Cu"\) \(net 1\)', '(width 0.10) (layer "F.Cu") (net 1)', text, count=1), lambda f: "width_track" in f))
# 2. an HV-net (TX_B) track 0.4 mm from the TX_A track on the same layer: needs 1.0 mm
seg = '  (segment (start 99.000 101.000) (end 105.000 101.000) (width 0.2) (layer "F.Cu") (net 2))\n'
CASES.append(("TX_B track 0.4 mm from TX_A (HV 1.0 mm) is caught", text.replace("  (gr_line", seg + "  (gr_line", 1), lambda f: "clearance" in f))
# 3. the TX_A track removed: pads of net TX_A become islands
CASES.append(("removed TX_A track splits the net is caught", re.sub(r'  \(segment \(start 97\.000 103\.000\) \(end 115\.500 103\.000\) \(width 3\.0\) \(layer "F\.Cu"\) \(net 1\)\)\n', '', text, count=1), lambda f: any(k.startswith("split:TX_A") for k in f)))
# 4. a pad 0.5 mm over the edge (edge at x = 95.0; pad centred at x = 95.4, 2.0 mm wide)
pad_out = '  (footprint "TXJ1:PTH" (layer "F.Cu") (at 95.400 100.000) (property "Reference" "E1" (at 0 -2.4) (layer "F.SilkS")) (pad "1" thru_hole circle (at 0 0) (size 2.0 2.0) (drill 1.3) (layers "*.Cu" "*.Mask") (net 2 "TX_B")))\n'
CASES.append(("pad over the board edge is caught", text.replace("  (gr_line", pad_out + "  (gr_line", 1), lambda f: "edge" in f))
rows = []; ok = True
for name, body, expect in CASES:
    r = run(name, body)
    good = (r["fails"] == {}) if name.startswith("untouched") else expect(r["fails"])
    rows.append(dict(r, caught=good)); ok &= good
json.dump(dict(all_caught=ok, cases=rows), open(OUT, "w"), indent=1)
for r in rows: print(("OK  " if r["caught"] else "MISS"), r["control"], "->", r["fails"])
print("controls:", "all behave as intended" if ok else "A CONTROL FAILED")
sys.exit(0 if ok else 1)
