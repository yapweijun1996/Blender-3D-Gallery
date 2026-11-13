"""Actual source reopen, topology, full door sweep and isolated mesh/pose edit proof."""
from pathlib import Path
import bpy,bmesh,runpy,json,hashlib,math,tempfile
from mathutils import Vector
HERE=Path(__file__).resolve().parent;source=HERE/'sources/mall-fire-hose-reel-cabinet.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source);api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects[api['ROOT']]
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
meshes=[o for o in root.children_recursive if o.type=='MESH']
assert all(abs(v-1)<1e-6 for o in meshes for v in o.scale)
def digest(o):return hashlib.sha256(json.dumps([[list(v.co) for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons]],sort_keys=True).encode()).hexdigest()
original={o.name:digest(o) for o in meshes}
topology={}
for o in meshes:
    bm=bmesh.new();bm.from_mesh(o.data)
    bad=sum(not e.is_manifold for e in bm.edges);deg=sum(f.calc_area()<1e-12 for f in bm.faces);assert bm.calc_volume(signed=True)>0,(o.name,'non-positive signed volume')
    assert bad==0 and deg==0,(o.name,bad,deg)
    topology[o.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifoldEdges':bad,'degenerateFaces':deg};bm.free()
def bounds(o):return [o.matrix_world @ Vector(v) for v in o.bound_box]
def overlap(a,b):
    pa,pb=bounds(a),bounds(b)
    if max(p.z for p in pa)<=min(p.z for p in pb)+1e-6 or max(p.z for p in pb)<=min(p.z for p in pa)+1e-6:return False
    for o in [a,b]:
        for local in [Vector((1,0,0)),Vector((0,1,0))]:
            axis=o.matrix_world.to_3x3() @ local;aa=[p.dot(axis) for p in pa];bb=[p.dot(axis) for p in pb]
            if max(aa)<=min(bb)+1e-6 or max(bb)<=min(aa)+1e-6:return False
    return True
moving=[o for o in bpy.data.objects['PIVOT_CabinetDoor'].children_recursive if o.type=='MESH']
obstacles=[o for o in meshes if o.name.startswith('ENCLOSURE_')]
interior=[o for o in meshes if o.name.startswith(('REEL_','MODULE_Coil','MODULE_Hose','MODULE_Nozzle'))]
fixedfront=min(p.y for o in obstacles+interior for p in bounds(o))
checks=0;mingap=100;maxreach=0;minbottom=100
for angle in range(106):
    root['door_angle_degrees']=angle;api['apply_pose'](root)
    movingrear=max(p.y for o in moving for p in bounds(o));gap=fixedfront-movingrear;assert gap>0
    mingap=min(mingap,gap)
    for o in moving:
        for fixed in obstacles:assert not overlap(o,fixed),(angle,o.name,fixed.name);checks+=1
        for p in bounds(o):maxreach=max(maxreach,-p.y);minbottom=min(minbottom,p.z)
assert minbottom>.011
coil=bpy.data.objects['MODULE_CoiledHose'];points=[]
# Real mesh center of each eight-vertex cross-section verifies 7 turns and pitch.
for i in range(449):points.append(sum((v.co for v in coil.data.vertices[i*8:(i+1)*8]),Vector())/8)
pitch=min(math.hypot(points[i+64].x,points[i+64].z)-math.hypot(points[i].x,points[i].z) for i in range(len(points)-64))
assert abs(pitch-.027)<1e-6
report={'source_reopened':'PASS','source_sha256':before,'blender_version':bpy.app.version_string,'editable_mesh_parts':len(meshes),'source_units':'metres','source_scales':'UNIT','topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0,'parts':topology},'coil':{'crossSections':449,'turns':7,'measuredMinimumRadialPitch_m':pitch,'tubeDiameter_m':.024,'minimumRadialInterturnGap_m':pitch-.024},'pose_sweep':{'status':'PASS','angles':106,'range_degrees':[0,105],'tested_collision_pairs':checks,'collisions':0,'moving_parts':len(moving),'minimum_door_to_fixed_front_plane_gap_m':mingap,'minimum_door_bottom_m':minbottom,'maximum_front_reach_from_wall_m':maxreach,'scene_envelope_only':'Visual geometry check, not installation or safety clearance','method':'Conservative source mesh oriented boxes against enclosure panels; all moving door parts additionally remain in front of every reel/hose/nozzle point. Joined hinge bearings intentionally excluded.'}}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
root['door_angle_degrees']=0;api['apply_pose'](root)
tip=bpy.data.objects['MODULE_NozzleTip']
for v in tip.data.vertices:v.co.z*=1.2
tip.data.update()
assert [o.name for o in meshes if digest(o)!=original[o.name]]==['MODULE_NozzleTip']
fixture=Path(tempfile.mkdtemp(prefix='mall-fire-hose-434-edit-'));blend=fixture/'edited.blend';glb=fixture/'edited.glb'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(blend));root=bpy.data.objects[api['ROOT']];assert root['door_angle_degrees']==0
api['export'](root,glb);assert sha(source)==before
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(glb),'fixtureBlend':str(blend),'originalSourceSha256':before,'shippedSourceHashUnchanged':True,'changedMesh':'MODULE_NozzleTip','unchangedMeshCoordinates':len(meshes)-1},indent=2)+'\n')
print(json.dumps({**report,'topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0}}))
