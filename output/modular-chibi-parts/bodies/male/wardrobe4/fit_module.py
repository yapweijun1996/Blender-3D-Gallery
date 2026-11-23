"""Fit a neutral skinned GLB to the Studio male and audit the reimported export.

Guarded Blender invocation:
  ./run.sh fit_module.py -- SOURCE DESTINATION --slot SLOT [--iterations 6]
SLOT is hair, top, dress, bottom or shoes. All destinations must be in this folder.
"""
import argparse
from collections import defaultdict
import hashlib
from pathlib import Path
import sys

from asset_io import *
from body_audit import frame_grid, load_body_motion, posed, set_frame, use_action, pair_depth
from fitting_geometry import SurfaceField, arrays, laplacian, limit_weights, region, shoe_layer_links, tree, weights, welded
from gltf_pose import GLTF_TO_BPY, Rig, clock
from mathutils import Matrix

FLOOR = .0005
MARGIN = .0015
CAP = .030
TRI_LIMIT = {'hair':3000,'top':6000,'dress':6000,'bottom':6000,'shoes':3500}


def read_module(path, arm):
    imported = import_objects(path)
    garment, = [o for o in imported if o.type=='MESH' and len(o.vertex_groups)]
    world = garment.matrix_world.copy()
    garment.parent = arm
    garment.matrix_parent_inverse = Matrix.Identity(4)
    garment.matrix_basis = Matrix.Identity(4)
    if np.max(abs(np.asarray(world)-np.eye(4)))>1.e-7:
        garment.data.transform(world)
    garment.modifiers.clear()
    garment.modifiers.new('Male armature','ARMATURE').object = arm
    for obj in imported-{garment}:
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.view_layer.update()
    return garment


def stash_neutral():
    bpy.ops.wm.open_mainfile(filepath=str(NEUTRAL),load_ui=False)
    arm, body = (bpy.context.scene.objects[n] for n in ('Armature','Base_Body'))
    source = body.copy()
    source.data = body.data.copy()
    source.parent = None
    source.modifiers.clear()
    source_rig = arm.copy()
    source_rig.data = arm.data.copy()
    with bpy.data.libraries.load(str(MASTER),link=False) as (src,dst):
        dst.objects = ['Armature','Base_Body']
    male_rig, male = dst.objects
    assert male.type == 'MESH'
    names = [bone.name for bone in male_rig.data.bones]
    return SurfaceField(source,male,source_rig,male_rig,names)


class Sample:
    def __init__(self, clip, frame, body_points, body_faces, transforms):
        self.clip,self.frame = clip,frame
        self.body = body_points.astype(np.float32)
        self.faces = body_faces
        self.transforms = transforms
        self.cached_tree = None


def motion_samples(body,names,body_asset,motion):
    points,faces = arrays(body)
    faces = faces.tolist()
    rig = Rig(body_asset)
    joint_order = [rig.index[n.split(':')[-1]] for n in names]
    ids,packed = influences(weights(body,names))
    rest = Sample('rest',1.,points,faces,np.tile(np.eye(4,dtype=np.float32)[None,:3],(len(names),1,1)))
    yield rest
    for anim in motion.doc['animations']:
        times = clock(motion,anim,(24,) if anim["name"] in LEGACY else (30,))
        worlds = rig.world_batch(rig.sample(motion,anim,times))
        skin_matrices = GLTF_TO_BPY @ worlds @ rig.inv @ GLTF_TO_BPY.T
        for frame,transforms in zip(times*24,skin_matrices):
            sample = object.__new__(Sample)
            sample.clip,sample.frame = anim['name'],float(frame)
            sample.transforms = transforms[joint_order,:3]
            sample.body,_ = skin(sample,ids,packed,points)
            sample.faces = faces
            sample.cached_tree = None
            yield sample


def influences(w):
    ids = np.argpartition(w,-4,axis=1)[:,-4:]
    return ids, w[np.arange(len(ids))[:,None],ids]


def skin(sample, ids, w, p):
    transforms = (sample.transforms[ids]*w[:,:,None,None]).sum(axis=1)
    return np.einsum('vij,vj->vi',transforms[:,:,:3],p) + transforms[:,:,3], transforms[:,:,:3]


def nearest(bvh,points):
    signed = np.empty(len(points),dtype=np.float32)
    normals = np.empty_like(points,dtype=np.float32)
    bodies = np.empty(len(points),dtype=np.int32)
    for i,p in enumerate(points.tolist()):
        loc,n,face,_ = bvh.find_nearest(p)
        signed[i] = (p[0]-loc.x)*n.x+(p[1]-loc.y)*n.y+(p[2]-loc.z)*n.z
        normals[i] = n
        bodies[i] = face
    return signed,normals,bodies


