from pathlib import Path
import bpy,runpy,sys
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-emergency-exit-door.blend'))
api=runpy.run_path(str(HERE/'generate.py'));s=bpy.context.scene;root=bpy.data.objects['ASSET_MallEmergencyExitDoor']
views=[('mall-emergency-exit-door',(3,-6,3),(0,-.03,1.08),2.7,0),('front',(0,-6,1.09),(0,0,1.09),2.55,0),('side',(5,-3,2.7),(0,0,1.08),2.65,0),('rear',(-3,6,3),(0,0,1.08),2.7,0),('open',(3,-6,3),(-.1,-.35,1.08),2.8,85),('hardware',(1,-3,2.7),(-.14,-.12,1.96),.8,0)]
for name,pos,target,scale,angle in views:
    if '--front-only' in sys.argv and name!='front':continue
    bpy.data.objects['STUDIO_Floor'].hide_render=name=='front'
    root['door_angle_degrees']=angle;api['apply_pose'](root);s.camera.location=pos;s.camera.data.ortho_scale=scale;api['point_at'](s.camera,target);s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
