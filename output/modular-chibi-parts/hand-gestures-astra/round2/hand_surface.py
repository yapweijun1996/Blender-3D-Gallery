"""Closest surface witnesses on fixed rest-space fingertip pulp and palmar triangle sets."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from hand_common import DIGITS, prefix


def patches(body, rig, side, tips, geom):
    tris,labels,palm,_=geom
    rest=np.array([v.co for v in body.data.vertices])*1000
    sets={'Palm':palm}
    for digit in DIGITS:
        bone=rig.data.bones[prefix(side)+digit+('3' if digit=='Thumb' else '4')]
        distal=np.array(bone.matrix_local.col[1].xyz)
        volar=np.array(bone.matrix_local.col[2].xyz)
        normal=distal+.65*volar
        normal/=np.linalg.norm(normal)
        tip=rest[tips[digit]].mean(0)
        region=[t for t,l in zip(tris,labels) if l==digit and
                all(np.linalg.norm(rest[i]-tip)<16 for i in t)]
        support=max((rest[i]-tip)@normal for t in region for i in t)
        pulp=[];terminal=[]
        for t in region:
            a,b,c=rest[list(t)]
            fc=np.cross(b-a,c-a);fc/=max(1e-20,np.linalg.norm(fc))
            dots=(rest[list(t)]-tip)@normal
            if min(dots)>=support-2.65 and fc@normal>.32:pulp.append(t)
            if min((rest[list(t)]-tip)@distal)>-8.0:terminal.append(t)
        assert pulp and terminal,(side,digit,len(pulp),len(terminal))
        sets[digit]=pulp
        sets[digit+'_tip']=terminal
        if digit=='Index':
            root=np.array(rig.data.bones[prefix(side)+'Index1'].head_local)*1000
            prox=np.array(rig.data.bones[prefix(side)+'Index1'].matrix_local.col[1].xyz)
            sets['Index_proximal']=[t for t,l in zip(tris,labels) if l=='Index' and
                all(-2<(rest[i]-root)@prox<28 for i in t)]
    return sets


def nearest(points, first, second):
    """The minimum for two disjoint triangles occurs at vertex/face or edge/edge."""
    points=np.asarray(points,dtype=float)*1000
    verts=[set(i for t in fs for i in t) for fs in (first,second)]
    trees=[BVHTree.FromPolygons(points.tolist(),fs,all_triangles=True) for fs in (first,second)]
    best=float('inf');witness=None
    for which in (0,1):
        for i in verts[which]:
            q,_,_,distance=trees[1-which].find_nearest(points[i])
            if distance<best:
                best=distance
                witness=[points[i],np.array(q)][::1 if which==0 else -1]
    def edges(faces):
        return np.array(sorted({tuple(sorted((a,b))) for t in faces for a,b in zip(t,t[1:]+t[:1])}))
    e2=points[edges(second)]
    lo=e2.min(1);hi=e2.max(1)
    for p,q in points[edges(first)]:
        select=((np.minimum(p,q)-best<=hi)&(np.maximum(p,q)+best>=lo)).all(1)
        if not np.any(select):continue
        bb=e2[select];s=bb[:,0];v=bb[:,1]-s;u=q-p;w=p-s
        a=u@u;b=v@u;c=(v*v).sum(1);d=w@u;e=(v*w).sum(1)
        den=a*c-b*b
        valid=den>1e-12*a*c
        den=np.where(valid,den,1)
        t=(b*e-c*d)/den;k=(a*e-b*d)/den
        valid&=(t>=0)&(t<=1)&(k>=0)&(k<=1)
        if not np.any(valid):continue
        aa=p+t[:,None]*u;zz=s+k[:,None]*v
        dist=np.where(valid,np.linalg.norm(aa-zz,axis=1),np.inf)
        i=int(np.argmin(dist))
        if dist[i]<best:best=dist[i];witness=[aa[i],zz[i]]
    return dict(distance_mm=round(float(best),5),witness_world_mm=[[round(float(v),5) for v in p] for p in witness],
                triangles=[len(first),len(second)])


def measures(points,sets,gesture):
    if gesture in ('pinch','ok'):
        return {'thumb_to_index_pulp':nearest(points,sets['Thumb'],sets['Index'])}
    if gesture=='fist':
        return {'terminal_to_palm':{d:nearest(points,sets[d+'_tip'],sets['Palm']) for d in DIGITS},
                'pulp_to_palm':{d:nearest(points,sets[d],sets['Palm']) for d in DIGITS[:4]}}
    folds={'thumbs_up':DIGITS[:4],'point':DIGITS[1:4],'peace':DIGITS[2:4]}
    if gesture in folds:
        result={'folded_pulp_to_palm':{d:nearest(points,sets[d],sets['Palm']) for d in folds[gesture]}}
        if gesture in ('point','peace'):
            result['thumb_to_proximal_index']=nearest(points,sets['Thumb_tip'],sets['Index_proximal'])
        return result
    return {}
