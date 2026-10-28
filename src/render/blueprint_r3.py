#!/usr/bin/env python3
"""Full-system layered cut-away blueprint (r3): every cut face is computed from the CURRENT generated meshes (stl/, the low-resolution formers, the generated PB1R board model),
not from the legacy renderer (whose inputs predate Step 5). Sections are exact mesh/plane intersections (even-odd filled), so what is drawn is what the STL contains.
Panels: 1 whole detector at the 47 deg use pose (mid-plane cut), 2 head half-section, 3 head plan sections, 4 yoke/hinge, 5 neck module with PB1R, 6 upper assembly,
7 layer map, 8 board gallery (KiCad 3-D renders) and the level schematic. Boards inside the vault (AB1A/B, CB1D, LB1, HTA board) are drawn as slabs at the z of DESIGN_STATE section 3
(no board STL is placed in the vault by the generators); the SB1R-Q boards sit inside the base-plate recess. Nothing here is built or measured.
usage (repo root, after make setup + formers-low): python3 src/render/blueprint_r3.py OUT_DIR"""
import sys, os, struct, math, json, glob
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mech")); import mesh_section as _ms
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle
from matplotlib.collections import PolyCollection
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import unary_union, polygonize
from PIL import Image
OUT = sys.argv[1] if len(sys.argv) > 1 else "deliverables/blueprint"; os.makedirs(OUT, exist_ok=True)
def tris(p):
    b = open(p, "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def section(T, axis, val):
    """mesh/plane intersection -> filled polygons in the two remaining axes (even-odd): src/mech/mesh_section.py (symmetric edge interpolation)"""
    return _ms.section(T, axis, val)
MIR = [False]
flipx = lambda a: np.asarray(a) * np.array([-1.0, 1.0]) if MIR[0] else np.asarray(a)
REC = {} if os.environ.get("BLUEPRINT_RECORD") else None              # viewer_r1.py: cut faces by part tag, per axes (the drawing is unchanged)
def _rec(ax, tag, rings, fc):
    if REC is not None and tag: REC.setdefault(id(ax), []).append(dict(tag=tag, fc=fc, rings=[np.round(np.asarray(r, float), 2).tolist() for r in rings]))
def draw(ax, g, fc, ec="#222", lw=0.4, alpha=1.0, z=2, tag=None):
    if g is None or g.is_empty: return
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        if p.geom_type != "Polygon": continue
        path = [MPoly(np.asarray(p.exterior.coords), closed=True)]
        ax.add_patch(MPoly(flipx(p.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z)); _rec(ax, tag, [flipx(p.exterior.coords)] + [flipx(h.coords) for h in p.interiors], fc)
        for h in p.interiors: ax.add_patch(MPoly(flipx(h.coords), closed=True, fc="white", ec=ec, lw=lw, zorder=z + 0.1))
def rotz(T, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]); return T @ R.T
XH, ZH = 159.0, 76.0
def arm2heel(T, alpha):                                  # shaft-local (x, y, z along the shaft) -> head frame before the 178 deg heel rotation (render_system.py convention)
    ph = math.radians(90 - alpha); V = T.reshape(-1, 3); o = np.c_[XH + V[:, 0] * math.cos(ph) + V[:, 2] * math.sin(ph), V[:, 1], ZH - V[:, 0] * math.sin(ph) + V[:, 2] * math.cos(ph)]
    return o.reshape(T.shape)
def tube(ro, ri, z0, z1, n=72):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False); c, s = np.cos(t), np.sin(t); T = []
    def quad(a, b, c_, d): T.extend([[a, b, c_], [a, c_, d]])
    for i in range(n):
        j = (i + 1) % n
        O = lambda k, z: (ro * c[k], ro * s[k], z); I = lambda k, z: (ri * c[k], ri * s[k], z)
        quad(O(i, z0), O(j, z0), O(j, z1), O(i, z1)); quad(I(i, z0), I(i, z1), I(j, z1), I(j, z0)); quad(O(i, z1), O(j, z1), I(j, z1), I(i, z1)); quad(O(i, z0), I(i, z0), I(j, z0), O(j, z0))
    return np.array(T, float)
def box(x0, x1, y0, y1, z0, z1):
    X = [x0, x1]; Y = [y0, y1]; Z = [z0, z1]; V = np.array([[x, y, z] for x in X for y in Y for z in Z], float)
    F = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]; return V[np.array(F)]
