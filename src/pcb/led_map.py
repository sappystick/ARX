import math, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge
# ---------- shielding options (S = 1 + mu_eff t / 2a), a = cylinder radius
mu0=4e-7*math.pi; rows={}
def S(mu,t,a): return 1+mu*t/(2*a)
for name,mu,t in (("sprayed ferrite-silicone, mu 10, 0.3 mm",10,0.3),("flexible ferrite sheet, mu 100, 0.5 mm",100,0.5),("flaked nanocrystalline, mu_eff 1500, 0.12 mm",1500,0.12),
                  ("nanocrystalline, mu_eff 5000 (pulse), 0.12 mm",5000,0.12),("nanocrystalline, mu_eff 5000, 0.25 mm",5000,0.25),("nanocrystalline, mu_eff 10000, 0.25 mm",10000,0.25),("MnZn tube mu 2000, 3 mm",2000,3.0)):
    s=S(mu,t,48); rows[name]=dict(S=round(s,1),dB=round(20*math.log10(s),1),metal_in_head_reduction_S2=round(s*s))
area=math.pi*102*40+2*math.pi*51**2
mass=dict(ribbon_0p25mm_g=round(area*0.25*7.2/1000,0),MnZn_3mm_g=round(area*3*4.8/1000,0))
tau_us=mu0*8.3e5*0.25e-3*0.048/2*1e6
res=dict(shield=rows,mass=mass,unslit_ribbon_cylinder_eddy_tau_us=round(tau_us,2),sectored_Cu_plane_nuggets=13.0,
         combined="sectored copper (13x nugget bare) / S^2: S=29 -> 0.015x ; S=15 -> 0.06x; S=1.03 (spray) -> 12x")
json.dump(res,open("kit_v6/shield_options.json","w"),indent=1); print(json.dumps(res,indent=1))
# ---------- LED face map
fig,axs=plt.subplots(1,2,figsize=(15,7.6),facecolor="#0b1220")
ax=axs[0]; ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-130,130); ax.set_ylim(-130,130)
ax.add_patch(Circle((0,0),116.5,fc="#1b2436",ec="#6b7a99",lw=2)); ax.add_patch(Circle((0,0),60,fc="#141b2a",ec="#3a4660",lw=1))
rings=[(72,"deep"),(90,"mid"),(108,"shallow")]; NA=24
def pix(a,ri,col,al=1,sz=150):
    r=rings[ri][0]; x=r*math.cos(math.radians(a)); y=r*math.sin(math.radians(a)); ax.scatter([x],[y],s=sz,c=[col],alpha=al,edgecolors="none",zorder=5)
for ri in range(3):
    for k in range(NA): pix(k*360/NA,ri,"#2b3550",1,60)
gold=(1,0.68,0.1); 
for ri,(w) in enumerate((0.25,0.55,1.0)):                  # a gold target at bearing 40 deg, shallow, strong: afterglow spread across 3 azimuth pixels
    pass
for k,al in ((2,0.35),(1,1.0),(0,0.35)):                   # bearing 40 deg -> pixel index 40/15=2.67 ~ 3
    pass
tg=[(3,2,1.0),(2,2,0.45),(4,2,0.45),(3,1,0.55),(3,0,0.2)]
for k,ri,al in tg: pix(k*360/NA,ri,gold,al,260)
for k,ri,col,al in ((14,1,(1,0.2,0.2),0.9),(15,1,(1,0.2,0.2),0.4),(19,2,(0.7,0.4,1),0.8)):
    pix(k*360/NA,ri,col,al,220)
ax.annotate("",xy=(100*math.cos(math.radians(45)),100*math.sin(math.radians(45))),xytext=(0,0),arrowprops=dict(arrowstyle="->",color="#ffd27a",lw=2))
ax.text(0,0,"heading\n(front)",color="#8fa3c8",ha="center",va="center",fontsize=9)
ax.text(0,-124,"top face, 24 azimuth x 3 rings = 72 light-pipe pixels",color="#c9d4ee",ha="center",fontsize=10)
ax.set_title("What the operator sees (example: shallow gold at bearing 45, iron behind-left, foil right)",color="w",fontsize=11)
ax=axs[1]; ax.axis("off"); ax.set_xlim(0,10); ax.set_ylim(0,10)
txt=[("PIXEL CODE","w",14),("azimuth = target bearing (from GX/GY ratio, sign from main-coil polarity)","#c9d4ee",10),("ring  = depth tier: inner ring dim/deep ... outer ring bright/shallow  (centred on target = full ring lights = pinpoint)","#c9d4ee",10),
("brightness = signal strength, pulse rate = confidence, afterglow 400 ms = trail","#c9d4ee",10),("",None,8),("COLOUR = MATERIAL CLASS","w",14)]
y=9.6
for t,c,s in txt:
    if t: ax.text(0.1,y,t,color=c,fontsize=s,wrap=True,va="top")
    y-=0.9 if s>10 else 0.75
cols=[((1,0.68,0.1),"gold / gold alloy (decay 6-30 us, high conductivity ratio)"),((0.85,0.95,1),"silver, copper, large non-ferrous (long decay)"),((1,0.2,0.2),"ferrous / hot rock (viscous tail)"),
      ((0.7,0.4,1),"foil / pull-tab (very short decay)"),((0.3,0.8,0.4),"ground mineralisation warning (slow breathing)"),((0.35,0.55,1),"unknown / low confidence")]
y=6.2
for c,t in cols: ax.scatter([0.4],[y],s=220,c=[c]); ax.text(0.9,y,t,color="#dfe7f7",fontsize=10,va="center"); y-=0.62
ax.text(0.1,2.2,"MODES (joystick press cycles):  SOUND+LED | SOUND only | LED only | SILENT\nDial: 4 programs.  Trigger: pinpoint / re-zero.\nStatus pixel (ring 0, index 0): battery colour.",color="#c9d4ee",fontsize=10,va="top")
plt.tight_layout(); plt.savefig("kit_v6/RENDER/08_LED_FACE_MAP.png",dpi=110,facecolor=fig.get_facecolor())
