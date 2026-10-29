#!/usr/bin/env python3
"""RF1 phase 3: collect the final AB1 route results (layout report, KiCad DRC, independent DRC, the placement that produced it) into results/rf1_ab1_route.json"""
import os, json
EXP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); out = {"status": "MODELED / tool-checked (KiCad 9 DRC + independent DRC); RF1 side experiment", "boards": {}}
for B in ("A", "B"):
    F = os.path.join(EXP, "build_ab1", f"final_{B}")
    if not os.path.exists(os.path.join(F, "out_board", f"AB1{B}_layout.json")): continue
    rep = json.load(open(os.path.join(F, "out_board", f"AB1{B}_layout.json")))["rep"]; kd = json.load(open(os.path.join(F, "kicad_drc.json"))); ind = json.load(open(os.path.join(F, "indep_drc.json")))
    out["boards"][B] = dict(open=len(rep["unrouted"]) + len(rep["fanout_failed"]), unrouted=rep["unrouted"], fanout_failed=rep["fanout_failed"], tracks=rep["tracks"], vias=rep["vias"],
                            kicad_errors=kd.get("errors"), kicad_unconnected=kd.get("unconnected"), kicad_warnings=kd.get("warnings"),
                            indep=ind.get("fails") if "fails" in ind else ind.get("summary", "see indep_drc.json"), placement=json.load(open(os.path.join(F, "late.json")))["late"])
json.dump(out, open(os.path.join(EXP, "results", "rf1_ab1_route.json"), "w"), indent=1); print(json.dumps({k: {kk: v[kk] for kk in ("open", "kicad_errors", "kicad_unconnected", "indep")} for k, v in out["boards"].items()}))
