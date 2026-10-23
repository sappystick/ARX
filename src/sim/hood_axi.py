#!/usr/bin/env python3
"""Ferrite hood: axisymmetric magnetostatic model (an independent method to the coupled-dipole model of hood_study2.py, docs/ASSUMPTIONS.md 8).
Solves for the flux function psi = r A_phi on a non-uniform (r, z) grid:  -d/dz( 1/(mu_r r) dpsi/dz ) - d/dr( 1/(mu_z r) dpsi/dr ) = mu0 J_phi.
Field lines are contours of psi (where the field is pointed); B_z = (1/r) dpsi/dr, B_r = -(1/r) dpsi/dz.
Coil: each of the 16 turns per layer of the six petal formers (kit_v15/LOW/paths.pkl) as an equivalent ring (area-preserving radius), I/6 per
layer, all turns in the same sense. The petal ripple (12-fold) averages out of the axisymmetric field.
Hood: the tile layer is homogenised per radius with the azimuthal fill f(r) = N w / (2 pi r) of straight tiles. Bounds on the effective
permeability of a tile/air layer (Wiener bounds, docs/ASSUMPTIONS.md 23): upper = f mu + (1-f) for both components (parallel paths); lower = the
same radially but the harmonic mean vertically, f/mu + (1-f) inverted. Real tiles sit between the bounds. MnZn mu = 2000, no losses, DC."""
import numpy as np, math, json, pickle, time
import scipy.sparse as sp, scipy.sparse.linalg as spl
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
mu0 = 4e-7 * math.pi; MU = 2000.0; I_TX = 20.0
PN, G, ZRX = 3.6, 0.8, 3.2

def rings():
    P = pickle.load(open("kit_v15/LOW/paths.pkl", "rb")); out = []
    for k in range(1, 7):
        z = (ZRX + (6 - k) * (PN + G) + PN - 0.7) * 1e-3
        for path in (np.asarray(P[k][0], float), np.asarray(P[k][1], float)):
            th = np.unwrap(np.arctan2(path[:, 1], path[:, 0])); r2 = (path ** 2).sum(1); turn = np.floor((th - th[0]) / (2 * math.pi) * np.sign(th[-1] - th[0]) + 1e-9).astype(int)
            for t in range(turn.max() + 1):
                m = turn == t
                if m.sum() > 20: out.append((math.sqrt(r2[m].mean()) * 1e-3, z, np.sign(th[-1] - th[0]) * I_TX / 6))
    return out

def axis_grid(fine_lo, fine_hi, h, far_lo, far_hi, ratio=1.06):
    x = list(np.arange(fine_lo, fine_hi + h / 2, h)); d = h
    while x[-1] < far_hi: d *= ratio; x.append(x[-1] + d)
    d = h; lo = [x[0]]
    while lo[-1] > far_lo: d *= ratio; lo.append(lo[-1] - d)
    return np.array(sorted(set(lo[1:] + x)))

R = np.r_[0.0, axis_grid(0.5e-3, 0.140, 0.5e-3, 0.0, 3.0)[1:]]; R = R[R >= 0]; R = np.unique(np.r_[0.0, R[R > 0]])
Z = axis_grid(-0.100, 0.060, 0.5e-3, -3.0, 3.0)

