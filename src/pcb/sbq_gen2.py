#!/usr/bin/env python3
"""SB1R-Q receive boards v2. Every lobe = 4 series stepped spirals of exactly 6 full rings (r = 40,35,...,15 mm), seam, vias and
junctions at the same relative angle, so the four lobes are identical up to 90 deg rotation and winding direction (+,-,+,-).
Board A: 4 layers, through vias only. Board B = the same copper rotated 45 deg."""
import numpy as np, math, json, itertools
from scipy.spatial import cKDTree
R_OUT, R_IN, NT, W = 40.0, 15.0, 6, 0.8
VIA_D, VIA_DR, CLR = 0.8, 0.4, 0.2
RAMP = 20.0
VIN1, VIN2, VOUT = 12.8, 6.5, 42.0
CENT = [(50., 50.), (-50., 50.), (-50., -50.), (50., -50.)]
SGN = [1, -1, 1, -1]
P1, P2 = (4.0, 33.0), (-4.0, 33.0)
# board B terminals end at r23 (same angles): QA covers r33 at 128-142 deg, so QB leads come up through two transfer holes in QA
# where QA has no copper (radial terminal legs carry no EMF from the axisymmetric field; the shorter closing chord is re-tuned by sbq_tune B)
PB_R = 23.0; P1B, P2B = tuple(np.multiply(P1, PB_R / math.hypot(*P1))), tuple(np.multiply(P2, PB_R / math.hypot(*P2)))
# damping resistor across each coil (OPEN_ITEMS 1): 0805 on the QA top, on the chord between the lead pads; RD2 sits across the QB transfer pads
RD_PAD, RD_PITCH, RD_TRACE, PTH_PAD = (1.0, 1.3), 1.9, 0.4, 1.6
HOLE_RAD = 1.7

def pt(c, r, a): a = math.radians(a); return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))

def spiral(c, r0, r1, sg, sm):
    radii = np.linspace(r0, r1, NT); d = math.radians(RAMP); h = d / 2; sm = math.radians(sm); cur = sm + sg * h; pts = []
    def arc(r, a, sweep):
        n = max(2, int(abs(sweep) / math.radians(5)) + 2); th = a + np.linspace(0, sweep, n); return list(zip(c[0] + r * np.cos(th), c[1] + r * np.sin(th)))
    for j in range(NT):
        sweep = sg * (2 * math.pi - d); pts += arc(radii[j], cur, sweep); cur += sweep
        if j < NT - 1:
            th = cur + sg * np.linspace(0, d, 6); rr = np.linspace(radii[j], radii[j + 1], 6); pts += list(zip(c[0] + rr * np.cos(th), c[1] + rr * np.sin(th))); cur += sg * d
    return np.array(pts)

def lobe(k):
    c = CENT[k]; sg = SGN[k]; sm = math.degrees(math.atan2(-c[1], -c[0]))
    s0 = spiral(c, R_OUT, R_IN, sg, sm); s1 = spiral(c, R_IN, R_OUT, sg, sm); s2 = spiral(c, R_OUT, R_IN, sg, sm); s3 = spiral(c, R_IN, R_OUT, sg, sm)
    v1, v2, v3 = pt(c, VIN1, sm), pt(c, VOUT, sm), pt(c, VIN2, sm)
    s0 = np.vstack([s0, v1]); s1 = np.vstack([v1, s1, v2]); s2 = np.vstack([v2, s2, v3]); s3 = np.vstack([v3, s3])
    S = tuple(s0[0]); E = tuple(s3[-1])
    order = [0, 1, 2, 3] if k % 2 == 0 else [3, 2, 1, 0]
    return [(order[0], s0), (order[1], s1), (order[2], s2), (order[3], s3)], [v1, v2, v3], S, E

RAD = dict(a=8.0, b=9.0, c=10.0, t1=14.0, t2=8.0); RADB = dict(RAD)
try: _r = json.load(open("kit_v22/sbq_radii.json")); RAD.update(_r.get("A", {})); RADB.update(_r.get("B", {}))
except Exception: pass

