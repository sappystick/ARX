#!/usr/bin/env python3
"""One figure for the upper assembly v1 decision: side views (extended, collapsed), the rail-fit section, the twin-cavity section and the pack
section, with the measured numbers from upper_check.json and power_dock_check.json (all modeled / measured on meshes, nothing built)."""
import json, struct, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
D = "kit_v23/UPPER"; R = json.load(open(f"{D}/upper_v21_report.json")); C = json.load(open("kit_v23/upper_check.json")); P = json.load(open("kit_v23/power_dock_check.json"))
def tris(n):
    b = open(f"{D}/{n}.stl", "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def section(Tr, axis, val):
    keep = [i for i in range(3) if i != axis]; d = Tr[:, :, axis] - (val + 1.234e-4); m = (d.min(1) < 0) & (d.max(1) > 0); S = []
    for tri, dd in zip(Tr[m], d[m]):
        q = [tri[i] + dd[i] / (dd[i] - dd[j]) * (tri[j] - tri[i]) for i, j in ((0, 1), (1, 2), (2, 0)) if (dd[i] < 0) != (dd[j] < 0)]
        if len(q) == 2: S.append([q[0][keep], q[1][keep]])
    return np.array(S).reshape(-1, 2, 2)
COL = {"U1": "#4a6fa5", "U2": "#7d8fa8", "U3": "#4a6fa5", "U4": "#d0782a", "U5": "#5a8f5a", "ARMREST": "#333333", "U6": "#8c6d4f", "U7": "#b5523b", "TUBE": "#222222", "U8": "#c9a227", "U9": "#666666"}
def col(n): return next(v for k, v in COL.items() if n.startswith(k))
common = ["U1_TOP_HOUSING", "U2_GRIP", "U3_BOTTOM_HOUSING", "U4_TRIGGER", "U5_ARMREST_CUP", "ARMREST_TUBE_CFRP_pos1", "U6_BATTERY_DOCK", "U7_BATTERY_PACK_SHELL", "TUBE_A_CFRP", "U8_CORD_ANCHOR", "U9_CAM_COLLAR"]
fig = plt.figure(figsize=(17, 11)); gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 1.15])
for row, cfg in enumerate(("extended", "collapsed")):
    ax = fig.add_subplot(gs[row, :])
    for n in common + [f"TUBE_B_CFRP_{cfg}", f"U8_SEPTUM_{cfg}"]:
        T = tris(n); ax.add_collection(PolyCollection(T[:, :, [0, 2]], facecolor=col(n), edgecolor="none", alpha=0.28))
    ax.set_aspect(1); ax.autoscale(); ax.grid(alpha=0.25); ax.set_ylabel("z (mm, stem frame)")
    L = C["lengths_mm"]; ax.set_title(f"{cfg}: upper assembly {L['upper_assembly_' + cfg + '_mm']} mm, cup back to head hinge {L['cup_back_to_hinge_' + cfg + '_mm']} mm "
                                      f"(neck module 84 + GFRP 400 mm not drawn)", fontsize=10)
    if row == 0:
        for txt, xy in (("top housing U1 (HB2, dial, power button)", (-30, 118)), ("trigger U4 (index finger)", (60, 20)), ("grip U2", (-60, 0)), ("bottom housing U3 (PM2)", (-160, -45)),
                        ("forearm cup U5 (3 positions)", (-330, 25)), ("battery pack U7 on T rails, MT60 at the front", (-170, -150)), ("tube A / B, twin cavity U8", (300, 110))):
            ax.annotate(txt, xy, fontsize=8)
b = C["balance"]; m = C["mass"]
ax = fig.add_subplot(gs[2, 0]); zpt = R["params"]["dock"]["z_pack_top"]
for n, c in (("U6_BATTERY_DOCK", "#8c6d4f"), ("U7_BATTERY_PACK_SHELL", "#b5523b"), ("U3_BOTTOM_HOUSING", "#4a6fa5")):
    for s in section(tris(n), 0, -80.0): ax.plot(s[:, 0], s[:, 1], color=c, lw=0.8)
