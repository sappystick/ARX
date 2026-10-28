/* Hardware abstraction for the PHI-FOLD 233 firmware. The target builds implement it on the Pico SDK (CB1D, RP2350: PIO for the gated ADC frames,
 * the SK9822 LED stream and the half-duplex link) and on the TI MSPM0 SDK / DriverLib (AU1: UART0, DAC12, TIMG12 PWM, GPIO, I2C0 for the gyro);
 * neither SDK is installed in this repository's container, so only the host stubs (fw/tests/hal_host.c) are built and run here. Every call that touches
 * the coil, the receive chain or the cord is issued by the scheduler only in the slot fw_timeline.py / output_modes.py allow. */
#pragma once
#include <stdint.h>
/* ---- CB1D (head) ---- */
void hal_tx_fire(uint32_t ton_ns);                                   /* TX1_IN high for ton, then off (PB1R) */
void hal_adc_gates(float gA[9], float gB[9]);                        /* gate means of QUAD-A / QUAD-B for the pulse just fired (PIO + AD7389-4) */
float hal_gyro_yaw_dps(void);                                        /* AU1 only: BMI270 / LSM6DSO z rate over I2C0 on PA0 / PA1 (address 0x69 / 0x6B: SDO high) */
int hal_trigger(void);                                               /* TRIG_IN high = pressed (boost) */
void hal_led_frame(const uint8_t *frame, int nbytes);                /* SK9822 frame on LED_IN / LED_CLK (PIO, 8 MHz) */
void hal_link_send(const uint8_t *b, int n);                         /* AUD_LINK, 1 Mbaud, then release the line */
int hal_link_reply(uint8_t *b, int n, uint32_t timeout_us);          /* bytes received from AU1 within the timeout */
void hal_wait_period_end(uint32_t period_ns);                        /* sleep to the next TX period boundary */
/* ---- AU1 (audio) ---- */
int au_link_recv(uint8_t *b, int n, uint32_t timeout_us);
void au_link_send(const uint8_t *b, int n);
int au_selector(void);                                               /* 0 AUDIO_ONLY, 1 LED_ONLY, 2 COMBINED (JSEL: SEL1..SEL3 active low) */
int au_headphones(void);                                             /* plug-detect */
void au_amp_enable(int speaker, int headphones);                     /* TPA2005D1 SHUTDOWN, TPA6132A2 EN */
void au_audio_out(const int16_t *left, const int16_t *right, int n); /* left -> DAC12 (PA15), right -> TIMG12 PWM (PA14) */
