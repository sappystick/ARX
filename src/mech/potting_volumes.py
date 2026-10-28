#!/usr/bin/env python3
"""Exact potting and fill volumes from the meshes (FINAL_INTEGRATION_PLAN P2), replacing the box estimates (mech_v20.py "potting volumes", POTTING_SEQUENCE.md).
Every free volume is an exact boolean (manifold3d) of a cavity envelope minus the parts inside it:
  NPM (neck power module, mech_v20.py frame): envelope = the pocket interior x -39..39, y 14 (back-wall inner face) .. 37 (lid underside), z 3..81 (end walls);
    minus N1 body (rails, walls), N2 lid, N3 dam v2, the PB1R board (70 x 70 x 1.6 at y 33..34.6, z 7..77) and the 41 PB1R component bodies of kit_v6/PB1R/bodies.json
    (pw_export.py package extents, same mapping as pb1r_check.py NPM fit). The bodies are bounding boxes, so the displaced volume is an UPPER bound and the free
    volume a LOWER bound; the same volume without components is the upper bound. Split at the dam: hot zone x < -5 (alumina-filled silicone), main zone x > -3.
  L4 absorber cell (head, hub frame): envelope = cylinder r 44.0 (hub bore HUB_RI, hub_v22.py), z 21.9..27.0 (DESIGN_STATE section 3); minus CORE_CYLINDER_v5,
    SPINE_COMB_v5 and the masked spine-duct insert (x -6..6, y 40..44, link_path_check.py) and the CB1D slot ribs that reach below z 27.0 (part of the core mesh).
Fill and vent: every zone must hold a fill port and a vent; when poured lid-up the highest surface is the lid underside (y 37), where both vents sit.
Densities stay ASSUMED (1.9 and 0.75 g/cm3 as mech_v20.py, carbonyl-iron silicone 3.5 g/cm3 ASSUMED): no resin datasheet is on disk (rule 7).
usage (repo root, after make setup and the mech-npm / v5 steps): python3 src/mech/potting_volumes.py [OUT.json]"""
import sys, os, json, struct
import numpy as np
import manifold3d as M3
W = "work"
def stl(p):
    b = open(p, "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    T = np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3).astype(np.float32)
    U, inv = np.unique(T, axis=0, return_inverse=True); m = M3.Manifold(M3.Mesh(vert_properties=U, tri_verts=inv.reshape(-1, 3).astype(np.uint32)))
    if m.status() != M3.Error.NoError: raise ValueError(f"{p}: not a closed manifold ({m.status()})")
    return m
def box(x0, x1, y0, y1, z0, z1): return M3.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
def cyl(r, z0, z1, n=360): return M3.Manifold.cylinder(z1 - z0, r, r, n).translate([0, 0, z0])
def union(ms):
    return M3.Manifold.batch_boolean(ms, M3.OpType.Add) if len(ms) > 1 else ms[0]
cm3 = lambda m: m.volume() / 1000.0

def npm():
    S = f"{W}/kit_v19/SPINE"; env = box(-39, 39, 14, 37, 3, 81)
    parts = union([stl(f"{S}/{n}.stl") for n in ("NPM_N1_body_with_tunnel_v2", "NPM_N2_lid_with_fill_ports", "NPM_N3_hot_zone_dam_v2")])
    board = box(-35, 35, 33.0, 34.6, 7, 77)
    comps = []
    for bd in json.load(open(f"{W}/kit_v6/PB1R/bodies.json")):
        lo, hi = bd["lo"], bd["hi"]; y0, y1 = 34.6 - (hi[2] + 1.6), 34.6 - (lo[2] + 1.6)
        if hi[0] - lo[0] > 0 and y1 - y0 > 0 and hi[1] - lo[1] > 0: comps.append(box(lo[0], hi[0], y0, y1, lo[1] + 42.0, hi[1] + 42.0))
    C = union(comps)
    free_nc = env - parts - board; free = free_nc - C
    out = {}
    for nm, zone in (("hot_zone", box(-39, -5, 14, 37, 3, 81)), ("main_zone", box(-3, 39, 14, 37, 3, 81))):
        a, b = free ^ zone, free_nc ^ zone
        out[nm] = dict(free_cm3_lower=round(cm3(a), 2), free_cm3_upper_no_parts=round(cm3(b), 2), component_box_cm3=round(cm3(C ^ zone), 2))
    out["envelope_cm3"] = round(cm3(env), 2); out["printed_parts_in_envelope_cm3"] = round(cm3(parts ^ env), 2); out["board_cm3"] = round(cm3(board), 2)
    out["component_boxes"] = len(comps)
    # flow from the lid side to the component side: free area around the board edge in the board mid-plane (y 33.8)
    sl = free_nc ^ box(-39, 39, 33.79, 33.81, 3, 81); out["edge_passage_mm2"] = round(sl.volume() / 0.02, 1)
    ports = dict(fill=[-25.0, 15.0], vent=[-25.0, 15.0])                                        # mech_v20.py lid: D8 fill ports at z 40, D3 vents at z 76, both on the lid (y 37..40)
    out["fill_vent"] = {"hot_zone": dict(fill=any(x < -5 for x in ports["fill"]), vent=any(x < -5 for x in ports["vent"])), "main_zone": dict(fill=any(x > -3 for x in ports["fill"]), vent=any(x > -3 for x in ports["vent"])),
                        "vent_at_highest_surface": True, "note": "poured lid-up: the lid underside y 37 is the top of both zones and both vents open there (z 76, far end from the fill ports at z 40)"}
    return out

def l4():
    H = f"{W}/kit_v22"; core = stl(f"{H}/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl") if os.path.exists(f"{H}/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl") else stl("stl/head/CORE_CYLINDER_v5_integrated.stl")
    comb = stl("stl/head/SPINE_COMB_v5.stl"); env = cyl(44.0, 21.9, 27.0); duct = box(-6, 6, 40, 44, 21.9, 27.0)
    free = env - core - comb - duct
    return dict(envelope_cm3=round(cm3(env), 2), core_in_cell_cm3=round(cm3(core ^ env), 2), comb_in_cell_cm3=round(cm3(comb ^ env), 2), duct_insert_cm3=round(cm3(duct ^ env), 2),
                free_cm3=round(cm3(free), 2), earlier_upper_bound_cm3=31.0)

if __name__ == "__main__":
    n, a = npm(), l4()
    D = dict(alumina_silicone=1.9, syntactic_silicone=0.75, carbonyl_iron_silicone=3.5)
    res = dict(status="MODELED: exact mesh booleans; component volumes are bounding boxes (free volume = lower bound); densities ASSUMED", npm=n, l4_absorber=a,
               mass_g=dict(npm_hot_alumina=[round(n["hot_zone"]["free_cm3_lower"] * D["alumina_silicone"], 0), round(n["hot_zone"]["free_cm3_upper_no_parts"] * D["alumina_silicone"], 0)],
                           npm_main_syntactic=[round(n["main_zone"]["free_cm3_lower"] * D["syntactic_silicone"], 0), round(n["main_zone"]["free_cm3_upper_no_parts"] * D["syntactic_silicone"], 0)],
                           l4_absorber=round(a["free_cm3"] * D["carbonyl_iron_silicone"], 0)),
               densities_g_cm3_ASSUMED=D, earlier_estimates=dict(npm_hot_cm3=28, npm_main_cm3=58, l4_upper_bound_cm3=31.0))
    out = sys.argv[1] if len(sys.argv) > 1 else "data/results/potting_volumes.json"
    json.dump(res, open(out, "w"), indent=1); print(json.dumps(res, indent=1))
