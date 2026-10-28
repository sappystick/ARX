#!/usr/bin/env python3
"""Interactive cut-away viewer (r2; r1 = the click-to-files page, same data): placement editing with live compatibility checks, a system simulation (src/render/system_live.js, the twin of src/sim/system_live.py) and the wiring runs, on top of r1: one self-contained HTML page with the whole detector (panel 1 of blueprint_r3) and the head half-section (panel 2) drawn from the
SAME cut faces as the blueprint (BLUEPRINT_RECORD), every face tagged with the part it belongs to. Clicking a part opens its card: what it is, its check status, and
links to every file of it in the package: STL, KiCad board / rules / project, schematic, Gerber + drill zip, BOM, pick-and-place, netlist, layer PDFs, STEP, GLB,
board renders and the release folder. Parts with no face in these two cuts (pins, bushings, NPM lid and dam, cassette, PB1R, PM2, HB2, TXJ1, ...) are in the index under
the drawing. The page carries no number of its own: names, classes and hashes come from STL_CLASSIFICATION.csv, board status from data/results/SIGNOFF_STATUS.json,
board descriptions from 00_INDEX.md, printed-part specs from docs/delivery/PURCHASED_PARTS.csv and data/results/BOM_SHAFT_YOKE.csv. MODELED design, nothing built.
usage (repo root, after make_package.py): python3 src/render/viewer_r2.py [PACKAGE_DIR] [--web BRANCH OUT.html]
  default: PACKAGE_DIR/viewer.html with links relative to the package (open it from a checkout or the package folder);
  --web: links point at github.com/sappystick/ARX on BRANCH (for a hosted copy; the board renders are expected next to OUT.html under renders/boards/)."""
import os, sys, csv, json, re, html, subprocess, datetime, glob
PKG = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "deliverables/PHIFOLD233_PACKAGE_r6"
WEB = sys.argv[sys.argv.index("--web") + 1] if "--web" in sys.argv else None
OUT = sys.argv[sys.argv.index("--web") + 2] if WEB else os.path.join(PKG, "viewer.html")
GH = "https://github.com/sappystick/ARX"
FACES = os.path.join(PKG, "blueprint", "cutaway_faces.json")
if not os.path.exists(FACES):                                            # make_package.py writes it with the blueprint; standalone: record it now (same sections)
    tmp = os.path.join(PKG, "blueprint", "_viewer_tmp"); r = subprocess.run([sys.executable, "src/render/blueprint_r3.py", tmp], env=dict(os.environ, BLUEPRINT_RECORD=FACES), capture_output=True, text=True)
    if r.returncode: sys.exit("blueprint record failed: " + r.stderr[-800:])
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
F = json.load(open(FACES))
S = json.load(open("data/results/SIGNOFF_STATUS.json"))

def href(repo_path, is_dir=False):
    if WEB: return f"{GH}/{'tree' if is_dir else 'blob'}/{WEB}/{repo_path}"
    return os.path.relpath(repo_path, os.path.dirname(OUT) or ".")
def ok_for_link(p): return os.path.exists(p) and (not WEB or subprocess.run(["git", "check-ignore", "-q", p]).returncode != 0)
FMT = {".stl": "STL", ".kicad_pcb": "KiCad board", ".kicad_dru": "KiCad rules", ".kicad_pro": "KiCad project", ".kicad_sch": "KiCad schematic", ".pdf": "PDF", ".zip": "Gerber + drill",
       ".csv": "CSV", ".net": "Netlist", ".step": "STEP", ".glb": "GLB", ".png": "PNG", ".md": "Markdown", ".json": "JSON"}
def fobj(p, label=None, is_dir=False):
    ext = os.path.splitext(p)[1].lower(); return dict(label=label or os.path.basename(p.rstrip("/")), fmt="folder" if is_dir else FMT.get(ext, ext[1:].upper()), href=href(p, is_dir))
slug = lambda s: re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()

