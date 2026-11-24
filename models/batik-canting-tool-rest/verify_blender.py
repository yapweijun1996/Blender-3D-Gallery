"""Physical native and export-reimport audit of an actually connected curved lumen."""
from collections import Counter,defaultdict
import json,math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

s='batik-canting-tool-rest'
imp='--reimport' in sys.argv
if imp:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(__file__).resolve().parent/'exports'/f'{s}.glb'))
deps=bpy.context.evaluated_depsgraph_get()
scene=bpy.context.scene
by_name={}
for o in scene.objects:
    if o.type!='MESH' or any(c.name.startswith('04 studio') for c in o.users_collection):
        continue
    e=o.evaluated_get(deps);m=e.to_mesh();m.calc_loop_triangles()
    by_name[o.name]=[e.matrix_world @ x.co for x in m.vertices],[tuple(x.vertices) for x in m.loop_triangles]
    e.to_mesh_clear()
name='CANTING_CONNECTED_COPPER_BOWL_AND_SPOUT'
def bvh(key):
    v,f=by_name[key]
    return BVHTree.FromPolygons(v,f,all_triangles=True)
c=bvh(name)
v,f=by_name[name]
weld=[tuple(round(p*1e7) for p in x) for x in v]
edges=Counter(); graph=defaultdict(set)
for f0 in f:
    a,b,d=[weld[j] for j in f0]
    assert len({a,b,d})==3
    for u,w in ((a,b),(b,d),(d,a)):
        edges[tuple(sorted((u,w)))]+=1
        graph[u].add(w);graph[w].add(u)
assert set(edges.values())=={2},Counter(edges.values())
seen=set();pending=[weld[0]]
while pending:
    x=pending.pop()
    if x in seen:continue
    seen.add(x);pending.extend(graph[x]-seen)
assert len(seen)==len(set(weld)) and len(seen)-len(edges)+len(f)==0
V=Vector
for x in (-.017,-.007,.006,.014,.024):
    for y in (-.008,-.003,0,.004,.009):
        p,n,i,d=c.ray_cast(V((x,y,.15)),V((0,0,-1)),.15)
        assert p is not None and .068<=p.z<(.090 if abs(x-.006)>.014 else .079),(x,y,p,n)
# A straight run begins inside the actual bowl and reaches the first curved-ring center.
def pos(t):
    return V((.039+.058*t,-.0044*t*t,.096-.031*t*t))
def axis(t):
    return V((.058,-.0088*t,-.062*t)).normalized()
def basis(t):
    T=axis(t);Y=(V((0,1,0))-T*T.y).normalized()
    return Y,T.cross(Y).normalized()
def rad(t):
    return .00440-.00325*t**.77
def point(t,angle,multiple):
    y,z=basis(t)
    return pos(t)+multiple*rad(t)*(math.cos(angle)*y+math.sin(angle)*z)
clear=0
def sep(a,b):
    global clear
    for q,w in ((a,b),(b,a)):
        p,n,i,d=c.ray_cast(q,(w-q).normalized(),(w-q).length)
        assert p is None,(tuple(q),tuple(w),p)
        clear+=1
for r in (0,.0018,.0030):
    for j in range(1 if r==0 else 16):
        a=math.tau*j/16
        sep(V((.014,r*math.cos(a),.096+r*math.sin(a))),
            V((.039,r*math.cos(a),.096+r*math.sin(a))))
for j in range(56):
    t=j/56;u=(j+1)/56
    for a in (0,math.tau/8,math.tau/4,3*math.tau/8,math.tau/2,5*math.tau/8,3*math.tau/4,7*math.tau/8):
        sep(point(t,a,.43),point(u,a,.43))
sep(pos(1)-axis(1)*.002,pos(1)+axis(1)*.006)
inner_dist=[]
for i in range(1,28):
    t=i/28
    Y,Z=basis(t)
    for j in range(16):
        a=math.tau*j/16;direction=math.cos(a)*Y+math.sin(a)*Z
        p,n,k,d=c.ray_cast(pos(t),direction,.015)
        assert p is not None and .65*rad(t)<d<1.02*rad(t),(i,j,p,d,rad(t))
        assert n.dot(direction)<-.25,(i,j,n,direction)
        inner_dist.append(d)
# Both supports are separate but touch the corresponding object underneath.
def support(a,b,x,y,tip):
    off=bvh(a).ray_cast(V((x,y,tip)),V((0,0,1)),.08)[0]
    on=bvh(b).ray_cast(V((x,y,tip+.10)),V((0,0,-1)),.11)[0]
    assert off is not None and on is not None
    diff=on.z-off.z
    assert 0<diff<.0007,(a,b,off,on)
    return diff
seat=[support('Offset turned wooden canting handle','Flat padded handle saddle seat',-.110,-.016,.077),
      support(name,'Thin padded bowl heel cutout',.006,0,.052)]
# Near the old left-wall witness mark, the real vessel must remain the first surface;
# no handle tang, ferrule or exterior pad is allowed to show through the cavity.
assembly=['Offset turned wooden canting handle','Copper offset handle ferrule with shoulder',
          'Short bent metal tang seated on external weld saddle','Exterior copper tang weld saddle']
hardware=[(key,bvh(key)) for key in assembly]
shell_boundary_rays=0
for y in (-.015,-.013,-.011,-.009,-.007,-.005,-.003):
    for i in range(21):
        z=.085+i*.0012
        o=V((-.008,y,z));d=V((-1,0,0))
        barrier=c.ray_cast(o,d,.060)
        assert barrier[0] is not None and barrier[3]>.001
        for key,check in hardware:
            h,_,_,distance=check.ray_cast(o,d,barrier[3]-.00010)
            assert h is None,(y,z,key,h,distance,barrier[3])
        shell_boundary_rays+=1
assert len([k for k in by_name if k.startswith('Original branching stem on cloth')])==4
print('CANTING_GEOMETRY '+json.dumps({'domain':'GLB-reimport' if imp else 'editable-source','one_manifold_genus':1,
  'reservoir_depth_first_surface_probes':25,'bidirectional_bore_path_probes':clear,'curved_inner_wall_probes':len(inner_dist),
  'minimum_sampled_inner_wall_distance_mm':1000*min(inner_dist),'seat_contact_mm':[x*1000 for x in seat],'no_handle_intrusion_rays':shell_boundary_rays}))
