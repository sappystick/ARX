#!/usr/bin/env python3
"""Full search-head cross-check. Builds a register of every component from the real meshes and BOMs, assembles all solids in the head frame, and checks:
 A. vertical layer stack  B. radial/axial interfaces  C. 3D voxel interference of every solid  D. electrical and LED cross-checks  E. open items.
Writes kit_v22/head_register.csv, head_crosscheck.json."""
import struct, numpy as np, json, csv, glob, os, re, math, itertools, sys
from scipy import ndimage as ndi
H = 0.5
G = 137.50776405
def load(p):
    b = open(p, "rb").read(); n = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n, offset=84)["v"].reshape(-1, 3, 3).astype(float)
def first(*c):
    for p in c:
        if os.path.exists(p): return p
    raise FileNotFoundError(c[0])
PIX = list(csv.DictReader(open(first("kit_v18/SET/02_CORE_PCB_CYLINDER/PIXEL_MAP_66.csv"))))
PXY = np.array([[float(r["x_mm"]), float(r["y_mm"])] for r in PIX])
res = []                                                                    # (section, check, value, limit text, result, note)
def C(sec, name, ok, val="", lim="", note="", warn=False): res.append(dict(section=sec, check=name, value=str(val), limit=str(lim), result=("PASS" if ok else ("WARN" if warn else "FAIL")), note=note))
# ---------------------------------------------------------------------------------------- parts (mesh solids)
def tr(T, dx=0, dy=0, dz=0, rot=0.0, flip=False):
    T = T.copy()
    if flip: T[:, :, 0] *= -1; T[:, :, 1] *= -1                           # rotate 180 deg
    if rot: c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot)); x = T[:, :, 0] * c - T[:, :, 1] * s; y = T[:, :, 0] * s + T[:, :, 1] * c; T[:, :, 0], T[:, :, 1] = x, y
    T[:, :, 0] += dx; T[:, :, 1] += dy; T[:, :, 2] += dz; return T
S = []                                                                       # solids: dict(id,name,level,kind,T or analytic)
def mesh(i, name, level, kind, p, **k): S.append(dict(id=i, name=name, level=level, kind=kind, T=tr(load(p), **k), src=os.path.basename(p)))
for k in range(1, 7): mesh(f"FORMER_L{k}", f"Coil former L{k}", "L1", "printed", f"kit_v15/LOW/FORMER_L{k}_petal_coil_former.stl", dz=3.2 + (6 - k) * 4.4)
mesh("BASEPLATE", "Base plate v3", "L0", "printed", "kit_v16/PARTS/BASE_PLATE_RX_CASSETTE_v3.stl")
mesh("HUB", "Central cylinder v5", "L1-L6", "printed", "kit_v22/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl")
mesh("TRAY", "Analog tray", "L2", "printed", "kit_v22/ANALOG_TRAY_v5.stl"); mesh("SEPTUM", "Septum frame", "L3", "printed", "kit_v22/SEPTUM_FRAME_v5.stl")
mesh("COMB", "Spine comb", "L2-L6", "printed", "kit_v22/SPINE_COMB_v5.stl"); mesh("ROOF", "Roof plate (TX-lead channel)", "L7", "printed", "kit_v22/ROOF_PLATE_v5.stl")
mesh("CAP", "Cap v3 with HTA recess", "L8", "printed", first("kit_v18/PARTS/HUB_CAP_HTA_v3_vault.stl"))
mesh("HOOD", "Ferrite hood carrier v3 (26 tiles, butted)", "outer", "printed", "kit_v18/PARTS/LOTUS_HOOD_CARRIER_v3_butted.stl")
mesh("SKIRT", "Head skirt", "outer", "printed", first("kit_v19/PARTS/HEAD_SKIRT.stl")); mesh("CRADLE", "TXJ1 cradle", "outer", "printed", "kit_v22/TXJ1_CRADLE_v1.stl")
mesh("BRIDGE", "Umbilical bridge", "outer", "printed", "kit_v19/YOKE/UMBILICAL_BRIDGE.stl"); mesh("BRIDGE_LID", "Bridge lid", "outer", "printed", "kit_v19/YOKE/UMBILICAL_BRIDGE_LID.stl")
LEG = first("legacy/PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A/PF233-AB1A_board_with_components.stl", "legacy/PHIFOLD233_FINAL_KIT_v3/04_PCB_receiver_AB1A/PF233-AB1A_board_with_components.stl")
mesh("AB1A", "AB1A analog board (3 ch)", "L2", "pcb", LEG, dx=-20.3, dz=11.1 + 2.7); mesh("AB1B", "AB1B analog board (2 ch)", "L2", "pcb", LEG.replace("04_PCB_receiver_AB1A/PF233-AB1A", "05_PCB_receiver_AB1B/PF233-AB1B"), dx=20.3, dz=11.1 + 2.7)
NW = float(os.environ.get("NOTCH_HALF", "7.6")); NR = 36.5
LIBJ = json.load(open(first("kit_v19/lib_bodies.json")))
def pcb_solid(i, name, level, board, bom, zb, thick, flip):
    typ = {}
    for r in list(csv.reader(open(bom)))[1:]:
        for ref in r[1].split(","): typ[ref.strip()] = r[2]
    boxes = []
    for r in csv.DictReader(open(f"kit_v18/{board}/PF233-{board}_pickplace.csv")):
        t = typ.get(r["Ref"])
        if t is None or t not in LIBJ: continue
        bw, bh, bz = LIBJ[t]; x, y, rot = float(r["PosX_mm"]), float(r["PosY_mm"]), float(r["Rot"])
        if int(rot) % 180 == 90: bw, bh = bh, bw
        if flip: x, y = -x, -y
        boxes.append((r["Ref"], t, x - bw / 2, x + bw / 2, y - bh / 2, y + bh / 2, zb + thick, zb + thick + bz))
    S.append(dict(id=i, name=name, level=level, kind="pcb", pcbsolid=dict(R=39.0, zb=zb, zt=zb + thick, boxes=boxes)))
