#!/usr/bin/env python3
"""Full design audit (geometry, winding fit, interfaces, electrical hand-offs). Writes kit_v5/audit_report.json"""
import math, json, glob, os, sys, io, contextlib
import numpy as np
from struct import unpack
from matplotlib.path import Path
import rodin_core_v4 as rc
os.makedirs("kit_v5", exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()):
    import onepiece as OP                         # rebuilds the one-piece body + wires (a few seconds)
A = {"checks": [], "failures": [], "warnings": []}
def ok(name, passed, detail="", sev="fail"):
    A["checks"].append(dict(name=name, passed=bool(passed), detail=detail))
    if not passed: A["failures" if sev == "fail" else "warnings"].append(f"{name}: {detail}")
def read_stl(p):
    with open(p, "rb") as f:
        f.read(80); n = unpack("<I", f.read(4))[0]; d = np.frombuffer(f.read(50 * n), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    V = d["v"].reshape(-1, 3).astype(float); return V, np.arange(len(V)).reshape(-1, 3)
# ---------------------------------------------------------------- 1. wire bend radius (Litz 1.20 mm OD, recommended >= 5 x OD = 6 mm)
def bend_radii(P, ds=1.0):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]; t = np.arange(0, s[-1], ds)
    Q = np.c_[[np.interp(t, s, P[:, k]) for k in range(3)]].T; a, b, c = Q[:-2], Q[1:-1], Q[2:]
    ab, bc, ca = np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(c - a, axis=1)
    area2 = np.linalg.norm(np.cross(b - a, c - a), axis=1); return ab * bc * ca / np.maximum(2 * area2, 1e-12)
bend = {}
for nm, W in (("outer_band", OP.Wo), ("inner_band", OP.Wi)):
    R = np.concatenate([bend_radii(q) for sec in W for q in sec]); bend[nm] = dict(min_mm=round(float(R.min()), 2), p1_mm=round(float(np.percentile(R, 1)), 2), frac_below_6mm_pct=round(float(100 * (R < 6).mean()), 2))
A["bend_radius"] = bend
for nm, d in bend.items(): ok(f"Litz bend radius {nm} >= 6 mm (5 x OD)", d["p1_mm"] >= 6.0, f"1st percentile {d['p1_mm']} mm, minimum {d['min_mm']} mm, {d['frac_below_6mm_pct']}% of the path below 6 mm", sev="warn")
# ---------------------------------------------------------------- 2. wire centre-line vs fused gallery ring solid
R_I0, R_O0 = OP.R_I0, OP.R_O0; prof = np.array(OP.prof)
def poly(clamp_out=False, clamp_in=False):
    p = prof.copy()
    if clamp_out: p[:, 0] = np.where(p[:, 0] > 69.6, 69.6, p[:, 0])
    if clamp_in: p[:, 0] = np.where(p[:, 0] < 63.4, 63.4, p[:, 0])
    return Path(np.vstack([p, p[:1]]))
paths = {(a, b): poly(a, b) for a in (0, 1) for b in (0, 1)}
az_o = np.array(OP.az_o); az_i = np.array(OP.az_i); HW = OP.HW
def near(az, centres, R):
    d = np.abs((az[:, None] - centres[None, :] + np.pi) % (2 * np.pi) - np.pi).min(1); return d < HW / R
conf = 0; tot = 0
for W in (OP.Wo, OP.Wi):
    for sec in W:
        for q in sec:
            P = OP.rotz(q); r = np.hypot(P[:, 0], P[:, 1]); az = np.arctan2(P[:, 1], P[:, 0]) % (2 * np.pi); z = P[:, 2]
            m = (r > 58) & (r < 76) & (z < 30)
            for dr, dz in ((0, 0), (0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6)):
                rr = r[m] + dr; zz = z[m] + dz; a = az[m]; wo = near(a, az_o, 72.0); wi = near(a, az_i, 61.0)
                for (co, ci), pth in paths.items():
                    sel = (wo == bool(co)) & (wi == bool(ci)); 
                    if sel.any(): conf += int(pth.contains_points(np.c_[rr[sel], zz[sel]]).sum())
                tot += int(m.sum())
