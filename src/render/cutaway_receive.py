#!/usr/bin/env python3
"""Receive-stage cut-away and AB1A (AD7389-4 build, +3V3D island on In4) figure; updated 2026-10-27, the earlier version showed the ADS8860 build and its 3 open nets.
Panels: 1 vault half-section (y = 0) from the CURRENT meshes with the level z-ranges of DESIGN_STATE section 3 and the measured gaps; 2 plan section at the AB1 level
(core wall, board discs); 3 AB1A routed layout (pads, tracks per layer, vias, the open nets as air-wires); 4-6 the three open pads with the free gap measured in 8 directions
against the foreign copper (needed: track passage 0.47 mm = 0.15 + 2 x 0.16; via passage 0.83 mm); 7 the blocker table. Everything is MODELED / tool-measured; nothing is built.
usage (repo root, after make setup, with the AB1A layout written by afe_layout.py --route in work/):
  cd work && BOARD=A python3 afe_layout.py --route && cd .. && python3 src/render/cutaway_receive.py OUT_DIR"""
import sys, os, json, math, struct
import numpy as np
os.environ.setdefault("BOARD", "A")
ROOT = os.getcwd(); OUT = sys.argv[1] if len(sys.argv) > 1 else "deliverables/receive_cutaway"; os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "work")); os.chdir(os.path.join(ROOT, "work"))
import afe_layout as A
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle, Circle, FancyBboxPatch
from shapely.geometry import LineString, Polygon, Point, box as sbox
from shapely.ops import unary_union, polygonize
from shapely import affinity

