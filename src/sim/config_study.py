#!/usr/bin/env python3
"""System configuration study (head + upper assembly v1), built only from the repo's own models:
 - first clean gate: sbq_damp2.first_clean (real AB1T input network, RD, Cself) driven by the TX current waveform of sim_head1.pulse()
 - noise-limited depth: sim_head1.depth_for (idealised quadrupole receive rings scaled by the 3.2 x real-pattern signal, gated noise of sbq_damping2.json, 20 A ampere-turns)
 - hood gain at 200 mm: hood_axi.json (TX field only, the conservative choice)
 - upper-assembly mass and centroids: measured on the kit_v23/UPPER meshes, and on a light variant regenerated with thinner walls
 - static torque about the grip: the reach-matched model of upper_check.py (head side from shaft_calc_v20.json)
 - runtime: pack energy / system power (system_budget.py)
Depths are reported relative to C0 with the same model; absolute values inherit ASSUMPTIONS 5, 7, 13 (idealised quadrupole, free air, no ground).
Cell, cord and part figures are ASSUMPTIONS 24-28."""
import os, json, math, struct, subprocess, sys, numpy as np
OUT = "kit_v23"; os.makedirs(OUT, exist_ok=True)
# ------------------------------------------------------------------ models
src = open("sim_head1.py").read(); M = {}; exec(src.split("latx=np.array")[0], M)
exec("latx=np.array([-150,-100,-60,-30,0,30,60,100,150])*1e-3; grid=np.array([[x,y] for x in latx for y in latx])", M)
exec(src[src.index("def depth_for("):src.index("scen=")], M)
import sbq_damp2 as SD
DMP = json.load(open("kit_v22/sbq_damping2.json")); LEAK = json.load(open("kit_v22/sbq_sim.json"))["leak"]
WORST = max(v["peak_V"] for bd in LEAK.values() for k, v in bd.items() if "lobes only" not in k); ALIGNED = LEAK["QUAD-A board"]["aligned"]["peak_V"]
ND = DMP["gate_noise_nV_rtHz"]["Cself 100 pF, gate at 6 us"]["Rd 680"] * 1e-9
HOOD = json.load(open("kit_v22/hood_axi.json"))["variants"]
def hood_gain(prefix): return 1.0 + next(v["lower"]["200"] for k, v in HOOD.items() if k.startswith(prefix)) / 100.0
T0, G0 = SD.t.copy(), SD.g.copy(); i0 = SD.wf["100 nF C0G/film"][1]; DI0 = np.max(np.abs(np.gradient(i0, T0)))
def waveform(turns):
    """TX current for a turns factor at constant ampere-turns (sim_head1.pulse with L x n^2, I / n; Cself 500 pF, 330 ohm chain held, ASSUMPTIONS 28)"""
    L0 = M["L"]; M["L"] = 54e-6 * turns ** 2; r, (t, i, vd, vc) = M["pulse"](20.0 / turns, 100e-9); M["L"] = L0
    g = np.gradient(i, t); scale = turns * np.max(np.abs(g)) / DI0                                    # receive emf ~ M (turns) x dI/dt
    return r, t, g / np.max(np.abs(g)), scale
def first_gate(turns=1.0, leak=WORST, rd=680, cs=100e-12):
    r, t, g, scale = waveform(turns); SD.t, SD.g = t, g
    tf, _ = SD.first_clean(leak * scale, rd, cs, 0.0); SD.t, SD.g = T0, G0
    return round(tf, 2), round(r["t_quiet_us"], 2)
SIG_REAL = 3.2                                                                                       # real SB1R-Q copper vs the idealised quadrupole rings (DESIGN_STATE 6, sbq_sim.py)
def depths(tf_us, gain=1.0, N=100):
    """noise-limited depth with the real-pattern signal factor applied as in DESIGN_STATE 6 (ASSUMPTIONS 7)"""
    return {f"{m} g": M["depth_for"](m, ND, N, gain * SIG_REAL, "QUAD", M["quad"], tf_us * 1e-6) for m in (0.1, 1.0, 5.0)}

