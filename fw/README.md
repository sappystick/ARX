# PHI-FOLD 233 firmware (MODELED: host-tested, not run on hardware)

| Part | Files | What it does |
|---|---|---|
| DSP core (both MCUs) | `dsp/pf_dsp.{h,c}` | Per averaged frame: ground-held ridge fit of the 9 golden-ratio gate means (target `exp(-t/tau)` + viscous ground `1/t`, tau bank 2 us .. 3 ms, golden-section maximum likelihood), SNR, class from tau, quad bearing axis; slow ground balance on target-free frames with a 64-frame power-up acquisition (in `cb1d/pf_head.c`); sweep tracker (side from the axis rotation sense x gyro yaw, pinpoint = quad null between two peaks); 10-byte descriptor with CRC-8; SK9822 LED renderer (grayscale 0 / 255, 5-bit current brightness, 0.35 A frame cap) |
| Head (CB1D, RP2350) | `cb1d/pf_head.{h,c}` | Pulse accumulation over the mode's averaging window (`PF_OUT_N_AVG`, 30 ms), the receive chain, and the idle-slot work in the order of `src/sim/output_modes.py`: LED frame (mode rules), descriptor burst, AU1 reply (selector), gyro read |
| Audio (AU1, MSPM0G3507) | `au1/pf_voice.{h,c}`, `au1/pf_audio.{h,c}` | Descriptor in, selector reply out, voice synthesis at 32 kHz (pitch falls with tau, timbre per class, loudness from SNR, attack from depth, equal-power pan from bearing), amplifier enables per mode and headphone plug |
| Hardware layer | `common/pf_hal.h` | The calls the target builds implement (Pico SDK: PIO for the gated ADC frames, the LED stream and the link, I2C0 for the gyro; MSPM0 SDK: UART0, DAC12, TIMG12 PWM, GPIO) |
| Tests | `tests/test_dsp.c`, `test_voice.c`, `test_system.c` | C vs the Python reference vectors; voice properties; end-to-end head <-> link <-> AU1 over a simulated sweep and ground |

Generated headers (never edited): `pf233_dsp_tables.h`, `pf233_dsp_vectors.h` (src/sim/fw_tables.py), `pf233_timing.h` (src/sim/fw_timeline.py), `pf233_output.h` (src/sim/output_modes.py).

`make -C fw test` builds and runs the three host tests (pipeline step `fw-test`). Not done here: the target builds (the Pico SDK and the TI MSPM0 SDK with their toolchains are not installed in this container), the BMI270 configuration-file load, the AD7389-4 PIO capture, and every bench item in docs/design/BENCH_FIRST_ARTICLE_TX.md. Constants marked ASSUMED in docs/ASSUMPTIONS.md (39-41) include the averaging window, the swing radius 1.2 m, the class tau edges, the ground prior (10 %), the pass gap, `PF_GYRO_Z_SIGN` (mounting orientation, set on the bench).
