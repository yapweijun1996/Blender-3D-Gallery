"""Verify authored returns layout and reimport the actual GLB for measured bounds."""
import bpy
import json
from pathlib import Path
import sys

args=sys.argv[sys.argv.index("--")+1:]
glb=Path(args[0]).resolve()
assert Path(bpy.data.filepath).name=="mall-returns-exchange-counter.blend"
authored=bpy.data.objects
for name in (
    "Overhanging customer document shelf", "Primary service sign", "Slim acrylic divider sheet",
    "Inspection tray anti-slip liner", "Blank kraft sample carton", "Brushed low scale weigh plate",
    "Scanner tilted green aperture", "Staff procedure drawer face",
):
    assert name in authored, name
assert sum(o.name.startswith("Raised inspection tray side-wall") for o in authored)==2
for label in ("INTAKE","CHECKED"):
    assert label+" open tote floor" in authored
    assert label+" low front tote face" in authored
    assert label+" taller rear tote wall" in authored
    assert sum(o.name.startswith(label+" independent tote side wall") for o in authored)==2
    assert authored[label+" physical tag"].data.body==label
assert authored["INTAKE open tote floor"].location.x+.4 < authored["CHECKED open tote floor"].location.x
assert authored["Overhanging customer document shelf"].location.z > authored["Inspection worktop mass"].location.z + .1
assert not any(o.animation_data for o in authored)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
obs=[o for o in bpy.context.scene.objects if o.type=="MESH"]
loc=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
low=[min(v[i] for v in loc) for i in range(3)]
high=[max(v[i] for v in loc) for i in range(3)]
dims=[round(b-a,6) for a,b in zip(low,high)]
assert len(obs)==36 and all(o.data.polygons for o in obs)
assert abs(low[2])<.001
assert all(a<=x<=b for a,x,b in zip((2.30,.77,1.47),dims,(2.51,.99,1.66))),dims
assert not any(o.type in ("CAMERA","LIGHT") or o.animation_data for o in bpy.context.scene.objects)
alpha=bpy.data.materials["Neutral transparent acrylic divider"].node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value
assert abs(alpha-.100)<.001
report={"blender":bpy.app.version_string,"mesh_count":len(obs),"bounds_m":[low,high],"dimensions_m":dims,
        "return_bins":2,"acrylic_alpha":round(alpha,4)}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report,indent=2)+"\n")
