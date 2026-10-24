#!/usr/bin/env python3
"""MRI-style target-field / stream-function design of the TX turn distribution, compared with the as-built Fermat petal winding.

Method (as in MRI gradient-coil design: field targets + an energy penalty, then the stream function gives the winding):
 1. The as-built winding (kit_v15/LOW/paths.pkl, 6 layers x 2 arms x 8 turns, petal ripple) is reduced to its axisymmetric equivalent loops
    (one loop per turn, radius from the enclosed area). Validated against the real-path axis field of sim_head1 and the 54 uH coil.
 2. Same winding band (r 62.0-109.6 on every former), the same distribution on all six layers (keeps the parallel current sharing),
    two arms at the same radii as built (8 turns each, interleaved), pitch per arm >= 4.8 mm: the as-built outer pitch per arm is 4.87 mm,
    so the grooves of the two arms stay 2.4 mm apart (groove top 1.5 mm). Unknown: turns per 0.5 mm radial bin, n(r) >= 0.
 3. Design A: the least stored energy (inductance at 20 A) that keeps the B_z of the as-built coil at the target points
    (axis 150 / 200 / 300 mm, and 50 / 100 mm off-axis at 200 mm). Design B: design A run at the current that restores the as-built stored
    energy (more field). Design C: least energy for the as-built field at 300 / 400 mm on the axis and 100 mm off-axis at 300 mm (deep targets).
 4. Stream function psi(r) = cumulative turns; the discrete turns sit where psi crosses (k - 1/2): that is the new spiral rho(t) for the
    unchanged two-arm petal former generator.
 5. Each design goes through sim_head1.pulse (TX turn-off, 100 nF film clamp, 330 ohm chain and 500 pF held: ASSUMPTIONS 28) and the
    first clean gate of sbq_damp2 (worst real leak), and the depth model of config_study.py.
Axisymmetric: the 12-fold petal ripple (2.4 mm) is kept in the drawings but not in the field model (it averages out at depth)."""
import json, math, pickle, numpy as np
from scipy.special import ellipk, ellipe
from scipy.optimize import minimize, Bounds, LinearConstraint
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
MU0 = 4e-7 * math.pi; I_TX = 20.0; NL = 6; R0, R1 = 62.0, 116.5 - 4.5 - 2.4; P_MIN = 4.8; WIRE_R = 0.6; DR = 0.5
PN, G, ZRX = 3.6, 0.8, 3.2; ZL = np.array([ZRX + (6 - k) * (PN + G) + PN - 0.7 for k in range(1, 7)])          # layer heights (sim_head1 S2)
P = pickle.load(open("kit_v15/LOW/paths.pkl", "rb"))
# ------------------------------------------------------------------ 1 as-built equivalent loops (per layer; all layers equal within 0.01 mm)
def eq_radii(k):
    out = []
    for arm in (P[k][0], P[k][1]):
        th = np.unwrap(np.arctan2(arm[:, 1], arm[:, 0])); th = th if th[-1] > th[0] else -th; n = int(round((th[-1] - th[0]) / (2 * np.pi)))
        for j in range(n):
            m = (th >= th[0] + 2 * np.pi * j) & (th <= th[0] + 2 * np.pi * (j + 1)); x, y = arm[m, 0], arm[m, 1]
            out.append(math.sqrt(abs(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) / math.pi))
    return np.sort(np.array(out))
R_AS = eq_radii(1); assert all(np.allclose(np.sort(eq_radii(k)), R_AS, atol=0.05) for k in range(2, 7))
# ------------------------------------------------------------------ coaxial-loop kernels (mm in, SI out)
def Mloop(a, b, d):
    a, b, d = np.asarray(a, float) * 1e-3, np.asarray(b, float) * 1e-3, np.asarray(d, float) * 1e-3
    m = np.clip(4 * a * b / ((a + b) ** 2 + d ** 2), 0, 1 - 1e-12); k = np.sqrt(m)
    return MU0 * np.sqrt(a * b) * ((2 / k - k) * ellipk(m) - 2 / k * ellipe(m))
def Lself(a): a_ = a * 1e-3; return MU0 * a_ * (math.log(8 * a / WIRE_R) - 1.75)
def Bz(a, rho, z):
    """B_z per ampere of a loop radius a (mm) at radius rho, axial distance z (mm)"""
    a, rho, z = a * 1e-3, rho * 1e-3, z * 1e-3
    if rho < 1e-9: return MU0 * a ** 2 / (2 * (a ** 2 + z ** 2) ** 1.5)
    m = 4 * a * rho / ((a + rho) ** 2 + z ** 2)
    return MU0 / (2 * math.pi) / math.sqrt((a + rho) ** 2 + z ** 2) * (ellipk(m) + (a ** 2 - rho ** 2 - z ** 2) / ((a - rho) ** 2 + z ** 2) * ellipe(m))
