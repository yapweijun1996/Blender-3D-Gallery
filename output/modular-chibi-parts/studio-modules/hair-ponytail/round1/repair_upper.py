"""Open local tangencies left by the Studio decimator at the tail/cap fold."""
import numpy as np
from mathutils.bvhtree import BVHTree

def relax_fold(verts,faces,upper_end):
    rings=[set() for _ in verts]
    for a,b,c in faces:
        rings[a].update((b,c));rings[b].update((a,c));rings[c].update((b,a))
    for _ in range(16):
        tree=BVHTree.FromPolygons(verts,faces,all_triangles=True)
        pairs=[(i,j) for i,j in tree.overlap(tree) if i<j and set(faces[i]).isdisjoint(faces[j])]
        if not pairs:return
        targets={v for pair in pairs for i in pair if i<upper_end for v in faces[i]}
        if not targets:raise RuntimeError(('Lining intersection',pairs))
        # Tangent folds are confined to the hidden interface. Move the
        # two incident fans toward their respective local surface averages.
        near={n for i in targets for n in rings[i]}-targets
        fresh={}
        for i in targets|near:
            v=verts[i];adj=rings[i]
            weights=np.array([1/max(.003,(verts[j]-v).length) for j in adj]);weights/=weights.sum()
            mean=sum((verts[j]*float(w) for j,w in zip(adj,weights)),v*0)
            fresh[i]=v.lerp(mean,.62 if i in targets else .19)
        for i,v in fresh.items():verts[i]=v
    raise RuntimeError('Unresolved Studio fold intersections')

