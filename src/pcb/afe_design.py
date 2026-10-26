#!/usr/bin/env python3
"""
PF233-AB1 analog receiving board: SINGLE SOURCE OF TRUTH
Parts library (symbol pins + land patterns + 3D body) -> netlist -> ERC -> BOM -> KiCad netlist.
IC pin maps marked VERIFY come from memory (no datasheet access in the build environment).
"""
import json, math, datetime
# ------------------------------------------------------------------ parts library
# pads: (number, x, y, w, h, shape)   local coords, mm, y down (KiCad), "front" orientation
def two(dx, w, h): return [("1", -dx, 0, w, h, "roundrect"), ("2", dx, 0, w, h, "roundrect")]
LIB = {
 "R0402": dict(desc="Resistor 0402", fp="Resistor_SMD:R_0402_1005Metric", pins=[("1", "1", "passive"), ("2", "2", "passive")], pads=two(0.51, 0.54, 0.64), body=(1.0, 0.5, 0.35)),
 "C0402": dict(desc="Capacitor 0402", fp="Capacitor_SMD:C_0402_1005Metric", pins=[("1", "1", "passive"), ("2", "2", "passive")], pads=two(0.51, 0.54, 0.64), body=(1.0, 0.5, 0.5)),
 "C0603": dict(desc="Capacitor 0603", fp="Capacitor_SMD:C_0603_1608Metric", pins=[("1", "1", "passive"), ("2", "2", "passive")], pads=two(0.775, 0.8, 0.95), body=(1.6, 0.8, 0.8)),
 "C0805": dict(desc="Capacitor 0805", fp="Capacitor_SMD:C_0805_2012Metric", pins=[("1", "1", "passive"), ("2", "2", "passive")], pads=two(0.95, 1.0, 1.45), body=(2.0, 1.25, 1.0)),
 "BAV199": dict(desc="Low-leakage series diode pair, SOT-23", fp="Package_TO_SOT_SMD:SOT-23",
    pins=[("1", "A1", "passive"), ("2", "K2", "passive"), ("3", "K1/A2", "passive")],
    pads=[("1", -0.9375, -0.95, 1.475, 0.6, "roundrect"), ("2", -0.9375, 0.95, 1.475, 0.6, "roundrect"), ("3", 0.9375, 0, 1.475, 0.6, "roundrect")], body=(2.9, 1.3, 1.1)),
 "SW1G66": dict(desc="SN74LVC1G66 SPST analog switch, SOT-23-5 (VERIFY pinout)", fp="Package_TO_SOT_SMD:SOT-23-5",
    pins=[("1", "A", "passive"), ("2", "B", "passive"), ("3", "GND", "power_in"), ("4", "C", "input"), ("5", "VCC", "power_in")],
    pads=[("1", -1.1375, -0.95, 1.325, 0.6, "roundrect"), ("2", -1.1375, 0, 1.325, 0.6, "roundrect"), ("3", -1.1375, 0.95, 1.325, 0.6, "roundrect"),
          ("4", 1.1375, 0.95, 1.325, 0.6, "roundrect"), ("5", 1.1375, -0.95, 1.325, 0.6, "roundrect")], body=(2.9, 1.6, 1.1)),
 "OPA2211": dict(desc="OPA2211 dual low-noise op amp, SOIC-8", fp="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    pins=[("1", "OUT_A", "output"), ("2", "-IN_A", "input"), ("3", "+IN_A", "input"), ("4", "V-", "power_in"), ("5", "+IN_B", "input"),
          ("6", "-IN_B", "input"), ("7", "OUT_B", "output"), ("8", "V+", "power_in")],
    pads=[("1", -2.7, -1.905, 1.55, 0.6, "roundrect"), ("2", -2.7, -0.635, 1.55, 0.6, "roundrect"), ("3", -2.7, 0.635, 1.55, 0.6, "roundrect"), ("4", -2.7, 1.905, 1.55, 0.6, "roundrect"),
          ("5", 2.7, 1.905, 1.55, 0.6, "roundrect"), ("6", 2.7, 0.635, 1.55, 0.6, "roundrect"), ("7", 2.7, -0.635, 1.55, 0.6, "roundrect"), ("8", 2.7, -1.905, 1.55, 0.6, "roundrect")], body=(4.9, 3.9, 1.6)),
 "ADS8860": dict(desc="ADS8860 16-bit 1 MSPS SAR ADC, MSOP-10 (VERIFY pinout)", fp="Package_SO:MSOP-10_3x3mm_P0.5mm",
    pins=[("1", "REF", "input"), ("2", "AVDD", "power_in"), ("3", "AINP", "input"), ("4", "AINN", "input"), ("5", "GND", "power_in"),
          ("6", "CS", "input"), ("7", "SDO", "output"), ("8", "SCLK", "input"), ("9", "DVDD", "power_in"), ("10", "GND2", "power_in")],
    pads=[("1", -2.15, -1.0, 1.45, 0.3, "roundrect"), ("2", -2.15, -0.5, 1.45, 0.3, "roundrect"), ("3", -2.15, 0, 1.45, 0.3, "roundrect"), ("4", -2.15, 0.5, 1.45, 0.3, "roundrect"), ("5", -2.15, 1.0, 1.45, 0.3, "roundrect"),
          ("6", 2.15, 1.0, 1.45, 0.3, "roundrect"), ("7", 2.15, 0.5, 1.45, 0.3, "roundrect"), ("8", 2.15, 0, 1.45, 0.3, "roundrect"), ("9", 2.15, -0.5, 1.45, 0.3, "roundrect"), ("10", 2.15, -1.0, 1.45, 0.3, "roundrect")], body=(3.0, 3.0, 1.1)),
 "REF5041": dict(desc="REF5041 4.096 V precision reference, MSOP-8 (VERIFY pinout)", fp="Package_SO:MSOP-8_3x3mm_P0.65mm",
    pins=[("1", "DNC1", "no_connect"), ("2", "VIN", "power_in"), ("3", "TEMP", "no_connect"), ("4", "GND", "power_in"), ("5", "TRIM_NR", "passive"),
          ("6", "VOUT", "power_out"), ("7", "DNC2", "no_connect"), ("8", "DNC3", "no_connect")],
    pads=[("1", -2.15, -0.975, 1.45, 0.4, "roundrect"), ("2", -2.15, -0.325, 1.45, 0.4, "roundrect"), ("3", -2.15, 0.325, 1.45, 0.4, "roundrect"), ("4", -2.15, 0.975, 1.45, 0.4, "roundrect"),
          ("5", 2.15, 0.975, 1.45, 0.4, "roundrect"), ("6", 2.15, 0.325, 1.45, 0.4, "roundrect"), ("7", 2.15, -0.325, 1.45, 0.4, "roundrect"), ("8", 2.15, -0.975, 1.45, 0.4, "roundrect")], body=(3.0, 3.0, 1.1)),
 "OPA2365": dict(desc="OPA2365 dual RRIO op amp, MSOP-8", fp="Package_SO:MSOP-8_3x3mm_P0.65mm",
    pins=[("1", "OUT_A", "output"), ("2", "-IN_A", "input"), ("3", "+IN_A", "input"), ("4", "V-", "power_in"), ("5", "+IN_B", "input"), ("6", "-IN_B", "input"), ("7", "OUT_B", "output"), ("8", "V+", "power_in")],
    pads=[("1", -2.15, -0.975, 1.45, 0.4, "roundrect"), ("2", -2.15, -0.325, 1.45, 0.4, "roundrect"), ("3", -2.15, 0.325, 1.45, 0.4, "roundrect"), ("4", -2.15, 0.975, 1.45, 0.4, "roundrect"),
          ("5", 2.15, 0.975, 1.45, 0.4, "roundrect"), ("6", 2.15, 0.325, 1.45, 0.4, "roundrect"), ("7", 2.15, -0.325, 1.45, 0.4, "roundrect"), ("8", 2.15, -0.975, 1.45, 0.4, "roundrect")], body=(3.0, 3.0, 1.1)),
}
def ffc(n):
    pins = [(str(i + 1), str(i + 1), "passive") for i in range(n)] + [("MH1", "SHELL1", "passive"), ("MH2", "SHELL2", "passive")]
    pads = [(str(i + 1), (i - (n - 1) / 2) * 0.5, 0.0, 0.3, 1.3, "roundrect") for i in range(n)]
    hw = (n - 1) / 4 + 1.6
    pads += [("MH1", -hw, -1.5, 1.8, 1.6, "roundrect"), ("MH2", hw, -1.5, 1.8, 1.6, "roundrect")]
    return dict(desc=f"FFC/FPC connector {n}-pos 0.5 mm (Hirose FH12-{n}S-0.5SH class, VERIFY land pattern)", fp=f"Connector_FFC-FPC:Hirose_FH12-{n}S-0.5SH_1x{n}-1MP_P0.50mm_Horizontal",
                pins=pins, pads=pads, body=((n - 1) * 0.5 + 5.0, 3.6, 1.0))
