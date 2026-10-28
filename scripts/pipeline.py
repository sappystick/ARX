#!/usr/bin/env python3
"""Incremental, parallel sign-off pipeline (replaces the 30-40 minute serial `make signoff`; the old path stays as `make signoff-serial`).

How it works
  * Every step is one shell command (STEPS below, same commands as the Makefile recipes). Each run is TRACED (scripts/tracehook): the files a step really reads and
    writes are recorded, so nothing depends on hand-declared inputs.
  * A step is SKIPPED only if its command and the tool versions are unchanged, every file it read has the same content hash, and every file it wrote still exists with
    the hash it left (a deleted or edited output re-runs the step). Cached state lives in work/.pipeline/ (wiped by `make clean`).
  * The order of independent steps comes from data/pipeline/graph.json (committed, paths only: learned from a traced serial run). Two steps may overlap only if neither
    writes what the other reads or writes. A step missing from the graph runs alone, in the declared order. After every run the fresh traces are checked against the
    graph; an uncovered conflict is reported as GRAPH STALE (fix: serial run, then --update-graph).
  * Steps tagged 'kicad' never overlap each other (memory); BLAS thread counts are left alone (forcing 1 changed last digits of stiff-ODE results); steps with internal pools read ARX_INNER_JOBS.
usage: python3 scripts/pipeline.py run [--jobs N] [--cold] [--only STEP[,STEP]] [--update-graph] [--no-setup]
       python3 scripts/pipeline.py plan          (what would run and why; runs nothing)
       python3 scripts/pipeline.py list
Outputs: work/.pipeline/{cache,logs,timing.json}; exit 1 if any step fails or the graph is stale."""
import os, sys, json, time, hashlib, subprocess, threading, shlex, shutil, platform, signal, atexit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = os.path.join(ROOT, "work", ".pipeline")
# run guards (2026-10-28): the longest step takes about 9.5 min (sbq-fast 563 s, route-cb1d 420 s); a step that runs past STEP_TIMEOUT is hung, not slow:
# its whole process group is killed and the step FAILs with rc 124. One run at a time (RUN_FILE holds pid, start, argv); scripts/wait_run.sh waits on that pid.
STEP_TIMEOUT = int(os.environ.get("PIPELINE_STEP_TIMEOUT", "900"))
RUN_FILE = os.path.join(PIPE, "run.json")
GRAPH = os.path.join(ROOT, "data", "pipeline", "graph.json")
HOOK = os.path.join(ROOT, "scripts", "tracehook")
W, P = "cd work && ", "python3 "

def route(b):
    return (f"cd work && for i in 1 2 3 4 5 6; do python3 route_run.py {b}; [ -f kit_v20/route_{b}.json ] && break; done; "
            f"test -f kit_v20/route_{b}.json && python3 route_fix.py {b} kit_v20/route_{b}.json")

