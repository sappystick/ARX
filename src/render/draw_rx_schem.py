import textwrap, json, math, numpy as np, textwrap
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
BG="#0b2a52"; FG="#e8f1ff"; ACC="#7fd4ff"; ORG="#ffb347"; GRN="#6fe3a0"; RED="#ff8a8a"; YEL="#f2c94c"
t=json.load(open("kit_v21/sim_tanr.json")); qb=json.load(open("kit_v21/sim_quadbearing.json"))
# ======================= figure 1: the receive platform
S=json.load(open("kit_v22/sbq_sim.json")); D=json.load(open("kit_v22/sbq_damping2.json"))["first_clean_gate_us"]
fig=plt.figure(figsize=(24,13),facecolor=BG)
def axs_(pos): a=fig.add_axes(pos,facecolor="#10335f"); a.tick_params(colors=FG); [s.set_color(FG) for s in a.spines.values()]; return a
a=axs_([0.04,0.56,0.27,0.36]); pv=t["peak_volts_at_turnoff"]; lk=S["leak"]
labs=["aligned","0.1 mm","0.5 mm (worst of x,y)"]
x8=[pv["X8 figure-8"]["shift 0,0 mm"],pv["X8 figure-8"]["shift 0.1,0.0 mm"],pv["X8 figure-8"]["shift 0.5,0 mm"]]
def qv(b): d=lk[b]; return [d["aligned"]["peak_V"],d["0.1 mm x"]["peak_V"],max(d["0.5 mm x"]["peak_V"],d["0.5 mm y"]["peak_V"])]
w=0.26; xs=np.arange(3)
for i_,(nm,vals,c) in enumerate((("X8 figure-8 (old idealised model)",x8,"#ff8a8a"),("SB1R-QA real copper",qv("QUAD-A board"),"#7fd4ff"),("SB1R-QB real copper",qv("QUAD-B board (rotated 45 deg)"),"#6fe3a0"))): a.bar(xs+(i_-1)*w,[max(v,1e-5) for v in vals],w,color=c,label=nm)
a.set_yscale("log"); a.set_xticks(xs); a.set_xticklabels(labs,color=FG); a.set_ylabel("peak volts on the receive coil at turn-off",color=FG); a.set_xlabel("board offset against the transmit coil",color=FG); a.legend(fontsize=9,facecolor="#10335f",labelcolor=FG); a.grid(alpha=.3,which="both"); a.set_title("Leak from the real Gerber copper (modeled)",color=FG,fontsize=13)
a=axs_([0.36,0.56,0.27,0.36]); ph=np.radians(np.arange(0,361,5)); a.plot(np.degrees(ph),np.sin(2*ph),color="#7fd4ff",label="QUAD A  ~ sin 2phi"); a.plot(np.degrees(ph),-np.cos(2*ph),color="#6fe3a0",label="QUAD B  ~ -cos 2phi"); a.plot(np.degrees(ph),np.hypot(np.sin(2*ph),np.cos(2*ph)),color=ORG,lw=2,label="RSS of the pair (flat within +-2.5% in the real-copper model)")
a.set_xlabel("target bearing (deg)",color=FG); a.set_title("Bearing = 0.5 atan2(B,A) + 45 deg; model scatter 0.3-0.5 deg",color=FG,fontsize=12); a.legend(fontsize=9,facecolor="#10335f",labelcolor=FG); a.grid(alpha=.3)
a=axs_([0.68,0.56,0.29,0.36]); dd=D["A aligned 0.01 mV, Cself 100 pF, blank release 0 us"]; kw=[k for k in D if k.startswith("worst modeled") and "Cself 100 pF, blank release 0 us" in k][0]; dw=D[kw]
lab=["none (rings past 60 us)","330 ohm","470 ohm","680 ohm (fitted)","2.2 kohm"]; kk=["no Rd","Rd 330","Rd 470","Rd 680","Rd 2200"]
a.bar(np.arange(5)-0.2,[dd[k] for k in kk],0.4,color="#6fe3a0",label="board A aligned (0.01 mV)"); a.bar(np.arange(5)+0.2,[dw[k] for k in kk],0.4,color="#ffb347",label=f"worst real leak ({kw.split(',')[0].split()[-2]} mV)")
a.set_xticks(range(5)); a.set_xticklabels(lab,color=FG); a.set_ylabel("first clean gate (us), 176 uH, 100 pF, AB1T input, no blanking",color=FG); a.set_title("Damping resistor across each coil is mandatory",color=FG,fontsize=13); a.legend(fontsize=9,facecolor="#10335f",labelcolor=FG); a.grid(alpha=.3,axis="y")
tx=fig.add_axes([0.03,0.02,0.94,0.46]); tx.axis("off"); tx.set_facecolor(BG)
rows=[("SB1R-Q = two stacked 4-layer D228 boards (through vias only), generated in src/pcb/sbq_*.py","Each board: 4 lobes at (+-50, +-50) mm, each lobe = 4 series stepped spirals of 6 full rings (r 40..15 mm, 0.8 mm trace), lobes wired + - + - by radial links; 24 turns/lobe, 16.9 m copper, L = 176 uH, R = 10.4 ohm (1 oz) or 5.2 ohm (2 oz). Board B = board A rotated 45 deg with its own tuned arc radii. Lead pads P1/P2 at (+-4, 33) mm; 3 M3 holes r28 at 22.5/157.5/247.5 deg."),
("Modeled results (real copper, 100 nF film clamp)","Leak at turn-off: A 0.01 mV aligned, 0.02 / 0.13 / 3.9 mV at 0.1 mm / 0.5 mm x / 0.5 mm y; B 0.07, 0.59 / 6.0 / 10.3 mV. Figure-8 at 0.5 mm: 630 mV. Pattern: sin 2phi and cos 2phi, RSS flat within +-2.5%, signal 3.2x the earlier idealised quad at equal noise (about 1.7 nV/rtHz with RS = 100 ohm). Scaled depth estimate about 115 / 170 / 205 mm for 0.1 / 1 / 5 g gold (free air, unverified)."),
("Analog boards and the one new part","AB1T-A: IN1 (J1.1) = QUAD-A, IN2 (J1.2) = QUAD-B, return J1.4/J1.5, RS 100 ohm. AB1T-B: spare + MONO. Damping: RD1/RD2 680 ohm 0805 on the QA top across each coil (the 176 uH coil rings for more than 60 us without it); QB leads come up through two QA transfer pads at r23. Tuned link radii cancel the lobe residual: fabrication tolerance will set the real leak, hence the digital air template."),
("Dropped / corrected","Analog multiplying-DAC trim dropped (needs 20 MHz, under 10 ns). Earlier estimate L = 360 uH was wrong (176 uH). First attempt with continuous spirals leaked 3.5 V because spiral turns drift off-centre; replaced by full concentric rings.")]
y=0.97
for h,b in rows:
    tx.text(0.0,y,h,color=ORG,fontsize=13,weight="bold",va="top",transform=tx.transAxes); y-=0.05; b="\n".join(textwrap.wrap(b,190)); tx.text(0.0,y,b,color=FG,fontsize=11,va="top",transform=tx.transAxes); y-=0.05*(b.count("\n")+1)+0.02
