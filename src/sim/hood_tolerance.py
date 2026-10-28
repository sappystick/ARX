#!/usr/bin/env python3
"""Ferrite hood placement tolerance (FINAL_INTEGRATION_PLAN P3): how much the on-axis field changes per mm of tile placement error, from the same axisymmetric
magnetostatic model as the hood design (hood_axi.py: solve, hood_cells, rings, spoke_width; MnZn mu 2000, DC, Wiener upper bound, ASSUMPTIONS 8 / 23).
Baseline = hood v3 (hood_v20.py): 13 spokes, inner tile r57-84 x 26.2, outer tile butted r84.2-112.5, 2.5 mm thick, layer centre z 31.65, butt gap 0.2 mm.
Perturbations (each applied to ALL tiles, the only kind an axisymmetric model can represent): layer height dz, radial shift dr, butt gap, thickness, width.
Result per perturbation: field change at 100 / 200 / 300 mm in % of the hood-on field, the slope (% per mm, central difference), and the placement
tolerance that keeps the field within 0.5 % at 200 mm (half of a 1 % hood budget, the other half left to the material permeability).
A single misplaced tile is roughly 1/13 of the uniform effect on the axis field, but it breaks the symmetry the receive null relies on: that part needs a 3-D
model and the bench (U-BENCH), and is not claimed here. MODELED.
usage (in work/, after make setup): python3 hood_tolerance.py [OUT.json]"""
import sys, json, math, time
import numpy as np
import hood_axi as H
DEP = np.array([100, 200, 300]) * 1e-3
ZC, TH, N = 31.65, 2.5, 13
def v3(dz=0.0, dr=0.0, gap=0.2, th=TH, dw=0.0):
    w2 = H.spoke_width(N, 84.0 + gap, 112.5)
    return [(57.0 + dr, 84.0 + dr, 26.2 + dw), (84.0 + dr, 112.5 + dr, w2 + dw)], ZC + dz, th, gap
def field(rg, segs, zc, th, gap):
    """thickness below the 0.5 mm grid: the layer keeps the design cells and its radial permeability is scaled by th / TH (the same thin-layer homogenisation
    as the azimuthal fill: parallel flux paths); the vertical (harmonic) component is left as designed. Without this a +-0.2 mm change selects the same cells."""
    mr, mz = H.hood_cells(N, segs, zc, TH, "upper", gap)
    if abs(th - TH) > 1e-9:
        lay = mr > 1.5; mr = mr.copy(); mr[lay] = (th / TH) * mr[lay] + (1 - th / TH)
    return H.Bz_axis(H.solve(mr, mz, rg), DEP)
if __name__ == "__main__":
    t0 = time.time(); rg = H.rings(); one = np.ones((len(H.R) - 1, len(H.Z) - 1)); B0 = H.Bz_axis(H.solve(one, one, rg), DEP)
    base = field(rg, *v3()); gain = {int(d * 1e3): round(100 * (b / b0 - 1), 3) for d, b, b0 in zip(DEP, base, B0)}
    print("baseline v3 gain %", gain, round(time.time() - t0, 1), "s", flush=True)
    SWEEP = {"layer height dz (mm, + = up, away from the soil)": ("dz", [-1.0, -0.5, 0.5, 1.0]), "radial shift dr (mm, + = outward)": ("dr", [-1.0, -0.5, 0.5, 1.0]),
             "butt gap (mm, design 0.2)": ("gap", [0.0, 0.1, 0.3, 0.5]), "tile thickness (mm, design 2.5)": ("th", [2.3, 2.4, 2.6, 2.7]), "tile width change (mm, both tiles)": ("dw", [-0.4, -0.2, 0.2, 0.4])}
    DEF = dict(dz=0.0, dr=0.0, gap=0.2, th=TH, dw=0.0); out = dict(status="MODELED (axisymmetric, upper Wiener bound, DC)", baseline_gain_pct=gain, sweeps={})
    for nm, (k, vals) in SWEEP.items():
        rows = []
        for v in vals:
            kw = dict(DEF); kw[k] = v; B = field(rg, *v3(**kw))
            rows.append(dict(value=v, dfield_pct={int(d * 1e3): round(100 * (b / bb - 1), 4) for d, b, bb in zip(DEP, B, base)}))
        x = np.array([r["value"] for r in rows]) - DEF[k]; y = np.array([r["dfield_pct"][200] for r in rows]); s = float(np.polyfit(x, y, 1)[0])
        tol = 0.5 / abs(s) if abs(s) > 1e-9 else None
        out["sweeps"][nm] = dict(param=k, rows=rows, slope_pct_per_mm_at_200=round(s, 4), tolerance_mm_for_0p5pct_at_200=round(tol, 3) if tol else None)
        print(nm, "slope %.4f %%/mm" % s, "-> +-%.2f mm for 0.5 %%" % tol if tol else "", round(time.time() - t0, 1), "s", flush=True)
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "kit_v23/hood_tolerance.json", "w"), indent=1)
