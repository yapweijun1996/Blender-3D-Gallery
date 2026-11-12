"""Render actual exported GLBs. Assembly removes only PANEL_1, not the ceiling kit."""
from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-ceiling-light-module.glb'))
h['studio']();s=bpy.context.scene;s.cycles.samples=128
for name,location,scale in [('mall-ceiling-light-module',(1.2,-1.6,-1.1),.94),('underside',(0,0,-3),.72),('rear',(1.2,-1.6,1.4),.94),('edge',(-2,-3,-.6),.90)]:
    s.camera.location=location;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,(0,0,.025));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(HERE.parent/'mall-ceiling-panel/exports/mall-ceiling-panel-module.glb'))
panel=bpy.data.objects['PANEL_1'];bpy.data.objects.remove(panel,do_unlink=True)
before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-ceiling-light-module.glb'))
root=next(o for o in set(bpy.context.scene.objects)-before if o.parent is None);root.location=(-.3,-.3,.008)
h['studio'](1.95,(0,0,.12));s=bpy.context.scene;s.cycles.samples=128;s.camera.location=(1.8,-2.3,-1.8);h['point_at'](s.camera,(0,0,.12));s.render.filepath=str(HERE/'previews/assembly-with-422.png');bpy.ops.render.render(write_still=True)
