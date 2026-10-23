import math, json, numpy as np
import rodin_core_v4 as rc, golden_cone_head as g
from render_v6 import tri2d
OUT="kit_v19/PARTS"; GOLD=137.50776405; rep={}
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

def pieces_ring(r0,r1,z0,z1,gaps=None):
    """annulus r0..r1 (r0>0) with optional angular gaps [(a0,a1) rad]"""
    if not gaps: return [ring(circ(r1,720),circ(r0,720),z0,z1)]
    g=sorted(gaps); out=[]
    for i in range(len(g)):
        a0=g[i][1]; a1=g[(i+1)%len(g)][0]+(2*np.pi if i==len(g)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
def disc(r,z0,z1): return [extrude(circ(r,720),z0,z1)]
def cup(z0,H,name,note,slots_floor,wall_gap=None,tabs=(),pockets=False):
    """flange/floor disc r43.8 (z0..z0+0.8), wall r40.7-41.3 up to z0+H, optional floor slots, wall slot, board-support tabs"""
    sh=[]; zf=z0+0.8
    ribbon=[(math.radians(a)-4.0/36.0,math.radians(a)+4.0/36.0) for a in slots_floor]                     # 8 mm wide slots at r33-39
    sh+=disc(33.0,z0,zf); sh+=pieces_ring(33.0,39.0,z0,zf,ribbon); sh+=pieces_ring(39.0,43.8,z0,zf)
    if wall_gap:
        a,zl,zh,w=wall_gap; g=[(math.radians(a)-w/2/41.0,math.radians(a)+w/2/41.0)]
        sh+=pieces_ring(40.7,41.3,zf,zl); sh+=pieces_ring(40.7,41.3,zl,zh,g); sh+=pieces_ring(40.7,41.3,zh,z0+H)
    else: sh+=pieces_ring(40.7,41.3,zf,z0+H)
    for (az,zt,zb) in tabs: sh.append(sector(37.5,40.8,math.radians(az-9),math.radians(az+9),zb,zt))
    if pockets:
        for sx in (-20.3,20.3):
            for k in range(3):
                a=math.radians(90+120*k); sh.append(extrude(circ(1.5,24)+[sx+17.0*math.cos(a),17.0*math.sin(a)],zf,zf+1.3))
        for x in (-0.45,0.45): sh.append(extrude(np.array([(x-0.25,-38),(x+0.25,-38),(x+0.25,38),(x-0.25,38)]),zf,zf+1.6))
    emit(name,sh,note); return sh
cup(9.0,6.6,"VAULT_CUP_A_ANALOG","analog cell: two D40 boards (AB1A, AB1B) centred at x=+/-20.3, a 0.6 mm gap held by a pair of 0.5 ribs for a 0.3 mm foil/graphite shim, 3 standoff pads per board; floor slots at 180 deg (ribbon) and 0 deg (power)",[180,0],pockets=True)
cup(17.0,6.6,"VAULT_CUP_B_ISOLATION","isolation cell: empty cup filled with absorber (carbonyl-iron silicone); ribbon/power pass through the 2 floor slots; optional home for an AB1C tip board",[180,0])
cup(25.0,15.2,"VAULT_CUP_CD_CONTROL_DISPLAY","tall control cell: CB1D (D78) on 3 wall tabs at z27.0 (parts up to 10 mm), LB1 display board (D78) on 3 wall tabs at z39.2; TX-lead wall slot 10 wide x 3 tall at z27-30, 178 deg; floor slots at 180 and 0 deg",[180,0],wall_gap=(178.0,27.0,30.0,10.0),tabs=[(30,27.0,25.8),(150,27.0,25.8),(270,27.0,25.8),(60,39.2,38.2),(180,39.2,38.2),(300,39.2,38.2)])
# ---- waterproof head skirt: ring r117-119, z0-33.4, 8 vertical fill slits 3 wide (z3.4-29.0) so silicone reaches every 0.8 mm layer gap and the 0.5 mm annulus
fw=[(math.radians(22.5+45*i)-1.5/118.0,math.radians(22.5+45*i)+1.5/118.0) for i in range(8)]
sk=pieces_ring(117.0,119.0,0.0,3.4)+pieces_ring(117.0,119.0,3.4,29.0,fw)+pieces_ring(117.0,119.0,29.0,33.4)
emit("HEAD_SKIRT",sk,"waterproof skirt D238 x 33.4: 0.5 mm gap to the petal tips and base rim, 8 vertical fill/vent slits 3 wide at 22.5+45k deg, z3.4-29.0 (reach every layer gap); closed by the 3.4 mm base band and the 4.4 mm top band")
json.dump(rep,open(f"{OUT}/report.json","w"),indent=1); print({k:(v['nonmanifold_edges'],v['tris'],v['bbox']) for k,v in rep.items()})
