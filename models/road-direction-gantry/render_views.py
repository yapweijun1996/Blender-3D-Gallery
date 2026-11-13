from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('road-direction-gantry',(14, -20, 13)),('front',(0,-100,19.599999999999998)),('rear',(-14, 20, 13))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/road-direction-gantry.glb'))
    if name=='lid-raised':bpy.data.objects['MOVABLE_Lid'].location.z+=.10
    h['studio']();s=bpy.context.scene
    for light in [o for o in s.objects if o.type=='LIGHT']:light.location*=max(1,13.5/3);light.data.energy*=max(1,13.5/3)**2;light.data.size*=max(1,13.5/3)
    s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=13.5;h['point_at'](s.camera,(0, 0, 3.4));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
