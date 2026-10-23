#!/usr/bin/env python3
"""Search-head drawings from the assembled model used by head_crosscheck.py: real cut-away sections (heel plane and spine plane), exploded layer stack, full colour-coded schematic."""
import sys, os
src = open("head_crosscheck.py").read().split("def overlap(")[0]
exec(src)                                                           # defines S (solids), VX (voxels), PXY, Z ... and voxelises everything
import numpy as np, math, json, csv
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
from PIL import Image
BG = "#0b2a52"; FG = "#e8f1ff"
# ---------------------------------------------------------------- part table: number, label, colour, subsystem
ORDER = ["BASEPLATE", "SB1R_QB", "SB1R_QA", "FORMER_L6", "FORMER_L5", "FORMER_L4", "FORMER_L3", "FORMER_L2", "FORMER_L1", "HUB", "TRAY", "AB1A", "AB1B", "SEPTUM", "COMB", "CB1D", "LB1", "ROOF", "PIPES", "CAP", "HTA", "HOOD", "SKIRT", "CRADLE", "BRIDGE", "BRIDGE_LID", "TXJ1"]
INFO = {"BASEPLATE": (1, "Base plate v3", "#7b8aa8", "mechanical"), "SB1R_QB": (2, "SB1R-QB receive board", "#2aa6d9", "receive"), "SB1R_QA": (3, "SB1R-QA receive board", "#7fd4ff", "receive"),
        "FORMER_L6": (4, "Coil former L6", "#ff9d2e", "transmit"), "FORMER_L5": (4, "Coil former L5", "#ffb347", "transmit"), "FORMER_L4": (4, "Coil former L4", "#ff9d2e", "transmit"), "FORMER_L3": (4, "Coil former L3", "#ffb347", "transmit"), "FORMER_L2": (4, "Coil former L2", "#ff9d2e", "transmit"), "FORMER_L1": (4, "Coil former L1", "#ffb347", "transmit"),
        "HUB": (5, "Central cylinder v5 (ribs, posts, TX-lead channel)", "#aab4c8", "mechanical"), "TRAY": (6, "Analog tray", "#3fb8b0", "mechanical"), "AB1A": (7, "AB1A analog board", "#4ade80", "receive"), "AB1B": (8, "AB1B analog board", "#22c55e", "receive"),
        "SEPTUM": (9, "Septum frame + copper cloth", "#e8c14a", "mechanical"), "COMB": (10, "Spine comb", "#b5835a", "mechanical"), "CB1D": (11, "CB1D controller", "#16a34a", "digital"), "LB1": (12, "LB1 display board (0.8 mm)", "#a78bfa", "led"),
        "ROOF": (13, "Roof plate", "#c6d0e4", "mechanical"), "PIPES": (14, "66 light pipes", "#fde047", "led"), "CAP": (15, "Cap v3", "#f1f5f9", "mechanical"), "HTA": (16, "HTA antenna board", "#bef264", "receive"),
        "HOOD": (17, "Ferrite hood carrier (26 tiles)", "#6b7690", "mechanical"), "SKIRT": (18, "Head skirt", "#8a93a8", "mechanical"), "CRADLE": (19, "TXJ1 cradle", "#f472b6", "transmit"), "BRIDGE": (20, "Umbilical bridge", "#9aa3b8", "mechanical"), "BRIDGE_LID": (21, "Bridge lid", "#b4bccd", "mechanical"), "TXJ1": (22, "TXJ1 junction board", "#fb7185", "transmit")}
