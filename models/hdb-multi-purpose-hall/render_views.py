from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc in [('hdb-multi-purpose-hall',(14, -18, 12)),('front',(0,-18,3.5999999999999996)),('rear',(-14,18,12))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    if name=='front':loc=tuple(t+5*(v-t) for v,t in zip(loc,(0, 0, 2.1)))
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hdb-multi-purpose-hall.glb'))
    h['studio']()
    for n,lamp_loc,power,size in [('Key',(-8,-10,14),3000,10),('Fill',(10,-8,10),2500,10),('Rear',(1,10,12),3500,10)]:
        lamp=bpy.data.objects['STUDIO_'+n];lamp.location=lamp_loc;lamp.data.energy=power;lamp.data.size=size;h['point_at'](lamp,(0,0,2))
    s=bpy.context.scene;s.camera.data.clip_end=10000;s.camera.location=loc;s.camera.data.ortho_scale=17;h['point_at'](s.camera,(0, 0, 2.1));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
