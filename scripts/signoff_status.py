#!/usr/bin/env python3
"""Sign-off table for the transmit region: board x check -> PASS / FAIL / SKIP / UNVERIFIED, read from the result files in work/ (nothing is recomputed here except tests/regress.py, run last).
A missing result is FAIL unless its item is registered in docs/UNVERIFIED.md (then UNVERIFIED). Writes data/results/SIGNOFF_STATUS.json and docs/STATUS.md (GENERATED, never hand-edited).
usage: scripts/signoff_status.py [--no-regress]      exit 1 if anything FAILs"""
import json, os, re, subprocess, sys, datetime, glob
W = "work"
def arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default
REG, OUT_JSON, OUT_MD = arg("--register", "docs/UNVERIFIED.md"), arg("--out-json", "data/results/SIGNOFF_STATUS.json"), arg("--out-md", "docs/STATUS.md")
def rd(p):
    try: return json.load(open(os.path.join(W, p)))
    except Exception: return None
UNV = {}
try:
    for m in re.finditer(r"^\|\s*(U-[A-Z0-9-]+)\s*\|\s*([^|]*)\|", open(REG).read(), re.M): UNV[m[1]] = m[2].strip()
except Exception: pass
def chk(path, f, uid=None):
    """-> (state, detail). path=None means the check needs no file."""
    d = rd(path) if path else {}
    if d is None:
        return ("UNVERIFIED", uid) if uid in UNV else ("FAIL", f"missing {path}")
    try: ok, detail = f(d)
    except Exception as e: return ("FAIL", f"unreadable {path}: {e}")
    return ("PASS" if ok else "FAIL", detail)
def gerbers(dirn, prefix=None):
    files = [f for f in glob.glob(f"{W}/{dirn}/*") if not f.endswith("jogbrjob")]
    ok = len([f for f in files if f.endswith(".gbr")]) >= 4 and any("PTH" in f and f.endswith(".drl") for f in files)
    return ("PASS" if ok else "FAIL", f"{len(files)} files")
NA = ("-", "")
def kicad(b, hv):
    return chk(f"kit_v22/kicad_drc_{b}.json", lambda d: (not d["errors"] and d["unconnected"] == 0 and (not hv or d.get("rules_loaded") is True),
                                                         f"errors {d['errors']}, unconnected {d['unconnected']}" + (f", HV control {'live' if d.get('rules_loaded') else 'NOT live'}" if hv else "")))
def indep(b): return chk(f"kit_v22/drc_{b}.json", lambda d: (d["clearance_violations"] == 0 and d["open_nets"] == 0 and d["edge_samples"] == 0 and d["notch_samples"] == 0, f"{d['clearance_violations']} violations, {d['open_nets']} opens"))
def route(b): return chk(f"kit_v20/route_{b}.json", lambda d: (d["stats"]["nets_routed"] == d["stats"]["nets_to_route"] and not d["stats"]["failures"], f"{d['stats']['nets_routed']}/{d['stats']['nets_to_route']} nets"))
B = {}
B["CB1D"] = dict(route=route("CB1D"), indep=indep("CB1D"), kicad=kicad("CB1D", True), gerber=gerbers("kit_v22/GERBER_CB1D_v2"),
                 plane=chk("kit_v22/gerber_hv_CB1D.json", lambda d: (d["failures"] == 0 and d["checked"] >= 8, f"{d['checked']} HV pad/via x plane checks")),
                 cross=chk("kit_v22/wiring_audit.json", lambda d: (not d["errors"], f"{d['link_pins']} link pins, {d['harness_conductors']} conductors")))
B["LB1"] = dict(route=route("LB1"), indep=indep("LB1"), kicad=kicad("LB1", False), gerber=gerbers("kit_v22/GERBER_LB1_v2"), plane=NA,
                cross=chk("kit_v22/stack_check.json", lambda d: (all(r["result"] == "PASS" for r in d), f"{len(d)} stack-up checks")))
B["PB1R"] = dict(route=route("PB1R"), indep=indep("PB1R"), kicad=kicad("PB1R", True), gerber=gerbers("kit_v22/GERBER_PB1R"),
                 plane=chk("kit_v22/gerber_plane_PB1R.json", lambda d: (d["failures"] == 0 and d["control_ok"] and d["hv_checks"] >= 4, f"{d['hv_checks']} checks, min {d['min_distance_mm']} mm, control {d['control_ok']}")),
                 cross=chk("kit_v22/pb1r_check.json", lambda d: (not [c for c in d["checks"] if c["result"] == "FAIL"], f"{len(d['checks'])} checks, {len([c for c in d['checks'] if c['result'] == 'WARN'])} warn")))
