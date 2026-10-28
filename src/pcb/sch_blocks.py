"""Functional grouping of every board's parts for the readable schematics (sch_func.py). One entry per board: blocks in signal-flow order, each with a title, a few plain lines
of what the block does (taken from the netlist and the part values: no performance numbers), and the refs. Parts not listed fall into an automatic "Other parts" block, and
sch_func.py fails if a ref is listed twice. Changing a block list never changes the netlist: the schematic is checked against it with KiCad."""
DATE = "2026-10-26"
TITLE = {"CB1D": "CB1D-C2 controller: Pico 2 W, supplies, handle cable, receive-board links, TX monitor", "LB1": "LB1-v6 display: 66 x SK9822-EC20 clocked chain with 3V3 -> 5 V data and clock buffers",
         "PB1R": "PB1R transmit stage: gate drive, two 650 V FETs, shunt, flyback clamp, overcurrent comparator, 12 V aux", "PM2": "PM2 battery dock: fuse, P-FET power switch with soft start, bulk, cord",
         "HB2": "HB2 grip board: Hall trigger, 4-position dial divider, signal cord", "AB1A": "AB1A receive analog board: 3 channels (GX, GY, X8), blanking, gain, 16-bit quad ADC (AD7389-4)",
         "AB1B": "AB1B receive analog board: 2 channels (Y8, MONO), blanking, gain, 16-bit quad ADC (AD7389-4)"}