def rpath(Q0, Q1, r, ccw=True):
    """Q0 -> radial leg in to radius r -> circular arc -> radial leg out to Q1 (radial legs carry no EMF from the azimuthal induced field)"""
    a0 = math.atan2(Q0[1], Q0[0]); a1 = math.atan2(Q1[1], Q1[0]); sw = (a1 - a0) % (2 * math.pi) if ccw else -((a0 - a1) % (2 * math.pi))
    n = max(2, int(abs(sw) / math.radians(5)) + 2); th = a0 + np.linspace(0, sw, n)
    return np.array([Q0] + [(r * math.cos(t), r * math.sin(t)) for t in th] + [Q1])

def link_paths(S, E, rad, pads=(P1, P2)):
    return dict(l1=rpath(E[0], S[1], rad["a"]), l2=rpath(E[1], S[2], rad["b"]), l3=rpath(E[2], S[3], rad["c"]), t1=rpath(S[0], pads[0], rad["t1"]), t2=rpath(E[3], pads[1], rad["t2"]))

def build(rad=None, pads=(P1, P2)):
    rad = rad or RAD; layers = {i: [] for i in range(4)}; vias = []; S = []; E = []
    for k in range(4):
        sp, vs, s, e = lobe(k)
        for lay, poly in sp: layers[lay].append(poly)
        vias += vs; S.append(s); E.append(e)
    lp = link_paths(S, E, rad, pads)
    layers[3].append(lp["l1"]); layers[0].append(lp["l2"]); layers[3].append(lp["l3"]); layers[0].append(lp["t1"]); layers[0].append(lp["t2"])
    return layers, vias

def rot(arr, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); a = np.asarray(arr, float)
    return np.c_[a[:, 0] * c - a[:, 1] * s, a[:, 0] * s + a[:, 1] * c]

def pdist(p, poly):
    a, b = poly[:-1], poly[1:]; ab = b - a; L2 = (ab ** 2).sum(1) + 1e-12
    t = np.clip(((p - a) * ab).sum(1) / L2, 0, 1); q = a + ab * t[:, None]
    return float(np.sqrt(((p - q) ** 2).sum(1)).min())

def same_layer_clearance(layers, joined_ok=3.0):
    worst, where = 1e9, None
    for lay, polys in layers.items():
        pts, pid, arc = [], [], []
        for i, p in enumerate(polys):
            seg = np.sqrt((np.diff(p, axis=0) ** 2).sum(1)); s = np.r_[0, np.cumsum(seg)]; n = max(2, int(s[-1] / 0.25)); u = np.linspace(0, s[-1], n)
            q = np.c_[np.interp(u, s, p[:, 0]), np.interp(u, s, p[:, 1])]; pts.append(q); pid += [i] * n; arc += list(u)
        P = np.vstack(pts); pid = np.array(pid); arc = np.array(arc); T = cKDTree(P)
        tot = {i: float(np.sqrt((np.diff(p, axis=0) ** 2).sum(1)).sum()) for i, p in enumerate(polys)}
        atend = np.array([(arc[j] < joined_ok) or (arc[j] > tot[pid[j]] - joined_ok) for j in range(len(arc))])
        for a, b in T.query_pairs(W + CLR + 1.2):
            if pid[a] == pid[b] and abs(arc[a] - arc[b]) < 8.0: continue
            if atend[a] and atend[b]: continue
            d = np.linalg.norm(P[a] - P[b]) - W
            if d < worst: worst = d; where = (int(lay), tuple(np.round(P[a], 1)), tuple(np.round(P[b], 1)))
    return worst, where

def via_check(layers, vias):
    """vias are through holes: every layer's copper must stay >= 1.0 mm from the via centre unless that copper ends at the via"""
    m, where = 1e9, None
    for v in vias:
        for lay, polys in layers.items():
            for p in polys:
                ends = min(math.dist(v, p[0]), math.dist(v, p[-1]))
                if ends < 1e-6: continue                              # copper that terminates at this via
                d = pdist(np.array(v), p) - (VIA_DR + W / 2 + CLR)
                if d < m: m = d; where = (tuple(np.round(v, 1)), int(lay))
    return m, where