COL = dict(base="#9aa5b8", former=["#e8955a", "#d66fa0", "#a56fd6", "#6f8fe0", "#4fb8c8", "#5fc9a0"], hub="#7f8aa0", cap="#c9ced8", hood="#6c7890", skirt="#b5bccb", yoke="#59627a", board="#1f7a4d", abs="#8a7a55",
           tubeG="#c9b458", tubeC="#2b2b2b", npm="#8d99ad", pb="#1f7a4d", can="#c0392b", upper="#4a6fa5", trig="#d0782a", pack="#b5523b", dock="#8c6d4f", septum="#c9a227", ribbon="#3b7ddd", brdge="#5a8f5a")
FIGDPI = 80
fig = plt.figure(figsize=(34, 23), dpi=FIGDPI, facecolor="#f4f6fa")
gs = fig.add_gridspec(4, 8, left=0.012, right=0.992, top=0.945, bottom=0.025, hspace=0.20, wspace=0.16, height_ratios=[1.0, 1.0, 1.0, 1.0])
def panel(rc, title, sub=""):
    ax = fig.add_subplot(rc); ax.set_aspect("equal"); ax.set_facecolor("white"); ax.grid(alpha=0.15, lw=0.4)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#14213d", pad=14); ax.text(0, 1.015, sub, transform=ax.transAxes, fontsize=7.5, color="#55607a", va="bottom")
    for s in ax.spines.values(): s.set_color("#99a")
    ax.tick_params(labelsize=6.5); return ax
