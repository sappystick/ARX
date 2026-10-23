---
name: phifold-design-rules
description: Design rules, conventions and claim wording for the PHI-FOLD 233 detector head. Use when changing geometry, boards, simulations or reports in this repo, or when asked what is allowed (eddy rule, high-voltage rule, frames, units, claim policy).
---
# PHI-FOLD 233 design rules
1. Frames and units: mm/deg; z up from the underside of the base plate; azimuth CCW from +x; heel 178 deg; spine 90 deg; board exporter y-down, pickplace y-up; CB1D rotated 180 deg.
2. Eddy rule: no solid planes, foil rings or closed metal loops around the axis in the head or vault. Solid 1 oz plane D78 has tau 17.8 us, which sits in the receive gates. Use hatched planes (1.6 mm pitch, 0.4 mm lines), copper-cloth septa, slit liners.
3. High voltage: coil flyback nets need 1.0 mm clearance and 630 V parts. The clamp is a capacitor snubber (Vds peaks 341-462 V, one 100 nF C0G/film is the design value).
4. Receiver: two rotated quadrupoles (RX-Q). Do not reintroduce the figure-8 net or the analog trim loop without new simulation.
5. Claims: modeled / built / measured; list assumptions; never "record"; update docs/CORRECTIONS.md when wrong.
6. Changes go through generators; checks go into tests/regress.py.
Reference: docs/DESIGN_STATE.md, docs/CONVENTIONS.md, docs/ASSUMPTIONS.md.
