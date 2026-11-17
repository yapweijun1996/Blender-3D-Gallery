"""Reopen, inspect, edit a temporary copy, and independently re-export it."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import traceback

import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def main():
    spec = json.loads((HERE/'backlog.json').read_text())
    source = HERE/'sources'/(spec['slug']+'.blend')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    assert scene.unit_settings.system == 'METRIC' and scene.unit_settings.scale_length == 1
    root = bpy.data.objects[spec['root']]
    assert tuple(root.location) == (0, 0, 0)
    assert len([o for o in root.children if o.name.startswith('DIYA_')]) == 12
    assert len([o for o in root.children if o.name.startswith('GARLAND_')]) == 2
    objects = [o for o in root.children_recursive if o.type == 'MESH']
    assert len({m for o in objects for m in o.data.materials}) == 3
    assert not any(o.modifiers for o in objects)
    for o in objects:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        assert all(e.is_manifold for e in bm.edges), o.name
        assert bm.calc_volume() > 0, o.name
        assert all(f.calc_area() > 1e-12 for f in bm.faces), o.name
        bm.free()
    floor = bpy.data.objects['RANGOLI_OriginalTwelvePetalMosaic']
    assert abs(floor.dimensions.x-2.4) < 1e-6 and abs(floor.dimensions.y-2.4) < 1e-6
    assert abs(floor.dimensions.z-.008) < 1e-6
    floor_dimensions = list(floor.dimensions)
    square = bpy.data.objects['FLOOR_TwoMetreSquare']
    assert all(abs(a-b) < 1e-6 for a, b in zip(square.dimensions, (2, 2, .012)))
    square_dimensions = list(square.dimensions)
    assert abs(floor.location.z-.012) < 1e-6
    assert len([o for o in objects if o.name.startswith('MARIGOLD_')]) == 42
    for j in range(2):
        foot = bpy.data.objects['FRAME_Foot_%02d' % j]
        post = bpy.data.objects['FRAME_Post_%02d' % j]
        assert abs(min(v.co.z for v in foot.data.vertices)-.012) < 1e-6
        assert abs(min(v.co.z for v in post.data.vertices)-.032) < 1e-6
        assert abs(max(v.co.z for v in post.data.vertices)-1.96) < 1e-6
    for j in range(12):
        flame = bpy.data.objects['FLAME_Teardrop_%02d' % (j+1)]
        assert flame.data.materials[0].name == 'RiceIvory'
        assert flame.dimensions.x >= .047 and flame.dimensions.z >= .089
    for hanger in [o for o in objects if o.name.startswith('HANGER_')]:
        # The bar's 17 mm radius fits through the loop's 27 mm inner radius
        # with a 5 mm centre offset; the string reaches the loop's lower rim.
        assert abs(hanger.location.z-1.955) < 1e-6
    bpy.context.view_layer.update()
    groups = {}
    for group in root.children:
        if not group.name.startswith(('DIYA_', 'GARLAND_')):
            continue
        points = [o.matrix_world @ Vector(p) for o in group.children_recursive if o.type == 'MESH' for p in o.bound_box]
        groups[group.name] = {'min': [min(p[i] for p in points) for i in range(3)],
                              'max': [max(p[i] for p in points) for i in range(3)]}
    module_spec = importlib.util.spec_from_file_location('asset_generator', HERE/'generate.py')
    generator = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(generator)
    generator.MATERIALS = [bpy.data.materials[n] for n in ['Terracotta', 'MarigoldGold', 'RiceIvory']]
    original = HERE/'exports'/'optimized.glb'
    with tempfile.TemporaryDirectory(prefix=spec['slug']+'-source-') as temp:
        copy = Path(temp)
        generator.export(copy/'reopened.glb')
        assert (copy/'reopened.glb').read_bytes() == original.read_bytes(), 'saved-source export differs'
        target = bpy.data.objects['CLAY_Bowl_01']
        before_width = max(v.co.x for v in target.data.vertices)-min(v.co.x for v in target.data.vertices)
        for vertex in target.data.vertices:
            vertex.co.x *= .92
        generator.MATERIALS[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .83
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(copy/'edited.blend'), compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(copy/'edited.blend'))
        target = bpy.data.objects['CLAY_Bowl_01']
        edited_width = max(v.co.x for v in target.data.vertices)-min(v.co.x for v in target.data.vertices)
        assert abs(edited_width-before_width*.92) < 1e-7
        assert bpy.data.materials['Terracotta'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value > .829
        generator.MATERIALS = [bpy.data.materials[n] for n in ['Terracotta', 'MarigoldGold', 'RiceIvory']]
        generator.export(copy/'edited.glb')
        assert (copy/'edited.glb').read_bytes() != original.read_bytes()
        # Retain only the small edited export as inspectable editability evidence.
        (HERE/'reports'/'edited.glb').write_bytes((copy/'edited.glb').read_bytes())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    report = {'result': 'PASS', 'blender_version': bpy.app.version_string, 'source_sha256': before,
              'source_reopened': True, 'closed_positive_volume_meshes': len(objects),
              'units': 'metres', 'origin': [0, 0, 0], 'materials': 3,
              'rangoli_dimensions_blender_xyz': floor_dimensions,
              'included_square_floor_dimensions_blender_xyz': square_dimensions,
              'support': 'Two posts with feet on the square floor, shared crossbar and four interlocking hanger loops',
              'groups_blender_xyz': groups,
              'saved_source_export_byte_identical': True,
              'copy_edit': 'CLAY_Bowl_01 local X scaled by .92; clay roughness changed to .83; saved, reopened and exported',
              'canonical_source_unchanged': True}
    (HERE/'reports'/'source.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