# TXJ1 board (heel frame x' 53..76, y' +-5.5, z 36.4..38.0) as an analytic solid
c178, s178 = math.cos(math.radians(178)), math.sin(math.radians(178))
txj1 = dict(id="TXJ1", name="TXJ1", level="outer", kind="pcb", box=((53.0, 76.0), (-5.5, 5.5), (36.4, 38.0)))
SAll = S + [txj1]
def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
# ---------------------------------------------------------------- vertical slab sections at 0.25 mm
HS = 0.25; XW = 130.0; ZH = 49.0
def slab_mesh(T, rotdeg, ymin, ymax, swap):
    T = T.copy(); a = math.radians(rotdeg); c, s = math.cos(a), math.sin(a); x = T[:, :, 0] * c - T[:, :, 1] * s; y = T[:, :, 0] * s + T[:, :, 1] * c; T[:, :, 0], T[:, :, 1] = x, y
    lo = T.min(1); hi = T.max(1); T = T[(hi[:, 1] >= ymin) & (lo[:, 1] <= ymax)]
    nx = int(2 * XW / HS); nz = int((ZH + 1) / HS); ny = 2; cols = {}
    img = np.zeros((nx, nz), bool); ci = []; cz = []
    for t in T:
        a_, b_, c_ = t; ar = (b_[0] - a_[0]) * (c_[1] - a_[1]) - (c_[0] - a_[0]) * (b_[1] - a_[1])
        if abs(ar) < 1e-12: continue
        i0 = max(0, int(np.floor((min(a_[0], b_[0], c_[0]) + XW) / HS))); i1 = min(nx - 1, int(np.ceil((max(a_[0], b_[0], c_[0]) + XW) / HS)))
        if i1 < i0: continue
        gx = -XW + (np.arange(i0, i1 + 1) + 0.5) * HS + 0.0173; gy = np.array([0.0127])
        GX, GY = np.meshgrid(gx, gy, indexing="ij"); w0 = ((b_[0] - GX) * (c_[1] - GY) - (c_[0] - GX) * (b_[1] - GY)) / ar; w1 = ((c_[0] - GX) * (a_[1] - GY) - (a_[0] - GX) * (c_[1] - GY)) / ar; w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any(): continue
        z = w0 * a_[2] + w1 * b_[2] + w2 * c_[2]; ii, jj = np.nonzero(m); ci.append(ii + i0); cz.append(z[ii, jj])
    if not ci: return img
    ci = np.concatenate(ci); cz = np.concatenate(cz); o = np.lexsort((cz, ci)); ci = ci[o]; cz = cz[o]; st = np.r_[0, np.nonzero(np.diff(ci))[0] + 1]; cnt = np.diff(np.r_[st, len(ci)]); rk = np.arange(len(ci)) - np.repeat(st, cnt)
    hi_ = np.nonzero(rk % 2 == 1)[0]; lo_ = hi_ - 1; ok = ci[lo_] == ci[hi_]; lo_ = lo_[ok]; hi_ = hi_[ok]
    za = np.ceil((cz[lo_] + 1.0) / HS - 0.5).astype(int); zb = np.floor((cz[hi_] + 1.0) / HS - 0.5).astype(int); k = zb >= za; za = np.clip(za[k], 0, nz - 1); zb = np.clip(zb[k], 0, nz - 1); cc = ci[lo_][k]
    D = np.zeros((nx, nz + 1), np.int32); np.add.at(D, (cc, za), 1); np.add.at(D, (cc, zb + 1), -1); return np.cumsum(D[:, :nz], axis=1) > 0
def analytic_slab(sp, rotdeg):
    nx = int(2 * XW / HS); nz = int((ZH + 1) / HS); xs = -XW + (np.arange(nx) + 0.5) * HS; zs = -1.0 + (np.arange(nz) + 0.5) * HS
    a = math.radians(-rotdeg); X = xs[:, None] * np.ones((1, nz)); Y = np.zeros_like(X); Zg = zs[None, :] * np.ones((nx, 1)); xo = X * math.cos(a) - Y * math.sin(a); yo = X * math.sin(a) + Y * math.cos(a)     # back to the original frame
    if "disc" in sp:
        r, z0, z1 = sp["disc"]; m = (xo ** 2 + yo ** 2 <= r * r) & (Zg >= z0) & (Zg <= z1)
        if sp["id"] == "HTA":
            for px_, py_ in PXY: m &= ((xo - px_) ** 2 + (yo - py_) ** 2) > 0.85 ** 2
        return m
    if "pipes" in sp:
        r, z0, z1 = sp["pipes"]; m = np.zeros_like(X, bool)
        for px_, py_ in PXY: m |= ((xo - px_) ** 2 + (yo - py_) ** 2) <= r * r
        return m & (Zg >= z0) & (Zg <= z1)
    if "pcbsolid" in sp:
        d = sp["pcbsolid"]; m = ((xo ** 2 + yo ** 2 <= d["R"] ** 2) & ~((np.abs(xo) < NW) & (yo > NR)) & (Zg >= d["zb"]) & (Zg <= d["zt"]))
        for ref, t, x0, x1, y0, y1, z0, z1 in d["boxes"]: m |= (xo >= x0) & (xo <= x1) & (yo >= y0) & (yo <= y1) & (Zg >= z0) & (Zg <= z1)
        return m
    if "box" in sp:                                                       # heel-frame box -> head frame
        (a0, a1), (b0, b1), (c0, c1) = sp["box"]; xh = xo * c178 + yo * s178 * (-1) * (-1); xp = xo * c178 + yo * s178; yp = -xo * s178 + yo * c178
        return (xp >= a0) & (xp <= a1) & (yp >= b0) & (yp <= b1) & (Zg >= c0) & (Zg <= c1)