# (name, command, tags). Declared order = the order of the old serial signoff, minus the repeats (each board is generated once, not four times).
STEPS = [
    ("baseplate", W + "python3 cap_hood_v16.py", ""),
    ("sbq-geom", W + "python3 sbq_gen2.py", ""),
    ("v5", W + "python3 hub_v22.py && python3 parts_v22.py", ""),
    ("check", W + "python3 check_v22.py", ""),
    ("sim-head1", W + "python3 sim_head1.py > /dev/null", ""),
    ("hood", W + "python3 hood_v20.py && python3 hood_axi.py", ""),
    ("yoke", W + "python3 yoke_v20.py", ""),
    ("yoke-check", W + "python3 yoke_check.py", ""),
    ("pcb-lb1", W + "PW=L python3 pw_design.py && PW=L python3 lb1_export.py", ""),
    ("pcb-hb1", W + "PW=H python3 pw_design.py && PW=H python3 pw_export.py", ""),
    ("pcb-hb2", W + "PW=G python3 pw_design.py && PW=G python3 pw_export.py", ""),
    ("pcb-au1", W + "mkdir -p kit_v23 && PW=U python3 pw_design.py && PW=U python3 pw_export.py && PW=U python3 au1_check.py > /dev/null", ""),   # AU1 audio board (output modes): placement + electrical cross-check
    ("pcb-pb1r", W + "PW=R python3 pw_design.py && PW=R python3 pw_export.py", ""),
    ("pcb-cb1d", W + "PW=C DISC=1 python3 pw_design.py && PW=C DISC=1 python3 cb1d_export.py", ""),
    ("tx-vbus", W + "mkdir -p kit_v23 && python3 tx_vbus_sweep.py", ""),
    ("system-live", W + "mkdir -p kit_v23 && python3 tx_vbus_sweep.py > /dev/null && python3 system_live.py", ""),     # viewer r2 system model + golden cases (src/sim/system_live.py)
    ("pcb-pm2", W + "PW=P python3 pw_design.py && PW=P python3 pw_export.py && python3 power_dock_check.py", ""),
    ("upper", W + "python3 shaft_calc_v20.py > /dev/null && python3 upper_v21.py && python3 upper_check.py && python3 upper_figure.py", ""),
    ("sim-head2", W + "python3 sim_head2.py > /dev/null", ""),
    ("tx", W + "python3 tx_system.py", ""),
    ("pcb-ab1", W + "mkdir -p out_board kit_v22 && for B in A B; do BOARD=$B python3 afe_layout.py --route > /dev/null && BOARD=$B python3 afe_export.py > /dev/null; done", ""),
    ("ab1-checks", "for B in A B; do python3 src/pcb/kicad_drc.py work/kit_v3/PCB_AB1$B/PF233-AB1$B.kicad_pcb work/kit_v22/kicad_drc_AB1$B.json AB1$B | head -c 120; python3 src/pcb/indep_drc.py AB1$B work/kit_v3/PCB_AB1$B/PF233-AB1$B.kicad_pcb work/kit_v22/indep_drc_AB1$B.json | tail -1; (cd work && BOARD=$B python3 ab1_island_check.py kit_v22/ab1_island_check_AB1$B.json | head -c 60); done", "kicad"),
    ("gerber-ab1", "for B in A B; do python3 src/pcb/kicad_gerber.py work/kit_v3/PCB_AB1$B/PF233-AB1$B.kicad_pcb AB1$B work/kit_v22/GERBER_AB1$B PF233-AB1$B F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts | head -c 60; done && " + W + "for B in A B; do python3 gerber_edge_check.py kit_v22/gerber_edge_AB1$B.json kit_v22/GERBER_AB1$B PF233-AB1$B | tail -1; BOARD=$B python3 gerber_ab1_check.py kit_v22/gerber_ab1_AB1$B.json | head -c 60; done", "kicad"),
    ("audit-system", W + "python3 wiring_audit.py && python3 system_budget.py && python3 stack_check.py && python3 interference_audit.py", ""),
    ("sch", W + "python3 sch_export.py && python3 trigger_check.py", ""),
    ("sims-rx", W + "python3 sim_cage_rx.py && python3 sim_tanr.py && python3 sim_quadbearing.py", ""),
    ("route-lb1", route("LB1"), ""),
    ("gerber-lb1", W + "python3 gerber_out.py LB1 hatch notch-1 && python3 gerber_edge_check.py kit_v22/gerber_edge_LB1.json kit_v22/GERBER_LB1_v2 PF233-LB1-v2", ""),
    ("route-cb1d", route("CB1D"), ""),
    ("gerber-cb1d", W + "python3 gerber_out.py CB1D hatch notch1 hv=COIL_A,COIL_B,DM1,DM2 && python3 gerber_hv_check.py CB1D kit_v22/GERBER_CB1D_v2 PF233-CB1D-v2 COIL_A,COIL_B,DM1,DM2 && python3 gerber_edge_check.py kit_v22/gerber_edge_CB1D.json kit_v22/GERBER_CB1D_v2 PF233-CB1D-v2", ""),
    ("route-pb1r", route("PB1R") + " && python3 viafarm.py PB1R kit_v20/route_PB1R.json", ""),
    ("drc-lb1", W + "python3 drc.py LB1 kit_v20/route_LB1.json -1", ""),
    ("drc-cb1d", W + "python3 drc.py CB1D kit_v20/route_CB1D.json 1 COIL_A,COIL_B,DM1,DM2", ""),
    ("drc-pb1r", W + "python3 drc.py PB1R kit_v20/route_PB1R.json 0 DRAIN1,CLAMP1", ""),
    ("kicad-lb1", "mkdir -p work/kit_v22/KICAD && " + W + "python3 kicad_inject.py LB1 kit_v20/route_LB1.json kit_v22/KICAD/PF233-LB1_routed.kicad_pcb -1", ""),
    ("kicad-cb1d", "mkdir -p work/kit_v22/KICAD && " + W + "python3 kicad_inject.py CB1D kit_v20/route_CB1D.json kit_v22/KICAD/PF233-CB1D_routed.kicad_pcb 1 six", ""),
    ("kicad-pb1r", "mkdir -p work/kit_v22/KICAD && " + W + "python3 rect_inject.py PB1R kit_v20/route_PB1R.json kit_v6/PB1R/PF233-PB1R.kicad_pcb kit_v22/KICAD/PF233-PB1R_routed.kicad_pcb", ""),
    ("gerber-pb1r", "python3 src/pcb/kicad_gerber.py work/kit_v22/KICAD/PF233-PB1R_routed.kicad_pcb PB1R work/kit_v22/GERBER_PB1R PF233-PB1R && "
                    + W + "python3 gerber_plane_check.py PB1R kit_v22/GERBER_PB1R PF233-PB1R DRAIN1,CLAMP1 In1:GND,In2:VBUS && python3 gerber_edge_check.py kit_v22/gerber_edge_PB1R.json kit_v22/GERBER_PB1R PF233-PB1R", "kicad"),
    ("route-pm2", route("PM2"), ""),
    ("drc-pm2", W + "python3 drc.py PM2 kit_v20/route_PM2.json 0", ""),
    ("kicad-pm2", "mkdir -p work/kit_v22/KICAD && " + W + "python3 rect_inject.py PM2 kit_v20/route_PM2.json kit_v6/PM2/PF233-PM2.kicad_pcb kit_v22/KICAD/PF233-PM2_routed.kicad_pcb", ""),
    ("gerber-pm2", "python3 src/pcb/kicad_gerber.py work/kit_v22/KICAD/PF233-PM2_routed.kicad_pcb PM2 work/kit_v22/GERBER_PM2 PF233-PM2 && " + W + "python3 gerber_edge_check.py kit_v22/gerber_edge_PM2.json kit_v22/GERBER_PM2 PF233-PM2", "kicad"),
    ("route-hb2", route("HB2"), ""),
    ("drc-hb2", W + "python3 drc.py HB2 kit_v20/route_HB2.json 0", ""),
    ("kicad-hb2", "mkdir -p work/kit_v22/KICAD && " + W + "python3 rect_inject.py HB2 kit_v20/route_HB2.json kit_v6/HB2/PF233-HB2.kicad_pcb kit_v22/KICAD/PF233-HB2_routed.kicad_pcb", ""),
    ("gerber-hb2", "python3 src/pcb/kicad_gerber.py work/kit_v22/KICAD/PF233-HB2_routed.kicad_pcb HB2 work/kit_v22/GERBER_HB2 PF233-HB2 && " + W + "python3 gerber_edge_check.py kit_v22/gerber_edge_HB2.json kit_v22/GERBER_HB2 PF233-HB2", "kicad"),
    ("route-au1", route("AU1"), ""),
    ("drc-au1", W + "python3 drc.py AU1 kit_v20/route_AU1.json 0", ""),
    ("kicad-au1", "mkdir -p work/kit_v22/KICAD && " + W + "python3 rect_inject.py AU1 kit_v20/route_AU1.json kit_v6/AU1/PF233-AU1.kicad_pcb kit_v22/KICAD/PF233-AU1_routed.kicad_pcb", ""),
    ("gerber-au1", "python3 src/pcb/kicad_gerber.py work/kit_v22/KICAD/PF233-AU1_routed.kicad_pcb AU1 work/kit_v22/GERBER_AU1 PF233-AU1 && " + W + "python3 gerber_edge_check.py kit_v22/gerber_edge_AU1.json kit_v22/GERBER_AU1 PF233-AU1", "kicad"),
    ("sbq-fast", W + "python3 sbq_gen2.py && python3 sbq_export.py && python3 sbq_sim.py && python3 sbq_damp2.py", ""),
    ("pcb-hta", W + "python3 hta_gerber.py > /dev/null && python3 hta_kicad.py && python3 gerber_edge_check.py kit_v22/gerber_edge_HTA.json kit_v18/HTA PF233-HTA", ""),
    ("kicad-drc", "; ".join([f"python3 src/pcb/kicad_drc.py work/kit_v22/KICAD/PF233-{b}_routed.kicad_pcb work/kit_v22/kicad_drc_{b}.json {b} | head -1" for b in ("CB1D", "LB1", "PB1R", "PM2", "HB2", "AU1")]
                  + ["python3 src/pcb/kicad_drc.py work/kit_v22/KICAD_TXJ1/TXJ1.kicad_pcb work/kit_v22/kicad_drc_TXJ1.json TXJ1 | head -1"]
                  + ["python3 src/pcb/kicad_drc.py work/kit_v22/KICAD/PF233-HTA.kicad_pcb work/kit_v22/kicad_drc_HTA.json HTA | head -1"]
                  + [f"python3 src/pcb/kicad_drc.py work/kit_v22/KICAD_SBQ/{b}.kicad_pcb work/kit_v22/kicad_drc_{b}.json {b} | head -1" for b in ("SB1R-QA", "SB1R-QB")]), "kicad"),
    ("print-check", "python3 src/mech/print_check.py data/results/print_check.json", ""),
    ("indep-drc", "mkdir -p data/results/indep_drc && " + " && ".join(f"python3 src/pcb/indep_drc.py {b} {p} data/results/indep_drc/{b}.json" for b, p in (("TXJ1", "data/kicad/TXJ1.kicad_pcb"), ("SB1R-QA", "data/kicad/SB1R-QA.kicad_pcb"), ("SB1R-QB", "data/kicad/SB1R-QB.kicad_pcb"), ("HTA", "data/kicad/PF233-HTA.kicad_pcb"))) + " && python3 tests/indep_drc_controls.py && python3 src/pcb/board_sch.py data/results/board_sch", ""),
    ("models3d", W + "mkdir -p kit_v22/3dmodels && python3 models3d.py kit_v22/3dmodels", ""),
    ("models3d-check", W + "python3 models3d_check.py kit_v22/3dmodels kit_v22/models3d_check.json " + " ".join(f"kit_v22/KICAD/PF233-{b}_routed.kicad_pcb" for b in ("CB1D", "LB1", "PB1R", "PM2", "HB2", "AU1")) + " kit_v22/KICAD_SBQ/SB1R-QA.kicad_pcb kit_v22/KICAD_SBQ/SB1R-QB.kicad_pcb kit_v3/PCB_AB1A/PF233-AB1A.kicad_pcb kit_v3/PCB_AB1B/PF233-AB1B.kicad_pcb", ""),
    ("pad-orient", W + "/usr/bin/python3 pad_orient_check.py > /dev/null 2>&1", ""),       # KiCad pad geometry = placement model on the rotated-footprint boards (CORRECTIONS 2026-10-28): kit_v22/pad_orient_check.json
    ("sch-func", W + "mkdir -p kit_v22/SCHF && PW=R python3 sch_func.py PB1R kit_v22/SCHF && PW=P python3 sch_func.py PM2 kit_v22/SCHF && PW=G python3 sch_func.py HB2 kit_v22/SCHF && PW=U python3 sch_func.py AU1 kit_v22/SCHF && PW=C DISC=1 python3 sch_func.py CB1D kit_v22/SCHF && PW=L python3 sch_func.py LB1 kit_v22/SCHF && BOARD=A python3 sch_func.py AB1A kit_v22/SCHF && BOARD=B python3 sch_func.py AB1B kit_v22/SCHF", "kicad"),
    ("cap-v18", W + "python3 cap_v18.py > /dev/null", ""),                        # HUB_CAP_HTA_v3_vault through the closing union (kit_v18/PARTS): was not a step, so a fresh work/ carried the open seed copy (108 bad edges) into head_crosscheck and curate
    ("mech-npm", W + "python3 mech_v20.py > /dev/null", ""),                       # neck module / elbow / battery drawer meshes (kit_v19/SPINE): pb1r_check NPM fit reads them; was not a step, so a fresh work/ skipped that check
    ("fw-timeline", W + "mkdir -p kit_v23 && python3 fw_timeline.py > /dev/null", ""),     # P5 firmware timing model + generated C header (kit_v23/pf233_timing.h)
    ("output-modes", W + "mkdir -p kit_v23 && python3 output_modes.py > /dev/null", ""),   # output modes step 1: audio / LED renderers, idle-slot, latency, rail cap: kit_v23/output_modes.json, pf233_output.h
    ("sweep-track", W + "mkdir -p kit_v23 && python3 sweep_track.py > /dev/null", ""),     # sweep tracking / pinpoint over a target (quad model): kit_v23/sweep_track.json
    ("tx-steer", W + "mkdir -p kit_v23 && python3 tx_steer_study.py > /dev/null", ""),     # TX steering study (offset coils / push-pull pairs vs RX-Q): kit_v23/tx_steer_study.json
    ("hood-tol", W + "mkdir -p kit_v23 && python3 hood_tolerance.py > /dev/null", ""),      # P3 hood placement tolerance (axisymmetric, hood_axi.py): kit_v23/hood_tolerance.json
    ("potting", "python3 src/mech/potting_volumes.py > /dev/null", ""),                 # P2 exact potting volumes (NPM zones, L4 absorber) from the meshes: data/results/potting_volumes.json
    ("check-pb1r", W + "mkdir -p kit_v23 && python3 tx_vbus_sweep.py > /dev/null && python3 pb1r_check.py", ""),
    ("formers-low", "test -f work/kit_v15/LOW/FORMER_L1_petal_coil_former.stl || (" + W + "python3 phifold_v15.py low)", ""),
    ("head-audit", W + "mkdir -p kit_v21 && python3 head_crosscheck.py && python3 fine_check.py && python3 head_drawings.py", ""),
    ("publish", "python3 scripts/publish_data.py", ""),
    ("fab-margin", "/usr/bin/python3 src/pcb/fab_margin.py > /dev/null 2>&1", ""),          # P1 margin audit of the published boards (data/kicad): data/results/fab_margin_audit.json
    ("led-fit", "python3 src/pcb/led_upgrade_check.py > /dev/null", ""),                  # LB1-v6 SK9822-EC20 fit at the published positions and chain rotations: data/results/led_upgrade_check.json
    ("controls", "python3 tests/release_signoff_controls.py", ""),
    ("status", "python3 scripts/signoff_status.py", ""),
    ("viewer", "test ! -f deliverables/PHIFOLD233_PACKAGE_r5/blueprint/cutaway_faces.json || python3 src/render/viewer_r2.py > /dev/null", ""),   # package r5 viewer.html: sign-off states, system model, owners (after status)
]
NAMES = [s[0] for s in STEPS]
IGNORE_READS = {"controls": {"data/results/SIGNOFF_STATUS.json", "docs/STATUS.md"}}   # the controls only use the previous table as a template; it is rewritten by the step after them (would re-run them forever)
OPEN_ENDED = {"publish", "fab-margin", "led-fit", "controls", "status", "viewer"}  # always run alone, last, in order (controls temporarily edit a work/ file)


