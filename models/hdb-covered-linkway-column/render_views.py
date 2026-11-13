from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('hdb-covered-linkway-column',(4, -6, 3.2)),('front',(0,-6,3.05)),('rear',(-4,6,3.2))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    if name=='front':loc=tuple(t+5*(v-t) for v,t in zip(loc,(0, 0, 1.55)))
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hdb-covered-linkway-column.glb'))
    h['studio']();s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=4.2;h['point_at'](s.camera,(0, 0, 1.55));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
