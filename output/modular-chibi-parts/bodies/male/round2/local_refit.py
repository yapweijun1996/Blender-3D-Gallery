"""Search residual pockets across poses with per-group displacement and weight trials."""
from robust_refit import *


def candidate_field(g,constraints,trust,prioritize):
    group,axes,need,touch = map(np.concatenate,zip(*constraints))
    count = len(g.group_rep)
    affected = np.zeros(count,dtype=bool)
    affected[group[touch]] = True
    mask = affected[group]
    group,axes,need,touch = group[mask],axes[mask],need[mask],touch[mask]
    largest = np.zeros(count)
    np.maximum.at(largest,group,need)
    sizes = np.bincount(group,minlength=count).clip(1,None)
    hit = touch & (need>=largest[group])
    axis = np.zeros((count,3))
    axis[group[hit]] = axes[hit]
    outward = g.guide[g.group_rep]
    points = g.base[g.group_rep]
    radial = normalized(np.column_stack((points[:,0]-.0019,points[:,1]+.0248,np.zeros(count))))
    directions = [axis,outward,-outward,radial,-radial,normalized(axis+radial),normalized(axis+outward)]
    for vector in np.eye(3).tolist():
        directions.extend((np.tile(vector,(count,1)),-np.tile(vector,(count,1))))
    current_score = np.full(count,np.inf)
    best = np.zeros_like(axis)
    guard = np.where(touch,1.,2.75)
    for direction in directions:
        cosine = np.einsum('ij,ij->i',axes,direction[group])
        scale = np.zeros(count)
        initial = np.where((cosine>.36)&touch,need/np.maximum(cosine,.36),0.)
        np.maximum.at(scale,group,initial)
        for gain in (0.30,0.60,0.90,1.1):
            proposed = np.minimum(scale*gain,trust)
            deficit = np.maximum(0.,need-cosine*proposed[group])*guard
            maximum = np.zeros(count)
            np.maximum.at(maximum,group,deficit)
            loss = np.bincount(group,deficit**2,minlength=count)/sizes
            loss += (1.6 if prioritize else .42)*maximum**2 + .0012*proposed**2
            win = loss<current_score
            current_score[win] = loss[win]
            best[win] = direction[win]*proposed[win,None]
    inverse = g.graph[0]
    axis = normalized(best)
    move = best[inverse]
    for _ in range(3):
        blended = welded(.74*move+.26*laplacian(move,g.graph),g.graph)
        before = np.einsum('ij,ij->i',move[g.group_rep],axis)
        after = np.einsum('ij,ij->i',blended[g.group_rep],axis)
        move = blended + (axis*np.maximum(0,before-after)[:,None])[inverse]
    def apply(amount):
        delta = g.position-g.base+move*amount
        delta *= np.minimum(1.,.03/np.linalg.norm(delta,axis=1,keepdims=True).clip(1.e-9,None))
        return (g.base+delta).astype(np.float32)
    return [apply(1.),apply(.63),apply(.31)],affected[inverse]


def patch_weights(g,mask,x):
    blend = mask.astype(np.float32)*x
    for _ in range(3):
        blend = np.maximum(blend,laplacian(blend,g.graph)*.65)
    original,donor = g.w,g.body_weights
    # Transfer only across compatible anatomical zones. A skirt near a
    # passing hand must keep its pelvis and leg influences.
    both = (original*donor).sum(axis=1)
    compatible = both>.20
    blend *= compatible
    w = limit_weights(welded(original+(donor-original)*blend[:,None],g.graph)).astype(np.float32)
    return w


def shape_trials(g,cycle):
    p = g.base
    x,y,z = p.T
    if g.key=='jeans':
        radial = normalized(np.column_stack((x-.0019,(y+.0248)*1.3,np.zeros(len(p)))))
        waiver = np.clip((z-.287)/.080,0.,1.)
        top = np.clip((.467-z)/.038,0.,1.)
        weight = waiver**2*top
        axis = radial*weight[:,None]
        gains = (.003,.006)
    elif g.key=='dress':
        # Give the left-front skirt panel a little room from the swinging thumb.
        radius = ((x-.128)/.038)**2+((y+.006)/.043)**2+((z-.306)/.048)**2
        gain = np.exp(-radius*.8)
        axis = gain[:,None]*np.array([-1.,-.22,.18])
        gains = (.004,.007)
    else:
        return []
    if cycle:
        gains = tuple(v*.63 for v in gains)
    candidates = []
    for strength in gains:
        delta = g.position-g.base+welded(axis*strength,g.graph)
        delta *= np.minimum(1.,.03/np.linalg.norm(delta,axis=1,keepdims=True).clip(1.e-9,None))
        candidates.append((g.base+delta).astype(np.float32))
    return candidates


