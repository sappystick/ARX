# Unverified assumptions (each one needs a datasheet check, a measurement, or a better model)
| # | Assumption | Used in | How to verify |
|---|---|---|---|
| 1 | Coil self-capacitance 250 pF, FET Coss node 500 pF total | sim_head1 (turn-off, first gate) | impedance analyzer on the wound coil; FET datasheet |
| 2 | X7R 100 nF/630 V loses about 65 % at 630 V (model C0/(1+(V/462)^2)) | sim_head1 | manufacturer DC-bias curve |
| 3 | RS3 is the X8 input series resistor; noise densities 4.2 / 1.7 nV/rtHz | depth tables | netlist (confirmed), noise measurement on AB1A |
| 4 | Gold sphere target, sigma 4.1e7 S/m, decay tau = mu0 sigma a^2/pi^2; step-off approximation | detection depth | add ground (mineralised soil + viscosity), finite turn-off, non-spherical targets |
| 5 | Null residuals come from idealised circular-loop receive models, not the real SB1R-Q pattern | leak numbers | model the real pattern from the Gerber geometry; measure |
| 6 | Thermal: PETG 0.2, potting 0.25-1.8, FR4 0.5, h 6-10 W/m2K | sim_head2 | thermocouples on a heated mock-up |
| 7 | 24-turn quadrupole depth scaled by the model slope 0.22 | RX_PLATFORM_QUAD | run the target model with the 24-turn geometry |
| 8 | Hood gain from the axisymmetric model (hood_axi.py, MnZn mu 2000, DC, no losses); the coupled-moment model of hood_study2.py does not converge (8 -> 3 mm cells: +5.3 -> +7.3 % at 200 mm, 2.5 mm cells +17 %) and the earlier boundary-element note (+7.5 %, full plate) has no geometry on record | hood tables | measure the axis field of the built head with and without the tiles (search coil or gaussmeter, DC or a slow ramp) |
| 9 | LED pinout (SK6812-mini class), 74AHCT1G125 pinout, part heights, OKI module height 10.2 mm | LB1, CB1D | datasheets |
| 10 | Head mass 2.22 kg uses estimates for SB1R, potting, litz insulation | balance | weigh parts |
| 11 | Saddle/hinge loads (30 N m) and epoxy strength | yoke | FEA + pull test |
| 12 | Router results are grid-quantised (0.15 mm) with no independent DRC | CB1D/LB1 | import into KiCad or another CAM tool and run DRC |
| 13 | Receive-board copper modeled as thin-wire polylines (Biot-Savart / Neumann), no skin or proximity, traces at z of the layers | SBQ results | impedance and TX-leak measurement on the first boards |
| 14 | Coil self-capacitance 50-200 pF; damping resistor 680 ohm across the coil on the QA top | sbq_damp2 | measure the self-resonance and ring-down of a built board with and without RD |
| 15 | Tuned link radii cancel the lobe residual at the modeled z positions and 0.0 mm offset | sbq_tune | etch tolerance +-0.05 mm and layer spacing change the real leak; measure and re-tune |
| 16 | The independent DRC samples copper at 0.1 mm and uses the pad rectangles from pads.json; it does not check mask, silk, drill-to-copper, annular ring | drc.py | open the Gerbers in KiCad/Gerbv and run KiCad DRC |
| 17 | Litz resistance 30 mohm/m (from R_coil 45 mohm = 6 x 8.97 m in parallel); minimum bend radius 3 x OD = 3.6 mm; two leads 4 mm apart for the loop inductance | tx_system | measure a wound layer and a lead pair |
| 18 | Creepage: 3.0 mm edge gap plus 1.6 mm FR4 is enough for 460 V peak (about 2.5 mm needed, pollution 2) | TXJ1 | check against the applicable standard and hipot test at 1 kV |
| 19 | Part ratings in system_budget.py (FET 24 A, ES3J IFSM, R2512 200 V, BAV199 surge, TVS, TC4420 6 A, FET Qg 45 nC) are from memory | stress table | read the datasheets (prompt C05) |
| 20 | Junction hand-soldering and wire dressing fit in the 14 x 6.4 mm bridge channel together with the ribbons | bridge | build a dummy bridge with real cable |
| 21 | AB1T input parts: 74LVC1G66 on-resistance 8 ohm (sensitivity 4-20 ohm), input-node capacitance 15 pF (5-30 pF: BAV199 + switch off-capacitance + OPA2211 input), BAV199 off for small signals, OPA2211 1.1 nV/rtHz; RD resistor with non-magnetic terminations is available in 0805 (unverified) | sbq_damp2 | datasheets (C05); ring-down measurement on AB1T with a built coil |
| 22 | RP2350 GPIO thresholds VIL 0.8 V / VIH 2.0 V at 3.3 V; Hall switch Vsat <= 0.4 V, open-drain, pin order VCC/GND/OUT on the TO-92 footprint; 1 uA input + clamp leakage; Pico 2 board pins 31/32/34 = ADC0/1/2 and pin 7 = GP5 (digital) | trigger_check, HB1 | RP2350 and Pico 2 datasheets, the chosen Hall switch datasheet (C05) |
| 23 | Hood homogenisation: straight tiles smeared over the azimuth with fill N w / 2 pi r, Wiener bounds; the 0.2 mm butt joint as a series gap (lower bound) or no gap (upper); MnZn initial permeability holds at 50-60 mT and the tiles add no eddy/relaxation signal of their own at the receive gates; 27-28 x 26-40 x 2.5 mm tiles can be cut from stock plates with flat butt faces | hood_axi, hood_v20 | build one spoke and measure; ferrite datasheet (mu vs B, loss vs f); ring-down of the receive channel with and without the hood |
