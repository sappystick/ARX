#!/usr/bin/env python3
"""TX field steering study (owner question 2026-10-28: drive the six petals separately and "spin" the field). MODELED with the Biot-Savart loops of
sim_quadbearing.py (RX-Q: QUAD-A and QUAD-B rotated 45 deg, the active receive channels). No design change follows from this script by itself.
Facts it records:
(0) the six v15 TX layers are concentric full-ring spirals stacked at z 3.2-28.8 mm; the golden-angle step rotates only a 2.4 mm 12-fold ripple and the lead
    exits, so firing layers separately cannot steer the field (ENHANCEMENT_REVIEW 2026-10-23 s.5: the top layer is 0.69-0.88 of the bottom one on the axis).
(1) a SINGLE offset coil (8 turns r 20-50 mm, centred 55 mm off the axis, z 10 mm, x 16 as in a layer) tilts the field below the centre in the azimuth of
    the coil (a field that turns as the coils fire in sequence), at about 0.2 of the full coil's field, and couples microhenries into a quadrupole:
    tens of volts at turn-off against 0.01 mV for the symmetric coil (DESIGN_STATE RX-Q leak).
(2) a PUSH-PULL PAIR (coil at a, the opposite coil at a + 180 deg driven the other way) couples ZERO into both quadrupoles by symmetry (a quadrupole is even
    under a 180 deg turn, the pair is odd) and makes a horizontal field below the centre along the pair axis: three pairs give three field directions
    (0 / 60 / 120 deg), the sign of the drive gives the opposite ones.
Turn-off rate for the leak volts: 20 A in t_zero 3.76 us -> 5.3 A/us (fw_timeline inputs), the same for every option (MODELED, not a driver design).
Writes kit_v23/tx_steer_study.json. usage (in work/): python3 tx_steer_study.py"""
import sys, json, math
import numpy as np
src = open("sim_quadbearing.py").read().split("out={}")[0]; ns = {}; exec(src, ns)
Bvec_many, quadA, quadB, ring = ns["Bvec_many"], ns["quadA"], ns["quadB"], ns["ring"]
Z = 10.0; TURNS = 16; DIDT = 20.0 / 3.76e-6; DEPTHS = (100, 200, 300); R_OFF = 55.0
def coil(cx, cy, sgn=1, r0=20, r1=50, n=8): return [ring(r, cx, cy, sgn, z=Z * 1e-3) for r in np.linspace(r0, r1, n)]
FULL = [ring(r, 0, 0, 1, z=Z * 1e-3) for r in np.linspace(62, 110, 8)]          # same 8-turn spiral span as a v15 layer (R0 62, R1 109.6)
def flux_disc(loops, cx, cy, r):
    n = 40; rr = (np.arange(n) + 0.5) / n * r; th = np.linspace(0, 2 * np.pi, 72, endpoint=False); R, T = np.meshgrid(rr, th)
    pts = np.c_[(cx + R * np.cos(T)).ravel(), (cy + R * np.sin(T)).ravel(), np.full(R.size, Z)] * 1e-3
    return float(np.sum(Bvec_many(loops, pts)[:, 2] * (r / n * 1e-3) * (R.ravel() * 1e-3) * (2 * np.pi / 72)))
def M_to_quads(discs):
    """mutual inductance (H) of TX discs [(cx, cy, r, sign)] x TURNS to QUAD-A and QUAD-B (flux of the quad field through the TX turns, reciprocity)"""
    return [TURNS * sum(s * flux_disc(q, cx, cy, r) for cx, cy, r, s in discs) for q in (quadA, quadB)]
