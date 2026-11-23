"""Verify authoring pose and imported footprint on a clean Blender re-open."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

slug="mall-carpark-help-point"
d=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(d/(slug+".blend")))
sc=bpy.context.scene
groups={c.name:len(c.objects) for c in sc.collection.children}
assert len(groups)==5 and groups["04 Moving demo button and acknowledgment lens"]==4
assert bpy.data.objects["Malay header"].data.body=="BANTUAN"
assert bpy.data.objects["English header"].data.body=="HELP POINT"
assert bpy.data.objects["Fictional demo small marker"].data.body=="CONTOH / DEMO"
b=bpy.data.objects["CARPARK_HELP_BUTTON"]
i=bpy.data.objects["CARPARK_HELP_INDICATOR"]
assert bpy.data.objects["Malay key print"].parent is b
assert bpy.data.objects["English key print"].parent is b
samples={}
for frame in (0,14,36):
    sc.frame_set(frame)
    samples[frame]=[round(b.location.y,5),round(i.location.y,5)]
assert samples=={0:[-.223,-.171],14:[-.211,-.171],36:[-.223,-.197]},samples

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(d/"exports"/(slug+".glb")))
sc=bpy.context.scene
sc.frame_set(0)
meshes=[o for o in sc.objects if o.type=="MESH"]
p=[o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo=[min(v[a] for v in p) for a in range(3)]
hi=[max(v[a] for v in p) for a in range(3)]
dims=[hi[a]-lo[a] for a in range(3)]
assert abs(lo[2])<1e-6 and .92<dims[0]<.94 and .62<dims[1]<.64 and 1.28<dims[2]<1.32,dims
assert not any(o.type in {"LIGHT","CAMERA"} for o in sc.objects)
for nm in ("CARPARK_HELP_BUTTON","CARPARK_HELP_INDICATOR"):
    assert bpy.data.objects[nm].animation_data
assert {c.name for c in bpy.data.objects["CARPARK_HELP_BUTTON"].children}=={"Malay key print","English key print"}
print("REIMPORT",json.dumps({"groups":groups,"dimensionsBlenderXYZ":[round(v,5) for v in dims],"buttonAndIndicatorY":samples,"glbMeshes":len(meshes)}))
