#!/usr/bin/env python3
"""Hash manifest (file, bytes, sha256) for one or more folders: the format of stl/MANIFEST.csv. Reports added / removed / changed files against the previous manifest.
usage: manifest.py OUT.csv DIR [DIR ...]      (OUT itself and SUPERSEDED notes are not listed; paths are as given, with forward slashes)"""
import sys, os, hashlib, csv
out, dirs = sys.argv[1], sys.argv[2:]
rows = []
for d in dirs:
    for root, _, files in os.walk(d):
        for f in sorted(files):
            p = os.path.join(root, f).replace(os.sep, "/")
            if os.path.abspath(p) == os.path.abspath(out): continue
            rows.append((p, os.path.getsize(p), hashlib.sha256(open(p, "rb").read()).hexdigest()))
rows.sort()
old = {}
if os.path.exists(out):
    for r in csv.DictReader(open(out)): old[r["file"]] = r["sha256"]
new = {r[0]: r[2] for r in rows}
added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new)); changed = sorted(f for f in new if f in old and new[f] != old[f])
with open(out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["file", "bytes", "sha256"]); w.writerows(rows)
print(f"manifest {out}: {len(rows)} files, {len(added)} added, {len(removed)} removed, {len(changed)} changed" + ("" if old else " (new)"))
for tag, lst in (("added", added), ("removed", removed), ("changed", changed)):
    for f in lst[:6]: print(f"  {tag}: {f}")