def label(ax, text, xy, xytext, fs=7.2, color="#14213d"):
    ax.annotate(text, xy, xytext=xytext, fontsize=fs, color=color, ha="left", va="center", arrowprops=dict(arrowstyle="-", color="#556", lw=0.5), bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#aab", lw=0.4), zorder=20)
# ------------------------------------------------------------------ data
S = lambda p: tris(p)
HEEL = lambda T: rotz(T, -178.0)             # STL head frame (heel at 178 deg) -> heel on +x: the plane y = 0 is then the shaft mid-plane
head = {os.path.basename(p)[:-4]: S(p) for p in glob.glob("stl/head/*.stl") if "FERRITE" not in p and "TXJ1" not in p}
formers = {k: S(f"work/kit_v15/LOW/FORMER_L{k}_petal_coil_former.stl") for k in range(1, 7)}
off = lambda k: 3.2 + (6 - k) * 4.4                                  # assembly_z_offset (phifold_v15.py: ZRX + (6 - k) (PN + G), PN 3.9, G 0.5)
yoke = {os.path.basename(p)[:-4]: S(p) for p in glob.glob("stl/yoke/*.stl")}
npm = {n: S(f"stl/shaft_handle/{n}.stl") for n in ("NPM_N1_body_with_tunnel_v2", "NPM_N2_lid_with_fill_ports", "NPM_N3_hot_zone_dam_v2")}
pb = S("work/kit_v6/PB1R/PF233-PB1R_board_with_components.stl")
UP = {n: S(f"stl/upper/{n}.stl") for n in ("U1_TOP_HOUSING", "U2_GRIP", "U3_BOTTOM_HOUSING", "U4_TRIGGER", "U5_ARMREST_CUP", "U6_BATTERY_DOCK", "U7_BATTERY_PACK_SHELL", "U8_CORD_ANCHOR", "U8_SEPTUM_extended", "U9_CAM_COLLAR")}
rep = json.load(open("work/kit_v23/UPPER/upper_v21_report.json")); TA = rep["params"]["tube_A"]["x"]; TB = rep["params"]["tube_B"]["extended"]; ZT = rep["params"]["ZT"]
D_HINGE = TB[1] + 484.0                                              # stem x of the head hinge: tube B end + 84 mm neck module + 400 mm lower GFRP tube (= cup back to hinge 1655 - 278.8)
def stem2shaft(T):                                                   # upper-assembly stem frame (x along the shaft toward the head, z up) -> shaft-local frame of render_system.py
    V = T.reshape(-1, 3); return np.c_[-V[:, 2], -V[:, 1], D_HINGE - V[:, 0]].reshape(T.shape)
# ------------------------------------------------------------------ 2 head half-section (y = 0)
ax2 = panel(gs[0, 3:8], "2  Head half-section (y = 0): every layer, cut faces from the generated meshes", "formers = low-resolution print meshes at their assembly z; boards in the vault = slabs at the DESIGN_STATE z ranges")
MIR[0] = True; draw(ax2, section(HEEL(head["BASE_PLATE_RX_CASSETTE_v3"]), 1, 0.0), COL["base"], tag="BASE_PLATE_RX_CASSETTE_v3")
for k in range(1, 7):
    T = formers[k].copy(); T[:, :, 2] += off(k); draw(ax2, section(HEEL(T), 1, 0.0), COL["former"][k - 1], lw=0.25, tag=f"FORMER_L{k}")
for n, c in (("CORE_CYLINDER_v5_integrated", COL["hub"]), ("ROOF_PLATE_v5", COL["cap"]), ("HUB_CAP_HTA_v3_vault", COL["cap"]), ("LOTUS_HOOD_CARRIER_v3_butted", COL["hood"]), ("HEAD_SKIRT", COL["skirt"]),
             ("SEPTUM_FRAME_v5", COL["septum"]), ("ANALOG_TRAY_v5", COL["abs"]), ("SPINE_COMB_v5", COL["abs"])): draw(ax2, section(HEEL(head[n]), 1, 0.0), c, lw=0.3, tag=n)
for n in ("TXJ1_CRADLE_v1",): draw(ax2, section(HEEL(S("stl/head/TXJ1_CRADLE_v1.stl")), 1, 0.0), COL["brdge"], tag=n)
for n in ("HEEL_SADDLE_TOWER", "UMBILICAL_BRIDGE", "UMBILICAL_BRIDGE_LID"): draw(ax2, section(HEEL(yoke[n]), 1, 0.0), COL["yoke"] if n.startswith("HEEL") else COL["brdge"], tag=n)
MIR[0] = False
def slab(ax, x0, x1, z0, z1, c, a=1.0, ec="#0a3d24", tag=None):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=c, ec=ec, lw=0.4, alpha=a, zorder=4)); _rec(ax, tag, [[(x0, z0), (x1, z0), (x1, z1), (x0, z1)]], c)
slab(ax2, -114, 114, 0.8, 3.2, COL["board"], tag="SB1R-QA");                                       # SB1R-QA/QB (2 x 4-layer, D228) in the base-plate recess
slab(ax2, -40.3, -0.3, 10.1, 11.7, COL["board"], tag="AB1A"); slab(ax2, 0.3, 40.3, 10.1, 11.7, COL["board"], tag="AB1B")  # AB1A / AB1B (D40, x -/+ 20.3)
slab(ax2, -39, 39, 27.0, 28.6, COL["board"], tag="CB1D"); slab(ax2, -39, 39, 39.2, 40.0, COL["board"], tag="LB1"); slab(ax2, -46, 46, 44.5, 46.1, COL["board"], tag="HTA")   # CB1D, LB1, HTA board in the cap
ax2.set_xlim(-205, 125); ax2.set_ylim(-6, 70)
for t, xy, xt in (("SB1R-QA/QB (2 x 4-layer D228)", (-95, 2), (-203, -3)), ("L6 former + litz", (-108, 5.3), (-203, 6)), ("L1 former + litz", (-108, 27.5), (-203, 15)), ("hood carrier + MnZn tiles", (-110, 31.4), (-203, 24)),
                  ("skirt", (-118, 14), (-203, 33)), ("hub = vault wall", (-48, 25), (-203, 42)), ("L2 AB1A | AB1B", (-20, 11), (-60, -3)), ("L3 septum + Cu mesh", (-30, 21), (-20, 62)),
                  ("L4 absorber", (30, 24), (20, 66)), ("L5 CB1D", (30, 27.8), (55, 62)), ("L6 LB1 + 66 LEDs", (-30, 39.6), (62, 66)), ("cap + HTA board", (0, 45.8), (88, 62)),
                  ("umbilical bridge + TXJ1", (-95, 37.3), (-203, 51)), ("heel saddle + tower", (-150, 55), (-203, 60))): label(ax2, t, xy, xt)
