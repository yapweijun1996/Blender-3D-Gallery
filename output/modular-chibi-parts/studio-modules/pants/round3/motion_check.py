"""Check the exported pants against the Blender-evaluated master at half frames.

Usage: blender -b --python motion_check.py -- MASTER MOTION_FIXED GARMENT OUT
"""

import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils.bvhtree import BVHTree


CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
FIXED = Path(__file__).resolve().parents[3] / "body-fix/motion_fixed.glb"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(paths):
    master, motion, garment, _ = paths
    if motion.resolve() != FIXED:
        raise ValueError(f"Use the corrected actions at {FIXED}")
    bpy.ops.wm.open_mainfile(filepath=str(master), use_scripts=False, load_ui=False)
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(garment))
    incoming = set(scene.objects) - before
    pants, = [obj for obj in bpy.context.selected_objects if obj in incoming and obj.type == "MESH"]
    pants.parent = None
    for obj in incoming - {pants}:
        bpy.data.objects.remove(obj, do_unlink=True)
    pants.modifiers.clear()
    pants.parent = arm
    pants.modifiers.new("Master armature", "ARMATURE").object = arm
    before = set(scene.objects)
    incoming_actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(motion))
    actions = {action.name: action for action in set(bpy.data.actions) - incoming_actions}
    assert set(actions) == set(CLIPS)
    source, = [obj for obj in set(scene.objects) - before if obj.type == "ARMATURE"]
    assert len(arm.data.bones) == 65
    assert set(arm.data.bones.keys()) == set(source.data.bones.keys())
    for obj in scene.objects:
        if obj not in (arm, body, pants):
            obj.hide_viewport = obj.hide_render = True
    arm.animation_data_create()
    return scene, arm, body, pants, actions


def surfaces(obj, depsgraph, faces=True):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        if faces:
            mesh.calc_loop_triangles()
            return points, [face.vertices[:] for face in mesh.loop_triangles]
        return points, None
    finally:
        evaluated.to_mesh_clear()


def measures(body_tree, points):
    minimum, inside, worst = math.inf, 0, None
    for index, point in enumerate(points):
        nearest, normal, face, _ = body_tree.find_nearest(point)
        distance = (point - nearest).dot(normal)
        inside += distance < 0
        if distance < minimum:
            minimum, worst = distance, (index, face)
    return {"max_verts_inside": inside, "min_signed_distance_m": minimum,
            "minimum_garment_vertex": worst[0], "nearest_body_triangle": worst[1]}


def poses(scene, arm, actions):
    modes = tuple(bone.rotation_mode for bone in arm.pose.bones)
    arm.animation_data.action = None
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    yield "rest", 1.0
    for clip in CLIPS:
        action = actions[clip]
        arm.animation_data.action = action
        arm.animation_data.action_slot = action.slots[0]
        start, end = action.frame_range
        times = {start, end}
        times.update(i / 2 for i in range(math.ceil(2 * start), math.floor(2 * end) + 1))
        for frame in sorted(times):
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            yield clip, frame
    assert tuple(bone.rotation_mode for bone in arm.pose.bones) == modes


def summarize(frames, field):
    worst = min(frames, key=lambda frame: frame["min_signed_distance_m"])
    return {"samples": len(frames), field: max(frame[field] for frame in frames),
            "min_signed_distance_m": worst["min_signed_distance_m"],
            "minimum_frame": worst["frame"],
            "peak_frame": max(frames, key=lambda frame: frame[field])["frame"]}


def check(paths, stem="motion_check", pairs=None):
    scene, arm, body, pants, actions = load(paths)
    counts = {name: [] for name in ("rest", *CLIPS)}
    field = "tri_overlap_pairs" if pairs else "max_verts_inside"
    state = pairs(body, paths) if pairs else None
    for clip, frame in poses(scene, arm, actions):
        graph = bpy.context.evaluated_depsgraph_get()
        body_points, body_faces = surfaces(body, graph)
        pants_points, pants_faces = surfaces(pants, graph, faces=bool(pairs))
        tree = BVHTree.FromPolygons(body_points, body_faces, all_triangles=True, epsilon=0)
        row = {"frame": frame, **measures(tree, pants_points)}
        if state:
            row.update(state(clip, frame, tree, pants_points, pants_faces))
        counts[clip].append(row)
    lines = []
    clips = {}
    for clip, frames in counts.items():
        summary = summarize(frames, field)
        int_frames = [row for row in frames if row["frame"].is_integer()]
        half_frames = [row for row in frames if row["frame"] % 1 == .5]
        summary["integer_frames"] = summarize(int_frames, field)
        if half_frames:
            summary["half_frames"] = summarize(half_frames, field)
        summary["frames"] = frames
        clips[clip] = summary
        lines.append(f"RESULT {clip} {field} {summary[field]} "
                     f"min_signed_dist {summary['min_signed_distance_m']:.9f} "
                     f"samples {len(frames)} min_frame {summary['minimum_frame']:g}")
    report = {"hashes": {label: digest(path) for label, path in zip(
        ("master", "motion", "garment"), paths)}, "clips": clips}
    out = paths[3]
    (out / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / f"{stem}.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    check(tuple(Path(arg) for arg in sys.argv[sys.argv.index("--") + 1:]))
