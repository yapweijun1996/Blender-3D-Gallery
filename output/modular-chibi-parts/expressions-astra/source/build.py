"""Build the selectable facial expressions in Blender from the read-only base."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from face import *
from paint import make_maps
from regions import deformation,hair_distance,lid_relief

for name in ("textures","checks","renders",".work"):
    (ROOT/name).mkdir(exist_ok=True)
body=open_body()
xyz,_,_=triangles(body)
dist=hair_distance(xyz)
_,front_depth,_=project(body)
make_maps(body)
body.shape_key_add(name="Basis")
for name in NAMES[1:]:
    key=body.shape_key_add(name="expr_"+name,from_mix=False)
    key.value=0.0
    displacement=deformation(xyz,dist,name)
    displacement[:,1]+=lid_relief(xyz,front_depth,dist,name)
    key.data.foreach_set("co",np.ascontiguousarray(xyz+displacement,dtype=np.float32).ravel())
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
arm=body.find_armature()
body.parent=None
arm.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=str(ROOT/"body_expressions.glb"),use_selection=True,
    export_format="GLB",export_animations=False,export_morph=True,export_morph_normal=False,
    export_image_format="AUTO",export_def_bones=False)
