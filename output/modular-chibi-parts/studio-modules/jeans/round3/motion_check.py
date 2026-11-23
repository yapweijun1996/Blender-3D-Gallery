"""Measure every half frame of the corrected motion on a fresh GLB import."""

import json
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_jeans_r3.py"))


def posed(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        return ([evaluated.matrix_world @ vertex.co for vertex in mesh.vertices],
                [triangle.vertices[:] for triangle in mesh.loop_triangles])
    finally:
        evaluated.to_mesh_clear()


def run(triangles=False):
    master, motion, garment, output = (
        Path(arg).resolve() for arg in sys.argv[sys.argv.index("--") + 1:])
    assert master == FIT["MASTER"] and motion == FIT["MOTION"] and output == HERE
    garment_sha = FIT["sha256"](garment)
    scene, arm, body, jeans = FIT["setup"](garment)
    prior = FIT["PRIOR"]
    initial = [vertex.co.copy() for vertex in jeans.data.vertices]
    zones = np.asarray([FIT["zone"](point) for point in initial])
    names = [bone.name for bone in arm.pose.bones]
    _, body_faces = FIT["mesh_arrays"](body.data)
    body_weights = FIT["read_weights"](body, names)
    body_zones = np.array([names[i].split(":")[-1] for i in body_weights[body_faces].sum(axis=1).argmax(axis=1)])
    modes = [bone.rotation_mode for bone in arm.pose.bones]
    pair_depth = (runpy.run_path(str(FIT["PARTS"] / "body-fix/bodycheck.py"))["pair_depth"]
                  if triangles else None)
    initial_xyz = np.asarray(initial)
    rows = {}
    rest_gaps = None
    for clip, frame in FIT["frames"]():
        FIT["set_pose"](scene, arm, clip, frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        body_coords, body_faces = posed(body, depsgraph)
        coords, faces = posed(jeans, depsgraph)
        tree = BVHTree.FromPolygons(body_coords, body_faces, all_triangles=True, epsilon=0)
        nearest = [tree.find_nearest(point) for point in coords]
        gaps = np.array([(point - hit[0]).dot(hit[1]) for point, hit in zip(coords, nearest)])
        closest = int(gaps.argmin())
        row = {"frame": frame, "minimum_m": float(gaps[closest]), "jeans_zone": str(zones[closest]),
               "body_zone": str(body_zones[nearest[closest][2]])}
        if triangles:
            garment_tree = BVHTree.FromPolygons(coords, faces, all_triangles=True, epsilon=0)
            pairs = tree.overlap(garment_tree)
            row["garment_pairs"] = len(pairs)
            if pairs:
                a, b = np.asarray(pairs).T
                vertices, face_array = np.asarray(coords), np.asarray(faces)
                depths = pair_depth(np.asarray(body_coords)[np.asarray(body_faces)[a]], vertices[face_array[b]])
                worst = int(depths.argmax())
                row["worst_pair"] = {
                    "depth_mm": float(depths[worst]), "body_triangle": int(a[worst]),
                    "garment_triangle": int(b[worst]), "body_zone": str(body_zones[a[worst]]),
                    "jeans_zone": FIT["zone"](initial_xyz[face_array[b[worst]]].mean(axis=0)),
                }
                regions = {}
                centers = initial_xyz[face_array[b]].mean(axis=1)
                for body_id, center, depth in zip(a, centers, depths):
                    label = f"{FIT['zone'](center)} / {body_zones[body_id]}"
                    record = regions.setdefault(label, {"pairs": 0, "maximum_pair_depth_mm": 0.})
                    record["pairs"] += 1
                    record["maximum_pair_depth_mm"] = max(record["maximum_pair_depth_mm"], float(depth))
                row["pair_regions"] = regions
        else:
            row["vertices_inside"] = int((gaps < 0).sum())
            near = np.flatnonzero(gaps < FIT["MINIMUM"])
            if len(near):
                regions = {}
                for v in near:
                    label = f"{zones[v]} / {body_zones[nearest[v][2]]}"
                    record = regions.setdefault(label, {"vertices_below_floor": 0, "minimum_m": 1.})
                    record["vertices_below_floor"] += 1
                    record["minimum_m"] = min(record["minimum_m"], float(gaps[v]))
                row["regions_below_floor"] = regions
            if clip == "rest":
                rest_gaps = gaps
        rows.setdefault(clip, []).append(row)
    assert modes == [bone.rotation_mode for bone in arm.pose.bones]
    result = {}
    key = "garment_pairs" if triangles else "vertices_inside"
    metric = "tri_overlap_pairs" if triangles else "max_verts_inside"
    stem = "motion_check_tri" if triangles else "motion_check"
    lines = []
    for clip, measures in rows.items():
        peak = max(measures, key=lambda row: row[key])
        closest = min(measures, key=lambda row: row["minimum_m"])
        result[clip] = {"poses": len(measures), f"max_{key}": peak[key], "peak_frame": peak["frame"],
                        f"total_{key}": sum(m[key] for m in measures), "closest": closest}
        lines.append(f"RESULT {clip} {metric} {peak[key]} min_signed_dist {closest['minimum_m']:.9f}")
    assert FIT["sha256"](garment) == garment_sha, "The GLB changed during the check"
    report = {"master_sha256": FIT["sha256"](master), "motion_sha256": FIT["sha256"](motion),
              "garment_sha256": garment_sha, "blender": bpy.app.version_string,
              "samples": sum(map(len, rows.values())), "results": result, "frames": rows,
              "passes": all(row[f"max_{key}"] == 0 and row["closest"]["minimum_m"] >= FIT["MINIMUM"]
                            for row in result.values())}
    if not triangles:
        report["rest_clearance_m"] = {"all": prior["statistics"](rest_gaps), **{
            label: prior["statistics"](rest_gaps[zones == label]) for label in sorted(set(zones))}}
        report["rest_vertices_over_30mm"] = int((rest_gaps > FIT["CAP"]).sum())
        report["openings_m"] = prior["mesh_boundaries"](jeans.data)
        report["passes"] &= report["rest_vertices_over_30mm"] == 0
    (output / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / f"{stem}.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    run()
