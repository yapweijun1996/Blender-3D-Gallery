from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-sprinkler-head.blend'));s=bpy.context.scene
views=[('mall-sprinkler-head',(.10,-.20,-.10),(0,0,-.017),.10),('front',(0,-.20,-.021),(0,0,-.017),.095),('side',(.20,0,-.025),(0,0,-.017),.095),('top',(.08,-.12,.15),(0,0,-.015),.10),('underside',(.06,-.10,-.20),(0,0,-.022),.09)]
for name,position,target,scale in views:
    s.camera.location=position;s.camera.data.ortho_scale=scale;api['point_at'](s.camera,target);s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
# Studio-only ceiling slab has a 30 mm diameter fitting clearance hole.
mat=api['material']('STUDIO matte ceiling',(206,213,211),0,.8)
ceiling=api['lathe']('STUDIO_CeilingContext',[(.015,0),(.18,0),(.18,.012),(.015,.012)],mat,None,64,False)
s.camera.location=(.11,-.19,-.11);s.camera.data.ortho_scale=.135;api['point_at'](s.camera,(0,0,-.023));s.render.filepath=str(HERE/'previews/ceiling-context.png');bpy.ops.render.render(write_still=True)
