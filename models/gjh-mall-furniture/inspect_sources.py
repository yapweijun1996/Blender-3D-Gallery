"""Reopen the editable Blender sources and verify their authoring roots."""
import bpy
import json
from pathlib import Path
root = Path(__file__).resolve().parent
results = []
for name, expected in [('gjh-lounge-bench', 'ASSET_GJHLoungeBench'), ('gjh-areca-planter', 'ASSET_GJHArecaPlanter')]:
    bpy.ops.wm.open_mainfile(filepath=str(root / 'sources' / (name + '.blend')))
    source = bpy.data.objects.get(expected)
    assert source and len(source.children) > 10
    assert tuple(source.location) == (0, 0, 0)
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert all(obj.data for obj in source.children)
    results.append({'id': name, 'source_reopened': 'PASS', 'editable_parts': len(source.children), 'floor_origin': 'PASS', 'blender_version': bpy.app.version_string})
(root / 'reports' / 'sources.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results))
