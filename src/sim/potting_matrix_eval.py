#!/usr/bin/env python3
"""Evaluation of the owner's single-matrix potting proposal (2026-10-28): low-exotherm epoxy + 40-50 vol% hollow glass bubbles (3M iM30K) + 10-15 vol% boron nitride
or alumina + 1-2 vol% hydrophobic fumed silica, injected through the whole head, with a conductive-paint shield on the circuit cavity walls and optional phase-change
additives. Each claim is tested with the repo's own models; MODELED, nothing mixed or poured.
  composite thermal conductivity and permittivity: symmetric Bruggeman effective-medium mixing of all phases (spherical inclusions; platelet BN aligned in-plane
  would do better along the plates, so the BN conductivity is taken high, 60 W/mK, to favour the claim)
  coil quiet time: tx_vbus_sweep.pulse via system_live.tx_point with the coil self-capacitance (250 pF of the 500 pF node, ASSUMPTIONS 1) scaled by the fill
  conductive cavity paint: thin conducting cylinder, decay time tau = mu0 sigma d r / 2 = mu0 r / (2 Rs) (Rs sheet resistance), against the first receive gate
  phase-change additive: latent heat against the neck-module dissipation of the transmit model (boost)
Verified constituent data: 3M Glass Bubbles iM30K (3M product information table, K / S / iM series, copy at https://Aircraftspruce.Com/catalog/pdf/3MGLASS BUBBLES.pdf):
true density 0.60 g/cc (0.57-0.63), crush 28,000 psi at 90 % survival (the iM30K data sheet Rev C lists 27,000 psi), calculated thermal conductivity 0.200 W/mK,
dielectric constant 1.2-2.0 (theoretical). Owner-supplied data sheets (2026-10-28): iM30K, MG 832TC (Ver. 4.3), MG 841AR (Rev. 7.0 and Ver. 2.05): products() and
product_fit use their printed values. Every other constituent value is an ASSUMED class value (ASSUMPTIONS 44).
usage (repo root, after make setup and the system-live step): python3 src/sim/potting_matrix_eval.py [OUT.json]"""
import sys, os, json, math
import numpy as np
from scipy.optimize import brentq

def bruggeman(phases):
    """symmetric Bruggeman effective medium for spherical phases [(vol fraction, property)]: sum f (p - e) / (p + 2 e) = 0"""
    lo = min(p for f, p in phases if f > 0); hi = max(p for f, p in phases if f > 0)
    return brentq(lambda e: sum(f * (p - e) / (p + 2 * e) for f, p in phases if f > 0), lo * 0.999, hi * 1.001)

# constituents: (density g/cc, thermal conductivity W/mK, relative permittivity) - only iM30K is from a data sheet
K = dict(epoxy=dict(rho=(1.10, 1.20), k=(0.18, 0.22), er=(3.5, 4.2), src="ASSUMED class (unfilled casting epoxy)"),
         im30k=dict(rho=(0.57, 0.63), k=(0.20, 0.20), er=(1.2, 2.0), src="3M product information (iM30K density, calculated k; series dielectric constant)"),
         bn=dict(rho=(2.10, 2.28), k=(30.0, 60.0), er=(3.9, 4.2), src="ASSUMED class (hexagonal boron nitride powder)"),
         alumina=dict(rho=(3.8, 3.95), k=(25.0, 35.0), er=(9.0, 10.0), src="ASSUMED class (alumina powder)"),
         silica=dict(rho=(2.2, 2.2), k=(1.3, 1.4), er=(3.8, 3.9), src="ASSUMED class (fumed silica)"))

