"""Check every integer and half frame of the fixed clips on a fresh GLB import.

Usage in Blender 5: -- <master.blend> <motion_fixed.glb> <garment.glb> <out_dir>
The companion triangle checker uses the same pose binding and output schema.
"""
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys

import bpy
from mathutils.bvhtree import BVHTree


CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
BODY_FIX = Path(__file__).resolve().parents[3] / "body-fix"
TARGET = .0005


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_objects(path):
    existing = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj.name not in existing]


def setup(master, motion, garment):
    bpy.ops.wm.open_mainfile(filepath=str(master), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    arm.animation_data_clear()
    arm.animation_data_create()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    garment_objects = import_objects(garment)
    shirt, = (obj for obj in garment_objects
              if obj.type == "MESH" and obj in bpy.context.selected_objects)
    shirt.parent = None
    for modifier in list(shirt.modifiers):
        shirt.modifiers.remove(modifier)
    for obj in garment_objects:
        if obj != shirt:
            bpy.data.objects.remove(obj, do_unlink=True)
    shirt.parent = arm
    shirt.modifiers.new("Armature", "ARMATURE").object = arm

    motion_objects = import_objects(motion)
    source, = (obj for obj in motion_objects if obj.type == "ARMATURE")
    assert set(source.data.bones.keys()) == set(arm.data.bones.keys())
    assert len(arm.data.bones) == 65
    for obj in motion_objects:
        obj.hide_viewport = obj.hide_render = True
    return scene, arm, body, shirt


def posed_geometry(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        coords = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        faces = [tuple(face.vertices) for face in mesh.polygons]
        return coords, faces
    finally:
        evaluated.to_mesh_clear()


def poses(arm):
    yield "rest", (1.0,)
    for clip in CLIPS:
        action = bpy.data.actions[clip]
        arm.animation_data.action = action
        arm.animation_data.action_slot = action.slots[0]
        start, stop = action.frame_range
        assert abs(2 * start - round(2 * start)) < .0001
        assert abs(2 * stop - round(2 * stop)) < .0001
        yield clip, tuple(index / 2 for index in range(round(2 * start), round(2 * stop) + 1))


def summarize(rows, count_key):
    if not rows:
        return None
    minimum = min(rows, key=lambda row: row["min_signed_dist_m"])
    maximum = max(rows, key=lambda row: row[count_key])
    return {"samples": len(rows), "peak_count": maximum[count_key], "peak_frame": maximum["frame"],
            "sum_count": sum(row[count_key] for row in rows),
            "min_signed_dist_m": minimum["min_signed_dist_m"],
            "min_clearance_frame": minimum["frame"], "min_clearance_vertex": minimum["vertex"],
            "frames_below_floor": sum(row["min_signed_dist_m"] < TARGET for row in rows)}


def check(triangle=False):
    master, motion, garment, out = map(lambda path: Path(path).resolve(),
                                        sys.argv[sys.argv.index("--") + 1:])
    expected = (BODY_FIX / "motion_fixed.glb").resolve()
    assert checksum(motion) == checksum(expected), "Use the corrected shared clips"
    scene, arm, body, shirt = setup(master, motion, garment)
    modes = tuple(bone.rotation_mode for bone in arm.pose.bones)
    count_key = "tri_overlap_pairs" if triangle else "max_verts_inside"
    stem = "motion_check_tri" if triangle else "motion_check"
    report = {"master_sha256": checksum(master), "motion_sha256": checksum(motion),
              "glb_sha256": checksum(garment), "metric": count_key, "fps": scene.render.fps,
              "minimum_clearance_m": TARGET, "clips": {}}
    body_reference = None
    checker = None
    if triangle:
        # Independently match the body-only reference at integer frames with
        # the original adjacency rule. Garment pairs always use full geometry.
        body_reference = json.loads((BODY_FIX / "body_selfcheck_after.json").read_text())
        assert body_reference["master_sha256"] == report["master_sha256"]
        assert body_reference["motion_sha256"] == report["motion_sha256"]
        body_tools = runpy.run_path(str(BODY_FIX / "bodycheck.py"))
        checker = body_tools["Checker"](body)
        body_report = report["body_only"] = {}
    lines = []
    for clip, frames in poses(arm):
        rows, body_rows = [], []
        for frame in frames:
            floor = math.floor(frame)
            scene.frame_set(floor, subframe=frame - floor)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bv, bf = posed_geometry(body, depsgraph)
            gv, gf = posed_geometry(shirt, depsgraph)
            tree = BVHTree.FromPolygons(bv, bf, epsilon=0)
            distances = []
            for point in gv:
                closest, normal, _, _ = tree.find_nearest(point)
                distances.append((point - closest).dot(normal))
            vertex = min(range(len(gv)), key=distances.__getitem__)
            count = sum(distance < 0 for distance in distances)
            if triangle:
                garment_tree = BVHTree.FromPolygons(gv, gf, epsilon=0)
                count = len(tree.overlap(garment_tree))
                pairs, _ = checker.overlap(bv)
                body_rows.append({"frame": frame, "pairs": len(pairs)})
            rows.append({"frame": frame, count_key: count,
                         "min_signed_dist_m": distances[vertex], "vertex": vertex})
        integers = [row for row in rows if row["frame"].is_integer()]
        halves = [row for row in rows if not row["frame"].is_integer()]
        metrics = summarize(rows, count_key)
        report["clips"][clip] = {"combined": metrics, "integers": summarize(integers, count_key),
                                  "halves": summarize(halves, count_key), "frames": rows}
        if triangle:
            reference = ([body_reference["source_rest_pose"]] if clip == "rest"
                         else body_reference["clips"][clip]["samples"])
            observed = [entry["pairs"] for entry in body_rows if entry["frame"].is_integer()]
            comparison = [entry["pairs"] for entry in reference]
            body_report[clip] = {"integer_counts_match": observed == comparison,
                                 "reference_integer_sum": sum(comparison),
                                 "observed_integer_sum": sum(observed),
                                 "observed_half_sum": sum(entry["pairs"] for entry in body_rows
                                                          if not entry["frame"].is_integer()),
                                 "frames": body_rows}
        line = (f"RESULT {clip} {count_key} {metrics['peak_count']} "
                f"min_signed_dist {metrics['min_signed_dist_m']:.9f} samples {len(rows)}")
        print(line, flush=True)
        lines.append(line)
    assert modes == tuple(bone.rotation_mode for bone in arm.pose.bones)
    (out / f"{stem}.txt").write_text("\n".join(lines) + "\n")
    (out / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    check()