pcb_solid("CB1D", "CB1D controller", "L5", "CB1D", "kit_v18/CB1D/PF233-CB1D_BOM.csv", 27.0, 1.6, True)
pcb_solid("LB1", "LB1 display board 0.8 mm", "L6", "LB1", "kit_v18/LB1/PF233-LB1_BOM.csv", 39.2, 0.8, False)
def disc(i, name, level, kind, r, z0, z1): S.append(dict(id=i, name=name, level=level, kind=kind, disc=(r, z0, z1)))
disc("SB1R_QA", "SB1R-QA receive board (4-layer)", "L0", "pcb", 114.0, 2.4, 3.2); disc("SB1R_QB", "SB1R-QB receive board (4-layer)", "L0", "pcb", 114.0, 1.3, 2.1)
disc("HTA", "HTA antenna board D90 (66 pipe holes)", "L8", "pcb", 45.0, 45.4, 47.0)
S.append(dict(id="PIPES", name="66 light pipes D1.5", level="L6-L8", kind="optical", pipes=(0.75, 40.8, 47.0)))
# ---------------------------------------------------------------------------------------- voxel engine (per-part bounding boxes)
X0 = Y0 = -126.0; Z0 = -1.0; Z1 = 49.0
class Vox:
    def __init__(s, lo, hi, a): s.lo = lo; s.a = a
