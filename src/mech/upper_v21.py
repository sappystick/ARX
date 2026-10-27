#!/usr/bin/env python3
"""PHI-FOLD 233 upper assembly v1 (generator upper_v21.py): XP D044-A-style S-stem with armrest, index-finger trigger, quick-swap battery dock
under the bottom housing, telescoping shaft with a shielded twin-bore cable path to the neck module (mm).

Stem frame: origin at the grip centre, x forward along the shaft toward the head, y left, z up perpendicular to the shaft. The top housing sits on
the shaft line, the bottom housing on the armrest line (parallel, below), the grip joins them raked 16 deg (top forward). In use the whole frame is
tilted head-down by the shaft angle (upper_check.py).

Parts (kit_v23/UPPER):
 U1  top housing: sealed shell, shaft-tube A socket, dial and power-button bosses, trigger ears; HB2 inside (Hall switch reads the trigger magnet
     through the 2.5 mm wall, so there is no trigger slot to seal)
 U2  grip: hollow ellipse 40 x 32 with a septum (front channel: power pair PM2 -> top housing; rear channel: power-button pair)
 U3  bottom housing: shell, armrest-tube socket with 3 detent positions, PM2 inside, dock plate underneath
 U4  trigger lever on the U1 ears, magnet pocket at the top
 U5  armrest: tube clamp, saddle and forearm cup with strap anchors (tube itself is purchased CFRP)
 U6  battery dock: plate, two T rails, MT60-M pedestal (mating along the slide axis, drip edge above), rear latch catch
 U7  battery pack shell: rail channels with undercut, BMS bay, 7 x 18650 transverse cell bay, front connector bay, latch
 U8  twin cavity: cord anchor in tube A; in tube B a full-length septum strip (slit Cu-mesh shield, drain at PM2) held by twin-bore spacer discs
 U9  cam-lock collar (tube A front)
Purchased parts are carried as envelopes in the report (cells, BMS, MT60 pair, cords, tubes, latch, magnet, boards) for the checks.
Dimensions of the D044-A itself are not published: they are scaled from photos and ergonomics and are ASSUMPTIONS (docs/ASSUMPTIONS.md 24-27)."""
import math, json, os
import numpy as np
import rodin_core_v4 as rc, golden_cone_head as g, solid_union as su
from render_v6 import tri2d
OUT = "kit_v23/UPPER"; os.makedirs(OUT, exist_ok=True); rep = dict(parts={}, envelopes={}, params={})

# ------------------------------------------------------------------ parameters (mm, deg)
RAKE = 16.0; GL = 118.0; GA, GB = 20.0, 16.0; GWALL = 4.0                 # grip: axis length between the housings, ellipse semi-axes (fore-aft, side), wall
WT, HT, RT_, WALL = 46.0, 48.0, 10.0, 2.5                                   # top housing section and wall
WB, HB_, RB_ = 46.0, 40.0, 10.0                                             # bottom housing section
TA = (33.0, 30.0); TB = (28.5, 26.0); TAL, TBL, OVL = 450.0, 450.0, 80.0    # shaft tubes A (hand end) and B (head end), CFRP, as shaft_calc_v20.py
SOCK = 44.0; CLR_T = 0.2                                                    # tube A bonded depth in the top housing (1.33 x OD), radial clearance of tubes in sockets
AT = (22.0, 19.0); ATL = 200.0; DET = (90.0, 68.0, 46.0); ASOCK = 95.0      # armrest tube, length, insertion depths of the 3 positions, socket length
RC, CW, CL_ = 46.0, 3.0, 85.0                                               # forearm cup inner radius, wall, length
CELL_D, CELL_L, PITCH, NCELL = 18.6, 65.3, 19.6, 7                          # 18650 envelope (P30B max, unverified) and holder pitch
MT60 = (20.0, 16.5, 8.6)                                                    # MT60 body envelope x (mating axis) y z (unverified, ASSUMPTIONS 25)
BMS = (60.0, 41.0, 5.4)                                                     # BMS envelope that the bay accepts (part to be chosen to fit)
CORD_OD = 10.4; BORE_R = 5.6; BORE_Y = 6.4                                  # coiled-cord envelope, twin-bore radius and centre offset
SEPT, SP_LEN, SP_PITCH = 1.4, 8.0, 75.0                                     # septum strip thickness, spacer length and pitch
LATCH_TRAVEL = 4.0
ug = np.array([math.sin(math.radians(RAKE)), 0.0, math.cos(math.radians(RAKE))])     # grip axis (up, leaning forward)
un = np.array([math.cos(math.radians(RAKE)), 0.0, -math.sin(math.radians(RAKE))])    # forward normal of the grip
Pt, Pb = ug * GL / 2, -ug * GL / 2
ZT = Pt[2] + HT / 2; ZB = Pb[2] - HB_ / 2                                   # shaft axis and armrest axis heights
XT0, XT1 = Pt[0] - 55.0, Pt[0] + 100.0                                      # top housing x span
XB0, XB1 = Pb[0] - 150.0, Pb[0] + 32.0                                      # bottom housing x span
ZDOCK = ZB - HB_ / 2                                                        # underside of the bottom housing = top of the dock plate

