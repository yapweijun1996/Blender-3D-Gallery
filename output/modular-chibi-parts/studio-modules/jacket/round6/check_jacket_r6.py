"""Replay the supplied Blender checkers at full precision on the half-frame grid."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
SCRATCH = Path("/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
               "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular")
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS / "body-fix/motion_fixed.glb"
GROUPS = {
    "shared": (SCRATCH, None),
    "sit_hold": (MOTION.parent / "act", PARTS / "actions-fix/actions_fixed.glb"),
    "carry": (MOTION.parent / "act2", PARTS / "actions-hold2/hold_actions.glb"),
}


def half_frames(first, last):
    first, last = round(float(first), 5), round(float(last), 5)
    return sorted({first, last, *(i / 2 for i in range(math.ceil(first * 2), math.floor(last * 2) + 1))})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(code, before, after):
    assert code.count(before) == 1, before
    return code.replace(before, after)


def shared(folder, triangles):
    path = folder / ("motion_check_tri.py" if triangles else "motion_check_dense.py")
    code = path.read_text().split("sc.render.engine=", 1)[0]
    code = replace_once(code, "range(int(f0),int(f1)+1,3)" if triangles else "range(int(f0),int(f1)+1)",
                        "half_frames(f0,f1)")
    code = replace_once(code, "sc.frame_set(fr);i,m=measure()", """sc.frame_set(math.floor(fr), subframe=fr%1)
        i,m=measure()
        detail.setdefault(name,[]).append(dict(frame=fr,count=i,min_signed_m=m))""")
    code = replace_once(code, "sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()",
                        "arm.animation_data.action=None\narm.animation_data.use_nla=False\n"
                        "for bone in arm.pose.bones: bone.matrix_basis.identity()\n"
                        "sc.frame_set(1);bpy.context.view_layer.update()")
    code = replace_once(code, "res={}", "res={};detail={}")
    code = replace_once(code, "res[name]=(worst,round(mn,4))", "res[name]=(worst,mn)")
    code = replace_once(code, "filepath=master)", "filepath=master,load_ui=False,use_scripts=False)")
    namespace = {"__name__": "__main__", "__file__": str(path), "half_frames": half_frames}
    exec(compile(code, str(path), "exec"), namespace)
    return path, path, namespace["res"], namespace["detail"]


def additional(folder, triangles, output):
    path = folder / "motion_check.py"
    module = ModuleType("motion_check")
    module.__file__, module.half_frames = str(path), half_frames
    sys.modules[module.__name__] = module
    code = path.read_text().split("    # Retain the original checker previews", 1)[0]
    code = replace_once(code, "first,last=map(round,act.frame_range)", "first,last=act.frame_range")
    code = replace_once(code, "for f in range(first,last+1):", "for f in half_frames(first,last):")
    code = replace_once(code, "scene.frame_set(f)", "scene.frame_set(math.floor(f),subframe=f%1)")
    exec(compile(code, str(path), "exec"), vars(module))
    entry = folder / "motion_check_tri.py" if triangles else path
    if triangles:
        runpy.run_path(str(entry), run_name="__main__")
    else:
        module.garment_check()
    stem = "motion_check_tri" if triangles else "motion_check"
    results_file = output / (stem + ".json")
    frames_file = output / (stem + "_frames.json")
    return entry, path, json.loads(results_file.read_text()), json.loads(frames_file.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=GROUPS)
    parser.add_argument("metric", choices=("vertex", "triangle"))
    parser.add_argument("--garment", type=Path, default=HERE / "jacket_v6.glb")
    options = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    triangles = options.metric == "triangle"
    garment = options.garment.resolve()
    digest = sha(garment)
    folder, animation = GROUPS[options.group]
    output = HERE / ".runtime" / f"check_{options.group}_{options.metric}"
    output.mkdir(exist_ok=True)
    sys.argv = [__file__, "--", str(MASTER), str(MOTION), str(garment), str(output)]
    if animation is None:
        entry, source, results, frames = shared(folder, triangles)
    else:
        sys.argv.append(str(animation))
        entry, source, results, frames = additional(folder, triangles, output)
    assert sha(garment) == digest
    result = dict(entry=str(entry), entry_sha256=sha(entry), implementation=str(source),
                  implementation_sha256=sha(source), garment_sha256=digest,
                  master_sha256=sha(MASTER), motion_sha256=sha(MOTION),
                  additional_actions_sha256=sha(animation) if animation else None,
                  sampling="Every integer and half frame, inclusive", results=results, frames=frames)
    destination = HERE / f"checker_{options.group}_{options.metric}.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
