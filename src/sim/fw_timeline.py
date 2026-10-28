#!/usr/bin/env python3
"""Firmware timing model for the CB1D controller (FINAL_INTEGRATION_PLAN P5). Builds the per-pulse schedule of every operating mode from the repo's own results
and proves that nothing collides; writes the table the firmware compiles from (a generated C header), so firmware and model cannot drift. MODELED.
Inputs (no new numbers where the repo has one):
  modes and on-time: system_live.json modes (8 A / 800 Hz, 14 A / 600 Hz, 20 A / 400 Hz); on-time from TX_ONTIME_LUT.csv at the worst (lowest) pack voltage
  turn-off: current zero and quiet time from tx_vbus.json (film clamp, the design case); blank release and first clean gate from sbq_damping2.json (RD 680, Cself 100 pF)
  receive gates: sim_head1.py scheme, t_first x 1.618^k, k = 0..8 (last gate ends at t_first x 1.618^9)
  ADC: AD7389-4 Rev. 0 (datasheet on disk): 2 MSPS (tCONVERT 190 + tACQUIRE 310 ns), 32 SCLK per 2-wire frame, tSCLK >= 12.5 ns, tCSH 20 ns, tQUIET 20 ns
  SCLK 40 MHz: firmware requirement from rule (3) (the model reports the minimum); RP2350 PIO / SPI capability at that clock not read from a datasheet (UNVERIFIED)
  LEDs: 66 x SK6812-mini class on LB1 (ASSUMPTIONS 9, UNVERIFIED): one-wire 800 kbit/s, 24 bit per LED, latch after >= 80 us low: ASSUMED class timing
  housekeeping per pulse: VBUS / ISENSE / NTC read on the RP2350 ADC before the pulse: 10 us budget (ASSUMED)
Rules checked per mode: (1) ramp + turn-off + receive window + housekeeping fit the period with >= 10 % spare; (2) no LED data edge inside a receive window:
the LED stream needs one contiguous quiet slot, so it is either placed after the receive window if it fits, or the firmware drops ONE pulse every N periods
to make room (the PRF cost is reported); (3) the ADC frame rate stays under 2 MSPS and gives at least 3 frames inside the shortest gate.
usage (in work/): python3 fw_timeline.py [OUT.json] [HEADER.h]"""
import json, csv, math, sys, os
def rd(p, alt):
    return json.load(open(p)) if os.path.exists(p) else json.load(open(alt))
SL = rd("kit_v23/system_live.json", "../data/results/system_live.json"); TV = rd("kit_v23/tx_vbus.json", "../data/results/tx_vbus.json")
SD = rd("kit_v22/sbq_damping2.json", "../data/results/sbq_damping2.json")
LUT = list(csv.DictReader(open("kit_v23/TX_ONTIME_LUT.csv" if os.path.exists("kit_v23/TX_ONTIME_LUT.csv") else "../data/results/TX_ONTIME_LUT.csv")))
film = [r for r in TV["tx_stage_vs_vbus"] if not r["derated"]]
T_ZERO, T_QUIET = max(r["t_zero_us"] for r in film), max(r["t_quiet_us"] for r in film)
fg = SD["first_clean_gate_us"]; key = next(k for k in fg if "release 5 us" in k and "100 pF" in k) if any("100 pF" in k for k in fg) else next(k for k in fg if "release 5 us" in k)
T_FIRST = fg[key]["Rd 680"]; T_BLANK = 5.0
GATES = [(T_FIRST * 1.618 ** k, T_FIRST * 1.618 ** (k + 1)) for k in range(9)]; RX_END = GATES[-1][1]
SCLK = 40e6; ADC_MIN_US = 0.5; FRAME_US = max((32 / SCLK + 20e-9 + 20e-9) * 1e6, ADC_MIN_US)
SHORTEST = min(b - a for a, b in [(T_FIRST * 1.618 ** k, T_FIRST * 1.618 ** (k + 1)) for k in range(9)])
SCLK_MIN = 32 / ((SHORTEST / 3 - 0.04) * 1e-6)                                            # 3 frames inside the shortest (first) gate
LED_BITS, LED_BIT_US, LED_LATCH_US, N_LED = 24, 1.25, 80.0, 66; LED_US = N_LED * LED_BITS * LED_BIT_US + LED_LATCH_US     # one-wire SK6812 class (MINI-E Rev.02: 800 kbit/s, 24 bit, reset 80 us)
# clocked SK9822 (OPSCO SK9822 Rev.01, data/seed/datasheets): frame = 64 + 32 x N bits (start + LED frames + end), TCLKH / TCLKL > 30 ns, data set-up > 10 ns, 30 MHz max;
# firmware clock 8 MHz (125 ns period, 4x the minimum widths). The stream can pause at any bit (clocked), but at 8 MHz one refresh is short enough to fit whole.
LED_CLK_HZ = 8e6; LED_CLOCKED_US = (64 + 32 * N_LED) / LED_CLK_HZ * 1e6
HK_US, SPARE = 10.0, 0.10
def ton_us(I):
    col = {8: "ton_8A_us", 14: "ton_14A_us", 20: "ton_20A_us"}[int(I)]; return max(float(r[col]) for r in LUT)