def solve(mu_r_cell, mu_z_cell, rg):
    """mu_*_cell: (len(R)-1, len(Z)-1) cell permeabilities. Returns psi on nodes (interior unknowns; psi = 0 on the axis and far boundary)."""
    nr, nz = len(R), len(Z); dr = np.diff(R); dz = np.diff(Z); rc = 0.5 * (R[1:] + R[:-1])
    idx = -np.ones((nr, nz), int); inner = [(i, j) for i in range(1, nr - 1) for j in range(1, nz - 1)]
    for n, (i, j) in enumerate(inner): idx[i, j] = n
    rows, cols, vals = [], [], []; diag = np.zeros(len(inner))
    iz_r = 1.0 / mu_z_cell / rc[:, None]; ir_r = 1.0 / mu_r_cell / rc[:, None]       # 1/(mu r) per cell
    def add(n, m, c):
        diag[n] += c
        if m >= 0: rows.append(n); cols.append(m); vals.append(-c)
    for n, (i, j) in enumerate(inner):
        # r-edges (i,j)-(i+1,j) and (i-1,j)-(i,j): coefficient = mean over the two cells above/below of 1/(mu_z r) x (half heights) / dr
        for ii, nb in ((i, i + 1), (i - 1, i - 1)):
            c = (iz_r[ii, j - 1] * dz[j - 1] / 2 + iz_r[ii, j] * dz[j] / 2) / dr[ii]; add(n, idx[nb if nb != i - 1 else i - 1, j], c)
        for jj, nb in ((j, j + 1), (j - 1, j - 1)):
            c = (ir_r[i - 1, jj] * dr[i - 1] / 2 + ir_r[i, jj] * dr[i] / 2) / dz[jj]; add(n, idx[i, nb if nb != j - 1 else j - 1], c)
    A = sp.csr_matrix((np.r_[vals, diag], (np.r_[rows, np.arange(len(inner))], np.r_[cols, np.arange(len(inner))])), shape=(len(inner),) * 2)
    b = np.zeros(len(inner))
    for r0, z0, I in rg:                                                    # ring current -> bilinear share on the 4 surrounding nodes
        i = np.searchsorted(R, r0) - 1; j = np.searchsorted(Z, z0) - 1; tr = (r0 - R[i]) / (R[i + 1] - R[i]); tz = (z0 - Z[j]) / (Z[j + 1] - Z[j])
        for (a, c), w in (((i, j), (1 - tr) * (1 - tz)), ((i + 1, j), tr * (1 - tz)), ((i, j + 1), (1 - tr) * tz), ((i + 1, j + 1), tr * tz)):
            if idx[a, c] >= 0: b[idx[a, c]] += mu0 * I * w
    psi = np.zeros((nr, nz)); x = spl.spsolve(A.tocsc(), b)
    for n, (i, j) in enumerate(inner): psi[i, j] = x[n]
    return psi

def Bz_axis(psi, depths):
    """B_z on the axis from psi ~ B_z r^2 / 2 (quadratic fit over the first nodes)"""
    out = []
    for d in depths:
        zc = -d; j = np.searchsorted(Z, zc); w = (zc - Z[j - 1]) / (Z[j] - Z[j - 1]); col = psi[:, j - 1] * (1 - w) + psi[:, j] * w
        k = slice(1, 5); out.append(float(np.polyfit(R[k] ** 2, col[k], 1)[0] * 2))
    return np.array(out)

def hood_cells(N, segs, zc, th, bound, gap=0.0):
    """segs: [(r0, r1, width_mm)]; straight tiles of constant width -> fill f = N w / (2 pi r). gap: radial air gap (mm) between butted tiles of a
    spoke, below the grid resolution: applied as a series reluctance over the spoke length, mu_r = L / (L / mu + gap)"""
    rc = 0.5 * (R[1:] + R[:-1]); zm = 0.5 * (Z[1:] + Z[:-1]); mr = np.ones((len(rc), len(zm))); mz = np.ones_like(mr)
    inz = (zm > (zc - th / 2) * 1e-3) & (zm < (zc + th / 2) * 1e-3)
    for r0, r1, w in segs:
        m = (rc > r0 * 1e-3) & (rc < r1 * 1e-3); f = np.minimum(1.0, N * w * 1e-3 / (2 * math.pi * rc[m]))
        Lsp = max(b for _, b, _ in segs) - min(a for a, _, _ in segs); mu_s = Lsp / (Lsp / MU + gap) if gap > 0 else MU
        par = f * mu_s + (1 - f); har = 1.0 / (f / MU + (1 - f)); par_z = f * MU + (1 - f)
        mr[np.ix_(m, inz)] = par[:, None]; mz[np.ix_(m, inz)] = (par_z if bound == "upper" else har)[:, None]
    return mr, mz

def Bmax_in(psi, mr):
    """largest |B| (T) in the ferrite cells (cell-centred gradients of psi)"""
    dr = np.diff(R)[:, None]; dz = np.diff(Z)[None, :]; rc = 0.5 * (R[1:] + R[:-1])[:, None]
    dpr = 0.5 * ((psi[1:, 1:] - psi[:-1, 1:]) + (psi[1:, :-1] - psi[:-1, :-1])) / dr; dpz = 0.5 * ((psi[1:, 1:] - psi[1:, :-1]) + (psi[:-1, 1:] - psi[:-1, :-1])) / dz
    B = np.hypot(dpr / rc, dpz / rc); return float(B[mr > 1.5].max()) if (mr > 1.5).any() else 0.0