def tris(p):
    b = open(p, "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def section(T, axis, val):                                             # src/mech/mesh_section.py (symmetric edge interpolation)
    import mesh_section as _ms; return _ms.section(T, axis, val)
def rotz(T, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]); return T @ R.T
HEEL = lambda T: rotz(T, -178.0)
def poly_patches(ax, g, fc, ec="#222", lw=0.4, alpha=1.0, z=2, flip=False):
    if g is None or g.is_empty: return
    f = (lambda c: np.asarray(c) * np.array([-1.0, 1.0])) if flip else (lambda c: np.asarray(c))
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        if p.geom_type != "Polygon": continue
        ax.add_patch(MPoly(f(p.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z))
        for h in p.interiors: ax.add_patch(MPoly(f(h.coords), closed=True, fc="white", ec=ec, lw=lw, zorder=z + 0.1))
def dim(ax, p, q, text, off=(0, 0), fs=7, color="#b00020", lw=0.7, ha="center"):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="<->", color=color, lw=lw, shrinkA=0, shrinkB=0), zorder=30)
    ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], text, fontsize=fs, color=color, ha=ha, va="center", zorder=31,
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec=color, lw=0.4, alpha=0.95))
def lab(ax, text, xy, xt, fs=7, color="#14213d", ha="left"):
    ax.annotate(text, xy, xytext=xt, fontsize=fs, color=color, ha=ha, va="center", arrowprops=dict(arrowstyle="-", color="#556", lw=0.5),
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#aab", lw=0.4), zorder=40)

# ------------------------------------------------------------------ data
head = {os.path.basename(p)[:-4]: tris(p) for p in (os.path.join(ROOT, "stl/head", n + ".stl") for n in
        ("CORE_CYLINDER_v5_integrated", "ROOF_PLATE_v5", "HUB_CAP_HTA_v3_vault", "SEPTUM_FRAME_v5", "ANALOG_TRAY_v5", "SPINE_COMB_v5", "BASE_PLATE_RX_CASSETTE_v3", "HEAD_SKIRT"))}
lay = json.load(open("out_board/AB1A_layout.json")); rep = lay["rep"]
TR = [(l, tuple(a), tuple(b), w, n) for l, a, b, w, n in lay["TRACKS"]]; VI = [tuple(v) for v in lay["VIAS"]]
NAMES = {v: k for k, v in A.NETID.items()}; byname = {f"{p['ref']}.{p['num']}": p for p in A.PADS}
OPEN = [f.split(": ")[1] for f in rep["unrouted"]]; OPENNET = [f.split(": ")[0] for f in rep["unrouted"]]
ZOOM = ["UA1.4", "UA1.2", "UA1.3"]                                    # the VCC / VLOGIC / REGCAP pins that were the last open pocket before the island
LCOL = {"F.Cu": "#d33a2c", "In2.Cu": "#2e9c4a", "In3.Cu": "#d49a00", "B.Cu": "#2b63d8"}
CLEAR, TRACK, VIA = A.CLEAR, A.TRACK, A.VIA_D
NEED_TRACK = TRACK + 2 * CLEAR; NEED_VIA = VIA + 2 * CLEAR

fig = plt.figure(figsize=(30, 21), dpi=80, facecolor="#f4f6fa")
gs = fig.add_gridspec(3, 6, left=0.012, right=0.992, top=0.93, bottom=0.03, hspace=0.22, wspace=0.14, height_ratios=[1.0, 1.3, 1.1])
def panel(rc, title, sub=""):
    ax = fig.add_subplot(rc); ax.set_aspect("equal"); ax.set_facecolor("white"); ax.grid(alpha=0.15, lw=0.4)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#14213d", pad=14); ax.text(0, 1.015, sub, transform=ax.transAxes, fontsize=7.5, color="#55607a", va="bottom")
    ax.tick_params(labelsize=6.5); return ax
fig.suptitle("PHI-FOLD 233  receive stage cut-away: AB1A / AB1B with the AD7389-4 and the +3V3D island  (MODELED, tool-checked, nothing built)", fontsize=17, fontweight="bold", color="#14213d", x=0.012, ha="left", y=0.985)

# ------------------------------------------------------------------ 1 vault half-section
ax1 = panel(gs[0, 0:3], "1  Vault half-section (y = 0), cut faces from the current meshes", "heel (178 deg) to the left; boards drawn as slabs at the DESIGN_STATE section 3 z-ranges; D40 AB1A/AB1B at x = -/+ 20.3")
COL = dict(core="#7f8aa0", roof="#c9ced8", sep="#c9a227", tray="#8a7a55", base="#9aa5b8", comb="#8a7a55", skirt="#b5bccb")
for n, c in (("BASE_PLATE_RX_CASSETTE_v3", COL["base"]), ("HEAD_SKIRT", COL["skirt"]), ("CORE_CYLINDER_v5_integrated", COL["core"]), ("ROOF_PLATE_v5", COL["roof"]), ("HUB_CAP_HTA_v3_vault", COL["roof"]),
             ("SEPTUM_FRAME_v5", COL["sep"]), ("ANALOG_TRAY_v5", COL["tray"]), ("SPINE_COMB_v5", COL["comb"])):
    poly_patches(ax1, section(HEEL(head[n]), 1, 0.0), c, lw=0.3, flip=True)
def slab(ax, x0, x1, z0, z1, c, ec="#0a3d24", z=6, hatch=None):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=c, ec=ec, lw=0.5, zorder=z, hatch=hatch))
slab(ax1, -40.3, -0.3, 10.1, 11.7, "#1f7a4d"); slab(ax1, 0.3, 40.3, 10.1, 11.7, "#1f7a4d")
slab(ax1, -39, 39, 27.0, 28.6, "#1f7a4d"); slab(ax1, -39, 39, 39.2, 40.0, "#1f7a4d"); slab(ax1, -46, 46, 44.5, 46.1, "#1f7a4d")
for x0, x1 in ((-40.3, -0.3), (0.3, 40.3)):                                           # ADC (B side, below), front-side parts above
    slab(ax1, x0 + 10, x1 - 14, 9.0, 10.1, "#222", ec="#000", z=7); slab(ax1, x0 + 10, x1 - 14, 11.7, 12.5, "#555", ec="#000", z=7)