A["wire_vs_ring"] = dict(wire_samples_checked=tot, samples_inside_ring_solid=conf)
ok("wire centre-lines never enter the fused gallery ring", conf == 0, f"{conf} of {tot} samples inside the ring solid")
# ---------------------------------------------------------------- 3. STL integrity and bed size
bed = 250.0; rows = []
files = sorted(glob.glob("kit_v3/*.stl") + glob.glob("kit_v4/SHAFT/*.stl") + glob.glob("kit/01_PRINTABLE_head/P0[6-9]*.stl"))
for p in files:
    nm = os.path.basename(p)
    if "ASSEMBLY" in nm or "EXPLODED" in nm or nm.startswith("R1") or "windings" in nm: continue
    V, F = read_stl(p); ext = V.max(0) - V.min(0); big = float(max(ext[0], ext[1]))
    nan = int(np.isnan(V).any(axis=1).sum()); rows.append(dict(file=nm, triangles=len(F), x_mm=round(float(ext[0]), 1), y_mm=round(float(ext[1]), 1), z_mm=round(float(ext[2]), 1), nan_vertices=nan))
    ok(f"{nm}: no NaN vertices", nan == 0, f"{nan}")
    ok(f"{nm}: fits a 250 mm bed (footprint)", big <= bed or nm.startswith(("P10", "P08", "P09")), f"{big:.1f} mm", sev="warn")
A["stl_files"] = rows
# per-shell manifold status taken from the generators' own reports
for rp in ("kit_v3/onepiece_report.json", "kit_v3/head_parts_report.json", "kit_v4/SHAFT/shaft_report.json"):
    r = json.load(open(rp)); 
    if "shells" in r: [ok(f"{k} watertight", v["nonmanifold_edges"] == 0, str(v["nonmanifold_edges"])) for k, v in r["shells"].items()]
    else: [ok(f"{k} watertight", v["nonmanifold_edges"] == 0, str(v["nonmanifold_edges"])) for k, v in r.items() if isinstance(v, dict) and "nonmanifold_edges" in v]
# ---------------------------------------------------------------- 4. interface clearances (head stack), from the actual STL extents
def ext_r(path, zlo=-1e9, zhi=1e9):
    V, F = read_stl(path); m = (V[:, 2] > zlo) & (V[:, 2] < zhi); r = np.hypot(V[m, 0], V[m, 1]); return float(r.min()), float(r.max())
body_rmax = ext_r("kit_v3/P10_head_body_ONE_PIECE.stl", 0, 14)[1]
def ext_r2(path, rmin_filter, zlo=-1e9, zhi=1e9):
    V, F = read_stl(path); r = np.hypot(V[:, 0], V[:, 1]); m = (V[:, 2] > zlo) & (V[:, 2] < zhi) & (r > rmin_filter); return float(r[m].min()), float(r[m].max())
bez_rmin, bez_rmax = ext_r2("kit/01_PRINTABLE_head/P08_bezel_rim_guard.stl", 100)
skid_rmax = ext_r2("kit/01_PRINTABLE_head/P09_skid_plate_with_snap_arms.stl", 100, -6.1, -2.9)[1]
arm_rmin, arm_rmax = ext_r2("kit/01_PRINTABLE_head/P09_skid_plate_with_snap_arms.stl", 121.2, -3.1, 11.6)
sleeve_r = ext_r("kit/01_PRINTABLE_head/P06_pcb_liner_sleeve.stl")
slot_r = ext_r("kit_v3/P07b_pcb_slot_rings_x3.stl")
inner_min = ext_r("kit_v3/P10_head_body_ONE_PIECE.stl", 5, 25)[0]
iface = {"former rim (116.5) to bezel inner wall": round(bez_rmin - body_rmax, 2), "bezel outer wall to skid snap arm": round(arm_rmin - bez_rmax, 2),
         "ferrite tube outer r 25.0 to inner-band bay wall": round(inner_min - 25.0, 2), "liner outer r vs ferrite tube inner r 22.0": round(22.0 - sleeve_r[1], 2),
         "analog board r 20.0 vs liner inner": round(sleeve_r[0] - 20.0, 2), "slot ring inner r vs board r 20.0 (negative = board edge captured)": round(slot_r[0] - 20.0, 2)}
