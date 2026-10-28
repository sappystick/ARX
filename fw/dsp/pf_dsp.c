/* PHI-FOLD 233 receive DSP core: see pf_dsp.h. Port of src/sim/dsp_ref.py / sweep_track.py / output_modes.py (MODELED, host-tested). */
#include "pf_dsp.h"
#include <math.h>
#include <string.h>

static float sumw(const float *a, const float *b) { float s = 0.0f; for (int k = 0; k < PF_NG; k++) s += PF_W[k] * a[k] * b[k]; return s; }
static float nk_sum(void) { float s = 0.0f; for (int k = 0; k < PF_NG; k++) s += PF_NK[k]; return s; }

void pf_phi(float tau, float out[PF_NG]) {
    for (int k = 0; k < PF_NG; k++) out[k] = tau / (PF_G1[k] - PF_G0[k]) * (expf(-PF_G0[k] / tau) - expf(-PF_G1[k] / tau));
}

/* ridge fit for one basis row P: a per channel with the ground deviation d under the prior; returns the cost, writes aA, aB, v */
typedef struct { const float *hA, *hB; float S22, lam; } ridge_ctx_t;
static float ridge_one(const ridge_ctx_t *c, const float P[PF_NG], float *aA, float *aB, float *v) {
    float S11 = sumw(P, P), S12 = sumw(P, PF_PSI), det = S11 * c->S22 - S12 * S12, tot = 0.0f;
    const float *hs[2] = {c->hA, c->hB}; float as[2];
    for (int ch = 0; ch < 2; ch++) {
        const float *h = hs[ch]; float r1 = sumw(P, h), r2 = sumw(PF_PSI, h);
        float a = (r1 * c->S22 - r2 * S12) / det, d = (S11 * r2 - S12 * r1) / det, e = 0.0f;
        for (int k = 0; k < PF_NG; k++) { float r = h[k] - a * P[k] - d * PF_PSI[k]; e += PF_W[k] * r * r; }
        tot += e + c->lam * d * d; as[ch] = a;
    }
    if (aA) *aA = as[0];
    if (aB) *aB = as[1];
    if (v) *v = c->S22 / det;
    return tot;
}
static float cost_at(const ridge_ctx_t *c, float ltau) { float P[PF_NG]; pf_phi(expf(ltau), P); return ridge_one(c, P, 0, 0, 0); }

pf_fit_t pf_fit_ridge(const float gA[PF_NG], const float gB[PF_NG], float bA, float bB, float sig0, float sb) {
    float hA[PF_NG], hB[PF_NG];
    for (int k = 0; k < PF_NG; k++) { hA[k] = gA[k] - bA * PF_PSI[k]; hB[k] = gB[k] - bB * PF_PSI[k]; }
    if (sb < 1e-12f) sb = 1e-12f;
    ridge_ctx_t c = {hA, hB, 0.0f, sig0 * sig0 / (nk_sum() * sb * sb)};
    c.S22 = sumw(PF_PSI, PF_PSI) + c.lam;
    int best = 0; float bc = 0.0f;
    for (int i = 0; i < PF_NTAU; i++) { float cst = ridge_one(&c, PF_PHI[i], 0, 0, 0); if (i == 0 || cst < bc) { bc = cst; best = i; } }
    /* golden-section on log tau inside the grid bracket (maximum likelihood tau) */
    float lo = logf(PF_TAU[best > 0 ? best - 1 : 0]), hi = logf(PF_TAU[best < PF_NTAU - 1 ? best + 1 : PF_NTAU - 1]);
    const float g = 0.6180339887f; float a = lo, b = hi, x1 = b - g * (b - a), x2 = a + g * (b - a), f1 = cost_at(&c, x1), f2 = cost_at(&c, x2);
    for (int it = 0; it < 24; it++) {
        if (f1 < f2) { b = x2; x2 = x1; f2 = f1; x1 = b - g * (b - a); f1 = cost_at(&c, x1); }
        else { a = x1; x1 = x2; f1 = f2; x2 = a + g * (b - a); f2 = cost_at(&c, x2); }
    }
    pf_fit_t f; f.tau = expf(0.5f * (a + b)); float P[PF_NG]; pf_phi(f.tau, P); ridge_one(&c, P, &f.aA, &f.aB, &f.v);
    return f;
}
float pf_snr(const pf_fit_t *f, float sig0) { return hypotf(f->aA, f->aB) / (sig0 * sqrtf(f->v / nk_sum()) + 1e-30f); }
int pf_classify(float tau) { for (int i = 0; i < PF_NCLASS; i++) if (tau < PF_CLASS_HI[i]) return i; return PF_NCLASS - 1; }
float pf_axis_deg(float aA, float aB) { float x = 0.5f * atan2f(aB, aA) * 57.29577951f + 45.0f; x = fmodf(x, 180.0f); return x < 0 ? x + 180.0f : x; }