fig.suptitle("Receiver platform v5 (RX-Q): dual rotated quadrupole receive boards, modeled from the real Gerber copper",color=FG,fontsize=19,x=0.02,ha="left")
plt.savefig("kit_v22/RX_PLATFORM_QUAD.png",dpi=60,facecolor=BG)
# ======================= figure 2: level-by-level electrical schematic
fig=plt.figure(figsize=(24,17),facecolor=BG); ax=fig.add_axes([0,0,1,1],facecolor=BG); ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis("off")
import textwrap as _tw
def B(x,y,w,h,title,body,ec=ACC):
    body="\n".join(l2 for l in body.split("\n") for l2 in _tw.wrap(l,int(w*2.75)))
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.25",fc="#143d73",ec=ec,lw=1.6)); ax.text(x+0.6,y+h-0.8,title,color=ORG,fontsize=11.5,weight="bold",va="top"); ax.text(x+0.6,y+h-2.8,body,color=FG,fontsize=9.3,va="top",linespacing=1.35)
def A(x0,y0,x1,y1,c=FG,lw=1.4): ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle="->",mutation_scale=13,color=c,lw=lw))
ax.text(1,98.3,"Level-by-level electrical schematic: PHI-FOLD 233 head v5 (bottom = ground side)",color=FG,fontsize=18,weight="bold")
B(4,90,40,6.6,"L8  cap + hub-top antenna (HTA)","4-layer D90, 2 x 1.915 turns, about 2.8 uH. 2 leads (twisted pair) -> CB1D JHTA -> 10k + 1n + BAS16 clamps -> mux Y4.\nTX monitor (about 18 V at turn-off before the clamp) and the reference for the adaptive filter.",ACC)
B(4,82.2,40,6.2,"L7  roof plate (passive)","66 light-pipe holes, vents, 8 screw slots, gasket. No electronics; the cap hooks pass the vents.",ACC)
B(4,72,40,8.4,"L6  LB1 display (D78, 4 layers, 0.8 mm, hatched planes)","74AHCT1G125 level shifter (3V3 -> 5 V data), 66 SK6812-class RGB LEDs on one data chain, 11 x 100n + 10u.\nJLB = 4 flat wire pads (no header): +5V, LED_IN, GND, GND. LED budget about 50 mA average (0.25 W).\nBearing from the quad pair -> azimuth; depth class -> ring; noise ring from the consistency residual.",GRN)
B(4,50,40,19.8,"L5  CB1D controller (D78, 6 layers, 61 parts)","Pico 2 W (RP2350 only, radio off): SPI master to the ADCs (SCLK, CS, SDOA1-3, SDOB1-2), PIO capture, BLANK, LED_IN.\nOKI-78SR 5 V (Vin 7-36 V), AMS1117 3V3, 5 A fuse, SMCJ30A TVS on VBUS.\nMONO tap: coil B -> 3 x 110 ohm (R2512, 330 ohm across the coil, 0.33-0.46 W) -> 100n/630 V -> RAW_MONO.\nHTA chain: JHTA -> 10k -> 74HC4051 Y4 (S2 = GP1) -> ADC. Connectors: JPW (VBUS), JTR (handle 7), JPB (neck driver 8),\nJCL (coil leads), JA/JB (analog boards), JHTA, JLB. Firmware: air-template subtraction, adaptive filter on the HTA,\nmatched filter bank tau = t1 x 1.618^n, bearing 0.5 atan2(B,A)+45 deg, ground balance, display frames.",ORG)
B(4,41.2,40,7.2,"L4  absorber cell + L3 septum","Carbonyl-iron silicone absorber; copper-cloth septum (D62 window) with one drain wire to the single star ground.\nSpine flex passes the 16 mm notch. No active parts.",ACC)
B(4,24,40,15.2,"L2  analog cell: AB1T-A and AB1T-B","AB1T-A: 3 channels, each RS 100 ohm -> BAV199 clamp + blank switch (74LVC1G66) -> OPA2211 -> ADS8860 16-bit: QUAD-A, QUAD-B, spare.\nAB1T-B: 2 channels (RS 1 kohm): spare, MONO. REF5041 reference, OPA2365 buffer, +5VA from a ferrite bead.\nJ2 (2x6, 1.27 mm) to CB1D JA/JB: +5VA, GND, +3V3D, SCLK, CS, SDO, BLANK (+ RAW_MONO, VCM on AB1T-B).\nNo copper pour; hatched where a plane is needed.",GRN)
B(4,12,40,10.2,"L1  gallery under the floor","4 twisted pairs (AWG36) from the SB1R pads through the bottom ports: QUAD-A + -> J1.1, - -> J1.4;  QUAD-B + -> J1.2, - -> J1.5.\nSpine flex (rigid-flex tails) rises through the 12 mm floor slot.",ACC)
B(4,2,40,8.6,"L0  base plate + SB1R-Q receive board","SB1R-QA and SB1R-QB: two stacked 4-layer boards, 24 turns/lobe, B = A rotated 45 deg, no pour, immersion silver (no nickel).\n3 M3 screws at r28 into the hub bosses; index key at 0 deg; damping resistors RD1/RD2 680 ohm on the QA top; QB pads at r23 under QA transfer pads.",RED)
# spine bus
ax.add_patch(Rectangle((51,3),0.8,92,fc=ORG,ec="none")); ax.text(51.4,96.2,"SPINE BUS (rigid-flex, 12 mm channel at 90 deg)",color=ORG,fontsize=11,ha="center",weight="bold")
bus=["+5V (VBUS-derived, 4 pins)","+3V3D / +5VA (filtered per board)","GND, GND, GND, GND (single star point)","SCLK, CS, SDOA1-3, SDOB1-2 (SPI/ADC)","BLANK (receive blanking)","RAW_MONO, VCM (to AB1T-B)","LED_IN (to LB1)","HTA reference (to the adaptive filter)"]
for i,b_ in enumerate(bus): ax.text(53,92-i*3.1,b_,color=FG,fontsize=10)
for y_ in (92,74,52,32,16,5): A(44,y_,51,y_,ORG,1.2)
# outside world
B(70,66,28,14,"neck module (outside the head, 0.4 m up)","PB1R TX driver: 2 x 650 V FET, 2 x 100 nF clamp (use ONE 100 nF C0G/film, Vds peak 462 V),\n5k/10 W bleed, shunt, TC4420, LM393 overcurrent. JC (8-way) <-> CB1D JPB; TX pair (AWG12) <-> coil junction + JCL.",ORG)
B(70,48,28,13,"shaft (power + signal ribbons)","Power ribbon: VBUS x3, GND x3 -> CB1D JPW.   Signal ribbon: TRIG, DIAL, P3V3, GND, SHIELD -> CB1D JTR.\nHandle board: passive Hall, dial (no joystick: CB1D-B); battery pod with the quick-swap pack.",ACC)
B(70,30,28,13,"transmit coil + junction (head)","12 litz leads run in the wall-top channel (r45.6-48.6) to the 178 deg exit window -> TXJ1 board in the bridge\n(6 A + 6 B soldered to two bus bars) -> AWG12 TX pair; AWG22 taps -> CB1D JCL.",RED)
A(44,56,70,72,ORG); A(44,60,70,54,ACC); A(44,52,70,37,RED)
B(70,10,28,16,"protection and ratings (computed)","Vds peak 462 V vs 650 V FET (29% margin); CL caps 630 V vs about 436 V; RCL1 3.8-4.7 W of 10 W;\ndamping chain 0.46 W in the vault; vault 1.13 W -> 34 C at 25 C ambient;\nRX input leak 0.01-10 mV (quad, real copper) vs 0.6 V (figure-8 off 0.5 mm); VBUS drop 0.49 V at 2 A.",GRN)
plt.savefig("kit_v22/LEVELS_SCHEMATIC.png",dpi=58,facecolor=BG); print("ok")