out = dict(status="MODELED; SCLK, LED class timing and housekeeping ASSUMED", inputs=dict(t_zero_us=T_ZERO, t_quiet_us=T_QUIET, blank_release_us=T_BLANK, first_gate_us=T_FIRST, first_gate_case=key,
           gates_us=[[round(a, 2), round(b, 2)] for a, b in GATES], rx_end_us=round(RX_END, 1), adc_frame_us=round(FRAME_US, 3), led_stream_us=LED_US, sclk_hz=SCLK, sclk_min_hz_for_3_frames=round(SCLK_MIN), adc_sclk_max_hz=80e6), modes={})
for nm, m in SL["modes"].items():
    T = 1e6 / m["f"]; ton = ton_us(m["I"]); busy = HK_US + ton + RX_END                         # housekeeping, ramp (from -ton to 0), turn-off and receive (0 .. RX_END)
    free = T - busy; fits = busy <= T * (1 - SPARE)
    led_clk = dict(strategy="SK9822 clocked: whole refresh in the free time after the receive window, every period" if free - T * SPARE >= LED_CLOCKED_US else "SK9822 clocked: refresh split over the free time of several periods",
                   stream_us=round(LED_CLOCKED_US, 1), prf_cost_pct=0.0, refresh_hz=m["f"] if free - T * SPARE >= LED_CLOCKED_US else round(m["f"] / math.ceil(LED_CLOCKED_US / (free - T * SPARE)), 1))
    led_after_rx = free - T * SPARE >= LED_US
    if led_after_rx: led = dict(strategy="after the receive window, every period", prf_cost_pct=0.0, refresh_hz=m["f"])
    else:                                                                                     # drop k consecutive pulses every N periods: slot = k*T + free >= LED_US
        k = math.ceil(max(0.0, LED_US - (free - T * SPARE)) / T); N = max(k + 1, round(m["f"] / 30.0))   # 30 Hz display refresh
        led = dict(strategy=f"drop {k} pulse(s) every {N} periods; the LED stream runs in the gap", prf_cost_pct=round(100 * k / N, 2), refresh_hz=round(m["f"] / N, 1), dropped=k, every=N)
    shortest_gate = GATES[0][1] - GATES[0][0]; frames = shortest_gate / max(FRAME_US, ADC_MIN_US)
    sched = [("housekeeping: VBUS / ISENSE / NTC, set ton from the LUT", -ton - HK_US, -ton), ("TX on (ramp)", -ton, 0.0), ("TX off: flyback to current zero", 0.0, T_ZERO),
             ("blank switch closed until release", 0.0, T_BLANK), ("ring-down to quiet", T_ZERO, T_QUIET)] + [(f"gate {i + 1}", a, b) for i, (a, b) in enumerate(GATES)] + [("free", RX_END, T - ton - HK_US)]
    out["modes"][nm] = dict(I_A=m["I"], f_Hz=m["f"], period_us=round(T, 1), ton_max_us=ton, busy_us=round(busy, 1), free_us=round(free, 1), spare_pct=round(100 * free / T, 1), fits=fits, led=led_clk, led_one_wire=led,
                            adc_frames_in_shortest_gate=round(frames, 1), adc_ok=frames >= 3 and SCLK <= 80e6,
                            schedule=[dict(what=w, t0_us=round(a, 2), t1_us=round(b, 2)) for w, a, b in sched])
    out["modes"][nm]["ok"] = fits and out["modes"][nm]["adc_ok"] and T_BLANK <= T_FIRST
