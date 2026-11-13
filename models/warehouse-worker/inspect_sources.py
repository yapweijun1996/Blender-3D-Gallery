from pathlib import Path
import bpy,json,hashlib,importlib.util,shutil
H=Path(__file__).resolve().parent
source=H/'sources/warehouse-worker.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
assert bpy.context.scene.unit_settings.scale_length==1
assert bpy.data.objects.get('CharacterRoot')
for n in ['HeadJoint','RightShoulder','LeftShoulder']:
 assert {t.name for t in bpy.data.objects[n].animation_data.nla_tracks}=={'Idle','InspectParcel'}
o=bpy.data.objects['EditPocket'];old=float(o.data.vertices[0].co.x);m=o.data.materials[0];rough=float(m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value)
o.data.vertices[0].co.x=old+.015;m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.79
copy=H/'reports/source-edit.blend';bpy.ops.wm.save_as_mainfile(filepath=str(copy))
bpy.ops.wm.open_mainfile(filepath=str(copy));o=bpy.data.objects['EditPocket'];assert abs(o.data.vertices[0].co.x-old-.015)<1e-6;assert abs(o.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value-.79)<1e-6
spec=importlib.util.spec_from_file_location('warehouse-worker_helpers',H/'generate.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
g.select_clip('Idle',0);g.export(H/'reports/source-edit.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(H/'reports/sources.json').write_text(json.dumps({'status':'PASS','canonical_sha256':before,'source_copy_sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),'edited_component':'EditPocket','original_vertex_x':old,'saved_reopened_vertex_x':float(o.data.vertices[0].co.x),'material_roughness':.79,'saved_reopened':True,'export_without_regeneration':True,'canonical_unchanged':True},indent=2)+'\n')
