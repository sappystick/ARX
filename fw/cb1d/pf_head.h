#pragma once
#include "pf_dsp.h"
typedef struct {
    float accA[PF_NG], accB[PF_NG]; int nacc; int prf; int out_mode; int led_was_lit; uint8_t seq; uint8_t depth;
    float sig0; pf_ground_t ground; pf_track_t track; int acquire;   /* frames left in the power-up ground acquisition */
    float yaw_dps; int yaw_ok;                                       /* last yaw rate from the AU1 reply (the gyro moved to AU1, 2026-10-28) */
} pf_head_t;
void pf_head_init(pf_head_t *h, int prf_mode);
void pf_head_pulse(pf_head_t *h, const float gA[PF_NG], const float gB[PF_NG]);
int pf_head_frame_ready(const pf_head_t *h, int n_avg);
int pf_head_process(pf_head_t *h, float yaw_dps, pf_desc_t *d);
void pf_head_idle(pf_head_t *h, const pf_desc_t *d, int in_sweep);
