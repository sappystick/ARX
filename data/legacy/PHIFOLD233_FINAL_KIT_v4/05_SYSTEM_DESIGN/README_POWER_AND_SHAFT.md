# PHI-FOLD 233 v4 — Power System, Hot-Swap Batteries, Dual-Chamber Shaft

Builds on `PHIFOLD233_FINAL_KIT_v3` (one-piece head, receiver boards AB1A/AB1B, antenna board SB1). **This kit adds the power, driver and shaft hardware.**

## 1. Status at a glance
| Item | Status |
|---|---|
| Power architecture, pack, hot-swap, protection, TX-stage calculations | Done (`power_system.json`) |
| **Dual-chamber shaft spine** (12 printable part types) | Done, watertight, fit-checked |
| **PM1** power-path/protection board: schematic, netlist, BOM, KiCad PCB | Done to **placement** (28 × 136 mm) |
| **PB1** TX-driver board: schematic, netlist, BOM, KiCad PCB + HV rules | Done to **placement** (28 × 224 mm) |
| PM1 / PB1 **routing and Gerbers** | **Not done.** Hand-route in KiCad (HV and 20–30 A nets) |
| **Controller / head-interface board** (MCU, DSP, 5 V/3.3 V rails for AB1, X/Y drivers, audio, UI pod) | **Not designed** |
| Bench, thermal, EMC or HV tests; any real build | **None** |

## 2. Corrections to earlier results (important)
- **Turn-off time.** With a 500 V clamp, the outer band (102.6 µH) turns off in **1.64 µs at 8 A** and **4.1 µs at 20 A**. The earlier work assumed 1 µs. The 5 µs gate is fine in scan mode but **unusable in boost**; start boost sampling at about 8–10 µs.
- **Clamp energy.** A 20 A pulse stores 20.9 mJ. Dissipated in a clamp at 800 Hz that is **16.7 W**, which this design cannot cool. The earlier "75% recovery" assumption has no design behind it. **Boost therefore runs at 300 Hz (6.3 W clamp)**; scan stays at 800 Hz (2.7 W).
- **Equal-depth drive** (13 A scan / 33 A boost) is not supported: boost clamp energy would be 56 mJ.

## 3. Power system
| | Value |
|---|---|
| Pack | 7S1P 18650 per cartridge, 24.5–29.4 V (25.9 V nominal, 21.0 V cutoff), 90.7 Wh, about 460 g |
| Cartridges | **Two**, hot-swappable; both together 181 Wh |
| Scan (8 A, 800 Hz) | 6.05 W → **15 h per cartridge, 30 h with both** |
| Trigger boost (20 A, 300 Hz, X/Y on) | 15.3 W → **5.9 h per cartridge, 11.8 h with both** |
| Bulk capacitance | PB1: 2 × 470 µF + 4 × 10 µF → about 2 V droop at a 20 A pulse |

**Hot swap (passive, no controller needed):**
1. Remove one cartridge: the other keeps the load through its OR-ing Schottky.
2. Insert the new one. Contacts mate in order **NEG (longest) → PRE (via 22 Ω into the bus) → POS and ID**.
3. The bus precharges with at most 1.1 A (τ 33 ms); the higher-voltage cartridge then carries the load.

**Protection stack:**
| Level | Protection |
|---|---|
| Cartridge BMS (buy a 7S, 30 A class unit) | OVP 4.25 V/cell, UVP 2.8 V/cell, OCP 12 A, short-circuit 40 A / 200 µs, over-temperature 60 °C, balance |
| PM1 | 5 A slow-blow 32 V fuse per cartridge, OR-ing diodes (reverse block), precharge, SMCJ33A TVS, bleeder, bus-sense divider |
| PB1 | hardware current limit (comparator, fast cut), NTC on the FET spreader; MCU watchdog must disable TX if pulses stop |

**Shielding, honestly:** 35 µm copper foil is a good *electric-field/RF* shield above about 1 MHz, but gives almost **no magnetic shielding at the 5–100 kHz pulse frequencies**. Isolation from the receiver therefore relies on distance (the spine is more than 600 mm from the coil), twisted pairs, local bulk capacitors, a short TX current loop in PB1, and blanking the receiver during TX edges. Foil lines the septum and compartment walls; ground it at one point (the PM1 sled screw).

