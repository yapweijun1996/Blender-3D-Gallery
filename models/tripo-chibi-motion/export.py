"""Import the original Tripo ZIP and export the motion edition with Blender."""

from math import floor, radians
from pathlib import Path
from runpy import run_path
from tempfile import TemporaryDirectory

import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "tripo-convert-405dc0a0" / "export.py"
RUN_FBX = HERE / "source" / "tripo-preset-run-b8bd37fe.fbx"
PREFIX = "mixamorig:"


def floor_height(mesh):
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    surface = evaluated.to_mesh()
    try:
        return min((evaluated.matrix_world @ vertex.co).z for vertex in surface.vertices)
    finally:
        evaluated.to_mesh_clear()


def author_actions(rig, mesh, clips):
    names = sorted({name for keys in clips.values() for _, (rotations, _) in keys
                    for name in rotations})
    bones = {name: rig.pose.bones[PREFIX + name] for name in names}
    bind = {name: rig.matrix_world @ bone.bone.matrix_local for name, bone in bones.items()}
    frames = {name: matrix.to_quaternion() for name, matrix in bind.items()}
    hips = bones["Hips"]
    hips_inverse = bind["Hips"].to_3x3().inverted()
    animation = rig.animation_data
    scene = bpy.context.scene

    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
        bone.rotation_mode = "QUATERNION"
    bpy.context.view_layer.update()

    for name, keys in clips.items():
        # Evaluate contact heights with no active Action or NLA influence.
        samples = []
        for frame, (rotations, lift) in keys:
            hips.location = (0, 0, 0)
            for joint, bone in bones.items():
                angles = rotations.get(joint, (0, 0, 0))
                rotation = Euler(tuple(map(radians, angles)), "XYZ").to_quaternion()
                basis = frames[joint]
                bone.rotation_quaternion = basis.inverted() @ rotation @ basis
            bpy.context.view_layer.update()
            height = lift - floor_height(mesh)
            samples.append((frame, hips_inverse @ Vector((0, 0, height)),
                            [bone.rotation_quaternion.copy() for bone in bones.values()]))
        # Use exactly the same transform data at both ends of the cycle.
        samples[-1] = (samples[-1][0], *samples[0][1:])

        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        animation.action = action
        for frame, location, rotations in samples:
            hips.location = location
            hips.keyframe_insert("location", frame=frame, group=hips.name)
            for bone, rotation in zip(bones.values(), rotations):
                bone.rotation_quaternion = rotation
                bone.keyframe_insert("rotation_quaternion", frame=frame, group=bone.name)
        slot = animation.action_slot
        bag = action.layers[0].strips[0].channelbag(slot)
        for curve in bag.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = "BEZIER"
                key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"
            curve.update()
        animation.action = None
        scene.frame_set(0)
        yield name, action, slot