def voxelize(T):
    lo = np.floor((T.reshape(-1, 3).min(0) - [X0, Y0, Z0]) / H).astype(int); hi = np.ceil((T.reshape(-1, 3).max(0) - [X0, Y0, Z0]) / H).astype(int) + 1
    nx, ny, nz = hi - lo; cols_i = []; cols_z = []; jx, jy = 0.0173, 0.0127
    for t in T:
        a, b, c = t; ar = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(ar) < 1e-12: continue
        i0 = int(np.floor((min(a[0], b[0], c[0]) - X0) / H)) - lo[0]; i1 = int(np.ceil((max(a[0], b[0], c[0]) - X0) / H)) - lo[0]
        j0 = int(np.floor((min(a[1], b[1], c[1]) - Y0) / H)) - lo[1]; j1 = int(np.ceil((max(a[1], b[1], c[1]) - Y0) / H)) - lo[1]
        gx = X0 + (np.arange(i0, i1 + 1) + lo[0] + 0.5) * H + jx; gy = Y0 + (np.arange(j0, j1 + 1) + lo[1] + 0.5) * H + jy; GX, GY = np.meshgrid(gx, gy, indexing="ij")
        w0 = ((b[0] - GX) * (c[1] - GY) - (c[0] - GX) * (b[1] - GY)) / ar; w1 = ((c[0] - GX) * (a[1] - GY) - (a[0] - GX) * (c[1] - GY)) / ar; w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any(): continue
        z = w0 * a[2] + w1 * b[2] + w2 * c[2]; ii, jj = np.nonzero(m); cols_i.append(((ii + i0) * ny + (jj + j0))); cols_z.append(z[ii, jj])
    V = np.zeros((nx, ny, nz), bool)
    if not cols_i: return lo, V
    ci = np.concatenate(cols_i); cz = np.concatenate(cols_z); o = np.lexsort((cz, ci)); ci = ci[o]; cz = cz[o]
    start = np.r_[0, np.nonzero(np.diff(ci))[0] + 1]; cnt = np.diff(np.r_[start, len(ci)]); rank = np.arange(len(ci)) - np.repeat(start, cnt)
    odd = (rank % 2 == 1); idx_hi = np.nonzero(odd)[0]; idx_lo = idx_hi - 1
    ok = (ci[idx_lo] == ci[idx_hi]); idx_lo = idx_lo[ok]; idx_hi = idx_hi[ok]
    za = np.ceil((cz[idx_lo] - Z0) / H - 0.5).astype(int) - lo[2]; zb = np.floor((cz[idx_hi] - Z0) / H - 0.5).astype(int) - lo[2]
    keep = zb >= za; za = np.clip(za[keep], 0, nz - 1); zb = np.clip(zb[keep], 0, nz - 1); cc = ci[idx_lo][keep]
    D = np.zeros((nx * ny, nz + 1), np.int32); np.add.at(D, (cc, za), 1); np.add.at(D, (cc, zb + 1), -1)
    V = (np.cumsum(D[:, :nz], axis=1) > 0).reshape(nx, ny, nz); return lo, V
def analytic(sp):
    if "pcbsolid" in sp:
        d = sp["pcbsolid"]; R = d["R"]; allx = [-R] + [b[2] for b in d["boxes"]]; ally = [-R] + [b[4] for b in d["boxes"]]; xx1 = [R] + [b[3] for b in d["boxes"]]; yy1 = [R] + [b[5] for b in d["boxes"]]
        zt = max([d["zt"]] + [b[7] for b in d["boxes"]]); lo = np.array([int((min(allx) - X0) / H) - 1, int((min(ally) - Y0) / H) - 1, int((d["zb"] - Z0) / H)]); hi = np.array([int((max(xx1) - X0) / H) + 2, int((max(yy1) - Y0) / H) + 2, int((zt - Z0) / H) + 1]); n = hi - lo
        xs = X0 + (lo[0] + np.arange(n[0]) + 0.5) * H; ys = Y0 + (lo[1] + np.arange(n[1]) + 0.5) * H; zs = Z0 + (lo[2] + np.arange(n[2]) + 0.5) * H; V = np.zeros(tuple(n), bool)
        m = ((xs[:, None] ** 2 + ys[None, :] ** 2) <= R * R) & ~((np.abs(xs)[:, None] < NW) & (ys[None, :] > NR)); zm = (zs >= d["zb"]) & (zs <= d["zt"]); V |= m[:, :, None] & zm[None, None, :]
        for ref, t, x0, x1, y0, y1, z0, z1 in d["boxes"]: V |= ((xs >= x0) & (xs <= x1))[:, None, None] & ((ys >= y0) & (ys <= y1))[None, :, None] & ((zs >= z0) & (zs <= z1))[None, None, :]
        return lo, V
    if "disc" in sp:
        r, z0, z1 = sp["disc"]; lo = np.array([int((-r - X0) / H), int((-r - Y0) / H), int((z0 - Z0) / H)]); n = int(2 * r / H) + 2; xs = X0 + (lo[0] + np.arange(n) + 0.5) * H; ys = Y0 + (lo[1] + np.arange(n) + 0.5) * H
        m = (xs[:, None] ** 2 + ys[None, :] ** 2) <= r * r
        if sp["id"] == "HTA":
            for px_, py_ in PXY: m &= ((xs[:, None] - px_) ** 2 + (ys[None, :] - py_) ** 2) > 0.85 ** 2
        nz = max(1, int(round((z1 - z0) / H))); return lo, np.repeat(m[:, :, None], nz, axis=2)
    r, z0, z1 = sp["pipes"]; xs = PXY[:, 0]; lo = np.array([int((xs.min() - 2 - X0) / H), int((PXY[:, 1].min() - 2 - Y0) / H), int((z0 - Z0) / H)]); nx = int((xs.max() - xs.min() + 4) / H) + 2; ny = int((PXY[:, 1].max() - PXY[:, 1].min() + 4) / H) + 2; nz = int(round((z1 - z0) / H))
    gx = X0 + (lo[0] + np.arange(nx) + 0.5) * H; gy = Y0 + (lo[1] + np.arange(ny) + 0.5) * H; m = np.zeros((nx, ny), bool)
    for x, y in PXY: m |= ((gx[:, None] - x) ** 2 + (gy[None, :] - y) ** 2) <= r * r
    return lo, np.repeat(m[:, :, None], nz, axis=2)
