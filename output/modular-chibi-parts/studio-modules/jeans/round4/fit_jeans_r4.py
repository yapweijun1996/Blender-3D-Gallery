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
ACTIONS = R3["PARTS"] / "actions-astra/actions.glb"
BASE = HERE.parent / "round3/jeans_v3.glb"
GLB, BLEND = HERE / "jeans_v4.glb", HERE / "jeans_v4.blend"
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


def local_refit(strict_legacy=False):
    """Use exact incident-face checks to resolve conflicting contact directions."""
    import json

    checkpoint = GLB if GLB.exists() else BASE
    scene, arm, body, garment = setup(checkpoint, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    points, faces = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    _, body_faces = mesh_arrays(body.data)
    body_joints = np.asarray(names)[read_weights(body, names)[body_faces].sum(axis=1).argmax(axis=1)]
    graph = PRIOR["adjacency"](garment.data)
    anatomy = limit_weights(R2["body_weights"](points, body, names, rest))
    shape = R2["HOODIE"]["PRIOR"]["RestShape"](garment.data, points, rest)
    directions = R2["HOODIE"]["PRIOR"]["scaled_directions"](28).astype(np.float32)
    directions = np.vstack((directions, np.eye(3), -np.eye(3)))
    original = points.copy()
    original_weights = weights.copy()
    anchors = original.copy()
    result = evaluate(points, weights, faces, samples, transforms, .001)
    previous = print_result("LOCAL START", result, samples, points, body_joints)
    local_history = []
    legacy_rows = np.array([name == "rest" or name in LEGACY for name, *_ in samples])

    def priority(distances, crossings):
        old = float(crossings[legacy_rows].sum() + 4 * (distances[legacy_rows] < 0).sum())
        shortfall = np.maximum(0, .00062 - distances)
        return (score((distances, crossings))[0], float(crossings.sum() + 4 * (distances < 0).sum()
                                                       + 1600 * shortfall.sum() + 2 * old))

    guard_rows = np.flatnonzero(legacy_rows)
    legacy_trees = [samples[row][2] for row in guard_rows]
    for sweep in range(2 if strict_legacy else 3):
        distances, overlaps, hits, _, skin, posed = result
        if passes(result):
            break
        point_contacts = (distances < .00068).sum(axis=0).astype(float)
        face_contacts = np.zeros((len(samples), len(faces)), dtype=np.int16)
        for i in np.flatnonzero(overlaps):
            body_tree = samples[i][2]
            pairs = np.asarray(body_tree.overlap(tree_from(posed[i], faces)))
            np.add.at(face_contacts[i], pairs[:, 1], 1)
        rank = point_contacts * 4 + np.bincount(faces.ravel(), weights=np.repeat(hits, 3), minlength=len(points))
        order = np.flatnonzero(rank)
        order = order[np.argsort(-rank[order], kind="stable")]
        columns = R2["skin_columns"](weights, names, points)
        graph_points = average(points, graph)
        pending = []
        visited = 0
        for vertex in order:
            incident = shape.incidence[vertex]
            patch_indices, inverse = np.unique(faces[incident], return_inverse=True)
            local_faces = inverse.reshape(-1, 3)
            slot = np.searchsorted(patch_indices, vertex)
            previous_hits = face_contacts[:, incident].sum(axis=1)
            worst_rows = np.r_[np.argsort(-previous_hits, kind="stable")[:17],
                               np.argsort(distances[:, vertex], kind="stable")[:16]]
            # Spread the coarse samples across both motion banks. Include the
            # most difficult adjacent frames from each library at full density.
            coarse = np.r_[np.arange(0, len(samples), 35), np.arange(824, len(samples), 11)]
            rows = np.unique(np.r_[0, worst_rows, coarse])
            selected_trees = [samples[index][2] for index in rows]
            patch = posed[rows[:, None], patch_indices]
            current = points[vertex]
            current_weights = weights[vertex]
            moves = np.vstack((np.zeros(3), *(radius * directions for radius in
                                               ((.0015, .0035, .007, .012) if sweep == 0
                                                else (.0007, .0018, .0045, .010, .018)))))
            positions = np.asarray(current + moves, dtype=np.float32)
            rest_gaps = nearest(rest, positions)[0]
            admissible = (rest_gaps >= .0007) & (rest_gaps < CAP - .0001)
            admissible &= np.linalg.norm(positions - anchors[vertex], axis=1) <= .025
            admissible[0] = True
            positions = positions[admissible]
            j = np.unique(np.r_[columns[vertex], np.flatnonzero(current_weights),
                                np.flatnonzero(anatomy[vertex])])
            alternatives = [current_weights, .5 * current_weights + .5 * anatomy[vertex],
                            .2 * current_weights + .8 * anatomy[vertex], original_weights[vertex]]
            for joint in j:
                basis = np.zeros_like(current_weights)
                basis[joint] = 1
                alternatives.extend(current_weights + mix * (basis - current_weights) for mix in (.12, .32, .60))
            if points[vertex, 2] > .220:
                side = "Left" if points[vertex, 0] > 0 else "Right"
                for suffix in ("Shoulder", "Arm", "ForeArm"):
                    basis = np.zeros_like(current_weights)
                    basis[names.index("mixamorig:" + side + suffix)] = 1
                    alternatives.extend(current_weights + mix * (basis - current_weights)
                                        for mix in (.015, .04, .075))
            trial_weights = limit_weights(np.array(alternatives))
            # Evaluate every geometry direction with the current skin, then a
            # compact joint/shape grid for lower-body weight adjustments.
            size = min(len(positions), 18)
            candidates = np.vstack((positions, np.tile(positions[:size], (len(trial_weights) - 1, 1))))
            candidate_weights = np.vstack((np.repeat(current_weights[None], len(positions), axis=0),
                                           np.repeat(trial_weights[1:], size, axis=0)))
            matrices = skin_matrices(transforms[rows], candidate_weights)
            trial = (matrices[..., :3] @ candidates[None, :, :, None])[..., 0] + matrices[..., 3]
            gaps = np.array([nearest(tree, trial[i])[0] for i, tree in enumerate(selected_trees)])
            pose_weight = np.where(legacy_rows[rows], 2.2, 1.)
            deficit = 1000 * np.maximum(0, .00085 - gaps)
            approx = np.sum(pose_weight[:, None] * (1.3 * (gaps < 0) + .15 * deficit**2), axis=0)
            approx += .25 * np.linalg.norm((candidates - current) * 1000, axis=1)
            approx += .45 * np.abs(candidate_weights - current_weights).sum(axis=1)
            approx += .14 * 1000 * np.maximum(0, np.linalg.norm(candidates - graph_points[vertex], axis=1)
                                             - np.linalg.norm(current - graph_points[vertex]))

            # Mid-edge witnesses ensure the shortlist includes moves that open
            # a cut in an otherwise clear trio of corners.
            incident_rows = np.flatnonzero(previous_hits[rows])
            for row in incident_rows[:14]:
                local = patch[row][local_faces]
                for fraction in (.5, .78):
                    witness = local.mean(axis=1) * (1 - fraction) + fraction * patch[row, slot]
                    delta = trial[row] - patch[row, slot]
                    shifted = witness[None] + fraction * delta[:, None]
                    gaps_at_witness = nearest(selected_trees[row], shifted.reshape(-1, 3))[0].reshape(len(trial[row]), -1)
                    approx += .08 * np.square(1000 * np.maximum(0, .0004 - gaps_at_witness)).sum(axis=1)
            shortlist = np.r_[0, np.argsort(approx, kind="stable")[:12]]
            exact_rows = np.unique(np.r_[0, np.flatnonzero(previous_hits[rows]),
                                         np.argsort(gaps[:, 0], kind="stable")[:12]])
            best = (float("inf"), 0)
            for candidate in np.unique(shortlist):
                if candidate and not shape.accepts(vertex, candidates[candidate], points):
                    continue
                cut_count = 0.
                for row in exact_rows:
                    proposed = patch[row].copy()
                    proposed[slot] = trial[row, candidate]
                    cut_count += pose_weight[row] * len(selected_trees[row].overlap(tree_from(proposed, local_faces)))
                value = float(cut_count + approx[candidate])
                if value >= best[0]:
                    continue
                if strict_legacy and candidate:
                    legacy_skin = skin_matrices(transforms[guard_rows], candidate_weights[candidate:candidate + 1])[:, 0]
                    legacy_trial = legacy_skin[..., :3] @ candidates[candidate] + legacy_skin[..., 3]
                    old_patch = posed[guard_rows[:, None], patch_indices]
                    old_patch[:, slot] = legacy_trial
                    original_gaps = distances[guard_rows, vertex]
                    safe = True
                    for j, legacy_tree in enumerate(legacy_trees):
                        gap = nearest(legacy_tree, legacy_trial[j:j + 1])[0][0]
                        if gap < min(.00055, original_gaps[j] - .000002):
                            safe = False
                            break
                        if len(legacy_tree.overlap(tree_from(old_patch[j], local_faces))) > previous_hits[guard_rows[j]]:
                            safe = False
                            break
                    if not safe:
                        continue
                best = value, candidate
            index = best[1]
            if index:
                points[vertex] = candidates[index]
                weights[vertex] = candidate_weights[index]
                matrix = skin_matrices(transforms, weights[vertex:vertex + 1])[:, 0]
                posed[:, vertex] = (matrix[..., :3] @ points[vertex]) + matrix[..., 3]
                pending.append(int(vertex))
            visited += 1
            if visited % 75 == 0:
                print("LOCAL SEARCH", sweep, visited, len(order), "moves", len(pending), flush=True)

        test = evaluate(points, weights, faces, samples, transforms, .001)
        after = print_result(f"LOCAL {sweep}", test, samples, points, body_joints)
        before_score, after_score = priority(distances, overlaps), priority(*test[:2])
        local_history.append({"stage": sweep, "attempted_vertices": len(order), "moves": len(pending),
                              "before": before_score, "after": after_score, "results": after})
        if after_score >= before_score:
            break
        original, original_weights = points.copy(), weights.copy()
        result = test
        previous = after

    path = HERE / "fit_history.json"
    history = json.loads(path.read_text()) if path.exists() else {}
    history["strict_local_stages" if strict_legacy else "local_stages"] = local_history
    history["result"] = previous
    save_fit(arm, body, garment, original, original_weights, names)
    write_json("fit_history.json", history)


def shape_patches(checkpoint=GLB):
    """Search coherent waistband and thigh moves around crossing body panels."""
    import json

    scene, arm, body, garment = setup(checkpoint, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    points, faces = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    _, body_faces = mesh_arrays(body.data)
    body_joints = np.asarray(names)[read_weights(body, names)[body_faces].sum(axis=1).argmax(axis=1)]
    result = evaluate(points, weights, faces, samples, transforms, .001)
    print_result("PATCH START", result, samples, points, body_joints)
    original = points.copy()
    original_weights = weights.copy()
    joint = {name.split(":")[-1]: i for i, name in enumerate(names)}
    sample_clips = np.array([s[0] for s in samples])
    anatomy = limit_weights(R2["body_weights"](points, body, names, rest))
    prior_rows = np.flatnonzero(np.isin(sample_clips, LEGACY))
    updated = []
    smoothstep = PRIOR["smoothstep"]

    def merit(distances, counts, rows):
        old = np.isin(sample_clips[rows], LEGACY)
        violation = 1000 * np.maximum(0., .00062 - distances)
        return float(counts.sum() + 4 * (distances < 0).sum() + 2.3 * violation.sum()
                     + 1.8 * (counts[old].sum() + 3 * (distances[old] < 0).sum() + violation[old].sum()))

    for side, region in ((1., "waist"), (-1., "waist"), (-1., "thigh"),
                         (1., "thigh"), (1., "waist"), (-1., "waist")):
        x, y, z = original.T
        if region == "waist":
            mask = smoothstep(.060, .114, side * x) * smoothstep(.316, .410, z)
            mask *= 1 - smoothstep(.040, .090, abs(y + .021))
        else:
            center = np.array((side * .085, -.067, .256))
            extent = np.asarray((.085, .068, .083))
            mask = 1 - smoothstep(0., 1., np.linalg.norm((original - center) / extent, axis=1))
        impacted = np.flatnonzero((mask[faces] > .015).any(axis=1))
        indices, inverse = np.unique(faces[impacted], return_inverse=True)
        local_faces = inverse.reshape(-1, 3)
        amplitude = mask[indices, None]
        current_points = points[indices]
        current_weights = weights[indices]
        # Favor the sampled frames affecting this patch and retain all motion
        # families in the coarse ranking before an exact full-motion check.
        d, p, _, _, skin, posed = result
        local_count = np.zeros(len(samples), dtype=int)
        for row in np.flatnonzero(p):
            overlap = samples[row][2].overlap(tree_from(posed[row, indices], local_faces))
            local_count[row] = len(overlap)
        ranked = []
        for clip in CLIPS:
            clips = np.flatnonzero(sample_clips == clip)
            ranking = sorted(clips, key=lambda row: (-local_count[row], d[row, indices].min()))
            if local_count[clips].max() or d[clips[:, None], indices].min() < .001:
                ranked.extend(ranking[:5])
            ranked.extend(clips[::max(1, len(clips) // 5)])
        focus = np.unique(np.r_[0, ranked, prior_rows[::37]])
        trees = [samples[row][2] for row in focus]
        current_skin = skin[np.ix_(focus, indices)]
        base_cost = merit(d[np.ix_(focus, indices)], local_count[focus], focus)
        _, _, outward, _ = nearest(rest, current_points)

        def rest_candidate(coords):
            coords = original[indices] + R2["limit_delta"](coords - original[indices], .03)
            for _ in range(4):
                clearance, _, normals, _ = nearest(rest, coords)
                correction = np.maximum(0, .00105 - clearance) - np.maximum(0, clearance - .0298)
                coords += correction[:, None] * normals
            return coords

        def test(coords, candidate_skin, early_limit):
            positions = skin_positions(coords, candidate_skin)
            total = 0.
            for i, tree in enumerate(trees):
                gap = nearest(tree, positions[i])[0]
                cuts = len(tree.overlap(tree_from(positions[i], local_faces)))
                if i == 0 and (cuts or gap.min() < MINIMUM or gap.max() > CAP):
                    return float("inf")
                total += merit(gap[None], np.array([cuts]), focus[i:i + 1])
                if total > early_limit:
                    break
            return total

        choices = []
        axes = [(side, 0, 0), (-side, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, -1), (0, 0, 1),
                (side, .65, -.65), (side, -.65, -.65), (-side, 1, -.9), (-side, -1, -.9),
                (0, 1, -1), (0, -1, -1), (side, .45, .6)]
        for axis in axes:
            direction = np.asarray(axis) / np.linalg.norm(axis)
            for magnitude in (.005, .010, .018, .028):
                choices.append((current_points + (magnitude * direction) * amplitude, current_weights,
                                current_skin, f"axis {axis} {magnitude:g}"))
        for magnitude in (.006, .012, .023, -.005, -.012):
            choices.append((current_points + outward * magnitude * amplitude, current_weights, current_skin,
                            f"radial {magnitude:g}"))
        leg = joint["LeftUpLeg" if side > 0 else "RightUpLeg"]
        fixes = [(anatomy[indices], "transferred")]
        for label, j in (("hip", joint["Hips"]), ("thigh", leg), ("spine", joint["Spine"])):
            basis = np.zeros_like(current_weights)
            basis[:, j] = 1
            fixes.append((basis, label))
        for target, label in fixes:
            for fraction in (.24, .55, .85):
                alternative = limit_weights(current_weights + (target - current_weights) * amplitude * fraction)
                alternative_skin = skin_matrices(transforms[focus], alternative)
                for lift in (0., -.005, .007):
                    coords = current_points + lift * outward * amplitude
                    choices.append((coords, alternative, alternative_skin, f"{label} {fraction:g} lift {lift:g}"))
        # A small shoulder or upper-arm contribution can open a narrow
        # moving side seam while the hip and thigh retain primary control.
        side_name = "Left" if side > 0 else "Right"
        for suffix in ("Shoulder", "Arm", "ForeArm"):
            control = np.zeros_like(current_weights)
            control[:, joint[side_name + suffix]] = 1
            for fraction in (.02, .045, .075):
                alternative = limit_weights(current_weights + (control - current_weights) * amplitude * fraction)
                alternative_skin = skin_matrices(transforms[focus], alternative)
                for lift in (0., -.004, .010):
                    coords = current_points + lift * outward * amplitude
                    choices.append((coords, alternative, alternative_skin, f"{side_name}{suffix} {fraction:g} lift {lift:g}"))
        proposals = []
        for coords, influence, candidate_skin, label in choices:
            coords = rest_candidate(coords)
            value = test(coords, candidate_skin, base_cost)
            if value < base_cost:
                proposals.append((value, label, coords, influence))
        proposals.sort(key=lambda entry: entry[0])
        print("PATCH", side, region, len(indices), len(focus), "start", base_cost,
              "best", [entry[:2] for entry in proposals[:4]], flush=True)
        for _, label, coords, influence in proposals[:3]:
            candidate = points.copy()
            candidate[indices] = coords
            candidate = limit_rest(points, candidate, original, faces, rest)
            candidate_weights = weights.copy()
            candidate_weights[indices] = influence
            trial = evaluate(candidate, candidate_weights, faces, samples, transforms, .001)
            before = merit(*result[:2], np.arange(len(samples)))
            after = merit(*trial[:2], np.arange(len(samples)))
            print("PATCH FULL", side, region, label, before, after, flush=True)
            if not score(trial)[0] and after < before:
                result, points, weights = trial, candidate, candidate_weights
                updated.append({"side": side, "region": region, "proposal": label, "before": before, "after": after})
                break

    path = HERE / "fit_history.json"
    history = json.loads(path.read_text()) if path.exists() else {}
    history["shape_patches"] = updated
    history["result"] = print_result("PATCH END", result, samples, points, body_joints)
    if updated:
        save_fit(arm, body, garment, points, weights, names)
    write_json("fit_history.json", history)


def preserve_legacy():
    """Pull the few legacy collision patches toward the verified round-3 fit."""
    import json

    scene, arm, body, garment = setup(GLB, editable=True)
    reference = PRIOR["import_garment"](BASE, merge=True)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    points, faces = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    source_points, _ = mesh_arrays(reference.data)
    source_weights = read_weights(reference, names)
    _, body_faces = mesh_arrays(body.data)
    body_joints = np.asarray(names)[read_weights(body, names)[body_faces].sum(axis=1).argmax(axis=1)]
    rows = np.flatnonzero([clip in ("rest", *LEGACY) for clip, *_ in samples])

    def uv_keys(mesh):
        norms = np.empty(len(mesh.loops) * 2, dtype=np.float32)
        mesh.uv_layers.active.uv.foreach_get("vector", norms)
        uv = np.rint(norms.reshape(-1, 2) * 10**6).astype(int)
        verts = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", verts)
        keys = [set() for _ in mesh.vertices]
        for index, value in zip(verts, uv):
            keys[index].add(tuple(value))
        return keys

    source = {}
    for i, keys in enumerate(uv_keys(reference.data)):
        for key in keys:
            source.setdefault(key, []).append(i)
    matched = np.full(len(points), -1, dtype=int)
    for i, keys in enumerate(uv_keys(garment.data)):
        options = sorted({index for key in keys for index in source.get(key, [])})
        if options:
            distances = np.linalg.norm(source_points[options] - points[i], axis=1)
            near = distances.argmin()
            if distances[near] < .035:
                matched[i] = options[near]
    assert (matched >= 0).mean() > .85
    valid = matched >= 0
    fallback_points, fallback_weights = points.copy(), weights.copy()
    fallback_points[valid] = source_points[matched[valid]]
    fallback_weights[valid] = source_weights[matched[valid]]
    bpy.data.objects.remove(reference, do_unlink=True)
    graph = PRIOR["adjacency"](garment.data)

    def old_score(result):
        distance, count = result[:2]
        sub = distance[rows]
        return (score(result)[0], int(count[rows].sum() + 4 * (sub < 0).sum()),
                int((sub < MINIMUM).sum()), float(np.maximum(0, MINIMUM - sub).sum()))

    result = evaluate(points, weights, faces, samples, transforms, .0007)
    stages = []
    for iteration in range(6):
        d, p, _, _, _, posed = result
        initial = old_score(result)
        if initial == (0, 0, 0, 0.):
            break
        active = (d[rows].min(axis=0) < .000505)
        for i in rows[p[rows] > 0]:
            pairs = samples[i][2].overlap(tree_from(posed[i], faces))
            active[faces[np.asarray(pairs)[:, 1]]] = True
        region = active.astype(np.float32)[:, None]
        for _ in range(1 + iteration % 3):
            region = np.maximum(region, .88 * average(region, graph))
        region *= valid[:, None]
        for blend in (1., .55):
            p0 = points + blend * region * (fallback_points - points)
            w0 = limit_weights(weights + blend * region * (fallback_weights - weights))
            p0 = R2["rest_guard"](points, p0, faces, rest)
            trial = evaluate(p0, w0, faces, samples, transforms, .0007)
            value = old_score(trial)
            print("LEGACY REPAIR", iteration, int(active.sum()), blend, initial, value, flush=True)
            if value < initial:
                points, weights, result = p0, w0, trial
                stages.append({"stage": iteration, "blend": blend, "restored_vertices": int(active.sum()),
                               "before": initial, "after": value})
                break
        else:
            break
    final = print_result("LEGACY PROTECTION", result, samples, points, body_joints)
    if stages:
        save_fit(arm, body, garment, points, weights, names)
        path = HERE / "fit_history.json"
        history = json.loads(path.read_text())
        history["legacy_repair"] = stages
        history["result"] = final
        write_json(path.name, history)


def refine_split_contacts():
    """Fit split-edge vertices before deciding whether the cuts improve the result."""
    import json

    scene, arm, body, garment = setup(GLB, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    points, faces = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    _, body_faces = mesh_arrays(body.data)
    body_joints = np.asarray(names)[read_weights(body, names)[body_faces].sum(axis=1).argmax(axis=1)]
    initial = evaluate(points, weights, faces, samples, transforms, .001)
    old = np.array([sample[0] in ("rest", *LEGACY) for sample in samples])

    def measure(result):
        distance, pairs = result[:2]
        return (score(result)[0], score(result)[1] + 4 * pairs[old].sum() + 9 * (distance[old] < MINIMUM).sum())

    cuts = R2["split_edges"](garment, faces, initial[2], local=True)
    if not cuts:
        return
    points, faces = mesh_arrays(garment.data)
    weights = limit_weights(read_weights(garment, names))
    graph = PRIOR["adjacency"](garment.data)
    original = points.copy()
    for _ in range(4):
        gap, _, normals, _ = nearest(rest, points)
        points += (np.maximum(0., .00095 - gap) - np.maximum(0., gap - .0298))[:, None] * normals
    installed = evaluate(points, weights, faces, samples, transforms, .001)
    print_result(f"FIT SPLITS START ({cuts})", installed, samples, points, body_joints)
    records = []
    for i in range(4):
        region = contact_region(installed, faces, graph)
        columns = R2["skin_columns"](weights, names, points)
        candidate, influences = R2["fit_step"](
            points, original, weights, columns, installed[4], transforms, installed[3], graph,
            rest, .001, i % 2 == 1)
        candidate = limit_rest(points, points + .65 * region * (candidate - points), original, faces, rest)
        influences = limit_weights(weights + .70 * region * (influences - weights))
        proposed = evaluate(candidate, influences, faces, samples, transforms, .001)
        value = measure(proposed)
        print("FIT SPLITS", i, measure(installed), value, flush=True)
        records.append({"stage": i, "before": measure(installed), "after": value})
        if value < measure(installed):
            points, weights, installed = candidate, influences, proposed
    accepted = measure(installed) < measure(initial) and not score(installed)[0]
    print("FIT SPLITS ACCEPTED", accepted, measure(initial), measure(installed), flush=True)
    path = HERE / "fit_history.json"
    history = json.loads(path.read_text())
    history["split_edge_trial"] = {"edges": cuts, "accepted": bool(accepted), "stages": records}
    if accepted:
        history["result"] = print_result("FIT SPLITS END", installed, samples, points, body_joints)
        save_fit(arm, body, garment, points, weights, names)
    write_json(path.name, history)


def fix_reimported_legacy():
    """Locate legacy contacts directly on the GLB's split vertices and repair them."""
    import json
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree

    scene, arm, body, garment = setup(GLB)
    source = PRIOR["import_garment"](BASE, merge=False)
    names = [bone.name for bone in arm.pose.bones]
    points, faces = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    original, _ = mesh_arrays(source.data)
    original_weights = read_weights(source, names)

    def coordinates(mesh):
        mesh.calc_loop_triangles()
        return [tuple(face.vertices) for face in mesh.loop_triangles]

    def keys(mesh):
        values = np.empty(len(mesh.loops) * 2, dtype=np.float32)
        mesh.uv_layers.active.uv.foreach_get("vector", values)
        vertices = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", vertices)
        for index, uv in zip(vertices, np.rint(values.reshape(-1, 2) * 10**6).astype(int)):
            yield index, tuple(uv)

    lookup = {}
    for index, uv in keys(source.data):
        lookup.setdefault(uv, set()).add(index)
    match, best = np.full(len(points), -1, dtype=int), np.full(len(points), np.inf)
    for index, uv in keys(garment.data):
        candidates = sorted(lookup.get(uv, ()))
        if candidates:
            delta = np.linalg.norm(original[candidates] - points[index], axis=1)
            nearest_index = delta.argmin()
            if delta[nearest_index] < min(best[index], .040):
                best[index] = delta[nearest_index]
                match[index] = candidates[nearest_index]
    assert (match >= 0).mean() > .95
    bpy.data.objects.remove(source, do_unlink=True)
    body_faces = coordinates(body.data)
    garment_faces = coordinates(garment.data)
    selected_frames = [(name, frame) for name, frame in frames() if name in ("rest", *LEGACY)]
    tree = KDTree(len(points))
    for index, xyz in enumerate(points):
        tree.insert(xyz, index)
    tree.balance()
    seam = [np.array([entry[1] for entry in tree.find_range(Vector(xyz), .00000025)], dtype=int)
            for xyz in points]
    incident = [[] for _ in points]
    for index, face in enumerate(faces):
        for vertex in face:
            incident[vertex].append(index)

    def posed(obj, dep):
        evaluated = obj.evaluated_get(dep)
        transform = evaluated.matrix_world
        return [transform @ v.co for v in evaluated.data.vertices]

    def inspect(sample_times):
        for clip, frame in sample_times:
            set_pose(scene, arm, clip, frame)
            dep = bpy.context.evaluated_depsgraph_get()
            body_points = posed(body, dep)
            jeans_points = posed(garment, dep)
            surface = BVHTree.FromPolygons(body_points, body_faces, all_triangles=True)
            jeans = BVHTree.FromPolygons(jeans_points, garment_faces, all_triangles=True)
            crossings = surface.overlap(jeans)
            signed = np.fromiter(((pos - hit[0]).dot(hit[1]) for pos in jeans_points
                                  for hit in (surface.find_nearest(pos),)), dtype=np.float64)
            low = np.flatnonzero(signed < MINIMUM)
            if crossings or len(low):
                yield clip, frame, len(crossings), float(signed.min()), low, crossings

    history = []
    for stage in range(4):
        failures = list(inspect(selected_frames))
        if not failures:
            break
        active = set()
        for clip, frame, count, low, vertices, crossings in failures:
            print("EXACT LEGACY", stage, clip, frame, count, low, len(vertices), flush=True)
            active.update(map(int, vertices))
            for _, face in crossings:
                active.update(garment_faces[face])
        if stage > 1:
            active |= {int(corner) for index in active for face in incident[index] for corner in faces[face]}
        ids = np.unique(np.concatenate([seam[index] for index in sorted(active)]))
        ids = ids[match[ids] >= 0]
        if not len(ids):
            break
        points[ids] = original[match[ids]]
        weights[ids] = original_weights[match[ids]]
        PRIOR["set_vertices"](garment.data, points)
        PRIOR["write_weights"](garment, names, weights)
        history.append({"pass": stage, "frames_with_errors": len(failures),
                        "restored_export_vertices": len(ids),
                        "minimum_m": min(f[3] for f in failures),
                        "legacy_pair_count": sum(f[2] for f in failures)})
    if history:
        save_fit(arm, body, garment, points, weights, names)
        path = HERE / "fit_history.json"
        records = json.loads(path.read_text())
        records.setdefault("exact_legacy_repair", []).extend(history)
        write_json(path.name, records)


def stabilize_export_floor(minimum_step=.0004, use_actual=True):
    """Give round-trip-sensitive legacy vertices a positive clearance margin."""
    import json
    from mathutils import Vector

    report = json.loads((HERE / "motion_check.json").read_text())
    assert report["garment_sha256"] == sha256(GLB)
    failure_frames = {(clip, row["frame"])
                      for clip in ("rest", *LEGACY)
                      for row in report["frames"][clip] if row["minimum_m"] < MINIMUM}
    if not failure_frames:
        return
    scene, arm, body, garment = setup(GLB)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    points, faces = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    legacy_rows = np.flatnonzero([clip in ("rest", *LEGACY) for clip, *_ in samples])

    def signed(tree, points):
        return np.array([(point - hit[0]).dot(hit[1])
                         for point in map(Vector, points.tolist())
                         for hit in (tree.find_nearest(point),)])

    active = set()
    for row, sample in enumerate(samples):
        if sample[:2] in failure_frames:
            set_pose(scene, arm, *sample[:2])
            coordinates, _ = evaluated_arrays(garment, bpy.context.evaluated_depsgraph_get())
            active.update(map(int, np.flatnonzero(signed(sample[2], coordinates) < MINIMUM)))
    shape = R2["HOODIE"]["PRIOR"]["RestShape"](garment.data, points, samples[0][2])
    directions = R2["HOODIE"]["PRIOR"]["scaled_directions"](40).astype(np.float32)
    directions = np.vstack((directions, np.eye(3), -np.eye(3)))
    changes = []
    for vertex in sorted(active):
        if vertex not in active:
            continue
        group = np.flatnonzero(np.linalg.norm(points - points[vertex], axis=1) < .00000025)
        if len(group) == 0:
            continue
        rows = np.unique(np.concatenate([shape.incidence[index] for index in group]))
        other_indices, inverse = np.unique(faces[rows], return_inverse=True)
        local_faces = inverse.reshape(-1, 3)
        group_local = np.searchsorted(other_indices, group)
        patch_skin = skin_matrices(transforms, weights[other_indices])
        patch_poses = skin_positions(points[other_indices], patch_skin)
        if use_actual:
            for i in legacy_rows:
                set_pose(scene, arm, *samples[i][:2])
                evaluated = garment.evaluated_get(bpy.context.evaluated_depsgraph_get())
                world = evaluated.matrix_world
                patch_poses[i] = [world @ evaluated.data.vertices[int(index)].co for index in other_indices]
        scales = (.0004, .0008, .0014, .0022, .0033, .0046)
        offsets = np.vstack((np.zeros(3), *(scale * directions for scale in scales if scale >= minimum_step)))
        misses = np.zeros(len(offsets))
        for i in legacy_rows:
            positions = patch_poses[i, group_local[:1]]
            linear = patch_skin[i, group_local[0], :, :3]
            scored = signed(samples[i][2], positions + offsets @ linear.T)
            misses += np.maximum(0., .00080 - scored)
        ordering = np.argsort(250 * misses + np.linalg.norm(offsets, axis=1), kind="stable")
        after = None
        for option in ordering[:32]:
            offset = offsets[option]
            if not option or misses[option] > .00003:
                continue
            if not all(shape.accepts(index, points[index] + offset, points) for index in group):
                continue
            delta = patch_skin[:, group_local, :, :3] @ offset
            candidate = patch_poses.copy()
            candidate[:, group_local] += delta
            if signed(samples[0][2], candidate[0, group_local]).max() > CAP:
                continue
            clear = True
            for i in legacy_rows:
                tree = samples[i][2]
                current = candidate[i, group_local]
                if (signed(tree, current) < .00072).any() or tree.overlap(tree_from(candidate[i], local_faces)):
                    clear = False
                    break
                jitters = current[:, None] + .000020 * np.vstack((np.eye(3), -np.eye(3)))
                if (signed(tree, jitters.reshape(-1, 3)) < .00054).any():
                    clear = False
                    break
            if clear:
                after = offset
                break
        if after is not None:
            prior = points[group].copy()
            points[group] += after
            changes.append({"vertices": group.tolist(), "rest_offset_m": after.tolist(),
                            "original_location_m": prior[0].tolist()})
            active.difference_update(group)
        print("EXPORT FLOOR", vertex, "moved", after is not None, changes[-1:] if after is not None else [], flush=True)
    if changes:
        save_fit(arm, body, garment, points, weights, names)
        history_path = HERE / "fit_history.json"
        records = json.loads(history_path.read_text())
        records.setdefault("roundtrip_floor_offsets", []).extend(changes)
        write_json(history_path.name, records)


def preserve_stable_export(stable_path, precise_path):
    """Transfer the two Blender-edited seam samples without requantizing the rest."""
    import json
    import struct

    def chunks(path):
        asset = path.read_bytes()
        metadata_size = struct.unpack_from("<I", asset, 12)[0]
        return json.loads(asset[20:20 + metadata_size]), bytearray(asset[28 + metadata_size:])

    stable, binary = chunks(stable_path)
    precise, precise_binary = chunks(precise_path)
    primitive, = stable["meshes"][0]["primitives"]
    precise_primitive, = precise["meshes"][0]["primitives"]

    def rows(doc, payload, index, kind, columns):
        accessor = doc["accessors"][index]
        view = doc["bufferViews"][accessor["bufferView"]]
        width = np.dtype(kind).itemsize * columns
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        return np.ndarray((accessor["count"], columns), dtype=kind, buffer=payload, offset=offset,
                          strides=(view.get("byteStride", width), np.dtype(kind).itemsize))

    source_uv = rows(stable, binary, primitive["attributes"]["TEXCOORD_0"], "<f4", 2)
    edit_uv = rows(precise, precise_binary, precise_primitive["attributes"]["TEXCOORD_0"], "<f4", 2)
    assert np.array_equal(source_uv, edit_uv)
    stable_index = stable["accessors"][primitive["indices"]]
    index_kind = {5123: "<u2", 5125: "<u4"}[stable_index["componentType"]]
    assert np.array_equal(rows(stable, binary, primitive["indices"], index_kind, 1),
                          rows(precise, precise_binary, precise_primitive["indices"], index_kind, 1))
    position_index = primitive["attributes"]["POSITION"]
    base_xyz = rows(stable, binary, position_index, "<f4", 3)
    edit_xyz = rows(precise, precise_binary, precise_primitive["attributes"]["POSITION"], "<f4", 3)
    changed = np.flatnonzero(np.linalg.norm(edit_xyz - base_xyz, axis=1) > .0001)
    assert len(changed) == 2
    base_xyz[changed] = edit_xyz[changed]
    stable["accessors"][position_index].update(min=base_xyz.min(axis=0).tolist(),
                                               max=base_xyz.max(axis=0).tolist())
    encoded = json.dumps(stable, separators=(",", ":"), ensure_ascii=True).encode()
    encoded += b" " * (-len(encoded) % 4)
    GLB.write_bytes(struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(binary))
                    + struct.pack("<I4s", len(encoded), b"JSON") + encoded
                    + struct.pack("<I4s", len(binary), b"BIN\x00") + binary)

    # Reopen the stable asset in Blender so the editable deliverable matches it.
    scene, arm, body, garment = setup(GLB)
    set_pose(scene, arm, "rest", 1)
    garment.name = garment.data.name = "Jeans"
    for obj in list(scene.objects):
        if obj not in (arm, body, garment):
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    body.hide_render = True
    body.hide_set(True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    history = json.loads((HERE / "fit_history.json").read_text())
    history["stable_export"] = {"preserved_glb_sha256": sha256(stable_path),
                               "replaced_position_indices": changed.tolist()}
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
    elif "--patches" in sys.argv:
        shape_patches()
    elif "--stable-export" in sys.argv:
        first = sys.argv.index("--stable-export") + 1
        stable, repaired = map(Path, sys.argv[first:first + 2])
        preserve_stable_export(stable, repaired)
    elif "--stabilize-floor" in sys.argv:
        stabilize_export_floor(minimum_step=.0014 if "--wider-step" in sys.argv else .0004,
                               use_actual="--analytic" not in sys.argv)
    elif "--exact-legacy" in sys.argv:
        fix_reimported_legacy()
    elif "--split-fit" in sys.argv:
        refine_split_contacts()
    elif "--preserve-legacy" in sys.argv:
        preserve_legacy()
    elif "--local" in sys.argv or "--strict-local" in sys.argv:
        local_refit(strict_legacy="--strict-local" in sys.argv)
    else:
        fit()
