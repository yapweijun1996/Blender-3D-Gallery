from pathlib import Path
import bpy,importlib.util
from mathutils import Vector
p=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(p/'sources'/(p.name+'.blend')))
s=importlib.util.spec_from_file_location('gen',p/'generate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
bpy.context.scene.frame_set(30)
bpy.context.scene.camera.location=Vector(m.TARGET)+Vector((1.3,-2,1))*m.SCALE;m.aim(bpy.context.scene.camera,m.TARGET)
if p.name=='car-park-ticket-machine':
 bpy.context.scene.camera.location=Vector(m.TARGET)+Vector((1.3,2,1))*m.SCALE;m.aim(bpy.context.scene.camera,m.TARGET)
bpy.context.scene.render.filepath=str(p/'previews/open.png');bpy.ops.render.render(write_still=True)
