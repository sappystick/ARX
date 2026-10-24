#!/usr/bin/env python3
"""
PF233-PM1 (battery power path / protection / hot-swap OR-ing)  and  PF233-PB1 (TX driver power stage) design database.
Select with env PW=M (PM1) or PW=T (PB1); PW=P (PM2, battery dock power path) and PW=G (HB2, grip board without joystick) are the upper-assembly v1 boards.  API mirrors afe_design (PARTS, NETS, LIB, BYREF, erc(), bom(), kicad_netlist()).
Pin maps / land patterns for ICs and power packages are from memory -> VERIFY list in the build report.
"""
import os, datetime
PW = os.environ.get("PW", "M"); BOARD = PW; CH = []
def pads2(dx, w, h, shape="roundrect"): return [("1", -dx, 0, w, h, shape), ("2", dx, 0, w, h, shape)]
def pair(desc, fp, dx, w, h, body, names=("1", "2"), types=("passive", "passive")):
    return dict(desc=desc, fp=fp, pins=[("1", names[0], types[0]), ("2", names[1], types[1])], pads=pads2(dx, w, h), body=body)
def tht(n, pitch, rows=1, dia=1.7, drill=1.0, desc="header"):
    pins = [(str(i + 1), str(i + 1), "passive") for i in range(n * rows)]; pads = []
    for i in range(n * rows):
        if rows == 1: x, y = 0.0, (i - (n - 1) / 2) * pitch
        else: k, c = divmod(i, 2); x, y = (c - 0.5) * pitch, (k - (n - 1) / 2) * pitch
        pads.append((str(i + 1), x, y, dia, dia, "circle"))
    return dict(desc=f"{desc} {rows}x{n} pitch {pitch}", fp=f"Connector:{desc.replace(' ', '_')}_{rows}x{n}_P{pitch}mm", pins=pins, pads=pads, body=(rows * pitch + 1.5, n * pitch + 1.5, 9.0), tht=True, drill=drill)
LIB = {
 "R0603": pair("Resistor 0603", "Resistor_SMD:R_0603_1608Metric", 0.825, 0.8, 0.95, (1.6, 0.8, 0.5)),
 "R1206": pair("Resistor 1206", "Resistor_SMD:R_1206_3216Metric", 1.5, 1.2, 1.8, (3.2, 1.6, 0.6)),
 "R2512": pair("Resistor 2512 (1-3 W)", "Resistor_SMD:R_2512_6332Metric", 3.1, 1.6, 3.4, (6.3, 3.2, 0.7)),
 "C0603": pair("Capacitor 0603", "Capacitor_SMD:C_0603_1608Metric", 0.775, 0.8, 0.95, (1.6, 0.8, 0.8)),
 "C0805": pair("Capacitor 0805", "Capacitor_SMD:C_0805_2012Metric", 0.95, 1.0, 1.45, (2.0, 1.25, 1.0)),
 "C1210": pair("Capacitor 1210", "Capacitor_SMD:C_1210_3225Metric", 1.5, 1.2, 2.7, (3.2, 2.5, 2.0)),
 "CAN10": pair("SMD aluminium/hybrid can 10x10", "Capacitor_SMD:CP_Elec_10x10", 4.4, 4.0, 2.6, (10.3, 10.3, 10.5), ("+", "-")),
 "FUSE1812": pair("SMD fuse 1812 (6.1x2.7)", "Fuse:Fuse_1812_4532Metric", 2.9, 2.0, 3.4, (4.5, 3.2, 1.8)),
 "DSMC": pair("Diode SMC (DO-214AB)", "Diode_SMD:D_SMC", 3.4, 2.4, 3.4, (7.1, 6.1, 2.4), ("K", "A")),
 "DSMB": pair("Diode SMB (DO-214AA)", "Diode_SMD:D_SMB", 2.2, 2.0, 2.4, (4.6, 3.6, 2.4), ("K", "A")),
 "DSOD": pair("Signal diode SOD-123", "Diode_SMD:D_SOD-123", 1.35, 0.9, 1.2, (2.7, 1.6, 1.1), ("K", "A")),
 "FB1812": pair("Ferrite bead 1812 (>=6 A)", "Inductor_SMD:L_1812_4532Metric", 2.9, 2.0, 3.4, (4.5, 3.2, 2.5)),
 "WIRE2": dict(desc="two solder pads for an external power resistor (wire/lug), 5.08 mm", fp="Connector:SolderPad_2x_P5.08mm", pins=[("1", "1", "passive"), ("2", "2", "passive")],
               pads=[("1", -2.54, 0, 3.0, 3.0, "circle"), ("2", 2.54, 0, 3.0, 3.0, "circle")], body=(8.0, 3.5, 3.0), tht=True, drill=1.6),
 "TERM4": tht(4, 5.08, 1, 3.0, 1.7, "Terminal block"), "TERM2": tht(2, 5.08, 1, 3.0, 1.7, "Terminal block"),
 "HDR1x3": tht(3, 2.54, 1, 1.8, 1.0, "Pin header"), "HDR1x5": tht(5, 2.54, 1, 1.8, 1.0, "Pin header"), "HDR2x6S": tht(6, 1.27, 2, 1.0, 0.65, "Pin header 1.27"), "HDR1x2": tht(2, 2.54, 1, 1.8, 1.0, "Pin header"),
 "HDR2x4": tht(4, 2.54, 2, 1.8, 1.0, "Pin header"), "HDR1x4": tht(4, 2.54, 1, 1.8, 1.0, "Pin header"), "WIRE1x4": dict(tht(4, 2.54, 1, 1.8, 1.0, "Wire pads"), body=(4.04, 11.66, 0.1)),
 "LED2020": dict(desc="RGB LED SK6812 MINI-E class 3.2x2.8 (VERIFY pinout and land pattern)", fp="LED_SMD:LED_SK6812MINI-E_3.2x2.8mm", pins=[("1", "VDD", "power_in"), ("2", "DOUT", "output"), ("3", "GND", "power_in"), ("4", "DIN", "input")], pads=[("1", -1.45, -0.85, 1.0, 0.7, "roundrect"), ("2", -1.45, 0.85, 1.0, 0.7, "roundrect"), ("3", 1.45, 0.85, 1.0, 0.7, "roundrect"), ("4", 1.45, -0.85, 1.0, 0.7, "roundrect")], body=(3.2, 2.8, 0.8)),
 "SOT23-5": dict(desc="74AHCT1G125 buffer SOT-23-5: 1 OE#, 2 A, 3 GND, 4 Y, 5 VCC (VERIFY)", fp="Package_TO_SOT_SMD:SOT-23-5", pins=[("1", "OE", "input"), ("2", "A", "input"), ("3", "GND", "power_in"), ("4", "Y", "output"), ("5", "VCC", "power_in")], pads=[("1", -1.1, -0.95, 1.0, 0.6, "roundrect"), ("2", -1.1, 0, 1.0, 0.6, "roundrect"), ("3", -1.1, 0.95, 1.0, 0.6, "roundrect"), ("4", 1.1, 0.95, 1.0, 0.6, "roundrect"), ("5", 1.1, -0.95, 1.0, 0.6, "roundrect")], body=(3.0, 1.7, 1.1)), "HDR2x6": tht(6, 2.54, 2, 1.8, 1.0, "Pin header"),
 "D2PAK": dict(desc="MOSFET TO-263-3 (D2PAK) G-D-S, tab = drain (VERIFY land pattern)", fp="Package_TO_SOT_SMD:TO-263-3_TabPin2",
               pins=[("1", "G", "input"), ("2", "D", "passive"), ("3", "S", "passive")],
               pads=[("1", -6.8, -2.54, 3.0, 1.6, "roundrect"), ("3", -6.8, 2.54, 3.0, 1.6, "roundrect"), ("2", 2.4, 0, 9.4, 10.8, "rect")], body=(10.2, 9.2, 4.6)),
 "CAPD": pair("Polymer tantalum D-case 7.3x4.3 (low profile)", "Capacitor_Tantalum_SMD:CP_EIA-7343-43_Kemet-X", 3.2, 2.4, 1.7, (7.3, 4.3, 4.3), ("+", "-")),
 "SOT223": dict(desc="LDO SOT-223 (AMS1117-3.3 class): 1 GND/ADJ, 2 VOUT, 3 VIN, tab VOUT (VERIFY)", fp="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
                pins=[("1", "GND", "power_in"), ("2", "VOUT", "power_out"), ("3", "VIN", "power_in"), ("4", "TAB", "power_out")],
                pads=[("1", -3.15, -2.3, 2.0, 1.5, "roundrect"), ("2", -3.15, 0, 2.0, 1.5, "roundrect"), ("3", -3.15, 2.3, 2.0, 1.5, "roundrect"), ("4", 3.15, 0, 3.4, 3.4, "rect")], body=(6.5, 3.5, 1.7)),
 "OKI3": dict(desc="Murata OKI-78SR class SIP-3 switching regulator: 1 VIN, 2 GND, 3 VOUT (VERIFY)", fp="Converter_DCDC:Converter_DCDC_Murata_OKI-78SR_Horizontal",
              pins=[("1", "VIN", "power_in"), ("2", "GND", "power_in"), ("3", "VOUT", "power_out")], pads=[("1", 0, -2.54, 1.8, 1.8, "circle"), ("2", 0, 0, 1.8, 1.8, "circle"), ("3", 0, 2.54, 1.8, 1.8, "circle")],
              body=(11.5, 8.5, 10.2), tht=True, drill=1.0),
 "HC4051": dict(desc="74HC4051 8-ch analog mux SOIC-16 (VERIFY pinout)", fp="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
    pins=[("1", "Y4", "passive"), ("2", "Y6", "passive"), ("3", "Z", "passive"), ("4", "Y7", "passive"), ("5", "Y5", "passive"), ("6", "E", "input"), ("7", "VEE", "power_in"), ("8", "GND", "power_in"),
          ("9", "S2", "input"), ("10", "S1", "input"), ("11", "S0", "input"), ("12", "Y3", "passive"), ("13", "Y0", "passive"), ("14", "Y1", "passive"), ("15", "Y2", "passive"), ("16", "VCC", "power_in")],
    pads=[(str(i + 1), -2.7, (i - 3.5) * 1.27, 1.55, 0.6, "roundrect") for i in range(8)] + [(str(16 - i), 2.7, (i - 3.5) * 1.27, 1.55, 0.6, "roundrect") for i in range(8)], body=(9.9, 3.9, 1.6)),
}
_pico_names = {1: "GP0", 2: "GP1", 3: "GND", 4: "GP2", 5: "GP3", 6: "GP4", 7: "GP5", 8: "GND", 9: "GP6", 10: "GP7", 11: "GP8", 12: "GP9", 13: "GND", 14: "GP10", 15: "GP11", 16: "GP12", 17: "GP13", 18: "GND", 19: "GP14", 20: "GP15",
               21: "GP16", 22: "GP17", 23: "GND", 24: "GP18", 25: "GP19", 26: "GP20", 27: "GP21", 28: "GND", 29: "GP22", 30: "RUN", 31: "GP26", 32: "GP27", 33: "AGND", 34: "GP28", 35: "ADC_VREF", 36: "3V3_OUT", 37: "3V3_EN", 38: "GND", 39: "VSYS", 40: "VBUS"}