def arm_radii(r):
    """radii of one arm: the two arms share each radius (as built they differ by about 0.01 mm), so group radii closer than 1 mm"""
    r = np.sort(np.asarray(r, float)); out = [[r[0]]]
    for x in r[1:]:
        if x - out[-1][-1] < 1.0: out[-1].append(x)
        else: out.append([x])
    return np.array([np.mean(g) for g in out])
def coil_L(radii_w):
    """terminal inductance of six identical layers in parallel (each layer carries I/6). Same-layer turns closer than one wire diameter
    (the two crossing arms) are coupled at a one-diameter separation; each turn's own term is the self-inductance."""
    r = np.asarray(radii_w[0], float); w = np.asarray(radii_w[1], float); tot = 0.0; A, B = np.meshgrid(r, r, indexing="ij")
    for zl in ZL:
        for zm in ZL:
            if zl != zm: Mm = Mloop(A, B, abs(zl - zm))
            else: Mm = Mloop(A, B, np.where(np.abs(A - B) < 2 * WIRE_R, 2 * WIRE_R, 0.0)); np.fill_diagonal(Mm, [Lself(x) for x in r])
            tot += w @ Mm @ w
    return tot / NL ** 2
TARGETS = [(0.0, 150.0), (0.0, 200.0), (0.0, 300.0), (50.0, 200.0), (100.0, 200.0)]
def field(radii_w, pts=TARGETS):
    r, w = radii_w; return np.array([sum(w[i] * Bz(r[i], rho, d + zl) for i in range(len(r)) for zl in ZL) / NL * I_TX for rho, d in pts])   # tesla at 20 A
# validation against the real paths (sim_head1: axis field at 20 A) and the 54 uH coil
S1 = json.load(open("kit_v20/sim_head1.json")); ax_real = S1["axis_field_uT_at_20A"]
AS = (R_AS, np.ones(len(R_AS)))
val = {d: dict(eq_uT=round(field(AS, [(0.0, float(d))])[0] * 1e6, 1), real_path_uT=ax_real[f"{d}mm"]) for d in (50, 100, 150, 200, 300)}
for d, v in val.items(): v["dev_pct"] = round(100 * (v["eq_uT"] / v["real_path_uT"] - 1), 2)
L_AS = coil_L(AS)
# ------------------------------------------------------------------ 2-3 target-field design A (least energy at the as-built field), design B (as-built energy)
RB = np.arange(R0 + DR / 2, R1, DR); CAP = 2 * DR / P_MIN                                   # two arms share each radius
Kbin = np.zeros((len(RB), len(RB)))
for zl in ZL:
    for zm in ZL:
        A_, B_ = np.meshgrid(RB, RB, indexing="ij")
        if zl != zm: Mm = Mloop(A_, B_, abs(zl - zm))
        else: Mm = Mloop(A_, B_, np.where(np.abs(A_ - B_) < 2 * WIRE_R, 2 * WIRE_R, 0.0)); np.fill_diagonal(Mm, [Lself(x) for x in RB])
        Kbin += Mm
Kbin /= NL ** 2
# feasible start: the as-built winding as a smooth density (stream function interpolated between the turn radii, differentiated on the bins)
_edges = np.concatenate([[R0], RB + DR / 2]); _psi = np.interp(_edges, np.concatenate([[R0], R_AS, [R1]]), np.concatenate([[0.0], np.arange(len(R_AS)) + 0.5, [len(R_AS)]]))
X0 = np.minimum(np.diff(_psi), CAP)
def design(pts):
    """convex QP: least stored energy n'Kn subject to B_z(n) >= the as-built field at pts, 0 <= n <= CAP (trust-constr, started feasible)"""
    Ab = np.array([[sum(Bz(r, rho, d + zl) for zl in ZL) / NL * I_TX for r in RB] for rho, d in pts]) * 1e6; b = field(AS, pts) * 1e6; Ks = Kbin * 1e6
    res = minimize(lambda n: n @ Ks @ n, X0, jac=lambda n: 2 * Ks @ n, hess=lambda n: 2 * Ks, method="trust-constr", bounds=Bounds(np.zeros(len(RB)), np.full(len(RB), CAP)),
                   constraints=[LinearConstraint(Ab, b, np.inf)], options=dict(maxiter=3000, gtol=1e-10, xtol=1e-12))
    res.field_ratio = (Ab @ res.x) / b
    return res
