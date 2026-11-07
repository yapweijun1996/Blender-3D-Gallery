"""Sampled mesh intersection audit, excluding intentional hardware contacts."""
import bpy,math,json,re
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=bpy.data.objects['ASSET_Proton_Saga_1985']
dep=bpy.context.evaluated_depsgraph_get()
# Audit the shaped body panels, door openings, and opposite door leaves.
prefixes=('Left Front wing panel','Right Front wing panel','Left Rear quarter panel','Right Rear quarter panel','Slender A pillar','Painted B pillar','Formed C pillar','Window belt ledge','Roof rail','Pressed rocker sill','Front door opening threshold','Rear door opening threshold','Door opening upright seal','Cabin floor','Front seat cushion','Rear seat cushion','Sculpted padded dashboard')
statics=[o for o in root.children if o.type=='MESH' and o.name.startswith(prefixes)]

def tree(obj):
 e=obj.evaluated_get(dep); m=e.to_mesh();m.calc_loop_triangles();w=obj.matrix_world
 vertices=[w@v.co for v in m.vertices];triangles=[tuple(t.vertices) for t in m.loop_triangles]
 e.to_mesh_clear()
 if not vertices or not triangles:return None
 lo=tuple(min(v[i] for v in vertices) for i in range(3));hi=tuple(max(v[i] for v in vertices) for i in range(3))
 return BVHTree.FromPolygons(vertices,triangles,all_triangles=True,epsilon=0),lo,hi

def intersect(a,b):
 if a is None or b is None:return False
 for i in range(3):
  if a[2][i] < b[1][i] or b[2][i] < a[1][i]:return False
 return bool(a[0].overlap(b[0]))

static_trees={o:tree(o) for o in statics}

result={};all_failed=[]
for code in ('FL','FR','RL','RR'):
 pivot=bpy.data.objects[f'PIVOT_Door_{code}_Hinge']
 # Sample primary door panels, panes, cards and moulding; hinge/latch contact
 # and narrow trim pieces are deliberately outside this geometric audit.
 movable=[o for o in pivot.children_recursive if o.type=='MESH' and not any(x in o.name.lower() for x in ('hinge','latch','structural frame','rubber channel','narrow metal surround','shutline','molding insert','lower pressed contour','crank','interior door pull','armrest','pocket','upper edge'))]
 others=[o for other in ('FL','FR','RL','RR') if other!=code for o in bpy.data.objects[f'PIVOT_Door_{other}_Hinge'].children_recursive if o.type=='MESH' and ('door panel' in o.name or 'door window' in o.name and o.name.split('.')[0].endswith('window'))]
 obstacles={**static_trees,**{o:tree(o) for o in others}}
 poses={}
 for angle in range(0,61,5):
  pivot.rotation_euler.z=math.radians(angle)*(-1 if code.endswith('L') else 1);bpy.context.view_layer.update()
  dynamic={o:tree(o) for o in movable}
  pairs=sorted((o.name,s.name) for o,t in dynamic.items() for s,st in obstacles.items() if intersect(t,st))
  poses[angle]=pairs
 baseline=set(poses[0]);added={angle:[pair for pair in pairs if pair not in baseline] for angle,pairs in poses.items() if angle and any(pair not in baseline for pair in pairs)}
 open_overlaps={angle:pairs for angle,pairs in poses.items() if angle and pairs}
 result[code]={'open_overlaps':open_overlaps,'baseline_intersections':len(baseline),'baseline_pairs':sorted(baseline),'new_intersections':added,'existing_pairs_still_overlapping':{a:[p for p in pairs if p in baseline] for a,pairs in poses.items() if a in (5,15,30,45,60)},'moving_objects':len(movable),'obstacle_objects':len(obstacles)}
 if open_overlaps:all_failed.append(code)
 pivot.rotation_euler.z=0;bpy.context.view_layer.update()
# Check the two doors on each side at independent angle combinations.
combined={}
for side in ('L','R'):
    pivots=[bpy.data.objects[f'PIVOT_Door_{end}{side}_Hinge'] for end in ('F','R')]
    doors=[[o for o in p.children_recursive if o.type=='MESH' and ('door panel' in o.name or re.fullmatch(r'(?:Front|Rear) door window(?:\.\d+)?',o.name) or 'fitted inner door card' in o.name)] for p in pivots]
    overlaps={}
    for front_angle in (0,15,30,45,60):
        for rear_angle in (0,15,30,45,60):
            if front_angle==rear_angle==0:continue
            for p,angle in zip(pivots,(front_angle,rear_angle)):p.rotation_euler.z=math.radians(angle)*(-1 if side=='L' else 1)
            bpy.context.view_layer.update()
            first={o:tree(o) for o in doors[0]};second={o:tree(o) for o in doors[1]}
            pairs=[(a.name,b.name) for a,ta in first.items() for b,tb in second.items() if intersect(ta,tb)]
            if pairs:overlaps[f'{front_angle},{rear_angle}']=pairs
    combined[side]=overlaps
    if overlaps:all_failed.append('pair-'+side)
    for p in pivots:p.rotation_euler.z=0
    bpy.context.view_layer.update()
print('CLEARANCE_RESULT',json.dumps(result,sort_keys=True))
print('PAIRED_SWEEP',json.dumps(combined,sort_keys=True))
assert not all_failed,'Overlaps during sampled door sweep: '+','.join(all_failed)
