/* AU1 audio firmware main step (portable over pf_hal.h): receive a descriptor, answer with the selector state, drive the voice and the amplifiers.
 * Mode rules (output_modes.py): AUDIO_ONLY and COMBINED sound the voice; LED_ONLY keeps both amplifiers shut down (no audio). MODELED: host-tested only. */
#include "pf_hal.h"
#include "pf_voice.h"
#include "pf_audio.h"
void pf_audio_init(pf_audio_t *a) { pf_voice_init(&a->voice); a->mode = 2; a->good = a->bad = 0; }
/* one TX period: link, reply, voice parameters; then render n samples (n = FS x period) */
void pf_audio_step(pf_audio_t *a, int n_samples, int16_t *L, int16_t *R) {
    uint8_t b[PF_DESC_BYTES]; pf_desc_t d;
    if (au_link_recv(b, PF_DESC_BYTES, 200) == PF_DESC_BYTES && pf_desc_unpack(b, &d)) {
        a->good++; a->mode = au_selector();
        uint8_t r[2] = {(uint8_t)(a->mode & 3), 0}; r[1] = pf_crc8(r, 1); au_link_send(r, 2);
        if (a->mode == 1) d.snr = 0.0f;                                                          /* LED_ONLY: silent */
        pf_voice_set(&a->voice, &d);
    } else a->bad++;
    int hp = au_headphones(); au_amp_enable(a->mode != 1 && !hp, a->mode != 1 && hp);
    pf_voice_render(&a->voice, L, R, n_samples, !hp); au_audio_out(L, R, n_samples);
}