slab(ax1, -40.3 + 31, -40.3 + 38, 11.7, 15.7, "#bbb", ec="#555", z=7)                   # J2 header body 4.0 mm
for z, t in ((9.8, "L2 floor z 9.8"), (20.0, "L2/L3 z 20.0"), (21.9, "L3/L4 z 21.9"), (27.0, "L4/L5 z 27.0"), (38.8, "L5/L6 z 38.8")):
    ax1.axhline(z, color="#b00020", lw=0.4, ls=":", zorder=1); ax1.text(64, z + 0.25, t, fontsize=6, color="#b00020", ha="right")
dim(ax1, (-44, 9.8), (-44, 20.0), "L2 cell 10.2 mm\n(board 1.6 + parts above/below)", off=(-12, 0), fs=6.5)
dim(ax1, (47, 11.7), (47, 20.0), "8.3 mm free above AB1 (z 11.7 to 20.0)", off=(0, 0), fs=6.5, ha="center")
dim(ax1, (47, 9.8), (47, 10.1), "0.3 shim", off=(5.5, -2.0), fs=6)
lab(ax1, "AB1A (3 ch)", (-20, 10.9), (-60, 4)); lab(ax1, "AB1B (2 ch)", (20, 10.9), (28, 4)); lab(ax1, "J2 header 4.0 mm tall (AB1 <-> CB1D link)", (-5.5, 13.5), (-60, 16.5))
lab(ax1, "AD7389-4 (one quad ADC, LFCSP 4 x 4 x 0.55) on the BACK side", (-24, 9.5), (-60, 28)); lab(ax1, "septum + Cu cloth (D62 window)", (-30, 21), (-60, 33)); lab(ax1, "CB1D (D78), parts to 10.2 mm", (30, 27.8), (22, 33))
lab(ax1, "LB1 display", (30, 39.6), (22, 49)); lab(ax1, "HTA board in the cap", (0, 45.3), (-30, 52)); lab(ax1, "vault wall (CORE)", (-48, 22), (-62, 40))
ax1.set_xlim(-65, 65); ax1.set_ylim(-3, 56); ax1.set_xlabel("x (mm)", fontsize=7); ax1.set_ylabel("z (mm)", fontsize=7)

# ------------------------------------------------------------------ 2 plan at the AB1 level
ax2 = panel(gs[0, 3:6], "2  Plan section at z = 11 (AB1 level): what the two D40 discs must fit inside", "ring = the core wall cut at z = 11; discs AB1A / AB1B at x = -/+ 20.3; the shared strip between them carries J2 and the BLANK / SPI links")
T_ = HEEL(head["CORE_CYLINDER_v5_integrated"]); d_ = T_[:, :, 2] - (11.0 + 1.234e-4); m_ = (d_.min(1) < 0) & (d_.max(1) > 0); P_ = []
for tri_, dd_ in zip(T_[m_], d_[m_]):                                                   # points where the plane z = 11 cuts the triangle edges: the inner wall radius is the median of the per-10-degree minimum (the spine comb at 70-110 deg reaches r 37.2; the rest of the wall is at r 44.0)
    for i_, j_ in ((0, 1), (1, 2), (2, 0)):
        if (dd_[i_] < 0) != (dd_[j_] < 0): P_.append(tri_[i_] + dd_[i_] / (dd_[i_] - dd_[j_]) * (tri_[j_] - tri_[i_]))
P_ = np.array(P_); rr_ = np.hypot(P_[:, 0], P_[:, 1]); aa_ = np.degrees(np.arctan2(P_[:, 1], P_[:, 0])) % 360; bb_ = np.floor(aa_ / 10).astype(int)
Rin = float(np.median([rr_[bb_ == b].min() for b in range(36) if (bb_ == b).any()])); Rout = float(rr_[rr_ < 70].max()); cxin = 0.0
ax2.add_patch(Circle((0, 0), Rout, fc=COL["core"], ec="#222", lw=0.4, zorder=1)); ax2.add_patch(Circle((0, 0), Rin, fc="white", ec="#222", lw=0.6, zorder=2))
for cx, nm in ((-20.3, "AB1A"), (20.3, "AB1B")):
    ax2.add_patch(Circle((cx, 0), 20.0, fc="#1f7a4d", ec="#0a3d24", alpha=0.35, lw=0.8, zorder=5)); ax2.text(cx, 0, nm, ha="center", va="center", fontsize=12, color="#073b20", zorder=6, fontweight="bold")