_spare = {2, 16, 19, 20, 21, 22, 26, 27, 29, 35, 37, 40}
def _pico():
    pins = []; pads = []
    for n in range(1, 41):
        nm = _pico_names[n]; t = "power_in" if nm in ("GND", "AGND", "VSYS") else ("power_out" if nm == "3V3_OUT" else ("no_connect" if n in _spare else "passive"))
        pins.append((str(n), nm, t))
        x, y = (-8.89, (n - 10.5) * 2.54) if n <= 20 else (8.89, (30.5 - n) * 2.54)
        pads.append((str(n), x, y, 1.7, 1.7, "circle"))
    return dict(desc="Raspberry Pi Pico 2 W (RP2350 + CYW43439 Bluetooth) 40-pin DIP, 21 x 51 mm (pin order from memory: VERIFY)", fp="Module:RaspberryPi_Pico_Common_THT", pins=pins, pads=pads, body=(21.0, 51.0, 8.0), tht=True, drill=1.0)
LIB["PICO"] = _pico(); LIB.pop("SOIC8", None)
_soic_pads = [("1", -2.7, -1.905, 1.55, 0.6, "roundrect"), ("2", -2.7, -0.635, 1.55, 0.6, "roundrect"), ("3", -2.7, 0.635, 1.55, 0.6, "roundrect"), ("4", -2.7, 1.905, 1.55, 0.6, "roundrect"),
              ("5", 2.7, 1.905, 1.55, 0.6, "roundrect"), ("6", 2.7, 0.635, 1.55, 0.6, "roundrect"), ("7", 2.7, -0.635, 1.55, 0.6, "roundrect"), ("8", 2.7, -1.905, 1.55, 0.6, "roundrect")]
LIB["TC4420"] = dict(desc="TC4420 6 A MOSFET driver SOIC-8 (VERIFY pinout)", fp="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    pins=[("1", "VDD", "power_in"), ("2", "IN", "input"), ("3", "NC", "no_connect"), ("4", "GND", "power_in"), ("5", "GND2", "power_in"), ("6", "OUT", "output"), ("7", "OUT2", "output"), ("8", "VDD2", "power_in")],
    pads=_soic_pads, body=(4.9, 3.9, 1.6))
LIB["LM393"] = dict(desc="LM393 dual comparator SOIC-8", fp="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    pins=[("1", "OUT_A", "output"), ("2", "IN-_A", "input"), ("3", "IN+_A", "input"), ("4", "GND", "power_in"), ("5", "IN+_B", "input"), ("6", "IN-_B", "input"), ("7", "OUT_B", "output"), ("8", "VCC", "power_in")],
    pads=_soic_pads, body=(4.9, 3.9, 1.6))
