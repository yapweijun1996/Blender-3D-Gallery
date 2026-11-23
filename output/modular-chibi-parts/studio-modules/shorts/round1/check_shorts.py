"""Run the six supplied checkers without modifying the supplied files."""
import argparse
import json
import math
import runpy
import sys
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shorts import BANKS, GLB, HERE, MASTER, SHA, half_frames

SCRATCH = Path("/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
               "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular")


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
    old = "sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()"
    assert old in code
    code = code.replace(old, "arm.animation_data.action=None\narm.animation_data.use_nla=False\n"
                        "for bone in arm.pose.bones: bone.matrix_basis.identity()\n"
                        "sc.frame_set(1);bpy.context.view_layer.update()")
    code = code.replace("res={}", "res={};detail={}")
    code = code.replace("res[name]=(worst,round(mn,4))", "res[name]=(worst,mn)")
    namespace = {"__name__": "__main__", "__file__": str(path), "half_frames": half_frames}
    exec(compile(code, str(path), "exec"), namespace)
    return {"entry": str(path), "checker_sha256": SHA(path), "results": namespace["res"], "frames": namespace["detail"]}


def additional(bank, triangles, tmp):
    folder = BANKS["shared"][0].parent / ("act" if bank == "sit" else "act2")
    path = folder / "motion_check.py"
    module = ModuleType("motion_check")
    module.__file__, module.half_frames = str(path), half_frames
    sys.modules[module.__name__] = module
    code = path.read_text().split("    # Retain the original checker previews", 1)[0]
    assert "for f in range(first,last+1):" in code and "scene.frame_set(f)" in code
    code = code.replace("first,last=map(round,act.frame_range)", "first,last=act.frame_range")
    code = code.replace("for f in range(first,last+1):", "for f in half_frames(first,last):")
    code = code.replace("scene.frame_set(f)", "scene.frame_set(math.floor(f),subframe=f%1)")
    exec(compile(code, str(path), "exec"), vars(module))
    module.LEGACY = ()  # The shared bank is already measured by its own supplied checkers.
    if triangles:
        entry = folder / "motion_check_tri.py"
        runpy.run_path(str(entry), run_name="__main__")
    else:
        entry = path
        module.garment_check()
    name = "motion_check_tri" if triangles else "motion_check"
    files = [tmp / (name + suffix) for suffix in (".json", "_frames.json")]
    results, frames = (json.loads(file.read_text()) for file in files)
    for file in files:
        file.unlink()
    tmp.rmdir()
    return {"entry": str(entry), "checker_sha256": SHA(entry), "implementation_sha256": SHA(path),
            "results": results, "frames": frames}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", choices=BANKS)
    parser.add_argument("--triangles", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bank, triangles = args.bank, args.triangles
    folder = HERE / "checks"
    folder.mkdir(exist_ok=True)
    tmp = folder / ".checker-output"
    digest = SHA(GLB)
    sys.argv = [__file__, "--", *map(str, (MASTER, BANKS["shared"][0], GLB, tmp))]
    if bank == "shared":
        details = legacy(triangles)
    else:
        sys.argv.append(str(BANKS[bank][0]))
        details = additional(bank, triangles, tmp)
    assert SHA(GLB) == digest
    assert all(name in details["results"] and details["frames"].get(name) for name in BANKS[bank][1])
    details.update(glb_sha256=digest, master_sha256=SHA(MASTER), bank_sha256=SHA(BANKS[bank][0]),
                   shared_bank_sha256=SHA(BANKS["shared"][0]))
    mode = "triangle" if triangles else "vertex"
    (folder / f"{bank}_{mode}.json").write_text(json.dumps(details, indent=2) + "\n")


if __name__ == "__main__":
    main()
