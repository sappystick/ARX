#!/bin/sh
# Wait for the active pipeline run to end, by its pid (work/.pipeline/run.json), never by a process-name search:
# `pgrep -f scripts/pipeline.py` also matches the waiting shell's own command line, so such a waiter never ends (2026-10-28: three waiters ran 15-30 min after their run finished).
# usage: scripts/wait_run.sh [MAX_SECONDS=1800] [LOG]   exit 0 = run ended (prints its summary lines from LOG), 2 = no active run, 124 = still running at MAX_SECONDS
MAX=${1:-1800}; LOG=$2; RUN=work/.pipeline/run.json
cd "$(dirname "$0")/.." || exit 1
[ -f "$RUN" ] || { echo "wait_run: no active pipeline run"; exit 2; }
PID=$(python3 -c "import json;print(json.load(open('$RUN'))['pid'])" 2>/dev/null) || { echo "wait_run: unreadable $RUN"; exit 2; }
T=0
while kill -0 "$PID" 2>/dev/null; do
  [ "$T" -ge "$MAX" ] && { echo "wait_run: pid $PID still running after $MAX s"; exit 124; }
  sleep 5; T=$((T + 5))
done
echo "wait_run: pipeline pid $PID ended after ${T} s of waiting"
[ -n "$LOG" ] && grep -E "^FAIL|^pipeline:|^FAILED|TIMEOUT|SIGNOFF_RC" "$LOG" | tail -6
exit 0