LIB.pop("SOIC8", None)
LIB["HDR1x7"] = tht(7, 2.54, 1, 1.8, 1.0, "Pin header")
LIB["SS49E"] = dict(desc="SS49E linear Hall sensor (TO-92 style)", fp="Package_TO_SOT_THT:TO-92_Inline", pins=[("1", "VCC", "power_in"), ("2", "GND", "power_in"), ("3", "OUT", "output")], pads=[("1", -1.27, 0, 1.0, 1.0, "circle"), ("2", 0, 0, 1.0, 1.0, "circle"), ("3", 1.27, 0, 1.0, 1.0, "circle")], body=(4.0, 3.0, 4.5), tht=True, drill=0.65)
# digital Hall switch for the trigger (replaces the linear SS49E: CB1D reads TRIG on a digital-only GPIO with a pull-up). Generic open-drain part, same TO-92
# footprint; pin order VCC/GND/OUT and Vsat <= 0.4 V are UNVERIFIED until a part is chosen (docs/ASSUMPTIONS.md 22, prompt C05)
LIB["HALL_SW"] = dict(LIB["SS49E"], desc="digital Hall switch, open-drain output, 3.3 V (generic, TO-92 style; pinout unverified)", pins=[("1", "VCC", "power_in"), ("2", "GND", "power_in"), ("3", "OUT", "open_collector")])
if "HDR1x5" not in LIB: LIB["HDR1x5"] = tht(5, 2.54, 1, 1.8, 1.0, "Pin header")
# upper assembly v1 (PM2 / HB2): wire pads for panel parts and the cords, and an SO-8 P-channel MOSFET. SO-8 pinout 1-3 S, 4 G, 5-8 D is the common P-FET
# arrangement but VERIFY against the chosen part (docs/ASSUMPTIONS.md 26)
LIB["WIRE3"] = dict(tht(3, 5.08, 1, 3.0, 1.7, "Wire pads"), body=(4.04, 14.7, 0.1))
LIB["WIRE4"] = dict(tht(4, 5.08, 1, 3.0, 1.7, "Wire pads"), body=(4.04, 19.8, 0.1))
LIB["WIRE2S"] = dict(tht(2, 2.54, 1, 1.8, 1.0, "Wire pads"), body=(3.0, 6.6, 0.1))
LIB["PMOS_SO8"] = dict(desc="P-channel MOSFET SO-8, -40 V, Rds(on) <= 15 mohm at -10 V (1-3 S, 4 G, 5-8 D: VERIFY)", fp="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                       pins=[("1", "S", "passive"), ("2", "S", "passive"), ("3", "S", "passive"), ("4", "G", "input"), ("5", "D", "passive"), ("6", "D", "passive"), ("7", "D", "passive"), ("8", "D", "passive")],
                       pads=[(str(i + 1), -2.7, -1.905 + 1.27 * i, 1.55, 0.6, "roundrect") for i in range(4)] + [(str(8 - i), 2.7, -1.905 + 1.27 * i, 1.55, 0.6, "roundrect") for i in range(4)], body=(5.0, 6.0, 1.75))

PARTS = []; NETS = {}
def add(ref, typ, value, mpn="", **kw): PARTS.append(dict(ref=ref, type=typ, value=value, mpn=mpn, **kw))
def net(name, *pins):
    NETS.setdefault(name, [])
    for p in pins: NETS[name].append((p[0], str(p[1])))
if PW == "M":
    # ------------------------------------------------------------------ PM1: two cartridge inputs, fuse, precharge, OR-ing, TVS, bulk, aux, sense, outputs
    for X in "AB":
        add(f"J{X}", "TERM4", f"Cartridge {X}: NEG, PRE, POS, ID", "5.08 mm blade-contact block (see shaft design)")
        add(f"F{X}", "FUSE1812", "5A slow 32V", "Littelfuse 0453005 class (verify DC rating)")
        add(f"DO{X}", "DSMC", "SS10P6 60V 10A", "Schottky SMC 60 V 10 A")
        add(f"RP{X}", "R2512", "22R 2W pulse", "Vishay CRCW-HP / KOA SR732 class")
        add(f"DP{X}", "DSMB", "SS3P6 60V 3A", "Schottky SMB 60 V 3 A")
        net("GND", (f"J{X}", 1)); net(f"{X}_PRE", (f"J{X}", 2), (f"RP{X}", 1)); net(f"{X}_PM", (f"RP{X}", 2), (f"DP{X}", 2))
        net(f"{X}_POS", (f"J{X}", 3), (f"F{X}", 1)); net(f"{X}_FO", (f"F{X}", 2), (f"DO{X}", 2))
        net("VBUS", (f"DO{X}", 1), (f"DP{X}", 1)); net(f"{X}_ID", (f"J{X}", 4))
    add("DTVS", "DSMC", "SMCJ33A", "TVS 33 V stand-off, uni-directional"); net("VBUS", ("DTVS", 1)); net("GND", ("DTVS", 2))
    for n in (1, 2): add(f"CB{n}", "CAN10", "470u 50V", "hybrid polymer/Al 10x10, low ESR"); net("VBUS", (f"CB{n}", 1)); net("GND", (f"CB{n}", 2))
    for n in (1, 2): add(f"CM{n}", "C1210", "10u 50V", "X7R"); net("VBUS", (f"CM{n}", 1)); net("GND", (f"CM{n}", 2))
    add("RBL", "R1206", "100k", "bleeder"); net("VBUS", ("RBL", 1)); net("GND", ("RBL", 2))
    add("RS1", "R0603", "100k", "0.1%"); add("RS2", "R0603", "10k", "0.1%"); add("CS1", "C0603", "100n", "X7R 50V")
    net("VBUS", ("RS1", 1)); net("BUS_SENSE", ("RS1", 2), ("RS2", 1), ("CS1", 1)); net("GND", ("RS2", 2), ("CS1", 2))
    add("JBK", "HDR1x3", "Aux buck module VIN GND VOUT", "COTS 36 V -> 12 V >= 1.5 A buck module (e.g. Pololu D36V28F12 class)")
    net("VBUS", ("JBK", 1)); net("GND", ("JBK", 2)); net("BUCK_OUT", ("JBK", 3), ("FB1", 1))
    add("FB1", "FB1812", "BLM/742792 class 6A", "ferrite bead"); add("CAUX", "C1210", "22u 25V", "X7R"); add("CAUX2", "C0603", "100n", "X7R")
    net("AUX12", ("FB1", 2), ("CAUX", 1), ("CAUX2", 1)); net("GND", ("CAUX", 2), ("CAUX2", 2))
    add("JP", "TERM4", "Power out: VBUS VBUS GND GND", "5.08 mm terminal block 10 A"); net("VBUS", ("JP", 1), ("JP", 2)); net("GND", ("JP", 3), ("JP", 4))
    add("JS", "HDR2x4", "Signals: 12V GND 485A 485B SENSE A_ID B_ID SHLD", "2.54 mm header")
    net("AUX12", ("JS", 1)); net("GND", ("JS", 2)); net("RS485_A", ("JS", 3), ("JR", 1)); net("RS485_B", ("JS", 4), ("JR", 2)); net("BUS_SENSE", ("JS", 5))
    net("A_ID", ("JS", 6)); net("B_ID", ("JS", 7)); add("JR", "HDR1x2", "RS-485 to pod", "2.54 mm header")
    add("RSH", "R0603", "1M", ""); add("CSH", "C0603", "1n 100V", "C0G"); net("SHIELD", ("JS", 8), ("RSH", 1), ("CSH", 1)); net("GND", ("RSH", 2), ("CSH", 2))
