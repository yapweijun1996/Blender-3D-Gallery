"""Independently import the GLB into Blender and verify geometry and sale-neutral materials."""
from pathlib import Path
import json
import sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
item = Path(args[0]).resolve()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(item))
objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
world = [o.matrix_world @ Vector(p) for o in objects for p in o.bound_box]
lower = tuple(min(p[i] for p in world) for i in range(3))
upper = tuple(max(p[i] for p in world) for i in range(3))
dimensions = [round(hi-lo, 6) for lo, hi in zip(lower, upper)]
assert len(objects) == 41 and all(o.data.polygons for o in objects)
assert abs(lower[2]) < 0.001
assert all(a <= x <= b for a, x, b in zip((1.24,.82,2.02),dimensions,(1.30,.98,2.10)))
for group in ("Cabinet", "Product window", "Unbranded products", "Selection panel", "Recessed pickup"):
    assert any(group in o.name for o in objects), group
assert not any(o.type in ("CAMERA", "LIGHT") for o in bpy.context.scene.objects)
glass = bpy.data.materials["Clear protective glazing"]
alpha = glass.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value
assert .04 < alpha < .14, alpha
report={"meshes":len(objects),"blender":bpy.app.version_string,"bounds_m":[lower,upper],"dimensions_m":dimensions,"glass_alpha":round(alpha,5)}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report,indent=2)+"\n")
