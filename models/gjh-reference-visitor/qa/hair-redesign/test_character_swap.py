"""Test standalone hair against the character GLB in Blender after import."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils.kdtree import KDTree
BASE=Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/models/gjh-reference-visitor')
CHAR=BASE/'exports/gjh-reference-visitor-rigged.glb'; MODULE=BASE/'exports/gjh-visitor-hair.glb';OUT=BASE/'qa/hair-redesign/character-swap-test.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={'character':digest(CHAR),'module':digest(MODULE)}
scene=bpy.data.scenes.new('Swap test');bpy.context.window.scene=scene
old=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(CHAR));char_objects=set(scene.objects)-old
rig=next(o for o in char_objects if o.type=='ARMATURE')
hair_candidates=[o for o in char_objects if o.type=='MESH' and o.get('partSlot')=='Hair']
if len(hair_candidates)!=1:raise RuntimeError('Expected one Hair partSlot, got '+str([o.name for o in hair_candidates]))
hair=hair_candidates[0]
if rig.animation_data:
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=True
scene.frame_set(1)
for bone in rig.pose.bones:
    bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.location=(0,0,0);bone.scale=(1,1,1)
rig.data.pose_position='REST';bpy.context.view_layer.update()
def points(obj):
    dg=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(dg);m=ev.to_mesh();r=[ev.matrix_world @ v.co for v in m.vertices];ev.to_mesh_clear();return r
def measure(a,b):
    t=KDTree(len(b))
    for i,p in enumerate(b):t.insert(p,i)
    t.balance();d=sorted(t.find(p)[2] for p in a)
    return {'max_m':d[-1],'p95_m':d[int((len(d)-1)*.95)],'mean_m':sum(d)/len(d)}
def compare(a,b):return {'character_to_module':measure(a,b),'module_to_character':measure(b,a)}
character_rest=points(hair)
old=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(MODULE));new=set(scene.objects)-old
module=next(o for o in new if o.type=='MESH');bpy.context.view_layer.update();module_rest=points(module)
rest=compare(character_rest,module_rest)
head=rig.pose.bones['Head'];rest_head=rig.matrix_world@head.bone.matrix_local
rig.data.pose_position='POSE';head.rotation_euler=(math.radians(12),math.radians(-17),math.radians(8));bpy.context.view_layer.update()
move=rig.matrix_world@head.matrix@rest_head.inverted();rotated=compare(points(hair),[move@p for p in module_rest])
hair.hide_set(True);module.hide_set(False);bpy.context.view_layer.update();swap={'original_visible':hair.visible_get(),'replacement_visible':module.visible_get()}
hair.hide_set(False);module.hide_set(True);bpy.context.view_layer.update();restore={'original_visible':hair.visible_get(),'replacement_visible':module.visible_get()}
after={'character':digest(CHAR),'module':digest(MODULE)};threshold=1e-5
ok=all(x['max_m']<threshold for c in (rest,rotated) for x in c.values()) and swap=={'original_visible':False,'replacement_visible':True} and restore=={'original_visible':True,'replacement_visible':False} and before==after
result={'status':'PASS' if ok else 'FAIL','blender':bpy.app.version_string,'sha256':before,'inputs_unchanged':before==after,'character_hair_node':hair.name,'character_hair_partSlot':hair.get('partSlot'),'head_bone':head.name,'module_node':module.name,'vertex_counts':{'character':len(character_rest),'module':len(module_rest)},'threshold_m':threshold,'rest':rest,'head_rotation_degrees':[12,-17,8],'rotated_head':rotated,'swap':swap,'restore':restore,'limitations':['Blender importer and visibility tested; no browser/Three.js runtime or full animation cycle tested.','Only a rigid head rotation was tested.','Nearest vertices do not establish topology or shading equality.']}
OUT.write_text(json.dumps(result,indent=2)+'\n');print('CHARACTER_SWAP_QA',json.dumps(result))
if not ok:raise SystemExit(1)
