"""Inspect the saved native source without changing it."""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
root = bpy.data.objects['ASSET_MallDirectoryStandee']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.scale_length == 1
assert bpy.context.scene.unit_settings.system == 'METRIC'
parts = sorted(root.children_recursive, key=lambda obj: obj.name)
assert all(obj.type == 'MESH' for obj in parts)
assert not any(obj.animation_data for obj in parts)
assert not any(image.source == 'FILE' for image in bpy.data.images)
materials = {mat.name for obj in parts for mat in obj.data.materials}
assert len(materials) == 3
graph = bpy.context.evaluated_depsgraph_get()
records = {}
for obj in parts:
    evaluated = obj.evaluated_get(graph)
    corners = [obj.matrix_world @ Vector(point) for point in evaluated.bound_box]
    records[obj.name] = {
        'min': [min(point[i] for point in corners) for i in range(3)],
        'max': [max(point[i] for point in corners) for i in range(3)],
        'modifiers': [mod.type for mod in obj.modifiers],
        'delivery_group': obj['delivery_group'],
    }
for name in ['PANEL_Front', 'PANEL_Rear', 'MARKER_Dot_Front', 'MARKER_Dot_Rear', 'BASE_SlimWeightedFoot', 'LIGHTBAR_TopHousing']:
    assert name in records
report = {
    'result': 'PASS', 'blender_version': bpy.app.version_string,
    'source_sha256': hashlib.sha256((HERE / 'sources/mall-directory-standee.blend').read_bytes()).hexdigest(),
    'authoring_part_count': len(parts), 'materials': sorted(materials),
    'coordinate_order': 'Blender X width, Y depth, Z height',
    'external_file_images': 0, 'text_objects': 0, 'parts': records,
}
(HERE / 'reports/source.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
