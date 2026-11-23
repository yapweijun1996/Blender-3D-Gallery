"""Refine the round-2 Studio jeans in Blender 5.1 against the corrected clips."""

import hashlib
import json
import math
from pathlib import Path
import runpy
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROUND2 = HERE.parent / "round2"
PARTS = HERE.parents[2]
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS / "body-fix/motion_fixed.glb"
BASE = ROUND2 / "jeans_v2.glb"
GLB = HERE / "jeans_v3.glb"
BLEND = HERE / "jeans_v3.blend"
R2 = runpy.run_path(str(ROUND2 / "fit_jeans_r2.py"))
PRIOR = R2["PRIOR"]
CLIPS = R2["CLIPS"]
MARGIN = .002
MINIMUM = .0005
CAP = .030
BAKE_STAGES = (1, 5, 6, 8, 9, 11, 13, 16)
TRIANGLE_LIMIT = 8000

mesh_arrays = PRIOR["mesh_arrays"]
evaluated_arrays = PRIOR["evaluated_arrays"]
nearest = PRIOR["nearest"]
tree_from = PRIOR["tree_from"]
skin_matrices = PRIOR["pose_matrices"]
skin_positions = PRIOR["skin_positions"]
read_weights = PRIOR["read_weights"]
limit_weights = PRIOR["limit_weights"]
set_pose = PRIOR["set_pose"]
zone = PRIOR["zone"]