def mix(fb, ft, fs, therm="bn"):
    fe = 1.0 - fb - ft - fs; out = {}
    for lab, i in (("low", 0), ("high", 1)):
        ph_k = [(fe, K["epoxy"]["k"][i]), (fb, K["im30k"]["k"][i]), (ft, K[therm]["k"][i]), (fs, K["silica"]["k"][i])]
        ph_e = [(fe, K["epoxy"]["er"][i]), (fb, K["im30k"]["er"][i]), (ft, K[therm]["er"][i]), (fs, K["silica"]["er"][i])]
        rho = fe * K["epoxy"]["rho"][i] + fb * K["im30k"]["rho"][i] + ft * K[therm]["rho"][i] + fs * K["silica"]["rho"][i]
        out[lab] = dict(k_W_mK=round(bruggeman(ph_k), 3), er=round(bruggeman(ph_e), 2), rho_g_cc=round(rho, 3))
    return dict(epoxy=round(fe, 3), bubbles=fb, thermal=ft, thermal_powder=therm, silica=fs, **out)

def k_needed_for(target=3.0, therm="bn"):
    """thermal-powder volume fraction that reaches the target conductivity (with 0 % bubbles and 1.5 % silica), Bruggeman, high constituent values"""
    for ft in np.arange(0.05, 0.90, 0.01):
        if mix(0.0, float(ft), 0.015, therm)["high"]["k_W_mK"] >= target: return round(float(ft), 2)
    return None

def coil(er_list):
    cwd = os.getcwd(); os.chdir("work"); sys.path.insert(0, "."); import system_live as SL
    TL = json.load(open("kit_v23/fw_timeline.json"))["inputs"]; g0 = TL["first_gate_us"]; C0 = SL.NS["Cn"]; Cs = 250e-12; res = []
    for lab, er in er_list:
        for phi in (0.3, 0.7):
            SL.NS["Cn"] = C0 + Cs * phi * (er - 1.0); p = SL.tx_point(24.5, "boost", "design"); SL.NS["Cn"] = C0
            res.append(dict(fill=lab, er=er, phi=phi, t_quiet_us=round(p["t_quiet_us"], 3), first_gate_us=g0, margin_us=round(g0 - p["t_quiet_us"], 3)))
    heat = {m: dict(P_clamp_W=round(float(SL.tx_point(24.5, m, "design")["P_RCL_W"]), 2), P_damp_head_W=round(float(SL.tx_point(24.5, m, "design")["P_damp_W"]), 3),
                    P_fet_W=round(SL.tx_point(24.5, m, "design")["i_rms"] ** 2 * SL.TX["Ron"], 3)) for m in ("scan", "boost")}
    os.chdir(cwd); return res, heat, g0

def paint(r=0.044, gate_us=5.91):
    """grounded conductive paint on a closed cavity wall around the axis: decay time of its eddy current, mu0 r / (2 Rs), and the share left at the first gate"""
    mu0 = 4e-7 * math.pi; out = []
    for lab, Rs in (("silver-coated copper paint (ASSUMED 0.01-0.05 ohm/sq)", 0.01), ("", 0.05), ("graphite paint (ASSUMED 10-100 ohm/sq)", 10.0), ("", 100.0)):
        tau = mu0 * r / (2 * Rs) * 1e6
        out.append(dict(coating=lab or out[-1]["coating"], Rs_ohm_sq=Rs, tau_us=round(tau, 4), left_at_first_gate=float(f"{math.exp(-gate_us / tau):.3g}")))
    return out

# owner-supplied manufacturer data sheets (2026-10-28, data/seed/datasheets, DATASHEET_LOG): the values the fit evaluation uses, as printed
TC832 = dict(name="MG Chemicals 832TC thermally conductive epoxy (TDS Ver. 4.3, 04 Feb 2026)", rho=1.7, visc_cP=27000, mix="1:1 by volume", work_h=2.0, shrink_pct=1.4,
             k=0.7, Tg_C=50.0, cte_ppm=(142, 114), shore_D=81, breakdown_V_at_mm=(48300, 3.175), er_1MHz=3.7, df_1MHz=0.1, service_C=(-30, 175),
             cure="96 h at 25 C, or 2 h 65 C / 1 h 80 C / 45 min 100 C", deair="vacuum 25 inHg about 2 min")
