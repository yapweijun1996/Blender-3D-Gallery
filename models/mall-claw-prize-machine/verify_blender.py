"""Verify editable assembly and real exported geometry using Blender."""
import json
from pathlib import Path
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
glb = Path(args[0]).resolve()
assert Path(bpy.data.filepath).name == "mall-claw-prize-machine.blend"
authored = bpy.data.objects
for n in range(1,4):
    finger = f"Finger {n} "
    for part in ("fixed socket", "stamped upper link", "angled lower link",
                 "rounded inward tip", "rubber gripping pad", "actuation strut",
                 "exposed pivot pin 0", "exposed pivot pin 1"):
        assert finger + part in authored, (finger, part)
for landmark in ("Moving trolley housing", "Suspended cable braid", "Front acrylic viewing door",
                 "Prize chute padded floor", "Static inward swung bump flap", "Joystick sphere"):
    assert landmark in authored, landmark
assert sum(o.name.endswith(" body") for o in bpy.data.collections["05 Original toy sculptures"].objects) == 6

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
world = [o.matrix_world @ vertex.co for o in objects for vertex in o.data.vertices]
lower = tuple(min(p[i] for p in world) for i in range(3))
upper = tuple(max(p[i] for p in world) for i in range(3))
dims = [round(hi-lo, 6) for lo, hi in zip(lower, upper)]
assert len(objects) == 46 and all(o.data.polygons for o in objects)
assert abs(lower[2]) < .001
assert all(a <= x <= b for a, x, b in zip((1.22,1.03,2.10),dims,(1.26,1.24,2.12))),dims
for group in ("Shell and service hardware", "Glazing and light bars", "X-Y gantry and cable reel",
              "Claw links and pivot hardware", "Original toy sculptures", "Joystick and buttons",
              "Prize drop and collection tunnel"):
    assert any(group in o.name for o in objects), group
assert not any(o.type in ("CAMERA", "LIGHT") for o in bpy.context.scene.objects)
glass = bpy.data.materials["Anti-reflective clear acrylic"]
alpha = glass.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value
assert .045 < alpha < .060, alpha
report = {"meshes":len(objects),"blender":bpy.app.version_string,"bounds_m":[lower,upper],
          "dimensions_m":dims,"acrylic_alpha":round(alpha,5),"editable_fingers":3,"original_toys":6}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report, indent=2)+"\n")
