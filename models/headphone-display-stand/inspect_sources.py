"""Inspect editable source; exercise an edit in a separate saved copy."""
from pathlib import Path
import bpy
import bmesh
import json
import hashlib
import importlib.util
import os

p = Path(__file__).resolve().parent
slug = p.name
source = p / 'sources' / (slug + '.blend')
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_HeadphoneDisplayStand']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
headphones = [o for o in root.children if o.name.startswith('HEADPHONE_')]
assert len(headphones) == 6
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, (o.name, bm.calc_volume())
    bm.free()
assert len({m.name for o in meshes for m in o.data.materials}) == 3
assert sum(o.name.endswith('_CurvedJ') for o in meshes) == 6
assert 'HEADER_BlankFront' in bpy.data.objects and 'PRICE_BlankCard' in bpy.data.objects
assert not any(o.type == 'FONT' for o in root.children_recursive)
target = bpy.data.objects['HEADER_BlankFront']
for vertex in target.data.vertices:
    vertex.co.x *= .92
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
out = Path(os.environ.get('HEADPHONE_EDIT_DIR', '/tmp/headphone-display-stand-source-edit'))
out.mkdir(exist_ok=True, parents=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / (slug + '-edited.blend')), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / (slug + '-edited.blend')))
spec = importlib.util.spec_from_file_location('asset_generator', p / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(out / 'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = {'result': 'PASS', 'source_reopened': 'PASS', 'editable_mesh_parts': len(meshes),
          'closed_manifold_positive_volume_meshes': len(meshes), 'headphones': len(headphones),
          'curved_hooks': 6, 'source_materials': 3, 'text_objects': 0, 'units': 'metres',
          'blender_version': bpy.app.version_string, 'source_sha256': before,
          'edited_mesh': 'HEADER_BlankFront', 'edit': 'Header local X scaled by 0.92; porcelain roughness changed to 0.77',
          'original_source_unchanged': True,
          'edited_glb_sha256': hashlib.sha256((out / 'edited.glb').read_bytes()).hexdigest()}
(p / 'reports' / 'sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
