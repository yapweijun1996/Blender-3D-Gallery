"""Compare the standalone GLB hair with its saved, rigged Blender source.

Run with Blender --background <source.blend> --python this_script. No input
file is modified. The nearest-vertex check is symmetric because glTF can split
vertices at normals/UV seams.
"""
import bpy, json, hashlib, math
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

BASE=Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/models/gjh-reference-visitor')
SOURCE=BASE/'sources/gjh-reference-visitor.blend'
GLB=BASE/'exports/gjh-visitor-hair.glb'
OUT=BASE/'qa/hair-redesign/hair-module-test.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes_before={'source':digest(SOURCE),'module':digest(GLB)}
scene=bpy.data.scenes['GJH Reference Visitor'];bpy.context.window.scene=scene
coll=next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
rig=next(o for o in coll.objects if o.type=='ARMATURE')
hair=next(o for o in coll.objects if o.type=='MESH' and o.name.startswith('Hair'))
if rig.animation_data:
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks: track.mute=True
scene.frame_set(1)
for bone in rig.pose.bones:
    bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.location=(0,0,0);bone.scale=(1,1,1)
rig.data.pose_position='REST';bpy.context.view_layer.update()

def evaluated_points(obj):
    deps=bpy.context.evaluated_depsgraph_get(); ev=obj.evaluated_get(deps);mesh=ev.to_mesh()
    points=[ev.matrix_world @ v.co for v in mesh.vertices];ev.to_mesh_clear();return points

def dist(a,b):
    tree=KDTree(len(b))
    for i,p in enumerate(b):tree.insert(p,i)
    tree.balance();ds=sorted(tree.find(p)[2] for p in a)
    return {'max_m':ds[-1], 'p95_m':ds[int((len(ds)-1)*.95)], 'mean_m':sum(ds)/len(ds)}
def compare(a,b):return {'source_to_module':dist(a,b), 'module_to_source':dist(b,a)}
source_rest=evaluated_points(hair)
old_objects=set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(GLB))
new_objects=set(scene.objects)-old_objects
modules=[o for o in new_objects if o.type=='MESH']
if len(modules)!=1:raise RuntimeError('Expected one imported hair mesh, got '+str([o.name for o in modules]))
module=modules[0]
bpy.context.view_layer.update();module_rest=evaluated_points(module)
rest_comparison=compare(source_rest,module_rest)
head=rig.pose.bones['Head'];rest_head_world=rig.matrix_world @ head.bone.matrix_local
rig.data.pose_position='POSE';head.rotation_euler=(math.radians(12), math.radians(-17), math.radians(8));bpy.context.view_layer.update()
head_world=rig.matrix_world @ head.matrix
attach_matrix=head_world @ rest_head_world.inverted()
module_posed=[attach_matrix @ p for p in module_rest]
source_posed=evaluated_points(hair)
posed_comparison=compare(source_posed,module_posed)
# Switch visibility through the view layer and read back the result.
hair.hide_set(True);module.hide_set(False);bpy.context.view_layer.update()
visible_module_mode={'original_visible':hair.visible_get(), 'module_visible':module.visible_get()}
hair.hide_set(False);module.hide_set(True);bpy.context.view_layer.update()
visible_original_mode={'original_visible':hair.visible_get(), 'module_visible':module.visible_get()}
threshold=1e-5
geometry_pass=all(v['max_m']<threshold for comp in (rest_comparison,posed_comparison) for v in comp.values())
visibility_pass=(visible_module_mode=={'original_visible':False,'module_visible':True} and visible_original_mode=={'original_visible':True,'module_visible':False})
hashes_after={'source':digest(SOURCE),'module':digest(GLB)}
result={'status':'PASS' if geometry_pass and visibility_pass and hashes_before==hashes_after else 'FAIL','blender':bpy.app.version_string,'sha256':hashes_before,'source_and_module_unchanged':hashes_before==hashes_after,'source_mesh':hair.name,'module_mesh':module.name,'counts':{'source_vertices':len(source_rest),'module_vertices':len(module_rest)},'threshold_m':threshold,'rest':rest_comparison,'head_rotation_radians':[math.radians(12),math.radians(-17),math.radians(8)],'rotated_head':posed_comparison,'hide_original_show_module':visible_module_mode,'show_original_hide_module':visible_original_mode,'limitations':['Tests numerical geometry and visibility in Blender only; no browser or Three.js runtime is exercised.','Tests one head rotation, not animation throughout every action.','Nearest-vertex comparison does not compare shading, materials or mesh topology.']}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print('HAIR_MODULE_QA',json.dumps(result))
if result['status']!='PASS':raise SystemExit(1)