out["ok"] = all(v["ok"] for v in out["modes"].values())
op = sys.argv[1] if len(sys.argv) > 1 else "kit_v23/fw_timeline.json"; hp = sys.argv[2] if len(sys.argv) > 2 else "kit_v23/pf233_timing.h"
json.dump(out, open(op, "w"), indent=1)
H = ["/* GENERATED by src/sim/fw_timeline.py from the PHI-FOLD 233 models (MODELED). Do not edit: change the model and regenerate. */", "#pragma once", "#include <stdint.h>",
     f"#define PF_BLANK_RELEASE_NS {round(T_BLANK * 1000)}u", f"#define PF_FIRST_GATE_NS {round(T_FIRST * 1000)}u", f"#define PF_N_GATES {len(GATES)}u",
     "static const uint32_t PF_GATE_START_NS[PF_N_GATES] = {" + ", ".join(str(round(a * 1000)) for a, _ in GATES) + "};",
     "static const uint32_t PF_GATE_END_NS[PF_N_GATES] = {" + ", ".join(str(round(b * 1000)) for _, b in GATES) + "};", f"#define PF_SPI_SCLK_HZ {int(SCLK)}u", f"#define PF_HOUSEKEEPING_NS {round(HK_US * 1000)}u",
     "typedef struct { uint16_t i_peak_a; uint16_t prf_hz; uint32_t period_ns; uint8_t led_drop_one_wire; uint16_t led_every_one_wire; } pf_mode_t;  /* drop fields: only for the legacy SK6812 one-wire chain */"]
H.append("static const pf_mode_t PF_MODES[] = {" + ", ".join(f"{{ {int(v['I_A'])}u, {int(v['f_Hz'])}u, {round(v['period_us'] * 1000)}u, {v['led_one_wire'].get('dropped', 0)}u, {v['led_one_wire'].get('every', 1)}u }}" for v in out["modes"].values()) + "};")
H.append("/* on-time per pack voltage: TX_ONTIME_LUT.csv (tx_vbus_sweep.py loop model with bulk droop), 0.5 V steps */")
H.append(f"#define PF_LUT_N {len(LUT)}u"); H.append("static const uint16_t PF_LUT_VBUS_MV[PF_LUT_N] = {" + ", ".join(str(round(float(r['V_bus']) * 1000)) for r in LUT) + "};")
for I in (8, 14, 20): H.append(f"static const uint32_t PF_LUT_TON_{I}A_NS[PF_LUT_N] = {{" + ", ".join(str(round(float(r[f'ton_{I}A_us']) * 1000)) for r in LUT) + "};")
open(hp, "w").write("\n".join(H) + "\n")
for nm, v in out["modes"].items(): print(f"{nm:6} period {v['period_us']:7.1f} us busy {v['busy_us']:6.1f} spare {v['spare_pct']:5.1f} %  LED: {v['led']['strategy']} ({v['led']['stream_us']} us, PRF cost {v['led']['prf_cost_pct']} %, {v['led']['refresh_hz']} Hz); one-wire would cost {v['led_one_wire']['prf_cost_pct']} %  ok {v['ok']}")
print("first gate", T_FIRST, "us, rx end", round(RX_END, 1), "us, LED stream", LED_US, "us, ADC frame", round(FRAME_US, 3), "us, SCLK min", round(SCLK_MIN / 1e6, 1), "MHz")