def hole_margin(layers, vias, pads, hl):
    m = 1e9
    for h in hl:
        for polys in layers.values():
            for p in polys: m = min(m, pdist(np.array(h), p) - (W / 2 + HOLE_RAD + 0.4))
        for v in list(vias) + list(pads): m = min(m, math.dist(h, v) - (VIA_DR + HOLE_RAD + 0.4))
        m = min(m, 114 - math.hypot(*h) - HOLE_RAD - 1.0)
    return m

def rd_footprint(pa, pb):
    """0805 across the chord pa-pb: returns (centre, angle_deg, pad centres, connecting traces pad->PTH)"""
    pa, pb = np.asarray(pa, float), np.asarray(pb, float); c = (pa + pb) / 2; u = (pb - pa) / np.linalg.norm(pb - pa)
    q1, q2 = c - u * RD_PITCH / 2, c + u * RD_PITCH / 2
    return tuple(c), math.degrees(math.atan2(u[1], u[0])), [tuple(q1), tuple(q2)], [np.array([pa, q1]), np.array([q2, pb])]

def pad_margin(layers, pts, r, skip_ends=()):
    """copper margin (mm) of round pads of radius r at pts against every layer, ignoring copper that terminates at skip_ends"""
    m = 1e9
    for polys in layers.values():
        for p in polys:
            if any(min(math.dist(e, p[0]), math.dist(e, p[-1])) < 1e-6 for e in skip_ends): continue
            for q in pts: m = min(m, pdist(np.asarray(q), p) - (W / 2 + r + CLR))
    return m

def rd_margin(layer0, fp, own_ends):
    """F.Cu margin of the resistor pads (as circles enclosing the pad) and traces against F.Cu copper not ending at the lead pads"""
    _, _, qs, tr = fp; rp = math.hypot(*RD_PAD) / 2; m = 1e9
    for p in layer0:
        if any(min(math.dist(e, p[0]), math.dist(e, p[-1])) < 1e-6 for e in own_ends): continue
        for q in qs: m = min(m, pdist(np.asarray(q), p) - (W / 2 + rp + CLR))
        for t in tr:
            for s_ in np.linspace(0, 1, 12): m = min(m, pdist(t[0] + s_ * (t[1] - t[0]), p) - (W / 2 + RD_TRACE / 2 + CLR))
    return m

