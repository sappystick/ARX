#!/usr/bin/env python3
"""PHI-FOLD 233 v6 spine hardware (mm).  Local frames, shaft axis = +z unless noted.
 NPM  : neck power module at the shaft base, holds PB1R, potted (alumina hot zone + syntactic remainder), ribbon tunnel runs straight through
 CAS  : dual-chamber ribbon cassette (chamber A power, chamber B signal) with guide ribs, trolley with U-loop post, end anchor
 ELB  : 90 deg elbow + grip bar (PM1, HB1, supercap bridge), trigger, joystick boss, forearm cuff
 BAT  : battery drawer (4+3 U-pack 290 x 38 x 20) under the grip, contact plate, end cap with latch
"""
import math, json, os
import numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, solid_union as su
OUT = "kit_v19/SPINE"; os.makedirs(OUT, exist_ok=True); rep = {}
def rrect(w, h, r, na=8):
    pts = []; cx, cy = w / 2 - r, h / 2 - r
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(na + 1):
            a = math.radians(a0 + 90 * k / na); pts.append((sx * cx + r * math.cos(a), sy * cy + r * math.sin(a)))
    return np.array(pts)
def circ(r, m=48, cx=0.0, cy=0.0): t = np.linspace(0, 2 * np.pi, m, endpoint=False); return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]
def ring(outer, inner, z0, z1):
    m = len(outer); assert len(inner) == m
    V = np.concatenate([np.c_[outer, np.full(m, z0)], np.c_[outer, np.full(m, z1)], np.c_[inner, np.full(m, z0)], np.c_[inner, np.full(m, z1)]])
    O0, O1, I0, I1 = (np.arange(m) + k * m for k in range(4)); n = np.roll(np.arange(m), -1); F = []
    for i in range(m):
        j = n[i]
        F += [[O0[i], O0[j], O1[j]], [O0[i], O1[j], O1[i]], [I0[j], I0[i], I1[i]], [I0[j], I1[i], I1[j]], [O0[j], O0[i], I0[i]], [O0[j], I0[i], I0[j]], [O1[i], O1[j], I1[j]], [O1[i], I1[j], I1[i]]]
    F = np.array(F)
    if rc.signed_volume(V, F) < 0: F = F[:, ::-1]
    return V, F
def plate(cx, cy, cz, lx, ly, lz):
    x = np.array([-1, 1]) * lx / 2; y = np.array([-1, 1]) * ly / 2; z = np.array([-1, 1]) * lz / 2
    V = np.array([[a, b, c] for a in x for b in y for c in z]) + [cx, cy, cz]
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
def tube(ro, ri, z0, z1, cx=0.0, cy=0.0, m=48): return ring(circ(ro, m, cx, cy), circ(ri, m, cx, cy), z0, z1)
def sh(s, dx=0, dy=0, dz=0): return s[0] + np.array([dx, dy, dz]), s[1]
def rot(s, M, t=(0, 0, 0)):
    V = s[0] @ np.array(M).T + np.array(t); F = s[1]
    return V, (F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
Mz2x = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]                 # local (u,v,w) -> (x=w, y=v, z=-u): extrusion axis z becomes x
Mz2y = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]                 # extrusion axis z becomes y (y' = w, z' = -v)
def emit(name, shells, note=""):
    bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells)
    V, F, _su = su.merge_closed(shells, g.merge(shells)); rc.write_stl(f"{OUT}/{name}.stl", V, F, name)
    rep[name] = dict(shells=len(shells), triangles=int(len(F)), nonmanifold_edges=int(bad), bbox_mm=[round(float(x), 1) for x in (*V.min(0), *V.max(0))], note=note); return V, F
# ================================================================ CAS: dual-chamber ribbon cassette (fits the 26 mm bore of the 28.5 mm inner tube)
CW, CIW, CIH, WALL, SEP = 17.4, 14.4, 7.0, 1.1, 1.2
def chamber(sign, L):
    outer = rrect(CW, CIH + WALL + SEP, 3.0); inner = rrect(CIW, CIH, 1.2)
    yo = sign * ((CIH + WALL + SEP) / 2 - SEP / 2)
    yi = sign * (SEP / 2 + CIH / 2)
    shells = [ring(outer + [0, yo], inner + [0, yi], 0, L)]
    for sx in (-1, 1): shells.append(plate(sx * 6.9, yi, L / 2, 0.8, 1.6, L))              # guide ribs = the track the trolley rides on
    return shells
