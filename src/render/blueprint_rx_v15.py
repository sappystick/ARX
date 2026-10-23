import math, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, FancyArrowPatch
BG="#0b2a52"; FG="#e8f1ff"; ACC="#7fd4ff"; ORG="#ffb347"; YEL="#f2c94c"
def arc(rho,a0,a1,n=90): t=np.linspace(a0,a1,n); return np.c_[rho*np.cos(t),rho*np.sin(t)]
def dloop(rho,x0): a=math.acos(x0/rho); return np.vstack([arc(rho,-a,a),[[x0,-rho*math.sin(a)]],[[x0,rho*math.sin(a)]]])
def rotz(p,a): c,s=math.cos(a),math.sin(a); return np.c_[p[:,0]*c-p[:,1]*s,p[:,0]*s+p[:,1]*c]
def fig8_draw(ax,ang,N=6,r0=20,r1=110):
    for i,rho in enumerate(np.linspace(r1,r0,N)):
        x0=1.0+0.1*(r1-rho); R=dloop(rho,x0); L=R.copy(); L[:,0]*=-1
        for P,c in ((R,YEL),(L,ORG)): Q=rotz(P,ang); ax.plot(np.r_[Q[:,0],Q[0,0]],np.r_[Q[:,1],Q[0,1]],color=c,lw=0.9)
def quad_draw(ax,N=6,r0=20,r1=110):
    for rho in np.linspace(r1,r0,N):
        e=1.0+0.1*(r1-rho); s=math.sqrt(rho**2-e**2); a0=math.atan2(e,s); a1=math.atan2(s,e); base=np.vstack([[e,e],arc(rho,a0,a1,50)])
        for q,c in enumerate((YEL,ORG,YEL,ORG)): Q=rotz(base,q*math.pi/2); ax.plot(np.r_[Q[:,0],Q[0,0]],np.r_[Q[:,1],Q[0,1]],color=c,lw=0.9)
def board(ax,title):
    ax.add_patch(Circle((0,0),114,fc="#14634a",ec=FG,lw=1.5,alpha=0.85)); ax.add_patch(Circle((0,0),49.5,fc="none",ec=ACC,lw=0.9,ls="--")); ax.set_aspect("equal"); ax.set_xlim(-122,122); ax.set_ylim(-122,122); ax.axis("off"); ax.set_title(title,color=FG,fontsize=10)
    for a in (90,210,330): ax.add_patch(Circle((41*math.cos(math.radians(a)),41*math.sin(math.radians(a))),3.5,fc=BG,ec="w",lw=1.0))
    for a,lab in ((16.0,"X8"),(153.5,"W8"),(291.0,"V8"),(68.5,"Q"),(206.0,"spare"),(343.5,"shield")): ax.add_patch(Rectangle((48.3*math.cos(math.radians(a))-1.2,48.3*math.sin(math.radians(a))-1.2),2.4,2.4,fc=ACC,ec=FG,lw=0.5))
fig=plt.figure(figsize=(19,11.5),facecolor=BG)
for i,(ang,t) in enumerate(((0,"L1-L2: X8 figure-8 (axis 0 deg)"),(60,"L3-L4: W8 figure-8 (axis 60 deg)"),(120,"L5-L6: V8 figure-8 (axis 120 deg)"))):
    ax=fig.add_subplot(2,4,i+1,facecolor=BG); board(ax,t); fig8_draw(ax,math.radians(ang))
ax=fig.add_subplot(2,4,4,facecolor=BG); board(ax,"L7-L8: QUAD  + - + -"); quad_draw(ax)
ax=fig.add_subplot(2,4,5,facecolor=BG); ax.axis("off")
txt=["SB1R receive board (in BASE_PLATE_RX_TRAY recess D229 x 2.4)","","8 layers, 2.4 mm FR-4, ENIG, board D228.0, no ferrite, no copper pour,","open back (no restriction on the transmit side)","","per figure-8 channel: 6 nested D loops per lobe per layer, loops r110 to r20,","flat edge offset 1.0 + 0.1 (110 - r) mm, 1.8 mm trace, 35 um Cu,","2 layers in series (12 turns per lobe): L about 420 uH, R about 2.1 Ohm,","7.7 m trace, thermal noise about 0.19 nV/rtHz","","QUAD: 6 loops per quadrant per layer x 2 layers: L about 90 uH, R about 2.7 Ohm","","keep-outs: 3 x D7 at r41, 90/210/330 deg (M3 screws)","hub footprint r49.5 (dashed): lane pads sit under it at r48.3","pads (blue squares) 2.4 x 2.4 pairs at the 6 RX lane angles"]
for i,l in enumerate(txt): ax.text(-0.15,1.0-i*0.067,l,color=FG,fontsize=7.2,va="top",transform=ax.transAxes)
ax=fig.add_subplot(2,4,6,facecolor=BG); ax.axis("off")
tab=[("lane angle","coil","wires"),("16.0 deg (L1)","X8","twisted pair"),("153.5 deg (L2)","W8","twisted pair"),("291.0 deg (L3)","V8","twisted pair"),("68.5 deg (L4)","QUAD","twisted pair"),("206.0 deg (L5)","spare","-"),("343.5 deg (L6)","shield drain","1 wire"),("roof D20 port","HTA (hub-top antenna)","twisted pair")]
for i,row in enumerate(tab):
    for j,c in enumerate(row): ax.text(0.12+j*0.36,1.0-i*0.085,c,color=ORG if i==0 else FG,fontsize=8.6,va="top",transform=ax.transAxes,weight="bold" if i==0 else "normal")
