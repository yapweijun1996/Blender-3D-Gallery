"""Report verified, hash-matched, unchanged master-body overlap evidence."""

import json
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_jeans_r5.py"))


def main():
    legacy_file = HERE.parent / "round3/body_baseline_comparison.json"
    added_file = FIT["ACTIONS"].parent / "body_selfcheck_after.json"
    legacy = json.loads(legacy_file.read_text())
    added = json.loads(added_file.read_text())
    master = FIT["sha256"](FIT["MASTER"])
    motion = FIT["sha256"](FIT["MOTION"])
    actions = FIT["sha256"](FIT["ACTIONS"])
    assert legacy["master_sha256"] == added["master_sha256"] == master
    assert legacy["motion_sha256"] == motion and added["action_sha256"] == actions
    results = {"rest": {"samples": 1, "peak_body_pairs": legacy["neutral_pairs"]}}
    for name, row in legacy["body_only"].items():
        results[name] = {"peak_body_pairs": row["peak_pairs"],
                         "body_pairs_total": row["integer_pairs"] + row["half_frame_pairs"]}
    for name, clip in added["clips"].items():
        rows = clip["samples"]
        max_knee = max(rows, key=lambda row: row["target_pairs"])
        max_depth = max(rows, key=lambda row: row["deepest_target"]["depth_mm"])
        regions = clip["summary"]["target_by_region"]
        assert all("UpLeg" in key and any(f"{s}Leg" in key for s in ("Right", "Left"))
                   for key in regions)
        results[name] = {
            "samples": len(rows), "peak_body_pairs": max(row["all_pairs"] for row in rows),
            "body_pairs_total": sum(row["all_pairs"] for row in rows),
            "peak_knee_pairs": max_knee["target_pairs"], "peak_knee_frame": max_knee["frame"],
            "knee_pairs_total": clip["summary"]["target_total"],
            "deepest_knee": {"frame": max_depth["frame"], **max_depth["deepest_target"]},
        }
    FIT["write_json"]("body_only_baseline.json", {
        "master_sha256": master, "motion_sha256": motion, "additional_actions_sha256": actions,
        "source_reports": [str(path.relative_to(FIT["PARTS"])) for path in (legacy_file, added_file)],
        "results": results,
    })


if __name__ == "__main__":
    main()
