from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('hawker-centre-table-number',(0.28, -0.45, 0.23)),('front',(0, -2.25, 0.401)),('rear',(-0.28, 0.45, 0.23))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hawker-centre-table-number.glb'))
    h['studio']();s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=0.28;h['point_at'](s.camera,(0, 0, 0.065))
    if 367==366:bpy.data.objects['STUDIO_Floor'].hide_render=True
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
