import pickle, math, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
mu0=4e-7*math.pi; GOLD=137.50776405; PN,G,ZRX=3.6,0.8,3.2; P=pickle.load(open('kit_v15/LOW/paths.pkl','rb'))
TX=[np.c_[np.vstack([P[k][0],P[k][1]])[::3],np.full(len(np.vstack([P[k][0],P[k][1]])[::3]),ZRX+(6-k)*(PN+G)+PN-0.7)] for k in range(1,7)]           # mm
def Bvec(pt):
    B=np.zeros(3)
    for p in TX:
        d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2; r=pt-m; rn=np.sqrt((r**2).sum(1)+1.0)[:,None]; B+=np.sum(np.cross(d,r)/rn**3,axis=0)
    return B
xs=np.arange(-138,139,3.0); zs=np.arange(-45,80,3.0); BX=np.zeros((len(zs),len(xs))); BZ=np.zeros_like(BX)
for i,z in enumerate(zs):
    for j,x in enumerate(xs): b=Bvec(np.array([x,0.0,z])); BX[i,j]=b[0]; BZ[i,j]=b[2]
mag=np.hypot(BX,BZ)
fig,ax=plt.subplots(figsize=(17,8.2)); X,Z=np.meshgrid(xs,zs)
sp=ax.streamplot(X,Z,BX,BZ,color=np.log10(mag+1e-12),cmap="viridis",density=2.6,linewidth=0.9,arrowsize=0.9)
cols=["#33adb5","#5599e0","#8c85eb","#c26fdb","#eb7aae","#f59e6b"]
def box(x0,x1,z0,z1,fc,ec="k",lw=0.6,alpha=1.0): ax.add_patch(Rectangle((x0,z0),x1-x0,z1-z0,fc=fc,ec=ec,lw=lw,alpha=alpha,zorder=5))
box(-116.5,116.5,0,0.8,"#6c7a99"); box(-114,114,0.8,3.2,"#14634a")
for k in range(1,7):
    zb=3.2+(6-k)*4.4; box(49.9,112,zb,zb+3.6,cols[k-1]); box(-112,-49.9,zb,zb+3.6,cols[k-1])
box(44,49.5,3.2,41.3,"#9aa3b8"); box(-49.5,-44,3.2,41.3,"#9aa3b8"); box(-52,52,41.3,44.5,"#9aa3b8"); box(-45,45,44.5,47.1,"#14634a")
for a,b in ((63,79),(84,100),(100,113)): box(a,b,30.4,32.9,"#222",alpha=0.95); box(-b,-a,30.4,32.9,"#222",alpha=0.95)
ax.text(0,22,"vault: shielded electronics\n(field excluded by the closed nanocrystalline can)",ha="center",va="center",fontsize=9,zorder=6,color="w",bbox=dict(fc="#333",ec="none",alpha=0.7))
ax.annotate("ferrite lotus hood: gathers the return flux above the coil",xy=(85,32),xytext=(60,62),arrowprops=dict(arrowstyle="->",color="k"),fontsize=10,zorder=7)
ax.annotate("HTA: sees the transmit flux strongly\n(monitor), 18 V at turn-off",xy=(0,47.1),xytext=(-100,66),arrowprops=dict(arrowstyle="->",color="k"),fontsize=10,zorder=7)
ax.annotate("RX figure-8 / quad board: symmetric about the axis,\nso the transmit flux through it cancels",xy=(-70,2),xytext=(-125,-34),arrowprops=dict(arrowstyle="->",color="k"),fontsize=10,zorder=7)
ax.text(70,-35,"target signal arrives from here",fontsize=10,style="italic"); ax.axhline(0,color="k",lw=0.5)
ax.set_xlim(-138,138); ax.set_ylim(-45,78); ax.set_aspect(1.0); ax.set_xlabel("x (mm), plane y = 0"); ax.set_ylabel("z (mm)")
ax.set_title("Flux map of the six-layer transmit stack (Biot-Savart, layers in parallel): colour = log10 |B|; streamlines are the field lines",fontsize=11)
plt.colorbar(sp.lines,ax=ax,fraction=0.02,label="log10 |B| (arbitrary units)"); plt.tight_layout(); plt.savefig("kit_v16/FLUX_MAP_AND_MATERIAL_PLACEMENT.png",dpi=95); plt.close()
# ---------------- blueprint 5: HTA pattern, hood layout, material table
BG="#0b2a52"; FG="#e8f1ff"; ACC="#7fd4ff"; ORG="#ffb347"; YEL="#f2c94c"
fig=plt.figure(figsize=(19,10),facecolor=BG)
ax=fig.add_subplot(131,facecolor=BG); ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-58,58); ax.set_ylim(-62,58)
ax.add_patch(Circle((0,0),52,fc="none",ec=FG,lw=1.2)); ax.add_patch(Circle((0,0),45.2,fc="#14634a",ec=FG,lw=1.0)); ax.add_patch(Circle((0,0),4,fc=BG,ec=FG))
t=np.linspace(0,2*np.pi,360)
for r,c in ((35.5,YEL),(38.0,YEL),(40.5,ORG),(43.0,ORG)): ax.plot(r*np.cos(t),r*np.sin(t),color=c,lw=1.6)
ax.plot([35.5,43],[0,0],color=FG,lw=0.0); ax.add_patch(Rectangle((33.8,-1.2),2.4,2.4,fc=ACC,ec=FG)); ax.text(33,-4.5,"pad A",color=ACC,fontsize=8,ha="right"); ax.add_patch(Rectangle((-44.2,-1.2),2.4,2.4,fc=ACC,ec=FG)); ax.text(-43,-4.5,"pad B",color=ACC,fontsize=8,ha="center")
for a in (45,135,225,315): ax.add_patch(Rectangle((30*math.cos(math.radians(a))-2,30*math.sin(math.radians(a))-2),4,4,fc="none",ec=ACC,ls="--",lw=0.8)); ax.text(30*math.cos(math.radians(a)),30*math.sin(math.radians(a)),"hook",color=ACC,fontsize=7,ha="center",va="center")
ax.plot([48.6,50.8],[0,0],color="r",lw=3); ax.text(55,0,"strap\ngap 0 deg",color="r",fontsize=8,ha="center",va="center")
ax.set_title("HTA board: D90 x 1.6, 2 layers, 4 turns r35.5-43\n(L1 yellow, L2 orange, in series), about 3 uH",color=FG,fontsize=10)
ax.text(0,-58,"D104 hub cap; board sits in the 0.9 floor + 1.7 recess\n8 mm cable port; hooks pass through the 4 roof windows at r30",color=FG,fontsize=8.5,ha="center")
ax=fig.add_subplot(132,facecolor=BG); ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-122,122); ax.set_ylim(-125,122)
ax.add_patch(Circle((0,0),116.5,fc="none",ec=FG,lw=1.4)); ax.add_patch(Circle((0,0),52.6,fc="none",ec=ACC,ls="--"))
def rect_poly(cx,cy,ang,hr,ht): c,s=math.cos(ang),math.sin(ang); return [(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(hr,-ht),(hr,ht),(-hr,ht),(-hr,-ht)]]
for nm,rc_,hr,ht,cnt,ph,col in (("A",71.0,8,14,12,0.0,"#7fd4ff"),("B",92.0,8,19,12,(GOLD*1)%30,"#ffb347"),("C",106.5,6.5,25,12,(GOLD*2)%30,"#f2c94c")):
    for i in range(cnt):
        th=math.radians(ph+i*360/cnt); ax.add_patch(Polygon(rect_poly(rc_*math.cos(th),rc_*math.sin(th),th,hr,ht),fc=col,ec=FG,lw=0.6,alpha=0.85))
