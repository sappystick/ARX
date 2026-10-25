# Datasheet log (Step 5, read 2026-10-25)

Evidence file for the datasheet groups that replaced U-DS-PARTS (`scripts/signoff_status.py` DS_GROUPS). A group counts as closed only when its row is gone from docs/UNVERIFIED.md AND its heading here reads `## <ID>: VERIFIED`. Every number is quoted from the manufacturer PDF named in its row (document number and revision). Pages that could not be read are listed with the URL tried and the reply; nothing was filled from memory. A verified rating is a datasheet number, not a measurement of our parts.

## U-DS-PB1R: VERIFIED (PB1R bulk bank, shunt, clamp diode, damping resistors, comparator)

| Part (ref) | Source | Numbers used | Design effect |
|---|---|---|---|
| Panasonic EEHZC1H101P hybrid polymer-Al (PB1R CB1-CB9, PM2 CB1) | Panasonic "Technical Data ZC series" (Conductive Polymer Hybrid Aluminum Electrolytic Capacitor), https://industrial.panasonic.com/content/data/CP/PDF/ABA0000PE429.pdf, PDF of 2015-07-22, page ZC-16 | 50 V, 100 uF +-20 % (120 Hz), phi 10.0 x 10.2 mm (size code G: A, B 10.3; H 12.0 max; P 4.6; W 0.9), ESR 28 mohm max at 100 kHz, ripple 1600 mA rms max (100 kHz, 105 C), 125 C 4000 h, leakage 50 uA max. The 50 V ZC range ends at 100 uF (ZC-12 to ZC-16). | Replaces the six unverified 150 uF / 50 V polymer-Ta (7343-43): 9 cans keep 900 uF nominal, 720 uF at -20 % (>= 625 uF needed for 5 % droop at 19.6 V). PM2 CB1 470 uF -> 100 uF (no 470 uF 50 V part in this can). Eddy: the cans are closed aluminium loops that do not decay before the gate (pb1r_check WARN, OPEN_ITEMS 34). Land pattern: KiCad CP_Elec_10x10 (pads 4.0 x 2.6 at +-4.4 mm) covers the terminal span P 4.6 to H 12.0; Panasonic's recommended land was not in this document (bench/CAM item). Surge-voltage rating not in this document. |
| KEMET T521 polymer Ta, 50 V | not read from KEMET (search only: the largest 50 V X-case part listed in KEMET kits was 33 uF) | none used | the 150 uF / 50 V 7343-43 part was not found: replaced, see above |
| Vishay WSL2512 Power Metal Strip, 10 mohm (RS1S) | Vishay "WSL", https://www.vishay.com/docs/30100/wsl.pdf, document 30100, revision 23-Nov-2023 | WSL2512: 1.0 W at 70 C; 0.003-0.5 ohm at +-0.5 % / 0.0005-0.5 ohm at +-1 % | value text "10m 3W" -> "10m 1W"; the modeled RMS shunt current 1.8 A gives 32 mW (pb1r_check). Ordering code not checked. |
| Vishay WSK2512 four-terminal (considered for RS1S) | https://www.vishay.com/docs/30108/wsk2512.pdf, document 30108, revision 11-Dec-2023 | 1.0 W at 70 C, 0.0005-0.2 ohm; solder pad table a/b/c/d/e/l (0.005-0.2 ohm: a 2.29, b 3.30, c 0.76, d 0.51, e 1.70, l 3.68 mm) | NOT adopted: the 3-D pad drawing places the sense pads diagonally but gives no dimension for their position along the force-pad edge, so the land cannot be generated without guessing. Two-pad R2512 with the Kelvin sense track kept (handoff default). |
| Good-Ark ES3J (PB1R DC1) | Good-Ark "ES3D thru ES3J", https://goodarksemi.com/docs/datasheets/super_fast_recovery_rectifiers/ES3x.pdf (PDF modified 2025-06-16) | VRRM 600 V, IF(AV) 3.0 A, IFSM 100 A (8.3 ms), VF 1.7 V max at 3 A, trr 35 ns typ (IF 0.5 A, IR 1.0 A, Irr 0.25 A), CJ 40 pF | **WATCH (rule 6)**: 600 V < 630 V. No >= 630 V ultrafast SMC part was readable from a manufacturer: Vishay ES3 (https://www.vishay.com/docs/88589/es3.pdf, 88589, 08-Apr-2020) stops at 200 V; Vishay MURS340/360 (https://www.vishay.com/docs/88816/murs340.pdf, 88816, 08-Apr-2020) is 400/600 V, trr 50 ns; Vishay RS3 (https://www.vishay.com/docs/88709/rs3a.pdf, 88709, 25-Feb-2020) reaches 800 V but is a fast (trr 150/250/500 ns), not ultrafast, rectifier; Diodes, onsemi, MCC and Littelfuse pages answered 403 / Cloudflare. Modeled stress 466 V max (78 % of 600 V). ES3J kept. |
| Vishay D/CRCW e3, CRCW2512 (CB1D RDM1-3, 3 x 110 ohm) | Vishay "D/CRCW e3", https://www.vishay.com/docs/20035/dcrcwe3.pdf, document 20035, revision 14-Apr-2026 | CRCW2512 e3: P70 1.0 W, operating voltage Umax 500 V AC rms/DC, permissible voltage against ambient (insulation, 1 min) 300 V, 1 ohm - 10 Mohm | the stress table assumed 200 V working voltage: now 500 V (margin rises). WATCH: insulation 300 V against ambient, the chain node reaches about 466 V: the resistor bodies must not touch grounded metal or a conductive coating. |
| TI LM393 (PB1R U3) | TI SLCS005AH, revised April 2025, https://www.ti.com/lit/ds/symlink/lm393.pdf | pins (SOIC): 1 1OUT, 2 1IN-, 3 1IN+, 4 GND, 5 2IN+, 6 2IN-, 7 2OUT, 8 VCC (Table 4-1); supply (non-V devices) 2-30 V recommended, 36 V absolute; input range 0 to (V+) - 2.0 V | pinout matches `pw_design.LIB["LM393"]`; AUX12 = 12 V is inside the range; REF_I1 / ISENSE1 (about 0.2 V) are inside the input range |

