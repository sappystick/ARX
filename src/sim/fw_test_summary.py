#!/usr/bin/env python3
"""Summarise the firmware host tests (make -C fw test, log in kit_v23/fw_test.log) into kit_v23/fw_test.json: checks and failures per test program.
usage (in work/): python3 fw_test_summary.py"""
import json, re, sys
t = open("kit_v23/fw_test.log").read(); res = [dict(checks=int(a), fails=int(b)) for a, b in re.findall(r"checks (\d+), fails (\d+)", t)]
names = ["test_dsp (C vs Python reference)", "test_voice (AU1 voice)", "test_system (head <-> link <-> AU1, sweep over ground)"]
out = dict(status="MODELED: host build (gcc -std=c99 -Wall -Wextra -Werror), not run on target hardware", tests={n: r for n, r in zip(names, res)},
           ok=len(res) == 3 and all(r["fails"] == 0 for r in res), total_checks=sum(r["checks"] for r in res))
json.dump(out, open("kit_v23/fw_test.json", "w"), indent=1); print(out); sys.exit(0 if out["ok"] else 1)