elif PW == "T":
    # ------------------------------------------------------------------ PB1: bulk, two TX channels (gate driver, FETs, shunt, clamp, OCP comparator), controller interface
    add("JP", "TERM4", "Power in: VBUS VBUS GND GND", "5.08 mm terminal block 10 A"); net("VBUS", ("JP", 1), ("JP", 2)); net("GND", ("JP", 3), ("JP", 4))
    for n in (1, 2): add(f"CB{n}", "CAN10", "470u 50V", "hybrid polymer, low ESR"); net("VBUS", (f"CB{n}", 1)); net("GND", (f"CB{n}", 2))
    for n in range(1, 5): add(f"CM{n}", "C1210", "10u 50V", "X7R"); net("VBUS", (f"CM{n}", 1)); net("GND", (f"CM{n}", 2))
    add("JC", "HDR2x6", "Controller I/F", "2.54 mm header")
    jc = {1: "AUX12", 2: "GND", 3: "TX1_IN", 4: "TX2_IN", 5: "REF_I1", 6: "REF_I2", 7: "FAULT1_N", 8: "FAULT2_N", 9: "ISENSE1", 10: "ISENSE2", 11: "NTC_SENSE", 12: "GND"}
    for p, nm in jc.items(): net(nm, ("JC", p))
    add("RNTC", "R0603", "10k NTC", "NTC thermistor (on FET heat spreader)"); net("NTC_SENSE", ("RNTC", 1)); net("GND", ("RNTC", 2))
    add("U3", "LM393", "LM393", "TI LM393DR"); add("CU3", "C0805", "1u 25V", "X7R"); net("AUX12", ("U3", 8), ("CU3", 1)); net("GND", ("U3", 4), ("CU3", 2))
    CHANNELS = [dict(n=1, Qs=["Q1A", "Q1B"], Dc="DC1", dtype="DSMC", dval="ES3J 600V 3A", vtype="C1210", cl=["CL1A", "CL1B"], clv="100n 630V", rs="RS1S", rsval="10m 3W", half="A", coil="JL1"),
                 dict(n=2, Qs=["Q2A"], Dc="DC2", dtype="DSMB", dval="ES2D 200V 2A", vtype="C1210", cl=["CL2A"], clv="1u 100V", rs="RS2S", rsval="10m 3W", half="B", coil="JL2")]
    for c in CHANNELS:
        n = c["n"]; U = f"U{n}"
        add(U, "TC4420", "TC4420", "Microchip TC4420"); add(f"CD{n}", "C0805", "1u 25V", "X7R"); add(f"CE{n}", "C0603", "100n", "X7R")
        net("AUX12", (U, 1), (U, 8), (f"CD{n}", 1), (f"CE{n}", 1)); net("GND", (U, 4), (U, 5), (f"CD{n}", 2), (f"CE{n}", 2)); net(f"DRV{n}_NC", (U, 3))
        add(f"RIN{n}", "R0603", "100", ""); net(f"TX{n}_IN", (f"RIN{n}", 1)); net(f"DRVIN{n}", (f"RIN{n}", 2), (U, 2), (f"DOC{n}", 2))
        add(f"DOC{n}", "DSOD", "BAS16", "signal diode"); net(f"OC{n}_OUT", (f"DOC{n}", 1))
        net(f"G{n}", (U, 6), (U, 7)); add(f"RGP{n}", "R0603", "10k", ""); net(f"G{n}", (f"RGP{n}", 1)); net("GND", (f"RGP{n}", 2))
        for q in c["Qs"]:
            add(q, "D2PAK", "650V SJ 95mR" if n == 1 else "100V 10mR", "IPB65R095C7 class" if n == 1 else "100 V D2PAK, Rds(on) <= 10 mohm")
            add(f"RG{q}", "R0603", "10", ""); net(f"G{n}", (f"RG{q}", 1)); net(f"GATE_{q}", (f"RG{q}", 2), (q, 1))
            net(f"DRAIN{n}", (q, 2)); net(f"SRC{n}", (q, 3))
        add(c["rs"], "R2512", c["rsval"], "Kelvin-capable 2512 shunt, 3 W")
        net(f"SRC{n}", (c["rs"], 1)); net("GND", (c["rs"], 2))
        add(c["Dc"], c["dtype"], c["dval"], "ultrafast clamp diode"); net(f"DRAIN{n}", (c["Dc"], 2)); net(f"CLAMP{n}", (c["Dc"], 1))
        for cl in c["cl"]: add(cl, c["vtype"], c["clv"], "C0G/X7R HV"); net(f"CLAMP{n}", (cl, 1)); net("VBUS", (cl, 2))
        add(f"RCL{n}", "WIRE2", "external 5k 10W" if n == 1 else "external 100R 5W", "chassis-mount power resistor on the aluminium spreader"); net(f"CLAMP{n}", (f"RCL{n}", 1)); net("VBUS", (f"RCL{n}", 2))
        add(f"JL{n}", "TERM2", f"Coil {'outer' if n == 1 else 'inner'}: DRAIN, VBUS", "5.08 mm terminal block 10 A"); net(f"DRAIN{n}", (f"JL{n}", 1)); net("VBUS", (f"JL{n}", 2))
        # over-current comparator: IN- = filtered shunt voltage, IN+ = REF_I; output low when sense > ref
        h = c["half"]; inm, inp, out = (2, 3, 1) if h == "A" else (6, 5, 7)
        add(f"RK{n}", "R0603", "100", ""); add(f"CK{n}", "C0603", "100p", "C0G"); add(f"RPU{n}", "R0603", "10k", ""); add(f"RF{n}", "R0603", "1k", "")
        net(f"SRC{n}", (f"RK{n}", 1)); net(f"ISENSE{n}", (f"RK{n}", 2), (f"CK{n}", 1), ("U3", inm)); net("GND", (f"CK{n}", 2))
        net(f"REF_I{n}", ("U3", inp)); net(f"OC{n}_OUT", ("U3", out), (f"RPU{n}", 1), (f"RF{n}", 1)); net("AUX12", (f"RPU{n}", 2)); net(f"FAULT{n}_N", (f"RF{n}", 2))

