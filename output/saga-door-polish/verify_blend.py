"""Check the isolated wheel hierarchy without editing or saving the scene."""
import bpy
import re
from mathutils import Vector
root=bpy.data.objects.get('ASSET_Proton_Saga_1985')
assert root is not None
bpy.context.view_layer.update()
for code in ('FL','FR','RL','RR'):
    roll=bpy.data.objects.get(f'PIVOT_Wheel_{code}_Roll')
    assert roll and roll.type=='EMPTY'
    steer=bpy.data.objects.get(f'PIVOT_Wheel_{code}_Steer')
    if code.startswith('F'):
        assert steer and steer.type=='EMPTY' and steer.parent==root and roll.parent==steer
        backings=[o for o in steer.children if o.name.startswith('Dark brake backing')]
        assert len(backings)==1
    else:
        assert steer is None and roll.parent==root
    children=list(roll.children_recursive)
    for prefix in ('High profile radial tire','Pressed steel wheel with punched vents','Shallow silver wheel cover'):
        assert len([o for o in children if o.name.startswith(prefix)])==1,(code,prefix)
    tire=next(o for o in children if o.name.startswith('High profile radial tire'))
    corners=[tire.matrix_world @ Vector(c) for c in tire.bound_box]
    center=sum(corners,Vector())/len(corners)
    pivot=roll.matrix_world.translation
    assert (center-pivot).length<.01,(code,center[:],pivot[:])
    print(code,'roll_children',len(children),'pivot',tuple(round(x,4) for x in pivot),'tire_center',tuple(round(x,4) for x in center))
print('PASS: independent roll pivots, front steering pivots and wheel centers')
for code in ('FL','FR','RL','RR'):
    pivot=bpy.data.objects.get(f'PIVOT_Door_{code}_Hinge')
    assert pivot and pivot.type=='EMPTY' and pivot.parent==root
    children=list(pivot.children_recursive)
    side='Left' if code.endswith('L') else 'Right'
    end='Front' if code.startswith('F') else 'Rear'
    for prefix in (f'{side} {end} door panel',f'{end} door window','Black lift handle','Door handle recess','Individual rubber side molding'):
        assert len([o for o in children if re.fullmatch(re.escape(prefix)+r'(?:\.\d+)?',o.name)])==1,(code,prefix,[o.name for o in children])
    if code.startswith('F'):
        assert len([o for o in children if o.name.startswith('Tapered black door mirror')])==1
    print(code, 'hinge',tuple(round(v,4) for v in pivot.matrix_world.translation),'parts',len(children))
print('PASS: four independent door hinges with corresponding panel, window, handle and molding')

for code in ('FL','FR','RL','RR'):
    pivot=bpy.data.objects[f'PIVOT_Door_{code}_Hinge']
    children=list(pivot.children_recursive)
    end='Front' if code.startswith('F') else 'Rear'
    for prefix in (end+' fitted inner door card',end+' interior armrest',end+' interior door pull',end+' door window structural frame'):
        assert len([o for o in children if re.fullmatch(re.escape(prefix)+r'(?:\.\d+)?',o.name)])==1,(code,prefix)
    if code.startswith('R'):
        assert len([o for o in children if re.fullmatch(r'Fixed rear quarterlight(?:\.\d+)?',o.name)])==1
    card=next(o for o in children if o.name.startswith(end+' fitted inner door card'))
    assert card.data.polygons[0].normal.y * (-1 if code.endswith('L') else 1)<-.9, (code, 'inner face must face cabin')
    before=card.matrix_world.copy();pivot.rotation_euler.z=(-1 if code.endswith('L') else 1)*.5;bpy.context.view_layer.update();assert card.matrix_world!=before
    pivot.rotation_euler.z=0;bpy.context.view_layer.update();assert all(abs(a-b)<1e-6 for row1,row2 in zip(before,card.matrix_world) for a,b in zip(row1,row2))
for prefix in ('Front door opening threshold','Rear door opening threshold','Door opening upright seal'):
    assert len([o for o in root.children if o.name.startswith(prefix)])>=2,prefix
print('PASS: independent fitted door cards, window frames, rear quarterlights and body-mounted thresholds')

for code in ('FL','FR','RL','RR'):
    pivot=bpy.data.objects[f'PIVOT_Door_{code}_Hinge'];end='Front' if code.startswith('F') else 'Rear'
    children=list(pivot.children_recursive)
    for prefix,count in ((end+' door hinge leaf',2),(end+' door latch plate',1),(end+' manual window crank boss',1),(end+' manual window crank arm',1),(end+' manual window crank knob',1),(end+' lower interior storage pocket',1)):
        found=[o for o in children if re.fullmatch(re.escape(prefix)+r'(?:\.\d+)?',o.name)]
        assert len(found)==count,(code,prefix,len(found))
    leaf=next(o for o in children if o.name.startswith(end+' door hinge leaf'));before=leaf.matrix_world.copy()
    pivot.rotation_euler.z=(-1 if code.endswith('L') else 1)*.5;bpy.context.view_layer.update();assert leaf.matrix_world!=before
    pivot.rotation_euler.z=0;bpy.context.view_layer.update()
for end in ('Front','Rear'):
    for prefix,count in ((end+' body hinge bracket',4),(end+' body hinge pin',4),(end+' body striker plate',2),(end+' body latch striker',2)):
        assert len([o for o in root.children if re.fullmatch(re.escape(prefix)+r'(?:\.\d+)?',o.name)])==count,prefix
print('PASS: moving hinge leaves, window cranks and latch plates; body-mounted hinge pins and strikers')

for code in ('FL','FR','RL','RR'):
    pivot=bpy.data.objects[f'PIVOT_Door_{code}_Hinge'];end='Front' if code.startswith('F') else 'Rear'
    children=list(pivot.children_recursive)
    for prefix,count in ((end+' woven door insert',1),(end+' padded upper vinyl rail',1),(end+' woven insert pleat',6),(end+' insert stitched piping',1),(end+' interior release lever',1),(end+' door lower window weatherstrip',1)):
        found=[o for o in children if re.fullmatch(re.escape(prefix)+r'(?:\.\d+)?',o.name)]
        assert len(found)==count,(code,prefix,len(found))
print('PASS: door upholstery layers, pleats, handles and per-door window seals')
