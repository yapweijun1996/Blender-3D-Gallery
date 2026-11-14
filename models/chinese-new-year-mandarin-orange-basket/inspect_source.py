from pathlib import Path
import bpy,json,runpy,hashlib,math
HERE=Path(__file__).resolve().parent
source=HERE/'sources/chinese-new-year-mandarin-orange-basket.blend';before=hashlib.sha256(source.read_bytes()).hexdigest();h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects['ASSET_ChineseNewYearMandarinOrangeBasket'];meshes=[o for o in root.children_recursive if o.type=='MESH']
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)>=2 and len({o.data.as_pointer() for o in meshes})==len(meshes)
assert not bpy.data.libraries
assert all(all(math.isfinite(c) for v in o.data.vertices for c in v.co) for o in meshes)
material=meshes[0].data.materials[0];node=material.node_tree.nodes.get('Principled BSDF');old_roughness=node.inputs['Roughness'].default_value;new_roughness=.17 if old_roughness>.3 else .73;node.inputs['Roughness'].default_value=new_roughness;material_name=material.name
edit=bpy.data.objects['BASKET_Base'];original_z=edit.location.z;edit.location.z+=.2
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'reports/source-edit.blend'),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(HERE/'reports/source-edit.blend'))
assert abs(bpy.data.objects['BASKET_Base'].location.z-original_z-.2)<1e-6
h['export'](HERE/'reports/source-edit.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(HERE/'reports/source.json').write_text(json.dumps({'result':'PASS','source_sha256':before,'metric_units':True,'editable_meshes':len(meshes),'independent_mesh_data':True,'edited_component':'BASKET_Base','edit':'local z +0.2m','source_preserved':True,'material':material_name,'old_roughness':old_roughness,'new_roughness':new_roughness},indent=2)+'\n')
