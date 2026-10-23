import math, csv, json, numpy as np
from render_v6 import render, load_stl, box, cyl, clip_y
GOLD=137.50776405
def tr(S,d): return (S[0]+np.asarray(d,float),S[1])
def rotz(S,deg):
    c,s=math.cos(math.radians(deg)),math.sin(math.radians(deg)); return (S[0]@np.array([[c,-s,0],[s,c,0],[0,0,1]]).T,S[1])
def roty(S,deg,c=(0,0,0)):                         # rotation about the y axis through c; z -> (sin, 0, cos)
    ps=math.radians(deg); M=np.array([[math.cos(ps),0,math.sin(ps)],[0,1,0],[-math.sin(ps),0,math.cos(ps)]]); c=np.asarray(c,float); return ((S[0]-c)@M.T+c,S[1])
def PT(S,c,a=1.0,name=""): return dict(V=np.asarray(S[0],float),F=np.asarray(S[1]),c=c,a=a,name=name)
def clipall(P,y0=0.0):
    out=[]
    for p in P:
        V,F=clip_y((p["V"],p["F"]),y0)
        if len(F): out.append(dict(p,V=V,F=F))
    return out
def merge(L):
    V=[];F=[];o=0
    for v,f in L: V.append(v); F.append(f+o); o+=len(v)
    return (np.vstack(V),np.vstack(F)) if V else (np.zeros((0,3)),np.zeros((0,3),int))
def seg_box(p0,p1,wdir,width,thick):
    p0=np.asarray(p0,float);p1=np.asarray(p1,float); ax=p1-p0; L=np.linalg.norm(ax); ex=ax/L; wd=np.asarray(wdir,float); wd=wd-ex*(wd@ex); ey=wd/np.linalg.norm(wd); ez=np.cross(ex,ey)
    V,F=box(0,0,0,L,width,thick); V=(p0+p1)/2+np.outer(V[:,0],ex)+np.outer(V[:,1],ey)+np.outer(V[:,2],ez); return V,F
def tube_poly(pts,r,n=6):
    L=[]
    for a,b in zip(pts[:-1],pts[1:]):
        if np.linalg.norm(np.asarray(b)-np.asarray(a))>1e-6: L.append(cyl(a,b,r,n))
    return merge(L)
def disc(r,z0,z1,n=96,cx=0,cy=0): return cyl((cx,cy,z0),(cx,cy,z1),r,n)
def stl(p): return load_stl(p)
# ---- colours
COL=dict(petg=(0.62,0.66,0.78),hub=(0.55,0.58,0.68),cup=(0.90,0.92,0.97),skirt=(0.86,0.90,0.96),base=(0.42,0.50,0.60),hood=(0.64,0.68,0.80),tile=(0.10,0.10,0.12),cap=(0.92,0.92,0.96),pcb=(0.04,0.38,0.24),
 copper=(0.86,0.52,0.26),pipe=(1.0,0.96,0.62),ic=(0.08,0.08,0.10),cap_c=(0.78,0.62,0.36),res=(0.14,0.14,0.16),conn=(0.95,0.92,0.72),mod=(0.18,0.34,0.72),pico=(0.10,0.52,0.36),fuse=(0.88,0.78,0.42),diode=(0.10,0.10,0.13),
 cfrp=(0.16,0.17,0.20),gfrp=(0.80,0.78,0.52),ribP=(0.88,0.20,0.20),ribS=(0.20,0.40,0.90),ribJ=(0.20,0.70,0.35),tx=(0.95,0.60,0.10),bat=(0.25,0.55,0.30),yellow=(0.95,0.80,0.20))
LAYER=[None,(0.20,0.68,0.70),(0.33,0.60,0.88),(0.55,0.52,0.92),(0.76,0.48,0.86),(0.92,0.48,0.68),(0.96,0.62,0.42)]
def comp_color(typ,val=""):
    t=typ.upper()
    if t.startswith("R"): return COL["res"]
    if t.startswith("C") and t not in ("CAPD","CAN10"): return COL["cap_c"]
    if t in ("CAPD","CAN10"): return (0.30,0.30,0.34)
    if t.startswith("D"): return COL["diode"]
    if t.startswith("FUSE"): return COL["fuse"]
    if t.startswith("FB"): return (0.25,0.25,0.28)
    if t.startswith(("TERM","HDR","WIRE")): return COL["conn"]
    if t=="PICO": return COL["pico"]
    if t=="OKI3": return COL["mod"]
    if t=="LED2020": return (0.96,0.96,0.96)
    return COL["ic"]
def board_parts(prefix,pp,bom,libjson,z_top,rot180=False,board_r=39.0,thick=1.6,led_colors=None,y_sign=1):
    lib=json.load(open(libjson)); typ={}
    for r in list(csv.reader(open(bom)))[1:]:
        for ref in r[1].split(","): typ[ref.strip()]=r[2]
    out=[PT(disc(board_r,z_top-thick,z_top),COL["pcb"],1.0,prefix+" board")]
    for r in csv.DictReader(open(pp)):
        ref=r["Ref"]; t=typ.get(ref)
        if t is None or t not in lib: continue
        bw,bh,bz=lib[t]; x,y,rot=float(r["PosX_mm"]),float(r["PosY_mm"]),float(r["Rot"])
        if int(rot)%180==90: bw,bh=bh,bw
        if rot180: x,y=-x,-y
        col=comp_color(t)
        if t=="LED2020" and led_colors: col=led_colors(ref)
        out.append(PT(box(x,y,z_top+bz/2,bw,bh,bz),col,1.0,prefix+" "+ref+" "+t))
    return out
def lib_bodies():
    import subprocess, os
    d={}
    for pw in ("C","L"):
        code="import os,json;import pw_design as D;print(json.dumps({k:v['body'] for k,v in D.LIB.items()}))"
        o=subprocess.run(["python3","-c",code],capture_output=True,text=True,env=dict(os.environ,PW=pw,DISC="1"),cwd="/home/claude").stdout.strip().splitlines()[-1]
        d.update(json.loads(o))
    json.dump(d,open("/home/claude/kit_v19/lib_bodies.json","w")); return d
