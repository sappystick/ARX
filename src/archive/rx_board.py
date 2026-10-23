#!/usr/bin/env python3
"""
PHI-FOLD 233 — ground-side 8-layer sensor board ("PF233-SB1")
================================================================
Merges the X/Y figure-8 quadrature layer with a centre self-nulled
gradiometer pair.  Board Ø232, 2.4 mm, 8 Cu layers, built as four 2-layer
sub-stacks with buried vias (sequential lamination):

  L1/L2  X figure-8   (TX-X quadrature / RX-X)   2 D-lobes, Rmax 110, gap 6
  L3/L4  Y figure-8   (TX-Y quadrature / RX-Y)   rotated 90 deg
  L5/L6  GX gradiometer, centre Ø44, 2 D-lobes, gap 3   (RX only)
  L7/L8  GY gradiometer, centre Ø44, rotated 90 deg     (RX only)   <- ground side

Each lobe: spiral IN on the odd layer, buried via at the lobe centre-line,
spiral OUT on the even layer with the SAME circulation; the two lobes of a
pattern are bridged across the gap on the even layer and wound in opposition
(signed area check).  Terminals escape along the gap to a copper-free rim
annulus (r 110-116) and around it to edge connector J1 at 90 deg.
Outputs: Gerber RS-274X per copper layer, outline, Excellon drills
(through + four buried pairs), pinout CSV, SVG preview, STL.
"""
import math, os, csv, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g

OUT = "out_board"; os.makedirs(OUT, exist_ok=True)
R_BOARD, R_FREE = 116.0, 110.0
BOARD_T = 2.4; Z_TOP = -0.4
LAYER_Z = {k: Z_TOP - 0.15 - (k - 1) * (BOARD_T - 0.3) / 7 for k in range(1, 9)}
PAT = {  # name: (layers, Rmax, gap, pitch, trace, turns, rot)
    "X8": ((1, 2), 110.0, 6.0, 2.40, 1.80, 18, 0.0),   # 1.8 mm, 2 oz Cu (TX-capable)
    "Y8": ((3, 4), 110.0, 6.0, 2.40, 1.80, 18, math.pi / 2),
    "GX": ((5, 6), 22.0, 3.0, 0.30, 0.15, 24, 0.0),
    "GY": ((7, 8), 22.0, 3.0, 0.30, 0.15, 24, math.pi / 2),
}

def d_spiral(Rmax, gap, pitch, turns, n_per_turn=420):
    """True continuous inward D-spiral for the +x lobe.  Inset grows linearly along the path
    (never revisits itself); only whole turns are laid, so the spiral starts AND ends exactly on
    the lobe axis y = 0 -> the buried via lines up with the mirrored partner layer."""
    def point(d, u):
        R = Rmax - d; xg = gap / 2 + d
        ym = math.sqrt(max(R * R - xg * xg, 0)); amax = math.asin(min(ym / R, 1))
        Lc, La = ym, 2 * amax * R; s_ = u * (2 * Lc + La)
        if s_ < Lc: return (xg, -s_)
        if s_ < Lc + La:
            t = -amax + (s_ - Lc) / R; return (max(R * math.cos(t), xg), R * math.sin(t))
        return (xg, ym - (s_ - Lc - La))
    pts = []
    for k in range(turns):
        d_end = (k + 1) * pitch
        if (Rmax - d_end) - (gap / 2 + d_end) < 3 * pitch: break
        for u in np.linspace(0, 1, n_per_turn, endpoint=False):
            pts.append(point((k + u) * pitch, u))
    kf = len(pts) // n_per_turn
    pts.append((gap / 2 + kf * pitch, 0.0))                 # exact end on the axis
    P = np.array(pts)
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-6]
    return P[keep]

def signed_area(P): return 0.5 * np.sum(P[:-1, 0] * P[1:, 1] - P[1:, 0] * P[:-1, 1])
def rot(P, a):
    c, s = math.cos(a), math.sin(a); return P @ np.array([[c, -s], [s, c]]).T

