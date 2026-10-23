---
description: Route a board and export Gerbers with hatched planes
argument-hint: <LB1|CB1D>
allowed-tools: Bash(make:*), Bash(python3:*), Read
---
Run the placement, routing and Gerber flow for $ARGUMENTS with the Makefile targets (pcb-*, route-*, gerber-*). Report nets routed, tracks, vias, any failures, minimum clearances and whether HV nets keep 1.0 mm. If nets fail, read src/pcb/router.py, change the strategy (layer assignment, order, via cost) and retry; do not loosen clearances silently. State that no independent DRC has been run.
