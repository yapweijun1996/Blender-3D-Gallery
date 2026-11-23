"""Apply localized clearance corrections to full-gate witness poses."""
import numpy as np

from bake import layer_pressure, pose_shell, required_on_pose, transforms
from body_audit import posed, set_frame, use_action
from fitting_geometry import barycentric,laplacian,limit_weights,tree,weld_graph
from fit_module import nearest
from garments import unit


def failed_frames(report, item):
    threshold = .0016 if item=='bottom-shorts' else .00085
    picks = {('rest',0.)}
    for clip, data in report['clips'].items():
        frames = data['frames']
        # Score in sections so a different contact later in the same clip
        # has a chance to affect the revision.
        chunks = np.array_split(np.arange(len(frames)),min(12,len(frames)))
        for indices in chunks:
            rows = [frames[i] for i in indices]
            critical = [min(rows,key=lambda r:r['min_signed_m']),
                        max(rows,key=lambda r:r['pairs'])]
            critical.extend(max(rows,key=lambda r:r['layer_pairs'][name])
                            for name in data['layer_peaks'] if data['layer_peaks'][name])
            picks.update((clip,row['frame']) for row in critical if row['pairs']
                         or any(row['layer_pairs'].values()) or row['min_signed_m']<threshold)
    return sorted(picks)


