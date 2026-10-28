#!/usr/bin/env python3
"""Output modes, step 1 (docs/design/OUTPUT_MODES_PLAN.md, owner approval 2026-10-28): one target descriptor -> an audio voice and an LED frame, in three
user modes (AUDIO_ONLY, LED_ONLY, COMBINED). Python model of the firmware renderers; MODELED, nothing built or heard on hardware.

Descriptor (from the receive DSP, OPEN_ITEMS 5): metal class, tau (us), SNR above the ground-balanced noise, depth class 1..4, bearing (deg, head frame:
azimuth CCW from +x, heel 178 deg, so "forward" for the user is 358 deg).
Audio voice: silent below 4 sigma; pitch FALLS with tau (ENHANCEMENT_REVIEW 2026-10-23 s.7: low = long tau / large or ferrous, high = short tau / small gold;
the older src/archive/audio_dsp.py rose with tau and is not followed): f = 1200 * 2^(-0.8 log10(tau / 1 us)) Hz; iron = fixed 110 Hz voice;
timbre per class; loudness from log SNR; attack from depth; stereo pan from bearing (headphones; the speaker sums to mono).
LED voice (66 x SK9822-EC20 on 4 rings: 12 / 18 / 24 / 12 at r 12.5 / 20 / 26.5 / 34 mm): ring = depth class (outer = shallow, inner = deep), the lit pixels
are those nearest the bearing, colour = class with each channel fully on or off (grayscale 0 / 255, no 1.2 kHz PWM steps), brightness = the 5-bit
CURRENT field (datasheet Rev. A/0 current table: code 5 -> 2.905 mA, code 22 -> 12.782 mA, i.e. 18.0 mA x code / 31). Whether grayscale 255 is truly free of
PWM edges is NOT stated in the sheet: UNVERIFIED (scope on the first article).
Audio link (change against the plan text found here): the head does NOT send an audio waveform (a PWM carrier on CB1D would switch next to the coils during
the gates); it sends the descriptor as a short UART burst on the spare signal-cord core 5 in the idle slot after the LED frame, and the handle audio board
synthesises the sound. So in every mode no LED or audio edge leaves the head inside the receive window.
Checks: (1) every LED and UART burst lies inside the idle slot (after the last gate, before the next pulse's housekeeping, 10 % spare kept) in every PRF
mode; (2) end-to-end latency (averaging window + one period + synth buffer) <= 50 ms; (3) LED rail <= the 0.35 A firmware cap for the worst frame;
(4) silent search: no sound and no lit LED below threshold; (5) every class has a distinct LED colour and a distinct voice (timbre, or pitch >= 2 semitones);
(6) mode rules: AUDIO_ONLY sends no LED frame after the all-off frame, LED_ONLY uses only grayscale 0 / 255, COMBINED keeps LEDs dark in a sweep.
Writes kit_v23/output_modes.json, kit_v23/pf233_output.h (firmware constants), kit_v23/output_modes.png (LED frames of the example targets) and
kit_v23/OUT_AUDIO/*.wav (16-bit mono previews).
usage (in work/): python3 output_modes.py"""
import os, sys, csv, json, math, wave
import numpy as np
TL = json.load(open("kit_v23/fw_timeline.json"))
PIX = [dict(ring=int(r["ring"]), az=float(r["azimuth_deg"]), x=float(r["x_mm"]), y=float(r["y_mm"])) for r in csv.DictReader(open("kit_v18/SET/02_CORE_PCB_CYLINDER/PIXEL_MAP_66.csv"))]
N_LED = len(PIX); I_CODE31_MA = 18.0; I_STATIC_MA = 1.0; I_CAP_A = 0.35                  # SK9822-EC20 Rev. A/0; static IDD per LED as in the rail budget; firmware cap (OPEN_ITEMS 0)
LED_CLK_HZ = 8e6; LED_FRAME_US = (64 + 32 * N_LED) / LED_CLK_HZ * 1e6
UART_BAUD = 1_000_000; LINK_BYTES = 10; UART_US = LINK_BYTES * 10 / UART_BAUD * 1e6     # start + 8 data + stop; bytes: sync, seq, mode, class, tau, snr, depth, bearing(2), crc
HK_US, SPARE = 10.0, 0.10                                                                # as fw_timeline.py
REPLY_BYTES = 2; REPLY_US = REPLY_BYTES * 10 / 1e6 * 1e6 + 10.0                            # AU1 answers in the same slot: 2 bytes at 1 Mbaud + 10 us bus turnaround (ASSUMED)
I2C_HZ = 400e3; GYRO_BITS = 9 * 5 + 2; GYRO_US = GYRO_BITS / I2C_HZ * 1e6                    # CB1D-C2 BMI270 yaw read: addr+W, reg, restart addr+R, 2 data bytes (+ start / stop) at 400 kHz
WINDOW_MS = 30.0                                                                         # averaging window per mode (ASSUMPTIONS 39): trade against depth gain (ENHANCEMENT_REVIEW s.2)
SYNTH_MS = 2.0                                                                           # handle synth buffer (64 samples at 32 kHz), ASSUMED
THRESH = 4.0; SNR_FULL = 1000.0; FWD = 358.0; FS = 22050
CLASSES = {  # id (= the DSP class id of dsp_ref.CLASSES and the firmware), LED colour (R, G, B on/off), voice timbre, fixed pitch (None = from tau)
    "foil / tiny":                 (0, (1, 0, 1), "chirp", None),
    "small gold or pull-tab zone": (1, (1, 1, 0), "gold",  None),
    "medium gold":                 (2, (0, 1, 0), "gold",  None),
    "large gold / coin":           (3, (0, 1, 1), "bell",  None),
    "iron":                        (4, (1, 0, 0), "iron",  110.0)}
