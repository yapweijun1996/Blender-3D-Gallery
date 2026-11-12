"""Reopen shipped source and verify real separated bodies, lids and editable labels."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
here = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(here/'sources/mall-waste-sorting-station.blend'))
root = bpy.data.collections.get('ASSET_MallWasteSortingStation')
groups = ['StationFrame', 'RecycleCompartment', 'FoodCompartment', 'GeneralCompartment',
          'RecycleLid', 'FoodLid', 'GeneralLid']
assert root and set(groups) == {c.name for c in root.children}
assert root['origin'] == 'floor centre' and root['front_axis'] == '+Y'
details = {}
for name in groups:
    collection = root.children[name]
    assert any(o.type == 'MESH' and len(o.data.polygons) for o in collection.objects)
    details[name] = {'objects': len(collection.objects), 'editable_text': {
        o.name: o.data.body for o in collection.objects if o.type == 'FONT'}}
for key, text in [('Recycle','RECYCLE'), ('Food','FOOD'), ('General','GENERAL')]:
    assert text in details[key+'Lid']['editable_text'].values()
    assert sum('lid side rim' in o.name or 'lid front back rim' in o.name for o in root.children[key+'Lid'].objects) == 4
    assert any('liner bottom' in o.name for o in root.children[key+'Compartment'].objects)
points = [o.matrix_world @ Vector(corner) for c in root.children for o in c.objects for corner in o.bound_box]
assert abs(min(p.z for p in points)) < .001
assert bpy.context.scene.unit_settings.system == 'METRIC'
report = {'id': 'mall-waste-sorting-station', 'source_reopened': 'PASS',
          'blender_version': bpy.app.version_string, 'origin': root['origin'],
          'front_axis': root['front_axis'], 'groups': details,
          'source_bounds': {'min': [min(p[i] for p in points) for i in range(3)],
                            'max': [max(p[i] for p in points) for i in range(3)]}}
(here/'reports/sources.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
