"""Inspect saved authoring geometry and exercise a mesh/material edit in a copy."""
from pathlib import Path
import bpy
import bmesh
import hashlib
import importlib.util
import json
import math
from mathutils import Vector

HERE = Path(__file__).resolve().parent
source = HERE / 'sources/peanut-butter-jar-stand.blend'
original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_PeanutButterJarStand']
bpy.context.view_layer.update()
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()
    assert all(math.isfinite(v) for vertex in o.data.vertices for v in vertex.co), o.name
assert not any(o.type == 'FONT' for o in bpy.data.objects)
assert not bpy.data.images
jars = sorted([o for o in root.children if o.name.startswith('Jar_')], key=lambda o: o.name)
assert len(jars) == 24

def world_bounds(group):
    points = [o.matrix_world @ v.co for o in group.children if o.type == 'MESH' for v in o.data.vertices]
    return [min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]

parts = []
for group in jars:
    assert len(group.children) == 2
    body = next(o for o in group.children if o.name.startswith('JarBody_'))
    lid = next(o for o in group.children if o.name.startswith('PlainLid_'))
    assert sum(p.material_index == 1 for p in body.data.polygons) == 24
    lo, hi = world_bounds(group)
    dims = [hi[i] - lo[i] for i in range(3)]
    assert abs(dims[2] - .12) < 1e-6
    assert abs(dims[0] - .104) < 1e-6
    tier = group['tier']
    deck = bpy.data.objects[f'Tier_{tier}_Deck']
    top = max((deck.matrix_world @ v.co).z for v in deck.data.vertices)
    assert abs(lo[2] - top) < 1e-6, (group.name, lo[2], top)
    # Every jar footprint fits its supporting deck, including the top pair.
    assert abs(group.location.x) + .052 <= deck.dimensions.x / 2 + 1e-6
    assert abs(group.location.y) + .052 <= deck.dimensions.y / 2 + 1e-6
    parts.append({'name': group.name, 'tier': tier, 'dimensions_m': dims, 'bounds_blender': {'min': lo, 'max': hi}, 'support_gap_m': lo[2] - top})
for i, a in enumerate(jars):
    for b in jars[i + 1:]:
        if a['tier'] == b['tier']:
            assert math.hypot(a.location.x - b.location.x, a.location.y - b.location.y) >= .104 - 1e-6
        else:
            al, ah = world_bounds(a)
            bl, bh = world_bounds(b)
            assert ah[2] <= bl[2] + 1e-6 or bh[2] <= al[2] + 1e-6
counts = [sum(o['tier'] == i for o in jars) for i in [1, 2, 3]]
assert counts == [14, 8, 2]
# Preserve the editable source and test an actual saved edit, as in the template.
target = bpy.data.objects['Pedestal_Cabinet']
for v in target.data.vertices:
    v.co.x *= .92
mat = bpy.data.materials['SharedPlainTerracottaLid']
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
out = HERE / 'reports/source-edit'
out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'edited.blend'), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / 'edited.blend'))
assert abs(bpy.data.materials['SharedPlainTerracottaLid'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value - .77) < 1e-6
spec = importlib.util.spec_from_file_location('asset_generator', HERE / 'generate.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.export(out / 'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
report = {'result': 'PASS', 'blender_version': bpy.app.version_string, 'source_sha256': original_hash,
          'editable_meshes': len(meshes), 'closed_manifold_meshes': len(meshes), 'jar_count': len(jars),
          'tier_counts': counts, 'jars': parts, 'source_reopened': True, 'original_source_unchanged': True,
          'saved_edit': 'Cabinet local X vertices scaled by 0.92; lid roughness set to 0.77',
          'edited_glb_sha256': hashlib.sha256((out / 'edited.glb').read_bytes()).hexdigest()}
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
