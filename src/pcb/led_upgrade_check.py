#!/usr/bin/env python3
"""Feasibility of the clocked-LED change on LB1 (owner request 2026-10-28: clocked LEDs fed in the idle time, no dropped pulses). MODELED / measured on the
current LB1 placement; no board is changed by this script. Datasheet facts (data/seed/datasheets, DATASHEET_LOG):
  SK9822 (OPSCO Rev.01): body 5.0 x 5.0 x 1.6 mm (drawing; the text table says 5.5 x 5.0), recommended PCB pads 1.5 x 1.0 mm, three per side on 1.6 mm
    pitch, inner pad edges 3.4 mm apart (footprint 6.4 mm wide); pins 1 SDI, 2 CKI, 3 GND, 4 VCC, 5 CKO, 6 SDO; IDD static 1 mA; Imax 20 mA per channel; PWM 1.2 kHz
  SK6812MINI-E (current LB1 part, Rev.02): 3.2 x 2.8 x 1.78 mm REVERSE-mount: the body drops through a 3.2 x 2.8 cutout, leads 0.84 mm below the top;
    pads 1.8 mm long OUTSIDE the cutout. LB1 (pw_design.py LED2020) has 1.0 x 0.7 pads at +-1.45 / +-0.85 inside that outline and no cutout.
Checks: (1) SK9822 pads at every current LD position with the pad columns along the radius (each LED rotated to its azimuth): min pad-to-pad gap between
neighbours >= 0.16 mm floor (also "as placed": the pickplace rotations; the pad pattern is symmetric under 180 deg, so the y-UP sign does not matter) and the routing room between them; (2) height: LB1 top z 40.0 (39.2 + 0.8) + 1.6 vs roof underside z 41.3 with the 0.3 mm stack rule
-> pocket depth in the roof underside; (3) rail: static 66 x 1 mA added to +5V.
usage (repo root): python3 src/pcb/led_upgrade_check.py [OUT.json]"""
import csv, math, json, sys, itertools
from shapely.geometry import box
from shapely import affinity
from shapely.ops import unary_union
LB1_TOP, ROOF, RULE = 39.2 + 0.8, 41.3, 0.3
rows = [r for r in csv.DictReader(open("data/results/PF233-LB1_pickplace.csv")) if r["Ref"].startswith("LD")]
P = [(r["Ref"], float(r["PosX_mm"]), float(r["PosY_mm"])) for r in rows]; ROT = {r["Ref"]: float(r["Rot"]) for r in rows}   # LB1-v6: chain rotations (lb1_export.chain_rots)
PARTS = {"SK9822 5050": dict(cx=1.7 + 0.75, pw=1.5, ph=1.0, pitch=1.6, half=2.5, h=1.6), "SK9822-EC20": dict(cx=0.68, pw=0.76, ph=0.46, pitch=0.86, half=1.0, h=0.65)}
def pads(x, y, rot, q):
    out = []
    for side in (-1, 1):
        cx = side * q["cx"]
        for k in (-1, 0, 1): out.append(affinity.rotate(affinity.translate(box(cx - q["pw"] / 2, k * q["pitch"] - q["ph"] / 2, cx + q["pw"] / 2, k * q["pitch"] + q["ph"] / 2), x, y), rot, origin=(x, y)))
    return out
def body(x, y, rot, q): return affinity.rotate(box(x - q["half"], y - q["half"], x + q["half"], y + q["half"]), rot, origin=(x, y))
res = {}
for (part, q), (orient, rotf) in itertools.product(PARTS.items(), (("pad columns radial", lambda n, x, y: math.degrees(math.atan2(y, x))), ("as placed", lambda n, x, y: ROT[n]))):
    orient = f"{part}, {orient}"
    G = [(n, unary_union(pads(x, y, rotf(n, x, y), q)), body(x, y, rotf(n, x, y), q)) for n, x, y in P]
    pg = min((a[1].distance(b[1]), a[0], b[0]) for a, b in itertools.combinations(G, 2))
    bg = min((a[2].distance(b[2]), a[0], b[0]) for a, b in itertools.combinations(G, 2))
    res[orient] = dict(min_pad_gap_mm=round(pg[0], 3), pair=[pg[1], pg[2]], min_body_gap_mm=round(bg[0], 3), body_pair=[bg[1], bg[2]],
                       one_track_between=pg[0] >= 0.15 + 2 * 0.16, ok=pg[0] >= 0.16 and bg[0] >= 0.2)
best = max(res, key=lambda k: res[k]["min_pad_gap_mm"])
height = {p: dict(led_top_z=round(LB1_TOP + q["h"], 2), roof_underside_z=ROOF, gap_mm=round(ROOF - LB1_TOP - q["h"], 2), rule_mm=RULE, roof_pocket_depth_mm=round(max(0.0, LB1_TOP + q["h"] + RULE - ROOF), 2)) for p, q in PARTS.items()}
chosen = "SK9822-EC20"
out = dict(status="MODELED feasibility on the current LB1 positions; LB1-v6 uses SK9822-EC20", fit=res, best_orientation=best, height=height, chosen=chosen,
           chosen_ok=res[f"{chosen}, as placed"]["ok"] and height[chosen]["gap_mm"] >= RULE,
           rail=dict(static_A=round(66 * 0.001, 3), note="66 x 1 mA static (SK9822 IDD); LED current itself stays under the firmware cap 0.35 A"),
           mini_e_finding=dict(part_height_mm=1.78, reverse_mount=True, lb1_pads_inside_body_outline=True, lb1_cutout=False,
                               consequence="the current LB1 footprint cannot take the SK6812MINI-E: either the LED or the footprint has to change regardless of the clocked upgrade"))
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "data/results/led_upgrade_check.json", "w"), indent=1); print(json.dumps(out, indent=1))
