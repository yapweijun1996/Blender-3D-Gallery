"""Re-import exact model, verifying a metric scale and openings in the actual grate."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

id="monsoon-underpass-depth-marker"
d=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(d/(id+".blend")))
groups={c.name:len(c.objects) for c in bpy.context.scene.collection.children}
assert len(groups)==5,groups
b=bpy.data.objects
assert b["Malay heading"].data.body=="ARAS AIR"
assert b["English heading"].data.body=="WATER DEPTH"
assert b["Units centimetres"].data.body=="CM"
numbers=[]
road=.090
for cm in (20,40,60,80,100):
    tick=b[f"Scale tick {cm:03} cm"]
    n=b[f"Measured depth label {cm:03} cm"]
    assert n.data.body==str(cm) and abs(tick.location.z-n.location.z)<1e-6
    assert abs(tick.location.z-road-cm/100)<1e-6
    assert n.location.y<b["Exchangeable slim scale liner"].location.y-.007
    numbers.append([cm,round(tick.location.z,3)])
bars=[o for o in b if o.name.startswith("Open grate cast round-edged crossbar")]
assert len(bars)==10

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(d/"exports"/(id+".glb")))
scene=bpy.context.scene
vv=[o.matrix_world@Vector(v) for o in scene.objects if o.type=="MESH" for v in o.bound_box]
lo=[min(v[i] for v in vv) for i in range(3)]
hi=[max(v[i] for v in vv) for i in range(3)]
dims=[hi[i]-lo[i] for i in range(3)]
assert 2.37<dims[0]<2.39 and 1.62<dims[1]<1.65 and 1.34<dims[2]<1.36,dims
assert abs(lo[2])<1e-6 and not any(o.type in {"LIGHT","CAMERA"} or o.animation_data for o in scene.objects)
dpg=bpy.context.evaluated_depsgraph_get()
def down(x,y):
    ok,xyz,_,_,o,_=scene.ray_cast(dpg,Vector((x,y,1.7)),Vector((0,0,-1)))
    assert ok
    return round(xyz.z,4),o.name
x=-.806
hitBars=[down(x+n*.066,-.0735) for n in range(10)]
hitOpen=[down(x+.033+n*.066,-.0735) for n in range(9)]
assert all(abs(hit[0]-.096)<.0005 and hit[1].startswith("Open recessed drain") for hit in hitBars),hitBars
assert all(.04<h[0]<.045 and "Pitch inside" in h[1] for h in hitOpen),hitOpen
print("REIMPORT",json.dumps({"groups":groups,"metricLabelsAndBlenderZ":numbers,
    "boundsBlenderXYZ":[round(a,5) for a in dims],"barFaceHeight":hitBars[0][0],"openSlotFloorDepth":round(hitBars[0][0]-hitOpen[0][0],5),
    "crossbars":len(hitBars),"realHoles":len(hitOpen),"threshold":None}))