dim(ax2, (-Rin, -46), (Rin, -46), f"inner bore {2 * Rin:.1f} mm at z = 11 (wall at z = 11, median of the section; spine comb to r 37.2)", off=(0, -3), fs=7)
dim(ax2, (-Rin, 24), (-40.3, 24), f"{Rin - 40.3:.1f}", off=(0, 2.5), fs=7); dim(ax2, (40.3, 24), (Rin, 24), f"{Rin - 40.3:.1f}", off=(0, 2.5), fs=7)
dim(ax2, (-40.3, 30), (-0.3, 30), "D40", off=(0, 2.5), fs=7); dim(ax2, (0.3, 30), (40.3, 30), "D40", off=(0, 2.5), fs=7); dim(ax2, (-0.3, 36), (0.3, 36), "0.6 gap", off=(0, 3), fs=6.5)
ax2.set_xlim(-60, 60); ax2.set_ylim(-60, 60); ax2.set_xlabel("x (mm)", fontsize=7)

# ------------------------------------------------------------------ 3 AB1A routed layout
ax3 = panel(gs[1, 0:2], "3  AB1A routed layout (AD7389-4 build): 0 open nets; the +3V3D island on In4 is the yellow box", "board frame, y down; tracks coloured by layer; planes In1 = GND and In4 = +5VA (hatched) are not drawn; island x 7.0 to 12.6, y 2.0 to 3.6 mm")
ax3.add_patch(Circle((0, 0), 20.0, fc="#f3f8f4", ec="#0a3d24", lw=1.2, zorder=0))
for l, a, b, w, n in TR: ax3.plot([a[0], b[0]], [a[1], b[1]], color=LCOL[l], lw=max(w * 4.5, 0.6), alpha=0.8 if l in ("F.Cu", "B.Cu") else 0.55, solid_capstyle="round", zorder=3 if l == "F.Cu" else 2)
for x, y, n in VI: ax3.add_patch(Circle((x, y), VIA / 2, fc="#ddd", ec="#444", lw=0.3, zorder=4))
for pd in A.PADS:
    top = pd["layer"] in ("F.Cu", "ALL"); bad = f"{pd['ref']}.{pd['num']}" in OPEN
    ax3.add_patch(Rectangle((pd["x"] - pd["w"] / 2, pd["y"] - pd["h"] / 2), pd["w"], pd["h"], fc=("#f2b8b0" if top else "#b8c9f2"), ec=("#e00000" if bad else "#333"), lw=(1.4 if bad else 0.25), zorder=5 if bad else 4, alpha=0.9))
for ref in sorted({p["ref"] for p in A.PADS}):
    if ref[:2] in ("UA", "J1", "J2", "U1", "U2", "U3", "UR", "UB", "SW", "D1", "D2", "D3"):
        xs = [p["x"] for p in A.PADS if p["ref"] == ref]; ys = [p["y"] for p in A.PADS if p["ref"] == ref]
        ax3.text(np.mean(xs), min(ys) - 1.0 if ref[:2] == "UA" else max(ys) + 1.2, ref, fontsize=6, color="#222", ha="center", zorder=8)
for name, net in zip(OPEN, OPENNET):
    p = byname[name]; others = [q for q in A.PADS if q["net"] == net and q is not p]
    q = min(others, key=lambda q: math.hypot(q["x"] - p["x"], q["y"] - p["y"]))
    ax3.plot([p["x"], q["x"]], [p["y"], q["y"]], color="#e00000", lw=1.4, ls=(0, (3, 2)), zorder=9)
    ax3.add_patch(Circle((p["x"], p["y"]), 1.1, fc="none", ec="#e00000", lw=1.6, zorder=9))
    ax3.text(p["x"] + 1.4, p["y"] - 1.3, f"OPEN {net}\n{name}", fontsize=7, color="#e00000", fontweight="bold", zorder=10, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="#e00000", lw=0.5))
