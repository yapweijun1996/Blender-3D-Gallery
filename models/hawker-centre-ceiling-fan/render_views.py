from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('hawker-centre-ceiling-fan',(2, -3, -1.4)),('front',(0, -15, 2.5599999999999996)),('rear',(-2, 3, 1.4))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hawker-centre-ceiling-fan.glb'))
    h['studio']();s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=1.9;h['point_at'](s.camera,(0, 0, 0.28))
    if 366==366:bpy.data.objects['STUDIO_Floor'].hide_render=True
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