def hdr(rows, cols, pitch=1.27):
    n = rows * cols; pins = [(str(i + 1), str(i + 1), "passive") for i in range(n)]
    pads = []
    for i in range(n):
        if cols == 1: x, y = 0.0, (i - (n - 1) / 2) * pitch
        else: k, c = divmod(i, 2); x, y = (c - 0.5) * pitch, (k - (rows - 1) / 2) * pitch
        pads.append((str(i + 1), x, y, 1.10, 1.10, "circle"))      # 1.10 mm pad on the 0.65 mm drill: 0.225 mm ring (floor 0.18), pad gap 0.17 mm (clearance floor 0.16); was 1.00 (0.175 ring, OPEN_ITEMS 33)
    return dict(desc=f"{cols}x{rows} through-hole header/solder pads {pitch} mm, drill 0.65", fp=f"Connector_PinHeader_1.27mm:PinHeader_{cols}x{rows if cols==1 else rows}_P1.27mm", pins=pins, pads=pads, body=(cols * pitch + 1.5, rows * pitch + 1.5, 4.0), tht=True, drill=0.65)
LIB["HDR1x8"] = hdr(8, 1); LIB["HDR1x6"] = hdr(6, 1); LIB["HDR2x6"] = hdr(6, 2)
for _n in (6, 8, 10, 12, 16): LIB[f"FFC{_n}"] = ffc(_n)

