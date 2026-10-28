/* Host test of the C DSP core against the Python reference (src/sim/dsp_ref.py vectors, generated pf233_dsp_vectors.h). MODELED inputs. */
#include <stdio.h>
#include <math.h>
#include <string.h>
#include "pf_dsp.h"
#include "pf233_dsp_vectors.h"
static int fails = 0, checks = 0;
#define CHECK(cond, ...) do { checks++; if (!(cond)) { fails++; printf("FAIL "); printf(__VA_ARGS__); printf("\n"); } } while (0)
int main(void) {
    /* 1 fit vs the Python reference: tau within 0.5 %, amplitudes within 1 % of |a| + 1e-6, axis within 0.2 deg, class equal, SNR within 1 % */
    for (int i = 0; i < PF_NVEC; i++) {
        const pf_vec_t *V = &PF_VEC[i]; pf_fit_t f = pf_fit_ridge(V->gA, V->gB, V->bA, V->bB, V->sig0, V->sb);
        float amag = hypotf(V->aA, V->aB), snr = pf_snr(&f, V->sig0);
        printf("vec %d: tau %.4g (ref %.4g) aA %.4g (%.4g) aB %.4g (%.4g) snr %.3g (%.3g) cls %d (%d)\n", i, f.tau, V->tau, f.aA, V->aA, f.aB, V->aB, snr, V->snr, pf_classify(f.tau), V->cls);
        if (amag > 1e-3f) {
            CHECK(fabsf(f.tau / V->tau - 1.0f) < 5e-3f, "vec %d tau %g vs %g", i, f.tau, V->tau);
            CHECK(fabsf(f.aA - V->aA) < 0.01f * amag + 1e-6f && fabsf(f.aB - V->aB) < 0.01f * amag + 1e-6f, "vec %d amplitudes", i);
            float da = fabsf(fmodf(pf_axis_deg(f.aA, f.aB) - V->axis + 270.0f, 180.0f) - 90.0f); CHECK(da < 0.2f, "vec %d axis %g", i, da);
            CHECK(pf_classify(f.tau) == V->cls, "vec %d class %d vs %d", i, pf_classify(f.tau), V->cls);
        }
        CHECK(fabsf(snr / V->snr - 1.0f) < 0.01f || (snr < 4.0f && V->snr < 4.0f), "vec %d snr %g vs %g", i, snr, V->snr);
    }
    /* 2 descriptor round trip and CRC: every field survives within its quantisation; a flipped bit is rejected */
    pf_desc_t d = {7, 2, 1, 1, 1, 3, 18e-6f, 60.0f, 300.0f}, e; uint8_t b[PF_DESC_BYTES]; pf_desc_pack(&d, b);
    CHECK(pf_desc_unpack(b, &e) == 1, "desc unpack");
    CHECK(e.seq == 7 && e.mode == 2 && e.centred == 1 && e.side_valid == 1 && e.cls == 1 && e.depth == 3, "desc fields");
    CHECK(fabsf(e.tau / d.tau - 1.0f) < 0.02f && fabsf(e.snr / d.snr - 1.0f) < 0.02f && fabsf(e.bearing - d.bearing) < 0.01f, "desc quantisation %g %g %g", e.tau, e.snr, e.bearing);
    b[4] ^= 0x10; CHECK(pf_desc_unpack(b, &e) == 0, "desc CRC must reject a flipped bit");
    /* 3 LED renderer: below threshold all dark; a target lights 3 pixels in its ring; 12 full-strength targets capped at 0.35 A */
    pf_led_t fr[PF_NLED]; pf_desc_t q = d; q.snr = 3.0f; pf_led_render(&q, 1, fr); int lit = 0; for (int k = 0; k < PF_NLED; k++) lit += fr[k].code > 0; CHECK(lit == 0, "silent below threshold");
    q.snr = 60.0f; pf_led_render(&q, 1, fr); lit = 0; for (int k = 0; k < PF_NLED; k++) lit += fr[k].code > 0; CHECK(lit == 3, "3 pixels lit, got %d", lit);
    pf_led_render(&q, 0, fr); lit = 0; for (int k = 0; k < PF_NLED; k++) lit += fr[k].code > 0; CHECK(lit == 0, "dark during sweep");
    pf_led_t all[PF_NLED]; memset(all, 0, sizeof all);
    for (int dep = 1; dep <= 4; dep++) for (int a = 0; a < 3; a++) { pf_desc_t t = {0, 1, 0, 1, 3, (uint8_t)dep, 300e-6f, 1000.0f, 120.0f * a}; pf_led_t one[PF_NLED]; pf_led_render(&t, 1, one);
        for (int k = 0; k < PF_NLED; k++) if (one[k].code > all[k].code) all[k] = one[k]; }
    pf_led_cap(all); float I = pf_led_current_a(all); printf("worst LED frame %.3f A\n", I); CHECK(I <= PF_I_CAP_A + 1e-6f, "LED cap %g A", I);
    /* 4 tracker: a synthetic pass (axis turning 180 deg one way, RSS peak - null - peak) with positive yaw gives a side and one centre event */
    pf_track_t t; pf_track_reset(&t); int centred = 0;
    for (int k = 0; k <= 80; k++) {
        float u = (k - 40) / 20.0f, ax = 90.0f - 80.0f * tanhf(u * 1.5f), r = fabsf(u) * expf(-u * u / 2.0f) + 0.02f;   /* off-centre pass: the axis turns, RSS dips at k = 40 */
        float th = (ax - 45.0f) * 2.0f / 57.29577951f; pf_track_step(&t, r * cosf(th), r * sinf(th), 50.0f, 40.0f); centred += t.centred;
    }
    CHECK(t.side != 0, "tracker side resolved"); CHECK(centred == 1, "one centre event, got %d", centred);
    printf("checks %d, fails %d\n", checks, fails); return fails ? 1 : 0;
}
