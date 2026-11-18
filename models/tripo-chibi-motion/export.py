"""Import the original Tripo ZIP and export the motion edition with Blender."""

from math import radians
from pathlib import Path
from runpy import run_path
from tempfile import TemporaryDirectory

import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "tripo-convert-405dc0a0" / "export.py"
PREFIX = "mixamorig:"


def floor_height(mesh):
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    surface = evaluated.to_mesh()
    try:
        return min((evaluated.matrix_world @ vertex.co).z for vertex in surface.vertices)
    finally:
        evaluated.to_mesh_clear()


def align_run_stance(scene, mesh, hips, hips_inverse, bag, keys):
    # Keep the sole on the floor between pairs of grounded phase keys.
    samples = []
    for (start, (_, lift)), (end, (_, next_lift)) in zip(keys, keys[1:]):
        if lift or next_lift:
            continue
        for frame in range(start + 1, end):
            scene.frame_set(frame)
            correction = hips_inverse @ Vector((0, 0, floor_height(mesh)))
            samples.append((frame, hips.location - correction))

    for axis in range(3):
        curve = bag.fcurves.find(hips.path_from_id("location"), index=axis)
        for frame, position in samples:
            key = curve.keyframe_points.insert(frame, position[axis])
            key.interpolation = "BEZIER"
            key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"
        curve.update()


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
        if name == "run_in_place":
            align_run_stance(scene, mesh, hips, hips_inverse, bag, keys)
        animation.action = None
        scene.frame_set(0)
        yield name, action, slot


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
    for name, action, slot in [*actions, ("walk", walk, walk_slot)]:
        clip_name = "run" if name == "run_in_place" else name
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