## 4. Boards
**PM1 — power path** (28 × 136 mm, 28 parts, 18 nets, ERC 0 errors). Two cartridge blade-contact inputs (NEG, PRE, POS, ID), fuses, OR-ing Schottkys, precharge, TVS, 2 × 470 µF, bleeder, bus-sense divider, header for a COTS 36 V→12 V buck module, ferrite-filtered 12 V aux, shield RC, terminal block out, signal header out.

**PB1 — TX driver** (28 × 224 mm, 48 parts, 29 nets, ERC 0 errors).
- **Channel 1 (outer band 102.6 µH):** 2 parallel 650 V D2PAK FETs, TC4420 driver, 10 mΩ shunt, ES3J clamp diode into 2 × 0.1 µF 630 V, external 5 kΩ 10 W bleed resistor, coil terminal.
- **Channel 2 (inner band 14.9 µH):** one 100 V FET, TC4420, 10 mΩ shunt, 200 V clamp, 1 µF 100 V, external resistor.
- **Current control:** LM393 comparators (one per channel) cut gate drive when shunt voltage exceeds the controller's reference, giving cycle-by-cycle current limiting.
- **Interface header JC:** +12 V, GND, TX1_IN, TX2_IN, REF_I1, REF_I2, FAULT1_N, FAULT2_N, ISENSE1, ISENSE2, NTC_SENSE, GND.
- **High-voltage rules:** the 500 V clamp nets (DRAIN1, CLAMP1) need ≥ 1.0 mm clearance and a conformal coat (rule file included); the inner-channel nets ≥ 0.5 mm.

**Placement status:** both boards pass my placement check (0 overlaps, edge, or HV-clearance errors) but are **unrouted**. PB1's gate loop (driver to FET) is about 20 mm; shorten it when routing.

**Verify before ordering:** TC4420, LM393, D2PAK land pattern and FET part numbers, ES3J/ES2D, fuse and diode packages, the aux buck module, and all footprints.

## 5. Dual-chamber shaft spine (folder 01 and 02)
Envelope **58 × 41 mm**, total length about **807 mm**: front cap 38 + 3 battery segments × 165 + electronics segment 232 + rear cap 30, plus 12 mm spigots.

| Part | Qty | Notes |
|---|---|---|
| SH01–SH03 battery segment | 3 | two Ø22.4 cartridge bores, centre raceway 6 × 12, foil septum |
| SH04 electronics segment | 1 | upper compartment PM1, lower compartment PB1, 2.4 mm septum |
| SH05 front cap, SH06 rear cap | 1 each | cartridge entry with latch windows; cable exit |
| CT01 sleeve segment | 8 | 4 per cartridge, heat-shrink wrapped |
| CT02 contact plug, CT03 rear cap | 2 each | blade protrusions NEG 14.0 / PRE 12.2 / POS 10.6 / ID 10.6 mm |
| SL01 / SL02 sleds | 1 each | PM1 and PB1 carriers |
| LT01 latch | 2 | push-button, 3 × 8 mm spring |

**Fit check passed:** cartridge 21.6 mm in a 22.4 mm bore (0.4 mm radial clearance); PM1/PB1 stack 15.6 mm in a 16.8 mm compartment.
**Print:** PETG or ASA, 0.2 mm layers, 3 walls, 25% infill, axis vertical, no supports. Estimated mass with both cartridges: spine about 1.6 kg; whole detector about 3 kg (the earlier concept was 1.7 kg).

## 6. Wiring (spine → head)
| Run | Spec |
|---|---|
| TX leads to the head | 4 conductors, AWG 12 class, about 1.2 m (adds about 1.5 µH to the 102.6 µH coil) |
| Vbus pair | 2 × AWG 16 plus 2 × AWG 16 return |
| Aux | +12 V pair AWG 24 |
| RS-485 | 1 twisted pair AWG 26 |
| Shield | overall braid, one end grounded at PM1 |

The head's cable strip (P11) carries these plus the antenna ribbon; check the 14 × 2.8 mm channel fit when you build it.

## 7. Open items
1. **Controller / head-interface board is not designed** (MCU, ADC data path from AB1A/B, 5 V analog and 3.3 V digital rails for the AB1 boards, timing, X/Y drivers, audio and UI pod, RS-485 link). Interface headers are defined on PM1 (JS), PB1 (JC) and AB1 (J2).
2. **PM1/PB1 layout** is a hand-routing job; have a power-electronics engineer review it.
3. **Safety:** 500 V clamp and 1 mF stored charge. Add discharge verification and an interlock before any bench power-up.
4. **Physics checks still needed on a bench:** receiver overload recovery, gate-loop ringing, clamp heating, and hot-swap behaviour.