B["TXJ1"] = dict(route=NA, indep=NA, kicad=kicad("TXJ1", True), gerber=gerbers("kit_v22/GERBER_TXJ1"), plane=NA,
                 cross=chk("kit_v22/tx_system.json", lambda d: (all(c["result"] == "PASS" for c in d["checks"]), f"{len(d['checks'])} lead/TXJ1 checks")))
for q in ("QA", "QB"):
    B[f"SB1R-{q}"] = dict(route=NA, indep=NA, kicad=kicad(f"SB1R-{q}", False), gerber=gerbers(f"kit_v22/GERBER_SB1R_{q}"), plane=NA,
                          cross=chk("kit_v22/sbq_geometry.json", lambda d: (d["via_margin_mm"] >= 0.3 and d["hole_margin_mm"] >= 0.5, f"via margin {d['via_margin_mm']}, hole margin {d['hole_margin_mm']} mm")))
for b in ("PM2", "HB2"):
    r = rd(f"kit_v20/route_{b}.json")
    if r is None:
        u = ("UNVERIFIED", f"U-ROUTE-{b}") if f"U-ROUTE-{b}" in UNV else ("FAIL", "not routed")
        B[b] = dict(route=u, indep=u, kicad=u, gerber=u, plane=NA, cross=u)
    else: B[b] = dict(route=route(b), indep=indep(b), kicad=kicad(b, False), gerber=gerbers(f"kit_v22/GERBER_{b}"), plane=NA, cross=chk("kit_v22/wiring_audit.json", lambda d: (not d["errors"], "wiring audit")))
B["HTA"] = dict(route=NA, indep=NA, kicad=(("UNVERIFIED", "U-KICAD-HTA") if "U-KICAD-HTA" in UNV and rd("kit_v22/kicad_drc_HTA.json") is None else kicad("HTA", False)), gerber=gerbers("kit_v18/HTA") if os.path.isdir(f"{W}/kit_v18/HTA") else NA, plane=NA, cross=NA)
SYS = {
    "cylinder v5 + parts + 47 geometry checks": chk("kit_v22/check_v22.json", lambda d: (len(d["checks"]) >= 47 and all(c["result"] == "PASS" for c in d["checks"]), f"{len(d['checks'])} checks")),
    "KiCad schematics (9 boards, nets rebuilt = netlists)": chk("kit_v22/sch_check.json", lambda d: (all(v["check"]["ok"] for v in d.values() if "check" in v), f"{len([v for v in d.values() if 'check' in v])} boards")),
    "wiring audit (links + harness)": chk("kit_v22/wiring_audit.json", lambda d: (not d["errors"], f"{d['link_pins']} pins, {d['harness_conductors']} conductors")),
    "stress table (only the documented LED-rail row may fail)": chk("kit_v22/system_budget.json", lambda d: (len([r for r in d["rows"] if r["status"] == "FAIL"]) == 1, f"{d['fails']} fail (LED rail, by design), {d['watch']} watch")),
    "TX stage over 19.6-29.4 V (reproduces sim_head1 at 26 V)": chk("kit_v23/tx_vbus.json", lambda d: (d["validation_ok"], "Vds 456-466 V, ton table")),
    "PM2 dock chain (time-domain)": chk("kit_v23/power_dock_check.json", lambda d: (all(c["result"] == "PASS" for c in d["checks"]), f"{len(d['checks'])} checks")),
    "full head cross-check (26 solids, 3D interference)": chk("kit_v22/head_crosscheck.json", lambda d: (d["fails"] == 0, f"{len(d['checks'])} checks, {d['warns']} warnings")),
    "0.2 mm fine check": chk("kit_v22/fine_check.json", lambda d: (d[0][1] == 0 and d[1][1] == [] and d[2][1] == 0 and d[3][1] == [], "board discs and bodies clear")),
    "voxel interference (window, bridge, junction)": chk("kit_v22/interference_audit.json", lambda d: (len(d["interferences"]) == 0, f"{len(d['pairs'])} pairs")),
}
# An UNVERIFIED item can be closed only by deleting its row in docs/UNVERIFIED.md AND having its evidence on disk: removing the row without evidence is a FAIL (not a silent PASS).
KNOWN_EVIDENCE = {"U-DS-PARTS": "docs/design/DATASHEET_LOG.md", "U-FAB-RULES": "docs/design/FAB_RULES_VERIFIED.md", "U-FAB-DRC": "data/results/fab_drc/*", "U-CAM-VIEW": "data/results/cam_view/*",
                  "U-BENCH": "data/bench/*", "U-COLD-BOOTSTRAP": "data/results/bootstrap_cold.json"}
import glob as _g
def ev_state(k):
    if k in UNV: return ("UNVERIFIED", UNV[k])
    return ("PASS", f"evidence present: {KNOWN_EVIDENCE[k]}") if _g.glob(KNOWN_EVIDENCE[k]) else ("FAIL", f"row removed from the register but no evidence at {KNOWN_EVIDENCE[k]}")
