import json, math, heapq, time, os
import numpy as np
from scipy import ndimage as ndi
GR=0.15
def disk(r): y,x=np.ogrid[-r:r+1,-r:r+1]; return (x*x+y*y)<=r*r+0.5
class Router:
    def __init__(s,pads_json,layers,planes,widths,hv=(),clr=0.2,hv_clr=1.0,via_pad=0.6,via_drill=0.3,default_w=0.2,edge_clr=0.5):
        d=json.load(open(pads_json)); s.R=d["R"]; s.pads=d["pads"]; s.layers=layers; s.nl=len(layers); s.planes=planes; s.widths=widths; s.hv=set(hv); s.clr=clr; s.hv_clr=hv_clr; s.via_pad=via_pad; s.via_drill=via_drill; s.dw=default_w; s.edge=edge_clr
        s.off=s.R+1.0; s.N=int(2*s.off/GR)+1
        names=sorted({p["net"] for p in s.pads if p["net"]}); s.nid={n:i+1 for i,n in enumerate(names)}; s.nid[None]=0
        s.own=np.zeros((s.nl,s.N,s.N),np.int32); yy,xx=np.mgrid[0:s.N,0:s.N]; s.rad=np.hypot((xx*GR-s.off),(yy*GR-s.off))
        # distance of each cell to the board edge (positive inside): a circle of radius R for the discs, a W x H rectangle when pads.json carries "rect" (PB1R)
        s.edged=(np.minimum(d['rect'][0]/2-np.abs(xx*GR-s.off),d['rect'][1]/2-np.abs(yy*GR-s.off)) if d.get('rect') else s.R-s.rad)
        s.padcells=[]; s.tracks=[]; s.vias=[]; s.fail=[]; s.unnet=1000; s.finem=np.zeros((s.nl,s.N,s.N),bool)
        for k,p in enumerate(s.pads):
            nid=s.nid[p["net"]] if p["net"] else s.unnet+k
            m=s.rast(p); lays=range(s.nl) if p["tht"] else [0]
            for l in lays:
                s.own[l][m]=nid
                if p.get("fine"): s.finem[l]|=m
            cells=np.argwhere(m); s.padcells.append((nid,cells,list(lays)))
        s.finez=ndi.binary_dilation(s.finem.any(axis=0),structure=disk(10)) if s.finem.any() else np.zeros((s.N,s.N),bool)   # 1.5 mm zone around fine-pitch pads
        s.stats={}
    def rast(s,p):
        m=np.zeros((s.N,s.N),bool); r0,c0=s.cell(p["x"],p["y"]); hw=int(math.ceil(p["w"]/2/GR)); hh=int(math.ceil(p["h"]/2/GR))
        if p.get("fine"):          # fine-pitch pads (LIB "fine": 0.5 mm LGA): only the cells whose centres lie in the pad (ceil inflates a 0.25 pad to 0.45 and closes the gaps);
            hw=int(math.floor(p["w"]/2/GR+1e-9)); hh=int(math.floor(p["h"]/2/GR+1e-9))   # the true clearance is proved by drc.py and KiCad DRC on the exported copper
        if p["shape"]=="circle": rr=int(math.ceil(p["w"]/2/GR)); m[r0-rr:r0+rr+1,c0-rr:c0+rr+1]|=disk(rr)
        else: m[max(0,r0-hh):r0+hh+1,max(0,c0-hw):c0+hw+1]=True
        return m
    def cell(s,x,y): return int(round((y+s.off)/GR)),int(round((x+s.off)/GR))
    def xy(s,r,c): return (c*GR-s.off,r*GR-s.off)
    def halfw(s,net): return s.widths.get(net,s.dw)/2
    def masks(s,nid,net):
        hw=s.halfw(net); ishv=net in s.hv; blk=[]; viablk=np.zeros((s.N,s.N),bool)
        for l in range(s.nl):
            o=s.own[l]; others=(o!=0)&(o!=nid); hvm=np.zeros_like(others)
            for h in s.hv:
                if h in s.nid and s.nid[h]!=nid: hvm|=(o==s.nid[h])
            rc=int(math.ceil((s.clr+hw)/GR)); b=ndi.binary_dilation(others&~s.finez,structure=disk(rc))
            # in the zone around fine-pitch pads (finez: 1.5 mm) the halo of all copper is the exact cell count: ceil((0.2+0.1)/0.15) is 3 in floating point
            # (0.45 mm) and seals a 0.5 mm-pitch middle pad and its neighbours' stubs; elsewhere the old (conservative) halo, so boards without fine pads route as before
            if s.finez.any(): b|=ndi.binary_dilation(others&s.finez,structure=disk(int(math.ceil((s.clr+hw)/GR-1e-9))))
            rh=int(math.ceil(((s.hv_clr if (ishv or True) else s.clr)+hw)/GR))
            if ishv: b=ndi.binary_dilation(others,structure=disk(rh))
            else: b|=ndi.binary_dilation(hvm,structure=disk(rh))
            b|=(s.edged<s.edge+hw)
            blk.append(b)
            rv=int(math.ceil((s.clr+s.via_pad/2)/GR)); vb=ndi.binary_dilation(others&~s.finez,structure=disk(rv)) if not ishv else ndi.binary_dilation(others,structure=disk(int(math.ceil((s.hv_clr+s.via_pad/2)/GR))))
            if not ishv and s.finez.any(): vb|=ndi.binary_dilation(others&s.finez,structure=disk(int(math.ceil((s.clr+s.via_pad/2)/GR-1e-9))))
            if not ishv and len(hvm.nonzero()[0]): vb|=ndi.binary_dilation(hvm,structure=disk(int(math.ceil((s.hv_clr+s.via_pad/2)/GR))))
            viablk|=vb
        viablk|=(s.edged<s.edge+s.via_pad/2)
        for l in range(s.nl): viablk|=False
        return blk,viablk
    def astar(s,sources,goal_set,goal_fn,blk,viablk,nid):
        N=s.N; nl=s.nl; B=[b.astype(np.uint8).ravel().tobytes() for b in blk]; V=viablk.astype(np.uint8).ravel().tobytes()
        heap=[]; g={}; par={}
        for idx in sources: g[idx]=0.0; heapq.heappush(heap,(0.0,0.0,idx))
        nb=[(-1,0,1.0),(1,0,1.0),(0,-1,1.0),(0,1,1.0),(-1,-1,1.414),(-1,1,1.414),(1,-1,1.414),(1,1,1.414)]
        gx=None; gl=None
        if goal_set: gl=list(goal_set)[:50]; gr=[(i//N)%N for i in gl]; gc=[i%N for i in gl]
        pops=0
        while heap:
            f,gc0,idx=heapq.heappop(heap)
            if gc0>g.get(idx,1e18)+1e-9: continue
            pops+=1
            if (goal_set and idx in goal_set) or (goal_fn and goal_fn(idx)): 
                path=[idx]
                while idx in par: idx=par[idx]; path.append(idx)
                return path[::-1]
            if pops>900000: return None
            l=idx//(N*N); rem=idx%(N*N); r=rem//N; c=rem%N
            for dr,dc,cost in nb:
                r2=r+dr; c2=c+dc
                if r2<0 or c2<0 or r2>=N or c2>=N: continue
                if B[l][r2*N+c2]: continue
                if dr and dc and (B[l][r*N+c2] or B[l][r2*N+c]): continue
                i2=l*N*N+r2*N+c2; ng=gc0+cost
                if ng<g.get(i2,1e18)-1e-9:
                    g[i2]=ng; par[i2]=idx
                    h=0.0
                    if goal_set and gl is not None:
                        h=min(max(abs(r2-a),abs(c2-b))+0.414*min(abs(r2-a),abs(c2-b)) for a,b in zip(gr,gc)) if len(gl)<=3 else 0.0
                    heapq.heappush(heap,(ng+h,ng,i2))
            if not V[r*N+c]:
                for l2 in range(nl):
                    if l2==l or B[l2][r*N+c]: continue
                    i2=l2*N*N+r*N+c; ng=gc0+10.0
                    if ng<g.get(i2,1e18)-1e-9: g[i2]=ng; par[i2]=idx; heapq.heappush(heap,(ng,ng,i2))
        return None
    def mark(s,path,nid,net):
        N=s.N; hwc=max(0,int(round(s.halfw(net)/GR))); out=[]; cur=[]; lay=None; vcount=0
        cells=[(i//(N*N),(i//N)%N,i%N) for i in path]
        for k,(l,r,c) in enumerate(cells):
            m=disk(hwc) if hwc>0 else np.ones((1,1),bool)
            a=s.own[l]; r0=max(0,r-hwc); r1=min(N,r+hwc+1); c0=max(0,c-hwc); c1=min(N,c+hwc+1); sub=m[(r0-(r-hwc)):(r1-(r-hwc)),(c0-(c-hwc)):(c1-(c-hwc))]; reg=a[r0:r1,c0:c1]; reg[sub&(reg==0)]=nid
            if k>0 and cells[k-1][0]!=l:
                x,y=s.xy(r,c); s.vias.append((x,y,net)); vr=int(math.ceil(s.via_pad/2/GR))
                for L in range(s.nl):
                    ar=s.own[L]; vm=disk(vr); rr0=max(0,r-vr); rr1=min(N,r+vr+1); cc0=max(0,c-vr); cc1=min(N,c+vr+1); sub2=vm[(rr0-(r-vr)):(rr1-(r-vr)),(cc0-(c-vr)):(cc1-(c-vr))]; reg2=ar[rr0:rr1,cc0:cc1]; reg2[sub2&(reg2==0)]=nid
        # polylines per layer, merging collinear steps
        seg=None
        for k,(l,r,c) in enumerate(cells):
            x,y=s.xy(r,c)
            if seg is None or seg["layer"]!=s.layers[l]:
                if seg: out.append(seg)
                seg=dict(net=net,layer=s.layers[l],width=s.widths.get(net,s.dw),pts=[(x,y)])
                if k>0 and cells[k-1][0]!=l: seg["pts"]=[s.xy(cells[k-1][1],cells[k-1][2]),(x,y)] if False else [(x,y)]
            else:
                p=seg["pts"]
                if len(p)>=2 and abs((p[-1][0]-p[-2][0])*(y-p[-1][1])-(p[-1][1]-p[-2][1])*(x-p[-1][0]))<1e-9: p[-1]=(x,y)
                else: p.append((x,y))
        if seg: out.append(seg)
        s.tracks+=out
    def route_net(s,net,pad_idx,planes_stub=False):
        nid=s.nid[net]; blk,viablk=s.masks(nid,net); N=s.N
        pcs=[(k,s.padcells[k]) for k in pad_idx]
        def flat(cells,lays): return {l*N*N+int(r)*N+int(c) for l in lays for r,c in cells}
        pad_sets=[flat(c,lays) for _,(_,c,lays) in pcs]
        if len(pcs)<2: return True
        tree=set(pad_sets[0]); remaining=list(range(1,len(pcs))); ok=True
        while remaining:
            goal=set().union(*[pad_sets[i] for i in remaining]); path=s.astar(tree,goal,None,blk,viablk,nid)
            if path is None: ok=False; break
            s.mark(path,nid,net); tree|=set(path)
            hit=[i for i in remaining if path[-1] in pad_sets[i]]; remaining=[i for i in remaining if i not in hit]
            blk,viablk=s.masks(nid,net)
        return ok
    def plane_stub(s,net,k):
        nid=s.nid[net]; blk,viablk=s.masks(nid,net); N=s.N; _,cells,lays=s.padcells[k]; p=s.pads[k]
        if p["tht"]: return True
        src={int(r)*N+int(c) for r,c in cells}; r0,c0=s.cell(p["x"],p["y"]); minr=int(math.ceil((max(p["w"],p["h"])/2+0.45)/GR))
        V=viablk
        def goal(i):
            if i>=N*N: return False
            r=i//N; c=i%N; return (not V[r,c]) and max(abs(r-r0),abs(c-c0))>=minr
        path=s.astar(src,None,goal,blk,viablk,nid)
        if path is None: return False
        r=path[-1]//N; c=path[-1]%N; vr=(path[-1]//(N*N)); s.mark(path,nid,net)
        x,y=s.xy(r,c); s.vias.append((x,y,net)); vr=int(math.ceil(s.via_pad/2/GR))
        for L in range(s.nl):
            m=disk(vr); a=s.own[L]; rr0=max(0,r-vr); rr1=min(N,r+vr+1); cc0=max(0,c-vr); cc1=min(N,c+vr+1); sub=m[(rr0-(r-vr)):(rr1-(r-vr)),(cc0-(c-vr)):(cc1-(c-vr))]; reg=a[rr0:rr1,cc0:cc1]; reg[sub&(reg==0)]=nid
        return True
    def run(s,budget=240.0,state=None):
        import pickle
        t0=time.time()
        if state and os.path.exists(state):
            z=pickle.load(open(state,"rb")); s.own=z["own"]; s.tracks=z["tracks"]; s.vias=z["vias"]; s.fail=z["fail"]; s.done=z["done"]; s.stub_done=z["stub_done"]
        else: s.done=set(); s.stub_done=set()
        bynet={}
        for k,p in enumerate(s.pads):
            if p["net"]: bynet.setdefault(p["net"],[]).append(k)
        def save():
            if state: pickle.dump(dict(own=s.own,tracks=s.tracks,vias=s.vias,fail=s.fail,done=s.done,stub_done=s.stub_done),open(state,"wb"))
        # learned stub-first pads (opt-in, AU1 reorder rounds): plane stubs of pads whose stub failed in an earlier round go before everything else
        for k in range(len(s.pads)):
            p_ = s.pads[k]
            if p_["net"] in s.planes and (p_["ref"] + "." + p_["num"]) in getattr(s, "stub_first", set()) and k not in s.stub_done:
                if not s.plane_stub(p_["net"], k): s.fail.append((p_["net"], "stub", p_["ref"] + "." + p_["num"]))
                s.stub_done.add(k)
        # nets on fine-pitch pads go before the plane stubs: a stub from the neighbouring pad otherwise takes the only escape of a 0.5 mm-pitch middle pad
        # (boards without fine pads: no such net, order unchanged)
        _fine = {s.pads[k]["net"] for k in range(len(s.pads)) if s.pads[k].get("fine") and s.pads[k]["net"] and s.pads[k]["net"] not in s.planes and not s.pads[k]["net"].endswith("_NC")}
        if getattr(s, "fine_order", "alpha") == "span":     # opt-in (AU1): priority nets first, then the shortest; default alphabetical keeps CB1D's route unchanged
            _sp = lambda n: (lambda ks: (max(s.pads[k]["x"] for k in ks) - min(s.pads[k]["x"] for k in ks)) + (max(s.pads[k]["y"] for k in ks) - min(s.pads[k]["y"] for k in ks)))(bynet[n])
            _fine = sorted(_fine, key=lambda n: (0 if n in getattr(s, "priority", []) else 1, _sp(n)))
        else: _fine = sorted(_fine)
        for net in _fine:
            if net in s.done or len(bynet[net]) < 2: continue
            ok=s.route_net(net,bynet[net]); s.done.add(net)
            if not ok: s.fail.append((net,"net",len(bynet[net])))
        for net in s.planes:
            if net in bynet:
                for k in bynet[net]:
                    if k in s.stub_done: continue
                    if time.time()-t0>budget: save(); return dict(finished=False,done=len(s.done),stubs=len(s.stub_done))
                    if not s.plane_stub(net,k): s.fail.append((net,"stub",s.pads[k]["ref"]+"."+s.pads[k]["num"]))
                    s.stub_done.add(k)
        def span(ks): xs=[s.pads[k]["x"] for k in ks]; ys=[s.pads[k]["y"] for k in ks]; return (max(xs)-min(xs))+(max(ys)-min(ys))
        order=sorted([n for n in bynet if n not in s.planes and len(bynet[n])>=2 and not n.endswith("_NC")],key=lambda n:(0 if n in s.hv else (1 if n in getattr(s,'priority',[]) else (2 if s.widths.get(n,s.dw)>0.3 else 3)),(getattr(s,'priority',[]).index(n) if n in getattr(s,'priority',[]) else span(bynet[n]))))
        for n in order:
            if n in s.done: continue
            if time.time()-t0>budget: save(); return dict(finished=False,done=len(s.done),of=len(order),stubs=len(s.stub_done))
            ok=s.route_net(n,bynet[n]); s.done.add(n)
            if not ok: s.fail.append((n,"net",len(bynet[n])))
        save(); s.stats=dict(finished=True,nets_to_route=len(order),nets_routed=len(order)-len([f for f in s.fail if f[1]=="net"]),plane_nets=list(s.planes),failures=s.fail,tracks=len(s.tracks),vias=len(s.vias))
        return s.stats
    def length(s): return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for t in s.tracks for a,b in zip(t["pts"][:-1],t["pts"][1:]))
