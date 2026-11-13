"""Studio renders import the actual delivered GLB. Assembly imports original 421."""
from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
views=[('mall-escalator-landing',(2.3,-3,3.2),1.85,(0,0,.015)),('top',(0,-.001,4),1.55,(0,0,.015)),('interface',(1.4,2.5,1.9),1.9,(0,0,.015)),('underside',(2,-3,-2),1.9,(0,0,.015)),('assembly-floor',(2.8,-4,3.8),3.1,(0,-.6,.015))]
for name,loc,scale,target in views:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/optimized.glb'))
    if name=='assembly-floor':
        before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(HERE.parent/'mall-floor-tile/exports/mall-floor-tile-module.glb'))
        # GLB importer maps back to Blender: adjacent root at Y=-1.2 (glTF Z=+1.2).
        added=set(bpy.context.scene.objects)-before
        for o in added:
            if o.parent is None:o.location.y-=1.2
    h['studio']();s=bpy.context.scene;s.cycles.samples=32;s.camera.location=loc;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,target)
    if name=='underside':bpy.data.objects['STUDIO_Floor'].hide_render=True
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
