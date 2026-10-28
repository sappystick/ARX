#!/usr/bin/env python3
"""Whole-system operating model for the interactive viewer (viewer_r2): TX pulse, power draw and runtime, rails, wiring runs, vault temperature.
MODELED, nothing measured. The browser runs the same equations in JavaScript (src/render/viewer_r2.html, "sim" block); this script is the reference: it writes
the model inputs the page needs and a grid of GOLDEN cases that tests/regress.py replays through the page's JavaScript (node) and compares.
Sources (no new physics here):
  TX turn-off and on-time: tx_vbus_sweep.py pulse() / ton_loop() (same topology and values as sim_head1.py; ASSUMPTIONS 28)
  supply energy per pulse = V x Q drawn from the bulk bank during the ramp (dissipative clamp: none of it comes back)
  rails: system_budget.py rows (+5V: LED firmware cap, logic estimate, AMS1117 input, +5VA analog from the TI OPA2211 / OPA2365 IQ maxima)
  converter efficiency 0.85 for both modules: the factor system_budget.py already uses for the cord current (ASSUMED, ASSUMPTIONS 38)
  M12 load other than the gate drive: not budgeted (ASSUMPTIONS 29), an input here, default 0.10 W (ASSUMED)
  pack: 7S1P Molicel P30B, 7 x 3.6 V x 3.0 Ah = 75.6 Wh (system_budget.py), used to the BMS cut-off
  wiring: HARNESS_MASTER_v3.csv lengths; copper resistivity 1.72e-8 ohm m at 20 C (pb1r_check / power_system value) on the AWG nominal area
    A = pi/4 (0.127 mm x 92^((36 - n) / 39))^2; TX layer leads from tx_system.json (litz)
  vault temperature: linear fit of the sim_thermal.json hot spot rise against the dissipated power (an interpolation of that model, not a new one)
usage (in work/): python3 system_live.py [OUT.json]"""
import json, math, csv, sys, os
import numpy as np
src = open("tx_vbus_sweep.py").read().split("out = dict(")[0]; NS = {}; exec(src, NS)            # pulse(), ton_loop(), constants: the stored sweep's own code
pulse, ton_loop, peak_current = NS["pulse"], NS["ton_loop"], NS["peak_current"]
L, R_LOOP, C_BULK = NS["L"], NS["R_LOOP"], NS["C_BULK_NOM"] * NS["C_BULK_TOL"]
TX = dict(L=L, Rc=NS["Rc"], Cn=NS["Cn"], Rd=NS["Rd"], Vf=NS["Vf"], Ron=NS["Ron"], RCL=NS["RCL"], R_loop=R_LOOP, C_bulk=C_BULK, Vk=462.0)
MODES = {"scan": dict(I=8.0, f=800.0), "mid": dict(I=14.0, f=600.0), "boost": dict(I=20.0, f=400.0)}       # tx_vbus_sweep ton_rule operating points
CAPS = {"design": dict(CL=100e-9, derate=False, label="1 x 100 nF C0G/film (design)"), "asbuilt": dict(CL=200e-9, derate=True, label="2 x 100 nF X7R, DC-bias derated (as built)")}
PACK = dict(Wh=7 * 3.6 * 3.0, V_min=19.6, V_max=29.4)
ETA = 0.85
I5 = dict(led_cap=0.35, logic=0.15, ams_in=2 * (0.023 + 0.0041) + 3.3 / 270.0 + 0.011, analog_5va=6 * 0.006 + 4 * 0.005)  # system_budget.py terms (A)
QG, VG = 90e-9, 12.0                                                                       # 2 x 45 nC at 12 V (system_budget TC4420 row)
LIMITS = dict(Vds=650.0, clamp_rule=630.0, diode_VRRM=600.0, RCL_W=10.0, droop_pct=5.0, rail5_A=1.5, vault_C=80.0, cord_A=5.0)
RHO = 1.72e-8
def awg_area_m2(n): d = 0.127e-3 * 92 ** ((36 - n) / 39); return math.pi / 4 * d * d

def tx_supply(V, mode, L_scale=1.0, R_scale=1.0):
    """on-time and charge per pulse from the bulk bank (fast: no turn-off simulation); P_tx = V Q f"""
    m = MODES[mode]; ton, Q = ton_loop(m["I"], V, R=R_LOOP * R_scale, C=C_BULK, Lc=L * L_scale); return ton, Q, V * Q * m["f"]

