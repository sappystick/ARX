"""SB1R-Q coil damping with the real AB1T input network (supersedes sbq_damp.py, which modeled a bare coil || Rd).
Network per channel (AB1A netlist, relabelled AB1T-A): coil (L, Rc, Cself) between J1.IN and J1.VCM; optional damping resistor Rd across the
coil terminals; RS 100 ohm to the amplifier input node IN; BAV199 clamp to the rails, 74LVC1G66 blank switch IN -> VCM, OPA2211 (+) input.
While BLANK is high the switch holds IN at VCM through Ron, so the coil is terminated by RS + Ron. The firmware releases BLANK at t_b;
from then on IN sees only the input capacitance Cin. First clean gate = max(t_b, last time |v_IN| > 100 nV).
Noise after release: Rc, Rd, RS thermal noise + OPA2211 voltage noise, shaped by the network and the 362 kHz anti-alias pole (RAAF 200 ohm,
CAAF 2.2 nF), integrated through a boxcar gate of width Tg = 0.5 tc (the gate rule of sim_head1.py).
Unverified part values (docs/ASSUMPTIONS.md 21): Ron 8 ohm, Cin 15 pF (BAV199 + switch off-capacitance + op-amp input), BAV199 off for |v| < 0.5 V."""
import numpy as np, json, math
import os
from scipy.integrate import solve_ivp
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
src = open('sim_head1.py').read().split("# ======================= S2")[0]; ns = {}; exec(src, ns); wf = ns["wf"]
t, i, vd, vc = wf["100 nF C0G/film"]; g = np.gradient(i, t); g = g / np.max(np.abs(g))
L, Rc, RS, RON, CIN, EN_AMP, kT = 176e-6, 10.4, 100.0, 8.0, 15e-12, 1.1e-9, 1.380649e-23 * 300.0
THR, TEND, F_AA = 1e-7, 60e-6, 1 / (2 * math.pi * 200.0 * 2.2e-9)

def first_clean(e_pk, Rd, Cs, t_b, Cin=CIN, Ron=RON):
    """state: coil current iL, coil-terminal voltage vc (across Cself), input node vin (across Cin); all relative to VCM"""
    e = lambda tt: e_pk * np.interp(tt, t, g, left=0, right=0)
    def f(tt, y):
        il, v, vin = y; isw = vin / Ron if tt < t_b else 0.0
        return [(e(tt) - Rc * il - v) / L, (il - (v / Rd if Rd else 0.0) - (v - vin) / RS) / Cs, ((v - vin) / RS - isw) / Cin]
    tt = np.arange(0, TEND, 5e-9); s = solve_ivp(f, (0, TEND), [0, 0, 0], t_eval=tt, method="Radau", rtol=1e-8, atol=[1e-12, 1e-12, 1e-12], max_step=2e-8)
    vin = s.y[2]; after = s.t >= t_b; bad = np.where(after & (np.abs(vin) > THR))[0]
    return float(max(t_b, s.t[bad[-1]] if len(bad) else 0.0) * 1e6), float(np.max(np.abs(vin[after])) if after.any() else 0.0)

def _fc(a):
    return first_clean(*a)

def pmap(fn, items):
    """order-preserving parallel map over the cores (ARX_INNER_JOBS, default all); serial if 1"""
    n = int(os.environ.get("ARX_INNER_JOBS", os.cpu_count() or 1))
    if n <= 1 or len(items) < 2: return [fn(x) for x in items]
    import multiprocessing as mp
    with mp.get_context("fork").Pool(min(n, len(items))) as pool: return pool.map(fn, items, chunksize=1)

def gate_noise(Rd, Cs, tc, Cin=CIN):
    """equivalent white density (V/rtHz) at the amplifier input for a boxcar gate of width 0.5 tc, switch open"""
    f = np.logspace(2, 8, 6000); w = 2 * np.pi * f; jw = 1j * w; Tg = 0.5 * tc
    Zcoil = Rc + jw * L; Ycs = jw * Cs; Ycin = jw * Cin; Yd = (1 / Rd) if Rd else 0.0
    Zin = RS + 1 / Ycin                                                   # RS in series with Cin, seen from the coil terminals
    Ys = 1 / Zcoil + Ycs + Yd; Zs = 1 / Ys                                 # source impedance at the coil terminals (excluding RS branch)
    H = (1 / Ycin) / Zin                                                   # coil-terminal voltage -> input node
    Ztot = 1 / (Ys + 1 / Zin)                                              # impedance at the coil terminals with the RS branch
    v_rc = np.sqrt(4 * kT * Rc) * np.abs(Ztot / Zcoil) * np.abs(H)        # Rc noise voltage in series with L -> current into the terminal node
    v_rd = (np.sqrt(4 * kT / Rd) * np.abs(Ztot) * np.abs(H)) if Rd else 0.0 * f
    v_rs = np.sqrt(4 * kT * RS) * np.abs((1 / Ycin) / (Zs + Zin))
    S = v_rc ** 2 + v_rd ** 2 + v_rs ** 2 + EN_AMP ** 2
    Hg = np.sinc(f * Tg) ** 2 / (1 + (f / F_AA) ** 2)                    # boxcar gate x anti-alias pole
    var = np.trapezoid(S * Hg, f); return float(math.sqrt(var * 2 * Tg)), dict(Rc=float(np.trapezoid(v_rc ** 2 * Hg, f) * 2 * Tg), Rd=float(np.trapezoid(v_rd ** 2 * Hg, f) * 2 * Tg) if Rd else 0.0, RS=float(np.trapezoid(v_rs ** 2 * Hg, f) * 2 * Tg), amp=float(np.trapezoid(EN_AMP ** 2 * Hg, f) * 2 * Tg))