if PW == "C":
    # ------------------------------------------------------------------ CB1: head controller / interface board (Pico 2 W, power tree, analog mux, handle inputs, headers)
    add("U1", "PICO", "Pico 2 W", "Raspberry Pi Pico 2 W (RP2350 + CYW43439)")
    pico = {1: "TX1_IN", 4: "BLANK", 5: "SCLK", 6: "CS", 7: "TRIG_IN", 9: "SDOA1", 10: "SDOA2", 11: "SDOA3", 12: "SDOB1", 14: "SDOB2", 15: "FAULT1_N", 17: "REF_PWM1",
            24: "MUX_S0", 25: "MUX_S1", 31: "MUX_OUT", 32: "DIAL_IN", 34: "VBUS_SENSE", 36: "P3V3", 39: "+5V", 30: "RUN"}
    for p, nm in pico.items(): net(nm, ("U1", p))
    net("GND", ("U1", 3), ("U1", 8), ("U1", 13), ("U1", 18), ("U1", 23), ("U1", 28), ("U1", 33), ("U1", 38))
    add("JDBG", "HDR1x2", "RUN / GND (reset, SWD pads on Pico underside)", "2.54 mm header"); net("RUN", ("JDBG", 1)); net("GND", ("JDBG", 2))
    add("CP1", "C0805", "10u 10V", "X7R"); add("CP2", "C0603", "100n", "X7R"); net("+5V", ("CP1", 1), ("CP2", 1)); net("GND", ("CP1", 2), ("CP2", 2))
    # power input
    add("JPW", "TERM4", "Power in: VBUS VBUS GND GND (from shaft)", "5.08 mm terminal block"); net("VBUS_IN", ("JPW", 1), ("JPW", 2), ("F1", 1)); net("GND", ("JPW", 3), ("JPW", 4))
    add("F1", "FUSE1812", "5A slow 32V", "Littelfuse 0453005 class"); net("VBUS", ("F1", 2))
    add("DTV", "DSMC", "SMCJ33A", "TVS"); net("VBUS", ("DTV", 1)); net("GND", ("DTV", 2))
    for n in (1, 2): add(f"CI{n}", "C1210", "10u 50V", "X7R"); net("VBUS", (f"CI{n}", 1)); net("GND", (f"CI{n}", 2))
    add("M5", "OKI3", "5 V 1.5 A switching module", "Murata OKI-78SR-5/1.5-W36 class (Vin 7-36 V)"); net("VBUS", ("M5", 1)); net("GND", ("M5", 2)); net("+5V", ("M5", 3))
    add("C5A", "C1210", "22u 16V", "X7R"); add("C5B", "C0603", "100n", "X7R"); net("+5V", ("C5A", 1), ("C5B", 1)); net("GND", ("C5A", 2), ("C5B", 2))
    add("FB2", "FB1812", "ferrite bead 1 A", "analog supply bead"); net("+5V", ("FB2", 1)); net("+5VA", ("FB2", 2), ("CV1", 1), ("CV2", 1), ("CV3", 1))
    add("CV1", "C1210", "10u 16V", "X7R"); add("CV2", "C0603", "100n", "X7R"); add("CV3", "C0805", "1u", "X7R"); net("GND", ("CV1", 2), ("CV2", 2), ("CV3", 2))
    add("UL", "SOT223", "AMS1117-3.3", "3.3 V LDO for ADC I/O"); net("+5V", ("UL", 3)); net("GND", ("UL", 1)); net("+3V3D", ("UL", 2), ("UL", 4), ("CL1", 1), ("CL2", 1))
    add("CL1", "C1210", "22u 10V", "X7R"); add("CL2", "C0603", "100n", "X7R"); net("GND", ("CL1", 2), ("CL2", 2))
    # analog mux for slow signals
    add("UM", "HC4051", "74HC4051", "Nexperia/TI 74HC4051D"); add("CM1", "C0603", "100n", "X7R")
    net("P3V3", ("UM", 16), ("CM1", 1)); net("GND", ("UM", 8), ("UM", 7), ("UM", 6), ("UM", 9), ("UM", 1), ("UM", 2), ("UM", 4), ("UM", 5), ("CM1", 2))
    net("ISENSE1", ("UM", 13)); net("NTC_SENSE", ("UM", 14)); net("GND", ("UM", 15), ("UM", 12)); net("MUX_S0", ("UM", 11)); net("MUX_S1", ("UM", 10)); net("MUX_COM", ("UM", 3), ("RMO", 1))
    add("RMO", "R0603", "1k", ""); add("CMO", "C0603", "1n", "C0G"); net("MUX_OUT", ("RMO", 2), ("CMO", 1)); net("GND", ("CMO", 2))
    # reference PWM filters (two-pole RC) and VBUS sense
    add("RR1", "R0603", "10k", ""); add("RR2", "R0603", "10k", ""); add("CR1", "C0603", "1u", "X7R"); add("CR2", "C0603", "1u", "X7R")
    net("REF_PWM1", ("RR1", 1)); net("REF_N1", ("RR1", 2), ("CR1", 1), ("RR2", 1)); net("REF_I1", ("RR2", 2), ("CR2", 1)); net("GND", ("CR1", 2), ("CR2", 2))
    add("RV1", "R0603", "100k", "0.1%"); add("RV2", "R0603", "10k", "0.1%"); add("CV4", "C0603", "100n", "X7R")
    net("VBUS", ("RV1", 1)); net("VBUS_SENSE", ("RV2", 1), ("RV1", 2), ("CV4", 1)); net("GND", ("RV2", 2), ("CV4", 2))
    # handle: trigger + dial (the only things that leave the head besides power)
    add("JTR", "HDR1x7", "Handle: +3V3 GND TRIG DIAL JOYX JOYY SHLD", "shielded 6-core + drain (the only signal cable leaving the head)"); net("P3V3", ("JTR", 1)); net("GND", ("JTR", 2)); net("TRIG_EXT", ("JTR", 3), ("RT1", 1)); net("DIAL_EXT", ("JTR", 4), ("RD1", 1)); net("SHIELD", ("JTR", 7), ("RSH", 1), ("CSH", 1)); net("JTR5_OPT", ("JTR", 5), ("RJ5", 1)); net("JTR6_OPT", ("JTR", 6), ("RJ6", 1)); net("GND", ("RJ5", 2), ("RJ6", 2))
    add("RJ5", "R0603", "0R DNP", "option: fit to ground JTR.5 at the CB1D end (handle-end check: OPEN_ITEMS 25)"); add("RJ6", "R0603", "0R DNP", "option: fit to ground JTR.6 at the CB1D end (handle-end check: OPEN_ITEMS 25)")
    add("RJB10", "R0603", "0R", "FITTED: JB.10 (AB1B idle MONO input, RS2 into the MONO amplifier) to VCM_OUT; remove only to isolate the input, which then floats: not for service"); net("JB10_VCM", ("RJB10", 1)); net("VCM_OUT", ("RJB10", 2))   # JTR.5/.6 (JOYX/JOYY) unconnected: joystick removed (owner decision 2026-10-23), CB1D-B
    add("RSH", "R0603", "1M", ""); add("CSH", "C0603", "1n 100V", "C0G"); net("GND", ("RSH", 2), ("CSH", 2))
    for k, (ext, inn) in enumerate((("TRIG_EXT", "TRIG_IN"), ("DIAL_EXT", "DIAL_IN")), 1):
        r = "RT1" if k == 1 else "RD1"; add(r, "R0603", "1k", "series protection"); add(f"DH{k}", "DSOD", "BAS16", ""); add(f"DL{k}", "DSOD", "BAS16", ""); add(f"CQ{k}", "C0603", "10n", "X7R"); add(f"RP{k}", "R0603", "47k" if k == 1 else "10k", "pull-up (47k on TRIG: low level with the 2 kohm series path stays under VIL)" if k == 1 else "pull-up")
        net(inn, (r, 2), (f"DH{k}", 2), (f"DL{k}", 1), (f"CQ{k}", 1), (f"RP{k}", 1)); net("P3V3", (f"DH{k}", 1), (f"RP{k}", 2)); net("GND", (f"DL{k}", 2), (f"CQ{k}", 2))
    # headers to the receiver boards, PB1R and the power
    add("JA", "HDR2x6S", "to AB1A J2", "1.27 mm 2x6 header"); add("JB", "HDR2x6S", "to AB1B J2", "1.27 mm 2x6 header")
    for ref, sd in (("JA", ["SDOA1", "SDOA2", "SDOA3"]), ("JB", ["SDOB1", "SDOB2"])):
        names = ["+5VA", "GND", "+3V3D", "GND", "SCLK", "CS"] + sd + (["BLANK", "GND", "GND"] if ref == "JA" else ["BLANK", "JB10_VCM", "VCM_OUT", "GND"])
        for i, nm in enumerate(names, 1): net(nm, (ref, i))
    add("JPB", "HDR2x4", "to PB1R: 12V GND TX1_IN REF_I1 FAULT1_N ISENSE1 NTC GND", "2.54 mm header")
    for i, nm in enumerate(["UMB_SHLD", "GND", "TX1_IN", "REF_I1", "FAULT1_N", "ISENSE1", "NTC_SENSE", "GND"], 1): net(nm, ("JPB", i))
    add("RUS", "R0603", "1M", ""); add("CUS", "C0603", "1n 100V", "C0G"); net("UMB_SHLD", ("RUS", 1), ("CUS", 1)); net("GND", ("RUS", 2), ("CUS", 2))
    # coil interface at the HEAD end of the coil leads: critical damping (3 x 110 R = 330 R, 600 V) and the AC-coupled MONO receive tap to AB1B
    add("JCL", "TERM2", "Coil leads from the neck module: COIL_B (drain side), COIL_A (VBUS side)", "5.08 mm terminal block, silicone AWG12 leads")
    for k in (1, 2, 3): add(f"RDM{k}", "R2512", "110R", "damping chain 3 x 110 = 330 R (600 V)")
    net("COIL_B", ("JCL", 1), ("RDM1", 1)); net("DM1", ("RDM1", 2), ("RDM2", 1)); net("DM2", ("RDM2", 2), ("RDM3", 1)); net("COIL_A", ("JCL", 2), ("RDM3", 2))
    # CB1D-B: the AC-coupled MONO tap (CMON 100 nF / 630 V, RBI) is removed: a 460 V node on a 1.27 mm header could not meet the 1.0 mm HV rule (KiCad DRC), and the mono/disc channel is not used with RX-Q