void pf_ground_init(pf_ground_t *g, float alpha) { g->bA = 0.0f; g->bB = 0.0f; g->alpha = alpha; }
void pf_ground_update(pf_ground_t *g, const float gA[PF_NG], const float gB[PF_NG]) {
    float S = sumw(PF_PSI, PF_PSI); g->bA += g->alpha * (sumw(PF_PSI, gA) / S - g->bA); g->bB += g->alpha * (sumw(PF_PSI, gB) / S - g->bB);
}

/* ---- sweep tracker ----
 * The head swings about the user (behind it, toward the heel at 178 deg), so the head moves along its own y axis: v_y = yaw_rate x R (z up). A target at
 * (x, y) relative to the head then turns the bearing at dphi/dt = -x v_y / rho^2 (sweep_track.py derives the same law for a sweep along x). With the
 * quad axis known only mod 180 deg, the sign of x (ahead of / behind the head centre) follows from the axis rotation sense and the yaw sign:
 * x_sign = -sign(d axis) * sign(yaw). PF_GYRO_Z_SIGN corrects the mounting orientation of the gyro (UNVERIFIED until the bench). */
#ifndef PF_PASS_GAP
#define PF_PASS_GAP 6
#endif
#ifndef PF_PIN_SMOOTH
#define PF_PIN_SMOOTH 2
#endif
#ifndef PF_GYRO_Z_SIGN
#define PF_GYRO_Z_SIGN 1.0f
#endif
void pf_track_reset(pf_track_t *t) { memset(t, 0, sizeof *t); }
float pf_track_step(pf_track_t *t, float aA, float aB, float snr, float yaw_dps) {
    float ax = pf_axis_deg(aA, aB), rss = hypotf(aA, aB); t->centred = 0;
    /* below threshold: the centre null of the quad pair is quiet by nature, so a pass ends only after PF_PASS_GAP quiet frames; quiet frames still feed the
       pinpoint RSS but not the bearing (the axis of a null is meaningless) */
    if (snr < 4.0f) { if (!t->state) return ax; if (++t->quiet > PF_PASS_GAP) { pf_track_reset(t); return ax; } goto pin; }
    t->quiet = 0;
    if (t->have_axis) { float d = ax - t->last_axis; while (d > 90.0f) d -= 180.0f; while (d <= -90.0f) d += 180.0f; t->axis_unwrapped += d; t->rate_acc += d * PF_GYRO_Z_SIGN * (yaw_dps > 0 ? 1.0f : (yaw_dps < 0 ? -1.0f : 0.0f)); }
    else { t->axis_unwrapped = ax; t->have_axis = 1; }
    t->last_axis = ax;
    if (fabsf(t->rate_acc) > 10.0f) t->side = t->rate_acc > 0 ? -1 : 1;    /* >= 10 deg of consistent rotation before deciding */
    /* pinpoint: PF_PIN_SMOOTH-frame moving average of RSS (2 frames = about 25 mm of travel at 30 ms and 0.84 m/s, the smoothing sweep_track.py validated),
       peak -> null (< 0.5 peak) -> rise again: the centre is the null */
pin:
    t->rss[t->head] = rss; t->head = (t->head + 1) % PF_TRACK_N; if (t->n < PF_TRACK_N) t->n++;
    int m = t->n < PF_PIN_SMOOTH ? t->n : PF_PIN_SMOOTH; float s = 0.0f; for (int i = 1; i <= m; i++) s += t->rss[(t->head - i + PF_TRACK_N) % PF_TRACK_N]; s /= (float)m;
    switch (t->state) {
        case 0: t->pk1 = s; t->state = 1; break;
        case 1: if (s > t->pk1) t->pk1 = s; else if (s < 0.5f * t->pk1) { t->state = 2; t->pk1_seen_drop = s; } break;
        case 2: if (s < t->pk1_seen_drop) t->pk1_seen_drop = s; else if (s > 2.0f * t->pk1_seen_drop && s > 0.5f * t->pk1) { t->centred = 1; t->state = 3; } break;
        default: break;
    }
    if (snr < 4.0f || !t->side) return ax;
    /* full bearing: x = rho cos(phi) must have the sign t->side */
    float full = ax; if ((cosf(ax / 57.29577951f) >= 0.0f ? 1 : -1) != t->side) full += 180.0f;
    return fmodf(full, 360.0f);
}

