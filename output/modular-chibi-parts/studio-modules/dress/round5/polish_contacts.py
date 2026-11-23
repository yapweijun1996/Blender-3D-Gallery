"""Local finishing around a handful of residual contact triangles."""
import numpy as np
from mathutils.bvhtree import BVHTree


def move_patch(pivot, radius, points, weights, faces, posed, skin, signed,
               contacts, samples, matrices, anatomy, api):
    """Rank smooth position and weight changes, then check all affected poses."""
    r1,r2,helpers = api
    clearance = helpers["clearance"]
    d = np.linalg.norm(points-points[pivot],axis=1)
    changed = np.flatnonzero(d<radius)
    fall = (1-d[changed]/radius)
    fall = (fall**2*(3-2*fall))[:,None]
    mask = np.isin(faces,changed).any(axis=1)
    global_faces = faces[mask]
    loc,index = np.unique(global_faces.ravel(),return_inverse=True)
    local_faces = index.reshape(-1,3)
    moving = np.searchsorted(loc,changed)
    old_p, old_w = points[changed], weights[changed]
    rest = samples[0][2]
    bary = r2["REST_BARYCENTRICS"]
    baseline_shape = points[global_faces]
    normal = np.cross(baseline_shape[:,1]-baseline_shape[:,0],baseline_shape[:,2]-baseline_shape[:,0])
    area_squared = (normal**2).sum(axis=1)
    overlaps = {}
    local_face_ids = np.flatnonzero(mask)
    for row, pairs in contacts.items():
        own = pairs[np.isin(pairs[:,1],local_face_ids)]
        if len(own):
            overlaps[row] = own
    priority = np.maximum(.00068-signed[:,loc],0).max(axis=1)
    for row, pairs in overlaps.items():
        priority[row] += .00010*len(pairs)
    hot = np.flatnonzero(priority > 0)
    if not len(hot):
        return
    clock = []
    for i in hot[np.argsort(-priority[hot],kind="stable")]:
        if all(abs(i-j)>2 for j in clock):
            clock.append(i)
        if len(clock)>=18:
            break
    short = np.unique(np.r_[0, clock, np.arange(1,len(samples),41)])
    contact_frames = sorted(overlaps,key=lambda row: -len(overlaps[row]))
    rays = []
    for row in contact_frames[:24]:
        name, frame, tree, body, bt = samples[row]
        witnesses, coeff = r1["pair_witnesses"](posed[row],faces,body,bt,overlaps[row][:,::-1])
        pts = np.einsum("fi,fij->fj",coeff,posed[row,faces[witnesses]])
        gap, normals, _ = clearance(tree,pts)
        for i in np.argsort(gap,kind="stable")[:2]:
            n = normals[i] @ skin[row,pivot,:,:3]
            n /= np.linalg.norm(n).clip(1e-8)
            if all(abs(n @ a)<.96 for a in rays):
                rays.append(n)
    for row in clock[:14]:
        n = clearance(samples[row][2],posed[row,pivot:pivot+1])[1][0] @ skin[row,pivot,:,:3]
        n /= np.linalg.norm(n).clip(1e-8)
        if all(abs(n @ a)<.95 for a in rays):
            rays.append(n)
    rays.extend(np.eye(3,dtype=np.float32))
    face_list = local_faces.tolist()
    all_frames = np.arange(len(samples))

    def score(delta, candidate_weights, rows, check_shape=True):
        trial = old_p+delta
        local = posed[rows[:,None],loc].copy()
        local[:,moving] = r2["skin_poses"](trial,*r2["sparse_weights"](candidate_weights),matrices[rows])[0]
        if check_shape and delta.any():
            shape = local[0,local_faces]
            cross = np.cross(shape[:,1]-shape[:,0],shape[:,2]-shape[:,0])
            if np.any((cross*normal).sum(axis=1)<area_squared*.20):
                return float("inf")
            d = clearance(rest,np.vstack((trial,np.einsum("vi,fij->fvj",bary,shape).reshape(-1,3))))[0]
            if d.min()<.00052 or d.max()>.03001:
                return float("inf")
        value = 0.
        worst = 0.
        for f,r in enumerate(rows):
            tree = samples[r][2]
            signed = clearance(tree,local[f])[0]
            hard = np.maximum(.000515-signed,0)*1000
            soft = np.maximum(.00059-signed,0)*1000
            pairs = len(tree.overlap(BVHTree.FromPolygons(local[f].tolist(),face_list,all_triangles=True)))
            value += pairs*12 + float(hard@hard)*110 + float(soft@soft)*.55
            worst = max(worst,float(hard.max()))
        return value+1000*worst**2

    zero = np.zeros_like(old_p)
    initial = score(zero,old_w,short,False)
    proposals = []
    minimum = min(.0015,max(.00012,.5*float(priority.max())))
    amplitudes = np.unique(np.r_[.00018,.00040,.00075,.00135,.0024,.0038,minimum])
    for ray in rays[:14]:
        for amplitude in np.r_[amplitudes,-amplitudes]:
            delta = fall * (amplitude*ray)
            value = score(delta,old_w,short)
            if value < initial:
                proposals.append((value,delta,old_w))
    directions = [zero]+[x[1] for x in sorted(proposals,key=lambda v:v[0])[:3]]
    support = [anatomy[changed]]
    current = weights[pivot] + anatomy[pivot]*.3
    for b in np.argsort(-current)[:6]:
        w = np.zeros_like(old_w)
        w[:,b] = 1.
        support.append(w)
    for target in support:
        for amount in (.07,.19,.38,.65):
            w = r2["limit_weights"](old_w+(amount*fall)*(target-old_w))
            for delta in directions:
                value = score(delta,w,short)
                if value < initial:
                    proposals.append((value,delta,w))
    if not proposals:
        return
    initial = score(zero,old_w,all_frames,False)
    best = None
    for _,delta,w in sorted(proposals,key=lambda v:v[0])[:12]:
        value = score(delta,w,all_frames)
        if value < initial-1e-5:
            quantized_penalty = 1e-4*float(((delta*1000)**2).sum())
            best = changed,old_p+delta,w,value,initial-value
            if value < .0001:
                break
            initial = value+min(1e-5,quantized_penalty)
    return best