def section(rotdeg):
    lab = np.zeros((int(2 * XW / HS), int((ZH + 1) / HS)), np.int16)
    for pid in ORDER:
        sp = next(s for s in SAll if s["id"] == pid)
        m = slab_mesh(sp["T"], rotdeg, -0.4, 0.4, False) if "T" in sp else analytic_slab(sp, rotdeg)
        lab[m] = ORDER.index(pid) + 1
    return lab
# plane A through the heel axis: rotate by +2 deg so 178 deg maps to 180 (the -x axis); plane B through the spine: rotate by -90 so +y maps to +x ... slab y=0 then contains the 90/270 axis
LA = section(2.0); print("section A done", flush=True)
LB_ = section(-90.0); print("section B done", flush=True)
def render(lab, ax, title, xlim, annotate=True, num_offsets=None, aspect="equal"):
    h, w = lab.shape[1], lab.shape[0]; img = np.zeros((h, w, 4), float)
    for idx, pid in enumerate(ORDER):
        m = (lab == idx + 1).T[::-1]
        if m.any(): img[m, :3] = np.array(hexrgb(INFO[pid][2])) / 255.0; img[m, 3] = 1.0
    ax.imshow(img, extent=[-XW, XW, -1.0, ZH], aspect=aspect, interpolation="nearest"); ax.set_facecolor("#0b2a52"); ax.set_xlim(*xlim); ax.set_ylim(-1.5, 49.5)
    ax.tick_params(colors=FG, labelsize=8); [sp.set_color(FG) for sp in ax.spines.values()]; ax.set_title(title, color=FG, fontsize=12, loc="left"); ax.set_xlabel("mm along the cut", color=FG, fontsize=9); ax.set_ylabel("z (mm)", color=FG, fontsize=9)
    if annotate:
        placed = {}
        for idx, pid in enumerate(ORDER):
            m = (lab == idx + 1)
            if not m.any(): continue
            xs, zs = np.nonzero(m); xx = -XW + (xs + 0.5) * HS; zz = -1.0 + (zs + 0.5) * HS; vis = (xx > xlim[0]) & (xx < xlim[1])
            if not vis.any(): continue
            cx, cz = xx[vis].mean(), zz[vis].mean(); k = np.argmin((xx[vis] - cx) ** 2 + (zz[vis] - cz) ** 2); n = INFO[pid][0]
            if n in placed and pid.startswith("FORMER_L") and pid != "FORMER_L1": continue
            placed[n] = 1; ax.text(xx[vis][k], zz[vis][k], str(n), color="black", fontsize=8, ha="center", va="center", weight="bold", bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec="black", lw=0.5))
    for z, t in ((3.2, "L0|L1"), (9.8, "L2"), (20.0, "L3"), (21.9, "L4"), (27.0, "L5"), (39.2, "L6"), (41.3, "L7"), (44.5, "L8")):
        ax.axhline(z, color="#ffffff", lw=0.35, ls=":", alpha=0.6); ax.text(xlim[1] - 0.5, z + 0.3, t, color="#ffd27f", fontsize=7, ha="right")