for xs_, t in (((-19, 0), "front-side input chain (RS / D / SW / gain / RAAF)"), ):
    pass
ax3.text(-19.5, 19.0, "layers: F red, In2 green, In3 amber, B blue", fontsize=7, color="#333")
ax3.text(-19.5, 17.4, f"tracks {len(TR)}, vias {len(VI)}, unrouted {len(OPEN)}", fontsize=7, color="#1a8f3c")
if A.ISL is not None:
    ax3.add_patch(Rectangle((A.ISL[0], A.ISL[2]), A.ISL[1] - A.ISL[0], A.ISL[3] - A.ISL[2], fc="#ffe680", ec="#b38600", lw=1.0, alpha=0.6, zorder=1)); ax3.text(A.ISL[0], A.ISL[3] + 0.9, "+3V3D island (In4, hatched)", fontsize=6.5, color="#7a5c00", zorder=10)
dim(ax3, (-20, 21.5), (20, 21.5), "D40", fs=7)
ax3.set_xlim(-22, 22); ax3.set_ylim(22.5, -22); ax3.set_xlabel("x (mm)", fontsize=7); ax3.set_ylabel("y (mm, down)", fontsize=7)

# ------------------------------------------------------------------ zoom helpers: free gap around an open pad
def foreign_geoms(layer_name, net):
    G = []
    for pd in A.PADS:
        if pd["net"] == net: continue
        if pd["layer"] in (layer_name, "ALL"): G.append(sbox(pd["x"] - pd["w"] / 2, pd["y"] - pd["h"] / 2, pd["x"] + pd["w"] / 2, pd["y"] + pd["h"] / 2))
    for l, a, b, w, n in TR:
        if l == layer_name and NAMES.get(n) != net: G.append(LineString([a, b]).buffer(w / 2))
    for x, y, n in VI:
        if NAMES.get(n) != net: G.append(Point(x, y).buffer(VIA / 2))
    return unary_union(G)
