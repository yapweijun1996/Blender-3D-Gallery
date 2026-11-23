"""Bidirectional triangle penetration check adapted from the original socket verifier."""
import numpy as np
from mathutils import Vector
from geometry import EPSILON_M, inside, inside_depth

DEPTH_LIMIT = .001


def penetration_report(p, pf, bt, body_parts, q, qf, qt, prop_shells, certify=False):
    hits = bt.overlap(qt)
    bdep = inside_depth(p, prop_shells)
    qdep = inside_depth(q, body_parts)
    measured = max([0., *bdep.values(), *qdep.values()])
    certified = not (hits or bdep or qdep)
    if certify and not certified:
        # Refine triangles crossed by the opposing surface. Signed distance
        # is 1-Lipschitz per closed shell, so intervals bound unsampled depth.
        hit1 = {i for i, _ in hits}
        hit2 = {j for _, j in hits}
        for points, faces_, indices, parts, depths in (
                (p,pf,hit1,prop_shells,bdep),(q,qf,hit2,body_parts,qdep)):
            if depths:
                indices.update(i for i, f in enumerate(faces_) if any(j in depths for j in f))
            if indices:
                sub = np.array(faces_)[sorted(indices)]
                d, passed = certify_depth(points[sub], parts, DEPTH_LIMIT)
                measured = max(measured, d)
                if not passed:
                    break
        else:
            certified = measured <= DEPTH_LIMIT
    return dict(depth_mm=measured*1000, body_vertices_inside=len(bdep),
                prop_vertices_inside=len(qdep), triangle_pairs=len(hits), depth_gate_certified=certified)


def certify_depth(triangles, parts, limit):
    # Four-way subdivision reuses all dyadic sample points. Subdivision
    # stops at every triangle proven within the tolerance or a failing sample.
    peak = 0.
    for lo, hi, surface in parts:
        local = triangles[((triangles.max(1)>=lo)&(triangles.min(1)<=hi)).all(1)]
        cache = {}
        for _ in range(12):
            if not len(local):
                break
            corners = local.reshape(-1,3)
            key = [tuple(v) for v in corners]
            for v in set(key)-cache.keys():
                point = Vector(v)
                _, _, _, d = surface.find_nearest(point)
                cache[v] = d if d <= EPSILON_M or inside(point, surface) else -d
            depth = np.asarray([cache[k] for k in key]).reshape(-1,3)
            peak = max(peak, float(depth.max()))
            if peak > limit:
                return peak, False
            edge = np.linalg.norm(local-np.roll(local,1,axis=1),axis=2).max(1)
            # Each point is within at most 2/3 of the longest edge from
            # the nearest vertex. Use max + radius as a conservative bound.
            local = local[depth.max(1)+edge*(2/3)>limit]
            if len(local):
                a,b,c = local.transpose(1,0,2)
                x,y,z = (a+b)*.5,(b+c)*.5,(c+a)*.5
                local = np.concatenate([np.stack(q,axis=1) for q in ((a,x,z),(b,y,x),(c,z,y),(x,y,z))])
        else:
            return peak, False
    return peak, True
