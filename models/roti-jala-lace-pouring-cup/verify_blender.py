"""Actual rays and welded topology for the native source and reimported export."""
from collections import Counter
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

imported='--reimport' in sys.argv
if imported:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(__file__).resolve().parent/'exports/roti-jala-lace-pouring-cup.glb'))
scene=bpy.context.scene
deps=bpy.context.evaluated_depsgraph_get()
verts=[];faces=[];names=[];local={}
for o in scene.objects:
    if o.type!='MESH' or any(c.name.startswith('04 studio') for c in o.users_collection):
        continue
    ev=o.evaluated_get(deps);m=ev.to_mesh();m.calc_loop_triangles()
    v=[ev.matrix_world @ i.co for i in m.vertices]
    tris=[tuple(i.vertices) for i in m.loop_triangles]
    off=len(verts);verts.extend(v)
    faces.extend(tuple(off+i for i in f) for f in tris);names.extend([o.name]*len(tris))
    local[o.name]=v,tris
    ev.to_mesh_clear()
bvh=BVHTree.FromPolygons(verts,faces,all_triangles=True)
cup=bpy.data.objects['ROTI_JALA_CUP_LOCAL'].matrix_world
dish=bpy.data.objects['ROTI_JALA_SAMPLE_DISH'].matrix_world
inv=cup.inverted()
down=(cup.to_3x3()@Vector((0,0,-1))).normalized()
up=-down
cw=lambda x,y,z:cup @ Vector((x,y,z))
C=[(0,0),(.031,0),(-.031,0),(0,.031),(0,-.031)]
tube_rays=0
for j,(x,y) in enumerate(C,1):
    for radius in (0,.0017,.0038):
        for k in range(1 if radius==0 else 12):
            t=math.tau*k/12
            a=x+radius*math.cos(t);b=y+radius*math.sin(t)
            for z,dr,dist in ((.153,down,.190),(-.034,up,.180)):
                h,_,f,_=bvh.ray_cast(cw(a,b,z),dr,dist)
                assert h is None,(j,radius,k,None if f is None else names[f],None if h is None else tuple(inv@h))
                tube_rays+=1
    for n in range(12):
        t=math.tau*n/12;radius=.0053
        h,_,f,_=bvh.ray_cast(cw(x+radius*math.cos(t),y+radius*math.sin(t),-.044),up,.032)
        assert h is not None and names[f].startswith(f'CUP_HOLLOW_NOZZLE_{j}'),(j,n,h,None if f is None else names[f])
        assert abs((inv@h).z+.029)<.000025
for x,y in ((.018,.017),(-.019,.019),(.020,-.019),(-.019,-.019),(.052,0)):
    h,_,f,_=bvh.ray_cast(cw(x,y,.151),down,.18)
    assert h is not None and names[f]=='CUP_FLOOR_TOP_FIVE_CUTS',(x,y,h,None if f is None else names[f])
    assert abs((inv@h).z-.014)<.00002

def euler(keys):
    edges=Counter();vertices=set();N=0
    for k in keys:
        xyz,ts=local[k]
        vv=[tuple(round(u*1e5) for u in v) for v in xyz];vertices.update(vv)
        for fi in ts:
            a,b,c=[vv[i] for i in fi]
            assert len({a,b,c})==3
            for edge in ((a,b),(b,c),(c,a)):
                edges[tuple(sorted(edge))]+=1
            N+=1
    assert set(edges.values())=={2},(keys[0],Counter(edges.values()))
    return len(vertices)-len(edges)+N
body=[k for k in local if k=='CUP_ROLLED_BODY' or k.startswith(('CUP_FLOOR_','CUP_DRILLED_THROAT_'))]
assert len(body)==8 and euler(body)==-8
for j in range(1,6):
    assert euler([f'CUP_HOLLOW_NOZZLE_{j}'])==0

gaps=0
for i in range(-5,5):
    for j in range(-5,5):
        x=(i+.5)*.018;y=(j+.5)*.018
        if x*x+y*y>.089**2:
            continue
        h,_,f,_=bvh.ray_cast(dish@Vector((x,y,.110)),Vector((0,0,-1)),.070)
        assert h is not None and names[f].startswith('Warm cream shallow'),(x,y,h,None if f is None else names[f])
        assert .055<h.z<.061
        gaps+=1
for k in range(-5,6):
    u=k*.018+.0028*math.sin(7*.65+k*.72)+.0010*math.sin(7*.92)
    h,_,f,_=bvh.ray_cast(dish@Vector((0,u,.113)),Vector((0,0,-1)),.080)
    assert h is not None and names[f].startswith('Physical roti'),(k,h,None if f is None else names[f])
    assert .062<h.z<.071
assert gaps>=75
for prefix,n in [('Cradle foot',4),('Open rubber-tipped',4),('Green angled',4),('Curved joined',1)]:
    assert len([k for k in local if k.startswith(prefix)])==n
print('ROTI_JALA_GEOMETRY '+json.dumps({'mode':'reimported-GLB' if imported else 'native-source','five_bored_outlets':5,
  'through_bore_bidirectional_rays':tube_rays,'annular_tip_hits':60,'solid_floor_hits':5,'cup_welded_euler':-8,
  'separate_nozzle_closed_tori':5,'lace_gap_rays':gaps,'lace_ribbon_hits':11,'tip_radial_clearance_samples_mm':3.8}))