def zoom(rc, name, title):
    pd = byname[name]; lname = "F.Cu" if pd["layer"] == "F.Cu" else "B.Cu"; net = pd["net"]
    ax = panel(rc, title, f"{name} on {lname}; red = needed passage, numbers = measured edge-to-edge gap to foreign copper")
    cx, cy = pd["x"], pd["y"]; W = 3.4
    F = foreign_geoms(lname, net); own = sbox(cx - pd["w"] / 2, cy - pd["h"] / 2, cx + pd["w"] / 2, cy + pd["h"] / 2)
    for l, a, b, w, n in TR:
        if abs(a[0] - cx) < W + 1 and abs(a[1] - cy) < W + 1 or abs(b[0] - cx) < W + 1 and abs(b[1] - cy) < W + 1:
            ax.plot([a[0], b[0]], [a[1], b[1]], color=LCOL[l], lw=w * 28 * (4.4 / 3.4) / 1.0 if False else max(w * 40, 1.0), alpha=1.0 if l == lname else 0.25, solid_capstyle="round", zorder=3 if l == lname else 2)
    for x, y, n in VI:
        if abs(x - cx) < W + 1 and abs(y - cy) < W + 1: ax.add_patch(Circle((x, y), VIA / 2, fc="#ddd", ec="#444", lw=0.6, zorder=4)); ax.add_patch(Circle((x, y), 0.127 + 0.0, fc="white", ec="#444", lw=0.3, zorder=5))
    for q in A.PADS:
        if abs(q["x"] - cx) < W + 1 and abs(q["y"] - cy) < W + 1 and q["layer"] in (lname, "ALL"):
            mine = q is pd
            ax.add_patch(Rectangle((q["x"] - q["w"] / 2, q["y"] - q["h"] / 2), q["w"], q["h"], fc=("#ff9d9d" if mine else "#d9c9a8"), ec=("#e00000" if mine else "#333"), lw=(1.8 if mine else 0.6), zorder=6))
            ax.text(q["x"], q["y"], f"{q['ref']}.{q['num']}" if mine or q["w"] > 0.4 else q["num"], fontsize=5.5 if not mine else 7, ha="center", va="center", zorder=7, color="#600" if mine else "#333")
    # clearance halo of the foreign copper: where the track CENTRE may not go
    halo = F.buffer(CLEAR + TRACK / 2)
    for p in (halo.geoms if hasattr(halo, "geoms") else [halo]):
        if p.geom_type == "Polygon" and abs(p.centroid.x - cx) < W + 3 and abs(p.centroid.y - cy) < W + 3:
            ax.add_patch(MPoly(np.asarray(p.exterior.coords), closed=True, fc="#ffcc00", ec="none", alpha=0.22, zorder=1))
    # rays from the pad edge to the nearest foreign copper
    for ang in range(0, 360, 45):
        dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        e = own.exterior; ex = max(abs(pd["w"] / 2 / dx) if abs(dx) > 1e-6 else 1e9, 0); ey = abs(pd["h"] / 2 / dy) if abs(dy) > 1e-6 else 1e9; t0 = min(ex, ey)
        s0 = (cx + dx * t0, cy + dy * t0); ray = LineString([s0, (cx + dx * 8, cy + dy * 8)]); hit = ray.intersection(F)
        if hit.is_empty: gap = None
        else: gap = Point(s0).distance(hit)
        need = NEED_TRACK
        ok = gap is None or gap >= need
        endp = (s0[0] + dx * (gap if gap is not None else 2.4), s0[1] + dy * (gap if gap is not None else 2.4))
        ax.plot([s0[0], endp[0]], [s0[1], endp[1]], color="#1a8f3c" if ok else "#e00000", lw=1.0, zorder=8)
        if gap is not None and gap < 2.4: ax.text(*(np.array(endp) + np.array([dx, dy]) * 0.12), f"{gap:.2f}", fontsize=6.5, color="#1a8f3c" if ok else "#e00000", ha="center", va="center", zorder=9, fontweight="bold",
                                                   bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none", alpha=0.85))
    ax.set_xlim(cx - W, cx + W); ax.set_ylim(cy + W, cy - W)
    ax.text(cx - W + 0.15, cy + W - 0.2, f"need >= {NEED_TRACK:.2f} mm for a track, {NEED_VIA:.2f} mm for a via; yellow = track-centre keep-out", fontsize=6.5, color="#7a5c00", va="bottom")
    return ax
zoom(gs[1, 2:4], ZOOM[0], "4  VCC pin UA1.4: closed by the island (stub + via at the tip)"); zoom(gs[1, 4:6], ZOOM[1], "5  VLOGIC pin UA1.2: closed the same way")
zoom(gs[2, 0:2], ZOOM[2], "6  REGCAP pin UA1.3 between them: the surface trace to CRG")

# ------------------------------------------------------------------ 7 blockers table (text built from the measured numbers)
ua = [p for p in A.PADS if p["ref"] == "UA1" and p["num"] != "25"]; uyx = sorted({round(p["y"], 2) for p in ua}); uxs = sorted({round(p["x"], 2) for p in ua})
pw = min(min(p["w"], p["h"]) for p in ua); ph = max(max(p["w"], p["h"]) for p in ua)
pitch = min(math.hypot(a['x'] - b['x'], a['y'] - b['y']) for a in ua for b in ua if a is not b)
axt = fig.add_subplot(gs[2, 2:6]); axt.axis("off"); axt.set_title("7  Receive-board status and every item still open", loc="left", fontsize=12, fontweight="bold", color="#14213d")
rows = [
 ("AB1A routing", f"0 unrouted nets, {len(TR)} tracks, {len(VI)} vias (two identical runs); KiCad DRC 0 errors / 0 unconnected", "was 3 open nets with 3 x ADS8860; closed by one AD7389-4 and the +3V3D island"),
 ("AD7389-4 pin row", f"pad {pw:.2f} x {ph:.2f} mm, pitch {pitch:.2f} mm: pad gap {pitch - min(pw, ph):.2f}", f"a track needs {NEED_TRACK:.2f} mm, a via {NEED_VIA:.2f} mm: pins 2 and 4 leave by a stub and a via into the island"),
 ("+3V3D island (In4)", "x 7.0..12.6, y 2.0..3.6 mm, 8.96 mm2, hatched; Gerber read-back: island vias connected, 0.16 mm to the +5VA pour", "3.025 mm from the OPA2211 pads; no closed copper loop around the axis"),
 ("Fab floor (AB1 override)", f"clearance {CLEAR}, track {TRACK}, via {VIA} / drill {A.VIA_DRILL}", "TTM T-HDI Standard, AdvancedPCB A-TOL; U-FAB-DRC: some facilities list 0.216 ring"),
 ("Router", "greedy single pass A*, 0.1 mm grid, no rip-up", "enough for this build; Options 2 (rip-up) and 3 (J2 move) were not needed"),
 ("J2 pad block", "2 x 6, 1.27 mm pitch, pads 1.10 mm (ring 0.225, gap 0.17)", "J2.3 (+3V3D) reaches the island by one trace and a via; SDO3 unused (2-wire readout)"),
 ("AB1B", "0 unrouted, KiCad DRC 0 errors / 0 unconnected, independent DRC 0 fails", "same chip and island; MONO input pad 3.085 mm from the island"),
 ("Datasheet pin maps", "AD7389-4 read from the supplied datasheet; SW1G66, OPA2365, BAV199 marked VERIFY", "exposed pad size of the LFCSP is a PLACEHOLDER (drawing shows none, text says ground it)"),
 ("Mechanics", "CORE cylinder + 14 other STLs non-manifold; U8_SEPTUM_extended oversize", "vault +8 mm (option 2) and rim disc not implemented; no eddy / field model for an added board"),
 ("Unverified", "SDI tied low, +3V3D rail budget (about 25 mA more), island hatch in a CAM viewer, fabricator DRC, bench", "U-DS-TXDRIVE, OKI, PACK, BAV199, HVTERM, U-FAB-DRC, U-CAM-VIEW, U-BENCH"),
]
y = 0.97
axt.text(0.0, y, "item", fontsize=9, fontweight="bold", transform=axt.transAxes); axt.text(0.14, y, "state / measured number", fontsize=9, fontweight="bold", transform=axt.transAxes); axt.text(0.60, y, "reason / next step", fontsize=9, fontweight="bold", transform=axt.transAxes)
for i, (a, b, c) in enumerate(rows):
    yy = y - 0.085 * (i + 1)
    axt.add_patch(Rectangle((0, yy - 0.04), 1.0, 0.08, transform=axt.transAxes, fc="#ffe9e9" if a in ("AB1A routing",) else ("#eef2fa" if i % 2 else "white"), ec="none", zorder=0))
    axt.text(0.0, yy, a, fontsize=8.2, fontweight="bold", transform=axt.transAxes, va="center"); axt.text(0.14, yy, b, fontsize=8, transform=axt.transAxes, va="center"); axt.text(0.60, yy, c, fontsize=8, transform=axt.transAxes, va="center")
for ext, kw in (("png", dict(dpi=80)), ("pdf", {})): fig.savefig(os.path.join(ROOT, OUT, f"PHIFOLD233_RECEIVE_CUTAWAY_AB1.{ext}"), **kw)
json.dump(dict(open_nets=dict(zip(OPEN, OPENNET)), need_track=NEED_TRACK, need_via=NEED_VIA, adc_pad=[pw, ph], adc_pitch=pitch, tracks=len(TR), vias=len(VI)), open(os.path.join(ROOT, OUT, "receive_cutaway_numbers.json"), "w"), indent=1)
print("wrote", OUT, dict(zip(OPEN, OPENNET)), "pad", pw, ph, "pitch", pitch)
