"""Render real exported GLB, including joined copies with duplicate posts removed."""
from pathlib import Path
import bpy,runpy,json,math
HERE=Path(__file__).resolve().parent;h=runpy.run_path(str(HERE/'generate.py'))
layouts=json.loads((HERE/'layouts.json').read_text())
def imported():
    bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/mall-glass-partition.glb'))
    return next(o for o in bpy.context.selected_objects if o.name.startswith('ASSET_'))
for name,location,scale,target in [('mall-glass-partition',(2.6,-6,3),3,(0,0,1.2)),('front',(0,-6,1.55),2.8,(0,0,1.2)),('rear',(-2.6,6,3),3,(0,0,1.2)),('straight-three-bay',(4,-7,3.5),4.5,(1.14,0,1.2)),('corner-three-bay',(4.6,-6.5,4),3.9,(.85,-.45,1.2))]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    example=next((e for e in layouts['examples'] if e['name']==name),None)
    for i,bay in enumerate(example['bays'] if example else [{'position':[0,0,0],'rotationY':0,'remove_left_post':False}]):
        root=imported()
        if bay['remove_left_post']:
            post=next(o for o in root.children_recursive if o.name.startswith('POST_Left'));bpy.data.objects.remove(post,do_unlink=True)
        x,y,z=bay['position'];root.location=(x,-z,y);root.rotation_mode='XYZ';root.rotation_euler.z=bay['rotationY']
        # glTF +Y rotation and Blender +Z rotation share the same sign.
    h['studio']();s=bpy.context.scene;s.camera.location=location;s.camera.data.ortho_scale=scale;h['point_at'](s.camera,target)
    s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
