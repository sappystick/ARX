import math, json, os, numpy as np
s=open('cap_hood_v16.py').read(); head=s[:s.index("# ---------------- 1. HUB CAP")].replace('OUT="kit_v16/PARTS"','OUT="kit_v19/YOKE"'); os.makedirs("kit_v19/YOKE",exist_ok=True); exec(head)
def circc(r,m,cx=0.0,cy=0.0):
    t=np.linspace(0,2*np.pi,m,endpoint=False); return np.c_[cx+r*np.cos(t),cy+r*np.sin(t)]
def box(x0,x1,y0,y1,z0,z1): return extrude(np.array([(x0,y0),(x1,y0),(x1,y1),(x0,y1)]),z0,z1)
def along_y(S,y0=0.0):                       # local (u,v,w) -> (x=u, y=w, z=v): a profile in the x-z plane extruded along y
    V=S[0][:,[0,2,1]]+np.array([0,y0,0]); F=S[1]; return (V,F if rc.signed_volume(V,F)>0 else F[:,::-1])
def rotz(S,deg):
    c,s_=math.cos(math.radians(deg)),math.sin(math.radians(deg)); R=np.array([[c,-s_,0],[s_,c,0],[0,0,1]]); V=S[0]@R.T; return (V,S[1])
def pring(r0,r1,z0,z1,gaps=None):
    if not gaps: return [ring(circ(r1,360),circ(r0,360),z0,z1)]
    g=sorted(gaps); out=[]
    for i in range(len(g)):
        a0=g[i][1]; a1=g[(i+1)%len(g)][0]+(2*np.pi if i==len(g)-1 else 0.0); out.append(sector(r0,r1,a0,a1,z0,z1))
    return out
HEEL=178.0; XH,ZH=159.0,76.0; assembly=lambda L:[rotz(S,HEEL) for S in L]            # heel frame: x' outward from the head centre, y' tangential
# ---------------- saddle + tower (heel frame) ----------------
sad=[sector(119.4,123.0,-math.radians(22),math.radians(22),0.0,33.4)]
tw=[box(121,182,-26,26,0,4)]                                                           # floor
tw+=[box(178,182,-26,26,4,56)]+[box(121,182,sy*22,sy*26 if sy>0 else sy*22,4,76) if False else box(121,178,(22 if sy>0 else -26),(26 if sy>0 else -22),4,76) for sy in (1,-1)]
tw+=[box(121,125,-22,22,4,34.4),box(121,125,-22,22,41.2,56),box(121,125,7.0,22,34.4,41.2),box(121,125,-22,-7.0,34.4,41.2)]   # front wall with the 14 wide window z34.4-41.2
for sy in (1,-1):                                                                       # hinge lugs: D36 plates 6 thick at y = +/-17..23, bore D10.2
    y0=17.0 if sy>0 else -23.0
    tw.append(along_y(ring(circc(18.0,96,XH,ZH),circc(5.1,96,XH,ZH),y0,y0+6.0)))
    tw.append(box(XH-18,XH+18,y0,y0+6.0,60.0,76.0))
    for k in range(36):                                                                 # serrations on the lug faces facing the arm: 36 ribs, 10 deg pitch, offset 5 deg
        a=math.radians(5+10*k); yf=17.0 if sy>0 else -17.0; ys=(16.1,17.0) if sy>0 else (-17.0,-16.1)
        poly=np.array([(XH+r*math.cos(a)+w*(-math.sin(a)),ZH+r*math.sin(a)+w*math.cos(a)) for r,w in ((10.5,-0.3),(15.5,-0.3),(15.5,0.3),(10.5,0.3))]); tw.append(along_y(extrude(poly,ys[0],ys[1])))
