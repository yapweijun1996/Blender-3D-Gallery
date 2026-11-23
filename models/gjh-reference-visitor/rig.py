"""Add a simple poseable rig and draft actions to the current GJH visitor scene.

Run in the connected Blender after build.py, before export. Geometry and the
scaled placement root stay editable. This is a first-pass rig; joint separation,
contact and visual animation quality must be checked on the exported model.
"""
import bpy
import math
from mathutils import Vector

scene = bpy.data.scenes['GJH Reference Visitor']
bpy.context.window.scene = scene
model = next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
root = next(o for o in model.objects if o.name == 'GJH_Visitor')
if any(o.type == 'ARMATURE' for o in model.objects):
    raise RuntimeError('Model already has an armature; start from an unrigged build')

# Meshes have different origins; retain their transforms during curve conversion.
for obj in list(model.objects):
    if obj.type == 'CURVE':
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')

arm = bpy.data.armatures.new('Visitor Humanoid')
rig = bpy.data.objects.new('Visitor Rig', arm)
model.objects.link(rig)
rig.parent = root
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
positions = {
    'Root': ((0, 0, .30), (0, 0, .35), None),
    'Spine': ((0, 0, .35), (0, 0, .50), 'Root'),
    'Head': ((0, 0, .56), (0, 0, .70), 'Spine'),
}
for s, label in ((1, 'L'), (-1, 'R')):
    positions['UpperArm.'+label] = ((s*.090, .003, .49), (s*.090, .003, .55), 'Spine')
    positions['UpperLeg.'+label] = ((s*.068, .006, .235), (s*.068, .006, .285), 'Root')
    positions['LowerLeg.'+label] = ((s*.068, .006, .155), (s*.068, .006, .205), 'UpperLeg.'+label)
for name, (head, tail, _) in positions.items():
    b = arm.edit_bones.new(name)
    b.head, b.tail = head, tail
for name, (_, _, parent) in positions.items():
    if parent:
        arm.edit_bones[name].parent = arm.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front = True
bpy.context.view_layer.update()

# Bind the face and hair as rigid parts; blend the lower leg around the knee.
# The sweatshirt torso and its original short upper sleeves are one mesh, so
# shoulders cannot deform seamlessly without rebuilding that mesh.
for obj in list(model.objects):
    if obj.type != 'MESH':
        continue
    name = obj.name
    if name.startswith(('Head', 'Hair')):
        bone = 'Head'
    elif name.startswith(('Arm.L', 'Arm.R')):
        bone = 'UpperArm.' + ('L' if name.startswith('Arm.L') else 'R')
    elif name.startswith(('Long sleeve', 'Purple cuff')):
        bone = 'UpperArm.' + ('L' if obj.location.x > 0 else 'R')
    elif name.startswith(('Leg.L', 'Leg.R')):
        side = 'L' if name.startswith('Leg.L') else 'R'
        upper = obj.vertex_groups.new(name='UpperLeg.' + side)
        lower = obj.vertex_groups.new(name='LowerLeg.' + side)
        for v in obj.data.vertices:
            z = (obj.matrix_local @ v.co).z
            w = max(0., min(1., (.18-z)/.05))
            if w < 1: upper.add([v.index], 1-w, 'REPLACE')
            if w > 0: lower.add([v.index], w, 'REPLACE')
        bone = None
    elif name.startswith(('Shoe.L', 'Shoe.R')):
        bone = 'LowerLeg.' + ('L' if name.startswith('Shoe.L') else 'R')
    elif name.startswith(('Shorts', 'Cargo side pocket')):
        bone = 'Root'
    else:
        bone = 'Spine'
    if bone:
        vg = obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    mod = obj.modifiers.new('Visitor armature', 'ARMATURE')
    mod.object = rig

rig.animation_data_create()
scene.render.fps = 30
for clip, duration in [('idle', 60), ('walk', 30), ('run', 20), ('sit', 30), ('stand_up', 30)]:
    action = bpy.data.actions.new(clip)
    rig.animation_data.action = action
    for frame in range(1, duration + 2):
        t = (frame-1)/duration
        phase = t*math.tau
        ease = t*t*(3-2*t)
        for b in rig.pose.bones:
            b.rotation_mode = 'XYZ'
            b.rotation_euler = (0, 0, 0)
            b.location = (0, 0, 0)
        rig.pose.bones['Spine'].rotation_euler.y = .025*math.sin(phase)
        for side, sign in (('L', 1), ('R', -1)):
            arm_b = rig.pose.bones['UpperArm.'+side]
            leg = rig.pose.bones['UpperLeg.'+side]
            shin = rig.pose.bones['LowerLeg.'+side]
            if clip in ('walk', 'run'):
                amt = .30 if clip == 'walk' else .53
                swing = math.sin(phase)*sign
                leg.rotation_euler.x = amt*swing
                shin.rotation_euler.x = -.6*amt*max(0, swing)
                arm_b.rotation_euler.x = -amt*.8*swing
            elif clip in ('sit', 'stand_up'):
                amount = ease if clip == 'sit' else 1-ease
                leg.rotation_euler.x = -1.0*amount
                shin.rotation_euler.x = 1.0*amount
                arm_b.rotation_euler.x = -.22*amount
            else:
                arm_b.rotation_euler.x = .02*math.sin(phase)*sign
        for b in rig.pose.bones:
            b.keyframe_insert(data_path='rotation_euler', frame=frame, group=b.name)
    rig.animation_data.action = None
    track = rig.animation_data.nla_tracks.new()
    track.name = clip
    track.strips.new(clip, 1, action)
    track.mute = True
scene.frame_set(1)
bpy.context.view_layer.update()
result = {'bones': len(arm.bones), 'actions': [t.name for t in rig.animation_data.nla_tracks], 'bound_meshes': sum(o.type == 'MESH' for o in model.objects), 'note': 'Draft rig; visual and runtime validation still required.'}
