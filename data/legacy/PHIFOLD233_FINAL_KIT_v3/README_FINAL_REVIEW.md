# PHI-FOLD 233 v3 — One-Piece Head, Receiver Boards, Review

Shared frame for every STL: z = 0 is the flat ground-facing underside of the body; +z points toward the handle.

## 0. Why the earlier attempts stalled
- The single 40 mm receiver board could not be routed: the dense ADC/clock/data fan-out and through-vias that block every layer kept it from completing, and several turns ended mid-work.
- One run also used stale results after a router bug (array bounds) crashed silently.
- Fixes that worked: split the receiver into two boards, through-hole connectors, reserved escape stubs, routing the ADC middle pins first, and via sharing.

## 1. Status review (what is complete vs open)
| Item | Status |
|---|---|
| **One-piece head body (P10)** | Complete. 3 fused shells, all watertight, 8 wire windows, trough, bay socket |
| Gapped lids, cable strip, 3-board slot rings (P04b, P05b, P11, P07b) | Complete, watertight |
| Bezel (P08), skid (P09), liner (P06) | Unchanged from the earlier kit |
| **Receiver board A (GX, GY, X8)** and **B (Y8, MONO)** | Fully routed per my checker (0 opens, 0 shorts). KiCad PCB + schematic + Gerbers + STL |
| Antenna board PF233-SB1 (8 layers) | Unchanged. Gerbers included |
| Full-system simulation on the one-piece coil | Re-run (section 4) |
| **Main/power board** (GaN TX drivers, boost, MCU, audio) | **Not designed.** Only the block diagram in the earlier electronics document |
| Any bench or print test | **None.** Everything is simulated or checked by my own tools |

## 2. One-piece head body (P10_head_body_ONE_PIECE.stl)
**Idea.** Each wire section crosses the wall facing the gallery ring at one fixed azimuth (zero-twist zone). The ring is therefore fused solid to both bands everywhere except 8 small windows (4.8 mm wide), where the wire runs vertically.

| Item | Value |
|---|---|
| Print size | Ø233 × 33.3 mm, 1.52 M triangles, 3 shells (outer band, ring, inner band) fused by 0.15 mm overlap |
| Orientation | Base down, no supports. Grooves are 1.30 × 2.45 mm, pitch 1.85 mm, ≥ 0.55 mm walls |
| Material | PETG / ASA / unfilled PA12. **No carbon fibre or metal-filled filament** |
| Bed | ≥ 250 mm |
| Body rotation | 65°, so no window falls on the 90° cable path |
| Outer-band windows (sections A/B/C/D) | 65° / 155° / 245° / 335° at the r = 72 wall |
| Inner-band windows (sections A/B/C/D) | 295.88° / 25.88° / 115.88° / 205.88° at the r = 60.4 wall |
| Lead trough | r 63.4–69.6, 7.5 mm deep; windows open straight into it |

**Coil data (4 sections per band, 2 stacked circuits per section):**
| | Outer band | Inner band |
|---|---|---|
| Turns per circuit / per section | 9 / 18 | 9 / 18 |
| Wire per section | 11.84 m | 3.68 m |
| L, R per section | 113.8 µH, 0.407 Ω | 16.3 µH, 0.127 Ω |
| All 4 sections in parallel | **102.6 µH, 0.102 Ω** | **14.9 µH, 0.032 Ω** |
| Smallest groove pitch | 1.853 mm | 1.86 mm |

**Winding procedure (per section, both bands):** (1) start at the top of the section's window and lead into the trough; (2) run down the vertical window groove to the underside; (3) follow the underside groove outward, round the rim, over the crown, and inward along the face (the groove straightens to a radial line as it nears the window); (4) drop into the window again and lay the second circuit on top of the first; (5) bring both ends out of the window top into the trough. Wire is 1.20 mm OD Litz; about 62 m total plus leads. Tie the four section starts together and the four section ends together in the trough.

**Trade-off versus the earlier two-piece design (computed from the same code):**
| Field per √W | 100 mm | 200 mm | 300 mm |
|---|---|---|---|
| Earlier v2A outer band | 144.8 | 36.1 | 13.0 |
| One-piece, outer band only | 113.5 | 30.6 (−15%) | 11.2 |
| One-piece, both bands, optimal split (inner at 0.374×) | 120.0 | 31.2 (−19% vs the earlier two-band build) | 11.4 |

