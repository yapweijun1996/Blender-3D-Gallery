"""Independently check the fixed blend, its GLB skin and two stress poses.

Blender --python hand_check.py -- [--renderer auto|workbench|cycles|none].
Distances are in Blender units. Scene edits for posing and lighting are in RAM.
"""
import argparse
import ctypes
import hashlib
import json
import math
import platform
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
MASTER = OUT.parent/'master'/'GJH_Chibi_Master_rigged.blend'
FIXED = OUT/'hands_fixed.blend'
GLB = OUT/'base_body_handfix.glb'
DIGITS = ('Index','Middle','Ring','Pinky')
SIDES = (('Left',1),('Right',-1))
DOWN = Vector((0,0,-1))


def load(path):
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    body = bpy.data.objects['Base_Body']
    return body, bpy.data.objects['Armature']


def xyz(v):
    return tuple(round(c,8) for c in v)


def world_vertices(body):
    return [body.matrix_world @ v.co for v in body.data.vertices]


def weights(body):
    names = [v.name for v in body.vertex_groups]
    return [{names[g.group]:g.weight for g in v.groups if g.weight>0} for v in body.data.vertices]


def chain_count(w, threshold):
    digits = defaultdict(float)
    for name, weight in w.items():
        if 'Hand' in name and name[-1].isdigit():
            digits[name[:-1]] += weight
    return sum(weight>threshold for weight in digits.values())


def components(graph):
    pending = set(graph)
    while pending:
        start = pending.pop()
        group = [start]
        for p in group:
            for q in graph[p].intersection(pending):
                pending.remove(q)
                group.append(q)
        yield group


def section(vertices, triangles, x):
    # Match oppositely traversed intersection edges and imported UV seams.
    # Count only closed 2-regular contours, and flag all open/branched ones.
    graph = defaultdict(set)
    for tri in triangles:
        hit = []
        for i,j in zip(tri, tri[1:]+tri[:1]):
            p,q = vertices[i],vertices[j]
            if (p.x < x) == (q.x < x):
                continue
            if p.x>q.x:
                p,q = q,p
            t = (x-p.x)/(q.x-p.x)
            hit.append((round(p.y+t*(q.y-p.y),7),round(p.z+t*(q.z-p.z),7)))
        if len(hit)==2 and hit[0]!=hit[1]:
            a,b = hit
            graph[a].add(b)
            graph[b].add(a)
    groups = sorted(components(graph),key=lambda g: min(y for y,z in g))
    closed = [g for g in groups if all(len(graph[p])==2 for p in g)]
    intervals = [(min(p[0] for p in g),max(p[0] for p in g)) for g in closed]
    return {'closed_loops':len(closed), 'open_or_branched':len(groups)-len(closed),
            'min_clear_y_gap':min((b[0]-a[1] for a,b in zip(intervals,intervals[1:])),default=None),
            'y_centers':[(a+b)/2 for a,b in intervals]}


def palm_patch(mesh,arm,side,sign):
    # Identify the central palmar patch ON THE MASTER by anatomical landmarks.
    # Freeze face indices before opening the result. This never selects faces
    # from the candidate by their repaired normal.
    prefix = 'mixamorig:'+side+'Hand'
    wrist = arm.data.bones[prefix].head_local.copy()
    index = arm.data.bones[prefix+'Index1'].head_local
    pinky = arm.data.bones[prefix+'Pinky1'].head_local
    distal = (index+pinky)/2-wrist
    across = (pinky-index).normalized()
    palmar = sign*across.cross(distal).normalized()
    ids = []
    for p in mesh.polygons:
        c = p.center
        fraction = (sign*c.x-sign*wrist.x)/(sign*distal.x)
        center = wrist + fraction*distal
        if 0.47<fraction<0.89 and abs((c-center).dot(across))<0.023:
            if (c-center).dot(palmar)>0 and p.normal.dot(palmar)>0.45:
                ids.append(p.index)
    assert ids
    return ids