## U-DS-POWERPATH: VERIFIED (PM2 and CB1D input: TVS, P-FET, gate zener, fuse)

| Part (ref) | Source | Numbers used | Design effect |
|---|---|---|---|
| SMCJ33A / SMCJ30A TVS (PM2 DTVS, CB1D DTV) | Vishay "SMCJ5.0A thru SMCJ188CA", https://www.vishay.com/docs/88394/smcj.pdf, document 88394, revision 09-Jan-2024 (Vishay second-source datasheet for the same part numbers; the Littelfuse page answered 403) | 1500 W (10/1000 us). SMCJ33A: VWM 33 V, VBR 36.7-40.6 V at 1 mA, IR 1.0 uA, IPPM 28.1 A, VC 53.3 V. SMCJ30A: VWM 30 V, VBR 33.3-36.8 V, IR 1.0 uA, IPPM 31.0 A, VC 48.4 V; VBR temperature coefficient 0.099-0.100 %/C | **Choice: SMCJ30A** (same SMC footprint). SMCJ33A's 53.3 V clamp exceeds the 50 V capacitors; SMCJ30A clamps at 48.4 V and its rated stand-off (30 V) is above the 29.4 V pack maximum. WATCH in the stress table: stand-off margin 2 % (rule 5 %); VBR min 33.3 V at 25 C is still 31.8 V at -20 C. |
| Vishay Si4401FDY P-MOSFET (PM2 Q1) | https://www.vishay.com/docs/75996/si4401fdy.pdf, document 75996, S17-1783-Rev. A, 27-Nov-17 | SO-8 single: 1, 2, 3 S; 4 G; 5-8 D (drawing, top view); VDS -40 V; VGS +-20 V; RDS(on) 0.0118 typ / 0.0142 max ohm at VGS -10 V, ID -10 A; 0.0183 max at -4.5 V; VGS(th) -1 to -2.3 V; EAS 20 mJ | pinout matches `PMOS_SO8`; the 15 mohm assumption holds (14.2 mohm max) |
| Vishay BZT52C15 zener (PM2 DZ1) | Vishay "BZT52 Series", https://www.vishay.com/docs/86342/bzt52_series.pdf, document 86342, Rev. 1.0, 22-Dec-2022 | VZ 14.25 / 15 / 15.60 V at IZT1 5 mA | Q1 gate clamp 15.6 V max < VGS 20 V |
| Bourns SF-1206S500-2 fuse (PM2 F1, CB1D F1) | Bourns "SinglFuse SF-1206S Series", https://www.bourns.com/docs/product-datasheets/sf-1206s.pdf, REV. J 04/21 | slow blow, 5.00 A, 32 VDC, interrupting 50 A at 32 VDC, 0.013 ohm typ, I2t 2.533 A2s; recommended pad layout 2.2 mm gap, 4.7 mm overall, 1.65 mm pad height (pads 1.25 x 1.65 mm); operating -20 to +105 C | replaces the "Littelfuse 0453005 class (verify DC rating)" 1812 part, whose page answered 403: new footprint FUSE1206B on PM2 and CB1D. 32 VDC vs 29.4 V pack maximum. |
| Amass MT60 (pack dock) | Amass "规格书" (specification) V1.2, MT60-M / MT60-F, PDF of 2016-06-07, manufacturer's sheet hosted by distributor ChipDip: https://static.chipdip.ru/lib/502/DOC008502173.pdf | DC 500 V, RC 30 A, MC 60 A, contact resistance 0.45 mohm, 1000 mating cycles, 12 AWG recommended, -20 to 120 C | ratings as assumed. The body envelope (ASSUMPTIONS 25) is in the drawing image, not read: stays in U-DS-PACK. |