def _by(PARTS, *prefixes): return [r for r in PARTS if r.startswith(prefixes)]
def blocks(b, PARTS, PINNET):
    if b == "PB1R": return [
        dict(title="1  Power input and bulk bank", note=["VBUS from the shaft (7S pack range 19.6 to 29.4 V) enters at JP (2 x VBUS, 2 x GND).", "Nine 100 uF 50 V hybrid cans plus four 10 uF X7R cap the DC bus of the transmit stage."],
             refs=["JP"] + [f"CB{i}" for i in range(1, 10)] + [f"CM{i}" for i in range(1, 5)], width=210),
        dict(title="2  Gate drive", note=["TX1_IN (logic from CB1D) -> RIN1 -> DRVIN1 -> U1 (TC4420, both halves paralleled) -> G1.", "G1 -> RGQ1A / RGQ1B (10 R each) -> the gates of Q1A / Q1B; RGP1 pulls G1 low.",
                                          "DOC1 can pull DRVIN1 low from the comparator output (overcurrent inhibit). U1 and the comparator run from AUX12."], refs=["RIN1", "DOC1", "U1", "CD7", "CE1", "RGP1", "RGQ1A", "RGQ1B"]),
        dict(title="3  Power switch and current shunt", note=["Q1A, Q1B (650 V super-junction FETs, in parallel) switch DRAIN1 to SRC1.", "RS1S 10 mohm shunt to GND; RK1 / CK1 take the Kelvin sense at SRC1 into ISENSE1."], refs=["Q1A", "Q1B", "RS1S", "RK1", "CK1"]),
        dict(title="4  Coil connection and flyback clamp", note=["JL1: coil outer band between DRAIN1 and VBUS.", "DC1 (ultrafast diode) clamps the flyback from DRAIN1 into CLAMP1: CL1A / CL1B (630 V film / C0G) with the external bleed RCL1 (5 k, lid bank).",
                                                               "High-voltage nets DRAIN1 and CLAMP1: 1.0 mm clearance rule on the board."], refs=["JL1", "DC1", "CL1A", "CL1B", "RCL1"]),
        dict(title="5  Overcurrent comparator", note=["U3 (LM393) compares ISENSE1 (IN-) with REF_I1 (IN+) from the controller; OC1_OUT is open collector, pulled up by RPU1 to AUX12.", "RF1 -> FAULT1_N to CB1D; the same node drives DOC1 (gate-drive inhibit). The second comparator half has its inputs grounded and its output open (OCB_NC)."],
             refs=["U3", "CU3", "RPU1", "RF1"]),
        dict(title="6  12 V aux supply", note=["M12 (OKI-78SR-12 class module, datasheet unverified, ASSUMPTIONS 29) makes AUX12 from VBUS for the driver and comparator."], refs=["M12", "C12A", "C12B"]),
        dict(title="7  Umbilical to the head (JC) and sensing", note=["JC pins: 1 SHLD, 2 GND, 3 TX1_IN, 4 REF_I1, 5 FAULT1_N, 6 ISENSE1, 7 NTC, 8 GND.", "RNTC (10 k NTC on the FET spreader) -> NTC_SENSE; RUS bleeds the cable shield to GND."], refs=["JC", "RNTC", "RUS"])]
    if b == "PM2": return [
        dict(title="1  Battery input", note=["J1: MT60 leads BAT+ / BAT- / ILK (interlock), potted at the pedestal.", "F1 5 A slow-blow in the BAT+ path -> BAT_F."], refs=["J1", "F1"]),
        dict(title="2  High-side P-FET switch with soft start", note=["Q1 (P-channel, source on BAT_F, drain to VBUS). R1 gate-to-source 47 k; DZ1 15 V zener clamps VGS.", "Gate is pulled low through R2 and the top-housing switch J3 and the ILK interlock; R3 + C1 (Miller soft start) slow the turn-on."],
             refs=["Q1", "R1", "DZ1", "R2", "R3", "C1", "J3"]),
        dict(title="3  Bulk, TVS and bleeder", note=["DTVS (30 V stand-off TVS) on VBUS; CB1 100 uF hybrid + CM1 10 uF X7R; RBL 100 k bleeder."], refs=["DTVS", "CB1", "CM1", "RBL"]),
        dict(title="4  Power cord and shield", note=["JP: coiled cord VBUS x2 / GND x2 to the head (shaft).", "JS: braid and septum mesh shields; RSH + CSH drain the shield to GND at one point."], refs=["JP", "JS", "RSH", "CSH"])]
    if b == "HB2": return [
        dict(title="1  Signal cord to the head", note=["JH: +3V3 (P3V3), GND, TRIG, DIAL, two unused, SHLD.", "RSHH (0 R) bonds the signal-cord shield to GND at the handle."], refs=["JH", "RSHH"]),
        dict(title="2  Hall trigger", note=["HS1 (digital Hall switch, open drain): magnet near at rest -> TRIG low.", "RH1 1 k in series to the cord; CH1 100 nF decoupling."], refs=["HS1", "CH1", "RH1"]),
        dict(title="3  Dial (4-position rotary)", note=["RD0 10 k pull-up from P3V3 to DIAL (= JDIAL COM). Positions: P1 straight to GND; P2 / P3 / P4 through RD2 3k3 / RD3 10 k / RD4 33 k to GND, so each position gives a different divider level."], refs=["JDIAL", "RD0", "RD2", "RD3", "RD4"])]
    if b == "LB1": return [
        dict(title="1  Data and clock entry: 3V3 -> 5 V buffers", note=["JLB: +5V, LED_IN, LED_CLK, GND from CB1D. U1 / U2 (74AHCT1G125) buffer LED_IN / LED_CLK to 5 V logic;", "RS / RSC 33 R series damping -> LD_D0 / LD_C0."], refs=["JLB", "U1", "RS", "U2", "RSC"]),
        dict(title="2  SK9822-EC20 clocked chain, 66 pixels", note=["SDO of each pixel goes straight to SDI of the next (wired); CKO -> CKI of the next by net label (LD_Cn).", "Pins: 1 SDO, 2 GND, 3 SDI, 4 CKI, 5 VDD (+5V), 6 CKO. LD66 SDO / CKO are left open (LD_END_NC / LD_CEND_NC)."], refs=_by(PARTS, "LD"), link=("1", "3"), cols=11, width=2000),
        dict(title="3  Decoupling", note=["CL1 to CL11: 100 nF across +5V / GND; CB 10 uF bulk."], refs=_by(PARTS, "CL") + ["CB"])]
    if b == "CB1D": return [
        dict(title="1  Controller", note=["U1: Raspberry Pi Pico 2 W (RP2350 + CYW43439). Powered from +5V at VSYS; 3V3_OUT = P3V3.", "JDBG: RUN / GND reset pads (SWD pads are on the Pico underside). CP1 / CP2 decouple VSYS."], refs=["U1", "JDBG", "CP1", "CP2"]),
        dict(title="2  Power input and protection", note=["JPW: VBUS x2 / GND x2 from the shaft -> F1 5 A slow-blow -> VBUS (DTV: 30 V TVS, CI1 / CI2 10 uF bulk)."], refs=["JPW", "F1", "DTV", "CI1", "CI2"]),
        dict(title="3  5 V and analog supplies", note=["M5 (OKI-78SR-5 class, datasheet unverified) makes +5V from VBUS (C5A / C5B).", "FB2 ferrite bead separates +5VA (CV1 / CV2 / CV3) for the receive boards."], refs=["M5", "C5A", "C5B", "FB2", "CV1", "CV2", "CV3"]),
        dict(title="4  3.3 V for the ADC I/O", note=["UL (AMS1117-3.3 type) makes +3V3D from +5V for the digital side of the ADCs on AB1A / AB1B."], refs=["UL", "CL1", "CL2"]),
        dict(title="5  Monitor multiplexer", note=["UM (74HC4051): S0 / S1 / S2 from the Pico, MUX_COM -> RMO / CMO -> the Pico ADC (MUX_OUT).", "Inputs in use: Y0 = ISENSE1, Y1 = NTC_SENSE, Y4 = HTA_IN; E, VEE and GND are grounded."], refs=["UM", "CM1", "RMO", "CMO"]),
        dict(title="6  Current-limit reference (REF_I1)", note=["REF_PWM1 (PWM from the Pico) -> RR1 -> REF_N1 -> RR2 -> REF_I1 with CR1 / CR2 to GND: a two-pole RC filter; REF_I1 goes to the comparator on PB1R."], refs=["RR1", "RR2", "CR1", "CR2"]),
        dict(title="7  VBUS sense", note=["RV1 100 k / RV2 10 k divider from VBUS to VBUS_SENSE (Pico ADC), CV4 filter."], refs=["RV1", "RV2", "CV4"]),
        dict(title="8  Handle cable: trigger, dial, shield", note=["JTR: +3V3, GND, TRIG, DIAL, JOYX, JOYY, SHLD (the only signal cable leaving the head).", "TRIG / DIAL inputs: series 1 k, BAS16 clamps to P3V3 / GND (DH / DL), 10 nF, pull-ups RP1 47 k / RP2 10 k.",
                                                      "RJ5 / RJ6 (0 R, not fitted): optional grounding of JTR.5 / JTR.6. RSH + CSH shield termination."],
             refs=["JTR", "RT1", "DH1", "DL1", "CQ1", "RP1", "RD1", "DH2", "DL2", "CQ2", "RP2", "RJ5", "RJ6", "RSH", "CSH"]),
        dict(title="9  Links to the receive boards AB1A / AB1B", note=["JA / JB: +5VA, +3V3D, SPI (SCLK, CS, SDOA1..3, SDOB1..2), BLANK, and from AB1B the VCM_OUT return; RJB10 (fitted 0 R) ties JB.10 to VCM_OUT."], refs=["JA", "JB", "RJB10"]),
        dict(title="10  Link to PB1R", note=["JPB: 12V-side signals only: UMB_SHLD, TX1_IN, REF_I1, FAULT1_N, ISENSE1, NTC_SENSE, GND (same order as JC on PB1R).", "RUS / CUS bleed the umbilical shield."], refs=["JPB", "RUS", "CUS"]),
        dict(title="11  Coil monitor: damping chain", note=["JCL: coil leads COIL_B (drain side) / COIL_A (VBUS side). RDM1..3 (3 x 110 R, 600 V) form the damping chain DM1 / DM2 between them.", "High-voltage nets COIL_B / DM1 / DM2: 1.0 mm rule."], refs=["JCL", "RDM1", "RDM2", "RDM3"]),
        dict(title="12  HTA timing-coil input", note=["JHTA: HTA coil leads (twisted pair from the cap). RHTA 10 k series, CHTA 1 n, DHA1 / DHA2 clamp to P3V3 / GND -> HTA_IN (multiplexer input)."], refs=["JHTA", "RHTA", "CHTA", "DHA1", "DHA2"]),
        dict(title="13  Display link", note=["JLB: +5V, LED_IN, LED_CLK (from the Pico), GND to LB1."], refs=["JLB"]),
        dict(title="14  Yaw gyro (sweep direction)", note=["UG BMI270 (alternate: ST LSM6DSO, same land) on I2C (Pico pins 21 / 22): SDO to GND, CSB and pins 2 / 3 to P3V3; CG1 / CG2 100 nF at VDDIO / VDD;", "RGA / RGL 4k7 pull-ups. Read in the idle slot after the receive window."], refs=["UG", "CG1", "CG2", "RGA", "RGL"])]
    if b in ("AB1A", "AB1B"):
        chans = {"AB1A": [("GX", 1, "U1", "A"), ("GY", 2, "U1", "B"), ("X8", 3, "U2", "A")], "AB1B": [("Y8", 1, "U1", "A"), ("MONO", 2, "U1", "B")]}[b]
        v7 = "CRC" in PARTS                                                        # AD7389-4 variant: one quad ADC replaces the ADS8860s and the REF5041 chain
        out = [dict(title="1  Connectors", note=["J1: antenna harness (raw coil signals RAW_*, and VCM returns).", "J2: main-board 2x6 header: +5VA, +3V3D, SPI (SCLK, CS, SDO*), BLANK" + (", VCM" if b == "AB1B" else "") + "."], refs=["J1", "J2"])]
        for name, i, amp, half in chans:
            refs = [f"RS{i}", f"D{i}", f"SW{i}", f"CSW{i}", f"RG{i}", f"RF{i}", f"CF{i}", f"RAAF{i}", f"CAAF{i}"] + ([] if v7 else [f"UA{i}", f"CAV{i}", f"CDV{i}", f"CRF{i}"])
            out.append(dict(title=f"{i + 1}  Channel {name}", note=[f"RAW_{name} -> RS{i} (series) -> D{i} (BAV199 clamp to +5VA / GND) -> SW{i} (74LVC1G66; BLANK opens the path) -> IN_{name} -> op-amp {amp} half {half}.",
                f"Non-inverting gain stage: RG{i} to VCM, RF{i} || CF{i} feedback; OUT_{name} -> RAAF{i} / CAAF{i} anti-alias -> ADCIN_{name} -> " + (f"UA1 input pair {i} (AD7389-4, differential: AIN+ = ADCIN_{name}, AIN- = VCM)." if v7 else f"UA{i} (ADS8860, 16-bit SAR; REF = VREF with CRF{i})."), ("The shared AD7389-4 is in block " + str(len(chans) + 4) + "." if v7 else f"SPI: SCLK / CS from the main board, SDO{i} back.")], refs=refs))
        amps = ["U1", "CO1"] + (["U2", "CO2"] if b == "AB1A" else []) + ["CB1"]
        out.append(dict(title=f"{len(chans) + 2}  Gain-stage op-amps", note=["OPA2211 dual op-amps (each half = one channel) from +5VA, decoupled CO*; CB1 bulk."], refs=amps))
        if v7:
            out.append(dict(title=f"{len(chans) + 3}  Reference and common-mode", note=["UA1 REFOUT (internal 2.5 V) -> VREF_RAW (CRF 1 uF); RD1 / RD2 (100 k) divide it to VCM_DIV (1.25 V) -> UB (OPA2365) half B -> VCM (CVM); UB half A is parked as a follower."], refs=["UB", "CBD", "RD1", "RD2", "CDF", "CVM"]))
            out.append(dict(title=f"{len(chans) + 4}  Quad simultaneous ADC", note=["UA1 AD7389-4 (16-bit, 2 MSPS, four differential inputs, internal reference): inputs ADCIN_* with VCM; unused pairs are parked on VCM.", "VCC and VLOGIC from +3V3D (CVC, CVL 1 uF), REGCAP (CRG), REFCAP (CRC), REFOUT (CRF). 2-wire readout: SDOA (channels A then C) to J2 SDO1, SDOB to J2 SDO2; SDI tied to GND; CS starts a conversion."], refs=["UA1", "CVC", "CVL", "CRG", "CRC", "CRF"]))
        else:
            out.append(dict(title=f"{len(chans) + 3}  Reference and common-mode", note=["UR (REF5041) -> VREF_RAW (CRI / CRO / CRN) -> UB (OPA2365) buffers VREF for the ADCs; RD1 / RD2 / CDF divide VREF_RAW to VCM_DIV -> UB other half -> VCM (CVM)."],
                        refs=["UR", "CRI", "CRO", "CRN", "UB", "CBD", "RD1", "RD2", "CDF", "CVM"]))
        return out
    raise KeyError(b)
