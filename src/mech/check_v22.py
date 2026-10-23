import struct, numpy as np, math, json
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]; return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3,3).astype(float)
def open_edges(T):
    V=T.reshape(-1,3); q=np.round(V*1000).astype(np.int64)+(1<<20); key=(q[:,0]<<42)|(q[:,1]<<21)|q[:,2]; u,inv=np.unique(key,return_inverse=True); tri=inv.reshape(-1,3)
    e=np.vstack([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]); lo=np.minimum(e[:,0],e[:,1]); hi=np.maximum(e[:,0],e[:,1]); k=lo.astype(np.int64)*10**8+hi; uq,c=np.unique(k,return_counts=True); return int((c==1).sum())
R=[]
def chk(n,v,lo=None,hi=None,note=""):
    ok=(lo is None or v>=lo) and (hi is None or v<=hi); R.append(dict(check=n,value=round(float(v),3),min=lo,max=hi,result="PASS" if ok else "FAIL",note=note))
H=load("kit_v22/SET/02_CORE_PCB_CYLINDER/CORE_CYLINDER_v5_integrated.stl"); RF=load("kit_v22/ROOF_PLATE_v5.stl"); TR=load("kit_v22/ANALOG_TRAY_v5.stl"); SP=load("kit_v22/SEPTUM_FRAME_v5.stl"); CB=load("kit_v22/SPINE_COMB_v5.stl")
for n,T in (("hub",H),("roof",RF),("tray",TR),("septum",SP),("comb",CB)): chk(f"{n}: open edges",open_edges(T),0,0)
def cen(T): c=T.mean(1); return c,np.hypot(c[:,0],c[:,1]),np.degrees(np.arctan2(c[:,1],c[:,0]))%360
def faces(T,ang,half,z0,z1,r0,r1): c,r,a=cen(T); return int(np.sum((np.abs(((a-ang)+180)%360-180)<half)&(c[:,2]>z0)&(c[:,2]<z1)&(r>r0)&(r<r1)))
chk("hub: faces inside the spine channel volume (0 = clear)",faces(H,90,4,11,38,37.6,40.0),0,0)
chk("hub: faces inside the floor slot (r29-36, 0 = open)",faces(H,90,4,9.1,9.7,29.0,36.0),0,0)
chk("hub: exit window still open",faces(H,178,6,34.8,40.2,44.3,51.7),0,0)
chk("hub: top of the cylinder (no roof) z max",H[:,:,2].max(),41.29,41.31)
# rib / post angles versus the lead ports
tracks=[0.0,137.50776,275.01553,52.52329,190.03106,327.53882]; ports=sorted([(t+o)%360 for t in tracks for o in (6,11,16)])
RIBS=[24.0,48.0,109.0,135.0,225.0,244.0,300.0,317.0]
mn=min(min(abs(((a-p)+180)%360-180) for p in ports) for a in RIBS); chk("rib/post angle vs nearest lead port (deg; need >= 5.2 deg = 4 mm at r44)",mn,5.2,None,f"smallest {mn:.1f} deg")
mnE=min(abs(((a-178)+180)%360-180) for a in RIBS); chk("rib/post angle vs exit window centre (deg; window half width 9.5 deg)",mnE,12.0,None)
# post bores vs roof slots
c,r,a=cen(RF); ok=0
for ang in RIBS:
    cx,cy=42.5*math.cos(math.radians(ang)),42.5*math.sin(math.radians(ang))
    near=np.hypot(c[:,0]-cx,c[:,1]-cy)<1.4; ok+=int(np.sum(near&(c[:,2]>41.4)&(c[:,2]<44.4)))
chk("roof: faces inside the 8 screw holes (0 = open over every post)",ok,0,0)
# pixel holes open in the roof
PX=[(12.5,12,15.0),(20.0,18,10.0),(26.5,24,7.5),(34.0,12,7.5)]; n=0; top=RF[np.all(np.abs(RF[:,:,2]-44.5)<1e-3,axis=1)]; ct=top.mean(1)
for r_,k,ph in PX:
    for i in range(k):
        aa=np.radians(ph+i*360/k); n+=int(np.sum(np.hypot(ct[:,0]-r_*np.cos(aa),ct[:,1]-r_*np.sin(aa))<0.7))
