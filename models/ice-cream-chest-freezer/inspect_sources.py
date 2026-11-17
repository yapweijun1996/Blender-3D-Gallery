"""Audit editable source, save/reopen an edit, and render the delivered GLB."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy
import bmesh
from mathutils import Vector

here = Path(__file__).resolve().parent
source = here / 'sources/ice-cream-chest-freezer.blend'
delivery = here / 'exports/optimized.glb'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original_source, original_glb = sha(source), sha(delivery)
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_IceCreamChestFreezer']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH' and o.name != 'collider_box']
collider = bpy.data.objects['collider_box']
assert collider.hide_render and collider.hide_get() and not collider.data.materials
assert len({m for o in meshes for m in o.data.materials}) == 2
assert not any(o.type in ['FONT', 'ARMATURE'] for o in root.children_recursive)
assert not any(o.animation_data for o in root.children_recursive)
assert not any(i.source == 'FILE' for i in bpy.data.images)
for o in meshes:
    assert not o.data.validate(verbose=False), o.name
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()
assert len([o for o in meshes if o.name.startswith('Tub_')]) == 6
assert len([o for o in meshes if o.name.startswith('Frozen_')]) == 6
relief = {}
for o in meshes:
    if o.name.startswith('Frozen_'):
        heights = [v.co.z for v in o.data.vertices if v.co.z > .2]
        relief[o.name] = max(heights) - min(heights)
        assert .02 < relief[o.name] < .05, 'Restrained visible cream relief'
target = bpy.data.objects['Blank thermostat bezel']
for v in target.data.vertices:
    v.co.x *= .9
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .78
original_lid_x = bpy.data.objects['Lid_Left'].location.x
bpy.data.objects['Lid_Left'].location.x += .05
out = Path(tempfile.mkdtemp(prefix='ice-cream-source-edit-'))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / 'edited.blend'))
assert abs(bpy.data.objects['Blank thermostat bezel'].dimensions.x - .1035) < 1e-5
assert abs(bpy.data.objects['Lid_Left'].location.x - original_lid_x - .05) < 1e-6
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('freezer_generator', here / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(out / 'edited.glb')
assert sha(out / 'edited.glb') != original_glb
assert sha(source) == original_source and sha(delivery) == original_glb
# Import the canonical delivery independently; studio objects are not in it.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(delivery))
imported_root = bpy.data.objects['ASSET_IceCreamChestFreezer']
imported_meshes = [o for o in imported_root.children_recursive if o.type == 'MESH']
imported_collider = bpy.data.objects['collider_box']
assert imported_collider not in imported_meshes and not imported_collider.data.materials
imported_collider.hide_render = True
assert imported_meshes
assert not any(o.type in ['LIGHT', 'CAMERA'] for o in bpy.context.scene.objects)
bpy.context.view_layer.update()
points = [o.matrix_world @ Vector(c) for o in imported_meshes for c in o.bound_box]
imported_dims = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]
assert abs(imported_dims[0] - 1.5) < .001 and abs(imported_dims[2] - .9) < .001
generator.studio()
scene = bpy.context.scene
scene.camera.location = (3, -4.2, 4.91)
generator.aim(scene.camera, (0, 0, .41))
scene.render.filepath = str(here / 'previews/reimport.png')
bpy.ops.render.render(write_still=True)
report = {'result':'PASS', 'source_reopened':True, 'editable_mesh_parts':len(meshes),
    'manifold_positive_volume_parts':len(meshes), 'source_sha256':original_source,
    'cream_surface_relief_m':relief, 'hidden_unmaterialed_source_collider':True,
    'canonical_glb_sha256':original_glb, 'original_files_unchanged':True,
    'edited_glb':str(out / 'edited.glb'), 'saved_edit':'Bezel width 0.115 -> 0.1035 m, shared opaque roughness -> 0.78, left lid X +0.05 m',
    'independent_native_glb_import':'PASS', 'native_import_dimensions_blender_xyz_m':imported_dims,
    'native_import_render':'previews/reimport.png', 'blender_version':bpy.app.version_string}
(here / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