# ------------------------------------------------------------------ primitives (closed shells, outward normals)
def fix(V, F): F = np.asarray(F); return (V, F if rc.signed_volume(V, F) > 0 else F[:, ::-1])
def box(x0, x1, y0, y1, z0, z1):
    V = np.array([[a, b, c] for a in (x0, x1) for b in (y0, y1) for c in (z0, z1)], float)
    return fix(V, [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
def prism(P, z0, z1):
    """extrude a simple polygon P (u, v) along w from z0 to z1 -> vertices (u, v, w)"""
    P = np.asarray(P, float); m = len(P); T = tri2d(P); ar = (P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]).sum()
    V = np.concatenate([np.c_[P, np.full(m, z0)], np.c_[P, np.full(m, z1)]]); F = []
    for t in T: F += [[m + t[0], m + t[1], m + t[2]], [t[0], t[2], t[1]]] if ar > 0 else [[m + t[0], m + t[2], m + t[1]], [t[0], t[1], t[2]]]
    for i in range(m): j = (i + 1) % m; F += [[i, j, m + j], [i, m + j, m + i]] if ar > 0 else [[i, m + j, j], [i, m + i, m + j]]
    return fix(V, F)
def ring(O, I, z0, z1):
    """hollow prism between outer polygon O and inner polygon I (same vertex count, same winding)"""
    m = len(O); V = np.concatenate([np.c_[O, np.full(m, z0)], np.c_[O, np.full(m, z1)], np.c_[I, np.full(m, z0)], np.c_[I, np.full(m, z1)]])
    O0, O1, I0, I1 = (np.arange(m) + k * m for k in range(4)); n = np.roll(np.arange(m), -1); F = []
    for i in range(m):
        j = n[i]; F += [[O0[i], O0[j], O1[j]], [O0[i], O1[j], O1[i]], [I0[j], I0[i], I1[i]], [I0[j], I1[i], I1[j]], [O0[j], O0[i], I0[i]], [O0[j], I0[i], I0[j]], [O1[i], O1[j], I1[j]], [O1[i], I1[j], I1[i]]]
    return fix(V, F)
def circ(r, m=48, cy=0.0, cz=0.0): t = np.linspace(0, 2 * np.pi, m, endpoint=False); return np.c_[cy + r * np.cos(t), cz + r * np.sin(t)]
def ell(a, b, m=64): t = np.linspace(0, 2 * np.pi, m, endpoint=False); return np.c_[a * np.cos(t), b * np.sin(t)]
def rrect(w, h, r, na=6):
    pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(na + 1): a = math.radians(a0 + 90 * k / na); pts.append((sx * (w / 2 - r) + r * math.cos(a), sy * (h / 2 - r) + r * math.sin(a)))
    return np.array(pts)
def along_x(S, y0=0.0, z0=0.0):
    """shell built with (u, v, w) = (y, z, x) -> stem frame"""
    V, F = S; return fix(np.c_[V[:, 2], V[:, 0] + y0, V[:, 1] + z0], F)
def frame(S, O, eu, ev, ew):
    V, F = S; return fix(np.asarray(O) + np.outer(V[:, 0], eu) + np.outer(V[:, 1], ev) + np.outer(V[:, 2], ew), F)
def tube_x(ro, ri, x0, x1, z, m=64): return along_x(ring(circ(ro, m), circ(ri, m), x0, x1), 0.0, z)
def twin_bore(R, x0, x1, z):
    V, F = g.plate_with_holes([(0.0, BORE_Y, BORE_R), (0.0, -BORE_Y, BORE_R)], R, x0, x1, n_out=160, n_hole=40, grid=1.6)
    return along_x((np.c_[V[:, 1], V[:, 0], V[:, 2]], F), 0.0, z)            # holes at y = +-BORE_Y
def emit(name, shells, note, material, density):
    bad = sum(rc.edge_manifold_check(F)[1] for V, F in shells); V, F, _su = su.merge_closed(shells, g.merge(shells)); rc.write_stl(f"{OUT}/{name}.stl", V, F, name)
    vol = sum(rc.signed_volume(Vs, Fs) for Vs, Fs in shells) / 1000.0
    rep["parts"][name] = dict(shells=len(shells), triangles=int(len(F)), nonmanifold_edges=int(bad), bbox_mm=[round(float(x), 2) for x in (*V.min(0), *V.max(0))],
                              volume_cm3=round(vol, 2), material=material, mass_g=round(vol * density, 1), note=note)
    return shells

# ------------------------------------------------------------------ U1 top housing
hO, hI = rrect(WT, HT, RT_), rrect(WT - 2 * WALL, HT - 2 * WALL, RT_ - WALL)
U1 = [along_x(ring(hO, hI, XT0 + WALL, XT1 - WALL), 0.0, ZT),
      along_x(prism(hO, XT0, XT0 + WALL), 0.0, ZT)]                                                  # rear end closed
sockO = circ(TA[0] / 2 + CLR_T + 3.0, 64); sockI = circ(TA[0] / 2 + CLR_T, 64)
U1 += [along_x(ring(sockO, sockI, XT1 - SOCK, XT1), 0.0, ZT)]                                         # tube A socket sleeve (bonded)
U1 += [along_x(ring(rrect(WT, HT, RT_, 10), circ(TA[0] / 2 + CLR_T + 3.0, 44), XT1 - WALL, XT1), 0.0, ZT)]    # front end cap around the sleeve
DIAL_X, BTN_X = XT0 + 24.0, XT0 + 50.0
dial_boss = (lambda V_F: (V_F[0] + np.array([DIAL_X, 0.0, ZT + HT / 2 - 0.5]), V_F[1]))(ring(circ(10.0, 40), circ(7.2, 40), 0.0, 4.0))
btn_boss = (lambda V_F: (V_F[0] + np.array([BTN_X, 0.0, ZT + HT / 2 - 0.5]), V_F[1]))(ring(circ(8.0, 40), circ(6.2, 40), 0.0, 3.0))
U1 += [dial_boss, btn_boss]
EAR_X = Pt[0] + GA / math.cos(math.radians(RAKE)) + 8.0                                                # trigger pivot x (in front of the grip top)
PIV = np.array([EAR_X, 0.0, Pt[2] - 6.0])
U1 += [box(EAR_X - 5, EAR_X + 5, s * 8.0 - 1.25, s * 8.0 + 1.25, Pt[2] - 10.0, Pt[2] + 0.5) for s in (-1, 1)]   # trigger ears under the housing
emit("U1_TOP_HOUSING", U1, f"sealed shell {WT} x {HT}, wall {WALL}; tube A socket D{TA[0]+2*CLR_T:.1f} x {SOCK}; dial boss x {DIAL_X:.1f}, power button x {BTN_X:.1f}; trigger ears; HB2 inside", "PETG/ASA", 1.27)

# ------------------------------------------------------------------ U2 grip: raked elliptical tube with horizontal ends (sheared extrusion), 2 mm into each housing wall
TR = math.tan(math.radians(RAKE)); CR = math.cos(math.radians(RAKE))
def shear(S): V, F = S; V = V.copy(); V[:, 0] += V[:, 2] * TR; return fix(V, F)
gO, gI = ell(GA / CR, GB, 72), ell((GA - GWALL) / CR, GB - GWALL, 72)                                   # horizontal section of the raked ellipse (GA x GB normal section)
gz0, gz1 = Pb[2] - 2.0, Pt[2] + 2.0
U2 = [shear(ring(gO, gI, gz0, gz1)),
      shear(prism(np.array([[-0.8 / CR, -(GB - GWALL)], [0.8 / CR, -(GB - GWALL)], [0.8 / CR, GB - GWALL], [-0.8 / CR, GB - GWALL]]), gz0, gz1))]
emit("U2_GRIP", U2, f"hollow ellipse {2*GA} x {2*GB} (perimeter about {math.pi*(3*(GA+GB)-math.sqrt((3*GA+GB)*(GA+3*GB))):.0f} mm), wall {GWALL}, raked {RAKE} deg; septum: front channel power pair, rear channel button pair; over-grip sleeve optional", "PETG/TPU sleeve", 1.27)

# ------------------------------------------------------------------ U3 bottom housing with armrest socket
bO, bI = rrect(WB, HB_, RB_), rrect(WB - 2 * WALL, HB_ - 2 * WALL, RB_ - WALL)
aSO, aSI = circ(AT[0] / 2 + CLR_T + 2.8, 64), circ(AT[0] / 2 + CLR_T, 64)
U3 = [along_x(ring(bO, bI, XB0 + WALL, XB1 - WALL), 0.0, ZB), along_x(prism(bO, XB1 - WALL, XB1), 0.0, ZB),
      along_x(ring(rrect(WB, HB_, RB_, 10), circ(AT[0] / 2 + CLR_T + 2.8, 44), XB0, XB0 + WALL), 0.0, ZB),   # rear end cap around the armrest socket
      along_x(ring(aSO, aSI, XB0, XB0 + ASOCK), 0.0, ZB)]
emit("U3_BOTTOM_HOUSING", U3, f"shell {WB} x {HB_}, wall {WALL}; armrest socket D{AT[0]+2*CLR_T:.1f} x {ASOCK} with detents at insertion {DET}; PM2 bay x {XB0+ASOCK+5:.0f}..{XB1-8:.0f}", "PETG/ASA", 1.27)

# ------------------------------------------------------------------ U4 trigger lever (pivot on the U1 ears, pad in front of the grip top, magnet at the top)
s_pad = GL / 2 - 26.0; pad_c = ug * s_pad + un * (GA + 3.5 + 2.5)                                      # pad centre: 3.5 mm in front of the grip at rest
PAD = frame(box(-2.5, 2.5, -7.0, 7.0, -13.0, 13.0), pad_c, un, np.array([0, 1.0, 0]), ug)
BAR = frame(box(-2.5, 2.5, -6.0, 6.0, s_pad + 11.0, GL / 2 - 2.0), un * (GA + 6.0), un, np.array([0, 1.0, 0]), ug)   # bar parallel to the grip, same 3.5 mm gap
bar_top = ug * (GL / 2 - 2.0) + un * (GA + 6.0)
ARM = box(bar_top[0] - 1.0, PIV[0] + 3.0, -6.0, 6.0, bar_top[2] - 3.0, PIV[2] + 3.0)                       # link from the bar top to the pivot
pivot = frame(ring(circ(4.0, 32), circ(1.6, 32), -6.7, 6.7), PIV, np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), np.array([0, 1.0, 0]))
TAIL = 22.0; mag_c = np.array([PIV[0] + TAIL, 0.0, Pt[2] - 0.8 - 1.5])                                    # magnet at the end of a 22 mm tail, 0.8 mm under the wall at rest
TAILB = box(PIV[0], PIV[0] + TAIL + 3.5, -4.0, 4.0, mag_c[2] - 2.0, mag_c[2] + 1.5)                         # tail; pressing the pad swings it down, away from the Hall sensor
MAG = dict(d=5.0, h=3.0, centre=[round(float(v), 2) for v in mag_c], tail_mm=TAIL)
emit("U4_TRIGGER", [PAD, BAR, ARM, pivot, TAILB], f"lever on a D3.2 pin through the ears, pad 5 x 14 x 26 at {s_pad:.0f} mm above the grip centre, 3.5 mm in front of the grip; "
     f"magnet on a {TAIL:.0f} mm tail ahead of the pivot, 0.8 mm under the housing wall at rest; pressing swings it away from Hall HS1 on HB2 (through {WALL} mm PETG): active-low trigger; pad travel 3 mm to the stop", "PETG", 1.27)
