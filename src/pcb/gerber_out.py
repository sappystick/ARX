import json, math, os, sys
import numpy as np
def export(pads_json,route_json,outdir,prefix,via_pad=0.6,via_drill=0.3,hatch=False,notch=None,hv=(),hv_clr=1.0):
    os.makedirs(outdir,exist_ok=True); d=json.load(open(pads_json)); r=json.load(open(route_json)); R=d["R"]; pads=d["pads"]; layers=r["layers"]; planes=r["planes"]
    pl_layers={}; hv=set(hv)
    # plane anti-pads: 0.3 mm around ordinary through-hole pads and vias, hv_clr (1.0 mm, CLAUDE.md rule 6) around pads and vias of the flyback nets (the writer used a fixed 0.3 mm for every net before)
    ap_pad=lambda p:max(p['w'],p['h'])+(2*hv_clr if p['net'] in hv else 0.6); ap_via=lambda nn:via_pad+(2*hv_clr-0.0 if nn in hv else 0.5)
    for n_,l_ in planes.items():
        for ly_ in (l_ if isinstance(l_,list) else [l_]): pl_layers[ly_]=n_
    all_layers=[l for l in ["F.Cu","In1.Cu","In2.Cu","In3.Cu","In4.Cu","B.Cu"] if l in layers or l in pl_layers]; fl=lambda x:"%d"%round(x*1e6)
    class Ap:
        def __init__(s): s.tab={}; s.n=10
        def get(s,kind,w,h=None):
            k=(kind,round(w,3),round(h if h else w,3))
            if k not in s.tab: s.tab[k]=s.n; s.n+=1
            return s.tab[k]
        def defs(s): return [f"%ADD{n}{'C' if k[0]=='C' else 'R'},{k[1]:.3f}{'' if k[0]=='C' else 'X%.3f'%k[2]}*%" for k,n in s.tab.items()]
    def write(name,body_fn):
        ap=Ap(); body=[]; body_fn(ap,body)
        L=["G04 PHI-FOLD 233 %s %s*"%(prefix,name),"%FSLAX46Y46*%","%MOMM*%"]+ap.defs()+["G75*","%LPD*%"]+body+["M02*"]; open(f"{outdir}/{prefix}-{name}.gbr","w").write("\n".join(L)+"\n")
    def flash(body,ap,kind,w,h,x,y): body+= [f"D{ap.get(kind,w,h)}*",f"X{fl(x)}Y{fl(-y)}D03*"]
    def stroke(body,ap,w,pts):
        body.append(f"D{ap.get('C',w)}*"); body.append(f"X{fl(pts[0][0])}Y{fl(-pts[0][1])}D02*")
        for p in pts[1:]: body.append(f"X{fl(p[0])}Y{fl(-p[1])}D01*")
    def padflash(body,ap,p,grow=0.0): flash(body,ap,"C" if p["shape"]=="circle" else "R",p["w"]+grow,p["h"]+grow,p["x"],p["y"])
    def copper(layer):
        def fn(ap,body):
            for p in pads:
                if p["tht"] or layer=="F.Cu": 
                    if layer=="F.Cu" or p["tht"]: padflash(body,ap,p)
            for t in r["tracks"]:
                if t["layer"]==layer and len(t["pts"])>=2: stroke(body,ap,t["width"],t["pts"])
                elif t["layer"]==layer and len(t["pts"])==1: flash(body,ap,"C",t["width"],t["width"],*t["pts"][0])
            for (x,y,n) in r["vias"]: flash(body,ap,"C",via_pad,via_pad,x,y)
        return fn
    # planes keep the fabrication edge floor (dru_gen.GEN["edge"], 0.5 mm) from the round edge AND from the notch: before Step 5 they were clipped to a circle only
    # (hatch copper reached R - 0.1 mm and 12-16 mm2 of it lay inside the notch; gerber_edge_check.py reads the files back)
    import dru_gen; EDGE=dru_gen.GEN["edge"]+0.05
    def clear_notch(ap,body):
        if notch is None: return
        s=notch; w=7.6+EDGE; y0=s*(36.5-EDGE); y1=s*(R+1.0)
        body.append("%LPC*%"); body.append("G36*"); body.append(f"X{fl(-w)}Y{fl(-y0)}D02*")      # board y-down -> Gerber y-up, as stroke() and flash()
        for (x,y) in ((w,y0),(w,y1),(-w,y1),(-w,y0)): body.append(f"X{fl(x)}Y{fl(-y)}D01*")
        body.append("G37*"); body.append("%LPD*%")
    def plane(net):
        def fn(ap,body):
            if hatch:
                pitch=1.6; w=0.4; rr=R-EDGE-w/2
                for v in np.arange(-rr+0.4,rr-0.3,pitch):
                    x=math.sqrt(max(rr*rr-v*v,0.0)); stroke(body,ap,w,[(-x,v),(x,v)]); stroke(body,ap,w,[(v,-x),(v,x)])
                for (x,y,nn) in r["vias"]:
                    if nn==net: flash(body,ap,"C",1.6,None,x,y)
                for p in pads:
                    if p["tht"] and p["net"]==net: flash(body,ap,"C",max(p["w"],p["h"])+0.2,None,p["x"],p["y"])
                body.append("%LPC*%")
                for p in pads:
                    if p["tht"] and p["net"]!=net: flash(body,ap,"C",ap_pad(p),None,p["x"],p["y"])
                for (x,y,nn) in r["vias"]:
                    if nn!=net: flash(body,ap,"C",ap_via(nn),None,x,y)
                body.append("%LPD*%"); clear_notch(ap,body); return
            n=360; ang=np.linspace(0,2*math.pi,n,endpoint=False); body.append("G36*"); 
            body.append(f"X{fl((R-EDGE)*1)}Y{fl(0)}D02*")
            for a in ang[1:]: body.append(f"X{fl((R-EDGE)*math.cos(a))}Y{fl((R-EDGE)*math.sin(a))}D01*")
            body.append(f"X{fl(R-EDGE)}Y{fl(0)}D01*"); body.append("G37*"); body.append("%LPC*%")
            for p in pads:
                if p["tht"] and p["net"]!=net: flash(body,ap,"C",ap_pad(p),None,p["x"],p["y"])
            for (x,y,nn) in r["vias"]:
                if nn!=net: flash(body,ap,"C",ap_via(nn),None,x,y)
            body.append("%LPD*%"); clear_notch(ap,body)
        return fn
    names={"F.Cu":"F_Cu","In1.Cu":"In1_Cu","In2.Cu":"In2_Cu","In3.Cu":"In3_Cu","In4.Cu":"In4_Cu","B.Cu":"B_Cu"}
    for ly in all_layers:
        pn=[pl_layers[ly]] if ly in pl_layers else []
        write(names[ly],plane(pn[0]) if pn else (copper(ly) if ly in layers else (lambda ap,body:None)))
    def mask(side):
        def fn(ap,body):
            for p in pads:
                if p["tht"] or side=="F": padflash(body,ap,p,0.1)
        return fn
    write("F_Mask",mask("F")); write("B_Mask",lambda ap,body: [padflash(body,ap,p,0.1) for p in pads if p["tht"]] and None)
    def edge(ap,body):
        if notch is None: a=np.linspace(0,2*math.pi,361); stroke(body,ap,0.1,[(R*math.cos(t),R*math.sin(t)) for t in a]); return
        s=notch; w=7.6; yb=36.5; yc=math.sqrt(R*R-w*w); A=math.atan2(s*yc,w); B=math.atan2(s*yc,-w)
        a0,a1=(A,B+2*math.pi) if s<0 else (B,A+2*math.pi); a=np.linspace(a0,a1,360); pts=[(R*math.cos(t),R*math.sin(t)) for t in a]
        S=pts[0]; E=pts[-1]; pts+= [(E[0],s*yb),(S[0],s*yb),S]; stroke(body,ap,0.1,pts)
    write("Edge_Cuts",edge)
    tools={}
    for p in pads:
        if p["tht"]: tools.setdefault(round(p["drill"],2),[]).append((p["x"],-p["y"]))
    tools.setdefault(via_drill,[]).extend([(x,-y) for x,y,_ in r["vias"]])
    tl=sorted(tools.items()); txt="M48\nMETRIC,TZ\n"+"".join(f"T{i+1}C{dd:.3f}\n" for i,(dd,_) in enumerate(tl))+"%\nG90\n"+"".join(f"T{i+1}\n"+"".join(f"X{x:.3f}Y{y:.3f}\n" for x,y in pts) for i,(dd,pts) in enumerate(tl))+"M30\n"
    open(f"{outdir}/{prefix}-PTH.drl","w").write(txt)
    return dict(layers=[names[l] for l in all_layers],drill_sizes={str(k):len(v) for k,v in tools.items()})
if __name__=="__main__":
    b=sys.argv[1]; hatch="hatch" in sys.argv; nt=[int(x[5:]) for x in sys.argv if x.startswith("notch")]; hv=[x[3:].split(",") for x in sys.argv if x.startswith("hv=")]; print(export(f"kit_v18/{b}/pads.json",f"kit_v20/route_{b}.json",f"kit_v22/GERBER_{b}_v2",f"PF233-{b}-v2",hatch=hatch,notch=(nt[0] if nt else None),hv=(hv[0] if hv else ())))
