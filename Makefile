# Arx / PHI-FOLD 233 : reproducible build and verification
# Run from the repo root. Scripts are flattened into ./work (they read each other and write to kit_vNN/ relative paths).
PY ?= python3
W  := work

.PHONY: head-audit tx audit-system baseplate sbq-geom sbq sbq-fast drc-lb1 drc-cb1d kicad-lb1 kicad-cb1d gerber-cb1d pcb-release help setup clean formers-low formers-print v5 check hood yoke sims pcb-lb1 pcb-cb1d route-lb1 route-cb1d gerber-lb1 verify-quick verify-full

help:
	@echo "make setup           copy scripts, seed data and legacy board data into ./work"
	@echo "make verify-quick    v5 cylinder + parts + geometry checks + transmit-stage/field sim (about 3 min)"
	@echo "make verify-full     adds the quadrupole/receiver sims, thermal, hood, yoke, display-board PCB flow"
	@echo "make formers-low     low-resolution formers (needed by audits/renders)"
	@echo "make formers-print   full-resolution formers (about 70 MB each, slow)"
	@echo "see docs/PROCESS.md for the engineering loop"

setup:
	mkdir -p $(W)
	find src -name '*.py' -not -path 'src/archive/*' -exec cp {} $(W)/ \;
	cp -r data/seed/* $(W)/
	mkdir -p $(W)/legacy && cp -r data/legacy/* $(W)/legacy/
	cd $(W) && mkdir -p kit_v15/LOW kit_v15/PRINT kit_v15/SET kit_v16/PARTS kit_v17/PARTS kit_v18/SET/02_CORE_PCB_CYLINDER kit_v18/PARTS kit_v18/CB1D kit_v18/LB1 kit_v18/HTA kit_v18/MFG kit_v19/SET/02_CORE_PCB_CYLINDER kit_v19/PARTS kit_v19/YOKE kit_v19/SPINE kit_v19/MFG kit_v20 kit_v21 kit_v22/SET/02_CORE_PCB_CYLINDER kit_v22/DXF
	@echo "setup done: now make verify-quick"

clean:
	rm -rf $(W)

formers-low:
	cd $(W) && $(PY) phifold_v15.py low

formers-print:
	cd $(W) && $(PY) phifold_v15.py print

baseplate:
	cd $(W) && $(PY) cap_hood_v16.py

sbq-geom:
	cd $(W) && $(PY) sbq_gen2.py

v5: baseplate
	cd $(W) && $(PY) hub_v22.py && $(PY) parts_v22.py

check: v5 sbq-geom
	cd $(W) && $(PY) check_v22.py

hood:
	cd $(W) && $(PY) hood_v19.py

yoke:
	cd $(W) && $(PY) yoke_v20.py

sims:
	cd $(W) && $(PY) sim_head1.py && $(PY) sim_head2.py && $(PY) sim_cage_rx.py && $(PY) sim_tanr.py && $(PY) sim_quadbearing.py

pcb-lb1:
	cd $(W) && PW=L $(PY) pw_design.py && PW=L $(PY) lb1_export.py

pcb-cb1d:
	cd $(W) && PW=C DISC=1 $(PY) pw_design.py && PW=C DISC=1 $(PY) cb1d_export.py

route-lb1: pcb-lb1
	cd $(W) && $(PY) route_run.py LB1 && $(PY) route_fix.py LB1 kit_v20/route_LB1.json

route-cb1d: pcb-cb1d
	cd $(W) && $(PY) route_run.py CB1D && $(PY) route_fix.py CB1D kit_v20/route_CB1D.json

gerber-lb1: route-lb1
	cd $(W) && $(PY) gerber_out.py LB1 hatch notch-1

verify-quick: check
	cd $(W) && $(PY) sim_head1.py

verify-full: verify-quick hood yoke
	$(MAKE) audit-system
	cd $(W) && $(PY) sim_head2.py && $(PY) sim_cage_rx.py && $(PY) sim_tanr.py && $(PY) sim_quadbearing.py
	$(MAKE) gerber-lb1

gerber-cb1d: route-cb1d
	cd $(W) && $(PY) gerber_out.py CB1D hatch notch1

drc-lb1:
	cd $(W) && $(PY) drc.py LB1 kit_v20/route_LB1.json -1

drc-cb1d:
	cd $(W) && $(PY) drc.py CB1D kit_v20/route_CB1D.json 1 COIL_A,COIL_B,DM1,DM2

kicad-lb1:
	mkdir -p $(W)/kit_v22/KICAD && cd $(W) && $(PY) kicad_inject.py LB1 kit_v20/route_LB1.json kit_v22/KICAD/PF233-LB1_routed.kicad_pcb -1

kicad-cb1d:
	mkdir -p $(W)/kit_v22/KICAD && cd $(W) && $(PY) kicad_inject.py CB1D kit_v20/route_CB1D.json kit_v22/KICAD/PF233-CB1D_routed.kicad_pcb 1 six

# receive boards: sbq-fast uses the stored tuned radii (data/seed/kit_v22/sbq_radii.json); sbq re-tunes them (about 3 min)
sbq-fast:
	cd $(W) && $(PY) sbq_gen2.py && $(PY) sbq_export.py && $(PY) sbq_sim.py && $(PY) sbq_damp.py

sbq:
	cd $(W) && rm -f kit_v22/sbq_radii.json && $(PY) sbq_gen2.py && $(PY) sbq_tune.py A && $(PY) sbq_tune.py B && $(MAKE) -C .. sbq-fast

pcb-release: gerber-lb1 gerber-cb1d drc-lb1 drc-cb1d kicad-lb1 kicad-cb1d sbq-fast

# transmit lead system (channel, TXJ1 board, cradle, schematics) and the system audits
tx:
	cd $(W) && $(PY) tx_system.py

audit-system: tx pcb-lb1 pcb-cb1d
	cd $(W) && $(PY) wiring_audit.py && $(PY) system_budget.py && $(PY) stack_check.py && $(PY) interference_audit.py

# full cross-check of the assembled head (3D interference at 0.5 and 0.2 mm, layers, radial fits, LED/TX/RX/wiring) and the cut-away drawings
head-audit: audit-system
	cd $(W) && mkdir -p kit_v21 && $(PY) head_crosscheck.py && $(PY) fine_check.py && $(PY) head_drawings.py
