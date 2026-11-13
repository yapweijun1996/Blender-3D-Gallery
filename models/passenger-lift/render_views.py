"""Inspect exported GLB, not authoring scene. Six independent views/modes."""
from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent
h=runpy.run_path(str(HERE/'generate.py'),run_name='helpers')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/passenger-lift.glb'))
for o in list(bpy.context.scene.objects):o.animation_data_clear()
cab=bpy.data.objects['CAB_Carriage'];cab.location.z=0
for name in ['DOOR_CabL','DOOR_Landing0L','DOOR_Landing1L']:bpy.data.objects[name].location.x=-.255
for name in ['DOOR_CabR','DOOR_Landing0R','DOOR_Landing1R']:bpy.data.objects[name].location.x=.255
h['studio']();s=bpy.context.scene;s.render.resolution_x=s.render.resolution_y=768;s.cycles.samples=24
for name,loc in [('hero',(8,-12,8)),('front',(0,-14,4)),('rear',(8,10,8)),('side',(14,0,4))]:
 s.camera.location=loc;h['point_at'](s.camera,(0,-.4,3.245));s.camera.data.ortho_scale=8.1;s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
s.camera.location=(8,-12,8);h['point_at'](s.camera,(0,-.4,3.245))
for name in ['DOOR_CabL','DOOR_Landing0L']:bpy.data.objects[name].location.x=-.785
for name in ['DOOR_CabR','DOOR_Landing0R']:bpy.data.objects[name].location.x=.785
s.render.filepath=str(HERE/'previews/doors-open.png');bpy.ops.render.render(write_still=True)
for name in ['DOOR_CabL','DOOR_Landing0L']:bpy.data.objects[name].location.x=-.255
for name in ['DOOR_CabR','DOOR_Landing0R']:bpy.data.objects[name].location.x=.255
cab.location.z=3;s.render.filepath=str(HERE/'previews/travel-upper.png');bpy.ops.render.render(write_still=True)
