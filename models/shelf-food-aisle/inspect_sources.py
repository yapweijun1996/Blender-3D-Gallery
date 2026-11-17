"""Reopen, measure and edit a disposable source copy; preserve original files."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy
import bmesh

HERE = Path(__file__).resolve().parent


def bounds(objects):
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    return [[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]


def main():
    source = HERE / 'sources/shelf-food-aisle.blend'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects['ASSET_ShelfFoodAisle']
    bpy.context.view_layer.update()
    assert tuple(root.location) == (0, 0, 0)
    assert bpy.context.scene.unit_settings.system == 'METRIC'
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert not bpy.data.libraries
    assert not any(obj.type == 'FONT' for obj in bpy.data.objects)
    assert not [image for image in bpy.data.images if image.type != 'RENDER_RESULT']
    parts = [obj for obj in root.children_recursive if obj.type == 'MESH']
    materials = {mat.name for obj in parts for mat in obj.data.materials}
    assert len(materials) == 3
    for obj in parts:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        assert all(face.calc_area() > 1e-12 for face in bm.faces), obj.name
        assert all(edge.is_manifold for edge in bm.edges), obj.name
        bm.free()
    items = sorted([obj for obj in root.children if obj.name.startswith('ITEM_')], key=lambda o: o.name)
    assert len(items) == 70
    counts = {kind: sum(obj['kind'] == kind for obj in items) for kind in ['box', 'can', 'bag']}
    assert counts == {'box': 30, 'can': 20, 'bag': 20}
    shelves = [obj for obj in parts if obj.name.startswith('SHELF_')]
    assert len(shelves) == 10
    assert len([obj for obj in parts if obj.name.startswith('PRICE_Blank_')]) == 10
    assert len([obj for obj in parts if obj.name.startswith('ENDSIGN_Blank_')]) == 2
    measurements, gaps, clearances = [], [], []
    for item in items:
        minimum, maximum = bounds([obj for obj in item.children if obj.type == 'MESH'])
        shelf = bpy.data.objects[f'SHELF_S{item["side"]}_T{item["tier"]}']
        shelf_min, shelf_max = bounds([shelf])
        assert abs(minimum[2] - shelf_max[2]) < 1e-6, item.name
        for axis in (0, 1):
            assert minimum[axis] > shelf_min[axis] + .005, item.name
            assert maximum[axis] < shelf_max[axis] - .005, item.name
        if item['tier'] < 5:
            ceiling = bounds([bpy.data.objects[f'SHELF_S{item["side"]}_T{item["tier"] + 1}']])[0][2]
            clearance = ceiling - maximum[2]
            assert clearance > .020, item.name
            clearances.append(clearance)
        measurements.append({'name': item.name, 'kind': item['kind'],
                             'tier': item['tier'], 'side': item['side'],
                             'bounds_blender_xyz_m': [minimum, maximum],
                             'contact_gap_m': minimum[2] - shelf_max[2]})
    for side in (-1, 1):
        for tier in range(1, 6):
            row = sorted([m for m in measurements if m['side'] == side and m['tier'] == tier],
                         key=lambda m: m['bounds_blender_xyz_m'][0][0])
            assert len(row) == 7
            for a, b in zip(row, row[1:]):
                gap = b['bounds_blender_xyz_m'][0][0] - a['bounds_blender_xyz_m'][1][0]
                assert gap > .025
                gaps.append(gap)
    minimum, maximum = bounds(parts)
    report = {'result': 'PASS', 'source_reopened': True, 'blender_version': bpy.app.version_string,
              'source_sha256': source_hash, 'item_count': len(items), 'item_counts': counts,
              'levels_per_side': len(shelves) // 2, 'shelf_decks': len(shelves),
              'blank_price_rails': 10, 'blank_end_signs': 2,
              'closed_manifold_parts': len(parts), 'asset_materials': len(materials),
              'external_libraries': 0, 'images': 0, 'text_objects': 0,
              'bounds_blender_xyz_m': [minimum, maximum],
              'minimum_item_gap_m': min(gaps), 'minimum_overhead_clearance_m': min(clearances),
              'items': measurements}
    first_box = next(obj for obj in items if obj['kind'] == 'box')
    first_box.location.x += .005
    edited = Path(tempfile.gettempdir()) / 'shelf-food-aisle-source-edit'
    edited.mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(edited / 'edited.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(edited / 'edited.blend'))
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('shelf_generator', HERE / 'generate.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.export(edited / 'edited.glb')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    report.update({'controlled_edit': 'First carton anchor translated +0.005 m in X',
                   'edited_glb': str(edited / 'edited.glb'),
                   'edited_glb_sha256': hashlib.sha256((edited / 'edited.glb').read_bytes()).hexdigest(),
                   'original_source_unchanged': True})
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'items'}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
