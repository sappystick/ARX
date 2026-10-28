/* PHI-FOLD 233 receive DSP core (portable C99, float32). Port of src/sim/dsp_ref.py (fit_ridge, GroundTracker), src/sim/sweep_track.py (side, pinpoint)
 * and src/sim/output_modes.py (descriptor, LED renderer, current cap). MODELED: tested on the host against the Python vectors (fw/tests); not run on hardware.
 * Tables (gates, weights, tau bank, LED map) come from the generated header pf233_dsp_tables.h (src/sim/fw_tables.py). */
#pragma once
#include <stdint.h>
#include "pf233_dsp_tables.h"

/* ---- per-frame fit ---- */
typedef struct { float tau, aA, aB, v; } pf_fit_t;               /* tau (s), amplitudes per quad, posterior variance factor of a */
/* target fit with the ground held at (bA, bB) and a Gaussian prior on its deviation (sb); sig0 = noise of one ADC frame */
pf_fit_t pf_fit_ridge(const float gA[PF_NG], const float gB[PF_NG], float bA, float bB, float sig0, float sb);
float pf_snr(const pf_fit_t *f, float sig0);                      /* |a| / sigma_a */
int pf_classify(float tau);                                       /* 0 foil, 1 small gold / pull-tab zone, 2 medium gold, 3 large gold / coin, 4 iron */
float pf_axis_deg(float aA, float aB);                            /* 0.5 atan2(aB, aA) + 45, mod 180 */
void pf_phi(float tau, float out[PF_NG]);                         /* mean of exp(-t / tau) over each gate */

/* ---- slow ground balance: ground-only LS of target-free frames, exponential average ---- */
typedef struct { float bA, bB, alpha; } pf_ground_t;
void pf_ground_init(pf_ground_t *g, float alpha);
void pf_ground_update(pf_ground_t *g, const float gA[PF_NG], const float gB[PF_NG]);

/* ---- sweep tracker: side (axis rotation sense x gyro yaw sign) and pinpoint (RSS null between two peaks) ---- */
#define PF_TRACK_N 96
typedef struct {
    float axis_unwrapped, last_axis, rate_acc; int have_axis;
    float rss[PF_TRACK_N]; int n, head;                           /* ring buffer of RSS over the pass */
    float pk1, pk1_seen_drop; int state;                          /* 0 idle, 1 rising to first peak, 2 falling to null, 3 rising to second peak */
    int side;                                                     /* +1 / -1 / 0 unknown */
    int centred;                                                  /* 1 for the frame in which the null between two peaks was confirmed */
    int quiet;                                                    /* consecutive frames below 4 sigma (the null itself is quiet) */
} pf_track_t;
void pf_track_reset(pf_track_t *t);
/* yaw_dps: gyro yaw rate (deg/s, +CCW from above); returns full bearing 0..360 when the side is known, else the axis 0..180 */
float pf_track_step(pf_track_t *t, float aA, float aB, float snr, float yaw_dps);

/* ---- descriptor link (10 bytes, CRC-8 poly 0x07) ---- */
#define PF_DESC_BYTES 10
typedef struct { uint8_t seq, mode, centred, side_valid, cls, depth; float tau, snr, bearing; } pf_desc_t;
uint8_t pf_crc8(const uint8_t *p, int n);
void pf_desc_pack(const pf_desc_t *d, uint8_t out[PF_DESC_BYTES]);
int pf_desc_unpack(const uint8_t in[PF_DESC_BYTES], pf_desc_t *d);   /* 1 ok, 0 bad sync / CRC */

/* ---- LED renderer (SK9822-EC20): grayscale 0 / 255 per channel, brightness by the 5-bit current field, frame current capped ---- */
typedef struct { uint8_t r, g, b, code; } pf_led_t;
#define PF_I_CODE31_MA 18.0f
#define PF_I_STATIC_MA 1.0f
#define PF_I_CAP_A 0.35f
void pf_led_render(const pf_desc_t *d, int lit, pf_led_t fr[PF_NLED]);   /* one target; lit = 0 gives all off (dark during sweep) */
float pf_led_current_a(const pf_led_t fr[PF_NLED]);
void pf_led_cap(pf_led_t fr[PF_NLED]);
uint8_t pf_snr_code(float snr);                                     /* 0 below 4 sigma, 1..31 log scale up to SNR 1000 */
