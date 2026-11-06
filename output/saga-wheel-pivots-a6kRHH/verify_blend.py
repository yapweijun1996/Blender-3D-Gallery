"""Check the isolated wheel hierarchy without editing or saving the scene."""
import bpy
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
