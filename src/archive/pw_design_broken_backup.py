#!/usr/bin/env python3
"""
PF233-PM1 (battery power path / protection / hot-swap OR-ing)  and  PF233-PB1 (TX driver power stage) design database.
Select with env PW=M (PM1) or PW=T (PB1).  API mirrors afe_design (PARTS, NETS, LIB, BYREF, erc(), bom(), kicad_netlist()).
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
 "HDR2x4": tht(4, 2.54, 2, 1.8, 1.0, "Pin header"), "HDR2x6": tht(6, 2.54, 2, 1.8, 1.0, "Pin header"),
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

def _lqfp(n_side=25, pitch=0.5, c=7.675):
    pads = []; k = 1
    for i in range(n_side): pads.append((str(k), -c, -6.0 + i * pitch, 1.475, 0.3, "roundrect")); k += 1
    for i in range(n_side): pads.append((str(k), -6.0 + i * pitch, c, 0.3, 1.475, "roundrect")); k += 1
    for i in range(n_side): pads.append((str(k), c, 6.0 - i * pitch, 1.475, 0.3, "roundrect")); k += 1
    for i in range(n_side): pads.append((str(k), 6.0 - i * pitch, -c, 0.3, 1.475, "roundrect")); k += 1
    return pads
_MCU = {1: "PE2", 2: "PE3", 3: "PE4", 4: "PE5", 5: "PE6", 6: "VBAT", 7: "PC13", 8: "PC14", 9: "PC15", 10: "VSS", 11: "VDD", 12: "PH0", 13: "PH1", 14: "NRST", 15: "PC0", 16: "PC1", 17: "PC2_C", 18: "PC3_C", 19: "VSSA",
        20: "VREFP", 21: "VDDA", 22: "PA0", 23: "PA1", 24: "PA2", 25: "PA3", 26: "VSS", 27: "VDD", 28: "PA4", 29: "PA5", 30: "PA6", 31: "PA7", 32: "PC4", 33: "PC5", 34: "PB0", 35: "PB1", 36: "PB2", 37: "PE7",
        38: "PE8", 39: "PE9", 40: "PE10", 41: "PE11", 42: "PE12", 43: "PE13", 44: "PE14", 45: "PE15", 46: "PB10", 47: "PB11", 48: "VCAP", 49: "VSS", 50: "VDD", 51: "PB12", 52: "PB13", 53: "PB14", 54: "PB15",
        55: "PD8", 56: "PD9", 57: "PD10", 58: "PD11", 59: "PD12", 60: "PD13", 61: "PD14", 62: "PD15", 63: "PC6", 64: "PC7", 65: "PC8", 66: "PC9", 67: "PA8", 68: "PA9", 69: "PA10", 70: "PA11", 71: "PA12",
        72: "PA13", 73: "VCAP2", 74: "VSS", 75: "VDD", 76: "PA14", 77: "PA15", 78: "PC10", 79: "PC11", 80: "PC12", 81: "PD0", 82: "PD1", 83: "PD2", 84: "PD3", 85: "PD4", 86: "PD5", 87: "VSS", 88: "VDD",
        89: "PD6", 90: "PD7", 91: "PB3", 92: "PB4", 93: "PB5", 94: "PB6", 95: "PB7", 96: "BOOT0", 97: "PB8", 98: "PB9", 99: "PE0", 100: "PE1"}
def _mtype(n):
    return "power_in" if n.startswith(("VSS", "VDD", "VCAP", "VBAT", "VREF")) else ("input" if n in ("NRST", "BOOT0") else "no_connect")
LIB["STM32H7"] = dict(desc="STM32H743VIT6 LQFP-100 (pin map from the F4/H7 LQFP100 family: VERIFY with CubeMX)", fp="Package_QFP:LQFP-100_14x14mm_P0.5mm",
    pins=[(str(i), _MCU[i], _mtype(_MCU[i])) for i in range(1, 101)], pads=_lqfp(), body=(14.0, 14.0, 1.6))
LIB["XTAL3225"] = dict(desc="Crystal 25 MHz 3225 4-pad", fp="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", pins=[("1", "X1", "passive"), ("2", "GND1", "passive"), ("3", "X2", "passive"), ("4", "GND2", "passive")],
    pads=[("1", -1.1, 0.85, 1.4, 1.15, "roundrect"), ("2", 1.1, 0.85, 1.4, 1.15, "roundrect"), ("3", 1.1, -0.85, 1.4, 1.15, "roundrect"), ("4", -1.1, -0.85, 1.4, 1.15, "roundrect")], body=(3.2, 2.5, 0.8))
_s5 = [("1", -1.1375, -0.95, 1.325, 0.6, "roundrect"), ("2", -1.1375, 0, 1.325, 0.6, "roundrect"), ("3", -1.1375, 0.95, 1.325, 0.6, "roundrect"), ("4", 1.1375, 0.95, 1.325, 0.6, "roundrect"), ("5", 1.1375, -0.95, 1.325, 0.6, "roundrect")]
LIB["LP2985"] = dict(desc="LP2985-50 150 mA low-noise LDO SOT-23-5 (VERIFY pinout)", fp="Package_TO_SOT_SMD:SOT-23-5", pins=[("1", "VIN", "power_in"), ("2", "GND", "power_in"), ("3", "ON_OFF", "input"), ("4", "BYPASS", "passive"), ("5", "VOUT", "power_out")], pads=_s5, body=(2.9, 1.6, 1.1))
LIB["AP2112K"] = dict(desc="AP2112K-3.3 600 mA LDO SOT-23-5 (VERIFY pinout)", fp="Package_TO_SOT_SMD:SOT-23-5", pins=[("1", "VIN", "power_in"), ("2", "GND", "power_in"), ("3", "EN", "input"), ("4", "NC", "no_connect"), ("5", "VOUT", "power_out")], pads=_s5, body=(2.9, 1.6, 1.1))
LIB["LM386"] = dict(desc="LM386 audio amplifier SOIC-8", fp="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", pins=[("1", "GAIN1", "passive"), ("2", "IN-", "input"), ("3", "IN+", "input"), ("4", "GND", "power_in"), ("5", "VOUT", "output"), ("6", "VS", "power_in"), ("7", "BYPASS", "passive"), ("8", "GAIN2", "passive")], pads=_soic_pads, body=(4.9, 3.9, 1.6))
LIB["SS49E"] = dict(desc="SS49E linear Hall sensor (TO-92 style, 3 pins)", fp="Package_TO_SOT_THT:TO-92_Inline", pins=[("1", "VCC", "power_in"), ("2", "GND", "power_in"), ("3", "OUT", "output")],
    pads=[("1", -1.27, 0, 1.0, 1.0, "circle"), ("2", 0, 0, 1.0, 1.0, "circle"), ("3", 1.27, 0, 1.0, 1.0, "circle")], body=(4.0, 3.0, 4.5), tht=True, drill=0.65)
LIB["LED0603"] = pair("LED 0603", "LED_SMD:LED_0603_1608Metric", 0.825, 0.8, 0.95, (1.6, 0.8, 0.5), ("K", "A"))
LIB["FB0603"] = pair("Ferrite bead 0603", "Inductor_SMD:L_0603_1608Metric", 0.825, 0.8, 0.95, (1.6, 0.8, 0.6))
LIB["R0402"] = pair("Resistor 0402", "Resistor_SMD:R_0402_1005Metric", 0.51, 0.54, 0.64, (1.0, 0.5, 0.35)); LIB["C0402"] = pair("Capacitor 0402", "Capacitor_SMD:C_0402_1005Metric", 0.51, 0.54, 0.64, (1.0, 0.5, 0.5))
LIB["HDR2x10_127"] = tht(10, 1.27, 2, 1.0, 0.65, "Pin header 1.27"); LIB["HDR2x6_127"] = tht(6, 1.27, 2, 1.0, 0.65, "Pin header 1.27"); LIB["HDR2x8"] = tht(8, 2.54, 2, 1.8, 1.0, "Pin header")
LIB["HDR1x5_127"] = tht(5, 1.27, 1, 1.0, 0.65, "Pin header 1.27"); LIB["HDR1x5"] = tht(5, 2.54, 1, 1.8, 1.0, "Pin header"); LIB["HDR1x4"] = tht(4, 2.54, 1, 1.8, 1.0, "Pin header"); LIB["HDR1x6"] = tht(6, 2.54, 1, 1.8, 1.0, "Pin header")
LIB["C1206"] = pair("Capacitor 1206", "Capacitor_SMD:C_1206_3216Metric", 1.5, 1.2, 1.8, (3.2, 1.6, 1.0))
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
    add("JS", "HDR2x6", "POWER ribbon: 12V GND 5V5 GND 3V6 GND SENSE EN A_ID B_ID SHLD GND", "2.54 mm header to the power ribbon")
    # rev B rail modules: pre-regulated 5.5 V (analog LDO feed) and 3.6 V (digital LDO feed) so regulation heat stays out of the head
    add("JBK5", "HDR1x3", "5.5 V buck module VIN GND VOUT", "COTS adjustable buck module set to 5.5 V >= 1 A"); add("JBK3", "HDR1x3", "3.6 V buck module VIN GND VOUT", "COTS adjustable buck module set to 3.6 V >= 1 A")
    add("FB2", "FB1812", "BLM class 3A", "ferrite bead"); add("FB3", "FB1812", "BLM class 3A", "ferrite bead")
    add("C55", "C1210", "22u 16V", "X7R"); add("C55B", "C0603", "100n", "X7R"); add("C36", "C1210", "22u 16V", "X7R"); add("C36B", "C0603", "100n", "X7R")
    net("VBUS", ("JBK5", 1), ("JBK3", 1)); net("GND", ("JBK5", 2), ("JBK3", 2), ("C55", 2), ("C55B", 2), ("C36", 2), ("C36B", 2))
    net("V5R5_RAW", ("JBK5", 3), ("FB2", 1)); net("V5R5", ("FB2", 2), ("C55", 1), ("C55B", 1)); net("V3R6_RAW", ("JBK3", 3), ("FB3", 1)); net("V3R6", ("FB3", 2), ("C36", 1), ("C36B", 1))
    net("AUX12", ("JS", 1)); net("GND", ("JS", 2), ("JS", 4), ("JS", 6), ("JS", 12)); net("V5R5", ("JS", 3)); net("V3R6", ("JS", 5)); net("BUS_SENSE", ("JS", 7)); net("EN_MAIN", ("JS", 8), ("REN", 1))
    add("REN", "R0603", "100k", "EN_MAIN pull-down (spare master-enable line)"); net("GND", ("REN", 2))
    net("A_ID", ("JS", 9)); net("B_ID", ("JS", 10))
    add("RSH", "R0603", "1M", ""); add("CSH", "C0603", "1n 100V", "C0G"); net("SHIELD", ("JS", 11), ("RSH", 1), ("CSH", 1)); net("GND", ("RSH", 2), ("CSH", 2))
elif PW == "T":
    # ------------------------------------------------------------------ PB1: bulk, two TX channels (gate driver, FETs, shunt, clamp, OCP comparator), controller interface
    add("JP", "TERM4", "Power in: VBUS VBUS GND GND", "5.08 mm terminal block 10 A"); net("VBUS", ("JP", 1), ("JP", 2)); net("GND", ("JP", 3), ("JP", 4))
    for n in (1, 2): add(f"CB{n}", "CAN10", "470u 50V", "hybrid polymer, low ESR"); net("VBUS", (f"CB{n}", 1)); net("GND", (f"CB{n}", 2))
    for n in range(1, 5): add(f"CM{n}", "C1210", "10u 50V", "X7R"); net("VBUS", (f"CM{n}", 1)); net("GND", (f"CM{n}", 2))
    add("JC", "HDR2x8", "Controller I/F", "2.54 mm header")
    jc = {1: "AUX12", 2: "GND", 3: "TX1_IN", 4: "TX2_IN", 5: "REF_I1", 6: "REF_I2", 7: "FAULT1_N", 8: "FAULT2_N", 9: "ISENSE1", 10: "ISENSE2", 11: "NTC_SENSE", 12: "GND", 13: "MONO_OUT", 14: "VCM_IN", 15: "SHIELD", 16: "GND"}
    for p, nm in jc.items(): net(nm, ("JC", p))
    add("RD1A", "R2512", "235R 2W pulse", "damping resistor (series pair = 470 ohm)"); add("RD1B", "R2512", "235R 2W pulse", "damping resistor")
    net("DRAIN1", ("RD1A", 1)); net("DMP1", ("RD1A", 2), ("RD1B", 1)); net("VBUS", ("RD1B", 2))
    add("CMON", "C1210", "100n 630V", "HV coupling cap for the MONO receive tap"); add("RBIAS", "R0603", "100k", "bias to VCM")
    net("DRAIN1", ("CMON", 1)); net("MONO_OUT", ("CMON", 2), ("RBIAS", 1)); net("VCM_IN", ("RBIAS", 2)); add("RSHD", "R0603", "1M", ""); net("SHIELD", ("RSHD", 1)); net("GND", ("RSHD", 2))
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
    add("M12", "OKI3", "12 V 1.5 A switching module", "Murata OKI-78SR-12/1.5-W36 class (Vin 15-36 V)"); net("VBUS", ("M12", 1)); net("GND", ("M12", 2)); net("AUX12", ("M12", 3))
    add("C12A", "C1210", "22u 25V", "X7R"); add("C12B", "C0603", "100n", "X7R"); net("AUX12", ("C12A", 1), ("C12B", 1)); net("GND", ("C12A", 2), ("C12B", 2))
    add("M5", "OKI3", "5 V 1.5 A switching module", "Murata OKI-78SR-5/1.5-W36 class (Vin 7-36 V)"); net("VBUS", ("M5", 1)); net("GND", ("M5", 2)); net("+5V", ("M5", 3))
    add("C5A", "C1210", "22u 16V", "X7R"); add("C5B", "C0603", "100n", "X7R"); net("+5V", ("C5A", 1), ("C5B", 1)); net("GND", ("C5A", 2), ("C5B", 2))
    add("FB2", "FB1812", "ferrite bead 1 A", "analog supply bead"); net("+5V", ("FB2", 1)); net("+5VA", ("FB2", 2), ("CV1", 1), ("CV2", 1), ("CV3", 1))
    add("CV1", "C1210", "10u 16V", "X7R"); add("CV2", "C0603", "100n", "X7R"); add("CV3", "C0805", "1u", "X7R"); net("GND", ("CV1", 2), ("CV2", 2), ("CV3", 2))
    add("UL", "SOT223", "AMS1117-3.3", "3.3 V LDO for ADC I/O"); net("+5V", ("UL", 3)); net("GND", ("UL", 1)); net("+3V3D", ("UL", 2), ("UL", 4), ("CL1", 1), ("CL2", 1))
    add("CL1", "C1210", "22u 10V", "X7R"); add("CL2", "C0603", "100n", "X7R"); net("GND", ("CL1", 2), ("CL2", 2))
    # analog mux for slow signals
    add("UM", "HC4051", "74HC4051", "Nexperia/TI 74HC4051D"); add("CM1", "C0603", "100n", "X7R")
    net("P3V3", ("UM", 16), ("CM1", 1)); net("GND", ("UM", 8), ("UM", 7), ("UM", 6), ("UM", 9), ("UM", 1), ("UM", 2), ("UM", 4), ("UM", 5), ("UM", 12), ("UM", 15), ("CM1", 2))
    net("ISENSE1", ("UM", 13)); net("NTC_SENSE", ("UM", 14)); net("MUX_S0", ("UM", 11)); net("MUX_S1", ("UM", 10)); net("MUX_COM", ("UM", 3), ("RMO", 1))
    add("RMO", "R0603", "1k", ""); add("CMO", "C0603", "1n", "C0G"); net("MUX_OUT", ("RMO", 2), ("CMO", 1)); net("GND", ("CMO", 2))
    # reference PWM filters (two-pole RC) and VBUS sense
    add("RR1", "R0603", "10k", ""); add("RR2", "R0603", "10k", ""); add("CR1", "C0603", "1u", "X7R"); add("CR2", "C0603", "1u", "X7R")
    net("REF_PWM1", ("RR1", 1)); net("REF_N1", ("RR1", 2), ("CR1", 1), ("RR2", 1)); net("REF_I1", ("RR2", 2), ("CR2", 1)); net("GND", ("CR1", 2), ("CR2", 2))
    add("RV1", "R0603", "100k", "0.1%"); add("RV2", "R0603", "10k", "0.1%"); add("CV4", "C0603", "100n", "X7R")
    net("VBUS", ("RV1", 1)); net("VBUS_SENSE", ("RV2", 1), ("RV1", 2), ("CV4", 1)); net("GND", ("RV2", 2), ("CV4", 2))
    # handle: trigger + dial (the only things that leave the head besides power)
    add("JTR", "HDR1x5", "Handle: +3V3 GND TRIG DIAL SHLD", "shielded 4-core + drain"); net("P3V3", ("JTR", 1)); net("GND", ("JTR", 2)); net("TRIG_EXT", ("JTR", 3), ("RT1", 1)); net("DIAL_EXT", ("JTR", 4), ("RD1", 1)); net("SHIELD", ("JTR", 5), ("RSH", 1), ("CSH", 1))
    add("RSH", "R0603", "1M", ""); add("CSH", "C0603", "1n 100V", "C0G"); net("GND", ("RSH", 2), ("CSH", 2))
    for k, (ext, inn) in enumerate((("TRIG_EXT", "TRIG_IN"), ("DIAL_EXT", "DIAL_IN")), 1):
        r = "RT1" if k == 1 else "RD1"; add(r, "R0603", "1k", "series protection"); add(f"DH{k}", "DSOD", "BAS16", ""); add(f"DL{k}", "DSOD", "BAS16", ""); add(f"CQ{k}", "C0603", "10n", "X7R"); add(f"RP{k}", "R0603", "10k", "pull-up")
        net(inn, (r, 2), (f"DH{k}", 2), (f"DL{k}", 1), (f"CQ{k}", 1), (f"RP{k}", 1)); net("P3V3", (f"DH{k}", 1), (f"RP{k}", 2)); net("GND", (f"DL{k}", 2), (f"CQ{k}", 2))
    # headers to the receiver boards, PB1R and the power
    add("JA", "HDR2x6S", "to AB1A J2", "1.27 mm 2x6 header"); add("JB", "HDR2x6S", "to AB1B J2", "1.27 mm 2x6 header")
    for ref, sd in (("JA", ["SDOA1", "SDOA2", "SDOA3"]), ("JB", ["SDOB1", "SDOB2"])):
        names = ["+5VA", "GND", "+3V3D", "GND", "SCLK", "CS"] + sd + (["BLANK", "GND", "GND"] if ref == "JA" else ["BLANK", "MONO_IN_NC", "VCM_OUT_NC", "GND"])
        for i, nm in enumerate(names, 1): net(nm, (ref, i))
    add("JPB", "HDR2x4", "to PB1R: 12V GND TX1_IN REF_I1 FAULT1_N ISENSE1 NTC GND", "2.54 mm header")
    for i, nm in enumerate(["AUX12", "GND", "TX1_IN", "REF_I1", "FAULT1_N", "ISENSE1", "NTC_SENSE", "GND"], 1): net(nm, ("JPB", i))
    add("JVB", "TERM4", "to PB1R: VBUS VBUS GND GND", "5.08 mm terminal block"); net("VBUS", ("JVB", 1), ("JVB", 2)); net("GND", ("JVB", 3), ("JVB", 4))
if PW == "R":
    # ------------------------------------------------------------------ PB1R: single-channel TX power stage for the head vault (70 x 70)
    add("JP", "TERM4", "Power in: VBUS VBUS GND GND", "5.08 mm terminal block 10 A"); net("VBUS", ("JP", 1), ("JP", 2)); net("GND", ("JP", 3), ("JP", 4))
    for n in range(1, 7): add(f"CD{n}", "CAPD", "150u 35V polymer Ta", "KEMET T52x/Panasonic POSCAP class, low ESR"); net("VBUS", (f"CD{n}", 1)); net("GND", (f"CD{n}", 2))
    for n in range(1, 5): add(f"CM{n}", "C1210", "10u 50V", "X7R"); net("VBUS", (f"CM{n}", 1)); net("GND", (f"CM{n}", 2))
    add("JC", "HDR2x4", "Controller I/F: 12V GND TX1_IN REF_I1 FAULT1_N ISENSE1 NTC GND", "2.54 mm header")
    for i, nm in enumerate(["AUX12", "GND", "TX1_IN", "REF_I1", "FAULT1_N", "ISENSE1", "NTC_SENSE", "GND"], 1): net(nm, ("JC", i))
    add("RD1A", "R2512", "235R 2W pulse", "damping resistor (series pair = 470 ohm)"); add("RD1B", "R2512", "235R 2W pulse", "damping resistor")
    net("DRAIN1", ("RD1A", 1)); net("DMP1", ("RD1A", 2), ("RD1B", 1)); net("VBUS", ("RD1B", 2))
    add("CMON", "C1210", "100n 630V", "HV coupling cap for the MONO receive tap"); add("RBIAS", "R0603", "100k", "bias to VCM")
    net("DRAIN1", ("CMON", 1)); net("MONO_OUT", ("CMON", 2), ("RBIAS", 1)); net("VCM_IN", ("RBIAS", 2)); add("RSHD", "R0603", "1M", ""); net("SHIELD", ("RSHD", 1)); net("GND", ("RSHD", 2))
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
    for i in (1, 2, 3): add(f"RD{i}", "R2512", "110R", "damping resistor chain, 3 in series = 330 R (600 V)")
    net("DRAIN1", ("RD1", 1)); net("N1", ("RD1", 2), ("RD2", 1)); net("N2", ("RD2", 2), ("RD3", 1)); net("VBUS", ("RD3", 2))
    add("RK1", "R0603", "100", ""); add("CK1", "C0603", "100p", "C0G"); add("RPU1", "R0603", "10k", ""); add("RF1", "R0603", "1k", "")
    net("SRC1", ("RK1", 1)); net("ISENSE1", ("RK1", 2), ("CK1", 1), ("U3", 2)); net("GND", ("CK1", 2)); net("REF_I1", ("U3", 3)); net("OC1_OUT", ("U3", 1), ("RPU1", 1), ("RF1", 1)); net("AUX12", ("RPU1", 2)); net("FAULT1_N", ("RF1", 2))
    add("RT1", "R1206", "100k", "HV tap resistor (200 V)"); add("RT2", "R1206", "100k", "HV tap resistor (200 V)"); add("JM", "HDR1x2", "MONO tap -> AB1B (PRELIMINARY, needs level-shift design)", "2.54 mm header")
    net("DRAIN1", ("RT1", 1)); net("TAPMID", ("RT1", 2), ("RT2", 1)); net("MONO_TAP", ("RT2", 2), ("JM", 1)); net("GND", ("JM", 2))
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
