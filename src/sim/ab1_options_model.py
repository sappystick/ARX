#!/usr/bin/env python3
"""Receive-stage options model (MODELED, tool-measured; nothing built). Which hard-coded rules and which additions would make the receive boards (AB1A / AB1B) fit, route and perform better?
Parts (each writes its JSON before the next starts, so a failure never costs the earlier parts):
  room      radial room map from the CURRENT meshes: what lies outside the vault wall at each level (free ring between the core collar and the next solid), inner wall radius, board-to-wall gaps
  area      board-area utilisation of AB1A / AB1B (part bodies per side / disc area) for the board diameters considered
  layers    how much of each routing layer the committed AB1A / AB1B layouts use (extra layers only help if the existing ones are crowded)
  router    routing robustness: the committed layout is perturbed (seeded random 0.4 mm nudges of 6 parts) and routed at several fab tiers; success rate, tracks and vias are the capacity proxy
  noise     front-end noise and range model for the signal-chain options (datasheet numbers where cited, the rest labelled ASSUMED / UNVERIFIED)
  scenarios the options combined, scored for function (routing), fit (room), performance (noise) and risk
usage (repo root): python3 src/sim/ab1_options_model.py [room|area|layers|router|noise|scenarios|all] [--n N]      -> data/results/ab1_options_model.json"""
import os, sys, json, math, struct, random, subprocess, glob, time
import numpy as np
ROOT = os.getcwd(); OUTJ = "data/results/ab1_options_model.json"
def load():
    try: return json.load(open(OUTJ))
    except Exception: return {}
def save(k, v):
    d = load(); d[k] = v; os.makedirs(os.path.dirname(OUTJ), exist_ok=True); json.dump(d, open(OUTJ, "w"), indent=1, default=float)
def tris(p):
    b = open(p, "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def section_points(T, z):
    d = T[:, :, 2] - (z + 1.234e-4); m = (d.min(1) < 0) & (d.max(1) > 0); P = []
    for tri, dd in zip(T[m], d[m]):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if (dd[i] < 0) != (dd[j] < 0): P.append(tri[i] + dd[i] / (dd[i] - dd[j]) * (tri[j] - tri[i]))
    return np.array(P)

# ------------------------------------------------------------------ room
def room():
    out = {}; files = {os.path.basename(f)[:-4]: f for f in glob.glob("stl/head/*.stl") if "FERRITE" not in f}
    form = {f"FORMER_L{k}": f"work/kit_v15/LOW/FORMER_L{k}_petal_coil_former.stl" for k in range(1, 7)}
    off = lambda k: 3.2 + (6 - k) * 4.4
    solids = {n: tris(f) for n, f in files.items()}
    for n, f in form.items():
        if os.path.exists(f): T = tris(f); T[:, :, 2] += off(int(n[-1])); solids[n] = T
    core = solids["CORE_CYLINDER_v5_integrated"]
    rows = []
    for z in (6.0, 11.0, 16.0, 20.0, 24.0, 30.0, 36.0, 42.0):
        P = section_points(core, z)
        if len(P) == 0: continue
        r = np.hypot(P[:, 0], P[:, 1]); a = np.degrees(np.arctan2(P[:, 1], P[:, 0])) % 360; b = np.floor(a / 10).astype(int)
        mins = [r[b == k].min() for k in range(36) if (b == k).any()]; inner = float(np.median(mins)); outer = float(r[r < 70].max())
        near = {}
        for n, T in solids.items():
            if n == "CORE_CYLINDER_v5_integrated" or n == "HEAD_SKIRT": continue
            Q = section_points(T, z)
            if len(Q) == 0: continue
            rq = np.hypot(Q[:, 0], Q[:, 1]); rq = rq[rq > outer - 0.5]
            if len(rq): near[n] = round(float(rq.min()), 1)
        nxt = min(near.values()) if near else None
        rows.append(dict(z=z, inner_wall_r=round(inner, 1), comb_min_r=round(float(min(mins)), 1), core_outer_r=round(outer, 1), nearest_other_solid_r=nxt, free_ring_mm=None if nxt is None else round(nxt - outer, 1), nearest=sorted(near.items(), key=lambda t: t[1])[:3]))
    out["levels"] = rows
    out["winding_R0_mm"] = 62.0; out["hub_collar_r_mm"] = [49.5, 52.0]
    out["ab1_span_mm"] = 80.6; out["bore_mm"] = 2 * inner
    out["note"] = "free_ring_mm = distance from the core's outer radius to the next solid cut at that z (formers use the low-resolution print meshes at their assembly z); a ring of several mm means the vault wall could move outward without touching anything else, subject to the checks listed in docs/OPEN_ITEMS.md"
    save("room", out); return out

# ------------------------------------------------------------------ area
def area():
    sys.path.insert(0, "work"); os.chdir("work")
    res = {}
    try:
        for B in ("A", "B"):
            env = dict(os.environ, BOARD=B)
            code = "import afe_layout as A, json; "\
                   "tot={'F':0.0,'B':0.0}; "\
                   "[tot.__setitem__(A.PLACE[p['ref']][3], tot[A.PLACE[p['ref']][3]] + A.D.LIB[p['type']]['body'][0]*A.D.LIB[p['type']]['body'][1]) for p in A.D.PARTS if not A.D.LIB[p['type']].get('tht')]; "\
                   "print(json.dumps(dict(parts=len(A.D.PARTS), front_mm2=tot['F'], back_mm2=tot['B'])))"
            r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True); res[B] = json.loads(r.stdout.strip().splitlines()[-1])
    finally: os.chdir(ROOT)
    rows = []
    for D in (40, 44, 46):
        disc = math.pi * (D / 2 - 0.35) ** 2
        rows.append(dict(diameter_mm=D, usable_area_mm2=round(disc, 0), AB1A_front_pct=round(100 * res["A"]["front_mm2"] / disc, 1), AB1A_back_pct=round(100 * res["A"]["back_mm2"] / disc, 1),
                         AB1B_front_pct=round(100 * res["B"]["front_mm2"] / disc, 1), AB1B_back_pct=round(100 * res["B"]["back_mm2"] / disc, 1), gain_vs_D40_pct=round(100 * (D / 40) ** 2 - 100, 0)))
    save("area", dict(parts=res, rows=rows, note="body footprints only (courtyards and keep-outs are larger); the discs at x = -/+ D/2 + 0.3 must fit the bore: two D40 plus 0.6 mm = 80.6 mm, D44 = 88.6 mm (wall radius 44.0: does not fit side by side), D46 needs a wider wall")); return rows

