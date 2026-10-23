import numpy as np, math, json
src=open('sim_head1.py').read().split("# ======================= S4")[0]; ns={}; exec(src,ns)
ring=ns["ring"]; Mutual=ns["Mutual"]; TXs=ns["TXs"]; mono=ns["mono"]; x8=ns["x8"]; wf=ns["wf"]; M_mono=ns["M_mono"]
def rot45(loops,deg):
    c,s=math.cos(math.radians(deg)),math.sin(math.radians(deg)); out=[]
    for l in loops: out.append(np.c_[l[:,0]*c-l[:,1]*s,l[:,0]*s+l[:,1]*c,l[:,2]])
    return out
quadA=ns["quad"]; quadB=rot45(quadA,45.0)
def shifted(loops,dx,dy): return [np.c_[l[:,0]+dx*1e-3,l[:,1]+dy*1e-3,l[:,2]] for l in loops]
res={}
for nm,g in (("X8 figure-8",x8),("QUAD A (quadrants)",quadA),("QUAD B (rotated 45 deg)",quadB)):
    row={}
    for sh in ((0,0),(0.5,0),(0,0.5),(0.1,0.0)):
        M=Mutual(TXs,[l[::2] for l in shifted(g,*sh)])/6.0; row[f"shift {sh[0]},{sh[1]} mm"]=abs(M)/abs(M_mono)
    res[nm]=row
for k,v in res.items(): print(k,{a:f"{b:.2e}" for a,b in v.items()})
didt=max(np.max(np.abs(np.gradient(w[1],w[0]))) for w in wf.values()); pk=abs(M_mono)*didt
out={"leak_relative_to_unnulled":{k:{a:float(b) for a,b in v.items()} for k,v in res.items()},"peak_volts_at_turnoff":{k:{a:round(float(b)*pk,4) for a,b in v.items()} for k,v in res.items()},"unnulled_peak_V":round(pk,1)}
print("peak V:",out["peak_volts_at_turnoff"])
# ---- bandwidth of the analog trim path: cancel a leak EMF (proportional to dI/dt) with a scaled, filtered, delayed reference
t,i,vd,vc=wf["100 nF C0G/film"]; g=np.gradient(i,t); dt=t[1]-t[0]
def first_clean(resid_V,thr=1e-7):
    bad=np.where(np.abs(resid_V)>thr)[0]; return float(t[bad[-1]+1]*1e6) if len(bad) else 0.0
def trim(eps,fc,delay_ns,bits,rng,tmpl=1.0):
    leak=eps*pk*g/np.max(np.abs(g)); a=2*math.pi*fc; ref=np.zeros_like(g); y=0.0
    for n in range(len(g)): y+=dt*a*(g[n]-y); ref[n]=y
    sh=int(round(delay_ns*1e-9/dt)); ref=np.roll(ref,sh); ref[:sh]=0; ref=ref/np.max(np.abs(g))
    w=(t>3e-6)&(t<15e-6); k=np.sum(leak[w]*ref[w])/np.sum(ref[w]**2); lsb=(4*eps*pk)/2**bits; kq=round(k/lsb)*lsb if lsb>0 else k
    r=leak-kq*ref; return first_clean(r*tmpl),float(np.max(np.abs(r))/np.max(np.abs(leak)))
tab={}
for eps_name,eps in (("quad, 0.5 mm off-centre",None),):
    pass
eps_q=res["QUAD A (quadrants)"]["shift 0.5,0 mm"]; eps_x=res["X8 figure-8"]["shift 0.1,0.0 mm"]
for nm,eps in (("QUAD 0.5 mm off",eps_q),("X8 keyed to 0.1 mm",eps_x)):
    rows={}
    for fc in (0.5e6,1e6,2e6,5e6,20e6):
        for dly in (0,50):
            tf,rr=trim(eps,fc,dly,14,2.0*eps,1.0); tf2,_=trim(eps,fc,dly,14,2.0*eps,0.03)
            rows[f"BW {fc/1e6:g} MHz, delay {dly} ns"]=dict(first_clean_us_analog_only=round(tf,2),with_digital_template_us=round(tf2,2),residual_fraction=round(rr,3))
    tab[nm]=rows; 
    print(nm,"untrimmed first clean gate:",round(first_clean(eps*pk*g/np.max(np.abs(g))),2),"us")
    for k,v in rows.items(): print("  ",k,v)
out["trim_bandwidth"]=tab; json.dump(out,open("kit_v21/sim_tanr.json","w"),indent=1)
