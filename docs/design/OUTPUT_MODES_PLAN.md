# Output modes: audio only / LED only / combined (PLAN, 2026-10-28, not started; owner approval pending)

Owner request: a 3-position selector (audio only, LED only, combined), silent search with a coded audio signature only over a target (tone, depth,
length, volume by metal class), the same signature mirrored on the 66 LEDs (colour, direction, brightness), a small loud speaker on the handle, and
optionally Bluetooth / bone-conduction headphones. Goal: the least change to the existing, released design. Everything here is a PLAN; no number is measured.

## What the design has today
- The receive signal is never "sent to" an output. It is sampled (AB1A/AB1B, AD7389-4), reduced per pulse in the Pico (gates, ground balance,
  classification) to a short target descriptor (class, tau, depth class, SNR, bearing). Outputs only render that descriptor; they cost little compute
  (fw_timeline: 61-79 % of each period is spare).
- Planned since Step 7 (HANDOFF_ARCHIVE_step7, ENHANCEMENT_REVIEW 2026-10-23 section 7): audio library (pitch from tau class, loudness from SNR,
  silent search, latency under about 50 ms) and LED map (bearing on the ring, depth as ring, confidence as brightness). The audio rules exist only as
  src/archive/audio_dsp.py (renders WAVs).
- Built so far: the LED output only (LB1-v6, dark during sweeps). There is NO audio hardware: no amplifier, speaker, jack or audio net on any board.
- Spare capacity already in place: the 5-core signal cord uses 4 cores (W013 TRIG, W016 DIAL, W018 GND, W021 P3V3): core 5 is spare. JH.5 / JH.6 on HB2
  and JTR.5 / JTR.6 on CB1D exist and are unconnected. The Pico has unassigned GPIO pins (20, 21, 22, 26, 27, 29 by the Pico pinout, ASSUMPTIONS 22,
  UNVERIFIED). The DIAL line is an analog resistor ladder read by the Pico ADC (trigger_check.py models it).
- The Pico 2 W on CB1D carries a CYW43439 radio inside the head, next to the receive coils. No radio policy is recorded yet (new open item).

## Recommended route (least modification)
1. Firmware first (no hardware): one signature descriptor -> two renderers.
   - Audio voice: pitch = tau / conductivity class, timbre = metal class (gold window, large non-ferrous, foil, iron), loudness = SNR above threshold,
     attack = depth class, length = time over target; stereo pan = bearing (headphones only). Silent until the ground-balanced signal passes the threshold.
   - LED voice: hue = metal class, ring position = bearing, ring index = depth class, brightness = SNR by the SK9822 5-bit CURRENT setting (datasheet
     Rev. A/0: the 5-bit field sets the drive current of all three outputs), colours fully on/off so the 1.2 kHz grayscale PWM is not used.
   - Mode table (pf233_timing.h): AUDIO_ONLY = LEDs held off (lowest receive noise); LED_ONLY = LEDs lit and refreshed every period in the idle slot,
     current-set brightness, no audio; COMBINED = today's dark-during-sweep LEDs + live audio.
   - Python model + checks first (DSP in Python, OPEN_ITEMS 5): latency per mode under 50 ms, no LED clock / data edge inside a receive gate in any mode.
2. Selector: a 3-position rotary switch on the grip next to the existing 4-position dial, wired into the SAME DIAL ladder (4 x 3 = 12 ADC levels, values
   chosen so every level is separated with resistor tolerance and P3V3 drift; extend trigger_check.py). No new conductor, no cord change.
   (On the battery side instead: one extra wire in the 0.2 m grip rear channel.)
3. Audio path, wired (lowest latency): Pico PWM (one or two free GPIOs) -> RC filter on CB1D -> JTR.5 -> spare cord core 5 (new harness W067) -> HB2 JH.5
   -> 0.2 m lead in the grip rear channel -> small audio board in the battery-side housing: class-D amplifier powered from the pack (not from the AWG28
   P3V3 core: amplifier current on that core would shift the dial reading), small sealed speaker, 3.5 mm jack whose plug mutes the speaker (wired or
   wired bone-conduction headphones). PM2 change limited to a fused, switched 2-pin power tap. Parts and ratings to be taken from datasheets (rule 7).
4. Bluetooth / bone-conduction headphones: try first with NO hardware, using the Pico 2 W radio (firmware). Two risks decide it on the bench:
   classic Bluetooth audio latency against the 50 ms target (UNVERIFIED), and radio / supply bursts in the head during receive gates. If either fails,
   a Bluetooth transmitter on the handle audio board (1.75 m from the coils) fed from the same audio line.

## Changes by board (if approved)
| Item | Change | Released board affected |
|---|---|---|
| Firmware | descriptor, two renderers, mode table, header constants | none |
| CB1D | audio net on a free Pico pin, RC filter, JTR.5 | CB1D-C1 -> C2 |
| Signal cord | core 5 used (W067 AUDIO) | none (cord unchanged) |
| HB2 | JH.5 pass-through, 3-position switch in the dial ladder | HB2 rev |
| PM2 | fused switched power tap | PM2 rev |
| New AU1 | amplifier, regulator, speaker, jack (battery-side housing) | new board |
| Housing | speaker grille, jack, selector holes (generators) | upper assembly rev |

Releases: TX_r6 after CB1D / HB2 / PM2 change; the whole-system package stays held until the owner says the open work is done.
