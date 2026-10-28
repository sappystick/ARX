/* AU1 voice synthesiser (portable C99): one target descriptor -> stereo samples. Same rules as src/sim/output_modes.py voice(): silent below 4 sigma;
 * pitch falls with tau (f = 1200 * 2^(-0.8 log10(tau / 1 us)) Hz), iron a fixed 110 Hz buzz; timbre per class (foil chirp, gold sine + 5 Hz vibrato,
 * large gold / coin bell with a 2.76 x partial, iron buzz); loudness from log SNR; attack from depth class; equal-power pan from bearing (headphones).
 * MODELED: host-tested (fw/tests/test_voice.c); not heard on hardware. */
#pragma once
#include <stdint.h>
#include "pf_dsp.h"
#define PF_FS 32000
typedef struct {
    float phase, phase2, vib, env, target_amp, attack_s, f0, pan_l, pan_r, chirp_t; int cls, active; uint32_t since_desc;
} pf_voice_t;
void pf_voice_init(pf_voice_t *v);
void pf_voice_set(pf_voice_t *v, const pf_desc_t *d);          /* call on every received descriptor (once per TX period) */
void pf_voice_render(pf_voice_t *v, int16_t *left, int16_t *right, int n, int speaker_only);  /* speaker_only: mono sum on both */
float pf_voice_pitch(float tau);
