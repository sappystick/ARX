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
  * Steps tagged 'kicad' never overlap each other (memory); BLAS threads are divided between parallel jobs.
usage: python3 scripts/pipeline.py run [--jobs N] [--cold] [--only STEP[,STEP]] [--update-graph] [--no-setup]
       python3 scripts/pipeline.py plan          (what would run and why; runs nothing)
       python3 scripts/pipeline.py list
Outputs: work/.pipeline/{cache,logs,timing.json}; exit 1 if any step fails or the graph is stale."""
import os, sys, json, time, hashlib, subprocess, threading, shlex, shutil, platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = os.path.join(ROOT, "work", ".pipeline")
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
    ("pcb-pb1r", W + "PW=R python3 pw_design.py && PW=R python3 pw_export.py", ""),
    ("pcb-cb1d", W + "PW=C DISC=1 python3 pw_design.py && PW=C DISC=1 python3 cb1d_export.py", ""),
    ("tx-vbus", W + "mkdir -p kit_v23 && python3 tx_vbus_sweep.py", ""),
    ("pcb-pm2", W + "PW=P python3 pw_design.py && PW=P python3 pw_export.py && python3 power_dock_check.py", ""),
    ("upper", W + "python3 shaft_calc_v20.py > /dev/null && python3 upper_v21.py && python3 upper_check.py && python3 upper_figure.py", ""),
    ("sim-head2", W + "python3 sim_head2.py > /dev/null", ""),
    ("tx", W + "python3 tx_system.py", ""),
    ("audit-system", W + "python3 wiring_audit.py && python3 system_budget.py && python3 stack_check.py && python3 interference_audit.py", ""),
    ("sch", W + "python3 sch_export.py && python3 trigger_check.py", ""),
    ("sims-rx", W + "python3 sim_cage_rx.py && python3 sim_tanr.py && python3 sim_quadbearing.py", ""),
    ("route-lb1", route("LB1"), ""),
    ("gerber-lb1", W + "python3 gerber_out.py LB1 hatch notch-1", ""),
    ("route-cb1d", route("CB1D"), ""),
    ("gerber-cb1d", W + "python3 gerber_out.py CB1D hatch notch1 hv=COIL_A,COIL_B,DM1,DM2 && python3 gerber_hv_check.py CB1D kit_v22/GERBER_CB1D_v2 PF233-CB1D-v2 COIL_A,COIL_B,DM1,DM2", ""),
    ("route-pb1r", route("PB1R") + " && python3 viafarm.py PB1R kit_v20/route_PB1R.json", ""),
    ("drc-lb1", W + "python3 drc.py LB1 kit_v20/route_LB1.json -1", ""),
    ("drc-cb1d", W + "python3 drc.py CB1D kit_v20/route_CB1D.json 1 COIL_A,COIL_B,DM1,DM2", ""),
    ("drc-pb1r", W + "python3 drc.py PB1R kit_v20/route_PB1R.json 0 DRAIN1,CLAMP1", ""),
    ("kicad-lb1", "mkdir -p work/kit_v22/KICAD && " + W + "python3 kicad_inject.py LB1 kit_v20/route_LB1.json kit_v22/KICAD/PF233-LB1_routed.kicad_pcb -1", ""),
    ("kicad-cb1d", "mkdir -p work/kit_v22/KICAD && " + W + "python3 kicad_inject.py CB1D kit_v20/route_CB1D.json kit_v22/KICAD/PF233-CB1D_routed.kicad_pcb 1 six", ""),
    ("kicad-pb1r", "mkdir -p work/kit_v22/KICAD && " + W + "python3 rect_inject.py PB1R kit_v20/route_PB1R.json kit_v6/PB1R/PF233-PB1R.kicad_pcb kit_v22/KICAD/PF233-PB1R_routed.kicad_pcb", ""),
    ("gerber-pb1r", "python3 src/pcb/kicad_gerber.py work/kit_v22/KICAD/PF233-PB1R_routed.kicad_pcb PB1R work/kit_v22/GERBER_PB1R PF233-PB1R && "
                    + W + "python3 gerber_plane_check.py PB1R kit_v22/GERBER_PB1R PF233-PB1R DRAIN1,CLAMP1 In1:GND,In2:VBUS", "kicad"),
    ("sbq-fast", W + "python3 sbq_gen2.py && python3 sbq_export.py && python3 sbq_sim.py && python3 sbq_damp2.py", ""),
    ("pcb-hta", W + "python3 hta_gerber.py > /dev/null", ""),
    ("kicad-drc", "; ".join([f"python3 src/pcb/kicad_drc.py work/kit_v22/KICAD/PF233-{b}_routed.kicad_pcb work/kit_v22/kicad_drc_{b}.json {b} | head -1" for b in ("CB1D", "LB1", "PB1R")]
                  + ["python3 src/pcb/kicad_drc.py work/kit_v22/KICAD_TXJ1/TXJ1.kicad_pcb work/kit_v22/kicad_drc_TXJ1.json TXJ1 | head -1"]
                  + [f"python3 src/pcb/kicad_drc.py work/kit_v22/KICAD_SBQ/{b}.kicad_pcb work/kit_v22/kicad_drc_{b}.json {b} | head -1" for b in ("SB1R-QA", "SB1R-QB")]), "kicad"),
    ("check-pb1r", W + "mkdir -p kit_v23 && python3 tx_vbus_sweep.py > /dev/null && python3 pb1r_check.py", ""),
    ("formers-low", "test -f work/kit_v15/LOW/FORMER_L1_petal_coil_former.stl || (" + W + "python3 phifold_v15.py low)", ""),
    ("head-audit", W + "mkdir -p kit_v21 && python3 head_crosscheck.py && python3 fine_check.py && python3 head_drawings.py", ""),
    ("publish", "python3 scripts/publish_data.py", ""),
    ("controls", "python3 tests/release_signoff_controls.py", ""),
    ("status", "python3 scripts/signoff_status.py", ""),
]
NAMES = [s[0] for s in STEPS]
IGNORE_READS = {"controls": {"data/results/SIGNOFF_STATUS.json", "docs/STATUS.md"}}   # the controls only use the previous table as a template; it is rewritten by the step after them (would re-run them forever)
OPEN_ENDED = {"publish", "controls", "status"}  # always run alone, last, in order (controls temporarily edit a work/ file)


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
        if sha_dir(os.path.join(ROOT, d)) != h:
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
        r = subprocess.run(["/bin/sh", "-c", cmd], cwd=ROOT, env=env, stdout=lg, stderr=subprocess.STDOUT)
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
    d = {"R": sorted(p for p in rec["reads"] if p not in rec["writes"]), "W": sorted(rec["writes"]), "L": sorted(rec["lists"])}
    return d


def conflicts(a, b):
    """True if steps a (earlier) and b (later) must not overlap, from their footprints."""
    aw, bw, ar, br = set(a["W"]), set(b["W"]), set(a["R"]), set(b["R"])
    if aw & (bw | br) or ar & bw:
        return True
    for lst, other in ((a["L"], b["W"]), (b["L"], a["W"])):
        if any(os.path.dirname(w) == d or w.startswith(d + "/") for d in lst for w in other):
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
    env_extra = {"OMP_NUM_THREADS": str(max(1, cpu // jobs)), "OPENBLAS_NUM_THREADS": str(max(1, cpu // jobs)), "MKL_NUM_THREADS": str(max(1, cpu // jobs))}

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
    if "--update-graph" in a and not failed:
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