def surface_caps(body,arm,sign,side):
    # Track distal cap vertices of independent digit islands from the master.
    # These tips measure skin geometry and are independent of bone tail length.
    coords = world_vertices(body)
    caps = {}
    shafts = {}
    for cut,names in ((0.323,('Thumb',)),(0.356,DIGITS)):
        graph = defaultdict(set)
        for e in body.data.edges:
            i,j = e.vertices
            p,q = tuple(coords[i]),tuple(coords[j])
            if min(sign*p[0],sign*q[0])>cut:
                graph[p].add(q)
                graph[q].add(p)
        groups = sorted(components(graph),key=lambda g:sum(p[1] for p in g)/len(g))
        assert len(groups)==(2 if names==('Thumb',) else 4)
        for name,g in zip(names,groups):
            chain = 'mixamorig:'+side+'Hand'+name
            axis = (arm.data.bones[chain+'3'].tail_local -
                    arm.data.bones[chain+'1'].head_local).normalized()
            end = max(Vector(p).dot(axis) for p in g)
            cap = {p for p in g if Vector(p).dot(axis) > end-0.004}
            # Exactly one index per distinct location, irrespective of UV splits.
            cap_ids = {p:i for i,v in enumerate(coords) if (p:=tuple(v)) in cap}
            caps[name] = list(cap_ids.values())
            points=set(g)
            shafts[name]={i for i,v in enumerate(coords) if tuple(v) in points}
    return caps,shafts


def bone_state(arm):
    return {b.name:(b.parent.name if b.parent else None, b.matrix_local.copy(),
                    b.head_local.copy(),b.tail_local.copy()) for b in arm.data.bones}


def rest_check():
    src,rig = load(MASTER)
    before = world_vertices(src)
    old_weights = weights(src)
    tris = [tuple(f.vertices) for f in src.data.polygons]
    old_rig = bone_state(rig)
    patches = {s:palm_patch(src.data,rig,s,sign) for s,sign in SIDES}
    caps = {s:surface_caps(src,rig,sign,s) for s,sign in SIDES}
    body,arm = load(FIXED)
    after = world_vertices(body)
    assert len(before)<=len(after)
    new_tris=[tuple(f.vertices) for f in body.data.polygons]
    lineage=[x.value for x in body.data.attributes['source_triangle'].data]
    assert set(lineage)==set(range(len(tris)))
    children=defaultdict(list)
    for i,parent in enumerate(lineage):
        children[parent].append(i)
    for parent,indices in children.items():
        corners={v for i in indices for v in new_tris[i]}
        assert set(tris[parent])<=corners
        if any(abs(before[i].x)<=0.27 for i in tris[parent]):
            assert len(indices)==1 and corners==set(tris[parent])
    nonhand = [i for i,v in enumerate(before) if abs(v.x)<=0.27]
    fixed_weights = weights(body)
    rig_after = bone_state(arm)
    assert set(old_rig)==set(rig_after)
    changed = [k for k,(parent,_,_,_) in old_rig.items() if rig_after[k][0]!=parent]
    bone_delta = max(max(abs(new-old) for u,v in zip(a,b) for new,old in zip(u,v))
                     for k,(_,a,_,_) in old_rig.items() if 'Hand' not in k
                     for b in [rig_after[k][1]])
    nonhand_tail = max((old_rig[k][3]-rig_after[k][3]).length for k in old_rig if 'Hand' not in k)
    result = {'geometry':{'vertices':len(after),'triangles':len(new_tris),'nonhand_n':len(nonhand),
                           'nonhand_max_delta':max((before[i]-after[i]).length for i in nonhand),
                           'outside_wrist_max_delta':max((u-v).length for u,v in zip(before,after) if abs(u.x)<=0.251),
                           'nonhand_weight_changes':sum(old_weights[i]!=fixed_weights[i] for i in nonhand)},
              'rig':{'bones':len(rig_after),'changed_parents':changed,'nonhand_matrix_delta':bone_delta,
                     'nonhand_tail_delta':nonhand_tail,'groups':len(body.vertex_groups)},
              'weights':{'bleed_joint_threshold_source':sum(len({k[:-1] for k,w in d.items() if
                          'Hand' in k and k[-1].isdigit() and w>0.2})>1 for d in old_weights),
                         'bleed_chain_total_source':sum(chain_count(w,0.2)>1 for w in old_weights),
                         'bleed_above_0.2':sum(chain_count(w,0.2)>1 for w in fixed_weights),
                         'mixed_chains_any_weight':sum(chain_count(w,0)>1 for w in fixed_weights),
                         'unweighted':sum(not w for w in fixed_weights),'above_four':sum(len(w)>4 for w in fixed_weights),
                         'max_influences':max(map(len,fixed_weights)),
                         'max_sum_error':max(abs(sum(w.values())-1) for w in fixed_weights)}}
    result['hands']={}
    for side,sign in SIDES:
        prefix = 'mixamorig:'+side+'Hand'
        faces = [body.data.polygons[i] for parent in patches[side] for i in children[parent]]
        mean = sum((p.normal*p.area for p in faces),Vector())/sum(p.area for p in faces)
        cap_ids,shaft_ids=caps[side]
        surface_dirs = {}
        rig_dirs = {}
        foreign=0
        for digit in ('Thumb',*DIGITS):
            root = rig_after[prefix+digit+'1'][2]
            tip = sum((after[i] for i in cap_ids[digit]),Vector())/len(cap_ids[digit])
            surface_dirs[digit] = (tip-root).normalized()
            rig_dirs[digit] = (rig_after[prefix+digit+'3'][3]-root).normalized()
            shaft=shaft_ids[digit].copy()
            for parent,tri in enumerate(tris):
                if set(tri)<=shaft_ids[digit]:
                    shaft.update(v for i in children[parent] for v in new_tris[i])
            foreign+=sum(any(not k.startswith(prefix+digit) for k in fixed_weights[i]) for i in shaft)
        def yaw(v):
            return math.degrees(math.atan2(v.y,sign*v.x))
        def gaps(dirs):
            yaws = [yaw(dirs[d]) for d in DIGITS]
            return [round(b-a,4) for a,b in zip(yaws,yaws[1:])]
        result['hands'][side] = {
            'palm_faces':len(faces),'palm_area_mean_normal':xyz(mean),
            'palm_unit_normal':xyz(mean.normalized()),'degrees_from_down':math.degrees(mean.angle(DOWN)),
            'thumb_surface_dir':xyz(surface_dirs['Thumb']),'index_surface_dir':xyz(surface_dirs['Index']),
            'thumb_index_degrees':math.degrees(surface_dirs['Thumb'].angle(surface_dirs['Index'])),
            'surface_splay_degrees':gaps(surface_dirs),'bone_splay_degrees':gaps(rig_dirs),
            'free_finger_vertices_with_foreign_weights':foreign,
            'sections':{str(x):section(after,new_tris,sign*x) for x in (0.34,0.38)}}
    return body,arm,before,after,result