def discretise(n):
    """stream function per arm: psi(r) = turns inside r; arm turns sit at psi = k - 1/2; both arms use the same radii (as built)"""
    psi = np.concatenate([[0.0], np.cumsum(n)]) / 2.0; edges = np.concatenate([[R0], RB + DR / 2]); Na = int(round(psi[-1]))
    psi = psi * Na / psi[-1]; ra = np.interp(np.arange(Na) + 0.5, psi, edges); return np.sort(np.concatenate([ra, ra])), ra
resA = design(TARGETS); print('A', resA.message, round(resA.fun, 2), resA.field_ratio.round(4)); rA, armA = discretise(resA.x); DA = (rA, np.ones(len(rA))); L_A = coil_L(DA)
DEEP = [(0.0, 300.0), (0.0, 400.0), (100.0, 300.0)]
resC = design(DEEP); print('C', resC.message, round(resC.fun, 2), resC.field_ratio.round(4)); rC, armC = discretise(resC.x); DC = (rC, np.ones(len(rC))); L_C = coil_L(DC)
b0 = field(AS)
I_B = I_TX * math.sqrt(L_AS / L_A)                                                                        # design B: A at the as-built stored energy
# ------------------------------------------------------------------ 5 turn-off, first gate, depth (repo models)
src = open("sim_head1.py").read(); M = {}; exec(src.split("# ======================= S2")[0], M)
def tx(L, I=I_TX):
    L0 = M["L"]; M["L"] = L; r, w = M["pulse"](I, 100e-9); M["L"] = L0; return r, w
import sbq_damp2 as SD
LEAK = json.load(open("kit_v22/sbq_sim.json"))["leak"]; WORST = max(v["peak_V"] for bd in LEAK.values() for k, v in bd.items() if "lobes only" not in k)
T0, G0 = SD.t.copy(), SD.g.copy(); DI0 = np.max(np.abs(np.gradient(SD.wf["100 nF C0G/film"][1], T0)))
def gate(L, couple, I=I_TX):
    r, (t, i, vd, vc) = tx(L, I); g = np.gradient(i, t); SD.t, SD.g = t, g / np.max(np.abs(g)); tf, _ = SD.first_clean(WORST * couple * np.max(np.abs(g)) / DI0, 680, 100e-12, 0.0); SD.t, SD.g = T0, G0
    return round(tf, 2), r
rows = {}
for nm, D, L, I in (("as built (Fermat petal, 16 turns/layer)", AS, L_AS, I_TX), ("A: target field, least energy at the as-built field", DA, L_A, I_TX),
                   (f"B: design A at {I_B:.1f} A (as-built stored energy, more field)", DA, L_A, I_B), ("C: target field for deep targets (300-400 mm)", DC, L_C, I_TX)):
    f = field(D) * I / I_TX; turns = len(D[0]); couple = (turns / 16.0) * I / I_TX                       # receive leak scales with the TX ampere-turns (same geometry otherwise)
    tf, r = gate(L, couple, I)
    rows[nm] = dict(turns_per_layer=turns, peak_A=round(I, 2), L_uH=round(L * 1e6, 2), energy_mJ=round(0.5 * L * I ** 2 * 1e3, 2), Bz_uT_at_20A={f"r{int(p[0])} z{int(p[1])}": round(x * 1e6, 1) for p, x in zip(TARGETS, f)},
                    field_ratio_vs_as_built={f"r{int(p[0])} z{int(p[1])}": round(x / y, 4) for p, x, y in zip(TARGETS, f, b0)}, tx_zero_us=round(r["t_zero_us"], 2), tx_quiet_us=round(r["t_quiet_us"], 2),
                    Vds_peak_V=round(r["Vds_peak"], 1), clamp_W_400Hz=round(r["P_RCL_W"], 2), first_clean_gate_worst_us=tf,
                    copper_m=round(sum(2 * math.pi * x for x in D[0]) * NL / 1000, 2), min_pitch_per_arm_mm=round(float(np.diff(arm_radii(D[0])).min()), 2), arm_radii_mm=[round(float(x), 2) for x in arm_radii(D[0])])
