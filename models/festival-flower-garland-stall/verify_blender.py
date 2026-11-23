"""Verify source design, six alternating stock strands and exported bounds."""
import bpy
import json
from pathlib import Path
import sys

args=sys.argv[sys.argv.index("--")+1:]
glb=Path(args[0]).resolve()
assert Path(bpy.data.filepath).name=="festival-flower-garland-stall.blend"
authored=bpy.data.objects
pale=sorted(o.name for o in authored if o.name.startswith("Ivory jasmine-like retail garland"))
warm=sorted(o.name for o in authored if o.name.startswith("Ochre marigold-like retail garland"))
assert [x[-1] for x in pale]==list("135")
assert [x[-1] for x in warm]==list("246")
for name in pale+warm:
    assert len(authored[name].data.polygons)>400,name
for prefix,n in (("Over-rail garland stock hanger",12),("Reusable cotton garland loop",6),
                 ("Tensioned awning cloth panel",8),("Rolled spool thread band",3),
                 ("Loose leaf backing blade",7)):
    assert sum(o.name.startswith(prefix) for o in authored)==n,prefix
for name in ("Pale oak worktop and sales ledge","Customer-visible front garland rail",
             "Low open garland wrapping tray base","Perforation-free square leaf and supply tray base",
             "Basket low structural board","Two folded retail specimen strands in wrapping tray"):
    assert name in authored,name
assert not any(o.animation_data for o in authored)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
objects=[o for o in bpy.context.scene.objects if o.type=="MESH"]
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
lo=[min(v[i] for v in points) for i in range(3)]
hi=[max(v[i] for v in points) for i in range(3)]
dims=[round(b-a,6) for a,b in zip(lo,hi)]
assert all(o.data.polygons for o in objects)
assert abs(lo[2])<.001
assert all(a<=x<=b for a,x,b in zip((2.09,.89,2.10),dims,(2.18,.99,2.15))),dims
assert not any(o.type in ("CAMERA","LIGHT") or o.animation_data for o in bpy.context.scene.objects)
for name in pale+warm:
    assert name in bpy.data.objects,name
report={"blender":bpy.app.version_string,"mesh_count":len(objects),"bounds_m":[lo,hi],"dimensions_m":dims,
        "pale_garlands":len(pale),"warm_garlands":len(warm),"reusable_hangers":12,"thread_spools":3}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report,indent=2)+"\n")
