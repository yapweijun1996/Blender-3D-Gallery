"""Multi-angle evidence from the actual shipped GLB."""
from pathlib import Path
import bpy,runpy,math
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-ceiling-panel-module.glb'))
h['studio']();s=bpy.context.scene
for name,location,scale,target in [('mall-ceiling-panel-module',(1.8,-2.3,-1.8),1.95,(0,0,.12)),('underside',(0,0,-3),1.5,(0,0,.10)),('rear',(1.8,-2.3,2.0),1.95,(0,0,.12)),('edge',(-2,-3,-.6),1.85,(0,0,.16))]:
    s.camera.location=location;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,target);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for x in (-1.2,0,1.2):
    for y in (-1.2,0,1.2):
        before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-ceiling-panel-module.glb'))
        root=next(o for o in set(bpy.context.scene.objects)-before if o.parent is None);root.location=(x,y,0);root.rotation_euler.z=((round(x/1.2)+round(y/1.2))%4)*math.pi/2
h['studio'](5.4);s=bpy.context.scene;s.camera.location=(3,-4,-4);h['point_at'](s.camera,(0,0,.10));s.render.filepath=str(HERE/'previews/assembly-3x3.png');bpy.ops.render.render(write_still=True)