if PW == "R":
    # ------------------------------------------------------------------ PB1R: single-channel TX power stage for the head vault (70 x 70)
    add("JP", "TERM4", "Power in: VBUS VBUS GND GND", "5.08 mm terminal block 10 A"); net("VBUS", ("JP", 1), ("JP", 2)); net("GND", ("JP", 3), ("JP", 4))
    for n in range(1, 7): add(f"CD{n}", "CAPD", "150u 50V polymer Ta", "50 V polymer Ta or hybrid, low ESR; >= 130 uF each at 19.6 V (tx_vbus_sweep.py); 150 uF in 7343-43 at 50 V UNVERIFIED (ASSUMPTIONS 28)"); net("VBUS", (f"CD{n}", 1)); net("GND", (f"CD{n}", 2))
    for n in range(1, 5): add(f"CM{n}", "C1210", "10u 50V", "X7R"); net("VBUS", (f"CM{n}", 1)); net("GND", (f"CM{n}", 2))
    add("JC", "HDR2x4", "Umbilical from the head: SHLD GND TX1_IN REF_I1 FAULT1_N ISENSE1 NTC GND", "2.54 mm header")
    for i, nm in enumerate(["UMB_SHLD", "GND", "TX1_IN", "REF_I1", "FAULT1_N", "ISENSE1", "NTC_SENSE", "GND"], 1): net(nm, ("JC", i))
    add("RUS", "R0603", "1M", ""); net("UMB_SHLD", ("RUS", 1)); net("GND", ("RUS", 2))
    add("RNTC", "R0603", "10k NTC", "NTC on the FET spreader"); net("NTC_SENSE", ("RNTC", 1)); net("GND", ("RNTC", 2))
    add("U3", "LM393", "LM393", "TI LM393DR"); add("CU3", "C0805", "1u 25V", "X7R"); net("AUX12", ("U3", 8), ("CU3", 1)); net("GND", ("U3", 4), ("CU3", 2))
    net("GND", ("U3", 5), ("U3", 6)); net("OCB_NC", ("U3", 7))
    add("U1", "TC4420", "TC4420", "Microchip TC4420"); add("CD7", "C0805", "1u 25V", "X7R"); add("CE1", "C0603", "100n", "X7R")
    net("AUX12", ("U1", 1), ("U1", 8), ("CD7", 1), ("CE1", 1)); net("GND", ("U1", 4), ("U1", 5), ("CD7", 2), ("CE1", 2)); net("DRV1_NC", ("U1", 3))
    add("RIN1", "R0603", "100", ""); net("TX1_IN", ("RIN1", 1)); net("DRVIN1", ("RIN1", 2), ("U1", 2), ("DOC1", 2)); add("DOC1", "DSOD", "BAS16", ""); net("OC1_OUT", ("DOC1", 1))
    net("G1", ("U1", 6), ("U1", 7)); add("RGP1", "R0603", "10k", ""); net("G1", ("RGP1", 1)); net("GND", ("RGP1", 2))
    for q in ("Q1A", "Q1B"):
        add(q, "D2PAK", "650V SJ 95mR", "IPB65R095C7 class (VERIFY)"); add(f"RG{q}", "R0603", "10", ""); net("G1", (f"RG{q}", 1)); net(f"GATE_{q}", (f"RG{q}", 2), (q, 1)); net("DRAIN1", (q, 2)); net("SRC1", (q, 3))
    add("RS1S", "R2512", "10m 3W", "Kelvin shunt"); net("SRC1", ("RS1S", 1)); net("GND", ("RS1S", 2))
    add("DC1", "DSMC", "ES3J 600V 3A", "ultrafast clamp diode"); net("DRAIN1", ("DC1", 2)); net("CLAMP1", ("DC1", 1))
    for cl in ("CL1A", "CL1B"): add(cl, "C1210", "100n 630V", "C0G/X7R HV"); net("CLAMP1", (cl, 1)); net("VBUS", (cl, 2))
    add("RCL1", "WIRE2", "external 5k 10W (lid bank)", "resistor bank bonded under the lid"); net("CLAMP1", ("RCL1", 1)); net("VBUS", ("RCL1", 2))
    add("JL1", "TERM2", "Coil outer band: DRAIN, VBUS", "5.08 mm terminal block"); net("DRAIN1", ("JL1", 1)); net("VBUS", ("JL1", 2))
    add("RK1", "R0603", "100", ""); add("CK1", "C0603", "100p", "C0G"); add("RPU1", "R0603", "10k", ""); add("RF1", "R0603", "1k", "")
    net("SRC1", ("RK1", 1)); net("ISENSE1", ("RK1", 2), ("CK1", 1), ("U3", 2)); net("GND", ("CK1", 2)); net("REF_I1", ("U3", 3)); net("OC1_OUT", ("U3", 1), ("RPU1", 1), ("RF1", 1)); net("AUX12", ("RPU1", 2)); net("FAULT1_N", ("RF1", 2))
    add("M12", "OKI3", "12 V 1.5 A switching module", "Murata OKI-78SR-12/1.5-W36 class, Vin 15-36 V covers the 7S range 19.6-29.4 V (datasheet UNVERIFIED, ASSUMPTIONS 29)"); net("VBUS", ("M12", 1)); net("GND", ("M12", 2)); net("AUX12", ("M12", 3))
    add("C12A", "C1210", "22u 25V", "X7R"); add("C12B", "C0603", "100n", "X7R"); net("AUX12", ("C12A", 1), ("C12B", 1)); net("GND", ("C12A", 2), ("C12B", 2))

