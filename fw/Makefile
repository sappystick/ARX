# PHI-FOLD 233 firmware: host build and tests (the target builds need the Pico SDK for CB1D and the TI MSPM0 SDK for AU1: see README.md).
# GEN = folder with the generated headers (pf233_dsp_tables.h, pf233_dsp_vectors.h, pf233_timing.h, pf233_output.h): work/kit_v23 after the pipeline,
# or data/results in a clean clone.
GEN ?= ../work/kit_v23
OUT ?= build
CC ?= gcc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Werror
INC = -Idsp -Iau1 -Icb1d -Icommon -I$(GEN)
CORE = dsp/pf_dsp.c
.PHONY: test clean
test: $(OUT)/test_dsp $(OUT)/test_voice $(OUT)/test_system
	$(OUT)/test_dsp && $(OUT)/test_voice && $(OUT)/test_system
$(OUT):
	mkdir -p $(OUT)
$(OUT)/test_dsp: $(CORE) tests/test_dsp.c | $(OUT)
	$(CC) $(CFLAGS) $(INC) $^ -lm -o $@
$(OUT)/test_voice: $(CORE) au1/pf_voice.c tests/test_voice.c | $(OUT)
	$(CC) $(CFLAGS) $(INC) $^ -lm -o $@
$(OUT)/test_system: $(CORE) au1/pf_voice.c au1/pf_audio.c cb1d/pf_head.c tests/test_system.c | $(OUT)
	$(CC) $(CFLAGS) $(INC) $^ -lm -o $@
clean:
	rm -f $(OUT)/test_dsp $(OUT)/test_voice $(OUT)/test_system
