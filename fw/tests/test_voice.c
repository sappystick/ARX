/* Host test of the AU1 voice synthesiser: silent search, pitch per class (zero crossings), pan direction, attack from depth, descriptor link round trip. */
#include <stdio.h>
#include <math.h>
#include "pf_voice.h"
static int fails = 0, checks = 0;
#define CHECK(cond, ...) do { checks++; if (!(cond)) { fails++; printf("FAIL "); printf(__VA_ARGS__); printf("\n"); } } while (0)
#define N (PF_FS / 2)
static int16_t L[N], R[N];
static float rms(const int16_t *x, int a, int b) { double s = 0; for (int i = a; i < b; i++) s += (double)x[i] * x[i]; return (float)sqrt(s / (b - a)); }
static float zc_freq(const int16_t *x, int a, int b) { int z = 0; for (int i = a + 1; i < b; i++) z += (x[i - 1] < 0) != (x[i] < 0); return z * 0.5f * PF_FS / (b - a); }
int main(void) {
    pf_voice_t v; pf_desc_t d = {0, 2, 0, 1, 1, 3, 95e-6f, 60.0f, 358.0f};
    /* 1 silent below threshold */
    pf_voice_init(&v); d.snr = 3.0f; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, N, 0); CHECK(rms(L, 0, N) < 1.0f && rms(R, 0, N) < 1.0f, "silent below 4 sigma");
    /* 2 pitch of the medium-gold voice = pitch(tau) within 3 % (vibrato averages out over 0.25 s) */
    pf_voice_init(&v); d.snr = 60.0f; d.cls = 2; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, N, 1);
    float f = zc_freq(L, N / 2, N), f0 = pf_voice_pitch(95e-6f); printf("medium gold: %.1f Hz (expected %.1f)\n", f, f0); CHECK(fabsf(f / f0 - 1.0f) < 0.03f, "gold pitch %g vs %g", f, f0);
    /* 3 pitch falls with tau: small gold (18 us) higher than large gold (300 us) */
    CHECK(pf_voice_pitch(18e-6f) > pf_voice_pitch(95e-6f) && pf_voice_pitch(95e-6f) > pf_voice_pitch(300e-6f), "pitch falls with tau");
    /* 4 iron buzz near 110 Hz fundamental (square + 55 Hz: zero crossings of the sum at 110 Hz) */
    pf_voice_init(&v); d.cls = 4; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, N, 1); f = zc_freq(L, N / 2, N); printf("iron: %.1f Hz\n", f); CHECK(f > 90.0f && f < 130.0f, "iron %g Hz", f);
    /* 5 pan: a target to the user's left (bearing 88 deg) is louder in the left ear, to the right (268 deg) in the right ear */
    pf_voice_init(&v); d.cls = 1; d.bearing = 88.0f; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, N, 0); CHECK(rms(L, N / 2, N) > 2.0f * rms(R, N / 2, N), "left target pans left");
    pf_voice_init(&v); d.bearing = 268.0f; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, N, 0); CHECK(rms(R, N / 2, N) > 2.0f * rms(L, N / 2, N), "right target pans right");
    /* 6 attack from depth: a deep target (depth class 1) rises slower than a shallow one (4) */
    pf_voice_init(&v); d.bearing = 358.0f; d.depth = 4; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, 640, 1); float shallow = rms(L, 320, 640);
    pf_voice_init(&v); d.depth = 1; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, 640, 1); float deep = rms(L, 320, 640);
    CHECK(shallow > 1.5f * deep, "attack: shallow %g vs deep %g", shallow, deep);
    /* 7 release: after the target goes below threshold the voice fades out within 0.5 s */
    d.snr = 3.0f; pf_voice_set(&v, &d); pf_voice_render(&v, L, R, N, 1); CHECK(rms(L, N - 1600, N) < 50.0f, "release");
    /* 8 descriptor link: pack -> unpack -> voice gives the same pitch */
    uint8_t b[PF_DESC_BYTES]; pf_desc_t e; d.snr = 60.0f; d.cls = 1; d.tau = 18e-6f; pf_desc_pack(&d, b); CHECK(pf_desc_unpack(b, &e), "unpack");
    CHECK(fabsf(pf_voice_pitch(e.tau) / pf_voice_pitch(d.tau) - 1.0f) < 0.01f, "pitch survives the link quantisation");
    printf("checks %d, fails %d\n", checks, fails); return fails ? 1 : 0;
}