ax.text(0.12,0.28,"RX lanes carry twisted pairs of D0.4 wire\n(lane 1.8 x 1.4 mm). TX lanes are separate.",color=ACC,fontsize=9,transform=ax.transAxes,va="top")
ax=fig.add_subplot(2,4,7,facecolor=BG); ax.axis("off"); ax.set_aspect("equal"); ax.set_xlim(-60,60); ax.set_ylim(-60,60)
ax.add_patch(Circle((0,0),45,fc="#2b3b55",ec=FG)); ax.add_patch(Circle((0,0),38,fc="none",ec=YEL,lw=1.2)); ax.add_patch(Circle((0,0),40.5,fc="none",ec=YEL,lw=1.2)); ax.add_patch(Circle((0,0),43,fc="none",ec=YEL,lw=1.2)); ax.add_patch(Circle((0,0),35.5,fc="none",ec=YEL,lw=1.2)); ax.add_patch(Circle((0,0),10,fc=BG,ec=FG))
ax.set_title("HTA: hub-top antenna (D90 PCB on the hub roof)",color=FG,fontsize=10); ax.text(0,-52,"4 turns r35.5 to r43, 4-layer 0.8 mm, L about 3 uH\nwires leave through the roof D20 port",color=FG,fontsize=8.5,ha="center")
ax=fig.add_subplot(2,4,8,facecolor=BG); ax.axis("off")
ls=["Channel plan (fits AB1A + AB1B, 5 channels):","","AB1A: X8, W8, V8","AB1B: QUAD, MONO (tap on the transmit coil leads, CB1)","CB1 ADC: HTA (transmit monitor / EMI reference)","","TX null (measured on the real winding paths):","  QUAD 0.003%   hex fig-8 0.002%   Y8 0.011%   X8 0.025%","  X8 shifted 0.5 mm along its axis: 0.66%","  so hold the board to +/-0.2 mm in its recess"]
for i,l in enumerate(ls): ax.text(0,1.0-i*0.085,l,color=FG,fontsize=9,va="top",transform=ax.transAxes)
fig.suptitle("PHI-FOLD 233 - receive cassette SB1R (ground-facing board in the base plate), all dimensions in mm",color=FG,fontsize=14,x=0.01,ha="left")
fig.subplots_adjust(wspace=0.35,hspace=0.25); plt.savefig("kit_v15/BLUEPRINT_3_RX_CASSETTE.png",dpi=90,facecolor=BG,bbox_inches="tight"); plt.close()
# ---------------- system elevation + block diagram
fig=plt.figure(figsize=(18,9),facecolor=BG); ax=fig.add_subplot(121,facecolor=BG)
def box(x0,x1,z0,z1,fc,ec=FG,lw=1.0,alpha=1.0): ax.add_patch(Rectangle((x0,z0),x1-x0,z1-z0,fc=fc,ec=ec,lw=lw,alpha=alpha))
box(-116.5,116.5,0,0.8,"#6c7a99"); box(114.5,116.5,0,3.2,"#6c7a99"); box(-114.5,-116.5,0,3.2,"#6c7a99"); box(-114,114,0.8,3.2,"#14634a"); ax.text(0,1.9,"SB1R receive board D228 x 2.4 (8 layers: X8, W8, V8, QUAD)",color="w",fontsize=8,ha="center",va="center")
cols=["#33adb5","#5599e0","#8c85eb","#c26fdb","#eb7aae","#f59e6b"]
for k in range(1,7):
    zb=3.2+(6-k)*4.4
    for s in (-1,1): box(s*49.9 if s>0 else -112,112 if s>0 else -49.9,zb,zb+3.6,cols[k-1],alpha=0.92)
