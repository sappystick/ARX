#!/usr/bin/env python3
"""Controls for the sign-off and release tooling (Step 3.9). Nothing committed is edited: release_tx.py / signoff_status.py are driven through their override switches
(ARX_RELEASE_ROOT, ARX_SIGNOFF_JSON, --register, --out-json, --out-md) into a temporary folder, and the one stale-data control changes a COPY-BACKED work/ file that is restored in a finally block.
Cases: release-tx positive + three refusals (existing revision, sign-off with a FAIL, stale data); sign-off table baseline, a closed register row without evidence, PM2 / HTA rows that cannot vanish,
a registered ID nobody displays, fixed table shape, and byte-identical output on a second run (idempotent: no timestamp, no commit hash).
The vanish and evidence controls run on FIXTURES (Step 5): a symlink copy of work/ or of the repo with the one result or evidence file removed (or a datasheet section marked UNVERIFIED),
so they keep testing the rule after the production IDs (U-ROUTE-PM2, U-KICAD-HTA, the datasheet groups) are closed.
usage: python3 tests/release_signoff_controls.py      -> work/kit_v22/controls_3_9.json, exit 1 if any control does not behave"""
import os, sys, json, subprocess, tempfile, hashlib, csv, re
T = tempfile.mkdtemp(); PY = sys.executable; cases = []
def run(*a, env=None):
    e = dict(os.environ); e.update(env or {}); r = subprocess.run([PY, *a], capture_output=True, text=True, env=e); return r.returncode, (r.stdout + r.stderr)
def case(name, expect_rc, expect_text, rc, text, extra=True):
    ok = rc == expect_rc and (expect_text is None or expect_text in text) and extra; cases.append(dict(name=name, expected=f"rc {expect_rc}" + (f" + '{expect_text}'" if expect_text else ""), got=f"rc {rc}: {text.strip().splitlines()[0][:90] if text.strip() else ''}", ok=bool(ok)))
# ---------------- release-tx
env = {"ARX_RELEASE_ROOT": T}
rc, tx = run("scripts/release_tx.py", "ctl1", env=env)
man = os.path.join(T, "TX_ctl1", "MANIFEST.csv"); good = False
if os.path.exists(man):
    rows = list(csv.DictReader(open(man))); good = len(rows) > 30 and all(hashlib.sha256(open(r["file"], "rb").read()).hexdigest() == r["sha256"] for r in rows if os.path.exists(r["file"]))
case("release-tx positive control: writes a package whose manifest hashes verify", 0, "written", rc, tx, good)
rc, tx = run("scripts/release_tx.py", "ctl1", env=env); case("release-tx refuses an existing revision", 1, "exists", rc, tx)
S = json.load(open("data/results/SIGNOFF_STATUS.json")); S["counts"]["FAIL"] = 1; bad = os.path.join(T, "status_fail.json"); json.dump(S, open(bad, "w"))
rc, tx = run("scripts/release_tx.py", "ctl2", env={**env, "ARX_SIGNOFF_JSON": bad}); case("release-tx refuses a sign-off that has a FAIL", 1, "FAIL", rc, tx, not os.path.exists(os.path.join(T, "TX_ctl2")))
victim = "work/kit_v22/wiring_audit.json"; keep = open(victim, "rb").read()
try:
    d = json.loads(keep); d["_control"] = 1; open(victim, "w").write(json.dumps(d, indent=1))
    rc, tx = run("scripts/release_tx.py", "ctl3", env=env); case("release-tx refuses stale data (a work/ result differs from data/)", 1, "stale", rc, tx, not os.path.exists(os.path.join(T, "TX_ctl3")))
finally: open(victim, "wb").write(keep)
rc, tx = run("scripts/publish_data.py", "--check"); case("work/ restored after the stale-data control (publish check: 0 stale)", 0, "0 stale", rc, tx)
# ---------------- sign-off table
reg = open("docs/UNVERIFIED.md").read()
def farm(src, dst, omit=(), replace=None, rel=""):
    """mirror src into dst with symlinks; a directory that holds an omitted or replaced path is rebuilt file by file, everything else is one symlink"""
    replace = replace or {}; os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        r = f"{rel}/{name}" if rel else name; s_, d_ = os.path.join(src, name), os.path.join(dst, name)
        if r in omit: continue
        if r in replace: open(d_, "w").write(replace[r]); continue
        if os.path.isdir(s_) and any(o.startswith(r + "/") for o in list(omit) + list(replace)): farm(s_, d_, omit, replace, r)
        else: os.symlink(os.path.abspath(s_), d_)
    return dst