NI841 = dict(name="MG Chemicals 841AR Super Shield nickel conductive coating (TDS Rev. 7.0, 17 Sept 2026; older TDS Ver. 2.05, 31 Oct 2017)",
             Rs=[(25, 1.60, "Rev 7.0"), (50, 0.80, "Rev 7.0"), (41, 0.52, "Ver 2.05, 1 coat 1.6 mil"), (102, 0.38, "Ver 2.05, 2 coats 4.0 mil"), (147, 0.29, "Ver 2.05, 3 coats 5.8 mil")],
             resistivity_ohm_cm=4.0e-3, magnetic="ferromagnetic (both); relative permeability >= 100 (Ver 2.05)", service_C=(-40, 120), solvent="acetone, dimethyl carbonate, heptan-2-one (etches ABS / PC; Ver 2.05)",
             adhesion_5B="ABS, PC, polyamide, PVC, FR4 (Rev 7.0); PETG not listed", cure="24 h at 25 C or 30 min at 65 C")
IM30K = dict(name="3M Glass Bubbles iM30K data sheet (owner copy)", crush_psi=27000, rho=0.60, packing=0.60, d_um=18, soften_C=600, flotation=0.90, volatiles_wt=0.005)

def products(r=0.044, gate_us=5.91):
    """fit of the three owner-supplied products, with their printed values: 832TC neat and with 45 vol% iM30K on the coil quiet time; 841AR eddy decay at its
    printed sheet resistances; 832TC dielectric strength against the 460 V flyback nodes and its Tg against the modeled head temperature"""
    er_b = (round(bruggeman([(0.55, TC832["er_1MHz"]), (0.45, K["im30k"]["er"][0])]), 2), round(bruggeman([(0.55, TC832["er_1MHz"]), (0.45, K["im30k"]["er"][1])]), 2))
    k_b = round(bruggeman([(0.55, TC832["k"]), (0.45, K["im30k"]["k"][0])]), 3)
    rho_b = round(0.55 * TC832["rho"] + 0.45 * IM30K["rho"], 3)
    coilres = coil([("832TC neat", TC832["er_1MHz"]), ("832TC + 45 % iM30K (low)", er_b[0]), ("832TC + 45 % iM30K (high)", er_b[1])])[0]
    mu0 = 4e-7 * math.pi
    paint841 = [dict(thick_um=t, Rs_ohm_sq=Rs, src=s, tau_us=round(mu0 * r / (2 * Rs) * 1e6, 4), left_at_first_gate=float(f"{math.exp(-gate_us / (mu0 * r / (2 * Rs) * 1e6)):.3g}"))
                for t, Rs, s in NI841["Rs"]]
    kv_mm = TC832["breakdown_V_at_mm"][0] / TC832["breakdown_V_at_mm"][1] / 1000
    return dict(TC832=TC832, NI841=NI841, IM30K=IM30K, coil=coilres, tc832_bubbles=dict(er=er_b, k_W_mK=k_b, rho_g_cc=rho_b),
                paint841=paint841, tc832_kV_mm=round(kv_mm, 1), hv_node_V=460.0, head_peak_C=50.6)

