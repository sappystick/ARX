import numpy as np, math, importlib, json
import phi_fold_v2 as v2, rodin_core_v4 as rc, golden_cone_head as g, phi_fold_former as pf
def evaluate():
    fm=v2.Former(); W,s=v2.wires(fm,0.03)
    # bends + location
    L=W[0][0]; a,b,c=np.roll(L,1,0),L,np.roll(L,-1,0)
    R=np.linalg.norm(b-a,axis=1)*np.linalg.norm(c-b,axis=1)*np.linalg.norm(c-a,axis=1)/np.maximum(2*np.linalg.norm(np.cross(b-a,c-a),axis=1),1e-15)
    idx=rc.eval_profile(fm.segs,s)[4]; seg=[n for n,_ in fm.segs][idx[np.argmin(R)]]
    Lw=sum(np.linalg.norm(np.diff(np.vstack([q,q[:1]]),axis=0),axis=1).sum() for q in W[0])
    mm,dd=[],[]
    for sec in W:
        for q in sec: m_,d_=pf.segs_closed(q[::3]); mm.append(m_); dd.append(d_)
    mm,dd=np.concatenate(mm),np.concatenate(dd)
    z=np.array([100,200,300.0]); pts=np.stack([0*z,0*z,-z*1e-3],-1)
    B4=g.biot_savart(mm,dd,np.ones(len(mm)),pts)[:,2]
    Rpar=0.0172/0.5*Lw/1000/4
    return dict(turns=fm.turns, Lw=round(Lw/1000,2), minbend=round(float(R.min()),2), at=seg,
                BpsW=[round(x,2) for x in (B4/4)/math.sqrt(Rpar)*1e6])
if __name__=="__main__": print("v1 reference B/sqrtW @100/200/300: 111.1 / 25.49 / 8.95")
if False:
 for rim,zone,ramp,rho in [(13,7,6,5),(13,0,3,5),(10,0,3,4),(8,0,3,3.5)]:
    v2.RIM_H=rim; v2.RIM_ZONE=zone; v2.RAMP=ramp; v2.RHO.update(heel=rho,crown=rho)
    v2.H_IN=v2.RIM_H+(v2.R_B-v2.R_I)*v2.T_SLOPE
    try: print(f"rim {rim} zone {zone} ramp {ramp} rho {rho}:",evaluate())
    except AssertionError as e: print(rim,zone,ramp,rho,"fail",e)
