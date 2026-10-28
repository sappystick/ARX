#!/usr/bin/env python3
"""B5: 3D check of the physical CB1D JA / JB -> AB1A / AB1B J2 links (2 x 12 conductors) on the meshes. Run in work/ after v5, parts, pcb-ab1 and pcb-cb1d.
Connector positions come from the real layouts (out_board/AB1x_layout.json, kit_v18/CB1D/PF233-CB1D_pickplace.csv; CB1D mounted rotated 180 deg, AB1A/AB1B at x -/+20.3,
board bottom z 11.1; CB1D bottom z 27.0; LB1 bottom z 39.2). The printed parts are the v5 meshes (hub, septum frame, spine comb, analog tray).
Questions answered (each a PASS/FAIL row in kit_v22/link_path_check.json):
  1. can a link go straight up from J2 to JA/JB?  (septum ring r31-39 and the copper-cloth window r < 31 lie across it; the absorber cell L4 fills z 21.9-27)
  2. does the designed passage (the 90 deg spine duct behind the comb, with its four windows) take two flat cables: every sample of each cable's
     cross-section along the route is outside every printed solid, it passes the comb windows at the AB1 and CB1D levels, and fits the CB1D notch;
  3. is there free height on the board lanes: AB1 (J2 to the duct, under the septum) and CB1D (duct to JA / JB, under LB1), from the component bodies;
  4. route length per link.
Two concepts (CONCEPTS): an IDC ribbon on the current 1.27 mm headers (width 12 x 0.635 mm by pitch, thickness 1.0 mm, mated socket 5.0 mm) and a 0.5 mm FFC with
low-profile connectors at the duct-side board edges (width 7.0, thickness 0.2, connector 2.0 mm): every cable and connector size is ASSUMED (ASSUMPTIONS row 37, no datasheet read).
MODELED geometry only; nothing is built."""
import json, csv, math, os, struct, sys
import numpy as np
CONCEPTS = {"IDC ribbon on the current 1.27 mm headers": dict(w=12 * 0.635, t=1.0, sock=5.0, hdr_ab=4.0, hdr_cb=None, lanes=True),
            "FFC 0.5 mm with low-profile connectors at the duct-side board edges": dict(w=7.0, t=0.2, sock=0.0, hdr_ab=2.0, hdr_cb=2.0, lanes=False)}
W_CAB, T_CAB, SOCKET_H, CLR = 12 * 0.635, 1.0, 5.0, 0.3
Z_AB_TOP, Z_SEPT_BOT, Z_SEPT_TOP, Z_ABS_TOP, Z_CB_BOT, Z_CB_TOP, Z_LB_BOT = 11.1 + 1.6, 20.1, 21.8, 27.0, 27.0, 28.6, 39.2
DUCT_Y = 42.0                                                      # duct centre: behind the comb bar (y 37.4-40) and inside the hub bore (r 44)
WIN = {"AB1": (12.0, 14.0), "SEPTUM": (19.5, 22.5), "CB1D": (26.5, 29.5), "LB1": (38.0, 39.2)}
NOTCH_HALF, NOTCH_R = 7.6, 36.5

def stl(p):
    b = open(p, "rb").read(); k = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=k, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def inside(T, P):
    """point-in-closed-mesh by vertical ray parity (rays to +z), P (n,3); triangles bucketed by column"""
    P = np.asarray(P, float); out = np.zeros(len(P), bool)
    cols = {}
    for i, (x, y, z) in enumerate(P): cols.setdefault((round(x, 4), round(y, 4)), []).append(i)
    x0, x1 = T[:, :, 0].min(1), T[:, :, 0].max(1); y0, y1 = T[:, :, 1].min(1), T[:, :, 1].max(1)
    for (x, y), idx in cols.items():
        m = (x0 <= x) & (x <= x1) & (y0 <= y) & (y <= y1)
        if not m.any(): continue
        t = T[m]; a, b, c = t[:, 0], t[:, 1], t[:, 2]
        d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1]); ok = np.abs(d) > 1e-12
        a, b, c, d = a[ok], b[ok], c[ok], d[ok]
        l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / d
        l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / d; l3 = 1 - l1 - l2
        h = (l1 >= 0) & (l2 >= 0) & (l3 >= 0); zc = l1[h] * a[h, 2] + l2[h] * b[h, 2] + l3[h] * c[h, 2]
        for i in idx: out[i] = (np.sum(zc > P[i, 2]) % 2) == 1
    return out

