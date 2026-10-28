// System model for the interactive viewer: the JavaScript twin of src/sim/system_live.py (MODELED). Same equations, same inputs (the page embeds
// system_live.json as M). tests/regress.py runs this file under node against the Python golden cases. Works in a browser (window.SystemLive) and in node (module.exports).
(function (root) {
  "use strict";
  // ---- on-time: series R-L fed from the bulk bank (capacitor sags by q / C); RK4, crossing interpolated (python: solve_ivp with an event)
  function tonLoop(M, I, V, Rs, Ls) {
    const L = M.tx.L * Ls, R = M.tx.R_loop * Rs, C = M.tx.C_bulk, h = 2e-9;
    let t = 0, i = 0, q = 0;
    const f = (i, q) => [(V - q / C - R * i) / L, i];
    while (t < 200e-6) {
      const k1 = f(i, q), k2 = f(i + h / 2 * k1[0], q + h / 2 * k1[1]), k3 = f(i + h / 2 * k2[0], q + h / 2 * k2[1]), k4 = f(i + h * k3[0], q + h * k3[1]);
      const i2 = i + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]), q2 = q + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]);
      if (i2 >= I) { const a = (I - i) / (i2 - i); return { ton: t + a * h, Q: q + a * (q2 - q) }; }
      i = i2; q = q2; t += h;
    }
    return { ton: NaN, Q: NaN };
  }
  // ---- turn-off: coil -> snubber node (Cn, Rd) -> clamp diode -> clamp capacitor CL || RCL (python: pulse(), Radau). Stiff while the diode conducts
  // (Ron Cn = 25 ps), so BDF2 with Newton on the three states; 2 ns steps, the metrics read on a 10 ns grid as the python t_eval.
  function pulse(M, I0, CL, derate, Vbus, f, ton, Ls, keepWave) {
    const p = M.tx, L = p.L * Ls, T = 1 / f, h = 2e-9, N = 30000, every = 5;
    const Cf = derate ? (v => CL / (1 + (Math.abs(v) / p.Vk) ** 2)) : (() => CL);
    let vc0 = 0, out = null;
    for (let it = 0; it < 10; it++) {
      let y = [I0, 0, vc0], yp = null; const S = [[0, I0, 0, vc0]];
      for (let n = 1; n <= N; n++) {
        const a = yp ? [4 / 3, -1 / 3, 2 / 3] : [1, 0, 1];          // BDF2 coefficients (BE on the first step)
        const base = yp ? [a[0] * y[0] + a[1] * yp[0], a[0] * y[1] + a[1] * yp[1], a[0] * y[2] + a[1] * yp[2]] : y.slice();
        let z = y.slice();
        for (let k = 0; k < 30; k++) {
          const [i, vd, vc] = z, on = vd - vc - p.Vf > 0, iD = on ? (vd - vc - p.Vf) / p.Ron : 0, C = Cf(vc);
          const F = [(-vd - p.Rc * i) / L, (i - vd / p.Rd - iD) / p.Cn, (iD - vc / p.RCL) / C];
          const g = [z[0] - base[0] - a[2] * h * F[0], z[1] - base[1] - a[2] * h * F[1], z[2] - base[2] - a[2] * h * F[2]];
          const dD = on ? 1 / p.Ron : 0, dCdv = derate ? -CL * 2 * vc * Math.sign(1) / (p.Vk * p.Vk) / (1 + (Math.abs(vc) / p.Vk) ** 2) ** 2 : 0;
          const J = [[-p.Rc / L, -1 / L, 0], [1 / p.Cn, (-1 / p.Rd - dD) / p.Cn, dD / p.Cn],
                     [0, dD / C, (-dD - 1 / p.RCL) / C - (iD - vc / p.RCL) / (C * C) * dCdv]];
          const A = J.map((r, ri) => r.map((v, ci) => (ri === ci ? 1 : 0) - a[2] * h * v));
          const d = solve3(A, g); z = [z[0] - d[0], z[1] - d[1], z[2] - d[2]];
          if (Math.abs(d[0]) < 1e-9 && Math.abs(d[1]) < 1e-6 && Math.abs(d[2]) < 1e-6) break;
        }
        yp = y; y = z;
        if (n % every === 0) S.push([n * h, y[0], y[1], y[2]]);
      }
      const rest = T - 60e-6 - ton, vcEnd = S[S.length - 1][3] * Math.exp(-rest / (p.RCL * CL));
      out = { S, rest };
      if (Math.abs(vcEnd - vc0) < 0.5) break;
      vc0 = vcEnd;
    }
    const S = out.S, dt = S[1][0] - S[0][0];
    let vdMax = -1e9, vcMax = -1e9, tz = NaN, iDmax = 0, Er = 0, Ed = 0, lastBad = -1;
    for (let k = 0; k < S.length; k++) {
      const [t, i, vd, vc] = S[k];
      vdMax = Math.max(vdMax, vd); vcMax = Math.max(vcMax, vc); iDmax = Math.max(iDmax, Math.max(0, vd - vc - p.Vf) / p.Ron);
      if (isNaN(tz) && i <= 0) tz = t;
      if (Math.abs(vd) > 1 || Math.abs(i) > 2e-3) lastBad = k;
      Er += vc * vc / p.RCL * dt; Ed += vd * vd / p.Rd * dt;
    }
    const vcl = S[S.length - 1][3]; Er += vcl * vcl / p.RCL * (p.RCL * CL / 2) * (1 - Math.exp(-2 * out.rest / (p.RCL * CL)));
    const r = { Vds_peak: vdMax + Vbus, vc_peak: vcMax, t_zero_us: tz * 1e6, t_quiet_us: lastBad >= 0 && lastBad + 1 < S.length ? S[lastBad + 1][0] * 1e6 : 0,
                P_RCL_W: Er * f, P_damp_W: Ed * f, i_diode_pk: iDmax };
    if (keepWave) r.wave = S.filter((_, k) => k % 4 === 0).map(s => [s[0] * 1e6, s[1], s[2] + Vbus, s[3]]);
    return r;
  }
  function solve3(A, b) {
    const m = A.map((r, i) => [...r, b[i]]);
    for (let c = 0; c < 3; c++) {
      let piv = c; for (let r = c + 1; r < 3; r++) if (Math.abs(m[r][c]) > Math.abs(m[piv][c])) piv = r;
      [m[c], m[piv]] = [m[piv], m[c]];
      for (let r = c + 1; r < 3; r++) { const k = m[r][c] / m[c][c]; for (let j = c; j < 4; j++) m[r][j] -= k * m[c][j]; }
    }
    const x = [0, 0, 0];
    for (let r = 2; r >= 0; r--) { let s = m[r][3]; for (let j = r + 1; j < 3; j++) s -= m[r][j] * x[j]; x[r] = s / m[r][r]; }
    return x;
  }
  // current ramp during the on-time (for the waveform plot): same circuit as tonLoop, sampled every 0.25 us
  function rampWave(M, V, mode, Ls = 1, Rs = 1) {
    const md = M.modes[mode], L = M.tx.L * Ls, R = M.tx.R_loop * Rs, C = M.tx.C_bulk, h = 5e-9, out = [];
    let t = 0, i = 0, q = 0;
    const f = (i, q) => [(V - q / C - R * i) / L, i];
    while (i < md.I && t < 200e-6) {
      if (Math.round(t / h) % 50 === 0) out.push([t * 1e6, i, V - q / C]);
      const k1 = f(i, q), k2 = f(i + h / 2 * k1[0], q + h / 2 * k1[1]), k3 = f(i + h / 2 * k2[0], q + h / 2 * k2[1]), k4 = f(i + h * k3[0], q + h * k3[1]);
      i += h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]); q += h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]); t += h;
    }
    out.push([t * 1e6, md.I, V - q / C]); return out;
  }
  // pack voltage over a discharge, OCV taken as linear in delivered energy between V_max and V_min (ASSUMED; no P30B discharge curve is in the repo)
  function discharge(M, mode, Ls, Rs, ledA, m12W, n = 24) {
    const Vs = [], E = M.pack.Wh; let hrs = 0; const pts = [[0, M.pack.V_max]];
    for (let k = 0; k < n; k++) {
      const V = M.pack.V_max - (k + 0.5) / n * (M.pack.V_max - M.pack.V_min);
      const P = power(M, V, mode, txSupply(M, V, mode, Ls, Rs).P_tx_W, ledA, m12W).P_total_W;
      hrs += E / n / P; pts.push([hrs, M.pack.V_max - (k + 1) / n * (M.pack.V_max - M.pack.V_min), P]);
    }
    return { hours: hrs, pts };
  }
  function txSupply(M, V, mode, Ls = 1, Rs = 1) {
    const md = M.modes[mode], r = tonLoop(M, md.I, V, Rs, Ls); return { ton: r.ton, Q: r.Q, P_tx_W: V * r.Q * md.f };
  }
  function txPoint(M, V, mode, cap, Ls = 1, Rs = 1, keepWave = false) {
    const md = M.modes[mode], c = M.caps[cap], s = txSupply(M, V, mode, Ls, Rs);
    const pl = pulse(M, md.I, c.CL, c.derate, V, md.f, s.ton, Ls, keepWave);
    return Object.assign({ ton_us: s.ton * 1e6, Q_uC: s.Q * 1e6, droop_pct: s.Q / M.tx.C_bulk / V * 100, E_mJ: V * s.Q * 1e3, P_tx_W: s.P_tx_W,
                           i_rms: md.I * Math.sqrt(s.ton * md.f / 3) }, pl);
  }
  function power(M, V, mode, P_tx_W, ledA, m12W) {
    ledA = ledA ?? M.i5.led_cap; m12W = m12W ?? 0.10;
    const f = M.modes[mode].f, i5 = ledA + (M.i5.led_static || 0) + M.i5.logic + M.i5.ams_in + M.i5.analog_5va;
    const P5 = 5.0 * i5 / M.eta, P12 = (M.gate.Qg * M.gate.Vg * f + m12W) / M.eta, P = P_tx_W + P5 + P12;
    return { I5_A: i5, P5_W: P5, P12_W: P12, P_total_W: P, I_batt_A: P / V, hours: M.pack.Wh / P };
  }
  // ---- wiring runs: current per conductor in the chosen operating point; drop and loss on the modeled resistance (two-way for a supply pair is the sum of both rows)
  function wiring(M, tx, pw, mode) {
    const md = M.modes[mode];
    return M.wires.map(w => {
      let I = 0, kind = "signal";
      if (w.load === "battery") { I = pw.I_batt_A; kind = "average"; }
      else if (w.load === "coil") { I = tx.i_rms; kind = "rms"; }
      else if (w.load === "layer") { I = tx.i_rms / 6; kind = "rms"; }
      else if (w.load === "led5") { I = pw.I5_A - M.i5.logic - M.i5.ams_in - M.i5.analog_5va; kind = "average"; }       // LED current incl. the 66 mA static
      const R = w.R_ohm;
      return Object.assign({}, w, { I_A: I, kind, drop_mV: R == null ? null : I * R * 1e3, loss_mW: R == null ? null : I * I * R * 1e3,
                                    I_peak_A: w.load === "coil" ? md.I : w.load === "layer" ? md.I / 6 : I });
    });
  }
  function vault(M, P_W, ambient) { return ambient + M.thermal.K_per_W * P_W; }
  function checks(M, tx, pw, ambient, ledA, vaultW) {
    const L = M.limits, T = vault(M, vaultW, ambient), rows = [];
    const add = (what, v, lim, unit, hi = true, note = "") => rows.push({ what, value: v, limit: lim, unit, margin_pct: hi ? (1 - v / lim) * 100 : (v / lim - 1) * 100, ok: hi ? v <= lim : v >= lim, note });
    add("FET Vds peak", tx.Vds_peak, L.Vds, "V", true, "IPB65R095C7 650 V; 20 % margin required (system_budget)");
    add("Clamp node peak vs 630 V part rule", tx.vc_peak, L.clamp_rule, "V");
    add("ES3J reverse voltage", tx.vc_peak, L.diode_VRRM, "V", true, "VRRM 600 V");
    add("RCL1 power", tx.P_RCL_W, L.RCL_W, "W", true, "5 kohm 10 W");
    add("Bulk droop per pulse", tx.droop_pct, L.droop_pct, "%", true, "5 % of VBUS budget");
    add("+5V rail (M5 1.5 A)", pw.I5_A, L.rail5_A, "A");
    add("Power cord AWG20 average", pw.I_batt_A, L.cord_A, "A", true, "5 A enclosed (ASSUMPTIONS 27)");
    add("Vault hot spot", T, L.vault_C, "C", true, "linear fit of sim_thermal; PETG Tg about 80 C");
    rows.forEach(r => r.need = r.what === "FET Vds peak" ? r.margin_pct >= 20 : r.ok);
    return { rows, T_vault: T };
  }
  const api = { tonLoop, pulse, rampWave, discharge, txSupply, txPoint, power, wiring, vault, checks };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.SystemLive = api;
})(typeof window !== "undefined" ? window : globalThis);
