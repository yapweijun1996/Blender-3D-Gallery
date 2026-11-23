"""Verify actual source and clean reimport, including open slots and tray pitch."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

root=Path(__file__).resolve().parent
slug="mall-wet-umbrella-drip-station"
bpy.ops.wm.open_mainfile(filepath=str(root/(slug+".blend")))
cols={c.name:len(c.objects) for c in bpy.context.scene.collection.children}
assert len(cols)==6,cols
assert cols["04 Sculpted wet umbrellas"]>26
assert bpy.data.objects["Malay primary guidance"].data.body=="PAYUNG BASAH"
assert bpy.data.objects["English secondary guidance"].data.body=="WET UMBRELLAS"
handles=[o.name for o in bpy.data.objects if o.name.endswith((" cane J grip"," compact grip"))]
assert len(handles)==5 and sum(n.endswith(" cane J grip") for n in handles)==3
assert bpy.data.objects["Continuous pitched drip pan bottom"].rotation_euler.x>.035
assert bpy.data.objects.get("Removable-looking drip drawer pull")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root/"exports"/(slug+".glb")))
sc=bpy.context.scene
meshes=[o for o in sc.objects if o.type=="MESH"]
vs=[o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
lo=[min(v[i] for v in vs) for i in range(3)]
hi=[max(v[i] for v in vs) for i in range(3)]
dims=[hi[i]-lo[i] for i in range(3)]
assert abs(lo[2])<1e-6 and .89<dims[0]<.94 and .49<dims[1]<.55 and 1.12<dims[2]<1.15,(lo,hi,dims)
assert not any(o.type in {"LIGHT","CAMERA"} or o.animation_data for o in sc.objects)
for prefix in ("Open rounded long guide ","Open rounded compact guide ","Slatted tip cradle "):
    group=[o for o in meshes if o.name.startswith(prefix)]
    assert len(group)==4,(prefix,group)
    assert len({o.data for o in group})==1,(prefix,"not instanced")
    slotxs=[]
    for o in group:
        corners=[o.matrix_world @ Vector(v) for v in o.bound_box]
        slotxs.append(round((min(v.x for v in corners)+max(v.x for v in corners))/2,3))
    assert sorted(slotxs)==[-.322,-.108,.108,.322],(prefix,slotxs)
# An empty long slot passes a vertical ray down to the pan. The empty compact
# slot also stays open, but its separate spaced cradle bars support short tips.
bpy.context.view_layer.update()
dp=bpy.context.evaluated_depsgraph_get()
def hit(x,y,height=1.65):
    ok,p,_,_,obj,_=sc.ray_cast(dp,Vector((x,y,height)),Vector((0,0,-1)))
    assert ok
    return (round(p.z,5),obj.name)
lp=hit(.108,.097)
cp=hit(-.322-.020,-.132)
front=hit(.04,-.113,.25)
rear=hit(.04,.121,.25)
assert .123<lp[0]<.15 and lp[1].startswith("Liftable drip pan"),lp
assert .31 < cp[0] < .34 and cp[1].startswith("Long and compact umbrella"),cp
assert rear[0]>front[0]+.007 and .11<front[0]<.145 and .12<rear[0]<.16,(front,rear)
print("REIMPORT",json.dumps({"sourceGroups":cols,"standsGrounded":round(lo[2],6),"boundsBlenderXYZ":[round(d,4) for d in dims],
                  "umbrellas":len(handles),"emptyLongSlotPanHit":lp,"compactSlotCradleHit":cp,"drainPitchHeightDelta":round(rear[0]-front[0],5)}))