def Bz_row(psi, depth, radii):
    """B_z = (1/r) dpsi/dr at depth (m) for the given radii (m)"""
    j = np.searchsorted(Z, -depth); w = (-depth - Z[j - 1]) / (Z[j] - Z[j - 1]); col = psi[:, j - 1] * (1 - w) + psi[:, j] * w
    g = np.gradient(col, R); return np.array([np.interp(x, R[1:], g[1:] / R[1:]) for x in radii])

def spoke_width(N, r0, r1, gap=1.7):
    """widest straight tile r0..r1 that keeps `gap` to the neighbouring spoke (same bisection as the hood generators)"""
    def sat(A, B):
        best = -1e9
        for Q in (A, B):
            for i in range(4):
                e = Q[(i + 1) % 4] - Q[i]; n = np.array([-e[1], e[0]]) / np.linalg.norm(e); a = A @ n; b = B @ n; best = max(best, max(b.min() - a.max(), a.min() - b.max()))
        return best
    def rect(cx, cy, t, hl, hw): c, s_ = math.cos(t), math.sin(t); return np.array([(cx + x * c - y * s_, cy + x * s_ + y * c) for x, y in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))])
    lo, hi = 4.0, 200.0; rm = (r0 + r1) / 2; th = 2 * math.pi / N
    for _ in range(50):
        w = (lo + hi) / 2
        if sat(rect(rm, 0, 0, (r1 - r0) / 2, w / 2), rect(rm * math.cos(th), rm * math.sin(th), th, (r1 - r0) / 2, w / 2)) >= gap: lo = w
        else: hi = w
    return math.floor(lo * 10) / 10

