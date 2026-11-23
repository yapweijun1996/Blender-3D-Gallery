"""Solve known clearance witnesses on the entire baked timeline."""
from vertex_refit import *
from mathutils.kdtree import KDTree


def load_witness_groups(g,exported,records):
    kd=KDTree(len(g.position))
    for i,p in enumerate(g.position):
        kd.insert(p,i)
    kd.balance()
    points,_=arrays(exported)
    groups=set()
    for row in records:
        for frame in row['frames']:
            if 'worst_vertex' in frame:
                _,vertex,error=kd.find(points[frame['worst_vertex']])
                assert error<.00001,error
                groups.add(int(g.graph[0][vertex]))
    return sorted(groups)


def from_export(key,body,arm,names):
    exported=read_module(OUT/f'male-{key}-v2.glb',arm)
    record=np.load(FITTED/f'fit-{key}.npz')
    kd=KDTree(len(record['position']))
    for i,p in enumerate(record['position']):
        kd.insert(p,i)
    kd.balance()
    g=GuardedGarment(key,exported,names,None,body)
    mapped=[]
    for p in g.position:
        _,i,dist=kd.find(p)
        assert dist<.00001,(key,dist)
        mapped.append(i)
    g.base=record['base'][mapped].copy()
    g.graph=weld_graph(g.base,g.faces)
    _,g.group_rep=np.unique(g.graph[0],return_index=True)
    g.guide,g.body_weights=g.guides(body,names)
    g.history=json.loads((OUT/'qa'/f'fit-{key}.json').read_text())['iterations']
    return g,exported


def polish(key):
    scene,arm,body,actions=load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names=[bone.name for bone in arm.data.bones]
    g,exported=from_export(key,body,arm,names)
    frozen=g.position.copy()
    source=json.loads((OUT/'qa/modules'/f'{key}.json').read_text())
    groups=load_witness_groups(g,exported,source['clips'].values())
    if key=='tshirt':
        from body_audit import posed,set_frame
        body_faces=arrays(body)[1].tolist()
        inspect=set()
        for clip,row in source['clips'].items():
            for frame in row['frames']:
                if frame['min_signed_m']<.00055:
                    inspect.add((clip,frame['frame']))
        for clip,frame in sorted(inspect):
            use_action(arm,actions.get(clip))
            set_frame(scene,frame)
            d,_,_=nearest(tree(posed(body),body_faces),posed(exported))
            groups.extend(int(k) for k in g.graph[0][d<.00071])
        groups=sorted(set(groups))
        use_action(arm,None)
        bpy.context.view_layer.update()
    if not groups:
        return
    samples=sample_bank(body,names)
    if key!='tshirt':
        data=[]
        for name,row in source['clips'].items():
            for entry in row['frames']:
                if 'worst_vertex' in entry:
                    data.append((entry['min_signed_m'],int(g.graph[0][entry['worst_vertex']])))
        groups=list(dict.fromkeys(k for _,k in sorted(data)))[:16]
    reps=g.group_rep[groups]
    near={i:[] for i in groups}
    for i,s in enumerate(samples):
        m=(s.transforms[g.ids[reps]]*g.packed[reps,:,None,None]).sum(axis=1)
        points=np.einsum('vij,vj->vi',m[:,:,:3],g.position[reps])+m[:,:,3]
        bvh=tree(s.body,s.faces)
        d,n,_=nearest(bvh,points)
        for j,k in enumerate(groups):
            if d[j]<.006:
                near[k].append((i,m[j],bvh,float(d[j]),m[j,:,:3].T@n[j]))
    inv=g.graph[0]
    trials=[]
    for k in groups:
        n=near[k]
        idx=g.group_rep[k]
        point=g.position[idx]
        critical=sorted(n,key=lambda q:q[3])[:10]
        basis=[row[4] for row in critical]
        axes=np.concatenate((np.asarray(basis),np.array([np.sum(basis,axis=0),g.guide[idx]]),
                             np.asarray([v for v in product((-1,0,1),repeat=3) if any(v)])))
        axes=np.unique(np.round(normalized(axes),4),axis=0)
        sizes=np.array([.0002,.00035,.0005,.00072,.001,.00135,.00165,.002,.00245,.0029,.0034])
        positions=np.concatenate((point[None,:],point+(axes[:,None,:]*sizes[None,:,None]).reshape(-1,3)))
        valid=np.linalg.norm(positions-g.base[idx],axis=1)<=.03
        positions=positions[valid]
        minima=np.full(len(positions),1.)
        cost=np.linalg.norm(positions-point,axis=1)
        for _,m,bvh,_,_ in n:
            projected=positions@m[:,:3].T+m[:,3]
            minima=np.minimum(minima,np.asarray(signed_at(bvh,projected)))
        peak=np.argmax(minima)
        chosen=np.flatnonzero(minima>=.00062)
        if len(chosen):
            peak=chosen[np.argmin(cost[chosen])]
        if minima[peak]>minima[0]+.00002:
            g.position[inv==k]+=positions[peak]-point
        trials.append([int(k),len(n),float(minima[0]),float(minima[peak]),float(cost[peak])])
        print('MICRO',key,trials[-1],flush=True)
    if key!='tshirt':
        from triangle_refit import focused
        support=focused(g,samples,OUT/'qa/modules'/f'{key}.json')
        _,faces=arrays(body)
        rows=[[],[]]
        adopted=g.position.copy()
        for i in support:
            s=samples[i]
            bvh=tree(s.body,s.faces)
            for j,points in enumerate((frozen,adopted)):
                g.position=points
                stats,_=g.examine(s,bvh,faces,False)
                rows[j].append(stats)
        older,newer=(np.stack(x) for x in rows)
        print('MICRO GATE',key,quality(older),quality(newer),flush=True)
        if quality(newer)>=quality(older):
            return
    g.history.append(dict(stage='all-frame vertex micro clearance',groups=trials))
    g.persist(arm,names)


if __name__=='__main__':
    polish(sys.argv[sys.argv.index('--')+1])
