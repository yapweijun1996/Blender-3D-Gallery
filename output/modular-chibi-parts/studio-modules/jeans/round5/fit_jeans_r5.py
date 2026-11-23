"""Refit the shipped round-3 jeans to the eleven-clip gate with Blender 5."""

import math
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils import Matrix

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
R3 = runpy.run_path(str(HERE.parent / "round3/fit_jeans_r3.py"))
R2, PRIOR = R3["R2"], R3["PRIOR"]
PARTS, MASTER, MOTION = R3["PARTS"], R3["MASTER"], R3["MOTION"]
ACTIONS = R3["PARTS"] / "actions-fix/actions_fixed.glb"
BASE = HERE.parent / "round3/jeans_v3.glb"
GLB, BLEND = HERE / "jeans_v5.glb", HERE / "jeans_v5.blend"
LEGACY = R3["CLIPS"]
ADDED = ("sit_down", "sit_idle", "stand_up", "hold_item")
CLIPS = LEGACY + ADDED
MINIMUM, CAP, MARGIN = .0005, .030, .002
TRIANGLE_LIMIT = 8000

mesh_arrays = R3["mesh_arrays"]
evaluated_arrays = R3["evaluated_arrays"]
nearest = R3["nearest"]
tree_from = R3["tree_from"]
skin_matrices = R3["skin_matrices"]
skin_positions = R3["skin_positions"]
read_weights = R3["read_weights"]
limit_weights = R3["limit_weights"]
zone = R3["zone"]
sha256 = R3["sha256"]
average = PRIOR["average"]


def write_json(name, value):
    import json
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def setup(path, editable=False):
    scene, arm, body, garment = R3["setup"](path, editable=editable)
    scene.render.fps, scene.render.fps_base = 30, 1
    previous_actions = set(bpy.data.actions)
    previous_objects = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(ACTIONS))
    actions = {action.name: action for action in set(bpy.data.actions) - previous_actions}
    assert all(name in actions and actions[name].slots for name in ADDED)
    for obj in set(scene.objects) - previous_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data.use_nla = False
    return scene, arm, body, garment


def set_pose(scene, arm, clip, frame):
    action = None if clip == "rest" else bpy.data.actions[clip]
    if arm.animation_data.action != action or action is None:
        arm.animation_data.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        if action:
            arm.animation_data.action = action
            arm.animation_data.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def frames():
    yield "rest", 1.
    for clip in CLIPS:
        first, last = map(float, bpy.data.actions[clip].frame_range)
        first, last = round(first, 5), round(last, 5)
        times = {first, last}
        times.update(i / 2 for i in range(math.ceil(2 * first), math.floor(2 * last) + 1))
        yield from ((clip, time) for time in sorted(times))


def cache_motion(scene, arm, body):
    source = R3["cache_motion"]
    source.__globals__.update(frames=frames, set_pose=set_pose)
    samples, transforms = source(scene, arm, body)
    print("Cached", len(samples), "poses", flush=True)
    return samples, transforms


def summarize(distances, overlaps, samples, points=None, body_joints=None, posed=None):
    source = R3["summarize"]
    source.__globals__["CLIPS"] = CLIPS
    results = source(distances, overlaps, samples)
    if points is not None:
        for clip, result in results.items():
            row = next(i for i, sample in enumerate(samples)
                       if sample[:2] == (clip, result["minimum_frame"]))
            vertex = result["minimum_vertex"]
            body_triangle = samples[row][2].find_nearest(posed[row, vertex])[2]
            result.update(zone=zone(points[vertex]), location_m=points[vertex].tolist(),
                          body_joint=str(body_joints[body_triangle]))
    return results


def evaluate(points, weights, faces, samples, transforms, margin, skin=None):
    if skin is None:
        skin = skin_matrices(transforms, weights)
    posed = skin_positions(points, skin)
    distances, pairs, hits, constraints = R2["scan"](posed, faces, samples, margin=margin, details=False)
    return distances, pairs, hits, constraints, skin, posed


def score(result):
    distances, pairs = result[:2]
    shortfall = np.maximum(0, .00062 - distances)
    hard = int(distances[0].min() < MINIMUM or distances[0].max() > CAP or pairs[0] > 0)
    return (hard, float(pairs.sum() + 4 * (distances < 0).sum() + 1700 * shortfall.sum()),
            int((distances < .00062).sum()))


def passes(result):
    distances, pairs = result[:2]
    return distances.min() >= .00062 and distances[0].max() <= CAP and not pairs.any()


def print_result(label, result, samples, points, body_joints):
    distances, pairs = result[:2]
    rows = summarize(distances, pairs, samples, points, body_joints, result[5])
    brief = {name: (row["max_vertices_inside"], row["max_garment_pairs"],
                    round(1000 * row["minimum_m"], 3), row["minimum_frame"],
                    row["zone"], row["body_joint"]) for name, row in rows.items()}
    print(label, "score", score(result), "rest max mm", float(distances[0].max() * 1000), brief, flush=True)
    return rows


def contact_region(result, triangles, graph):
    distances, _, hits = result[:3]
    active = (distances.min(axis=0) < .001) | np.isin(np.arange(distances.shape[1]), triangles[hits > 0])
    region = active.astype(np.float32)[:, None]
    for _ in range(4):
        region = np.maximum(region, .90 * average(region, graph))
    return region


def limit_rest(old, trial, original, triangles, tree):
    trial = original + R2["limit_delta"](trial - original, CAP)
    trial = PRIOR["enforce_cap"](trial, tree)
    return R2["rest_guard"](old, trial, triangles, tree)