if __name__ == "__main__":
    t0 = time.time(); rg = rings(); nturns = len(rg); one = np.ones((len(R) - 1, len(Z) - 1))
    DEP = np.array([50, 100, 150, 200, 300, 400, 500]) * 1e-3
    psi0 = solve(one, one, rg); B0 = Bz_axis(psi0, DEP)
    ref = dict(zip([50, 100, 150, 200, 300, 400, 500], [1135.8, 491.2, 231.2, 122.0, 44.4, 20.4, 11.0]))   # Biot-Savart on the real paths (sim_head1.json, uT at 20 A)
    val = {int(d * 1e3): dict(axi_uT=round(b * 1e6, 1), biot_savart_uT=ref[int(d * 1e3)], dev_pct=round(100 * (b * 1e6 / ref[int(d * 1e3)] - 1), 2)) for d, b in zip(DEP, B0)}
    print("rings", nturns, "grid", len(R), "x", len(Z), "validation (no hood):", val, round(time.time() - t0, 1), "s", flush=True)
    ZC, TH = 31.65, 2.5                                                    # hood v2 tile layer (hood_v19.py: carrier z29.4-33.4, tiles 2.5 mm)
    V = {"v2 as built: 13 spokes, tiles r57-84 (26.2 wide) + r86-112.5 (40.5 wide)": (13, [(57.0, 84.0, 26.2), (86.0, 112.5, 40.5)], ZC, TH),
         "21 spokes (Fibonacci), same radii, width for 1.79 mm gaps": (21, [(57.0, 84.0, 15.1), (86.0, 112.5, 24.6)], ZC, TH),
         "13 spokes, one tile r57-112.5 (no 2 mm radial gap)": (13, [(57.0, 112.5, 26.2)], ZC, TH),
         "13 spokes, tiles 5 mm thick": (13, [(57.0, 84.0, 26.2), (86.0, 112.5, 40.5)], ZC + 1.25, 5.0),
         "13 spokes, extended outward to r116 (outer tile 86-116)": (13, [(57.0, 84.0, 26.2), (86.0, 116.0, 40.5)], ZC, TH),
         "continuous MnZn annulus r52.6-116.1, 2.5 mm (upper limit)": (1, [(52.6, 116.1, 1e6)], ZC, TH)}
    for g in (2.0, 1.0, 0.5, 0.2, 0.1):                                    # radial gap between butted inner/outer tiles, as a series reluctance (2.0 = v2 cross-check)
        V[("v3 (hood_v20.py): " if g == 0.2 else "") + f"13 spokes, butted tiles, radial gap {g} mm (series model)"] = (13, [(57.0, 84.0, 26.2), (84.0, 112.5, spoke_width(13, 84.0 + g, 112.5))], ZC, TH, g)
    res = dict(validation_no_hood=val, rings=nturns, grid=[len(R), len(Z)], assumptions=dict(mu=MU, I_A=I_TX, homogenisation="Wiener bounds, straight tiles, fill N w / 2 pi r", losses="none (DC)"), variants={})
    keep = {}
    for nm, spec in V.items():
        N, segs, zc, th = spec[:4]; gap = spec[4] if len(spec) > 4 else 0.0
        row = {}
        for bd in ("upper", "lower"):
            mr, mz = hood_cells(N, segs, zc, th, bd, gap); psi = solve(mr, mz, rg); Bh = Bz_axis(psi, DEP)
            row[bd] = {int(d * 1e3): round(100 * (bh / b0 - 1), 2) for d, bh, b0 in zip(DEP, Bh, B0)}
            if bd == "upper": keep[nm] = psi
        area = sum(N * min(w, 2 * math.pi * (r0 + r1) / 2 / N) * (r1 - r0) for r0, r1, w in segs) if N > 1 else math.pi * (116.1 ** 2 - 52.6 ** 2)
        row["mass_g"] = round(area * th * 4.8e-3); row["Bmax_in_tiles_mT_at_20A"] = round(Bmax_in(keep[nm], hood_cells(N, segs, zc, th, "upper", gap)[0]) * 1e3, 1); row["gain_pct_at_200_per_100g_upper"] = round(row["upper"][200] / row["mass_g"] * 100, 2)
        res["variants"][nm] = row; print(nm, row, round(time.time() - t0, 1), "s", flush=True)
    # footprint: B_z across the search area at 100 and 200 mm depth, without hood, v2 and v3 (upper bound)
    v3 = next(k for k in keep if k.startswith("v3")); rad = np.array([0, 25, 50, 75, 100, 150, 200, 250]) * 1e-3
    res["footprint_uT_at_20A"] = {f"{int(d*1e3)} mm": {nm: [round(float(x) * 1e6, 1) for x in Bz_row(ps, d, rad)] for nm, ps in (("no hood", psi0), ("v2", keep[list(V)[0]]), ("v3", keep[v3]))} | {"radius_mm": [int(x * 1e3) for x in rad]} for d in (0.1, 0.2)}
    print("footprint", res["footprint_uT_at_20A"])
    json.dump(res, open("kit_v22/hood_axi.json", "w"), indent=1)
    # figure: field lines (psi contours) without and with the v2 hood, and gain vs depth for each variant (bounds as a band)
    fig, ax = plt.subplots(1, 2, figsize=(14, 6)); ir = R <= 0.30; jz = (Z > -0.35) & (Z < 0.12); RR, ZZ = np.meshgrid(R[ir] * 1e3, Z[jz] * 1e3, indexing="ij")
    lv = np.linspace(-1, 1, 41) ** 3 * np.abs(psi0[ir][:, jz]).max()
    ax[0].contour(RR, ZZ, psi0[ir][:, jz], levels=lv, colors="#888", linewidths=0.6)
    ax[0].contour(RR, ZZ, keep[v3][ir][:, jz], levels=lv, colors="#d33", linewidths=0.6)
    ax[0].add_patch(plt.Rectangle((57, ZC - TH / 2), 55.5, TH, color="k")); ax[0].add_patch(plt.Rectangle((62, 3.2), 47.6, 25.6, fc="none", ec="#36c"))
    ax[0].set_aspect(1); ax[0].set_xlabel("r (mm)"); ax[0].set_ylabel("z (mm), 0 = underside of the base plate"); ax[0].set_title("Field lines (psi contours, 20 A): grey no hood, red hood v3 (butted tiles). Blue box = coil, black = tiles", fontsize=9)
    for nm, row in res["variants"].items():
        if "series model" in nm and not nm.startswith("v3") and "2.0" not in nm: continue
        d = sorted(row["upper"]); ax[1].fill_between(d, [row["lower"][x] for x in d], [row["upper"][x] for x in d], alpha=0.25); ax[1].plot(d, [row["upper"][x] for x in d], "o-", ms=3, label=f'{nm[:48]} ({row["mass_g"]} g)')
    ax[1].set_xlabel("depth below the head on the axis (mm)"); ax[1].set_ylabel("field gain vs no hood (%)"); ax[1].set_title("Hood gain on the axis (modeled; band = Wiener bounds)", fontsize=10); ax[1].legend(fontsize=7); ax[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("kit_v22/HOOD_AXI.png", dpi=90); print("done", round(time.time() - t0, 1), "s")
