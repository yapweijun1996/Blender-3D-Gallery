from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-wayfinding-ceiling-sign.blend'));s=bpy.context.scene
for name,position,scale in [('mall-wayfinding-ceiling-sign',(1.2,-4,.35),2.55),('front',(0,-4,-.46),2.42),('rear',(0,4,-.46),2.42),('rear-angle',(-1.2,4,.35),2.55),('side',(3,-.8,.2),1.5),('mount',(1.2,-2,1.2),2.55)]:
 s.camera.location=position;s.camera.data.ortho_scale=scale;api['point_at'](s.camera,(0,0,-.47));s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
mat=api['material']('STUDIO ceiling',(195,203,204),0,.85);api['box']('STUDIO_CeilingContext',(0,0,.035),(3.1,1.2,.07),mat,None,.001)
s.camera.location=(1.1,-4,-1.45);s.camera.data.ortho_scale=3.55;api['point_at'](s.camera,(0,0,-.35));s.render.filepath=str(HERE/'previews/ceiling-context.png');bpy.ops.render.render(write_still=True)