def save_fit(arm, body, garment, points, weights, names):
    do_export = R3["export"]
    do_export.__globals__.update(GLB=GLB, BLEND=BLEND, set_pose=set_pose)
    do_export(arm, body, garment, points, weights, names)


def fit():
    scene, arm, body, garment = setup(BASE, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    points, triangles = mesh_arrays(garment.data)
    original = points.copy()
    weights = read_weights(garment, names)
    _, body_faces = mesh_arrays(body.data)
    body_joints = np.asarray(names)[read_weights(body, names)[body_faces].sum(axis=1).argmax(axis=1)]
    assert np.allclose(weights.sum(axis=1), 1, atol=1e-5)
    result = evaluate(points, weights, triangles, samples, transforms, MARGIN)
    for name in ADDED:
        row = next(i for i, sample in enumerate(samples) if sample[0] == name)
        set_pose(scene, arm, *samples[row][:2])
        actual, _ = evaluated_arrays(garment, bpy.context.evaluated_depsgraph_get())
        assert np.max(abs(actual - result[5][row])) < .000005

    baseline = print_result("ROUND3", result, samples, points, body_joints)
    history = {"source_sha256": sha256(BASE), "motion_sha256": sha256(MOTION),
               "additional_actions_sha256": sha256(ACTIONS), "baseline": baseline, "iterations": []}
    if "--baseline" in sys.argv:
        write_json("baseline.json", baseline)
        return

    graph = PRIOR["adjacency"](garment.data)
    for iteration in range(8):
        if passes(result):
            break
        distances, pairs, hits, constraints, skin, posed = result
        margin = MARGIN
        region = contact_region(result, triangles, graph)
        columns = R2["skin_columns"](weights, names, points)
        use_weights = iteration >= 1 and iteration % 4 != 3
        fit_step = R2["fit_step"]
        candidate, proposed_weights = fit_step(points, original, weights, columns, skin, transforms,
                                               constraints, graph, rest, margin, use_weights)
        candidate = limit_rest(points, points + region * (candidate - points), original, triangles, rest)
        proposed_weights = limit_weights(weights + region * (proposed_weights - weights))
        if iteration == 5 and pairs.any():
            PRIOR["set_vertices"](garment.data, points)
            PRIOR["write_weights"](garment, names, weights)
            backup = garment.data.copy()
            cuts = R2["split_edges"](garment, triangles, hits, local=True)
            if cuts:
                split_p, split_f = mesh_arrays(garment.data)
                split_w = limit_weights(read_weights(garment, names))
                split_result = evaluate(split_p, split_w, split_f, samples, transforms, margin)
                print_result(f"SPLIT {iteration} ({cuts} edges)", split_result, samples, split_p, body_joints)
                if not score(split_result)[0] and score(split_result)[1] < 1.12 * score(result)[1]:
                    points, triangles, weights, result = split_p, split_f, split_w, split_result
                    original = points.copy()
                    graph = PRIOR["adjacency"](garment.data)
                    history["iterations"].append({"stage": iteration, "split_edges": cuts, "score": score(result)})
                    continue
                garment.data = backup

        for scale in (1., .45):
            p = points + scale * (candidate - points)
            w = limit_weights(weights + scale * (proposed_weights - weights))
            test = evaluate(p, w, triangles, samples, transforms, margin, None if use_weights else skin)
            print_result(f"BAKE {iteration} x{scale:g}", test, samples, p, body_joints)
            if score(test) < score(result) or passes(test):
                points, weights, result = p, w, test
                history["iterations"].append({"stage": iteration, "scale": scale, "score": score(result),
                                              "minimum_m": float(result[0].min()),
                                              "overlap_pairs": int(result[1].sum())})
                break
    history["result"] = print_result("FIT", result, samples, points, body_joints)
    assert len(triangles) <= TRIANGLE_LIMIT
    save_fit(arm, body, garment, points, weights, names)
    write_json("fit_history.json", history)

def verify_export():
    import json

    verify = R3["verify_export"]
    verify.__globals__.update(HERE=HERE, GLB=GLB, BLEND=BLEND, BASE=BASE,
                              setup=setup, write_json=write_json)
    verify()
    path = HERE / "export_check.json"
    report = json.loads(path.read_text())
    corrected = {key.replace("round2", "round3"): value for key, value in report.items()}

    def glb_document(filepath):
        import struct
        content = filepath.read_bytes()
        size = struct.unpack_from("<I", content, 12)[0]
        return json.loads(content[20:20 + size])

    source, candidate = glb_document(BASE), glb_document(GLB)
    corrected["round3_material_definition_equal"] = all(
        source.get(field) == candidate.get(field)
        for field in ("materials", "textures", "samplers", "extensionsUsed"))
    assert corrected["round3_material_definition_equal"] and corrected["round3_image_bytes_equal"]
    assert corrected["round3_uvs"] == corrected["round3_uvs_found_after_export"]
    garment = bpy.context.scene.objects["Jeans"]
    weights = read_weights(garment, corrected["joints"])
    corrected["side_seam_control_weights"] = {
        name.split(":")[-1]: {"vertices": int(np.count_nonzero(values)), "maximum": float(values.max())}
        for name, values in zip(corrected["joints"], weights.T)
        if any(label in name for label in ("Shoulder", "Arm")) and np.any(values > 0)
    }
    write_json(path.name, corrected)


if __name__ == "__main__":
    if "--verify-export" in sys.argv:
        verify_export()
    else:
        fit()
