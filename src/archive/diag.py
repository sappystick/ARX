import sys, numpy as np, math
sys.argv=['x']
import afe_layout as A
from scipy import ndimage
for pd in A.PADS:
    if pd["ref"] in ("U1","U2","U3") and pd["num"]=="9": A.ep_vias(pd)
def reach(net, pd):
    P=[A.passable(L,net) for L in range(A.NL)]
    lab=[ndimage.label(P[L],structure=np.ones((3,3)))[0] for L in range(A.NL)]
    cells=A.pad_cells(pd); ids=set((L,lab[L][j,i]) for (L,i,j) in cells if P[L][j,i])
    return {L:int(sum((lab[L]==l).sum() for (LL,l) in ids if LL==L)) for L in range(A.NL)}, len([1 for (L,i,j) in cells if P[L][j,i]]), len(cells)
for name in ("SCLK","CS","VCM","+3V3D","FB_X8"):
    net=A.NETID[name]; pads=[p for p in A.PADS if p["net"]==name]
    print(name,[ (p["ref"],p["num"],reach(net,p)) for p in pads[:4]])
print("---- direct A* tests")
def pad(ref,num): return [p for p in A.PADS if p["ref"]==ref and p["num"]==str(num)][0]
import time
for name,(r1,n1),(r2,n2) in (("IN_GX",("RS1",2),("D1",3)),("SCLK",("UA1",8),("J2",5)),("VCM",("J1",2),("SW1",2))):
    net=A.NETID[name]; t=time.time()
    p=A.astar(net,A.pad_cells(pad(r1,n1)),A.pad_cells(pad(r2,n2)),max_exp=300000)
    print(name,"found" if p else "NONE",len(p) if p else 0,"%.1fs"%(time.time()-t))
    if not p:
        P=[A.passable(L,net) for L in range(A.NL)]
        tgt=A.pad_cells(pad(r2,n2)); st=A.pad_cells(pad(r1,n1))
        print(" start passable cells",sum(1 for (L,i,j) in st if P[L][j,i]),"/",len(st)," target passable",sum(1 for (L,i,j) in tgt if P[L][j,i]),"/",len(tgt))
        # which neighbours of start pad are free
        L,i,j=st[len(st)//2]; 
        print(" window around start (layer",L,") free map:")
        for dj in range(-8,9):
            print("  "+"".join("." if P[L][j+dj,i+di] else "#" for di in range(-20,21)))