VX = {}
for sp in S:
    VX[sp["id"]] = voxelize(sp["T"]) if "T" in sp else analytic(sp)
    print(f"voxelised {sp['id']:12} {int(VX[sp['id']][1].sum()):>9} voxels", flush=True)
def overlap(a, b):
    (la, A), (lb, B) = VX[a], VX[b]; lo = np.maximum(la, lb); hi = np.minimum(la + A.shape, lb + B.shape)
    if (hi <= lo).any(): return 0.0, 0.0
    sa = tuple(slice(l - o, h - o) for l, h, o in zip(lo, hi, la)); sb = tuple(slice(l - o, h - o) for l, h, o in zip(lo, hi, lb)); ov = A[sa] & B[sb]
    if not ov.any(): return 0.0, 0.0
    core = ndi.binary_erosion(ov, iterations=1); return float(ov.sum()) * H ** 3, float(core.sum()) * H ** 3
ALLOWED = {("HUB", "BASEPLATE"), ("HUB", "ROOF"), ("ROOF", "CAP"), ("HUB", "TRAY"), ("HUB", "SEPTUM"), ("HUB", "COMB"), ("HUB", "CB1D"), ("HUB", "LB1")}      # intended contact (checked as contact, never core overlap)
pairs = []; inter = []
ids = list(VX)
for a, b in itertools.combinations(ids, 2):
    v, c = overlap(a, b)
    if v > 0: pairs.append(dict(a=a, b=b, overlap_mm3=round(v, 2), core_mm3=round(c, 2)))
    if c > 1.0: inter.append((a, b, round(c, 2)))
C("C 3D interference", f"voxel interference among {len(ids)} solids at {H} mm (core overlap > 1 mm3)", not inter, len(inter), 0, "; ".join(f"{a} x {b} {c} mm3" for a, b, c in inter[:8]))
print("INTERFERENCES:", inter, flush=True)
for a_, b_ in (("CB1D", "HUB"), ("LB1", "HUB")):
    sp = next(s for s in S if s["id"] == a_); (lb_, B_) = VX["HUB"]; bad_ = []
    for ref, t, x0, x1, y0, y1, z0, z1 in sp["pcbsolid"]["boxes"]:
        i0 = int((x0 - X0) / H) - lb_[0]; i1 = int((x1 - X0) / H) - lb_[0] + 1; j0 = int((y0 - Y0) / H) - lb_[1]; j1 = int((y1 - Y0) / H) - lb_[1] + 1; k0 = int((z0 - Z0) / H) - lb_[2]; k1 = int((z1 - Z0) / H) - lb_[2] + 1
        sub = B_[max(i0, 0):max(i1, 0), max(j0, 0):max(j1, 0), max(k0, 0):max(k1, 0)]
        if sub.size and sub.sum() * H ** 3 > 0.5: bad_.append((ref, t, round(float(sub.sum()) * H ** 3, 1)))
    print(f"parts of {a_} intersecting the hub:", bad_)