def tx_point(V, mode, cap, L_scale=1.0, R_scale=1.0):
    m, c = MODES[mode], CAPS[cap]
    ton, Q, _ = tx_supply(V, mode, L_scale, R_scale)
    NS["L"] = L * L_scale                                                                  # pulse() reads the module L
    p = pulse(m["I"], c["CL"], V, f=m["f"], derate=c["derate"], ton=ton); NS["L"] = L
    E = V * Q
    return dict(ton_us=ton * 1e6, Q_uC=Q * 1e6, droop_pct=Q / C_BULK / V * 100, E_mJ=E * 1e3, P_tx_W=E * m["f"], Vds_peak=p["Vds_peak"], vc_peak=p["vc_peak"],
                t_zero_us=p["t_zero_us"], t_quiet_us=p["t_quiet_us"], P_RCL_W=p["P_RCL_W"], P_damp_W=p["P_damp_W"], i_diode_pk=p["peak_i_diode"],
                i_rms=m["I"] * math.sqrt(ton * m["f"] / 3))

def power(V, mode, tx, led_A=I5["led_cap"], m12_W=0.10):
    f = MODES[mode]["f"]; i5 = led_A + I5["logic"] + I5["ams_in"] + I5["analog_5va"]
    P5 = 5.0 * i5 / ETA; P12 = (QG * VG * f + m12_W) / ETA; P = tx["P_tx_W"] + P5 + P12
    return dict(I5_A=i5, P5_W=P5, P12_W=P12, P_total_W=P, I_batt_A=P / V, hours=PACK["Wh"] / P)

def thermal_fit():
    T = json.load(open("kit_v22/sim_thermal.json")) if os.path.exists("kit_v22/sim_thermal.json") else json.load(open("../data/results/sim_thermal.json"))
    pts = [(v["total_W"], v["max_C"] - (25.0 if "25 C" in k else 40.0)) for k, v in T.items()]
    W = np.array([p[0] for p in pts]); dT = np.array([p[1] for p in pts]); k = float(np.sum(W * dT) / np.sum(W * W))            # through the origin
    # the rest of the vault inventory (CB1D parts, AB1, ...) = total minus the named damping and LED watts of each case; LED heat per LED electrical watt from the worst case (0.5 W at the 0.35 A cap)
    rest = []
    for kk, v in T.items():
        m = re.search(r"damping ([\d.]+) W, LED ([\d.]+) W", kk) or re.search(r"LED ([\d.]+) W", kk)
        if m and m.re.groups == 2: rest.append(v["total_W"] - float(m.group(1)) - float(m.group(2)))
    return dict(K_per_W=k, points=[[round(a, 3), round(b, 2)] for a, b in pts], max_dev_K=float(np.max(np.abs(dT - k * W))), rest_W=round(float(np.mean(rest)), 3),
                led_heat_per_W=round(0.5 / (5.0 * I5["led_cap"]), 4), note="vault W = damping chain + rest_W + LED heat; LED heat scaled so the 0.35 A cap gives the 0.5 W worst case of sim_thermal (ASSUMED)")

BOARDS = ("PM2", "PB1R", "CB1D", "TXJ1", "LB1", "HB2", "HTA", "AB1A", "AB1B", "SB1R-QA", "SB1R-QB")
def node(t):
    """harness end -> diagram node: the board named first, else the part the text names"""
    t0 = t.split("->")[0].strip()
    for b in BOARDS:
        if t0.startswith(b + ".") or t0.startswith(b + " "): return b
    low = t.lower()
    if "npm" in low: return "PB1R"
    if "former" in low: return "FORMERS"
    if "mt60" in low or "battery pack" in low: return "PACK"
    if "power switch" in low: return "SWITCH"
    if "antenna board" in low: return "HTA"
    if "txj1" in low: return "TXJ1"
    for b in BOARDS:
        if b in t: return b
    return "OTHER"

def wiring():
    tx = json.load(open("kit_v22/tx_system.json")) if os.path.exists("kit_v22/tx_system.json") else json.load(open("../data/results/tx_system.json"))
    leadR = {(l["layer"], l["lead"]): l["R_mohm"] * 1e-3 for l in tx["leads"]}
    p = "HARNESS_MASTER_v3.csv" if os.path.exists("HARNESS_MASTER_v3.csv") else "../data/results/HARNESS_MASTER_v3.csv"
    out = []
    for r in csv.DictReader(open(p)):
        spec = r["spec"]; L_m = float(r["length_m"]); sig = r["signal"]; R = None; src = ""
        m = re.search(r"AWG\s?(\d+)", spec)
        lm = re.match(r"TX layer (\d) lead ([AB])", sig)
        if lm: R = leadR[(int(lm.group(1)), lm.group(2))]; src = "tx_system.json lead"
        elif m: R = RHO * L_m / awg_area_m2(int(m.group(1))); src = f"AWG{m.group(1)} copper"
        load = ("battery" if r["id"] in ("W001", "W002", "W060", "W061") else "coil" if r["id"] in ("W033", "W034") else "layer" if lm else
                "led5" if r["id"] in ("W036", "W037") else None)
        out.append(dict(a=node(r["from (board.connector.pin)"]), b=node(r["to (board.connector.pin)"]), id=r["id"], signal=sig, frm=r["from (board.connector.pin)"], to=r["to (board.connector.pin)"], spec=spec, length_m=L_m, R_ohm=R, R_src=src, load=load,
                        hv="flyback" in sig.lower() or "DRAIN" in sig or bool(lm) or r["id"] in ("W033", "W034", "W058")))
    return out
