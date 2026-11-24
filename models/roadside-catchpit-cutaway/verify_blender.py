"""Actual cast-path audit on source and independently imported export."""
from collections import Counter
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

slug='roadside-catchpit-cutaway'
root=Path(__file__).resolve().parent
imported='--reimport' in sys.argv
if imported:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root/'exports'/f'{slug}.glb'))
C=bpy.context
exported=[]
for o in C.scene.objects:
    if o.type=='MESH' and not any(c.name.startswith('06 studio') for c in o.users_collection):
        exported.append(o)
deps=C.evaluated_depsgraph_get()
vertices=[];faces=[];names=[]
local={}
for ob in exported:
    ev=ob.evaluated_get(deps); g=ev.to_mesh();g.calc_loop_triangles()
    xyz=[tuple(ev.matrix_world @ v.co) for v in g.vertices]
    ff=[tuple(p.vertices) for p in g.loop_triangles]
    local[ob.name]=(xyz,ff)
    start=len(vertices);vertices.extend(xyz)
    faces.extend(tuple(start+j for j in indices) for indices in ff)
    names.extend([ob.name]*len(ff))
    ev.to_mesh_clear()
bvh=BVHTree.FromPolygons(vertices,faces,all_triangles=True)
rr=[0]
def ray(origin,direction,maximum):
    p,n,t,d=bvh.ray_cast(Vector(origin),Vector(direction),maximum)
    rr[0]+=1
    assert p is not None, (origin,direction)
    return p,names[t],d
def only(k,prefix):
    assert k.startswith(prefix), (prefix,k)

grate=[]
for i in range(9):
    for y in (-.268,-.213,-.148):
        x=-.565+i*.0615
        p,k,d=ray((x,y,1.3),(0,0,-1),1.4)
        only(k,'Distinct crossbar')
        assert .934<p.z<.938
        grate.append(p.z)
for i in range(8):
    for y in (-.268,-.213,-.148):
        for offset in (-.011,0,.011):
            x=-.565+(i+.5)*.0615+offset
            p,k,d=ray((x,y,1.3),(0,0,-1),1.4)
            only(k,'Thin illustrative sump')
            assert .173<p.z<.177, (x,y,p,k)
throat=[]
for x in (-.535,-.445,-.35,-.264,-.178,-.088):
    for z in (.948,.965,.984,.999):
        p,k,d=ray((x,-.405,z),(0,1,0),1.1)
        only(k,'Small rim collar')
        assert .243<p.y<.250
        throat.append(d)
    for y in (.112,.156,.189,.222):
        p,k,d=ray((x,y,1.001),(0,0,-1),1.05)
        only(k,'Thin illustrative sump')
        assert .173<p.z<.177
# The front is deliberately cut off, not a dark opaque rectangle concealing the well.
for x in (-.62,-.50,-.365,-.22,-.082,.055):
    for z in (.362,.443,.525,.588):
        p,k,d=ray((x,-.565,z),(0,1,0),1.2)
        only(k,'Rear chamber backing wall')
        assert .432<p.y<.442
# The bore reaches the same open chamber volume, not a blind dark cap or a plug at the cut face.
bore=[]
for r in (0,.045,.080,.106,.119):
    for n in range(1 if r==0 else 16):
        a=math.tau*n/16
        y=.063+r*math.cos(a); z=.385+r*math.sin(a)
        p,k,d=ray((.864,y,z),(-1,0,0),1.9)
        only(k,'Left full-height cast retaining wall')
        assert -.735<p.x<-.715
        bore.append(d)
annulus=[]
for n in range(24):
    a=math.tau*n/24;r=.140
    y=.063+r*math.cos(a);z=.385+r*math.sin(a)
    p,k,d=ray((.864,y,z),(-1,0,0),.2)
    assert k.startswith(('OUTLET_HOLLOW_PIPE','Outlet terminal edge band')),(p,k)
    assert .802<p.x<.809
    annulus.append(p.x)
# Weld upon import (vertex splitting by material and hard-edge normals is expected), then prove
# the structural ring walls are closed solids with open central holes, not two-sided sheets.
topology={}
for k in ('OUTLET_PASS_THROUGH_WALL','OUTLET_HOLLOW_PIPE'):
    xyz,tris=local[k];weld=[tuple(round(x*1e5) for x in p) for p in xyz];cnt=Counter()
    for tri in tris:
        a,b,c=[weld[i] for i in tri];assert len({a,b,c})==3
        for edge in ((a,b),(b,c),(c,a)):
            cnt[tuple(sorted(edge))]+=1
    assert set(cnt.values())=={2},(k,Counter(cnt.values()))
    V=len(set(weld));E=len(cnt);F=len(tris);assert V-E+F==0,(k,V,E,F)
    topology[k]={'welded_vertices':V,'edges':E,'triangles':F,'Euler':V-E+F}

print('CATCHPIT_CAST '+json.dumps({'domain':'GLB-reimported' if imported else 'editable-source',
      'rays':rr[0],'physical_grate_crossbars':9,'through_grate_clearance_rays':72,'through_kerb_throat_rays':24,
      'through_throat_down_into_sump_rays':24,'sawn_side_chamber_rays':24,'bore_through_to_chamber_rays':len(bore),
      'annular_outlet_surface_rays':len(annulus),'min_entrance_travel_m':min(throat),
      'shortest_through_bore_and_chamber_cast_m':min(bore),'topology':topology}))