## U-DS-RXAMP: VERIFIED (receive amplifier, VCM buffer, mux; OPEN_ITEMS 27)

| Part | Source | Numbers used | Design effect |
|---|---|---|---|
| TI OPA2365 (AB1 UB: VREF and VCM buffers) | TI SBOS365G, revised May 2023, https://www.ti.com/lit/ds/symlink/opa2365.pdf | supply 2.2-5.5 V; IB 0.2 pA typ; ISC +-65 mA; open-loop output impedance 30 ohm (1 MHz); section 8.3.3: "When operating in the unity-gain configuration, the OPAx365 remain stable with a pure capacitive load up to approximately 1 nF"; series resistor "typically 10 ohm to 20 ohm" for larger loads | OPEN_ITEMS 27, DC part: driving RS2 (1 kohm) into the idle MONO input costs at most 175 nA x 1 kohm = 0.18 mV: yes. NEW FINDING (OPEN_ITEMS 30): the buffers drive CVM 1 uF and CRF 10 uF per ADC directly at unity gain, far above the 1 nF the datasheet states. |
| TI OPA2211 (AB1 U1/U2) | TI SBOS377L, revised January 2020, https://www.ti.com/lit/ds/symlink/opa211.pdf, table 6.6 "Standard Grade OPAx211A" | supply 4.5-36 V; IB +-60 typ / +-175 max nA (25 C), +-250 nA max OPA2211A (-40 to 125 C); IOS +-25 / +-100 nA; en 1.1 nV/rtHz at 1 kHz, 1.4 at 100 Hz; In 1.7 pA/rtHz at 1 kHz; common-mode range for VS < +-5 V: (V-) + 2 V to (V+) - 1.4 V | noise as assumed (1.1 nV/rtHz). NEW FINDING (OPEN_ITEMS 31): on the single 5 V rail the input range is 2.0-3.6 V; VCM = VREF / 2 sits about 0.05 V above its lower end (VREF 4.096 V assumed, REF5041 not read). |
| TI CD74HC4051 (CB1D UM, 74HC4051) | TI SCHS122O, revised January 2026, https://www.ti.com/lit/ds/symlink/cd74hc4051.pdf | pins: 1 A4, 2 A6, 3 COM, 4 A7, 5 A5, 6 E (active low), 7 VEE, 8 GND, 9 S2, 10 S1, 11 S0, 12 A3, 13 A0, 14 A1, 15 A2, 16 VCC; VCC abs max 7 V; VCC - VEE 2-10 V; ron 70 ohm typ at 4.5 V | pinout matches `HC4051`; the Nexperia sheet (https://assets.nexperia.com/documents/data-sheet/74HC_HCT4051.pdf) answered 403, so the TI part is the verified one |

## U-DS-HALL: VERIFIED (HB2 trigger Hall switch)

