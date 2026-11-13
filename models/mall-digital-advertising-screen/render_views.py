from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-digital-advertising-screen.blend'));s=bpy.context.scene
for name,position,scale in [('mall-digital-advertising-screen',(.85,-3,.55),1.58),('front',(0,-3,0),1.49),('side',(2,-.4,.2),1.20),('rear',(-.85,3,.55),1.58),('mount',(1.2,2,.9),1.58)]:
    s.camera.location=position;s.camera.data.ortho_scale=scale;api['point_at'](s.camera,(0,-.04,0));s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
mat=api['material']('STUDIO wall',(176,185,187),0,.8)
api['box']('STUDIO_WallContext',(0,.015,0),(2,.03,1.3),mat,None)
s.camera.location=(.85,-3,.55);s.camera.data.ortho_scale=2.25;api['point_at'](s.camera,(0,-.04,0));s.render.filepath=str(HERE/'previews/wall-context.png');bpy.ops.render.render(write_still=True)
