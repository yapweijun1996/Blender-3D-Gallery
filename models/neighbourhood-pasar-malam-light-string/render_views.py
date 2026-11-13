from pathlib import Path
import bpy,runpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
import sys
for name,direction in [('hero',(1.3,-2,1)),('front',(0,-2,1.05)),('rear',(-1.3,2,1))]:
 if '--front-only' in sys.argv and name!='front':continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports'/(h['SLUG']+'.glb')));bpy.context.view_layer.update()
 pts=[o.matrix_world@Vector(v) for o in bpy.context.scene.objects if o.type=='MESH' for v in o.bound_box]
 lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)));target=(lo+hi)*.5;size=max(hi-lo)
 h['studio']();bpy.data.objects['STUDIO_Floor'].location.z=-.43;s=bpy.context.scene;s.camera.location=target+Vector(direction)*size;s.camera.data.ortho_scale=size*1.65;h['point_at'](s.camera,target)
 s.camera.data.clip_end=10000;s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
