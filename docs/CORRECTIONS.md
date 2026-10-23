# Claims that were wrong or revised (do not repeat the old versions)
| Old claim | Correct statement | Evidence |
|---|---|---|
| Turn-off 2.2 us at a 500 V clamp, first gate 6 us | The clamp is a capacitor snubber; current zero 3.8-5.0 us, quiet 5.6-6.7 us, first clean gate 7.3-8.8 us (6.3 us with quadrupoles) | sim_head1.py on the PB1R/CB1D netlists |
| Analog multiplying-DAC trim cancels the leak | Needs about 20 MHz and under 10 ns; at 1 MHz it is worse than nothing; magnetic trim cannot cancel volts | sim_tanr.py |
| TANR gives +40-50 % depth from the adaptive null | Most of the gain is the input-noise fix (RS 1 kohm -> 100 ohm); the null mostly buys robustness and an earlier gate | sim_head1.py improvement steps |
| Figure-8 receive net with nulls 0.003-0.025 % | Null is first-order sensitive to misalignment: 0.5 mm -> 0.63 V; quadrupoles are 300-1000x better | sim_tanr.py |
| Blueprint 6 showed the TX driver and power in the vault | Driver and power stay in the neck module at >= 0.4 m (thermal 5.9 W, copper near the coil) | docs, shaft_calc_v20.py |
| Hood v1 (36 tangential tiles) fits | Pockets overlapped by up to 4.7 mm and corners reached r117.35; replaced by 13 radial spokes | audit_v20.py |
| Solid planes / foil in the vault are fine | tau 17.8-35 us eddy targets; use hatched planes and mesh septa | sim_cage_rx.py |
| Head dissipation limit about 1 W (27 K/W) | 8.1 K/W in the axisymmetric model; 1.13 W gives 9 K | sim_head2.py |
| 90 deg elbow | Needs about 47 deg bend (socket tilted 43 deg) for a horizontal grip at a 47 deg shaft | shaft_calc_v20.py |
| AB1A/AB1B input names X8/W8/V8 | Files say GX, GY, X8 (AB1A) and Y8, MONO (AB1B); RS3 = 1 kohm is the X8 input resistor; AB1B RS1/RS2 = 1 kohm | netlists in data/legacy |
| Pipe length 8 mm | 6.2 mm | audit |
| Cap hooks clear the LEDs | They hit at 15 deg ring phase; moved to 7.5 deg | audit |
| Quadrupole leak 0.7-2 mV (idealised rings) and 12-turn L = 90 uH, 24-turn L = 360 uH | Real copper (full rings, 0.8 mm traces, 4 layers): leak 0.01-11 mV depending on board and offset, L = 176 uH, R = 10.4 ohm | sbq_sim.py |
| Continuous spiral lobes are equivalent to rings | They drift off-centre and the four lobes stop cancelling: 3.5 V leak; partial rings gave 4 percent area-turn imbalance | sbq_gen first versions |
| Inter-lobe links and terminals are harmless | Azimuthal runs near the axis carry the induced field: 1 V; routed radially with tuned arc radii | sbq_tune.py |
| Router output is a complete connection | Track ends stop up to 0.15 mm short of pads (grid quantisation): opens in the Gerbers. LB1 v2 Gerbers are defective; v3 includes stubs | drc.py (independent) |
| Router keeps HV clearance for all copper | Vias of ordinary nets were only kept 0.2 mm from HV copper; patched in router.py | drc.py found 0.34 mm |
| The coil can be connected straight to the amplifier | 176 uH with tens of pF rings for more than 60 us: a 470-680 ohm damping resistor across each coil is required | sbq_damp.py |
| Screw bosses at r41 (90/210/330) | Moved to r28 (22.5/157.5/247.5) so the receive-board copper clears them; base plate v3 | check_v22.py |
| First clean gate about 5 us with quadrupoles | 5.2 us only for a well-nulled board; 8.3 us at 11 mV leak | sbq_damp.py |
| The 12 transmit leads reach the exit window inside the vault | Posts, ribs and track fillers blocked every circumferential path: the leads had no route. Fixed with a wall-top groove + roof channel and trimmed fillers | hub mesh check (channel volume) |
| TX lead junction part pending | TXJ1 board + cradle designed, checked and exported | tx_system.py |
| LB1 is a 1.6 mm board | Must be 0.8 mm: 1.6 mm puts the LED tops 0.3 mm into the roof; KiCad stackup, STL and notes changed | stack_check.py |
| JLB is a 1x4 pin header | A header is 9 mm tall (hits the cap): flat wire pads | stack_check.py |
| MONO is a receive-board lead (harness W043) | MONO is the transmit-coil tap from CB1D (JB.10 to AB1B.J2.10); harness receive rows still named X8/W8/V8 and 'cup A': rewritten (HARNESS_MASTER_v2) | wiring_audit.py |
| Spare receive inputs can be left open | Floating high-impedance inputs: tie to VCM | harness W043/W059 |
| 5 V rail has margin for the LED map | 66 LEDs at full white = 3.96 A vs 1.5 A: firmware cap 0.35 A required | system_budget.py |

| CB1D fits inside the cylinder with ribs at 28/48/112/130/235/255/305/355 | JPW (4-way terminal block) hit the 130 deg rib and a 0603 hit the 235 deg rib; ribs moved to 24/48/109/135/225/244/300/317 | head_crosscheck.py exact polygon test |
| Board notch 12 mm (half-width 6.0) clears the spine channel | The spine walls' outer faces reach 7.24 mm at r39: notch widened to half-width 7.6 on CB1D and LB1 | head_crosscheck.py |
| The *_board_with_components.stl files are valid envelopes | They draw every body as an unrotated, uncentred box: use pickplace + BOM + lib_bodies (head_crosscheck.py) | head_crosscheck.py |
| Hood v2 adds +6.7 / +5.3 / +4.3 % field at 100 / 200 / 300 mm | That came from the coupled-moment model at 8 mm cells, which does not converge for a 2.5 mm plate. The axisymmetric model gives v2 +12.7 / +9.8 / +7.8 %, and v3 (butted tiles) +17-18.5 / +13-14 / +10.3-11.2 % | hood_axi.py, hood_dipole convergence (8/6/4/3/2.5 mm cells) |
| The 2 mm gap between a spoke's inner and outer tile is harmless | It is a series air gap in the radial flux path: closing it is worth about +4 points at 200 mm, more than doubling the tile thickness | hood_axi.py |