# depth (config_study model: idealised quad x 3.2, worst leak gate, gain = field ratio at 200 mm on the axis)
M2 = {}; exec(src.split("latx=np.array")[0], M2); exec("latx=np.array([-150,-100,-60,-30,0,30,60,100,150])*1e-3; grid=np.array([[x,y] for x in latx for y in latx])", M2)
exec(src[src.index("def depth_for("):src.index("scen=")], M2)
ND = json.load(open("kit_v22/sbq_damping2.json"))["gate_noise_nV_rtHz"]["Cself 100 pF, gate at 6 us"]["Rd 680"] * 1e-9
for nm, r_ in rows.items():
    g200 = r_["field_ratio_vs_as_built"]["r0 z200"]; r_["depth_mm_worst_leak"] = {f"{m} g": M2["depth_for"](m, ND, 100, 3.2 * g200, "QUAD", M2["quad"], r_["first_clean_gate_worst_us"] * 1e-6) for m in (0.1, 1.0, 5.0)}
out = dict(method=__doc__.split("\n\n")[0], validation=dict(axis_field=val, L_equivalent_uH=round(L_AS * 1e6, 2), L_repo_uH=54.0, as_built_radii_mm=[round(float(x), 2) for x in R_AS]),
           band_mm=[R0, R1], pitch_min_mm=P_MIN, optimiser=dict(A=str(resA.message), C=str(resC.message)), designs=rows)
json.dump(out, open("kit_v23/target_field.json", "w"), indent=1, default=float)
for k, v in rows.items(): print(k, {x: v[x] for x in ("turns_per_layer", "peak_A", "L_uH", "energy_mJ", "tx_zero_us", "tx_quiet_us", "clamp_W_400Hz", "first_clean_gate_worst_us", "copper_m", "min_pitch_per_arm_mm", "depth_mm_worst_leak")}, v["field_ratio_vs_as_built"])
print("validation", val, "L eq", round(L_AS * 1e6, 2))

# ------------------------------------------------------------------ figures
A_RIP, M_PET, GOLD = 2.4, 12, 137.50776405
def petal_path(radii, alpha=0.0):
    """two-arm petal spiral through the given turn radii (arm A out on even turns, arm B in on odd), with the 12-fold ripple"""
    r = np.sort(radii); ra, rb = r[0::2], r[1::2][::-1]
    def arm(rs, th0, sgn):
        t = np.linspace(0, 1, 1600); rr = np.interp(t * len(rs), np.arange(len(rs)) + 0.5, rs); th = th0 + sgn * 2 * np.pi * len(rs) * t
        rr = rr + A_RIP * (rr / R1) ** 2 * np.cos(M_PET * (th - alpha)); return rr * np.cos(th), rr * np.sin(th)
    xa, ya = arm(ra, alpha + math.radians(6), 1); xb, yb = arm(rb, alpha + math.radians(11), 1); return (xa, ya), (xb, yb)
cols = {"as built": "#333333", "A": "#c0392b", "B": "#e59866", "C": "#2c6fbb"}
fig = plt.figure(figsize=(18, 11)); gs = fig.add_gridspec(2, 3)
for j, (nm, D, c1, c2) in enumerate((("as built: Fermat petal, %d turns" % len(AS[0]), AS, "#333", "#888"), ("A: target field, least energy, %d turns" % len(DA[0]), DA, "#c0392b", "#e59866"),
                                     ("C: target field, deep targets, %d turns" % len(DC[0]), DC, "#2c6fbb", "#85c1e9"))):
    ax = fig.add_subplot(gs[0, j])
    if j == 0:
        for arm, c in ((P[1][0], c1), (P[1][1], c2)): ax.plot(arm[:, 0], arm[:, 1], color=c, lw=0.7)
    else:
        for (x, y), c in zip(petal_path(D[0]), (c1, c2)): ax.plot(x, y, color=c, lw=0.7)
    th = np.linspace(0, 2 * np.pi, 300)
    for rr in (49.5, R0, R1 + A_RIP, 116.5): ax.plot(rr * np.cos(th), rr * np.sin(th), ":", color="#999", lw=0.6)
    ax.set_aspect(1); ax.set_xlim(-120, 120); ax.set_ylim(-120, 120); ax.set_title(f"layer L1 plan view, {nm}\nband r{R0}-{R1} + 2.4 ripple; hub r49.5, rim r116.5; arm A dark, arm B light", fontsize=9)
