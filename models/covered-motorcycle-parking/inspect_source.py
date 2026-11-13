from pathlib import Path
import bpy,json,runpy,hashlib,math
HERE=Path(__file__).resolve().parent;source=HERE/'sources/covered-motorcycle-parking.blend';before=hashlib.sha256(source.read_bytes()).hexdigest();h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects['ASSET_CoveredMotorcycleParking'];meshes=[o for o in root.children_recursive if o.type=='MESH']
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)>=5 and len({o.data.as_pointer() for o in meshes})==len(meshes)
assert all(all(math.isfinite(c) for v in o.data.vertices for c in v.co) for o in meshes)
report={'result':'PASS','blender':bpy.app.version_string,'source_sha256':before,'editable_meshes':len(meshes),'independent_mesh_data':True,'metric_units':True,'edit':"bpy.data.objects['ROOF_Cantilever'].location.z=.15",'runtime_interactivity':'NOT IMPLEMENTED'}
bpy.data.objects['ROOF_Cantilever'].location.z=.15
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'reports/source-edit.blend'),compress=True);h['export'](root,HERE/'reports/source-edit.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(HERE/'reports/source.json').write_text(json.dumps(report,indent=2)+'\n')
