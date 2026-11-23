"""Polish connected contact patches against the exact triangle checker."""
from vertex_refit import *


def focused(g,samples,report):
    slots = {c:[i for i,s in enumerate(samples) if s.clip==c] for c in ('rest',*CLIPS)}
    seen = {0}
    for c,indices in slots.items():
        seen.update([*indices[::31],indices[-1]])
    if report.exists():
        data = json.loads(report.read_text())
        for clip,row in data['clips'].items():
            for f in row['frames']:
                if f['inside'] or f['triangle_pairs'] or f['min_signed_m']<.00054:
                    seen.add(min(slots[clip],key=lambda i:abs(samples[i].frame-f['frame'])))
    residual = OUT/'qa'/f'fit-residual-{g.key}.json'
    if residual.exists():
        old = json.loads(residual.read_text())
        for clip,f,*_ in old[::max(1,len(old)//75)]:
            seen.add(min(slots[clip],key=lambda i:abs(samples[i].frame-f)))
    return sorted(seen)


def collect(g,samples,ids):
    hits = {}
    groups = g.graph[0]
    for ix in ids:
        sample = samples[ix]
        if sample.cached_tree is None:
            sample.cached_tree=tree(sample.body,sample.faces)
        bvh = sample.cached_tree
        base = g.basis(sample)
        p = np.einsum('vij,vj->vi',base[:,:,:3],g.position)+base[:,:,3]
        d,n,_ = nearest(bvh,p[g.group_rep])
        pairs = bvh.overlap(tree(p,g.face_list))
        for v in np.flatnonzero(d<.00062):
            r = g.group_rep[v]
            hits.setdefault(int(v),[]).append((ix,base[r,:,:3].T@n[v],float(.0015-d[v])))
        if pairs:
            a,b = np.asarray(pairs).T
            tri = g.faces[b]
            q = (BARYCENTRIC @ p[tri]).reshape(-1,3)
            distance,normal,_ = nearest(bvh,q)
            distance=distance.reshape(len(tri),-1)
            best=distance.argmin(axis=1)
            normal=normal.reshape(len(tri),-1,3)[np.arange(len(tri)),best]
            depth = pair_depth(sample.body[np.asarray(sample.faces)[a]],p[tri])*.001
            require = MARGIN+np.maximum(np.maximum(-distance.min(axis=1),0),depth)
            for corners,normal,need in zip(tri,normal,require):
                for v in corners:
                    hits.setdefault(int(groups[v]),[]).append((ix,base[v,:,:3].T@normal,float(need)))
    return hits


def zones(g,hits):
    _,p,q,_,_=g.graph
    neighbors = {k:set(q[p==k]) for k in hits}
    live = set(hits)
    found = []
    while live:
        kernel = {live.pop()}
        while True:
            adjacent = set().union(*(neighbors[k] for k in kernel)) & live
            if not adjacent:
                break
            live -= adjacent
            kernel |= adjacent
        found.append(sorted(kernel))
    return found


def solve_zone(g,samples,support,zone,hits):
    inv,_,_,_,_=g.graph
    mask = np.isin(inv,zone).astype(np.float32)
    for _ in range(2):
        mask = np.maximum(mask,laplacian(mask,g.graph)*.72)
    face_ids = np.flatnonzero((mask[g.faces]>0).any(axis=1))
    verts,tri = np.unique(g.faces[face_ids],return_inverse=True)
    tri=tri.reshape(-1,3).tolist()
    local = g.position[verts]
    baseline = g.base[verts]
    influence = mask[verts]
    unit = []
    for k in zone:
        unit.extend(hits[k])
    hist = sorted({i for i,_,_ in unit})
    samples_to_try = sorted(set(hist)|set(support[::9]))
    sockets = []
    for i in samples_to_try:
        sample = samples[i]
        transform = (sample.transforms[g.ids[verts]]*g.packed[verts,:,None,None]).sum(axis=1)
        sockets.append((sample.cached_tree,transform))
    def rank_patch(position,subset):
        residual = power = maxdepth = 0.
        for j in subset:
            bvh,basis = sockets[j]
            pose = np.einsum('vij,vj->vi',basis[:,:,:3],position)+basis[:,:,3]
            clipped = len(bvh.overlap(tree(pose,tri)))
            d,_,_ = nearest(bvh,pose)
            residual += clipped
            power += float(np.maximum(.00055-d,0).sum())*7000
            maxdepth = max(maxdepth,-float(d.min()))
        return residual + power + maxdepth*16000
    full = list(range(len(sockets)))
    fast = [j for j,i in enumerate(samples_to_try) if i in hist]
    if len(fast)>35:
        fast=fast[::max(1,len(fast)//28)]
    fast=sorted(set(fast)|set(full[::13]))
    directions = sorted(unit,key=lambda item:item[2],reverse=True)
    means = np.array([v*size for _,v,size in unit])
    core = g.group_rep[zone]
    base_dir = g.guide[core].mean(axis=0)
    axis=[means.mean(axis=0),base_dir,-base_dir,*[v for _,v,_ in directions[:5]],
          *[np.array(x) for x in product((-1,0,1),repeat=3) if any(x)]]
    axis=np.unique(np.round(normalized(np.array(axis)),3),axis=0)
    measures=[]
    best = rank_patch(local,full)
    if not best:
        return
    for v in axis:
        for spacing in (.00075,.0015,.0028,.0045,.007):
            amount = local-baseline+influence[:,None]*v*spacing
            amount *= np.minimum(1.,.03/np.linalg.norm(amount,axis=1,keepdims=True).clip(1.e-9,None))
            candidate=(baseline+amount).astype(np.float32)
            value=rank_patch(candidate,fast)
            if value == 0 and rank_patch(candidate,full) == 0:
                g.position[verts]=candidate
                print('TRI PATCH',g.key,len(zone),len(verts),len(hist),0.,True,flush=True)
                return
            measures.append((value,spacing,candidate))
    output=None
    for value,spacing,candidate in sorted(measures,key=lambda x:x[:2])[:8]:
        score=rank_patch(candidate,full)
        if score<best:
            best,output=score,candidate
    if output is not None:
        g.position[verts]=output
    print('TRI PATCH',g.key,len(zone),len(verts),len(hist),best,output is not None,flush=True)


def main(keys,refined=False):
    _,arm,body,_ = load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names = [bone.name for bone in arm.data.bones]
    samples = sample_bank(body,names)
    _,faces = arrays(body)
    for key in keys:
        if refined:
            from micro_refit import from_export
            g,_=from_export(key,body,arm,names)
        else:
            g=GuardedGarment(key,read_module(HERE/f'male-{key}.glb',arm),names,.027,body)
            g.resume()
        support=focused(g,samples,OUT/'qa/modules'/f'{key}.json')
        def scan():
            rows=[]
            for i in support:
                s=samples[i]
                a,_=g.examine(s,s.cached_tree,faces,False)
                rows.append(a)
            return np.stack(rows)
        hits=collect(g,samples,support)
        before=scan()
        g.history.append(details(before,g,samples,support,'triangle patch start'))
        baseline=g.position.copy()
        cells=sorted(zones(g,hits),key=len,reverse=True)
        for cell in cells[:28]:
            if len(cell)>90:
                vector=np.argsort(-np.asarray([max(r[2] for r in hits[k]) for k in cell]))
                cell=[cell[i] for i in vector[:90]]
            solve_zone(g,samples,support,cell,hits)
        after=scan()
        if quality(after)<quality(before):
            g.history.append(details(after,g,samples,support,'triangle patch accepted'))
            g.persist(arm,names)
        else:
            g.position=baseline
            print('TRI PATCH kept baseline',key,quality(before),quality(after),flush=True)


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    main(args[0].split(','),'refined' in args)
