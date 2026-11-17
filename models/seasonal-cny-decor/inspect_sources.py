"""Reopen native source, measure actual features, edit and re-export a copy."""
from pathlib import Path
import bpy
import bmesh
import json
import hashlib
import importlib.util
from mathutils import Vector

p = Path(__file__).resolve().parent
source = p/'sources/seasonal-cny-decor.blend'
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_SeasonalCNYDecor']
assert tuple(root.location) == (0,0,0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
assert not any(o.type in ['FONT','CURVE'] for o in root.children_recursive)
assert len({m.name for o in meshes for m in o.data.materials}) == 3
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()
lanterns = [o for o in root.children if o.name.startswith('LANTERN_')]
banners = [o for o in root.children if o.name.startswith('BANNER_')]
oranges = [o for o in meshes if o.name.startswith('ORANGE_')]
envelopes = [o for o in meshes if o.name.startswith('ENVELOPE_') and '_Flap_' not in o.name]
leaves = [o for o in meshes if o.name.startswith('LEAF_')]
assert len(lanterns) == 2 and len(banners) == 2
assert len(oranges) == 16 and len(envelopes) == 6 and len(leaves) == 81
for o in lanterns+banners:
    assert 'hanging_anchor_blender' in o
    if o in lanterns:
        assert len([m for m in o.children if m.name.startswith('LANTERN_BODY_')]) == 1
        assert len([m for m in o.children if m.name.startswith('LANTERN_TASSEL_')]) == 2
    else:
        assert len([m for m in o.children if m.name.startswith('BANNER_CLOTH_')]) == 1
bpy.context.view_layer.update()
plant = bpy.data.objects['PLANT_Assembly']
points = [o.matrix_world @ Vector(v) for o in plant.children_recursive if o.type == 'MESH' for v in o.bound_box]
height = max(v.z for v in points)-min(v.z for v in points)
assert abs(height-1) < 1e-6
target = bpy.data.objects['ORANGE_0_0']
batch = target['delivery_mesh']
for vertex in target.data.vertices:
    vertex.co.x *= .92
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
out = p/'reports/source-edit'
out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'seasonal-cny-decor-edited.blend'),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out/'seasonal-cny-decor-edited.blend'))
assert bpy.data.objects['ORANGE_0_0'].data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value > .769
spec = importlib.util.spec_from_file_location('asset_generator',p/'generate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.export(out/'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = {'result':'PASS','source_reopened':True,'editable_mesh_parts':len(meshes),
    'closed_manifold_meshes':len(meshes),'materials':3,'hanging_lanterns':len(lanterns),
    'blank_banners':len(banners),'potted_tangerine_plants':1,'red_envelope_stands':1,
    'oranges':len(oranges),'leaves':len(leaves),'red_envelopes':len(envelopes),
    'plant_height_metres':height,'blender_version':bpy.app.version_string,
    'source_sha256':before,'original_source_unchanged':True,'edited_delivery_mesh':batch,
    'edit':'ORANGE_0_0 local X scaled by 0.92; shared roughness changed to 0.77 in a copy',
    'edited_glb_sha256':hashlib.sha256((out/'edited.glb').read_bytes()).hexdigest(),
    'limitations':'Individual closed components can intentionally overlap at joints; no collision or mesh-union certification.'}
(p/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
