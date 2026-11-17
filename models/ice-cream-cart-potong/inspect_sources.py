"""Reopen the native source; edit a saved temporary copy and export it for independent QA."""
import bpy
import bmesh
import importlib.util
import json
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('potong_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / 'ice-cream-cart-potong.blend'))
assert bpy.app.version[:3] == (5, 2, 3)
root = bpy.data.objects[generator.ROOT]
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.scale_length == 1
collider = bpy.data.objects['collider_box']
assert collider.type == 'MESH' and len(collider.data.materials) == 0
assert collider.hide_render and collider.hide_get()
objects = [o for o in root.children_recursive if o.type == 'MESH' and o != collider]
assert len([o for o in objects if o.name.startswith('TUB_') and o.name.endswith('_FrozenSlab')]) == 3
assert len([o for o in objects if o.name.startswith('WHEEL_MainTyre_')]) == 2
assert len([o for o in objects if o.name == 'WHEEL_RearCaster']) == 1
assert len([o for o in objects if o.name.startswith('BAR_')]) == 3
assert len([o for o in objects if '_Filling' in o.name]) == 2
assert all(o.type != 'FONT' for o in root.children_recursive)
assert len({m for o in objects for m in o.data.materials}) == 2
assert len(bpy.data.images) == 0
assert not bpy.data.libraries
assert not bpy.data.actions
for o in objects:
    assert len(o.data.vertices) > 0 and all(all(__import__('math').isfinite(v) for v in p.co) for p in o.data.vertices)
depsgraph = bpy.context.evaluated_depsgraph_get()
def bounds(o):
    evaluated = o.evaluated_get(depsgraph)
    points = [evaluated.matrix_world @ Vector(p) for p in evaluated.bound_box]
    return [min(p.z for p in points), max(p.z for p in points)]

tub_geometry, tray_contacts = [], []
liner_top = bounds(bpy.data.objects['TRAY_CreamInsert'])[1]
for i in range(1, 4):
    shell = bpy.data.objects['TUB_%02d_OpenContainer' % i]
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    assert all(e.is_manifold for e in bm.edges), 'closed container shell'
    bm.free()
    # A ray through the opening must reach the interior floor, not a top cap.
    hit, location, *_ = shell.ray_cast(Vector(([-.325, 0, .325][i - 1], -.128, 1.3)), Vector((0, 0, -1)))
    assert hit and abs(location.z - 1.009) < 1e-6, 'real hollow container'
    recess = bounds(shell)[1] - bounds(bpy.data.objects['TUB_%02d_FrozenSlab' % i])[1]
    assert abs(recess - .04) < 1e-6
    tub_geometry.append({'container': shell.name, 'interior_floor': location.z, 'food_recess_metres': recess})
    for name in ['BAR_%02d_RoundedStickIce' % i, 'STICK_%02d_PlainWoodGrip' % i]:
        gap = bounds(bpy.data.objects[name])[0] - liner_top
        assert abs(gap) < 1e-6, 'ice and wood rest on the tray liner'
        tray_contacts.append({'part': name, 'gap_metres': gap})
report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
          'source_mesh_objects': len(objects), 'flavour_tubs': 3, 'large_wheels': 2,
          'rear_casters': 1, 'plain_bars': 3, 'wafer_sandwiches': 2, 'materials': 2,
          'external_libraries': 0, 'images': 0, 'font_objects': 0,
          'collider_hidden': True, 'collider_materials': 0,
          'tub_geometry': tub_geometry, 'tray_contacts': tray_contacts,
          'source_parts': [o.name for o in objects]}
(HERE / 'reports' / 'sources.json').write_text(json.dumps(report, indent=2) + '\n')
tubs = bpy.data.objects['FLAVOUR_ThreeTubs']
tubs.location.z += .02
bpy.context.view_layer.update()
temp = '/tmp/ice-cream-cart-potong-source-edit.blend'
bpy.ops.wm.save_as_mainfile(filepath=temp, compress=True)
bpy.ops.wm.open_mainfile(filepath=temp)
generator.export(Path('/tmp/ice-cream-cart-potong-source-edit.glb'))
print('PASS saved source inspection and temporary edit export')
