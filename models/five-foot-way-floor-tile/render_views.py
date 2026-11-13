from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('five-foot-way-floor-tile',(1, -1.4, 1.5)),('front',(0,-7.0,1.081)),('rear',(-1, 1.4, 1.5))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/five-foot-way-floor-tile.glb'))
    if name=='lid-raised':bpy.data.objects['MOVABLE_Lid'].location.z+=.10
    h['studio']();s=bpy.context.scene
    for light in [o for o in s.objects if o.type=='LIGHT']:light.location*=max(1,0.88/3);light.data.energy*=max(1,0.88/3)**2;light.data.size*=max(1,0.88/3)
    s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=0.88;h['point_at'](s.camera,(0, 0, 0.025));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