ax2.set_xlabel("x (mm), heel (178 deg) to the left", fontsize=7); ax2.set_ylabel("z (mm)", fontsize=7)
# ------------------------------------------------------------------ 3 head plan sections
for i, (zv, ttl) in enumerate(((5.2, "z = 5.2: L6 former (litz petals)"), (24.0, "z = 24: absorber cell, hub ribs"), (36.0, "z = 36: CB1D slot, TX-lead channel, exit window"))):
    ax = panel(gs[1, 3 + i], f"3{'abc'[i]}  Plan section {ttl}")
    draw(ax, section(head["HEAD_SKIRT"], 2, zv), COL["skirt"], lw=0.3)
    for k in range(1, 7):
        T = formers[k].copy(); T[:, :, 2] += off(k)
        if T[:, :, 2].min() - 0.1 < zv < T[:, :, 2].max() + 0.1: draw(ax, section(T, 2, zv), COL["former"][k - 1], lw=0.2)
    for n in ("CORE_CYLINDER_v5_integrated", "SEPTUM_FRAME_v5", "ANALOG_TRAY_v5", "LOTUS_HOOD_CARRIER_v3_butted"):
        draw(ax, section(head[n], 2, zv), COL["hub"], lw=0.25)
    for n in ("HEEL_SADDLE_TOWER", "UMBILICAL_BRIDGE"):
        draw(ax, section(yoke[n], 2, zv), COL["yoke"])
    draw(ax, section(S("stl/head/TXJ1_CRADLE_v1.stl"), 2, zv), COL["brdge"])
    ax.set_xlim(-190, 125); ax.set_ylim(-125, 125); ax.set_xlabel("x (mm)", fontsize=7)
# ------------------------------------------------------------------ 5 neck module with PB1R (section through the can row, x = -7.2 on the board = NPM x)
ax5 = panel(gs[1, 6:8], "5  Neck power module section x = -7: PB1R with the 9 hybrid cans", "PB1R stands in the pocket, components toward the back wall (mech_v20.py); the cans are 10.3 mm tall: pocket clearance below")
for n, c in (("NPM_N1_body_with_tunnel_v2", COL["npm"]), ("NPM_N2_lid_with_fill_ports", "#b9c2d2"), ("NPM_N3_hot_zone_dam_v2", "#e08a2b")): draw(ax5, section(npm[n], 0, -7.0), c)
P2 = pb.copy(); P2 = np.stack([P2[:, :, 0], 34.6 - (P2[:, :, 2] + 1.6), P2[:, :, 1] + 42.0], axis=2)      # board model -> NPM frame (as render_detail.py)
for xv in (-7.0, -7.2, 6.1):
    g = section(P2, 0, xv); draw(ax5, g, COL["pb"] if xv == -7.0 else COL["can"], lw=0.25, alpha=0.9 if xv == -7.0 else 0.5)
ax5.set_xlim(-25, 50); ax5.set_ylim(-25, 110); ax5.set_xlabel("y (mm)", fontsize=7); ax5.set_ylabel("z (mm)", fontsize=7)
label(ax5, "ribbon tunnel (straight through)", (8, 40), (-22, 100)); label(ax5, "PB1R board + hybrid cans (red)", (30, 42), (8, 104)); label(ax5, "hot zone dam (alumina fill / syntactic silicone)", (24, 60), (-22, 95))
# ------------------------------------------------------------------ 6 upper assembly extended (y = 0 section) + 7 layer map
ax6 = panel(gs[2, 5:8], "6  Upper assembly v1, extended (mid-plane cut)", "stem frame: grip at x = 0, tubes toward +x (the head); battery on T rails below")
cm = {"U1_TOP_HOUSING": COL["upper"], "U2_GRIP": "#7d8fa8", "U3_BOTTOM_HOUSING": COL["upper"], "U4_TRIGGER": COL["trig"], "U5_ARMREST_CUP": "#5a8f5a", "U6_BATTERY_DOCK": COL["dock"], "U7_BATTERY_PACK_SHELL": COL["pack"],
      "U8_CORD_ANCHOR": COL["septum"], "U8_SEPTUM_extended": COL["septum"], "U9_CAM_COLLAR": "#666"}
for n, T in UP.items(): draw(ax6, section(T, 1, 0.0), cm[n], lw=0.3)
for x0, x1, ro, ri, c in ((TA[0], TA[1], 16.5, 15.0, COL["tubeC"]), (TB[0], TB[1], 14.25, 13.0, "#555")):
    ax6.add_patch(Rectangle((x0, ZT - ro), x1 - x0, 2 * ro, fc="none", ec=c, lw=1.0, zorder=3)); ax6.add_patch(Rectangle((x0, ZT - ri), x1 - x0, 2 * ri, fc="#e8eaf0", ec=c, lw=0.4, zorder=3))
