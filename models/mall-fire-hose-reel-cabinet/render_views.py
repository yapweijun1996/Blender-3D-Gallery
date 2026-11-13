from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-fire-hose-reel-cabinet.blend'))
api=runpy.run_path(str(HERE/'generate.py'));s=bpy.context.scene;root=bpy.data.objects[api['ROOT']]
views=[('mall-fire-hose-reel-cabinet',(2,-5,2),(-.22,-.32,.41),1.52,105),('closed',(2,-5,1.6),(0,-.1,.41),1.08,0),('front',(0,-5,.41),(-.13,-.1,.41),1.12,105),('side',(5,-3,2),(-.18,-.34,.41),1.5,105),('rear',(-3,5,2),(0,-.1,.41),1.1,0),('interior',(0,-5,.5),(-.025,-.1,.43),.88,105)]
for name,pos,target,scale,angle in views:
    root['door_angle_degrees']=angle;api['apply_pose'](root);s.camera.location=pos;s.camera.data.ortho_scale=scale;api['point_at'](s.camera,target);s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
