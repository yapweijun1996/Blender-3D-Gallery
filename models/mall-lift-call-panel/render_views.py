from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-lift-call-panel.blend'))
point_at=runpy.run_path(str(HERE/'generate.py'))['point_at'];s=bpy.context.scene
views=[('mall-lift-call-panel',(.34,-.7,.43),(0,-.01,.17),.43),('front',(0,-.8,.17),(0,0,.17),.4),('side',(.65,-.28,.28),(0,-.01,.17),.41),('rear',(-.3,.7,.4),(0,-.01,.17),.43),('buttons',(.08,-.5,.22),(0,-.031,.17),.225)]
for name,pos,target,scale in views:
    bpy.data.objects['STUDIO_Wall'].hide_render=name=='rear';s.camera.location=pos;s.camera.data.ortho_scale=scale;point_at(s.camera,target);s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
