import bpy, json
from pathlib import Path
root = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root / 'sources/mall-event-booth.blend'))
scene_root = bpy.data.collections.get('ASSET_MallEventBooth')
assert scene_root and {'BoothStructure', 'PosterPanel', 'DisplayContent'} <= {c.name for c in scene_root.children}
poster = scene_root.children.get('PosterPanel'); display = scene_root.children.get('DisplayContent')
assert poster and display and len(poster.objects) >= 5 and len(display.objects) >= 5
assert any(o.type == 'FONT' and o.data.body == 'YOUR STORY' for o in poster.objects)
assert any(o.type == 'FONT' and o.data.body == 'EDITABLE DISPLAY' for o in display.objects)
result = {'id': 'mall-event-booth', 'source_reopened': 'PASS', 'collections': [c.name for c in scene_root.children], 'poster_objects': len(poster.objects), 'display_objects': len(display.objects), 'blender_version': bpy.app.version_string, 'floor_origin': scene_root['origin']}
(root / 'reports').mkdir(exist_ok=True); (root / 'reports/sources.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))
