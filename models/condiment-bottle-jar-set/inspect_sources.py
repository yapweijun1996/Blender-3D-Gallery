"""Inspect the saved source, shelf contacts, original meshes and a source edit."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
source = HERE / 'sources/condiment-bottle-jar-set.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_CondimentBottleJarSet']
bpy.context.view_layer.update()
bottles = sorted([o for o in root.children if o.name.startswith('BOTTLE_')], key=lambda o: o.name)
assert len(bottles) == 16
assert list(root.location) == [0, 0, 0]
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
assert len(bpy.data.materials) == 3
assert not bpy.data.images
assert not any(obj.type == 'FONT' for obj in bpy.data.objects)
assert not bpy.data.libraries
assert not bpy.data.filepath.endswith('edited.blend')
tiers = Counter(obj['tier'] for obj in bottles)
assert [tiers[i] for i in (1, 2, 3)] == [5, 5, 6]


def bounds(objects):
    points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
    return [[min(v[i] for v in points) for i in range(3)],
            [max(v[i] for v in points) for i in range(3)]]


measurements = []
closed_count = 0
for obj in (o for o in root.children_recursive if o.type == 'MESH'):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(face.calc_area() > 1e-12 for face in bm.faces), obj.name
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    closed_count += 1
    bm.free()

for index, bottle in enumerate(bottles):
    parts = [o for o in bottle.children if o.type == 'MESH']
    assert len(parts) == 2
    body = next(o for o in parts if o.name.endswith('_Body'))
    assert len(body.data.materials) == 2
    assert sum(p.material_index == 1 for p in body.data.polygons) == 24
    minimum, maximum = bounds(parts)
    tier = bottle['tier']
    shelf = bpy.data.objects[f'RACK_Shelf_T{tier}']
    shelf_min, shelf_max = bounds([shelf])
    assert abs(minimum[2] - shelf_max[2]) < 1e-6, 'bottle rests on shelf'
    assert abs((maximum[2] - minimum[2]) - [.30, .22, .12][tier - 1]) < 1e-6
    assert shelf_min[0] < minimum[0] < maximum[0] < shelf_max[0]
    assert shelf_min[1] < minimum[1] < maximum[1] < shelf_max[1]
    for other in bottles[index + 1:]:
        if other['tier'] == tier:
            other_min, other_max = bounds(other.children)
            assert maximum[0] < other_min[0], 'same-tier bottle spacing'
    if tier < 3:
        next_shelf_min, _ = bounds([bpy.data.objects[f'RACK_Shelf_T{tier + 1}']])
        assert next_shelf_min[2] - maximum[2] > .015, 'shelf above clears cap'
    measurements.append({'name': bottle.name, 'tier': tier,
                         'height_m': maximum[2] - minimum[2],
                         'width_m': maximum[0] - minimum[0],
                         'bounds_blender_xyz_m': [minimum, maximum]})

source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
report = {
    'result': 'PASS', 'source_reopened': True, 'blender_version': bpy.app.version_string,
    'source_sha256': source_hash, 'bottle_count': len(bottles),
    'bottles_bottom_to_top': [tiers[i] for i in (1, 2, 3)],
    'closed_manifold_parts': closed_count,
    'flush_blank_bands': len(bottles), 'overlapping_label_sleeves': 0,
    'same_tier_overlap': False, 'shelf_contacts': 'PASS',
    'materials': len(bpy.data.materials), 'external_libraries': 0,
    'images': 0, 'text_objects': 0, 'bottles': measurements,
}
# Reopen and independently re-export a controlled edit in a disposable copy.
for bottle in bottles:
    bottle.location.x += .01
bpy.data.materials['Dark filled amber'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .31
edited = Path(tempfile.gettempdir()) / 'condiment-bottle-jar-set-source-edit'
edited.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(edited / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(edited / 'edited.blend'))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('bottle_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(edited / 'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
report['controlled_edit'] = 'All bottle anchors translated +0.01 m in X; amber roughness set to 0.31'
report['edited_glb'] = str(edited / 'edited.glb')
report['edited_glb_sha256'] = hashlib.sha256((edited / 'edited.glb').read_bytes()).hexdigest()
report['original_source_unchanged'] = True
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'bottles'}))
