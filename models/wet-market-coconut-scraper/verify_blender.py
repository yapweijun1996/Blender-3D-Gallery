"""Verify real crank/bowl clearance and ratio on editable source and a clean GLB import."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

id="wet-market-coconut-scraper"
d=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(d/(id+".blend")))
scene=bpy.context.scene
groups={c.name:len(c.objects) for c in scene.collection.children}
assert len(groups)==6
b=bpy.data.objects
assert b["Malay primary equipment label"].data.body=="KUKUR KELAPA"
a,c=b["KELAPA_CRANK_HANDLE"],b["KELAPA_SCRAPER_ROTOR"]
assert abs((c.location.z-a.location.z)-.138)<1e-6
assert abs(a.location.y-c.location.y)<1e-6
grip=b["Large amber hand-crank fiducial grip"]
cap=b["Small silver end cap on knob"]
spot=b["Amber rotor fiducial dot"]
bowl=b["Empty satin bowl with true open concave interior"]
assert grip.parent is a and cap.parent is a and spot.parent is c
assert len([o for o in b if o.name.startswith("Open brown coconut half shell")])==2
def vx(o):
    return [(o.matrix_world@Vector(p)).x for p in o.bound_box]
space=[]
angles={}
old=bowl.matrix_world.copy()
for frame in range(49):
    scene.frame_set(frame)
    space.append(min(vx(bowl))-max(vx(grip)+vx(cap)))
    assert bowl.matrix_world==old
    assert abs(c.rotation_euler.x+a.rotation_euler.x*2)<1e-5
    if frame in (0,23,48):
        angles[frame]=[round(math.degrees(a.rotation_euler.x),4),round(math.degrees(c.rotation_euler.x),4)]
assert angles=={0:[0,0],23:[121.5,-243],48:[270,-540]},angles
assert min(space)>.009,min(space)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(d/"exports"/(id+".glb")))
s=bpy.context.scene;s.frame_set(0)
meshes=[o for o in s.objects if o.type=="MESH"]
p=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
lo=[min(v[j] for v in p) for j in range(3)]
hi=[max(v[j] for v in p) for j in range(3)]
dim=[round(hi[j]-lo[j],5) for j in range(3)]
assert abs(lo[2])<1e-6 and 1.26<dim[0]<1.29 and .79<dim[1]<.81 and abs(dim[2]-.50129)<.00002,dim
assert not [o for o in s.objects if o.type in {"CAMERA","LIGHT"}]
for n in ("KELAPA_CRANK_HANDLE","KELAPA_SCRAPER_ROTOR"):
    assert bpy.data.objects[n].animation_data and len(bpy.data.objects[n].children)>2
print("REIMPORT",json.dumps({"groups":groups,"sizeBlenderXYZ":dim,"degrees":angles,"fixedAxleSpacingMetres":.138,
 "crankToBowlClearanceMetres":round(min(space),5),"meshNodes":len(meshes)}))