import re

def main(outp):
    th = thermal_fit(); wires = wiring()
    golden = []
    for V in (19.6, 24.5, 29.4):
        for mode in MODES:
            for cap in CAPS:
                t = tx_point(V, mode, cap); pw = power(V, mode, t); golden.append(dict(V=V, mode=mode, cap=cap, L_scale=1.0, R_scale=1.0, **{k: round(v, 4) for k, v in {**t, **pw}.items()}))
    for (V, mode, cap, Ls, Rs) in ((24.5, "boost", "design", 1.05, 1.0), (24.5, "boost", "design", 0.95, 1.25), (19.6, "boost", "asbuilt", 1.0, 1.25)):
        t = tx_point(V, mode, cap, Ls, Rs); pw = power(V, mode, t); golden.append(dict(V=V, mode=mode, cap=cap, L_scale=Ls, R_scale=Rs, **{k: round(v, 4) for k, v in {**t, **pw}.items()}))
    ref = json.load(open("kit_v23/tx_vbus.json")) if os.path.exists("kit_v23/tx_vbus.json") else None
    chk = []
    if ref:                                                                                  # the stored sweep at the same points must come back (same code, same inputs)
        for r in ref["tx_stage_vs_vbus"]:
            cap = "design" if not r["derated"] else "asbuilt"; g = next((x for x in golden if x["V"] == r["Vbus"] and x["mode"] == "boost" and x["cap"] == cap and x["L_scale"] == 1.0 and x["R_scale"] == 1.0), None)
            if g: chk.append(dict(V=r["Vbus"], cap=cap, Vds_sweep=round(r["Vds_peak"], 2), Vds_live=g["Vds_peak"], note="the sweep uses ton = L I / V; the live model uses the loop on-time, so a small difference is expected"))
    # board links that are not harness rows (B5 FFC CB1D JA/JB -> AB1A/AB1B J2): +5VA analog and +3V3D ADC current per board, from the system_budget terms
    links = [dict(a="CB1D", b="AB1A", id="FFC-A", signal="+5VA / +3V3D / SPI (FFC, B5)", I_A=round(2 * 2 * 0.0045 + 2 * 0.005 + (0.023 + 0.0041), 4), note="2 x OPA2211 + OPA2365 max IQ + one AD7389-4 operational max"),
             dict(a="CB1D", b="AB1B", id="FFC-B", signal="+5VA / +3V3D / SPI (FFC, B5)", I_A=round(1 * 2 * 0.0045 + 2 * 0.005 + (0.023 + 0.0041), 4), note="OPA2211 + OPA2365 max IQ + one AD7389-4 operational max")]
    out = dict(model="system_live r1", links=links, status="MODELED", tx=TX, modes=MODES, caps={k: dict(CL=v["CL"], derate=v["derate"], label=v["label"]) for k, v in CAPS.items()}, pack=PACK, eta=ETA,
               i5=I5, gate=dict(Qg=QG, Vg=VG), limits=LIMITS, thermal=th, wires=wires, golden=golden, check_vs_sweep=chk,
               sources=["tx_vbus_sweep.py pulse()/ton_loop()", "system_budget.py rail terms", "TI SBOS377L / SBOS365G IQ", "sim_thermal.json (linear fit)", "HARNESS_MASTER_v3.csv", "tx_system.json"])
    json.dump(out, open(outp, "w"), indent=1, default=float)
    b = [g for g in golden if g["mode"] == "boost" and g["cap"] == "design" and g["V"] == 24.5][0]; s = [g for g in golden if g["mode"] == "scan" and g["cap"] == "design" and g["V"] == 24.5][0]
    print(f"system_live: {len(golden)} golden cases, {len(wires)} wires; at 24.5 V scan {s['P_total_W']:.2f} W {s['hours']:.1f} h, boost {b['P_total_W']:.2f} W {b['hours']:.1f} h; vault fit {th['K_per_W']:.2f} K/W (max dev {th['max_dev_K']:.2f} K)")

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "kit_v23/system_live.json")