def sample_preset_run(rig, mesh):
    scene = bpy.context.scene
    fps, fps_base = scene.render.fps, scene.render.fps_base
    existing = set(bpy.data.user_map())
    bones = list(rig.pose.bones)
    hips = rig.pose.bones[PREFIX + "Hips"]
    target_bind = rig.matrix_world @ hips.bone.matrix_local
    hips_inverse = target_bind.to_3x3().inverted()
    try:
        bpy.ops.import_scene.fbx(filepath=str(RUN_FBX), use_image_search=False)
        imported = set(bpy.data.user_map()) - existing
        source, = (obj for obj in imported if isinstance(obj, bpy.types.Object)
                   and obj.type == "ARMATURE")
        source_mesh, = (obj for obj in imported if isinstance(obj, bpy.types.Object)
                        and obj.type == "MESH")
        source_bones = source.pose.bones
        if {bone.name: bone.parent and bone.parent.name for bone in source_bones} != {
            bone.name: bone.parent and bone.parent.name for bone in bones
        }:
            raise ValueError("Preset Run must have the original Mixamo joint hierarchy")
        action = source.animation_data.action
        start, end = action.frame_range
        source_fps = scene.render.fps / scene.render.fps_base
        if not action.name.endswith("|Armature|run") or (start, end, source_fps) != (1, 38, 30):
            raise ValueError("Expected the Tripo Run Action on frames 1–38 at 30 fps")

        source_hips = source_bones[hips.name]
        source_bind = source.matrix_world @ source_hips.bone.matrix_local
        # The joint names match, but their rest axes differ. Express each local
        # pose delta in the corresponding target basis through world rest axes.
        basis_changes = [
            (rig.matrix_world @ bone.bone.matrix_local).to_quaternion().inverted()
            @ (source.matrix_world @ source_bones[bone.name].bone.matrix_local).to_quaternion()
            for bone in bones
        ]
        duration = (end - start) / source_fps
        last_frame = round(duration * fps / fps_base)
        samples = []
        for frame in range(last_frame + 1):
            seconds = duration * frame / last_frame
            source_frame = start + seconds * source_fps
            scene.frame_set(floor(source_frame), subframe=source_frame % 1)
            rotations = [
                (basis @ source_bones[bone.name].matrix_basis.to_quaternion() @ basis.inverted())
                .normalized()
                for bone, basis in zip(bones, basis_changes)
            ]
            height = (source.matrix_world @ source_hips.head).z - source_bind.translation.z
            # The source soles sit about 1 cm below zero on contact. Clearance
            # above that level retains the flight phases after grounding the skin.
            clearance = max(0, floor_height(source_mesh) + .010)
            samples.append((height, clearance, rotations))

        # Blend the final three frame intervals to close this preset's seam.
        first_height, first_clearance, first_rotations = samples[0]
        keys = []
        for frame, (height, clearance, rotations) in enumerate(samples):
            if frame > last_frame - 3:
                weight = (frame - (last_frame - 3)) / 3
                weight = weight * weight * (3 - 2 * weight)
                height += (first_height - height) * weight
                clearance += (first_clearance - clearance) * weight
                rotations = [rotation.slerp(first, weight)
                             for rotation, first in zip(rotations, first_rotations)]
            if keys:
                for rotation, previous in zip(rotations, keys[-1][1]):
                    rotation.make_compatible(previous)
            for bone, rotation in zip(bones, rotations):
                bone.rotation_quaternion = rotation
            hips.location = hips_inverse @ Vector((0, 0, height))
            bpy.context.view_layer.update()
            # Leave 1.5 mm of margin for interpolation between stance samples.
            correction = clearance + .0015 - floor_height(mesh)
            keys.append((hips.location + hips_inverse @ Vector((0, 0, correction)), rotations))
        keys[-1] = keys[0]
        return keys
    finally:
        bpy.data.batch_remove(ids=set(bpy.data.user_map()) - existing)
        scene.render.fps, scene.render.fps_base = fps, fps_base
        scene.frame_set(0)


def author_preset_run(rig, mesh):
    keys = sample_preset_run(rig, mesh)
    action = bpy.data.actions.new("run_in_place")
    action.use_fake_user = True
    animation = rig.animation_data
    animation.action = action
    hips = rig.pose.bones[PREFIX + "Hips"]
    for frame, (location, rotations) in enumerate(keys):
        hips.location = location
        hips.keyframe_insert("location", frame=frame, group=hips.name)
        for bone, rotation in zip(rig.pose.bones, rotations):
            bone.rotation_quaternion = rotation
            bone.keyframe_insert("rotation_quaternion", frame=frame, group=bone.name)
    slot = animation.action_slot
    for curve in action.layers[0].strips[0].channelbag(slot).fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    animation.action = None
    return "run", action, slot


def export_motion(directory):
    # Reuse the source importer's exact path allowlist and regular-file checks.
    original = run_path(str(SOURCE))
    rig, mesh, walk = original["import_character"](directory)
    if len(rig.pose.bones) != 65:
        raise ValueError("Expected the original 65-joint rig")

    # Match the original export's scene-root skin and preserve its binding.
    world = mesh.matrix_world.copy()
    mesh.parent = None
    mesh.matrix_world = world

    animation = rig.animation_data
    walk_slot = animation.action_slot
    animation.action = None
    for track in list(animation.nla_tracks):
        animation.nla_tracks.remove(track)
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_set(0)
    clips = run_path(str(HERE / "poses.py"))["motion_keys"]()
    actions = list(author_actions(rig, mesh, clips))
    run = author_preset_run(rig, mesh)
    for clip_name, action, slot in [*actions, run, ("walk", walk, walk_slot)]:
        track = animation.nla_tracks.new()
        track.name = clip_name
        start, end = action.frame_range
        strip = track.strips.new(clip_name, int(start), action)
        strip.action_slot = slot
        strip.action_frame_start = start
        strip.action_frame_end = end
        strip.extrapolation = "NOTHING"

    # Establish the same rest transform used by the single-clip source export.
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    bpy.ops.file.pack_all()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (rig, mesh):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=str(HERE / "motion.glb"), export_format="GLB",
                              use_selection=True, export_animations=True,
                              export_animation_mode="NLA_TRACKS")

    for track in animation.nla_tracks:
        track.mute = True
    _, animation.action, animation.action_slot = actions[0]
    scene.frame_end = int(animation.action.frame_range[1])
    scene.frame_set(0)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "motion.blend"))


if __name__ == "__main__":
    with TemporaryDirectory(prefix="tripo_motion_fbx_") as source_directory:
        export_motion(source_directory)