def scan(points, w, faces, samples, zones, body_faces, face_groups, collect, progress=False):
    ids, packed = influences(w)
    face_list = faces.tolist()
    rows = {}
    worst = np.zeros(len(points),dtype=np.float32)
    directions = np.zeros_like(points)
    violations = []
    last_clip = None
    for sample in samples:
        if progress and sample.clip!=last_clip:
            print('SCAN',sample.clip,flush=True)
            last_clip = sample.clip
        p,basis = skin(sample,ids,packed,points)
        body_tree = sample.cached_tree or tree(sample.body,sample.faces)
        depth,normal,face_id = nearest(body_tree,p)
        pairs = body_tree.overlap(tree(p,face_list))
        row = rows.setdefault(sample.clip,dict(samples=0,max_vertices_inside=0,max_tri_pairs=0,
                                               total_vertices_inside=0,total_tri_pairs=0,minimum_m=1,
                                               max_triangle_depth_mm=0,shortfall_samples=0,zones={}))
        row['samples'] += 1
        count = int((depth<0).sum())
        row['max_vertices_inside'] = max(row['max_vertices_inside'],count)
        row['max_tri_pairs'] = max(row['max_tri_pairs'],len(pairs))
        row['total_vertices_inside'] += count
        row['total_tri_pairs'] += len(pairs)
        row['shortfall_samples'] += int(bool(pairs) or depth.min() < FLOOR)
        vi = int(depth.argmin())
        if depth[vi] < row['minimum_m']:
            row.update(minimum_m=float(depth[vi]),frame=round(sample.frame,5),
                       zone=zones[vi],body_joint=face_groups[face_id[vi]],vertex=vi)
        bad = np.flatnonzero(depth < FLOOR)
        if len(bad):
            for v in bad:
                label = zones[v]
                witness = row['zones'].get(label)
                if witness is None or depth[v]<witness['minimum_m']:
                    row['zones'][label] = dict(minimum_m=float(depth[v]),frame=round(sample.frame,5),
                                               body_joint=face_groups[face_id[v]])
        if pairs:
            body_ids, module_ids = np.array(pairs).T
            penetration = pair_depth(sample.body[body_faces[body_ids]],p[faces[module_ids]])
            index = int(penetration.argmax())
            if penetration[index] >= row['max_triangle_depth_mm']:
                row.update(max_triangle_depth_mm=float(penetration[index]),triangle_frame=round(sample.frame,5),
                           triangle_zone=zones[faces[module_ids[index],0]],triangle_body_joint=face_groups[body_ids[index]])
        if not collect:
            continue
        requires = np.zeros(len(points),dtype=np.float32)
        if len(bad):
            requires[bad] = np.maximum(MARGIN-depth[bad],0)
        if pairs:
            touched = np.unique(module_ids)
            corners = faces[touched]
            marked = np.unique(corners)
            requires[marked] = np.maximum(requires[marked],MARGIN+np.maximum(0,-depth[marked]))
            coeff = np.array(((1/3,1/3,1/3),(.5,.5,0),(.5,0,.5),(0,.5,.5),
                              (.6,.2,.2),(.2,.6,.2),(.2,.2,.6)),dtype=np.float32)
            probes = np.einsum('kc,tcd->tkd',coeff,p[corners]).reshape(-1,3)
            probes_d,probes_n,_ = nearest(body_tree,probes)
            probes_d = probes_d.reshape(-1,len(coeff))
            deepest = probes_d.argmin(axis=1)
            mover = probes_n.reshape(-1,len(coeff),3)[np.arange(len(corners)),deepest]
            interior_req = MARGIN + np.maximum(0,-probes_d.min(axis=1))
            for triangle,heading,need in zip(corners,mover,interior_req):
                apply = triangle[requires[triangle] < need]
                requires[apply] = need
                normal[apply] = heading
            np.maximum.at(requires,faces[module_ids].ravel(),
                          np.repeat(MARGIN+penetration*.001,3))
        active = np.flatnonzero(requires)
        if not len(active):
            continue
        # Pull the posed normal back through the vertex's skin matrix. This
        # gives the signed-distance gradient with respect to a bind-space move.
        gradient = np.einsum('vji,vj->vi',basis[active],normal[active])
        magnitude = np.maximum(np.linalg.norm(gradient,axis=1),.25)
        gradient /= magnitude[:,None]
        space_requirement = requires[active]/magnitude
        compare = space_requirement>worst[active]
        worst[active[compare]] = space_requirement[compare]
        directions[active[compare]] = gradient[compare]
        violations.append((active,gradient,space_requirement))
    return rows,worst,directions,violations