ax.set_title("Lotus hood: 36 MnZn tiles 2.5 thick in 3 rings (A r71, B r92, C r106.5),\nring phases 0 / 17.5 / 5.0 deg (golden angle mod 30) so the slits never line up radially",color=FG,fontsize=10)
ax.text(0,-121,"coverage 64% of r52.6-114; all 36 tiles about 246 g; rings B+C only about 181 g\nfield gain: +14/+7.5/+4% for a full ideal hood (earlier BEM); partial coverage roughly in proportion (estimate)",color=FG,fontsize=8.5,ha="center")
ax=fig.add_subplot(133,facecolor=BG); ax.axis("off")
rows=[("material / part","where","what it does (and the limit)"),
("MnZn ferrite hood","above L1, z30.4-32.9","collects return flux: +2 to +9% depth (est), +15% L, 181-246 g"),
("nanocrystalline can","closed wrap round the vault","keeps electronics out of the field: 14-27x reduction; slit, never a closed loop"),
("NiZn lossy bead / sleeve","hub roof port, umbilical entry","absorbs common-mode RF on leads (dissipates, near no cost)"),
("carbonyl-iron silicone sheet","under the roof, inside the vault","damps cavity ringing and board resonances (optional)"),
("syntactic foam / gel","all cavities","holds, seals, low dielectric constant; does not guide flux"),
("drain wires + one star ground","vault floor; strap gaps at 0 / 180 deg","grounds the shields at ONE point; replaces 'dissipating rods'"),
("NO metal rods or plates","anywhere near the coil","any solid metal is an eddy-current target (looks like gold)")]
import textwrap
for i,(a,b,c) in enumerate(rows):
    y=0.98-i*0.125; col=ORG if i==0 else (("#ff7f7f") if i==len(rows)-1 else FG)
    if i==0: ax.text(0.0,y,"MATERIALS AND PLACEMENT",color=ORG,fontsize=10,weight="bold",va="top",transform=ax.transAxes); continue
    ax.text(0.0,y,a,color=col,fontsize=9,weight="bold",va="top",transform=ax.transAxes); ax.text(0.0,y-0.032,"where: "+b,color=col,fontsize=7.6,va="top",transform=ax.transAxes)
    ax.text(0.0,y-0.060,"\n".join(textwrap.wrap("does: "+c,58)),color=col,fontsize=7.6,va="top",transform=ax.transAxes)
fig.suptitle("PHI-FOLD 233 - hub-top antenna, lotus hood and materials placement (dimensions in mm)",color=FG,fontsize=14,x=0.01,ha="left"); fig.subplots_adjust(wspace=0.18)
plt.savefig("kit_v16/BLUEPRINT_5_HTA_HOOD_MATERIALS.png",dpi=90,facecolor=BG,bbox_inches="tight"); print("figs ok")