def cassette(L=150.0): return chamber(+1, L) + chamber(-1, L)
emit("CAS_R1_cassette_segment_150", cassette(150.0), "dual chamber 17.4 x 17.4: A (power ribbon) y>0, B (signal ribbon) y<0, 14.4 x 7.0 inner, guide ribs on both side walls; print 3 pcs per tube, bond end to end")
tr = [plate(0, 0, 9.0, 12.6, 5.6, 18.0), rot(tube(2.75, 0.9, -6.0, 6.0), Mz2x, (0, 0, 20.5))]
emit("CAS_R2_trolley", tr, "slider 12.6 x 5.6 x 18 with 5.5 mm U-loop post (ribbon bend radius 3.0 with ribbon thickness); one per chamber")
emit("CAS_R3_end_anchor", [plate(0, 0, 4, 17.0, 17.0, 8.0), plate(0, 4.1, 10, 12.4, 1.4, 4.0), plate(0, -4.1, 10, 12.4, 1.4, 4.0)], "ribbon clamp block: ribbon end is glued/clamped, drain wire to the foil lining; one at each end")
# ================================================================ NPM: neck power module (PB1R 70 x 70 stands in the x-z plane, components face +y)
NZ = 84.0
back = [plate(-34, 12.5, NZ / 2, 16.0, 3.0, NZ), plate(14, 12.5, NZ / 2, 56.0, 3.0, NZ)]                  # back wall with a 12 mm cable window at x -26..-14
sides = [plate(sx * 40.5, 24.0, NZ / 2, 3.0, 26.0, NZ) for sx in (-1, 1)]
ends = [plate(0, 24.0, 1.5, 78.0, 26.0, 3.0), plate(0, 24.0, NZ - 1.5, 78.0, 26.0, 3.0)]
tunnel = ring(rrect(23.0, 23.0, 5.0), rrect(17.8, 17.8, 3.4), 0, NZ)
socket_lo = tube(19.8, 16.2, -22.0, 0.0); socket_hi = tube(19.8, 14.45, NZ, NZ + 22.0)             # lower fixed tube D32 / upper tube B D28.5 (socket ID 28.9)
ledge = [plate(sx * 36.4, 32.2, NZ / 2, 4.8, 1.6, 60.0) for sx in (-1, 1)]                         # board rails at the board EDGES (x +-34.0..38.8, 1.0 mm land under the 70 mm board): PB1R sits at y = 33..34.6, components face the back wall; v2 (Step 4/5) was x +-27..33, under the part bodies
fill = [rot(tube(6.0, 4.0, 0, 8), Mz2y, (x, 37.0, 40.0)) for x in (-25.0, 15.0)] + [rot(tube(3.0, 1.5, 0, 6), Mz2y, (x, 37.0, 76.0)) for x in (-25.0, 15.0)]
emit("NPM_N1_body_with_tunnel_v2", back + sides + ends + [tunnel, socket_lo, socket_hi] + ledge, "pocket 78 x 20 x 78 for PB1R, 12 mm cable window, straight ribbon tunnel and tube sockets D32.4 (lower fixed tube and upper OUTER tube, both D32)")
emit("NPM_N2_lid_with_fill_ports", [plate(0, 38.5, NZ / 2, 84.0, 3.0, NZ)] + [rot(tube(6.0, 4.0, 0, 6), Mz2y, (x, 40.0, 40.0)) for x in (-25.0, 15.0)] + [rot(tube(3.0, 1.5, 0, 5), Mz2y, (x, 40.0, 76.0)) for x in (-25.0, 15.0)],
     "lid with 2 x D8 fill ports (hot zone x -25, main zone x +15) and 2 x D3 vents at the far end; bond with epoxy, fill through the ports under vacuum")
