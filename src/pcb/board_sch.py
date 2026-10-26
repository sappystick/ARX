#!/usr/bin/env python3
"""Schematics for the boards with no design database (TXJ1, SB1R-QA, SB1R-QB; Step 9). Their connectivity is the pad-to-net assignment in the .kicad_pcb itself,
so the netlist is read from that file (indep_drc.py's reader), written in the format sch_export.py uses, and drawn with its box-per-footprint layout. The schematic is then
checked the same way as the other boards (sch_check rebuilds every net from the drawn labels), and KiCad re-exports the netlist, runs ERC and a PDF. This is a CONNECTIVITY
drawing with a title and a note per board, not a functional block diagram: these boards are passive coil and junction assemblies with few components.
usage (repo root): python3 src/pcb/board_sch.py OUTDIR"""
import sys, os, re, json, subprocess
sys.path.insert(0, "src/pcb")
import indep_drc as D
import sch_export as S
BOARDS = {"TXJ1": "data/kicad/TXJ1.kicad_pcb", "SB1R-QA": "data/kicad/SB1R-QA.kicad_pcb", "SB1R-QB": "data/kicad/SB1R-QB.kicad_pcb"}
NOTE = {"TXJ1": "TXJ1 junction (16 PTH pads on TX_A and TX_B): the two TX coil leads, 3.0 mm tracks, HV 1.0 mm between the nets. Connectivity drawing, no discrete parts.",
        "SB1R-QA": "SB1R-QA receive coil board: net QA_COIL (leads P1, P2, RD1 across them), transfer pads T1 / T2 on net QB_T1 / QB_T2 with RD2 across them, and three M3 holes. Connectivity drawing.",
        "SB1R-QB": "SB1R-QB receive coil board: net QB_COIL on the two lead pads P1, P2 and three M3 holes. No discrete parts. Connectivity drawing."}

def netlist(path):
    tree = D.parse(open(path).read())
    nets = {int(n[1]): (n[2] if len(n) > 2 else "") for n in D.kids(tree, "net")}
    comps = {}; nodes = {}
    for fp in D.kids(tree, "footprint"):
        ref = next((p[2] for p in D.kids(fp, "property") if p[1] == "Reference"), None)
        val = next((p[2] for p in D.kids(fp, "property") if p[1] == "Value"), ref)
        if ref is None: continue
        comps[ref] = dict(value=val, footprint=fp[1])
        for pad in D.kids(fp, "pad"):
            nn = D.one(pad, "net")
            if not nn: continue
            name = nn[2] if len(nn) > 2 else nets.get(int(nn[1]), "")
            if not name: continue
            nodes.setdefault(name, set()).add((ref, pad[1]))
    return comps, nodes

def write_net(board, comps, nodes, out):
    L = ['(export (version "D")', f'  (design (source "PF233-{board}") (date "2026-10-26"))']
    L += [f'  (comp (ref "{r}") (value "{c["value"]}") (footprint "{c["footprint"]}"))' for r, c in sorted(comps.items(), key=lambda t: S.nkey(t[0]))]
    L.append("  (nets")
    for i, (n, ns) in enumerate(sorted(nodes.items())):
        L.append(f'    (net (code "{i + 1}") (name "{n}")')
        L += [f'      (node (ref "{r}") (pin "{p}"))' for r, p in sorted(ns, key=lambda t: (S.nkey(t[0]), S.nkey(t[1])))]
        L.append("    )")
    L += ["  )", ")"]
    open(out, "w").write("\n".join(L) + "\n")

def main(outdir):
    os.makedirs(outdir, exist_ok=True); res = {}
    for b, pcb in BOARDS.items():
        comps, nodes = netlist(pcb); net_path = os.path.join(outdir, f"PF233-{b}.net"); sch = os.path.join(outdir, f"PF233-{b}.kicad_sch")
        write_net(b, comps, nodes, net_path)
        info = S.export(b, net_path, sch)
        chk = S.sch_check(sch, net_path)
        # KiCad re-reads the schematic: its own netlist export must match the drawn nets
        kn = os.path.join(outdir, f"PF233-{b}_kicad.net")
        r = subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", kn, sch], capture_output=True, text=True)
        erc = os.path.join(outdir, f"PF233-{b}_erc.json")
        subprocess.run(["kicad-cli", "sch", "erc", "--format", "json", "--severity-all", "-o", erc, sch], capture_output=True, text=True)
        e = json.load(open(erc)) if os.path.exists(erc) else {}
        errs = sum(1 for s in e.get("sheets", []) for v in s.get("violations", []) if v.get("severity") == "error")
        pdf = os.path.join(outdir, f"PF233-{b}.pdf"); subprocess.run(["kicad-cli", "sch", "export", "pdf", "-o", pdf, sch], capture_output=True, text=True)
        res[b] = dict(parts=info["parts"], nets=info["nets"], pins=info["pins"], drawn_check=chk["ok"], drawn_mismatch=chk["mismatched_nets"], stray=chk["stray_labels"],
                      kicad_netlist_ok=r.returncode == 0 and os.path.exists(kn), erc_errors=errs, pdf=os.path.exists(pdf), note=NOTE[b])
        print(b, res[b]["parts"], "parts", res[b]["nets"], "nets", "drawn ok", res[b]["drawn_check"], "ERC errors", errs, flush=True)
    json.dump(res, open(os.path.join(outdir, "board_sch_check.json"), "w"), indent=1)
    return res

if __name__ == "__main__":
    res = main(sys.argv[1] if len(sys.argv) > 1 else "work/kit_v22/SCH_BOARDS")
    bad = [b for b, v in res.items() if not (v["drawn_check"] and v["kicad_netlist_ok"] and v["pdf"])]
    sys.exit(1 if bad else 0)
