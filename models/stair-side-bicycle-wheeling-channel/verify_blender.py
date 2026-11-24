"""Actual rolled trough and handover geometry, native and independently reimported."""
from collections import Counter
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

imported='--reimport' in sys.argv
if imported:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(__file__).resolve().parent/'exports/stair-side-bicycle-wheeling-channel.glb'))
scene=bpy.context.scene
deps=bpy.context.evaluated_depsgraph_get()
names=[];vertices=[];tris=[];per={}
for o in scene.objects:
    if o.type!='MESH' or any(c.name.startswith('05 studio') for c in o.users_collection):
        continue
    ob=o.evaluated_get(deps);mesh=ob.to_mesh();mesh.calc_loop_triangles()
    v=[ob.matrix_world @ k.co for k in mesh.vertices]
    f=[tuple(k.vertices) for k in mesh.loop_triangles]
    per[o.name]=(v,f)
    off=len(vertices);vertices.extend(v)
    tris.extend(tuple(off+i for i in t) for t in f);names.extend([o.name]*len(f))
    ob.to_mesh_clear()
tree=BVHTree.FromPolygons(vertices,tris,all_triangles=True)
cy=-.492
x0,x1=-1.145,.985
base,high=.143,.839
start,end=-1.072,.758
lb=.125
length=end-start
def level(x):
    u=min(length,max(0,x-start))
    area=u*u/(2*lb) if u<lb else length-lb-(length-u)**2/(2*lb) if u>length-lb else u-lb/2
    return base+(high-base)*area/(length-lb)
def down(x,y):
    p,n,i,d=tree.ray_cast(Vector((x,y,1.99)),Vector((0,0,-1)),2)
    assert p is not None and n.z>0.75,(x,y,p,n)
    return p,names[i]
previous=base
max_profile=0
min_lips=1
count=0
for i in range(341):
    x=x0+.0005+(x1-x0-.001)*i/340
    for off in (-.036,-.018,0,.018,.036):
        h,n=down(x,cy+off)
        assert n=='CONTINUOUS_WHEEL_TROUGH',(i,x,off,n,h)
        e=abs(h.z-level(x))
        assert e<.00028,(i,x,off,e)
        max_profile=max(max_profile,e)
        count+=1
        if off==0:
            assert h.z>=previous-3e-7,(i,x,h.z,previous)
            previous=h.z
for x in (-.840,-.644,-.400,-.101,.25,.51,.699):
    c,n=down(x,cy)
    for side in (-1,1):
        p,n=down(x,cy+side*.066)
        assert n=='CONTINUOUS_WHEEL_TROUGH'
        assert p.z-c.z>.037,(x,side,p,c)
        min_lips=min(min_lips,p.z-c.z)

joins=0
for x,z,landing,s in [(x0,base,'Lower cropped loading landing slab',1),(x1,high,'Narrow upper handover closeout slab',-1)]:
    for d in (.0004,.0017,.0048,.013):
        for off in (-.032,0,.032):
            p,k=down(x+s*d,cy+off);q,l=down(x-s*d,cy+off)
            assert k=='CONTINUOUS_WHEEL_TROUGH' and l==landing,(x,d,k,l)
            assert abs(p.z-z)<3e-6 and abs(q.z-z)<3e-6 and abs(p.z-q.z)<3e-6
            joins+=1
# Separate concrete treads and the high stair-to-landing merge, verified independently of the trough.
for i in range(6):
    x=-.932+(i+.51)*.267
    p,n=down(x,.057)
    assert n.startswith('Editable concrete stair tread') and abs(p.z-(base+(i+1)*.116))<3e-6
for x in (.665,.669,.674,.679,.683,.699):
    p,n=down(x,.130)
    assert n.startswith(('Editable concrete stair tread','Upper landing slab behind clear channel')),(x,p,n)
    assert abs(p.z-high)<.004,(x,p,n)

v,t=per['CONTINUOUS_WHEEL_TROUGH'];w=[tuple(round(a*1e5) for a in p) for p in v]
edges=Counter()
for face in t:
    a,b,c=[w[i] for i in face]
    assert len({a,b,c})==3
    for edge in ((a,b),(b,c),(c,a)):
        edges[tuple(sorted(edge))]+=1
assert set(edges.values())=={2}
euler=len(set(w))-len(edges)+len(t)
assert euler==2
def named_bvh(name):
    v,t=per[name]
    return BVHTree.FromPolygons(v,t,all_triangles=True)
skin=named_bvh('CONTINUOUS_WHEEL_TROUGH')
seats=sorted(k for k in per if k.startswith('Welded blue wedge saddle supporting channel'))
assert len(seats)==6
minimum_contact=1
maximum_contact=-1
for x,k in zip((-.925,-.578,-.210,.166,.525,.842),seats):
    b=named_bvh(k)
    top,_,_,_=b.ray_cast(Vector((x,cy,1.35)),Vector((0,0,-1)),1.3)
    under,_,_,_=skin.ray_cast(Vector((x,cy,.10)),Vector((0,0,1)),1.3)
    assert top is not None and under is not None,(x,k)
    contact=top.z-under.z
    assert -.0018<contact<.0022,(x,k,contact)
    minimum_contact=min(minimum_contact,contact);maximum_contact=max(maximum_contact,contact)
assert len([n for n in per if n.startswith('Independently editable rail upright')])==6
print('WHEEL_CHANNEL_PROOF '+json.dumps({'domain':'GLB-reimport' if imported else 'editable-source',
      'floor_samples':count,'landing_pairs':joins,'cross_section_lip_samples':14,'welded_closed_shell_euler':euler,
      'independent_treads':6,'mounted_saddles':6,'max_profile_error_mm':max_profile*1000,
      'min_crown_above_floor_mm':min_lips*1000,'saddle_contact_mm':[minimum_contact*1000,maximum_contact*1000]}))