figA = plt.figure(figsize=(26, 9), facecolor=BG); a1 = figA.add_axes([0.04, 0.12, 0.93, 0.78]); render(LA, a1, "CUT-AWAY A: plane through the heel axis (178 deg): exit window, TX-lead channel, TXJ1 and bridge on the left, spine-side wall on the right", (-130, 125))
figA.text(0.04, 0.03, "Colours: orange = transmit coil (6 formers, TXJ1), cyan/lime = receive (SB1R-QA/QB, AB1A/B, HTA), green = digital (CB1D), violet/yellow = LED (LB1, pipes), grey = printed housing. Formers shown as the low-resolution mesh. Litz windings, potting and the 26 ferrite tiles are not drawn.", color=FG, fontsize=10)
figA.savefig("kit_v22/HEAD_CUTAWAY_A_HEEL.png", dpi=55, facecolor=BG)
figB = plt.figure(figsize=(26, 9), facecolor=BG); b1 = figB.add_axes([0.04, 0.12, 0.93, 0.78]); render(LB_, b1, "CUT-AWAY B: plane through the spine channel (90 deg to 270 deg): floor slot, ribs' slots, boards, septum, roof, cap, HTA and pipes", (-125, 125))
figB.text(0.04, 0.03, "Left = 270 deg side, right = 90 deg side (spine channel, floor slot, comb). Same colour key as cut-away A.", color=FG, fontsize=10)
figB.savefig("kit_v22/HEAD_CUTAWAY_B_SPINE.png", dpi=55, facecolor=BG)
# ---------------------------------------------------------------- exploded layer stack from horizontal slices of the 0.5 mm label volume
LV = [("L0", 2.8, "base plate + SB1R-QA / QB receive boards"), ("L1", 6.0, "gallery: formers L6, hub wall, bosses, SB1R leads"), ("L2", 15.0, "analog cell: tray, AB1A, AB1B"), ("L3", 20.9, "septum frame + copper cloth, ribs"), ("L4", 24.5, "absorber cell, ribs, spine channel"),
      ("L5", 32.0, "CB1D controller, ribs"), ("L6", 40.4, "LB1 display, light pipes, posts, TX-lead groove"), ("L7", 42.6, "roof plate: pixel holes, vents, TX-lead channel"), ("L8", 46.0, "cap + HTA antenna + pipes")]
def plan(z):
    n = int(252 / H); lab = np.zeros((n, n), np.int16); k0 = int((z - Z0) / H)
    for idx, pid in enumerate(ORDER):
        if pid not in VX: continue
        lo, V = VX[pid]; k = k0 - lo[2]
        if k < 0 or k >= V.shape[2]: continue
        sl = V[:, :, k]; x0 = lo[0]; y0 = lo[1]; nx_, ny_ = sl.shape
        xa = max(x0, 0); xb = min(x0 + nx_, n); ya = max(y0, 0); yb = min(y0 + ny_, n)
        if xb > xa and yb > ya: sub = sl[xa - x0:xb - x0, ya - y0:yb - y0]; lab[xa:xb, ya:yb][sub] = idx + 1
    return lab
tiles = []
for name, z, desc in LV:
    lab = plan(z); h, w = lab.shape; img = np.zeros((w, h, 4), np.uint8)
    for idx, pid in enumerate(ORDER):
        m = (lab == idx + 1).T[::-1]; img[m, :3] = hexrgb(INFO[pid][2]); img[m, 3] = 255
    crop = Image.fromarray(img).resize((420, 420), Image.NEAREST); crop = crop.resize((420, 200), Image.BILINEAR); tiles.append((name, z, desc, crop))
fig = plt.figure(figsize=(22, 20), facecolor=BG); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 22); ax.set_ylim(0, 20); ax.axis("off"); ax.set_facecolor(BG)
for i, (name, z, desc, crop) in enumerate(tiles):
    y0 = 1.0 + i * 1.95; a2 = fig.add_axes([0.03, y0 / 20, 0.42, 2.3 / 20]); a2.imshow(np.asarray(crop)); a2.axis("off")
    ax.text(10.7, y0 + 1.25, f"{name}   z {z} mm", color="#ffd27f", fontsize=13, weight="bold"); ax.text(10.7, y0 + 0.75, desc, color=FG, fontsize=10.5)
