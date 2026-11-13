from pathlib import Path
import bpy,runpy,math
HERE=Path(__file__).resolve().parent;api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-cctv-camera.blend'));s=bpy.context.scene
views=[('mall-cctv-camera',(.25,-.42,-.20),(0,0,-.073),.22),('front',(0,-.42,-.13),(0,0,-.073),.21),('side',(.42,0,-.11),(0,0,-.073),.21),('mount',(.20,-.22,.30),(0,0,-.07),.22),('underside',(.16,-.25,-.38),(0,0,-.08),.22)]
for name,position,target,scale in views:
    s.camera.location=position;s.camera.data.ortho_scale=scale;api['point_at'](s.camera,target);s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
pan=bpy.data.objects['PIVOT_Pan'];tilt=bpy.data.objects['PIVOT_Tilt'];pan.rotation_euler.z=math.radians(40);tilt.rotation_euler.x=math.radians(45)
s.camera.location=(.25,-.42,-.20);s.camera.data.ortho_scale=.22;api['point_at'](s.camera,(0,0,-.073));s.render.filepath=str(HERE/'previews/pose.png');bpy.ops.render.render(write_still=True)
pan.rotation_euler.z=0;tilt.rotation_euler.x=math.radians(20)
mat=api['material']('STUDIO ceiling slab',(206,213,211),0,.8)
api['box']('STUDIO_CeilingContext',(0,0,.012),(.44,.40,.024),mat,None)
s.camera.location=(.25,-.42,-.23);s.camera.data.ortho_scale=.29;api['point_at'](s.camera,(0,0,-.066));s.render.filepath=str(HERE/'previews/ceiling-context.png');bpy.ops.render.render(write_still=True)