# ------------------------------------------------------------------ layers
def layers():
    res = {}
    for B in ("A", "B"):
        j = json.load(open(f"work/out_board/AB1{B}_layout.json")); L = {}
        for l, a, b, w, n in j["TRACKS"]: L[l] = L.get(l, 0.0) + math.hypot(b[0] - a[0], b[1] - a[1])
        disc = math.pi * 19.65 ** 2
        res[B] = {l: dict(track_mm=round(v, 1), copper_pct_of_disc=round(100 * v * 0.15 / disc, 2)) for l, v in sorted(L.items())}; res[B]["vias"] = len(j["VIAS"])
    res["note"] = "copper_pct_of_disc = track area (0.15 mm wide) over the disc area. A routing layer used at a few percent is not the bottleneck: extra layers would not help; the pocket problem was local (pin pitch), not global"
    save("layers", res); return res

# ------------------------------------------------------------------ router robustness
TIERS = {"T0 committed (via 0.508/0.254, track 0.15, clear 0.16)": dict(AFE_VIA="0.508", AFE_VDRILL="0.254", AFE_TRACK="0.15", AFE_CLEAR="0.16"),
         "T1 finer lines only (track 0.10, clear 0.10)": dict(AFE_VIA="0.508", AFE_VDRILL="0.254", AFE_TRACK="0.10", AFE_CLEAR="0.10"),
         "T2 finer via only (via 0.40/0.20)": dict(AFE_VIA="0.40", AFE_VDRILL="0.20", AFE_TRACK="0.15", AFE_CLEAR="0.16"),
         "T3 finer lines and via (0.10 / 0.10, via 0.40/0.20)": dict(AFE_VIA="0.40", AFE_VDRILL="0.20", AFE_TRACK="0.10", AFE_CLEAR="0.10"),
         "T4 coarser than committed (track 0.18, clear 0.20)": dict(AFE_VIA="0.508", AFE_VDRILL="0.254", AFE_TRACK="0.18", AFE_CLEAR="0.20")}
