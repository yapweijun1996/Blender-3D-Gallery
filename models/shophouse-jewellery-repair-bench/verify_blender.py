"""Verify useful authored bench geometry and a clean static Blender reimport."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

slug="shophouse-jewellery-repair-bench"
d=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(d/(slug+".blend")))
sc=bpy.context.scene
g={c.name:len(c.objects) for c in sc.collection.children}
assert len(g)==6,g
ob=bpy.data.objects
assert ob["Generic Malay repair heading first line"].data.body=="BAIK PULIH"
assert ob["Generic Malay jewellery heading"].data.body=="BARANG KEMAS"
assert ob["Generic English service"].data.body=="JEWELLERY REPAIR"
assert len([x for x in ob if x.name.startswith("Represented articulated hinge pivot")])==3
def bounds(o):
  v=[o.matrix_world@Vector(c) for c in o.bound_box]
  return [[min(p[a] for p in v) for a in range(3)],[max(p[a] for p in v) for a in range(3)]]
lengths=[]
for n,parent_length in (("Long tapered ring mandrel with plain shaft",.249),("Short tapered ring-forming mandrel",.190)):
    lo,hi=bounds(ob[n])
    assert abs(hi[0]-lo[0]-parent_length)<1e-5
    lengths.append(round(hi[0]-lo[0],4))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(d/"exports"/(slug+".glb")))
sc=bpy.context.scene;gltf=[o for o in sc.objects if o.type=="MESH"]
bb=[bounds(o) for o in gltf]
lo=[min(v[0][a] for v in bb) for a in range(3)]
hi=[max(v[1][a] for v in bb) for a in range(3)]
dim=[round(hi[a]-lo[a],5) for a in range(3)]
assert abs(lo[2])<1e-6 and 1.43<dim[0]<1.45 and .91<dim[1]<1.0 and 1.48<dim[2]<1.53,dim
assert not any(o.type in {"LIGHT","CAMERA"} or o.animation_data for o in sc.objects)
dep=bpy.context.evaluated_depsgraph_get()
def down(x,y):
    ok,v,_,_,o,_=sc.ray_cast(dep,Vector((x,y,1.8)),Vector((0,0,-1)))
    assert ok
    return [round(v.z,5),o.name]
slot=down(0,-.392)
assert .745<slot[0]<.754 and "Charcoal felt" in slot[1],slot
for x in (-.079,.079):
    side=down(x,-.386)
    assert .943<side[0]<.948 and "Honey ash bench-pin" in side[1],side
tray=down(.173,-.459)
assert .745<tray[0]<.754 and "Charcoal felt" in tray[1],tray
dedicated_top=down(-.418,-.324)
assert .950<dedicated_top[0]<.954 and "Used warm walnut" in dedicated_top[1],dedicated_top
print("REIMPORT",json.dumps({"groups":g,"boundsBlenderXYZ":dim,"mandrelLengthsM":lengths,
 "notchRayHitsLowerTray":slot,"openTrayRay":tray,"independentHinges":3,"static":True,"meshNodes":len(gltf)}))