def set_weights(g,w):
    g.w = w
    g.ids,g.packed = influences(w)
    g.representatives,g.inverse = unique_vertices(g.base,w)


def solve_local(keys,cycles):
    _,arm,body,_ = load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names = [bone.name for bone in arm.data.bones]
    samples = sample_bank(body,names)
    _,faces = arrays(body)
    slots = {c:[i for i,s in enumerate(samples) if s.clip==c] for c in ('rest',*CLIPS)}
    for key in keys:
        g = GuardedGarment(key,read_module(HERE/f'male-{key}.glb',arm),names,.027,body)
        g.resume()
        dense = OUT/'qa'/f'fit-residual-{key}.json'
        observed = json.loads(dense.read_text()) if dense.exists() else []
        support = {0}
        for c,indices in slots.items():
            support.update([*indices[::21],indices[-1]])
            for f in FRAME_HINTS.get(c,()):
                support.add(min(indices,key=lambda i:abs(samples[i].frame-f)))
        if observed:
            worst = sorted(observed,key=lambda r:(r[4],-r[3],-r[2]))
            witness = worst[:45]+list(reversed(sorted(observed,key=lambda r:r[3])))[:45]
            witness.extend(observed[::max(1,len(observed)//75)])
            for c,f,*_ in witness:
                support.add(min(slots[c],key=lambda i:abs(samples[i].frame-f)))
        ids = sorted(support)
        for i in ids:
            if samples[i].cached_tree is None:
                samples[i].cached_tree = tree(samples[i].body,samples[i].faces)
        def scan(indices,collect):
            records,opts = [],[]
            for i in indices:
                row,option = g.examine(samples[i],samples[i].cached_tree,faces,collect)
                records.append(row)
                if option is not None:
                    opts.append(option)
            return np.stack(records),opts
        for cycle in range(cycles):
            rows,opts = scan(ids,True)
            score = rank(rows)
            old_pos,old_w = g.position.copy(),g.w.copy()
            g.history.append(details(rows,g,samples,ids,f'local cycle {cycle} start'))
            if not score[0]:
                break
            options,mask = candidate_field(g,opts,.0045 if cycle<2 else .0025,cycle%2==0)
            options.extend(g.suggestions(opts,.0035,True)[:2])
            options.extend(shape_trials(g,cycle))
            selection = [j for j,row in enumerate(rows) if row[0]+row[1]>0 or row[2]<.0005 or j%7==0]
            subset = [ids[j] for j in selection]
            baseline = rank(rows[selection])
            def depth_penalty(distance):
                return max(0.,-.0005-distance)*110000
            def merit(r):
                return r[1] + r[0]*1.6 + depth_penalty(r[2])
            winner = old_pos,old_w,merit(baseline)
            def turn(pos,w):
                nonlocal winner
                g.position = pos
                set_weights(g,w)
                outcome,_ = scan(subset,False)
                r = rank(outcome)
                if merit(r)<winner[2]:
                    winner = pos.copy(),w.copy(),merit(r)
            for p in options:
                turn(p,old_w)
            if cycle%2==0:
                for strength in (.22,.46):
                    set_weights(g,old_w)
                    w = patch_weights(g,mask,strength)
                    turn(old_pos,w)
                    turn(options[1],w)
            g.position,w,_ = winner
            set_weights(g,w)
            rows,_ = scan(ids,False)
            new = rank(rows)
            if merit(new)>=merit(score):
                g.position = old_pos
                set_weights(g,old_w)
            else:
                g.history.append(details(rows,g,samples,ids,f'local cycle {cycle} accepted'))
            g.persist(arm,names)
            print('LOCAL CYCLE',key,cycle,score,new,flush=True)


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    solve_local(args[0].split(','),int(args[1]))
