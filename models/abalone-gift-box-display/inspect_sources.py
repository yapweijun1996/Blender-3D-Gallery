"""Reopen and inspect the native source independently of the generator."""
from pathlib import Path
import bpy
import json
from mathutils import Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/abalone-gift-box-display.blend'))
bpy.context.view_layer.update()
root = bpy.data.objects['ASSET_AbaloneGiftBoxDisplay']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.scale_length == 1
gifts = sorted([o for o in root.children if o.name.startswith('GiftBox_')], key=lambda o: o.name)
assert len(gifts) == 12
parts = [o for o in root.children_recursive if o.type == 'MESH']
assert len({m.name for o in parts for m in o.data.materials}) == 3
assert len([o for o in parts if o.name.startswith('PlainCan_')]) == 24
assert len([o for o in parts if o.name.startswith('Gift_ClearLid')]) == 12
assert len([o for o in parts if o.name.startswith('BlankGiftCard')]) == 12
assert len([o for o in parts if o.name == 'BlankSignPanel']) == 1
assert len([o for o in parts if o.name.startswith('Cradle_')]) == 12
assert not bpy.data.images
assert not [o for o in bpy.data.objects if o.type in {'FONT', 'CAMERA', 'LIGHT'}]
details = []
for group in gifts:
    cans = [o for o in group.children if o.name.startswith('PlainCan_')]
    lids = [o for o in group.children if o.name.startswith('Gift_ClearLid')]
    cards = [o for o in group.children if o.name.startswith('BlankGiftCard')]
    assert len(cans) == 2 and len(lids) == 1 and len(cards) == 1
    assert len([o for o in group.children if o.name.startswith('Ribbon_')]) == 3
    assert all(o.data.vertices for o in group.children if o.type == 'MESH')
    # The plain can tops sit below the clear lid and above the inner floor.
    assert all(max(v.co.z + o.location.z for v in o.data.vertices) < .052 for o in cans)
    assert all(min(v.co.z + o.location.z for v in o.data.vertices) > -.0441 for o in cans)
    deps = bpy.context.evaluated_depsgraph_get()
    corners = [o.matrix_world @ v.co for o in group.children if o.type == 'MESH' for v in o.evaluated_get(deps).data.vertices]
    minimum = [min(p[i] for p in corners) for i in range(3)]
    maximum = [max(p[i] for p in corners) for i in range(3)]
    expected_tier = [.045, .245, .445][(int(group.name[-2:]) - 1) // 4]
    assert abs(minimum[2] - expected_tier) < .0001, (group.name, minimum, expected_tier)
    details.append({'name': group.name, 'cans': len(cans), 'clear_lids': len(lids),
                    'blank_cards': len(cards), 'bounds_blender': {'min': minimum, 'max': maximum}})
report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
          'units': 'metres', 'editable_gift_boxes': len(gifts), 'plain_cans': 24,
          'clear_lids': 12, 'blank_gift_cards': 12, 'blank_signs': 1,
          'materials': len({m.name for o in parts for m in o.data.materials}),
          'source_mesh_objects': len(parts), 'gifts': details}
(HERE / 'reports/source.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
