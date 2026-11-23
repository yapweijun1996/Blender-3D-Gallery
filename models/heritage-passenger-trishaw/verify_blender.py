"""Independently verify editable trishaw parts and final exported geometry."""
import json
from pathlib import Path
import sys
import bpy

args = sys.argv[sys.argv.index("--") + 1:]
glb = Path(args[0]).resolve()
assert Path(bpy.data.filepath).name == "heritage-passenger-trishaw.blend"
authored = bpy.data.objects
front=authored["Front bicycle wheel barrel hub"]
rear=authored["Rear bicycle wheel barrel hub"]
side=authored["Outboard passenger wheel barrel hub"]
assert abs(front.location.x-rear.location.x) < .001
assert front.location.y < rear.location.y-1.3
assert side.location.x < rear.location.x-1.2
assert sum("cross-laced spoke" in o.name for o in bpy.data.collections["03 Three spoked wheels"].objects) == 72
assert sum(o.name.startswith("Curved fork blade") for o in authored) == 2
for landmark in ("Closed roller-chain core","Rim brake caliper arm","Crank chainring backing plate",
                 "Rear freewheel sprocket backing plate","Outboard sidecar axle bridge",
                 "Bench seat cushion thick roll","Rolled front external footrest step",
                 "Stretched canvas roof stripe","Three continuous bowed canopy ribs"):
    assert landmark in authored, landmark

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
world = [o.matrix_world @ vertex.co for o in objects for vertex in o.data.vertices]
lower = tuple(min(p[i] for p in world) for i in range(3))
upper = tuple(max(p[i] for p in world) for i in range(3))
dims = [round(hi-lo, 6) for lo, hi in zip(lower, upper)]
assert all(o.data.polygons for o in objects)
assert abs(lower[2]) < .015,lower
assert all(a <= x <= b for a, x, b in zip((1.60,2.10,1.76),dims,(1.86,2.29,1.83))),dims
for group in ("Cycle frame and rear dropouts","Fork and steering controls","Three spoked wheels",
              "Crank chain and brakes","Passenger sidecar and step","Seat and stitched upholstery",
              "Canvas canopy and support hoops","Trim and equipment"):
    assert any(group in o.name for o in objects), group
assert not any(o.type in ("CAMERA", "LIGHT") for o in bpy.context.scene.objects)
report = {"meshes":len(objects),"blender":bpy.app.version_string,"bounds_m":[lower,upper],"dimensions_m":dims,
          "editable_wheels":3,"editable_spokes":72}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report,indent=2)+"\n")