def glb_check(body,arm):
    raw = GLB.read_bytes()
    length,tag = struct.unpack_from('<I4s',raw,12)
    assert raw[:4]==b'glTF' and tag==b'JSON'
    doc = json.loads(raw[20:20+length])
    offset = 20+length+8
    def values(index):
        a = doc['accessors'][index]
        view = doc['bufferViews'][a['bufferView']]
        typ = {5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']]
        n = {'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        fmt = '<'+typ*n
        start = offset+view.get('byteOffset',0)+a.get('byteOffset',0)
        stride = view.get('byteStride',struct.calcsize(fmt))
        return [struct.unpack_from(fmt,raw,start+i*stride) for i in range(a['count'])]
    skin, = doc['skins']
    js = [doc['nodes'][i]['name'] for i in skin['joints']]
    prim, = doc['meshes'][0]['primitives']
    attributes = prim['attributes']
    pos = values(attributes['POSITION'])
    joints = values(attributes['JOINTS_0'])
    influences = values(attributes['WEIGHTS_0'])
    assert len(pos)==len(joints)==len(influences) and 'WEIGHTS_1' not in attributes
    assert set(js)==set(arm.data.bones.keys()) and len(js)==len(values(skin['inverseBindMatrices']))
    assert any(n.get('skin')==0 and n.get('mesh')==0 for n in doc['nodes'])
    nodes=doc['nodes']
    parents={child:i for i,node in enumerate(nodes) for child in node.get('children',[])}
    def global_matrix(i):
        node=nodes[i]
        if 'matrix' in node:
            flat=node['matrix']
            local=Matrix([flat[k:k+4] for k in range(0,16,4)]).transposed()
        else:
            x,y,z,w=node.get('rotation',(0,0,0,1))
            local=Matrix.LocRotScale(Vector(node.get('translation',(0,0,0))),
                    Quaternion((w,x,y,z)),Vector(node.get('scale',(1,1,1))))
        return global_matrix(parents[i]) @ local if i in parents else local
    mesh_node=next(i for i,n in enumerate(nodes) if n.get('skin')==0)
    inv_mesh=global_matrix(mesh_node).inverted()
    bind_error=0
    for joint,flat in zip(skin['joints'],values(skin['inverseBindMatrices'])):
        inv_bind=Matrix([flat[k:k+4] for k in range(0,16,4)]).transposed()
        bind=inv_mesh @ global_matrix(joint) @ inv_bind
        bind_error=max(bind_error,max(abs(bind[i][j]-float(i==j)) for i in range(4) for j in range(4)))
        b=arm.data.bones[nodes[joint]['name']]
        if b.parent:
            assert nodes[parents[joint]]['name']==b.parent.name
    # Compare actual per-vertex glTF weights against all candidates at the
    # corresponding .blend position, including duplicated texture seam vertices.
    expected = defaultdict(list)
    for p,w in zip(world_vertices(body),weights(body)):
        expected[xyz((p.x,p.z,-p.y))].append(w)
    max_error = 0
    for v,j,w in zip(pos,joints,influences):
        actual = {js[k]:a for k,a in zip(j,w) if a>0}
        assert actual and xyz(v) in expected
        max_error = max(max_error,min(max(abs(u.get(k,0)-actual.get(k,0)) for k in u.keys()|actual.keys())
                                      for u in expected[xyz(v)]))
    return {'meshes':len(doc['meshes']),'skins':len(doc['skins']),'joints':len(js),
            'animations':len(doc.get('animations',[])),'vertices':len(pos),
            'triangles':len(values(prim['indices']))//3,'max_skin_weight_delta':max_error,
            'max_rest_skin_matrix_delta':bind_error}


def pose(arm,mode):
    for b in arm.pose.bones:
        b.matrix_basis = Matrix.Identity(4)
    for side,sign in SIDES:
        for digit in (*DIGITS,'Thumb'):
            name = 'mixamorig:'+side+'Hand'+digit
            for i in range(1,5):
                b = arm.pose.bones[name+str(i)]
                rest = b.bone.matrix_local.to_quaternion()
                direction = b.bone.tail_local - b.bone.head_local
                if mode=='fist':
                    axis = direction.cross(DOWN).normalized()
                    angle = 70 if digit!='Thumb' else (24,32,28,15)[i-1]
                else:
                    axis = Vector((0,0,sign))
                    angle = dict(Index=-12,Middle=-4,Ring=4,Pinky=12,Thumb=-10)[digit] if i==1 else 0
                b.rotation_mode='QUATERNION'
                b.rotation_quaternion=Quaternion(rest.inverted() @ axis, math.radians(angle))
    bpy.context.view_layer.update()


def configure(scene,renderer,body):
    if renderer in ('auto','workbench') and platform.system()=='Darwin':
        metal=ctypes.CDLL('/System/Library/Frameworks/Metal.framework/Metal')
        metal.MTLCreateSystemDefaultDevice.restype=ctypes.c_void_p
        if not metal.MTLCreateSystemDefaultDevice():
            if renderer=='workbench':
                raise RuntimeError('Workbench unavailable: this Blender process has no Metal device.')
            print('Workbench unavailable: no Metal device. Rendering with Cycles CPU.',flush=True)
            renderer='cycles'
    if renderer=='auto':
        renderer='workbench'
    scene.render.engine = 'BLENDER_WORKBENCH' if renderer=='workbench' else 'CYCLES'
    scene.render.resolution_x=600
    scene.render.resolution_y=480
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.render.use_compositing=False
    scene.render.use_sequencer=False
    scene.view_settings.view_transform='AgX'
    if renderer=='workbench':
        shade=scene.display.shading
        shade.light='STUDIO'
        shade.color_type='SINGLE'
        shade.single_color=(0.73,0.54,0.39)
        shade.show_shadows=True
        shade.show_cavity=True
    else:
        scene.cycles.device='CPU'
        scene.cycles.samples=12
        scene.cycles.use_denoising=True
        world=bpy.data.worlds.new('QA studio')
        scene.world=world
        world.use_nodes=True
        world.node_tree.nodes['Background'].inputs[0].default_value=(0.34,0.38,0.43,1)
        world.node_tree.nodes['Background'].inputs[1].default_value=0.36
        clay=bpy.data.materials.new('QA matte clay')
        clay.use_nodes=True
        bsdf=clay.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=(0.63,0.44,0.31,1)
        bsdf.inputs['Roughness'].default_value=0.8
        body.data.materials.clear()
        body.data.materials.append(clay)
        for n,power,size in [('QA Key',3.4,0.17),('QA Fill',0.9,0.23),('QA Rim',2.4,0.14)]:
            data=bpy.data.lights.new(n,'AREA')
            data.energy=power
            data.shape='DISK'
            data.size=size
            light=bpy.data.objects.new(n,data)
            scene.collection.objects.link(light)
    data=bpy.data.cameras.new('QA orthographic')
    camera=bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(camera)
    scene.camera=camera
    data.type='ORTHO'
    data.clip_start=0.01
    data.clip_end=4
    return camera,renderer


def render_view(scene,camera,points,side,sign,mode,view):
    direction=Vector({'dorsal':(0.08*sign,0.02,1),'palmar':(0.62*sign,0.12,-1),
                      'radial':(0.34*sign,-1,-0.14)}[view]).normalized()
    right=Vector((1,0,0))
    right=(right-direction*right.dot(direction)).normalized()
    up=direction.cross(right)
    center=Vector()
    widths=[]
    for axis in (right,up,direction):
        values=[v.dot(axis) for v in points]
        center+=axis*((min(values)+max(values))/2)
        widths.append(max(values)-min(values))
    camera.rotation_euler=Matrix((right,up,direction)).transposed().to_euler()
    camera.location=center+0.6*direction
    camera.data.clip_end=0.6+widths[2]/2+0.012
    if scene.render.engine=='CYCLES':
        for name,u,v,w in [('QA Key',-0.16,0.18,0.20),('QA Fill',0.19,-0.02,0.26),
                            ('QA Rim',0.09,0.22,-0.14)]:
            light=scene.objects[name]
            light.location=center+u*right+v*up+w*direction
            light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=max(widths[0],widths[1]*scene.render.resolution_x/scene.render.resolution_y)*1.22
    path=OUT/f'{side.lower()}_{mode}_{view}.png'
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    return path


def hand_topology(body,rest):
    triangles=[tuple(p.vertices) for p in body.data.polygons]
    seam_ids={}
    ids=[seam_ids.setdefault(tuple(p),i) for i,p in enumerate(rest)]
    faces=[frozenset(ids[i] for i in f) for f in triangles]
    edges=Counter()
    for f in triangles:
        for a,b in zip(f,f[1:]+f[:1]):
            if min(abs(rest[a].x),abs(rest[b].x))>0.27:
                edges[tuple(sorted((ids[a],ids[b])))] += 1
    return triangles,faces,sum(n!=2 for n in edges.values())


def intersections(points,rest,triangles,faces):
    tree=BVHTree.FromPolygons(points,triangles,all_triangles=True)
    return sum(1 for a,b in tree.overlap(tree) if a<b and not (faces[a]&faces[b])
               and any(abs(rest[i].x)>0.27 for i in triangles[a]+triangles[b]))


def check_poses(body,arm,before,after,renderer):
    scene=bpy.context.scene
    camera=None
    if renderer!='none':
        camera,renderer=configure(scene,renderer,body)
    triangles,faces,open_edges=hand_topology(body,after)
    duplicates=defaultdict(list)
    for i,p in enumerate(after):
        if abs(p.x)>0.27:
            duplicates[tuple(p)].append(i)
    original_seams=defaultdict(list)
    for i,p in enumerate(before):
        if abs(p.x)>0.27:
            original_seams[tuple(p)].append(i)
    seam_groups=list(duplicates.values())+list(original_seams.values())
    topology={'nonmanifold_hand_edges':open_edges,
              'rest_intersecting_triangle_pairs':intersections(after,after,triangles,faces)}
    results={}
    for mode in ('fist','spread'):
        pose(arm,mode)
        obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        points=world_vertices(obj)
        crack=max((points[i]-points[g[0]]).length for g in seam_groups for i in g)
        results[mode]={'max_duplicate_seam_opening':crack,
                       'nonhand_original_to_pose_max_delta':max((p-points[i]).length
                             for i,p in enumerate(before) if abs(p.x)<=0.27),
                       'intersecting_triangle_pairs':intersections(points,after,triangles,faces),
                       'renders':{}}
        if mode=='fist':
            bones=[arm.pose.bones['mixamorig:'+side+'Hand'+digit+str(i)]
                   for side,_ in SIDES for digit in DIGITS for i in range(1,5)]
            angles=[math.degrees(b.rotation_quaternion.angle) for b in bones]
            results[mode].update(non_thumb_segments=len(angles),min_curl_degrees=min(angles),
                                 max_curl_degrees=max(angles))
        else:
            results[mode]['finger_root_spread_degrees']=[-12,-4,4,12]
        for side,sign in SIDES:
            ids=[i for i,p in enumerate(after) if sign*p.x>0.26]
            for view in ('dorsal','palmar','radial'):
                if camera:
                    path=render_view(scene,camera,[points[i] for i in ids],side,sign,mode,view)
                    results[mode]['renders'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return renderer,results,topology


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--renderer',choices=['auto','workbench','cycles','none'],default='auto')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    body,arm,before,after,r=rest_check()
    r['glb']=glb_check(body,arm)
    print('REST_AND_EXPORT '+json.dumps(r,indent=2),flush=True)
    r['renderer'],r['poses'],r['topology']=check_poses(body,arm,before,after,args.renderer)
    print('POSES '+json.dumps(r['poses'],indent=2),flush=True)
    print('TOPOLOGY '+json.dumps(r['topology']),flush=True)
    r['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (MASTER,FIXED,GLB)}
    if r['renderer']!='none':
        (OUT/'hand_check.json').write_text(json.dumps(r,indent=2)+'\n')
    assert r['geometry']['nonhand_max_delta']<0.0005
    assert r['rig']['bones']==r['rig']['groups']==65 and not r['rig']['changed_parents']
    assert r['rig']['nonhand_matrix_delta']<1e-6 and r['rig']['nonhand_tail_delta']<1e-6
    assert r['weights']['unweighted']==r['weights']['above_four']==r['weights']['mixed_chains_any_weight']==0
    assert r['weights']['max_sum_error']<1e-6
    assert r['glb']['max_skin_weight_delta']<1e-5 and r['glb']['animations']==0
    assert r['glb']['max_rest_skin_matrix_delta']<1e-5
    for v in r['hands'].values():
        assert v['free_finger_vertices_with_foreign_weights']==0
        assert v['palm_unit_normal'][2]<-0.95 and v['thumb_surface_dir'][1]<-0.65
        assert all(a['closed_loops']==4 and a['open_or_branched']==0 and a['min_clear_y_gap']>0
                   for a in v['sections'].values())
        assert all(5<=a<=8 for a in v['surface_splay_degrees']+v['bone_splay_degrees'])
    assert all(p['max_duplicate_seam_opening']<1e-6 for p in r['poses'].values())
    assert all(p['nonhand_original_to_pose_max_delta']<0.0005 for p in r['poses'].values())
    assert all(p['intersecting_triangle_pairs']==0 for p in r['poses'].values())
    assert all(n==0 for n in r['topology'].values())
    assert r['poses']['fist']['non_thumb_segments']==32
    assert 69.99<r['poses']['fist']['min_curl_degrees']<=r['poses']['fist']['max_curl_degrees']<70.01
    print('NUMERICAL CHECKS PASSED',flush=True)


if __name__=='__main__':
    main()