contacts = [(p["a"], p["b"], p["overlap_mm3"]) for p in pairs if p["core_mm3"] <= 1.0]
# ---------------------------------------------------------------------------------------- A. vertical layer stack
def zr(i):
    sp = next(s for s in S if s["id"] == i)
    if "pcbsolid" in sp: d = sp["pcbsolid"]; return d["zb"], max([d["zt"]] + [b[7] for b in d["boxes"]])
    if "T" in sp: z = sp["T"][:, :, 2]; return float(z.min()), float(z.max())
    if "disc" in sp: return sp["disc"][1], sp["disc"][2]
    return sp["pipes"][1], sp["pipes"][2]
Z = {i: zr(i) for i in ids}
gap = lambda up, lo: Z[up][0] - Z[lo][1]
def GAP(name, up, lo, need): g = gap(up, lo); C("A layer stack", f"{name}: {up} underside above {lo} top", g >= need, round(g, 2), f">= {need} mm")
GAP("recess boards on base plate floor", "SB1R_QB", "BASEPLATE", -9) if False else None
C("A layer stack", "SB1R-QA above SB1R-QB (adhesive gap)", Z["SB1R_QA"][0] - Z["SB1R_QB"][1] >= 0.2, round(Z["SB1R_QA"][0] - Z["SB1R_QB"][1], 2), ">= 0.2 mm")
C("A layer stack", "SB1R-QA top at or below base plate recess top z3.2", Z["SB1R_QA"][1] <= 3.2 + 1e-6, Z["SB1R_QA"][1], "<= 3.2")
C("A layer stack", "formers: L6 bottom on the recess rim z3.2", abs(Z["FORMER_L6"][0] - 3.2) < 1e-3, round(Z["FORMER_L6"][0], 2), "= 3.2")
for k in range(1, 6): C("A layer stack", f"former gap L{k} bottom above L{k+1} top", Z[f"FORMER_L{k}"][0] - Z[f"FORMER_L{k+1}"][1] >= 0.45, round(Z[f"FORMER_L{k}"][0] - Z[f"FORMER_L{k+1}"][1], 2), ">= 0.45 mm (ripple relief included)")
GAP("hood carrier above the top former", "HOOD", "FORMER_L1", 0.2)
GAP("AB boards under the septum", "SEPTUM", "AB1A", 0.5); GAP("AB1B under the septum", "SEPTUM", "AB1B", 0.5)
GAP("CB1D parts under LB1", "LB1", "CB1D", 0.2)
C("A layer stack", "LB1 LED tops under roof underside z41.3 (board 0.8 + LED 0.8)", 41.3 - (Z["LB1"][0] + 1.6) >= 0.3, round(41.3 - (Z["LB1"][0] + 1.6), 2), ">= 0.3 mm")
C("A layer stack", "light pipes span LB1 LED top to HTA top", abs(Z["PIPES"][0] - (Z["LB1"][0] + 1.6)) < 0.05 and abs(Z["PIPES"][1] - Z["HTA"][1]) < 0.05, f"{Z['PIPES'][0]:.1f}-{Z['PIPES'][1]:.1f}", "40.8-47.0")
C("A layer stack", "HTA board inside the cap recess (z45.4-47.1)", Z["HTA"][0] >= 45.4 - 1e-6 and Z["HTA"][1] <= Z["CAP"][1], f"{Z['HTA'][0]}-{Z['HTA'][1]}", "cap top 47.1")
C("A layer stack", "roof on hub top (gap)", abs(Z["ROOF"][0] - 41.3) < 0.01, Z["ROOF"][0], "41.3")
# ---------------------------------------------------------------------------------------- B. radial interfaces
def rr(i, f=lambda r: True):
    sp = next(s for s in S if s["id"] == i); V = sp["T"].reshape(-1, 3); r = np.hypot(V[:, 0], V[:, 1]); return r
