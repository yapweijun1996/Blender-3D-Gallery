"""Reopen the native source, inspect mounting geometry, and export a saved edit."""
from pathlib import Path
import bpy
import bmesh
import hashlib
import importlib.util
import json
import math
import os
from mathutils import Vector

p = Path(__file__).resolve().parent
slug = p.name
source = p/'sources'/(slug+'.blend')
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_VehicleEtagDisplayStand']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
tags = sorted([o for o in root.children if o.name.startswith('TAG_')], key=lambda o: o.name)
assert len(tags) == 6
for obj in meshes:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert bm.calc_volume() > 0, (obj.name, bm.calc_volume())
    assert all(math.isfinite(v) for vertex in obj.data.vertices for v in vertex.co)
    bm.free()
assert len({mat.name for obj in meshes for mat in obj.data.materials}) == 3
assert not any(obj.type == 'FONT' for obj in root.children_recursive)
windows = [obj for obj in meshes if obj.name.endswith('_BlankWindow')]
pads = [obj for obj in meshes if '_MountPad' in obj.name]
assert len(windows) == 6 and len(pads) == 12
assert 'SIGN_BlankCard' in bpy.data.objects
bpy.context.view_layer.update()
mount_residuals = []
for tag in tags:
    assert abs(tag.rotation_euler.x-math.radians(30)) < 1e-6
    assert tag['has_blank_window']
    for pad in [obj for obj in tag.children if '_MountPad' in obj.name]:
        bottom = min(vertex.co.z for vertex in pad.data.vertices) + pad.location.z
        assert abs(bottom) < 1e-7, 'Pads contact the mounting plane'
        world = tag.matrix_world @ Vector((pad.location.x, pad.location.y, bottom))
        residual = abs(world.z - (.064+(world.y+.148)*math.tan(math.radians(30))))
        assert residual < 1e-7, 'Mounting plane agrees with wedge face'
        mount_residuals.append(residual)
source_report = {
    'result': 'PASS', 'source_reopened': 'PASS', 'editable_mesh_parts': len(meshes),
    'closed_manifold_positive_volume_meshes': len(meshes), 'toll_tags': len(tags),
    'blank_windows': len(windows), 'mounting_pads': len(pads),
    'mount_contact_max_residual_m': max(mount_residuals),
    'riser_angle_degrees': math.degrees(tags[0].rotation_euler.x),
    'source_materials': 3, 'text_objects': 0, 'units': 'metres',
    'blender_version': bpy.app.version_string, 'source_sha256': before,
}
target = bpy.data.objects['SIGN_BlankCard']
for vertex in target.data.vertices:
    vertex.co.x *= .92
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
out = Path(os.environ.get('ETAG_EDIT_DIR', '/tmp/vehicle-etag-display-stand-source-edit'))
out.mkdir(exist_ok=True, parents=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'-edited.blend')), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out/(slug+'-edited.blend')))
spec = importlib.util.spec_from_file_location('asset_generator', p/'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(out/'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
source_report.update({
    'edited_mesh': 'SIGN_BlankCard', 'edit': 'Card local X scaled by 0.92; ivory roughness changed to 0.77',
    'original_source_unchanged': True,
    'edited_glb_sha256': hashlib.sha256((out/'edited.glb').read_bytes()).hexdigest(),
})
(p/'reports/sources.json').write_text(json.dumps(source_report, indent=2)+'\n')
print(json.dumps(source_report))