if PW == "H":
    # ------------------------------------------------------------------ HB1: ergonomic handle board (trigger Hall sensor, joystick, dial ladder) on the shielded 6-core cable to the head
    add("JH", "HDR1x7", "Cable to head: +3V3 GND TRIG DIAL JOYX JOYY SHLD", "shielded 6-core + drain")
    for p, nm in ((1, "P3V3"), (2, "GND"), (3, "TRIG"), (4, "DIAL"), (5, "JOY_X"), (6, "JOY_Y"), (7, "SHIELD")): net(nm, ("JH", p))
    add("HS1", "HALL_SW", "Hall switch OD", "digital Hall switch, open-drain, 3.3 V (part to be chosen; trigger magnet travel 0-4 mm)"); add("CH1", "C0603", "100n", ""); add("RH1", "R0603", "1k", "")
    net("P3V3", ("HS1", 1), ("CH1", 1)); net("GND", ("HS1", 2), ("CH1", 2)); net("HALL_OUT", ("HS1", 3), ("RH1", 1)); net("TRIG", ("RH1", 2))
    add("JJOY", "HDR1x5", "Joystick: V GND X Y SW", "2-axis thumb joystick module"); net("P3V3", ("JJOY", 1)); net("GND", ("JJOY", 2)); net("JOY_X", ("JJOY", 3)); net("JOY_Y", ("JJOY", 4)); net("JOY_SW", ("JJOY", 5), ("RSW", 1))
    add("RSW", "R0603", "10k", "joystick switch pull-up"); net("P3V3", ("RSW", 2))
    add("JDIAL", "HDR1x5", "Dial: COM P1 P2 P3 P4 (4-position rotary switch)", "4-position rotary switch"); add("RD0", "R0603", "10k", ""); add("RD2", "R0603", "3k3", ""); add("RD3", "R0603", "10k", ""); add("RD4", "R0603", "33k", "")
    net("P3V3", ("RD0", 1)); net("DIAL", ("RD0", 2), ("JDIAL", 1)); net("GND", ("JDIAL", 2)); net("DP2", ("JDIAL", 3), ("RD2", 1)); net("DP3", ("JDIAL", 4), ("RD3", 1)); net("DP4", ("JDIAL", 5), ("RD4", 1)); net("GND", ("RD2", 2), ("RD3", 2), ("RD4", 2))
    add("RSHH", "R0603", "0R", "shield to grip foil"); net("SHIELD", ("RSHH", 1)); net("GND", ("RSHH", 2))
if PW == "P":
    # ------------------------------------------------------------------ PM2 (upper assembly v1): MT60 dock power path in the bottom housing
    # pack MT60-F pin 3 is looped to pack GND; the dock MT60-M is panel-mounted in the pedestal and wired to J1. Q1 conducts only when the pack is
    # seated (ILK = pack GND) AND the power switch on the top housing is closed; C1 sets the soft-start ramp (power_dock_check.py)
    add("J1", "WIRE3", "MT60-M leads: BAT+ BAT- ILK", "AWG16 x 2 + AWG24, 80 mm, potted at the pedestal")
    net("BAT_P", ("J1", 1), ("F1", 1)); net("GND", ("J1", 2)); net("ILK", ("J1", 3), ("J3", 2))
    add("F1", "FUSE1812", "5A slow 32V", "Littelfuse 0453005 class (verify DC rating)"); net("BAT_F", ("F1", 2))
    add("Q1", "PMOS_SO8", "P-MOSFET -40V", "SO-8 P-channel, -40 V, <= 15 mohm (part to be chosen)")
    net("BAT_F", ("Q1", 1), ("Q1", 2), ("Q1", 3)); net("Q1_G", ("Q1", 4)); net("VBUS", ("Q1", 5), ("Q1", 6), ("Q1", 7), ("Q1", 8))
    add("R1", "R0603", "47k", "gate to source"); net("BAT_F", ("R1", 1)); net("Q1_G", ("R1", 2))
    add("DZ1", "DSOD", "15V zener", "BZT52C15 class, Vgs clamp"); net("BAT_F", ("DZ1", 1)); net("Q1_G", ("DZ1", 2))
    add("R2", "R0603", "68k", "gate pull-down through the switch and the interlock"); net("Q1_G", ("R2", 1)); net("SW_A", ("R2", 2), ("J3", 1))
    add("J3", "WIRE2S", "Power switch pair (top housing)", "AWG28 pair")
    add("R3", "R0603", "1k", "soft-start damping"); add("C1", "C0805", "220n 50V", "X7R, Miller soft-start"); net("Q1_G", ("R3", 1)); net("SS", ("R3", 2), ("C1", 1)); net("VBUS", ("C1", 2))
    add("DTVS", "DSMC", "SMCJ33A", "TVS 33 V stand-off, uni-directional"); net("VBUS", ("DTVS", 1)); net("GND", ("DTVS", 2))
    add("CB1", "CAN10", "470u 50V", "hybrid polymer/Al 10x10, low ESR"); net("VBUS", ("CB1", 1)); net("GND", ("CB1", 2))
    add("CM1", "C1210", "10u 50V", "X7R"); net("VBUS", ("CM1", 1)); net("GND", ("CM1", 2))
    add("RBL", "R1206", "100k", "bleeder"); net("VBUS", ("RBL", 1)); net("GND", ("RBL", 2))
    add("JP", "WIRE4", "Power cord: VBUS VBUS GND GND", "coiled cord 2 x AWG20 shielded (one conductor per net, second pad for strain relief)")
    net("VBUS", ("JP", 1), ("JP", 2)); net("GND", ("JP", 3), ("JP", 4))
    add("JS", "WIRE2S", "Shields: power-cord braid, septum Cu mesh", "single-point drain at PM2"); net("SHIELD", ("JS", 1), ("JS", 2), ("RSH", 1), ("CSH", 1))
    add("RSH", "R0603", "1M", ""); add("CSH", "C0603", "1n 100V", "C0G"); net("GND", ("RSH", 2), ("CSH", 2))
if PW == "G":
    # ------------------------------------------------------------------ HB2 (upper assembly v1): grip board in the top housing; trigger Hall switch and dial; no joystick
    # JH keeps the CB1D JTR pinout; pins 5/6 (the old joystick) have no conductor in the 5-core signal cord
    add("JH", "HDR1x7", "Signal cord to the head: +3V3 GND TRIG DIAL - - SHLD", "coiled cord 5-core AWG28 shielded")
    for p_, nm in ((1, "P3V3"), (2, "GND"), (3, "TRIG"), (4, "DIAL"), (5, "JH5_NC"), (6, "JH6_NC"), (7, "SHIELD")): net(nm, ("JH", p_))
    add("HS1", "HALL_SW", "Hall switch OD", "digital Hall switch, open-drain, 3.3 V (part to be chosen); magnet near at rest -> TRIG low, pressed -> TRIG high (active-low lever)")
    add("CH1", "C0603", "100n", ""); add("RH1", "R0603", "1k", "")
    net("P3V3", ("HS1", 1), ("CH1", 1)); net("GND", ("HS1", 2), ("CH1", 2)); net("HALL_OUT", ("HS1", 3), ("RH1", 1)); net("TRIG", ("RH1", 2))
    add("JDIAL", "HDR1x5", "Dial: COM P1 P2 P3 P4 (4-pos rotary, top housing)", "4-position rotary switch"); add("RD0", "R0603", "10k", ""); add("RD2", "R0603", "3k3", ""); add("RD3", "R0603", "10k", ""); add("RD4", "R0603", "33k", "")
    net("P3V3", ("RD0", 1)); net("DIAL", ("RD0", 2), ("JDIAL", 1)); net("GND", ("JDIAL", 2)); net("DP2", ("JDIAL", 3), ("RD2", 1)); net("DP3", ("JDIAL", 4), ("RD3", 1)); net("DP4", ("JDIAL", 5), ("RD4", 1)); net("GND", ("RD2", 2), ("RD3", 2), ("RD4", 2))
    add("RSHH", "R0603", "0R", "signal-cord shield to GND at the handle"); net("SHIELD", ("RSHH", 1)); net("GND", ("RSHH", 2))
