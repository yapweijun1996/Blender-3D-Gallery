"""Run the supplied garment checkers at the round-4 half-frame cadence.

The supplied source files remain unchanged. This adapter extends their sampling
and output precision, resets the neutral pose, and omits Workbench previews.
"""

import argparse
import json
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_jeans_r4.py"))
SCRATCH = Path("/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
               "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular")
ACT = FIT["MOTION"].parent / "act"


def half_frames(first, last):
    first, last = round(float(first), 5), round(float(last), 5)
    return sorted({first, last, *(step / 2 for step in range(math.ceil(first * 2), math.floor(last * 2) + 1))})


def legacy(triangles):
    path = SCRATCH / ("motion_check_tri.py" if triangles else "motion_check_dense.py")
    code = path.read_text().split("sc.render.engine=", 1)[0]
    old = "range(int(f0),int(f1)+1,3)" if triangles else "range(int(f0),int(f1)+1)"
    assert old in code and "sc.frame_set(fr);i,m=measure()" in code
    code = code.replace(old, "half_frames(f0,f1)")
    code = code.replace("sc.frame_set(fr);i,m=measure()", """
        sc.frame_set(math.floor(fr),subframe=fr%1)
        i,m=measure()
        detail.setdefault(name,[]).append(dict(frame=fr,count=i,min_signed_m=m))""".strip())
    neutral = "sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()"
    assert neutral in code
    code = code.replace(neutral, "arm.animation_data.action=None\n"
                        "for bone in arm.pose.bones: bone.matrix_basis.identity()\n"
                        "sc.frame_set(1);bpy.context.view_layer.update()")
    code = code.replace("res={}", "res={};detail={}")
    code = code.replace("res[name]=(worst,round(mn,4))", "res[name]=(worst,mn)")
    namespace = {"__name__": "__main__", "__file__": str(path), "half_frames": half_frames}
    exec(compile(code, str(path), "exec"), namespace)
    return {"source": str(path), "source_sha256": FIT["sha256"](path),
            "results": namespace["res"], "frames": namespace["detail"]}


def added(triangles, output):
    path = ACT / "motion_check.py"
    module = ModuleType("motion_check")
    module.__file__, module.half_frames = str(path), half_frames
    sys.modules[module.__name__] = module
    code = path.read_text().split("    # Retain the original checker previews", 1)[0]
    assert "for f in range(first,last+1):" in code and "scene.frame_set(f)" in code
    code = code.replace("first,last=map(round,act.frame_range)", "first,last=act.frame_range")
    code = code.replace("for f in range(first,last+1):", "for f in half_frames(first,last):")
    code = code.replace("scene.frame_set(f)", "scene.frame_set(math.floor(f),subframe=f%1)")
    exec(compile(code, str(path), "exec"), vars(module))
    if triangles:
        entry = ACT / "motion_check_tri.py"
        runpy.run_path(str(entry), run_name="__main__")
    else:
        entry = path
        module.garment_check()
    stem = "motion_check_tri" if triangles else "motion_check"
    results_file = output / (stem + ".json")
    frames_file = output / (stem + "_frames.json")
    result = {"source": str(entry), "source_sha256": FIT["sha256"](entry),
              "implementation_sha256": FIT["sha256"](path),
              "results": json.loads(results_file.read_text()),
              "frames": json.loads(frames_file.read_text())}
    results_file.unlink()
    frames_file.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sweep", choices=("legacy", "added", "detail"))
    parser.add_argument("--triangles", action="store_true")
    parser.add_argument("--garment", type=Path, default=FIT["GLB"])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    digest = FIT["sha256"](args.garment)
    stem = "motion_check_tri" if args.triangles else "motion_check"
    paths = [FIT["MASTER"], FIT["MOTION"], args.garment]

    if args.sweep == "detail":
        sys.argv = [__file__, "--", *map(str, paths), str(HERE)]
        run = runpy.run_path(str(HERE.parent / "round3/motion_check.py"))["run"]
        run.__globals__.update(HERE=HERE, FIT=FIT)
        run(triangles=args.triangles)
        report_path = HERE / (stem + ".json")
        result = json.loads(report_path.read_text())
        result["additional_actions_sha256"] = FIT["sha256"](FIT["ACTIONS"])
        report_path.write_text(json.dumps(result, indent=2) + "\n")
    else:
        scratch = HERE / ".checker"
        scratch.mkdir(exist_ok=True)
        sys.argv = [__file__, "--", *map(str, paths), str(scratch)]
        if args.sweep == "legacy":
            result = legacy(args.triangles)
        else:
            sys.argv.append(str(FIT["ACTIONS"]))
            result = added(args.triangles, scratch)
        assert FIT["sha256"](args.garment) == digest
        result["garment_sha256"] = digest
        result["master_sha256"] = FIT["sha256"](FIT["MASTER"])
        result["motion_sha256"] = FIT["sha256"](FIT["MOTION"])
        if args.sweep == "added":
            result["additional_actions_sha256"] = FIT["sha256"](FIT["ACTIONS"])
        output = HERE / f"{stem}_{args.sweep}_supplied.json"
        output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
