"""Reopen and edit a copy, preserving the delivered source and GLB."""
from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile
import bpy
import bmesh

HERE = Path(__file__).resolve().parent
source = HERE/'sources/atrium-chandelier.blend'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_AtriumChandelier']
meshes = [o for o in root.children_recursive if o.type == 'MESH']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()
assert len([o for o in meshes if o.name.endswith('_Crystal')]) == 24
assert len([o for o in meshes if o.name.endswith('_Housing')]) == 3
assert len([o for o in meshes if o.name.startswith('SUSPENSION_') and not o.name.endswith('_Socket')]) == 9
target = bpy.data.objects['CEILING_Plate']
for vertex in target.data.vertices:
    vertex.co.x *= .92
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
out = Path(tempfile.gettempdir())/'atrium-chandelier-source-edit'
out.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out/'edited.blend'))
spec = importlib.util.spec_from_file_location('generator', HERE/'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(out/'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
report = {'source_reopened':'PASS', 'closed_manifold_source_meshes':len(meshes),
          'blender_version':bpy.app.version_string, 'units':'metres', 'source_sha256':source_hash,
          'editable_light_ring_housings':3, 'editable_crystal_drops':24, 'suspension_rods':9,
          'original_source_unchanged':True, 'edit':'CEILING_Plate local X vertices scaled by 0.92; shared metal roughness to 0.77',
          'edited_glb':str(out/'edited.glb')}
(HERE/'reports/sources.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
