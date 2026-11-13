from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('hdb-neighbourhood-shopfront',(5, -8, 4)),('front',(0,-8,3.1)),('rear',(-5,8,4))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    if name=='front':loc=tuple(t+5*(v-t) for v,t in zip(loc,(0, -0.25, 1.6)))
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hdb-neighbourhood-shopfront.glb'))
    h['studio']();s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=5.5;h['point_at'](s.camera,(0, -0.25, 1.6));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
