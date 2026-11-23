"""Package the Studio male body and its unchanged gesture bank."""
from copy import deepcopy
from asset_io import *

bpy.ops.wm.read_factory_settings(use_empty=True)
source = GLB(STUDIO/'body_male_v1.glb')
neutral = GLB(HERE.parents[3]/'models/chibi-dressup/base_body.glb')
def hierarchy(asset):
    return {name:asset.nodes[asset.parents[i]].get('name') for name,i in asset.ids.items()}
assert hierarchy(neutral) == hierarchy(source)
for item in source.nodes:
    if 'mesh' in item:
        item['name'] = 'Base_Body'
        source.doc['meshes'][item['mesh']]['name'] = 'Base_Body'
output = HERE/'body_male.glb'
for normal_cap in (384, 320, 256):
    transcode(source, output, 1024, normal_cap)
    if output.stat().st_size <= 1.2 * 1024**2:
        break
assert output.stat().st_size <= 1.2 * 1024**2

bpy.ops.wm.read_factory_settings(use_empty=True)
objects = import_objects(output)
arm, = [o for o in objects if o.type=='ARMATURE']
body, = [o for o in objects if o.type=='MESH' and len(o.vertex_groups)]
arm.name = 'Armature'
body.name = 'Base_Body'
for obj in objects - {arm,body}:
    bpy.data.objects.remove(obj, do_unlink=True)
for bone in arm.data.bones:
    assert bone.name in source.ids
bpy.context.scene.render.fps = 24
bpy.context.scene.render.fps_base = 1
bpy.context.preferences.filepaths.save_version = 0
prefs = bpy.context.preferences.filepaths
preview_type = prefs.bl_rna.properties.get('file_preview_type')
if preview_type and 'NONE' in preview_type.enum_items.keys():
    prefs.file_preview_type = 'NONE'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))

gesture = GLB(STUDIO/'hand_gestures_male.glb')
wanted = {f'hand_{name}_{side}' for side in ('L','R') for name in
          ('fist','open_relaxed','point','thumbs_up','peace','ok','grip_small','pinch','open_wide')}
assert {a['name'] for a in gesture.doc['animations']} == wanted
assert hierarchy(gesture)==hierarchy(source)
assert all(gesture.nodes[gesture.ids[name]] == source.nodes[idx] for name,idx in source.ids.items())
(HERE/'hand_gestures_male.glb').write_bytes(gesture.path.read_bytes())
print('Body bytes:',output.stat().st_size,'data texture cap:',normal_cap,flush=True)