def clean_open_edges(p, f, item):
    edge, count = np.unique(np.sort(np.vstack((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1),
                            axis=0,return_counts=True)
    edge = edge[count==1]
    result = p.copy()
    if item=='bottom-shorts':
        cuffs = p[:,2]<.321
        hem = p[:,2]>.362
    else:
        cuffs = abs(p[:,0])>.265
        hem = (p[:,2]<.417)&(abs(p[:,0])<.15)
    for region in (cuffs,hem):
        pairs = edge[region[edge].all(axis=1)]
        a,b = np.vstack((pairs,pairs[:,::-1])).T
        degree = np.bincount(a,minlength=len(p))
        idx = np.flatnonzero(degree==2)
        for _ in range(3):
            avg = np.column_stack([np.bincount(a,weights=v[b],minlength=len(p))
                                   for v in result.T])*.5
            correction = avg[idx]-result[idx]
            result[idx] += .40*correction
    return result


def settle(p, f, w, item, scene, arm, body, bf, actions, layers, report, guide=None, donor=None):
    graph = weld_graph(p,f)
    faces, body_faces = f.tolist(),bf.tolist()
    bind = np.array([np.asarray(arm.data.bones[b.name].matrix_local.inverted()) for b in arm.pose.bones])
    ids = np.argpartition(w,-4,axis=1)[:,-4:]
    packets = w[np.arange(len(ids))[:,None],ids]
    cache, seen = [],set()
    for clip, frame in failed_frames(report,item):
        use_action(arm,actions.get(clip))
        set_frame(scene,frame)
        matrices = transforms(arm,bind)
        identity = np.round(matrices,5).tobytes()
        if identity in seen:
            continue
        seen.add(identity)
        fit,_ = pose_shell(p,matrices,ids,packets)
        close, lo, hi = [], fit.min(axis=0)-.04,fit.max(axis=0)+.04
        for obj, tri in layers.values():
            other = posed(obj)
            if (other.max(axis=0)>=lo).all() and (other.min(axis=0)<=hi).all():
                close.append(tree(other,tri))
        cache.append((matrices,tree(posed(body),body_faces),close))
    direction = np.zeros_like(p)
    x,y,z = p.T
    if item.startswith('top'):
        direction = unit(np.column_stack((x-.00191,y+.04,np.zeros(len(p)))))
    elif item=='bottom-skirt':
        direction = unit(np.column_stack((x-.00191,y+.0248,np.zeros(len(p)))))
    model = clean_open_edges(p,f,item) if item!='bottom-skirt' else p.copy()
    best,best_key = model.copy(),None
    history = []
    if guide is not None:
        alternatives = [model,.45*model+.55*guide,guide]
        scores = []
        for trial in alternatives:
            violations = 0.
            for matrices,surface,references in cache:
                fit,_ = pose_shell(trial,matrices,ids,packets)
                candidate = tree(fit,faces)
                dist,*_ = nearest(surface,fit)
                violations += len(surface.overlap(candidate))
                violations += sum(len(x.overlap(candidate)) for x in references)
                violations += 8400*np.maximum(0,.0005-dist).sum()
            scores.append(violations)
        model = alternatives[int(np.argmin(scores))]
        print('SETTLE START',item,scores,flush=True)
    last_improvement = -1
    for cycle in range(24):
        strongest, sum_delta, support = np.zeros(len(p)),np.zeros_like(p),np.zeros(len(p))
        largest = np.zeros_like(p)
        body_pairs, layer_pairs, inside, minimum = 0,0,0,1.
        for matrices, surface, references in cache:
            fit,basis = pose_shell(model,matrices,ids,packets)
            candidate = tree(fit,faces)
            hits = surface.overlap(candidate)
            need,normal,count,depth = required_on_pose(surface,fit,f,hits)
            body_pairs += len(hits)
            inside += count
            minimum = min(minimum,depth)
            at = np.flatnonzero(need>.00015)
            axes = np.einsum('vji,vj->vi',basis[at],normal[at])
            active = [(at,unit(axes),need[at]/np.maximum(.4,np.linalg.norm(axes,axis=1)))]
            for reference in references:
                pairs = reference.overlap(candidate)
                layer_pairs += len(pairs)
                if pairs:
                    active.append(layer_pressure(item,reference,fit,f,pairs,direction,basis))
            for at,axis,need in active:
                np.add.at(support,at,1)
                np.add.at(sum_delta,at,axis*need[:,None])
                better = need>strongest[at]
                selected = at[better]
                strongest[selected] = need[better]
                largest[selected] = axis[better]*need[better,None]
        key = (body_pairs+layer_pairs,inside,max(0.,(.0016 if item=='bottom-shorts' else .0009)-minimum))
        history.append(dict(pairs=body_pairs,layer_pairs=layer_pairs,inside=inside,minimum_m=minimum))
        improved = best_key is None or key<best_key
        if improved:
            best,best_key = model.copy(),key
            last_improvement = cycle
        if cycle%4==0:
            print('SETTLE',item,cycle,key,'poses',len(cache),flush=True)
        if key==(0,0,0.) or not strongest.any() or cycle-last_improvement>=6:
            break
        raw = .34*largest+.66*sum_delta/np.maximum(1,support[:,None])
        delta = raw.copy()
        for _ in range(4):
            delta = .72*delta+.28*laplacian(delta,graph)
        delta = .70*delta+.30*raw
        limit = .0020 if cycle<12 else .0012
        delta *= np.minimum(1,limit/np.maximum(1e-10,np.linalg.norm(delta,axis=1)))[:,None]
        model = (model + delta) if improved else (best + .34*delta)
    patches = []
    if best_key!=(0,0,0.) and item!='bottom-skirt':
        fitting_donor = donor if item in ('top-jacket','bottom-shorts') else None
        best,w,patches = patch_search(best,f,w,cache,item,ids,packets,fitting_donor)
    return best,w,dict(samples=len(cache),passes=history,patches=patches)


def patch_search(p, f, weights, cache, item, ids, packets, donor):
    """Search small coherent cloth patches where posed normals disagree."""
    face_list = f.tolist()
    stress = np.zeros(len(p))
    support = []
    clearance = .00160 if item=='bottom-shorts' else .00065
    for matrices, body_surface, layers in cache:
        fit,_ = pose_shell(p,matrices,ids,packets)
        surface = tree(fit,face_list)
        need,_,_,_ = required_on_pose(body_surface,fit,f,body_surface.overlap(surface))
        for layer in layers:
            collisions = layer.overlap(surface)
            if collisions:
                touched = np.unique(f[np.asarray(collisions)[:,1]])
                need[touched] = np.maximum(.002,need[touched])
        np.maximum(stress,need,out=stress)
        support.append((int(np.count_nonzero(need)),matrices,body_surface,layers))
    order = sorted(range(len(support)),key=lambda i:-support[i][0])
    take = sorted(set(order[:26])|set(range(0,len(support),max(1,len(support)//10))))
    bank = [support[i][1:] for i in take]
    directions = np.array([(i,j,k) for i in (-1,0,1) for j in (-1,0,1) for k in (-1,0,1)
                           if abs(i)+abs(j)+abs(k)])
    directions = unit(directions)
    result, applied = p.copy(),[]
    weights = weights.copy()
    if donor is not None:
        body, body_faces, source_skin = donor
        source = tree(body,body_faces.tolist())
    for _ in range(5):
        seed = int(stress.argmax())
        if stress[seed]<.0007:
            break
        dist = np.linalg.norm(p-p[seed],axis=1)
        mask = np.maximum(0,1-(dist/.030)**2)**2
        stress[dist<.024] = 0
        nearby = f[(mask[f]>0).any(axis=1)]
        verts, compact = np.unique(nearby,return_inverse=True)
        faces = compact.reshape(-1,3).tolist()
        local = result[verts]
        base = mask[verts,None]
        def weight_pack(values):
            bone_ids = np.argpartition(values,-4,axis=1)[:,-4:]
            return bone_ids,values[np.arange(len(values))[:,None],bone_ids]

        local_ids,local_weights = weight_pack(weights[verts])
        records = []
        for matrices, body_surface, layers in bank:
            before,basis = pose_shell(local,matrices,local_ids,local_weights)
            records.append((before,basis,body_surface,layers,matrices))

        def score(shift, subset, alternative=None):
            penalty, hits = 0.,0
            displacement = base*shift
            for original,basis,body_surface,layers,matrices in subset:
                if alternative is None:
                    fit = original+np.einsum('vij,vj->vi',basis,displacement)
                else:
                    fit,_ = pose_shell(local+displacement,matrices,*alternative)
                shell = tree(fit,faces)
                hits += len(body_surface.overlap(shell))
                hits += sum(len(obstacle.overlap(shell)) for obstacle in layers)
                depth,*_ = nearest(body_surface,fit)
                penalty += np.maximum(0,clearance-depth).sum()
            return hits + 4000*penalty
        zero = np.zeros(3)
        ranked = sorted(((score(zero,[entry]),i) for i,entry in enumerate(records)),reverse=True)
        narrow = [records[i] for _,i in ranked[:12]]
        baseline = sum(value for value,_ in ranked)
        if baseline==0:
            continue
        options = [(score(axis*step,narrow),axis*step)
                   for axis in directions for step in (.0018,.0036,.0060)]
        best, shift = baseline,zero
        for _, trial in sorted(options,key=lambda entry:entry[0])[:6]:
            value = score(trial,records)
            if value<best:
                best,shift = value,trial
        chosen_weights = None
        if donor is not None:
            transfer = []
            for point in local:
                hit,_,face,_ = source.find_nearest(point)
                ids_in_body = body_faces[face]
                transfer.append(barycentric(hit,body[ids_in_body]) @ source_skin[ids_in_body])
            original = weights[verts]
            concentrated = original**2
            concentrated /= concentrated.sum(axis=1,keepdims=True)
            for target in (np.asarray(transfer),concentrated):
                for strength in (.25,.55):
                    trial = limit_weights(original+strength*base*(target-original))
                    pack = weight_pack(trial)
                    value = score(shift,records,pack)
                    if value<best:
                        best,chosen_weights = value,trial
        if chosen_weights is not None:
            weights[verts] = chosen_weights
        result[verts] += base*shift
        applied.append(dict(seed_m=p[seed].tolist(),shift_m=shift.tolist(),before=float(baseline),
                            after=float(best),skin_adjusted=chosen_weights is not None))
    return result,weights,applied
