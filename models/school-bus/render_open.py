from pathlib import Path
import bpy,hashlib,importlib.util
from mathutils import Vector
p=Path(__file__).resolve().parent;source=p/'sources'/(p.name+'.blend');before=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(30)
s=importlib.util.spec_from_file_location('asset_generator',p/'generate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
scene=bpy.context.scene;scene.camera.data.ortho_scale=m.SCALE*1.25
for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
 scene.camera.location=Vector(m.TARGET)+Vector(delta)*m.SCALE*1.25;m.aim(scene.camera,m.TARGET);scene.render.filepath=str(p/'previews'/('open-'+name+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('OPEN_POSE_SOURCE_UNCHANGED',before)
