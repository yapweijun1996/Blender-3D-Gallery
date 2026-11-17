"""Import the supplied animated FBX and add simple, editable animation clips."""
import math
import os
import sys
import bpy
from mathutils import Quaternion, Vector

if '--' not in sys.argv:
    raise SystemExit('Use: blender -b --python create_motion.py -- path/to/animated.fbx')
source = sys.argv[sys.argv.index('--') + 1]
out = os.path.dirname(os.path.abspath(__file__))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=source)
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
# The armature modifier still drives the mesh when it is a scene root.
world_matrix = mesh.matrix_world.copy()
mesh.parent = None
mesh.matrix_world = world_matrix
walk = rig.animation_data.action
if walk is None or len(bpy.data.actions) != 1:
    raise ValueError('Expected one imported walking action')
source_walk = walk
scene = bpy.context.scene
scene.render.fps = 24
# Frames 11–40 are the closest matching consecutive gait poses in this source.
samples = []
for frame in range(11, 41):
    scene.frame_set(frame)
    samples.append({bone.name: (bone.rotation_quaternion.copy(), bone.location.copy()) for bone in rig.pose.bones})
rig.animation_data_clear()
bpy.data.actions.remove(source_walk)

# Convert an axis in the model rest space to the bone's local rest coordinates.
def set_angle(name, axis, degrees):
    bone = rig.pose.bones['mixamorig:' + name]
    local_axis = bone.bone.matrix_local.to_quaternion().inverted() @ Vector(axis)
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = Quaternion(local_axis, math.radians(degrees))

def key_action(name, frames, pose):
    rig.animation_data_clear()
    for frame in frames:
        for bone in rig.pose.bones:
            bone.matrix_basis.identity()
        pose(frame)
        for bone_name in ('Hips', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'RightUpLeg', 'RightLeg', 'RightFoot', 'LeftArm', 'RightArm', 'LeftForeArm', 'Head', 'Neck', 'Spine2'):
            bone = rig.pose.bones['mixamorig:' + bone_name]
            bone.rotation_mode = 'QUATERNION'
            bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone.name)
            if bone_name == 'Hips':
                bone.keyframe_insert(data_path='location', frame=frame, group=bone.name)
    action = rig.animation_data.action
    action.name = name
    action.use_fake_user = True
    return action

def idle_pose(frame):
    sway = {1: 0, 13: 2, 25: 0, 37: -2, 49: 0}[frame]
    set_angle('LeftArm', (0, 1, 0), 65)
    set_angle('RightArm', (0, 1, 0), -65)
    set_angle('Head', (0, 1, 0), sway)
    set_angle('Spine2', (0, 1, 0), -sway / 2)

def wave_pose(frame):
    upper = {1: 65, 13: 15, 25: -18, 37: -10, 49: -18, 61: 15, 73: 65}[frame]
    elbow = {1: 0, 13: -8, 25: -15, 37: -27, 49: -15, 61: -8, 73: 0}[frame]
    set_angle('LeftArm', (0, 1, 0), upper)
    set_angle('RightArm', (0, 1, 0), -65)
    set_angle('LeftForeArm', (0, 1, 0), elbow)
    set_angle('Head', (0, 1, 0), 0)
    set_angle('Spine2', (0, 1, 0), 0)

def in_place_sample(index, seam, running=False):
    sample = samples[index]
    first = samples[0]
    for bone in rig.pose.bones:
        q, loc = sample[bone.name]
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = q.slerp(first[bone.name][0], seam)
        if bone.name in ('mixamorig:Head', 'mixamorig:Neck'):
            # The supplied motion tips the face upward; retain the neutral rest orientation.
            bone.rotation_quaternion = Quaternion((1, 0, 0, 0))
        if running and any(part in bone.name for part in ('UpLeg', 'Leg', 'Foot')):
            axis, angle = bone.rotation_quaternion.to_axis_angle()
            bone.rotation_quaternion = Quaternion(axis, angle * 1.25)
        if bone.name == 'mixamorig:Hips':
            initial = first[bone.name][1]
            # Source FBX bone-local X and Z carry horizontal displacement; Y is vertical.
            bone.location = Vector((0, loc.y * (1 - seam) + initial.y * seam, 0))
            if running:
                # Two small suspension phases make this a stylized jog, not a speed change alone.
                height = .04 * math.sin(2 * math.pi * index / 29) ** 2
                bone.location += bone.bone.matrix_local.to_quaternion().inverted() @ Vector((0, 0, height))