rep["envelopes"]["trigger_magnet"] = MAG
HB2_ENV = dict(x=[float(mag_c[0]) - 35.0, float(mag_c[0]) + 3.0], y=[-12.0, 12.0], z_board=[float(Pt[2]) + WALL + 1.0, float(Pt[2]) + WALL + 2.6], parts_height=4.5, hall_x=float(mag_c[0]))
PM2_ENV = dict(x=[float(XB0 + ASOCK + 5.0), float(XB0 + ASOCK + 75.0)], y=[-14.0, 14.0], z_board=[float(ZB - HB_ / 2 + WALL + 2.0), float(ZB - HB_ / 2 + WALL + 3.6)], parts_height=10.8)
rep["envelopes"].update(HB2_board=HB2_ENV, PM2_board=PM2_ENV)

# ------------------------------------------------------------------ armrest tube positions and U5 armrest (at position 1)
def arm_rear(depth): return XB0 + depth - ATL                                                          # rear end of the armrest tube
CUP_Z = ZB + AT[0] / 2 + 6.0 + CW + RC                                                                  # cup axis height (saddle 6 mm)
def cup_centre(depth): return arm_rear(depth) + 40.0
def armrest(depth):
    xr = arm_rear(depth); xc = cup_centre(depth); sh = []
    sh.append(tube_x(AT[0] / 2 + CLR_T + 3.0, AT[0] / 2 + CLR_T, xr - 2.0, xr + 34.0, ZB))              # clamp sleeve on the tube end
    sh.append(box(xr + 2.0, xr + 30.0, -10.0, 10.0, ZB + AT[0] / 2 + CLR_T + 1.5, CUP_Z - RC - CW + 1.0))    # saddle up to the cup
    a = np.radians(np.linspace(-205, 25, 70)); O = np.c_[(RC + CW) * np.cos(a), (RC + CW) * np.sin(a)]; I = np.c_[RC * np.cos(a), RC * np.sin(a)]
    sh.append(along_x(prism(np.vstack([O, I[::-1]]), xc - CL_ / 2, xc + CL_ / 2), 0.0, CUP_Z))             # forearm cup, 230 deg arc
    for ang in (25.0, -205.0):                                                                            # strap anchors on both cup edges
        c = np.array([0.0, (RC + CW + 3.0) * math.cos(math.radians(ang)), CUP_Z + (RC + CW + 3.0) * math.sin(math.radians(ang))])
        sh.append(box(xc - 14.0, xc + 14.0, c[1] - 3.0, c[1] + 3.0, c[2] - 3.0, c[2] + 3.0))
    return sh