def objective(rows):
    return (sum(r['total_tri_pairs']+2*r['total_vertices_inside'] for r in rows.values()),
            sum(r['shortfall_samples'] for r in rows.values()),
            max(0.-r['minimum_m'] for r in rows.values()))


def envelope(points, base, worst, directions, violations, graph, gain):
    inverse,_,_,_,copies = graph
    group_max = np.zeros(len(copies),dtype=worst.dtype)
    np.maximum.at(group_max,inverse,worst)
    fixed = group_max[inverse]
    delta = welded(directions*worst[:,None],graph)
    axis = delta/np.maximum(np.linalg.norm(delta,axis=1,keepdims=True),1.e-8)
    # A few projected passes incorporate competing pose normals. The busiest
    # locations still retain the maximum requested clearance after diffusion.
    for active,grad,needed in violations[::max(1,len(violations)//100)]:
        miss = needed-np.einsum('vi,vi->v',delta[active],grad)
        delta[active] += np.maximum(miss,0)[:,None]*grad*.38
    for _ in range(4):
        neighbors = laplacian(delta,graph)
        stronger = np.linalg.norm(neighbors,axis=1)>np.linalg.norm(delta,axis=1)
        delta[stronger] = .45*delta[stronger]+.55*neighbors[stronger]
    for _ in range(7):
        delta = welded(.54*delta + .46*laplacian(delta,graph),graph)
        deficit = np.maximum(0,fixed-np.einsum('vi,vi->v',delta,axis))
        delta += axis*deficit[:,None]
    move = points-base+delta*gain
    move *= np.minimum(1,CAP/np.maximum(np.linalg.norm(move,axis=1,keepdims=True),1.e-8))
    return base + move


def store_geometry(obj,p,w,names):
    obj.data.vertices.foreach_set('co',p.astype(np.float32).ravel())
    obj.data.normals_split_custom_set([(0.,0.,0.)]*len(obj.data.loops))
    obj.data.update()
    obj.vertex_groups.clear()
    groups = [obj.vertex_groups.new(name=name) for name in names]
    for i,j in zip(*np.nonzero(w)):
        groups[j].add([int(i)],float(w[i,j]),'REPLACE')


def fit(path,destination,slot,iterations):
    field = stash_neutral()
    scene,arm,body,actions = load_body_motion(MOTION)
    names = [bone.name for bone in arm.data.bones]
    garment = read_module(path,arm)
    initial,faces = arrays(garment)
    original_w = weights(garment,names)
    links = shoe_layer_links(garment,initial,original_w) if slot=='shoes' else ()
    base,w,zones,graph = field.apply(initial,faces,original_w,names,slot,links)
    if links:
        print('LAYER PAIRS',len(links),flush=True)
    _, body_faces = arrays(body)
    face_groups = np.asarray(names)[weights(body,names)[body_faces].sum(axis=1).argmax(axis=1)]
    samples = list(motion_samples(body,names,GLB(HERE/'body_male.glb'),GLB(MOTION)))
    print('FIT',slot,path.name,len(faces),'triangles',len(samples),'poses',flush=True)
    assert len(faces) <= TRI_LIMIT[slot], (len(faces),TRI_LIMIT[slot])
    best,best_score = base,None
    history = []
    # The coarse solve consumes a small cache. Full-bank scans stream their
    # trees and provide the final worst-case clearance constraints.
    coarse = [samples[0]]
    for clip in CLIPS:
        group = [s for s in samples if s.clip==clip]
        stride = 1 if slot=='shoes' and clip=='run' else 16
        coarse.extend(group[::stride])
        if group[-1] not in coarse:
            coarse.append(group[-1])
    prior_file = HERE/'qa'/f'{destination.stem}.json'
    if prior_file.exists():
        prior = json.loads(prior_file.read_text()).get('reimport',{})
        for clip,row in prior.items():
            if not row.get('shortfall_samples'):
                continue
            witness_frames = [row.get(key) for key in ('frame','triangle_frame') if row.get(key) is not None]
            candidates = [sample for sample in samples if sample.clip==clip and
                          any(abs(sample.frame-fr)<=1.8 for fr in witness_frames)]
            coarse.extend(sample for sample in candidates if sample not in coarse)
    for sample in coarse:
        sample.cached_tree = tree(sample.body,sample.faces)
    p = base
    for i in range(iterations+1):
        rows,req,axes,constraints = scan(p,w,faces,coarse,zones,body_faces,face_groups,i<iterations)
        score = objective(rows)
        history.append(dict(iteration=i,score=score,clips=rows))
        print('FIT ITER',i,score,[(c,r['max_vertices_inside'],r['max_tri_pairs'],round(r['minimum_m']*1000,2))
                                  for c,r in rows.items() if r['shortfall_samples']],flush=True)
        if best_score is None or score<best_score:
            best,best_score = p.copy(),score
        if not score[1] or i==iterations:
            break
        p = envelope(p,base,req,axes,constraints,graph,.90 if i<3 else .58)

    if best_score[1]:
        # Improve the whole-bank envelope from the same cap and its original
        # transferred surface. The reimport scan checks the chosen result.
        full_rows,req,axes,constraints = scan(best,w,faces,samples,zones,body_faces,face_groups,True,True)
        if objective(full_rows)[1]:
            candidate = envelope(best,base,req,axes,constraints,graph,.65)
            candidate_rows,*_ = scan(candidate,w,faces,coarse,zones,body_faces,face_groups,False)
            if objective(candidate_rows) <= best_score:
                best = candidate
        history.append(dict(iteration='full-bank',score=objective(full_rows),clips=full_rows))
    use_action(arm,None)
    set_frame(scene,1)
    store_geometry(garment,best,w,names)
    world = garment.matrix_world.copy()
    garment.parent = None
    garment.matrix_world = world
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    staging = HERE/'.runtime'/destination.name
    bpy.ops.export_scene.gltf(filepath=str(staging),export_format='GLB',use_selection=True,
                              export_animations=False,export_skins=True,export_yup=True,
                              export_tangents=bool(garment.data.uv_layers))
    staged = GLB(staging)
    if not staged.doc.get('images'):
        destination.write_bytes(staging.read_bytes())
    else:
        for texture_cap in (512,384,320,256):
            transcode(staged,destination,1024,texture_cap)
            if destination.stat().st_size <= 1.5*1024**2:
                break
    bpy.data.objects.remove(garment,do_unlink=True)
    check = read_module(destination,arm)
    q,qf = arrays(check)
    qw = weights(check,names)
    qzones = [region(names[i]) for i in qw.argmax(axis=1)] if slot!='hair' else ['head']*len(q)
    reimport_rows,*_ = scan(q,qw,qf,samples,qzones,body_faces,face_groups,False,True)
    # Direct Blender evaluation is an independent consistency check on the
    # analytical armature cache used for the all-sample bake.
    ids,packed = influences(qw)
    error = 0.
    for clip in ('rest',*CLIPS):
        sample = next(s for s in samples if s.clip==clip)
        use_action(arm,actions.get(clip))
        set_frame(scene,sample.frame)
        calculated,_ = skin(sample,ids,packed,q)
        error = max(error,float(np.max(abs(posed(check)-calculated))),
                    float(np.max(abs(posed(body)-sample.body))))
    if error >= .00001:
        print("Numerical versus Blender skin evaluation",error,"m",flush=True)
    assert error < .00004, error
    out = dict(source=str(path),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
               motion_sha256=hashlib.sha256(MOTION.read_bytes()).hexdigest(),slot=slot,triangles=len(qf),
               bytes=destination.stat().st_size,frames=len(samples),
               paired_layer_vertices=len(links),
               field_peak_displacement_mm=float(1000*np.linalg.norm(base-initial,axis=1).max()),
               baked_peak_offset_mm=float(1000*np.linalg.norm(best-base,axis=1).max()),
               skin_crosscheck_max_m=error,iterations=history,reimport=reimport_rows)
    write_json(HERE/'qa'/f'{destination.stem}.json',out)
    print('REIMPORT',destination.name,objective(reimport_rows),error,flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module',type=Path)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--slot',choices=TRI_LIMIT,required=True)
    parser.add_argument('--iterations',type=int,default=6)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    destination = args.destination.resolve()
    if destination.parent != HERE or destination.suffix.lower()!='.glb' or destination==args.module.resolve():
        parser.error('Destination must be a different GLB in the male output directory')
    fit(args.module.resolve(),destination,args.slot,args.iterations)