ax6.set_xlim(-290, 900); ax6.set_ylim(-150, 130); ax6.set_xlabel("x (mm), toward the head hinge", fontsize=7)
for t, xy, xt in (("top housing U1 + HB2 + dial", (40, 100), (-260, 120)), ("grip U2 + trigger U4", (20, 20), (-260, 70)), ("forearm cup U5 (3 positions)", (-240, 0), (-285, 30)), ("bottom housing U3 + PM2", (-100, -76), (-285, -110)),
                  ("T-rail dock U6, MT60 pair", (-60, -113), (-120, -140)), ("battery pack U7: 7S1P P30B, BMS bay", (-100, -118), (100, -140)), ("tube A (CFRP OD33/ID30) + twin-cavity septum", (300, 80), (200, 118)),
                  ("tube B (CFRP OD28.5/ID26)", (700, 80), (560, 118)), ("cam collar U9", (512, 85), (400, 128))): label(ax6, t, xy, xt, fs=6.6)
# ------------------------------------------------------------------ 1 whole detector, 47 deg use pose, mid-plane cut
ax1 = panel(gs[0:3, 0:3], "1  Whole detector, extended, shaft at 47 deg: mid-plane cut of the current head, yoke, tubes, neck module and upper assembly v1", "every cut face is computed from stl/ and the generated PB1R model; tube/neck parts from the same transforms as render_system.py; head is at the left (heel rotated 178 deg)")
sys_pts0 = lambda T: arm2heel(T, 47.0) * np.array([-1.0, 1.0, 1.0])
def draw_system(ax1, ALPHA=47.0):
    MIR[0] = True
    def sys_pts(T): return arm2heel(T, ALPHA)
    def shaft_section(T_local, c, lw=0.3, tag=None):
        T = sys_pts(T_local); draw(ax1, section(T, 1, 0.0), c, lw=lw, tag=tag)
    def envelope(ro, z0, z1, c, a=0.30):                     # the tube is a 1.5 mm wall: at this scale draw its outer envelope as a light band and the wall on top
        q = sys_pts(np.array([[-ro, 0, z0], [ro, 0, z0], [ro, 0, z1], [-ro, 0, z1]], float))[:, [0, 2]]
        ax1.add_patch(MPoly(flipx(q), closed=True, fc=c, ec=c, lw=0.8, alpha=a, zorder=1.5))
    for n, c in (("BASE_PLATE_RX_CASSETTE_v3", COL["base"]), ("CORE_CYLINDER_v5_integrated", COL["hub"]), ("ROOF_PLATE_v5", COL["cap"]), ("HUB_CAP_HTA_v3_vault", COL["cap"]), ("LOTUS_HOOD_CARRIER_v3_butted", COL["hood"]), ("HEAD_SKIRT", COL["skirt"])):
        draw(ax1, section(HEEL(head[n]), 1, 0.0), c, lw=0.2, tag=n)
    for k in range(1, 7):
        T = formers[k].copy(); T[:, :, 2] += off(k); draw(ax1, section(HEEL(T), 1, 0.0), COL["former"][k - 1], lw=0.15, tag=f"FORMER_L{k}")
    for n in ("HEEL_SADDLE_TOWER", "UMBILICAL_BRIDGE", "UMBILICAL_BRIDGE_LID"): draw(ax1, section(HEEL(yoke[n]), 1, 0.0), COL["yoke"] if n.startswith("HEEL") else COL["brdge"], lw=0.2, tag=n)
    shaft_section(yoke["HINGE_ARM"], COL["yoke"], tag="HINGE_ARM"); envelope(16.0, 14.0, 400.0, COL["tubeG"]); shaft_section(tube(16.0, 14.5, 14.0, 400.0), COL["tubeG"], 0.8, tag="TUBE_LOWER_GFRP")
    for n, c in (("NPM_N1_body_with_tunnel_v2", COL["npm"]), ("NPM_N3_hot_zone_dam_v2", "#e08a2b")):
        T = npm[n].copy(); T[:, :, 2] += 400.0; shaft_section(T, c, tag=n)
    Tpb = np.stack([pb[:, :, 0], 34.6 - (pb[:, :, 2] + 1.6), pb[:, :, 1] + 42.0 + 400.0], axis=2); shaft_section(Tpb, COL["pb"], 0.15, tag="PB1R")
    zB0, zB1, zA0, zA1 = D_HINGE - TB[1], D_HINGE - TB[0], D_HINGE - TA[1], D_HINGE - TA[0]
    envelope(14.25, zB0, zB1, "#555"); shaft_section(tube(14.25, 13.0, zB0, zB1), "#333", 0.8, tag="TUBE_B_CFRP"); envelope(16.5, zA0, zA1, COL["tubeC"], 0.22); shaft_section(tube(16.5, 15.0, zA0, zA1), COL["tubeC"], 0.8, tag="TUBE_A_CFRP")
    shaft_section(yoke["TELESCOPE_LOCK_COLLAR"].copy() + np.array([0, 0, zA0 + 1]), "#e0822f", tag="TELESCOPE_LOCK_COLLAR")
    for n, T in UP.items(): shaft_section(stem2shaft(T), cm[n], 0.25, tag=n)
    MIR[0] = False