emit("U5_ARMREST_CUP", armrest(DET[0]), f"forearm cup R{RC} inner, {CL_} long, 230 deg arc, strap anchors; clamp + saddle on the D{AT[0]} tube; shown at position 1", "PETG/TPU liner", 1.27)
emit("ARMREST_TUBE_CFRP_pos1", [tube_x(AT[0] / 2, AT[1] / 2, arm_rear(DET[0]), arm_rear(DET[0]) + ATL, ZB)], f"purchased CFRP tube OD{AT[0]}/ID{AT[1]} x {ATL}", "CFRP", 1.55)

# ------------------------------------------------------------------ U6 battery dock
DY = 36.5; RAIL_Y = 28.0; DT = 3.0                                                            # dock half-width, rail offset, plate thickness
DOCK_X0, DOCK_X1 = -178.0, 23.0
Z_PT = ZDOCK - DT - 0.5                                                                               # pack top (0.5 mm below the dock plate)
POCKET = (-174.5, -167.5, 10.0)                                                                         # latch pocket through the dock plate (x0, x1, half-width)
U6 = [box(POCKET[1], DOCK_X1, -DY, DY, ZDOCK - DT, ZDOCK), box(DOCK_X0, POCKET[0], -DY, DY, ZDOCK - DT, ZDOCK)]
U6 += [box(POCKET[0], POCKET[1], *sorted((s * POCKET[2], s * DY)), ZDOCK - DT, ZDOCK) for s in (-1, 1)]
for s in (-1, 1):
    U6.append(box(-170.0, -2.0, s * RAIL_Y - 2.5, s * RAIL_Y + 2.5, Z_PT - 2.8, ZDOCK - DT))           # rail stem 5.0 wide (through gap 0.5 + lip 2.5 + 0.3)
    U6.append(box(-170.0, -2.0, s * RAIL_Y - 5.5, s * RAIL_Y + 5.5, Z_PT - 5.6, Z_PT - 2.8))            # rail head 11.0 x 2.8