emit("HEEL_SADDLE_TOWER",assembly(sad+tw),f"saddle r119.4-123.0 (+/-22 deg, 0.4 mm epoxy gap to the skirt) + hollow tower 61 x 52 x 76 with a 14 x 6.8 window towards the head (z34.4-41.2); front and back walls stop at z56 so the tube and socket clear them in every position, hinge lugs D36 with D10.2 bore and 36 serrations (10 deg), hinge axis at x'={XH}, z={ZH}; heel azimuth {HEEL} deg")
# ---------------- umbilical bridge and lid (heel frame): from the hub exit window to the tower window ----------------
br=[box(52.2,125,-8.2,8.2,33.7,34.4)]+[box(52.2,125,sy*7.0 if sy>0 else -8.2,8.2 if sy>0 else -7.0,34.4,40.8) for sy in (1,-1)]
emit("UMBILICAL_BRIDGE",assembly(br),"U channel 14 wide x 6.4 tall (z34.4-40.8), floor z33.7 (0.3 mm over the hood frames and skirt), from r52.2 (hub collar) to the tower window; carries the power ribbon, signal ribbon, 8-way umbilical and the TX pair")
emit("UMBILICAL_BRIDGE_LID",assembly([box(52.2,125,-8.2,8.2,40.8,42.0)]),"lid, 1.2 mm, bond with silicone after the cables are dressed")
# ---------------- hinge arm (local frame: hinge centre at the origin, socket along +z) ----------------
arm=[along_y(ring(circ(16.0,96),circ(5.1,96),-16.0,16.0))]
arm+=[box(-16,16,sy*14.0 if sy>0 else -16.0,16.0 if sy>0 else -14.0,0,30) for sy in (1,-1)]
arm+=[ring(circ(19.8,96),circ(16.2,96),14.0,64.0)]
for sy in (1,-1):
    ys=(16.0,16.9) if sy>0 else (-16.9,-16.0)
    for k in range(36):
        a=math.radians(10*k); poly=np.array([(r*math.cos(a)+w*(-math.sin(a)),r*math.sin(a)+w*math.cos(a)) for r,w in ((10.5,-0.3),(15.5,-0.3),(15.5,0.3),(10.5,0.3))]); arm.append(along_y(extrude(poly,ys[0],ys[1])))
emit("HINGE_ARM",arm,"hub D32 x 32 (bore D10.2) between the lugs, 2 mm webs at y=+/-14..16 (ribbons run between them), socket ID 32.4 for the lower fixed tube (OD 32) from z14 to z64, 36 serrations 10 deg; pin = nylon M10, clamp = nylon thumb nut")
# ---------------- telescoping joint hardware (local frames) ----------------
emit("BUSHING_ON_TUBE_B",[ring(circ(14.8,120),circ(14.25,120),0,20.0)],"sleeve OD29.6 / ID28.5, 20 long, bond on the end of tube B (OD 28.5); slides in tube A (ID 30.0) with 0.2 mm clearance; PA12 or PETG")
emit("BUSHING_IN_TUBE_A",[ring(circ(15.0,120),circ(14.45,120),0,20.0),ring(circ(15.8,120),circ(14.45,120),20.0,21.2)],"sleeve OD30.0 (press / bond in the mouth of tube A, ID 30.0), ID28.9 so tube B (OD 28.5) slides with 0.2 mm clearance, 1.2 mm lip")
gap=[(-0.5/19.0,0.5/19.0)]
col=pring(16.6,22.5,0,30.0,gap)+[box(19.0,30.0,0.5,6.5,0,30.0),box(19.0,30.0,-6.5,-0.5,0,30.0)]
emit("TELESCOPE_LOCK_COLLAR",col,"split clamp ring ID 33.2 (fits tube A, OD 33), OD 45, 30 long, 1.0 slit, two ears 11 x 6 with an M4 cross hole (drill 4.2); cut 4 slits 1.5 x 40 in the end of tube A, then the collar squeezes A onto B through the bushing; nylon M4 x 30 + nut")
json.dump(rep,open("kit_v19/YOKE/yoke_report.json","w"),indent=1,default=float); print({k:(v['nonmanifold_edges'],v['tris']) for k,v in rep.items()})
