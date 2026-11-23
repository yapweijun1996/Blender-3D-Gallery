"""Check the authored road module, anchors and actual Blender GLB re-import."""
import json
from pathlib import Path
import sys
import bpy

args = sys.argv[sys.argv.index("--") + 1:]
glb = Path(args[0]).resolve()
assert Path(bpy.data.filepath).name == "mall-ride-hail-pickup-bay.blend"
anchors={
    "ANCHOR_PICKUP_B08": (-2.60,.146,1.855),
    "ANCHOR_VEHICLE_STOP": (0,-1.26,.177),
    "ANCHOR_BOARDING_POINT": (1.26,-.255,.177),
}

def check_anchors():
    for name, target in anchors.items():
        anchor=bpy.data.objects[name]
        assert anchor.type == "EMPTY"
        assert max(abs(a-b) for a,b in zip(anchor.matrix_world.translation,target)) < .001,name

check_anchors()
authored = list(bpy.context.scene.objects)
assert sum(o.name.startswith("Truncated tactile stud") for o in authored) == 39
assert sum(o.name.startswith("Folded standing seam canopy roof sheet") for o in authored) == 9
assert sum(o.name.startswith("Under-canopy continuous frosted lens") for o in authored) == 3
ramp_obj = bpy.data.objects["Continuous cast curb-cut ramp"]
ramp = [ramp_obj.matrix_world @ v.co for v in ramp_obj.data.vertices]
for i,target in enumerate(((.72,1.80),(-.135,.463),(.174,.302))):
    measured=(min(v[i] for v in ramp),max(v[i] for v in ramp))
    assert max(abs(a-b) for a,b in zip(measured,target))<.001,(i,measured)
bed_obj=bpy.data.objects["Inlaid darker single pickup berth"]
bed=[bed_obj.matrix_world @ v.co for v in bed_obj.data.vertices]
depth=max(v.y for v in bed)-min(v.y for v in bed)
assert abs(depth-2.04)<.001
assert max(v.z for v in bed) - anchors["ANCHOR_VEHICLE_STOP"][2] < .001
assert any(o.name.startswith("Connected rear downspout") for o in authored)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
check_anchors()
objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
world = [o.matrix_world @ vertex.co for o in objects for vertex in o.data.vertices]
lower = tuple(min(p[i] for p in world) for i in range(3))
upper = tuple(max(p[i] for p in world) for i in range(3))
dims = [round(hi-lo,6) for lo,hi in zip(lower,upper)]
assert len(objects)==34 and all(o.data.polygons for o in objects)
assert abs(lower[2])<.001
assert all(a<=x<=b for a,x,b in zip((6.24,4.28,2.65),dims,(6.31,4.37,2.71))),dims
assert not any(o.type in ("CAMERA","LIGHT") for o in bpy.context.scene.objects)
report={"meshes":len(objects),"blender":bpy.app.version_string,"bounds_m":[lower,upper],"dimensions_m":dims,
        "tactile_studs":39,"roof_sheets":9,"marked_depth_m":round(depth,3),
        "gltf_anchors":{k:[v[0],v[2],-v[1]] for k,v in anchors.items()}}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report,indent=2)+"\n")
