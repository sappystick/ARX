import numpy as np, math
mu0=4e-7*math.pi
def Bz_axis(a,zc,zt):            # ring radius a at height zc; field at zt (on axis), per amp
    dz=zt-zc; return mu0*a**2/(2*(a**2+dz**2)**1.5)
RB,RT,P=0.10795,0.01575,0.0018   # 8.5in base radius, plateau radius, 1.8 mm track pitch
def rings(kind):
    if kind=="flat":
        r=np.arange(RT,RB,P); z=np.zeros_like(r)
    else:
        th=math.radians(kind[1]); L=(RB-RT)/math.cos(th)
        s=np.arange(0,L,P); r=RB-s*math.cos(th)
        h=s*math.sin(th)                      # height of each turn above the base plane
        z = h if kind[0]=="tip_up" else (h.max()-h)   # tip_down: tip is lowest (z=0)
    return r,z
cases={"Flat spiral (pancake)":"flat",
       "Shallow cone 18.9°, tip UP (your OBJ)":("tip_up",18.86),
       "Shallow cone 18.9°, tip DOWN":("tip_down",18.86),
       "Steep golden cone 51.8°, tip DOWN":("tip_down",51.83),
       "Steep golden cone 51.8°, tip UP":("tip_up",51.83)}
depths=np.array([0.05,0.1,0.2,0.3])
print("B per sqrt(copper-loss), relative to flat, on axis below the lowest point of the head")
ref=None
for name,k in cases.items():
    r,z=rings(k); Lw=(2*np.pi*r).sum()
    B=np.array([sum(Bz_axis(a,zz,-d) for a,zz in zip(r,z)) for d in depths])/math.sqrt(Lw)
    if ref is None: ref=B
    print(f"{name:42s} turns {len(r):3d} wire {Lw:6.1f} m  height {1000*z.max():5.1f} mm  rel@50/100/200/300mm:",
          " ".join(f"{x:.2f}" for x in B/ref), " signal(TX=RX)@200mm %.2f"%((B/ref)[2]**2))
# Sequential firing test: rings fired one at a time from base to tip vs all together
r,z=rings(("tip_down",18.86)); d=0.2
each=np.array([Bz_axis(a,zz,-d) for a,zz in zip(r,z)])
print("\nSequential base->tip firing, field at 200 mm: max of any single step = %.3f µT/A, all together = %.3f µT/A"%(each.max()*1e6,each.sum()*1e6))
print("Peak if steps overlap in a travelling window of 10 rings: %.3f µT/A"%(max(np.convolve(each,np.ones(10),'valid'))*1e6))