def plot(out):
    """one figure: first clean gate vs Rd (worst real leak, 100 pF) for each blank release, and the gated noise vs Rd"""
    fc, nz = out["first_clean_gate_us"], out["gate_noise_nV_rtHz"]; worst = [k for k in fc if k.startswith("worst modeled") and "Cself 100 pF" in k]
    xs = [x for x in next(iter(fc.values())) if x != "no Rd"]; fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for k in worst: ax[0].plot(range(len(xs)), [fc[k][x] for x in xs], "o-", label=k.split(", ")[-1])
    ax[0].set_xticks(range(len(xs))); ax[0].set_xticklabels(xs); ax[0].set_ylabel("first clean gate (us)"); ax[0].set_ylim(4, 18)
    ax[0].set_title(f"{worst[0].split(',')[0]}, Cself 100 pF (modeled). No Rd: rings > 60 us", fontsize=10); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    for k in [k for k in nz if k.startswith("Cself 100 pF")]: ax[1].plot(range(len(xs) + 1), [nz[k][x] for x in ["no Rd"] + xs], "o-", label=k.split(", ")[-1])
    ax[1].set_xticks(range(len(xs) + 1)); ax[1].set_xticklabels(["no Rd"] + xs); ax[1].set_ylabel("equivalent input noise (nV/rtHz)"); ax[1].set_title("Gated input noise, Cself 100 pF (modeled)", fontsize=10); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("kit_v22/SBQ_DAMPING2.png", dpi=90)

if __name__ == "__main__":
    J = json.load(open("kit_v22/sbq_sim.json")); worst = max(v["peak_V"] for bd in J["leak"].values() for k, v in bd.items() if "lobes only" not in k)   # real board cases only (sbq_damp.py also took the lobes-only diagnostic rows, 187 mV)
    LEAKS = (("A aligned 0.01 mV", 1e-5), ("1 mV", 1e-3), (f"worst modeled {worst*1e3:.0f} mV", worst))
    RDS = (None, 2200, 1000, 680, 470, 330); TBS = (0.0, 4e-6, 5e-6, 6e-6, 7e-6); CSS = (50e-12, 100e-12, 200e-12)
    out = dict(assumptions=dict(L_uH=176, Rc_ohm=Rc, RS_ohm=RS, Ron_ohm_unverified=RON, Cin_pF_unverified=CIN * 1e12, en_amp_nV=EN_AMP * 1e9, threshold_nV=THR * 1e9, tx_case="100 nF C0G/film, 20 A"), first_clean_gate_us={}, peak_after_release_uV={})
    cases = [(epk, Rd, Cs, tb) for lab, epk in LEAKS for Cs in CSS for tb in TBS for Rd in RDS]          # 270 independent stiff solves: spread over the cores (same results, same order)
    done = iter(pmap(_fc, cases))
    for lab, epk in LEAKS:
        for Cs in CSS:
            for tb in TBS:
                key = f"{lab}, Cself {int(Cs*1e12)} pF, blank release {tb*1e6:.0f} us"; row = {}; pk = {}
                for Rd in RDS:
                    tf, p = next(done); nm = "no Rd" if Rd is None else f"Rd {Rd}"; row[nm] = round(tf, 2); pk[nm] = round(p * 1e6, 3)
                out["first_clean_gate_us"][key] = row; out["peak_after_release_uV"][key] = pk; print(key, row)
    nz = {}
    for Cs in CSS:
        for tc in (6e-6, 10e-6, 20e-6, 40e-6):
            row = {}
            for Rd in RDS: d, parts = gate_noise(Rd, Cs, tc); row["no Rd" if Rd is None else f"Rd {Rd}"] = round(d * 1e9, 3)
            nz[f"Cself {int(Cs*1e12)} pF, gate at {tc*1e6:.0f} us"] = row
    out["gate_noise_nV_rtHz"] = nz; print("gate noise", json.dumps(nz, indent=0))
    # sensitivity: input capacitance and switch resistance (worst leak, 100 pF, release 5 us, Rd 470 and none)
    sens = {}; scases = [(worst, Rd, 100e-12, 5e-6, Cin, Ron) for Cin in (5e-12, 15e-12, 30e-12) for Ron in (4.0, 8.0, 20.0) for Rd in (None, 470)]; sdone = iter(pmap(_fc, scases))
    for Cin in (5e-12, 15e-12, 30e-12):
        for Ron in (4.0, 8.0, 20.0):
            sens[f"Cin {Cin*1e12:.0f} pF, Ron {Ron:.0f} ohm"] = {nm: round(next(sdone)[0], 2) for nm, Rd in (("no Rd", None), ("Rd 470", 470))}
    out["sensitivity_worst_leak_100pF_release_5us"] = sens; print("sensitivity", sens)
    out["critical_damping_ohm"] = {f"{int(Cs*1e12)} pF": round(0.5 * math.sqrt(L / Cs)) for Cs in CSS}
    json.dump(out, open("kit_v22/sbq_damping2.json", "w"), indent=1)
    plot(out); print("critical", out["critical_damping_ohm"])
