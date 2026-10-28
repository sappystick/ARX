// tests/regress.py: replays the Python golden cases of src/sim/system_live.py (data/results/system_live.json) through the page's model (src/render/system_live.js)
// usage: node tests/system_live_golden.js src/render/system_live.js data/results/system_live.json  -> one JSON line: worst relative deviation per output, percent
const S = require(process.argv[2]); const M = require(process.argv[3]);
const keys = ["ton_us","Q_uC","P_tx_W","Vds_peak","vc_peak","t_zero_us","t_quiet_us","P_RCL_W","P_damp_W","i_diode_pk","P_total_W","hours"];
let worst = {}; const t0 = Date.now();
for (const g of M.golden) {
  const tx = S.txPoint(M, g.V, g.mode, g.cap, g.L_scale, g.R_scale); const pw = S.power(M, g.V, g.mode, tx.P_tx_W); const r = Object.assign({}, tx, pw);
  for (const k of keys) { const e = Math.abs(r[k] - g[k]) / Math.max(Math.abs(g[k]), 1e-9) * 100; if (!(worst[k] >= e)) worst[k] = e; }
}
console.log(JSON.stringify({ ms_per_case: (Date.now() - t0) / M.golden.length, worst_pct: Object.fromEntries(Object.entries(worst).map(([k, v]) => [k, +v.toFixed(3)])) }));