if PW == "L":
    import csv as _csv
    px = list(_csv.DictReader(open("kit_v18/SET/02_CORE_PCB_CYLINDER/PIXEL_MAP_66.csv")))
    for i, r in enumerate(px, 1):
        add(f"LD{i}", "LED2020", "SK6812 MINI-E RGB", "Worldsemi SK6812MINI-E class (verify)", xy=(float(r["x_mm"]), -float(r["y_mm"])), ring=int(r["ring"]), az=float(r["azimuth_deg"]))
        net("+5V", (f"LD{i}", 1)); net("GND", (f"LD{i}", 3)); net(f"LD_D{i-1}", (f"LD{i}", 4))
        net(f"LD_D{i}" if i < 66 else "LD_END_NC", (f"LD{i}", 2))
    for k in range(1, 12): add(f"CL{k}", "C0603", "100n", "X7R 10V"); net("+5V", (f"CL{k}", 1)); net("GND", (f"CL{k}", 2))
    add("CB", "C1210", "10u 16V", "X7R"); net("+5V", ("CB", 1)); net("GND", ("CB", 2))
    add("U1", "SOT23-5", "74AHCT1G125", "TI SN74AHCT1G125DBV (level shift 3V3 -> 5V data)"); net("+5V", ("U1", 5)); net("GND", ("U1", 3), ("U1", 1)); net("LED_IN", ("U1", 2)); net("LD_BUF", ("U1", 4), ("RS", 1))
    add("RS", "R0603", "33R", "series damping"); net("LD_D0", ("RS", 2))
    add("JLB", "WIRE1x4", "to CB1D: +5V, LED_IN, GND, GND", "4 wire pads, no header (a header is 9 mm tall and hits the cap)"); net("+5V", ("JLB", 1)); net("LED_IN", ("JLB", 2)); net("GND", ("JLB", 3), ("JLB", 4))
if PW == "C" and os.environ.get("DISC"):
    # ---- CB1D additions: hub-top antenna (HTA) monitor input on spare mux channel Y4 (select line S2 from the spare Pico pin GP1)
    NETS["GND"] = [p for p in NETS["GND"] if p not in (("UM", "1"), ("UM", "9"))]
    add("JHTA", "WIRE2", "HTA coil leads (twisted pair from the cap)", "solder pads 5.08 mm"); add("RHTA", "R0603", "10k", "series protection"); add("CHTA", "C0603", "1n", "C0G")
    add("DHA1", "DSOD", "BAS16", "clamp to 3V3"); add("DHA2", "DSOD", "BAS16", "clamp to GND")
    add("JLB", "HDR1x4", "to LB1: +5V, LED_IN, GND, GND", "4 wires to the display board"); net("+5V", ("JLB", 1)); net("LED_IN", ("JLB", 2), ("U1", 16)); net("GND", ("JLB", 3), ("JLB", 4))
    net("HTA_P", ("JHTA", 1), ("RHTA", 1)); net("GND", ("JHTA", 2)); net("HTA_IN", ("RHTA", 2), ("CHTA", 1), ("DHA1", 2), ("DHA2", 1), ("UM", 1))
    net("P3V3", ("DHA1", 1)); net("GND", ("CHTA", 2), ("DHA2", 2)); net("MUX_S2", ("UM", 9), ("U1", 2))
for k in NETS: NETS[k] = list(dict.fromkeys(NETS[k]))
BYREF = {p["ref"]: p for p in PARTS}
def pin_info(ref, num):
    for n, name, typ in LIB[BYREF[ref]["type"]]["pins"]:
        if str(n) == str(num): return name, typ
    raise KeyError((ref, num))
def erc():
    errs = []; owner = {}
    refs = [p["ref"] for p in PARTS]
    if len(set(refs)) != len(refs): errs.append("duplicate refs")
    for n, pins in NETS.items():
        for pr in pins:
            if pr in owner and owner[pr] != n: errs.append(f"pin {pr} in two nets {owner[pr]} / {n}")
            owner[pr] = n
            try: pin_info(*pr)
            except KeyError: errs.append(f"unknown pin {pr} in {n}")
    for p in PARTS:
        for num, name, typ in LIB[p["type"]]["pins"]:
            if (p["ref"], num) not in owner and typ != "no_connect": errs.append(f"unconnected {p['ref']}.{name}")
    for n, pins in NETS.items():
        if len(pins) < 2 and not n.endswith("_NC") and not n.endswith("_ID"): errs.append(f"single-pin net {n}: {pins}")
    for p in PARTS:
        if p["type"] in ("TC4420", "LM393"):
            sup = "AUX12"; v = [nm for nm, t in ((x[1], x[2]) for x in LIB[p["type"]]["pins"]) if nm in ("VDD", "VDD2", "VCC")]
            for num, name, t in LIB[p["type"]]["pins"]:
                if name in ("VDD", "VDD2", "VCC") and owner.get((p["ref"], num)) != sup: errs.append(f"{p['ref']}.{name} not on {sup}")
                if name in ("GND", "GND2") and owner.get((p["ref"], num)) != "GND": errs.append(f"{p['ref']}.{name} not on GND")
    return errs, []
def bom():
    rows = {}
    for p in PARTS: rows.setdefault((p["type"], p["value"], p["mpn"]), []).append(p["ref"])
    return [dict(qty=len(r), refs=",".join(r), type=k[0], value=k[1], mpn=k[2], footprint=LIB[k[0]]["fp"]) for k, r in sorted(rows.items())]
def kicad_netlist(path):
    L = ['(export (version "E")', f'  (design (source "PF233-{PW}.net") (date "{datetime.date.today()}") (tool "pw_design.py"))', "  (components"]
    for p in PARTS:
        lib = LIB[p["type"]]; L.append(f'    (comp (ref "{p["ref"]}") (value "{p["value"]}") (footprint "{lib["fp"]}") (libsource (lib "PF233") (part "{p["type"]}") (description "{lib["desc"]}")) (property (name "MPN") (value "{p["mpn"]}")))')
    L += ["  )", "  (nets"]
    for i, (n, pins) in enumerate(sorted(NETS.items()), 1):
        L.append(f'    (net (code "{i}") (name "{n}")')
        for ref, num in pins: L.append(f'      (node (ref "{ref}") (pin "{num}") (pinfunction "{pin_info(ref, num)[0]}"))')
        L.append("    )")
    L += ["  )", ")"]; open(path, "w").write("\n".join(L))
if __name__ == "__main__":
    e, w = erc(); print("board", PW, "parts", len(PARTS), "nets", len(NETS), "ERC errors", len(e)); [print(" E:", x) for x in e[:25]]