ax.plot([3.4, 3.4], [1.2, 18.5], color="#ffb347", lw=1.0, ls="--"); ax.text(3.6, 19.1, "spine channel (90 deg) and floor slot run through every level; TX leads run in the wall-top channel (L6/L7) to the 178 deg window", color=FG, fontsize=10)
ax.text(0.4, 19.6, "EXPLODED LAYERED CUT-AWAY: horizontal section of the assembled head at each level (bottom = L0)", color=FG, fontsize=17, weight="bold")
fig.savefig("kit_v22/HEAD_EXPLODED_LAYERS.png", dpi=50, facecolor=BG)
print("layers done", flush=True)
# ---------------------------------------------------------------- full schematic sheet
import textwrap
figS = plt.figure(figsize=(26, 17), facecolor=BG); S0 = figS.add_axes([0, 0, 1, 1]); S0.set_xlim(0, 100); S0.set_ylim(0, 65.4); S0.axis("off"); S0.set_facecolor(BG)
axc = figS.add_axes([0.02, 0.50, 0.47, 0.40]); render(LA, axc, "Cross-section through the heel axis (vertical scale x2.4): numbers = component register", (-130, 125), aspect=2.4)
S0.text(1.0, 63.6, "PHI-FOLD 233 SEARCH HEAD v5.3: full schematic, every component highlighted (modeled design; nothing built or measured)", color=FG, fontsize=21, weight="bold")
SUB = {"transmit": "#ff9d2e", "receive": "#4ade80", "digital": "#16a34a", "led": "#a78bfa", "power": "#fb7185", "mechanical": "#aab4c8"}
def wrap(t, n): return "\n".join(l2 for l in t.split("\n") for l2 in (textwrap.wrap(l, n) or [""]))
def box(x, y, w, h, n, title, body, col, fs=10.2): S0.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", fc="#143d73", ec=col, lw=2.4)); S0.text(x + 0.5, y + h - 0.5, (f"[{n}] " if n else "") + title, color=col, fontsize=fs + 1.6, weight="bold", va="top"); S0.text(x + 0.5, y + h - 2.1, wrap(body, int(w * 2.55)), color=FG, fontsize=fs, va="top", linespacing=1.3)
def arrow(x0, y0, x1, y1, col, t=""): S0.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="->", mutation_scale=16, color=col, lw=2.2)); S0.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.7, t, color=col, fontsize=9.5, ha="center", weight="bold")
T_, R_, D_, L_, P_ = SUB["transmit"], SUB["receive"], SUB["digital"], SUB["led"], SUB["power"]
X1_, X2_, BW, BH = 51.5, 76.0, 23.0, 17.2
box(X1_, 44.2, BW, BH, "4,22,19", "TRANSMIT COIL + TXJ1", "6 formers in parallel: 54 uH, 45 mohm, 53.8 m litz.\n12 litz leads run in the wall-top channel to the 178 deg window, 6 per side, into TXJ1 (two copper bus bars), then the AWG12 pair. Layer current sharing 1.4 %, lead loop 0.12 uH. Cradle [19] sits in the bridge [20, 21].", T_)
box(X2_, 44.2, BW, BH, "PB1R", "NECK MODULE (0.4 m up the shaft)", "2 x IPB65R095C7 + TC4420, 10 mohm shunt. Clamp: ES3J into ONE 100 nF C0G/film in parallel with 5k/10 W. 20 A, turn-off 3.8 us, quiet 5.6 us, Vds 462 V of 650 V (29 %). JC 8-way to CB1D.JPB, JL1 to TXJ1.", T_)
box(X1_, 25.8, BW, BH, "3,2,7,8,16", "RECEIVE: SB1R-QA/QB, AB1A/B, HTA", "Two rotated quadrupoles (176 uH, leak 0.01-11 mV). Pads P1/P2 through the floor slot to AB1A.J1.1/.4 and J1.2/.5; RS 100 ohm, BAV199, blank switch, OPA2211, ADS8860. Spare inputs tied to VCM. HTA [16] gives the di/dt reference. OPEN: a 470-680 ohm damping resistor per coil.", R_)
box(X2_, 25.8, BW, BH, "11", "CB1D CONTROLLER (6-layer)", "Pico 2 W, SPI master, 74HC4051 mux, OKI-78SR 5 V, 3V3. MONO tap (330 ohm chain, 100 nF/630 V) to AB1B.J2.10. JA/JB 12-way to AB1A/B J2 on the spine flex. JCL taps COIL_A/B at TXJ1; JHTA, JTR, JPB, JPW, JLB. 46/46 nets, independent DRC 0/0, min gap 0.17 mm.", D_)
box(X1_, 7.4, BW, BH, "12,14,13,15,16", "LED PROCESS: 66 pixels", "CB1D JLB (+5V, LED_IN, GND, GND) to LB1 flat wire pads; 74AHCT1G125 feeds 66 SK6812-class LEDs in one chain (65 links). 66 pipes D1.5 run from LED top z40.8 to HTA top z47.0 through 66 holes in the roof [13], cap [15] and HTA [16]. Full white would draw 3.96 A: firmware cap 0.35 A required.", L_)
box(X2_, 7.4, BW, BH, "PM1, HB1", "POWER PATH (elbow) and handle", "PM1: dual 7S1P pack OR-ing, 2 x 470 uF, SMCJ33A TVS. VBUS 29.4 V max over the ribbon (3 + 3 conductors, 1.72 m) to PB1R.JP and CB1D.JPW. Scan 4.7 W, boost 7.7 W, 90.7 Wh. HB1 trigger, dial and joystick feed CB1D.JTR (7-way).", P_)
arrow(X1_ + BW, 52.8, X2_, 52.8, T_, "TX pair AWG12"); arrow(X1_ + BW, 34.4, X2_, 34.4, R_, "SPI, BLANK, SDO"); arrow(X1_ + BW / 2, 25.8, X1_ + BW / 2, 24.6, L_, ""); arrow(X2_ + BW / 2, 25.8, X2_ + BW / 2, 24.6, P_, "")
arrow(X2_ + BW / 2, 44.2, X2_ + BW / 2, 43.0, D_, "")
S0.text(51.5, 6.7, "SIGNAL FLOW: PB1R drives the coil through TXJ1; the coil flux is read by SB1R-QA/QB; AB1A/B digitise; CB1D filters, bearings and drives the 66-pixel display;\nHTA monitors the transmit pulse; PM1 and HB1 supply and command.", color=FG, fontsize=9.8, va="top")
S0.text(51.5, 0.5, wrap("CHECKED THIS RELEASE: geometry 43/43; board stack-up 9/9; wiring 53 link pins + 59 harness conductors, 0 errors; 3D interference at 0.5 mm and 0.2 mm, 0; exact board-body vs rib/post/wall test, 0 conflicts; TX ports 12/12 open; LED chain 66/66 with pixel positions, roof, cap and HTA holes matching; stress table 24 pass, 1 watch, 1 fail by design (LED cap). OPEN: damping resistor, KiCad/CAM check, PB1R/PM1/HB1 routing, datasheet ratings, firmware, rigid-flex spine, handle redesign.", 175), color="#ffd27f", fontsize=9.8, va="bottom")
S0.text(1.5, 32.6, "COMPONENT REGISTER (colour = subsystem: orange transmit, green/lime receive and digital, violet/yellow LED, grey housing)", color="#ffd27f", fontsize=12.5, weight="bold"); seen = set(); items = []
for pid in ORDER:
    n, nm, col, sub = INFO[pid]
    if n in seen: continue
    seen.add(n); items.append((n, nm, col, sub))
for i, (n, nm, col, sub) in enumerate(items):
    cx = 1.5 + (i // 11) * 24.0; cy = 30.0 - (i % 11) * 2.15; S0.add_patch(Rectangle((cx, cy - 0.75), 1.4, 1.5, fc=col, ec="white", lw=0.5)); S0.text(cx + 1.9, cy, f"{n:>2}  " + wrap(nm, 30).replace("\n", "\n      "), color=FG, fontsize=10.4, va="center")
figS.savefig("kit_v22/SEARCH_HEAD_FULL_SCHEMATIC.png", dpi=55, facecolor=BG)
print("schematic done")