def write_json(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frames():
    yield "rest", 1.0
    for clip in CLIPS:
        first, last = map(float, bpy.data.actions[clip].frame_range)
        times = {first, last}
        times.update(i / 2 for i in range(math.ceil(2 * first), math.floor(2 * last) + 1))
        yield from ((clip, frame) for frame in sorted(times))


def setup(path, editable=False):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    body.hide_set(False)
    garment = PRIOR["import_garment"](path, merge=editable)
    garment.modifiers.clear()
    garment.modifiers.new("Master Skin", "ARMATURE").object = arm
    garment.parent = arm
    existing = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    clip_rig, = [obj for obj in scene.objects if obj not in existing and obj.type == "ARMATURE"]
    assert set(clip_rig.data.bones.keys()) == set(arm.data.bones.keys())
    for obj in scene.objects:
        if obj not in (arm, body, garment):
            obj.hide_viewport = obj.hide_render = True
    assert len(arm.data.bones) == 65
    assert all(bpy.data.actions.get(name) and bpy.data.actions[name].slots for name in CLIPS)
    arm.animation_data_create()
    set_pose(scene, arm, "rest", 1)
    return scene, arm, body, garment


def cache_motion(scene, arm, body):
    modes = tuple(bone.rotation_mode for bone in arm.pose.bones)
    bind = [bone.bone.matrix_local.inverted() for bone in arm.pose.bones]
    samples, transforms = [], []
    for clip, frame in frames():
        set_pose(scene, arm, clip, frame)
        coords, triangles = evaluated_arrays(body, bpy.context.evaluated_depsgraph_get())
        samples.append((clip, frame, tree_from(coords, triangles), coords, triangles))
        transforms.append(np.asarray([bone.matrix @ inv for bone, inv in zip(arm.pose.bones, bind)])[:, :3])
    assert modes == tuple(bone.rotation_mode for bone in arm.pose.bones)
    assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
    return samples, np.asarray(transforms, dtype=np.float32)


def summarize(distances, overlaps, samples):
    result = {}
    for clip in ("rest", *CLIPS):
        rows = [i for i, sample in enumerate(samples) if sample[0] == clip]
        d = distances[rows]
        frame, vertex = np.unravel_index(d.argmin(), d.shape)
        pairs = overlaps[rows]
        result[clip] = {
            "poses": len(rows),
            "max_vertices_inside": int((d < 0).sum(axis=1).max()),
            "minimum_m": float(d.min()),
            "minimum_frame": samples[rows[frame]][1],
            "minimum_vertex": int(vertex),
            "max_garment_pairs": int(pairs.max()),
            "max_pair_frame": samples[rows[int(pairs.argmax())]][1],
            "total_garment_pairs": int(pairs.sum()),
        }
    return result


def scan(positions, triangles, samples, constraints=True):
    if constraints:
        return R2["scan"](positions, triangles, samples, margin=MARGIN, details=True)
    distances = np.empty(positions.shape[:2], dtype=np.float32)
    pairs = np.empty(len(samples), dtype=np.int32)
    for i, (_, _, body, _, _) in enumerate(samples):
        distances[i] = nearest(body, positions[i])[0]
        pairs[i] = len(body.overlap(tree_from(positions[i], triangles)))
    return distances, pairs


def print_summary(label, distances, overlaps, samples):
    result = summarize(distances, overlaps, samples)
    print(label, json.dumps(result), flush=True)
    return result


def export(arm, body, garment, points, weights, names):
    scene = bpy.context.scene
    set_pose(scene, arm, "rest", 1)
    PRIOR["set_vertices"](garment.data, points)
    PRIOR["write_weights"](garment, names, weights)
    garment.name = garment.data.name = "Jeans"
    for obj in list(scene.objects):
        if obj not in (arm, body, garment):
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    export_glb = PRIOR["export_glb"]
    export_glb.__globals__["GLB"] = GLB
    export_glb(arm, garment)
    body.hide_render = True
    body.hide_set(True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def baseline():
    scene, arm, body, garment = setup(BASE)
    samples, transforms = cache_motion(scene, arm, body)
    points, triangles = mesh_arrays(garment.data)
    names = [bone.name for bone in arm.pose.bones]
    weights = read_weights(garment, names)
    skin = skin_matrices(transforms, weights)
    positions = skin_positions(points, skin)
    set_pose(scene, arm, "run", 9.5)
    row = next(i for i, s in enumerate(samples) if s[:2] == ("run", 9.5))
    evaluated, _ = evaluated_arrays(garment, bpy.context.evaluated_depsgraph_get())
    assert np.max(np.abs(positions[row] - evaluated)) < .000005
    distances, overlaps, hits, constraints = scan(positions, triangles, samples)
    result = print_summary("ROUND2", distances, overlaps, samples)
    body_names = np.asarray(names)
    _, body_faces = mesh_arrays(body.data)
    body_zones = body_names[read_weights(body, names)[body_faces].sum(axis=1).argmax(axis=1)]
    for clip, info in result.items():
        row = next(i for i, s in enumerate(samples) if s[:2] == (clip, info["minimum_frame"]))
        vertex = info["minimum_vertex"]
        nearest_face = samples[row][2].find_nearest(positions[row, vertex])[2]
        info.update(zone=zone(points[vertex]), point=points[vertex].tolist(), body=body_zones[nearest_face])
    summary = {}
    for i, sample in enumerate(samples):
        active = np.flatnonzero(distances[i] < 0)
        if not len(active) and not overlaps[i]:
            continue
        clip, frame, tree, _, _ = sample
        pairs = tree.overlap(tree_from(positions[i], triangles))
        for body_id, face_id in pairs:
            key = clip, zone(points[triangles[face_id]].mean(axis=0)), str(body_zones[body_id])
            summary[key] = summary.get(key, 0) + 1
    print("BASELINE ZONES", result, sorted(summary.items(), key=lambda pair: -pair[1])[:35], flush=True)
    print("BASELINE EDGES", int(np.max(hits)), int(np.count_nonzero(hits)), len(points), len(triangles),
          flush=True)


def passes(distances, overlaps):
    return distances.min() >= MINIMUM and distances[0].max() <= CAP and not overlaps.any()


def score(distances, overlaps):
    hard = int(distances[0].min() < MINIMUM or distances[0].max() > CAP or overlaps[0] > 0)
    deficit = np.maximum(0, MINIMUM - distances)
    return (hard, int(overlaps.sum() + 3 * (distances < 0).sum()),
            int(np.count_nonzero(deficit)), float(deficit.sum()))


def blended_pressure(points, weights, constraints, skin, transforms, body, names, graph, rest):
    """Translate the worst posed contact back into the editable rest mesh."""
    columns = R2["skin_columns"](weights, names, points)
    pressure = np.zeros(len(points), dtype=np.float32)
    directional = np.zeros_like(points)
    for row, ids, normals, values, factors in constraints:
        gradients = np.einsum("ni,nij->nj", normals, skin[row, ids, :, :3])
        strength = (MARGIN - values) * factors
        np.maximum.at(pressure, ids, strength)
        keep = strength >= pressure[ids]
        directional[ids[keep]] = gradients[keep] / np.square(gradients[keep]).sum(axis=1).clip(.15)[:, None]
    rest_distance, _, outward, _ = nearest(rest, points)
    changed = np.clip((pressure - .001) / .003, 0, 1)
    average = PRIOR["average"]
    for _ in range(5):
        changed = np.maximum(changed, .85 * average(changed, graph))
    field = pressure[:, None] * directional
    for _ in range(4):
        field += .39 * (average(field, graph) - field)
    direction = directional / np.linalg.norm(directional, axis=1).clip(1e-8)[:, None]
    component = np.multiply(field, direction).sum(axis=1)
    field += np.maximum(0, pressure * np.linalg.norm(directional, axis=1) - component)[:, None] * direction
    offset = np.minimum(.011 * changed, np.maximum(0, CAP - .0003 - rest_distance))
    anatomy = limit_weights(R2["body_weights"](points, body, names, rest))
    for _ in range(2):
        anatomy = limit_weights(.78 * anatomy + .22 * average(anatomy, graph))
    return field, offset[:, None] * outward, anatomy, changed[:, None]


def patch_search(points, weights, triangles, region, samples, transforms, focus, axes,
                 alternatives, rest):
    """Score smooth patch moves using the actual posed triangles."""
    covered = np.isin(triangles, np.flatnonzero(region > .0005)).any(axis=1)
    vertices = np.unique(triangles[covered])
    faces = np.searchsorted(vertices, triangles[covered])
    influence = region[vertices, None]
    poses = [samples[i] for i in focus]
    patch_transforms = transforms[focus]
    patch_points, patch_weights = points[vertices], weights[vertices]
    skin = skin_matrices(patch_transforms, patch_weights)
    baseline = scan(skin_positions(patch_points, skin), faces, poses, constraints=False)

    def quality(distances, pairs):
        gate = score(distances, pairs)
        penalty = pairs.sum() + 2 * (distances < 0).sum() + 65 * np.maximum(0, MINIMUM - distances).sum()
        return (gate[0], float(penalty), gate[2], gate[3])

    best = quality(*baseline), (np.zeros(3), 0, 0.), patch_points, patch_weights
    phase = ((axis, k, alpha) for axis in axes
             for k, alpha in ((0, 0.), *((i, .55) for i in range(len(alternatives))))
             if np.any(axis) or alpha)
    for axis, k, alpha in phase:
        p = patch_points + influence * np.asarray(axis, dtype=np.float32)
        d, _, n, _ = nearest(rest, p)
        p += (.001 * np.maximum(0, 1 - d * 1000) - np.maximum(0, d - .0298))[:, None] * n
        w = (limit_weights(patch_weights + alpha * influence * (alternatives[k][vertices] - patch_weights))
             if alpha else patch_weights)
        candidate_skin = skin_matrices(patch_transforms, w) if alpha else skin
        distance, pairs = scan(skin_positions(p, candidate_skin), faces, poses, constraints=False)
        value = quality(distance, pairs)
        if value < best[0]:
            best = value, (np.asarray(axis), k, alpha), p, w
    trial_points, trial_weights = points.copy(), weights.copy()
    trial_points[vertices], trial_weights[vertices] = best[2:]
    print("PATCH", "vertices", len(vertices), "samples", len(focus), "initial", quality(*baseline),
          "best", best[:2], flush=True)
    return trial_points, trial_weights


def tune_patches(checkpoint=GLB, waist_only=False):
    scene, arm, body, garment = setup(checkpoint, editable=True)
    points, triangles = mesh_arrays(garment.data)
    names = [bone.name for bone in arm.pose.bones]
    weights = read_weights(garment, names)
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    original = points.copy()
    x, y, z = points.T
    smoothstep = PRIOR["smoothstep"]
    waist = smoothstep(.024, .057, y) * np.exp(-(x / .043) ** 2) * smoothstep(.35, .419, z)
    knee = smoothstep(.018, .053, y) * np.exp(-((x + .076) / .030) ** 2 - ((z - .219) / .044) ** 2)
    distances, pairs = scan(skin_positions(points, skin_matrices(transforms, weights)), triangles,
                            samples, constraints=False)
    initial = score(distances, pairs)
    best = initial
    anatomy = limit_weights(R2["body_weights"](points, body, names, rest))
    hips = np.zeros_like(weights)
    hips[:, names.index("mixamorig:Hips")] = 1
    shins = np.zeros_like(weights)
    shins[:, names.index("mixamorig:RightLeg")] = 1
    thighs = np.zeros_like(weights)
    thighs[:, names.index("mixamorig:RightUpLeg")] = 1
    moves = (
        (waist, ((0, 0, 0), (0, .010, .003), (0, .016, 0), (0, .022, 0),
                 (0, .018, -.007), (0, .023, -.013), (0, .017, .007), (.006, .014, 0),
                 (-.006, .014, 0), (0, -.003, -.009), (0, .004, -.020), (0, .010, -.020)),
         (hips, anatomy)),
        (knee, ((0, 0, 0), (0, .004, 0), (0, .010, 0), (0, .016, 0), (0, .025, 0),
                (.005, .010, 0), (-.005, .010, 0), (.010, .006, 0), (-.010, .006, 0),
                (0, -.007, 0), (0, .010, .006), (0, .010, -.006)), (anatomy, shins, thighs)),
    )
    if waist_only:
        waist = ((1 - smoothstep(.024, .068, abs(x)))
                 * smoothstep(.035, .055, y) * smoothstep(.370, .413, z))
        axes = [(0, u / 1000, v / 1000) for u in (0, 3, 5, 7, 9, 11, 14, 17)
                for v in (-12, -9, -7, -5, -3, 0, 5, 8)]
        moves = ((waist, axes, ()),)
    for region, axes, alternatives in moves:
        focus = np.unique(np.r_[0, np.flatnonzero((pairs > 0) | (distances.min(axis=1) < MINIMUM)),
                                np.arange(1, len(samples), 17)])
        p, w = patch_search(points, weights, triangles, region, samples, transforms, focus, axes, alternatives, rest)
        p = R2["rest_guard"](points, p, triangles, rest)
        d, ov = scan(skin_positions(p, skin_matrices(transforms, w)), triangles, samples, constraints=False)
        print_summary("PATCH CHECK", d, ov, samples)
        if score(d, ov) < best:
            points, weights, distances, pairs, best = p, w, d, ov, score(d, ov)
    if best < initial:
        print("PATCH MOVEMENT", np.linalg.norm(points - original, axis=1).max(), flush=True)
        export(arm, body, garment, points, weights, names)
        history = json.loads((HERE / "fit_history.json").read_text())
        history.setdefault("local_patch_scores", []).append({"before": initial, "after": best})
        write_json("fit_history.json", history)


def refine_contacts(checkpoint=GLB, strict_floor=False):
    """Fit remaining vertices against measured local triangle and vertex clearance."""
    scene, arm, body, garment = setup(checkpoint, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    points, triangles = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    skin = skin_matrices(transforms, weights)
    positions = skin_positions(points, skin)
    distances, pairs, hits, constraints = scan(positions, triangles, samples)
    original_score = score(distances, pairs)
    prior = R2["HOODIE"]["PRIOR"]
    shape = prior["RestShape"](garment.data, points, rest)
    directions = prior["scaled_directions"](24).astype(np.float32)
    directions = np.vstack((directions, np.eye(3), -np.eye(3)))
    columns = R2["skin_columns"](weights, names, points)
    anatomy = limit_weights(R2["body_weights"](points, body, names, rest))
    pressure = blended_pressure(points, weights, constraints, skin, transforms, body, names,
                                PRIOR["adjacency"](garment.data), rest)[0]
    priority = np.zeros(len(points))
    for face, count in zip(triangles, hits):
        priority[face] += count
    priority += 4 * (distances < MINIMUM).sum(axis=0)
    active = np.flatnonzero(priority)
    active = active[np.argsort(-priority[active], kind="stable")]
    relevant = np.flatnonzero((pairs > 0) | (distances.min(axis=1) < MINIMUM))
    rows = np.unique(np.r_[0, relevant, np.arange(1, len(samples), 17)])
    plane_trees = [samples[i][2] for i in rows]
    accepted = 0
    for vertex in active:
        triangle_ids = shape.incidence[vertex]
        if not len(triangle_ids):
            continue
        neighbor_ids, inverse = np.unique(triangles[triangle_ids], return_inverse=True)
        patch = inverse.reshape(-1, 3)
        center_index = int(np.searchsorted(neighbor_ids, vertex))
        patch_positions = positions[rows[:, None], neighbor_ids[None, :]]
        current = points[vertex].copy()
        current_w = weights[vertex].copy()
        _, _, normal, _ = nearest(rest, current[None])
        choices = np.vstack((current, current + pressure[vertex] * np.array([.5, 1., 1.5])[:, None],
                            current + (.0018 * directions), current + (.0045 * directions),
                            current + (.0090 * directions[::2]), current + (.012 * normal),
                            current + (.016 * directions[-6:])))
        choices = choices.astype(np.float32)
        rest_d = nearest(rest, choices)[0]
        valid = (rest_d >= .0008) & (rest_d <= CAP - .00005)
        valid[0] = True
        choices = choices[valid]
        j = np.unique(np.r_[columns[vertex], np.flatnonzero(current_w), np.flatnonzero(anatomy[vertex])])
        weight_proposals = [current_w, limit_weights((.5 * current_w + .5 * anatomy[vertex])[None])[0],
                            limit_weights((.25 * current_w + .75 * anatomy[vertex])[None])[0]]
        for joint in j:
            basis = np.zeros_like(current_w)
            basis[joint] = 1.
            for mix in (.12, .35, .65):
                weight_proposals.append(limit_weights((current_w * (1 - mix) + basis * mix)[None])[0])
        # Coordinate moves are sampled most densely at the existing weights.
        # Weight choices also accompany each small direct-axis move.
        selected = np.r_[0, np.argsort(np.linalg.norm(choices - current, axis=1), kind="stable")[1:9]]
        candidate_p = np.vstack((choices, np.tile(choices[selected], (len(weight_proposals) - 1, 1))))
        candidate_w = np.vstack((np.repeat(current_w[None], len(choices), axis=0),
                                 np.repeat(np.asarray(weight_proposals[1:]), len(selected), axis=0)))
        skin_rows = skin_matrices(transforms[rows], candidate_w)
        posed = np.einsum("rcij,cj->rci", skin_rows[..., :3], candidate_p) + skin_rows[..., 3]

        # Sample neighboring triangle interiors to shortlist moves. The
        # selected candidates then face an exact BVH intersection test.
        starting = patch_positions[:, patch]
        bary = np.asarray(((1 / 3, 1 / 3, 1 / 3), (.5, .5, 0), (.5, 0, .5), (0, .5, .5)))
        base_witness = np.einsum("kc,rfcj->rfkj", bary, starting).reshape(len(rows), -1, 3)
        coefficients = np.einsum("kc,fc->fk", bary, patch == center_index).ravel()
        use = coefficients > 0
        gaps = np.array([nearest(tree, p)[0] for tree, p in zip(plane_trees, posed)])
        witness = base_witness[:, use]
        coeff = coefficients[use]
        near = []
        for i, tree in enumerate(plane_trees):
            local_gap = nearest(tree, witness[i])[0]
            for k in np.flatnonzero(local_gap < .0026):
                near.append((i, k, local_gap[k]))
        near.sort(key=lambda contact: contact[2])
        sample_indices = np.unique(np.r_[np.arange(min(25, len(near))),
                                         np.linspace(0, max(0, len(near) - 1), min(17, len(near)), dtype=int)])
        witness_cost = np.zeros(len(candidate_p))
        for i, k, old in (near[n] for n in sample_indices):
            moved = witness[i, k] + coeff[k] * (posed[i] - patch_positions[i, center_index])
            deficit = np.maximum(0, .0015 - nearest(plane_trees[i], moved)[0]) * 1000
            witness_cost += .015 * np.square(deficit) + .09 * (deficit > 1.5)
        deficit = np.maximum(0, .00075 - gaps) * 1000
        motion_cost = .06 * np.linalg.norm((candidate_p - current) * 1000, axis=1)
        motion_cost += .22 * np.abs(candidate_w - current_w).sum(axis=1)
        approximately = ((gaps < MINIMUM).sum(axis=0) * 2 + np.square(deficit).mean(axis=0)
                         + .3 * deficit.max(axis=0) + witness_cost + motion_cost)
        shortlist = np.unique(np.r_[0, np.argsort(approximately, kind="stable")[:16]])
        exact_rows = np.unique(np.r_[0, np.searchsorted(rows, relevant),
                                     np.argsort(gaps[:, 0], kind="stable")[:15]])
        best = None
        for i in shortlist:
            if not shape.accepts(vertex, candidate_p[i], points):
                continue
            count = 0
            for r in exact_rows:
                candidate = patch_positions[r].copy()
                candidate[center_index] = posed[r, i]
                count += len(plane_trees[r].overlap(tree_from(candidate, patch)))
            negative = int((gaps[:, i] < 0).sum())
            hard = int(gaps[0, i] < MINIMUM or gaps[0, i] > CAP)
            if strict_floor:
                hard = max(hard, int(gaps[:, i].min() < MINIMUM))
            value = (hard, count + 2 * negative, int((gaps[:, i] < MINIMUM).sum()),
                     float(approximately[i]))
            if best is None or value < best[0]:
                best = value, i
        if best and best[1]:
            i = best[1]
            points[vertex] = candidate_p[i]
            weights[vertex] = candidate_w[i]
            whole_skin = skin_matrices(transforms, weights[vertex:vertex + 1])[:, 0]
            positions[:, vertex] = whole_skin[:, :, :3] @ points[vertex] + whole_skin[:, :, 3]
            accepted += 1
    distances, pairs = scan(positions, triangles, samples, constraints=False)
    final_score = score(distances, pairs)
    print("LOCAL", accepted, len(active), original_score, final_score, flush=True)
    print_summary("LOCAL CHECK", distances, pairs, samples)
    if final_score < original_score and (not strict_floor or distances.min() >= MINIMUM):
        export(arm, body, garment, points, weights, names)
        history = json.loads((HERE / "fit_history.json").read_text())
        history.setdefault("local_contact_passes", []).append({"before": original_score, "after": final_score,
                                                               "changed_vertices": accepted})
        write_json("fit_history.json", history)


def clear_waist_skin(checkpoint=GLB):
    """Resolve the discrete nearest-face changes at the back waistband."""
    scene, arm, body, garment = setup(checkpoint, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    points, triangles = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    samples, transforms = cache_motion(scene, arm, body)
    posed = skin_positions(points, skin_matrices(transforms, weights))
    distances, overlaps = scan(posed, triangles, samples, constraints=False)
    initial = score(distances, overlaps)
    incidence = R2["HOODIE"]["PRIOR"]["RestShape"](garment.data, points, samples[0][2]).incidence
    band_bones = [names.index("mixamorig:" + label)
                 for label in ("Hips", "Spine", "LeftUpLeg", "RightUpLeg", "Spine1")]
    steps = 6
    parts = [[a, b, c, d, steps - a - b - c - d]
             for a in range(steps + 1) for b in range(steps + 1 - a)
             for c in range(steps + 1 - a - b) for d in range(steps + 1 - a - b - c)]
    pool = np.zeros((len(parts), len(names)), dtype=np.float32)
    pool[:, band_bones] = np.asarray(parts, dtype=np.float32) / steps
    pool = limit_weights(pool)
    candidates = np.flatnonzero((distances.min(axis=0) < MINIMUM) & (points[:, 2] > .395))
    candidates = candidates[np.argsort(distances[:, candidates].min(axis=0), kind="stable")]
    focus = (np.arange(len(samples)) if len(candidates) <= 4 else np.unique(np.r_[
        0, [i for i, row in enumerate(samples) if row[0] in ("walk", "run")],
        np.arange(1, len(samples), 11)]))
    used = 0
    for v in candidates:
        current = weights[v].copy()
        nearby = limit_weights(.65 * current + .35 * pool)
        choices = np.vstack((current, pool, nearby))
        matrix = skin_matrices(transforms[focus], choices)
        trial = matrix[..., :3] @ points[v] + matrix[..., 3]
        signed = np.asarray([nearest(samples[row][2], row_positions)[0]
                             for row, row_positions in zip(focus, trial)])
        edits = np.abs(choices - current).sum(axis=1)
        target = .0015 if len(candidates) <= 4 else .0007
        required = np.maximum(0, target - signed)
        quality = (100 * (signed < MINIMUM).sum(axis=0) + np.square(required * 1000).sum(axis=0)
                   + 4 * edits)
        ordering = np.argsort(quality, kind="stable")
        if len(candidates) <= 4:
            # A seam edge can be nearest to two strongly opposed normals.
            # Test the finalists with tiny perturbations to keep a stable
            # sign after the Blender-to-GLB float32 round trip.
            short = ordering[:40]
            for i, tree in enumerate(samples[row][2] for row in focus):
                p = trial[i, short]
                for axis in (0, 1, 2):
                    jitter = np.eye(3, dtype=np.float32)[axis] * .00002
                    for move in (-jitter, jitter):
                        gap = nearest(tree, p + move)[0]
                        quality[short] += 10 * (gap < MINIMUM) + np.maximum(0, .0012 - gap) * 1000
            ordering = short[np.argsort(quality[short], kind="stable")]
        local_ids, inverse = np.unique(triangles[incidence[v]], return_inverse=True)
        local_faces = inverse.reshape(-1, 3)
        j = int(np.searchsorted(local_ids, v))
        original = posed[focus[:, None], local_ids]
        local_trees = [samples[row][2] for row in focus]
        for option in ordering[:17]:
            if option == 0:
                break
            cuts = 0
            for i, tree in enumerate(local_trees):
                patch = original[i].copy()
                patch[j] = trial[i, option]
                cuts += len(tree.overlap(tree_from(patch, local_faces)))
                if cuts:
                    break
            if cuts:
                continue
            weights[v] = choices[option]
            s = skin_matrices(transforms, weights[v:v + 1])[:, 0]
            posed[:, v] = s[..., :3] @ points[v] + s[..., 3]
            used += 1
            break
    distances, overlaps = scan(posed, triangles, samples, constraints=False)
    final = score(distances, overlaps)
    print("WAIST SKIN", used, len(candidates), initial, final, flush=True)
    print_summary("WAIST SKIN CHECK", distances, overlaps, samples)
    if final < initial:
        export(arm, body, garment, points, weights, names)
        history = json.loads((HERE / "fit_history.json").read_text())
        history.setdefault("waist_skin", []).append({"before": initial, "after": final, "changed_vertices": used})
        write_json("fit_history.json", history)


def finish_knee_skin(checkpoint=GLB):
    """Use a full-motion local weight search for the final right-knee patch."""
    scene, arm, body, garment = setup(checkpoint, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    points, triangles = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    samples, transforms = cache_motion(scene, arm, body)
    positions = skin_positions(points, skin_matrices(transforms, weights))
    distances, pairs = scan(positions, triangles, samples, constraints=False)
    initial = score(distances, pairs)
    incidence = R2["HOODIE"]["PRIOR"]["RestShape"](garment.data, points, samples[0][2]).incidence
    run_rows = np.asarray([r for r, sample in enumerate(samples) if sample[0] == "run"])
    contacts = set(np.flatnonzero(distances[run_rows].min(axis=0) < .00085))
    for row in run_rows[pairs[run_rows] > 0]:
        for _, face in samples[row][2].overlap(tree_from(positions[row], triangles)):
            contacts.update(triangles[face])
    bones = [names.index("mixamorig:" + name)
             for name in ("RightUpLeg", "RightLeg", "RightFoot", "Hips")]
    done = []
    for v in sorted(contacts):
        current = weights[v].copy()
        if points[v, 0] > -.030 or not .15 < points[v, 2] < .28:
            continue
        adjustments = np.zeros((4, len(names)), dtype=np.float32)
        adjustments[np.arange(4), bones] = 1
        trial_weights = [current]
        for source in range(4):
            for target in range(4):
                if source == target:
                    continue
                for amount in (.008, .02, .042, .080, .142, .205):
                    step = min(amount, current[bones[source]])
                    if step > .0002:
                        trial_weights.append(current + step * (adjustments[target] - adjustments[source]))
        pool = limit_weights(np.asarray(trial_weights))
        matrix = skin_matrices(transforms, pool)
        trajectory = matrix[..., :3] @ points[v] + matrix[..., 3]
        clearance = np.asarray([nearest(sample[2], option)[0] for sample, option in zip(samples, trajectory)])
        local_ids, inverse = np.unique(triangles[incidence[v]], return_inverse=True)
        local_faces = inverse.reshape(-1, 3)
        index = int(np.searchsorted(local_ids, v))

        def overlap_count(choice, rows):
            total = 0
            for row in rows:
                patch = positions[row, local_ids].copy()
                patch[index] = trajectory[row, choice]
                total += len(samples[row][2].overlap(tree_from(patch, local_faces)))
            return total

        initial_cuts = overlap_count(0, run_rows)
        original = (int(clearance[:, 0].min() < MINIMUM), initial_cuts,
                    float(np.maximum(0, .0012 - clearance[:, 0]).sum()))
        best, selected = original, 0
        eligible = np.flatnonzero(clearance.min(axis=0) >= .0006)
        for option in eligible:
            if option == 0:
                continue
            count = overlap_count(option, run_rows)
            candidate = (0, count, float(np.maximum(0, .0012 - clearance[:, option]).sum()
                                         + .001 * np.abs(pool[option] - current).sum()))
            if candidate < best:
                best, selected = candidate, int(option)
        if selected:
            weights[v] = pool[selected]
            positions[:, v] = trajectory[:, selected]
            done.append((int(v), initial_cuts, best[1]))
    d, ov = scan(positions, triangles, samples, constraints=False)
    result = score(d, ov)
    print("FINAL KNEE SKIN", initial, result, done, flush=True)
    print_summary("FINAL KNEE CHECK", d, ov, samples)
    if result < initial and d.min() >= min(MINIMUM, distances.min()):
        export(arm, body, garment, points, weights, names)
        history = json.loads((HERE / "fit_history.json").read_text())
        history["knee_skin_finish"] = {"before": initial, "after": result, "local_vertices": done}
        write_json("fit_history.json", history)
        if d.min() < MINIMUM:
            clear_waist_skin()


def bend_knee_patch(checkpoint=GLB, posed_field=False, adaptive=False, band=None):
    """Fit a coherent rear-knee patch where individually clear corners still cross."""
    scene, arm, body, garment = setup(checkpoint, editable=True)
    points, triangles = mesh_arrays(garment.data)
    names = [bone.name for bone in arm.pose.bones]
    weights = read_weights(garment, names)
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    all_skin = skin_matrices(transforms, weights)
    posed = skin_positions(points, all_skin)
    distance, pairs = scan(posed, triangles, samples, constraints=False)
    if not pairs.any():
        return
    initial = score(distance, pairs)
    smoothstep = PRIOR["smoothstep"]
    x, y, z = points.T
    mask = ((1 - smoothstep(.016, .049, abs(x + .075)))
            * smoothstep(.020, .052, y) * (1 - smoothstep(.023, .076, abs(z - .219))))
    field_frames = np.flatnonzero(pairs)
    if adaptive:
        contacts = set()
        contact_rows = []
        body_rest, body_indices = mesh_arrays(body.data)
        body_centers = body_rest[body_indices].mean(axis=1)
        for row in np.flatnonzero(pairs):
            for master_triangle, triangle in samples[row][2].overlap(tree_from(posed[row], triangles)):
                if band == "lower" and body_centers[master_triangle, 2] >= .215:
                    continue
                if band == "upper" and body_centers[master_triangle, 2] < .215:
                    continue
                contacts.update(triangles[triangle])
                contact_rows.append(row)
        if not contacts:
            return
        field_frames = np.unique(contact_rows)
        affected = np.asarray(sorted(contacts))
        proximity = np.linalg.norm(points[:, None] - points[affected], axis=2).min(axis=1)
        mask = (1 - smoothstep(.002, .032 if band is None else .025, proximity)) * smoothstep(.018, .036, y)
    faces_mask = np.isin(triangles, np.flatnonzero(mask > 1e-4)).any(axis=1)
    ids = np.unique(triangles[faces_mask])
    faces = np.searchsorted(ids, triangles[faces_mask])
    influence = mask[ids, None]
    local_p, local_w = points[ids], weights[ids]
    knee_bones = [names.index("mixamorig:" + label) for label in ("RightUpLeg", "RightLeg", "RightFoot", "Hips")]
    relevant = np.unique(np.r_[0, np.flatnonzero(pairs), np.arange(1, len(samples), 17)])
    subset = [samples[i] for i in relevant]
    bone_transforms = transforms[relevant]
    rank = score(*scan(skin_positions(local_p, skin_matrices(bone_transforms, local_w)),
                       faces, subset, constraints=False))
    current_p, current_w = local_p, local_w
    chosen = []
    finalists = []
    stages = (1,) if posed_field else (0, 1)
    for stage in stages:
        alternatives = [(np.zeros(3), None)]
        if stage == 0:
            for center in (.177, .191, .206, .219, .234, .249, .262):
                for width in (.009, .023, .045):
                    for bias in (0, .12):
                        calf = smoothstep(center - width, center + width, -z[ids] + 2 * center)
                        target = np.zeros_like(local_w)
                        target[:, knee_bones[0]] = (1 - calf) * (1 - bias)
                        target[:, knee_bones[1]] = calf * (1 - bias)
                        target[:, knee_bones[2]] = bias * calf
                        target[:, knee_bones[3]] = bias * (1 - calf)
                        alternatives.append((np.zeros(3), target))
        else:
            if posed_field:
                axes = [(u, v, w) for u in (-.006, 0., .006)
                        for v in (-.010, -.006, -.003, 0., .003, .006, .010)
                        for w in (-.008, -.004, 0., .004, .008)]
                if adaptive:
                    axes = [(u, v, w) for u in (-.004, -.002, 0., .002, .004)
                            for v in (-.004, -.002, 0., .002, .004)
                            for w in (-.004, -.002, 0., .002, .004)]
                most = field_frames[np.argsort(-pairs[field_frames], kind="stable")[:5]]
                linear = skin_matrices(transforms[most], local_w)[..., :3]
                lhs = np.einsum("rvki,rvkj->vij", linear, linear) + .13 * np.eye(3)[None]
                rhs = linear.transpose(0, 1, 3, 2).sum(axis=0)
                inverse_skin = np.linalg.solve(lhs, rhs)
            else:
                axes = [(u, v, w) for u in (-.012, -.006, 0., .006, .012)
                        for v in (-.010, -.004, 0., .006, .013, .020)
                        for w in (0., -.009, .009)]
            alternatives.extend((np.asarray(axis), None) for axis in sorted(axes, key=np.linalg.norm))
        winner = None
        for axis, target in alternatives:
            step = R2["limit_delta"](inverse_skin @ axis, .025) if posed_field else axis
            p = current_p + influence * step
            w = limit_weights((1 - influence) * local_w + influence * target) if target is not None else current_w
            clear, _, normal, _ = nearest(rest, p)
            p -= np.maximum(0, clear - .02975)[:, None] * normal
            s = skin_matrices(bone_transforms, w)
            d, ov = scan(skin_positions(p, s), faces, subset, constraints=False)
            candidate = score(d, ov)
            if posed_field and candidate[0] == 0:
                finalists.append((candidate, axis.tolist(), p, w))
            if candidate < rank:
                rank, winner = candidate, (p, w)
                chosen.append((stage, rank, axis.tolist()))
        if winner is not None:
            current_p, current_w = winner
        print("KNEE PATCH STAGE", stage, len(ids), rank, "selected", len(chosen), flush=True)
    p, w = points, weights
    d, ov, result = distance, pairs, initial
    candidates = (sorted(finalists, key=lambda entry: entry[0])[:6] if posed_field and adaptive else
                  [(rank, None, current_p, current_w)])
    for _, axis, pp, ww in candidates:
        proposal, skin_weights = points.copy(), weights.copy()
        proposal[ids], skin_weights[ids] = pp, ww
        guarded = R2["rest_guard"](points, proposal, triangles, rest)
        shape_options = (guarded, .7 * guarded + .3 * proposal) if adaptive else (guarded,)
        for p_test in shape_options:
            trial = skin_positions(p_test, skin_matrices(transforms[relevant], skin_weights))
            local_rank = score(*scan(trial, triangles, subset, constraints=False))
            if local_rank >= score(distance[relevant], pairs[relevant]):
                continue
            cd, cp = scan(skin_positions(p_test, skin_matrices(transforms, skin_weights)), triangles, samples,
                          constraints=False)
            if score(cd, cp) < result:
                p, w, d, ov, result = p_test, skin_weights, cd, cp, score(cd, cp)
                print("KNEE FIELD", axis, result, flush=True)
    print("KNEE PATCH", initial, result, chosen, flush=True)
    print_summary("KNEE PATCH CHECK", d, ov, samples)
    if result < initial:
        export(arm, body, garment, p, w, names)
        history = json.loads((HERE / "fit_history.json").read_text())
        history.setdefault("knee_bend_patch", []).append({"before": initial, "after": result, "proposals": chosen})
        write_json("fit_history.json", history)


def loft_contacts(checkpoint=GLB):
    """Add short edges at the rear knee so its skin can bend around the fold."""
    scene, arm, body, garment = setup(checkpoint, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    points, triangles = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    skin = skin_matrices(transforms, weights)
    distances, pairs, hits, constraints = scan(skin_positions(points, skin), triangles, samples)
    initial = score(distances, pairs)
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    marked = {edge for face in np.flatnonzero(hits) for edge in bm.faces[int(face)].edges
              if edge.calc_length() > .012}
    marked.update(edge for face in np.flatnonzero(hits) for edge in bm.faces[int(face)].edges
                  if edge.calc_length() > .007 and all(
                      -.12 < v.co.x < -.036 and .160 < v.co.z < .265 and v.co.y > .029 for v in edge.verts))
    selected = sorted(marked, key=lambda edge: edge.index)
    if not selected:
        bm.free()
        return
    bmesh.ops.subdivide_edges(bm, edges=selected, cuts=2, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[face for face in bm.faces if len(face.verts) != 3])
    bm.to_mesh(garment.data)
    bm.free()
    garment.data.update()
    points, triangles = mesh_arrays(garment.data)
    assert len(triangles) <= TRIANGLE_LIMIT
    weights = limit_weights(read_weights(garment, names))
    skin = skin_matrices(transforms, weights)
    distances, pairs, hits, constraints = scan(skin_positions(points, skin), triangles, samples)
    print_summary("LOFT START", distances, pairs, samples)
    start = points.copy()
    graph = PRIOR["adjacency"](garment.data)
    columns = R2["skin_columns"](weights, names, points)
    for fraction in (.75, 1.):
        p, w = R2["fit_step"](points, start, weights, columns, skin, transforms, constraints,
                              graph, rest, MARGIN, True)
        p = R2["rest_guard"](points, points + fraction * (p - points), triangles, rest)
        w = limit_weights(weights + fraction * (w - weights))
        s = skin_matrices(transforms, w)
        d, ov = scan(skin_positions(p, s), triangles, samples, constraints=False)
        if score(d, ov) < score(distances, pairs):
            points, weights, distances, pairs = p, w, d, ov
            break
    result = score(distances, pairs)
    print("LOFT", len(selected), len(triangles), initial, result, flush=True)
    print_summary("LOFT CHECK", distances, pairs, samples)
    if result < initial or ("--keep-loft" in sys.argv and result[0] == 0):
        export(arm, body, garment, points, weights, names)
        history = json.loads((HERE / "fit_history.json").read_text())
        history.setdefault("loft_search", []).append({"edges_split": len(selected),
                                                    "before": initial, "after": result})
        write_json("fit_history.json", history)


def fit():
    scene, arm, body, garment = setup(BASE, editable=True)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    points, triangles = mesh_arrays(garment.data)
    weights = read_weights(garment, names)
    skin = skin_matrices(transforms, weights)
    distances, overlaps, hits, constraints = scan(skin_positions(points, skin), triangles, samples)
    baseline_result = print_summary("START", distances, overlaps, samples)
    history = []
    best = score(distances, overlaps)
    # Retain the eight accepted bake stages from the 16-proposal sweep.
    for stage in BAKE_STAGES:
        iteration = stage - 1
        if passes(distances, overlaps):
            break
        # Densify only the crossing patches so that coarse faces can curve
        # around the shin, cuff, and inner thigh under skinning.
        cuts = 0
        if iteration in (0, 5, 10):
            PRIOR["set_vertices"](garment.data, points)
            PRIOR["write_weights"](garment, names, weights)
            backup = garment.data.copy()
            cuts = R2["split_edges"](garment, triangles, hits, local=iteration > 0)
            if cuts:
                candidate, faces = mesh_arrays(garment.data)
                candidate_weights = limit_weights(read_weights(garment, names))
                candidate_skin = skin_matrices(transforms, candidate_weights)
                candidate_d, candidate_pairs, candidate_hits, candidate_constraints = scan(
                    skin_positions(candidate, candidate_skin), faces, samples)
                if not score(candidate_d, candidate_pairs)[0]:
                    points, triangles, weights, skin = candidate, faces, candidate_weights, candidate_skin
                    distances, overlaps, hits, constraints = (
                        candidate_d, candidate_pairs, candidate_hits, candidate_constraints)
                    best = score(distances, overlaps)
                else:
                    garment.data = backup
                    cuts = 0
        if iteration == 0 or cuts:
            original = points.copy()
            graph = PRIOR["adjacency"](garment.data)
        columns = R2["skin_columns"](weights, names, points)

        active = (distances.min(axis=0) < .001) | np.isin(np.arange(len(points)), triangles[hits > 0])
        region = active.astype(np.float32)[:, None]
        for _ in range(3):
            region = np.maximum(region, .82 * PRIOR["average"](region, graph))
        use_weights = iteration >= 3 and iteration % 3 != 0
        if iteration in (8, 12, 15):
            candidate = R2["choose_local_moves"](points, skin, samples, distances, constraints, graph, 1)
            proposed_weights = weights
        else:
            candidate, proposed_weights = R2["fit_step"](
                points, original, weights, columns, skin, transforms, constraints, graph, rest, MARGIN, use_weights)
        candidate = points + region * (candidate - points)
        candidate = R2["rest_guard"](points, candidate, triangles, rest)
        proposed_weights = limit_weights(weights + region * (proposed_weights - weights))
        attempts = (1., .55) if use_weights else (1.,)
        for blend in attempts:
            p = points + blend * (candidate - points)
            w = limit_weights(weights + blend * (proposed_weights - weights))
            candidate_skin = skin_matrices(transforms, w) if use_weights else skin
            candidate_d, candidate_pairs, candidate_hits, candidate_constraints = scan(
                skin_positions(p, candidate_skin), triangles, samples)
            new_score = score(candidate_d, candidate_pairs)
            print("ITERATION", iteration + 1, "cuts", cuts, "scale", blend, "score", new_score,
                  "minimum_mm", float(candidate_d.min() * 1000), "peak_pairs", int(candidate_pairs.max()),
                  flush=True)
            if new_score < best or passes(candidate_d, candidate_pairs):
                points, weights, skin, best = p, w, candidate_skin, new_score
                distances, overlaps, hits, constraints = (
                    candidate_d, candidate_pairs, candidate_hits, candidate_constraints)
                break
        history.append({"iteration": iteration + 1, "edge_splits": cuts, "score": best,
                        "minimum_m": float(distances.min()), "pairs_total": int(overlaps.sum()),
                        "gate_pass": bool(passes(distances, overlaps))})
    print_summary("FIT", distances, overlaps, samples)
    assert len(triangles) <= TRIANGLE_LIMIT
    export(arm, body, garment, points, weights, names)
    write_json("fit_history.json", {"round2_glb_sha256": sha256(BASE), "baseline": baseline_result,
                                  "iterations": history, "motion_sha256": sha256(MOTION)})


def verify_export():
    scene, arm, body, garment = setup(GLB)
    inspect_export = PRIOR["inspect_export"]
    inspect_export.__globals__.update(GLB=GLB, BLEND=BLEND, MAX_TRIANGLES=TRIANGLE_LIMIT)
    details = inspect_export()

    def glb_content(path):
        data = path.read_bytes()
        size = struct.unpack_from("<I", data, 12)[0]
        return json.loads(data[20 : 20 + size]), data[28 + size :]

    def image_digests(document, binary):
        images = []
        for image in document["images"]:
            view = document["bufferViews"][image["bufferView"]]
            start = view.get("byteOffset", 0)
            images.append(hashlib.sha256(binary[start : start + view["byteLength"]]).hexdigest())
        return sorted(images)

    def uv_set(document, binary):
        values = set()
        for primitive in document["meshes"][0]["primitives"]:
            accessor = document["accessors"][primitive["attributes"]["TEXCOORD_0"]]
            view = document["bufferViews"][accessor["bufferView"]]
            offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
            coords = np.ndarray((accessor["count"], 2), dtype="<f4", buffer=binary,
                                offset=offset, strides=(view.get("byteStride", 8), 4))
            values.update(map(tuple, np.rint(coords * 10**6).astype(np.int32)))
        return values

    doc, binary = glb_content(GLB)
    source, source_binary = glb_content(BASE)
    details["image_sha256"] = image_digests(doc, binary)
    details["round2_image_bytes_equal"] = details["image_sha256"] == image_digests(source, source_binary)
    primitives = doc["meshes"][0]["primitives"]
    assert all("TEXCOORD_0" in p["attributes"] for p in primitives)
    uv_old, uv_new = uv_set(source, source_binary), uv_set(doc, binary)
    details["round2_uvs"] = len(uv_old)
    details["round2_uvs_found_after_export"] = len(uv_old & uv_new)
    details["added_interpolated_uvs"] = len(uv_new - uv_old)
    details["exported_vertices"] = sum(doc["accessors"][p["attributes"]["POSITION"]]["count"] for p in primitives)
    details["material_count"] = len(doc["materials"])
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
    arm, body, jeans = (bpy.context.scene.objects[name] for name in ("Armature", "Base_Body", "Jeans"))
    assert jeans.parent == arm and len(arm.data.bones) == 65 and body.hide_render
    assert len(jeans.modifiers) == 1 and jeans.modifiers[0].object == arm
    assert len(mesh_arrays(jeans.data)[1]) == details["triangles"]
    for material in jeans.data.materials:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                assert node.image.packed_file
    weights = read_weights(jeans, details["joints"])
    assert np.allclose(weights.sum(axis=1), 1, atol=1e-6) and (weights > 0).sum(axis=1).max() <= 4
    write_json("export_check.json", details)
    print("EXPORT", json.dumps({k: details[k] for k in details if k != "joints"}), flush=True)


def verify_body_baseline():
    scene, arm, body, _ = setup(GLB)
    body_dir = MOTION.parent
    module = runpy.run_path(str(body_dir / "bodycheck.py"))
    original = json.loads((body_dir / "body_selfcheck_after.json").read_text())
    grouping = json.loads((body_dir / "verification.json").read_text())["rest_topology"]
    assert original["master_sha256"] == sha256(MASTER) and original["motion_sha256"] == sha256(MOTION)
    checker = module["Checker"](body)
    baseline_rest = original["source_rest_pose"]
    measured_rest = checker.frame("rest")
    assert measured_rest["region_pairs"] == baseline_rest["region_pairs"]
    integer_reference = {clip: {row["frame"]: row["pairs"] for row in data["samples"]}
                         for clip, data in original["clips"].items()}
    result = {clip: {"integer_pairs": 0, "half_frame_pairs": 0, "peak_pairs": 0}
              for clip in CLIPS}
    for clip, frame in frames():
        if clip == "rest":
            continue
        set_pose(scene, arm, clip, frame)
        points = module["posed"](body)
        pairs, _ = checker.overlap(points)
        count = len(pairs)
        if frame in integer_reference[clip]:
            assert count == integer_reference[clip][frame], (clip, frame, count)
            result[clip]["integer_pairs"] += count
        else:
            result[clip]["half_frame_pairs"] += count
        result[clip]["peak_pairs"] = max(result[clip]["peak_pairs"], count)
    write_json("body_baseline_comparison.json", {
        "master_sha256": sha256(MASTER), "motion_sha256": sha256(MOTION),
        "neutral_pairs": measured_rest["pairs"], "neutral_region_pairs": grouping["pairs_in_neutral_pose"],
        "all_integer_counts_match_body_only_baseline": True, "body_only": result,
    })


def render():
    # Keep round 2's orthographic framing and lighting for a direct fit review.
    render_round2 = R2["render"]
    render_round2.__globals__.update(HERE=HERE, GLB=GLB)
    original_setup = PRIOR["setup"]
    reference = json.loads((HERE / "fit_history.json").read_text())["baseline"]
    tri_check = json.loads((HERE / "motion_check_tri.json").read_text())
    assert tri_check["garment_sha256"] == sha256(GLB)
    for clip, row in tri_check["results"].items():
        if row["max_garment_pairs"]:
            reference[clip]["max_garment_pairs"] = row["max_garment_pairs"]
            reference[clip]["max_pair_frame"] = row["peak_frame"]
    # The round-2 render reads a dense report to pick poses. Use the former
    # peak contact poses from the corrected-motion baseline for this comparison.
    frame_source = HERE / "dense_check.json"
    write_json(frame_source.name, {
        "results": {clip: {"max_triangle_pairs": row["max_garment_pairs"],
                           "worst_overlap_frame": row["max_pair_frame"],
                           "worst_vertex_frame": row["minimum_frame"]}
                    for clip, row in reference.items()},
    })
    try:
        PRIOR["setup"] = setup
        render_round2.__globals__["report"] = write_json
        render_round2()
    finally:
        PRIOR["setup"] = original_setup
        frame_source.unlink()


if __name__ == "__main__":
    if "--baseline" in sys.argv:
        baseline()
    elif "--verify-export" in sys.argv:
        verify_export()
    elif "--body-baseline" in sys.argv:
        verify_body_baseline()
    elif "--renders" in sys.argv:
        render()
    elif "--patches" in sys.argv:
        tune_patches(waist_only="--waist" in sys.argv)
    elif "--local" in sys.argv:
        refine_contacts(strict_floor="--strict-floor" in sys.argv)
    elif "--waist-skin" in sys.argv:
        clear_waist_skin()
    elif "--knee-skin" in sys.argv:
        finish_knee_skin()
    elif "--knee-patch" in sys.argv:
        band = "upper" if "--upper-knee" in sys.argv else "lower" if "--lower-knee" in sys.argv else None
        bend_knee_patch(posed_field="--posed-field" in sys.argv, adaptive="--adaptive-field" in sys.argv, band=band)
    elif "--loft" in sys.argv:
        loft_contacts()
    else:
        fit()
