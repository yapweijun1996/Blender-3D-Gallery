"""Render actual shipped GLB, closed and articulated, not substitute geometry."""
from pathlib import Path
import bpy,runpy,math
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-shopfront-door.glb'))
h['studio']();s=bpy.context.scene
for name,location,scale in [('mall-shopfront-door',(3,-6,3.1),3.3),('front',(0,-6,1.55),2.8),('rear',(-3,6,3),3.3),('open',(3,-6,3.1),3.6)]:
    if name=='open':
        bpy.data.objects['HINGE_Left'].rotation_mode='XYZ';bpy.data.objects['HINGE_Right'].rotation_mode='XYZ';bpy.data.objects['HINGE_Left'].rotation_euler.z=-math.pi/2;bpy.data.objects['HINGE_Right'].rotation_euler.z=math.pi/2
    s.camera.location=location;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,(0,-.18 if name=='open' else 0,1.15));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
