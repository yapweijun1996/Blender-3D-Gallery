"""Check named cycle repair hardware and measure the reimported vertex bounds."""
import bpy
import json
from pathlib import Path
import sys

args=sys.argv[sys.argv.index("--")+1:]
glb=Path(args[0]).resolve()
assert Path(bpy.data.filepath).name=="park-connector-bicycle-repair-stand.blend"
authored=bpy.data.objects
for name in ("Captive open-ended wrench with jaw relief","Captive L-shaped hex tool",
             "Captive screwdriver thick handle","Captive wedge tyre lever",
             "Exposed plunger rod","Ivory unnumbered gauge face","Continuous reinforced pump hose",
             "Dock for captive air nozzle","Chamfered reusable granite footprint"):
    assert name in authored,name
for prefix,n in (("Captured orange-coated hanging tether",4),("Captive crimp collar",4),
                 ("Upturned bicycle support cantilever",2),("Replaceable soft contact cradle",2),
                 ("Bicycle pictogram open wheel",2),("Readout engraved radial tick",9)):
    assert sum(o.name.startswith(prefix) for o in authored)==n,prefix
assert not any(o.animation_data for o in authored)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
objects=[o for o in bpy.context.scene.objects if o.type=="MESH"]
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
lo=[min(v[i] for v in points) for i in range(3)]
hi=[max(v[i] for v in points) for i in range(3)]
dims=[round(b-a,6) for a,b in zip(lo,hi)]
assert len(objects)==27 and all(o.data.polygons for o in objects)
assert abs(lo[2])<.001
assert all(a<=x<=b for a,x,b in zip((1.08,.68,1.53),dims,(1.16,.86,1.59))),dims
assert not any(o.type in ("CAMERA","LIGHT") or o.animation_data for o in bpy.context.scene.objects)
alpha=bpy.data.materials["Dial translucent protective lens"].node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value
assert abs(alpha-.075)<.001,alpha
report={"blender":bpy.app.version_string,"mesh_count":len(objects),"bounds_m":[lo,hi],"dimensions_m":dims,
        "padded_arms":2,"captive_tool_count":4,"dial_alpha":round(alpha,4)}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report,indent=2)+"\n")
