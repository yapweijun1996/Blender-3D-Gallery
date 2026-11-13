"""All views import the actual assembled export. No stand-in railing or tiles."""
from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc,scale,target in [('mall-atrium-balcony',(3,-5,3),3.4,(0,0,.65)),('front',(0,-5,1.9),2.9,(0,0,.65)),('rear',(-3,5,3),3.4,(0,0,.65)),('underside',(3,-5,-2),3.4,(0,0,.55)),('assembly-three-bays',(7,-8,5),7.3,(2,0,.6))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for i in range(3 if name=='assembly-three-bays' else 1):
        before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-atrium-balcony.glb'))
        root=next(o for o in set(bpy.context.scene.objects)-before if o.name.startswith('ASSET_MallAtriumBalcony'));root.location.x=i*2
        if name=='assembly-three-bays':
            remove=(['MODULE_Post_Left','MODULE_EndCap_Left'] if i>0 else [])+(['MODULE_EndCap_Right'] if i<2 else [])
            for o in list(root.children):
                if any(o.name.startswith(n) for n in remove):
                    for c in list(o.children_recursive):bpy.data.objects.remove(c,do_unlink=True)
                    bpy.data.objects.remove(o,do_unlink=True)
    h['studio']();s=bpy.context.scene;s.cycles.samples=32;s.camera.location=loc;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,target)
    if name=='underside':bpy.data.objects['STUDIO_Floor'].hide_render=True
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
