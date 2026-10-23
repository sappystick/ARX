import numpy as np, math, json
from scipy.special import ellipk, ellipe
mu0=4e-7*math.pi
def Bz(a,h,rho,z,I=1.0):                                   # loop radius a (m) at height h above face, field at lateral rho, depth z below face
    d=z+h; s=(a+rho)**2+d*d; k2=4*a*rho/s; K=ellipk(k2); E=ellipe(k2)
    den=(a-rho)**2+d*d
    return mu0*I/(2*np.pi)/np.sqrt(s)*(K+(a*a-rho*rho-d*d)/den*E)
def field(fil,rho,z): return sum(Bz(r*1e-3,h*1e-3,rho,z,I) for r,h,I in fil)
def F(fil,z): W=sum(2*np.pi*r*1e-3 for r,h,I in fil); return field(fil,0,z)/W
out={}
# 1. tall solenoid penalty: 16 turns at the rim, columns x rows, 2.6 mm pitch
for cols,rows in ((16,1),(8,2),(4,4),(2,8),(1,16)):
    fil=[(116.5-1.3-c*2.6,1.3+r*2.6,1.0) for c in range(cols) for r in range(rows)]
    out[f"rim {cols}x{rows}"]=[round(F(fil,z)/F([(115.2,1.3,1.0)]*16,z),3) for z in (0.1,0.2,0.3)]
# 2. cone solenoid: rows rise toward the centre like the golden cone vs flat
cone=[(116.5-1.3-c*2.6,1.3+(c*2.6)*0.359+r*2.6,1.0) for c in range(4) for r in range(4)]
out["cone 4x4 rising inward"]=[round(F(cone,z)/F([(115.2,1.3,1.0)]*16,z),3) for z in (0.1,0.2,0.3)]
# 3. focusing test: rim ring + inner coil (r 45) with current ratio q, same copper split by wire length
rim=[(116.5-1.3-c*2.6,1.3+r*2.6,1.0) for c in range(4) for r in range(4)]
best=None; table={}
for q in (-1.0,-0.5,-0.25,0.0,0.25,0.5,1.0):
    inner=[(45.0,1.3,q)]*4
    fil=rim+inner; z=0.2
    Bax=field(fil,0,z); P=sum((I**2)*2*np.pi*r*1e-3 for r,h,I in fil)  # same wire: power ~ I^2 * length
    shape=[field(fil,rho,z)/Bax for rho in (0.05,0.10,0.15,0.2)]
    table[str(q)]=dict(B_per_sqrtP_rel=round(Bax/math.sqrt(P)/(field(rim,0,z)/math.sqrt(sum(2*np.pi*r*1e-3 for r,h,I in rim))),3),lateral_ratio_at_5_10_15_20cm=[round(s,2) for s in shape])
out["inner coil r45 (4 turns) current ratio q, field at 200 mm"]=table
print(json.dumps(out,indent=1))
