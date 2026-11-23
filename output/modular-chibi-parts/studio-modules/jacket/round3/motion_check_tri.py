"""Check garment-to-body triangle intersections independently on the exported GLB."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion_check import emit, geometry, load, samples, sha, signed, zones

DIVISIONS = 10
GRID = np.asarray([(a, b, DIVISIONS - a - b)
                   for a in range(DIVISIONS + 1) for b in range(DIVISIONS + 1 - a)]) / DIVISIONS


def surface_grid(points, faces, tree):
    patches = np.einsum("kc,fci->fki", GRID, points[faces])
    distances = signed(tree, patches.reshape(-1, 3)).reshape(len(faces), -1)
    return patches, distances


def rest_surface(points, faces, labels, tree):
    result = {}
    for label in sorted(set(labels)):
        subset = faces[labels == label]
        record = {"samples": 0, "below_minimum": 0, "over_cap": 0,
                  "min_signed_m": float("inf"), "max_euclidean_m": 0.}
        for offset in range(0, len(subset), 192):
            patches, d = surface_grid(points, subset[offset:offset + 192], tree)
            euclidean = np.asarray([tree.find_nearest(p)[3] for p in patches.reshape(-1, 3)])
            record["samples"] += d.size
            record["below_minimum"] += int((d < .0005).sum())
            record["over_cap"] += int((euclidean > .030).sum())
            record["min_signed_m"] = min(record["min_signed_m"], float(d.min()))
            record["max_euclidean_m"] = max(record["max_euclidean_m"], float(euclidean.max()))
        result[str(label)] = record
    return result


def main():
    master, motion, garment, out = map(Path, sys.argv[sys.argv.index("--") + 1:])
    scene, arm, body, mesh, actions = load(master, motion, garment)
    report = {"master_sha256": sha(master), "motion_sha256": sha(motion),
              "glb_sha256": sha(garment), "frames": []}
    baseline_path = motion.with_name("body_selfcheck_after.json")
    baseline = json.loads(baseline_path.read_text())
    assert baseline["master_sha256"] == report["master_sha256"]
    assert baseline["motion_sha256"] == report["motion_sha256"]
    report["body_only_baseline"] = {
        "source": baseline_path.name,
        "neutral_total": baseline["source_rest_pose"]["pairs"],
        "neutral_regions": {"eye inserts/head": 163, "shorts/legs": 60, "foot/toe": 95},
        "clip_integer_pair_sums": {key: value["sum_pairs"] for key, value in baseline["clips"].items()},
    }
    crossing = set()
    for clip, frame in samples(scene, arm, actions):
        dg = bpy.context.evaluated_depsgraph_get()
        bp, bf = geometry(body, dg)
        gp, gf = geometry(mesh, dg)
        body_tree = BVHTree.FromPolygons(bp, bf, all_triangles=True, epsilon=0)
        garment_tree = BVHTree.FromPolygons(gp, gf, all_triangles=True, epsilon=0)
        pairs = np.asarray(body_tree.overlap(garment_tree), dtype=int).reshape(-1, 2)
        d = signed(body_tree, gp)
        if clip == "rest":
            neutral = np.asarray(gp)
            faces = np.asarray(gf)
            face_regions, face_sides = zones(neutral[faces].mean(axis=1))
            _, vertex_sides = zones(neutral)
            lengths = np.linalg.norm(neutral[faces] - np.roll(neutral[faces], 1, axis=1), axis=2).max(axis=1)
            report["rest_surface_clearance_m"] = rest_surface(neutral, faces, face_regions, body_tree)
        index = int(d.argmin())
        row = {"clip": clip, "frame": frame, "tri_overlap_pairs": len(pairs),
               "min_signed_m": float(d[index]), "min_zone": str(vertex_sides[index])}
        if len(pairs):
            touched = np.unique(pairs[:, 1])
            crossing.update(touched.tolist())
            _, sample = surface_grid(np.asarray(gp), faces[touched], body_tree)
            by_zone = face_sides[pairs[:, 1]]
            row["pair_zones"] = {
                str(zone): {"pairs": int((by_zone == zone).sum()),
                            "min_sample_signed_m": float(sample[face_sides[touched] == zone].min())}
                for zone in sorted(set(by_zone))}
        report["frames"].append(row)
    assert len(report["frames"]) == 824
    report["distinct_crossing_garment_faces"] = len(crossing)
    report["crossing_faces_with_rest_edge_over_12_mm"] = sum(int(lengths[i] > .012) for i in crossing)
    emit(out, "motion_check_tri", "tri_overlap_pairs", report)


if __name__ == "__main__":
    main()
