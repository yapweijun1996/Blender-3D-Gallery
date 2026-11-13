from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
for name,loc,scale in [('hdb-lift-interior',(3, -7, 2.8),3.5),('front',(0,-7,1.2),3.5),('alternate',(-3, -7, 3.0),3.5)]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/hdb-lift-interior.glb'))
    h['studio']();s=bpy.context.scene;s.cycles.samples=128;bpy.ops.object.light_add(type='AREA',location=(0,-2,1.6));lamp=bpy.context.object;lamp.name='STUDIO_InteriorFill';lamp.data.energy=280;lamp.data.size=2;h['point_at'](lamp,(0,.7,1.2));s.camera.location=loc;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,(0, 0, 1.2));s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
