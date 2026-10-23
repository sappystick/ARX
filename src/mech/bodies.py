import struct, sys, json, hashlib, numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
def load(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[80:84])[0]
    if len(b)!=84+50*n: raise ValueError("not binary")
    return np.frombuffer(b,dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]),count=n,offset=84)['v'].reshape(-1,3,3).astype(np.float64), hashlib.sha256(b).hexdigest()[:16]
def info(p):
    T,h=load(p); V=T.reshape(-1,3); q=np.round(V*1000).astype(np.int64)+(1<<20); key=(q[:,0]<<42)|(q[:,1]<<21)|q[:,2]
    u,inv=np.unique(key,return_inverse=True); tri=inv.reshape(-1,3); e=np.vstack([tri[:,[0,1]],tri[:,[1,2]]]); g=coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(len(u),len(u)))
    nc,lab=connected_components(g,directed=False); sizes=np.bincount(lab[tri[:,0]],minlength=nc); sizes=sizes[sizes>0]
    # signed volume
    a,b,c=T[:,0],T[:,1],T[:,2]; vol=float(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6)
    r=np.hypot(V[:,0],V[:,1])
    return dict(file=p.split('/')[-1],sha16=h,triangles=int(len(T)),bodies=int(len(sizes)),body_triangle_counts=sorted(sizes.tolist(),reverse=True)[:4],bbox=[round(float(x),2) for x in (*V.min(0),*V.max(0))],max_radius=round(float(r.max()),2),volume_cm3=round(vol/1000,2))
paths=sys.argv[1:]; out=[]
for p in paths:
    d=info(p); out.append(d); print(json.dumps(d),flush=True)