def build_pattern(name):
    (La, Lb), Rm, gap, pitch, w, turns, a = PAT[name]
    A = d_spiral(Rm, gap, pitch, turns)                    # right lobe, layer a, inward
    B = (A * np.array([1, -1]))[::-1]                      # mirror y, traverse outward -> same sense
    # sense check: one closed lobe traversal (A then B) must keep one circulation
    sR = np.sign(signed_area(A)); assert sR == np.sign(signed_area(B)), "lobe sense"
    assert abs(A[-1][1]) < 1e-9 and np.allclose(A[-1], B[0]), "via misaligned between layers"
    assert abs(A[0][1]) < 1e-9, "outer terminal off axis"
    AL = -A                                                # left lobe = 180-deg rotation (same geometric sense);
    BL = -B                                                # traversed in reverse below -> opposite circulation
    # series: T+ -> A_R(in) -> via_R -> B_R(out) -> bridge(layer b) -> B_L reversed(in) -> via_L -> A_L reversed(out) -> T-
    BLr, ALr = BL[::-1], AL[::-1]
    assert np.sign(signed_area(BLr)) == -sR and np.sign(signed_area(ALr)) == -sR, "opposition"
    viaR, viaL = A[-1], AL[-1]
    bridge = np.array([B[-1], BLr[0]])
    tp, tm = A[0], ALr[-1]                                 # outer terminals on layer a (on the gap axis)
    R2 = lambda P: rot(P, a)
    return dict(name=name, layers=(La, Lb), width=w,
                tracks={La: [R2(A), R2(ALr)], Lb: [R2(B), R2(BLr), R2(bridge)]},
                vias=[R2(viaR[None])[0], R2(viaL[None])[0]], tp=tp, tm=tm, rot=a)

pats = {n: build_pattern(n) for n in PAT}
# ---- connector J1: 10 through-hole pads on the copper-free rim annulus at 90 deg (r = 114.5)
RP = 114.5
padx = {"Y8-": -10.5, "Y8+": -7.5, "GY-": -5, "GY+": -3, "X8-": -1.5, "X8+": 1.5, "GX-": 3, "GX+": 5, "SHLD1": 7, "SHLD2": 9}
padpos = {k: np.array([x, math.sqrt(RP * RP - x * x)]) for k, x in padx.items()}
def arc(r, a0, a1, n=80):
    t = np.linspace(a0, a1, n); return np.c_[r * np.cos(t), r * np.sin(t)]
def routes(n, P):
    tp, tm = P["tp"], P["tm"]; R2 = lambda Q: rot(np.asarray(Q, float), P["rot"])
    if n == "X8":
        rp = [tp, (1.5, 0), (1.5, 112.0), padpos["X8+"]]; rm = [tm, (-1.5, 0), (-1.5, 112.0), padpos["X8-"]]
        return [R2(rp), R2(rm)]
    if n == "Y8":   # escape along the (rotated) gap to different radii, then concentric arcs to the pads
        ep = R2([tp, (1.5, 0), (1.5, 110.9)]); em = R2([tm, (-1.5, 0), (-1.5, 113.0)])
        ap = math.atan2(ep[-1][1], ep[-1][0]); am = math.atan2(em[-1][1], em[-1][0]) % (2 * math.pi)
        tgt_p = math.atan2(padpos["Y8+"][1], padpos["Y8+"][0]); tgt_m = math.atan2(padpos["Y8-"][1], padpos["Y8-"][0])
        rp = np.r_[ep, arc(110.9, ap, tgt_p), padpos["Y8+"][None]]
        rm = np.r_[em, arc(113.0, am, tgt_m), padpos["Y8-"][None]]
        return [rp, rm]
    if n == "GX":
        return [np.array([tp, (0.6, 0), (0.6, 23.5), (0.6, 100.0), padpos["GX+"]]),
                np.array([tm, (-0.6, 0), (-0.6, 23.5), (-0.6, 100.0), padpos["GX-"]])]
    if n == "GY":
        ep = R2([tp, (0.6, 0), (0.6, 23.5)]); em = R2([tm, (-0.6, 0), (-0.6, 25.5)])
        return [np.r_[ep, padpos["GY+"][None]], np.r_[em, padpos["GY-"][None]]]
for n, P in pats.items():
    La, Lb = P["layers"]; A_, ALr_ = P["tracks"][La]; B_, BLr_, br_ = P["tracks"][Lb]
    rp, rm = routes(n, P)
    P["tracks"][La] = [np.r_[rp[::-1], A_[1:]], np.r_[ALr_, rm[1:]]]
    P["tracks"][Lb] = [np.r_[B_, BLr_]]
pins = list(padx.keys())

# ---- design-rule check: no two tracks on the same layer may come closer than (w + 0.15 mm), except
#      consecutive segments of one track
def seg_dist(p1, p2, q1, q2):
    def pd(p, a, b):
        ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1); return np.linalg.norm(p - (a + t * ab))
    def inter(a, b, c, d):
        cr = lambda o, p, q: (p[0]-o[0])*(q[1]-o[1]) - (p[1]-o[1])*(q[0]-o[0])
        return (cr(a, b, c) * cr(a, b, d) < 0) and (cr(c, d, a) * cr(c, d, b) < 0)
    if inter(p1, p2, q1, q2): return 0.0
    return min(pd(p1, q1, q2), pd(p2, q1, q2), pd(q1, p1, p2), pd(q2, p1, p2))
