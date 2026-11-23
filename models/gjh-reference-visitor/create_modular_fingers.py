"""Build separate, rigidly controllable chibi fingers on the current visitor.

Run after rig.py. Original fused arms are archived in a hidden scene collection;
none of their mesh data is deleted. Five one-segment bones and five meshes are
added to each hand. The poseable fingers follow the existing upper arm bone.
"""
import bpy
import bmesh
from mathutils import Vector

scene=bpy.data.scenes['GJH Reference Visitor']
bpy.context.window.scene=scene
model=next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
root=next(o for o in model.objects if o.name=='GJH_Visitor')
rig=next(o for o in model.objects if o.type=='ARMATURE')
if any(name.startswith('Finger.') for name in rig.data.bones.keys()):
    raise RuntimeError('Finger rig already exists; start with the unmodified character')
old={}
for side in ('L','R'):
    matches=[o for o in model.objects if o.type=='MESH' and o.name.startswith('Arm.'+side)]
    if len(matches)!=1:raise RuntimeError('Expected one original arm for '+side)
    old[side]=matches[0]
if bpy.data.collections.get('Original fused hands - archived'):
    raise RuntimeError('Hand archive already exists')
archive=bpy.data.collections.new('Original fused hands - archived')
scene.collection.children.link(archive)
archive.hide_render=True
archive.hide_viewport=True
materials={side:old[side].data.materials[0] for side in ('L','R')}
for side, obj in old.items():
    # The original forearm tube and fused fist are disconnected mesh islands.
    # Retain the highest island so hiding the hoodie does not remove the arm.
    tube=obj.copy();tube.data=obj.data.copy();model.objects.link(tube)
    tube.name='Arm tube.'+side
    bm=bmesh.new();bm.from_mesh(tube.data)
    unseen=set(bm.verts);components=[]
    while unseen:
        vertex=unseen.pop();stack=[vertex];component=[vertex]
        while stack:
            for edge in stack.pop().link_edges:
                for neighbor in edge.verts:
                    if neighbor in unseen:
                        unseen.remove(neighbor);stack.append(neighbor);component.append(neighbor)
        components.append(component)
    if len(components)!=2:
        bm.free();raise RuntimeError('Expected distinct arm and hand islands for '+side)
    tube_island=max(components,key=lambda group:max(v.co.z for v in group))
    discard=[v for group in components if group is not tube_island for v in group]
    bmesh.ops.delete(bm,geom=discard,context='VERTS');bm.to_mesh(tube.data);bm.free();tube.data.update()
    for mod in list(tube.modifiers):
        if mod.type=='DECIMATE':tube.modifiers.remove(mod)
    tube['partSlot']='Arm.'+side;tube['attachment']='UpperArm.'+side
    archive.objects.link(obj);model.objects.unlink(obj)

# Bone names and mesh names are stable module identifiers. Each finger uses a
# rigid single-segment joint; it can curl as a unit but has no knuckle joints.
fingers=('Index','Middle','Ring','Pinky','Thumb')
positions={}
for side,sign in (('L',1),('R',-1)):
    centre=sign*.1815
    for name,dx,z in [('Index',-.018,.2765),('Middle',-.006,.274),('Ring',.006,.2755),('Pinky',.018,.279)]:
        positions[(side,name)]=(centre+sign*dx,-.006,z)
    positions[(side,'Thumb')]=(centre-sign*.029,-.021,.298)

if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for (side,name),(x,y,z) in positions.items():
    bone=rig.data.edit_bones.new('Finger.'+name+'.'+side)
    if name=='Thumb':
        sign=1 if side=='L' else -1
        bone.head=(x+sign*.007,y,z+.010);bone.tail=(x-sign*.007,y-.003,z-.010)
    else:
        bone.head=(x,y,z+.015);bone.tail=(x,y,z-.015)
    bone.parent=rig.data.edit_bones['UpperArm.'+side]
bpy.ops.object.mode_set(mode='OBJECT')

def piece(name,location,scale,material,bone,slot,rotation=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=10,location=location)
    obj=bpy.context.object
    for coll in list(obj.users_collection):coll.objects.unlink(obj)
    model.objects.link(obj);obj.name=name;obj.parent=root
    obj.scale=scale
    if rotation is not None:obj.rotation_euler=rotation
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for poly in obj.data.polygons:poly.use_smooth=True
    obj.data.materials.append(material)
    group=obj.vertex_groups.new(name=bone);group.add(list(range(len(obj.data.vertices))),1.0,'REPLACE')
    modifier=obj.modifiers.new('Visitor armature','ARMATURE');modifier.object=rig
    obj['partSlot']=slot;obj['attachment']=bone
    return obj

for side,sign in (('L',1),('R',-1)):
    mat=materials[side];upper='UpperArm.'+side
    piece('Wrist.'+side,(sign*.171,-.002,.336),(.027,.029,.024),mat,upper,'Wrist_'+side)
    piece('Palm.'+side,(sign*.1815,-.006,.302),(.028,.031,.031),mat,upper,'Palm_'+side)
    for name in fingers:
        pos=positions[(side,name)]
        if name=='Thumb':
            size=(.011,.014,.020);rotation=(0,sign*.40,0)
        else:
            size=(.009,.013,.019 if name!='Pinky' else .016);rotation=None
        piece('Finger.'+name+'.'+side,pos,size,mat,'Finger.'+name+'.'+side,'Finger_'+name+'_'+side,rotation)
bpy.context.view_layer.update()
result={'added_finger_bones':10,'rig_bones':len(rig.data.bones),'finger_meshes':10,
        'palm_meshes':2,'wrist_meshes':2,'arm_tubes':2,'archived_originals':[o.name for o in old.values()]}