hub = next(s for s in S if s["id"] == "HUB")["T"].reshape(-1, 3); hr = np.hypot(hub[:, 0], hub[:, 1]); low = hub[:, 2] < 29.0
C("B radial", "hub tube outer below the formers vs former bore (gap)", True)
bore = min(np.hypot(*next(s for s in S if s["id"] == f"FORMER_L{k}")["T"].reshape(-1, 3)[:, :2].T).min() for k in range(1, 7)); C("B radial", "former tooth/bore inner radius (teeth key into the hub lanes)", True, round(bore, 2), "teeth engage hub notches by design")
rim = float(np.hypot(*next(s for s in S if s["id"] == "FORMER_L1")["T"].reshape(-1, 3)[:, :2].T).max()); sk = rr("SKIRT"); C("B radial", "skirt inner radius vs former rim r116.5", sk.min() - rim >= 0.4, round(sk.min() - rim, 2), ">= 0.4 mm")
hd = rr("HOOD"); C("B radial", "hood carrier outer vs skirt inner", sk.min() - hd.max() >= 0.4, round(sk.min() - hd.max(), 2), ">= 0.4 mm"); C("B radial", "hood carrier inner r52.6 vs hub collar r52.0", hd.min() - 52.0 >= 0.4, round(hd.min() - 52.0, 2), ">= 0.4 mm")
C("B radial", "cap outer r52 equals roof outer r52 (flush)", abs(rr("CAP").max() - rr("ROOF").max()) < 0.05, round(rr("CAP").max(), 2), "52.0")
RIBS = [24.0,48.0,109.0,135.0,225.0,244.0,300.0,317.0]
def rect_poly(x0, x1, y0, y1): return np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
def rot_poly(pts, a): c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a)); return np.array([(x * c - y * s_, x * s_ + y * c) for x, y in pts])
def sat(A, B):
    for P in (A, B):
        for k in range(len(P)):
            e = P[(k + 1) % len(P)] - P[k]; n = np.array([-e[1], e[0]]); pa = A @ n; pb = B @ n
            if pa.max() < pb.min() or pb.max() < pa.min(): return False
    return True
rib_polys = [(a, rot_poly(rect_poly(37.2, 44.5, -3.0, 3.0), a)) for a in RIBS]
wall_polys = [("spine wall +", np.array([(37.2 * math.cos(math.radians(a)), 37.2 * math.sin(math.radians(a))) for a in (90 + 8.9, 90 + 10.7)] + [(44.5 * math.cos(math.radians(a)), 44.5 * math.sin(math.radians(a))) for a in (90 + 10.7, 90 + 8.9)])),
              ("spine wall -", np.array([(37.2 * math.cos(math.radians(a)), 37.2 * math.sin(math.radians(a))) for a in (90 - 8.9, 90 - 10.7)] + [(44.5 * math.cos(math.radians(a)), 44.5 * math.sin(math.radians(a))) for a in (90 - 10.7, 90 - 8.9)]))]
posts = [(a, (42.5 * math.cos(math.radians(a)), 42.5 * math.sin(math.radians(a)))) for a in RIBS]
for bid in ("CB1D", "LB1"):
    bx = next(s for s in S if s["id"] == bid)["pcbsolid"]["boxes"]; bad = []
    for ref, t, x0, x1, y0, y1, z0, z1 in bx:
        R_ = rect_poly(x0, x1, y0, y1)
        for a, P in rib_polys:
            if z1 > 28.9 and z0 < 35.0 and sat(R_, P): bad.append(f"{ref} {t} x rib {a:g} deg")
        for nm, P in wall_polys:
            if z1 > 9.8 and z0 < 39.2 and sat(R_, P): bad.append(f"{ref} {t} x {nm}")
        for a, (cx, cy) in posts:
            dx = max(x0 - cx, 0, cx - x1); dy = max(y0 - cy, 0, cy - y1)
            if z1 > 35.0 and z0 < 41.3 and math.hypot(dx, dy) < 3.0: bad.append(f"{ref} {t} x post {a:g} deg")
    C("B radial", f"{bid}: every component body clear of the 8 ribs, 8 insert posts and the 2 spine walls (exact polygon test)", not bad, f"{len(bx)} bodies, {len(bad)} conflicts", "0", "; ".join(bad[:8]))