MOVABLE = ["SW1", "SW2", "SW3", "D1", "D2", "D3", "RG1", "RG2", "RG3", "RF1", "RF2", "RF3", "CF1", "CF2", "CF3", "RAAF1", "RAAF2", "RAAF3", "CAAF1", "CAAF2", "CAAF3", "CSW1", "CSW2", "CSW3", "CVC", "CRG", "CVL", "CRC", "CRF", "UB", "RD1", "RD2", "CDF", "CVM", "CBD", "CB1", "RS1", "RS2", "RS3", "CO1", "CO2"]
def perturb(seed, k=6, amp=0.4):
    rnd = random.Random(seed); refs = rnd.sample(MOVABLE, k); return ",".join(f"{r}:{round(rnd.uniform(-amp, amp), 2)}:{round(rnd.uniform(-amp, amp), 2)}" for r in refs)
def route_one(args):
    B, tier, seed = args; env = dict(os.environ, BOARD=B, **TIERS[tier]); base = "SW2:0.4:0,CBD:-0.3:0" if B == "A" else "RD2:0.4:0"
    env["AFE_NUDGE"] = base + ("," + perturb(seed) if seed else "")
    r = subprocess.run([sys.executable, "afe_layout.py", "--route"], env=env, capture_output=True, text=True, cwd="work", timeout=900)
    try: rep = json.loads(r.stdout[r.stdout.index("{"):r.stdout.rindex("}") + 1])
    except Exception: return dict(B=B, tier=tier, seed=seed, ok=False, err="no report")
    ok = not rep["unrouted"] and not rep["fanout_failed"] and not rep["placement_errors"]
    return dict(B=B, tier=tier, seed=seed, ok=ok, unrouted=len(rep["unrouted"]), place=len(rep["placement_errors"]), tracks=rep["tracks"], vias=rep["vias"])
def router(n=20):
    from concurrent.futures import ThreadPoolExecutor
    jobs = [("A", t, s) for t in TIERS for s in range(0, n + 1)]; rows = []
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(route_one, jobs):
            rows.append(r); save("router_runs", rows)
    summ = {}
    for t in TIERS:
        rr = [r for r in rows if r["tier"] == t and r["seed"] > 0]; ok = [r for r in rr if r["ok"]]
        summ[t] = dict(runs=len(rr), success_pct=round(100 * len(ok) / max(len(rr), 1), 1), mean_open_pads=round(float(np.mean([r.get("unrouted", 9) + r.get("place", 0) for r in rr])), 2),
                       mean_vias=round(float(np.mean([r["vias"] for r in ok])), 1) if ok else None, mean_tracks=round(float(np.mean([r["tracks"] for r in ok])), 0) if ok else None,
                       committed_layout_ok=[r["ok"] for r in rows if r["tier"] == t and r["seed"] == 0][0])
    save("router", dict(board="AB1A", perturbation="seeded random 0.4 mm nudges of 6 of 41 movable parts on top of the committed layout", summary=summ,
                        note="success_pct is the share of perturbed placements the single-pass router completes with 0 open pads: a measure of how much slack the fab tier gives, not a prediction of yield")); return summ

# ------------------------------------------------------------------ noise
K = 1.380649e-23; T = 300.0
def noise_case(name, G=40.0, rs=100.0, rcoil=10.4, en=1.1e-9, sw_ohm=3.0, adc_snr_db=90.5, swing_v=1.25, fs_pp=2.5, bw=360e3, osr_gain_db=0.0, rg_rf=(10.0, 390.0)):
    Rg, Rf = rg_rf; rn = lambda R: math.sqrt(4 * K * T * R)
    # input-referred: coil + RS + switch (series path) + amplifier voltage noise + RG||RF feedback network + ADC noise / G
    fb = rn(Rg * Rf / (Rg + Rf))
    adc_rms = (fs_pp / 2 / math.sqrt(2)) / 10 ** ((adc_snr_db + osr_gain_db) / 20.0)             # full-scale sine rms over the Nyquist band (1 MHz at 2 MSPS)
    adc_den = adc_rms / math.sqrt(1.0e6)
    terms = dict(coil=rn(rcoil), RS=rn(rs + sw_ohm), amp=en, feedback=fb, adc=adc_den / G)
    ein = math.sqrt(sum(v * v for v in terms.values()))
    return dict(case=name, gain=G, RS_ohm=rs, adc_snr_db=adc_snr_db + osr_gain_db, swing_v=swing_v, EIN_nV_rtHz=round(ein * 1e9, 3), integrated_uV_rms=round(ein * math.sqrt(bw) * 1e6, 3), max_input_mV_peak=round(swing_v / G * 1e3, 2),
                dynamic_range_dB=round(20 * math.log10((swing_v / G / math.sqrt(2)) / (ein * math.sqrt(bw))), 1), terms_nV_rtHz={k: round(v * 1e9, 3) for k, v in terms.items()})