MODES = ("AUDIO_ONLY", "LED_ONLY", "COMBINED")
def pitch(tau_us): return 1200.0 * 2 ** (-0.8 * math.log10(max(tau_us, 1.0)))
def snr_code(snr): return 0 if snr < THRESH else max(1, min(31, round(1 + 30 * math.log10(snr / THRESH) / math.log10(SNR_FULL / THRESH))))
def voice(d):
    """audio parameters for one descriptor (None below threshold = silent search)"""
    if d["snr"] < THRESH: return None
    cid, rgb, kind, f0 = CLASSES[d["cls"]]
    return dict(kind=kind, f_hz=round(f0 or pitch(d["tau_us"]), 1), amp=round(min(1.0, 0.18 * math.log10(d["snr"]) + 0.1), 3),
                attack_ms=round(10 + 25 * (4 - d["depth"]), 1), length_ms=round(min(600.0, 120 + 30.0 * d["snr"] ** 0.5), 0),   # length: WAV preview only; live, the voice lasts while descriptors stay above threshold
                pan=round(-math.sin(math.radians(d["bearing"] - FWD)), 3))
def led_frame(d, lit=True):
    """per-LED (gray R, G, B, current code); ring = depth class (4 shallow outer .. 1 deep inner), the 3 pixels nearest the bearing on that ring"""
    fr = [(0, 0, 0, 0)] * N_LED
    if not lit or d is None or d["snr"] < THRESH: return fr
    ring = d["depth"]; cand = sorted((abs((p["az"] - d["bearing"] + 180) % 360 - 180), i) for i, p in enumerate(PIX) if p["ring"] == ring)
    code = snr_code(d["snr"]); rgb = CLASSES[d["cls"]][1]
    for k, (_, i) in enumerate(cand[:3]): fr[i] = (255 * rgb[0], 255 * rgb[1], 255 * rgb[2], code if k == 0 else max(1, code // 3))
    return fr
def cap_frame(fr):
    """firmware LED-current cap (OPEN_ITEMS 0): scale every current code down by one factor until the frame is <= I_CAP_A (codes stay >= 1 where lit)"""
    budget = I_CAP_A * 1e3 - I_STATIC_MA * len(fr); load = sum(I_CODE31_MA * c / 31 * ((r > 0) + (g > 0) + (b > 0)) for r, g, b, c in fr)
    if load <= budget: return fr
    k = budget / load
    return [(r, g, b, max(1, math.floor(c * k)) if c else 0) for r, g, b, c in fr]
def render_leds(descs, lit=True):
    """all descriptors of one period into one frame (later targets do not erase earlier pixels), then the current cap"""
    fr = [(0, 0, 0, 0)] * N_LED
    for d in descs:
        for i, f in enumerate(led_frame(d, lit)):
            if f[3] > fr[i][3]: fr[i] = f
    return cap_frame(fr)
def frame_current_A(fr): return sum(I_STATIC_MA for _ in fr) / 1e3 + sum(I_CODE31_MA * c / 31 * ((r > 0) + (g > 0) + (b > 0)) for r, g, b, c in fr) / 1e3
def tone(v, dur=1.6):
    t = np.arange(int(dur * FS)) / FS; f = v["f_hz"]; env = np.exp(-((t - dur / 2) / (v["length_ms"] / 1e3 / 2.2)) ** 2) * (1 - np.exp(-t / (v["attack_ms"] / 1e3)))
    k = v["kind"]
    y = (np.sin(2 * np.pi * f * t + 0.35 * np.sin(2 * np.pi * 5 * t)) if k == "gold" else 0.7 * np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.76 * f * t) if k == "bell"
         else np.sin(2 * np.pi * (f + 900 * t) * t) * (t % 0.3 < 0.12) if k == "chirp" else np.sign(np.sin(2 * np.pi * 110 * t)) * 0.6 + 0.4 * np.sin(2 * np.pi * 55 * t))
    return v["amp"] * env * y
TARGETS = [dict(name="gold_3g_deep", cls="small gold or pull-tab zone", tau_us=18, snr=9, depth=1, bearing=20),
           dict(name="gold_30g_mid", cls="medium gold", tau_us=95, snr=60, depth=2, bearing=300),
           dict(name="nugget_1kg_deep", cls="large gold / coin", tau_us=900, snr=40, depth=1, bearing=90),
           dict(name="coin_shallow", cls="large gold / coin", tau_us=260, snr=800, depth=4, bearing=200),
           dict(name="foil_shallow", cls="foil / tiny", tau_us=6, snr=150, depth=4, bearing=10),
           dict(name="iron_nail", cls="iron", tau_us=400, snr=300, depth=3, bearing=140),
           dict(name="below_threshold", cls="medium gold", tau_us=95, snr=3.2, depth=2, bearing=45)]
if __name__ == "__main__":
    out = dict(status="MODELED: firmware renderers in Python; grayscale-255 edge-free drive UNVERIFIED; latency excludes Bluetooth (UNVERIFIED)", constants=dict(
        led_frame_us=round(LED_FRAME_US, 1), gyro_i2c_us=round(GYRO_US, 1), uart_baud=UART_BAUD, link_bytes=LINK_BYTES, uart_us=UART_US, window_ms=WINDOW_MS, synth_ms=SYNTH_MS, i_code31_mA=I_CODE31_MA, i_cap_A=I_CAP_A,
        threshold_sigma=THRESH), modes={}, prf={}, targets=[], checks={})
    rx_end = TL["inputs"]["rx_end_us"]; slots_ok = True
    for pm, m in TL["modes"].items():
        T = m["period_us"]; ton = m["ton_max_us"]; slot_end = T - ton - HK_US - T * SPARE
        led0, led1 = rx_end, rx_end + LED_FRAME_US
        sched = {mode: [] for mode in MODES}
        for mode in MODES:
            t = rx_end
            if mode == "LED_ONLY": sched[mode].append(("led frame", t, t + LED_FRAME_US)); t += LED_FRAME_US
            sched[mode].append(("descriptor UART", t, t + UART_US)); t += UART_US
            sched[mode].append(("AU1 reply: selector state + status (half duplex)", t, t + REPLY_US)); t += REPLY_US
            if mode == "COMBINED": sched[mode].append(("led frame (between sweeps only)", t, t + LED_FRAME_US)); t += LED_FRAME_US
            sched[mode].append(("gyro I2C read (yaw rate)", t, t + GYRO_US)); t += GYRO_US
        ends = {mode: max(b for _, a, b in s) for mode, s in sched.items()}
        ok = all(e <= slot_end and min(a for _, a, _ in s) >= rx_end for (mode, s), e in zip(sched.items(), ends.values()))
        slots_ok &= ok
        n_avg = max(1, round(WINDOW_MS * 1e-3 * m["f_Hz"]))
        out["prf"][pm] = dict(period_us=T, rx_end_us=rx_end, idle_slot_end_us=round(slot_end, 1), n_avg=n_avg, latency_ms=round(n_avg * T / 1e3 + T / 1e3 + SYNTH_MS, 2),
                              schedule={mode: [dict(what=w, t0_us=round(a, 1), t1_us=round(b, 1)) for w, a, b in s] for mode, s in sched.items()}, slot_margin_us={k: round(slot_end - e, 1) for k, e in ends.items()}, ok=ok)
    out["modes"] = {"AUDIO_ONLY": dict(led="one all-off frame on entry, then no LED clock, data or current", audio="live voice from every descriptor", receive_noise="lowest: no LED current"),
                    "LED_ONLY": dict(led="lit during sweeps, refreshed every period in the idle slot; channels 0 / 255, brightness by the 5-bit current field", audio="muted (descriptor still sent, voice off)"),
                    "COMBINED": dict(led="dark during sweeps (one all-off frame), lit and refreshed between sweeps", audio="live voice from every descriptor")}
    worst = 0.0; frames = {}
    for d in TARGETS:
        v = voice(d); fr = render_leds([d]); I = frame_current_A(fr); worst = max(worst, I); frames[d["name"]] = fr
        out["targets"].append(dict(d, voice=v, led_lit=[i for i, f in enumerate(fr) if f[3]], led_codes=[f[3] for f in fr if f[3]], led_current_A=round(I, 4)))
    # worst frame the renderer can produce: three targets at full SNR, white-equivalent (two channels on), on the same ring
    multi = [dict(cls="large gold / coin", tau_us=300, snr=SNR_FULL, depth=r, bearing=b) for r in (1, 2, 3, 4) for b in (0, 120, 240)]   # 12 full-SNR targets
    _u = [(0, 0, 0, 0)] * N_LED
    for d in multi:
        for i, f in enumerate(led_frame(d)):
            if f[3] > _u[i][3]: _u[i] = f
    out["constants"]["worst_uncapped_A"] = round(frame_current_A(_u), 3); worst = max(worst, frame_current_A(render_leds(multi)))
    f_by_cls = {c: (CLASSES[c][2], CLASSES[c][3] or pitch(t)) for c, t in (("iron", 400), ("foil / tiny", 6), ("small gold or pull-tab zone", 18), ("medium gold", 95), ("large gold / coin", 260))}   # typical tau per class
    pairs = [(a, b) for i, a in enumerate(f_by_cls) for b in list(f_by_cls)[i + 1:]]
    distinct_voice = all(f_by_cls[a][0] != f_by_cls[b][0] or abs(12 * math.log2(f_by_cls[a][1] / f_by_cls[b][1])) >= 2 for a, b in pairs)
    distinct_led = len({CLASSES[c][1] for c in CLASSES}) == len(CLASSES)
    silent = [t for t in out["targets"] if t["snr"] < THRESH]; silent_ok = all(t["voice"] is None and not t["led_lit"] for t in silent) and bool(silent)
    gray_ok = all(all(x in (0, 255) for x in f[:3]) for fr in frames.values() for f in fr)
    out["checks"] = dict(idle_slot_all_modes=slots_ok, latency_le_50ms=all(p["latency_ms"] <= 50 for p in out["prf"].values()), led_rail_le_cap=worst <= I_CAP_A, worst_led_A=round(worst, 3),
                         silent_search=silent_ok, distinct_led_colours=distinct_led, distinct_voices=distinct_voice, gray_only_0_255=gray_ok)
    out["ok"] = all(v for k, v in out["checks"].items() if isinstance(v, bool))
    json.dump(out, open("kit_v23/output_modes.json", "w"), indent=1)
    # firmware constants
    H = ["/* GENERATED by src/sim/output_modes.py (MODELED). Do not edit: change the model and regenerate. */", "#pragma once", "#include <stdint.h>",
         "typedef enum { PF_OUT_AUDIO_ONLY = 0, PF_OUT_LED_ONLY = 1, PF_OUT_COMBINED = 2 } pf_out_mode_t;",
         f"#define PF_OUT_THRESH_SIGMA_X10 {int(THRESH * 10)}u", f"#define PF_OUT_SNR_FULL {int(SNR_FULL)}u", f"#define PF_OUT_I_CODE31_UA {int(I_CODE31_MA * 1000)}u",
         f"#define PF_OUT_LINK_BAUD {UART_BAUD}u", f"#define PF_OUT_LINK_BYTES {LINK_BYTES}u", f"#define PF_OUT_LINK_SLOT_AFTER_RX_NS {round(UART_US * 1000)}u  /* UART burst length; starts after the LED frame in LED_ONLY */",
         f"#define PF_OUT_WINDOW_MS {int(WINDOW_MS)}u", f"#define PF_OUT_FWD_DEG {int(FWD)}u",
         "typedef struct { uint8_t r, g, b; uint8_t voice; uint16_t fixed_hz; } pf_class_out_t;  /* voice: 0 iron, 1 chirp, 2 gold, 3 bell; fixed_hz 0 = pitch from tau */",
         "static const pf_class_out_t PF_CLASS_OUT[] = {" + ", ".join(f"{{ {r}u, {g}u, {b}u, {['iron', 'chirp', 'gold', 'bell'].index(k)}u, {int(f or 0)}u }}" for (cid, (r, g, b), k, f) in sorted(CLASSES.values())) + " };",
         "static const uint8_t PF_OUT_N_AVG[] = {" + ", ".join(f"{p['n_avg']}u" for p in out["prf"].values()) + " };  /* scan, mid, boost */"]
    open("kit_v23/pf233_output.h", "w").write("\n".join(H) + "\n")
    os.makedirs("kit_v23/OUT_AUDIO", exist_ok=True)
    for d in TARGETS:
        v = voice(d); y = tone(v) if v else np.zeros(int(1.6 * FS)); s = (np.clip(y, -1, 1) * 32000).astype("<i2")
        with wave.open(f"kit_v23/OUT_AUDIO/{d['name']}.wav", "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS); w.writeframes(s.tobytes())
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, len(TARGETS), figsize=(2.2 * len(TARGETS), 2.6))
    for a, d in zip(ax, TARGETS):
        fr = frames[d["name"]]
        for p, f in zip(PIX, fr):
            c = (f[0] / 255, f[1] / 255, f[2] / 255) if f[3] else (0.85, 0.85, 0.85); a.add_patch(plt.Circle((p["x"], p["y"]), 1.6, color=c, alpha=0.25 + 0.75 * f[3] / 31 if f[3] else 1.0))
        a.set_xlim(-38, 38); a.set_ylim(-38, 38); a.set_aspect("equal"); a.axis("off"); a.set_title(d["name"].replace("_", " "), fontsize=7)
    fig.suptitle("LB1-v6 LED voice per example target (MODELED); ring = depth class, position = bearing, colour = class, brightness = current code", fontsize=8)
    fig.savefig("kit_v23/output_modes.png", dpi=110, bbox_inches="tight")
    for k, v in out["checks"].items(): print(f"{k:24s} {v}")
    for pm, p in out["prf"].items(): print(pm, "n_avg", p["n_avg"], "latency", p["latency_ms"], "ms, slot margin", p["slot_margin_us"])
    print("OK" if out["ok"] else "FAIL")
    sys.exit(0 if out["ok"] else 1)
