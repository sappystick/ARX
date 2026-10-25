# Fabricator rules read from the vendors (Step 5a, read 2026-10-25)

Evidence file for U-FAB-RULES (closed by this file). Vendors: Advanced Circuits (now AdvancedPCB; 4pcb.com redirects there) and TTM. Owner decision: design to the stricter of the two. Each number below is quoted from the page or PDF named in its row; the extracted facility table and the SHA-256 of every page read are in `data/results/fab/vendor_capabilities.json`. These are published capability numbers, not a fabricator review of our files: that is U-FAB-DRC (still open), and nothing here makes a board ready for fabrication.

Sources:
- [A-TOL] AdvancedPCB "Tolerances", https://www.advancedpcb.com/en-us/resources/tolerances/ (from https://4pcb.com/pcb-design-specifications). No date on the page.
- [A-CAP] AdvancedPCB "PCB capabilities and expanded capabilities", https://www.advancedpcb.com/en-us/resources/pcb-capabilities-and-expanded-capabilities/ (from https://4pcb.com/pcb-capabilities.html). Six facility tables (Santa Clara CA, Orange County CA, Chandler AZ, Anaheim CA, Maple Grove MN, Aurora CO), columns Standard / Advanced / Development. No unit is printed: the values are inches (they match [A-TOL] where both give a number). We use the **worst Standard value over the six facilities**, because the facility is not chosen.
- [A-FIN] AdvancedPCB "PCB finishes", https://www.advancedpcb.com/en-us/resources/pcb-finishes/
- [T-HDI] TTM "High-Density Interconnect Technology, Advanced Solutions", https://www.ttm.com/sites/default/files/documents/AMII-Overview.pdf (document 0001-000004-2024, PDF created 2024-11-22), matrix columns Standard / Advanced / Development.
- [T-BP] TTM "5 Essential PCB Design Practices (General)", https://www.ttm.com/sites/default/files/documents/5_Essential_PCB_Design_Best_Practices_(General).pdf (PDF created 2017-07-21).
- [T-CONV] TTM "Conventional PCB", https://www.ttm.com/en/solutions/printed-circuit-boards/conventional-pcb
- Not found: no TTM page gives a numeric line/space, annular-ring or edge rule for conventional (non-HDI) boards; the [T-HDI] matrix is used for TTM's through-hole numbers. Neither vendor publishes a high-voltage spacing rule ([T-BP] only asks for the voltage in the fabrication notes).

## Rules versus the `src/pcb/dru_gen.py` floor

| Rule | Floor before | AdvancedPCB (worst Standard) | TTM | Floor now | Result on the six KiCad boards |
|---|---|---|---|---|---|
| Copper-to-copper clearance | 0.15 | 0.006" = 0.152 mm (Orange County, "Outer Layer Space - Trace to Trace - 1 oz. Cu. Base"; also 0.006" spacing on boards with filled, plated-over vias) [A-CAP]; ".004" for 1 oz finished outer" processable, "A premium is charged for trace width/spacing less than .007"" (0.178 mm) [A-TOL] | 3.5 mil = 0.089 mm (B, outer, Standard) [T-HDI] | **0.16** (tightened) | 0 errors; the router designs to 0.20 (above the 0.178 mm premium threshold) |
| Track width | 0.15 | 0.0055" = 0.140 mm (Santa Clara, Anaheim, Chandler; 1 oz outer) [A-CAP] | 3.5 mil = 0.089 mm [T-HDI] | 0.15 (kept) | 0 errors |
| Finished drill (vias) | 0.30 | smallest mechanical PTH via 0.006" = 0.152 mm (Aurora) [A-CAP]; "minimum finished hole size; 0.004"" [A-TOL] | 10 mil = 0.254 mm (H, through hole, Standard) [T-HDI] | 0.30 (kept) | 0 errors |
| Via annular ring | 0.15 | pad >= hole + 0.010", "annular ring ... at least .005" for vias" = 0.127 mm [A-TOL]; "Drill/Pad Size - No Break Out - Thru drill" Standard nominal + .010" (Aurora) to + .017" (Anaheim) = 0.127-0.216 mm ring [A-CAP] | pad = drill + 10 mil = 0.127 mm ring (I, Standard) [T-HDI] | 0.15 (kept) | 0 errors. WATCH: 0.15 is below the 0.216 mm no-breakout ring of the Anaheim / Santa Clara / Chandler Standard column; acceptable only where tangency is allowed: settle with the chosen facility (U-FAB-DRC) |
| Component PTH annular ring | 0.15 (one rule) | "a minimum of 0.007" for component holes" = 0.178 mm (pad >= hole + 0.014") [A-TOL] | as vias [T-HDI] | **0.18** (new rule) | CB1D JA/JB (1.27 mm headers, 1.00 pad / 0.65 drill = 0.175) failed 24 times: pad now 1.02 (0.185). HB2 Hall TO-92 pads 1.00 -> 1.02 (same drill). |
| Component PTH finished hole | none | smallest PTH component 0.015" (most) to 0.018" (Orange County) = 0.457 mm [A-CAP] | - | **0.46** (new) | 0 errors (smallest component drill 0.65) |
| Drill to copper (other nets) | none | "Minimum Drill to Copper for PTH" Standard 0.010" = 0.254 mm (four facilities) [A-CAP]; "We require a minimum of 0.010" inner layer clearance" [A-TOL] | - | **0.26** (new) | 0 errors |
| Drill to drill (edge to edge) | KiCad default | "Minimum hole to hole edge for PTH" Standard 0.012" (most) to 0.015" (Orange County) = 0.381 mm [A-CAP] | "Our normal minimum design guideline is 16 mil for same-net circuits and larger (depending on material) for uncommon nets" = 0.406 mm [T-BP] | **0.41** (new) | CB1D one GND via pair at 0.371 mm, LB1 one at 0.300 mm: `route_fix.py` now merges same-net router vias closer than 0.41 + 0.30 mm centre to centre (stub to the kept via). The via farm keeps 0.85 mm centres (0.55 mm gap). |
| Copper to board edge | 0.5 | routed: 0.010" outer, 0.015" inner = 0.381 mm, "0.020" preferred for inner layers" = 0.508 mm; scored 0.015" / 0.020" [A-TOL]; Standard 0.010" (all facilities) [A-CAP] | - | 0.5 (kept) | KiCad: 0 errors. Gerber read-back (`gerber_edge_check.py`): the `gerber_out.py` planes of CB1D_B2 / LB1_v4 had copper in the notch and 0.1 mm from the edge (fixed: 0.549 mm min in CB1D_B3 / LB1_v5; PB1R_v2 0.500, TXJ1_v2 0.500, SB1R v2 2.909). 0.5 is 0.008 mm under the preferred inner-layer value, 0.12 mm above the required one |
| High-voltage nets (COIL_A/B, DM1/2, DRAIN1, CLAMP1, TX_A/B) | 1.0 mm | not published | not published | 1.0 mm (CLAUDE.md rule 6, kept) | negative control `rules_loaded` true on CB1D, PB1R, TXJ1 |
| Solder-mask web between pads | - | Standard 0.004" = 0.102 mm (0.0035" Orange County) [A-CAP] | - | not in the KiCad rules | for the CAM review (U-CAM-VIEW) |
| Silkscreen line | - | "minimum line width 0.005"" = 0.127 mm [A-TOL] | - | not in the KiCad rules | TXJ1 carries 2 silk-over-copper and 1 back-text warnings (known, cosmetic) |

