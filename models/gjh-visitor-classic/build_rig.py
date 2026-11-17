"""Classic visitor skeleton and baked, controller-free glTF actions."""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector


FPS = 30
CLIP_FRAMES = {"idle": 66, "walk": 30, "run": 20, "sit": 36, "stand_up": 36}
# Stance travel, fraction of the cycle in stance, maximum shoe lift (metres).
GAITS = {"walk": (.115, .60, .034), "run": (.155, .40, .059)}
FINGERS = {
    "Thumb": ((.210, -.052, .446), (.202, -.064, .424)),
    "Index": ((.217, -.045, .428), (.214, -.051, .402)),
    "Middle": ((.228, -.039, .425), (.226, -.047, .397)),
    "Ring": ((.238, -.031, .427), (.237, -.039, .401)),
    "Pinky": ((.246, -.021, .431), (.245, -.026, .408)),
}


def build_rig():
    collection = bpy.context.collection
    armature = bpy.data.armatures.new("Classic visitor skeleton")
    rig = bpy.data.objects.new("Classic visitor rig", armature)
    collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, head, tail, parent=None):
        item = armature.edit_bones.new(name)
        item.head = head
        item.tail = tail
        if parent:
            item.parent = armature.edit_bones[parent]
        return item

    bone("Root", (0, 0, 0), (0, 0, .08)).use_deform = False
    bone("Hips", (0, 0, .334), (0, 0, .425), "Root")
    bone("Spine", (0, 0, .425), (0, 0, .589), "Hips")
    bone("Chest", (0, 0, .589), (0, 0, .762), "Spine")
    bone("Head", (0, 0, .762), (0, 0, 1.248), "Chest")
    for side, mirror in (("L", 1), ("R", -1)):
        def pair(name, a, b, parent):
            def point(v):
                return (mirror * v[0], v[1], v[2])
            bone(f"{name}.{side}", point(a), point(b), parent)

        pair("UpperArm", (.118, 0, .709), (.182, -.006, .583), "Chest")
        pair("Forearm", (.182, -.006, .583), (.222, -.022, .478), f"UpperArm.{side}")
        pair("Hand", (.222, -.022, .478), (.229, -.029, .426), f"Forearm.{side}")
        for name, (start, tip) in FINGERS.items():
            pair(name, start, tip, f"Hand.{side}")
        pair("Thigh", (.092, 0, .334), (.095, -.002, .219), "Hips")
        pair("Shin", (.095, -.002, .219), (.099, 0, .112), f"Thigh.{side}")
        pair("Foot", (.099, 0, .112), (.099, -.100, .045), f"Shin.{side}")
    bpy.ops.object.mode_set(mode="OBJECT")
    armature.display_type = "STICK"
    rig.show_in_front = False
    return rig


def _ankle_path(phase, gait):
    travel, stance, lift = GAITS[gait]
    if phase < stance:
        return travel * (phase / stance - .5), 0.
    u = (phase - stance) / (1 - stance)
    # Match the constant stance velocity at toe-off and touchdown.
    smooth = u * u * (3 - 2 * u)
    tangent = u * (1 - u) * (1 - 2 * u)
    y = travel * (.5 - smooth + (1 - stance) / stance * tangent)
    return y, lift * math.sin(math.pi * u) ** 2


def _leg_angles(hip, ankle):
    # The knee bends forward. Solving in YZ keeps the stock lateral splay.
    foot_y, foot_z = ankle
    hip_y, hip_z = hip
    dy, dz = foot_y - hip_y, foot_z - hip_z
    distance = math.hypot(dy, dz)
    thigh = math.hypot(.002, .115)
    calf = math.hypot(.002, .107)
    projected = (thigh * thigh - calf * calf + distance * distance) / (2 * distance)
    height = math.sqrt(max(0., thigh * thigh - projected * projected))
    knee_y = hip_y + (projected * dy + height * dz) / distance
    knee_z = hip_z + (projected * dz - height * dy) / distance
    thigh_angle = math.atan2(knee_z - hip_z, knee_y - hip_y) - math.atan2(-.115, -.002)
    calf_angle = math.atan2(foot_z - knee_z, foot_y - knee_y) - math.atan2(-.107, .002)
    return thigh_angle, calf_angle


