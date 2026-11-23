"""Verify three separately editable vessels and authored pour contact in Blender."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

slug="ramadan-bazaar-air-balang-stall"
d=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(d/(slug+".blend")))
sc=bpy.context.scene
collections={c.name:len(c.objects) for c in sc.collection.children}
assert len(collections)==6
b=bpy.data.objects
assert b["Malay header"].data.body=="AIR BALANG"
assert len([o for o in b if o.name.startswith("Rounded transparent open-top vessel body")])==3
assert len([o for o in b if o.name.startswith("Individually tilted pale drink ice cube")])==12
tap=b["AIR_BALANG_TAP_LEVER"]
stream=b["AIR_BALANG_STREAM"]
fill=b["AIR_BALANG_CUP_FILL"]
raw=round
assert b["Featured amber lever paddle"].parent is tap
states={}
for frame in (0,30,54):
    sc.frame_set(frame)
    states[frame]=[raw(tap.rotation_euler.x,4),raw(stream.scale.z,4),raw(fill.scale.z,4)]
assert states=={0:[0,.001,.01],30:[.87,1,.57],54:[0,.001,.96]},states
sc.frame_set(0)
nozzle=b["Nozzle small black tip"];cup=b["Featured demonstration empty cup"]
assert abs(nozzle.location.x-stream.location.x)<1e-6
assert abs(nozzle.location.y-stream.location.y)<1e-6
assert abs(nozzle.location.z-.0065-stream.location.z)<.0006
assert abs(cup.location.x-fill.location.x)<1e-6 and abs(cup.location.y-fill.location.y)<1e-6
assert .001 < fill.location.z-cup.location.z < .016
assert fill.location.z+.095*.96 < cup.location.z+.132
assert abs(stream.location.z-.167-cup.location.z)<.01
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(d/"exports"/(slug+".glb")))
sc=bpy.context.scene
sc.frame_set(0)
names=["AIR_BALANG_TAP_LEVER","AIR_BALANG_STREAM","AIR_BALANG_CUP_FILL"]
assert all(bpy.data.objects[n].animation_data for n in names)
assert bpy.data.objects["Featured amber lever paddle"].parent is bpy.data.objects[names[0]]
meshes=[o for o in sc.objects if o.type=="MESH"]
world=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
lo=[min(p[i] for p in world) for i in range(3)]
hi=[max(p[i] for p in world) for i in range(3)]
dims=[hi[i]-lo[i] for i in range(3)]
assert 2.35<dims[0]<2.39 and 1.42<dims[1]<1.49 and 2.48<dims[2]<2.50,dims
assert abs(lo[2])<1e-6 and not [o for o in sc.objects if o.type in {"CAMERA","LIGHT"}]
print("REIMPORT",json.dumps({"groups":collections,"sizeBlenderXYZ":[round(x,4) for x in dims],"poses":states,
    "meshNodes":len(meshes),"physicalAlignment":True,"emptyCupAndFinalTopWithinRim":True}))
