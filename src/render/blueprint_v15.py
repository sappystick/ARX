import json, math, numpy as np, glob
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
GOLD=137.50776405; PN,G,ZRX=3.6,0.8,3.2
BG="#0b2a52"; FG="#e8f1ff"; ACC="#7fd4ff"
fig,ax=plt.subplots(figsize=(17,8.8),facecolor=BG); ax.set_facecolor(BG)
cols=["#33adb5","#5599e0","#8c85eb","#c26fdb","#eb7aae","#f59e6b"]
def box(x0,x1,z0,z1,fc,ec=FG,lw=1.0,alpha=1.0,hatch=None): ax.add_patch(Rectangle((x0,z0),x1-x0,z1-z0,fc=fc,ec=ec,lw=lw,alpha=alpha,hatch=hatch))
# base plate and PCB recess
box(5,116.5,0,0.8,"#6c7a99"); box(114.5,116.5,0,3.2,"#6c7a99"); box(5,114.5,0.8,3.2,"none",ec=ACC,lw=0.8,hatch="//"); ax.text(60,1.9,"RX board recess D229 x 2.4 (PCB SB1R)",color=ACC,fontsize=8,ha="center",va="center")
for k in range(1,7):
    zb=ZRX+(6-k)*(PN+G); box(49.9,112,zb,zb+PN,cols[k-1],ec=FG,lw=0.8,alpha=0.92); ax.text(80,zb+PN/2,f"FORMER L{k}   (track {(GOLD*(k-1))%360:.1f} deg, {k} rim notches)",color="k",fontsize=8,ha="center",va="center")
    ax.annotate("",xy=(114,zb),xytext=(114,zb+PN),arrowprops=dict(arrowstyle="<->",color=FG,lw=0.7))
    if k<6: ax.annotate("",xy=(119,zb),xytext=(119,zb-G),arrowprops=dict(arrowstyle="<->",color=ACC,lw=0.7)); ax.text(121,zb-G/2,"0.8",color=ACC,fontsize=7,va="center")
