from pathlib import Path
import bpy,json,runpy,hashlib,math
HERE=Path(__file__).resolve().parent
source=HERE/'sources/malaysia-terrace-house-porch.blend';before=hashlib.sha256(source.read_bytes()).hexdigest();h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects['ASSET_MalaysiaTerraceHousePorch'];meshes=[o for o in root.children_recursive if o.type=='MESH']
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)>=2 and len({o.data.as_pointer() for o in meshes})==len(meshes)
assert not bpy.data.libraries
assert all(all(math.isfinite(c) for v in o.data.vertices for c in v.co) for o in meshes)
edit=bpy.data.objects['PORCH_Step'];edit.location.z+=.2
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'reports/source-edit.blend'),compress=True)
h['export'](HERE/'reports/source-edit.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(HERE/'reports/source.json').write_text(json.dumps({'result':'PASS','source_sha256':before,'metric_units':True,'editable_meshes':len(meshes),'independent_mesh_data':True,'edited_component':'PORCH_Step','edit':'local z +0.2m','source_preserved':True},indent=2)+'\n')
