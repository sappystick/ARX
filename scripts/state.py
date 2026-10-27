#!/usr/bin/env python3
"""One-screen resume dashboard for a new thread or a new day. Reads only files that already exist (no flow is run), so it costs about 1 s.
usage: python3 scripts/state.py [--deep]
  --deep also runs `pipeline.py plan` (which steps are stale, about 15 s) and `publish_data.py --check` (about 15 s). Strict regress is NOT run here: run it once, at the end of a change.
Exit 1 if the tree is dirty, the sign-off table has a FAIL, or the branch is not the working branch."""
import os, sys, json, subprocess, time
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANCH = "claude/hopeful-bell-wms3xo"

def sh(c):
    return subprocess.run(c, shell=True, cwd=R, capture_output=True, text=True).stdout.strip()

bad = 0
br = sh("git rev-parse --abbrev-ref HEAD"); dirty = len(sh("git status --short").splitlines())
print(f"git      {br}  {sh('git log -1 --format=%h\\ %s')[:90]}")
print(f"tree     {'clean' if not dirty else str(dirty) + ' changed file(s): commit or checkpoint before anything else'}   ahead/behind origin: {sh('git rev-list --left-right --count @{u}...HEAD 2>/dev/null') or 'no upstream'}")
bad |= bool(dirty) or br != BRANCH
try:
    s = json.load(open(os.path.join(R, "data/results/SIGNOFF_STATUS.json")))
    c = s["counts"]; print(f"signoff  {c}   (data/results/SIGNOFF_STATUS.json, written {time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(os.path.join(R, 'data/results/SIGNOFF_STATUS.json'))))})")
    bad |= bool(c.get("FAIL"))
    fails = [f"{b}:{k}" for b, row in s["boards"].items() for k, v in row.items() if v == "FAIL"] + [k for k, v in s["system"].items() if (v[0] if isinstance(v, (list, tuple)) else v) == "FAIL"]
    if fails: print("FAILING  " + ", ".join(fails))
except Exception as e:
    print(f"signoff  unreadable ({e}): run `make signoff`")
t = os.path.join(R, "work/.pipeline/timing.json")
if os.path.exists(t):
    d = json.load(open(t)); print(f"pipeline last run: {d['wall_seconds']} s, ran {d['ran']}, skipped {d['skipped']}")
else:
    print("pipeline no work/.pipeline yet: `make setup` then `make signoff` (cold ~11 min warm, longer fresh)")
print(f"work/    {'present' if os.path.isdir(os.path.join(R, 'work')) else 'MISSING: run make setup'}")
if "--deep" in sys.argv:
    p = sh("python3 scripts/pipeline.py plan | grep '^RUN'"); print("stale steps: " + (p.replace(chr(10), "; ") if p else "none"))
    print("publish  " + (sh("python3 scripts/publish_data.py --check | head -1") or "?"))
b = json.load(open(os.path.join(R, "data/handoff/blockers.json")))["items"]
print("OPEN (data/handoff/blockers.json; owner=needs a person):")
for i in b:
    print(f"  {i['id']:4s}{'[owner] ' if i['owner'] else '        '}{i['what'][:118]}")
print("next: read docs/HANDOFF_NEXT_THREAD.md sections 1-3 only; recipes in docs/PROCESS.md")
sys.exit(1 if bad else 0)
