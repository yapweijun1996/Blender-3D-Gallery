"""Run both supplied checker metrics on the exported female module bytes."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE, MASTER, MODULES, MOTION, arguments

CHECKERS = HERE / "checkers"
OUT = HERE / "checks"


def audit(label):
    module = HERE / f"female-{label}.glb"
    output = OUT / label
    original_argv = sys.argv
    for folder, script in (("shared", "motion_check_dense.py"), ("shared", "motion_check_tri.py"),
                           ("act", "motion_check.py"), ("act2", "motion_check.py")):
        path = CHECKERS / folder / script
        argv = [MASTER, MOTION, module, output / folder]
        if folder != "shared":
            argv.append(MOTION)
        sys.argv = [str(path), "--", *map(str, argv)]
        runpy.run_path(str(path), run_name="__main__")
    sys.argv = original_argv

    def read(folder, filename):
        return json.loads((output / folder / filename).read_text())

    clean = {}
    dense = read("shared", "motion_check_dense.json")
    triangles = read("shared", "motion_check_tri.json")
    for name in dense:
        clean[name] = dict(max_vertices_inside=dense[name][0], max_triangle_pairs=triangles[name][0],
                           min_signed_m=min(dense[name][1], triangles[name][1]))
    for folder in ("act", "act2"):
        for name, (counts, distance) in read(folder, "motion_check_both.json").items():
            if name == "rest":
                continue
            clean[name] = dict(max_vertices_inside=counts[0], max_triangle_pairs=counts[1], min_signed_m=distance)
    assert len(clean) == 15
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(module_sha256=digest(module), motion_sha256=digest(MOTION), master_sha256=digest(MASTER),
                  interval_frames=.5, fps=30, clips=clean)
    (output / "gate.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    for module in arguments() or MODULES:
        audit(module)
