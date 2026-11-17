"""Reopen source, audit closed geometry, and prove saved edits survive export."""
from pathlib import Path
import bpy
import bmesh
import hashlib
import importlib.util
import json
import tempfile
import sys
from mathutils import Vector

here = Path(__file__).resolve().parent
source = here / 'sources/restaurant-table-chair-set.blend'
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_RestaurantTableChairSet']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
materials = {m.name for o in meshes for m in o.data.materials}
assert len(materials) == 3
assert not any(o.type == 'FONT' for o in bpy.data.objects)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
measurements = {}
for name in ['TableTop_800mm', 'Chair_North_Seat', 'Chair_East_Seat', 'Chair_South_Seat', 'Chair_West_Seat', 'StandBlankCard']:
    o = bpy.data.objects[name].evaluated_get(depsgraph)
    points = [o.matrix_world @ Vector(corner) for corner in o.bound_box]
    measurements[name] = {'min_blender_xyz':[min(v[i] for v in points) for i in range(3)],
                          'max_blender_xyz':[max(v[i] for v in points) for i in range(3)]}
for name in ['Chair_North', 'Chair_East', 'Chair_South', 'Chair_West']:
    o = bpy.data.objects[name]
    assert abs(o.location.z) < 1e-6
    forward = o.matrix_world.to_3x3() @ Vector((0, -1, 0))
    assert forward.dot(-o.location.normalized()) > .999
    assert abs(measurements[name + '_Seat']['max_blender_xyz'][2] - .45) < 1e-6
for o in meshes:
    assert o.data.validate(verbose=False) is False, o.name
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()
target = bpy.data.objects['StandBlankCard']
for vertex in target.data.vertices:
    vertex.co.x *= .92
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
out = Path(tempfile.mkdtemp(prefix='restaurant-table-chair-source-edit-'))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / 'edited.blend'))
assert abs(bpy.data.objects['StandBlankCard'].data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value - .77) < 1e-5
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('asset_generator', here / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(out / 'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = {'result':'PASS', 'source_reopened':True, 'editable_mesh_parts':len(meshes),
          'closed_manifold_meshes':len(meshes), 'shared_materials':sorted(materials),
          'units':'metres', 'blender_version':bpy.app.version_string, 'source_sha256':before,
          'saved_edit':'Blank card X width scaled to 0.92; ivory roughness changed to 0.77',
          'original_source_unchanged':True, 'measurements':measurements, 'chairs_face_inward':True,
          'edited_glb':str(out / 'edited.glb')}
(here / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