def sha_file(p, cache={}):
    try:
        st = os.stat(p)
    except OSError:
        return None
    k = (p, st.st_size, st.st_mtime_ns)
    if k not in cache:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        cache[k] = h.hexdigest()
    return cache[k]


def sha_dir(d):
    try:
        return hashlib.sha256("\n".join(sorted(os.listdir(d))).encode()).hexdigest()
    except OSError:
        return None


def env_fingerprint():
    fp = [platform.python_version()]
    for m in ("numpy", "scipy", "shapely", "gerbonara", "matplotlib"):
        try:
            fp.append(m + "=" + __import__(m).__version__)
        except Exception:
            fp.append(m + "=none")
    try:
        fp.append(subprocess.run(["kicad-cli", "version"], capture_output=True, text=True).stdout.strip())
    except Exception:
        fp.append("kicad=none")
    return hashlib.sha256("|".join(fp).encode()).hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT)


def cache_path(name):
    return os.path.join(PIPE, "cache", name + ".json")


def load_cache(name):
    try:
        return json.load(open(cache_path(name)))
    except Exception:
        return None


def why_stale(name, cmd, envfp):
    """None if the step can be skipped, else the reason."""
    c = load_cache(name)
    if c is None:
        return "no cached result"
    if c["cmd"] != cmd:
        return "command changed"
    if c["env"] != envfp:
        return "tool versions changed"
    for p, h in c["writes"].items():
        if sha_file(os.path.join(ROOT, p)) != h:
            return f"output missing or edited: {p}"
    for p, h in c["reads"].items():
        if p not in c["writes"] and p not in IGNORE_READS.get(name, ()) and sha_file(os.path.join(ROOT, p)) != h:
            return f"input changed: {p}"
    for d, h in c["lists"].items():
        if d not in (".", "work") and sha_dir(os.path.join(ROOT, d)) != h:
            return f"directory listing changed: {d}"
    return None


