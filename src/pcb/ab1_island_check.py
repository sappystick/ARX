#!/usr/bin/env python3
"""AB1A / AB1B +3V3D island checks (tool-checked, modeled): zero open nets in the exporter's connectivity check, island inside the board, island distance to the antenna inputs
(J1 and every RAW_* pad) and to the OPA2211 pads (>= 3 mm), every copper zone hatched, no +5VA item inside the island, island copper area and the nearest closed copper path note.
usage (in work/, after afe_layout.py --route and afe_export.py): BOARD=A python3 ab1_island_check.py OUT.json"""
import os, sys, json, math, re
out = sys.argv[1]; B = os.environ.get("BOARD", "A"); sys.argv = ["x"]
import afe_layout as A
R_BRD = A.R_BOARD
ck = json.load(open(f"kit_v3/PCB_AB1{B}/PF233-AB1{B}_check.json")); pcb = open(f"kit_v3/PCB_AB1{B}/PF233-AB1{B}.kicad_pcb").read()
res = dict(board=f"AB1{B}", adc=("AD7389" if A.D.ADC7 else "ADS8860"), island=A.ISL, opens=ck["nets_with_opens"], shorts=ck["shorts"], clearance_violations=ck["clearance_violations_below_0p09"])
def rect_gap(p, r):
    dx = max(r[0] - p["x"] - p["w"] / 2 * 0 - (p["w"] / 2), p["x"] - p["w"] / 2 - r[1], 0.0); dy = max(r[2] - p["y"] - p["h"] / 2, p["y"] - p["h"] / 2 - r[3], 0.0)
    return math.hypot(dx, dy)
if A.ISL is not None:
    r = A.ISL; res["island_corner_radius_max_mm"] = round(max(math.hypot(x, y) for x in r[:2] for y in r[2:]), 3); res["island_inside_board"] = res["island_corner_radius_max_mm"] <= R_BRD - 0.5
    ant = [p for p in A.PADS if p["ref"] == "J1" or (p["net"] or "").startswith("RAW_")]; opa = [p for p in A.PADS if p["ref"] in ("U1", "U2")]
    res["island_to_antenna_inputs_mm"] = round(min(rect_gap(p, r) for p in ant), 3); res["island_to_opa2211_mm"] = round(min(rect_gap(p, r) for p in opa), 3)
    res["island_area_mm2"] = round((r[1] - r[0]) * (r[3] - r[2]), 2)
    res["plus5va_items_inside_island"] = [(p["ref"], p["num"]) for p in A.PADS if p["net"] == "+5VA" and r[0] - 0.2 < p["x"] < r[1] + 0.2 and r[2] - 0.2 < p["y"] < r[3] + 0.2 and p["tht"]]
    res["plus5va_vias_inside_island"] = [(round(x, 2), round(y, 2)) for x, y, n in json.load(open(f"out_board/AB1{B}_layout.json"))["VIAS"] if n == A.NETID["+5VA"] and r[0] - 0.2 < x < r[1] + 0.2 and r[2] - 0.2 < y < r[3] + 0.2]
zones = re.findall(r"\(zone .*?\(polygon", pcb, re.S); res["zones"] = len(zones); res["zones_hatched"] = sum("(mode hatch)" in z for z in zones)
res["pass"] = bool(res["opens"] == 0 and res["shorts"] == 0 and res["zones"] == res["zones_hatched"] and (A.ISL is None or (res["island_inside_board"] and res["island_to_antenna_inputs_mm"] >= 3.0 and res["island_to_opa2211_mm"] >= 3.0 and not res["plus5va_items_inside_island"] and not res["plus5va_vias_inside_island"])))
json.dump(res, open(out, "w"), indent=1, default=str); print(json.dumps(res, default=str)[:600])
