"""Resolve isolated signed-distance failures with exact per-vertex trials."""
from local_refit import *
from itertools import product


def quality(rows):
    d = rows[:,2]
    return float((rows[:,0]*2.5+rows[:,1]).sum() + np.maximum(.0005-d,0).sum()*55000
                 + max(0.,-.0005-float(d.min()))*140000
                 + np.count_nonzero((d<.0005)|(rows[:,:2].sum(axis=1)>0))*1.8)


def gather(g,samples,support):
    positions = g.position[g.group_rep]
    ds,ns,ms = [],[],[]
    for i in support:
        sample = samples[i]
        if sample.cached_tree is None:
            sample.cached_tree = tree(sample.body,sample.faces)
        basis = g.basis(sample)[g.group_rep]
        posed = np.einsum('vij,vj->vi',basis[:,:,:3],positions)+basis[:,:,3]
        dist,n,_ = nearest(sample.cached_tree,posed)
        ds.append(dist)
        ns.append(n)
        ms.append(basis)
    return np.asarray(ds),np.asarray(ns),np.asarray(ms)


def signed_at(bvh,items):
    distances = []
    for p in items.tolist():
        loc,n,_,_ = bvh.find_nearest(p)
        distances.append((p[0]-loc.x)*n.x+(p[1]-loc.y)*n.y+(p[2]-loc.z)*n.z)
    return distances


def adjust(g,samples,support,d,n,m,limit):
    old = g.position.copy()
    guide = g.guide[g.group_rep]
    out = np.zeros((len(g.group_rep),3),dtype=np.float32)
    ranked = np.argsort(d.min(axis=0))
    active = [k for k in ranked if d[:,k].min()<.00058][:limit]
    for k in active:
        group_index = g.group_rep[k]
        distances = d[:,k]
        near = np.flatnonzero(distances<.010)
        s = near if len(near)<65 else np.unique(np.r_[near[::max(1,len(near)//40)],np.argsort(distances)[:30]])
        bad = np.argsort(distances)[:6]
        gradients = np.einsum('fji,fj->fi',m[bad,k,:,:3],n[bad,k])
        radial = normalized(np.array([old[group_index,0]-.0019,old[group_index,1]+.0248,0]))
        directions = np.stack([*gradients,gradients.mean(axis=0),guide[k],-guide[k],radial,-radial,
                               *[x for x in product((-1,0,1),repeat=3) if any(x)]])
        directions = np.unique(np.round(normalized(directions),4),axis=0)
        steps = np.array([.00045,.0009,.0015,.0024,.0035,.005,.0075,.011,.016])
        positions = old[group_index]+(directions[:,None,:]*steps[None,:,None]).reshape(-1,3)
        positions = np.concatenate((old[group_index][None,:],positions))
        radius = np.linalg.norm(positions-g.base[group_index],axis=1)
        positions = positions[radius<=.030]
        collision = np.zeros(len(positions),dtype=np.float64)
        lowest = np.full(len(positions),np.inf)
        count = np.zeros(len(positions),dtype=np.int32)
        for f in s:
            matrix = m[f,k]
            test = positions @ matrix[:,:3].T + matrix[:,3]
            sig = np.array(signed_at(samples[support[f]].cached_tree,test))
            lowest = np.minimum(lowest,sig)
            collision += np.maximum(.00074-sig,0)**1.25
            count += sig<.00058
        size = np.linalg.norm(positions-old[group_index],axis=1)
        rank = (count*.004 + collision + np.maximum(.0006-lowest,0)*9 + size*.018)
        best = np.argmin(rank)
        out[k] = positions[best]-old[group_index]
    inv = g.graph[0]
    field = out[inv]
    selected = np.linalg.norm(out,axis=1)>0
    for _ in range(3):
        smooth = welded(.72*field+.28*laplacian(field,g.graph),g.graph)
        smooth[selected[inv]] = out[inv[selected[inv]]]
        field = smooth
    return field,len(active)


def exact(keys,cycles):
    _,arm,body,_ = load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names = [bone.name for bone in arm.data.bones]
    samples = sample_bank(body,names)
    _,faces = arrays(body)
    slots = {c:[i for i,s in enumerate(samples) if s.clip==c] for c in ('rest',*CLIPS)}
    for k in keys:
        g = GuardedGarment(k,read_module(HERE/f'male-{k}.glb',arm),names,.027,body)
        g.resume()
        report = OUT/'qa'/f'fit-residual-{k}.json'
        observed = json.loads(report.read_text()) if report.exists() else []
        support = {0}
        for key,indices in slots.items():
            support.update([*indices[::25],indices[-1]])
            for f in FRAME_HINTS.get(key,()):
                support.add(min(indices,key=lambda i:abs(samples[i].frame-f)))
        witness = sorted(observed,key=lambda r:r[4])[:70]
        witness.extend(sorted(observed,key=lambda r:r[3],reverse=True)[:60])
        witness.extend(observed[::max(1,len(observed)//150)])
        for key,f,*_ in witness:
            support.add(min(slots[key],key=lambda i:abs(samples[i].frame-f)))
        for key in ('walk','run'):
            support.update(slots[key][::2])
        support = sorted(support)
        def scan(subset,collect=False):
            rows,opts = [],[]
            for i in subset:
                a,b = g.examine(samples[i],samples[i].cached_tree,faces,collect)
                rows.append(a)
                if b is not None:
                    opts.append(b)
            return np.stack(rows),opts
        for cycle in range(cycles):
            d,n,m = gather(g,samples,support)
            rows,opts = scan(support,True)
            prior = quality(rows)
            g.history.append(details(rows,g,samples,support,f'exact {cycle} start'))
            if not rank(rows)[0]:
                break
            field,affected = adjust(g,samples,support,d,n,m,170)
            pos = g.position.copy()
            candidates = []
            for fraction in (1.,.65,.36):
                delta = pos-g.base+fraction*field
                delta *= np.minimum(1.,.03/np.linalg.norm(delta,axis=1,keepdims=True).clip(1.e-9,None))
                candidates.append((g.base+delta).astype(np.float32))
            candidates.extend(candidate_field(g,opts,.0026,True)[0][:2])
            witness = [i for i,row in enumerate(rows) if row[0]+row[1]>0 or row[2]<.0005 or i%11==0]
            subset = [support[i] for i in witness]
            winner = pos
            best = quality(rows[witness])
            for proposed in candidates:
                g.position = proposed
                trial,_ = scan(subset)
                score = quality(trial)
                if score<best:
                    best,winner = score,proposed
            g.position = winner
            after,_ = scan(support)
            if quality(after)>=prior:
                g.position = pos
            else:
                g.history.append(details(after,g,samples,support,f'exact {cycle} accepted'))
            g.persist(arm,names)
            print('EXACT',k,cycle,affected,prior,quality(after),flush=True)


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    exact(args[0].split(','),int(args[1]))