| Part | Source | Numbers used | Design effect |
|---|---|---|---|
| TI DRV5023BIQLPG (HB2 HS1) | TI SLIS151G, revised September 2016, https://www.ti.com/lit/ds/symlink/drv5023.pdf | LPG (TO-92) pins: 1 VCC, 2 GND, 3 OUT (open drain, "requires a resistor pullup"); VCC 2.5-38 V; supply current 2.7 mA typ, 3.5 mA max; rDS(on) 22 ohm typ (25 C) / 50 ohm max (125 C) at 3.3 V, 10 mA; off leakage 1 uA max; output delay 13 typ / 25 max us; BI: BOP 6 / 14.5 / 24 mT, BRP 3 / 6 / 9 mT (min / typ / max, -40 to 125 C). TO-92 is orderable only as AJ and BI (FA is SOT-23 only, package addendum). | Chosen over AJ and FA because its worst-case BOP max / BRP min ratio (24 / 3 = 8) is the easiest to meet with the >= 2 mm extra magnet travel. Pin order matches `HALL_SW`. Vsat = I x 50 ohm, far below the 0.4 V the trigger check assumes. OPEN (OPEN_ITEMS 32): the magnet must give >= 24 mT at rest and <= 3 mT pressed at the sensor; no magnet field model yet. |

## U-DS-TXDRIVE: UNVERIFIED (main FET and gate driver)

| Part | URL tried | Reply | Kept as |
|---|---|---|---|
| Infineon IPB65R095C7 (Q1A/B) | https://www.infineon.com/cms/en/product/power/mosfet/n-channel/500v-900v/ipb65r095c7/ (curl and headless browser) | HTTP 202, "Page Not Found" (bot challenge); no direct PDF link found by search | 650 V, 24 A, 95 mohm class, Qg 45 nC (ASSUMPTIONS 19): unverified |
| Microchip TC4420 (U1) | https://ww1.microchip.com/downloads/en/DeviceDoc/20001419F.pdf (curl and browser) | HTTP 403 | 6 A driver, pinout in `LIB["TC4420"]`: unverified |

## U-DS-OKI: UNVERIFIED (12 V and 5 V switching modules)

| Part | URL tried | Reply | Kept as |
|---|---|---|---|
| Murata OKI-78SR-12/1.5-W36, OKI-78SR-5/1.5-W36 (M12, M5) | https://www.murata.com/products/productdata/8807029129246/oki-78sr.pdf, https://www.murata.com/products/productdata/8807037992990/oki-78sr.pdf (curl and browser) | HTTP 500 | Vin 15-36 V (12 V model), 7-36 V (5 V model), pinout 1 VIN / 2 GND / 3 VOUT: unverified. Copies exist on third-party sites (pdp8online.com, rgbautomatyka.pl), not used. |

## U-DS-PACK: UNVERIFIED (cells and connector body)

| Part | URL tried | Reply | Kept as |
|---|---|---|---|
| Molicel INR-18650-P30B | https://www.molicel.com/wp-content/uploads/INR18650P30B-V2-80092.pdf | HTTP 404; the only PDF found is a copy on fsaeonline.com (not a manufacturer or distributor host), not used | 3.0 Ah, 3.6 V, 4.2 V charge, 30 A continuous, 18.6 x 65.3 mm (ASSUMPTIONS 27): unverified |
| Amass MT60 body envelope | the Amass sheet above (ratings read) | the envelope is in the drawing image, not read | 20 x 16.5 x 8.6 mm (ASSUMPTIONS 25): unverified |

## U-DS-BAV199: UNVERIFIED (receive input clamp)

| Part | URL tried | Reply | Kept as |
|---|---|---|---|
| Nexperia BAV199 (AB1 D1-D3) | https://assets.nexperia.com/documents/data-sheet/BAV199.pdf (curl, browser, WebFetch) | HTTP 403 | low-leakage double diode, surge rating (ASSUMPTIONS 19/21): unverified |

## U-DS-HVTERM: UNVERIFIED (flyback-net connector and clamp resistor bank)

| Part | URL tried | Reply | Kept as |
|---|---|---|---|
| PB1R JL1, 5.08 mm 2-way terminal block on DRAIN1 / VBUS | Phoenix Contact product page for MKDS 1,5/2-5,08 (1715721), URL not found by search; https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721 | HTTP 404 | distributor listings (not used) give 250 V (III/3), 400 V (III/2), 630 V (II/2): whether the 466 V flyback peak meets rule 6 depends on the category the manufacturer states |
| PB1R RCL1, 5 kohm 10 W resistor bank under the lid | no part chosen | - | voltage rating unknown (BOM text has none) |
