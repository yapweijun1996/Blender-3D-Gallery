"""Render actual shipped GLB, not alternate scene geometry, at several angles."""
from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-floor-tile-module.glb'))
h['studio']();s=bpy.context.scene
for name,location,scale in [('mall-floor-tile-module',(1.8,-2.2,2.4),1.85),('top',(0,0,3),1.5),('edge',(-2,-3,1.4),1.85)]:
    s.camera.location=location;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,(0,0,.015));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for x in (-1.2,0,1.2):
    for y in (-1.2,0,1.2):
        before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-floor-tile-module.glb'))
        root=next(o for o in set(bpy.context.scene.objects)-before if o.parent is None);root.location=(x,y,0)
h['studio'](5.3);s=bpy.context.scene;s.camera.location=(3,-4,5);h['point_at'](s.camera,(0,0,.015));s.render.filepath=str(HERE/'previews/assembly-3x3.png');bpy.ops.render.render(write_still=True)
