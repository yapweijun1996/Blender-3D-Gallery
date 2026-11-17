"""Adapted template gate: saved source, dimensions, topology, counts and real edit proof."""
from pathlib import Path
import bpy
import bmesh
import hashlib
import importlib.util
import json
import tempfile
from mathutils import Vector

HERE = Path(__file__).resolve().parent
source = HERE / 'sources/fashion-clothing-rack.blend'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
before = sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_FashionClothingRack']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [obj for obj in root.children_recursive if obj.type == 'MESH']
materials = {mat.name for obj in meshes for mat in obj.data.materials}
assert materials == {'Cotton', 'MatteSurface', 'BrushedMetal'}
assert not any(obj.type == 'FONT' for obj in root.children_recursive)
assert not any(image.source == 'FILE' for image in bpy.data.images)
for obj in meshes:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert bm.calc_volume() > 0, (obj.name, bm.calc_volume())
    assert all(face.calc_area() > 1e-12 for face in bm.faces), obj.name
    bm.free()
names = [obj.name for obj in root.children_recursive]
garments = [obj for obj in root.children_recursive if 'garment_type' in obj]
counts = {
    'hanging_garments': len(garments),
    'shirts': sum(obj['garment_type'] == 'Shirt' for obj in garments),
    'jackets': sum(obj['garment_type'] == 'Jacket' for obj in garments),
    'dresses': sum(obj['garment_type'] == 'Dress' for obj in garments),
    'hangers': sum(name.startswith('HANGER_') and bpy.data.objects[name].type == 'EMPTY' for name in names),
    'folded_stacks': sum(name.startswith('STACK_') for name in names),
    'folded_garments': sum(name.startswith('FOLDED_') and bpy.data.objects[name].type == 'EMPTY' for name in names),
    'source_mesh_parts': len(meshes), 'source_materials': len(materials), 'source_text_objects': 0,
}
assert counts['hanging_garments'] == counts['hangers'] == 10
assert (counts['shirts'], counts['jackets'], counts['dresses']) == (7, 2, 1)
assert counts['folded_stacks'] == 3 and counts['folded_garments'] == 11


def bounds(group):
    objects = ([group] if group.type == 'MESH' else []) + list(group.children_recursive)
    points = [obj.matrix_world @ vertex.co for obj in objects if obj.type == 'MESH' for vertex in obj.data.vertices]
    minimum = [min(p[i] for p in points) for i in range(3)]
    maximum = [max(p[i] for p in points) for i in range(3)]
    return {'axis_order': 'Blender X,Y,Z (width,depth,height)', 'min': minimum, 'max': maximum,
            'size': [b - a for a, b in zip(minimum, maximum)]}


bpy.context.view_layer.update()
measured = {name: bounds(bpy.data.objects[name]) for name in ('RACK_Round', 'TABLE_Fixture', 'TABLE_FoldedDisplay')}
for actual, expected in zip(measured['TABLE_Fixture']['size'], (1.2, .6, .8)):
    assert abs(actual - expected) < 1e-5
assert 1.0 < measured['RACK_Round']['size'][0] < 1.15
assert abs(measured['RACK_Round']['size'][2] - 1.6) < 1e-5
# A real garment must be present under every hanger group; a hanger-only rack fails.
for garment in garments:
    assert any(obj.type == 'MESH' and obj.name.startswith('CLOTH_') for obj in garment.children)
    assert min(bounds(garment)['min'][2], 2) > .35

spec = importlib.util.spec_from_file_location('asset_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
out = Path(tempfile.mkdtemp(prefix='fashion-clothing-rack-source-edit-'))
generator.export(out / 'reopened.glb')
assert sha(out / 'reopened.glb') == sha(HERE / 'exports/optimized.glb')
target = bpy.data.objects['TABLE_Top']
for vertex in target.data.vertices:
    vertex.co.x *= .92
bpy.data.materials['BrushedMetal'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / 'edited.blend'))
generator.export(out / 'edited.glb')
assert sha(source) == before
assert sha(out / 'edited.glb') != sha(HERE / 'exports/optimized.glb')
report = {'result': 'PASS', 'source_reopened': True, 'closed_manifold_mesh_parts': len(meshes),
          'blender_version': bpy.app.version_string, 'counts': counts, 'measured_subassemblies': measured,
          'source_sha256': before, 'reopened_export_identical': True, 'original_source_unchanged': True,
          'edit': 'Tabletop local X scaled by 0.92 and metal roughness set to 0.77; saved, reopened, re-exported',
          'edited_glb': str(out / 'edited.glb'), 'edited_glb_sha256': sha(out / 'edited.glb')}
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
metadata_path = HERE / 'metadata/fashion-clothing-rack.json'
metadata = json.loads(metadata_path.read_text())
metadata['blender_version'] = bpy.app.version_string
metadata['content'] = counts
metadata['measured_subassemblies'] = measured
metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(report))
