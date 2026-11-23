"""Execute the six manager checker entry points with Cycles CPU previews."""

from contextlib import redirect_stdout
from pathlib import Path
import os
from shutil import copyfile
import sys
import types

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shoes import ACTIONS, CARRY, EXPORT, HERE, MASTER, MOTION, digest

INSTALL = Path(os.environ.get("SLIPONS_BLENDER_ROOT",
    "/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
    "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular"))


def render_block(scene, pad):
    return ("\n" + pad).join([
        f"{scene}.render.engine = 'CYCLES'",
        f"{scene}.cycles.device = 'CPU'",
        f"{scene}.cycles.samples = 8",
        f"{scene}.cycles.use_denoising = True",
        f"{scene}.render.resolution_percentage = 100",
        f"{scene}.render.image_settings.file_format = 'PNG'",
        f"{scene}.world = bpy.data.worlds.new('Checker lighting')",
        f"{scene}.world.use_nodes = True",
        f"{scene}.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.86, .89, .96, 1)",
        f"{scene}.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65",
    ])


def run(checker, output, extra=None, triangle=False, reuse=False):
    output.mkdir(parents=True, exist_ok=True)
    sys.argv = [sys.argv[0], "--", *map(str, (MASTER, MOTION, EXPORT, output))]
    if extra is not None:
        sys.argv.append(str(extra))
    shared = extra is None
    if shared:
        old = "sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL'"
        replacement = render_block("sc", "")
        main = checker
    else:
        old = "scene.render.engine='BLENDER_WORKBENCH'"
        replacement = render_block("scene", " " * 8)
        main = checker.with_name("motion_check.py")
    source = main.read_text()
    assert source.count(old) == 1
    source = source.replace(old, replacement)
    cache = HERE / "qa" / "checkers" / "shared" / "vertex"

    def reuse_preview(scene):
        # The completed shared vertex/triangle and sit/hold vertex previews
        # had identical PNG pixel streams for these four legacy poses.
        name = Path(scene.render.filepath).stem
        assert name in ("walk", "run", "wave", "jump")
        assert scene.camera.data.type == "ORTHO" and scene.camera.data.ortho_scale == 1.5
        assert tuple(round(x, 5) for x in scene.camera.location) == (0, -6, .5)
        assert scene.render.resolution_x == scene.render.resolution_y == 500
        action = scene.objects["Armature"].animation_data.action
        first, last = map(round, action.frame_range)
        assert action.name == name and scene.frame_current == int(first + (last - first) * .4)
        copyfile(cache / (name + ".png"), scene.render.filepath)

    if reuse:
        assert not shared and ("CHECKED_GLTF_SHA256 " + digest(EXPORT)) in (cache / "RESULT.txt").read_text()
        render_call = "bpy.ops.render.render(write_still=True)"
        assert source.count(render_call) == 1
        source = source.replace(render_call, "reuse_preview(scene)")
    code = compile(source, str(main), "exec")
    old_modules = {n: sys.modules.pop(n, None) for n in ("motion_check", "chibi")}
    old_path = sys.path.copy()
    try:
        with (output / "RESULT.txt").open("w", buffering=1) as log, redirect_stdout(log):
            print("CHECKER", checker)
            print("CHECKED_GLTF_SHA256", digest(EXPORT))
            print("PREVIEWS", "matching legacy-frame Cycles CPU cache" if reuse else "Cycles CPU")
            print("MEASUREMENT original source")
            if not shared and triangle:
                module = types.ModuleType("motion_check")
                module.__file__ = str(main)
                module.reuse_preview = reuse_preview
                sys.modules[module.__name__] = module
                exec(code, module.__dict__)
                exec(compile(checker.read_text(), str(checker), "exec"),
                     {"__name__": "__main__", "__file__": str(checker)})
            else:
                exec(code, {"__name__": "__main__", "__file__": str(checker), "reuse_preview": reuse_preview})
    finally:
        sys.path[:] = old_path
        for name, original in old_modules.items():
            sys.modules.pop(name, None)
            if original is not None:
                sys.modules[name] = original
    if shared and triangle:
        (output / "motion_check.json").replace(output / "motion_check_tri.json")
    print("CHECKER FINISHED", output.relative_to(HERE), flush=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    groups = {
        "shared": (INSTALL, None),
        "sit-hold": (MOTION.parent / "act", ACTIONS),
        "carry": (MOTION.parent / "act2", CARRY),
    }
    reuse = "--reuse-shared-previews" in args
    selected = [arg for arg in args if arg != "--reuse-shared-previews"]
    for arg in selected or groups:
        name, _, selection = arg.partition(":")
        directory, extra = groups[name]
        for triangle in (False, True):
            checker = "motion_check_tri.py" if triangle else (
                "motion_check_dense.py" if extra is None else "motion_check.py")
            mode = "triangle" if triangle else "vertex"
            if not selection or selection == mode:
                run(directory / checker, HERE / "qa" / "checkers" / name / mode,
                    extra, triangle, reuse and extra is not None)


if __name__ == "__main__":
    main()