import os
BOARD = os.environ.get("BOARD", "A")
CFG = {"A": dict(ch=["GX", "GY", "X8"], opamp={"GX": ("U1", "A"), "GY": ("U1", "B"), "X8": ("U2", "A")}, opamps=["U1", "U2"], spare=("U2", "B"),
                 j1=["GX+", "GY+", "X8+", "GX-", "GY-", "X8-", "SHLD", "SHLD"], j2=["+5VA", "GND", "+3V3D", "GND", "SCLK", "CS", "SDO1", "SDO2", "SDO3", "BLANK", "GND", "GND"]),
       "B": dict(ch=["Y8", "MONO"], opamp={"Y8": ("U1", "A"), "MONO": ("U1", "B")}, opamps=["U1"], spare=None,
                 j1=["Y8+", "Y8-", "SHLD", "SHLD", "SHLD", "SHLD"], j2=["+5VA", "GND", "+3V3D", "GND", "SCLK", "CS", "SDO1", "SDO2", "BLANK", "MONO_IN", "VCM_OUT", "GND"])}[BOARD]
PARTS = []; NETS = {}
def add(ref, typ, value, mpn="", **kw): PARTS.append(dict(ref=ref, type=typ, value=value, mpn=mpn, **kw))
def net(name, *pins):
    NETS.setdefault(name, [])
    for p in pins: NETS[name].append((p[0], str(p[1])))