box(-49.5,-44,3.2,41.3,"#9aa3b8"); box(44,49.5,3.2,41.3,"#9aa3b8"); box(-52,52,41.3,44.5,"#9aa3b8")
box(-45,45,44.5,46.1,"#14634a"); ax.text(0,47.2,"HTA D90 x 1.6 on the roof (transmit monitor / EMI reference)",color=YEL,fontsize=8,ha="center")
ax.text(0,22,"PCB vault: AB1A, AB1B, CB1 (+ shield wrap)",color=FG,fontsize=9,ha="center")
for z,t in ((3.2,"3.2"),(28.8,"28.8"),(44.5,"44.5")): ax.plot([118,122],[z,z],color=ACC); ax.text(123,z,t,color=ACC,fontsize=8,va="center")
ax.annotate("",xy=(-118,0),xytext=(-118,46.1),arrowprops=dict(arrowstyle="<->",color=ACC)); ax.text(-120,23,"46.1 overall",color=ACC,rotation=90,fontsize=8,va="center",ha="right")
ax.annotate("",xy=(-116.5,-4),xytext=(116.5,-4),arrowprops=dict(arrowstyle="<->",color=ACC)); ax.text(0,-7,"D233",color=ACC,ha="center",fontsize=9)
ax.text(-110,35,"ground\nfacing down",color=FG,fontsize=8)
ax.set_xlim(-128,135); ax.set_ylim(-10,52); ax.set_aspect(2.1); ax.axis("off"); ax.set_title("elevation: receive cassette at the bottom, six transmit formers, hub, hub-top antenna",color=FG,fontsize=11,loc="left")
ax=fig.add_subplot(122,facecolor=BG); ax.axis("off"); ax.set_xlim(0,10); ax.set_ylim(0,10)
def bx(x,y,w,h,t,fc="#1d4a85"): ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.05",fc=fc,ec=FG)); ax.text(x+w/2,y+h/2,t,color=FG,fontsize=9,ha="center",va="center")
def arr(x0,y0,x1,y1,t=""): ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle="->",mutation_scale=14,color=ACC,lw=1.3)); ax.text((x0+x1)/2,(y0+y1)/2+0.15,t,color=ACC,fontsize=7.5,ha="center")
bx(0.2,7.8,2.2,1.4,"X8 fig-8\nL1-L2"); bx(0.2,6.0,2.2,1.4,"W8 fig-8\nL3-L4"); bx(0.2,4.2,2.2,1.4,"V8 fig-8\nL5-L6"); bx(0.2,2.4,2.2,1.4,"QUAD\nL7-L8"); bx(0.2,0.4,2.2,1.4,"coil tap (MONO)\nCMON + 330R damping","#4a2d85")
bx(3.6,6.4,2.4,2.6,"RX lanes in the hub wall\n16.0 / 153.5 / 291.0 / 68.5 deg\ntwisted pairs"); bx(3.6,2.0,2.4,2.0,"TX lanes + 18 ports\nlead A / B of each layer","#4a2d85")
bx(7.0,6.6,2.8,2.6,"AB1A\nGX-free build:\nX8 / W8 / V8\n16-bit ADC x3"); bx(7.0,3.6,2.8,2.4,"AB1B\nQUAD + MONO\n16-bit ADC x2"); bx(7.0,0.6,2.8,2.4,"CB1 (Pico 2 W)\nHTA to the 12-bit ADC\nPIO capture of AB1 data","#2d6a4a")
for y in (8.5,6.7,4.9,3.1): arr(2.4,y,3.6,7.7)
arr(2.4,1.1,3.6,3.0); arr(6.0,7.7,7.0,8.0,"3 pairs"); arr(6.0,7.2,7.0,4.8,"1 pair"); arr(6.0,3.0,7.0,4.0,"MONO_IN"); arr(8.4,3.6,8.4,3.0,"SPI + BLANK")
ax.text(0.2,9.7,"signal path (all inside the head; only power and the trigger cable leave it)",color=FG,fontsize=11,weight="bold")
ax.text(7.0,0.1,"HTA wires: roof D20 port to CB1",color=YEL,fontsize=8)
plt.savefig("kit_v15/BLUEPRINT_4_SYSTEM_RX_AND_CHANNELS.png",dpi=90,facecolor=BG,bbox_inches="tight"); print("ok")
