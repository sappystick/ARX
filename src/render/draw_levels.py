import math, csv, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle, Rectangle, Polygon, FancyBboxPatch, FancyArrowPatch
BG="#0b2a52"; FG="#e8f1ff"; ACC="#7fd4ff"; ORG="#ffb347"; GRN="#6fe3a0"; RED="#ff8a8a"; YEL="#f2c94c"
RIBS=[24.0,48.0,109.0,135.0,225.0,244.0,300.0,317.0]; RXDEG=[16.0,68.5,153.5,206.0,291.0,343.5]
lib=json.load(open("kit_v19/lib_bodies.json")); px=list(csv.DictReader(open("kit_v18/SET/02_CORE_PCB_CYLINDER/PIXEL_MAP_66.csv")))
fig,axs=plt.subplots(3,3,figsize=(24,27),facecolor=BG)
import textwrap
def base(ax,title,sub,R=60):
    ax.set_facecolor(BG); ax.set_aspect(1); ax.set_xlim(-R,R); ax.set_ylim(-R,R); ax.axis("off"); ax.set_title(title,color=FG,fontsize=15,loc="left"); ax.text(0.0,-0.02,"\n".join(textwrap.wrap(sub.replace("\n"," "),88)),color=FG,fontsize=10.5,va="top",transform=ax.transAxes)
def ring(ax,r0,r1,a0,a1,fc,ec=FG,al=1,lw=0.6): ax.add_patch(Wedge((0,0),r1,a0,a1,width=r1-r0,fc=fc,ec=ec,alpha=al,lw=lw))
def hub(ax): ring(ax,44,49.5,0,360,"#9aa3b8",al=0.9)
def ribs(ax,r0=37.2,col="#c9cfe3"):
    for a in RIBS: ring(ax,r0,44.5,a-math.degrees(3.0/40.8),a+math.degrees(3.0/40.8),col)
    for sg in (1,-1): ring(ax,37.2,44.5,90+sg*math.degrees(6.0/38.7) if sg>0 else 90-math.degrees(7.2/38.7),(90+math.degrees(7.2/38.7)) if sg>0 else 90-math.degrees(6.0/38.7),col)
def posts(ax):
    for a in RIBS: ax.add_patch(Circle((42.5*math.cos(math.radians(a)),42.5*math.sin(math.radians(a))),3.0,fc="#e3e6f2",ec=FG,lw=0.5)); ax.add_patch(Circle((42.5*math.cos(math.radians(a)),42.5*math.sin(math.radians(a))),2.0,fc=BG,ec=FG,lw=0.5))
def board(ax,r,fc="#14634a",notch=True,al=0.9):
    ax.add_patch(Circle((0,0),r,fc=fc,ec=FG,alpha=al,lw=1))
    if notch: ax.add_patch(Rectangle((-6,36.5),12,r-36.4,fc=BG,ec=FG,lw=0.8))