if __name__ == "__main__":
    layers, vias = build(); pads = [P1, P2]
    g, where = same_layer_clearance(layers); gB, whB = same_layer_clearance(build(RADB, (P1B, P2B))[0]); g = min(g, gB); print("min same-layer gap (A,B):", None if g > 1e8 else round(g, 2), where)
    vm, vw = via_check(layers, vias); vm = min(vm, via_check(*build(RADB, (P1B, P2B)))[0]); print("via clearance margin (>0 ok):", round(vm, 2), vw)
    layersB0, viasB0 = build(RADB, (P1B, P2B)); LB = {l: [rot(p, 45) for p in ps] for l, ps in layersB0.items()}; vB = [tuple(rot([v], 45)[0]) for v in viasB0]; pB = [tuple(rot([p], 45)[0]) for p in (P1B, P2B)]
    best = (-1e9, None)
    for hr in (22.0, 24.0, 26.0, 28.0):
        angs = [a * 2.5 for a in range(144)]; mg = {}
        for a in angs:
            h = [(hr * math.cos(math.radians(a)), hr * math.sin(math.radians(a)))]
            mg[a] = min(hole_margin(layers, vias, pads + pB, h), hole_margin(LB, vB, pB, h))
        good = [a for a in angs if mg[a] > 0.0 and abs(((a - 90) + 180) % 360 - 180) > 28]
        for t in itertools.combinations(good, 3):
            sep = [min((t[j] - t[i]) % 360, (t[i] - t[j]) % 360) for i, j in ((0, 1), (1, 2), (0, 2))]
            if min(sep) < 80: continue
            # the triangle of bosses must enclose the axis
            pts = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in t]
            cr = [(pts[(i + 1) % 3][0] - pts[i][0]) * (0 - pts[i][1]) - (pts[(i + 1) % 3][1] - pts[i][1]) * (0 - pts[i][0]) for i in range(3)]
            if not (all(c > 0 for c in cr) or all(c < 0 for c in cr)): continue
            m = min(mg[a] for a in t) + 0.01 * min(sep)
            if m > best[0]: best = (m, (hr, t))
    print("holes: radius, angles", best[1], "margin", None if best[1] is None else round(min(mg_ for mg_ in [best[0]]), 2))
    hr, t = best[1]; hl = [(hr * math.cos(math.radians(a)), hr * math.sin(math.radians(a))) for a in t]
    hmarg = min(hole_margin(layers, vias, pads + pB, hl), hole_margin(LB, vB, pB, hl)); print("final hole margin (mm beyond 0.4 mm clearance):", round(hmarg, 2))
    # QB lead access and damping resistors (QA carries RD1 across P1/P2, two transfer PTHs over the QB pads and RD2 across them)
    tmA = pad_margin(layers, pB, PTH_PAD / 2); tmB = pad_margin(LB, pB, PTH_PAD / 2, skip_ends=pB)
    fA = rd_footprint(P1, P2); fB = rd_footprint(*pB); rmA = rd_margin(layers[0], fA, (P1, P2)); rmB = rd_margin(layers[0], fB, ())
    print("QB transfer pads on QA copper margin:", round(tmA, 2), "| QB pads on QB copper margin:", round(tmB, 2), "| RD1 / RD2 F.Cu margin:", round(rmA, 2), round(rmB, 2))
    # symmetry of the lobes: signed area-turns
    ar = []
    for k in range(4):
        sp, _, _, _ = lobe(k); ar.append(sum(0.5 * np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1]) for _, p in sp))
    print("signed area-turns per lobe (mm2):", [round(a) for a in ar])
    tot = sum(sum(float(np.sqrt((np.diff(p, axis=0) ** 2).sum(1)).sum()) for p in ps) for ps in layers.values())
    out = dict(hole_radius=hr, hole_angles=list(t), hole_margin_mm=round(hmarg, 2), min_same_layer_gap_mm=None if g > 1e8 else round(g, 2), via_margin_mm=round(vm, 2),
               area_turns_mm2=[round(a) for a in ar], copper_length_m=round(tot / 1000, 3), vias=len(vias),
               layers={str(l): [p.round(4).tolist() for p in ps] for l, ps in layers.items()}, via_xy=[list(np.round(v, 4)) for v in vias], pads=[P1, P2], layersB={str(l): [p.round(4).tolist() for p in ps] for l, ps in LB.items()}, via_xyB=[list(np.round(v, 4)) for v in vB], padsB=[list(np.round(p, 4)) for p in pB], radA=RAD, radB=RADB,
               transfer_margin_mm=round(tmA, 2), padB_margin_mm=round(tmB, 2), rd_margin_mm=[round(rmA, 2), round(rmB, 2)],
               rd=dict(RD1=dict(net="QA_COIL", centre=list(np.round(fA[0], 4)), angle=round(fA[1], 3), pads=[list(np.round(q, 4)) for q in fA[2]]), RD2=dict(net="QB_COIL", centre=list(np.round(fB[0], 4)), angle=round(fB[1], 3), pads=[list(np.round(q, 4)) for q in fB[2]])))
    json.dump(out, open("kit_v22/sbq_geometry.json", "w")); print("length m", out["copper_length_m"], "R(1oz) ohm", round(1.72e-8 * tot / 1000 / (W * 1e-3 * 35e-6), 1))
