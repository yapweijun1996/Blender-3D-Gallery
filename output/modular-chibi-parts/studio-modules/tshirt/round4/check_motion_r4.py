"""Run both supplied checker families on the exported T-shirt at half frames."""
import hashlib
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
PARTS = OUT.parents[2]
SCRATCH = Path("/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
               "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular")
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS / "body-fix/motion_fixed.glb"
ACTIONS = PARTS / "actions-astra/actions.glb"
GARMENT = OUT / "tshirt_v4.glb"
LEGACY = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
ADDED = ("sit_down", "sit_idle", "stand_up", "hold_item")
MINIMUM = .0005


def update_source(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Checker source changed around {old!r}")
    return source.replace(old, new)


def measure_legacy(triangles):
    path = SCRATCH / ("motion_check_tri.py" if triangles else "motion_check_dense.py")
    source = path.read_text().split("arm.animation_data_create();res={}", 1)[0]
    # Keep the supplied scene setup, native mesh queries and metric intact.
    # Its trailing preview and subsampled loop are replaced below.
    scope = {"__file__": str(path), "__name__": "__main__"}
    sys.argv = [str(path), "--", *map(str, (MASTER, MOTION, GARMENT, OUT))]
    exec(compile(source, str(path), "exec"), scope)
    scene, arm, measure, bpy = (scope[k] for k in ("sc", "arm", "measure", "bpy"))
    arm.animation_data_create()
    arm.animation_data.action = None
    scene.frame_set(1)
    bpy.context.view_layer.update()
    count, distance = measure()
    results = {"rest": [{"frame": 1., "count": count, "min_signed_m": distance}]}
    modes = tuple(b.rotation_mode for b in arm.pose.bones)
    for name in LEGACY:
        action = bpy.data.actions[name]
        arm.animation_data.action = action
        arm.animation_data.action_slot = action.slots[0]
        results[name] = []
        first, last = map(lambda value: round(2 * value), action.frame_range)
        for tick in range(first, last + 1):
            scene.frame_set(tick // 2, subframe=(tick % 2) / 2)
            count, distance = measure()
            results[name].append({"frame": tick / 2, "count": count, "min_signed_m": distance})
    assert modes == tuple(b.rotation_mode for b in arm.pose.bones)
    return results


def measure_added(triangles):
    base = PARTS / "body-fix/act"
    path = base / "motion_check.py"
    source = path.read_text().split("    # Retain the original checker previews", 1)[0]
    source = update_source(source, "    inputs={Path(motion).resolve():LEGACY}",
                           "    inputs={}")
    source = update_source(source, "            for f in range(first,last+1):\n                scene.frame_set(f)",
                           "            for tick in range(2*first,2*last+1):\n"
                           "                f=tick/2\n"
                           "                scene.frame_set(tick//2, subframe=(tick%2)/2)")
    source = source.split("    stem='motion_check_tri'", 1)[0] + "    return detail\n"
    scope = {"__file__": str(path), "__name__": "motion_check"}
    sys.argv = [str(path), "--", *map(str, (MASTER, MOTION, GARMENT, OUT, ACTIONS))]
    exec(compile(source, str(path), "exec"), scope)
    if triangles:
        assert "garment_check(triangles=True)" in (base / "motion_check_tri.py").read_text()
    return scope["garment_check"](triangles=triangles)


def summarize(frames):
    if not frames:
        return None
    low = min(frames, key=lambda row: row["min_signed_m"])
    peak = max(frames, key=lambda row: row["count"])
    return {
        "samples": len(frames), "peak_count": peak["count"], "peak_frame": peak["frame"],
        "sum_count": sum(row["count"] for row in frames), "min_signed_m": low["min_signed_m"],
        "min_frame": low["frame"],
        "below_floor_frames": sum(row["min_signed_m"] < MINIMUM for row in frames),
    }


def check(triangles):
    frames = measure_legacy(triangles) | measure_added(triangles)
    assert tuple(frames) == ("rest", *LEGACY, *ADDED)
    metric = "triangle_overlap_pairs" if triangles else "inside_vertices"
    report = {f"{name}_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
              for name, path in (("master", MASTER), ("motion", MOTION),
                                 ("actions", ACTIONS), ("glb", GARMENT))}
    report.update(metric=metric, minimum_clearance_m=MINIMUM, frame_step=.5,
                  fps={"legacy": 24, "added": 30}, clips={})
    lines = []
    for name, rows in frames.items():
        integers = summarize([r for r in rows if r["frame"] % 1 == 0])
        halves = summarize([r for r in rows if r["frame"] % 1 == .5])
        all_frames = summarize(rows)
        report["clips"][name] = {"combined": all_frames, "integers": integers, "halves": halves,
                                 "frames": rows}
        half_peak = halves["peak_count"] if halves else "—"
        lines.append(f"RESULT {name} {metric} {all_frames['peak_count']} "
                     f"integer_peak {integers['peak_count']} half_peak {half_peak} "
                     f"min_signed_m {all_frames['min_signed_m']:.9f} "
                     f"min_frame {all_frames['min_frame']:g} samples {len(rows)}")
    stem = "motion_check_tri" if triangles else "motion_check"
    (OUT / (stem + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    (OUT / (stem + ".txt")).write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    check("--triangles" in sys.argv)