ax = fig.add_subplot(gs[1, 0])
for nm, D, c in (("as built", AS, cols["as built"]), ("A", DA, cols["A"]), ("C deep", DC, cols["C"])):
    r = arm_radii(D[0]); ax.step(np.r_[R0, r, R1], np.r_[0, np.arange(1, len(r) + 1), len(r)], where="post", color=c, label=f"{nm}: {len(r)} turns per arm")
    ax.plot(r, np.arange(1, len(r) + 1) - 0.5, "o", ms=3, color=c)
ax.set_xlabel("radius (mm)"); ax.set_ylabel("stream function psi(r) = arm turns inside r"); ax.set_title("stream function per arm: the turns sit where psi = k - 1/2 (dots)", fontsize=9); ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax = fig.add_subplot(gs[1, 1]); dz = np.array([50, 75, 100, 150, 200, 250, 300, 400, 500.0]); ref = np.array([field(AS, [(0.0, d)])[0] for d in dz])
for nm, D, c, I in (("as built", AS, cols["as built"], I_TX), ("A (20 A)", DA, cols["A"], I_TX), (f"B = A at {I_B:.1f} A (same energy)", DA, cols["B"], I_B), ("C deep (20 A)", DC, cols["C"], I_TX)):
    ax.plot(dz, [field(D, [(0.0, d)])[0] * I / I_TX / r_ for d, r_ in zip(dz, ref)], "o-", color=c, ms=3, label=nm)
ax.axhline(1.0, color="#999", lw=0.6); ax.set_xlabel("depth below the base plate on the axis (mm)"); ax.set_ylabel("B_z / as-built B_z"); ax.set_title("axis field relative to the as-built coil", fontsize=9); ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax = fig.add_subplot(gs[1, 2]); ax.axis("off")
txt = [f"validation: equivalent loops vs real paths, axis field {min(v['dev_pct'] for v in val.values()):+.2f} .. {max(v['dev_pct'] for v in val.values()):+.2f} %; L {L_AS*1e6:.1f} uH (repo 54)", ""]
for k, v in rows.items():
    txt += [k, f"  {v['turns_per_layer']} turns/layer, {v['peak_A']} A, L {v['L_uH']} uH, {v['energy_mJ']} mJ, copper {v['copper_m']} m, pitch/arm >= {v['min_pitch_per_arm_mm']} mm",
            f"  field at 200 mm x{v['field_ratio_vs_as_built']['r0 z200']}, TX quiet {v['tx_quiet_us']} us, clamp {v['clamp_W_400Hz']} W, Vds {v['Vds_peak_V']} V",
            f"  first clean gate {v['first_clean_gate_worst_us']} us; depth 0.1/1/5 g {'/'.join(str(x) for x in v['depth_mm_worst_leak'].values())} mm", ""]
txt += ["all modeled: axisymmetric equivalent of the six formers, free air, no ground,", "no hood; TX chain 330 ohm / 500 pF held (ASSUMPTIONS 28)"]
ax.text(0, 1, "\n".join(txt), va="top", fontsize=8.2, family="monospace")
fig.suptitle("TX winding: as-built Fermat petal spiral vs MRI-style target-field / stream-function design (same band, same six formers, same petal ripple and golden-angle phase)", fontsize=12)
fig.tight_layout(); fig.savefig("kit_v23/TARGET_FIELD_WINDING.png", dpi=80)
# 3D stack of the six layers, both designs (golden-angle rotation as on the formers)
fig = plt.figure(figsize=(18, 8))
for j, (nm, D) in enumerate((("as built", AS), ("target field A (least energy)", DA))):
    ax = fig.add_subplot(1, 2, j + 1, projection="3d")
    for k in range(1, 7):
        al = math.radians(GOLD * (k - 1)); z = ZL[k - 1]
        if j == 0:
            for arm, c in ((P[k][0], "#333"), (P[k][1], "#888")): ax.plot(arm[:, 0], arm[:, 1], np.full(len(arm), z), color=c, lw=0.5)
        else:
            for (x, y), c in zip(petal_path(D[0], al), ("#c0392b", "#e59866")): ax.plot(x, y, np.full(len(x), z), color=c, lw=0.5)
        th = np.linspace(0, 2 * np.pi, 200); ax.plot(49.5 * np.cos(th), 49.5 * np.sin(th), np.full(200, z), color="#6a9", lw=0.6)
    ax.set_box_aspect((1, 1, 0.35)); ax.view_init(28, -60); ax.set_title(f"six layers, {nm}: {len(D[0])} turns per layer, golden-angle phase", fontsize=10)
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
fig.tight_layout(); fig.savefig("kit_v23/TARGET_FIELD_LAYERS_3D.png", dpi=80)