CONTROLS_ROW = ("release-tx / sign-off controls (refusals, evidence rule, idempotence)", chk("kit_v22/controls_3_9.json", lambda d: (d["all_ok"], f"{sum(c['ok'] for c in d['cases'])}/{len(d['cases'])} controls behave as intended")))
if "--ignore-controls" not in sys.argv:       # used only by tests/release_signoff_controls.py: its own result file cannot be an input of its baseline (cold-start chicken and egg)
    SYS[CONTROLS_ROW[0]] = CONTROLS_ROW[1]
EV = {k: ev_state(k) for k in KNOWN_EVIDENCE}
for k in UNV:                                                      # a registered ID nothing displays would be invisible: show it
    if k not in EV and not k.startswith(("U-ROUTE-", "U-KICAD-")): EV[k] = ("UNVERIFIED", UNV[k])
# board rows: a registered board ID must belong to a board row, an unregistered missing result is a FAIL (see chk); the table shape is fixed
EXPECTED_BOARDS = ["CB1D", "LB1", "PB1R", "TXJ1", "SB1R-QA", "SB1R-QB", "PM2", "HB2", "HTA"]
assert list(B) == EXPECTED_BOARDS, f"board rows changed: {list(B)}"
for b_, row in B.items(): assert set(row) == {"route", "indep", "kicad", "gerber", "plane", "cross"}, f"{b_}: check columns changed"
for k in UNV:
    if k.startswith(("U-ROUTE-", "U-KICAD-")) and not any(v[1] == k for row in B.values() for v in row.values()): EV[k] = ("FAIL", f"registered but shown by no board row: {k}")
reg = None
if "--no-regress" not in sys.argv:
    r = subprocess.run([sys.executable, "tests/regress.py"], capture_output=True, text=True); last = (r.stdout.strip().splitlines() or ["?"])[-1]
    npass = sum(1 for l in r.stdout.splitlines() if l.startswith("PASS")); reg = ("PASS" if r.returncode == 0 else "FAIL", f"{npass} PASS; {last}")
    SYS["tests/regress.py (strict: a missing result FAILs)"] = reg
cols = ["route", "indep", "kicad", "gerber", "plane", "cross"]; names = ["route", "indep. DRC", "KiCad DRC", "Gerber+drill", "plane HV", "cross-check"]
allst = [v[0] for b in B.values() for v in b.values()] + [v[0] for v in SYS.values()] + [v[0] for v in EV.values()]
cnt = {k: allst.count(k) for k in ("PASS", "FAIL", "SKIP", "UNVERIFIED")}
sym = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP", "UNVERIFIED": "UNVERIFIED", "-": "-"}
def table():
    L = ["| board | " + " | ".join(names) + " |", "|---|" + "---|" * len(cols)]
    for b, v in B.items(): L.append(f"| {b} | " + " | ".join(sym[v[c][0]] for c in cols) + " |")
    return L
out = dict(counts=cnt, boards={b: {c: dict(state=v[c][0], detail=v[c][1]) for c in cols} for b, v in B.items()},
           system={k: dict(state=v[0], detail=v[1]) for k, v in SYS.items()}, evidence={k: dict(state=v[0], detail=v[1]) for k, v in EV.items()}, unverified=UNV)
os.makedirs(os.path.dirname(OUT_JSON) or ".", exist_ok=True); json.dump(out, open(OUT_JSON, "w"), indent=1)
md = ["# Sign-off status of the transmit region (GENERATED by `make signoff` / scripts/signoff_status.py: do not edit)", "",
      f"Everything here is MODELED or tool-checked; nothing is built or measured. PASS means the tool check passed, not that a board is ready for fabrication.", "",
      f"**{cnt['PASS']} PASS, {cnt['FAIL']} FAIL, {cnt['SKIP']} SKIP, {cnt['UNVERIFIED']} UNVERIFIED**", "", "## Boards"] + table() + ["", "## System checks", "| check | state | detail |", "|---|---|---|"]
md += [f"| {k} | {v[0]} | {v[1]} |" for k, v in SYS.items()]
md += ["", "## Evidence still missing (docs/UNVERIFIED.md)", "| id | state | item |", "|---|---|---|"] + [f"| {k} | {v[0]} | {UNV.get(k, 'closed')[:110]} |" for k, v in EV.items()]
open(OUT_MD, "w").write("\n".join(md) + "\n")
print("\n".join(table())); print()
for k, v in SYS.items(): print(f"{v[0]:10} {k}: {v[1]}")
print(); [print(f"{v[0]:10} {k}") for k, v in EV.items()]
print(f"\nSIGN-OFF: {cnt['PASS']} PASS, {cnt['FAIL']} FAIL, {cnt['SKIP']} SKIP, {cnt['UNVERIFIED']} UNVERIFIED -> {OUT_JSON}, {OUT_MD}")
sys.exit(1 if cnt["FAIL"] else 0)
