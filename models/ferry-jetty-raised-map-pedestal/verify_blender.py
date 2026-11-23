"""Measure the two real map planes and physical raised relief in an imported GLB."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

slug="ferry-jetty-raised-map-pedestal"
d=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(d/(slug+".blend")))
source=bpy.data.objects
groups={c.name:len(c.objects) for c in bpy.context.scene.collection.children}
assert len(groups)==5
assert source["Malay upper title"].data.body=="PETA JETI"
assert source["English upper title"].data.body=="JETTY MAP"
assert source["Upper model-only marker"].data.body=="CONTOH / SAMPLE"
assert source["Lower model-only indicator"].data.body=="CONTOH / SAMPLE"
upper=source["Upper overview separate full sloping metal housing"]
lower=source["Lower boarding inset separate full sloping metal housing"]
assert abs(upper.location.z-lower.location.z-.379)<1e-6
assert abs(math.degrees(upper.rotation_euler.x)-23)<1e-5
assert abs(math.degrees(lower.rotation_euler.x)-24)<1e-5
planes=[(x.location.copy(),x.rotation_euler.x) for x in (upper,lower)]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(d/"exports"/(slug+".glb")))
scene=bpy.context.scene
meshes=[o for o in scene.objects if o.type=="MESH"]
vs=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
lo=[min(v[i] for v in vs) for i in range(3)]
hi=[max(v[i] for v in vs) for i in range(3)]
dims=[hi[i]-lo[i] for i in range(3)]
assert abs(lo[2])<1e-6 and 1.15<dims[0]<1.16 and .76<dims[1]<.85 and 1.32<dims[2]<1.38,dims
assert not any(o.type in {"LIGHT","CAMERA"} or o.animation_data for o in scene.objects)
dep=bpy.context.evaluated_depsgraph_get()
def sample(p,x,y):
    pos,theta=planes[p]
    r=Matrix.Rotation(theta,3,"X")
    n=r@Vector((0,0,1))
    ahead=pos+r@Vector((x,y,.134))
    ok,hit,_,_,ob,_=scene.ray_cast(dep,ahead,-n)
    assert ok
    return round((hit-pos).dot(n),5),ob.name
water=sample(0,.014,.104)
route=sample(0,.034,-.044)
land=sample(0,-.394,-.109)
smallwater=sample(1,.077,.091)
smallroute=sample(1,.079,-.059)
assert abs(water[0]-.057)<.001 and "printed water" in water[1],water
assert abs(smallwater[0]-.057)<.001 and "printed water" in smallwater[1],smallwater
assert abs(land[0]-.073)<.001 and "raised islands" in land[1],land
assert abs(route[0]-.0855)<.001 and "raised route" in route[1],route
assert abs(smallroute[0]-.090)<.001 and "raised route" in smallroute[1],smallroute
print("REIMPORT",json.dumps({"groups":groups,"bboxBlenderXYZ":[round(a,5) for a in dims],"insetCentreHeightsM":[1.202,.823],
 "slopeDegrees":[23,24],"physicalRouteReliefM":[round(route[0]-water[0],5),round(smallroute[0]-smallwater[0],5)],"meshes":len(meshes)}))