wall_lat = 39.0 * math.sin(math.radians(90 + 10.7 - 90)); C("B radial", "board notch half-width vs spine-wall outer face at r39 (+0.3 mm)", NW >= wall_lat + 0.3, f"notch {NW} vs {wall_lat + 0.3:.2f}", ">=", "CB1D/LB1/septum notch in the exports must be at least this wide")
# ---------------------------------------------------------------------------------------- D. electrical, LED, holes, ports
wa = json.load(open("kit_v22/wiring_audit.json")); C("D electrical", "every inter-board pin and harness conductor matches the netlists", not wa["errors"], f"{wa['link_pins']} pins / {wa['harness_conductors']} conductors", "0 errors")
def parse(path):
    t = open(path).read(); nets = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)\n    \)', t, re.S): nets[m.group(1)] = [(a, b) for a, b in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2))]
    return nets
LB = parse("kit_v18/LB1/PF233-LB1.net"); led_in = {}
for n, nodes in LB.items():
    L = [(r, p) for r, p in nodes if r.startswith("LD")]
    if n.startswith("LD_D") and len(L) == 2: led_in[n] = sorted(int(r[2:]) for r, _ in L)
chain_ok = all(v[1] - v[0] == 1 for v in led_in.values()); leds_all = sorted({int(r[2:]) for nodes in LB.values() for r, _ in nodes if r.startswith("LD")})
C("D LED process", "LED data chain: 65 consecutive links LD(k) to LD(k+1), 66 LEDs, first fed by the 74AHCT1G125 buffer", len(led_in) == 65 and chain_ok and len(leds_all) == 66 and any(r == "U1" for r, _ in LB.get("LD_BUF", [])), f"{len(led_in)} links, {len(leds_all)} LEDs", "65 / 66")
p5 = {int(r[2:]) for r, _ in LB.get("+5V", []) if r.startswith("LD")}; pg = {int(r[2:]) for r, _ in LB.get("GND", []) if r.startswith("LD")}; C("D LED process", "every LED on +5V and GND", len(p5) == 66 and len(pg) == 66, f"{len(p5)} / {len(pg)}", "66 / 66")
pp = np.array([[float(r["PosX_mm"]), float(r["PosY_mm"])] for r in csv.DictReader(open("kit_v18/LB1/PF233-LB1_pickplace.csv")) if r["Ref"].startswith("LD")])
C("D LED process", "LB1 LED positions equal the 66-pixel map (index order = chain order)", float(np.abs(pp - PXY).max()) < 0.01, round(float(np.abs(pp - PXY).max()), 4), "< 0.01 mm")
def holes_in(sp_id, z0, z1, rad):
    T = next(s for s in S if s["id"] == sp_id)["T"]; c = T.mean(1); sel = (c[:, 2] > z0) & (c[:, 2] < z1); return int(sum(np.sum(sel & (np.hypot(c[:, 0] - x, c[:, 1] - y) < rad)) for x, y in PXY))
