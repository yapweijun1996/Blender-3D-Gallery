from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent;api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-food-court-tray-station.blend'));s=bpy.context.scene
views=[('mall-food-court-tray-station',(2,-4,2.5),2.15,(0,0,.76)),('front',(0,-4,1.15),2.05,(0,0,.75)),('rear',(-2,4,2.3),2.15,(0,0,.75)),('side',(4,-.8,1.6),1.95,(0,0,.75)),('interior',(.4,-3,1.05),1.57,(0,0,.47))]
for name,position,scale,target in views:
 s.camera.location=position;s.camera.data.ortho_scale=scale;api['point_at'](s.camera,target);s.render.filepath=str(HERE/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
# Source-only tray-removal pose. Straight pull toward -Y; no runtime interaction.
for o in bpy.data.collections['Tray04'].objects:o.location.y-=.62
s.camera.location=(1.6,-3,1.9);s.camera.data.ortho_scale=2.35;api['point_at'](s.camera,(0,-.10,.74));s.render.filepath=str(HERE/'previews/tray-removal.png');bpy.ops.render.render(write_still=True)