# ---------------------------------------------------------------- printed parts: STL_CLASSIFICATION.csv + specs
specs = {}
for p in ("docs/delivery/PURCHASED_PARTS.csv", "data/results/BOM_SHAFT_YOKE.csv"):
    for r in csv.DictReader(open(p)):
        if r["section"] == "printed": specs.setdefault(r["item"], (r.get("spec / value") or r.get("spec") or "").strip())
GROUP = {"head": "Head", "formers": "Coil formers", "yoke": "Yoke and shaft fittings", "shaft_handle": "Neck module and cassette", "upper": "Upper assembly", "pins": "Alignment pins"}
items = {}
for r in csv.DictReader(open(os.path.join(PKG, "STL_CLASSIFICATION.csv"))):
    if r["class"] not in ("PRINT", "REFERENCE"): continue
    sub = r["file"].split("/")[1]; name = os.path.splitext(os.path.basename(r["file"]))[0]
    pp = os.path.join(PKG, "stl_print" if r["class"] == "PRINT" else "stl_reference", *r["file"].split("/")[1:])
    files = [fobj(pp)] if ok_for_link(pp) else []
    key = name.replace("_petal_coil_former", "")
    it = items.setdefault(slug(key), dict(id=slug(key), name=key, group=GROUP.get(sub, sub) if r["class"] == "PRINT" else "Fit references", kind=r["class"].lower(), facts=[], files=[], related=[]))
    it["files"] += files
    it["facts"].append(["Class", r["class"] + (" (" + r["note"] + ")" if r["note"] else "")])
    if specs.get(key) or specs.get(name): it["facts"].append(["Print spec", specs.get(key) or specs[name]])
    it["facts"].append(["SHA-256", r["sha256"][:16] + "...", r["sha256"]]); it["facts"].append(["Size", f"{int(r['bytes']) / 1e6:.2f} MB"])
    if not files: it["note"] = ("Not in git (about 70 MB each): build it with make formers-print; it is then written to stl_print/formers/." if sub == "formers"
                                else "File not present in this copy of the package.")
# formers rows are generated (not in the classification when absent): make sure L1..L6 exist
for k in range(1, 7):
    key = f"FORMER_L{k}"; p = os.path.join(PKG, "stl_print", "formers", f"{key}_petal_coil_former.stl")
    if slug(key) not in items:
        items[slug(key)] = dict(id=slug(key), name=key, group="Coil formers", kind="print", facts=[["Print spec", specs.get(key, "")]] if specs.get(key) else [], related=[],
                                files=[fobj(p)] if ok_for_link(p) else [], note=None if ok_for_link(p) else "Not in git (about 70 MB each): build it with make formers-print; it is then written to stl_print/formers/.")
# ---------------------------------------------------------------- boards
desc = {}
for line in open(os.path.join(PKG, "00_INDEX.md")):
    m = re.match(r"\| ((\S+?)(?:-B)? [^|]+?) \| [^|]+ \| [^|]+ \|$", line.rstrip("\n"))      # section 2 board table: first cell = description, its first word = board
    if m and os.path.isdir(os.path.join(PKG, "manufacturing", m.group(2))): desc[m.group(2)] = m.group(1)
REL = {b: ("releases/TX_r4" if b in ("PB1R", "CB1D", "TXJ1", "PM2", "HB2") else "releases/RX_r3" if b in ("AB1A", "AB1B") else None) for b in desc}
WHERE = {"PB1R": "Neck module pocket (NPM N1)", "PM2": "Bottom housing U3, battery dock", "HB2": "Top housing U1, grip", "TXJ1": "TXJ1 cradle at the 178 deg heel window",
         "SB1R-QA": "Base-plate recess (pair with SB1R-QB)", "SB1R-QB": "Base-plate recess (pair with SB1R-QA)", "AB1A": "L2 analog cell on the tray", "AB1B": "L2 analog cell on the tray",
         "CB1D": "L5, rotated 180 deg in the rib slots", "LB1": "L6 display under the roof", "HTA": "Cap (L8), timing coil and light pipes"}
