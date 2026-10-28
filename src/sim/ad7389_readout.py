#!/usr/bin/env python3
"""B6: Python model of the CB1D firmware readout of the AD7389-4 on AB1A / AB1B (2-wire mode, SDI tied low). MODELED from the datasheet only; no hardware.

Datasheet facts used (AD7389-4 Rev. 0, data/seed/footprints/AD7389-4_Rev0_datasheet_CP-24-25.pdf):
- CS falling edge samples all four ADCs and starts the conversion; one-cycle readback latency: a frame returns the PREVIOUS conversion (p. 21-22, Fig. 37).
- 2-wire mode = SDO bits 0b00 in Configuration 2, the reset default: SDOA carries ADC A then ADC C, SDOB carries ADC B then ADC D; 32 SCLK per frame
  without resolution boost or CRC (Table 13); MSB first, out on the CS falling edge and the SCLK rising edges (p. 21).
- Output coding twos complement, LSB = 2 x VREF / 2^16 with VREF 2.5 V (p. 4, 15).
- SDI word: D15 WR, D14-D12 REGADDR; WR = 0 with REGADDR 0x0 / 0x6 / 0x7 is ignored and the next access reads conversion results (Table 17, p. 26).
  SDI tied to GND clocks in 0x0000 every frame: a NOP. No register can be written, so no software reset and no mode change: the reset defaults stay.
- tPOWERUP: first conversion allowed 5 ms after the supplies, settled within 1 % (internal reference) after 11 ms; register access after 5 ms (p. 5).
- Throughput 2 MSPS: tCONVERT 190 ns, tACQUIRE 310 ns (p. 3, 5).
Board mapping (afe_design.py): channel k drives ADC input pair A (k=1), B (k=2), C (k=3); SDOA -> J2 SDO1, SDOB -> J2 SDO2; SDO3 unused.
"""
import json, os, sys
VREF = 2.5; NBITS = 16; LSB = 2 * VREF / 2 ** NBITS
T_FIRST_S, T_SETTLED_S = 5e-3, 11e-3
FRAME_SCLK = 32
BOARD_CH = {"A": {"GX": "A", "GY": "B", "X8": "C"}, "B": {"Y8": "A", "MONO": "B"}}


def to_code(v):
    """differential input (AINx+ - AINx-, volts) -> 16-bit twos complement code, clipped to the range"""
    c = int(round(v / LSB)); return max(-2 ** (NBITS - 1), min(2 ** (NBITS - 1) - 1, c))


def code_to_bits(c): return [(c & 0xFFFF) >> (NBITS - 1 - i) & 1 for i in range(NBITS)]


def bits_to_code(b):
    u = 0
    for x in b: u = (u << 1) | x
    return u - (1 << NBITS) if u & (1 << (NBITS - 1)) else u


class AD7389:
    """chip model: call frame(t, inputs, sdi_word) once per CS low period"""
    def __init__(self): self.prev = None; self.sdo_mode = 0b00; self.writes = 0

    def frame(self, t, inputs, sdi_word=0x0000):
        wr, addr = sdi_word >> 15 & 1, sdi_word >> 12 & 0x7
        if wr and addr not in (0x0, 0x6, 0x7): self.writes += 1             # a register write (never happens with SDI tied low)
        out_prev = self.prev
        if t < T_FIRST_S: self.prev = None                                   # conversion not allowed yet: the next frame returns no valid data
        else: self.prev = dict(codes={k: to_code(inputs.get(k, 0.0)) for k in "ABCD"}, settled=t >= T_SETTLED_S)
        if out_prev is None: return dict(valid=False, sdoa=[0] * FRAME_SCLK, sdob=[0] * FRAME_SCLK)
        c = out_prev["codes"]
        return dict(valid=True, settled=out_prev["settled"], sdoa=code_to_bits(c["A"]) + code_to_bits(c["C"]), sdob=code_to_bits(c["B"]) + code_to_bits(c["D"]))


def decode(sdoa, sdob):
    """firmware side: 32 bits on each line -> {A, B, C, D} in volts"""
    assert len(sdoa) == len(sdob) == FRAME_SCLK
    return {"A": bits_to_code(sdoa[:16]) * LSB, "C": bits_to_code(sdoa[16:]) * LSB, "B": bits_to_code(sdob[:16]) * LSB, "D": bits_to_code(sdob[16:]) * LSB}


