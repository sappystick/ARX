import struct, numpy as np, math, json, csv, sys
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3).astype(np.float64)
def rz(V): return np.hypot(V[:,0],V[:,1]),V[:,2]
R=[]; 
def chk(name,value,lo=None,hi=None,unit="mm",note=""):
    ok=True
    if lo is not None and value<lo: ok=False
    if hi is not None and value>hi: ok=False
    R.append(dict(check=name,value=round(float(value),3),min=lo,max=hi,result="PASS" if ok else "FAIL",note=note)); return ok
HUB=load("kit_v19/SET/02_CORE_PCB_CYLINDER/CORE_PCB_CYLINDER_v4_heel_exit.stl"); r,z=rz(HUB)
bore=r[(np.abs(z-6.3)<1e-3)&(r>43)&(r<45)].min()
led_in={zt:r[(np.abs(z-zt)<1e-3)&(r>40)&(r<45)].min() for zt in (9.0,17.0,25.0,33.0)}
roof_r=r[(np.abs(z-44.5)<1e-3)].max(); collar_r=r.max()
CUP={n:load(f"kit_v19/PARTS/{n}.stl") for n in ("VAULT_CUP_A_ANALOG","VAULT_CUP_B_ISOLATION","VAULT_CUP_CD_CONTROL_DISPLAY")}
zl={"VAULT_CUP_A_ANALOG":9.0,"VAULT_CUP_B_ISOLATION":17.0,"VAULT_CUP_CD_CONTROL_DISPLAY":25.0}
for n,V in CUP.items():
    cr,cz=rz(V); z0=zl[n]; fl=cr[cz<z0+0.81].max(); wo=cr[cz>z0+0.9].max(); top=cz.max()
    chk(f"{n} flange r vs hub bore",bore-fl,0.1,None,note=f"bore {bore:.2f}, flange {fl:.2f}")
    chk(f"{n} wall outer r vs ledge holes above",min(v for k,v in led_in.items() if k>z0)-wo,0.1,None,note=f"smallest ledge hole above {min(v for k,v in led_in.items() if k>z0):.2f}, wall {wo:.2f}")
    nxt=[k for k in (9.0,17.0,25.0,33.0) if k>z0]
    if n!="VAULT_CUP_CD_CONTROL_DISPLAY": chk(f"{n} wall top vs next ledge underside",(nxt[0]-1.2)-top,0.0,None,note=f"top {top:.2f}, ledge underside {nxt[0]-1.2:.2f}")
    else: chk(f"{n} wall top vs roof underside",41.3-top,0.5,None,note=f"top {top:.2f}")