emit("NPM_N3_hot_zone_dam_v2", [plate(-4.0, 23.5, NZ / 2, 2.0, 19.0, 76.0)], "vertical dam at x -5..-3 from the back wall (y 14) to the PB1R component face (y 33) separating the alumina-filled hot zone (FETs, clamp bank) from the syntactic main zone; no PB1R part body crosses the strip (pw_export KEEPOUT_X, pb1r_check NPM fit); v2 (Step 4/5): was x -6..-4 and 1 mm into the board, crossing 4 part bodies; leave 1 mm gaps top and bottom for the interface")
# ================================================================ ELB: elbow, grip, trigger, joystick, cuff (shaft up the -z side, grip along +x, grip axis at z = +20)
GZ = 20.0
elb = [rot(tube(20.8, 16.7, -40.0, 8.0), [[math.cos(math.radians(43)),0,math.sin(math.radians(43))],[0,1,0],[-math.sin(math.radians(43)),0,math.cos(math.radians(43))]]), ring(rrect(54, 46, 10), rrect(48, 40, 7), -10.0, 52.0)]
grip = rot(ring(rrect(36, 42, 14), rrect(31.2, 37.2, 11.6), 27.0, 190.0), Mz2x, (0, 0, GZ))
ports = [rot(tube(6.0, 4.0, 0, 6), [[1, 0, 0], [0, 1, 0], [0, 0, 1]], (-14, 0, 52.0)), rot(tube(3.0, 1.5, 0, 5), [[1, 0, 0], [0, 1, 0], [0, 0, 1]], (14, 0, 52.0))]
emit("ELB_E1_elbow_and_grip", elb + [grip] + ports, "shaft socket D33.4 (tube A, OD 33) tilted 43 deg from the elbow axis so the grip is horizontal with the shaft at 47 deg, elbow cavity 48 x 40 and grip cavity 31 x 37 hold PM1, HB1 and the 1 F supercap bridge; fill ports D8 + D3 vent on the elbow top; grip 36 x 42 stadium, 163 mm")
emit("ELB_E2_grip_endcap", [rot(plate(0, 0, 0, 36.0, 42.0, 6.0), Mz2x, (193.0, 0, GZ))], "end cap, bonded after potting")
emit("ELB_E3_trigger", [rot(plate(0, 0, 0, 20.0, 12.0, 26.0), [[1, 0, 0], [0, 1, 0], [0, 0, 1]], (62.0, 0, GZ - 18.0 - 14.0)), plate(62.0, 0, GZ - 18.0 + 1.0, 14.0, 10.0, 6.0)], "trigger lever (magnet in the tip over the HB1 Hall sensor, travel 0-4 mm), index-finger curve")
emit("ELB_E4_joystick_boss", [tube(14.0, 6.5, 0, 5.0), tube(4.0, 0.0001 + 0.5, 0, 24.0)], "thumb joystick boss and stick, sits on the grip top at x = 95 mm", )
emit("ELB_E5_forearm_cuff", [ring(circ(50, 48), circ(43, 48), 0, 55.0), plate(20.0, 0, -12.0, 36.0, 30.0, 24.0)], "forearm cuff D86 inner, 55 mm wide, centred 55 mm above the grip axis so the forearm rests ABOVE the battery drawer; bridge arm to the grip end; strap slots to be added by the user")
# ================================================================ BAT: battery drawer under the grip bar, hangs behind the hand as a counterweight
BZ = GZ - 18.0 - 1.5 - 15.0
drawer = rot(ring(rrect(30, 48, 6), rrect(23, 41, 3.5), 20.0, 332.0), Mz2x, (0, 0, BZ))
emit("BAT_B1_drawer_sleeve", [drawer], "U-pack drawer 41 x 23 inside, 312 mm long, hangs under the grip: 4+3 U-pack 290 x 38 x 20 plus contacts; bonded under the elbow and grip with 4 M3 inserts")
emit("BAT_B2_end_cap_with_latch", [rot(plate(0, 0, 0, 30.0, 48.0, 6.0), Mz2x, (335.0, 0, BZ)), rot(tube(5.0, 3.0, 0, 12.0), Mz2x, (338.0, 0, BZ))], "end cap with push latch boss; O-ring groove to be added, pressure-relief membrane in the cap")
emit("BAT_B3_contact_plate", [rot(plate(0, 0, 0, 23.0, 41.0, 6.0), Mz2x, (21.0, 0, BZ))] + [rot(plate(0, 0, 0, 1.2, 8.0, 14.0), Mz2x, (28.0, y, BZ)) for y in (-12.0, -4.0, 4.0, 12.0)], "contact receptacle: NEG, PRE (22 ohm pre-charge), POS, ID blade pads (same sequence as the v4 cartridge: NEG first, POS last)")
# ================================================================ potting volumes (cm3)
pk = 7.8 + 30.0
npm_pocket = 7.8 * 2.0 * 7.8 - pk * 0.0
npm_free = 7.8 * 2.0 * 7.8 * 1.0                                                                       # 78 x 20 x 78 mm
npm_free_cm3 = 7.8 * 2.0 * 7.8 - 7.0 * 7.0 * 0.16 - 28.0
hot = npm_free_cm3 * 0.33; main = npm_free_cm3 - hot
elb_cm3 = (4.8 * 4.0 * 6.2) + (3.12 * 3.72 * 16.3) - 55.0 - 20.0
pot = dict(NPM_free_cm3=round(npm_free_cm3, 0), NPM_alumina_hot_zone_cm3=round(hot, 0), NPM_alumina_g=round(hot * 1.9, 0), NPM_syntactic_cm3=round(main, 0), NPM_syntactic_g=round(main * 0.75, 0),
           elbow_grip_free_cm3=round(elb_cm3, 0), elbow_grip_syntactic_g=round(elb_cm3 * 0.75, 0))
rep["potting_volumes"] = pot
json.dump(rep, open(f"{OUT}/spine_report.json", "w"), indent=1, default=float)
print(json.dumps({k: (v["nonmanifold_edges"], v["triangles"], v["bbox_mm"]) if "triangles" in v else v for k, v in rep.items()}, default=float))
