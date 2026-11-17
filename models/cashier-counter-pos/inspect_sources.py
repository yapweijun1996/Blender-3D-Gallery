"""Reopen editable source, audit metric geometry and test a saved source edit."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
source = HERE / 'sources/cashier-counter-pos.blend'
delivery = HERE / 'exports/optimized.glb'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_hash, glb_hash = sha(source), sha(delivery)
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.view_layer.update()
root = bpy.data.objects['ASSET_CashierCounterPOS']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
assert not any(o.type in ['FONT', 'ARMATURE'] or o.animation_data for o in root.children_recursive)
assert not any(i.source == 'FILE' for i in bpy.data.images)
assert len({m.name for o in meshes for m in o.data.materials}) == 3
for o in meshes:
    assert not o.data.validate(verbose=False), o.name
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()


def measure(o):
    points = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    return {'min': lo, 'max': hi, 'dimensions': [hi[i] - lo[i] for i in range(3)]}


def surface(o):
    evaluated = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    vertices = [o.matrix_world @ v.co for v in mesh.vertices]
    faces = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(vertices, faces), vertices


def inside_depth(tree, point):
    closest, normal, _, distance = tree.find_nearest(point)
    assert (point - closest).dot(normal) < 0, 'Attachment point is outside its receiver'
    return distance


# Check evaluated surfaces, including bevels, rather than overlapping bounds.
contact_names = ['CARD_Support', 'CARD_Housing', 'PRINTER_BlankReceipt', 'PRINTER_PaperSlot']
surfaces = {name: surface(bpy.data.objects[name]) for name in contact_names}
support = bpy.data.objects['CARD_Support']
support_tip = support.matrix_world @ Vector((0, 0, max(v.co.z for v in support.data.vertices)))
support_depth = inside_depth(surfaces['CARD_Housing'][0], support_tip)
assert .002 < support_depth < .006, support_depth
paper = bpy.data.objects['PRINTER_BlankReceipt']
paper_root = paper.matrix_world @ Vector((0, min(v.co.y for v in paper.data.vertices), 0))
paper_tip = paper.matrix_world @ Vector((0, max(v.co.y for v in paper.data.vertices), 0))
paper_depth = inside_depth(surfaces['PRINTER_PaperSlot'][0], paper_root)
assert .0007 < paper_depth < .003, paper_depth
paper_direction = (paper_tip - paper_root).normalized()
exit_point, _, _, _ = surfaces['PRINTER_PaperSlot'][0].ray_cast(paper_tip, -paper_direction)
assert exit_point is not None, 'Receipt misses the paper slot'
slot_front = measure(bpy.data.objects['PRINTER_PaperSlot'])['max'][1]
assert abs(exit_point.y - slot_front) < 1e-6, 'Receipt must emerge through the front of the slot'
assert (paper_tip - exit_point).length > .05, 'Receipt must extend visibly beyond the slot'
attachments = {'card_support_tip_inside_housing_m': support_depth,
    'receipt_root_inside_slot_m': paper_depth, 'receipt_exit_blender_xyz_m': list(exit_point),
    'exposed_receipt_length_m': (paper_tip - exit_point).length}


top = measure(bpy.data.objects['COUNTER_Countertop'])
assert abs(top['dimensions'][0] - 1.4) < 1e-6
assert abs(top['dimensions'][1] - .7) < 1e-6
assert abs(top['max'][2] - .95) < 1e-6
screen = bpy.data.objects['POS_BlankDarkTouchscreen']
reader = bpy.data.objects['CARD_BlankScreen']
assert (screen.matrix_world.to_3x3() @ Vector((0, 1, 0))).y > .9
assert (reader.matrix_world.to_3x3() @ Vector((0, -1, 0))).y < -.5
assert (reader.matrix_world.to_3x3() @ Vector((0, -1, 0))).z > .7
for name in ['PRINTER_Body', 'BAG_Base', 'SIGN_Base', 'POS_Base', 'CARD_Base']:
    bounds = measure(bpy.data.objects[name])
    assert bounds['min'][0] > -.7 and bounds['max'][0] < .7, name
    assert bounds['min'][1] > -.35 and bounds['max'][1] < .35, name
    assert bounds['min'][2] >= .95 - 1e-6, name
assert len([o for o in meshes if o.name.startswith('BAG_Hook')]) == 2
sign = bpy.data.objects['SIGN_BlankFace']
old_width = sign.dimensions.x
for v in sign.data.vertices:
    v.co.x *= .9
out = Path(tempfile.mkdtemp(prefix='cashier-counter-pos-source-edit-'))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / 'edited.blend'))
assert abs(bpy.data.objects['SIGN_BlankFace'].dimensions.x - old_width * .9) < 1e-6
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('cashier_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(out / 'edited.glb')
assert sha(out / 'edited.glb') != glb_hash
assert sha(source) == source_hash and sha(delivery) == glb_hash
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(delivery))
bpy.context.view_layer.update()
imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert len(imported) == 3
assert not any(o.type in ['CAMERA', 'LIGHT'] for o in bpy.context.scene.objects)
# Confirm the tested joint geometry also exists in the delivered, batched GLB.
points = [o.matrix_world @ v.co for o in imported for v in o.data.vertices]
tree = KDTree(len(points))
for index, point in enumerate(points):
    tree.insert(point, index)
tree.balance()
export_deviation = max(tree.find(point)[2] for _, vertices in surfaces.values() for point in vertices)
assert export_deviation < 1e-6, export_deviation
attachments['max_glb_joint_vertex_deviation_m'] = export_deviation
attachments['evaluated_joint_vertices_checked'] = sum(len(vertices) for _, vertices in surfaces.values())
generator.studio()
bpy.context.scene.camera.location = (2.3, 3.6, 2.35)
generator.aim(bpy.context.scene.camera, generator.TARGET)
bpy.context.scene.render.filepath = str(HERE / 'previews/reimport.png')
bpy.ops.render.render(write_still=True)
report = {'result': 'PASS', 'source_reopened': True, 'editable_mesh_parts': len(meshes),
    'closed_positive_volume_source_parts': len(meshes), 'countertop_blender_xyz_m': top,
    'screen_faces_staff': True, 'card_reader_faces_customer_and_up': True,
    'attachments': attachments,
    'saved_edit_reopened_and_exported': True, 'edit': 'Blank sign width scaled by 0.9',
    'edited_glb': str(out / 'edited.glb'), 'canonical_files_unchanged': True,
    'independent_native_glb_import_meshes': len(imported), 'native_import_render': 'previews/reimport.png',
    'source_sha256': source_hash, 'canonical_glb_sha256': glb_hash, 'blender_version': bpy.app.version_string}
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
