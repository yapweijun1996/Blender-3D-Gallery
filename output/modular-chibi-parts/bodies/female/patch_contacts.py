"""Repair isolated ankle/skin contact keys without rebaking surrounding poses."""
from collections import defaultdict
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_motion import Checker, bone, female_coefficients, foot_lock, gltf_channels, pairs, pose_state, restore, turn
from common import BODY, MASTER, arguments, bind, dispose, load_glb, set_frame
from glb_io import Glb


def repair(input_path, output_path):
    asset = Glb(input_path)
    records = json.loads(input_path.with_suffix(".json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    dispose(load_glb(input_path))
    basis = female_coefficients(Glb(BODY).skeleton())
    checker = Checker(body)
    for animation in asset.doc["animations"]:
        name = animation["name"]
        rows = records[name]
        if not any(r["pairs"] for r in rows):
            continue
        bind(arm, bpy.data.actions[name])
        times = [r["seconds"] for r in rows]
        replacements = defaultdict(dict)
        for i, row in enumerate(rows):
            if not row["pairs"]:
                continue
            set_frame(scene, row["seconds"] * scene.render.fps)
            state = pose_state(arm)
            floors = [v / 1000 for v in row["neutral_floor_mm"]]
            count = len(pairs(checker)[0])
            if not count:
                row.update(pairs=0, regions={})
                continue
            found = False
            for angle in (.15, .3, .6, 1.2, 2.4, 4.8):
                if found:
                    break
                for side in ("Left", "Right"):
                    if found:
                        break
                    foot = bone(arm, side + "Foot")
                    for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
                        if found:
                            break
                        for sign in (-1, 1):
                            restore(arm, state)
                            turn(foot, Vector(axis), angle * sign)
                            bpy.context.view_layer.update()
                            foot_lock(arm, checker, floors)
                            hits, points = pairs(checker)
                            if hits:
                                continue
                            channels = defaultdict(list)
                            gltf_channels(arm, basis, channels)
                            joint_index = next(j for j, b in basis.items() if b[0] == foot.name)
                            for attribute in ("rotation", "translation"):
                                replacements[joint_index, attribute][i] = channels[joint_index, attribute][0]
                            row.update(pairs=0, regions={}, floor_mm=[
                                float(points[checker.feet[s], 2].min() * 1000) for s in ("Left", "Right")])
                            print("LOCAL ANKLE REPAIR", name, row["seconds"], side, axis, angle * sign,
                                  count, "-> 0", flush=True)
                            found = True
                            break
        if not replacements:
            continue
        common_times = asset.floats(times, "SCALAR")
        for channel in animation["channels"]:
            target = channel["target"]
            path, node = target["path"], target["node"]
            changed = replacements.get((node, path))
            if not changed:
                continue
            sampler = animation["samplers"][channel["sampler"]]
            old = asset.accessor(sampler["output"]).copy()
            if len(old) == 1:
                old = np.repeat(old, len(times), axis=0)
            assert len(old) == len(times)
            for i, value in changed.items():
                if path == "rotation" and np.dot(old[i], value) < 0:
                    value = -value
                old[i] = value
            sampler["input"] = common_times
            sampler["output"] = asset.floats(old, "VEC4" if path == "rotation" else "VEC3")
    asset.write(output_path)
    output_path.with_suffix(".json").write_text(json.dumps(records, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    paths = [Path(value).resolve() for value in arguments()]
    assert paths[1].parent == Path(__file__).resolve().parent / ".runtime"
    repair(*paths)