draw_system(ax1)
ax1.set_xlim(-1700, 330); ax1.set_ylim(-80, 1450)
for t, xy, xt in (("head (see 2, 3)", (0, 30), (80, 140)), ("yoke saddle + hinge, 10 deg serrations", tuple(sys_pts0(np.array([[0.0, 0.0, 30.0]]))[0][[0, 2]]), (150, 330)),
                  ("lower GFRP tube 0.40 m + TX pair + ribbons", tuple(sys_pts0(np.array([[0.0, 0.0, 200.0]]))[0][[0, 2]]), (150, 470)), ("neck module + PB1R (5)", tuple(sys_pts0(np.array([[0.0, 0.0, 442.0]]))[0][[0, 2]]), (150, 600)),
                  ("tube B / A telescoping, twin cavity (6)", tuple(sys_pts0(np.array([[0.0, 0.0, 900.0]]))[0][[0, 2]]), (-80, 880)), ("grip, trigger, top housing (HB2), bottom housing (PM2)", tuple(sys_pts0(stem2shaft(np.array([[0.0, 0.0, 0.0]])))[0][[0, 2]]), (-1240, 960)),
                  ("battery pack on T rails (7S1P)", tuple(sys_pts0(stem2shaft(np.array([[-80.0, 0.0, -115.0]])))[0][[0, 2]]), (-1240, 760)), ("forearm cup U5", tuple(sys_pts0(stem2shaft(np.array([[-240.0, 0.0, 0.0]])))[0][[0, 2]]), (-1240, 860))): label(ax1, t, xy, xt, fs=8)
ax1.set_xlabel("x (mm)", fontsize=7); ax1.set_ylabel("z (mm)", fontsize=7)

ax4 = panel(gs[2, 3:5], "4  Yoke saddle, hinge, lower tube and neck module at 47 deg (zoom of 1)", "same transforms as 1; cut at the mid-plane")
draw_system(ax4); ax4.set_xlim(-520, 230); ax4.set_ylim(-20, 620)
# ------------------------------------------------------------------ 7 layer map
ax7 = panel(gs[3, 3:5], "7  Head layer map (z, from the meshes and DESIGN_STATE section 3)")
rows = [("L0 base plate + SB1R-Q", 0, 3.2, COL["base"]), ("L1 gallery (RX leads, spine flex)", 3.2, 9.0, "#bbb"), ("L2 analog cell AB1A/AB1B", 9.8, 20.0, COL["board"]), ("L3 septum + Cu cloth", 20.0, 21.9, COL["septum"]), ("L4 absorber cell", 21.9, 27.0, COL["abs"]),
        ("L5 CB1D controller", 27.0, 38.8, COL["board"]), ("L6 LB1 display", 39.2, 40.8, COL["board"]), ("L7 roof plate", 41.3, 44.5, COL["cap"]), ("L8 cap + HTA antenna", 44.5, 47.1, COL["cap"])] + [(f"former L{k} (petals, litz)", off(k), off(k) + 3.9, COL["former"][k - 1]) for k in range(6, 0, -1)] + [("hood carrier + MnZn tiles", 29.4, 33.4, COL["hood"]), ("skirt", 0, 33.4, COL["skirt"])]
