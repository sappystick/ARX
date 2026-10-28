#include "pf_voice.h"
#include <math.h>
#include <string.h>
#define TWO_PI 6.283185307f
#define FWD_DEG 358.0f          /* forward for the user (output_modes.FWD) */
#define RELEASE_S 0.12f         /* voice fades this fast after the last above-threshold descriptor (ASSUMED) */
float pf_voice_pitch(float tau) { float us = tau / 1e-6f; if (us < 1.0f) us = 1.0f; return 1200.0f * powf(2.0f, -0.8f * log10f(us)); }
void pf_voice_init(pf_voice_t *v) { memset(v, 0, sizeof *v); v->cls = -1; }
void pf_voice_set(pf_voice_t *v, const pf_desc_t *d) {
    if (d->cls >= PF_NCLASS || d->snr < 4.0f) { v->active = 0; return; }                 /* silent search */
    int newcls = d->cls != v->cls; v->cls = d->cls; v->active = 1; v->since_desc = 0;
    v->f0 = (d->cls == 4) ? 110.0f : pf_voice_pitch(d->tau);
    float a = 0.18f * log10f(d->snr) + 0.1f; v->target_amp = a > 1.0f ? 1.0f : a;
    int dep = d->depth < 1 ? 1 : (d->depth > 4 ? 4 : d->depth); v->attack_s = (10.0f + 25.0f * (4 - dep)) * 1e-3f;
    float pan = -sinf((d->bearing - FWD_DEG) / 57.29577951f);                                /* -1 left .. +1 right */
    float th = (pan + 1.0f) * 0.25f * 3.14159265f; v->pan_l = cosf(th); v->pan_r = sinf(th);   /* equal power */
    if (newcls) { v->chirp_t = 0.0f; }
}
void pf_voice_render(pf_voice_t *v, int16_t *L, int16_t *R, int n, int speaker_only) {
    const float dt = 1.0f / PF_FS;
    for (int i = 0; i < n; i++) {
        float goal = v->active ? v->target_amp : 0.0f, tc = v->active ? v->attack_s : RELEASE_S;
        v->env += (goal - v->env) * (dt / (tc + dt));
        float y = 0.0f;
        if (v->env > 1e-4f && v->cls >= 0) {
            switch (v->cls) {
                case 0: { float f = v->f0 + 900.0f * v->chirp_t; v->phase += TWO_PI * f * dt; v->chirp_t += dt; if (v->chirp_t > 0.3f) v->chirp_t = 0.0f;
                          y = (v->chirp_t < 0.12f) ? sinf(v->phase) : 0.0f; break; }                                    /* foil: short upward chirp */
                case 1: case 2: { v->vib += TWO_PI * 5.0f * dt; v->phase += TWO_PI * v->f0 * dt * (1.0f + 0.35f * 5.0f / v->f0 * cosf(v->vib)); y = sinf(v->phase); break; }   /* gold: sine + 5 Hz vibrato */
                case 3: { v->phase += TWO_PI * v->f0 * dt; v->phase2 += TWO_PI * 2.76f * v->f0 * dt; y = 0.7f * sinf(v->phase) + 0.3f * sinf(v->phase2); break; }       /* bell */
                default: { v->phase += TWO_PI * 110.0f * dt; v->phase2 += TWO_PI * 55.0f * dt; y = 0.6f * (sinf(v->phase) >= 0 ? 1.0f : -1.0f) + 0.4f * sinf(v->phase2); break; } /* iron */
            }
            if (v->phase > TWO_PI) v->phase -= TWO_PI;
            if (v->phase2 > TWO_PI) v->phase2 -= TWO_PI;
            if (v->vib > TWO_PI) v->vib -= TWO_PI;
        }
        y *= v->env;
        float l = speaker_only ? y : y * v->pan_l * 1.41421356f, r = speaker_only ? y : y * v->pan_r * 1.41421356f;
        l = l > 1.0f ? 1.0f : (l < -1.0f ? -1.0f : l);
        r = r > 1.0f ? 1.0f : (r < -1.0f ? -1.0f : r);
        L[i] = (int16_t)(l * 32000.0f); R[i] = (int16_t)(r * 32000.0f);
    }
}