# ------------------------------------------------------------------ upper assembly: standard meshes and the light variant (measured)
def stl_tris(p):
    b = open(p, "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def vol_cent(T):
    a, b, c = T[:, 0], T[:, 1], T[:, 2]; v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0; return v.sum(), ((a + b + c) / 4.0 * v[:, None]).sum(0) / v.sum()
def upper_items(folder):
    rep = json.load(open(f"{folder}/upper_v21_report.json")); items = []
    for n, p in rep["parts"].items():
        if n.endswith("collapsed") or n.startswith("UPPER_"): continue
        v, c = vol_cent(stl_tris(f"{folder}/{n}.stl")); items.append((n, v / 1000.0 * p["mass_g"] / p["volume_cm3"] / 1000.0, c))
    return items, rep["params"]
env = dict(os.environ, UPPER_OUT=f"{OUT}/UPPER_light", UPPER_WALL="2.0", UPPER_DT="2.5")
subprocess.run([sys.executable, "upper_v21.py"], env=env, check=True, stdout=subprocess.DEVNULL)
UC = json.load(open(f"{OUT}/upper_check.json")); PURCH = [(i["item"], i["mass_g"] / 1000.0, np.array(i["at_mm"])) for i in UC["mass"]["items"] if i["source"] == "estimate"]
UP = {nm: upper_items(f) for nm, f in (("standard", f"{OUT}/UPPER"), ("light (walls 2.0, dock 2.5)", f"{OUT}/UPPER_light"))}
SC = json.load(open("kit_v19/shaft_calc_v20.json")); MH0 = SC["head_mass_kg"]["total"]; HP = SC["head_mass_kg"]["parts"]
NPMH, LOWER = 0.084, 0.40
PACKS = {"7S1P Molicel P30B (18650, as built)": dict(cells_g=7 * 47, Wh=7 * 3.6 * 3.0, shell_dg=0, dx=0.0, new_shell=False),
         "7S1P Molicel P42A (21700)": dict(cells_g=7 * 70, Wh=7 * 3.6 * 4.2, shell_dg=25, dx=-12.0, new_shell=True),
         "7S2P Molicel P30B (18650)": dict(cells_g=14 * 47, Wh=2 * 7 * 3.6 * 3.0, shell_dg=60, dx=0.0, new_shell=True)}
HOODS = {"v3 butted (as built)": dict(prefix="v3", tiles_g=286), "v4 one tile per spoke": dict(prefix="13 spokes, one tile", tiles_g=227), "no tiles (carrier only)": dict(prefix=None, tiles_g=0)}
P_SCAN, P_BOOST = 4.7, 7.7
def torque_mass(upper="standard", pack="7S1P Molicel P30B (18650, as built)", hood="v3 butted (as built)", alpha=47.0, pack_dx=0.0):
    items, prm = UP[upper]; pk = PACKS[pack]; hd = HOODS[hood]
    mh = MH0 - HP["ferrite tiles"] / 1000.0 + hd["tiles_g"] / 1000.0
    reach = SC["balance"]["head_horizontal_distance_m"]; a = math.radians(alpha); zt = prm["ZT"]
    b_work = ((reach - 0.154 - zt * math.sin(a) / 1000.0) / math.cos(a)) * 1000.0 - (NPMH + LOWER) * 1000.0
    wx = lambda p: (p[0] * math.cos(a) + p[2] * math.sin(a)) / 1000.0
    hinge = np.array([b_work + (NPMH + LOWER) * 1000.0, 0, zt]); bfront = prm["tube_B"]["extended"][1]
    t = (mh + 0.35) * (wx(hinge) + 0.154) + 0.55 * wx(np.array([b_work + NPMH * 500.0, 0, zt])) + 0.18 * wx(np.array([b_work + NPMH * 1000 + LOWER * 500.0, 0, zt]))
    m_up = 0.0
    for n, m, c in items + PURCH:
        c = np.array(c, float)
        if n.startswith("TUBE_B") or n.startswith("U8_SEPTUM"): c = c + np.array([b_work - bfront, 0, 0])
        is_pack = ("PACK" in n or "P30B" in n or "BMS" in n or "latch" in n or "nickel" in n)
        if "P30B" in n: m = pk["cells_g"] / 1000.0
        if "PACK_SHELL" in n: m = m + pk["shell_dg"] / 1000.0
        if is_pack: c = c + np.array([pk["dx"] + pack_dx, 0, 0])
        t += m * wx(c); m_up += m
    return round(t, 3), round(m_up, 3), round(mh + 0.35 + 0.55 + 0.18, 3)

# ------------------------------------------------------------------ candidate configurations
CFG = {
 "C0 as built (head v5, hood v3, upper v1, P30B 7S1P)": dict(turns=1.0, hood="v3 butted (as built)", upper="standard", pack="7S1P Molicel P30B (18650, as built)", N=100,
      changes=[]),
 "C1 light and balanced": dict(turns=1.0, hood="v4 one tile per spoke", upper="light (walls 2.0, dock 2.5)", pack="7S1P Molicel P30B (18650, as built)", N=100,
      changes=["hood carrier v4: one 55.5 mm tile per spoke (generator change, same carrier envelope)", "upper housings 2.0 mm walls, dock plate 2.5 mm (regenerated)",
               "PB1R bulk 35 V polymer Ta -> 50 V parts (29.4 V is 84 % of 35 V; about 80 % is the polymer-Ta guideline)", "firmware rules (constant-current ton, boost duty, BLANK policy, LED cap, TRIG boot rule)"]),
 "C2 early gate (12 turns per layer)": dict(turns=0.75, hood="v4 one tile per spoke", upper="light (walls 2.0, dock 2.5)", pack="7S1P Molicel P30B (18650, as built)", N=100,
      changes=["C1 changes", "six formers regenerated for 12 turns per layer (0.75 x), 26.7 A peak", "self-capacitance and damping chain re-derived for the new coil, then this study re-run",
               "PB1R: 26.7 A peak, 13.3 A per FET (44 % margin); shunt and OCP reference rescaled"]),
 "C3 endurance (P42A 21700 pack)": dict(turns=1.0, hood="v4 one tile per spoke", upper="light (walls 2.0, dock 2.5)", pack="7S1P Molicel P42A (21700)", N=100,
      changes=["C1 changes", "pack shell U7 regenerated for 7 x 21700 (21.7 x 70.2 mm) and the BMS bay; dock rails unchanged", "pack 0.16 kg heavier, behind the grip"]),
}
rows = {}
for nm, c in CFG.items():
    tf_al, tq = first_gate(c["turns"], ALIGNED); tf_w, _ = first_gate(c["turns"], WORST)
    gain = hood_gain(HOODS[c["hood"]]["prefix"]) if HOODS[c["hood"]]["prefix"] else 1.0
    tor, m_up, m_head = torque_mass(c["upper"], c["pack"], c["hood"])
    pk = PACKS[c["pack"]]
    rows[nm] = dict(first_gate_us=dict(aligned=tf_al, worst_leak=tf_w), tx_quiet_us=tq, hood_gain_200mm=round(gain, 4),
                    depth_mm_worst_leak=depths(tf_w, gain, c["N"]), depth_mm_aligned=depths(tf_al, gain, c["N"]),
                    mass_kg=dict(upper=m_up, head_neck_lower=m_head, total=round(m_up + m_head, 3)), torque_47deg_kg_m=tor,
                    runtime_h=dict(boost=round(pk["Wh"] / P_BOOST, 1), scan=round(pk["Wh"] / P_SCAN, 1)), peak_A=round(20.0 / c["turns"], 1),
                    fet_margin_pct=round(100 * (1 - (20.0 / c["turns"] / 2) / 24.0), 1), changes=c["changes"])
    print(nm, json.dumps({k: v for k, v in rows[nm].items() if k != "changes"}))
base = rows[next(iter(rows))]
for nm, r in rows.items():
    r["vs_C0"] = dict(depth_1g_worst_mm=r["depth_mm_worst_leak"]["1.0 g"] - base["depth_mm_worst_leak"]["1.0 g"], depth_0p1g_worst_mm=r["depth_mm_worst_leak"]["0.1 g"] - base["depth_mm_worst_leak"]["0.1 g"],
                      first_gate_worst_us=round(r["first_gate_us"]["worst_leak"] - base["first_gate_us"]["worst_leak"], 2), total_mass_g=round(1000 * (r["mass_kg"]["total"] - base["mass_kg"]["total"])),
                      torque_kg_m=round(r["torque_47deg_kg_m"] - base["torque_47deg_kg_m"], 3), boost_runtime_h=round(r["runtime_h"]["boost"] - base["runtime_h"]["boost"], 1))

# ------------------------------------------------------------------ sweeps and research items with a number behind them
sweeps = dict(
    torque_vs_shaft_angle={a: torque_mass(alpha=a)[0] for a in (40, 45, 47, 50, 55)},
    torque_vs_pack_shift_rearward_mm={d: torque_mass(pack_dx=-d)[0] for d in (0, 50, 100, 150)},
    pack_options={k: dict(Wh=round(v["Wh"], 1), boost_h=round(v["Wh"] / P_BOOST, 1), cells_g=v["cells_g"], torque=torque_mass(pack=k)[0], new_shell=v["new_shell"]) for k, v in PACKS.items()},
    hood_options={k: dict(gain_200mm=round(hood_gain(v["prefix"]), 4) if v["prefix"] else 1.0, tiles_g=v["tiles_g"], torque=torque_mass(hood=k)[0],
                          depth_1g_worst=depths(first_gate(1.0, WORST)[0], hood_gain(v["prefix"]) if v["prefix"] else 1.0)["1.0 g"]) for k, v in HOODS.items()},
    first_gate_vs_turns={f"{n} x": dict(zip(("worst_leak_us", "tx_quiet_us"), first_gate(n, WORST))) for n in (0.5, 0.75, 1.0)},
    negative_capacitance_research={f"Cself {int(cs*1e12)} pF, RD {rd}": first_gate(1.0, WORST, rd, cs)[0] for cs, rd in ((100e-12, 680), (50e-12, 680), (50e-12, 1000))},
    averaging={f"N {n}": depths(first_gate(1.0, WORST)[0], hood_gain("v3"), n)["1.0 g"] for n in (100, 400)})
PRM = UP["standard"][1]; piv = PRM["pivot"]; pc = PRM["pad_centre"]; phi = 3.0 / abs(pc[2] - piv[2])
sweeps["trigger_tail_mm_vs_magnet_travel"] = {t: dict(travel_mm=round(phi * t, 2), fits_before_socket=(piv[0] + t + 2.5 <= PRM["tube_A"]["x"][0] - 2.0)) for t in (15, 18, 22, 25, 28)}
out = dict(configs=rows, sweeps=sweeps, model=dict(noise_nV_rtHz=round(ND * 1e9, 3), worst_leak_V=WORST, aligned_leak_V=ALIGNED, head_mass_v20_kg=MH0),
           notes="depth: idealised quadrupole x 3.2 real-pattern signal (DESIGN_STATE 6), free air, no ground, 100 pulses at 20 A ampere-turns; compare configurations with each other, not with field results")
json.dump(out, open(f"{OUT}/config_study.json", "w"), indent=1, default=float)
print(json.dumps(sweeps, default=float)[:3000])
# ------------------------------------------------------------------ one figure: the four configurations side by side (modeled)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
names = list(rows); short = [n.split(" ")[0] for n in names]; cols = ["#888888", "#2c6fbb", "#c0392b", "#27ae60"]
panels = [("depth 1 g, worst leak (mm)", lambda r: r["depth_mm_worst_leak"]["1.0 g"]), ("depth 0.1 g, worst leak (mm)", lambda r: r["depth_mm_worst_leak"]["0.1 g"]),
          ("first clean gate, worst leak (us)", lambda r: r["first_gate_us"]["worst_leak"]), ("total mass head + shaft + handle (kg)", lambda r: r["mass_kg"]["total"]),
          ("torque about the grip, 47 deg (kg m)", lambda r: r["torque_47deg_kg_m"]), ("boost runtime per pack (h)", lambda r: r["runtime_h"]["boost"])]
fig, axs = plt.subplots(2, 3, figsize=(15, 8))
for ax, (title, f) in zip(axs.ravel(), panels):
    v = [f(rows[n]) for n in names]; ax.bar(short, v, color=cols); ax.set_title(title, fontsize=10)
    lo, hi = min(v), max(v); ax.set_ylim(lo - (hi - lo + 1e-9) * 1.5 - 0.02 * abs(lo), hi + (hi - lo + 1e-9) * 0.6 + 0.02 * abs(hi))
    for k, x in enumerate(v): ax.text(k, x, f"{x}", ha="center", va="bottom", fontsize=9)
fig.suptitle("Configurations C0 (as built) .. C3, modeled with the repo's own models (config_study.py); depths: idealised quadrupole x 3.2, free air, no ground\n"
             + "  ".join(f"{s} = {n[3:]}" for s, n in zip(short, names)), fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/CONFIGURATIONS_v1.png", dpi=80)
