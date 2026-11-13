"""Reopen delivered source; measure real poses, save/reopen changed source, export."""
from pathlib import Path
import bpy,runpy,json,hashlib,math,tempfile
from mathutils import Vector
HERE=Path(__file__).resolve().parent;source=HERE/'sources/mall-emergency-exit-door.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source)
api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects[api['ROOT']]
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
meshes=[o for o in root.children_recursive if o.type=='MESH']
assert all(abs(v-1)<1e-6 for o in meshes for v in o.scale)
def digest(o):return hashlib.sha256(json.dumps([[list(v.co) for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons]],sort_keys=True).encode()).hexdigest()
original={o.name:digest(o) for o in meshes}
def bounds(o):
    pts=[o.matrix_world @ Vector(v) for v in o.bound_box]
    return pts
# Conservative oriented bounding boxes of the actual exported source meshes.
# SAT over world Z and the 2D axes of both objects; all checked components rotate around Z only.
def overlap(a,b):
    pa,pb=bounds(a),bounds(b)
    if max(p.z for p in pa)<=min(p.z for p in pb)+1e-6 or max(p.z for p in pb)<=min(p.z for p in pa)+1e-6:return False
    for o in [a,b]:
        for local in [Vector((1,0,0)),Vector((0,1,0))]:
            axis=o.matrix_world.to_3x3() @ local
            aa=[p.dot(axis) for p in pa];bb=[p.dot(axis) for p in pb]
            if max(aa)<=min(bb)+1e-6 or max(bb)<=min(aa)+1e-6:return False
    return True
names=['MODULE_DoorLeaf','MODULE_KickPlate','MODULE_PushBarMountLeft','MODULE_PushBarMountRight','MODULE_HorizontalPushBar','MODULE_RearPullHandle','MODULE_ExitPlaque','MODULE_CloserBody']
obstacles=[bpy.data.objects[n] for n in ['FRAME_LeftJamb','FRAME_RightJamb','FRAME_Head']]
checks=0;min_floor=100;min_top=100;maxradius=0;maxreach=0;closer_lengths=[]
for angle in range(101):
    for depression in [0,.009,.018]:
        root['door_angle_degrees']=angle;root['push_bar_depression_m']=depression;api['apply_pose'](root)
        for name in names:
            o=bpy.data.objects[name]
            for fixed in obstacles:
                assert not overlap(o,fixed),f'{name} collides {fixed.name} at {angle}/{depression}'
                checks+=1
            for p in bounds(o):
                min_floor=min(min_floor,p.z);maxreach=max(maxreach,-p.y);maxradius=max(maxradius,math.hypot(p.x+.48,p.y+.05))
        leaf=bpy.data.objects['MODULE_DoorLeaf'];min_top=min(min_top,2.1-max(p.z for p in bounds(leaf)))
        a=bpy.data.objects['CONNECTOR_CloserLeafPivot'].matrix_world.translation
        b=bpy.data.objects['CONNECTOR_CloserFramePivot'].matrix_world.translation
        e=bpy.data.objects['MODULE_CloserElbowPin'].location
        l1=math.hypot(e.x-a.x,e.y-a.y);l2=math.hypot(e.x-b.x,e.y-b.y)
        assert abs(l1-.28)<1e-6 and abs(l2-.28)<1e-6
assert min_floor>.0119 and min_top>.0049
# Pressed bar never intersects door leaf and remains independent of fixed bar mounts.
root['door_angle_degrees']=0;root['push_bar_depression_m']=.018;api['apply_pose'](root)
bar=bpy.data.objects['MODULE_HorizontalPushBar'];leaf=bpy.data.objects['MODULE_DoorLeaf']
gap=min(p.y for p in bounds(leaf))-max(p.y for p in bounds(bar))
assert abs(gap-.0675)<1e-6
source_report={'source_reopened':'PASS','source_sha256':before,'blender_version':bpy.app.version_string,'editable_mesh_parts':len(meshes),'source_units':'metres','source_scales':'UNIT','pose_sweep':{'status':'PASS','angle_samples':101,'angle_range_degrees':[0,100],'push_samples_m':[0,.009,.018],'tested_collision_pairs':checks,'collisions':0,'method':'Conservative oriented source mesh bounding boxes, separating axis tests; joined hinge/closer bearings excluded by design','moving_components':names,'fixed_obstacles':[o.name for o in obstacles],'minimum_floor_clearance_m':min_floor,'minimum_leaf_header_gap_m':min_top,'pressed_bar_to_leaf_gap_m':gap,'maximum_hardware_swept_radius_m':maxradius,'maximum_front_reach_from_wall_m':maxreach,'suggested_scene_front_clearance_m':1.1,'closer_link_lengths_m':[.28,.28]},'runtime_door_UI':'NOT IMPLEMENTED','safety_compliance':'NOT CLAIMED'}
(HERE/'reports/sources.json').write_text(json.dumps(source_report,indent=2)+'\n')
root['door_angle_degrees']=85;root['push_bar_depression_m']=.018;api['apply_pose'](root)
fixture=Path(tempfile.mkdtemp(prefix='mall-emergency-exit-door-edit-'));editedSource=fixture/'edited.blend';editedGlb=fixture/'edited.glb'
assert all(digest(o)==original[o.name] for o in meshes)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(editedSource),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(editedSource));root=bpy.data.objects[api['ROOT']]
assert root['door_angle_degrees']==85 and root['push_bar_depression_m']==.018
api['export'](root,editedGlb);assert sha(source)==before
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(editedGlb),'fixtureBlend':str(editedSource),'originalSourceSha256':before,'shippedSourceHashUnchanged':True,'unchangedMeshCoordinates':len(meshes)},indent=2)+'\n')
print('Source mesh collision sweep and real 85 degree / 18 mm edit saved, reopened, exported:',editedGlb)
