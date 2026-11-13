from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc,scale in [('hdb-corridor-window',(3, -6, 2.0),2.6),('front',(0,-7,0.6),2.6),('alternate',(-3, 6, 2.0),2.6)]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hdb-corridor-window.glb'))
    h['studio']();s=bpy.context.scene;s.camera.location=loc;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,(0, 0, 0.6));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
