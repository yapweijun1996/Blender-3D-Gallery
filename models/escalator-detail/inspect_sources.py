"""Reopen, inspect, edit a disposable copy and export it without rebuilding."""
from pathlib import Path
import bpy
import bmesh
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
source = HERE/'sources/escalator-detail.blend'
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_EscalatorDetail']
assert tuple(root.location) == (0,0,0)
assert bpy.context.scene.unit_settings.scale_length == 1
assert bpy.context.scene.unit_settings.system == 'METRIC'
meshes = [o for o in root.children_recursive if o.type == 'MESH']
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()
assert len(bpy.data.objects['STEPS_FutureMotion'].children) == 22
assert len({m.name for o in meshes for m in o.data.materials}) == 3
assert all(o.type not in {'FONT','ARMATURE'} for o in root.children_recursive)
spec = importlib.util.spec_from_file_location('asset_generator',HERE/'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(HERE/'reports/source-reexport.glb')
reexport_hash = hashlib.sha256((HERE/'reports/source-reexport.glb').read_bytes()).hexdigest()
assert reexport_hash == hashlib.sha256((HERE/'exports/optimized.glb').read_bytes()).hexdigest()
target = bpy.data.objects['SIGN_BlankPanel']
for vertex in target.data.vertices:
    vertex.co.z *= .8
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
edited = HERE/'reports/source-edit.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(edited),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(edited))
assert bpy.data.objects['SIGN_BlankPanel'].data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value > .769
generator.export(HERE/'reports/source-edit.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = {'result':'PASS','source_reopened':True,'blender_version':bpy.app.version_string,
          'source_mesh_parts':len(meshes),'manifold_source_meshes':len(meshes),
          'shared_materials':3,'independent_steps':22,'no_text_or_rig':True,
          'source_sha256':before,'unchanged_source_reexport_sha256':reexport_hash,
          'saved_edit':'Blank sign panel local height reduced by 20%; steel roughness set to 0.77',
          'edited_glb_sha256':hashlib.sha256((HERE/'reports/source-edit.glb').read_bytes()).hexdigest(),
          'original_source_unchanged':True}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
