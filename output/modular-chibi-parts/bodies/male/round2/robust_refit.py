"""Bounded, per-vertex clearance solve with guards against new intersections."""
import sys
import time

from refit import *
from fitting_geometry import region
from gltf_pose import normalized

FITTED = OUT/'.runtime'
FRAME_HINTS = {
    'walk': [9,18,21,22,34.5,36,39,41,48],
    'run': [0,1,2,4,4.5,9,10,12,18,20],
    'wave': [10,19,33],
    'nod': [1.5,17],
    'jump': [6,8,8.5,9],
    'dance': [8,13.5,40],
    'sit_down': [17,20,21,22,24,26,28.8],
    'sit_idle': [1.6,39.6,53.6,56.8,59.2],
    'stand_up': [0,2,6.4,8,8.4,8.8],
    'idle': [66,80,81.5],
    'hold_box': [12,36],
}


class GuardedGarment(Garment):
    def __init__(self,key,obj,names,limit,body):
        super().__init__(key,obj,names,limit)
        _,self.group_rep = np.unique(self.graph[0],return_index=True)
        self.guide, self.body_weights = self.guides(body,names)

    def guides(self,body,names):
        points,faces = arrays(body)
        bvh = tree(points,faces.tolist())
        body_w = weights(body,names)
        guide,transferred = [],[]
        for p in self.base.tolist():
            loc,n,fi,_ = bvh.find_nearest(p)
            offset = np.array(p)-np.array(loc)
            n = np.asarray(n)
            if offset@n>5.e-5:
                n = normalized(offset)*.55+n*.45
            guide.append(n)
            from fitting_geometry import barycentric
            coefficients = barycentric(loc,points[faces[fi]])
            transferred.append(coefficients@body_w[faces[fi]])
        return normalized(welded(np.array(guide),self.graph)),np.asarray(transferred,dtype=np.float32)

    def examine(self,sample,bvh,body_faces,collect=True):
        basis = self.basis(sample)
        p = np.einsum('vij,vj->vi',basis[:,:,:3],self.position)+basis[:,:,3]
        ds,ns,_ = nearest(bvh,p[self.representatives])
        d,n = ds[self.inverse],ns[self.inverse].copy()
        pairs = bvh.overlap(tree(p,self.face_list))
        result = np.asarray([(d<0).sum(),len(pairs),d.min()],dtype=np.float64)
        if not collect:
            return result,None
        touched = d<.00072
        need = np.where(touched,.0015-d,.00063-d).astype(np.float32)
        interior = None
        if pairs:
            bb,jj = np.asarray(pairs).T
            f = np.unique(jj)
            corners = self.faces[f]
            probes = (BARYCENTRIC @ p[corners]).reshape(-1,3)
            q,normal,_ = nearest(bvh,probes)
            q = q.reshape(len(f),-1)
            dips = q.argmin(axis=1)
            deepest = q[np.arange(len(f)),dips]
            inward = normal.reshape(len(f),len(BARYCENTRIC),3)[np.arange(len(f)),dips]
            ixs = corners.ravel()
            normal_vectors = np.repeat(inward,3,axis=0)
            gradient = np.einsum('vji,vj->vi',basis[ixs,:,:3],normal_vectors)
            scale = np.linalg.norm(gradient,axis=1).clip(.25,None)
            depth = pair_depth(sample.body[body_faces[bb]],p[self.faces[jj]])*.001
            per_face = np.zeros(len(self.faces))
            np.maximum.at(per_face,jj,depth)
            penetration = np.maximum(np.maximum(0,-deepest),per_face[f])
            need_at_corners = np.repeat(.0015+penetration,3)
            interior = (self.graph[0][ixs].astype(np.int32),gradient/scale[:,None],
                        np.minimum(.030,need_at_corners/scale),np.ones(len(ixs),dtype=bool))
            for j,tri in enumerate(corners):
                fix = .0015 + float(penetration[j])
                for ix in tri:
                    if not touched[ix]:
                        # Use the interpolated crossing point for long edges,
                        # while preserving the side indicated by the vertex.
                        if d[ix]>.009 or np.dot(n[ix],inward[j])<.12:
                            continue
                        need[ix] = max(need[ix], min(fix,.0045))
                        touched[ix] = True
        use = np.flatnonzero((d<.0075)|touched)
        gradient = np.einsum('vji,vj->vi',basis[use,:,:3],n[use])
        size = np.linalg.norm(gradient,axis=1).clip(.25,None)
        exterior = (self.graph[0][use].astype(np.int32),gradient/size[:,None],
                    np.minimum(.030,need[use]/size),touched[use])
        return result,tuple(np.concatenate((a,b)) for a,b in zip(exterior,interior)) if interior else exterior

    def suggestions(self,constraints,radius,prioritize):
        groups,axes,bounds,touched = map(np.concatenate,zip(*constraints))
        total = len(self.group_rep)
        active = np.zeros(total,dtype=bool)
        active[groups[touched]] = True
        mask = active[groups]
        groups,axes,bounds,touched = groups[mask],axes[mask],bounds[mask],touched[mask]
        counts = np.bincount(groups,minlength=total).clip(1,None)
        maxneed = np.zeros(total,dtype=np.float32)
        np.maximum.at(maxneed,groups,bounds)
        def moments(values):
            return np.column_stack([np.bincount(groups,weights=v,minlength=total)
                                    for v in values.T])
        def clip(x,r):
            return x*np.minimum(1,r/np.linalg.norm(x,axis=1,keepdims=True).clip(1.e-8,None))
        push = moments(np.maximum(bounds,0)[:,None]*axes) / counts[:,None]
        mean = normalized(push)
        outward = self.guide[self.group_rep]
        start = self.position-self.base
        inv = self.graph[0]
        trial = np.zeros_like(mean)
        weights = np.where(touched,1.,2.8)
        for k in range(22):
            local = trial[groups]
            miss = np.maximum(0,bounds-np.einsum('ij,ij->i',axes,local))
            magnitude = miss*weights
            if prioritize:
                magnitude *= (.25+miss/.002)**1.45
            gradient = moments(magnitude[:,None]*axes) / counts[:,None]
            trial = clip(trial + gradient*(.75 if not prioritize else .34),radius)
        field = trial[inv]
        for _ in range(3):
            avg = laplacian(field,self.graph)
            keep = np.einsum('ij,ij->i',field[self.group_rep],mean)
            field = welded(.70*field+.30*avg,self.graph)
            drift = keep-np.einsum('ij,ij->i',field[self.group_rep],mean)
            field += (mean*np.maximum(drift,0)[:,None])[inv]
        strongest = np.zeros_like(trial)
        strongest[groups[touched & (bounds>=maxneed[groups])]] = axes[touched & (bounds>=maxneed[groups])]
        # A second candidate follows the fixed rest-surface field, where the
        # active normals agree on which side of the garment needs room.
        orientation = np.einsum('ij,ij->i',axes,outward[groups])
        radial_bound = np.where((orientation>.55)&touched,bounds/np.maximum(.55,orientation),0.)
        req = np.zeros(total)
        np.maximum.at(req,groups,radial_bound)
        for _ in range(4):
            req = np.maximum(req,laplacian(req[inv],self.graph)[self.group_rep]*.72)
        normal_move = outward[np.asarray(inv)]*np.minimum(radius,req[inv,None])
        return [self.base+clip(start+move,.030) for move in
                (field,field*.53,normal_move*.8,normal_move*.38)]

    def persist(self,arm,names):
        np.savez_compressed(FITTED/f'fit-{self.key}.npz',base=self.base,position=self.position,w=self.w,
                            faces=self.faces)
        self.best = ((0,),self.position.copy())
        write_json(OUT/'qa'/f'fit-{self.key}.json',self.export(arm,names))

    def resume(self):
        file = FITTED/f'fit-{self.key}.npz'
        if not file.exists():
            return
        prior = np.load(file)
        assert np.array_equal(self.base,prior['base']) and np.array_equal(self.faces,prior['faces'])
        self.position = prior['position']
        self.w = prior['w']
        self.ids,self.packed = influences(self.w)
        self.representatives,self.inverse = unique_vertices(self.base,self.w)
        record = OUT/'qa'/f'fit-{self.key}.json'
        if record.exists():
            self.history = json.loads(record.read_text())['iterations']