def noise():
    cases = [noise_case("current: G 40, RS 100, single-ended about VCM 1.25 V (+-1.25 V)"),
             noise_case("fully differential drive (AINx- driven opposite): +-2.5 V", swing_v=2.5),
             noise_case("rolling-average OSR 8 (datasheet 97.9 dB SNR; narrower bandwidth, pulse response must be re-checked)", adc_snr_db=90.5, osr_gain_db=97.9 - 90.5),
             noise_case("RS 100 -> 33 ohm (if the clamp current allows)", rs=33.0),
             noise_case("RS 100 -> 10 ohm", rs=10.0),
             noise_case("gain 40 -> 100 (RG 3.9 ohm)", G=100.0, rg_rf=(3.9, 390.0)),
             noise_case("amplifier 1.1 -> 1.0 nV/rtHz class (ADA4896-2 listed in datasheet Table 10)", en=1.0e-9),
             noise_case("combined: differential drive, RS 33 ohm, rolling-average OSR 8 (gain stays 40)", swing_v=2.5, rs=33.0, osr_gain_db=97.9 - 90.5),
             noise_case("AD4134-class 24-bit (rejected: 450 mW, 1.8 V rails): ADC term negligible", adc_snr_db=107.0, fs_pp=8.192, swing_v=4.096)]
    save("noise", dict(cases=cases, assumptions=["AD7389-4: SNR 90.5 dB typ, +-VREF = +-2.5 V differential, 2 MSPS, input range limits (datasheet p. 3)", "OPA2211 voltage noise 1.1 nV/rtHz and 3 ohm switch resistance: ASSUMED, the repo holds no datasheet for them (UNVERIFIED, U-DS-RXAMP)",
                                  "coil 10.4 ohm (SB1R-QA model), RS 100 ohm, RG 10 / RF 390 (gain 40), noise bandwidth 360 kHz (RAAF 200 ohm / CAAF 2.2 nF), T = 300 K", "ADC noise = full-scale rms / 10^(SNR/20) over 1 MHz, referred to the input through the stage gain",
                                  "dynamic range here is the peak-signal / noise ratio of the front end at the amplifier input; it says nothing about the target signal level, which needs the field model and the bench"])); return cases

