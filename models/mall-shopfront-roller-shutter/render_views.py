"""Every view uses actual exported meshes, with genuine geometric slat poses."""
from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-shopfront-roller-shutter.glb'))
h['studio']();s=bpy.context.scene
for name,location,lift in [('mall-shopfront-roller-shutter',(4,-7,4),0),('front',(0,-7,1.9),0),('rear',(-4,7,4),0),('part-open',(4,-7,4),1.3),('open',(4,-7,4),2.6)]:
    h['pose'](lift);s.camera.location=location;s.camera.data.ortho_scale=4.4;h['point_at'](s.camera,(0,.1,1.6));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
# Explicit cutaway evidence, not a full-asset open thumbnail.
for o in bpy.data.objects:
    if o.name.startswith('HOOD_'):o.hide_render=True
s.camera.location=(4,-7,4.3);h['point_at'](s.camera,(0,.1,1.6));s.render.filepath=str(HERE/'previews/mechanism-cutaway.png');bpy.ops.render.render(write_still=True)
