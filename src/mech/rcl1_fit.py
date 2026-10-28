#!/usr/bin/env python3
"""RCL1 clamp-resistor bank (B7, 2026-10-28): part rating against the transmit model, and fit of the bodies in the NPM hot zone on the meshes.
Part: 4 x Vishay BCcomponents PR03 metal film, 1 %, 1.24 kohm (E96) in series = 4.96 kohm (model 5.0 kohm, -0.8 %), Cu leads 0.78 mm (data sheet PR01/PR02/PR03,
Document 28729, Revision 08-Jul-2025, https://www.vishay.com/docs/28729/pr010203.pdf): P70 3 W (Cu lead), operating voltage Umax AC/DC 750 V, body D 5.2 max x
L 16.7 max, hot-spot limit 250 C, endurance 1000 h at P70 dR <= 5 % R + 0.1 ohm. Termination caps are plated steel (magnetic): the bank sits in the neck module,
0.4 m up the shaft, outside the head field (tx_system.py).
Rating: the bank sees the clamp-capacitor voltage minus VBUS. Peak <= Vds peak - VBUS (worst pack corner); RMS from the modeled dissipation, V = sqrt(P R).
Each part must hold the whole-bank RMS share and peak share, and on its own be >= 630 V (CLAUDE.md rule 6), at <= 50 % of P70.
Fit: the NPM pocket (potting_volumes.py frame: x -39..39, y 14..37, z 3..81) minus the N1 body, N2 lid, N3 dam, the PB1R board and its 41 component boxes;
each body box (5.2 x 5.2 x 16.7 + 3 mm straight lead at each end) inflated by 1.0 mm must sit in the free hot zone (x < -5, alumina / TC fill) and 1.0 mm from
the other bodies. Mesh booleans with manifold3d. MODELED / mesh-checked: nothing built.
usage (repo root, after make setup, the NPM meshes and the system-live step): python3 src/mech/rcl1_fit.py [OUT.json]"""
import sys, os, json, math, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import potting_volumes as PV

PART = dict(name="Vishay PR03 1 % 1K24 (Cu lead)", n=4, R_each=1240.0, P70=3.0, Umax=750.0, D=5.2, L=16.7, lead=3.0, src="Vishay PR01/PR02/PR03, Doc 28729, Rev 08-Jul-2025")
CLR = 1.0

def rating():
    cwd = os.getcwd(); os.chdir("work"); sys.path.insert(0, "."); import system_live as SL
    rows = []
    for vb in (19.6, 26.0, 29.4):
        for case in ("design",):
            p = SL.tx_point(vb, "boost", case)
            rows.append(dict(VBUS=vb, Vds_peak=round(float(p["Vds_peak"]), 1), P_RCL_W=round(float(p["P_RCL_W"]), 2)))
    R0 = SL.NS["RCL"]; os.chdir(cwd)
    Rb = PART["n"] * PART["R_each"]
    Vpk = max(r["Vds_peak"] - r["VBUS"] for r in rows)
    P = max(max(r["P_RCL_W"] for r in rows), 4.7)                     # 4.7 W = the as-built X7R clamp case (DESIGN_STATE), above the film-clamp model
    Vrms = math.sqrt(P * Rb)
    each = dict(P_W=round(P / PART["n"], 3), P_frac=round(P / PART["n"] / PART["P70"], 3), V_peak=round(Vpk / PART["n"], 1), V_rms=round(Vrms / PART["n"], 1))
    ok = each["P_frac"] <= 0.5 and each["V_peak"] <= PART["Umax"] and PART["Umax"] >= 630 and abs(Rb - R0) / R0 <= 0.02
    return dict(model_R_ohm=R0, bank_R_ohm=Rb, dev_pct=round((Rb - R0) / R0 * 100, 2), corners=rows, bank_V_peak=round(Vpk, 1), bank_P_W=P, bank_V_rms=round(Vrms, 1),
                per_part=each, bank_Umax=PART["Umax"] * PART["n"], ok=ok)