for i, (n, z0, z1, c) in enumerate(rows): ax7.barh(i, z1 - z0, left=z0, color=c, ec="#333", lw=0.4); ax7.text(z1 + 0.6, i, f"{n}  ({z0:.1f}-{z1:.1f})", va="center", fontsize=6.8)
ax7.set_yticks([]); ax7.set_xlim(0, 85); ax7.set_ylim(len(rows) - 0.3, -0.8); ax7.set_aspect("auto"); ax7.set_xlabel("z (mm)", fontsize=7)
# ------------------------------------------------------------------ 8 boards gallery + level schematic image
ax8 = fig.add_subplot(gs[3, 5:7]); ax8.axis("off"); ax8.set_title("8  Boards (KiCad 3-D render of the routed files, top side)", loc="left", fontsize=12, fontweight="bold", color="#14213d", pad=14)
imgs = sorted(glob.glob(os.path.join(OUT, "..", "renders", "boards", "*_top.png")))
if imgs:
    n = len(imgs); cols = 5; rws = math.ceil(n / cols)
    for i, p in enumerate(imgs):
        im = Image.open(p).convert("RGB"); w = 1.0 / cols; h = 1.0 / rws; x0 = (i % cols) * w; y0 = 1 - (i // cols + 1) * h
        sub = ax8.inset_axes([x0, y0 + 0.07 * h, w * 0.96, h * 0.82]); sub.imshow(im); sub.axis("off"); sub.set_title(os.path.basename(p).replace("_top.png", ""), fontsize=7)
ax9 = fig.add_subplot(gs[3, 7:8]); ax9.axis("off"); ax9.set_title("9  Level-by-level electrical schematic (LEVELS_SCHEMATIC.png)", loc="left", fontsize=12, fontweight="bold", color="#14213d", pad=14)
ax9.imshow(Image.open("docs/figures/LEVELS_SCHEMATIC.png").convert("RGB"))

axl = fig.add_subplot(gs[3, 0:3]); axl.axis("off")
axl.text(0, 1, "How to read this sheet\n\n"
 "- Panels 1-6 are exact mid-plane / plan cuts of the CURRENT generated meshes (stl/, work/kit_v15/LOW formers, the generated PB1R model).\n"
 "- Colours: formers L1-L6 orange to green, hub / hood grey-blue, boards green, GFRP tube gold, CFRP tubes black, housing blue, trigger orange, pack red, dock brown.\n"
 "- Boards inside the vault are slabs at the DESIGN_STATE z ranges (the generators place no board STL there); SB1R-Q sits in the base-plate recess.\n"
 "- Formers are the LOW-resolution meshes (print meshes: make formers-print, about 70 MB each).\n"
 "- 47 deg is the use pose; the shaft tubes, neck module and upper assembly use the transforms of render_system.py.\n"
 "- Panel 8 is KiCad's own 3-D render of the routed board files (copper, mask, pads; no component 3-D models exist).\n\n"
 "Status: MODELED design drawing, not a fabrication drawing. See 00_INDEX.md for what is verified, what is open and what must happen before anything is sent to print or to a PCB house.",
 va="top", ha="left", fontsize=10.5, color="#14213d", wrap=True, family="DejaVu Sans")
fig.suptitle("PHI-FOLD 233  -  full structure and layered cut-away blueprint (r3): current meshes, boards and parts", fontsize=19, fontweight="bold", color="#14213d", x=0.015, ha="left", y=0.985)
fig.text(0.015, 0.006, "MODELED design drawing: sections computed from the generated STLs; board slabs at the DESIGN_STATE z ranges; nothing here is built or measured. Not a fabrication drawing: see 00_INDEX.md for the status of every file.", fontsize=9, color="#55607a")
for ext, kw in (("png", dict(dpi=FIGDPI)), ("pdf", {})): fig.savefig(os.path.join(OUT, f"PHIFOLD233_FULL_SYSTEM_LAYERED_CUTAWAY_r3.{ext}"), **kw)
print("blueprint written to", OUT)
if REC is not None:                                                    # viewer_r1.py input: the tagged cut faces of panel 1 (whole detector) and panel 2 (head half-section), drawing coordinates in mm
    json.dump(dict(system=dict(faces=REC.get(id(ax1), []), xlim=list(ax1.get_xlim()), ylim=list(ax1.get_ylim())), head=dict(faces=REC.get(id(ax2), []), xlim=list(ax2.get_xlim()), ylim=list(ax2.get_ylim()))),
              open(os.environ["BLUEPRINT_RECORD"], "w"))