# ------------------------------------------------------------------ scenarios
def scenarios():
    d = load(); rs = d.get("router", {}).get("summary", {}); nz = {c["case"][:14]: c for c in d.get("noise", {}).get("cases", [])}
    base = d["noise"]["cases"][0]; best = d["noise"]["cases"][-2]
    get = lambda key: next((v for k, v in rs.items() if k.startswith(key)), {})
    rows = [
     dict(option="S0 committed design", routing_success_pct=get("T0").get("success_pct"), fit="AB1 D40 pair 80.6 mm in an 88.0 mm bore (3.7 mm per side)", noise_dR=base["dynamic_range_dB"], EIN=base["EIN_nV_rtHz"], cost="none", risk="exposed-pad land pattern, SDI wait, +3V3D rows open"),
     dict(option="S1 board D44 (R_BOARD 22): no wall change", routing_success_pct=get("T0").get("success_pct"), fit="two D44 need 88.6 mm: does NOT fit side by side in the 88.0 mm bore; one D44 board fits", noise_dR=base["dynamic_range_dB"], EIN=base["EIN_nV_rtHz"], cost="re-place and re-route", risk="the earlier advice of D44 without a wall change was wrong for two boards side by side (the bore is 88.0, not 92.7)"),
     dict(option="S2 wall +1/8 inch (r 44.0 -> 47.2) with D46 boards", routing_success_pct=get("T0").get("success_pct"), fit="bore 94.4 mm holds two D46 (92.6 mm); area +32%", noise_dR=base["dynamic_range_dB"], EIN=base["EIN_nV_rtHz"], cost="hub_v22 AND the six formers (their inner bore sits at r 49.1-49.9, no free ring at z 3-29), parts, ribs, posts, LB1 / CB1D margins, regress; two full regenerations", risk="the free ring outside the core is about 0 mm at the former levels (room): the earlier 10 mm was the winding start radius, not free space"),
     dict(option="S3 finer fab tier (0.10 / 0.10, via 0.40)", routing_success_pct=get("T3").get("success_pct"), fit="no change", noise_dR=base["dynamic_range_dB"], EIN=base["EIN_nV_rtHz"], cost="fabricator surcharge; needs a vendor that lists the tier (U-FAB-DRC)", risk="fab yield and cost, not electrical"),
     dict(option="S4 six to eight layers", routing_success_pct=None, fit="board 1.6 -> about 2.0 mm (8.3 mm free above AB1)", noise_dR=base["dynamic_range_dB"], EIN=base["EIN_nV_rtHz"], cost="fab cost", risk="measured: the routing layers are used at 0.3 to 3 percent, so this buys nothing for routing"),
     dict(option="S5 front-end changes (differential drive, RS 33, OSR 8, gain stays 40)", routing_success_pct=get("T0").get("success_pct"), fit="+2 parts per channel for the differential stage", noise_dR=best["dynamic_range_dB"], EIN=best["EIN_nV_rtHz"], cost="design time, bench; RS needs the clamp-current check; OSR changes the pulse response", risk="every performance number stays MODELED"),
     dict(option="S6 J2 as a small board-to-board connector", routing_success_pct=None, fit="frees about 3 mm x 12 mm at the edge", noise_dR=base["dynamic_range_dB"], EIN=base["EIN_nV_rtHz"], cost="CB1D JA/JB, housing, harness (wiring_audit 53 links / 50 conductors)", risk="largest knock-on of all options"),
     dict(option="S7 combined: S2 + S5 (S3 only if the fabricator needs it)", routing_success_pct=get("T0").get("success_pct"), fit="area +32%, +6 to +20 dB range", noise_dR=best["dynamic_range_dB"], EIN=best["EIN_nV_rtHz"], cost="one regeneration plus bench", risk="moderate")]
    save("scenarios", rows); return rows

# ------------------------------------------------------------------ report (figure + document, generated from the JSON)
ADDS = [
 ("Second AD7389-4 (or one per board plus a spare)", "AB1A + AB1B need 5 converter inputs; one chip has 4. Merging the two boards into one needs two chips (8 inputs, 3 spare for a test channel, the VCM monitor and a temperature or supply monitor).", "datasheet p. 1: 4 differential channels, 2 MSPS", "adds 1 package, one more island pin pocket; supply +25 mA"),
 ("Fully differential amplifier stage (ADA4940-2) or low-noise single-ended driver (ADA4896-2, 1 nV/rtHz)", "listed by the AD7389-4 datasheet as companion drivers (Table 10, p. 16): differential drive recovers the 6 dB of range lost by the 1.25 V single-ended swing", "datasheet p. 16 Table 10", "2 more parts per channel; not yet routed or placed"),
 ("Reference buffer ADA4807-2 for VCM", "datasheet p. 20: add a buffer when REFOUT feeds a common-mode voltage; the OPA2365 half B already does this job, so this is a change only if its noise or drive matters", "datasheet p. 20", "none needed now"),
 ("Supply filter: ferrite bead + 10 uF on +5VA and +3V3D at J2", "keeps CB1D switching noise out of the front end; the island makes a local +3V3D plane available", "design practice, no number from the datasheets", "2 parts, 1 pad pair each"),
 ("Calibration pulse: one switch and a precision divider", "injects a known step at the input to check gain and timing in the field", "none (design idea)", "needs the blanking switch family decided (quad ADG1611-class unverified)"),
 ("Temperature sensor near the converter", "the reference drifts 2 ppm/C typ and the coil resistance with temperature; one reading per frame corrects both", "datasheet p. 4: 2 ppm/C typ, 10 max", "1 small part; part not chosen"),
 ("A timing coprocessor (small CPLD / FPGA) in CB1D", "only if the Pico 2 W's PIO cannot hold the blanking and sampling edges; the converter's aperture jitter is 20 ps (datasheet p. 4), far below what PIO granularity (a few ns) would add", "datasheet p. 4", "NOT recommended now: no evidence the Pico limits timing"),
 ("A more capable processor for the DSP (TI C2000, STM32H7, FPGA)", "the 5-channel 2 MSPS stream is 160 Mbit/s of raw data: the RP2350's PIO plus DMA can take the 2-wire streams, but the filtering and detection (OPEN_ITEMS 5, DSP in Python) have not been sized", "none", "decide after the DSP load is measured, not before")]
