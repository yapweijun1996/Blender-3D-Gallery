"""Run the supplied checkers with full half-frame sampling and no legacy preview."""
import json
import math
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
SCRATCH = Path("/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
               "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular")


def replace(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f"Unexpected supplied checker revision at {before!r}")
    return source.replace(before, after)


def run(bank, kind):
    fit = runpy.run_path(str(HERE / "fit_pants_r6.py"))
    vertex = kind == "vertex"
    directory = HERE / "checkers" / bank / kind
    directory.mkdir(parents=True, exist_ok=True)
    master, module = fit["MASTER"], fit["GLB"]
    paths = [path for path, _ in fit["BANKS"]]
    sys.argv = ["--", *map(str, (master, paths[0], module, directory))]
    if bank == "shared":
        original = SCRATCH / ("motion_check_dense.py" if vertex else "motion_check_tri.py")
        source = original.read_text().split("sc.render.engine=", 1)[0]
        counter, measure = ("i", "inside") if vertex else ("o", "ov")
        source = replace(source, f"return {measure},mn", f"return ({measure},mn)")
        source = replace(source, "arm.animation_data_create();res={}",
                         "arm.animation_data_create();res={};detail={}")
        source = replace(source, "sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()",
                         "arm.animation_data.action=None;arm.animation_data.use_nla=False\n"
                         "for p in arm.pose.bones:p.matrix_basis.identity()\n"
                         "sc.frame_set(1);bpy.context.view_layer.update()")
        source = replace(source, "    arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]",
                         "    arm.animation_data.action=None\n"
                         "    for p in arm.pose.bones:p.matrix_basis.identity()\n"
                         "    arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]")
        source = replace(source, "    f0,f1=a.frame_range;worst=0;mn=9",
                         "    f0,f1=a.frame_range;worst=0;mn=9;detail[name]=[]")
        sampling = ",3" if not vertex else ""
        source = replace(source, f"    for fr in range(int(f0),int(f1)+1{sampling}):\n"
                         f"        sc.frame_set(fr);{counter},m=measure();worst=max(worst,{counter});mn=min(mn,m)\n"
                         "    res[name]=(worst,round(mn,4))",
                         f"    for fr in sample_times(f0,f1):\n"
                         f"        sc.frame_set(math.floor(fr),subframe=fr%1);{counter},m=measure()\n"
                         f"        worst=max(worst,{counter});mn=min(mn,m)\n"
                         f"        detail[name].append(dict(frame=fr,count={counter},min_signed_m=m))\n"
                         "    res[name]=(worst,mn)")
        stem = "motion_check" if vertex else "motion_check_tri"
        source += f"\nwrite_results(out, '{stem}', res, detail)\n"
    else:
        index = {"actions": 1, "carry": 2, "carry_native": 2}[bank]
        sys.argv.append(str(paths[index]))
        family = "act" if bank == "actions" else "act2"
        original = PARTS / "body-fix" / family / "motion_check.py"
        source = original.read_text().split("    # Retain the original checker previews", 1)[0]
        source = replace(source, "        first,last=map(round,act.frame_range)\n"
                         "            results=[]\n"
                         "            for f in range(first,last+1):\n"
                         "                scene.frame_set(f)",
                         "        first,last=act.frame_range\n"
                         "            results=[]\n"
                         "            for f in sample_times(first,last):\n"
                         "                scene.frame_set(math.floor(f),subframe=f%1)")
        source += "\nLEGACY = ()\n"
        if bank == "carry_native":
            source += "FPS = 24\n"
        source += f"\ngarment_check(triangles={not vertex!r})\n"

    def sample_times(first, last):
        first, last = round(float(first), 5), round(float(last), 5)
        return sorted({first, last, *(i / 2 for i in range(math.ceil(2 * first), math.floor(2 * last) + 1))})

    def write_results(out, stem, result, detail):
        for suffix, value in ((".json", result), ("_frames.json", detail)):
            (Path(out) / (stem + suffix)).write_text(json.dumps(value, indent=2) + "\n")

    namespace = {"__file__": str(original), "__name__": "__adapted_checker__",
                 "sample_times": sample_times, "write_results": write_results}
    exec(compile(source, str(original), "exec"), namespace)
    (directory / "provenance.json").write_text(json.dumps({
        "glb_sha256": fit["digest"](module), "source": str(original),
        "checker_sha256": fit["digest"](original),
        "triangle_entry_point": "garment_check(triangles=True)" if bank != "shared" and not vertex else None,
        "samples": "every integer and half frame, plus clip endpoints",
        "fps": 30 if bank in ("actions", "carry") else 24,
        "legacy_workbench_preview": "replaced by dedicated Cycles CPU captures",
    }, indent=2) + "\n")


if __name__ == "__main__":
    run(*sys.argv[sys.argv.index("--") + 1:])