def parse_trace(tf, t0):
    reads, writes, lists, ps = set(), set(), set(), set()
    if os.path.exists(tf):
        for ln in open(tf):
            k, _, p = ln.rstrip("\n").partition(" ")
            if not p:
                continue
            {"R": reads, "W": writes, "L": lists, "P": ps}.get(k, set()).add(p)
    for p in ps:
        if os.path.isfile(p):
            (writes if os.path.getmtime(p) >= t0 - 1e-3 else reads).add(p)
    writes = {p for p in writes if os.path.isfile(p)}  # deleted-only paths are not outputs
    reads = {p for p in reads if os.path.isfile(p)}
    return reads, writes, lists


def run_step(name, cmd, env_extra, envfp):
    os.makedirs(os.path.join(PIPE, "cache"), exist_ok=True)
    os.makedirs(os.path.join(PIPE, "logs"), exist_ok=True)
    tf = os.path.join(PIPE, "trace_" + name + ".txt")
    if os.path.exists(tf):
        os.remove(tf)
    env = dict(os.environ)
    env.update(env_extra)
    env["ARX_TRACE"], env["ARX_ROOT"] = tf, ROOT
    env["PYTHONPATH"] = HOOK + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    t0 = time.time()
    with open(os.path.join(PIPE, "logs", name + ".log"), "w") as lg:
        r = subprocess.Popen(["/bin/sh", "-c", cmd], cwd=ROOT, env=env, stdout=lg, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            r.wait(timeout=STEP_TIMEOUT)
        except subprocess.TimeoutExpired:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(r.pid, sig)
                except ProcessLookupError:
                    break
                try:
                    r.wait(timeout=10)
                    break
                except subprocess.TimeoutExpired:
                    pass
            lg.write(f"\nTIMEOUT: step ran past {STEP_TIMEOUT} s (PIPELINE_STEP_TIMEOUT); process group killed\n")
            r.returncode = 124
    dt = time.time() - t0
    reads, writes, lists = parse_trace(tf, t0)
    rec = dict(cmd=cmd, env=envfp, seconds=round(dt, 2), rc=r.returncode,
               reads={rel(p): sha_file(p) for p in sorted(reads | writes)},
               writes={rel(p): sha_file(p) for p in sorted(writes)},
               lists={rel(d): sha_dir(d) for d in sorted(lists) if not any(rel(d) == os.path.dirname(w) for w in map(rel, writes))})
    if r.returncode == 0:
        json.dump(rec, open(cache_path(name), "w"), indent=0)
    else:
        try:
            os.remove(cache_path(name))
        except OSError:
            pass
    return r.returncode, dt, rec


def footprint(rec):
    d = {"R": sorted(p for p in rec["reads"] if p not in rec["writes"]), "W": sorted(rec["writes"]), "L": sorted(x for x in rec["lists"] if x not in (".", "work"))}   # work/ and the repo root are listed by python's import finder in every step: not a data dependency
    return d


def conflicts(a, b):
    """True if steps a (earlier) and b (later) must not overlap, from their footprints."""
    aw, bw, ar, br = set(a["W"]), set(b["W"]), set(a["R"]), set(b["R"])
    if aw & (bw | br) or ar & bw:
        return True
    for lst, other in ((a["L"], b["W"]), (b["L"], a["W"])):
        if any(os.path.dirname(w) == d for d in lst for w in other):
            return True
    return False


def load_graph():
    try:
        return json.load(open(GRAPH))["steps"]
    except Exception:
        return {}


def build_deps(order, graph, selected):
    """deps[name] = set of earlier steps that must finish first. Unknown steps, and the closing steps, wait for everything before them."""
    deps = {}
    for i, n in enumerate(order):
        prior = [m for m in order[:i]]
        if n in OPEN_ENDED or n not in graph:
            deps[n] = set(prior)
            continue
        deps[n] = {m for m in prior if m not in graph or m in OPEN_ENDED or conflicts(graph[m], graph[n])}
    return deps


def take_run_lock(argv):
    """one pipeline run at a time: a second run on the same work/ would race on its files. A lock whose pid is gone is stale and is replaced."""
    os.makedirs(PIPE, exist_ok=True)
    try:
        old = json.load(open(RUN_FILE))
        os.kill(old["pid"], 0)
        print(f"pipeline: another run is active (pid {old['pid']}, {round(time.time() - old['start'])} s, {' '.join(old['argv'])}); wait with scripts/wait_run.sh")
        return False
    except (OSError, ValueError, KeyError):
        pass
    json.dump(dict(pid=os.getpid(), start=time.time(), argv=argv, step_timeout_s=STEP_TIMEOUT), open(RUN_FILE, "w"))
    atexit.register(lambda: os.path.exists(RUN_FILE) and json.load(open(RUN_FILE)).get("pid") == os.getpid() and os.remove(RUN_FILE))
    return True


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "run"
    opt = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
    if cmd == "graph":                       # write data/pipeline/graph.json from the cached traces of the last run (every step that succeeded)
        g = {}
        for n in NAMES:
            c = load_cache(n)
            if c:
                g[n] = footprint(c)
        os.makedirs(os.path.dirname(GRAPH), exist_ok=True)
        json.dump(dict(note="learned by scripts/pipeline.py graph from the traces of a serial run; paths only", steps=g), open(GRAPH, "w"), indent=0, sort_keys=True)
        print(f"graph written: {len(g)} of {len(NAMES)} steps")
        return 0
    if cmd == "list":
        for n, c, t in STEPS:
            print(f"{n:14s} {t:6s} {c[:100]}")
        return 0
    order = NAMES
    if opt("--only"):
        order = [n for n in NAMES if n in opt("--only").split(",")]
    cmds = {n: (c, t) for n, c, t in STEPS}
    envfp = env_fingerprint()
    cold = "--cold" in a
    if cmd == "plan":
        for n in order:
            r = "cold run requested" if cold else why_stale(n, cmds[n][0], envfp)
            print(f"{'RUN ' if r else 'SKIP'} {n:14s} {r or ''}")
        return 0
    if not take_run_lock(a):
        return 3
    if "--no-setup" not in a:
        s = subprocess.run(["make", "--no-print-directory", "setup"], cwd=ROOT, capture_output=True, text=True)
        if s.returncode:
            print(s.stdout + s.stderr)
            return 1
    jobs = int(opt("--jobs", "4"))
    graph = load_graph()
    deps = build_deps(order, graph, set(order))
    # a stale step forces re-running nothing downstream by itself: downstream steps are stale only if a file they read changed (their read hashes)
    state, rcs, secs, trace_fp = {}, {}, {}, {}
    lock, cv = threading.Lock(), threading.Condition()
    running = set()
    failed = []
    cpu = os.cpu_count() or 4
    env_extra = {"ARX_INNER_JOBS": str(max(2, cpu // 2) if jobs > 1 else cpu)}   # thread counts are NOT overridden: BLAS thread count changes the last digit of stiff-ODE results

    def worker(n):
        c, tags = cmds[n]
        why = "cold run requested" if cold else why_stale(n, c, envfp)
        if why is None:
            rec = load_cache(n)
            res = ("SKIP", 0.0, rec)
        else:
            rc, dt, rec = run_step(n, c, env_extra, envfp)
            res = ("OK" if rc == 0 else "FAIL", dt, rec)
        with cv:
            state[n], secs[n] = res[0], res[1]
            trace_fp[n] = footprint(res[2]) if res[2] else None
            if res[0] == "FAIL":
                failed.append(n)
            running.discard(n)
            print(f"{res[0]:4s} {n:14s} {res[1]:7.1f}s" + (f"  ({why})" if res[0] != "SKIP" and why else ""), flush=True)
            cv.notify_all()

    t0 = time.time()
    pending = list(order)
    threads = []
    with cv:
        while pending or running:
            ready = [n for n in pending if all(d in state for d in deps[n]) and not failed]
            kicad_busy = any("kicad" in cmds[r][1] for r in running)
            for n in ready:
                if len(running) >= jobs:
                    break
                if "kicad" in cmds[n][1] and kicad_busy:
                    continue
                if n in OPEN_ENDED and running:
                    continue
                if running and any(m in OPEN_ENDED for m in running):
                    break
                pending.remove(n)
                running.add(n)
                kicad_busy = kicad_busy or "kicad" in cmds[n][1]
                th = threading.Thread(target=worker, args=(n,), daemon=True)
                th.start()
                threads.append(th)
            if failed and not running:
                break
            if not ready and not running:
                break
            cv.wait(timeout=1.0)
    wall = time.time() - t0
    for th in threads:
        th.join()
    # graph check against the fresh traces
    stale = []
    run_names = [n for n in order if n in trace_fp and trace_fp[n]]
    done_state = {n: trace_fp[n] for n in run_names}
    closure = {n: set() for n in order}
    for n in order:
        for d in deps[n]:
            closure[n] |= {d} | closure[d]
    for i, x in enumerate(run_names):
        for y in run_names[i + 1:]:
            if x not in closure[y] and conflicts(done_state[x], done_state[y]):
                stale.append((x, y))
    ran = [n for n in order if state.get(n) in ("OK", "FAIL")]
    tot = sum(secs.values())
    tm = dict(wall_seconds=round(wall, 1), step_seconds_sum=round(tot, 1), jobs=jobs, ran=len(ran), skipped=sum(1 for n in order if state.get(n) == "SKIP"),
              steps={n: dict(state=state.get(n), seconds=round(secs.get(n, 0), 1)) for n in order})
    os.makedirs(PIPE, exist_ok=True)
    json.dump(tm, open(os.path.join(PIPE, "timing.json"), "w"), indent=1)
    # the graph is learned from the traces of the steps that ran; a failure of the open-ended reporting steps (status reads the regress, which fails while the graph is missing
    # steps: the catch-22 hit when Step 4 added eight steps) must not block writing it
    if "--update-graph" in a and not [f for f in failed if f not in OPEN_ENDED]:
        g = {n: trace_fp[n] for n in order if trace_fp.get(n)}
        os.makedirs(os.path.dirname(GRAPH), exist_ok=True)
        old = load_graph()
        old.update(g)
        json.dump(dict(note="learned by scripts/pipeline.py --update-graph from a traced run; paths only", steps={n: old[n] for n in NAMES if n in old}), open(GRAPH, "w"), indent=0, sort_keys=True)
        print(f"graph written: {len(old)} steps")
    print(f"pipeline: {len(ran)} ran, {tm['skipped']} skipped, wall {wall:.1f}s, sum of step times {tot:.1f}s, jobs {jobs}")
    if stale:
        print("GRAPH STALE: these step pairs conflict but were allowed to overlap (run serially with --jobs 1 --cold --update-graph): " + ", ".join(f"{x}/{y}" for x, y in stale[:6]))
    if failed:
        print("FAILED: " + ", ".join(failed) + "   (logs: work/.pipeline/logs/<step>.log)")
    return 1 if (failed or stale or len(state) < len(order)) else 0


if __name__ == "__main__":
    sys.exit(main())