def report():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    d = load(); fig = plt.figure(figsize=(22, 13), facecolor="#f4f6fa"); gs = fig.add_gridspec(2, 3, hspace=0.38, wspace=0.28, left=0.04, right=0.985, top=0.9, bottom=0.07)
    fig.suptitle("Receive-stage options model: which rule changes and additions help (MODELED, tool-measured, nothing built)", fontsize=17, fontweight="bold", x=0.04, ha="left")
    ax = fig.add_subplot(gs[0, 0]); L = d["room"]["levels"]; zs = [r["z"] for r in L]
    ax.bar([str(z) for z in zs], [r["free_ring_mm"] if r["free_ring_mm"] is not None else 0 for r in L], color="#c0392b"); ax.axhline(0, color="k", lw=0.6)
    for i, r in enumerate(L): ax.text(i, (r["free_ring_mm"] or 0) + 0.05, (r["nearest"][0][0].replace("LOTUS_HOOD_CARRIER_v3_butted", "hood")[:9] if r["nearest"] else "none"), ha="center", fontsize=7, rotation=90, va="bottom")
    ax.set_title("1  Room outside the vault wall: free ring (mm) at each level", loc="left", fontsize=11, fontweight="bold"); ax.set_xlabel("z (mm)"); ax.set_ylabel("core outer radius to next solid (mm)"); ax.set_ylim(-1, 4)
    ax2 = fig.add_subplot(gs[0, 1]); A = d["layers"]["A"]; names = [k for k in A if k != "vias"]
    ax2.bar(names, [A[k]["copper_pct_of_disc"] for k in names], color="#2b63d8"); ax2.set_title("2  AB1A routing layers: copper used (% of the disc area)", loc="left", fontsize=11, fontweight="bold"); ax2.set_ylabel("%")
    for i, k in enumerate(names): ax2.text(i, A[k]["copper_pct_of_disc"] + 0.05, f"{A[k]['track_mm']:.0f} mm", ha="center", fontsize=8)
    ax2.text(0.02, 0.9, f"components cover {d['area']['rows'][0]['AB1A_front_pct']}% (front) and {d['area']['rows'][0]['AB1A_back_pct']}% (back) of a D40 board", transform=ax2.transAxes, fontsize=8, color="#444")
    ax3 = fig.add_subplot(gs[0, 2]); S = d["router"]["summary"]; ks = list(S); ax3.barh([k[:2] for k in ks], [S[k]["success_pct"] for k in ks], color=["#1a8f3c" if S[k]["success_pct"] >= 90 else "#d49a00" if S[k]["success_pct"] >= 50 else "#c0392b" for k in ks])
    for i, k in enumerate(ks): ax3.text(2, i, k[3:60] + f"   committed layout ok: {S[k]['committed_layout_ok']}", va="center", fontsize=7)
    ax3.set_xlim(0, 100); ax3.invert_yaxis(); ax3.set_title("3  Router robustness: perturbed placements routed with 0 open pads (%)", loc="left", fontsize=11, fontweight="bold"); ax3.set_xlabel("success (%)")
    ax4 = fig.add_subplot(gs[1, 0:2]); C = d["noise"]["cases"]; lab = [c["case"][:58] for c in C]; keys = ["coil", "RS", "amp", "feedback", "adc"]; col = ["#7f8aa0", "#d33a2c", "#2e9c4a", "#d49a00", "#2b63d8"]
    left = np.zeros(len(C))
    for k, cc in zip(keys, col):
        v = np.array([c["terms_nV_rtHz"][k] ** 2 for c in C]); ax4.barh(lab, v, left=left, color=cc, label=k); left += v
    ax4.invert_yaxis(); ax4.legend(fontsize=8, loc="lower right"); ax4.set_xlabel("input-referred noise power (nV^2/Hz), stacked terms")
    for i, c in enumerate(C): ax4.text(left[i] + 0.03, i, f"EIN {c['EIN_nV_rtHz']} nV/rtHz, range {c['max_input_mV_peak']} mV pk, DR {c['dynamic_range_dB']} dB", va="center", fontsize=7)
    ax4.set_title("4  Front-end noise and range by option (assumptions in the JSON)", loc="left", fontsize=11, fontweight="bold")
    ax5 = fig.add_subplot(gs[1, 2]); ax5.axis("off"); ax5.set_title("5  Scenarios", loc="left", fontsize=11, fontweight="bold")
    y = 0.97
    for r in d["scenarios"]:
        ax5.text(0, y, r["option"], fontsize=8, fontweight="bold", transform=ax5.transAxes, va="top"); y -= 0.04
        ax5.text(0.02, y, f"fit: {r['fit'][:78]}", fontsize=6.8, transform=ax5.transAxes, va="top"); y -= 0.035
        ax5.text(0.02, y, f"route {r['routing_success_pct']}%  DR {r['noise_dR']} dB  cost: {r['cost'][:60]}", fontsize=6.8, transform=ax5.transAxes, va="top"); y -= 0.05
    os.makedirs("deliverables/options_model", exist_ok=True); fig.savefig("deliverables/options_model/PHIFOLD233_RECEIVE_OPTIONS_MODEL.png", dpi=80); fig.savefig("deliverables/options_model/PHIFOLD233_RECEIVE_OPTIONS_MODEL.pdf")
    t = ["# Receive-stage options model (MODELED, tool-measured; nothing built)", "", "Generated by `python3 src/sim/ab1_options_model.py all` from the current meshes, the committed AB1 layouts and datasheet numbers; data in `data/results/ab1_options_model.json`, figure in `deliverables/options_model/`.", "",
         "## Room outside the vault wall (z, inner wall r, core outer r, next solid, free ring)", ""] + [f"- z {r['z']}: inner wall r {r['inner_wall_r']}, comb to r {r['comb_min_r']}, core outer r {r['core_outer_r']}, next solid r {r['nearest_other_solid_r']} ({', '.join(n for n, _ in r['nearest'][:2]) or 'none'}), free ring {r['free_ring_mm']} mm" for r in d["room"]["levels"]]
    t += ["", d["room"]["note"], "", "## Board area and layers", ""] + [f"- D{r['diameter_mm']}: usable {r['usable_area_mm2']} mm2; AB1A parts cover {r['AB1A_front_pct']}% front / {r['AB1A_back_pct']}% back; AB1B {r['AB1B_front_pct']}% / {r['AB1B_back_pct']}%; area +{r['gain_vs_D40_pct']}% vs D40" for r in d["area"]["rows"]]
    t += [f"- layers AB1A: " + ", ".join(f"{k} {v['copper_pct_of_disc']}%" for k, v in d["layers"]["A"].items() if k != "vias"), d["layers"]["note"], "", "## Router robustness (AB1A, 20 perturbed placements per tier)", ""] + [f"- {k}: {v['success_pct']}% success, mean open pads {v['mean_open_pads']}, mean vias {v['mean_vias']}, committed layout ok: {v['committed_layout_ok']}" for k, v in d["router"]["summary"].items()]
    t += ["", d["router"]["note"], "", "## Front-end noise and range", ""] + [f"- {c['case']}: EIN {c['EIN_nV_rtHz']} nV/rtHz, {c['integrated_uV_rms']} uV rms over 360 kHz, max input {c['max_input_mV_peak']} mV peak, range/noise {c['dynamic_range_dB']} dB" for c in d["noise"]["cases"]]
    t += ["", "Assumptions: " + "; ".join(d["noise"]["assumptions"]), "", "## Scenarios", "", "| option | route success | fit | range/noise (dB) | EIN | cost | risk |", "|---|---|---|---|---|---|---|"] + [f"| {r['option']} | {r['routing_success_pct']} | {r['fit']} | {r['noise_dR']} | {r['EIN']} | {r['cost']} | {r['risk']} |" for r in d["scenarios"]]
    t += ["", "## What could be added", "", "| addition | why | source | cost |", "|---|---|---|---|"] + [f"| {a} | {b} | {c} | {e} |" for a, b, c, e in ADDS]
    open("docs/design/RECEIVE_OPTIONS_MODEL.md", "w").write("\n".join(t) + "\n")

if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "all"; n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 20
    for k, f in (("room", room), ("area", area), ("layers", layers), ("noise", noise), ("router", lambda: router(n)), ("scenarios", scenarios), ("report", report)):
        if part in (k, "all"):
            t0 = time.time(); r = f(); print(f"{k}: done in {time.time() - t0:.0f} s")
