/* End-to-end host test: CB1D head (pf_head) <-> link bytes <-> AU1 (pf_audio) with a simulated sweep over a buried target in viscous ground.
 * Scene (MODELED): the head swings at yaw +40 deg/s on a 1.2 m arm (0.84 m/s); a target 30 mm ahead of the sweep line, tau 18 us (small-gold class),
 * quad pattern A = s(rho) cos 2(phi - 45), B = s(rho) sin 2(phi - 45) with s(rho) = (rho / r0) exp(-(rho / r0)^2 / 2) (null under the centre, peak at r0);
 * ground 1/t in both quads with a 2 % imbalance; frame noise. Checks: silent over target-free ground; detection, class, side, exactly one centre event
 * during a pass 10 mm off the line and none 30 mm off it; AU1 voice pitch = pitch(tau); LED rules per mode (AUDIO_ONLY dark, LED_ONLY lit, COMBINED dark during the sweep); selector -> head. */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include "pf_hal.h"
#include "pf_head.h"
#include "pf_audio.h"
static int fails = 0, checks = 0;
#define CHECK(cond, ...) do { checks++; if (!(cond)) { fails++; printf("FAIL "); printf(__VA_ARGS__); printf("\n"); } } while (0)
/* ---- host HAL: link loopback between the two halves, LED capture, selector ---- */
static uint8_t link_h2a[16]; static int link_h2a_n; static uint8_t link_a2h[4]; static int link_a2h_n; static int selector = 2, led_lit_px; static float led_I;
static pf_audio_t AU; static int16_t AL[2048], AR[2048];
void hal_led_frame(const uint8_t *f, int n) { led_lit_px = 0; for (int i = 4; i + 3 < n - 4; i += 4) led_lit_px += (f[i] & 0x1F) > 0; (void)led_I; }
void hal_link_send(const uint8_t *b, int n) { memcpy(link_h2a, b, n); link_h2a_n = n; pf_audio_step(&AU, 1000, AL, AR); }   /* AU1 answers inside the slot */
int hal_link_reply(uint8_t *b, int n, uint32_t t) { (void)t; if (link_a2h_n < n) return 0; memcpy(b, link_a2h, n); link_a2h_n = 0; return n; }
int au_link_recv(uint8_t *b, int n, uint32_t t) { (void)t; if (link_h2a_n < n) return 0; memcpy(b, link_h2a, n); link_h2a_n = 0; return n; }
void au_link_send(const uint8_t *b, int n) { memcpy(link_a2h, b, n); link_a2h_n = n; }
int au_selector(void) { return selector; }
int au_headphones(void) { return 0; }
static int amp_spk; void au_amp_enable(int s, int h) { amp_spk = s; (void)h; }
static float audio_rms; static int16_t lastL[1000];
void au_audio_out(const int16_t *l, const int16_t *r, int n) { double s = 0; for (int i = 0; i < n; i++) s += (double)l[i] * l[i]; audio_rms = (float)sqrt(s / n); memcpy(lastL, l, sizeof(int16_t) * (n < 1000 ? n : 1000)); (void)r; }
void hal_tx_fire(uint32_t t) { (void)t; } void hal_adc_gates(float a[9], float b[9]) { (void)a; (void)b; } float hal_gyro_yaw_dps(void) { return 40.0f; }
int hal_trigger(void) { return 0; } void hal_wait_period_end(uint32_t p) { (void)p; }
/* ---- scene ---- */
static double gauss(void) { double u = (rand() + 1.0) / (RAND_MAX + 2.0), v = (rand() + 1.0) / (RAND_MAX + 2.0); return sqrt(-2 * log(u)) * cos(6.283185307 * v); }
static void scene(float x_mm, float y_mm, float amp, float tau, float ground, float sig, float gA[9], float gB[9]) {
    float P[9]; pf_phi(tau, P); float rho = hypotf(x_mm, y_mm), r0 = 70.0f, s = (rho / r0) * expf(-(rho / r0) * (rho / r0) / 2.0f), phi = atan2f(y_mm, x_mm);
    float th = 2.0f * (phi - 45.0f / 57.29577951f);
    for (int k = 0; k < 9; k++) { float n = sig / sqrtf(PF_NK[k]);
        gA[k] = amp * s * cosf(th) * P[k] + 0.02f * ground * PF_PSI[k] + n * (float)gauss(); gB[k] = amp * s * sinf(th) * P[k] + 0.02f * ground * PF_PSI[k] + n * (float)gauss(); }
}
static int run_pass(int mode_sel, float x0, int *hits, int *cls_ok, int *centred, int *side, float *pitch_hz, int *led_max, int *spk) {
    pf_head_t h; pf_head_init(&h, 0); h.sig0 = 2e-3f; pf_audio_init(&AU); selector = mode_sel; *hits = *cls_ok = *centred = *side = *led_max = *spk = 0; *pitch_hz = 0;
    float gA[9], gB[9]; pf_desc_t d;
    for (int i = 0; i < 24 * 80; i++) { scene(0, 0, 0, 18e-6f, 5.0f, 2e-3f, gA, gB); pf_head_pulse(&h, gA, gB); if (pf_head_frame_ready(&h, 24)) { pf_head_process(&h, 0, &d); pf_head_idle(&h, &d, 0); } }   /* power-up ground acquisition over clean ground */
    for (int i = 0; i < 24 * 30; i++) {                                                         /* the pass: y from -250 to +250 mm (0.84 m/s, 800 Hz) */
        float y = -250.0f + 500.0f * i / (24 * 30.0f);
        scene(x0, y, 0.08f, 18e-6f, 5.0f, 2e-3f, gA, gB); pf_head_pulse(&h, gA, gB);
        if (pf_head_frame_ready(&h, 24)) {
            int hit = pf_head_process(&h, 40.0f, &d); pf_head_idle(&h, &d, 1);
            if (hit) { (*hits)++; *cls_ok += d.cls == 1; } *centred += d.centred; if (d.side_valid) *side = h.track.side;
            if (led_lit_px > *led_max) *led_max = led_lit_px;
            *spk |= amp_spk;
            if (hit && fabsf(y) < 120.0f && AU.voice.active) { int z = 0; for (int k = 1; k < 1000; k++) z += (lastL[k - 1] < 0) != (lastL[k] < 0); *pitch_hz = z * 0.5f * PF_FS / 1000.0f; }
        }
    }
    return 0;
}
int main(void) {
    srand(233);
    int hits, ok, cen, side, ledm, spk; float pf;
    /* 1 silent over target-free ground (amplitude 0) */
    { pf_head_t h; pf_head_init(&h, 0); pf_audio_init(&AU); selector = 2; float gA[9], gB[9]; pf_desc_t d; int fired = 0;
      for (int i = 0; i < 24 * 264; i++) { scene(0, 0, 0, 18e-6f, 5.0f * (1 + 0.1f * sinf(i / 500.0f)), 2e-3f, gA, gB); pf_head_pulse(&h, gA, gB); if (pf_head_frame_ready(&h, 24)) { fired += pf_head_process(&h, 40, &d); pf_head_idle(&h, &d, 1); } }
      printf("ground only: %d detections in 200 frames after the 64-frame acquisition\n", fired); CHECK(fired <= 2, "silent over ground, %d", fired); }
    /* 2 COMBINED: detect, class small gold, side, one centre event, voice pitch, LEDs dark during the sweep */
    run_pass(2, 30.0f, &hits, &ok, &cen, &side, &pf, &ledm, &spk);
    printf("COMBINED, 30 mm off the sweep line: hits %d side %d centred %d (not under the centre: centre / peak 0.64 > 0.5, no event expected)\n", hits, side, cen);
    CHECK(side != 0, "side resolved at 30 mm"); CHECK(cen == 0, "no centre event 30 mm off the line, %d", cen);
    run_pass(2, 10.0f, &hits, &ok, &cen, &side, &pf, &ledm, &spk);
    printf("COMBINED: hits %d class-ok %d centred %d side %d pitch %.0f Hz (expected %.0f) LED max lit %d speaker %d\n", hits, ok, cen, side, pf, pf_voice_pitch(18e-6f), ledm, spk);
    CHECK(hits >= 5, "detected (%d frames)", hits); CHECK(ok >= hits * 8 / 10, "class small gold in %d of %d", ok, hits);
    CHECK(cen == 1, "one centre event, %d", cen); CHECK(fabsf(pf / pf_voice_pitch(18e-6f) - 1.0f) < 0.08f, "voice pitch %g", pf); CHECK(ledm == 0, "COMBINED: LEDs dark during the sweep"); CHECK(spk, "speaker on");
    /* 3 LED_ONLY: LEDs lit during the sweep, speaker off */
    run_pass(1, 30.0f, &hits, &ok, &cen, &side, &pf, &ledm, &spk); printf("LED_ONLY: LED max lit %d speaker %d\n", ledm, spk);
    CHECK(ledm == 3, "LED_ONLY: 3 pixels lit (%d)", ledm); CHECK(!spk, "LED_ONLY: speaker off");
    /* 4 AUDIO_ONLY: LEDs never driven, speaker on */
    run_pass(0, 30.0f, &hits, &ok, &cen, &side, &pf, &ledm, &spk); printf("AUDIO_ONLY: LED max lit %d speaker %d\n", ledm, spk);
    CHECK(ledm == 0, "AUDIO_ONLY: LEDs dark"); CHECK(spk, "AUDIO_ONLY: speaker on");
    printf("checks %d, fails %d\n", checks, fails); return fails ? 1 : 0;
}
