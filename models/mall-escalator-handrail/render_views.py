"""Source-only studio views, including optional two-instance visual arrangement."""
from pathlib import Path
import bpy, runpy
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/mall-escalator-handrail.blend'))
helper=runpy.run_path(str(HERE/'generate.py')); point_at=helper['point_at']; END=helper['END']
s=bpy.context.scene;s.cycles.samples=64
views=[
 ('mall-escalator-handrail',(7,-12,6.4),(0,0,1.65),7.6),
 ('side',(0,-12,1.7),(0,0,1.7),7.6),
 ('reverse',(-6,12,5.2),(0,0,1.65),7.8),
 ('lower-return',(-END-1.8,-5,1.8),(-END-.05,0,.57),1.65),
 ('underside',(4,-7,-3),(0,0,1.7),7.8),
]
for name,position,target,scale in views:
    bpy.data.objects['STUDIO_Floor'].hide_render=name=='underside'
    s.camera.location=position;s.camera.data.ortho_scale=scale;point_at(s.camera,target)
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.data.objects['STUDIO_Floor'].hide_render=False
root=bpy.data.objects['ASSET_MallEscalatorHandrail'];root.location.y=-.64
for o in list(root.children_recursive):
    if o.type!='MESH':continue
    copy=o.copy();copy.data=o.data.copy();bpy.context.scene.collection.objects.link(copy)
    copy.parent=None;copy.location.y=.64
s.camera.location=(8,-12,7);s.camera.data.ortho_scale=8.0;point_at(s.camera,(0,0,1.7))
s.render.filepath=str(HERE/'previews/pair-context.png');bpy.ops.render.render(write_still=True)