def rank(rows):
    d = rows[:,2]
    bad = (rows[:,:2].sum(axis=1)>0)|(d<.0005)
    return (int(bad.sum()),
            float((rows[:,0]*1.3+rows[:,1]).sum()+np.maximum(0,.0005-d).sum()*55000),
            float(d.min()))


def details(row,g,samples,ids,label):
    result = rank(row)
    i = int(row[:,2].argmin())
    worst = samples[ids[i]]
    item = dict(stage=label,samples=len(row),score=list(result),worst=[worst.clip,worst.frame,float(row[i,2])],
                peak_inside=int(row[:,0].max()),peak_triangles=int(row[:,1].max()))
    print(g.key,item,flush=True)
    return item


def solve(keys,iters,resume=False,validate=False):
    _,arm,body,_ = load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names = [bone.name for bone in arm.data.bones]
    gs = [GuardedGarment(k,read_module(HERE/f'male-{k}.glb',arm),names,.027,body) for k in keys]
    if resume:
        for g in gs:
            g.resume()
    samples = sample_bank(body,names)
    _,faces = arrays(body)
    slots = {c:[i for i,s in enumerate(samples) if s.clip==c] for c in ('rest',*CLIPS)}
    focus = {0}
    for c,indices in slots.items():
        focus.update([*indices[::13],indices[-1]])
        for f in FRAME_HINTS.get(c,[]):
            center = min(indices,key=lambda i:abs(samples[i].frame-f))
            focus.add(center)
    full_ids = list(range(len(samples)))

    def scan(g,ids,collect):
        rows,opts = [],[]
        for i in ids:
            s = samples[i]
            if s.cached_tree is None:
                bvh = tree(s.body,s.faces)
                if len(ids)<900:
                    s.cached_tree = bvh
            else:
                bvh = s.cached_tree
            row,opt = g.examine(s,bvh,faces,collect)
            rows.append(row)
            if opt is not None:
                opts.append(opt)
        return np.stack(rows),opts

    for cycle in range(iters):
        for g in gs:
            start = time.monotonic()
            ids = sorted(focus)
            rows,opts = scan(g,ids,True)
            prior = rank(rows)
            g.history.append(details(rows,g,samples,ids,f'guard cycle {cycle} start'))
            if prior[0]==0:
                g.persist(arm,names)
                continue
            current = g.position.copy()
            strongest = prior
            proposed = current
            # Keep each trial bounded so a clearance direction can be
            # relinearized once nearby positive safeguards move.
            moves = g.suggestions(opts,.006 if cycle<2 else .004,cycle%2==1)
            bad = np.flatnonzero((rows[:,:2].sum(axis=1)>0)|(rows[:,2]<.0005))
            if len(bad):
                impacted = {ids[i] for i in bad}
                probe = sorted(impacted|set(ids[::5]))
            else:
                probe = ids
            check0 = [ids.index(i) for i in probe]
            best_score = rank(rows[check0])
            for j in (0,1,2,3):
                g.position = moves[j].astype(np.float32)
                examined,_ = scan(g,probe,False)
                r = rank(examined)
                if r[:2]<best_score[:2]:
                    proposed,best_score = g.position.copy(),r
                if r[0]<prior[0]*.35:
                    break
            g.position = proposed
            new,_ = scan(g,ids,False)
            score = rank(new)
            if score[:2]>=prior[:2]:
                g.position = current
            else:
                g.history.append(details(new,g,samples,ids,f'guard cycle {cycle} accepted'))
            g.persist(arm,names)
            print('GUARD CYCLE',cycle,g.key,prior,score,'seconds',round(time.monotonic()-start,1),flush=True)

    if validate:
        for g in gs:
            rows,_ = scan(g,full_ids,False)
            g.history.append(details(rows,g,samples,full_ids,'final numerical bank'))
            g.persist(arm,names)
            bad = np.flatnonzero((rows[:,:2].sum(axis=1)>0)|(rows[:,2]<.0005))
            residual = [[samples[i].clip,samples[i].frame,*rows[i].tolist()] for i in bad]
            write_json(OUT/'qa'/f'fit-residual-{g.key}.json',residual)


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    solve(args[0].split(','),int(args[1]),'resume' in args,'validate' in args)
