from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-lift-floor-indicator.blend'))
point_at=runpy.run_path(str(HERE/'generate.py'))['point_at'];s=bpy.context.scene
views=[('mall-lift-floor-indicator',(.38,-.85,.29),(0,-.01,.08),.51),('front',(0,-.8,.08),(0,0,.08),.49),('side',(.65,-.28,.22),(0,-.01,.08),.49),('rear',(-.3,.7,.22),(0,-.01,.08),.51),('digits',(.03,-.6,.1),(.02,-.026,.08),.33)]
for name,pos,target,scale in views:
    bpy.data.objects['STUDIO_Wall'].hide_render=name=='rear';s.camera.location=pos;s.camera.data.ortho_scale=scale;point_at(s.camera,target);s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