def status(name, register=None, expect_rc=0, expect_text=None, what=None, work=None, evroot=None):
    regf = "docs/UNVERIFIED.md"
    if register is not None: regf = os.path.join(T, name + ".md"); open(regf, "w").write(register)
    oj = os.path.join(T, name + ".json"); om = os.path.join(T, name + "_status.md")
    rc, tx = run("scripts/signoff_status.py", "--no-regress", "--ignore-controls", "--register", regf, "--out-json", oj, "--out-md", om, *(["--work", work] if work else []), *(["--evidence-root", evroot] if evroot else []))
    j = json.load(open(oj)) if os.path.exists(oj) else {}; extra = True
    if what: extra = what(j)
    return rc, tx, j, extra
rc, tx, j1, ok = status("b1"); case("sign-off table baseline: 0 FAIL, fixed shape (12 boards x 6 checks)", 0, None, rc, tx, len(j1["boards"]) == 12 and all(len(v) == 6 for v in j1["boards"].values()) and j1["counts"]["FAIL"] == 0)
rc, tx, j2, ok = status("b1b"); case("sign-off table is idempotent: a second run writes byte-identical JSON and markdown", 0, None, rc, tx,
                                       open(os.path.join(T, "b1.json"), "rb").read() == open(os.path.join(T, "b1b.json"), "rb").read() and open(os.path.join(T, "b1_status.md"), "rb").read() == open(os.path.join(T, "b1b_status.md"), "rb").read())
nopm2 = farm("work", os.path.join(T, "w_nopm2"), omit={"kit_v20/route_PM2.json"})
rc, tx, j, ok = status("nopm2", re.sub(r"^\| U-ROUTE-PM2 \|.*\n", "", reg, flags=re.M), what=lambda j: j["boards"]["PM2"]["route"]["state"] == "FAIL", work=nopm2)
case("a board row cannot vanish: U-ROUTE-PM2 not registered and no PM2 route result (fixture work/) -> PM2 FAIL", 1, None, rc, tx, ok)
nohta = farm("work", os.path.join(T, "w_nohta"), omit={"kit_v22/kicad_drc_HTA.json"})
rc, tx, j, ok = status("nohta", re.sub(r"^\| U-KICAD-HTA \|.*\n", "", reg, flags=re.M), what=lambda j: j["boards"]["HTA"]["kicad"]["state"] == "FAIL", work=nohta)
case("U-KICAD-HTA not registered and no HTA KiCad DRC result (fixture work/) -> HTA FAIL", 1, None, rc, tx, ok)
nofab = farm(".", os.path.join(T, "r_nofab"), omit={"docs/design/FAB_RULES_VERIFIED.md"})
rc, tx, j, ok = status("nofab", re.sub(r"^\| U-FAB-RULES \|.*\n", "", reg, flags=re.M), what=lambda j: j["evidence"]["U-FAB-RULES"]["state"] == "FAIL", evroot=nofab)
case("a closed item needs its evidence: U-FAB-RULES not registered, evidence file absent (fixture repo) -> FAIL", 1, None, rc, tx, ok)
log = open("docs/design/DATASHEET_LOG.md").read() if os.path.exists("docs/design/DATASHEET_LOG.md") else ""
unv = farm(".", os.path.join(T, "r_dsunv"), replace={"docs/design/DATASHEET_LOG.md": re.sub(r"^## U-DS-HALL: VERIFIED", "## U-DS-HALL: UNVERIFIED", log, flags=re.M)})
rc, tx, j, ok = status("dsunv", re.sub(r"^\| U-DS-HALL \|.*\n", "", reg, flags=re.M), what=lambda j: j["evidence"]["U-DS-HALL"]["state"] == "FAIL", evroot=unv)
case("a datasheet group closes only with a VERIFIED section: U-DS-HALL not registered, its log section UNVERIFIED (fixture) -> FAIL", 1, None, rc, tx, ok)
rc, tx, j, ok = status("orphan", reg.rstrip("\n") + "\n| U-ROUTE-XYZ | invented | nowhere | never | none |\n", what=lambda j: j["evidence"].get("U-ROUTE-XYZ", {}).get("state") == "FAIL")
case("a registered board ID that no board row shows is a FAIL (cannot hide)", 1, None, rc, tx, ok)
res = dict(cases=cases, all_ok=all(c["ok"] for c in cases))
os.makedirs("work/kit_v22", exist_ok=True); json.dump(res, open("work/kit_v22/controls_3_9.json", "w"), indent=1)
for c in cases: print(("PASS " if c["ok"] else "FAIL ") + c["name"] + ("" if c["ok"] else f"  [expected {c['expected']}; got {c['got']}]"))
print(f"controls: {sum(c['ok'] for c in cases)}/{len(cases)} behave as intended")
sys.exit(0 if res["all_ok"] else 1)