# ---- L0
ax=axs[0,0]; base(ax,"L0  z 0-3.2   base plate + SB1R-Q receive board","Two stacked 4-layer D228 boards in the D229 recess (L1 copper of each shown): QUAD-A (blue) and QUAD-B = the same copper rotated 45 deg (orange dashed), 24 turns per lobe, 16.9 m of copper each. Lead pads P1/P2 at (+-4, 33) under the floor slot; 3 M3 holes at r28 (22.5/157.5/247.5 deg); index key at 0 deg.",R=125)
ax.add_patch(Circle((0,0),116.5,fc="#6c7a99",ec=FG)); ax.add_patch(Circle((0,0),114,fc="#14634a",ec=FG,alpha=0.95)); ax.add_patch(Circle((0,0),49.5,fc="none",ec=ACC,ls="--"))
GS=json.load(open("kit_v22/sbq_geometry.json"))
for p in GS["layers"]["0"]: p=np.array(p); ax.plot(p[:,0],p[:,1],color="#7fd4ff",lw=0.7)
for p in GS["layersB"]["0"]: p=np.array(p); ax.plot(p[:,0],p[:,1],color=ORG,lw=0.7,ls="--")
for a in GS["hole_angles"]: ax.add_patch(Circle((GS["hole_radius"]*math.cos(math.radians(a)),GS["hole_radius"]*math.sin(math.radians(a))),1.7,fc=BG,ec=FG))
ax.add_patch(Rectangle((112,-2),4.4,4,fc=YEL,ec=FG))
for a in (16.0,153.5,291.0,343.5): ax.add_patch(Circle((48.3*math.cos(math.radians(a)),48.3*math.sin(math.radians(a))),2.0,fc="#fff3b0",ec=FG))
ax.text(0,0,"axis",color=FG,ha="center",fontsize=9)
# ---- L1
ax=axs[0,1]; base(ax,"L1  z 3.2-9.0   gallery under the floor","RX leads: 4 twisted pairs (AWG36) from the pads, through the bottom ports (z4.3-6.3), along the gallery to the 12 mm floor slot (r28-37 at 90 deg)\nand up. 3 M3 insert bosses at r28 (22.5/157.5/247.5 deg) hang under the floor, z3.2-9.6. Spine flex starts here.")
hub(ax)
for a in (22.5,157.5,247.5): ax.add_patch(Circle((28*math.cos(math.radians(a)),28*math.sin(math.radians(a))),3.4,fc="#c9cfe3",ec=FG))
for k,a in enumerate(RXDEG): ax.add_patch(Rectangle((47*math.cos(math.radians(a))-1,47*math.sin(math.radians(a))-1),2,2,fc=(GRN if a in (16.0,153.5,291.0,343.5) else "#555"),ec=FG,transform=ax.transData))
ring(ax,28,37,90-math.degrees(6/32.5),90+math.degrees(6/32.5),"none",ec=ORG,lw=1.5)
for a in (16.0,153.5,291.0,343.5): ax.plot([46*math.cos(math.radians(a)),0 if False else 33*math.cos(math.radians(90))+(a/360-0.5)*6],[46*math.sin(math.radians(a)),33],color=GRN,lw=0.8)
ax.text(0,43,"floor slot",color=ORG,ha="center",fontsize=9)
# ---- L2
ax=axs[0,2]; base(ax,"L2  z 9.8-20.0   analog cell","ANALOG_TRAY on the floor (notch over the slot). AB1T-A (left): QUAD-A, QUAD-B, spare, RS 100 ohm. AB1T-B (right): spare, MONO from CB1D.\nBoards 6.7 mm tall, 3 standoffs each, 0.3 mm shim between. Liner panels line the wall between the ribs' z-range.")
hub(ax); ring(ax,37.2,44.5,90-math.degrees(7.2/38.7),90-math.degrees(6/38.7),"#c9cfe3"); ring(ax,37.2,44.5,90+math.degrees(6/38.7),90+math.degrees(7.2/38.7),"#c9cfe3")
t=Circle((0,0),38.8,fc="#33adb5",ec=FG,alpha=0.35); ax.add_patch(t); ax.add_patch(Rectangle((-8,28),16,12,fc=BG,ec=FG))
for cx,nm,col in ((-20.3,"AB1T-A\nQUAD-A / QUAD-B\n/ spare","#14634a"),(20.3,"AB1T-B\nspare / MONO","#14634a")): ax.add_patch(Circle((cx,0),20,fc=col,ec=FG)); ax.text(cx,0,nm,color=FG,ha="center",va="center",fontsize=9)
ax.plot([-0.45,-0.45],[-34,34],color=ORG,lw=1.2); ax.plot([0.45,0.45],[-34,34],color=ORG,lw=1.2)
for a in range(0,360,45): ax.add_patch(Wedge((0,0),44.0,a+5,a+40,width=0.6,fc="#d0d6e6",ec="none"))
# ---- L3
ax=axs[1,0]; base(ax,"L3  z 20.0-21.9   septum","SEPTUM_FRAME ring r31-39 (edge in the rib slots), outer sectors to r43.6 between ribs, 16 mm notch at 90 deg for the flex.\nCopper cloth over the D62 window: E-field shield with 1.2 mm mesh, no eddy loops. One drain wire to the star ground.")
hub(ax); ribs(ax)
ring(ax,31,39,90+math.degrees(8/35),90-math.degrees(8/35)+360,"#b7bfd4",ec=ORG,al=0.9)
ax.add_patch(Circle((0,0),31,fc="#d8a060",ec=ORG,alpha=0.35,hatch="////"))
ax.text(0,0,"copper cloth\nD62 window",color=FG,ha="center",va="center",fontsize=10)
# ---- L4
ax=axs[1,1]; base(ax,"L4  z 21.9-27.0   absorber cell","Carbonyl-iron silicone absorber between the analog and digital cells (damps cavity ringing). 8 guide ribs, spine channel at 90 deg,\nTX-lead channel at 178 deg (no rib: the coil leads come down from the exit window to JCL).")
hub(ax); ribs(ax); ax.add_patch(Circle((0,0),37.0,fc="#555",ec=FG,alpha=0.4))
ax.annotate("TX leads (12 litz -> junction -> JCL)",xy=(-39,2),xytext=(-58,14),color=FG,fontsize=9,arrowprops=dict(arrowstyle="->",color=ORG))
ax.annotate("spine channel\n12 mm",xy=(0,39),xytext=(14,52),color=FG,fontsize=9,arrowprops=dict(arrowstyle="->",color=ORG))
# ---- L5
ax=axs[1,2]; base(ax,"L5  z 27.0-38.8   digital cell: CB1D controller","CB1D (64 parts) in the rib slot at z27.0, mounted rotated 180 deg so JCL faces the heel (178 deg). Parts up to 10.2 mm.\nNotch at 90 deg for the spine stub; planes hatched. Routed 45/46 nets so far.")
hub(ax); ribs(ax); posts(ax); board(ax,39.0,"#14634a")
bom={}
for r in list(csv.reader(open("kit_v18/CB1D/PF233-CB1D_BOM.csv")))[1:]:
    for ref in r[1].split(","): bom[ref.strip()]=r[2]
