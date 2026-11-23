"""Combine disjoint parallel retarget runs onto the exact female bind skeleton."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BODY, CLIPS, MOTION, arguments
from glb_io import Glb


def main():
    target = Glb(BODY).skeleton()
    data = {}
    stage = {}
    quality = {}
    for source in map(Path, arguments()):
        asset = Glb(source)
        report = json.loads(source.with_suffix(".json").read_text())
        assert asset.doc["nodes"] == target.doc["nodes"]
        for animation in asset.doc["animations"]:
            name = animation["name"]
            samples = report[name]
            score = (sum(row["pairs"] for row in samples),
                     max((v["max_depth_mm"] for row in samples for v in row["regions"].values()), default=0))
            if name not in quality or score < quality[name]:
                quality[name] = score
                data[name] = (asset, animation)
                stage[name] = samples
    assert set(data) == set(CLIPS), set(CLIPS) - set(data)
    for name in CLIPS:
        source, animation = data[name]
        indices = {}
        for sampler in animation["samplers"]:
            for key in ("input", "output"):
                old = sampler[key]
                if old not in indices:
                    kind = source.doc["accessors"][old]["type"]
                    indices[old] = target.floats(source.accessor(old), kind)
                sampler[key] = indices[old]
        target.doc["animations"].append(animation)
    target.write(MOTION)
    MOTION.with_name("motion_fit.json").write_text(json.dumps(stage, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