for b in sorted(desc):
    pat = re.compile(rf"^(PF233-)?{re.escape(b)}(_routed)?\.kicad_(pcb|dru|pro)$")
    files = [fobj(os.path.join(PKG, "kicad", f)) for f in sorted(os.listdir(os.path.join(PKG, "kicad"))) if pat.match(f)]
    files += [fobj(os.path.join(PKG, "schematics", f)) for f in sorted(os.listdir(os.path.join(PKG, "schematics"))) if f.startswith(f"PF233-{b}_")]
    md = os.path.join(PKG, "manufacturing", b)
    if os.path.isdir(md):
        order = lambda f: (0 if f.endswith(".zip") else 1 if "BOM" in f else 2 if "pickplace" in f else 3 if f.endswith(".net") else 4 if f.endswith(".step") else 5, f)
        files += [fobj(os.path.join(md, f)) for f in sorted(os.listdir(md), key=order)]
    g = os.path.join(PKG, "models3d", f"{b}_with_components.glb")
    if os.path.exists(g): files.append(fobj(g))
    thumbs = [href(os.path.join(PKG, "renders", "boards", f"{b}_{s}.png")) if not WEB else f"renders/boards/{b}_{s}.png" for s in ("top", "bottom") if os.path.exists(os.path.join(PKG, "renders", "boards", f"{b}_{s}.png"))]
    if REL[b] and os.path.isdir(os.path.join(REL[b], b)): files += [fobj(os.path.join(REL[b], b), f"{REL[b].split('/')[1]} release folder", True), fobj(os.path.join(REL[b], "RELEASE.md"), f"{REL[b].split('/')[1]} RELEASE.md")]
    row = S["boards"].get(b, {})
    items[slug(b)] = dict(id=slug(b), name=b, group="Boards", kind="board", facts=[["Board", desc[b]], ["Where", WHERE.get(b, "")]], files=files, related=[], thumbs=thumbs,
                          checks=[[k, v["state"], v["detail"]] for k, v in row.items()])
# ---------------------------------------------------------------- purchased tubes (no STL: bought parts)
for tag, row in (("TUBE_A_CFRP", "tube A (hand end)"), ("TUBE_B_CFRP", "tube B"), ("TUBE_LOWER_GFRP", "lower fixed tube")):
    spec = next((r for r in csv.DictReader(open("data/results/BOM_SHAFT_YOKE.csv")) if r["item"] == row), None)
    items[slug(tag)] = dict(id=slug(tag), name=tag, group="Purchased", kind="purchased", related=[],
                            facts=[["Item", row], ["Spec", spec["spec"] if spec else "see BOM"], ["Mass", (spec or {}).get("note", "")]],
                            files=[fobj("data/results/BOM_SHAFT_YOKE.csv", "BOM_SHAFT_YOKE.csv")], note="Bought tube: cut to length, no print file.")
# ---------------------------------------------------------------- cut-face tags -> items, relations
TAG = {"SB1R-QA": ["sb1r-qa", "sb1r-qb"], "U8_SEPTUM_extended": ["u8-septum-extended", "u8-septum-extended-seg-a", "u8-septum-extended-seg-b"]}
REL_ITEMS = {"txj1-cradle-v1": ["txj1"], "npm-n1-body-with-tunnel-v2": ["pb1r", "npm-n2-lid-with-fill-ports", "npm-n3-hot-zone-dam-v2"], "u1-top-housing": ["hb2"],
             "u3-bottom-housing": ["pm2"], "hub-cap-hta-v3-vault": ["hta"], "base-plate-rx-cassette-v3": ["sb1r-qa", "sb1r-qb"], "lotus-hood-carrier-v3-butted": ["ferrite-tile-inner-v3-reference", "ferrite-tile-outer-v3-reference"],
             "core-cylinder-v5-integrated": ["spine-comb-v5", "analog-tray-v5", "septum-frame-v5"], "u8-septum-extended": ["u8-septum-extended-seg-a", "u8-septum-extended-seg-b"],
             "tube-a-cfrp": ["bushing-in-tube-a", "telescope-lock-collar"], "tube-b-cfrp": ["bushing-on-tube-b"]}
