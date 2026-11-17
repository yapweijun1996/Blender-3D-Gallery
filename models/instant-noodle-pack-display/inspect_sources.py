"""Reopen and measure source geometry, hanging contacts, spacing and editability."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
import bpy
import bmesh

HERE = Path(__file__).resolve().parent
source = HERE / 'sources/instant-noodle-pack-display.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_InstantNoodlePackDisplay']
bpy.context.view_layer.update()
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
assert not bpy.data.libraries
assert not any(o.type == 'FONT' for o in bpy.data.objects)
assert not [image for image in bpy.data.images if image.type != 'RENDER_RESULT']
parts = [o for o in root.children_recursive if o.type == 'MESH']
materials = {m.name for o in parts for m in o.data.materials}
assert len(materials) == 3
for obj in parts:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(face.calc_area() > 1e-12 for face in bm.faces), obj.name
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    bm.free()


def bounds(objects):
    points = [obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices]
    return [[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]


packs = sorted([o for o in root.children if o.name.startswith('PACK_')], key=lambda o: o.name)
hooks = sorted([o for o in parts if o.name.startswith('HOOK_')], key=lambda o: o.name)
assert len(packs) == len(hooks) == 20
measurements = []
clearances = []
for pack in packs:
    assert len([o for o in pack.children if o.name.startswith('BAG_PuffedBody')]) == 1
    assert len([o for o in pack.children if o.name.startswith('SEAL_TopWithHangHole')]) == 1
    row, col = pack['row'], pack['column']
    hook = bpy.data.objects[f'HOOK_R{row}C{col}']
    seal = next(o for o in pack.children if o.name.startswith('SEAL_TopWithHangHole'))
    hole_center = seal.matrix_world.translation
    # The first ring is straight along the depth axis and passes through the hole.
    ring = [hook.matrix_world @ v.co for v in list(hook.data.vertices)[:8]]
    hook_x = sum(p.x for p in ring) / len(ring)
    hook_z = sum(p.z for p in ring) / len(ring)
    radius = max(p.z for p in ring) - hook_z
    assert abs(hook_x - hole_center.x) < 1e-6
    assert abs(hole_center.y - pack.location.y) < 1e-6
    assert -.070 < hole_center.y < .12
    offset = hook_z - hole_center.z
    assert offset >= 0
    # Tube cross-section must remain inside every edge of the octagonal hang hole.
    poly = [(.0042 * math.cos(i * math.pi / 4), .0042 * math.sin(i * math.pi / 4))
            for i in range(8)]
    for x, z in [(p.x - hole_center.x, p.z - hole_center.z) for p in ring]:
        for i, (ax, az) in enumerate(poly):
            bx, bz = poly[(i + 1) % 8]
            assert (bx - ax) * (z - az) - (bz - az) * (x - ax) > -1e-8
    clearances.append(.0042 - offset - radius)
    minimum, maximum = bounds(pack.children)
    if col < 5:
        neighbor = bpy.data.objects[f'PACK_R{row}C{col + 1}']
        neighbor_min, _ = bounds(neighbor.children)
        assert neighbor_min[0] - maximum[0] > .010
    price = bpy.data.objects[f'PRICE_Rail_R{row}']
    _, price_max = bounds([price])
    assert minimum[2] - price_max[2] > .015
    measurements.append({'name': pack.name, 'row': row, 'column': col,
                         'bounds_blender_xyz_m': [minimum, maximum],
                         'size_blender_xyz_m': [maximum[i] - minimum[i] for i in range(3)]})
assert all(abs(value) < 1e-6 for value in clearances), 'seal rests on the hook top'

source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
report = {'result': 'PASS', 'source_reopened': True, 'blender_version': bpy.app.version_string,
          'source_sha256': source_hash, 'pack_count': len(packs), 'hook_count': len(hooks),
          'rows_bottom_to_top': [sum(o['row'] == row for o in packs) for row in range(1, 5)],
          'closed_manifold_parts': len(parts), 'asset_materials': len(materials),
          'external_libraries': 0, 'images': 0, 'text_objects': 0,
          'hang_hole_top_contact_gap_m': clearances,
          'pack_spacing_and_price_rail_clearance': 'PASS', 'packs': measurements}
# Save and reopen a disposable edit, then exercise the source-preserving export path.
packs[0].location.x += .005
edited = Path(tempfile.gettempdir()) / 'instant-noodle-pack-display-source-edit'
edited.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(edited / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(edited / 'edited.blend'))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('rack_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(edited / 'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
report.update({'controlled_edit': 'First pack anchor translated +0.005 m in X',
               'edited_glb': str(edited / 'edited.glb'),
               'edited_glb_sha256': hashlib.sha256((edited / 'edited.glb').read_bytes()).hexdigest(),
               'original_source_unchanged': True})
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'packs'}))