CH = CFG["ch"]; OPAMP_OF = CFG["opamp"]
RS = {"GX": 100, "GY": 100, "X8": 1000, "Y8": 1000, "MONO": 1000}
J1PIN = {nm: i + 1 for i, nm in enumerate(CFG["j1"]) if nm != "SHLD"}
J2PIN = {}
for i, nm in enumerate(CFG["j2"]): J2PIN.setdefault(nm if nm not in J2PIN else f"{nm}{i}", i + 1)
J1N, J2N = len(CFG["j1"]), len(CFG["j2"])
add("J1", f"HDR1x{J1N}", f"Antenna harness {J1N}p solder pads 1.27mm", "solder-in ribbon harness (36 AWG)")
add("J2", "HDR2x6", "Main-board 2x6 1.27mm header", "Samtec FTSH/TMM-106-class 2x6 1.27mm")
for k, ch in enumerate(CH, 1):
    ref_u, half = OPAMP_OF[ch]; A = half == "A"
    pin = lambda a, b: a if A else b
    add(f"RS{k}", "R0402", f"{RS[ch]}", "thin-film 0.1% 0402", channel=ch)
    add(f"D{k}", "BAV199", "BAV199", "Nexperia BAV199", channel=ch)
    add(f"SW{k}", "SW1G66", "74LVC1G66", "TI SN74LVC1G66DBVR", channel=ch)
    add(f"CSW{k}", "C0402", "100n", "X7R 10V", channel=ch)
    add(f"RG{k}", "R0402", "10", "thin-film 0.1%", channel=ch)
    add(f"RF{k}", "R0402", "390", "thin-film 0.1%", channel=ch)
    add(f"CF{k}", "C0402", "22p", "C0G 50V", channel=ch)
    add(f"RAAF{k}", "R0402", "200", "thin-film 0.1%", channel=ch)
    add(f"CAAF{k}", "C0603", "2n2", "C0G 50V", channel=ch)
    add(f"UA{k}", "ADS8860", "ADS8860", "TI ADS8860IDGSR", channel=ch)
    add(f"CAV{k}", "C0402", "100n", "X7R 10V", channel=ch)
    add(f"CDV{k}", "C0402", "100n", "X7R 10V", channel=ch)
    add(f"CRF{k}", "C0805", "10u", "X7R/X5R 10V", channel=ch)
    if ch == "MONO": net(f"RAW_{ch}", ("J2", J2PIN["MONO_IN"]), (f"RS{k}", 1))
    else: net(f"RAW_{ch}", ("J1", J1PIN[ch + "+"]), (f"RS{k}", 1))
    net(f"IN_{ch}", (f"RS{k}", 2), (f"D{k}", 3), (f"SW{k}", 1), (ref_u, pin(3, 5)))
    net("GND", (f"D{k}", 1), (f"SW{k}", 3), (f"CSW{k}", 2)); net("+5VA", (f"D{k}", 2), (f"SW{k}", 5), (f"CSW{k}", 1))
    net("VCM", (f"SW{k}", 2)); net("BLANK", (f"SW{k}", 4))
    net(f"FB_{ch}", (ref_u, pin(2, 6)), (f"RG{k}", 1), (f"RF{k}", 1), (f"CF{k}", 1)); net("VCM", (f"RG{k}", 2))
    net(f"OUT_{ch}", (ref_u, pin(1, 7)), (f"RF{k}", 2), (f"CF{k}", 2), (f"RAAF{k}", 1))
    net(f"ADCIN_{ch}", (f"RAAF{k}", 2), (f"CAAF{k}", 1), (f"UA{k}", 3))
    net("GND", (f"CAAF{k}", 2), (f"UA{k}", 4), (f"UA{k}", 5), (f"UA{k}", 10), (f"CAV{k}", 2), (f"CDV{k}", 2), (f"CRF{k}", 2))
    net("VREF", (f"UA{k}", 1), (f"CRF{k}", 1)); net("+5VA", (f"UA{k}", 2), (f"CAV{k}", 1)); net("+3V3D", (f"UA{k}", 9), (f"CDV{k}", 1))
    net("SCLK", (f"UA{k}", 8)); net("CS", (f"UA{k}", 6)); net(f"SDO{k}", (f"UA{k}", 7), ("J2", J2PIN[f"SDO{k}"]))
    if ch != "MONO": net("VCM", ("J1", J1PIN[ch + "-"]))