ax.text(117.4,ZRX+5*4.4+PN/2,"3.6",color=FG,fontsize=7,va="center")
# hub
box(44,49.5,3.2,41.3,"#9aa3b8"); box(10,52,41.3,44.5,"#9aa3b8"); box(49.5,52,29.2,41.3,"#9aa3b8")
for z in (9,17,25,33): box(41.5,44,z-1.2,z,"#9aa3b8")
box(37.6,44.4,3.2,14.2,"#b9c1d4",alpha=0.55); ax.text(41,15.3,"M3 boss",color=FG,fontsize=7,ha="center")
box(48.1,49.5,38,40,BG,ec=ACC,lw=1.0); ax.text(46.8,36.8,"lead port\n2 x 2",color=ACC,fontsize=7,ha="center",va="top")
box(46.5,49.5,3.2,28.5,"none",ec=ACC,lw=0.7); ax.text(47.4,12,"track 4 x 3\n(blind)",color=ACC,fontsize=7,rotation=90,ha="center",va="center")
box(48.6,51.4,25.0,29.1,"#d9b36b",ec=FG,lw=0.8); ax.text(53.5,26.5,"L1 bond lug",color=FG,fontsize=7)
c=51.7; zb2=ZRX+4*4.4; ax.add_patch(Rectangle((c-1.5,zb2+0.2),3.0,3.6,fc="#f2c94c",ec="k",lw=0.5)); ax.add_patch(Rectangle((c-2.1,zb2+3.6),4.2,0.8,fc="#f2c94c",ec="k",lw=0.5)); ax.text(58,zb2+4.5,"stepped pin\n(shoulder = gap)",color="#f2c94c",fontsize=7)
ax.text(30,42.9,"roof D20 port + 4 vent/fill windows",color=FG,fontsize=8,ha="center",va="center",color_="k") if False else ax.text(31,42.9,"hub roof (vent / fill windows)",color="k",fontsize=8,ha="center",va="center")
ax.text(28,24,"PCB vault\nD88 inner, 4 ledges at 8 mm pitch",color=FG,fontsize=9,ha="center",va="center")
# dimensions
def dim(x0,x1,z,txt,dz=2.2): ax.annotate("",xy=(x0,z),xytext=(x1,z),arrowprops=dict(arrowstyle="<->",color=ACC,lw=0.9)); ax.text((x0+x1)/2,z+dz,txt,color=ACC,fontsize=8,ha="center")
dim(0,116.5,-5,"D233 footprint (R116.5)",-3.5); dim(44,49.5,46.5,"hub wall 5.5",1.0); dim(49.5,49.9,31.5,"0.4",1.5)
ax.annotate("",xy=(-3,3.2),xytext=(-3,28.8),arrowprops=dict(arrowstyle="<->",color=ACC,lw=0.9)); ax.text(-4.5,16,"stack 25.6\n(3.2 to 28.8)",color=ACC,fontsize=8,rotation=90,ha="right",va="center")
ax.annotate("",xy=(-9,0),xytext=(-9,44.5),arrowprops=dict(arrowstyle="<->",color=ACC,lw=0.9)); ax.text(-10.5,22,"overall 44.5",color=ACC,fontsize=8,rotation=90,ha="right",va="center")
ax.axvline(0,color=FG,lw=0.6,ls="-.")
ax.set_xlim(-16,126); ax.set_ylim(-8,50); ax.set_aspect(1.9); ax.axis("off")
ax.set_title("PHI-FOLD 233 - radial section through the search-head core (flat-face final design), all dimensions in mm",color=FG,fontsize=12,loc="left")
ax.text(126,-7,"flat formers: every underside is a true plane (prints flat, no supports); top relief 0.30 (12 petals); layer pitch 4.4",color=FG,fontsize=8,ha="right")
plt.savefig("kit_v15/BLUEPRINT_1_SECTION.png",dpi=105,facecolor=BG,bbox_inches="tight"); plt.close()
# plan / angular map
R=json.load(open("kit_v15/PRINT/report.json")); H=json.load(open("kit_v15/SET/06_DATA/hub_flange_coupons_report.json"))["verification"]; P=json.load(open("kit_v15/SET/06_DATA/pins_and_base_plate.json"))["pins"]
fig=plt.figure(figsize=(12.5,12.5),facecolor=BG); ax=fig.add_subplot(111,projection="polar",facecolor=BG); ax.set_theta_zero_location("E"); ax.set_ylim(0,125); ax.set_yticks([]); ax.set_xticks(np.radians(np.arange(0,360,30))); ax.tick_params(colors=FG); ax.spines["polar"].set_color(FG)
t=np.linspace(0,2*np.pi,720)
for rr,lab in ((116.5,"R116.5 footprint"),(109.6,"R1 109.6 winding"),(62,"R0 62 winding start"),(49.9,"bore 49.9"),(44,"hub bore 44")): ax.plot(t,np.full_like(t,rr),color=ACC,lw=0.8,ls="--"); 
for k in range(1,7):
    a=math.radians((GOLD*(k-1))%360); ax.plot([a],[46],"s",color=cols[k-1],ms=13); ax.text(a,128,f"L{k}\n{(GOLD*(k-1))%360:.1f}",color=cols[k-1],ha="center",va="center",fontsize=10,weight="bold")
    la=a+math.radians(6); lb=a+math.radians(11); lr=a+math.radians(16)
    for q,mk,s in ((la,"o",6),(lb,"o",6)): ax.plot([q,q],[49.9,62],color=cols[k-1],lw=1.4); ax.plot([q],[48],mk,color=cols[k-1],ms=s)
    ax.plot([lr],[48],"^",color="#6aa0ff",ms=7)
for p in P: ax.plot([math.radians(p["theta_deg"])],[51.7],"D",color="#f2c94c",ms=7)
for th in R["spec"]["L1_bond_key_notches_deg"]: ax.plot([math.radians(th)],[50.0],"o",color="#d9b36b",ms=6,mfc="none")
for b in (90,210,330): ax.plot([math.radians(b)],[41],"o",color="w",ms=9,mfc="none"); 
ax.set_title("Plan / angular map of the core: tracks (squares, = key tooth = petal phase), TX lanes + radial leads (dots + lines), RX lanes (triangles),\npins (yellow diamonds, n x 137.508), L1 bond lugs (open orange), M3 bosses (open white at r41)",color=FG,fontsize=10)
plt.savefig("kit_v15/BLUEPRINT_2_ANGULAR_MAP.png",dpi=100,facecolor=BG,bbox_inches="tight"); print("ok")
