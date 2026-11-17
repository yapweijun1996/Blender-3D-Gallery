"""Inspect saved source and test a saved-edit export without changing delivery."""
from pathlib import Path
import importlib.util
import json
import sys
import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/glass-storefront-module.blend'))
roots = [bpy.data.objects['ASSET_GlassStorefrontModule'], bpy.data.objects['ASSET_GlassStorefrontModule_Open']]
assert bpy.context.scene.unit_settings.scale_length == 1
parts = {}
for root in roots:
    assert tuple(root.location) == (0, 0, 0)
    children = [o for o in root.children_recursive if o.type == 'MESH']
    assert all(o.data.validate() is False for o in children)
    assert all(len(o.data.materials) == 1 for o in children)
    parts[root.name] = [o.name for o in children]
for name in ['collider_box', 'collider_box_Open']:
    o = bpy.data.objects[name]
    assert o.hide_render and o.hide_get() and len(o.data.materials) == 0


def bounds(name):
    o = bpy.data.objects[name]
    points = [o.matrix_world @ Vector(p) for p in o.bound_box]
    return [[min(p[axis] for p in points), max(p[axis] for p in points)] for axis in range(3)]


def connected(a, b):
    aa, bb = bounds(a), bounds(b)
    assert all(min(aa[i][1], bb[i][1]) >= max(aa[i][0], bb[i][0]) - 1e-6 for i in range(3)), (a, b)


doors = {}
for side in ['Left', 'Right']:
    leaf = 'DOOR_FramelessLeaf_' + side
    bb = bounds(leaf)
    assert 2.2 < bb[2][1] - bb[2][0] < 2.3
    assert bb[2][0] > 0
    connected('PATCH_' + side + '_Bottom', leaf)
    connected('PATCH_' + side + '_Top', leaf)
    connected('PIVOT_FloorBearing_' + side, 'PIVOT_BottomSpindle_' + side)
    connected('PIVOT_BottomSpindle_' + side, 'PATCH_' + side + '_Bottom')
    connected('PATCH_' + side + '_Top', 'PIVOT_TopSpindle_' + side)
    connected('PIVOT_TopSpindle_' + side, 'PIVOT_TransomReceiver_' + side)
    connected('PIVOT_TransomReceiver_' + side, 'GLASS_OverdoorTransom_Closed')
    assert abs(bounds('PIVOT_FloorBearing_' + side)[2][0]) < 1e-6
    doors[side] = {'width_m': bb[0][1] - bb[0][0], 'height_m': bb[2][1] - bb[2][0],
                   'floor_gap_m': bb[2][0], 'top_gap_m': bounds('GLASS_OverdoorTransom_Closed')[2][0] - bb[2][1],
                   'pivot_connections': 'PASS: overlapping bounds from floor bearing through leaf patches to transom receiver'}
report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
          'unit_scale': 1, 'source_parts': parts, 'external_images': len(bpy.data.images), 'doors': doors}
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
if '--source-edit' in sys.argv:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.data.objects['HEADER_BlankSignBand_Closed'].location.z += .02
    proof = '/tmp/glass-storefront-module-source-edit.blend'
    bpy.ops.wm.save_as_mainfile(filepath=proof, compress=True)
    bpy.ops.wm.open_mainfile(filepath=proof)
    spec = importlib.util.spec_from_file_location('storefront_generator', HERE / 'generate.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.export(Path('/tmp/glass-storefront-module-source-edit.glb'))
print(json.dumps(report))