The inner band adds only about 2%, so winding it is optional.

## 3. Interconnect and cable path
- A 10-wire ribbon of 36 AWG wire (0.3 mm thick) is soldered to the antenna board's J1 pads at 90°. It climbs through the 0.5 mm gap between the former rim and bezel (leave 8 mm unglued there), turns inward under the **P11 strip** (azimuth 90°, channel 14 × 2.8 mm) and runs through the gap in the trough lid (P04b) and the bay-lid seat (P05b) into the bay.
- The same strip carries the coil leads: 4 section-start leads tied to 1 conductor and 4 section-end leads tied to 1 conductor per band, 4 conductors in all.
- The bay now holds **three** boards on the P07b rings (z = 6.8 main, 15.8 analog A, 24.8 analog B, 9 mm pitch).

## 4. Receiver boards (folders 04 and 05)
| | AB1A | AB1B |
|---|---|---|
| Channels | GX, GY, X8 | Y8, MONO |
| Parts / nets | 56 / 30 | 41 / 23 |
| Tracks / vias | 627 / 69 | 448 / 53 |
| Min clearance (my checker) | **0.085 mm at 2 spots** | 0.15 mm |
| Opens / shorts | 0 / 0 | 0 / 0 |

- **Stack and process:** 6-layer, 1.6 mm, Ø40 mm, ENIG. Layers: F, GND plane, 2 signal layers, +5 V plane, B. Needs a fabricator with 0.2 mm drill / 0.45 mm vias and 0.127 mm track / 0.1 mm space.
- **Connectors:** J1 is solder pads for the antenna harness (AB1A: GX+, GY+, X8+, GX−, GY−, X8−, 2 shields; AB1B: Y8+, Y8−, 4 shields). J2 is a 2×6, 1.27 mm header (+5VA, GND, +3V3D, SCLK, CS, SDOn, BLANK; AB1B also MONO_IN and VCM_OUT). The main board must accept 5 SDO lines.
- **Files per board:** `.kicad_pcb`, `.kicad_sch`, `.net`, 12 Gerbers, drill, BOM, pick-and-place, board STL with components, layout and schematic PNGs, and the check report.

**Open items on the boards (do these before ordering):**
1. **Datasheets.** ADS8860, REF5041 and SN74LVC1G66 pin maps are from memory, as are the OPA2211 noise and bandwidth numbers. All are in one table in `afe_design.py`; correcting it regenerates everything.
2. **KiCad validation.** KiCad was not available here. Open each `.kicad_pcb` and `.kicad_sch`, press B to fill zones, and run DRC. The two 0.085 mm spots on AB1A will need a nudge.
3. **Footprints** are custom (pads pre-rotated, footprint angle 0). Compare each against the manufacturer land pattern.
4. **Bottom-side parts** (ADCs and caps) store mirrored pad coordinates; confirm after loading.

## 5. Full-system simulation on the one-piece coil (06_SIMULATION)
| | Scan 8 A | Trigger 20 A |
|---|---|---|
| Z field at 200 mm | 81 µT | 204 µT |
| 1 g gold, main coil RX | 250 mm | 300 mm |
| 10 g gold | 350 mm | 420 mm |
| Silver coin | 400 mm | 480 mm |
| System power / battery (50 Wh) | 2.7 W / 18.8 h | 12.7 W / 3.9 h |

- **Compared with the earlier build at the same drive current**, depth is about 16% lower and power about 35–43% lower. At equal *power* the field penalty is the 19% in section 2 (about −6.5% depth).
- **To get the earlier depth back**, drive about 13 A in scan and 33 A in trigger mode. That exceeds the earlier 20 A component rating, so the driver would need re-rating.
- **Classifier (GOLD mode sounds):** 10 g gold 99%, 50 g 100%, 1 g gold 68%, 0.1 g 3%, pull-tab 93%, coin 100%, foil 2%, iron 0%. Depths are idealised upper bounds (1 µV/gate noise, sphere targets, receive sections in series).
