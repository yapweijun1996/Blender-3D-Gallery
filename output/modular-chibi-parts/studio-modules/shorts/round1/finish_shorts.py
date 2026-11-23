"""Finish the lining and repeat a full pose sweep before export."""
import json
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shorts import (EXTERIOR, GLB, HERE, SHA, cache_motion, helpers, load_actions,
                        prepare_exterior, shell_arrays, skin_export, summarize, write_json)
from shell_clearance import clean_pairs, generate, local_polish, separating_gaps


def main():
    api, motion = helpers()
    bpy.ops.wm.open_mainfile(filepath=str(EXTERIOR), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    body, arm, obj = (scene.objects[n] for n in ("Base_Body", "Armature", "Studio_Shorts"))
    body.hide_set(False)
    for other in scene.objects:
        if other not in {body, arm, obj}:
            other.hide_viewport = other.hide_render = True
    names = [bone.name for bone in arm.pose.bones]
    runpy.run_path(str(HERE / "polish_geometry.py"))["edge_cleanup"](obj)
    _, faces, uv, edges = prepare_exterior(obj)
    state = np.load(HERE / ".fit_state.npz")
    points, weights = state["points"], state["weights"]
    legacy, faces_all = shell_arrays(points, faces, edges)
    make_tree = api["tree_from"]
    n = len(points)
    reference = np.vstack((points, generate(points, faces, .00016)))
    stabilized, count = clean_pairs(reference, faces_all, n, make_tree, iterations=65)
    stabilized, count = clean_pairs(stabilized, faces_all, n, make_tree, iterations=90, max_outer=.00040)
    refined, self_pairs = local_polish(stabilized, faces_all, n, make_tree, reference)
    refined, _ = clean_pairs(refined, faces_all, n, make_tree, iterations=80, max_outer=.00010)
    print("Lining rest candidates", count, len(self_pairs), flush=True)

    actions = load_actions(scene)
    samples, transforms = cache_motion(scene, arm, body, actions, api)
    skin = api["pose_matrices"](transforms, weights)
    skin = np.concatenate((skin, skin), axis=1)
    history = json.loads((HERE / "fit_history.json").read_text())
    history["lining_attempts"] = []
    for label, coordinates in (("locally separated", refined), ("stabilized", stabilized), ("offset", legacy)):
        tree = make_tree(coordinates, faces_all)
        self_pairs = [(a, b) for a, b in tree.overlap(tree)
                      if a < b and not np.isin(faces_all[a], faces_all[b]).any()]
        gaps = separating_gaps(coordinates, faces_all, self_pairs)
        posed = api["skin_positions"](coordinates, skin)
        d, pairs, _, _ = motion["scan"](posed, faces_all, samples, margin=.0007)
        entry = dict(method=label, self_pairs=len(self_pairs),
                     deepest_self_intersection_m=float(max(0., -gaps.min())) if len(gaps) else 0.,
                     maximum_outer_adjustment_m=float(np.linalg.norm(coordinates[:n] - points, axis=1).max()),
                     max_rest_signed_m=float(d[0].max()), results=summarize(samples, d, pairs))
        history["lining_attempts"].append(entry)
        print(label, "self pairs", len(self_pairs), "min", float(d.min()), "pairs", int(pairs.max()), flush=True)
        if d.min() >= .00058 and d[0].max() <= .0299 and not pairs.any():
            skin_export(scene, arm, body, obj, points, faces, uv, edges, names, weights, api,
                        coordinates=coordinates)
            history.update(glb_sha256=SHA(GLB), chosen_lining=entry)
            write_json("fit_history.json", history)
            break
    else:
        raise RuntimeError("All lining candidates failed the motion gate")


if __name__ == "__main__":
    main()
