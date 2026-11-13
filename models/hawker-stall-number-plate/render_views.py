from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('hawker-stall-number-plate',(0.35, -0.65, 0.28)),('front',(0, -3.25, 0.5599999999999999)),('rear',(-0.35, 0.65, 0.28))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hawker-stall-number-plate.glb'))
    h['studio']();s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=0.4;h['point_at'](s.camera,(0, 0, 0.08))
    if 365==366:bpy.data.objects['STUDIO_Floor'].hide_render=True
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
