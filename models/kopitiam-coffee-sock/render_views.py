from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('kopitiam-coffee-sock',(0.6, -0.9, 0.65)),('front',(0, -4.5, 0.9520000000000001)),('rear',(-0.6, 0.9, 0.65))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/kopitiam-coffee-sock.glb'))
    h['studio']();s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=0.66;h['point_at'](s.camera,(0.13, 0, 0.16))
    if 369==366:bpy.data.objects['STUDIO_Floor'].hide_render=True
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
