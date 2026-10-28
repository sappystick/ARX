#!/usr/bin/env python3
"""Potting map (owner request 2026-10-28): a zoned fill plan for the whole detector, using several compound classes matched to what each zone needs,
filling as much as the function allows. MODELED: volumes are exact mesh booleans where meshes exist (manifold3d), electrical effects come from the
existing transmit model; every compound property is an ASSUMED class value (no product chosen, no datasheet on disk: rule 7), listed as a range.
Zones and their compound class:
  head  L1 gallery (RX leads)          GEL   soft silicone gel     locks the receive leads (lead movement is microphonic noise); low stress, low permittivity
        L2 analog cell (AB1A / AB1B)   GEL   same                  locks the boards and the FFC links; keeps the precision parts free of hard-resin stress
        L4 absorber                    CI    carbonyl-iron silicone  (existing design, potting_volumes.py)
        coil windings (six formers)    SYN / none                   decided by the transmit model: the fill raises the coil self-capacitance and delays the quiet time
        L0 receive boards, L5 CB1D, L6 LB1, L8 cap     CC conformal coat only (RX lobes: capacitance; CB1D: Pico antenna, gyro moved; LB1: light)
  neck  NPM hot zone (PB1R FETs, clamp)  TC  thermally conductive silicone (existing design)
        NPM main zone                    SYN syntactic silicone (existing design)
  upper U3 PM2 bay under AU1             SYN fill from the housing floor to 1 mm under AU1 (AU1 coated: speaker, jack and selector leads, SWD pads stay free)
        U1 HB2 pocket                     SYN pocket around HB2 (the Hall switch reads the trigger magnet through the wall: a non-magnetic fill does not change it)
        grip channels, shaft twin cavity, battery pack, dock: NO FILL (moving cords, collapsible shaft, cell venting, removable pack)
Checks written to the JSON: fill fraction, mass per zone, eddy rule (every filler electrically insulating), the coil-fill effect on the quiet time against the
first receive gate (fw_timeline.json), vault temperature bound, keep-outs. usage (repo root, after make setup and the v5 / upper / potting steps):
python3 src/mech/potting_map.py [OUT.json]"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, "src/mech"); import potting_volumes as PV                  # stl(), box(), cyl(), union(), cm3() and the NPM / L4 results
import manifold3d as M3
W = "work"
# compound classes: ASSUMED typical ranges for the class (no product chosen; replace with the datasheet values of the chosen products)
C = {
 "TC":  dict(name="thermally conductive silicone (alumina / boron-nitride filled)", rho=(1.9, 2.3), k_W_mK=(1.0, 3.0), er=(4.0, 6.0), shore="A 40-70", insulating=True),
 "SYN": dict(name="syntactic silicone (hollow glass microspheres)", rho=(0.6, 0.8), k_W_mK=(0.1, 0.2), er=(1.6, 2.2), shore="A 20-50", insulating=True),
 "GEL": dict(name="soft silicone gel (low stress, dielectric gel class)", rho=(0.95, 1.0), k_W_mK=(0.15, 0.2), er=(2.7, 3.0), shore="gel (penetration)", insulating=True),
 "CI":  dict(name="carbonyl-iron silicone absorber (existing design)", rho=(3.3, 3.7), k_W_mK=(0.5, 1.5), er=None, shore="A 50-70", insulating=True),
 "CC":  dict(name="conformal coat (silicone or acrylic class), 25-75 um", rho=(1.0, 1.1), k_W_mK=None, er=(2.7, 3.5), shore="film", insulating=True),
}
def mass(v_cm3, c): return [round(v_cm3 * C[c]["rho"][0], 1), round(v_cm3 * C[c]["rho"][1], 1)]

def stl_any(p):
    try: return PV.stl(p)
    except Exception: return None

def l2_cell():
    """analog cell z 9.8..20.0 inside the hub bore (r 44): minus the core cylinder, comb, tray, the masked duct, both AB1 boards with components (head_crosscheck placement)"""
    H = f"{W}/kit_v22"; core = stl_any(f"{H}/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl") or stl_any("stl/head/CORE_CYLINDER_v5_integrated.stl")
    env = PV.cyl(44.0, 9.8, 20.0); parts = [m for m in (core, stl_any("stl/head/SPINE_COMB_v5.stl"), stl_any("stl/head/ANALOG_TRAY_v5.stl")) if m is not None]
    duct = PV.box(-6, 6, 40, 44, 9.8, 20.0); boards = []; ok_boards = []
    for b, dx in (("AB1A", -20.3), ("AB1B", 20.3)):
        m = stl_any(f"{W}/kit_v3/PCB_{b}/PF233-{b}_board_with_components.stl")
        if m is not None: boards.append(m.translate([dx, 0, 11.1 + 2.7])); ok_boards.append(b)
    solid = PV.union(parts + [duct] + boards); free = env - solid
    return dict(envelope_cm3=round(PV.cm3(env), 2), parts_in_cell_cm3=round(PV.cm3(env ^ PV.union(parts)), 2), boards_meshed=ok_boards,
                boards_in_cell_cm3=round(PV.cm3(env ^ PV.union(boards)), 2) if boards else None, duct_keepout_cm3=round(PV.cm3(env ^ duct), 2), free_cm3=round(PV.cm3(free), 2))

def l1_gallery():
    """gallery z 3.2..9.0 inside r 44: minus the core and the base plate (bosses, recess walls); RX leads are thin and stay in the fill"""
    core = stl_any("stl/head/CORE_CYLINDER_v5_integrated.stl"); base = stl_any("stl/head/BASE_PLATE_RX_CASSETTE_v3.stl"); env = PV.cyl(44.0, 3.2, 9.0)
    parts = [m for m in (core, base) if m is not None]; free = env - PV.union(parts) if parts else env
    return dict(envelope_cm3=round(PV.cm3(env), 2), meshes=[n for n, m in (("core", core), ("base", base)) if m is not None], free_cm3=round(PV.cm3(free), 2))

def housing_interior(m):
    """the inside of a closed housing shell: its convex hull minus the shell (the U1 / U3 sections are convex rounded rectangles)"""
    return m.hull() - m

def upper(rep):
    U = f"{W}/kit_v23/UPPER"; E = rep["envelopes"]; out = {}
    u3 = stl_any(f"{U}/U3_BOTTOM_HOUSING.stl"); u1 = stl_any(f"{U}/U1_TOP_HOUSING.stl")
    if u3 is not None:
        p, a = E["PM2_board"], E["AU1_board"]; inner = housing_interior(u3)
        region = PV.box(p["x"][0], p["x"][1], -30, 30, -200, a["z_board"][0] - 1.0) ^ inner        # floor up to 1 mm under AU1, over the PM2 bay length
        pm2 = PV.box(p["x"][0], p["x"][1], p["y"][0], p["y"][1], p["z_board"][0], p["z_board"][1] + p["parts_height"])  # PM2 board + parts (bounding box)
        out["U3_PM2_bay"] = dict(region_cm3=round(PV.cm3(region), 2), pm2_box_cm3=round(PV.cm3(region ^ pm2), 2), free_cm3_lower=round(PV.cm3(region - pm2), 2),
                                 note="PM2 parts as one bounding box: the fill volume is a lower bound; AU1 above stays free (coated)")
        out["U3_interior_cm3"] = round(PV.cm3(inner), 2)
    if u1 is not None:
        h = E["HB2_board"]; inner = housing_interior(u1)
        pocket = PV.box(h["x"][0] - 1, h["x"][1] + 1, h["y"][0] - 1, h["y"][1] + 1, h["z_board"][0] - 3, h["z_board"][1] + h["parts_height"] + 1) ^ inner
        hb2 = PV.box(h["x"][0], h["x"][1], h["y"][0], h["y"][1], h["z_board"][0], h["z_board"][1] + h["parts_height"])
        out["U1_HB2_pocket"] = dict(pocket_cm3=round(PV.cm3(pocket), 2), free_cm3_lower=round(PV.cm3(pocket - hb2), 2), note="pocket = HB2 envelope + 1 mm, from 3 mm under the board")
        out["U1_interior_cm3"] = round(PV.cm3(inner), 2)
    return out

def coil_fill():
    """the coil self-capacitance (250 pF of the 500 pF node, ASSUMPTIONS 1) scaled by the fill: C = C0 (1 + phi (er - 1)), phi = share of the turn-to-turn
    field in the filled gap (ASSUMED 0.3-0.7); quiet time from the transmit model (tx_vbus_sweep.pulse via system_live.tx_point, boost, 24.5 V, design clamp)"""
    cwd = os.getcwd(); os.chdir(W); sys.path.insert(0, "."); import system_live as SL
    TL = json.load(open("kit_v23/fw_timeline.json"))["inputs"]; g0 = TL["first_gate_us"]
    NS = SL.NS; C0 = NS["Cn"]; Cself = 250e-12; res = []
    for cls, er in (("air (no fill)", 1.0), ("SYN low", C["SYN"]["er"][0]), ("SYN high", C["SYN"]["er"][1]), ("GEL", C["GEL"]["er"][1]), ("TC", C["TC"]["er"][1])):
        for phi in ((0.0,) if er == 1.0 else (0.3, 0.7)):
            NS["Cn"] = C0 + Cself * phi * (er - 1.0); p = SL.tx_point(24.5, "boost", "design"); NS["Cn"] = C0
            res.append(dict(fill=cls, er=er, phi=phi, Cn_pF=round((C0 + Cself * phi * (er - 1.0)) * 1e12, 1), t_quiet_us=round(p["t_quiet_us"], 3), first_gate_us=g0,
                            margin_us=round(g0 - p["t_quiet_us"], 3), ok=bool(p["t_quiet_us"] < g0 - 0.10)))
    os.chdir(cwd)
    return res

def main(outp):
    rep = json.load(open(f"{W}/kit_v23/UPPER/upper_v21_report.json")); pv = json.load(open("data/results/potting_volumes.json"))
    l2 = l2_cell(); l1 = l1_gallery(); up = upper(rep); coil = coil_fill()
    coil_ok = [r for r in coil if r["fill"] != "air (no fill)" and r["ok"]]
    winding = "SYN" if any(r["fill"].startswith("SYN") and r["ok"] for r in coil) and all(r["ok"] for r in coil if r["fill"].startswith("SYN")) else None
    Z = [
     dict(zone="NPM hot zone (PB1R FETs, clamp diode, shunt)", where="neck", compound="TC", cm3=[pv["npm"]["hot_zone"]["free_cm3_lower"], pv["npm"]["hot_zone"]["free_cm3_upper_no_parts"]], why="heat to the module wall; HV nodes wetted void-free", source="potting_volumes.json (exact)"),
     dict(zone="NPM main zone", where="neck", compound="SYN", cm3=[pv["npm"]["main_zone"]["free_cm3_lower"], pv["npm"]["main_zone"]["free_cm3_upper_no_parts"]], why="light, locks the board and the leads", source="potting_volumes.json (exact)"),
     dict(zone="L4 absorber cell", where="head", compound="CI", cm3=[pv["l4_absorber"]["free_cm3"]] * 2, why="magnetic absorber (existing design)", source="potting_volumes.json (exact)"),
     dict(zone="L2 analog cell (AB1A / AB1B, FFC links)", where="head", compound="GEL", cm3=[l2["free_cm3"]] * 2, why="locks boards and links against vibration (microphonics), no hard-resin stress on the precision parts", source="exact mesh boolean (this script)"),
     dict(zone="L1 gallery (RX leads, spine flex start)", where="head", compound="GEL", cm3=[l1["free_cm3"]] * 2, why="RX leads that move are microphonic noise", source="exact mesh boolean (core and base plate)"),
     dict(zone="U3 PM2 bay (under AU1)", where="upper", compound="SYN", cm3=[up.get("U3_PM2_bay", {}).get("free_cm3_lower", 0.0)] * 2, why="locks PM2 and the power leads; AU1 stays reachable above (coated)", source="exact mesh boolean, PM2 as a box (lower bound)"),
     dict(zone="U1 HB2 pocket", where="upper", compound="SYN", cm3=[up.get("U1_HB2_pocket", {}).get("free_cm3_lower", 0.0)] * 2, why="locks HB2 and the cord joint; the Hall switch reads through the wall", source="exact mesh boolean, HB2 as a box (lower bound)"),
    ]
    for z in Z: z["mass_g"] = [mass(z["cm3"][0], z["compound"])[0], mass(z["cm3"][1], z["compound"])[1]]
    coat = [dict(item="L0 SB1R-QA / QB receive boards", why="RX lobes: a pour adds capacitance to the receive coils (sbq_damp model); coat only"),
            dict(item="L5 CB1D", why="Pico 2 W antenna and 10.2 mm parts under LB1; coat + wire staking"),
            dict(item="L6 LB1", why="LEDs shine through the pixel holes: clear coat only"),
            dict(item="L8 cap / HTA board", why="final bond not specified; coat"),
            dict(item="AU1", why="speaker, jack, selector leads and the SWD pads stay free; coat + staking")]
    keepout = [dict(item="grip channels (U2)", why="cords move with the trigger and the housings"), dict(item="shaft tube B twin cavity", why="collapsible shaft: the cords slide"),
               dict(item="battery pack U7 and dock U6", why="removable pack; Li-ion cells need a vent path"), dict(item="spine duct and comb windows (head)", why="FFC passage (masked insert)"),
               dict(item="programming pads (AU1 JSWD, CB1D JDBG)", why="clip-on probe access"), dict(item="moving parts: trigger, dial, power button, latch", why="mechanisms")]
    wind = dict(zone="coil windings (six formers)", compound=winding or "none", rule="only a fill that keeps the quiet time >= 0.10 us before the first gate in the whole phi range",
                results=coil, decision=("winding lock with SYN (low permittivity) only" if winding else "no pour on the windings: lock the turns with a thin SYN bead at the ends only and verify on the bench"))
    tot = lambda w: round(sum(z["cm3"][0] for z in Z if z["where"] == w), 1)
    tests = [
     dict(id="PT1", what="compound properties of the chosen products", data="density, thermal conductivity, relative permittivity at 100 kHz-1 MHz, dielectric strength, Shore hardness, cure shrinkage, CTE, outgassing",
          how="manufacturer datasheets (log in DATASHEET_LOG); replace the ASSUMED class ranges in this script", pass_="every zone keeps its function with the real numbers (re-run potting_map.py)"),
     dict(id="PT2", what="coil self-capacitance and quiet time, bare vs end-bead lock", data="C_self of one wound former (impedance analyser, SRF), t_quiet on the bench (scope on the drain and the RX input)",
          how="before and after the SYN end beads; then one former test-potted in SYN as a sacrificial sample", pass_="t_quiet <= first gate - 0.10 us (fw_timeline.json) with the beads; record the potted sample's delay"),
     dict(id="PT3", what="RX microphonics, L1 / L2 unpotted vs GEL", data="RX output noise during a tap / swing test (fixed tap energy), 10 trials each", how="AB1 outputs on the logger, head swung on the rig",
          pass_="GEL reduces the tap response; no change of the quiet (no-tap) noise floor"),
     dict(id="PT4", what="mass and balance", data="weight of each poured zone, head and handle mass, balance point on the armrest", how="scale before / after each pour",
          pass_="within the ranges in this file; balance point recorded"),
     dict(id="PT5", what="thermal, NPM hot zone and vault", data="FET case and hot-zone temperature at boost, 25 / 40 C ambient, 30 min", how="thermocouples cast in the fill",
          pass_="below the model limits (vault 80 C, PETG); the potted case not hotter than the unpotted model"),
     dict(id="PT6", what="high voltage in the NPM fill", data="hipot DRAIN1 / CLAMP1 to everything at 1 kV (harness test T05/T06), partial discharge if available", how="after cure, before closing", pass_="no breakdown; leakage logged"),
     dict(id="PT7", what="voids and adhesion", data="X-ray or a cut sacrificial sample per compound; adhesion to PETG / FR4 / silicone wire", how="sample pours with the production degassing", pass_="no void at an HV node or a lead exit; no delamination after 10 thermal cycles"),
     dict(id="PT8", what="continuity and function after cure", data="every net continuity (netlist), plane HV keep-outs untouched, ring-down / leak bench items", how="POTTING_SEQUENCE rule 4", pass_="identical to before the pour"),
     dict(id="PT9", what="nickel shield paint (MG 841AR) near the coil", data="RX decay with a painted, slit PETG coupon (25 and 50 um) at the head face vs a bare coupon; then at the neck-module position",
          how="coupon taped at the vault and at the NPM wall, ring-down / leak bench items", pass_="no change in the RX window beyond the bare-coupon noise; otherwise no paint at that position"),
    ]
    out = dict(status="MODELED: volumes exact where meshes exist (lower bounds where parts are boxes); compound properties ASSUMED class ranges (no product chosen)",
               compounds=C, zones=Z, windings=wind, bench_tests=tests, coat_only=coat, keep_out=keepout, l2_detail=l2, l1_detail=l1, upper_detail=up,
               totals=dict(head_cm3=tot("head"), neck_cm3=tot("neck"), upper_cm3=tot("upper"),
                           mass_g=dict(head=[round(sum(z["mass_g"][0] for z in Z if z["where"] == "head"), 0), round(sum(z["mass_g"][1] for z in Z if z["where"] == "head"), 0)],
                                       neck=[round(sum(z["mass_g"][0] for z in Z if z["where"] == "neck"), 0), round(sum(z["mass_g"][1] for z in Z if z["where"] == "neck"), 0)],
                                       upper=[round(sum(z["mass_g"][0] for z in Z if z["where"] == "upper"), 0), round(sum(z["mass_g"][1] for z in Z if z["where"] == "upper"), 0)])),
               checks=dict(eddy_rule_all_insulating=all(C[z["compound"]]["insulating"] for z in Z),
                           vault_temperature_bound_C=max(v["max_C"] for v in json.load(open("data/results/sim_thermal.json")).values()),
                           vault_note="the thermal model is unpotted air; replacing air (0.026 W/mK) by GEL (0.15-0.2) only adds conduction, so the unpotted worst case is an upper bound",
                           winding_fill_ok=bool(winding)))
    json.dump(out, open(outp, "w"), indent=1)
    print("potting map:", ", ".join(f"{z['zone'].split(' (')[0]} {z['compound']} {z['cm3'][0]:.1f} cm3" for z in Z))
    print("windings:", wind["decision"]); [print(f"  {r['fill']:14s} er {r['er']} phi {r['phi']}: quiet {r['t_quiet_us']} us, margin {r['margin_us']} us {'ok' if r['ok'] else 'NO'}") for r in coil]
    print("totals:", out["totals"])

def figure(out, png):
    """one figure: fill volume per zone by compound (direct-labelled), and the coil-fill quiet-time margin against the first gate"""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    COL = {"TC": "#2a78d6", "SYN": "#eb6834", "GEL": "#1baf7a", "CI": "#eda100"}            # validated categorical slots 1-4 (dataviz reference palette)
    INK, MUTED, SURF = "#1f1f1e", "#6b6a64", "#fcfcfb"
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 5.0), gridspec_kw=dict(width_ratios=[1.25, 1]), facecolor=SURF)
    Z = out["zones"]; y = np.arange(len(Z))[::-1]
    for yi, z in zip(y, Z):
        a.barh(yi, z["cm3"][0], height=0.62, color=COL[z["compound"]], edgecolor=SURF, linewidth=2)
        a.text(z["cm3"][0] + 1.2, yi, f'{z["compound"]}  {z["cm3"][0]:.1f} cm³  ({z["mass_g"][0]:.0f}-{z["mass_g"][1]:.0f} g)', va="center", fontsize=8.5, color=INK)
    a.set_yticks(y, [z["zone"].split(" (")[0] for z in Z], fontsize=9, color=INK); a.set_xlabel("fill volume, cm³ (exact mesh booleans; lower bound where parts are boxes)", fontsize=8.5, color=MUTED)
    a.set_xlim(0, max(z["cm3"][0] for z in Z) * 1.75); a.set_title("Potting map: fill per zone (compound class, mass ASSUMED)", fontsize=10.5, color=INK, loc="left")
    from matplotlib.patches import Patch
    a.legend(handles=[Patch(color=COL[k], label=f"{k}  {C[k]['name'].split(' (')[0]}") for k in ("TC", "SYN", "GEL", "CI")], fontsize=7.5, frameon=False, loc="lower right")
    for sp in ("top", "right"): a.spines[sp].set_visible(False)
    a.tick_params(colors=MUTED); a.grid(axis="x", color="#e4e3df", linewidth=0.8); a.set_axisbelow(True)
    R = out["windings"]["results"]
    for phi, ls, lab in ((0.3, "-", "φ 0.3"), (0.7, "--", "φ 0.7")):
        pts = sorted([(1.0, R[0]["margin_us"])] + [(r["er"], r["margin_us"]) for r in R if r["phi"] == phi])
        b.plot([p[0] for p in pts], [p[1] for p in pts], ls, color=INK if phi == 0.3 else MUTED, linewidth=2, marker="o", markersize=6, label=f"share of field in the fill {lab}")
        b.text(pts[-1][0] + 0.08, pts[-1][1], lab, fontsize=8.5, va="center", color=INK if phi == 0.3 else MUTED)
    b.axhline(0, color="#b4473a", linewidth=1.2); b.text(6.3, -0.06, "first gate lost below 0", fontsize=8, color="#b4473a", ha="right", va="top")
    b.axhline(0.10, color=MUTED, linewidth=0.8, linestyle=":"); b.text(6.3, 0.15, "0.10 µs required margin", fontsize=8, color=MUTED, ha="right", va="bottom")
    b.set_xlabel("relative permittivity of the winding fill (air 1; SYN 1.6-2.2; GEL 3; TC 6)", fontsize=8.5, color=MUTED)
    b.set_ylabel("first gate − quiet time, µs", fontsize=8.5, color=MUTED); b.legend(fontsize=8, frameon=False, loc="lower left")
    b.set_title("Coil windings: any fill delays the receive window (MODELED)", fontsize=10.5, color=INK, loc="left")
    for sp in ("top", "right"): b.spines[sp].set_visible(False)
    b.tick_params(colors=MUTED); b.grid(color="#e4e3df", linewidth=0.8); b.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(png, dpi=130, facecolor=SURF); plt.close(fig)

if __name__ == "__main__":
    outp = sys.argv[1] if len(sys.argv) > 1 else "data/results/potting_map.json"; main(outp)
    figure(json.load(open(outp)), os.path.join(os.path.dirname(outp) or ".", "potting_map.png"))
