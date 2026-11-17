"""Reopen and inspect the saved source; optionally edit a temporary copy."""
from pathlib import Path
import bpy
import json
import runpy
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
api = runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/elevator-interior.blend'))
root = bpy.data.objects['ASSET_ElevatorInterior']
meshes = [o for o in root.children_recursive if o.type == 'MESH']
assert len({m for o in meshes for m in o.data.materials}) == 3
assert not any(o.type in ['FONT', 'CURVE'] for o in root.children_recursive)
assert bpy.context.scene.unit_settings.scale_length == 1
buttons = [o for o in meshes if o.name.startswith('BUTTON_Unlabelled_')]
doors = [o for o in meshes if o.name.startswith('DOOR_')]
assert len(buttons) == 8
assert len(doors) == 4


def bounds(o):
    points = [o.matrix_world @ Vector(p) for p in o.bound_box]
    return {'min':[min(p[i] for p in points) for i in range(3)],
            'max':[max(p[i] for p in points) for i in range(3)]}


panels = [o for o in meshes if o.name.startswith('WALL_SidePanel')]
right = [bounds(o)['min'][0] for o in panels if o.location.x > 0]
left = [bounds(o)['max'][0] for o in panels if o.location.x < 0]
jambs = [bounds(o) for o in meshes if o.name.startswith('FRAME_InnerJamb')]
aperture = min(j['min'][0] for j in jambs if j['min'][0]>0)-max(j['max'][0] for j in jambs if j['max'][0]<0)
floor = bounds(bpy.data.objects['FLOOR_Finish'])['max'][2]
head = bounds(bpy.data.objects['FRAME_Header'])['min'][2]
light = bounds(bpy.data.objects['LIGHT_CeilingPanel'])['min'][2]
report = {'result':'PASS','blender_version':bpy.app.version_string,'editable_mesh_objects':len(meshes),
          'unlabelled_buttons':len(buttons),'open_telescopic_leaves':len(doors),
          'clear_wall_width_m':min(right)-max(left),'door_aperture_width_m':aperture,
          'door_aperture_height_m':head-floor,'ceiling_light_clearance_m':light-floor,
          'parts':{o.name:bounds(o) for o in meshes}}
if '--edit-copy' in sys.argv:
    mirror = bpy.data.objects['MIRROR_RearPanel']
    mirror.scale.x *= .92
    mirror.location.z += .025
    bpy.context.view_layer.update()
    api['export'](HERE/'reports/source-edit.glb')
    report['edit'] = 'Mirror width scaled by 0.92 and raised 0.025 m in memory; source untouched'
    report['edited_mirror_bounds'] = bounds(mirror)
    target = HERE/'reports/source-edit.json'
else:
    api['export'](HERE/'reports/source-reexport.glb')
    target = HERE/'reports/sources.json'
target.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='parts'}))