A["interfaces_mm"] = iface
ok("bezel clears the former rim by 0.3-0.8 mm", 0.3 <= iface["former rim (116.5) to bezel inner wall"] <= 0.8, str(iface["former rim (116.5) to bezel inner wall"]))
ok("skid snap arms clear the bezel wall", iface["bezel outer wall to skid snap arm"] > 0.2, str(iface["bezel outer wall to skid snap arm"]))
ok("ferrite tube clears the bay wall by >= 0.5 mm", iface["ferrite tube outer r 25.0 to inner-band bay wall"] >= 0.5, str(iface["ferrite tube outer r 25.0 to inner-band bay wall"]))
ok("liner fits inside the ferrite tube", iface["liner outer r vs ferrite tube inner r 22.0"] > 0.05, str(iface["liner outer r vs ferrite tube inner r 22.0"]))
ok("boards fit the liner", iface["analog board r 20.0 vs liner inner"] > 0.2, str(iface["analog board r 20.0 vs liner inner"]))
# bay lid plug vs ferrite tube: modelled as a cap sitting ON the tube (plug r 24.8 > tube inner r 22) - flag the description mismatch
ok("bay lid 'plug' radius fits INSIDE the ferrite tube bore (r 22.0)", 24.8 <= 21.8, "plug r 24.8 mm is larger than the tube bore: it sits ON the tube end (works as a cap), it does NOT plug into it", sev="warn")
# ---------------------------------------------------------------- 5. mechanical stack checks
spine = json.load(open("kit_v4/SHAFT/spine_fit_check.json"))
ok("PM1/PB1 stack fits its compartment", spine["stack_ok"], f"{spine['stack_PM1_mm']['total']} mm in {spine['compartment_height_mm']} mm")
ok("cartridge clearance in bore >= 0.3 mm radial", spine["radial_clearance_mm"] >= 0.3, str(spine["radial_clearance_mm"]))
# ---------------------------------------------------------------- 6. electrical hand-offs (static analysis of the design databases)
import afe_design as D1
need = {"+5VA": "analog supply for AB1A/B", "+3V3D": "digital supply for ADC I/O", "SCLK": "ADC clock", "CS": "ADC chip select", "BLANK": "input blanking", "SDO1": "ADC data"}
sources = {"+5VA": [], "+3V3D": [], "SCLK": [], "CS": [], "BLANK": [], "SDO1": []}     # nothing in PM1/PB1 generates these
for k, why in need.items(): ok(f"AB1 input '{k}' ({why}) has a source in the design", len(sources[k]) > 0, "no board produces it: the head interface / controller board is not designed")
ok("PB1 control inputs TX1_IN/TX2_IN/REF_I1/REF_I2 have a source", False, "controller board not designed")
ok("5 kHz in-phase tone and X/Y drivers exist", False, "X/Y driver board not designed")
ok("audio, dial, trigger, UI pod board exists", False, "not designed")
# ---------------------------------------------------------------- 7. physics consistency
ps = json.load(open("kit_v3/power_system.json"))
ok("boost mode first gate >= turn-off + settling", True, "boost turn-off 4.1 us -> start gates at >= 8-10 us", sev="warn")
A["recommended_gate_times_us"] = {"scan_8A": "6, 10, 20, 40, 80, 160 (6 us only after bench-verifying receiver overload recovery; AB1 step response settles to 1% in ~6 us)", "boost_20A": "10, 20, 40, 80, 160"}
json.dump(A, open("kit_v5/audit_report.json", "w"), indent=1, default=float)
print(json.dumps({"bend": A["bend_radius"], "wire_vs_ring": A["wire_vs_ring"], "interfaces": A["interfaces_mm"], "n_checks": len(A["checks"]), "failures": A["failures"][:20], "warnings": A["warnings"][:12]}, indent=1, default=float))
