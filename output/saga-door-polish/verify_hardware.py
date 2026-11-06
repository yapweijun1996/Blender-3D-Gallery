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
statics={o:tree(o) for o in st};report={}
for code in ('FL','FR','RL','RR'):
 p=bpy.data.objects[f'PIVOT_Door_{code}_Hinge']
 move=[o for o in p.children_recursive if o.type=='MESH' and any(x in o.name.lower() for x in ('hinge leaf','door latch plate','crank','structural frame','rubber channel','metal surround','inner door card upper edge','door lower window weatherstrip','interior release lever','pocket fastening'))]
 states={}
 for angle in (0,1,2,3,*range(5,61,5)):
  p.rotation_euler.z=math.radians(angle)*(-1 if code.endswith('L') else 1);bpy.context.view_layer.update()
  pairs=[(m.name,o.name,n) for m in move for t in [tree(m)] for o,stree in statics.items() for n in [collide(t,stree)] if n]
  states[angle]=pairs
 p.rotation_euler.z=0;bpy.context.view_layer.update()
 report[code]={'samples':states,'movable':len(move),'static':len(st)}
print('HARDWARE_AUDIT',json.dumps(report,sort_keys=True))

unexpected={}
for code,entry in report.items():
    for angle,rows in entry['samples'].items():
        for moving,stationary,count in rows:
            # The hinge leaf rotates around its own fixed pin. A latch can touch
            # the striker at the closed position or just as it releases.
            is_pin='hinge leaf' in moving.lower() and 'hinge pin' in stationary.lower()
            is_latch=('door latch plate' in moving.lower() and ('striker plate' in stationary.lower() or 'latch striker' in stationary.lower()) and int(angle)<=1)
            # The rear quarterlight frame seals against the C pillar when shut;
            # record the closed-pose overlap but require release once opened.
            is_closed_seal=(int(angle)==0 and 'fixed rear quarterlight' in moving.lower() and 'formed c pillar' in stationary.lower())
            if not (is_pin or is_latch or is_closed_seal):unexpected.setdefault(code,{}).setdefault(angle,[]).append((moving,stationary,count))
print('UNEXPECTED_HARDWARE_CONTACTS',json.dumps(unexpected,sort_keys=True))
assert not unexpected,'Unexpected hardware or seal intersections in sampled poses'