def drc(tracks, w, clear=0.12, grid=2.0):
    from collections import defaultdict
    segs = []; sl = {}
    for ti, T in enumerate(tracks):
        cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(T, axis=0), axis=1))]
        for k in range(len(T) - 1): segs.append((ti, (cum[k], cum[k + 1]), T[k], T[k + 1]))
    cell = defaultdict(list)
    for si, (ti, k, a_, b_) in enumerate(segs):
        lo = np.floor(np.minimum(a_, b_) / grid).astype(int); hi = np.floor(np.maximum(a_, b_) / grid).astype(int)
        for i in range(lo[0], hi[0] + 1):
            for j in range(lo[1], hi[1] + 1): cell[(i, j)].append(si)
    worst = 1e9; bad = 0; seen = set(); where = []
    for lst in cell.values():
        for x in range(len(lst)):
            for y in range(x + 1, len(lst)):
                i1, i2 = lst[x], lst[y]
                if (i1, i2) in seen: continue
                seen.add((i1, i2))
                t1, k1, a1, b1 = segs[i1]; t2, k2, a2, b2 = segs[i2]
                m_ = max(1.0, 2.5 * w)
                if t1 == t2 and not (k2[1] < k1[0] - m_ or k2[0] > k1[1] + m_): continue   # same conductor, arclength-adjacent
                d = seg_dist(a1, b1, a2, b2)
                if d < w + clear:
                    bad += 1; where.append(((a1 + b1) / 2).round(2))
                worst = min(worst, d)
    return bad, worst, where[:6]

# ---------------- writers ----------------
def gerber(path, layer, tracks, width, pads=None, vias=None):
    with open(path, "w") as f:
        f.write("G04 PF233-SB1 layer L%d*\n%%FSLAX46Y46*%%\n%%MOMM*%%\n%%LPD*%%\n" % layer)
        f.write("%%ADD10C,%.3f*%%\n%%ADD11C,0.600*%%\n%%ADD12R,1.200X1.600*%%\n" % width)
        f.write("D10*\nG01*\n")
        fmt = lambda v: "%d" % round(v * 1e6)
        for P in tracks:
            f.write("X%sY%sD02*\n" % (fmt(P[0, 0]), fmt(P[0, 1])))
            for q in P[1:]: f.write("X%sY%sD01*\n" % (fmt(q[0]), fmt(q[1])))
        if vias:
            f.write("D11*\n")
            for v in vias: f.write("X%sY%sD03*\n" % (fmt(v[0]), fmt(v[1])))
        if pads:
            f.write("D12*\n")
            for v in pads: f.write("X%sY%sD03*\n" % (fmt(v[0]), fmt(v[1])))
        f.write("M02*\n")
def excellon(path, holes, dia):
    with open(path, "w") as f:
        f.write("M48\nMETRIC,TZ\nT1C%.3f\n%%\nT1\n" % dia)
        for h in holes: f.write("X%.3fY%.3f\n" % (h[0], h[1]))
        f.write("M30\n")

layer_tracks = {k: [] for k in range(1, 9)}; layer_w = {}
for P in pats.values():
    for L, tr in P["tracks"].items(): layer_tracks[L] += tr; layer_w[L] = P["width"]
names = {1: "X8_a", 2: "X8_b", 3: "Y8_a", 4: "Y8_b", 5: "GX_a", 6: "GX_b", 7: "GY_a", 8: "GY_b"}
for L in range(1, 9):
    vias = pats[names[L][:2]]["vias"]
    gerber(f"{OUT}/PF233-SB1_L{L}_{names[L]}.gbr", L, layer_tracks[L], layer_w[L],
           pads=list(padpos.values()), vias=vias)
th = np.linspace(0, 2 * math.pi, 721)
with open(f"{OUT}/PF233-SB1_outline.gko", "w") as f:
    f.write("%FSLAX46Y46*%\n%MOMM*%\n%ADD10C,0.100*%\nD10*\nG01*\n")
    f.write("X%dY%dD02*\n" % (round(R_BOARD * 1e6), 0))
    for t in th[1:]: f.write("X%dY%dD01*\n" % (round(R_BOARD * math.cos(t) * 1e6), round(R_BOARD * math.sin(t) * 1e6)))
    f.write("M02*\n")
excellon(f"{OUT}/PF233-SB1_through_J1.drl", list(padpos.values()), 0.80)
for pair, n in (("L1-L2", "X8"), ("L3-L4", "Y8"), ("L5-L6", "GX"), ("L7-L8", "GY")):
    excellon(f"{OUT}/PF233-SB1_buried_{pair}.drl", pats[n]["vias"], 0.30 if n[0] == "G" else 0.40)
