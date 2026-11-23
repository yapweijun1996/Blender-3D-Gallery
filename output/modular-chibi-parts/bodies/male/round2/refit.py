"""Refit the existing male garments against the baked bank using a bounded offset field."""
import hashlib
import sys
import time

import bmesh
from asset_io import *
from body_audit import load_body_motion, use_action
from fit_module import FLOOR, MARGIN, CAP, influences, nearest, read_module, skin, store_geometry, Sample
from fitting_geometry import arrays, laplacian, limit_weights, tree, weights, welded, weld_graph
from gltf_pose import GLTF_TO_BPY, Rig, clock
from motion_repair import OUT, FIXED, BODY_PATH, pair_depth

SLOTS = ('tshirt','dress','jeans')
GOAL = .00068
BARYCENTRIC = np.array([(a/4,b/4,1-(a+b)/4) for a in range(5) for b in range(5-a)
                        if max(a,b,4-a-b)<4],dtype=np.float32)


def subdivide(item,limit):
    mesh = bmesh.new()
    mesh.from_mesh(item.data)
    old = mesh.verts.layers.int.new('Original fit vertices')
    for vert in mesh.verts:
        vert[old] = 1
    cuts = [edge for edge in mesh.edges if edge.calc_length()>limit]
    created = bmesh.ops.subdivide_edges(mesh,edges=cuts,cuts=1,use_grid_fill=True)
    new = [item for item in created['geom_inner'] if isinstance(item,bmesh.types.BMVert)]
    for vert in new:
        vert[old] = 0
    bmesh.ops.triangulate(mesh,faces=[face for face in mesh.faces if len(face.verts)>3])
    mesh.verts.index_update()
    mask = np.array([not vert[old] for vert in mesh.verts])
    mesh.verts.layers.int.remove(old)
    mesh.to_mesh(item.data)
    mesh.free()
    item.data.update()
    print('SUBDIVIDE',item.name,len(cuts),'edges',len(new),'new verts',flush=True)
    return mask


def sample_bank(body,names):
    p,bfaces = arrays(body)
    bfaces = bfaces.tolist()
    target,motion = GLB(BODY_PATH),GLB(FIXED)
    rig = Rig(target)
    order = [rig.index[name.split(':')[-1]] for name in names]
    ids,packed = influences(weights(body,names))
    out = [Sample('rest',0,p,bfaces,np.tile(np.eye(4,dtype=np.float32)[None,:3],(len(names),1,1)))]
    for anim in motion.doc['animations']:
        time_lists = [motion.accessor(s['input']).ravel() for s in anim['samplers']]
        times = max(time_lists,key=len)
        worlds = rig.world_batch(rig.sample(motion,anim,times))
        transforms = (GLTF_TO_BPY @ worlds @ rig.inv @ GLTF_TO_BPY.T)[:,order,:3]
        for t,m in zip(times,transforms):
            sample = object.__new__(Sample)
            sample.clip,sample.frame = anim['name'],float(t*24)
            sample.transforms = m
            sample.body,_ = skin(sample,ids,packed,p)
            sample.faces = bfaces
            sample.cached_tree = None
            out.append(sample)
    return out


def unique_vertices(points,weight_rows):
    keys = np.column_stack((points,weight_rows))
    _,representatives,inverse = np.unique(keys,axis=0,return_index=True,return_inverse=True)
    return representatives,inverse.reshape(-1)


