"""Exact native spherical-cap, stationary mount and GLB round-trip checks."""
import json
import math
import sys
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

source,glb=(str(Path(p).resolve()) for p in sys.argv[sys.argv.index('--')+1:])
def measure(scene,original):
    glass=scene.objects['CONVEX_LENS_DECORATIVE_CAP']
    parent=scene.objects['MIRROR_STATIC_MOUNT']
    disc=scene.objects['Actual rear attachment disc']
    assert glass.parent==parent and parent.type=='EMPTY' and disc.type=='MESH'
    assert not any(o.animation_data and (o.animation_data.action or o.animation_data.nla_tracks) for o in scene.objects)
    assert len(glass.data.color_attributes)>0
    if original:
        bm=bmesh.new();bm.from_mesh(glass.data)
        assert all(edge.is_manifold for edge in bm.edges) and bm.calc_volume(signed=True)>.00001
        bm.free()
    dg=bpy.context.evaluated_depsgraph_get()
    MW=parent.matrix_world
    normal=MW.to_3x3()@Vector((0,-1,0))
    assert normal.x>.20 and normal.y<-.93 and normal.z<-.11,normal
    loc=MW.translation
    assert (loc-Vector((.222,-.354,1.491))).length<.00001
    R=.244; sphere=.575; edge=-.033
    def sag(r):return math.sqrt(sphere*sphere-r*r)-math.sqrt(sphere*sphere-R*R)
    def yf(x):return edge-sag(x)
    pts=[v.co for v in glass.data.vertices if v.co.y<-.03299]
    residual=max(abs(v.y-yf(math.hypot(v.x,v.z))) for v in pts)
    assert residual<.000004 and len(pts)>450
    assert abs(min(v.y for v in pts)-yf(0))<.000004
    depths=[]
    for x in (0,.075,.151,.213,.234):
        origin=MW@Vector((x,-.4,0)); toward=-normal
        ok,p,_,_,o,_=scene.ray_cast(dg,origin,toward,distance=.50)
        assert ok and o==glass,(x,o)
        yy=(MW.inverted()@p).y
        assert abs(yy-yf(x))<.00018,(x,yy,yf(x))
        depths.append(yy)
    assert all(a<b for a,b in zip(depths,depths[1:]))
    # A cast along the rear attachment axis reaches its actual geometry.
    rear=MW@Vector((.057,.083,0)); ok,p,_,_,o,_=scene.ray_cast(dg,rear,normal,distance=.089)
    assert ok and o==disc, (rear,o)
    return {'lensForwardSagM':sag(0),'sphericalFitMaxErrorM':residual,'frontLensRayY':depths,
            'mountForwardBlenderXYZ':list(normal),'mountDiscHit':o.name,'static':True}
bpy.ops.wm.open_mainfile(filepath=source)
s=measure(bpy.context.scene,True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
assert all(o.type not in {'CAMERA','LIGHT'} for o in bpy.context.scene.objects)
t=measure(bpy.context.scene,False)
assert max(abs(a-b) for a,b in zip(s['frontLensRayY'],t['frontLensRayY']))<.000004
print('M22_NATIVE_PROOF',json.dumps({'blender':bpy.app.version_string,'source':s,'roundTripGLB':t},sort_keys=True))