with open(f"{OUT}/PF233-SB1_pinout_and_stack.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["J1 pin", "net", "pattern", "layers", "role"])
    role = {"X8": "TX-X quadrature / RX-X", "Y8": "TX-Y quadrature / RX-Y", "GX": "RX gradiometer X (self-nulled)", "GY": "RX gradiometer Y (self-nulled)"}
    for i, p in enumerate(pins):
        n = p[:2]; w.writerow([i + 1, p, n if n in pats else "shield", "L%d/L%d" % pats[n]["layers"] if n in pats else "-", role.get(n, "cable shield drain")])
drc_rep = {}
for L in range(1, 9):
    bad, worst, wh = drc(layer_tracks[L], layer_w[L]); drc_rep[f"L{L}"] = dict(violations=bad, min_track_gap_mm=round(worst - layer_w[L], 3), at=[w_.tolist() for w_ in wh])
print("DRC:", drc_rep)
# ---------------- SVG preview ----------------
cols = {1: "#d4a017", 2: "#b8860b", 3: "#2e86c1", 4: "#1b4f72", 5: "#c0392b", 6: "#922b21", 7: "#27ae60", 8: "#145a32"}
with open(f"{OUT}/PF233-SB1_preview.svg", "w") as f:
    f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-120 -120 240 240" width="900" height="900">')
    f.write('<circle cx="0" cy="0" r="116" fill="#123b2a"/>')
    for L in range(1, 9):
        for P in layer_tracks[L]:
            d = "M" + " L".join("%.3f,%.3f" % (p[0], -p[1]) for p in P)
            f.write('<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" opacity="0.75"/>' % (d, cols[L], max(layer_w[L], 0.3)))
    for p in padpos.values(): f.write('<rect x="%.2f" y="%.2f" width="1.2" height="1.6" fill="#eee"/>' % (p[0] - .6, -p[1] - .8))
    f.write('<text x="-110" y="118" font-size="5" fill="#fff">PF233-SB1  8-layer  Ø232  L1-2 X8 (gold)  L3-4 Y8 (blue)  L5-6 GX (red)  L7-8 GY (green)</text></svg>')
# ---------------- STL: substrate + copper ribbons ----------------
sub = g.revolve([(0.01, Z_TOP - BOARD_T), (R_BOARD, Z_TOP - BOARD_T), (R_BOARD, Z_TOP), (0.01, Z_TOP)], 360)
rc.write_stl(f"{OUT}/PF233-SB1_substrate.stl", *sub, "substrate")
def ribbon(P2, z, w, h=0.035):
    P = np.c_[P2, np.full(len(P2), z)]
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-6]; P = P[keep]
    if len(P) < 2: return None
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    Nn = np.cross(T, [0, 0, 1.0]); Nn /= np.maximum(np.linalg.norm(Nn, axis=1), 1e-9)[:, None]
    up = np.array([0, 0, h])
    V = np.concatenate([P + Nn * w / 2, P - Nn * w / 2, P - Nn * w / 2 + up, P + Nn * w / 2 + up])
    n = len(P); F = []
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        i = np.arange(n - 1)
        F.append(np.stack([a * n + i, b * n + i, b * n + i + 1], -1)); F.append(np.stack([a * n + i, b * n + i + 1, a * n + i + 1], -1))
    F.append(np.array([[0, n, 2 * n], [0, 2 * n, 3 * n]])); F.append(np.array([[n - 1, 3 * n + n - 1, 2 * n + n - 1], [n - 1, 2 * n + n - 1, n + n - 1]]))
    F = np.concatenate(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F
cu = []
for L in range(1, 9):
    for P in layer_tracks[L]:
        r_ = ribbon(P, LAYER_Z[L], layer_w[L])
        if r_: cu.append(r_)
Vc, Fc = g.merge(cu); rc.write_stl(f"{OUT}/PF233-SB1_copper_all_layers.stl", Vc, Fc, "copper")
rc.write_stl(f"{OUT}/PF233-SB1_board_ASSEMBLY.stl", *g.merge([sub, (Vc, Fc)]), "board")
report = {"DRC": drc_rep, **{n: dict(layers=P["layers"], turns_per_lobe_per_layer=PAT[n][5], trace_mm=PAT[n][4], pitch_mm=PAT[n][3],
                  track_length_m=round(sum(np.linalg.norm(np.diff(t, axis=0), axis=1).sum() for L in P["tracks"] for t in P["tracks"][L]) / 1000, 2))
          for n, P in pats.items()}}
import json; json.dump(report, open(f"{OUT}/PF233-SB1_report.json", "w"), indent=1)
print(json.dumps(report, indent=1))