class Garment:
    def __init__(self, key, obj, names, edge_limit):
        self.key,self.obj = key,obj
        self.new = subdivide(obj,edge_limit) if edge_limit is not None else np.zeros(len(obj.data.vertices),dtype=bool)
        self.base,self.faces = arrays(obj)
        self.face_list = self.faces.tolist()
        self.graph = weld_graph(self.base,self.faces)
        self.original_w = weights(obj,names)
        self.w = self.original_w.copy()
        # New corners interpolate existing skin weights. A mild seam-aware
        # Laplacian pass softens gradients around split edges.
        for i in range(2):
            smooth = laplacian(self.w,self.graph)
            self.w[self.new] = .82*self.w[self.new] + .18*smooth[self.new]
        self.w = limit_weights(welded(self.w,self.graph)).astype(np.float32)
        self.ids,self.packed = influences(self.w)
        self.representatives,self.inverse = unique_vertices(self.base,self.w)
        self.position = self.base.copy()
        self.history = []
        self.samples = []
        self.best = None

    def basis(self, sample):
        return (sample.transforms[self.ids]*self.packed[:,:,None,None]).sum(axis=1)

    def row(self,sample,bvh,body_faces,collect=True,soft=False):
        basis = self.basis(sample)
        pts = np.einsum('vij,vj->vi',basis[:,:,:3],self.position)+basis[:,:,3]
        d,n,_ = nearest(bvh,pts[self.representatives])
        d,n = d[self.inverse],n[self.inverse]
        pairs = bvh.overlap(tree(pts,self.face_list))
        index = int(d.argmin())
        report = dict(frame=sample.frame,minimum_m=float(d[index]),vertex=index,
                      inside=int((d<0).sum()),triangle_pairs=len(pairs),depth_mm=0.)
        if pairs:
            ii,jj = np.asarray(pairs).T
            penetration = pair_depth(sample.body[body_faces[ii]],pts[self.faces[jj]])
            report['depth_mm'] = float(penetration.max())
        if not collect:
            return report,None
        bad = np.flatnonzero(d<GOAL)
        if not len(bad) and not pairs:
            return report,None
        required = np.zeros(len(pts),dtype=np.float32)
        required[bad] = MARGIN-d[bad]
        if pairs:
            intersected = np.unique(jj)
            faces = self.faces[intersected]
            probes = (BARYCENTRIC @ pts[faces]).reshape(-1,3)
            pdepth,pnormal,_ = nearest(bvh,probes)
            pdepth = pdepth.reshape(len(faces),-1)
            deep = pdepth.argmin(axis=1)
            heading = pnormal.reshape(len(faces),-1,3)[np.arange(len(faces)),deep]
            needs = MARGIN + np.maximum(0,-pdepth.min(axis=1))
            face_depths = np.zeros(len(self.faces),dtype=np.float32)
            np.maximum.at(face_depths,jj,penetration*.001)
            needs = np.maximum(needs,MARGIN+face_depths[intersected])
            for corners,direction,need in zip(faces,heading,needs):
                # Keep a reliable surface sign for close corners. Interior
                # probes supply direction where corners miss a crossing.
                swap = corners[required[corners] < need]
                n[swap] = np.where((d[swap]<GOAL)[:,None],n[swap],direction)
                required[swap] = need
        active = np.flatnonzero(required)
        gradient = np.einsum('vji,vj->vi',basis[active,:,:3],n[active])
        magnitude = np.maximum(np.linalg.norm(gradient,axis=1),.2)
        gradient /= magnitude[:,None]
        needs = np.clip(required[active]/magnitude,0,CAP)
        return report,(active,gradient,needs)

    def advance(self,constraints):
        inv,_,_,_,copies = self.graph
        proposed = np.zeros((len(copies),3),dtype=np.float32)
        best = np.zeros(len(copies),dtype=np.float32)
        largest = np.zeros_like(proposed)
        for ix,grad,needs in constraints:
            group = inv[ix]
            strict = needs>best[group]
            np.maximum.at(best,group,needs)
            strongest = strict & (needs>=best[group])
            largest[group[strongest]] = grad[strongest]
        proposed[:] = largest*best[:,None]
        # Sweep the linearized clearance constraints around the pose space.
        # Any opposed gradients are resolved by measuring the next bake.
        anchor = self.position - self.base
        limit = lambda v: v*np.minimum(1,CAP/np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1.e-10))
        for _ in range(5):
            move = proposed[inv]
            blend = welded(.57*move+.43*laplacian(move,self.graph),self.graph)
            proposed[inv] = blend
            amount = best-(proposed*largest).sum(axis=1)
            proposed += np.maximum(amount,0)[:,None]*largest
        if constraints:
            subset = constraints[::max(1,len(constraints)//120)]
            for _ in range(2):
                for ix,grad,needs in subset:
                    group = inv[ix]
                    short = needs-np.einsum('ij,ij->i',proposed[group],grad)
                    active = short>0
                    proposed[group[active]] += grad[active]*short[active,None]*.55
            amount = best-(proposed*largest).sum(axis=1)
            proposed += np.maximum(amount,0)[:,None]*largest
        self.position = self.base + limit(anchor+proposed[inv])

    def score(self,rows):
        hard = [r for r in rows if r['inside'] or r['triangle_pairs'] or r['minimum_m']<FLOOR]
        return (sum(r['inside']+r['triangle_pairs'] for r in hard),
                len(hard),max((FLOOR-r['minimum_m'] for r in hard),default=0.))

    def export(self,arm,names):
        if self.best is not None:
            self.position = self.best[1].copy()
        store_geometry(self.obj,self.position,self.w,names)
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        path = OUT/f'male-{self.key}-v2.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                  export_animations=False,export_skins=True,export_yup=True,
                                  export_tangents=bool(self.obj.data.uv_layers))
        return dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    source=f'male-{self.key}.glb',triangles=len(self.faces),
                    vertices=len(self.position),max_baked_offset_mm=float(
                        np.linalg.norm(self.position-self.base,axis=1).max()*1000),
                    split_vertices=int(self.new.sum()),iterations=self.history)


