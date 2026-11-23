"""Run the six supplied checker variants at integer and half frames."""
import json
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType

sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_skirt import BANKS, GLB, HERE, MASTER, digest, half_frames, write_json

SCRATCH = Path("/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
               "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular")


def replace(code, source, target):
    assert source in code, source
    return code.replace(source,target,1)


def legacy(triangles, garment, log_dir):
    path = SCRATCH / ("motion_check_tri.py" if triangles else "motion_check_dense.py")
    old = "range(int(f0),int(f1)+1,3)" if triangles else "range(int(f0),int(f1)+1)"
    code = path.read_text().split("sc.render.engine=",1)[0]
    code = replace(code, "bpy.ops.wm.open_mainfile(filepath=master)",
                   "bpy.ops.wm.open_mainfile(filepath=master,load_ui=False,use_scripts=False)")
    code = replace(code, old, "half_frames(f0,f1)")
    code = replace(code, "sc.frame_set(fr);i,m=measure();worst=max(worst,i);mn=min(mn,m)", """
        sc.frame_set(math.floor(fr),subframe=fr%1)
        i,m=measure()
        worst=max(worst,i)
        mn=min(mn,m)
        detail.setdefault(name,[]).append(dict(frame=fr,count=i,min_signed_m=m))""".strip())
    code = replace(code, "sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()", """
arm.animation_data.use_nla=False
arm.animation_data.action=None
for bone in arm.pose.bones: bone.matrix_basis.identity()
sc.frame_set(1)
bpy.context.view_layer.update()""".strip())
    code = replace(code, "    arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]", """
    arm.animation_data.action=None
    for bone in arm.pose.bones: bone.matrix_basis.identity()
    arm.animation_data.action=a
    arm.animation_data.action_slot=a.slots[0]""".strip("\n"))
    code = replace(code, "res={}", "res={};detail={}")
    code = replace(code, "res[name]=(worst,round(mn,4))", "res[name]=(worst,mn)")
    code = replace(code, "if not a:continue", "assert a is not None, name")
    motion,_ = BANKS["shared"]
    sys.argv = [str(path),"--",*map(str,(MASTER,motion,garment,log_dir))]
    namespace = {"__name__":"__main__","__file__":str(path),"half_frames":half_frames}
    exec(compile(code,str(path),"exec"),namespace)
    return path, path, namespace["res"], namespace["detail"]


def added(bank, triangles, garment, log_dir):
    motion = BANKS["shared"][0]
    path = motion.parent / ("act" if bank == "sit_hold" else "act2") / "motion_check.py"
    sys.path.insert(0,str(path.parent))
    sys.modules.pop("chibi",None)
    code = path.read_text().split("    # Retain the original checker previews",1)[0]
    code = replace(code,"first,last=map(round,act.frame_range)", "first,last=act.frame_range")
    code = replace(code,"for f in range(first,last+1):","for f in half_frames(first,last):")
    code = replace(code,"scene.frame_set(f)","scene.frame_set(math.floor(f),subframe=f%1)")
    module = ModuleType("motion_check")
    module.__file__, module.half_frames = str(path), half_frames
    sys.modules[module.__name__] = module
    sys.argv = [str(path),"--",*map(str,(MASTER,motion,garment,log_dir,BANKS[bank][0]))]
    try:
        exec(compile(code,str(path),"exec"),vars(module))
        if triangles:
            entry = path.with_name("motion_check_tri.py")
            runpy.run_path(str(entry),run_name="__main__")
            sys.path.pop(0)
        else:
            entry = path
            module.garment_check()
    finally:
        sys.path.remove(str(path.parent))
    stem = "motion_check_tri" if triangles else "motion_check"
    res = json.loads((log_dir/(stem+".json")).read_text())
    detail = json.loads((log_dir/(stem+"_frames.json")).read_text())
    return entry,path,res,detail


def sweep(garment, triangles):
    metric = "triangle_overlap_pairs" if triangles else "vertices_inside"
    stem = "motion_check_tri" if triangles else "motion_check"
    input_hashes = {name: digest(path) for name,(path,_) in BANKS.items()}
    garment_hash = digest(garment)
    banks, frames = {}, {}
    for name,(path,clips) in BANKS.items():
        destination = HERE/"checkers"/name
        destination.mkdir(exist_ok=True,parents=True)
        if name=="shared":
            entry, implementation, summary, detail = legacy(triangles,garment,destination)
            detail["rest"] = [{"frame":1,"count":summary["rest"][0],"min_signed_m":summary["rest"][1]}]
            include = ("rest",*clips)
        else:
            entry, implementation, summary, detail = added(name,triangles,garment,destination)
            include = clips
        assert all(clip in detail and len(detail[clip]) for clip in include)
        bank_report = {"source":str(entry),"source_sha256":digest(entry),
                       "implementation":str(implementation),"implementation_sha256":digest(implementation),
                       "garment_sha256":garment_hash,"clip_bank_sha256":input_hashes[name],
                       "source_summary":summary,"source_frames":detail}
        (destination/(stem+"_supplied.json")).write_text(json.dumps(bank_report,indent=2)+"\n")
        for suffix in (".json","_frames.json"):
            (destination/(stem+suffix)).unlink(missing_ok=True)
        banks[name] = str((destination/(stem+"_supplied.json")).relative_to(HERE))
        frames.update({clip:detail[clip] for clip in include})
    results = {}
    for clip,rows in frames.items():
        deepest = min(rows,key=lambda r:r["min_signed_m"])
        peak = max(rows,key=lambda r:r["count"])
        results[clip] = {"samples":len(rows),metric:peak["count"],"peak_frame":peak["frame"],
                         "minimum_m":deepest["min_signed_m"],"minimum_frame":deepest["frame"],
                         "total_count":sum(row["count"] for row in rows),
                         "below_floor_samples":sum(row["min_signed_m"] < .0005 for row in rows)}
    assert digest(garment) == garment_hash
    write_json(stem+".json",{"garment_sha256":garment_hash,"master_sha256":digest(MASTER),
                            "bank_sha256":input_hashes,"checkers":banks,"frames":frames,"results":results})
    lines = ["Clip          Samples   Peak   Min signed mm   Min frame"]
    for clip,row in results.items():
        lines.append(f"{clip:13} {row['samples']:7} {row[metric]:6} "
                     f"{row['minimum_m']*1000:15.6f} {row['minimum_frame']:11g}")
    (HERE/(stem+".txt")).write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:]
    garment = Path(args[1]) if len(args)>1 else GLB
    for variant in ((False,True) if args[0]=="both" else (args[0]=="triangles",)):
        sweep(garment,variant)
