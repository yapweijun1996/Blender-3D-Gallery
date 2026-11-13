from pathlib import Path
import bpy,sys
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'sources/mall-retail-pop-up-cart.blend'))
s=bpy.context.scene
for name,pos in [('mall-retail-pop-up-cart',(3,-5,3)),('front',(0,-5,1.4)),('rear',(3,5,2.8)),('side',(5,0,1.8))]:
 s.camera.location=pos;s.camera.rotation_euler=(Vector((0,0,1.02))-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(P/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
