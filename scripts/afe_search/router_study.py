#!/usr/bin/env python3
"""B9 study: single-pass router vs rip-up router (src/pcb/afe_ripup.py) on perturbed AB1A / AB1B placements, with the production DRC gates.
Perturbations (per board): the 8 orientations of the AD7389-4 (rotation 0/90/180/270 x back/front, AFE_UA7ROT / AFE_UA7SIDE; 270/back is the committed one) and
N_NUDGE seeded sets of part nudges (4 parts each, +/-0.3 mm in x or y, added to the committed BOARD_CFG7 nudges). A case whose placement check fails is reported as
'invalid placement' and counted for neither router. A router 'wins' a case when it leaves 0 unrouted connections and 0 failed plane fanouts AND the board then passes
the same gates as production: KiCad 9 DRC 0 errors / 0 unconnected, independent DRC 0 fails, +3V3D island check pass.
STUDY ONLY: it overwrites work/out_board/AB1x_layout.json and work/kit_v3/PCB_AB1x: finish with `make rx-board` (trap 1 in docs/HANDOFF_NEXT_THREAD.md).
usage (repo root): python3 scripts/afe_search/router_study.py OUT.json [N_NUDGE]"""
import os, sys, json, random, subprocess, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")); WK = os.path.join(ROOT, "work")
OUT = sys.argv[1]; N_NUDGE = int(sys.argv[2]) if len(sys.argv) > 2 else 8
BASE_NUDGE = {"A": "SW2:0.4:0,CBD:-0.3:0,CRF:0:-0.3", "B": "RD2:0.4:0,CRF:0:-0.3"}          # = BOARD_CFG7 (afe_layout.py)
MOVABLE = {"A": ["SW1", "SW2", "SW3", "D1", "D2", "D3", "RG1", "RG2", "RG3", "RF1", "RF2", "RF3", "CF1", "CF2", "CF3", "RAAF1", "RAAF2", "RAAF3", "CAAF1", "CAAF2", "CAAF3", "RS1", "RS2", "RS3", "CRF", "CRC", "CBD", "RD1", "RD2"],
           "B": ["SW1", "SW2", "D1", "D2", "RG1", "RG2", "RF1", "RF2", "CF1", "CF2", "RAAF1", "RAAF2", "CAAF1", "CAAF2", "RS1", "RS2", "CRF", "CRC", "CBD", "RD1", "RD2"]}

def sh(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)

def gates(b, env):
    e = dict(env, BOARD=b)
    if sh([sys.executable, "afe_export.py"], e, WK).returncode: return dict(ok=False, why="export failed")
    pcb = f"work/kit_v3/PCB_AB1{b}/PF233-AB1{b}.kicad_pcb"; kj = f"work/.study_kdrc_{b}.json"; ij = f"work/.study_idrc_{b}.json"; sj = f".study_isl_{b}.json"
    sh([sys.executable, "src/pcb/kicad_drc.py", pcb, kj, f"AB1{b}"], e, ROOT); sh([sys.executable, "src/pcb/indep_drc.py", f"AB1{b}", pcb, ij], e, ROOT)
    sh([sys.executable, "ab1_island_check.py", sj], e, WK)
    try:
        k = json.load(open(os.path.join(ROOT, kj))); i = json.load(open(os.path.join(ROOT, ij))); s = json.load(open(os.path.join(WK, sj)))
    except Exception as ex: return dict(ok=False, why=f"gate output missing: {ex}")
    ok = (not k["errors"]) and k["unconnected"] == 0 and i["n_fail"] == 0 and s["pass"]
    return dict(ok=ok, kicad_errors=k["errors"], unconnected=k["unconnected"], indep_fails=i["n_fail"], island=s["pass"])

def cases(b):
    out = [("orient %d/%s" % (r, sd), dict(AFE_UA7ROT=str(r), AFE_UA7SIDE=sd)) for sd in ("B", "F") for r in (0, 90, 180, 270)]
    rng = random.Random(1000 + ord(b))
    for n in range(N_NUDGE):
        parts = rng.sample(MOVABLE[b], 4); nud = []
        for p in parts:
            d = rng.choice((-0.3, 0.3)); nud.append(f"{p}:{d}:0" if rng.random() < 0.5 else f"{p}:0:{d}")
        out.append((f"nudge {n}: " + " ".join(nud), dict(AFE_NUDGE=BASE_NUDGE[b] + "," + ",".join(nud))))
    return out

def main():
    res = []; t0 = time.time()
    for b in "AB":
        for name, env0 in cases(b):
            env = dict(os.environ, BOARD=b, **env0); row = dict(board=f"AB1{b}", case=name)
            p = sh([sys.executable, "afe_layout.py", "--route"], env, WK)
            r = json.load(open(os.path.join(WK, f"out_board/AB1{b}_layout.json")))["rep"] if p.returncode == 0 else None
            if r is None or r["placement_errors"]:
                row["invalid_placement"] = (r or {}).get("placement_errors", ["layout failed"])[:3]; res.append(row); print(row, flush=True); continue
            row["single"] = dict(unrouted=len(r["unrouted"]), fanout_failed=len(r["fanout_failed"]))
            row["single"]["gates"] = gates(b, env) if not r["unrouted"] and not r["fanout_failed"] else dict(ok=False, why="open")
            q = sh([sys.executable, "afe_ripup.py", b, "6", f"out_board/.study_ripup_{b}.json"], env, WK)
            rr = json.load(open(os.path.join(WK, f"out_board/.study_ripup_{b}.json"))) if os.path.exists(os.path.join(WK, f"out_board/.study_ripup_{b}.json")) else dict(ok=False, rounds=[])
            last = rr["rounds"][-1] if rr["rounds"] else {}
            row["ripup"] = dict(rounds=len(rr["rounds"]) - 1, unrouted=len(last.get("unrouted", [1])), fanout_failed=len(last.get("fanout_failed", [])))
            if rr.get("ok"): row["ripup"]["gates"] = gates(b, dict(env, **rr.get("final_env", {})))
            else: row["ripup"]["gates"] = dict(ok=False, why="open")
            res.append(row); print({k: v for k, v in row.items()}, flush=True)
            json.dump(dict(rows=res), open(OUT, "w"), indent=1)
    summ = {}
    for b in ("AB1A", "AB1B", "both"):
        rows = [r for r in res if (b == "both" or r["board"] == b) and "single" in r]
        summ[b] = dict(valid_cases=len(rows), invalid_placement=sum(1 for r in res if (b == "both" or r["board"] == b) and "invalid_placement" in r),
                       single_pass_wins=sum(r["single"]["gates"]["ok"] for r in rows), ripup_wins=sum(r["ripup"]["gates"]["ok"] for r in rows))
        for k in ("single_pass", "ripup"):
            summ[b][k + "_rate"] = round(summ[b][k + "_wins"] / max(1, len(rows)), 3)
    json.dump(dict(rows=res, summary=summ, wall_s=round(time.time() - t0, 1), note="STUDY: production files overwritten; run make rx-board after"), open(OUT, "w"), indent=1)
    print(json.dumps(summ, indent=1))

if __name__ == "__main__": main()
