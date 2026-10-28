# LB1-v6: clocked LEDs fed in the idle time (owner decision 2026-10-28)

Owner request: switch to clocked LEDs (APA102 class) fed during the idle time so no TX pulse is dropped; if a better way exists that isolates the LED
process on its own and there is room, investigate it; if not, feed during idle time. All facts below are from datasheets on disk
(data/seed/datasheets, logged in DATASHEET_LOG.md). MODELED / tool-checked; nothing built.

## Why the change was needed at all
1. One-wire LEDs (SK6812 class: 800 kbit/s, 24 bit per LED, 80 us reset) need one unbroken 2.06 ms stream for 66 LEDs. It never fits after the receive
   window, so the firmware would have to drop 1-2 pulses every 13-27 periods: 5.0-7.7 % fewer pulses (src/sim/fw_timeline.py).
2. Found while checking: LB1-v5's part, the SK6812MINI-E (Rev. 02), is a REVERSE-mount LED (3.2 x 2.8 x 1.78 mm, body through a board cutout, pads
   1.8 mm long outside it). LB1-v5 had small pads inside the body outline and no cutout, and the stack check used 0.8 mm for its height. The v5 board
   could not take the part it was drawn for (CORRECTIONS).

## Options compared (datasheet facts)
| Option | Interface | Package | Fits LB1 | Pulses dropped | During the receive gates |
|---|---|---|---|---|---|
| SK6812MINI-E (v5) | one-wire | 3.2 x 2.8 x 1.78 reverse | no (footprint) | 5-7.7 % | data stream only in dropped slots; LED PWM 1.2 kHz free-running |
| SK6805-2427 | one-wire | 2.4 x 2.7 x 1.1 | needs 0.1 mm more roof gap | 5-7.7 % | same |
| APA102C (iPixel) | clocked, no max clock in the sheet | 5 x 5 x 1.4 | no (roof) | 0 | LED PWM from an 800-1200 kHz oscillator |
| SK9822 (OPSCO Rev.01) | clocked, 30 MHz | 5 x 5 x 1.6 | no: pads 0.03 mm apart at LD13 / LD31, 0.6 mm roof pocket | 0 | PWM 1.2 kHz |
| TLC5947 driver + plain RGB LEDs (isolated) | 30 MHz SPI, BLANK pin, own 4 MHz oscillator | 9 x HTSSOP-32 11 x 6.2 | no room on LB1 (0.35-0.5 mm vertical gaps) | 0 | the only option that can stop ALL LED switching in a gate (BLANK) |
| **SK9822-EC20 (OPSCO SK9822-EC20-000 Rev. A/0)** | **clocked, 15 MHz** | **2.0 x 2.0 x 0.65** | **yes, same 66 positions, 0.65 mm under the roof** | **0** | **no data or clock edge in a gate; LED PWM 1.2 kHz free-running** |

The isolated option (a driver with a blanking input) is the only way to silence the LED currents inside every receive gate, but nine driver ICs do
not fit LB1 or its vertical gaps. Per the owner's rule, the design feeds clocked LEDs in the idle time: SK9822-EC20.

## What changed (generators only)
- pw_design.py: library part SK9822EC20 (pins 1 SDO, 2 GND, 3 SDI, 4 CKI, 5 VDD, 6 CKO; pads 0.76 x 0.46 at x +-0.68, y 0 / +-0.86, read off the
  drawing; the "0.7-6" dimension is read as 0.76 mm); LB1 chains LD_D (SDI -> SDO) and LD_C (CKI -> CKO) through all 66 LEDs; second 74AHCT1G125 (U2) and
  33 ohm RSC on the clock (TI SCLS378P: pins 1 OE, 2 A, 3 GND, 4 Y, 5 VCC; VIH 2.0 V; tpd 6 ns max at 5 V); JLB = +5V, LED_IN, LED_CLK, GND (was +5V,
  LED_IN, GND, GND).
- CB1D-C1: JLB.3 = LED_CLK from Pico pin 19 (a PIO pin; Pico 2 W pinout ASSUMPTIONS 22).
- Harness v4: W037 GND on JLB.4, new W066 LED_CLK on JLB.3.
- stack_check: LED height 0.65 mm (gap to the roof 0.65 mm, rule 0.3).
- fw_timeline: SK9822 frame 64 + 32 x 66 = 2176 bit at 8 MHz = 272 us, placed after the last gate (449 us) in every period: 0 % pulses dropped, display
  refresh = PRF (400-800 Hz); generated header PF_LED_* constants.

## Still open
- LED policy (owner decision 2026-10-28): DARK DURING SWEEP. Entering a sweep the firmware sends one all-off frame (PWM duty 0/256), then no LED clock,
  data or LED current until the sweep ends; between sweeps the LEDs are lit and refreshed in the idle slot. This removes the 1.2 kHz LED PWM from the
  receive gates with no hardware change (fw_timeline.py, PF_LED_DARK_DURING_SWEEP). Still to measure on the first article: receive noise with LEDs dark
  and lit (U-BENCH), to decide whether a ferrite sheet under LB1 or tighter LED current loops are worth adding later.
- The 0.76 mm pad dimension and the land pattern want a check on a printed footprint against a real part.
- Pico 2 W pin 19 as a PIO output and the 8 MHz LED clock over the 60 mm AWG30 lead: scope on the first article.
- TX_r4 contains CB1D-B: a TX_r5 release is needed for CB1D-C1.
