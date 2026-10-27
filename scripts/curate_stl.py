#!/usr/bin/env python3
"""Copy regenerated STLs from work/ (generator output, never hand-edited) into the curated stl/ folders, and only those named below: the 15 shells that were open (non-manifold) before the closing
union of src/mech/solid_union.py, plus the two printable septum segments. Refuses a source that is not closed and oriented by print_check's definition. Then refresh the hashes: make manifest-stl.
usage (repo root, after the pipeline run): python3 scripts/curate_stl.py"""
import sys, os, glob, shutil
sys.path.insert(0, "src/mech"); import print_check as pc
NAMES = {"head": ["ANALOG_TRAY_v5", "BASE_PLATE_RX_CASSETTE_v3", "CORE_CYLINDER_v5_integrated", "HUB_CAP_HTA_v3_vault", "ROOF_PLATE_v5", "TXJ1_CRADLE_v1"], "shaft_handle": ["NPM_N1_body_with_tunnel_v2"],
         "upper": ["U1_TOP_HOUSING", "U3_BOTTOM_HOUSING", "U6_BATTERY_DOCK", "U7_BATTERY_PACK_SHELL", "U9_CAM_COLLAR", "U8_SEPTUM_extended_SEG_A", "U8_SEPTUM_extended_SEG_B"], "yoke": ["BUSHING_IN_TUBE_A", "HEEL_SADDLE_TOWER", "UMBILICAL_BRIDGE"]}
bad = 0
for folder, names in NAMES.items():
    for n in names:
        c = sorted(glob.glob(f"work/**/{n}.stl", recursive=True), key=os.path.getmtime)
        if not c: print("MISSING source", n); bad += 1; continue
        T = pc.read(c[-1]); closed, oriented, vol, nb = pc.closed_oriented(T)
        if not (closed and oriented): print(f"REFUSED {n}: closed={closed} oriented={oriented} bad_edges={nb}"); bad += 1; continue
        old = f"stl/{folder}/{n}.stl"; ov = pc.closed_oriented(pc.read(old))[2] if os.path.exists(old) else None
        shutil.copy(c[-1], old); print(f"{folder}/{n}: closed, volume {vol / 1000:.2f} cm3" + (f" (was {ov / 1000:.2f})" if ov is not None else " (new)"))
sys.exit(1 if bad else 0)
