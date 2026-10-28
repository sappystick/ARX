/* CB1D head firmware: per-period scheduler (pf233_timing.h, pf233_output.h) and the receive chain (pf_dsp). Portable over pf_hal.h.
 * One TX period: [housekeeping + TX on] -> [receive window: gates only, no other edge] -> idle slot: LED frame (mode rules), descriptor burst, AU1 reply,
 * (the gyro is on AU1: its yaw rate arrives in the AU1 reply). The averaging window (PF_OUT_N_AVG per PRF mode, 30 ms) turns pulses into one fit. MODELED: host-tested only. */
#include <string.h>
#include <math.h>
#include "pf_hal.h"
#include "pf_dsp.h"
#include "pf_head.h"

static void led_bytes(const pf_led_t fr[PF_NLED], uint8_t *out, int *n) {
    int k = 0; for (int i = 0; i < 4; i++) out[k++] = 0x00;                                      /* start frame: 32 zero bits */
    for (int i = 0; i < PF_NLED; i++) { out[k++] = (uint8_t)(0xE0 | (fr[i].code & 0x1F)); out[k++] = fr[i].b; out[k++] = fr[i].g; out[k++] = fr[i].r; }
    for (int i = 0; i < 4; i++) out[k++] = 0xFF;                                                  /* end frame: 32 one bits (SK9822: 64 + 32 N bits per frame) */
    *n = k;
}
void pf_head_init(pf_head_t *h, int prf_mode) {
    memset(h, 0, sizeof *h); h->prf = prf_mode; h->out_mode = 2; pf_ground_init(&h->ground, 0.05f); pf_track_reset(&h->track);
    h->sig0 = 2e-3f;                                                                            /* frame noise: re-estimated from target-free residuals */
    h->acquire = 64;   /* power-up ground acquisition (the user pumps the head over clean ground): 64 frames of unconditional, faster (alpha 0.2) ground learning;
                          without it the tracker starts at b = 0, reads the ground as a target and, learning only from target-free frames, never converges */
}
void pf_head_pulse(pf_head_t *h, const float gA[PF_NG], const float gB[PF_NG]) {
    for (int k = 0; k < PF_NG; k++) { h->accA[k] += gA[k]; h->accB[k] += gB[k]; } h->nacc++;
}
int pf_head_frame_ready(const pf_head_t *h, int n_avg) { return h->nacc >= n_avg; }
/* one averaged frame -> descriptor; returns 1 when the frame carries a target */
int pf_head_process(pf_head_t *h, float yaw_dps, pf_desc_t *d) {
    float gA[PF_NG], gB[PF_NG]; for (int k = 0; k < PF_NG; k++) { gA[k] = h->accA[k] / h->nacc; gB[k] = h->accB[k] / h->nacc; }
    float sig = h->sig0 / sqrtf((float)h->nacc);                                                /* averaging lowers the frame noise */
    memset(h->accA, 0, sizeof h->accA); memset(h->accB, 0, sizeof h->accB); h->nacc = 0;
    if (h->acquire > 0) { float al = h->ground.alpha; h->ground.alpha = 0.2f; pf_ground_update(&h->ground, gA, gB); h->ground.alpha = al; h->acquire--;
                          memset(d, 0, sizeof *d); d->seq = h->seq++; d->mode = (uint8_t)h->out_mode; d->cls = 0xFF; return 0; }
    float sb = 0.1f * hypotf(h->ground.bA, h->ground.bB) + 1e-4f;
    pf_fit_t f = pf_fit_ridge(gA, gB, h->ground.bA, h->ground.bB, sig, sb); float snr = pf_snr(&f, sig);
    int hit = snr >= 4.0f;
    if (!hit) pf_ground_update(&h->ground, gA, gB);                                             /* slow ground balance on target-free frames */
    float bearing = pf_track_step(&h->track, f.aA, f.aB, snr, yaw_dps);
    memset(d, 0, sizeof *d); d->seq = h->seq++; d->mode = (uint8_t)h->out_mode;
    d->cls = hit ? (uint8_t)pf_classify(f.tau) : 0xFF; d->tau = f.tau; d->snr = snr; d->bearing = bearing;
    d->side_valid = h->track.side != 0; d->centred = (uint8_t)h->track.centred; d->depth = h->depth ? h->depth : 2;
    return hit;
}
/* idle-slot work in the order output_modes.py schedules it; in_sweep: the user is sweeping (COMBINED keeps the LEDs dark then) */
void pf_head_idle(pf_head_t *h, const pf_desc_t *d, int in_sweep) {
    static uint8_t buf[8 + 4 * PF_NLED]; int n;
    pf_led_t fr[PF_NLED]; int lit = (h->out_mode == 1) || (h->out_mode == 2 && !in_sweep);       /* AUDIO_ONLY: dark; LED_ONLY: lit; COMBINED: dark in a sweep */
    if (h->out_mode != 0 || h->led_was_lit) { pf_led_render(d, lit, fr); led_bytes(fr, buf, &n); hal_led_frame(buf, n); h->led_was_lit = lit; }
    uint8_t b[PF_DESC_BYTES]; pf_desc_pack(d, b); hal_link_send(b, PF_DESC_BYTES);
    uint8_t r[4];                                                                                /* AU1 reply: selector, yaw (0.1 deg/s), CRC */
    if (hal_link_reply(r, 4, 60) == 4 && pf_crc8(r, 3) == r[3] && (r[0] & 3) <= 2) {
        h->out_mode = r[0] & 3; h->yaw_dps = 0.1f * (float)(int16_t)((uint16_t)r[1] | ((uint16_t)r[2] << 8)); h->yaw_ok = 1;   /* used by the next frame (one-frame latency) */
    }
}