for a, bs in REL_ITEMS.items():
    for b in bs:
        if a in items and b in items:
            items[a]["related"].append(b); items[b]["related"].append(a)
def tag_items(t): return [i for i in TAG.get(t, [slug(t)]) if i in items]
panels = {}
missing = set()
for pn, P in F.items():
    faces = []
    for f in P["faces"]:
        ids = tag_items(f["tag"])
        if not ids: missing.add(f["tag"]); continue
        d = " ".join("M" + " L".join(f"{x:g},{-y:g}" for x, y in ring) + " Z" for ring in f["rings"])
        faces.append(dict(id=ids[0], also=ids[1:], fc=f["fc"], d=d))
    panels[pn] = dict(faces=faces, xlim=P["xlim"], ylim=P["ylim"])
if missing: sys.exit(f"cut-face tags with no item: {sorted(missing)}")
for it in items.values():
    it["in_cut"] = sorted({pn for pn, P in panels.items() for f in P["faces"] if f["id"] == it["id"] or it["id"] in f["also"]})
    it["related"] = sorted(set(it["related"]))
DOCS = [(os.path.join(PKG, "00_INDEX.md"), "Package index (what is verified, what is open)"), (os.path.join(PKG, "blueprint", "PHIFOLD233_FULL_SYSTEM_LAYERED_CUTAWAY_r3.pdf"), "Layered cut-away blueprint"),
        (os.path.join(PKG, "blueprint", "PHIFOLD233_RECEIVE_CUTAWAY_AB1.pdf"), "Receive-stage cut-away"), (os.path.join(PKG, "STL_CLASSIFICATION.csv"), "STL classification and hashes"),
        ("docs/STATUS.md", "Sign-off table"), ("docs/delivery/ASSEMBLY_ORDER.md", "Assembly order"), ("docs/delivery/POTTING_SEQUENCE.md", "Potting sequence"),
        ("docs/delivery/PURCHASED_PARTS.csv", "Purchased parts"), ("data/results/BOM_SHAFT_YOKE.csv", "Shaft and yoke BOM"), ("releases/TX_r4/RELEASE.md", "Release TX_r4"), ("releases/RX_r3/RELEASE.md", "Release RX_r3")]
docs = [fobj(p, l) for p, l in DOCS if os.path.exists(p)]
c = S["counts"]
meta = dict(generated=datetime.date.today().isoformat(), status=f"{c['PASS']} PASS / {c['FAIL']} FAIL / {c['UNVERIFIED']} UNVERIFIED", unverified=[u if isinstance(u, str) else u.get("id", str(u)) for u in S.get("unverified", [])],
            web=bool(WEB), branch=WEB)
GORDER = ["Head", "Coil formers", "Boards", "Yoke and shaft fittings", "Neck module and cassette", "Upper assembly", "Alignment pins", "Purchased", "Fit references"]
# ---------------------------------------------------------------- r2: who generates each part (pipeline graph), placement rules, the system model, build stamp
G = json.load(open("data/pipeline/graph.json"))["steps"]; import importlib.util as _iu
_sp = _iu.spec_from_file_location("pipeline_steps", "scripts/pipeline.py"); STEPCMD = {}
for line in open("scripts/pipeline.py"):
    m = re.match(r'\s*\("([a-z0-9-]+)",(.*?), "[^"]*"\),', line)                    # ("step", <command expression>, "note"),
    if m: STEPCMD[m.group(1)] = re.findall(r"python3 ([\w./-]+\.py)", m.group(2))