/* ---- descriptor ---- */
uint8_t pf_crc8(const uint8_t *p, int n) {
    uint8_t c = 0; for (int i = 0; i < n; i++) { c ^= p[i]; for (int b = 0; b < 8; b++) c = (uint8_t)((c & 0x80) ? (c << 1) ^ 0x07 : (c << 1)); } return c;
}
static uint8_t clampu8(long v) { return (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v)); }
void pf_desc_pack(const pf_desc_t *d, uint8_t o[PF_DESC_BYTES]) {
    o[0] = 0xA5; o[1] = d->seq; o[2] = (uint8_t)((d->mode & 3) | ((d->centred & 1) << 2) | ((d->side_valid & 1) << 3) | ((d->depth & 7) << 4));
    o[3] = d->cls; o[4] = clampu8(lroundf(20.0f * log2f(d->tau / 1e-6f))); o[5] = clampu8(lroundf(32.0f * log2f(d->snr > 1.0f ? d->snr : 1.0f)));
    uint16_t br = (uint16_t)lroundf(fmodf(d->bearing < 0 ? d->bearing + 360.0f : d->bearing, 360.0f) / 360.0f * 65536.0f);
    o[6] = (uint8_t)(br & 0xFF); o[7] = (uint8_t)(br >> 8); o[8] = 0; o[9] = pf_crc8(o, 9);
}
int pf_desc_unpack(const uint8_t in[PF_DESC_BYTES], pf_desc_t *d) {
    if (in[0] != 0xA5 || pf_crc8(in, 9) != in[9]) return 0;
    d->seq = in[1]; d->mode = in[2] & 3; d->centred = (in[2] >> 2) & 1; d->side_valid = (in[2] >> 3) & 1; d->depth = (in[2] >> 4) & 7; d->cls = in[3];
    d->tau = 1e-6f * exp2f(in[4] / 20.0f); d->snr = exp2f(in[5] / 32.0f); d->bearing = (float)(in[6] | (in[7] << 8)) / 65536.0f * 360.0f;
    return 1;
}

/* ---- LEDs ---- */
static const uint8_t PF_RGB[PF_NCLASS][3] = {{1, 0, 1}, {1, 1, 0}, {0, 1, 0}, {0, 1, 1}, {1, 0, 0}};   /* class colours: output_modes.CLASSES */
uint8_t pf_snr_code(float snr) {
    if (snr < 4.0f) return 0;
    long c = lroundf(1.0f + 30.0f * log10f(snr / 4.0f) / log10f(1000.0f / 4.0f)); return (uint8_t)(c < 1 ? 1 : (c > 31 ? 31 : c));
}
void pf_led_render(const pf_desc_t *d, int lit, pf_led_t fr[PF_NLED]) {
    memset(fr, 0, sizeof(pf_led_t) * PF_NLED);
    if (!lit || d->cls >= PF_NCLASS || d->snr < 4.0f) return;
    int ring = d->depth < 1 ? 1 : (d->depth > 4 ? 4 : d->depth); float best[3] = {1e9f, 1e9f, 1e9f}; int idx[3] = {-1, -1, -1};
    for (int i = 0; i < PF_NLED; i++) {
        if (PF_LED_RING[i] != ring) continue;
        float da = fabsf(fmodf(PF_LED_AZ[i] - d->bearing + 540.0f, 360.0f) - 180.0f);
        for (int j = 0; j < 3; j++) if (da < best[j]) { for (int q = 2; q > j; q--) { best[q] = best[q - 1]; idx[q] = idx[q - 1]; } best[j] = da; idx[j] = i; break; }
    }
    uint8_t code = pf_snr_code(d->snr);
    for (int j = 0; j < 3; j++) if (idx[j] >= 0) {
        pf_led_t *L = &fr[idx[j]]; L->r = PF_RGB[d->cls][0] ? 255 : 0; L->g = PF_RGB[d->cls][1] ? 255 : 0; L->b = PF_RGB[d->cls][2] ? 255 : 0;
        L->code = j == 0 ? code : (uint8_t)(code / 3 > 1 ? code / 3 : 1);
    }
    pf_led_cap(fr);
}
float pf_led_current_a(const pf_led_t fr[PF_NLED]) {
    float i = PF_I_STATIC_MA * PF_NLED; for (int k = 0; k < PF_NLED; k++) i += PF_I_CODE31_MA * fr[k].code / 31.0f * ((fr[k].r > 0) + (fr[k].g > 0) + (fr[k].b > 0)); return i / 1000.0f;
}
void pf_led_cap(pf_led_t fr[PF_NLED]) {
    float budget = PF_I_CAP_A * 1000.0f - PF_I_STATIC_MA * PF_NLED, load = 0.0f;
    for (int k = 0; k < PF_NLED; k++) load += PF_I_CODE31_MA * fr[k].code / 31.0f * ((fr[k].r > 0) + (fr[k].g > 0) + (fr[k].b > 0));
    if (load <= budget) return;
    float s = budget / load; for (int k = 0; k < PF_NLED; k++) if (fr[k].code) { int c = (int)floorf(fr[k].code * s); fr[k].code = (uint8_t)(c < 1 ? 1 : c); }
}
