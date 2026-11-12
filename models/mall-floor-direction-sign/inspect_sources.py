"""Reopen the actual editable source and inspect real semantic collections."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
here = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(here/'sources/mall-floor-direction-sign.blend'))
root = bpy.data.collections.get('ASSET_MallFloorDirectionSign')
groups = ['SignStructure', 'FloorIdentity', 'DirectionDining', 'DirectionShops',
          'DirectionCinema', 'DirectionFacilities']
assert root and set(groups) == {c.name for c in root.children}
assert root['origin'] == 'floor centre' and root['front_axis'] == '+Y'
details = {}
for name in groups:
    collection = root.children[name]
    assert any(o.type == 'MESH' and len(o.data.polygons) for o in collection.objects)
    details[name] = {'objects': len(collection.objects), 'editable_text': {
        o.name: o.data.body for o in collection.objects if o.type == 'FONT'}}
for name, destination in [('DirectionDining', 'Dining'), ('DirectionShops', 'Shops'),
                          ('DirectionCinema', 'Cinema'), ('DirectionFacilities', 'Restrooms')]:
    assert destination in details[name]['editable_text'].values()
    assert any('arrow' in o.name and o.type == 'MESH' for o in root.children[name].objects)
assert '02' in details['FloorIdentity']['editable_text'].values()
points = [o.matrix_world @ Vector(corner) for c in root.children for o in c.objects for corner in o.bound_box]
assert abs(min(p.z for p in points)) < .001
assert bpy.context.scene.unit_settings.system == 'METRIC'
report = {'id': 'mall-floor-direction-sign', 'source_reopened': 'PASS',
          'blender_version': bpy.app.version_string, 'origin': root['origin'],
          'front_axis': root['front_axis'], 'groups': details,
          'source_bounds': {'min': [min(p[i] for p in points) for i in range(3)],
                            'max': [max(p[i] for p in points) for i in range(3)]}}
(here/'reports/sources.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