# boards in cups (analytic from the placed designs)
chk("AB boards: far edge vs cup A interior",40.7-(20.3+20.0),0.2,None,note="boards D40 at x=+/-20.3")
chk("AB1A/AB1B gap",2*20.3-40.0,0.3,None,note="0.3 mm foil shim")
chk("cup A: AB top (standoff 1.3 + board 1.6 + parts 4.0) vs lid underside z17",17.0-(9.8+1.3+1.6+4.0),0.2,None)
chk("cup A: AB bottom-side parts (1.1) vs floor top",(9.8+1.3-1.1)-9.8,0.1,None)
chk("cup CD: CB1D tallest part (10.2) top vs LB1 underside",39.2-(28.6+10.2),0.3,None,note="CB1D board top 28.6")
chk("cup CD: LB1 LED top vs roof underside",41.3-(39.2+0.8+0.8),0.4,None,note="LB1 0.8 thick + LED 0.8")
chk("CB1D board edge vs cup interior",40.7-39.0,1.0,None); chk("CB1D tab overlap under board",39.0-37.5,1.0,None)
# hood vs hub, vs L1, vs footprint
HOOD=load("kit_v18/PARTS/LOTUS_HOOD_CARRIER_v2_spokes.stl")
hr,hz=rz(HOOD); chk("hood bore vs hub collar/roof radius",hr.min()-collar_r,0.3,None,note=f"bore {hr.min():.2f}, hub max r {collar_r:.2f}")
chk("hood outer vs 116.5 footprint",116.5-hr.max(),0.0,None,note=f"hood {hr.max():.2f}")
L1=load("kit_v15/LOW/FORMER_L1_petal_coil_former.stl"); l1top=L1[:,2].max()+25.2; chk("hood floor underside vs L1 top",hz.min()-l1top,0.1,None,note=f"L1 top {l1top:.2f}, hood floor {hz.min():.2f}")
chk("L1 outer radius",116.6-np.hypot(L1[:,0],L1[:,1]).max(),0.0,None)
SK=load("kit_v19/PARTS/HEAD_SKIRT.stl"); sr,sz=rz(SK); chk("skirt inner vs petal tips (r116.5)",sr.min()-116.5,0.3,None,note=f"skirt inner {sr.min():.2f}")
BP=load("kit_v16/PARTS/BASE_PLATE_RX_CASSETTE_v2.stl"); br,bz=rz(BP); chk("skirt inner vs base plate rim",sr.min()-br.max(),0.3,None)
chk("skirt top vs hood top",abs(sz.max()-HOOD[:,2].max()),None,0.01)
# cap hooks vs roof windows (plan view, at 45 deg)
CAP=load("kit_v18/PARTS/HUB_CAP_HTA_v3_vault.stl"); cr_,cz_=rz(CAP)
hk=CAP[(cz_<41.3)]; ang=np.degrees(np.arctan2(hk[:,1],hk[:,0]))%360; m=np.abs(ang-45)<8; hr_=np.hypot(hk[m,0],hk[m,1]); lat=np.abs(-hk[m,0]*math.sin(math.radians(45))+hk[m,1]*math.cos(math.radians(45)))
chk("hook lip outer r vs window edge (32.0): catch",hr_.max()-32.0,0.2,None,note=f"lip reaches {hr_.max():.2f}")
chk("hook tangential half-width vs window half-width 2.0",2.0-lat.max(),0.1,None,note=f"hook half-width {lat.max():.2f}")
# LED vs hook interference (SAT on rectangles in plan, z ranges overlap)
px=list(csv.DictReader(open("kit_v18/SET/02_CORE_PCB_CYLINDER/PIXEL_MAP_66.csv")))
def rect(cx,cy,ang,hx,hy):
    c,s=math.cos(ang),math.sin(ang); return np.array([(cx+x*c-y*s,cy+x*s+y*c) for x,y in ((-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy))])
def sat_gap(A,B):
    best=-1e9
    for P in (A,B):
        for i in range(4):
            e=P[(i+1)%4]-P[i]; n=np.array([-e[1],e[0]])/np.linalg.norm(e); a=A@n; b=B@n; best=max(best,max(b.min()-a.max(),a.min()-b.max()))
    return best
mg=1e9
for a in (45,135,225,315):
    H=rect(30.5*math.cos(math.radians(a)),30.5*math.sin(math.radians(a)),math.radians(a),2.0,1.7)   # hook stem + lip footprint r28.6-32.4
    for p in px:
        x,y=float(p["x_mm"]),float(p["y_mm"]); L=rect(x,y,0.0,1.6,1.4); mg=min(mg,sat_gap(H,L))
chk("min gap between any snap hook and any LED body (plan view)",mg,0.3,None,note="hook z40.4-41.2 overlaps LED z40.0-40.8")
# hood v2: numbers from the build (tile gaps, pocket intrusion, corner radius), plus the mesh-measured outer radius vs the skirt
H=json.load(open("kit_v18/PARTS/hood_report.json"))["hood_v2_audit"]
chk("hood v2: smallest gap between neighbouring tiles",H["min_tile_gap"],1.6,None)
chk("hood v2: pocket wall of one tile vs the pocket of its neighbour (0 = touching, no intrusion)",H["frame_into_neighbour_pocket_gap"],0.0,None)
chk("hood v2: outer frame corner radius vs skirt inner 117.0",117.0-H["outer_frame_corner_r"],0.8,None,note=f"corner {H['outer_frame_corner_r']}")
chk("hood v2: inner frame radius vs hood bore 52.6",H["inner_frame_r"]-52.6,2.0,None,note=f"inner {H['inner_frame_r']}")
chk("hood v2: mesh outer radius vs skirt inner",sr.min()-hr.max(),0.8,None,note=f"mesh max r {hr.max():.2f}")
chk("hood: 26 tiles of 2 sizes (13 + 13)",H["tiles"],26,26)
json.dump(R,open("kit_v19/audit_v20_after.json","w"),indent=1)
for x in R: print(("%-4s"%x["result"]),x["check"],"=",x["value"],"|",x["note"])
print("FAILS:",sum(1 for x in R if x["result"]=="FAIL"),"of",len(R))
