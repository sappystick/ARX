# P07 Transmit stage and clamp
Goal: faster, safer turn-off. Evaluate: one 100 nF C0G/film (design value), TVS/avalanche-clamp alternatives, active clamp, damping chain value (330 ohm now), FET Coss, loop inductance of the snubber path, avalanche energy and Vds margin (650 V FET), RCL1 dissipation and rating, EMI. Use src/sim/sim_head1.py (real netlist-based circuit).
Deliver: a trade table (first clean gate, Vds peak, loss, parts), the recommended change, a modified PB1R/CB1D netlist or BOM edit, and re-run of the regression. Mark every parasitic assumption.