def colr(t):
    t=t.upper()
    if t.startswith("R"): return "#222"
    if t.startswith("C") and t not in("CAPD","CAN10"): return "#c89c5a"
    if t.startswith(("TERM","HDR","WIRE")): return "#f2ead0"
    if t=="PICO": return "#1a8a5a"
    if t=="OKI3": return "#2a4fb0"
    return "#111"
for r in csv.DictReader(open("kit_v18/CB1D/PF233-CB1D_pickplace.csv")):
    t=bom.get(r["Ref"]); 
    if t not in lib: continue
    w,h,_=lib[t]; rot=int(float(r["Rot"]))
    if rot%180==90: w,h=h,w
    x,y=-float(r["PosX_mm"]),-float(r["PosY_mm"]); ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc=colr(t),ec=FG,lw=0.3))
    if r["Ref"] in ("U1","M5","JCL","JPW","JPB","JTR","JA","JB","JHTA","JLB","UM"): ax.text(x,y,r["Ref"],color="#ff8a8a" if r["Ref"]=="JCL" else FG,fontsize=8,ha="center",va="center")
# ---- L6
ax=axs[2,0]; base(ax,"L6  z 39.2-40.8   display board LB1","LB1 rests on the rib inner tops (r37.2-39.5, z39.2); posts r42.5 stand clear. 66 SK6812-class LEDs under the roof holes; 66 light pipes D1.5 x 6.2.\nRouted 68/68 nets, hatched planes, notch at 90 deg (Gerbers in GERBER_LB1_v2).")
hub(ax)
for a in RIBS: ring(ax,37.2,39.5,a-math.degrees(3.0/40.8),a+math.degrees(3.0/40.8),"#c9cfe3")
posts(ax); board(ax,39.0,"#14634a",al=0.9)
rc={"1":"#a05af2","2":"#40d9f2","3":"#ffb833","4":"#59f266"}
for p in px: ax.add_patch(Rectangle((float(p["x_mm"])-1.6,float(p["y_mm"])-1.4),3.2,2.8,fc=rc[p["ring"]],ec=FG,lw=0.3)); ax.add_patch(Circle((float(p["x_mm"]),float(p["y_mm"])),0.75,fc="#fff3b0",ec="none"))
ax.text(0,-48,"depth rings: violet r12.5 (deep), cyan r20, amber r26.5 (shallow); green r34 = noise ring",color=FG,fontsize=9,ha="center")
# ---- L7
ax=axs[2,1]; base(ax,"L7  z 41.3-44.5   removable roof plate","Roof bolts on with 8 nylon M3 into the rib posts (slots 6.0 x 3.4, counterbores 6.0 x 6.2). 0.5 mm silicone gasket on the tube top and collar.\nPixel holes D1.7 (66), 4 vent windows (cap hooks pass through), D20 centre port.")
ax.add_patch(Circle((0,0),52,fc="#9aa3b8",ec=FG)); ax.add_patch(Circle((0,0),10,fc=BG,ec=FG))
for r_,k,ph in ((12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,7.5)):
    for i in range(k): a=math.radians(ph+i*360/k); ax.add_patch(Circle((r_*math.cos(a),r_*math.sin(a)),0.85,fc=BG,ec=FG,lw=0.4))
