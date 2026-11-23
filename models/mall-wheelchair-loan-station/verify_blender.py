"""Check the separate editable dock and narrow folded geometry after export."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

d=Path(__file__).resolve().parent
slug="mall-wheelchair-loan-station"
bpy.ops.wm.open_mainfile(filepath=str(d/(slug+".blend")))
groups={c.name:len(c.objects) for c in bpy.context.scene.collection.children}
assert len(groups)==7 and groups["05 Main and caster wheels"]>=40
assert bpy.data.objects["Primary Malay wheelchair loan label"].data.body=="PINJAMAN"
assert bpy.data.objects["Malay wheelchair name"].data.body=="KERUSI RODA"
assert bpy.data.objects["English wheelchair loan label"].data.body=="WHEELCHAIR LOAN"
assert len([o for o in bpy.data.objects if "collapsed X brace" in o.name])==2
assert len([o for o in bpy.data.objects if "slim stowed foot plate" in o.name])==2

def verts(o):
    return [o.matrix_world @ Vector(v) for v in o.bound_box]
def bounds(v):
    return [[min(p[a] for p in v) for a in range(3)],[max(p[a] for p in v) for a in range(3)]]

source=bpy.data.objects
t=[source[n] for n in ("Left spoke wheel multi-radius black tyre","Right spoke wheel multi-radius black tyre",
                       "Left front caster tread","Right front caster tread")]
bb=[bounds(verts(o)) for o in t]
assert all(abs(v[0][2]-.089)<.002 for v in bb),bb
wheel_gap=abs((bb[1][0][0]+bb[1][1][0]-bb[0][0][0]-bb[0][1][0])/2)
assert .26<wheel_gap<.27,wheel_gap
lo,hi=bounds(verts(source["Hanging indigo seat sling with central fold"]))
sling_drop=hi[2]-lo[2]
assert sling_drop>.22 and hi[0]-lo[0]<.22,(lo,hi)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(d/"exports"/(slug+".glb")))
scene=bpy.context.scene
meshes=[o for o in scene.objects if o.type=="MESH"]
lo,hi=bounds([v for o in meshes for v in verts(o)])
dims=[hi[a]-lo[a] for a in range(3)]
assert abs(lo[2])<1e-6
assert 1.24<dims[0]<1.25 and 1.13<dims[1]<1.15 and 1.24<dims[2]<1.25,dims
assert not any(o.type in {"LIGHT","CAMERA"} or o.animation_data for o in scene.objects)
deps=bpy.context.evaluated_depsgraph_get()
def ray(x,y):
    h,p,_,_,o,_=scene.ray_cast(deps,Vector((x,y,1.6)),Vector((0,0,-1)))
    assert h
    return round(p.z,6),o.name
for x in (.01,.166,.326):
    h,o=ray(x,-.482)
    assert .085 < h < .098 and o.startswith("Low-profile docking"),(h,o)
h,o=ray(.169,.452)
assert .39<h<.43 and o.startswith("Cup tray and docking bumper"),(h,o)
print("REIMPORT",json.dumps({"sourceGroups":groups,"boundsBlenderXYZ":[round(x,5) for x in dims],"wheelCentersSpacing":round(wheel_gap,4),
  "realSlingDrop":round(sling_drop,4),"wheelsReachDeck":True,"frontRolloutClear":True,"rearStopSeparate":True,"meshNodes":len(meshes)}))
