import math, numpy as np, colorsys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge
BG="#0b2a52"; FG="#e8f1ff"; ACC="#7fd4ff"; ORG="#ffb347"; YEL="#f2c94c"; RED="#ff7f7f"
PX=[(12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,7.5)]
# ================= BLUEPRINT 6: display map + vault section
fig=plt.figure(figsize=(19,10.2),facecolor=BG)
ax=fig.add_subplot(131,facecolor=BG); ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-44,44); ax.set_ylim(-52,44)
ax.add_patch(Circle((0,0),43,fc="none",ec=FG,lw=1.2)); ax.add_patch(Circle((0,0),4,fc=BG,ec=FG))
targets=[(40,2,YEL,1.0),(205,3,"#ff6bd6",0.8),(300,1,"#7dff9a",0.6)]   # azimuth, ring, colour, brightness
def lit(ri,a,c): 
    for (ta,tr,col,br) in targets:
        if tr==ri and abs(((a-ta)+180)%360-180)<=360/PX[ri-1][1]/2*1.6: return col,br*(1-0.5*abs(((a-ta)+180)%360-180)/(360/PX[ri-1][1]))
    return None
for ri,(r,c,ph) in enumerate(PX,1):
    ax.add_patch(Circle((0,0),r,fc="none",ec=ACC,lw=0.4,ls=":"))
    for i in range(c):
        a=(ph+i*360/c)%360; x,y=r*math.cos(math.radians(a)),r*math.sin(math.radians(a))
        if ri==4: col=[(0.2,1,0.3),(0.2,1,0.3),(1,0.85,0.2),(1,0.3,0.2)][min(3,i//3)] ; ax.add_patch(Circle((x,y),1.5,fc=col,ec=FG,lw=0.5,alpha=0.9)); continue
        l=lit(ri,a,None)
        if l: ax.add_patch(Circle((x,y),1.9,fc=l[0],ec=FG,lw=0.6,alpha=max(0.35,l[1])))
        else: ax.add_patch(Circle((x,y),1.2,fc="#22406e",ec=ACC,lw=0.4))
ax.text(0,40,"N (bearing 0 deg = head axis X8)",color=FG,fontsize=8,ha="center")
ax.set_title("Polar detection map on the hub cap (66 light pipes, example frame)",color=FG,fontsize=11)
ax.text(0,-47,"azimuth = bearing of the target (3-axis figure-8 vector)\nring = depth class: outer r26.5 shallow (24 pixels, finest bearing), r20 middle (18),\ninner r12.5 deep (12); r34 = noise ring (12): green quiet, amber busy, red EMI\ncolour = target class from the decay-time filter bank; brightness = strength;\nup to 4 targets are held at once, each with its own colour",color=FG,fontsize=8,ha="center",va="center")
ax=fig.add_subplot(132,facecolor=BG); ax.set_xlim(-60,60); ax.set_ylim(-4,66); ax.set_aspect(1.0); ax.axis("off")
def box(x0,x1,z0,z1,fc,ec=FG,lw=0.7,alpha=1): ax.add_patch(Rectangle((x0,z0),x1-x0,z1-z0,fc=fc,ec=ec,lw=lw,alpha=alpha))
box(-116,116,0,0.8,"#6c7a99"); box(-114,114,0.8,3.2,"#14634a")
for s in (-1,1):
    x0,x1=(44,49.5) if s>0 else (-49.5,-44); box(x0,x1,3.2,41.3,"#9aa3b8"); box(min(49.5*s,52*s),max(49.5*s,52*s),29.2,41.3,"#7d869c")
    for z in (9,17,25,33): box(41.5 if s>0 else -44,44 if s>0 else -41.5,z-1.2,z,"#9aa3b8")
box(-52,52,41.3,44.5,"#9aa3b8"); box(-52,52,44.5,45.4,"#e0e0ec"); box(-45,45,45.4,47.0,"#14634a"); box(-52,-45.2,45.4,47.1,"#e0e0ec"); box(45.2,52,45.4,47.1,"#e0e0ec")
for z,lab,c in ((9,"DB1 analog front end: 8 channels + HTA","#33adb5"),(17,"DB2 compute + timing (RP2350, PIO capture)","#5599e0"),(25,"DB3 TX driver / clamp / sequencer (hot)","#c26fdb"),(33,"DB4 power rails, supercaps, isolation","#f59e6b")):
    box(-41.5,41.5,z,z+1.6,c,alpha=0.85); ax.text(0,z+0.8,lab,color="k",fontsize=7.5,ha="center",va="center")
box(-41.5,41.5,36.3,37.3,"#ffb347"); ax.text(0,36.8,"LB1 display board: 66 RGB LEDs under the pixel holes",color="k",fontsize=7.3,ha="center",va="center")
for r,_,_ in PX:
    for s in (-1,1): box(s*r-0.75,s*r+0.75,37.9,47.0,"#fff3b0",lw=0.3,alpha=0.9)
for s in (-1,1):
    box(s*39-2,s*39+2,37.3,41.3,"#9aa3b8")
ax.text(0,64,"Section through the head (x-z): vault, display and receive board",color=FG,fontsize=10,ha="center")
ax.annotate("light pipes D1.5 x 9.2 mm (acrylic,\nblack heat-shrink sleeve) through roof,\ncap floor and the HTA board",xy=(26.5,43),xytext=(-58,53),color=FG,fontsize=7.5,arrowprops=dict(arrowstyle="->",color=FG))
ax.annotate("SB1R receive board (8-layer, D228)",xy=(0,2),xytext=(-55,-3),color=FG,fontsize=8,arrowprops=dict(arrowstyle="->",color=FG))
ax.annotate("HTA board D90 (pixel holes + 4 turns r35.5-43)",xy=(40,46),xytext=(6,58),color=FG,fontsize=7.5,arrowprops=dict(arrowstyle="->",color=FG))
ax=fig.add_subplot(133,facecolor=BG); ax.axis("off")
txt=["VAULT STACK AND SIGNAL CHAIN","",
"z=9   DB1 analog: SB1R pads -> 8 low-noise channels\n       (X8, W8, V8, QUAD, MONO, tip GX, GY) + HTA,\n       simultaneous-sampling 16-bit ADCs, input damping",
"z=17  DB2 compute: dual-core MCU, PIO sample capture,\n       decay filter bank, bearing/depth, display frames",
"z=25  DB3 TX: driver, 500 V clamp, damping, pulse\n       sequencer (hot: about 4 W at 20 A / 400 Hz)",
"z=33  DB4 power: isolated rails, supercaps, filters\n       (parts under LB1 must be under 1.5 mm tall)",
"z=36.3 LB1 display: LEDs under 66 holes, 3 posts",
"","SYNC: the TX gate pulse starts a hardware timer, so every\nreceive gate is locked to the turn-off edge (no software\njitter). The HTA samples the same edge as the monitor.",
"","SHIELD: closed slit nanocrystalline wrap round the tube; the\n66 pixel holes (D1.7) and the 18 lead ports are its only\nopenings. No continuous copper loop anywhere in the head."]
y=0.98
for t in txt:
    ax.text(0.0,y,t,color=ORG if t.isupper() else FG,fontsize=8.6 if not t.isupper() else 10,va="top",transform=ax.transAxes,weight="bold" if t.isupper() else "normal"); y-=0.03*(t.count("\n")+1)+0.012
fig.suptitle("PHI-FOLD 233 - blueprint 6: display map and vault stack (dimensions in mm)",color=FG,fontsize=14,x=0.01,ha="left"); fig.subplots_adjust(wspace=0.12)
plt.savefig("kit_v17/BLUEPRINT_6_DISPLAY_AND_VAULT.png",dpi=90,facecolor=BG,bbox_inches="tight"); plt.close()
# ================= BLUEPRINT 7: timing, bearing maths, power and alignment
fig=plt.figure(figsize=(19,10.2),facecolor=BG); GOLD=(1+5**.5)/2
ax=fig.add_subplot(2,2,1,facecolor="#10335f"); t=np.linspace(-45,200,2000); I=np.where(t<-0,20*(t+41.5)/41.5,0); I=np.where(t<-41.5,0,I)
ax.plot(t,I,color=YEL,lw=2); ax.set_xlim(-45,200); ax.set_ylim(-2,24)
taus=[6*GOLD**n for n in range(8)]
for n,tc in enumerate(taus): ax.add_patch(Rectangle((tc*0.78,-1.5),tc*0.44,3.2,fc=plt.cm.cool(n/8),ec=FG,lw=0.4,alpha=0.9))
ax.text(100,13,"decay-signature filter bank:\n8 gates at 6 x 1.618^n us\n= 6, 9.7, 15.7, 25.4, 41, 66, 108, 174",color=FG,fontsize=9)
ax.text(-44,21,"20 A ramp (41.5 us at 26 V, L = 54 uH), turn-off 2.2 us at 500 V",color=FG,fontsize=8); ax.text(2,5,"blank\n4 us",color=ORG,fontsize=8)
ax.set_xlabel("time from turn-off (us)",color=FG); ax.set_ylabel("coil current (A)",color=FG); ax.tick_params(colors=FG)
ax.set_title("One pulse: all six layers in parallel; all 8 channels sample at once",color=FG,fontsize=10)
ax=fig.add_subplot(2,2,2,facecolor=BG); ax.axis("off")
t2=["BEARING AND NOISE FROM THE THREE FIGURE-8 AXES (X8 0 deg, W8 60 deg, V8 120 deg)","",
"each channel: g(theta) = Gx cos(theta) + Gy sin(theta)",
"Gx = g0 ,  Gy = (2 g60 - g0) / sqrt(3)",
"bearing = atan2(Gy, Gx), side fixed by the sign of the MONO channel",
"consistency residual  e = g120 - (g60 - g0)",
"   a real target gives e near 0; interference does not, so e drives the NOISE ring",
"depth class: from MONO amplitude and |G| / |MONO| (needs a calibration table; not measured yet)",
"",
"ALIGNMENT BUDGET (already built in, audited on the meshes)",
"tooth 3.6 in track 4.0: play +/-0.2 mm = +/-0.23 deg, 0.47 mm at the rim",
"the ripple phase error that causes is 2.8 deg of 360: negligible for the field",
"layer phase step = 137.508 deg, the same for every layer (17.508 mod 30 for the petals)",
"layer pitch 4.4 fixed by the pin shoulders: measured gap 0.81 mm mean",
"worst stack eccentricity 0.65 mm: X8 null leak about 0.8%; trimmed out in calibration"]
for i,l in enumerate(t2): ax.text(0,0.99-i*0.062,l,color=ORG if l.isupper() else FG,fontsize=8.6 if not l.isupper() else 9.5,va="top",transform=ax.transAxes,weight="bold" if l.isupper() else "normal")
ax=fig.add_subplot(2,2,3,facecolor=BG); ax.axis("off")
rows=[("mode","ramp us","clamp W","total W","hours*"),("scan 8 A / 800 Hz","16.6","1.38","4.7","19.4"),("mid 14 A / 600 Hz","29.1","3.18","6.5","14.0"),("boost 20 A / 400 Hz","41.5","4.32","7.7","11.8"),("boost 20 A / 800 Hz","41.5","8.64","12.1","7.5")]
for i,r in enumerate(rows):
    for j,c in enumerate(r): ax.text([0.0,0.40,0.55,0.70,0.85][j],0.88-i*0.13,c,color=ORG if i==0 else (YEL if i==3 else FG),fontsize=9.5,transform=ax.transAxes,weight="bold" if i==0 else "normal")
ax.text(0,1.0,"ALWAYS-ON BOOST (six layers in parallel, L = 54 uH, 90.7 Wh pack)",color=ORG,fontsize=10,weight="bold",transform=ax.transAxes,va="top")
ax.text(0,0.18,"* other loads taken as 3.3 W from the earlier power budget (not re-measured).\nBest compromise: 20 A at 400 Hz, about 11.8 h per pack; coil copper loss only 0.1 W.",color=FG,fontsize=8.6,transform=ax.transAxes,va="top")
ax=fig.add_subplot(2,2,4,facecolor=BG); ax.axis("off")
rows=[("litz OD mm","Cu mm2","R six layers","layer needs","stack"),("1.2 (built)","0.57","45 mOhm","3.6 mm","29.6 mm"),("1.5","0.88","29 mOhm","4.2 mm","33.2 mm"),("1.8","1.27","20 mOhm","4.8 mm","36.8 mm")]
for i,r in enumerate(rows):
    for j,c in enumerate(r): ax.text([0.0,0.22,0.40,0.62,0.82][j],0.86-i*0.12,c,color=ORG if i==0 else FG,fontsize=9.5,transform=ax.transAxes,weight="bold" if i==0 else "normal")
ax.text(0,1.0,"LARGER LITZ: NOT WORTH IT",color=ORG,fontsize=10,weight="bold",transform=ax.transAxes,va="top")
ax.text(0,0.36,"the field is set by amp-turns, and the supply voltage and ramp time set the current\n(26 V x 41.5 us / 54 uH = 20 A), not the wire; the coil copper loss is 0.1 W anyway.\n1.5 mm would give only 1.25x field per watt of COPPER loss, but needs thicker layers\nand leaves a 0.5 mm groove wall at the rim. Solid wire is worse: a D1.2 solid wire\nrings for about 4 us after turn-off. Gain is smaller than the cost of re-tooling.",color=FG,fontsize=8.6,transform=ax.transAxes,va="top")
fig.suptitle("PHI-FOLD 233 - blueprint 7: timing, bearing maths, power and wire size",color=FG,fontsize=14,x=0.01,ha="left"); fig.subplots_adjust(hspace=0.25,wspace=0.1)
plt.savefig("kit_v17/BLUEPRINT_7_TIMING_BEARING_POWER.png",dpi=90,facecolor=BG,bbox_inches="tight"); print("ok")