CONN_Z = Z_PT - 20.0
PED_X0 = 0.5
U6 += [box(PED_X0, PED_X0 + MT60[0] + 1.5, -16.0, 16.0, CONN_Z + MT60[2] / 2 + 0.2, ZDOCK - DT),       # pedestal above the connector
       box(PED_X0, PED_X0 + MT60[0] + 1.5, -16.0, 16.0, CONN_Z - MT60[2] / 2 - 6.0, CONN_Z - MT60[2] / 2 - 0.2),   # below
       box(PED_X0, PED_X0 + MT60[0] + 1.5, -16.0, -MT60[1] / 2 - 0.2, CONN_Z - MT60[2] / 2 - 0.2, CONN_Z + MT60[2] / 2 + 0.2),
       box(PED_X0, PED_X0 + MT60[0] + 1.5, MT60[1] / 2 + 0.2, 16.0, CONN_Z - MT60[2] / 2 - 0.2, CONN_Z + MT60[2] / 2 + 0.2),
       box(PED_X0 + MT60[0] + 1.5, PED_X0 + MT60[0] + 4.0, -16.0, 16.0, CONN_Z - MT60[2] / 2 - 6.0, ZDOCK - DT)]   # back wall (potting dam)
emit("U6_BATTERY_DOCK", U6, f"plate {DOCK_X1-DOCK_X0:.0f} x {2*DY}, two T rails (stem 5.0, head 11.0 x 2.8) at y +-{RAIL_Y}; MT60-M pedestal, vertical mating face, mating along -x; "
     f"latch pocket x {POCKET[0]}..{POCKET[1]} through the plate", "PETG/PC (rails optionally aluminium)", 1.27)