def main(outp):
    prop = mix(0.45, 0.125, 0.015, "bn"); prop_al = mix(0.45, 0.125, 0.015, "alumina")
    need_bn = k_needed_for(3.0, "bn"); need_al = k_needed_for(3.0, "alumina")
    coilres, heat, g0 = coil([("proposed matrix (low)", prop["low"]["er"]), ("proposed matrix (high)", prop["high"]["er"]), ("proposed with alumina (high)", prop_al["high"]["er"])])
    pcm_J_g = (150.0, 200.0)                                                     # ASSUMED class: microencapsulated paraffin latent heat
    P = heat["boost"]["P_clamp_W"] + heat["boost"]["P_fet_W"]
    pcm = dict(neck_boost_W=round(P, 2), grams_for_10_min=[round(P * 600 / pcm_J_g[1], 1), round(P * 600 / pcm_J_g[0], 1)], latent_J_g_ASSUMED=pcm_J_g,
               note="a phase-change additive only delays the rise; the steady heat still has to leave through the module wall")
    claims = [
     dict(claim="iM30K glass bubbles: real 3M product, 0.6 g/cc, high crush strength", verdict="CONFIRMED", evidence="3M table: 0.60 g/cc (0.57-0.63), 28,000 psi 90 % survival (data sheet Rev C: 27,000)"),
     dict(claim="BN / alumina at 10-15 vol% gives > 3 W/mK", verdict="NOT SUPPORTED",
          evidence=f"Bruggeman with 45 % bubbles: {prop['low']['k_W_mK']}-{prop['high']['k_W_mK']} W/mK (BN), {prop_al['low']['k_W_mK']}-{prop_al['high']['k_W_mK']} (alumina); 3 W/mK needs about {need_bn * 100:.0f} vol% BN or {need_al * 100:.0f} vol% alumina with no bubbles"),
     dict(claim="the mix is invisible to the TX / RX coils (mu_r = 1)", verdict="HALF TRUE", evidence=f"magnetically yes; electrically no: er {prop['low']['er']}-{prop['high']['er']} raises the coil capacitance; injected through the windings the quiet time misses the first gate in every case (see coil)"),
     dict(claim="shrinkage < 0.1 %, zero drift, 100 % moisture barrier", verdict="UNVERIFIED / overstated", evidence="no product data sheet; a rigid epoxy also loads the precision parts (AB1 offsets) and solder joints by CTE mismatch: the soft gel was chosen there for that reason"),
     dict(claim="microballoons damp vibration and remove bump false targets", verdict="PARTLY", evidence="rigid potting stops winding / lead motion (the real microphonic source); glass bubbles in a rigid epoxy add little damping; bump signals from coil-to-ground motion are not removed by any potting"),
     dict(claim="BN removes hot spots on the driver chips in the head", verdict="DOES NOT APPLY", evidence=f"the head has no driver: the FETs and clamp are in the neck module (boost about {P:.1f} W there); the head dissipates 0.67-1.38 W and peaks at 50.6 C at 40 C ambient (limit 80 C)"),
     dict(claim="a single compound filling the whole head with conductive filler would ruin detection", verdict="CONFIRMED", evidence="eddy rule (CLAUDE.md 5): no conductive filler anywhere"),
     dict(claim="paint the circuit cavity with grounded conductive shield paint", verdict="ONLY IF SLIT", evidence="a closed painted wall around the axis is a closed loop (eddy rule 5): see paint; graphite paint decays too fast to matter but shields little; a slit / comb pattern with one ground point keeps the electric shielding and breaks the loop"),
    ]
    pm = json.load(open("data/results/potting_map.json")); vol = {z["zone"].split(" (")[0]: z["cm3"][0] for z in pm["zones"]}
    worst_margin = min(r["margin_us"] for r in coilres)
    EP = prop["high"]["rho_g_cc"]
    zones = [
     dict(zone="TX coil windings (six formers)", epoxy_matrix="NO", use="none (thin SYN end beads only)", why=f"every fill misses the first gate: proposed matrix margin {max(r['margin_us'] for r in coilres)} to {worst_margin} us"),
     dict(zone="L2 analog cell", epoxy_matrix="NO", use="soft gel (GEL)", why="a rigid epoxy loads the AB1 precision op-amps / ADC and the FFC joints by cure shrinkage and CTE mismatch (offset drift); the gel locks without stress"),
     dict(zone="L1 gallery", epoxy_matrix="YES (option)", use="epoxy + glass bubbles (no thermal powder needed)", why="only the RX leads are there: a rigid lock stops lead motion (microphonics); their capacitance change is to be measured (PT3)"),
     dict(zone="L4 absorber cell", epoxy_matrix="NO", use="carbonyl-iron silicone (CI)", why="magnetic absorber function; not a structural fill"),
     dict(zone="NPM hot zone", epoxy_matrix="ONLY AS A HIGH-BN VARIANT", use=f"TC silicone, or epoxy with about {round(need_bn * 100)} vol% BN and no bubbles (3 W/mK class)", why=f"the clamp bank and FETs dissipate about {P:.1f} W at boost; the proposed 12.5 % BN mix models at {prop['low']['k_W_mK']}-{prop['high']['k_W_mK']} W/mK, too low for the hot zone"),
     dict(zone="NPM main zone", epoxy_matrix="YES", use="the proposed mix (epoxy + 45 % iM30K + silica; BN optional)", why=f"structural, waterproof, {EP:.2f} g/cc vs 0.6-0.8 for syntactic silicone: about +{round(vol.get('NPM main zone', 0) * (EP - 0.7), 0):.0f} g"),
     dict(zone="U3 PM2 bay", epoxy_matrix="YES", use="the proposed mix", why=f"locks PM2 and the power leads; about +{round(vol.get('U3 PM2 bay', 0) * (EP - 0.7), 0):.0f} g over syntactic silicone"),
     dict(zone="U1 HB2 pocket", epoxy_matrix="YES", use="the proposed mix", why="the Hall switch reads the magnet through the wall: non-magnetic fill, no change"),
     dict(zone="CB1D / LB1 / SB1R / cap / AU1", epoxy_matrix="NO", use="conformal coat", why="antenna, LED light, RX-coil capacitance, serviceable pads (potting map)"),
     dict(zone="phase-change additive", epoxy_matrix="NPM hot zone only, after PT5", use=f"{pcm['grams_for_10_min'][0]}-{pcm['grams_for_10_min'][1]} g microencapsulated PCM buffers 10 min of boost", why="the head runs cool (peak 50.6 C at 40 C ambient): no head zone needs it; no NPM thermal model exists, so the bench decides"),
     dict(zone="conductive shield paint", epoxy_matrix="ONLY SLIT", use="comb / slit pattern, one ground point, on the CB1D cavity only if a bench test shows pickup; inside the head only a non-magnetic paint (no nickel: MG 841AR is ferromagnetic, see product_fit)", why="a closed painted wall around the axis is a closed eddy loop (rule 5); the copper-cloth septum already screens the analog cell"),
    ]
    pr = products(); pc = {(c["fill"], c["phi"]): c["margin_us"] for c in pr["coil"]}
    m_neat = [pc[("832TC neat", f)] for f in (0.3, 0.7)]; m_bub = [v for (lab, f), v in pc.items() if lab != "832TC neat"]
    t841 = [x["tau_us"] for x in pr["paint841"]]; TC = pr["TC832"]; B = pr["tc832_bubbles"]
    fit = [
     dict(product="3M iM30K glass bubbles", zone="NPM main, U3, U1, L1 gallery (option)", fit="YES (filler)",
          why=f"data sheet: {IM30K['rho']} g/cc, crush {IM30K['crush_psi']} psi at 90 % survival, 18 um: survives hand mixing and vacuum de-airing; lowers density and er of any resin it goes into"),
     dict(product="MG 832TC epoxy", zone="TX coil windings", fit="NO",
          why=f"er {TC['er_1MHz']} (DF {TC['df_1MHz']}) at 1 MHz: quiet-time margin {max(m_neat)} to {min(m_neat)} us neat, {max(m_bub)} to {min(m_bub)} us with 45 % iM30K; all below the first gate"),
     dict(product="MG 832TC epoxy", zone="NPM hot zone", fit="YES (candidate, PT5 decides)",
          why=f"the only fill with a printed conductivity: {TC['k']} W/mK, about twice the proposed bubble mix; dielectric strength {pr['tc832_kV_mm']} kV/mm against the {pr['hv_node_V']:.0f} V flyback nodes (1 mm of fill holds about {pr['tc832_kV_mm'] * 1000 / pr['hv_node_V']:.0f}x); "
              f"Tg only {TC['Tg_C']:.0f} C: above it the epoxy softens and its CTE stays {TC['cte_ppm'][1]} ppm/C (service to {TC['service_C'][1]} C), so PT5 must log the hot-zone temperature; {TC['visc_cP']} cP: pour and vacuum de-air ({TC['deair']}), no needle injection"),
     dict(product="MG 832TC epoxy + 45 vol% iM30K", zone="NPM main, U3 PM2 bay, U1 HB2 pocket", fit="YES (after a trial mix, PT1 / PT7)",
          why=f"modeled er {B['er'][0]}-{B['er'][1]}, k {B['k_W_mK']} W/mK, {B['rho_g_cc']} g/cc (neat 832TC {TC['rho']} g/cc: about {round(vol.get('NPM main zone', 0) * (TC['rho'] - B['rho_g_cc']))} g more in the NPM main zone); "
              "832TC is already filled, so 45 % bubbles on top may not pour: the trial mix decides the bubble fraction (start at 20-30 %)"),
     dict(product="MG 832TC epoxy", zone="L2 analog cell", fit="NO", why=f"Shore {TC['shore_D']} D, {TC['shrink_pct']} % shrinkage, CTE {TC['cte_ppm'][0]} ppm/C: loads the precision parts and joints; the soft gel stays"),
     dict(product="MG 832TC epoxy", zone="L1 gallery", fit="NO (use the bubble mix)", why=f"er {TC['er_1MHz']} next to the RX leads adds lead capacitance; the bubble mix (er {B['er'][0]}-{B['er'][1]}) is the better lock there"),
     dict(product="MG 841AR nickel paint", zone="head: vault, CB1D cavity, anywhere inside the coil field", fit="NO",
          why=f"eddy decay is not the problem (tau {min(t841)}-{max(t841)} us at 0.29-1.6 ohm/sq, gone long before the {g0} us gate); the problem is the nickel: "
              "ferromagnetic, relative permeability >= 100 (Ver 2.05), a magnetic surface the TX field magnetises on every pulse; its remanence and magnetic viscosity are not on either sheet (UNVERIFIED), so it may leave a slow tail in the RX window; the eddy rule (5) forbids a closed painted wall anyway"),
     dict(product="MG 841AR nickel paint", zone="neck module (NPM) inner wall, outside the coil field", fit="YES (option, slit, after PT9)",
          why="screens the 460 V switching node; comb / slit pattern with one ground point (rule 5); PETG adhesion not on the sheet and the acetone solvent etches some plastics: coupon test PT7; PT9 checks the RX tail with a painted coupon at the coil"),
    ]
    out = dict(status="MODELED: effective-medium mixing, transmit model, thin-cylinder eddy decay; constituent values ASSUMED except the 3M iM30K data", constituents=K,
               proposed_bn=prop, proposed_alumina=prop_al, vol_pct_for_3_W_mK=dict(bn=round(need_bn * 100), alumina=round(need_al * 100)), coil=coilres, first_gate_us=g0,
               paint=paint(), heat=heat, phase_change=pcm, claims=claims, zones=zones,
               single_matrix_coverage_cm3=round(sum(vol.get(k, 0) for k in ("L1 gallery", "NPM main zone", "U3 PM2 bay", "U1 HB2 pocket")), 1), total_fill_cm3=round(sum(vol.values()), 1), products=pr, product_fit=fit)
    json.dump(out, open(outp, "w"), indent=1)
    for z in zones: print(f"{z['epoxy_matrix']:26s} {z['zone']:32s} {z['use'][:60]}")
    for c in claims: print(f"{c['verdict']:22s} {c['claim'][:70]:70s} | {c['evidence'][:150]}")
    print("proposed BN mix:", prop); print("coil:", [(r["fill"], r["phi"], r["margin_us"]) for r in coilres]); print("paint:", out["paint"]); print("phase change:", pcm)
    for f in fit: print(f"{f['fit']:34s} {f['product']:32s} {f['zone'][:40]:40s} | {f['why'][:110]}")

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "data/results/potting_matrix_eval.json")
