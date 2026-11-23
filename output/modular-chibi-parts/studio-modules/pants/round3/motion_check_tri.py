"""Check garment/body triangle pairs separately from master self-overlap."""

import json
from pathlib import Path
import runpy
import sys

from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
CHECK = runpy.run_path(str(HERE / "motion_check.py"))
BODY_FIX = HERE.parents[2] / "body-fix"


def pair_checker(body, paths):
    baseline = json.loads((BODY_FIX / "body_selfcheck_after.json").read_text())
    assert CHECK["digest"](paths[0]) == baseline["master_sha256"]
    assert CHECK["digest"](paths[1]) == baseline["motion_sha256"]
    body.data.calc_loop_triangles()
    welded = {}
    ids = [welded.setdefault(tuple(v.co), v.index) for v in body.data.vertices]
    faces = [frozenset(ids[v] for v in triangle.vertices) for triangle in body.data.loop_triangles]

    def baseline_pairs(row):
        return {(a, b) for region in row["region_pairs"].values()
                for a, b, _ in region["triangles_and_depth_mm"]}

    references = {"rest": {1: baseline_pairs(baseline["source_rest_pose"])}}
    references.update({clip: {row["frame"]: baseline_pairs(row) for row in value["samples"]}
                       for clip, value in baseline["clips"].items()})

    def count(clip, frame, body_tree, points, triangles):
        garment = BVHTree.FromPolygons(points, triangles, all_triangles=True, epsilon=0)
        crossing = sorted(body_tree.overlap(garment))
        intrinsic = {(a, b) for a, b in body_tree.overlap(body_tree)
                     if a < b and faces[a].isdisjoint(faces[b])}
        row = {"tri_overlap_pairs": len(crossing), "body_only_pairs": len(intrinsic)}
        if crossing:
            row["body_triangle_garment_triangle_pairs"] = crossing
        reference = references[clip].get(frame)
        if reference is not None:
            row["body_only_baseline_pairs"] = len(reference)
            row["body_only_added_pairs"] = sorted(intrinsic - reference)
            row["body_only_missing_pairs"] = sorted(reference - intrinsic)
        return row

    return count


if __name__ == "__main__":
    CHECK["check"](tuple(Path(arg) for arg in sys.argv[sys.argv.index("--") + 1:]),
                   stem="motion_check_tri", pairs=pair_checker)