rep["envelopes"]["MT60_M"] = dict(x=[PED_X0, PED_X0 + MT60[0]], y=[-MT60[1] / 2, MT60[1] / 2], z=[CONN_Z - MT60[2] / 2, CONN_Z + MT60[2] / 2], mating_face_x=PED_X0)

# ------------------------------------------------------------------ U7 battery pack shell (pack front face at x = 0, top at Z_PT)
LP = 168.0; PW_ = 2 * DY; PH = 31.5
def P(x0, x1, y0, y1, z0, z1): return box(x0, x1, y0, y1, Z_PT + z0, Z_PT + z1)                          # pack-local z (0 = top)
SL0, SL1 = RAIL_Y - 2.8, RAIL_Y + 2.8                                                                  # slot opening 5.6
CV0, CV1 = RAIL_Y - 5.8, RAIL_Y + 5.8                                                                  # undercut cavity 11.6
U7 = []
for (y0, y1) in ((-DY, -SL1), (-SL0, SL0), (SL1, DY)): U7.append(P(-LP, 0, y0, y1, -2.5, 0.0))          # top skin with the two slot openings
for s in (-1, 1):
    U7.append(P(-LP, 0, *sorted((s * CV1, s * DY)), -5.9, -2.5))                                        # outer cavity walls
    U7.append(P(-LP, 0, *sorted((s * CV0, s * (CV0 - 1.5))), -8.4, -2.5))                               # inner cavity walls = BMS bay sides
    U7.append(P(-LP, 0, *sorted((s * CV0, s * DY)), -8.4, -5.9))                                        # cavity floors
U7.append(P(-LP, 0, -(CV0 - 1.5), CV0 - 1.5, -9.4, -8.4))                                               # BMS bay floor / cell bay ceiling
U7.append(P(-LP, 0, -DY, DY, -PH, -PH + 2.5))                                                           # bottom
for s in (-1, 1): U7.append(P(-LP, 0, *sorted((s * (DY - 2.5), s * DY)), -PH + 2.5, -8.4))              # side walls
U7.append(P(-LP, -LP + 2.5, -DY + 2.5, DY - 2.5, -PH + 2.5, -8.4))                                      # rear wall
for (x0, x1) in ((-LP, -LP + 2.5), (-2.5, 0.0)): U7.append(P(x0, x1, -(CV0 - 1.5), CV0 - 1.5, -8.4, -2.5))   # BMS bay end walls
CZ = CONN_Z - Z_PT                                                                                     # connector centre, pack-local
for (y0, y1, z0, z1) in ((-DY + 2.5, DY - 2.5, CZ + MT60[2] / 2 + 0.2, -8.4), (-DY + 2.5, DY - 2.5, -PH + 2.5, CZ - MT60[2] / 2 - 0.2),
                         (-DY + 2.5, -MT60[1] / 2 - 0.2, CZ - MT60[2] / 2 - 0.2, CZ + MT60[2] / 2 + 0.2), (MT60[1] / 2 + 0.2, DY - 2.5, CZ - MT60[2] / 2 - 0.2, CZ + MT60[2] / 2 + 0.2)):
    U7.append(P(-2.5, 0.0, y0, y1, z0, z1))                                                             # front wall with the MT60-F opening
