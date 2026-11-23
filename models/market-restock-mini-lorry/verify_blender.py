"""Verify source structure plus imported GLB wheel contact and open deck."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

p=Path(__file__).resolve().parent
slug="market-restock-mini-lorry"
bpy.ops.wm.open_mainfile(filepath=str(p/(slug+".blend")))
names = {c.name: len(c.objects) for c in bpy.context.scene.collection.children}
assert len(names) == 8, names
assert names["07 Reusable crate load and straps"] >= 180, names
assert names["05 Wheels and hubs"] == 36, names
assert sum(names.values()) >= 280, names
assert "08 Studio only" in names
assert bpy.data.objects["Right-hand steering rim"].location.x < 0, "vehicle right with -Y forward"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(p/"exports"/(slug+".glb")))
sc=bpy.context.scene
assert not [o.name for o in sc.objects if o.type in {"CAMERA","LIGHT"}]
assert not [o.name for o in sc.objects if o.animation_data]
meshes=[o for o in sc.objects if o.type=="MESH"]

def bounds(o):
    corners=[o.matrix_world @ Vector(v) for v in o.bound_box]
    return tuple(min(v[a] for v in corners) for a in range(3)), tuple(max(v[a] for v in corners) for a in range(3))
bb=[bounds(o) for o in meshes]
mn=[min(lo[i] for lo,_ in bb) for i in range(3)]
mx=[max(hi[i] for _,hi in bb) for i in range(3)]
dims=[mx[i]-mn[i] for i in range(3)]
assert 1.9<dims[0]<2.02 and 4.25<dims[1]<4.45 and 1.92<dims[2]<2.06, dims
assert abs(mn[2]) < 0.00001, mn

tyres={o.name.split(" | ")[0]:bounds(o) for o in meshes if " | Rubber tyres" in o.name and o.name.startswith(("Front","Rear"))}
assert set(tyres)=={"Front Left","Front Right","Rear Left","Rear Right"}, tyres
for k, (lo,hi) in tyres.items():
    x=-.702 if k.endswith("Right") else .702
    y=-1.23 if k.startswith("Front") else 1.05
    assert abs((lo[0]+hi[0])/2-x)<1e-5, (k,lo,hi)
    assert abs((lo[1]+hi[1])/2-y)<1e-5, (k,lo,hi)
    assert abs(lo[2])<1e-5 and abs(hi[2]-.604)<1e-5, (k,lo,hi)
crate=[o for o in meshes if o.name.startswith("Slatted crate ")]
assert len(crate)==6 and len({o.data.name for o in crate})==2
assert len({o.data.name for o in meshes if o.name.split(" | ")[0] in tyres and " | Rubber tyres" in o.name})==1

dep=bpy.context.evaluated_depsgraph_get()
deck=[]
for x,y in ((0,.37),(.47,1.58),(-.45,1.68)):
    hit,pos,_,_,obj,_=sc.ray_cast(dep,Vector((x,y,2.4)),Vector((0,0,-1)))
    assert hit and .77<pos.z<.80 and "Open dropside bed" in obj.name, (x,y,pos,obj)
    deck.append(round(pos.z,4))
print("REIMPORT",json.dumps({"sourceGroups":names,"meshNodes":len(meshes),"floor":round(mn[2],6),"sizeBlenderXYZ":[round(d,4) for d in dims],"distinctTyres":len(tyres),"linkedCrates":len(crate),"openCargoDeckHits":deck}))
