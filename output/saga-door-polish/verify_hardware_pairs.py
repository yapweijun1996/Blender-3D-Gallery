import bpy,math,json,re
from mathutils.bvhtree import BVHTree
root=bpy.data.objects['ASSET_Proton_Saga_1985'];dep=bpy.context.evaluated_depsgraph_get()
# Named moving fittings plus edge seals; scan relevant fixed body, trim and hardware.
static_markers=('hinge bracket','hinge pin','striker plate','latch striker','seal','weatherstrip','roof rail','window belt ledge','front wing panel','rear quarter panel','a pillar','b pillar','c pillar','rocker sill','door opening threshold','cabin floor','front seat','rear seat','dashboard')
st=[o for o in root.children if o.type=='MESH' and any(x in o.name.lower() for x in static_markers)]
def tree(obj):
 ev=obj.evaluated_get(dep);m=ev.to_mesh();m.calc_loop_triangles();mw=obj.matrix_world;v=[mw @ item.co for item in m.vertices];f=[tuple(t.vertices) for t in m.loop_triangles];ev.to_mesh_clear()
 if not v or not f:return None
 lo=tuple(min(x[i] for x in v) for i in range(3));hi=tuple(max(x[i] for x in v) for i in range(3));return BVHTree.FromPolygons(v,f,all_triangles=True,epsilon=0),lo,hi
def collide(a,b):
 if a is None or b is None:return 0
 if any(a[2][i]<b[1][i] or b[2][i]<a[1][i] for i in range(3)):return 0
 return len(a[0].overlap(b[0]))

markers=('hinge leaf','door latch plate','crank','structural frame','rubber channel','metal surround','inner door card upper edge','door lower window weatherstrip')
angles=(0,1,2,5,10,15,30,45,60)
for side in ('L','R'):
 p={end:bpy.data.objects[f'PIVOT_Door_{end}{side}_Hinge'] for end in ('F','R')}
 objects={end:[o for o in pivot.children_recursive if o.type=='MESH'] for end,pivot in p.items()}
 hw={end:[o for o in items if any(x in o.name.lower() for x in markers)] for end,items in objects.items()}
 cache={}
 for end,pivot in p.items():
  for angle in angles:
   pivot.rotation_euler.z=math.radians(angle)*(-1 if side=='L' else 1);bpy.context.view_layer.update()
   cache[end,angle]={o:tree(o) for o in objects[end]}
  pivot.rotation_euler.z=0;bpy.context.view_layer.update()
 report={}
 for a in angles:
  for b in angles:
   if a and b and (a not in (5,15,30,45,60) or b not in (5,15,30,45,60)):continue
   front=cache['F',a];rear=cache['R',b]
   pairs=[]
   for m in hw['F']:
    for other in rear:
     n=collide(front[m],rear[other])
     if n:pairs.append((m.name,other.name,n))
   for m in hw['R']:
    for other in front:
     if other in hw['F']:continue
     n=collide(rear[m],front[other])
     if n:pairs.append((other.name,m.name,n))
   if pairs:report[f'{a},{b}']=pairs
 print('PAIR_AUDIT',side,json.dumps(report,sort_keys=True))
 assert not report, f'Unexpected intersections between {side} door hardware and the other door'