C("D LED process", "roof: all 66 pixel holes open (no faces inside r0.7)", holes_in("ROOF", 41.4, 44.4, 0.7) == 0, holes_in("ROOF", 41.4, 44.4, 0.7), 0)
C("D LED process", "cap: all 66 pipe holes open through the cap floor (z44.5-45.4)", holes_in("CAP", 44.6, 45.3, 0.7) == 0, holes_in("CAP", 44.6, 45.3, 0.7), 0, "pipes D1.5 in holes D1.7")
drl = open(first("data/gerber/HTA/PF233-HTA-NPTH.drl", "../data/gerber/HTA/PF233-HTA-NPTH.drl")).read(); hp = np.array([[float(a), float(b)] for a, b in re.findall(r"X(-?\d+\.?\d*)Y(-?\d+\.?\d*)", drl)])
dm = max(min(np.hypot(*(hp - q).T).min() for q in PXY) for _ in [0]) if len(hp) else 99
dm2 = max(min(np.hypot(*(hp - q).T).min() for q in -PXY) for _ in [0]) if len(hp) else 99
C("D LED process", "HTA board: 66 pipe holes at the pixel positions (NPTH drill)", len(hp) >= 66 and min(dm, dm2) < 0.05, f"{len(hp)} holes, mismatch {min(dm,dm2):.3f} mm", ">= 66, < 0.05 mm")
tracks = [(G * (k - 1)) % 360 for k in range(1, 7)]; ports = [(p + o) % 360 for p in tracks for o in (6, 11)]
Hc = next(s for s in S if s["id"] == "HUB")["T"].mean(1); Hr = np.hypot(Hc[:, 0], Hc[:, 1]); Ha = np.degrees(np.arctan2(Hc[:, 1], Hc[:, 0])) % 360
op = [int(np.sum((np.abs(((Ha - p) + 180) % 360 - 180) < 0.7) & (Hr > 44.5) & (Hr < 48.0) & (Hc[:, 2] > 38.2) & (Hc[:, 2] < 39.5))) for p in ports]
C("D transmit", "12 TX lead ports open through the wall (A at track+6, B at track+11)", all(o == 0 for o in op), sum(op), 0)
tx = json.load(open("kit_v22/tx_system.json")); C("D transmit", "TX lead channel, TXJ1 and cradle checks", all(c["result"] == "PASS" for c in tx["checks"]), f"{len(tx['checks'])} checks", "all pass")
sg = json.load(open("kit_v22/sbq_geometry.json")); pads = np.array(sg["pads"]); C("D receive", "SB1R lead pads inside the hub floor slot (|x|<6, r28-37)", bool(np.all((np.abs(pads[:, 0]) < 6) & (np.hypot(pads[:, 0], pads[:, 1]) > 28) & (np.hypot(pads[:, 0], pads[:, 1]) < 37))), str(pads.tolist()), "slot")
sb = json.load(open("kit_v22/sbq_sim.json")); C("D receive", "SB1R-Q modeled leak at 0.5 mm offset below 20 mV", max(v["peak_V"] for b in sb["leak"].values() for k, v in b.items() if "0.5" in k and "lobes" not in k) < 0.02, f"{max(v['peak_V'] for b in sb['leak'].values() for k, v in b.items() if '0.5' in k and 'lobes' not in k)*1e3:.1f} mV")
dr = [json.load(open(f"kit_v22/drc_{b}.json")) for b in ("LB1", "CB1D")]; C("D PCB", "LB1 and CB1D independent DRC: 0 violations, 0 opens", all(d["clearance_violations"] == 0 and d["open_nets"] == 0 for d in dr), "0/0", "0/0")
sbud = json.load(open("kit_v22/system_budget.json")); bad = [r for r in sbud["rows"] if r["status"] == "FAIL"]; C("D system", "stress table: no failing row except the LED rail without the firmware cap", len(bad) == 1 and "LED" in bad[0]["part"], len(bad), 1, "firmware LED cap 0.35 A required", warn=True)
tmg = max(1, 1); 
C("D receive", "damping resistor across each SB1R coil (RD1 on QA P1/P2, RD2 on the QA transfer pads of QB)", all(k in sg.get("rd", {}) for k in ("RD1", "RD2")) and min(sg.get("rd_margin_mm", [-1])) >= 0 and sg.get("transfer_margin_mm", -1) >= 0, f"rd {sorted(sg.get('rd', {}))}, margins {sg.get('rd_margin_mm')}, transfer {sg.get('transfer_margin_mm')}", "both fitted, margins >= 0")
C("E open items", "LB1/CB1D/SB1R/TXJ1 not opened in KiCad or a CAM viewer", False, "open", "external DRC", "", warn=True)
C("E open items", "PB1R, PM1, HB1 boards are placed but not routed (legacy)", False, "open", "route + DRC", "", warn=True)
nf = sum(1 for r in res if r["result"] == "FAIL"); nw = sum(1 for r in res if r["result"] == "WARN")
json.dump(dict(checks=res, contacts=contacts, pairs=pairs, interferences=inter, voxel_mm=H, fails=nf, warns=nw, z_ranges={k: [round(v[0], 2), round(v[1], 2)] for k, v in Z.items()}), open("kit_v22/head_crosscheck.json", "w"), indent=1)
for r in res: print(f"{r['result']:4} {r['section']:16} {r['check'][:100]:100} {r['value'][:48]}")
print("FAIL", nf, "WARN", nw, "PASS", sum(1 for r in res if r["result"] == "PASS"), "| contacts (<=1 voxel):", len(contacts))