def lift_vertex(vertex, points, weights, faces, posed, skin, signed, samples,
                matrices, anatomy, api, rng):
    """Maximize the least signed clearance while preserving adjacent faces."""
    r2,helpers = api
    clearance = helpers["clearance"]
    original = points[vertex]
    current = weights[vertex]
    faces = faces[(faces==vertex).any(axis=1)]
    ids,local = np.unique(faces.ravel(),return_inverse=True)
    face_list = local.reshape(-1,3).tolist()
    pivot = np.searchsorted(ids,vertex)
    reference = points[faces]
    normal = np.cross(reference[:,1]-reference[:,0],reference[:,2]-reference[:,0])
    critical = np.argsort(signed[:,vertex],kind="stable")[:15]
    inspected = np.unique(np.r_[0, np.flatnonzero(signed[:,vertex]<.0035),
                                np.arange(1,len(samples),29)])
    count = 2200
    base_slots = np.argsort(-current,kind="stable")[:4]
    optional = [b for b in np.argsort(-(current+anatomy[vertex]*.3),kind="stable")[:9]
                if b not in base_slots]
    columns = np.tile(base_slots,(count,1))
    for j,bone in enumerate(optional):
        columns[900+j*200:1100+j*200,-1] = bone
    base = current[columns]
    base /= base.sum(axis=1,keepdims=True)
    widths = np.array([.00015,.00037,.0007,.00135,.0024,.0039],np.float32)
    delta = rng.standard_normal((count,3)).astype(np.float32)*widths[np.arange(count)%len(widths),None]
    increments = np.array([.003,.009,.024,.047,.084],np.float32)
    noise = rng.standard_normal((count,4)).astype(np.float32)*increments[np.arange(count)%5,None]
    noise[:580] = 0
    delta[580:850] = 0
    for j,row in enumerate(critical[:10]):
        grad = clearance(samples[row][2],posed[row,vertex:vertex+1])[1][0] @ skin[row,vertex,:,:3]
        grad /= np.linalg.norm(grad).clip(1e-8)
        delta[j*16:(j+1)*16] = np.linspace(.00009,.0036,16)[:,None]*grad
    alternatives = original + delta
    blends = r2["simplex"](base+noise)
    rest = samples[0][2]
    rest_gaps = clearance(rest,alternatives)[0]
    allowed = (rest_gaps > .00054) & (rest_gaps < .029999)
    shape = np.broadcast_to(reference[None],(count,*reference.shape)).copy()
    shape[:,faces==vertex] = alternatives[:,None]
    cross = np.cross(shape[:,:,1]-shape[:,:,0],shape[:,:,2]-shape[:,:,0])
    allowed &= (np.einsum("cfi,fi->cf",cross,normal) > .28*(normal**2).sum(axis=1)).all(axis=1)
    minima = np.full(count,1.,np.float32)
    for row in inspected:
        local = matrices[row,columns]
        predicted = np.einsum("cb,cbij,cj->ci",blends,local[...,:3],alternatives)
        predicted += np.einsum("cb,cbi->ci",blends,local[...,3])
        gaps = clearance(samples[row][2],predicted)[0]
        minima = np.minimum(minima,gaps)
    # Prefer increasing clearance using the smallest local change.
    rank = np.minimum(.00065,minima)*1000 - np.linalg.norm(delta*1000,axis=1)*.015
    rank[~allowed] = -np.inf
    start_min = float(signed[:,vertex].min())
    patch = posed[:,ids].copy()
    for i in np.argsort(-rank,kind="stable")[:45]:
        if not allowed[i] or minima[i] < start_min+.000005:
            break
        proposed = np.zeros_like(current)
        proposed[columns[i]] = blends[i]
        moved, new_skin = r2["skin_poses"](alternatives[i:i+1],blends[i:i+1],columns[i:i+1],matrices)
        patch[:,pivot] = moved[:,0]
        d = np.asarray([clearance(s[2],p)[0][0] for s,p in zip(samples,moved,strict=True)])
        if d.min() < max(.000504,start_min+.00001):
            continue
        if any(sample[2].overlap(BVHTree.FromPolygons(xyz.tolist(),face_list,all_triangles=True))
               for sample,xyz in zip(samples,patch,strict=True)):
            continue
        return alternatives[i],proposed,moved[:,0],new_skin[:,0],d
