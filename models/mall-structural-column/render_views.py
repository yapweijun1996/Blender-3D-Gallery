"""Render imported shipped GLBs, not stand-in geometry. Context uses existing assets."""
from pathlib import Path
import bpy,runpy,json,sys
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))['h']
layouts=json.loads((HERE/'layouts.json').read_text())
def imported(file,position):
    bpy.ops.import_scene.gltf(filepath=str(file))
    root=next(o for o in bpy.context.selected_objects if o.name.startswith('ASSET_'))
    x,y,z=position;root.location=(x,-z,y)
    return root
for name,loc,scale,target in [
 ('mall-structural-column',(3,-6,3),3.65,(0,0,1.5)),
 ('front',(0,-6,2.2),3.5,(0,0,1.5)),
 ('rear',(-3,6,3),3.65,(0,0,1.5)),
 ('placement-grid',(5,-7,3.8),6.1,(0,0,1.4)),
 ('assembly-two-columns',(7,-9,4.7),9.2,(1.8,0,1.4))]:
    if '--' in sys.argv and name not in sys.argv[sys.argv.index('--')+1:]:continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    example=next((x for x in layouts['examples'] if x['name']==name),None)
    for position in example['columns'] if example else [[0,0,0]]:
        imported(HERE/'exports/mall-structural-column.glb',position)
    if example:
        for p in example['floors']:imported(HERE.parent/'mall-floor-tile/exports/mall-floor-tile-module.glb',p)
        for p in example['ceilings']:imported(HERE.parent/'mall-ceiling-panel/exports/mall-ceiling-panel-module.glb',p)
    h['studio']();s=bpy.context.scene;s.camera.location=loc;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,target)
    if example:bpy.data.objects['STUDIO_Floor'].location.z=-.061 # Below actual module bottoms, never coplanar with tile finish.
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