def read_board(board, frames):
    """frames: list of (t_s, {channel: volts}) -> list of decoded {channel: volts} or None (one per frame, with the one-frame latency)"""
    chip = AD7389(); out = []
    for t, ch in frames:
        ins = {BOARD_CH[board][k]: v for k, v in ch.items()}
        r = chip.frame(t, ins, 0x0000)
        if not r["valid"]: out.append(None); continue
        d = decode(r["sdoa"], r["sdob"]); out.append(dict(settled=r["settled"], **{k: d[BOARD_CH[board][k]] for k in BOARD_CH[board]}))
    return out, chip


def netlist_mapping(board):
    """the channel -> ADC pair and SDO -> J2 wiring as the board generator builds it (catches a generator change the model would not see)"""
    os.environ["BOARD"] = board; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pcb"))
    import importlib; D = importlib.import_module("afe_design"); importlib.reload(D)
    pair = {13: "A", 11: "B", 9: "C", 7: "D"}; m = {}
    for ch in D.CH:
        pins = [int(p) for r, p in D.NETS[f"ADCIN_{ch}"] if r == "UA1"]; m[ch] = pair.get(pins[0]) if pins else None
    sdo = {n: [(r, p) for r, p in D.NETS[n] if r in ("UA1", "J2")] for n in ("SDO1", "SDO2")}
    sdi = ("UA1", "21") in D.NETS["GND"]
    return m, sdo, sdi


def selftest():
    res = {}
    for b in "AB":
        m, sdo, sdi = netlist_mapping(b)
        res[f"AB1{b} channel -> ADC pair from afe_design"] = (m == BOARD_CH[b], str(m))
        res[f"AB1{b} SDO1 = UA1.19 (SDOA), SDO2 = UA1.20 (SDOB)"] = (("UA1", "19") in sdo["SDO1"] and ("UA1", "20") in sdo["SDO2"], str(sdo))
        res[f"AB1{b} SDI (UA1.21) tied to GND"] = (sdi, "")
        vals = {k: 0.37 * (i + 1) * (-1) ** i for i, k in enumerate(BOARD_CH[b])}
        frames = [(t * 1e-3, vals) for t in (1, 4, 6, 8, 12, 12.0005)]
        out, chip = read_board(b, frames)
        res[f"AB1{b} no data before 5 ms, one-frame latency"] = (out[0] is None and out[1] is None and out[2] is None and out[3] is not None, str([o is None for o in out]))
        res[f"AB1{b} 'settled' only from 11 ms"] = (out[3]["settled"] is False and out[5]["settled"] is True, "")
        err = max(abs(out[5][k] - v) for k, v in vals.items())
        res[f"AB1{b} round trip within 1/2 LSB"] = (err <= LSB / 2 + 1e-12, f"{err * 1e6:.2f} uV, LSB {LSB * 1e6:.2f} uV")
        res[f"AB1{b} SDI low never writes a register"] = (chip.writes == 0, "")
    full = read_board("A", [(12e-3, {"GX": 9.9, "GY": -9.9, "X8": 0.0})] * 2)[0][1]
    res["clip to +-VREF (codes 0x7FFF / 0x8000)"] = (abs(full["GX"] - (2 ** 15 - 1) * LSB) < 1e-12 and abs(full["GY"] + 2 ** 15 * LSB) < 1e-12, "")
    return res


if __name__ == "__main__":
    r = selftest(); bad = [k for k, (ok, _) in r.items() if not ok]
    for k, (ok, d) in r.items(): print("PASS" if ok else "FAIL", k, d)
    out = sys.argv[1] if len(sys.argv) > 1 else None
    if out: json.dump(dict(model="AD7389-4 2-wire readout, SDI low (MODELED)", lsb_uV=LSB * 1e6, t_first_ms=T_FIRST_S * 1e3, t_settled_ms=T_SETTLED_S * 1e3, frame_sclk=FRAME_SCLK,
                           mapping=BOARD_CH, checks={k: dict(ok=ok, detail=d) for k, (ok, d) in r.items()}, n_fail=len(bad)), open(out, "w"), indent=1)
    sys.exit(1 if bad else 0)
