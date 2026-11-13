from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('satay-skewer-display',(0.6, -0.8, 0.65)),('front',(0,-4.0,0.8200000000000001)),('rear',(-0.6, 0.8, 0.65))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/satay-skewer-display.glb'))
    if name=='lid-raised':bpy.data.objects['MOVABLE_Lid'].location.z+=.10
    h['studio']();s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=0.65;h['point_at'](s.camera,(0, 0, 0.04));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
