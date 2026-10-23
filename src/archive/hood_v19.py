# SUPERSEDED by src/mech/hood_v20.py (hood v3, butted tiles, 2026-10-23). v2 held each spoke's two tiles in separate pockets with a 2.0 mm radial air gap. Kept for provenance.
import math, json, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
OUT="kit_v18/PARTS"; GOLD=137.50776405; rep={}
def circ(r,m=360): t=np.linspace(0,2*np.pi,m,endpoint=False); return np.c_[r*np.cos(t),r*np.sin(t)]
def ring(outer,inner,z0,z1):
    m=len(outer); V=np.concatenate([np.c_[outer,np.full(m,z0)],np.c_[outer,np.full(m,z1)],np.c_[inner,np.full(m,z0)],np.c_[inner,np.full(m,z1)]]); O0,O1,I0,I1=(np.arange(m)+k*m for k in range(4)); n=np.roll(np.arange(m),-1); F=[]
    for i in range(m): j=n[i]; F+=[[O0[i],O0[j],O1[j]],[O0[i],O1[j],O1[i]],[I0[j],I0[i],I1[i]],[I0[j],I1[i],I1[j]],[O0[j],O0[i],I0[i]],[O0[j],I0[i],I0[j]],[O1[i],O1[j],I1[j]],[O1[i],I1[j],I1[i]]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def extrude(poly,z0,z1):
    P=np.asarray(poly); m=len(P); T=tri2d(P); ar=(P[:,0]*np.roll(P[:,1],-1)-np.roll(P[:,0],-1)*P[:,1]).sum(); V=np.concatenate([np.c_[P,np.full(m,z0)],np.c_[P,np.full(m,z1)]]); F=[]
    for t in T: F.append([m+t[0],m+t[1],m+t[2]] if ar>0 else [m+t[0],m+t[2],m+t[1]]); F.append([t[0],t[2],t[1]] if ar>0 else [t[0],t[1],t[2]])
    for i in range(m): j=(i+1)%m; F+=[[i,j,m+j],[i,m+j,m+i]] if ar>0 else [[i,m+j,j],[i,m+i,m+j]]
    F=np.array(F); return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def sector(r0,r1,a0,a1,z0,z1):
    n=max(8,int(abs(a1-a0)*r1/0.4)); ang=np.linspace(a0,a1,n); return extrude(np.vstack([np.c_[r1*np.cos(ang),r1*np.sin(ang)],np.c_[r0*np.cos(ang),r0*np.sin(ang)][::-1]]),z0,z1)
def rectp(ang,r0,r1,half): c,s=math.cos(ang),math.sin(ang); return np.array([(x*c-y*s,x*s+y*c) for x,y in [(r0,-half),(r1,-half),(r1,half),(r0,half)]])
def rect_c(cx,cy,ang,hr,ht): c,s=math.cos(ang),math.sin(ang); return np.array([(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(hr,-ht),(hr,ht),(-hr,ht),(-hr,-ht)]])
def emit(name,shells,note):
    bad=sum(rc.edge_manifold_check(F)[1] for V,F in shells); V,F=g.merge(shells); rc.write_stl(f"{OUT}/{name}.stl",V,F,name); rep[name]=dict(shells=len(shells),tris=int(len(F)),nonmanifold_edges=int(bad),bbox=[round(float(x),2) for x in (*V.min(0),*V.max(0))],note=note)

import csv
def sat_gap(A,B):
    best=-1e9
    for Q in (A,B):
        for i in range(4):
            e=Q[(i+1)%4]-Q[i]; n=np.array([-e[1],e[0]])/np.linalg.norm(e); a=A@n; b=B@n; best=max(best,max(b.min()-a.max(),a.min()-b.max()))
    return best
def rect_pts(cx,cy,ang,hl,hw): c,s=math.cos(ang),math.sin(ang); return np.array([(cx+x*c-y*s,cy+x*s+y*c) for x,y in ((-hl,-hw),(hl,-hw),(hl,hw),(-hl,hw))])
N=13; GAP=1.7; SEG=[("inner",57.0,84.0),("outer",86.0,112.5)]; TT=2.5
tiles=[]; dims={}
for nm,r0,r1 in SEG:
    L=r1-r0; lo,hi=4.0,200.0
    for _ in range(50):
        w=(lo+hi)/2; th=2*math.pi/N; A=rect_pts((r0+r1)/2,0,0,L/2,w/2); B=rect_pts((r0+r1)/2*math.cos(th),(r0+r1)/2*math.sin(th),th,L/2,w/2)
        if sat_gap(A,B)>=GAP: lo=w
        else: hi=w
    w=math.floor(lo*10)/10; dims[nm]=(round(L,1),w)
    for i in range(N): t=2*math.pi*i/N; tiles.append((nm,i,(r0+r1)/2*math.cos(t),(r0+r1)/2*math.sin(t),t,L,w))
# carrier: base ring r52.6-115.8 (z29.4-30.4) + one open pocket frame per tile (wall 1.2, clearance 0.15 per side, 3.0 tall)
shells=[ring(circ(116.1,720),circ(52.6,720),29.4,30.4)]
for nm,i,cx,cy,t,L,w in tiles: shells.append(ring(rect_c(cx,cy,t,L/2+1.35,w/2+1.35),rect_c(cx,cy,t,L/2+0.15,w/2+0.15),30.4,33.4))
emit("LOTUS_HOOD_CARRIER_v2_spokes",shells,f"13 radial spokes (Fibonacci), 2 tiles per spoke: inner {dims['inner'][0]} x {dims['inner'][1]}, outer {dims['outer'][0]} x {dims['outer'][1]} x 2.5 mm MnZn; carrier ring r52.6-116.1, z29.4-33.4; min tile gap {GAP} mm")
for nm in dims:
    L,w=dims[nm]; emit(f"FERRITE_TILE_{nm.upper()}_v2_reference",[extrude(np.array([(-L/2,-w/2),(L/2,-w/2),(L/2,w/2),(-L/2,w/2)]),0.0,TT)],f"MnZn tile {L} x {w} x {TT}, 13 pieces")
# ---- audit numbers
tg=min(sat_gap(rect_pts(a[2],a[3],a[4],a[5]/2,a[6]/2),rect_pts(b[2],b[3],b[4],b[5]/2,b[6]/2)) for i,a in enumerate(tiles) for b in tiles[i+1:] if math.hypot(a[2]-b[2],a[3]-b[3])<75)
intr=min(sat_gap(rect_pts(a[2],a[3],a[4],a[5]/2+1.35,a[6]/2+1.35),rect_pts(b[2],b[3],b[4],b[5]/2+0.15,b[6]/2+0.15)) for i,a in enumerate(tiles) for b in tiles[i+1:] if math.hypot(a[2]-b[2],a[3]-b[3])<75)
cr=max(np.hypot(*p) for a in tiles for p in rect_pts(a[2],a[3],a[4],a[5]/2+1.35,a[6]/2+1.35)); ir=min(np.hypot(*p) for a in tiles for p in rect_pts(a[2],a[3],a[4],a[5]/2+1.35,a[6]/2+1.35))
area=sum(a[5]*a[6] for a in tiles); mass=area*TT*4.8e-3
rep["hood_v2_audit"]=dict(tiles=len(tiles),min_tile_gap=round(tg,2),frame_into_neighbour_pocket_gap=round(intr,2),outer_frame_corner_r=round(cr,2),inner_frame_r=round(ir,2),tile_area_mm2=round(area),mass_g=round(mass),dims=dims)
with open(f"{OUT}/hood_tile_cut_list.csv","w",newline="") as f:
    w_=csv.writer(f); w_.writerow(["id","segment","spoke","length_mm","width_mm","thick_mm","centre_r_mm","azimuth_deg"]); [w_.writerow([f"T{k+1:02d}",a[0],a[1]+1,a[5],a[6],TT,round(math.hypot(a[2],a[3]),2),round(math.degrees(a[4])%360,3)]) for k,a in enumerate(tiles)]
# ---- DXF cut sheet (mm): 26 rectangles in rows on a 300 x 220 sheet
def dxf_rect(lines,x,y,L,W,layer):
    for (x0,y0,x1,y1) in ((x,y,x+L,y),(x+L,y,x+L,y+W),(x+L,y+W,x,y+W),(x,y+W,x,y)): lines+=["0","LINE","8",layer,"10",f"{x0:.3f}","20",f"{y0:.3f}","30","0.0","11",f"{x1:.3f}","21",f"{y1:.3f}","31","0.0"]
ln=["0","SECTION","2","ENTITIES"]; y=5.0
for nm,col in (("inner",0),("outer",1)):
    L,w=dims[nm]; x=5.0
    for k in range(N):
        if x+L>300: x=5.0; y+=w+4
        dxf_rect(ln,x,y,L,w,"TILE_"+nm.upper()); x+=L+4
    y+=w+10
ln+=["0","ENDSEC","0","EOF"]; open(f"{OUT}/hood_tile_cut_sheet.dxf","w").write("\n".join(ln))
json.dump(rep,open(f"{OUT}/hood_report.json","w"),indent=1,default=float); print(rep["hood_v2_audit"])