for q in R["envelopes"]["cells"]["centres"][3:4]:
    ax.add_patch(plt.Rectangle((-32.65, q["z"] - 9.3), 65.3, 18.6, fc="none", ec="k", ls="--", lw=0.6))
ax.set_aspect(1); ax.set_xlim(-45, 45); ax.set_ylim(zpt - 36, zpt + 30); ax.set_title(f"section x = -80: T rails (clearance {next(c['value'] for c in C['checks'] if c['check'].startswith('rail fit'))} mm, "
                                                                                      f"undercut {next(c['value'] for c in C['checks'] if c['check'].startswith('rail undercut'))} mm), cell, BMS bay", fontsize=8)
ax = fig.add_subplot(gs[2, 1]); zt = R["params"]["ZT"]; tb = R["params"]["tube_B"]["extended"][0]
for n, c, x in (("TUBE_A_CFRP", "#222", 470.0), ("TUBE_B_CFRP_extended", "#555", 470.0), ("U8_SEPTUM_extended", "#c9a227", tb + 2.0 + 4.0)):
    for s in section(tris(n), 0, x): ax.plot(s[:, 0], s[:, 1] - zt, color=c, lw=0.8)
for sy in (-1, 1): ax.add_patch(plt.Circle((sy * R["params"]["bore_y"], 0), R["params"]["cord_od"] / 2, fc="none", ec="r", ls="--", lw=0.8))
ax.set_aspect(1); ax.set_xlim(-19, 19); ax.set_ylim(-19, 19); ax.set_title("twin cavity at a spacer: power cord | signal cord (red = 10.4 mm coiled-cord envelope);\nseptum carries the slit Cu-mesh shield, drained at PM2", fontsize=8)
ax = fig.add_subplot(gs[2, 2]); ax.axis("off")
txt = [f"mass upper assembly incl. pack {m['upper_total_kg']} kg (pack {m['battery_pack_kg']} kg), modeled",
       f"torque about the grip at 47 deg, same head reach as v20: {b['new_47deg_working']} kg m (v20 {b['baseline_v20_kg_m']})",
       f"  40 deg {b['new_40deg']} / 55 deg {b['new_55deg']} kg m; pack moved back under the cup: {b['option_pack_moved_back_under_the_cup']} kg m",
       f"telescoping stroke {next(c['value'] for c in C['checks'] if c['check'].startswith('telescoping stroke'))} mm, overlap >= 80 mm",
       f"trigger: pad 3.5 mm in front of the grip, travel 3 mm, magnet moves {next(c['value'] for c in C['checks'] if c['check'].startswith('magnet travel'))} mm (active-low lever)",
       f"PM2: on only with the pack seated AND the switch closed; soft start {P['soft_start']['ramp_ms']} ms, inrush {P['soft_start']['inrush_A']} A",
       f"pack 7S1P P30B {P['runtime']['pack_Wh']} Wh: boost {P['runtime']['boost_h_one_pack']} h, scan {P['runtime']['scan_h_one_pack']} h per pack",
       f"checks: upper {sum(c['result'] == 'PASS' for c in C['checks'])}/{len(C['checks'])}, power dock {sum(c['result'] == 'PASS' for c in P['checks'])}/{len(P['checks'])}",
       "D044-A dimensions scaled from photos (ASSUMPTIONS 24); nothing built or measured"]
ax.text(0, 1, "\n".join(txt), va="top", fontsize=9, family="monospace")
fig.suptitle("PHI-FOLD 233 upper assembly v1 (D044-A-style S-stem): modeled, measured on the generated meshes", fontsize=12); fig.tight_layout()
fig.savefig("kit_v23/UPPER_ASSEMBLY_v1.png", dpi=80); print("kit_v23/UPPER_ASSEMBLY_v1.png")
