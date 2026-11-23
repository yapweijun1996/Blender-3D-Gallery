"""Regularized rest-space solve for moving surface contacts (Blender and NumPy)."""
import numpy as np
from mathutils.bvhtree import BVHTree

FLOOR = .0005
CAP = .03


def fit_sweep(points, weights, origin, faces, links, samples, matrices, api, step):
    """Measure all poses, solve active clearance planes and guard the rest shape."""
    r1, r2, r3, helpers = api
    clearance = helpers["clearance"]
    posed, skin = r2["skin_poses"](points, *r2["sparse_weights"](weights), matrices)
    anatomy = helpers["anatomy"]
    # Rank alternative nearby joints without replacing established strong weights.
    if step % 4 in (1, 2):
        preference = weights + .11*anatomy + .08*r2["average"](weights, links)
    else:
        preference = weights
    cols = r2["sparse_weights"](preference)[1]
    coeff = np.take_along_axis(weights,cols,axis=1)
    coeff /= coeff.sum(axis=1,keepdims=True).clip(1e-8)
    old_shape = faces.tolist()
    display_zone = helpers["section"](points)
    report, constraints = {}, []
    hits = np.zeros(len(faces), np.int32)
    minimum = np.full(len(points), .002, dtype=np.float32)
    worst = np.zeros_like(points)
    scale = 8.
    face_bary = r2["REST_BARYCENTRICS"]
    baked_rest = r2["rest_sample_positions"](points, faces)
    added = helpers["ADDED"]
    delta_m = .002 if step < 4 else (.00115 if step < 11 else .00072)

    for f,(name, frame, tree, body, body_tri) in enumerate(samples):
        pos = posed[f]
        signed,normals,_ = clearance(tree,pos)
        pairs = np.asarray(tree.overlap(BVHTree.FromPolygons(pos.tolist(),old_shape,all_triangles=True)),
                           dtype=np.int32).reshape(-1,2)
        entry = report.setdefault(name, dict(inside=0,pairs=0,total_pairs=0,min_m=1.,samples=0,bad=0))
        entry["samples"] += 1
        entry["inside"] = max(entry["inside"],int((signed<0).sum()))
        entry["pairs"] = max(entry["pairs"],len(pairs))
        entry["total_pairs"] += len(pairs)
        j = int(signed.argmin())
        entry["bad"] += int(len(pairs)>0 or signed[j] < FLOOR)
        if signed[j] < entry["min_m"]:
            entry.update(min_m=float(signed[j]),min_frame=frame,zone=str(display_zone[j]),
                         point_mm=np.round(points[j]*1000,3).tolist(),vertex=j)
        lower = signed < minimum
        minimum[lower] = signed[lower]
        worst[lower] = np.einsum("ni,nij->nj",normals[lower],skin[f,lower,:,:3])
        goal = delta_m if name in added else max(.00072,delta_m*.62)
        idx = np.flatnonzero(signed < goal+.0015)
        ids = np.tile(idx[:,None],(1,3))
        bary = np.tile(np.array([1,0,0],np.float32),(len(ids),1))
        normal, gap = normals[idx], goal-signed[idx]
        if f == 0:
            d,n,_ = clearance(tree,baked_rest.reshape(-1,3))
            hi = np.flatnonzero(d > CAP-.0004)
            ids = np.vstack((ids,faces[hi//len(face_bary)]))
            bary = np.vstack((bary,face_bary[hi%len(face_bary)]))
            normal = np.vstack((normal,-n[hi]))
            gap = np.r_[gap,d[hi]-(CAP-.00010)]
        if len(pairs):
            np.add.at(hits,pairs[:,1],1)
            # Keep the deepest witness per face plus its four interior probes.
            tf, b = r1["pair_witnesses"](pos,faces,body,body_tri,pairs[:,::-1],dense=False)
            cross = np.unique(pairs[:,1])
            tf = np.r_[tf,np.repeat(cross,len(face_bary))]
            b = np.vstack((b,np.tile(face_bary,(len(cross),1))))
            contact = np.einsum("nk,nki->ni",b,pos[faces[tf]])
            d,n,_ = clearance(tree,contact)
            order = np.lexsort((d,tf))
            first = np.flatnonzero(np.r_[True,np.diff(tf[order])!=0])
            keep = order[first]
            keep = keep[d[keep] < goal]
            ids = np.vstack((ids,faces[tf[keep]]))
            bary = np.vstack((bary,b[keep]))
            normal = np.vstack((normal,n[keep]))
            gap = np.r_[gap,goal-d[keep]]
        if not len(ids):
            continue
        grad_xyz = np.einsum("ni,nkij->nkj",normal,skin[f,ids,:,:3])
        t = matrices[f,cols[ids]]
        t = np.einsum("nkbic,nkc->nkbi",t[...,:3],points[ids])+t[...,3]
        grad_w = np.einsum("ni,nkbi->nkb",normal,t)
        grad_w -= grad_w.mean(axis=2,keepdims=True)
        grad = np.concatenate((grad_xyz,scale*grad_w),axis=2)*bary[...,None]
        # Half-frame verification is exhaustive. During the local solve, space out
        # equivalent positive-deficit constraints until late-stage cleanup.
        useful = (gap>0) | (f%4==0)
        if step < 9 and f%3 and f:
            useful &= gap > .0018
        constraints.append((ids[useful],grad[useful],gap[useful]))

    r3["display"](f"CONTACT {step}",report)
    if all(row["bad"]==0 for row in report.values()):
        return report, hits, points, weights

    ids, grad, gap = [np.concatenate(items) for items in zip(*constraints)]
    flat_ids, flat_grad = ids.ravel(), grad.reshape(-1,7)
    active = np.zeros(len(points),dtype=bool)
    active[ids[gap>0].ravel()] = True
    src,dst,_ = links
    for _ in range(2):
        active[dst[active[src]]] = True
    required = (.002-minimum).clip(0,CAP)
    worst /= np.linalg.norm(worst,axis=1,keepdims=True).clip(1e-8)
    bake = worst*required[:,None]
    for _ in range(3):
        bake += .30*(r2["average"](bake,links)-bake)
        bake += (required - (bake*worst).sum(axis=1)).clip(0)[:,None]*worst

    # Smooth differential position and weight changes across the editing region.
    # Position changes retain a cost relative to the shipped cut.
    k = len(points)
    reg = np.array([.13,.13,.13,.10,.10,.10,.10])
    smooth = np.array([.95,.95,.95,.10,.10,.10,.10])
    sums = np.repeat(np.abs(grad).sum(axis=(1,2)),3)
    diag = np.stack([np.bincount(flat_ids,weights=np.abs(g)*sums,minlength=k)
                     for g in flat_grad.T],axis=1)
    diag += 2*smooth+reg
    offset = points-origin
    trial = np.zeros((k,7),dtype=np.float32)
    if step==0:
        trial[:,:3] = bake*.45
    previous = trial.copy()
    for iteration in range(77 if step>=8 else 54):
        residual = np.repeat((gap-np.einsum("nki,nki->n",grad,trial[ids])).clip(0),3)
        pull = np.stack([np.bincount(flat_ids,weights=residual*g,minlength=k)
                         for g in flat_grad.T],axis=1)
        shape = trial.copy()
        shape[:,:3] += offset
        pull += smooth*(r2["average"](shape,links)-shape)
        pull -= reg*trial
        next_step = trial + (pull/diag).astype(np.float32)
        next_step[~active] = 0
        next_step[:,:3] = r2["bound_delta"](next_step[:,:3], .009 if step<7 else .005)
        next_step[:,3:] = (r2["simplex"](coeff+scale*next_step[:,3:])-coeff)/scale
        trial = next_step + (iteration/(iteration+4))*(next_step-previous)
        previous = next_step

    candidate = r2["project_rest"](points+previous[:,:3],origin,samples[0][2])
    candidate = r2["rest_guard"](candidate,points,origin,faces,samples[0][2])
    improved = weights.copy()
    improved[active] = r2["full_weights"](coeff[active]+scale*previous[active,3:],
                                            cols[active],weights.shape[1])
    return report, hits, candidate, improved
