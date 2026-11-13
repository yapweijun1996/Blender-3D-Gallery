from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc,scale in [('hdb-staircase',(6,-8,6),6.3),('front',(0,-8,4.5),6.1),('rear',(-6,8,6),6.3)]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hdb-staircase.glb'))
    h['studio']();s=bpy.context.scene;s.camera.location=loc;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,(0,.45,1.8));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
