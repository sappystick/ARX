#pragma once
#include "pf_voice.h"
typedef struct { pf_voice_t voice; int mode; unsigned good, bad; } pf_audio_t;
void pf_audio_init(pf_audio_t *a);
void pf_audio_step(pf_audio_t *a, int n_samples, int16_t *L, int16_t *R);