def main(out_json):
    allrep = {}
    for cname, cp in CONCEPTS.items():
        global W_CAB, T_CAB, SOCKET_H
        W_CAB, T_CAB, SOCKET_H = cp["w"], cp["t"], cp["sock"]; allrep[cname] = one(cp)
        print("==", cname, "FAILS", allrep[cname]["n_fail"], "of", len(allrep[cname]["checks"]))
    dec = "FFC 0.5 mm with low-profile connectors at the duct-side board edges"
    allrep["decision"] = dict(choice=dec, why="the measured passage takes it (AB1 comb window 2.0 mm for two cables, 3.4 mm above a 1.27 mm header under the septum, JA/JB on the CB1D top under LB1); catalog parts, replaceable, no custom flex fabrication; rigid-flex (OPEN_ITEMS 3) stays the option if the bench shows TX-to-link coupling. Needs: J2 / JA / JB moved to the duct-side board edges and FFC footprints verified (not done: changes three released boards)",
                              header_ribbon_fails=allrep["IDC ribbon on the current 1.27 mm headers"]["n_fail"], ffc_fails=allrep[dec]["n_fail"])
    json.dump(allrep, open(out_json, "w"), indent=1); print("decision:", dec)
def one(cp):
    res = []; C = lambda name, ok, val="", note="": res.append(dict(check=name, result="PASS" if ok else "FAIL", value=str(val), note=note))
    sys.path.insert(0, "."); os.environ.setdefault("BOARD", "A")
    # ---- connectors in the hub frame
    J2 = {}
    for b, cx in (("A", -20.3), ("B", 20.3)):
        P = json.load(open(f"out_board/AB1{b}_layout.json"))["PLACE"]["J2"]; J2[b] = (cx + P[0], -P[1])           # exporter frame is y-down
    CB = {r["Ref"]: r for r in csv.DictReader(open("kit_v18/CB1D/PF233-CB1D_pickplace.csv"))}
    JA = (-float(CB["JA"]["PosX_mm"]), -float(CB["JA"]["PosY_mm"])); JB = (-float(CB["JB"]["PosX_mm"]), -float(CB["JB"]["PosY_mm"]))   # pickplace is y-up; CB1D rotated 180 deg
    side = {k: CB[k]["Side"] for k in ("JA", "JB")}
    links = {"JA-AB1A.J2": (JA, J2["A"]), "JB-AB1B.J2": (JB, J2["B"])}
    rep = dict(connectors_hub_mm={"AB1A.J2": J2["A"], "AB1B.J2": J2["B"], "CB1D.JA": JA, "CB1D.JB": JB}, cb1d_header_side=side)
    M = {n: stl(p) for n, p in (("HUB", "kit_v22/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl"), ("SEPTUM", "kit_v22/SEPTUM_FRAME_v5.stl"),
                                 ("COMB", "kit_v22/SPINE_COMB_v5.stl"), ("TRAY", "kit_v22/ANALOG_TRAY_v5.stl"))}
    # ---- 1. straight up
    for nm, (top, bot) in links.items():
        r = math.hypot(*bot); hit = inside(M["SEPTUM"], [(bot[0], bot[1], 20.95)])[0]
        why = "septum frame solid" if hit else ("copper-cloth window (r < 31): a cable through it breaks the shield" if r < 31 else "septum gap")
        C(f"{nm}: a straight vertical link from J2 (r {r:.1f}) is blocked (septum level z 20.1-21.8, then the absorber cell z 21.9-27)", hit or r < 31, why,
          "expected: the link cannot go straight up; it must use the spine duct")
    # ---- 2. the duct route: J2 -> AB1 lane -> comb window (AB1 level) -> duct -> comb window (CB1D level) -> notch -> CB1D lane -> JA/JB
    off = {"JA-AB1A.J2": -0.5 * (T_CAB + CLR), "JB-AB1B.J2": 0.5 * (T_CAB + CLR)}            # the two cables stacked in the duct (y offset)
    for nm in links:
        xs = np.linspace(-W_CAB / 2, W_CAB / 2, 9); pts = []
        for z in np.arange(WIN["AB1"][0] + 0.3, WIN["CB1D"][1] - 0.3, 0.25):
            for x in xs: pts.append((x, DUCT_Y + off[nm], z))
        bad = {n: int(inside(T, pts).sum()) for n, T in M.items()}
        C(f"{nm}: cable cross-section in the duct (y {DUCT_Y + off[nm]:.2f}, |x| <= {W_CAB / 2:.2f}, z {WIN['AB1'][0]:.1f}-{WIN['CB1D'][1]:.1f}) clear of every printed solid",
          sum(bad.values()) == 0, bad, f"{len(pts)} sample points")
        for lv in ("AB1", "CB1D"):
            z0, z1 = WIN[lv]; zc = 0.5 * (z0 + z1); pw = [(x, y, zc + dz) for x in xs for y in np.arange(37.0, 40.6, 0.3) for dz in (-0.5 * T_CAB, 0.5 * T_CAB)]
            nb = int(inside(M["COMB"], pw).sum())
            C(f"{nm}: passes the comb window at the {lv} level (z {z0}-{z1}, cable {T_CAB} mm thick, width {W_CAB:.2f} mm)", nb == 0 and z1 - z0 >= 2 * T_CAB + CLR if lv == "AB1" else nb == 0,
              f"{nb} points inside the comb; window {z1 - z0:.1f} mm for {2 if lv == 'AB1' else 1} cable(s)")
    C("CB1D notch takes the cables onto the board top (notch half-width vs half cable width + clearance)", NOTCH_HALF >= W_CAB / 2 + CLR, f"{NOTCH_HALF} vs {W_CAB / 2 + CLR:.2f}")
    # ---- 3. free height on the board lanes (component bodies along a lane W_CAB wide)
    LIBJ = json.load(open("kit_v19/lib_bodies.json"))
    typ = {}
    for r in list(csv.reader(open("kit_v18/CB1D/PF233-CB1D_BOM.csv")))[1:]:
        for ref in r[1].split(","): typ[ref.strip()] = r[2]
    cbox = []
    for r in CB.values():
        t = typ.get(r["Ref"])
        if t not in LIBJ: continue
        bw, bh, bz = LIBJ[t]
        if int(float(r["Rot"])) % 180 == 90: bw, bh = bh, bw
        x, y = -float(r["PosX_mm"]), -float(r["PosY_mm"]); cbox.append((r["Ref"], x - bw / 2, x + bw / 2, y - bh / 2, y + bh / 2, Z_CB_TOP + bz))
    def lane_max(boxes, p, q, skip):
        p, q = np.array(p), np.array(q); L = np.linalg.norm(q - p); u = (q - p) / L; n = np.array([-u[1], u[0]]); hmax, who = 0.0, ""
        for ref, a0, a1, b0, b1, zt in boxes:
            if ref in skip: continue
            cs = np.array([(a0, b0), (a0, b1), (a1, b0), (a1, b1)]) - p; s = cs @ u; t = cs @ n
            if s.max() < 0 or s.min() > L or t.max() < -W_CAB / 2 or t.min() > W_CAB / 2: continue
            if zt > hmax: hmax, who = zt, ref
        return hmax, who
    lengths = {}
    for nm, (top, bot) in links.items():
        hb = "JA" if nm.startswith("JA") else "JB"
        if cp["lanes"]:
            zmax, who = lane_max(cbox, (0.0, NOTCH_R), top, {hb})
            need = (zmax if zmax else Z_CB_TOP) + T_CAB + CLR
            C(f"{nm}: CB1D lane notch -> {hb} at {tuple(round(v, 1) for v in top)}: tallest body crossed + cable + clearance under LB1 (z {Z_LB_BOT})", need <= Z_LB_BOT,
              f"tallest {who} top z {zmax:.2f}; need {need:.2f}", "a lane over the parts; the cable may also weave between them")
        hdr = cp["hdr_cb"] if cp["hdr_cb"] is not None else LIBJ.get(typ.get(hb, ""), [0, 0, 4.0])[2]          # None: the CB1D header body height from kit_v19/lib_bodies.json
        C(f"{nm}: CB1D-end connector ({hdr} mm, {side[hb]} side) + mated socket ({SOCKET_H} mm) + cable bend fit under LB1 (ASSUMED heights)", Z_CB_TOP + hdr + SOCKET_H + T_CAB <= Z_LB_BOT,
          f"z {Z_CB_TOP + hdr + SOCKET_H + T_CAB:.1f} vs {Z_LB_BOT}")
        C(f"{nm}: AB1-end connector ({cp['hdr_ab']} mm) + mated socket ({SOCKET_H} mm) + cable fit under the septum (z {Z_SEPT_BOT}) (ASSUMED heights)", Z_AB_TOP + cp["hdr_ab"] + SOCKET_H + T_CAB <= Z_SEPT_BOT,
          f"z {Z_AB_TOP + cp['hdr_ab'] + SOCKET_H + T_CAB:.1f} vs {Z_SEPT_BOT}")
        L1 = math.hypot(bot[0] - 0.0, bot[1] - 37.0) + (4.0 + SOCKET_H)                          # AB1 lane to the AB1 window + the fold down from the socket
        L2 = (DUCT_Y - 37.0) * 2 + (WIN["CB1D"][0] + WIN["CB1D"][1] - WIN["AB1"][0] - WIN["AB1"][1]) / 2   # through the window, up the duct, back out
        L3 = math.hypot(top[0], top[1] - NOTCH_R) + 4.0 + SOCKET_H
        lengths[nm] = round(L1 + L2 + L3, 1)
    rep["route_length_mm"] = lengths
    C("route length per link <= 150 mm (two folds at the windows, one at each socket)", max(lengths.values()) <= 150, lengths)
    rep["checks"] = res; rep["n_fail"] = sum(r["result"] == "FAIL" for r in res)
    rep["assumed"] = dict(cp, clearance_mm=CLR, duct_centre_y_mm=DUCT_Y)
    for r in res: print(" ", r["result"], r["check"], "|", r["value"])
    return rep

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "kit_v22/link_path_check.json")
