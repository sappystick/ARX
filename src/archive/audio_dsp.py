#!/usr/bin/env python3
"""
PHI-FOLD 233 — reference signal chain and audio signature library
==================================================================
Runs the same per-pulse pipeline as the firmware should:
  6 time gates -> dual-pair ground balance -> tau fit (+ground term)
  -> ferrous flag (rotating-field lock-in in-phase sign) -> class
  -> two-sensor depth (gradiometer/mono ratio) -> audio voice.
and renders each class as a WAV so the sound design can be judged by ear.

Audio rules
  * SILENT SEARCH: no threshold hum. Output is exactly zero until the
    ground-balanced signal exceeds 4 sigma for >= 3 consecutive frames.
  * Pitch  = class / decay time:  f = 220 * 2**(0.8*log10(tau/1us))  (Hz)
             -> ~260 Hz foil, ~380 Hz 1 g gold, ~560 Hz 10 g, ~830 Hz coin
  * Timbre = class: gold = pure sine + 5 Hz vibrato; large non-ferrous = bell
    (sine + 2.76x partial); foil = short upward chirp; iron = 110 Hz low grunt.
  * Loudness = log(SNR); depth cue = attack time (shallow crisp, deep soft).
  * TRIGGER held: TX boost (8 -> 20 A), rotating field on, audio +9 dB,
    threshold halved.  Dial ALL-METAL -> every class enhanced.
    Dial GOLD -> only gold-window classes sound (iron/foil muted); gold
    voice gets a two-note chime.  Pull-tabs inside the gold window still
    sound (physics cannot separate them by decay alone).
"""
import math, json, os, wave, numpy as np
OUT = "out_audio"; os.makedirs(OUT, exist_ok=True)
FS = 22050
def tone(f, dur, kind, amp, attack):
    t = np.arange(int(dur * FS)) / FS
    env = np.exp(-((t - dur / 2) / (dur / 4.5)) ** 2)                     # sweep over target
    env *= 1 - np.exp(-t / attack)
    if kind == "gold":   y = np.sin(2 * np.pi * f * t + 0.35 * np.sin(2 * np.pi * 5 * t))
    elif kind == "gold_chime": y = 0.6 * np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t) * (t % 0.24 < 0.12)
    elif kind == "bell": y = 0.7 * np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.76 * f * t)
    elif kind == "chirp": y = np.sin(2 * np.pi * (f + 900 * t) * t) * (t % 0.3 < 0.12)
    elif kind == "iron": y = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.6 + 0.4 * np.sin(2 * np.pi * 55 * t)
    else: y = np.zeros_like(t)
    return amp * env * y
def pitch(tau): return 220 * 2 ** (0.8 * math.log10(max(tau, 1e-6) / 1e-6))
VOICE = {"iron": "iron", "foil / tiny": "chirp", "small gold or pull-tab zone": "gold", "medium gold": "gold", "large gold / coin": "bell"}
GOLDWIN = {"small gold or pull-tab zone", "medium gold", "large gold / coin"}
def render(cls, tau, snr, depth_mm, trigger=False, dial="ALL-METAL"):
    if snr < 4: return np.zeros(int(1.6 * FS)), "silent (below threshold)"
    amp = min(1.0, 0.18 * math.log10(snr) + 0.1)
    if trigger: amp = min(1.0, amp * 2.8)                                   # +9 dB
    attack = 0.01 + 0.0012 * depth_mm
    kind = VOICE[cls]
    if trigger and dial == "GOLD":
        if cls not in GOLDWIN: return np.zeros(int(1.6 * FS)), "muted by GOLD mode"
        if kind == "gold": kind = "gold_chime"
    f0 = 110 if kind == "iron" else pitch(tau)
    return tone(pitch(tau), 1.6, kind, amp, attack), f"{kind} {f0:.0f} Hz, amp {amp:.2f}"
def write_wav(name, y):
    y = np.clip(y, -1, 1); d = (y * 32767 * 0.9).astype("<i2")
    with wave.open(f"{OUT}/{name}.wav", "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS); w.writeframes(d.tobytes())
CASES = [  # file, class, tau (s), snr, depth mm, trigger, dial
    ("01_scan_gold_1g_shallow", "small gold or pull-tab zone", 10e-6, 80, 60, False, "ALL-METAL"),
    ("02_scan_gold_10g_deep", "medium gold", 48e-6, 9, 300, False, "ALL-METAL"),
    ("03_scan_silver_coin", "large gold / coin", 245e-6, 60, 120, False, "ALL-METAL"),
    ("04_scan_foil", "foil / tiny", 2.3e-6, 40, 50, False, "ALL-METAL"),
    ("05_scan_iron_nail", "iron", 30e-6, 50, 80, False, "ALL-METAL"),
    ("06_scan_nothing_silent", "medium gold", 48e-6, 2, 400, False, "ALL-METAL"),
    ("07_TRIGGER_allmetal_gold_10g_deep", "medium gold", 48e-6, 9 * 2.5, 300, True, "ALL-METAL"),
    ("08_TRIGGER_allmetal_pulltab", "small gold or pull-tab zone", 14e-6, 70, 80, True, "ALL-METAL"),
    ("09_TRIGGER_GOLD_gold_10g", "medium gold", 48e-6, 25, 250, True, "GOLD"),
    ("10_TRIGGER_GOLD_iron_muted", "iron", 30e-6, 50, 80, True, "GOLD"),
    ("11_TRIGGER_GOLD_foil_muted", "foil / tiny", 2.3e-6, 40, 50, True, "GOLD"),
    ("12_TRIGGER_GOLD_pulltab_STILL_SOUNDS", "small gold or pull-tab zone", 14e-6, 70, 80, True, "GOLD"),
]
lib = []
for fn, cls, tau, snr, dep, trig, dial in CASES:
    y, desc = render(cls, tau, snr, dep, trig, dial); write_wav(fn, y)
    lib.append(dict(file=fn + ".wav", class_=cls, tau_us=round(tau * 1e6, 1), snr=snr, depth_mm=dep, trigger=trig, dial=dial, sound=desc))
json.dump(lib, open(f"{OUT}/audio_signature_library.json", "w"), indent=1)
for l in lib: print(l["file"], "->", l["sound"])
