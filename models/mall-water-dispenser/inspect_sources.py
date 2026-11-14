from pathlib import Path
import bpy, bmesh, hashlib, json

p=Path(__file__).resolve().parent; source=p/'sources'/'mall-water-dispenser.blend'; before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source)); root=bpy.data.objects['ASSET_MallWaterDispenser']; meshes=[o for o in root.children_recursive if o.type=='MESH']
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
for o in meshes:
    bm=bmesh.new(); bm.from_mesh(o.data); assert bm.calc_volume()>0, o.name; bm.free()
target=sorted(meshes,key=lambda o:o.name)[0]; target_name=target.name
for v in target.data.vertices: v.co.x*=.97
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.71
out=p/'reports'/'source-edit'; out.mkdir(exist_ok=True); edited=out/'mall-water-dispenser-edited.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(edited),compress=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
bpy.ops.wm.open_mainfile(filepath=str(edited)); import importlib.util
spec=importlib.util.spec_from_file_location('mall_water_generator',p/'generate.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); mod.export(out/'edited.glb')
(p/'reports'/'sources.json').write_text(json.dumps({'source_sha256':before,'editable_mesh_parts':len(meshes),'edited_mesh':target_name,'saved_reopened':True,'export_without_regeneration':True,'original_source_unchanged':True},indent=2)+'\n')
print('PASS source edit saved copy; canonical source unchanged')
