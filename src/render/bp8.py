import math, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, textwrap
from matplotlib.patches import Rectangle
BG="#0b2a52"; FG="#e8f1ff"; ACC="#7fd4ff"; ORG="#ffb347"; YEL="#f2c94c"
fig=plt.figure(figsize=(19,11),facecolor=BG)
ax=fig.add_subplot(121,facecolor=BG); ax.set_xlim(-62,62); ax.set_ylim(-2,52); ax.set_aspect(1.0); ax.axis("off")
def box(x0,x1,z0,z1,fc,ec=FG,lw=0.6,alpha=1): ax.add_patch(Rectangle((x0,z0),x1-x0,z1-z0,fc=fc,ec=ec,lw=lw,alpha=alpha))
box(-116,116,0,0.8,"#6c7a99"); box(-114,114,0.8,3.2,"#14634a")
for s in (-1,1):
    a,b=(44,49.5) if s>0 else (-49.5,-44); box(a,b,3.2,41.3,"#9aa3b8")
    for z in (9,17,25): box(41.5 if s>0 else -44,44 if s>0 else -41.5,z-1.2,z,"#7d869c")
box(41.5,44,31.8,33.0,"#7d869c"); box(-44,-41.5,31.8,33.0,"#7d869c",ec="#ff7f7f")
box(-52,52,41.3,44.5,"#9aa3b8"); box(-52,52,44.5,45.4,"#e0e0ec"); box(-45,45,45.4,47,"#14634a")
def cup(z0,H,fc,fill,lab):
    for s in (-1,1): box(s*40.7 if s>0 else -41.3,41.3 if s>0 else -40.7,z0+0.8,z0+H,"#d9d9e8")
    box(-43.8,43.8,z0,z0+0.8,"#d9d9e8"); box(-40.7,40.7,z0+0.8,z0+H-0.0,fill,ec="none",alpha=0.45); ax.text(0,z0+H-0.9,lab,color=FG,fontsize=7.4,ha="center",va="top")
cup(9.0,6.8,"","#33adb5","CUP A  analog: AB1A + AB1B side by side, foil shim between"); box(-40.3,-0.3,11.1,12.7,"#2aa198"); box(0.3,40.3,11.1,12.7,"#2aa198")
cup(17.0,6.8,"","#555555","CUP B  isolation: carbonyl-iron silicone absorber")
cup(25.0,15.2,"","#c26fdb","CUP CD  control + display (syntactic silicone)")
box(-39,39,27.0,28.6,"#f59e6b"); ax.text(0,33,"CB1D controller (63 parts, parts up to 10.2 mm: room 10.6)",color=FG,fontsize=7.4,ha="center")
box(-39,39,39.2,40.0,"#ffb347"); ax.text(0,38.4,"LB1 66 RGB LEDs",color=FG,fontsize=7,ha="center")
for r in (12.5,20,26.5,34):
    for s in (-1,1): box(s*r-0.75,s*r+0.75,40.7,47,"#fff3b0",ec="none")
for s in (-1,1): box(s*47,s*47+0.01,4.3,6.3,"#ff7f7f")
ax.annotate("6 low RX entry ports\n(z4.3-6.3) right above\nthe receive board",xy=(46.5,5.3),xytext=(52,12),color=FG,fontsize=7.5,arrowprops=dict(arrowstyle="->",color=FG))
ax.annotate("TX lead corridor: ledge 4 notched\nat 0 deg, wall slot z27-30",xy=(42,31),xytext=(-60,45),color=FG,fontsize=7.5,arrowprops=dict(arrowstyle="->",color=FG))
ax.annotate("lead raceway annulus r41.5-44",xy=(42.5,38),xytext=(30,49),color=FG,fontsize=7.5,arrowprops=dict(arrowstyle="->",color=FG))
ax.set_title("Vault section (x-z), mm: three cups on the hub ledges, every cup closed by the floor of the next",color=FG,fontsize=10)
ax2=fig.add_subplot(122,facecolor=BG); ax2.axis("off")
rows=[("VAULT COMPARTMENTS (built: 3 cups + hub v3 + skirt)",""),
("A  analog z9-17","AB1A + AB1B (D40, 6.7 mm tall incl. bottom parts; 1.3 mm standoffs leave 0.3 mm to the lid). Lined with foil or 0.12 mm nanocrystalline ribbon. Fill: syntactic silicone (low capacitance, 2.6). The 5 receive leads enter at the BOTTOM ports and go up the 180 deg floor slot."),
("B  isolation z17-25","Empty cup, absorber fill (carbonyl-iron silicone) between analog and digital: damps cavity ringing; ribbons pass through. Optional home for an AB1C tip board."),
("CD control + display z25-40","CB1D on 3 tabs at z27 (room 10.6 mm), LB1 on 3 tabs at z39.2, LEDs 0.9 mm under the roof. TX leads arrive in the raceway annulus, drop through the ledge-4 notch and the 8 mm wall slot to JCL at 0 deg. Fill: syntactic silicone, clear silicone over the LEDs."),
("Skirt (built)","D238 ring, 0.5 mm gap to the stack, 8 fill/vent windows: silicone fills the gap and the 0.8 mm layer gaps."),
("",""),
("WHAT THE FIELD DOES INSIDE (calculated, Biot-Savart)","the transmit field is almost the same at every height: 106-141 uT/A, so about 2.3 mT at 20 A. Unshielded, a 1 cm2 loop picks up 100-130 mV at turn-off at ANY slot: the position cannot hide it. So: liners (0.12 mm ribbon about 17 dB, 0.25 mm about 23-29 dB, from the earlier shield study), loops under 1 cm2, BLANK during turn-off."),
("",""),
("BOARD MAP (earlier files mapped onto the vault)","AB1A inputs: GX, GY, X8 -> relabel V8, QUAD, X8.  AB1B: Y8, MONO -> W8, MONO.  So the existing 5-channel pair covers X8/W8/V8/QUAD/MONO after relabelling (the earlier notes called them X8/W8/V8 directly; the files say GX, GY, X8, Y8). Tip pair GX/GY needs an AB1C (copy of AB1B). HTA reads through the CB1D mux channel Y4 (new). PB1R, PM1 stay in the neck and shaft (TX driver and power)."),
("NOT FIXED YET","CB1D and LB1 are placed, NOT routed. The old CB1 (70 x 70) does not fit the round cell; its parts moved to the D78 disc. AB1A input resistor still 47 ohm (needs about 1 kohm). Pico 2 W radio is useless inside a shielded cell: use it only as an RP2350. No thermal or EMC test.")]
y=0.985
for h,t in rows:
    if h and not t: ax2.text(0,y,h,color=ORG,fontsize=10,weight="bold",va="top",transform=ax2.transAxes); y-=0.04; continue
    if not h: y-=0.01; continue
    ax2.text(0,y,h,color=YEL,fontsize=8.8,weight="bold",va="top",transform=ax2.transAxes); y-=0.026
    w="\n".join(textwrap.wrap(t,92)); ax2.text(0,y,w,color=FG,fontsize=7.9,va="top",transform=ax2.transAxes); y-=0.0205*(w.count("\n")+1)+0.014
fig.suptitle("PHI-FOLD 233 - blueprint 8: search-head compartments, isolation cups and board map",color=FG,fontsize=14,x=0.01,ha="left"); fig.subplots_adjust(wspace=0.05)
plt.savefig("kit_v18/BLUEPRINT_8_VAULT_COMPARTMENTS.png",dpi=88,facecolor=BG,bbox_inches="tight"); print("ok")