for a in (45,135,225,315): ax.add_patch(Rectangle((30*math.cos(math.radians(a))-2,30*math.sin(math.radians(a))-2),4,4,fc=BG,ec=ORG))
for a in RIBS: x,y=42.5*math.cos(math.radians(a)),42.5*math.sin(math.radians(a)); ax.add_patch(Rectangle((x-3,y-3),6,6,fc="#d0d6e6",ec=ORG,lw=0.8)); ax.add_patch(Circle((x,y),1.7,fc=BG,ec=FG,lw=0.5))
ax.add_patch(Wedge((0,0),49.2,0,360,width=3.6,fc="none",ec=GRN,ls="--"))
# ---- L8
ax=axs[2,2]; base(ax,"L8  z 44.5-47.1   cap + hub-top antenna","Cap D104 with 4 snap hooks through the roof vents, 6 deg strap gap at 0 deg. HTA 4-layer D90 board: 2 x 1.915 turns r35.5-43,\nabout 2.8 uH, pads A/B near the centre port; 66 pixel holes for the light pipes.")
ax.add_patch(Circle((0,0),52,fc="#e0e0ec",ec=FG)); ax.add_patch(Circle((0,0),45,fc="#14634a",ec=FG)); ax.add_patch(Circle((0,0),4,fc=BG,ec=FG))
NT=1.915; th=np.linspace(0,NT*2*math.pi,300); r=43.0+(35.5-43.0)*th/(NT*2*math.pi); ax.plot(r*np.cos(th),r*np.sin(th),color=YEL,lw=1.6); r2=35.5+(43.0-35.5)*(th)/(NT*2*math.pi); ax.plot(r2*np.cos(th+th[-1]),r2*np.sin(th+th[-1]),color=ORG,lw=1.6)
for r_,k,ph in ((12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,7.5)):
    for i in range(k): a=math.radians(ph+i*360/k); ax.add_patch(Circle((r_*math.cos(a),r_*math.sin(a)),0.85,fc=BG,ec=FG,lw=0.4))
ax.add_patch(Circle((6,0.9),0.8,fc="#fff",ec=FG)); ax.add_patch(Circle((6,-0.9),0.8,fc="#fff",ec=FG)); ax.text(7,3,"pads A / B",color=FG,fontsize=8)
for a in (45,135,225,315): ax.add_patch(Rectangle((30.5*math.cos(math.radians(a))-1.7,30.5*math.sin(math.radians(a))-1.7),3.4,3.4,fc=ORG,ec=FG))
ax.add_patch(Wedge((0,0),52,-3,3,width=7,fc=BG,ec=RED))
fig.suptitle("PHI-FOLD 233 vault v5: level-by-level plan views (looking down, hub frame, mm)",color=FG,fontsize=22,x=0.01,ha="left")
fig.subplots_adjust(left=0.01,right=0.99,top=0.945,bottom=0.035,wspace=0.03,hspace=0.17); plt.savefig("kit_v22/LEVELS_PLAN_VIEWS.png",dpi=60,facecolor=BG); print("ok")