Every rule written by `dru_gen.py` now carries `(severity error)`: KiCad 9 reports `hole_to_hole` as a warning by default, and the sign-off counts errors only, so the drill-spacing floor would otherwise have been invisible (shown on LB1: the same violation moved from `warnings` to `errors`).

## Via-in-pad (PB1R via farm, OPEN_ITEMS 28a)

| Vendor | What the page says | Our vias |
|---|---|---|
| AdvancedPCB [A-CAP] | "Minimum PTH Size That Can Be Filled With Non Conductive Material and Plated Over", Standard 0.0059"-0.0098" by facility; "Maximum ...", Standard 0.018"-0.040" by facility | 0.30 mm = 0.0118": inside the Standard range at all six facilities |
| TTM [T-CONV] | "Via-in-pad, Plated Over Filled Vias (POFV)/non-conductive fill" | offered (no size given on the page) |

Both vendors offer filled and plated-over vias, so the via farm stays inside the pads (the "move it beside the pads" default does not apply). The fabrication notes must call for non-conductive fill and plating over on the PB1R pad vias; whether a given panel got it is a first-article inspection item (OPEN_ITEMS 28a stays open for that).

## Finishes

| Finish | AdvancedPCB [A-FIN] | TTM [T-CONV] | Our use |
|---|---|---|---|
| Immersion silver | offered ("Immersion Silver - IAg"; shelf life "9-12 Months*") | offered ("Immersion silver") | CB1D, LB1, AB1A/B, SB1R-QA/QB, HTA, TXJ1 (no nickel near the coil) |
| OSP | offered (shelf life "9-12 Months") | offered | alternative to silver |
| HASL lead-free | offered ("HASL Lead-Free") | "Lead-Free Hot Air Solder Leveling ("LF-HASL") - limited sites" | PB1R, PM2, HB2. WATCH: if TTM is chosen, a site with LF-HASL must be chosen too, or these boards move to OSP |
| ENIG / ENEPIG | offered | offered | not used (nickel is magnetic) |

## Still open after this file

- U-FAB-DRC: the chosen fabricator's own DRC/CAM report on our files.
- The facility (and so the no-breakout via ring, 0.127 to 0.216 mm) is not chosen.
- TTM's conventional-board numbers were not published; the HDI matrix is a proxy for its through-hole rules.
- AB1A/AB1B (`afe_design.py`, not in the KiCad flow) still use 1.00 mm pads on 0.65 mm drills (0.175 mm ring) for their 1.27 mm headers: fix when they enter the KiCad flow (OPEN_ITEMS 33).