def _rot(axis, degrees):
    return Quaternion(axis, math.radians(degrees))


def _pose(rig, clip, t):
    phase = math.tau * t
    sit = t * t * (3 - 2 * t) if clip in ("sit", "stand_up") else 0.
    if clip == "stand_up":
        sit = 1 - sit
    gait = clip in GAITS
    run = clip == "run"
    idle = clip == "idle"
    if gait:
        hip_z = (.305 if run else .318) - (.006 if run else .003) * math.cos(2 * phase)
        hip_y = 0.
    else:
        hip_y, hip_z = .101 * sit, .334 - .110 * sit
    hip_translation = Vector((0., hip_y, hip_z - .334))
    rig.pose.bones["Hips"].location = rig.data.bones["Hips"].matrix_local.to_quaternion().inverted() @ hip_translation
    axis_x, axis_y, axis_z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    identity = Quaternion()
    rotations = {"Root": identity, "Hips": identity}
    chest_lean = 3.5 * sit + (10. if run else 3.) * gait + (1.1 * math.sin(phase) if idle else 0.)
    if clip in ("sit", "stand_up"):
        chest_lean += 7.5 * math.sin(math.pi * t) ** 2
    twist = (4. if run else 2.5) * math.cos(phase) if gait else 0.
    rotations["Spine"] = _rot(axis_x, chest_lean * .45) @ _rot(axis_z, twist * .45)
    rotations["Chest"] = _rot(axis_x, chest_lean) @ _rot(axis_z, twist)
    rotations["Head"] = _rot(axis_x, chest_lean * .28) @ _rot(axis_z, twist * .2)
    if idle:
        rotations["Head"] @= _rot(axis_y, .7 * math.sin(phase))
    for side, sign in (("L", 1), ("R", -1)):
        ankle_y, lift = _ankle_path((t + (0 if sign == 1 else .5)) % 1, clip) if gait else (0., 0.)
        thigh, calf = _leg_angles((hip_y, hip_z), (ankle_y, .112 + lift))
        rotations[f"Thigh.{side}"] = Quaternion(axis_x, thigh)
        rotations[f"Shin.{side}"] = Quaternion(axis_x, calf)
        rotations[f"Foot.{side}"] = identity
        swing = sign * math.cos(phase) * (36 if run else 19) if gait else 0.
        if idle:
            swing = sign * math.sin(phase) * 2.
        shoulder = rotations["Chest"] @ _rot(axis_y, sign * 13 * sit) @ _rot(axis_x, swing - 18 * sit)
        elbow = shoulder @ _rot(axis_x, -39 * sit - (42 if run else 13) * gait)
        rotations[f"UpperArm.{side}"] = shoulder
        rotations[f"Forearm.{side}"] = elbow
    for name, absolute in rotations.items():
        pose_bone = rig.pose.bones[name]
        parent = pose_bone.parent
        if not parent or name == "Hips":
            continue
        rest = pose_bone.bone.matrix_local.to_quaternion()
        local = rest.inverted() @ rotations[parent.name].inverted() @ absolute @ rest
        # Quaternions of equivalent rotations may have opposite signs.
        local.make_compatible(pose_bone.rotation_quaternion)
        pose_bone.rotation_quaternion = local.normalized()
    return [rig.pose.bones[n] for n in rotations if n not in ("Root", "Hips")]


def build_actions(rig):
    animation = rig.animation_data_create()
    scene = bpy.context.scene
    scene.render.fps = FPS
    for name, duration in CLIP_FRAMES.items():
        action = bpy.data.actions.new(f"Classic visitor | {name}")
        animation.action = action
        for frame in range(duration + 1):
            moving = _pose(rig, name, frame / duration)
            rig.pose.bones["Hips"].keyframe_insert("location", frame=frame, group="Hips")
            for bone in moving:
                bone.keyframe_insert("rotation_quaternion", frame=frame, group=bone.name)
        slot = animation.action_slot
        animation.action = None
        track = animation.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 0, action)
        strip.action_slot = slot
        track.mute = True
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    scene.frame_start = 0
    scene.frame_end = max(CLIP_FRAMES.values())
    scene.frame_set(0)
    bpy.context.view_layer.update()
