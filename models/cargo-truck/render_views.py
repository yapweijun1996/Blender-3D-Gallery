from pathlib import Path
import bpy,runpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
import sys
for name,direction in [('hero',(1.3,-2,1)),('front',(0,-3,.12)),('side',(3,0,.35)),('rear',(-1.3,2,1))]:
 if '--front-only' in sys.argv and name!='front':continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(HERE/'exports'/(h['SLUG']+'.glb')));bpy.context.view_layer.update()
 pts=[o.matrix_world@Vector(v) for o in bpy.context.scene.objects if o.type=='MESH' for v in o.bound_box]
 lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)));target=(lo+hi)*.5;size=max(hi-lo)
 h['studio']();s=bpy.context.scene;s.camera.location=target+Vector(direction)*size;s.camera.data.ortho_scale=size*1.65;h['point_at'](s.camera,target)
 bpy.context.view_layer.update();q=s.camera.matrix_world.to_quaternion();right=q@Vector((1,0,0));up=q@Vector((0,1,0));projections=[(v.dot(right),v.dot(up)) for v in pts];s.camera.data.ortho_scale=max(max(v[j] for v in projections)-min(v[j] for v in projections) for j in [0,1])*1.25
 scale=max(size/3,.5)
 for light_name,loc,power,area in [('Key',(-3,-4,6),800,4),('Fill',(4,-2,3),500,4),('Rear',(1,4,5),900,3)]:
  light=bpy.data.objects['STUDIO_'+light_name];light.location=target+Vector(loc)*scale;light.data.energy=power*scale*scale;light.data.size=area*scale;h['point_at'](light,target)
 s.camera.data.clip_end=10000;s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
