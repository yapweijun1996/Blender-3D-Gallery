"""Resolve isolated half-frame contacts while retaining the sewn skin shell."""
import runpy
import numpy as np
from mathutils.bvhtree import BVHTree

from fit_skirt import PARTS, nearest
from skirt_contact import ContactFit, measure_score
from skirt_surface import CENTER, limit_weights, smooth


def poses_for_patch(base, ids, rows, extra):
    distances, pairs = base[:2]
    gaps = distances[:,ids].min(axis=1)
    all_relevant = np.flatnonzero((gaps < .0065) | ((gaps < .010) & (pairs>0)))
    if len(all_relevant)>95:
        priority = all_relevant[np.argsort(gaps[all_relevant])[:75]]
        spread = all_relevant[::max(1,len(all_relevant)//55)]
        all_relevant = np.r_[priority,spread]
    return np.unique(np.r_[0,rows[::39],all_relevant,extra])


def patch_search(fit, points, weights, distances, pairs, vertex, opposite, radius):
    dist = np.linalg.norm(points[:len(opposite)]-points[vertex],axis=1)
    belt = points[vertex,2]>.408
    kernel = smooth(1-dist/radius)
    if belt:
        kernel = np.maximum(kernel,.35*smooth(1-dist/(radius*1.1)))
    outer = np.flatnonzero(kernel>.005)
    ids = np.r_[outer,opposite[outer]]
    fac = kernel[np.r_[outer,outer]]
    affected = fit.triangles[np.isin(fit.triangles,ids).any(axis=1)]
    distinct, local = np.unique(affected,return_inverse=True)
    polys = local.reshape(affected.shape).tolist()
    changed = np.searchsorted(distinct,ids)
    base = distances,pairs
    rows = np.arange(len(distances))
    active_frames = np.flatnonzero(distances[:,ids].min(axis=1)<.001)
    chosen = poses_for_patch(base,ids,rows,active_frames)
    mats = fit.motion[4][chosen]
    rest = fit.body(0)
    original_p,original_w = points[ids],weights[ids]

    def evaluate(p,w, compute_triangles=True):
        gaps,_,_,_ = nearest(rest,p)
        if gaps.min() < .00075 or gaps.max() > .0292:
            return float("inf"),None
        x,y = points[distinct].copy(),weights[distinct].copy()
        x[changed],y[changed] = p,w
        transform = np.einsum("vk,fkij->fvij", y, mats, optimize=True)
        pose = np.einsum("fvij,vj->fvi",transform[:,:,:,:3],x)+transform[:,:,:,3]
        ds = []
        for i,f in enumerate(chosen):
            tree = fit.body(f)
            g,_,_,_ = nearest(tree,pose[i,changed])
            ds.append(g)
        ds = np.asarray(ds)
        missing = np.maximum(.00075-ds,0)*1000
        score = missing.sum()+1.75*missing.max()
        if compute_triangles:
            for i,f in enumerate(chosen):
                tree = fit.body(f)
                patch = BVHTree.FromPolygons(pose[i].tolist(),polys,all_triangles=True)
                score += .45*len(tree.overlap(patch))
        return float(score),ds

    old,g = evaluate(original_p,original_w)
    if old <= 0:
        return None
    spatial = points[vertex,:2]-CENTER
    radial = np.array((*spatial/np.linalg.norm(spatial),0.),dtype=np.float32)
    tangent = np.array((-radial[1],radial[0],0),dtype=np.float32)
    z = np.array((0.,0.,1.),dtype=np.float32)
    pv = int(np.flatnonzero(ids==vertex)[0])
    seam = int(np.argmin(g[:,pv]))
    posed_matrix = np.einsum("k,kij->ij",weights[vertex],mats[seam])
    world = posed_matrix[:,:3]@points[vertex]+posed_matrix[:,3]
    _,_,n,_ = nearest(fit.body(chosen[seam]),world[None])
    normal = posed_matrix[:,:3].T@n[0]
    _, anchor, rest_normal, _ = nearest(rest,points[vertex,None])
    close = anchor[0]+.0035*rest_normal[0]-points[vertex]
    directional = [radial,-radial,z,-z,tangent,-tangent,normal,-normal,
                   .707*(z+radial),.707*(-z+radial),.707*(z-radial),.707*(-z-radial)]
    geometry = [(axis*step, None) for axis in directional for step in (.0008,.0022,.0045)]
    geometry.extend((axis*.007,None) for axis in directional[:8])
    geometry.extend((close*amount,None) for amount in (.55,.85))
    zero = np.zeros(3,dtype=np.float32)
    basis = np.eye(weights.shape[1],dtype=np.float32)
    own = 1 if points[vertex,0]>CENTER[0] else 2
    other = 2 if own==1 else 1
    choices = (own,other,3,4) if belt else (own,other,3)
    changes = [(zero, (basis[k]-basis[0])*step) for k in choices for step in (.055,-.055,.13,-.13)]
    transfers = [(zero,(basis[own]-basis[other])*s) for s in (.10,-.10)]
    variants = [(original_p+fac[:,None]*delta,
                 original_w if dw is None else limit_weights(original_w+fac[:,None]*dw))
                for delta,dw in geometry+changes+transfers]
    ranked = sorted((evaluate(p,w,False)[0],i) for i,(p,w) in enumerate(variants))
    # Include strong angular and weight alternatives even when a triangle
    # witness, rather than one of its corners, drives the improvement.
    finalists = list(dict.fromkeys([i for _,i in ranked[:14]] + list(range(0,len(geometry),6))))
    best = old
    candidate = None
    for index in finalists:
        p,w = variants[index]
        value,new_dist = evaluate(p,w)
        if value < best-1e-5:
            best = value
            candidate = ids,p,w,chosen,new_dist,old-best
        if value <= .00001:
            break
    return candidate


def polish_motion(motion, checkpoint, passes, max_patches=12):
    with np.load(checkpoint) as data:
        points,triangles,weights,paired,depth,theta,parameters = (
            data[key] for key in ("points","triangles","weights","paired","depth","theta","parameters"))
    fitter = ContactFit(motion,triangles,paired,np.arange(len(motion[0])))
    opposite = np.empty(len(points)//2,dtype=np.int32)
    for outward,inward in paired:
        opposite[outward] = inward
    witness = runpy.run_path(str(PARTS/"hoodie-fit-sol/round3/fit_hoodie_round3.py"))["pair_witnesses"]

    def save():
        np.savez(checkpoint,points=points,triangles=triangles,weights=weights,paired=paired,
                 depth=depth,theta=theta,parameters=parameters)

    best = float("inf")
    accepted = points.copy(),weights.copy()
    for iteration in range(passes+1):
        result = fitter.scan(points,weights,exact=witness)
        d,n,_,_,contact = result
        score = measure_score(result)
        row,v = np.unravel_index(d.argmin(),d.shape)
        print("POLISH",iteration,"score",score,"pairs",int(n.sum()),"below",int((d<.0005).sum()),
              "minimum",float(d.min()*1000),motion[0][row],motion[1][row],v,flush=True)
        if score < best:
            accepted = points.copy(),weights.copy()
            best = score
            save()
        if (d.min() >= .00065 and not n.any()) or iteration==passes:
            break
        heat = np.maximum(.00075-d,0).max(axis=0)
        if contact:
            ids,_,gaps,_ = contact
            np.maximum.at(heat,ids,.55*np.maximum(.0015-gaps,0))
        half = len(points)//2
        heat = np.maximum(heat[:half],heat[opposite])
        seen = np.zeros(half,dtype=bool)
        tried = 0
        for pivot in np.argsort(-heat):
            if heat[pivot] <= 1e-6 or tried >= max_patches:
                break
            if seen[pivot]:
                continue
            tried += 1
            candidate = None
            for radius in (.021,.0105,.032):
                candidate = patch_search(fitter,points,weights,d,n,int(pivot),opposite,radius)
                if candidate:
                    break
            if candidate:
                ids,p,w,rows,dist,gain = candidate
                points[ids],weights[ids] = p,w
                d[np.ix_(rows,ids)] = dist
                print("PATCH",int(pivot),"radius",radius,"gain",round(gain,4),flush=True)
            seen |= np.linalg.norm(points[:half]-points[pivot],axis=1)<.016
    points,weights = accepted
    save()


def anchor_search(fit, points, weights, state, pivot, opposite, rng):
    d, pair_counts, skin, pose, contacts = state
    move = np.array((pivot,opposite[pivot]))
    part = fit.triangles[np.isin(fit.triangles,move).any(axis=1)]
    specific, ids = np.unique(part,return_inverse=True)
    local = ids.reshape(part.shape)
    moving = np.searchsorted(specific,move)
    poly_list = local.tolist()
    mats = fit.motion[4]
    original = points[move]
    influence = weights[pivot]
    closest = d[:,move].min(axis=1)
    priority = np.argsort(closest)
    near = np.flatnonzero(closest<.004)
    probe = np.unique(np.r_[0,np.arange(0,len(d),41),priority[:55],near[::max(1,len(near)//38)]])
    worst = priority[:13]
    if contacts is not None:
        vertices, normal, gap, rows = contacts
        eligible = np.isin(vertices,move)
        tid = np.flatnonzero(eligible)
        important = tid[np.argsort(gap[tid])[:35]]
        probe = np.unique(np.r_[probe,rows[important],rows[tid[::max(1,len(tid)//40)]]])
    else:
        important = []
    count = 512
    scales = np.array((.00019,.00044,.00092,.0019,.0039,.0068,.011),dtype=np.float32)
    weight_scales = np.array((.006,.014,.029,.058,.12,.23,.36),dtype=np.float32)
    seq = np.arange(count)%len(scales)
    drift = rng.normal(size=(count,3)).astype(np.float32)*scales[seq,None]
    noise = rng.normal(size=(count,len(influence))).astype(np.float32)*weight_scales[seq,None]
    noise[:140] = 0
    drift[140:250] = 0
    for i,row in enumerate(worst):
        vertex = move[np.argmin(d[row,move])]
        _,_,n,_ = nearest(fit.body(row),pose[row,vertex,None])
        axis = n[0] @ skin[row,vertex,:,:3]
        axis /= max(1e-9,np.linalg.norm(axis))
        drift[i*9:(i+1)*9] = np.linspace(-.002,.006,9)[:,None]*axis
    for i,tid in enumerate(important[:14]):
        axis = normal[tid] @ skin[rows[tid],vertices[tid],:,:3]
        drift[260+i*8:268+i*8] = np.linspace(-.001,.004,8)[:,None]*axis
    candidate = original[None] + drift[:,None]
    candidate_weights = limit_weights(influence[None]+noise)
    rest_gap,rest_near,_,_ = nearest(fit.body(0),candidate.reshape(-1,3))
    rest_gap = rest_gap.reshape(count,2)
    rest_dist = np.linalg.norm(candidate.reshape(-1,3)-rest_near,axis=1).reshape(count,2)
    valid = (rest_gap.min(axis=1)>.00072) & (rest_dist.max(axis=1)<.0296)
    reference = points[part]
    a = np.cross(reference[:,1]-reference[:,0],reference[:,2]-reference[:,0])
    local_positions = np.broadcast_to(points[specific],(count,len(specific),3)).copy()
    local_positions[:,moving] = candidate
    patch = local_positions[:,local]
    b = np.cross(patch[:,:,1]-patch[:,:,0],patch[:,:,2]-patch[:,:,0])
    valid &= (np.einsum("cni,ni->cn",b,a)>.23*(a*a).sum(axis=1)).all(axis=1)
    allow = np.flatnonzero(valid)
    if not len(allow):
        return None
    candidate, candidate_weights = candidate[allow],candidate_weights[allow]
    drift = drift[allow]
    look = np.einsum("ck,rkij->rcij",candidate_weights,mats[probe],optimize=True)
    poses = np.einsum("rcij,cvj->rcvi",look[:,:,:,:3],candidate)+look[:,:,:,3][:,:,None]
    gaps = np.asarray([nearest(fit.body(row),q.reshape(-1,3))[0].reshape(-1,2)
                       for row,q in zip(probe,poses,strict=True)])
    defect = np.maximum(.00061-gaps,0)*1000
    fast_score = (defect**2).sum(axis=(0,2))+8*defect.max(axis=(0,2))**2
    fast_score += .004*np.linalg.norm(drift*1000,axis=1)
    smaller = list(np.argsort(fast_score)[:13])
    if len(important):
        # Give the contact normal a chance when the vertex test is clean but
        # the edge opposite the pivot still intersects.
        smaller += [int(np.argmin(np.linalg.norm(drift-shift,axis=1)))
                    for shift in (.0015*normal[important[0]],.0028*normal[important[0]])]
    checks = np.unique(np.r_[probe,worst,
                        np.flatnonzero((pair_counts>0)&(d[:,specific].min(axis=1)<.009))])

    def deep(p,w):
        transform = np.einsum("k,rkij->rij",w,mats[checks],optimize=True)
        pose_moving = np.einsum("rij,vj->rvi",transform[:,:,:3],p)+transform[:,:,3][:,None]
        local_pose = pose[checks[:,None],specific].copy()
        local_pose[:,moving] = pose_moving
        gaps = []
        pairs = 0
        for row,q in zip(checks,local_pose,strict=True):
            tree = fit.body(row)
            gaps.append(nearest(tree,q[moving])[0])
            pairs += len(tree.overlap(BVHTree.FromPolygons(q.tolist(),poly_list,all_triangles=True)))
        defect = np.maximum(.00061-np.asarray(gaps),0)*1000
        return float(1.4*pairs+(defect**2).sum()+8*defect.max()**2)

    initial = deep(original,influence)
    best = initial
    accepted = None
    for i in smaller:
        value = deep(candidate[i],candidate_weights[i])
        if value < best-1e-7:
            best = value
            accepted = move,candidate[i],candidate_weights[i],initial-best
        if value <= 1e-8:
            break
    return accepted


def polish_anchors(motion, checkpoint, passes):
    with np.load(checkpoint) as data:
        fields = dict(data)
    points,weights = fields["points"],fields["weights"]
    fit = ContactFit(motion,fields["triangles"],fields["paired"],np.arange(len(motion[0])))
    witness = runpy.run_path(str(PARTS/"hoodie-fit-sol/round3/fit_hoodie_round3.py"))["pair_witnesses"]
    half = len(points)//2
    opposite = np.empty(half,dtype=np.int32)
    for outward,inward in fields["paired"]:
        opposite[outward] = inward
    seed = np.random.default_rng(8262026)
    best = float("inf")
    for step in range(passes+1):
        state = fit.scan(points,weights,exact=witness)
        d,n,_,_,c = state
        score = measure_score(state)
        print("ANCHORS",step,"score",score,"pairs",int(n.sum()),"below",int((d<.0005).sum()),
              "min",float(d.min()*1000),flush=True)
        if score < best:
            np.savez(checkpoint,**fields)
            best = score
        if (d.min()>=.00057 and not n.any()) or step==passes:
            break
        heat = np.maximum(.00062-d,0).max(axis=0)
        if c:
            vi,_,gaps,_ = c
            np.maximum.at(heat,vi,.42*np.maximum(.0011-gaps,0))
        heat = np.maximum(heat[:half],heat[opposite])
        for v in np.argsort(-heat)[:15]:
            if heat[v]<.00001:
                break
            answer = anchor_search(fit,points,weights,state,int(v),opposite,seed)
            if answer:
                move,p,w,gain = answer
                points[move],weights[move] = p,w
                print("ANCHOR",int(v),round(gain,5),flush=True)
                updated = np.einsum("k,rkij->rij",w,motion[4],optimize=True)
                state[3][:,move] = (np.einsum("rij,vj->rvi",updated[:,:,:3],p) +
                                     updated[:,:,3][:,None])
                state[2][:,move] = updated[:,None]


def lower_rear_band(motion, checkpoint):
    """Test whole-band curvature around the compressed rear waist in walk."""
    from skirt_surface import SIDES
    with np.load(checkpoint) as data:
        fields = dict(data)
    p,w,t = (fields[name] for name in ("points","weights","triangles"))
    clips = motion[0]
    select = np.unique(np.r_[0,np.flatnonzero(clips=="walk"),
                             np.arange(0,len(clips),12)])
    fit = ContactFit(motion,t,fields["paired"],select)
    rest = fit.body(0)
    _, surface, normals, _ = nearest(rest,p)
    rear = np.maximum(0,-np.cos(fields["theta"][np.arange(len(p))%SIDES]))
    high = smooth((p[:,2]-.382)/.040)
    kernel = rear**8 * high
    direction = np.column_stack((np.sin(fields["theta"][np.arange(len(p))%SIDES]),
                                  -np.cos(fields["theta"][np.arange(len(p))%SIDES]),
                                  np.zeros(len(p))))
    potentials = [(0.,0.),(-.006,0.),(-.010,.0),(-.015,0.),(.005,0.),
                  (0.,-.004),(-.010,-.004),(-.018,-.0035),(.004,-.007),
                  (-.009,.003),(-.014,.003),(-.004,.003)]
    initial = fit.scan(p,w,edges=False)

    def loss(value):
        d,n = value[:2]
        return measure_score(value) + .9*np.square(np.maximum(.00055-d.min(axis=1),0)*1000).sum()

    best,best_mesh = loss(initial),p
    trials = []
    for z,radial in potentials[1:]:
        q = (p + (kernel*radial)[:,None]*direction).astype(np.float32)
        q[:,2] += kernel*z
        trials.append((f"rear {z} {radial}",q))
    rear_d = p[:,1]-surface[:,1]
    for center_raise,outside_gap in ((.004,.0045),(.009,.0045),(.005,.007),(0.,.004),(-.001,.005)):
        inward = np.clip(rear_d-outside_gap,0,.025)*kernel
        q = p.copy()
        q[:,1] -= inward
        q[:,2] += center_raise*kernel
        trials.append((f"high inward {center_raise} {outside_gap}",q))
    for label,q in trials:
        q = fit.constrain_rest(q)
        result = fit.scan(q,w,edges=False)
        score = loss(result)
        print("BAND",label,score,int(result[1].sum()),float(result[0].min()*1000),flush=True)
        if score < best:
            best, best_mesh = score,q
    if best_mesh is not p:
        fit.selected = np.arange(len(motion[0]))
        a = fit.scan(p,w,edges=False)
        b = fit.scan(best_mesh,w,edges=False)
        print("BAND DENSE",loss(a),loss(b),flush=True)
        if loss(b)<loss(a):
            fields["points"] = best_mesh
            np.savez(checkpoint,**fields)


def lengthen_hem(motion, checkpoint):
    """Use the longest tested hem that preserves the complete clearance gate."""
    from skirt_surface import SIDES
    with np.load(checkpoint) as data:
        fields = dict(data)
    points,triangles,weights,paired,depth,theta = (
        fields[key] for key in ("points","triangles","weights","paired","depth","theta"))
    all_samples = np.arange(len(motion[0]))
    fit = ContactFit(motion,triangles,paired,all_samples)
    current = fit.scan(points,weights,edges=False)
    if current[0].min() < .00056 or current[1].any():
        print("HEM BASE CONSTRAINT",float(current[0].min()),int(current[1].sum()),flush=True)
        return
    taper = smooth((depth-.54)/.46)
    taper = np.repeat(np.r_[taper,taper[::-1]],SIDES)
    theta = np.tile(theta,2*len(depth))
    radial = np.column_stack((np.sin(theta),-np.cos(theta),np.zeros(len(theta))))
    for length, flare in ((.014,.004),(.010,.0025),(.010,0.),(.007,.002),(.005,.0015),(.003,.0008)):
        p = (points+(taper*flare)[:,None]*radial).astype(np.float32)
        p[:,2] -= length*taper
        p = fit.constrain_rest(p)
        result = fit.scan(p,weights,edges=False)
        print("HEM",length,flare,float(result[0].min()),int(result[1].sum()),flush=True)
        if result[0].min()>=.00056 and result[0][0].max()<.029 and not result[1].any():
            fields["points"] = p
            np.savez(checkpoint,**fields)
            return


def clear_triangle_contacts(motion, checkpoint):
    """Repair face interiors where all vertices already have safe clearance."""
    with np.load(checkpoint) as data:
        fields = dict(data)
    points,triangles,weights,paired = (
        fields[key] for key in ("points","triangles","weights","paired"))
    samples = np.arange(len(motion[0]))
    fit = ContactFit(motion,triangles,paired,samples)
    half = len(points)//2
    opposite = np.empty(half,dtype=np.int32)
    for outer,inner in paired:
        opposite[outer] = inner
    witness = runpy.run_path(str(PARTS/"hoodie-fit-sol/round3/fit_hoodie_round3.py"))["pair_witnesses"]
    for iteration in range(6):
        distances,counts,skin,poses,*_ = fit.scan(points,weights,edges=False)
        print("FACE CONTACTS",iteration,int(counts.sum()),float(distances.min()),flush=True)
        if not counts.any() or distances.min()<.00050:
            break
        ranked = []
        for row in np.flatnonzero(counts):
            body_tree = fit.body(row)
            garment_tree = BVHTree.FromPolygons(poses[row].tolist(),fit.polys,all_triangles=True)
            pairs = np.asarray(body_tree.overlap(garment_tree))
            face_ids,blend = witness(poses[row],triangles,motion[2][row],motion[3],pairs[:,::-1])
            query = np.einsum("ni,nij->nj",blend,poses[row,triangles[face_ids]])
            gap,_,normals,_ = nearest(body_tree,query)
            for face in np.unique(pairs[:,1]):
                ids = np.flatnonzero(face_ids==face)
                worst = ids[gap[ids].argmin()]
                ranked.append((float(gap[worst]),row,int(face),normals[worst]))
        accepted = None
        print("FACE SET",[(str(motion[0][r]),float(motion[1][r]),f,d) for d,r,f,_ in ranked],flush=True)
        for _,row,face,normal in sorted(ranked,key=lambda item: item[0]):
            corners = triangles[face]
            center = points[fit.other[corners]].mean(axis=0)
            axis = normal @ skin[row,corners,:,:3].mean(axis=0)
            axis /= max(1e-8,np.linalg.norm(axis))
            now = counts.sum()
            for radius in (.012,.019,.026):
                kernel = smooth(1-np.linalg.norm(points[:half]-center,axis=1)/radius)
                kernel[fit.other[corners]] = np.maximum(.8,kernel[fit.other[corners]])
                active = np.flatnonzero(kernel>.01)
                moved = np.r_[active,opposite[active]]
                gain = kernel[fit.other[moved]]
                affected = triangles[np.isin(triangles,moved).any(axis=1)]
                local_ids, lookup = np.unique(affected,return_inverse=True)
                local_faces = lookup.reshape(affected.shape).tolist()
                slots = np.searchsorted(local_ids,moved)
                base = points[moved].copy()
                row_list = np.unique(np.r_[0, samples[::31], samples[counts>0],
                                           np.argsort(distances[:,moved].min(axis=1))[:80]])
                original_local = poses[row_list[:,None],local_ids]
                baseline = sum(len(fit.body(r).overlap(BVHTree.FromPolygons(xyz.tolist(),local_faces,
                                                                     all_triangles=True)))
                               for r,xyz in zip(row_list,original_local,strict=True))
                radial = center.copy()
                radial[:2] -= CENTER
                radial[2] = 0.
                radial /= max(1e-8,np.linalg.norm(radial))
                offsets = [axis*f for f in (.00030,.00062,.0011,.00175,.0027,.0040,.0056,-.0007,-.0018)]
                offsets += [v*f for v in (radial,-radial,np.array((0,0,1)),np.array((0,0,-1)))
                            for f in (.0008,.0016,.0028,.0045)]
                for offset in offsets:
                    delta = gain[:,None]*offset
                    rest = base+delta
                    gap, near, _, _ = nearest(fit.body(0),rest)
                    if gap.min()<.00061 or np.linalg.norm(rest-near,axis=1).max()>.0296:
                        continue
                    transformed = np.einsum("rvij,vj->rvi",skin[row_list[:,None],moved,:3,:3],delta)
                    patched = poses[row_list[:,None],local_ids].copy()
                    patched[:,slots] += transformed
                    rejected = False
                    local_count = 0
                    for r,new in zip(row_list,patched,strict=True):
                        tree = fit.body(r)
                        if nearest(tree,new[slots])[0].min()<.00055:
                            rejected = True
                            break
                        local_count += len(tree.overlap(BVHTree.FromPolygons(new.tolist(),local_faces,
                                                                          all_triangles=True)))
                        if local_count >= baseline:
                            rejected = True
                            break
                    if rejected or local_count >= baseline:
                        continue
                    candidate = points.copy()
                    candidate[moved] = rest
                    test = fit.scan(candidate,weights,edges=False)
                    if test[0].min()>=.00055 and test[1].sum()<now:
                        accepted = candidate
                        print("FACE PATCH",motion[0][row],motion[1][row],face,radius,offset.tolist(),
                              "remaining",int(test[1].sum()),flush=True)
                        break
                if accepted is not None:
                    break
            if accepted is not None:
                break
        if accepted is None:
            break
        points = fields["points"] = accepted
        np.savez(checkpoint,**fields)


def try_diagonals(motion, checkpoint):
    """Try the second diagonal in the few nonplanar quads with contacts."""
    with np.load(checkpoint) as data:
        fields = dict(data)
    points,triangles,weights,paired = (fields[key] for key in ("points","triangles","weights","paired"))
    rows = np.arange(len(motion[0]))
    fit = ContactFit(motion,triangles,paired,rows)
    d,counts,_,poses,*_ = fit.scan(points,weights,edges=False)
    if not counts.any():
        return
    affected = set()
    for row in np.flatnonzero(counts):
        tree = BVHTree.FromPolygons(poses[row].tolist(),fit.polys,all_triangles=True)
        pairs = fit.body(row).overlap(tree)
        affected.update(int(j//2*2) for _,j in pairs)
        print("TESSELLATION",motion[0][row],motion[1][row],[j for _,j in pairs],flush=True)
    if len(affected)>12:
        return
    choices = [affected,*({i} for i in sorted(affected))]
    current = counts.sum()
    for chosen in choices:
        candidate = triangles.copy()
        for start in chosen:
            a,b,c = triangles[start]
            x,y,h = triangles[start+1]
            if a!=x or c!=y:
                break
            candidate[start:start+2] = (a,b,h),(b,c,h)
        else:
            fit.triangles,fit.polys = candidate,candidate.tolist()
            result = fit.scan(points,weights,edges=False)
            count = int(result[1].sum())
            print("DIAGONALS",sorted(chosen),count,flush=True)
            if count<current and result[0].min()>=.00052:
                current = count
                fields["triangles"] = candidate
                np.savez(checkpoint,**fields)
                if not current:
                    break
                triangles = candidate


def fit_buckle(motion, checkpoint):
    """Fit the closed frame against the posed body, including seated torso flex."""
    from skirt_surface import add_buckle
    with np.load(checkpoint) as data:
        fields = dict(data)
    points,triangles,weights,paired = (
        fields[key] for key in ("points","triangles","weights","paired"))
    samples = np.arange(len(motion[0]))
    base_offset = fields.get("buckle_offset",np.zeros(3))
    p,t,w = add_buckle(points,triangles,weights,base_offset)
    t = t[len(triangles):] - len(points)
    fitter = ContactFit(motion,t,paired,samples)
    center = p[-32:]
    skin = np.einsum("vk,rkij->rvij",w[-32:],motion[4],optimize=True)
    poses = np.einsum("rvij,vj->rvi",skin[:,:,:,:3],center)+skin[:,:,:,3]

    def measure(posed, rows):
        distances,counts = [], []
        for row,xyz in zip(rows,posed,strict=True):
            tree = fitter.body(row)
            d,q,_,_ = nearest(tree,xyz)
            target = BVHTree.FromPolygons(xyz.tolist(),fitter.polys,all_triangles=True)
            counts.append(len(tree.overlap(target)))
            distances.append(float(d.min()))
            if row == 0 and np.linalg.norm(xyz-q,axis=1).max()>.0297:
                return np.full(len(rows),-1.), np.full(len(rows),999)
        return np.array(distances),np.array(counts)

    gaps,counts = measure(poses,samples)
    worst = gaps.argmin()
    print("BUCKLE INPUT",float(gaps.min()),int(counts.sum()),motion[0][worst],motion[1][worst],flush=True)
    if gaps.min()>=.00073 and not counts.any():
        return
    order = np.argsort(gaps)
    hot = np.unique(np.r_[0, samples[::35], order[:120], np.flatnonzero(counts>0)])
    choices = [(0.,0.,dz) for dz in (-.0009,.0009,-.0016,.0016)]
    choices += [(0.,dy,dz) for dy in (-.0006,-.0011,-.0017,.0005,.0011,-.0024)
               for dz in (0.,-.0009,-.0017,.0009)]
    for scale in (1.,.88,.75):
        for choice in choices:
            trial = add_buckle(points,triangles,weights,base_offset+choice,scale)[0][-32:]
            adjusted = poses + np.einsum("rvij,vj->rvi",skin[:,:,:,:3],trial-center)
            d,n = measure(adjusted[hot],hot)
            if d.min()>=.00073 and not n.any():
                d,n = measure(adjusted,samples)
                print("BUCKLE TRIAL",choice,scale,float(d.min()),int(n.sum()),flush=True)
                if d.min()>=.00064 and not n.any():
                    fields["buckle_offset"] = base_offset+choice
                    fields["buckle_scale"] = scale
                    np.savez(checkpoint,**fields)
                    return
    print("BUCKLE: only the integrated Studio belt clears the fitted body",flush=True)
    fields["buckle_scale"] = 0.
    np.savez(checkpoint,**fields)


def match_wall_diagonals(motion, checkpoint):
    """Pair the wall tessellation and retain any diagonals required for body clearance."""
    from skirt_surface import SIDES

    with np.load(checkpoint) as data:
        fields = dict(data)
    points,original,weights,paired,depth = (
        fields[key] for key in ("points","triangles","weights","paired","depth"))
    width = 2*SIDES
    first_inside = len(depth)*width
    last_inside = (2*len(depth)-1)*width
    opposite = np.empty(len(points)//2,dtype=np.int32)
    for outer,inner in paired:
        opposite[outer] = inner

    triangles = original.copy()
    for row in range(len(depth)-1):
        outside = row*width
        inside = (2*len(depth)-2-row)*width
        triangles[inside:inside+width] = opposite[original[outside:outside+width]][:,::-1]

    fit = ContactFit(motion,triangles,paired,np.arange(len(motion[0])))
    for _ in range(3):
        signed,counts,_,posed,*_ = fit.scan(points,weights,edges=False)
        if signed.min() < .00061:
            return
        if not counts.any():
            fields["triangles"] = triangles
            np.savez(checkpoint,**fields)
            return
        rejected = set()
        for row in np.flatnonzero(counts):
            garment = BVHTree.FromPolygons(posed[row].tolist(),fit.polys,all_triangles=True)
            for _,face in fit.body(row).overlap(garment):
                if first_inside <= face < last_inside:
                    rejected.add(face//2*2)
        for start in rejected:
            triangles[start:start+2] = original[start:start+2]
        fit.polys = triangles.tolist()