for n, ref in enumerate(CFG["opamps"], 1):
    add(ref, "OPA2211", "OPA2211", "TI OPA2211AIDR"); add(f"CO{n}", "C0402", "100n", "X7R 10V")
    net("+5VA", (ref, 8), (f"CO{n}", 1)); net("GND", (ref, 4), (f"CO{n}", 2))
if CFG["spare"]:
    ref = CFG["spare"][0]; net("VCM", (ref, 5)); net(f"SPARE_OUT_{ref}", (ref, 6), (ref, 7))
add("CB1", "C0805", "10u", "X7R/X5R 10V"); net("+5VA", ("CB1", 1)); net("GND", ("CB1", 2))
add("UR", "REF5041", "REF5041", "TI REF5041AIDGKR"); add("CRI", "C0603", "1u", "X7R 10V"); add("CRO", "C0603", "1u", "X7R 10V"); add("CRN", "C0603", "1u", "X7R 10V")
net("+5VA", ("UR", 2), ("CRI", 1)); net("GND", ("UR", 4), ("CRI", 2), ("CRO", 2), ("CRN", 2))
net("VREF_RAW", ("UR", 6), ("CRO", 1)); net("NR", ("UR", 5), ("CRN", 1))
add("UB", "OPA2365", "OPA2365", "TI OPA2365AIDGKR"); add("CBD", "C0402", "100n", "X7R 10V")
net("+5VA", ("UB", 8), ("CBD", 1)); net("GND", ("UB", 4), ("CBD", 2))
net("VREF_RAW", ("UB", 3)); net("VREF", ("UB", 2), ("UB", 1))
add("RD1", "R0402", "10k", "thin-film 0.1%"); add("RD2", "R0402", "10k", "thin-film 0.1%"); add("CDF", "C0402", "100n", "X7R 10V"); add("CVM", "C0603", "1u", "X7R 10V")
net("VREF_RAW", ("RD1", 1)); net("VCM_DIV", ("RD1", 2), ("RD2", 1), ("CDF", 1), ("UB", 5)); net("GND", ("RD2", 2), ("CDF", 2), ("CVM", 2))
net("VCM", ("UB", 6), ("UB", 7), ("CVM", 1))
if "VCM_OUT" in J2PIN: net("VCM", ("J2", J2PIN["VCM_OUT"]))
for i, nm in enumerate(CFG["j2"]):
    pin = i + 1
    if nm == "GND": net("GND", ("J2", pin))
    elif nm in ("+5VA", "+3V3D", "SCLK", "CS", "BLANK"): net(nm, ("J2", pin))
for i, nm in enumerate(CFG["j1"]):
    if nm == "SHLD": net("GND", ("J1", i + 1))
# de-duplicate pins inside each net
for k in NETS: NETS[k] = list(dict.fromkeys(NETS[k]))
BYREF = {p["ref"]: p for p in PARTS}

def pin_info(ref, num):
    for n, name, typ in LIB[BYREF[ref]["type"]]["pins"]:
        if str(n) == str(num): return name, typ
    raise KeyError((ref, num))
