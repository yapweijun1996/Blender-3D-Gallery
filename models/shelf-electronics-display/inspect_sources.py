"""Reopen native source, inspect real parts, and edit/re-export a disposable copy."""
from pathlib import Path
import bpy
import bmesh
import hashlib
import importlib.util
import json
import tempfile

HERE = Path(__file__).resolve().parent
source = HERE / 'sources/shelf-electronics-display.blend'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_ShelfElectronicsDisplay']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [obj for obj in root.children_recursive if obj.type == 'MESH']
materials = {mat.name for obj in meshes for mat in obj.data.materials}
assert materials == {'Ceramic', 'Graphite', 'Glass'}
assert not any(obj.type == 'FONT' for obj in root.children_recursive)
assert not any(image.source == 'FILE' for image in bpy.data.images)
for obj in meshes:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert bm.calc_volume() > 0, obj.name
    assert all(face.calc_area() > 1e-12 for face in bm.faces), obj.name
    bm.free()
names = [obj.name for obj in root.children_recursive]
counts = {
    'glass_front_panes': sum(name.startswith('GLASS_') for name in names),
    'shelf_decks': sum(name.startswith('SHELF_') and name.endswith('_Deck') for name in names),
    'boxed_devices': sum(name.startswith('BOX_') and name.endswith('_Carton') for name in names),
    'cable_coils': sum(name.startswith('CABLE_') and name.endswith('_Coil') for name in names),
    'j_hooks': sum(name.startswith('HOOK_') and name.endswith('_J') for name in names),
    'tablets': names.count('TABLET_OnStand'), 'cylindrical_speakers': names.count('SPEAKER_Cylinder'),
    'blank_header_panels': names.count('HEADER_BlankPanel'),
    'source_mesh_parts': len(meshes), 'source_materials': len(materials), 'source_text_objects': 0,
}
assert counts['glass_front_panes'] == 6 and counts['shelf_decks'] == 4
assert counts['boxed_devices'] == 6 and counts['cable_coils'] == counts['j_hooks'] == 3
assert counts['tablets'] == counts['cylindrical_speakers'] == counts['blank_header_panels'] == 1
spec = importlib.util.spec_from_file_location('asset_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
out = Path(tempfile.mkdtemp(prefix='shelf-electronics-display-source-edit-'))
generator.export(out / 'reopened.glb')
assert sha(out / 'reopened.glb') == sha(HERE / 'exports/optimized.glb')
target = bpy.data.objects['TABLET_Shell']
for vertex in target.data.vertices:
    vertex.co.x *= .92
material = bpy.data.materials['Graphite']
material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / 'edited.blend'))
assert abs(bpy.data.materials['Graphite'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value - .77) < 1e-6
generator.export(out / 'edited.glb')
assert sha(source) == before
assert sha(out / 'edited.glb') != sha(HERE / 'exports/optimized.glb')
report = {'result': 'PASS', 'source_reopened': True, 'closed_manifold_mesh_parts': len(meshes),
          'blender_version': bpy.app.version_string, 'counts': counts, 'source_sha256': before,
          'reopened_export_identical': True, 'original_source_unchanged': True,
          'edit': 'Tablet shell local X scaled by 0.92; Graphite roughness set to 0.77; saved, reopened, re-exported',
          'edited_glb': str(out / 'edited.glb'), 'edited_glb_sha256': sha(out / 'edited.glb')}
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
metadata_path = HERE / 'metadata/shelf-electronics-display.json'
if metadata_path.exists():
    metadata = json.loads(metadata_path.read_text())
    metadata['blender_version'] = bpy.app.version_string
    metadata['content'] = counts
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(report))