U7.append(P(-27.0, -26.0, -DY + 2.5, DY - 2.5, -PH + 2.5, -9.4))                                        # connector bay / cell bay divider
LATCH = dict(x=[-LP - 6.0, -LP - 0.5], y=[-8.0, 8.0], z_rest=[Z_PT - 12.0, Z_PT + 3.0], travel=LATCH_TRAVEL)   # spring thumb latch (purchased steel): tongue rises 3 mm into the dock pocket
U7.append(box(-LP - 0.5, -LP, -10.0, 10.0, Z_PT - 14.0, Z_PT - 0.5))                                    # latch mounting plate on the rear wall
emit("U7_BATTERY_PACK_SHELL", U7, f"{LP:.0f} x {PW_:.0f} x {PH} mm; rail channels slot 5.6 / undercut 11.6 x 3.4; BMS bay {2*(CV0-1.5):.1f} x 5.9; cell bay 7 x 18650 transverse at {PITCH} mm pitch; MT60-F front bay; latch plate", "PC (UL94 V-0) or PETG", 1.20)
CELLS = [dict(x=round(-27.0 - PITCH / 2 - PITCH * k, 2), z=round(float(Z_PT + (-PH + 2.5 + 0.4 + CELL_D / 2)), 2)) for k in range(NCELL)]
rep["envelopes"].update(cells=dict(d=CELL_D, l=CELL_L, axis="y", centres=CELLS), BMS=dict(size=BMS, x=[-90.0, -30.0], y=[-BMS[1] / 2, BMS[1] / 2], z=[Z_PT - 8.1, Z_PT - 8.1 + BMS[2]]),   
                        MT60_F=dict(x=[-MT60[0], 0.0], y=[-MT60[1] / 2, MT60[1] / 2], z=[CONN_Z - MT60[2] / 2, CONN_Z + MT60[2] / 2]), latch=LATCH,
                        latch_pocket=dict(x=list(POCKET[:2]), y=[-POCKET[2], POCKET[2]], z=[ZDOCK - DT, ZDOCK]))

