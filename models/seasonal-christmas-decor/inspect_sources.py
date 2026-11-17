"""Reopen and inspect native source, then exercise an edit in a separate copy."""
from pathlib import Path
import bpy
import bmesh
import json
import hashlib
import importlib.util
from mathutils import Vector

p = Path(__file__).resolve().parent
slug = p.name
source = p/'sources'/(slug+'.blend')
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_SeasonalChristmasDecor']
assert tuple(root.location) == (0,0,0)
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
assert not any(o.type in ['FONT','CURVE'] for o in root.children_recursive)
materials = {m.name for o in meshes for m in o.data.materials}
assert len(materials) == 3
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    assert bm.calc_volume() > 0, o.name
    bm.free()
gifts = [o for o in root.children_recursive if o.name.startswith('GIFT_')]
flakes = [o for o in root.children_recursive if o.name.startswith('SNOWFLAKE_')]
baubles = [o for o in meshes if o.name.startswith('BAUBLE_')]
assert len(gifts) == 4 and len(flakes) == 2 and len(baubles) == 27
assert len([o for o in meshes if o.name == 'STAR_FacetedTopper']) == 1
assert len([o for o in meshes if o.name.startswith('FOLIAGE_')]) == 7
for o in flakes:
    assert o['feature'] == 'six-arm hanging snowflake'
    assert len([m for m in o.children if '_Arm' in m.name]) == 6
    assert len([m for m in o.children if '_Cord' in m.name]) == 1
    assert len([m for m in o.children if '_Ring' in m.name]) == 1
# Inspect box support in saved source; the small top box sits on box 1's lid.
def bounds(o):
    points = [o.matrix_world @ Vector(v) for v in o.bound_box]
    return [min(v.z for v in points),max(v.z for v in points)]
bpy.context.view_layer.update()
for number in [1,3,4]:
    assert abs(bounds(bpy.data.objects[f'BOX_{number:02}_Body'])[0]) < 1e-6
assert abs(bounds(bpy.data.objects['BOX_02_Body'])[0]-bounds(bpy.data.objects['BOX_01_Lid'])[1]) < 1e-6
# A conservative sphere versus gift-assembly AABB check catches the observed
# ornament/bow overlap, including the bevels on the evaluated gift meshes.
deps = bpy.context.evaluated_depsgraph_get()
clearance = []
for gift in gifts:
    points = [o.matrix_world @ Vector(v) for o in gift.children_recursive
              if o.type == 'MESH' for v in o.evaluated_get(deps).bound_box]
    low = Vector(tuple(min(v[i] for v in points) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in points) for i in range(3)))
    for bauble in baubles:
        center = bauble.matrix_world.translation
        radius = max(bauble.dimensions)/2
        closest = Vector(tuple(max(low[i],min(high[i],center[i])) for i in range(3)))
        gap = (center-closest).length-radius
        assert gap > 0, (bauble.name,gift.name,gap)
        clearance.append(gap)
target = bpy.data.objects['BAUBLE_00_00']
batch = target['delivery_mesh']
for vertex in target.data.vertices:
    vertex.co.x *= .92
target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
out = p/'reports/source-edit'
out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'-edited.blend')),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out/(slug+'-edited.blend')))
assert bpy.data.objects['BAUBLE_00_00'].data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value > .769
spec = importlib.util.spec_from_file_location('asset_generator',p/'generate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.export(out/'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = {'result':'PASS','source_reopened':True,'editable_mesh_parts':len(meshes),
    'closed_manifold_meshes':len(meshes),'materials':len(materials),'gift_boxes':len(gifts),
    'hanging_snowflakes':len(flakes),'baubles':len(baubles),'star_toppers':1,'foliage_tiers':7,
    'floor_and_stacked_gift_support':'PASS','blender_version':bpy.app.version_string,
    'minimum_bauble_to_gift_aabb_clearance_metres':min(clearance),
    'source_sha256':before,'original_source_unchanged':True,'edited_delivery_mesh':batch,
    'edit':'BAUBLE_00_00 local X scaled by 0.92; shared roughness changed to 0.77 in a copy',
    'edited_glb_sha256':hashlib.sha256((out/'edited.glb').read_bytes()).hexdigest(),
    'limitations':'Closed components may overlap intentionally; this is not a mesh-union or collision certification.'}
(p/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