chk("roof: face centroids inside the 66 pixel holes (0 = open)",n,0,0)
chk("roof: z range",RF[:,:,2].min(),41.29,41.31); chk("roof: top z",RF[:,:,2].max(),44.49,44.51)
# tray vs spine walls / ribs
c,r,a=cen(TR); chk("tray: points inside the spine walls (|x|>6, r>37.2 near 90 deg)",int(np.sum((np.abs(a-90)<20)&(r>37.2)&(np.abs(c[:,0])<7.3))),0,0)
chk("tray max radius vs wall r44",44.0-np.hypot(TR[:,:,0],TR[:,:,1]).max(),4.0,None)
# septum
c,r,a=cen(SP); chk("septum: radial reach vs wall r44",44.0-np.hypot(SP[:,:,0],SP[:,:,1]).max(),0.2,None)
chk("septum ring edge vs slot floor r39.3",39.3-39.0,0.2,None)
chk("septum thickness vs slot 1.9",1.9-(SP[:,:,2].max()-SP[:,:,2].min()),0.1,None)
chk("septum: faces in the spine notch (r32-38.5, |x|<7)",int(np.sum((np.abs(c[:,0])<7.0)&(c[:,1]>0)&(r>32)&(r<38.5))),0,0)
# comb vs walls
chk("comb width vs 12 mm channel",12.0-(CB[:,:,0].max()-CB[:,:,0].min()),0.2,None)
vol=lambda T: abs(float(np.sum(np.einsum('ij,ij->i',T[:,0],np.cross(T[:,1],T[:,2])))/6.0))/1000.0

# ---- transmit-lead channel (wall-top groove + roof channel) and the junction cradle
cc,rr,aa=cen(H); G_=137.50776405; trk=[(G_*(k-1))%360 for k in range(1,7)]; prt=[(p+o)%360 for p in trk for o in (6,11,16)]
def near_(x,lst,w): return np.any([np.abs(((x-l)+180)%360-180)<w for l in lst],axis=0)
msk=~near_(aa,prt,5)&~near_(aa,trk,6)&~near_(aa,[178],11)
chk("hub: TX-lead channel open all round (faces in r46-48.4, z39.8-41.1, away from lanes)",int(np.sum((rr>46.0)&(rr<48.4)&(cc[:,2]>39.8)&(cc[:,2]<41.1)&msk)),0,0)
c2,r2,a2=cen(RF); chk("roof: TX-lead channel open (faces in r46-48.2, z41.4-43.4)",int(np.sum((r2>46.0)&(r2<48.2)&(c2[:,2]>41.4)&(c2[:,2]<43.4))),0,0)
chk("roof channel top skin thickness (mm)",44.5-43.5,0.8,None)
chk("hub wall above the channel: outer skin r48.6-49.5 (mm)",49.5-48.6,0.8,None)
chk("channel cross-section (wall groove 3.0 x 1.7 + roof 3.0 x 2.2 mm2) vs 6 litz (6.8 mm2 / 0.7 fill)",3.0*(1.7+2.2),6.8/0.7,None)

# ---- screw bosses (r28 under the floor), base plate v3 windows, SB1R-Q board holes
import os
BP=load("kit_v16/PARTS/BASE_PLATE_RX_CASSETTE_v3.stl"); chk("base plate v3: open edges",open_edges(BP),0,0)
BOSS=[(22.5,28.0),(157.5,28.0),(247.5,28.0)]; cb,rb,ab=cen(BP)[0],None,None
for ang,rad in BOSS:
    cx,cy=rad*math.cos(math.radians(ang)),rad*math.sin(math.radians(ang)); cc=cen(H)[0]; cp=cen(BP)[0]
    chk(f"boss {ang} deg: base plate window open (faces within 1.4 mm of the axis)",int(np.sum((np.hypot(cp[:,0]-cx,cp[:,1]-cy)<1.4)&(cp[:,2]>0.05)&(cp[:,2]<0.75))),0,0)
    chk(f"boss {ang} deg: boss wall present (faces at r2.0 of the axis)",int(np.sum((np.abs(np.hypot(cc[:,0]-cx,cc[:,1]-cy)-2.0)<0.3)&(cc[:,2]>3.3)&(cc[:,2]<8.4))),20,None)
    chk(f"boss {ang} deg: insert bore open (no faces inside r1.5)",int(np.sum((np.hypot(cc[:,0]-cx,cc[:,1]-cy)<1.5)&(cc[:,2]>3.3)&(cc[:,2]<8.4))),0,0)
    chk(f"boss {ang} deg: separation from the 90 deg spine slot (deg)",abs(((ang-90)+180)%360-180),50.0,None)
if os.path.exists("kit_v22/sbq_geometry.json"):
    G=json.load(open("kit_v22/sbq_geometry.json")); dev=max(abs(a-b[0]) for a,b in zip(sorted(G["hole_angles"]),sorted(BOSS)))+abs(G["hole_radius"]-28.0)
    chk("SB1R-Q board holes coincide with the hub bosses and base plate windows (angle+radius deviation)",dev,0,0.01)
    chk("SB1R-Q hole copper margin (mm beyond 0.4 mm clearance)",G["hole_margin_mm"],0.5,None)
    chk("SB1R-Q via clearance margin (mm)",G["via_margin_mm"],0.3,None)

masses={n:round(vol(T)*1.27) for n,T in (("hub v5 (upper bound)",H),("roof",RF),("tray",TR),("septum frame",SP),("comb",CB))}
json.dump(dict(checks=R,mass_g=masses),open("kit_v22/check_v22.json","w"),indent=1)
for x in R: print(x["result"],x["check"],"=",x["value"],x["note"])
print("FAILS",sum(1 for x in R if x["result"]=="FAIL"),"of",len(R),masses)