def field_at(loops, depth): return Bvec_many(loops, np.array([[0.0, 0.0, -depth * 1e-3]]))[0]
def tilt(B): return math.degrees(math.atan2(math.hypot(B[0], B[1]), abs(B[2])))
if __name__ == "__main__":
    out = dict(status="MODELED: Biot-Savart loops, quasi-static, no ferrite hood, no eddy currents; a study, not a design", didt_A_per_us=round(DIDT / 1e6, 2), single={}, pairs={}, checks={})
    Bf = {d: np.linalg.norm(field_at(FULL, d)) for d in DEPTHS}
    MA0, MB0 = M_to_quads([(0, 0, 110, 1)]); out["full_coil_M_nH"] = [round(MA0 * 1e9, 4), round(MB0 * 1e9, 4)]
    for k in range(6):
        a = math.radians(60 * k); cx, cy = R_OFF * math.cos(a), R_OFF * math.sin(a); L = coil(cx, cy); MA, MB = M_to_quads([(cx, cy, 50, 1)])
        out["single"][f"{60 * k} deg"] = dict(M_quadA_nH=round(MA * 1e9, 1), M_quadB_nH=round(MB * 1e9, 1), leak_V=round(max(abs(MA), abs(MB)) * DIDT, 2),
                                             per_depth={d: dict(tilt_deg=round(tilt(field_at(L, d)), 1), azimuth_deg=round(math.degrees(math.atan2(*field_at(L, d)[1::-1])) % 360, 1),
                                                                rel_full=round(float(np.linalg.norm(field_at(L, d)) / Bf[d]), 3)) for d in DEPTHS})
    for a_deg in (0, 60, 120):
        a = math.radians(a_deg); c1 = (R_OFF * math.cos(a), R_OFF * math.sin(a)); c2 = (-c1[0], -c1[1]); L = coil(*c1, 1) + coil(*c2, -1)
        MA, MB = M_to_quads([(c1[0], c1[1], 50, 1), (c2[0], c2[1], 50, -1)]); Ms, _ = M_to_quads([(c1[0], c1[1], 50, 1)])
        out["pairs"][f"axis {a_deg} deg"] = dict(M_quadA_nH=round(MA * 1e9, 4), M_quadB_nH=round(MB * 1e9, 4), cancel_vs_single=round(max(abs(MA), abs(MB)) / max(abs(Ms), 1e-30), 6),
                                                per_depth={d: dict(tilt_deg=round(tilt(field_at(L, d)), 1), azimuth_deg=round(math.degrees(math.atan2(*field_at(L, d)[1::-1])) % 360, 1),
                                                                   rel_full=round(float(np.linalg.norm(field_at(L, d)) / Bf[d]), 3)) for d in DEPTHS})
    S = out["single"]; P = out["pairs"]
    out["checks"] = dict(
        full_coil_nulled=max(abs(x) for x in out["full_coil_M_nH"]) < 1.0,
        single_coil_steers=all(abs(v["per_depth"][100]["azimuth_deg"] - float(k.split()[0])) % 360 < 1.0 or abs(v["per_depth"][100]["azimuth_deg"] - float(k.split()[0])) % 360 > 359.0 for k, v in S.items()),
        single_coil_leak_V_min=min(v["leak_V"] for v in S.values()),
        pairs_null_to_quads=all(max(abs(v["M_quadA_nH"]), abs(v["M_quadB_nH"])) < 1e-3 * max(abs(S["0 deg"]["M_quadA_nH"]), abs(S["0 deg"]["M_quadB_nH"]), 1.0) for v in P.values()),
        pairs_horizontal_below_centre=all(abs(v["per_depth"][d]["tilt_deg"] - 90.0) < 1.0 for v in P.values() for d in DEPTHS),
        pair_field_rel_full=[P["axis 0 deg"]["per_depth"][d]["rel_full"] for d in DEPTHS],
        single_field_rel_full=[S["0 deg"]["per_depth"][d]["rel_full"] for d in DEPTHS])
    out["ok"] = all(v for v in out["checks"].values() if isinstance(v, bool))
    json.dump(out, open("kit_v23/tx_steer_study.json", "w"), indent=1)
    for k, v in out["checks"].items(): print(f"{k:32s} {v}")
    print("OK" if out["ok"] else "FAIL"); sys.exit(0 if out["ok"] else 1)
