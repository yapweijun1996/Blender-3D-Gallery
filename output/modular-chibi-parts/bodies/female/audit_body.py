"""Run the supplied body self-overlap checker on the shipped GLB and female master."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import bpy

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BODY, CLIPS, HERE, MASTER, MOTION, PARTS, SOURCES, arguments, bind, samples, set_frame
from glb_io import Glb

sys.path.insert(1, str(PARTS / "body-fix"))
import bodycheck


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(path, destination, only=CLIPS):
    bodycheck.MASTER = MASTER
    scene, arm, body, source = bodycheck.load(path)
    fps = scene.render.fps = 30
    bind(arm, None)
    checker = bodycheck.Checker(body)
    rest = checker.frame("rest")
    report = dict(master_sha256=digest(MASTER), body_sha256=digest(BODY), motion_sha256=digest(path),
                  blender=bpy.app.version_string, fps=fps, method=bodycheck.__file__,
                  rest=rest, clips={})
    last = {}
    for source_path, _ in SOURCES:
        doc = Glb(source_path).doc
        last.update({a["name"]: max(doc["accessors"][s["input"]]["max"][0] for s in a["samplers"])
                     for a in doc["animations"]})
    build = json.loads((HERE / "motion_fit.json").read_text())
    motion = Glb(path)
    duration = {a["name"]: max(motion.doc["accessors"][s["input"]]["max"][0] for s in a["samplers"])
                for a in motion.doc["animations"]}
    report["sync"] = {clip: dict(neutral_duration_s=last[clip], output_duration_s=duration[clip],
                                same_end_time=abs(last[clip] - duration[clip]) < 1.e-7) for clip in only}
    for clip in only:
        action = bpy.data.actions[clip]
        bind(arm, action)
        bad_zones = defaultdict(lambda: {"triangles": 0, "depth_mm": 0, "worst_frame": None})
        frames = []
        maximum_floor_error = 0.
        planted_count = 0
        roundtrip_floor_error = 0.
        for frame in samples(*action.frame_range):
            set_frame(scene, frame)
            values = checker.frame(frame)
            scores = values["foot_min_z_mm"]
            aligned = min(build[clip], key=lambda row: abs(row["seconds"] * fps - frame))
            for side, reference, fitted in zip(("Left", "Right"), aligned["neutral_floor_mm"],
                                               aligned["floor_mm"], strict=True):
                if reference <= 1.:
                    maximum_floor_error = max(maximum_floor_error, abs(scores[side]))
                    planted_count += 1
                roundtrip_floor_error = max(roundtrip_floor_error, abs(scores[side] - fitted))
            for zone, evidence in values["region_pairs"].items():
                record = bad_zones[zone]
                record["triangles"] += evidence["count"]
                if evidence["max_depth_mm"] >= record["depth_mm"]:
                    record.update(depth_mm=evidence["max_depth_mm"], worst_frame=frame)
            frames.append({k: v for k, v in values.items() if k not in
                           {"seam_incident_region_pairs", "index_only_pairs"}})
        result = dict(samples=len(frames), peak_pairs=max(row["pairs"] for row in frames),
                      total_pairs=sum(row["pairs"] for row in frames),
                      max_depth_mm=max((item["depth_mm"] for item in bad_zones.values()), default=0),
                      zone_counts=dict(sorted(bad_zones.items())), min_sole_mm=min(
                          z for row in frames for z in row["foot_min_z_mm"].values()),
                      grounded_max_error_mm=maximum_floor_error, planted_foot_samples=planted_count,
                      max_bake_floor_delta_mm=roundtrip_floor_error, frames=frames)
        report["clips"][clip] = result
        print("BODY", clip, {k: v for k, v in result.items() if k not in {"frames", "zone_counts"}},
              sorted(bad_zones), flush=True)
        destination.write_text(json.dumps(report, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    run(MOTION, HERE / "body_selfcheck.json", tuple(arguments()) or CLIPS)
