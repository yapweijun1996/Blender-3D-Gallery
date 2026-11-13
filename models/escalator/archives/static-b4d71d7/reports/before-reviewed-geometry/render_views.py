"""Render four source-faithful inspection views; run inside Blender."""
import bpy, os
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent; out=Path(os.environ.get('MALL_QA_DIR',HERE/'previews'))/'views'; out.mkdir(parents=True,exist_ok=True)
root=bpy.data.objects['ASSET_EscalatorV1_ID004']; bpy.ops.object.select_all(action='DESELECT'); root.select_set(True)
for o in root.children_recursive:o.select_set(True)
for i,(loc,target) in enumerate([((6,-8,5),(0,0,1.5)),((-6,-5,3),(0,0,1.4)),((0,8,4),(0,0,1.5)),((0,-.5,8),(0,0,1.4))],1):
 bpy.ops.object.camera_add(location=loc); cam=bpy.context.object; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); bpy.context.scene.camera=cam; bpy.context.scene.render.filepath=str(out/f'view-{i}.png'); bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam,do_unlink=True)
