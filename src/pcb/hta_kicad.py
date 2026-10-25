#!/usr/bin/env python3
"""HTA (D90, 4-layer timing coil) as a KiCad 9 board, so it enters the same KiCad DRC as the other boards (Step 4, closes U-KICAD-HTA).
The geometry is NOT redrawn here: it is imported from hta_gerber.py (coil polylines L1 on F.Cu and L2 on In1, lead A on In2, lead B on B.Cu, the three vias, pads A/B,
the 66 light-pipe holes, the D90 outline and the 8 mm centre cut-out). The whole coil from pad A to pad B is one conductor, so it is ONE net (HTA_COIL): KiCad checks
clearances to holes and edge, track width, rings and drills; it cannot check the coil's own continuity as two nets would short. Gerber coordinates are y-up, KiCad y-down.
usage (in work/): python3 hta_kicad.py      -> kit_v22/KICAD/PF233-HTA.kicad_pcb"""
import os, math, io, contextlib
with contextlib.redirect_stdout(io.StringIO()): import hta_gerber as H      # rewrites the same Gerbers (deterministic) and gives the geometry
CX, CY = 100.0, 100.0
X = lambda p: CX + float(p[0]); Y = lambda p: CY - float(p[1])
NET = 1
L = ['(kicad_pcb (version 20221018) (generator "pf233_hta_kicad")', '  (general (thickness 1.6))', '  (paper "A4")', '  (layers',
     '    (0 "F.Cu" signal) (1 "In1.Cu" signal) (2 "In2.Cu" signal) (31 "B.Cu" signal) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (49 "F.Fab" user))',
     '  (setup (pad_to_mask_clearance 0.05) (stackup (layer "F.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 1" (type "prepreg") (thickness 0.2)) (layer "In1.Cu" (type "copper") (thickness 0.035)) '
     '(layer "dielectric 2" (type "core") (thickness 1.0)) (layer "In2.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 3" (type "prepreg") (thickness 0.2)) (layer "B.Cu" (type "copper") (thickness 0.035)) (copper_finish "Immersion silver")))',
     '  (net 0 "")', f'  (net {NET} "HTA_COIL")']
def seg(pts, layer):
    for a, b in zip(pts[:-1], pts[1:]):
        if math.dist(a, b) > 1e-6: L.append(f'  (segment (start {X(a):.4f} {Y(a):.4f}) (end {X(b):.4f} {Y(b):.4f}) (width {H.TW}) (layer "{layer}") (net {NET}))')
seg(H.L1, "F.Cu"); seg(H.L2, "In1.Cu"); seg(H.A_line, "In2.Cu"); seg(H.radial, "B.Cu")
for v in (H.viaA, H.viaM, H.viaB): L.append(f'  (via (at {X(v):.4f} {Y(v):.4f}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {NET}))')
for ref, p in (("PA", H.padA), ("PB", H.padB)):      # lead pads (the two leads to CB1D JHTA)
    L.append(f'  (footprint "PF233:HTA_lead_pad" (layer "F.Cu") (at {X(p):.4f} {Y(p):.4f})\n    (property "Reference" "{ref}" (at 0 -1.5 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))\n'
             f'    (attr through_hole)\n    (pad "1" thru_hole circle (at 0 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask") (net {NET} "HTA_COIL")))')
for i, (hx, hy) in enumerate(H.holes, 1):           # light-pipe holes: NPTH (the Gerber writer also draws their outlines on Edge_Cuts)
    L.append(f'  (footprint "PF233:NPTH_1.7" (layer "F.Cu") (at {X((hx, hy)):.4f} {Y((hx, hy)):.4f})\n    (property "Reference" "H{i}" (at 0 -1.5 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))\n'
             f'    (attr exclude_from_pos_files exclude_from_bom)\n    (pad "" np_thru_hole circle (at 0 0) (size 1.7 1.7) (drill 1.7) (layers "*.Cu" "*.Mask")))')
for r in (45.0, 4.0):                                # D90 outline and the 8 mm centre cut-out
    L.append(f'  (gr_circle (center {CX:.3f} {CY:.3f}) (end {CX + r:.3f} {CY:.3f}) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts"))')
L.append(")")
os.makedirs("kit_v22/KICAD", exist_ok=True); open("kit_v22/KICAD/PF233-HTA.kicad_pcb", "w").write("\n".join(L) + "\n")
print("HTA KiCad board:", len(H.L1) + len(H.L2) - 2, "coil segments,", len(H.holes), "NPTH, 2 lead pads, 3 vias -> kit_v22/KICAD/PF233-HTA.kicad_pcb")