def fit(keys,iterations,edge_limit):
    _,arm,body,_ = load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names = [bone.name for bone in arm.data.bones]
    garments = [Garment(k,read_module(HERE/f'male-{k}.glb',arm),names,edge_limit) for k in keys]
    samples = sample_bank(body,names)
    _,body_faces = arrays(body)
    working = list(garments)
    focus = {g.key:set() for g in garments}
    slots = {clip:[i for i,s in enumerate(samples) if s.clip==clip] for clip in ('rest',*CLIPS)}
    coarse = {i for indexes in slots.values() for i in (*indexes[::7],indexes[-1])}
    for step in range(iterations+1):
        if not working:
            break
        full = step in (0,3,6,9,12,iterations)
        chosen = set(range(len(samples))) if full else coarse | set().union(*(focus[g.key] for g in working))
        rows = {g.key:[] for g in working}
        constraints = {g.key:[] for g in working}
        start = time.monotonic()
        support = set().union(*(focus[g.key] for g in working))
        for index,i in enumerate(sorted(chosen)):
            if index and index%256==0:
                print('REFIT PROGRESS',step,index,len(chosen),flush=True)
            sample = samples[i]
            bvh = sample.cached_tree or tree(sample.body,sample.faces)
            # The same sparse support and failures are revisited each pass.
            if i in coarse or i in support:
                sample.cached_tree = bvh
            for g in working:
                row,required = g.row(sample,bvh,body_faces)
                rows[g.key].append(row)
                if required is not None:
                    constraints[g.key].append(required)
                    focus[g.key].add(i)
        for g in working[:]:
            row = rows[g.key]
            score = g.score(row)
            peak = min(row,key=lambda r:r['minimum_m'])
            summary = dict(step=step,full=full,samples=len(row),score=score,worst=peak,
                           peak_vertices=max(r['inside'] for r in row),
                           peak_triangles=max(r['triangle_pairs'] for r in row))
            g.history.append(summary)
            print('FIT',g.key,summary,'seconds',round(time.monotonic()-start,1),flush=True)
            if full and (g.best is None or score<g.best[0]):
                g.best = (score,g.position.copy())
                write_json(OUT/'qa'/f'fit-{g.key}.json',g.export(arm,names))
            if (full and not score[1]) or step==iterations:
                working.remove(g)
                continue
            g.advance(constraints[g.key])
    for g in garments:
        write_json(OUT/'qa'/f'fit-{g.key}.json',g.export(arm,names))


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    fit(args[0].split(',') if args else SLOTS,int(args[1]) if len(args)>1 else 12,
        float(args[2]) if len(args)>2 else .027)
