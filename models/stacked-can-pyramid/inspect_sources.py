"""Reopen the saved source and inspect instancing, topology and stack layout."""
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
source = HERE / 'sources/stacked-can-pyramid.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_StackedCanPyramid']
cans = sorted((obj for obj in root.children if obj.name.startswith('CAN_')), key=lambda obj: obj.name)
assert len(cans) == 91
assert len({obj.data.as_pointer() for obj in cans}) == 1
assert list(root.location) == [0, 0, 0]
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
assert len(bpy.data.materials) == 2
assert not bpy.data.images
tiers = Counter(obj['tier'] for obj in cans)
assert [tiers[i] for i in range(1, 7)] == [36, 25, 16, 9, 4, 1]
collider = bpy.data.objects['collider_box']
assert collider.hide_render and collider.hide_get()
assert not collider.data.materials
for obj in [cans[0], bpy.data.objects['BASE_ChamferedPlinth'], collider]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges)
    assert all(face.calc_area() > 1e-12 for face in bm.faces)
    bm.free()
for index, obj in enumerate(cans):
    assert abs(obj.location.z - (.10 + (obj['tier'] - 1) * (1.3 / 6))) < 1e-6
    for other in cans[index + 1:]:
        if obj['tier'] == other['tier']:
            assert (obj.location - other.location).length >= .15 - 1e-6
    if obj['tier'] > 1:
        supports = [other for other in cans if other['tier'] == obj['tier'] - 1
                    and Vector((obj.location.x - other.location.x,
                                obj.location.y - other.location.y)).length < .107]
        assert len(supports) == 4, 'each upper can bridges four lower cans'
bpy.context.view_layer.update()
can = cans[0]
coords = [can.matrix_world @ vertex.co for vertex in can.data.vertices]
can_dimensions = [max(v[i] for v in coords) - min(v[i] for v in coords) for i in range(3)]
report = {
    'result': 'PASS', 'source_reopened': True, 'blender_version': bpy.app.version_string,
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'can_instances': len(cans), 'unique_can_meshes': 1,
    'radial_segments_measured': len([v for v in can.data.vertices if abs(v.co.z) < 1e-7]),
    'can_dimensions_blender_xyz_m': can_dimensions,
    'tiers_bottom_to_top': [tiers[i] for i in range(1, 7)],
    'closed_manifold_prototypes': 3, 'same_tier_overlap': False,
    'collider_hidden_no_material': True, 'upper_can_supports': 4, 'materials': len(bpy.data.materials),
}
original_hash = report['source_sha256']
for vertex in can.data.vertices:
    vertex.co.x *= .9
can.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .7
edited = Path(tempfile.gettempdir()) / 'stacked-can-pyramid-source-edit'
edited.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(edited / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(edited / 'edited.blend'))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('can_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(edited / 'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
report['controlled_edit'] = 'Shared can vertices X scaled by 0.9; tinplate roughness set to 0.7'
report['edited_glb'] = str(edited / 'edited.glb')
report['edited_glb_sha256'] = hashlib.sha256((edited / 'edited.glb').read_bytes()).hexdigest()
report['original_source_unchanged'] = True
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