def erc():
    errs, warns = [], []
    refs = [p["ref"] for p in PARTS]
    if len(set(refs)) != len(refs): errs.append("duplicate reference designators")
    owner = {}
    for n, pins in NETS.items():
        for pr in pins:
            if pr in owner and owner[pr] != n: errs.append(f"pin {pr} in two nets: {owner[pr]} and {n}")
            owner[pr] = n
            try: pin_info(*pr)
            except KeyError: errs.append(f"net {n}: unknown pin {pr}")
    for p in PARTS:
        for num, name, typ in LIB[p["type"]]["pins"]:
            if (p["ref"], num) not in owner and typ != "no_connect": errs.append(f"unconnected pin {p['ref']}.{name}({num})")
    for n, pins in NETS.items():
        if len(pins) < 2 and n not in ("SPARE_OUT",): errs.append(f"net {n} has a single pin {pins}")
        outs = [pr for pr in pins if pin_info(*pr)[1] in ("output", "power_out")]
        if len(outs) > 1 and not all(o[0] == outs[0][0] for o in outs): errs.append(f"net {n}: multiple drivers {outs}")
    # power-pin sanity: every IC supply pin on a supply net, every IC has a decoupling cap on its supply net
    sup = {"V+": "+5VA", "AVDD": "+5VA", "DVDD": "+3V3D", "VCC": "+5VA", "VIN": "+5VA", "V-": "GND", "GND": "GND", "GND2": "GND", "EP": "GND"}
    for p in PARTS:
        for num, name, typ in LIB[p["type"]]["pins"]:
            if name in sup and owner.get((p["ref"], num)) != sup[name]: errs.append(f"{p['ref']}.{name} on {owner.get((p['ref'], num))}, expected {sup[name]}")
    DEC = {}
    for k in range(1, len(CH) + 1): DEC[f"SW{k}"] = [(f"CSW{k}", "+5VA")]; DEC[f"UA{k}"] = [(f"CAV{k}", "+5VA"), (f"CDV{k}", "+3V3D")]
    for n, ref in enumerate(CFG["opamps"], 1): DEC[ref] = [(f"CO{n}", "+5VA")]
    DEC["UR"] = [("CRI", "+5VA")]; DEC["UB"] = [("CBD", "+5VA")]
    for ic, caps in DEC.items():
        for cref, supply in caps:
            if cref not in BYREF or owner.get((cref, "1")) != supply or owner.get((cref, "2")) != "GND": errs.append(f"decoupling {cref} for {ic} not between {supply} and GND")
    for p in PARTS:
        if p["type"] in ("OPA2211", "ADS8860", "SW1G66", "OPA2365", "REF5041") and p["ref"] not in DEC: errs.append(f"{p['ref']} has no decoupling rule")
    # gain / bias sanity
    g = 1 + 390 / 10
    warns.append(f"stage gain {g:.0f} (non-inverting, referenced to VCM)")
    return errs, warns
def bom():
    rows = {}
    for p in PARTS:
        key = (p["type"], p["value"], p["mpn"]); rows.setdefault(key, []).append(p["ref"])
    return [dict(qty=len(r), refs=",".join(r), type=k[0], value=k[1], mpn=k[2], footprint=LIB[k[0]]["fp"]) for k, r in sorted(rows.items())]
def kicad_netlist(path):
    lines = ['(export (version "E")', f'  (design (source "PF233-AB1.net") (date "{datetime.date.today()}") (tool "afe_design.py"))', "  (components"]
    for p in PARTS:
        lib = LIB[p["type"]]
        lines.append(f'    (comp (ref "{p["ref"]}") (value "{p["value"]}") (footprint "{lib["fp"]}") (libsource (lib "PF233") (part "{p["type"]}") (description "{lib["desc"]}")) (property (name "MPN") (value "{p["mpn"]}")) (tstamps "{sum(ord(c) * 31 ** i for i, c in enumerate(p["ref"])) % 16**8:08x}"))')
    lines.append("  )"); lines.append("  (nets")
    for i, (n, pins) in enumerate(sorted(NETS.items()), 1):
        lines.append(f'    (net (code "{i}") (name "{n}")')
        for ref, num in pins: lines.append(f'      (node (ref "{ref}") (pin "{num}") (pinfunction "{pin_info(ref, num)[0]}"))')
        lines.append("    )")
    lines.append("  )"); lines.append(")")
    open(path, "w").write("\n".join(lines))
if __name__ == "__main__":
    e, w = erc(); print("parts", len(PARTS), "nets", len(NETS), "ERC errors", len(e)); [print("  E:", x) for x in e[:20]]; [print("  W:", x) for x in w]
    print("BOM lines", len(bom()))