for it in items.values():
    if it["kind"] in ("print", "reference"):
        nm = it["name"] + ("_petal_coil_former" if it["group"] == "Coil formers" else "") + ".stl"
        own = [s for s, v in G.items() if s not in ("curate",) and any(os.path.basename(w) == nm for w in v.get("W", []))]
        if own: it["owner"] = dict(step=own[0], scripts=STEPCMD.get(own[0], []))
    elif it["kind"] == "board":
        own = [s for s, v in G.items() if any(re.search(rf"(^|/)(PF233-)?{re.escape(it['name'])}(_routed)?\.kicad_pcb$", w) for w in v.get("W", []))]
        if own: it["owner"] = dict(step=own[0], scripts=STEPCMD.get(own[0], []))
_SRC = {f: open(f).read() for f in sorted(glob.glob("src/**/*.py", recursive=True))}
for it in items.values():                                                  # parts no traced pipeline step writes: the generator named in the source, the Makefile target, or the archive copy
    if it.get("owner") or it["kind"] not in ("print", "reference"): continue
    if it["group"] == "Coil formers": it["owner"] = dict(step=None, scripts=["phifold_v15.py print"], note="make formers-print (not a pipeline step: about 70 MB each)"); continue
    key = "PIN_interface" if it["name"].startswith("PIN_interface") else it["name"]
    hits = [f for f, t in _SRC.items() if f'"{key}' in t and ("emit(" in t or "write_stl" in t) and "/render/" not in f and "check" not in os.path.basename(f) and "audit" not in os.path.basename(f) and "mfg_" not in os.path.basename(f)]
    if hits:
        f = sorted(hits, key=lambda x: "/archive/" in x)[0]
        it["owner"] = dict(step=None, scripts=[f], note="ARCHIVED generator: the pipeline does not rebuild this STL (CORRECTIONS)" if "/archive/" in f else "generator not run by the pipeline graph")
stack = json.load(open("data/results/stack_check.json"))
SPAIR = [(r"^AB1A top vs septum", "ab1a", "septum-frame-v5"), (r"^AB1B top vs septum", "ab1b", "septum-frame-v5"), (r"^CB1D top parts vs LB1", "cb1d", "lb1"),
         (r"^LB1 LED tops .* vs roof", "lb1", "roof-plate-v5"), (r"^LB1 tallest part .* vs cap", "lb1", "hub-cap-hta-v3-vault")]          # vertical rows only: gap = upper z - lower z
for r in stack:
    for pat, lo, up in SPAIR:
        if re.search(pat, r["check"]): r["lower"], r["upper"] = lo, up
sim = json.load(open("data/results/system_live.json")); sim["golden"] = sim["golden"][:4]          # the page re-checks itself against four reference cases on load
commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
meta.update(commit=commit, model=sim["model"])
data = dict(items=sorted(items.values(), key=lambda i: (GORDER.index(i["group"]) if i["group"] in GORDER else 99, i["name"])), panels=panels, docs=docs, meta=meta, groups=GORDER,
            sim=sim, stack=stack, rules=dict(min_gap_mm=min(r["required_mm"] for r in stack if r["required_mm"] > 0), source="data/results/stack_check.json (smallest required vertical gap)"))
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer_r2.html")).read()
simjs = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_live.js")).read()
page = tpl.replace("/*SIMJS*/", simjs).replace("/*DATA*/null", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
if not WEB: page = "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n" + page.replace("<!--BODY-->", "</head><body>") + "</body></html>"
else: page = page.replace("<!--BODY-->", "")
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True); open(OUT, "w").write(page)
nf = sum(len(i["files"]) for i in items.values())
print(f"viewer: {OUT} | {len(items)} items, {sum(len(P['faces']) for P in panels.values())} cut faces, {nf} file links, {sum(1 for i in items.values() if i['in_cut'])} items in the cuts")
