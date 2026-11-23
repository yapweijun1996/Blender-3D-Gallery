"""Subdivide collision witnesses and clear the newly sampled cloth surface."""
from triangle_refit import *


def refine_mesh(g,names,samples,support,body):
    hits = np.zeros(len(g.faces),dtype=np.int32)
    for i in support:
        s = samples[i]
        if s.cached_tree is None:
            s.cached_tree=tree(s.body,s.faces)
        m = g.basis(s)
        points = np.einsum('vij,vj->vi',m[:,:,:3],g.position)+m[:,:,3]
        pairs = s.cached_tree.overlap(tree(points,g.face_list))
        if pairs:
            np.add.at(hits,np.asarray(pairs)[:,1],1)
    faces = np.flatnonzero(hits)
    if not len(faces):
        return False
    store_geometry(g.obj,g.position,g.w,names)
    mesh = g.obj.data
    for j in range(3):
        slot = mesh.attributes.new(f'OffsetOrigin{j}',type='FLOAT',domain='POINT')
        slot.data.foreach_set('value',g.base[:,j].astype(np.float32))
    assert len(mesh.polygons)==len(g.faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    new_edges = set()
    for idx in faces:
        face = bm.faces[int(idx)]
        for edge in face.edges:
            if edge.calc_length()>.008:
                new_edges.add(edge)
    if not new_edges:
        bm.free()
        return False
    orig = bm.verts.layers.int.new('Existing')
    for vert in bm.verts:
        vert[orig]=1
    geometry=bmesh.ops.subdivide_edges(bm,edges=sorted(new_edges,key=lambda e:e.index),cuts=1,use_grid_fill=True)
    for vert in geometry['geom_inner']:
        if isinstance(vert,bmesh.types.BMVert):
            vert[orig]=0
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    g.new=np.array([not v[orig] for v in bm.verts])
    bm.verts.layers.int.remove(orig)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    keep=np.empty((len(mesh.vertices),3),dtype=np.float32)
    for j in range(3):
        channel = mesh.attributes[f'OffsetOrigin{j}']
        component = np.empty(len(keep),dtype=np.float32)
        channel.data.foreach_get('value',component)
        keep[:,j] = component
        mesh.attributes.remove(channel)
    g.position,g.faces = arrays(g.obj)
    g.base=keep
    g.face_list=g.faces.tolist()
    g.graph=weld_graph(g.base,g.faces)
    _,g.group_rep=np.unique(g.graph[0],return_index=True)
    w=weights(g.obj,names)
    smooth=laplacian(w,g.graph)
    w[g.new]=.9*w[g.new]+.1*smooth[g.new]
    set_weights(g,limit_weights(welded(w,g.graph)).astype(np.float32))
    g.guide,g.body_weights=g.guides(body,names)
    print('SUBDIVIDE WITNESSES',g.key,len(faces),len(new_edges),len(g.faces),flush=True)
    return True


def main(keys):
    _,arm,body,_ = load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names=[bone.name for bone in arm.data.bones]
    samples=sample_bank(body,names)
    _,faces=arrays(body)
    for k in keys:
        g=GuardedGarment(k,read_module(HERE/f'male-{k}.glb',arm),names,.027,body)
        g.resume()
        support=focused(g,samples,OUT/'qa/modules'/f'{k}.json')
        def scan(indices,collect=False):
            rows,opts=[],[]
            for i in indices:
                s=samples[i]
                if s.cached_tree is None:
                    s.cached_tree=tree(s.body,s.faces)
                a,b=g.examine(s,s.cached_tree,faces,collect)
                rows.append(a)
                if b is not None:
                    opts.append(b)
            return np.stack(rows),opts
        rows,_=scan(support)
        before=quality(rows)
        g.history.append(details(rows,g,samples,support,'witness subdivision start'))
        if not refine_mesh(g,names,samples,support,body):
            continue
        for step in range(2):
            rows,opts=scan(support,True)
            if rank(rows)[0]==0:
                break
            d,n,m=gather(g,samples,support)
            field,affected=adjust(g,samples,support,d,n,m,140)
            x0=g.position.copy()
            trial,_=candidate_field(g,opts,.0028,True)
            for f in (.9,.54):
                delta=x0-g.base+field*f
                delta*=np.minimum(1.,.03/np.linalg.norm(delta,axis=1,keepdims=True).clip(1.e-9,None))
                trial.append((g.base+delta).astype(np.float32))
            winner=x0
            score=quality(rows)
            probe=[i for i,r in enumerate(rows) if r[0]+r[1]>0 or r[2]<.0005 or i%9==0]
            subset=[support[i] for i in probe]
            best=quality(rows[probe])
            for pose in trial:
                g.position=pose.copy()
                check,_=scan(subset)
                if quality(check)<best:
                    best,winner=quality(check),pose
            g.position=winner.copy()
            new,_=scan(support)
            if quality(new)>=score:
                g.position=x0
            print('SUBDIVIDE SOLVE',k,step,affected,score,quality(new),flush=True)
        after,_=scan(support)
        if quality(after)<before:
            g.history.append(details(after,g,samples,support,'witness subdivision accepted'))
            g.persist(arm,names)
        else:
            print('SUBDIVIDE kept baseline',g.key,before,quality(after),flush=True)


if __name__=='__main__':
    main(sys.argv[sys.argv.index('--')+1].split(','))