# ------------------------------------------------------------------ shaft tubes, collar, twin-bore inserts (extended and collapsed)
A0 = XT1 - SOCK; A1 = A0 + TAL
B_EXT = (A1 - OVL, A1 - OVL + TBL); ANCH = (A0 + 0.7, A0 + 13.0); B_COL = (ANCH[1] + 1.0, ANCH[1] + 1.0 + TBL)
emit("TUBE_A_CFRP", [tube_x(TA[0] / 2, TA[1] / 2, A0, A1, ZT)], f"purchased CFRP OD{TA[0]}/ID{TA[1]} x {TAL}", "CFRP", 1.55)
for nm, (b0, b1) in (("extended", B_EXT), ("collapsed", B_COL)):
    emit(f"TUBE_B_CFRP_{nm}", [tube_x(TB[0] / 2, TB[1] / 2, b0, b1, ZT)], f"purchased CFRP OD{TB[0]}/ID{TB[1]} x {TBL}, {nm}", "CFRP", 1.55)
    RS = TB[1] / 2 - 0.2; spacers = [twin_bore(RS, b0 + 2.0 + SP_PITCH * k, b0 + 2.0 + SP_PITCH * k + SP_LEN, ZT) for k in range(int((TBL - 4.0 - SP_LEN) // SP_PITCH) + 1)]
    strip = box(b0 + 2.0, b1 - 2.0, -SEPT / 2, SEPT / 2, ZT - (RS - 0.3), ZT + (RS - 0.3))
    if nm == "extended":                                                      # the full-length strip is 446 mm: it does not fit a 250 mm build volume. Print it as two segments cut between two spacers; the slit Cu-mesh laminate runs across the joint (the full-length STL stays as the fit / interference reference)
        n_sp = len(spacers); m = n_sp // 2 + 1; x0s, x1s = b0 + 2.0, b1 - 2.0; cut = x0s + SP_PITCH * (m - 1) + SP_LEN + 2.0; assert cut - x0s <= 250.0 and x1s - cut <= 250.0, (cut - x0s, x1s - cut)      # cut 2 mm after a spacer: both segments fit a 250 mm build volume
        segA = [box(x0s, cut, -SEPT / 2, SEPT / 2, ZT - (RS - 0.3), ZT + (RS - 0.3))] + spacers[:m]; segB = [box(cut, x1s, -SEPT / 2, SEPT / 2, ZT - (RS - 0.3), ZT + (RS - 0.3))] + spacers[m:]
        emit("U8_SEPTUM_extended_SEG_A", segA, f"printable segment A of the septum: x {x0s:.1f} to {cut:.1f} mm ({cut - x0s:.1f} mm), {m} spacers; joined to segment B by the laminated Cu-mesh shield", "PETG", 1.27)
        emit("U8_SEPTUM_extended_SEG_B", segB, f"printable segment B of the septum: x {cut:.1f} to {x1s:.1f} mm ({x1s - cut:.1f} mm), {n_sp - m} spacers", "PETG", 1.27)
    emit(f"U8_SEPTUM_{nm}", [strip] + spacers, f"twin cavity in tube B: full-length septum strip {SEPT} mm (PETG with a slit Cu-mesh shield laminated, drain at PM2) "
         f"+ {len(spacers)} twin-bore spacers {SP_LEN} mm long every {SP_PITCH} mm (bores 2 x D{2*BORE_R} at y +-{BORE_Y}); each half-bore holds a D{2*(TB[1]/2-SEPT/2)/2:.1f} circle", "PETG", 1.27)
emit("U8_CORD_ANCHOR", [twin_bore(TA[1] / 2 - 0.2, ANCH[0], ANCH[1], ZT)], "twin-bore cord anchor at the rear of tube A (start of the two cavities), cords clamped", "PETG", 1.27)
emit("U9_CAM_COLLAR", [tube_x(TA[0] / 2 + 4.0, TA[0] / 2 + 0.1, A1 - 24.0, A1, ZT), tube_x(TA[0] / 2 + 4.0, TB[0] / 2 + 0.2, A1, A1 + 4.0, ZT),
                       box(A1 - 20.0, A1 - 4.0, -6.0, 6.0, ZT + TA[0] / 2 + 3.0, ZT + TA[0] / 2 + 12.0)], "cam-lock collar (lever block on top), stops tube B at the 80 mm overlap", "PA12/PETG", 1.15)

# ------------------------------------------------------------------ assembly STLs and report
asm = [f"{OUT}/{n}.stl" for n in ("U1_TOP_HOUSING", "U2_GRIP", "U3_BOTTOM_HOUSING", "U4_TRIGGER", "U5_ARMREST_CUP", "ARMREST_TUBE_CFRP_pos1", "U6_BATTERY_DOCK", "U7_BATTERY_PACK_SHELL", "TUBE_A_CFRP", "U8_CORD_ANCHOR", "U9_CAM_COLLAR")]
def stl_tris(p):
    b = open(p, "rb").read(); n = int.from_bytes(b[80:84], "little"); a = np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n, offset=84); return a["v"].reshape(-1, 3, 3)
for nm, extra in (("extended", ("TUBE_B_CFRP_extended", "U8_SEPTUM_extended")), ("collapsed", ("TUBE_B_CFRP_collapsed", "U8_SEPTUM_collapsed"))):
    T = np.concatenate([stl_tris(p) for p in asm + [f"{OUT}/{e}.stl" for e in extra]]); V = T.reshape(-1, 3); F = np.arange(len(V)).reshape(-1, 3)
    rc.write_stl(f"{OUT}/UPPER_ASSEMBLY_{nm}.stl", V, F, f"UPPER_ASSEMBLY_{nm}")
rep["params"] = dict(rake_deg=RAKE, grip_axis_len=GL, grip_semi_axes=[GA, GB], ZT=round(float(ZT), 2), ZB=round(float(ZB), 2), top_housing_x=[round(float(XT0), 2), round(float(XT1), 2)],
                     bottom_housing_x=[round(float(XB0), 2), round(float(XB1), 2)], Pt=[round(float(v), 2) for v in Pt], Pb=[round(float(v), 2) for v in Pb], ug=[round(float(v), 5) for v in ug], un=[round(float(v), 5) for v in un],
                     trigger_pad_s=s_pad, trigger_pad_gap=3.5, trigger_travel=3.0, pad_centre=[round(float(v), 2) for v in pad_c], pivot=[round(float(v), 2) for v in PIV], dial_x=DIAL_X, button_x=BTN_X,
                     tube_A=dict(od=TA[0], id=TA[1], x=[A0, A1]), tube_B=dict(od=TB[0], id=TB[1], extended=list(B_EXT), collapsed=list(B_COL)), min_overlap=OVL, anchor_x=list(ANCH),
                     armrest=dict(od=AT[0], id=AT[1], length=ATL, socket=ASOCK, insertion_depths=list(DET), cup_centre_x=[round(float(cup_centre(d)), 1) for d in DET], cup_axis_z=round(float(CUP_Z), 2)),
                     dock=dict(rail_y=RAIL_Y, z_pack_top=round(float(Z_PT), 2), z_dock=round(float(ZDOCK), 2)), pack=dict(L=LP, W=PW_, H=PH, front_x=0.0),
                     cord_od=CORD_OD, bore_r=BORE_R, bore_y=BORE_Y)
json.dump(rep, open(f"{OUT}/upper_v21_report.json", "w"), indent=1, default=float)
for k, v in rep["parts"].items(): print(f"{k:28s} shells {v['shells']:3d} open edges {v['nonmanifold_edges']} vol {v['volume_cm3']:8.2f} cm3  {v['mass_g']:7.1f} g  bbox {v['bbox_mm']}")