def fit():
    W = "work"; S = f"{W}/kit_v19/SPINE"
    parts = PV.union([PV.stl(f"{S}/{n}.stl") for n in ("NPM_N1_body_with_tunnel_v2", "NPM_N2_lid_with_fill_ports", "NPM_N3_hot_zone_dam_v2")])
    board = PV.box(-35, 35, 33.0, 34.6, 7, 77); comps = []
    for bd in json.load(open(f"{W}/kit_v6/PB1R/bodies.json")):
        lo, hi = bd["lo"], bd["hi"]; y0, y1 = 34.6 - (hi[2] + 1.6), 34.6 - (lo[2] + 1.6)
        if hi[0] - lo[0] > 0 and y1 - y0 > 0 and hi[1] - lo[1] > 0: comps.append(PV.box(lo[0], hi[0], y0, y1, lo[1] + 42.0, hi[1] + 42.0))
    solid = PV.union([parts, board] + comps)
    D, Lz = PART["D"], PART["L"] + 2 * PART["lead"]
    def env(x, y, z): return PV.box(x - CLR, x + D + CLR, y - CLR, y + D + CLR, z - CLR, z + Lz + CLR)
    cand = []
    for x in [-38.0 + 0.5 * i for i in range(0, 60)]:
        if x + D + CLR > -5.0 or x - CLR < -39.0: continue
        for y in [14.0 + CLR + 0.5 * j for j in range(0, 40)]:
            if y + D + CLR > 37.0: continue
            for z in [3.0 + CLR + 1.0 * k for k in range(0, 80)]:
                if z + Lz + CLR > 81.0: continue
                if (env(x, y, z) ^ solid).volume() < 1e-6: cand.append((x, y, z))
    # four bodies, pairwise >= CLR apart (envelopes may touch), shortest bounding span: two columns of two in series
    def sep(a, b): return a[0] + D + CLR <= b[0] or b[0] + D + CLR <= a[0] or a[1] + D + CLR <= b[1] or b[1] + D + CLR <= a[1] or a[2] + Lz + CLR <= b[2] or b[2] + Lz + CLR <= a[2]
    best = None
    xs = sorted({c[0] for c in cand})
    cset = set(cand)
    for (x1, y1, z1) in cand:                                          # greedy: first body, then the next three nearest that separate
        pick = [(x1, y1, z1)]
        for c in sorted(cand, key=lambda c: abs(c[0] - x1) + abs(c[1] - y1) + abs(c[2] - z1)):
            if all(sep(c, p) for p in pick): pick.append(c)
            if len(pick) == 4: break
        if len(pick) == 4:
            span = max(p[2] for p in pick) + Lz - min(p[2] for p in pick) + max(p[0] for p in pick) - min(p[0] for p in pick)
            if best is None or span < best[0]: best = (span, pick)
        if best and len(cand) > 400 and best[0] <= 2 * Lz + CLR + D + CLR: break
    bodies = [dict(x=p[0], y=p[1], z=p[2], box=[p[0], p[0] + D, p[1], p[1] + D, p[2], p[2] + Lz]) for p in (best[1] if best else [])]
    clear = all((env(b["x"], b["y"], b["z"]) ^ solid).volume() < 1e-6 for b in bodies) and all(sep((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"])) for a, b in itertools.combinations(bodies, 2))
    hot = all(b["box"][1] + CLR <= -5.0 for b in bodies)
    return dict(candidates=len(cand), bodies=bodies, clear_1mm=clear, in_hot_zone=hot, ok=bool(bodies) and len(bodies) == 4 and clear and hot,
                displaced_cm3=round(len(bodies) * math.pi / 4 * D * D * PART["L"] / 1000, 2))

if __name__ == "__main__":
    r, f = rating(), fit()
    out = dict(status="MODELED / mesh-checked", part=PART, rating=r, fit=f, ok=r["ok"] and f["ok"])
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "data/results/rcl1_fit.json", "w"), indent=1)
    print("rating", r["per_part"], "bank", r["bank_R_ohm"], "peak", r["bank_V_peak"], "ok", r["ok"]); print("fit", f["candidates"], [(b["x"], b["y"], b["z"]) for b in f["bodies"]], f["ok"])
