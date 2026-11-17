"""Reopen the source, measure actual stock and verify a disposable saved edit."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent


def bounds(objects):
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    return [[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]


def main():
    source = HERE / 'sources/mosquito-patch-pack.blend'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects['ASSET_MosquitoPatchPack']
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
    packs = sorted([obj for obj in root.children if obj.name.startswith('PACK_')], key=lambda o: o.name)
    heroes = [obj for obj in root.children if obj.name == 'HERO_Pack']
    assert len(packs) == 16 and len(heroes) == 1
    measurements, clearances = [], []
    for parent in packs + heroes:
        cards = [o for o in parent.children if o.name.endswith('_BlankCard')]
        windows = [o for o in parent.children if o.name.endswith('_ClearWindow')]
        patches = [o for o in parent.children if '_Patch_' in o.name]
        assert len(cards) == len(windows) == 1 and len(patches) == 6
        card = cards[0]
        local = [[min(v.co[i] for v in card.data.vertices), max(v.co[i] for v in card.data.vertices)] for i in range(3)]
        scale = 1.4 if parent.name.startswith('HERO') else 1
        assert abs(local[0][1] - local[0][0] - .1 * scale) < 1e-6
        assert abs(local[2][1] - local[2][0] - .14 * scale) < 1e-6
        for patch in patches:
            assert len(patch.data.polygons) == 18
            assert abs(patch.dimensions.x - .023 * scale) < 1e-6
        minimum, maximum = bounds([o for o in parent.children if o.type == 'MESH'])
        assert minimum[0] >= -.25 and maximum[0] <= .25
        assert minimum[1] >= -.15 and maximum[1] <= .15
        measurements.append({'name': parent.name, 'tier': parent['tier'], 'patches': len(patches),
                             'card_width_height_m': [local[i][1] - local[i][0] for i in (0, 2)],
                             'bounds_blender_xyz_m': [minimum, maximum]})
    for tier in (1, 2):
        for column in range(1, 5):
            pair = [m for m in measurements if m['name'].startswith(f'PACK_T{tier}_C{column}_')]
            # The tilted parallel cards overlap in AABB depth. Compare planes instead.
            a, b = [bpy.data.objects[m['name']] for m in pair]
            normal = a.matrix_world.to_quaternion() @ Vector((0, -1, 0))
            spacing = abs((b.location - a.location).dot(normal))
            assert spacing > .006
            depths = [(o.matrix_local @ v.co).y for o in a.children for v in o.data.vertices]
            clearances.append(spacing - (max(depths) - min(depths)))
    report = {'result': 'PASS', 'source_reopened': True, 'blender_version': bpy.app.version_string,
              'source_sha256': source_hash, 'regular_pack_count': len(packs), 'hero_pack_count': len(heroes),
              'patch_count': sum(m['patches'] for m in measurements),
              'packs_per_tier': [sum(o['tier'] == t for o in packs) for t in (1, 2)],
              'closed_manifold_parts': len(parts), 'asset_materials': len(materials),
              'external_libraries': 0, 'images': 0, 'text_objects': 0,
              'bounds_blender_xyz_m': bounds(parts),
              'minimum_stock_plane_clearance_m': min(clearances), 'items': measurements}
    # Verify that batching honours edits stored in the native source file.
    packs[0].location.x += .004
    edited = Path(tempfile.gettempdir()) / 'mosquito-patch-pack-source-edit'
    edited.mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(edited / 'edited.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(edited / 'edited.blend'))
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('mosquito_generator', HERE / 'generate.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.export(edited / 'edited.glb')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    report.update({'controlled_edit': 'First regular pack translated +0.004 m in X',
                   'edited_glb': str(edited / 'edited.glb'), 'original_source_unchanged': True})
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'items'}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
