"""Measure the local surface consequence of coordinate-preserving diagonal changes."""
import json
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree

here=Path(__file__).resolve().parent
changes=json.loads((here/'diagonals.json').read_text())
zones={}
for source,result in changes:
    xyz=np.mean(source,axis=0)
    name='facial crease' if xyz[2]>.1 else ('left toes' if xyz[0]>0 else 'right toes')
    zones.setdefault(name,[[],[]])
    zones[name][0].append(source);zones[name][1].append(result)
out={}
for name,pair in zones.items():
    arrays=[np.asarray(p)*1000 for p in pair]
    fs=[tuple(np.arange(i*3,(i+1)*3).tolist()) for i in range(len(pair[0]))]
    bv=[BVHTree.FromPolygons(t.reshape(-1,3).tolist(),fs,all_triangles=True) for t in arrays]
    result={}
    for i,label in [(0,'old_to_new'),(1,'new_to_old')]:
        maxdist=0; total=0; count=0
        for p in arrays[i]:
            for a in range(25):
                for b in range(25-a):
                    u,v=a/24,b/24
                    q=(1-u-v)*p[0]+u*p[1]+v*p[2]
                    dist=bv[1-i].find_nearest(q)[3]
                    count+=1; total+=dist**2; maxdist=max(maxdist,dist)
        result[label]={'samples':count,'maximum_sampled_surface_mm':round(maxdist,5),'rms_mm':round((total/count)**.5,5)}
    out[name]=result
(here/'source_patch_distances.json').write_text(json.dumps(out,indent=2))
print(out)