def bake_gait(name, steps, running=False):
    rig.animation_data_clear()
    for step in range(steps + 1):
        index = min(29, round(step * 29 / steps))
        seam = max(0.0, (step - (steps - 4)) / 4)
        in_place_sample(index, seam, running)
        for bone in rig.pose.bones:
            bone.keyframe_insert(data_path='rotation_quaternion', frame=step + 1, group=bone.name)
            if bone.name == 'mixamorig:Hips':
                bone.keyframe_insert(data_path='location', frame=step + 1, group=bone.name)
    action = rig.animation_data.action
    action.name = name
    action.use_fake_user = True
    return action



def bake_foot_contacts(action, steps, stance_fraction, stride, lift):
    """Bake level foot contacts; forward runtime motion cancels the stance trajectory."""
    rig.animation_data.action = action
    targets = {}
    poles = []
    target_actions = []
    for side in ('Left', 'Right'):
        foot = rig.data.bones['mixamorig:' + side + 'Foot']
        rest = rig.matrix_world @ foot.head_local
        target = bpy.data.objects.new('FootTarget_' + side, None)
        bpy.context.collection.objects.link(target)
        target.rotation_mode = 'QUATERNION'
        target.rotation_quaternion = rig.matrix_world.to_quaternion() @ foot.matrix_local.to_quaternion()
        targets[side] = (target, rest)
        constraint = rig.pose.bones['mixamorig:' + side + 'Leg'].constraints.new('IK')
        constraint.target = target
        constraint.chain_count = 2
        pole = bpy.data.objects.new('KneePole_' + side, None)
        bpy.context.collection.objects.link(pole)
        pole.location = (rest.x, rest.y - 1, .18)
        constraint.pole_target = pole
        constraint.pole_angle = 0
        poles.append(pole)
        constraint = rig.pose.bones[foot.name].constraints.new('COPY_ROTATION')
        constraint.target = target
        constraint.target_space = 'WORLD'
        constraint.owner_space = 'WORLD'

    for frame in range(1, steps + 2):
        scene.frame_set(frame)
        phase = (frame - 1) / steps
        hip = rig.pose.bones['mixamorig:Hips']
        hip.location = hip.bone.matrix_local.to_quaternion().inverted() @ Vector((0, 0, -.025))
        hip.keyframe_insert(data_path='location', frame=frame, group=hip.name)
        for side, offset in (('Left', 0), ('Right', .5)):
            for suffix in ('ToeBase', 'Toe_End'):
                toe = rig.pose.bones['mixamorig:' + side + suffix]
                toe.matrix_basis.identity()
                toe.rotation_mode = 'QUATERNION'
                toe.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=toe.name)
            target, rest = targets[side]
            position = (phase + offset) % 1
            if position < stance_fraction:
                forward = -stride / 2 + stride * position / stance_fraction
                height = 0
            else:
                swing = (position - stance_fraction) / (1 - stance_fraction)
                forward = stride / 2 - stride * swing
                height = lift * math.sin(math.pi * swing)
            target.location = (rest.x, rest.y + forward, rest.z + height)
            target.keyframe_insert(data_path='location', frame=frame)

    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    for bone in rig.pose.bones:
        bone.select = False
    for side in ('Left', 'Right'):
        for suffix in ('UpLeg', 'Leg', 'Foot'):
            rig.pose.bones['mixamorig:' + side + suffix].select = True
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(frame_start=1, frame_end=steps + 1, only_selected=True,
                     visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    for target, _ in targets.values():
        target_actions.append(target.animation_data.action)
        bpy.data.objects.remove(target, do_unlink=True)
    for pole in poles:
        bpy.data.objects.remove(pole, do_unlink=True)
    for target_action in target_actions:
        if target_action and target_action.users == 0:
            bpy.data.actions.remove(target_action)


def set_hip_height(height):
    bone = rig.pose.bones['mixamorig:Hips']
    bone.location = bone.bone.matrix_local.to_quaternion().inverted() @ Vector((0, 0, height))


def jump_pose(frame):
    height = {1: 0, 7: -.025, 13: .09, 19: .18, 25: .09, 31: -.02, 37: 0}[frame]
    set_hip_height(height)
    set_angle('LeftArm', (0, 1, 0), 65)
    set_angle('RightArm', (0, 1, 0), -65)
    bend = {1: 0, 7: 20, 13: 10, 19: 8, 25: 10, 31: 18, 37: 0}[frame]
    for side in ('Left', 'Right'):
        set_angle(side + 'UpLeg', (1, 0, 0), -bend)
        set_angle(side + 'Leg', (1, 0, 0), bend * 1.5)


def sit_pose(frame):
    factor = {1: 0, 13: .5, 25: 1, 49: 1, 61: .5, 73: 0}[frame]
    set_hip_height(-.13 * factor)
    set_angle('LeftArm', (0, 1, 0), 65)
    set_angle('RightArm', (0, 1, 0), -65)
    for side in ('Left', 'Right'):
        set_angle(side + 'UpLeg', (1, 0, 0), -70 * factor)
        set_angle(side + 'Leg', (1, 0, 0), 75 * factor)

walk = bake_gait('Walk_InPlace', 29)
run = bake_gait('Run_InPlace', 20, running=True)
bake_foot_contacts(walk, 29, .60, .09, .035)
bake_foot_contacts(run, 20, .45, .105, .045)
idle = key_action('Idle', [1, 13, 25, 37, 49], idle_pose)
wave = key_action('Wave', [1, 13, 25, 37, 49, 61, 73], wave_pose)
jump = key_action('Jump', [1, 7, 13, 19, 25, 31, 37], jump_pose)
sit = key_action('Sit', [1, 13, 25, 49, 61, 73], sit_pose)
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
for action in (idle, walk, run, jump, sit, wave):
    track = rig.animation_data.nla_tracks.new()
    track.name = action.name
    track.strips.new(action.name, 1, action)
    track.mute = True

# Bake vertical corrections against the actual deformed mesh; horizontal root motion stays zero.
hip = rig.pose.bones['mixamorig:Hips']
up_local = hip.bone.matrix_local.to_quaternion().inverted() @ Vector((0, 0, 1))
for _ in range(3):
    for action in (walk, run, jump, sit):
        rig.animation_data.action = action
        corrections = []
        for frame in range(int(action.frame_range[0]), int(action.frame_range[1]) + 1):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            evaluated = mesh.evaluated_get(graph)
            deformed = evaluated.to_mesh()
            bottom = min((evaluated.matrix_world @ vertex.co).z for vertex in deformed.vertices)
            evaluated.to_mesh_clear()
            corrections.append((frame, hip.location.copy() + up_local * max(0, -bottom)))
        for frame, location in corrections:
            hip.location = location
            hip.keyframe_insert(data_path='location', frame=frame, group=hip.name)
rig.animation_data.action = idle
scene.frame_start = 1
scene.frame_end = 120
scene.frame_set(1)
for image in bpy.data.images:
    if image.source == 'FILE' and not image.packed_file:
        image.pack()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'character-motion.blend'), compress=True)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
mesh.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=os.path.join(out, 'character-motion.glb'), export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='ACTIONS', export_anim_slide_to_zero=True)
print('Actions:', [(a.name, tuple(a.frame_range)) for a in bpy.data.actions])
