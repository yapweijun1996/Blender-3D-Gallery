"""Refit the Studio jeans and check the exported skin in Blender 5.1.

Run this script in the round2 directory with the original master, motion,
and round 1 sources in their gallery locations. Modes: --verify, --checkers,
and --renders. The default mode fits and exports the editable and GLB assets.
"""

from pathlib import Path
from mathutils.bvhtree import BVHTree
import json
import math
import os
import runpy
import sys

import bmesh
import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
PRIOR = runpy.run_path(str(HERE.parent / "fit_jeans.py"))
HOODIE = runpy.run_path(str(HERE.parents[2] / "hoodie-fit-sol/round3/fit_hoodie_round3.py"))
BASE = HERE.parent / "jeans_v1.glb"
OUTPUT = Path(os.environ.get("JEANS_OUTPUT", HERE))
GLB = OUTPUT / "jeans_v2.glb"
BLEND = OUTPUT / "jeans_v2.blend"
CLIPS = PRIOR["CLIPS"]
MARGIN = .002
MINIMUM = .0005
CAP = .030
TRIANGLE_LIMIT = 8000
ITERATIONS = 12

mesh_arrays = PRIOR["mesh_arrays"]
nearest = PRIOR["nearest"]
tree_from = PRIOR["tree_from"]
average = PRIOR["average"]
adjacency = PRIOR["adjacency"]
smoothstep = PRIOR["smoothstep"]
limit_weights = PRIOR["limit_weights"]
skin_matrices = PRIOR["pose_matrices"]
skin_positions = PRIOR["skin_positions"]
set_vertices = PRIOR["set_vertices"]
write_weights = PRIOR["write_weights"]
pair_witnesses = HOODIE["pair_witnesses"]


def report(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2) + "\n")


def setup_editable(blend=BASE.with_suffix(".blend")):
    scene, arm, body, garment = PRIOR["setup"](blend.with_suffix(".glb"))
    with bpy.data.libraries.load(str(blend)) as (source, target):
        assert "Jeans" in source.objects
        target.objects = ["Jeans"]
    original, = target.objects
    garment.data = original.data
    assert [v.name for v in original.vertex_groups] == [v.name for v in garment.vertex_groups]
    bpy.data.objects.remove(original, do_unlink=True)
    return scene, arm, body, garment


def cache_motion(scene, arm, body):
    bones = tuple(arm.pose.bones)
    modes = tuple(bone.rotation_mode for bone in bones)
    inverse_bind = [bone.bone.matrix_local.inverted() for bone in bones]
    samples, transforms = [], []
    for clip, frame in PRIOR["frames"]():
        PRIOR["set_pose"](scene, arm, clip, frame)
        coords, faces = PRIOR["evaluated_arrays"](body, bpy.context.evaluated_depsgraph_get())
        transforms.append(np.asarray([bone.matrix @ matrix for bone, matrix in zip(bones, inverse_bind)])[:, :3])
        samples.append((clip, frame, tree_from(coords, faces), coords, faces))
    assert modes == tuple(bone.rotation_mode for bone in bones)
    return samples, np.asarray(transforms, dtype=np.float32)


def scan(posed, triangles, samples, margin=MARGIN, details=False):
    distances = np.empty(posed.shape[:2], dtype=np.float32)
    overlaps = np.zeros(len(samples), dtype=np.int32)
    hits = np.zeros(len(triangles), dtype=np.int32)
    constraints = []
    as_list = triangles.tolist()
    for row, (_, _, tree, body, body_faces) in enumerate(samples):
        points = posed[row]
        d, _, n, _ = nearest(tree, points)
        distances[row] = d
        garment = BVHTree.FromPolygons(points.tolist(), as_list, all_triangles=True)
        pairs = np.asarray(tree.overlap(garment), dtype=np.int32).reshape(-1, 2)
        overlaps[row] = len(pairs)
        active = np.flatnonzero(d < margin)
        indices, normals, values = [active], [n[active]], [d[active]]
        factors = [np.ones(len(active), dtype=np.float32)]
        if len(pairs):
            face_ids = pairs[:, 1]
            np.add.at(hits, face_ids, 1)
            faces, weights = pair_witnesses(points, triangles, body, body_faces, pairs[:, ::-1], dense=details)
            corners = triangles[faces]
            contact = np.einsum("ni,nij->nj", weights, points[corners])
            gaps, _, directions, _ = nearest(tree, contact)
            # Keep the deepest witness on each crossed face. Shared motion at
            # its corners shifts the actual intersection, including edge cuts.
            order = np.lexsort((gaps, faces))
            selected = order[np.r_[True, np.diff(faces[order]) != 0]]
            selected = selected[gaps[selected] < margin]
            for column in range(3):
                use = weights[selected, column] >= .08
                selection = selected[use]
                indices.append(corners[selection, column])
                normals.append(directions[selection])
                values.append(gaps[selection])
                factors.append(.65 + .35 * weights[selection, column])
        indices = np.concatenate(indices)
        if len(indices):
            constraints.append((row, indices, np.concatenate(normals), np.concatenate(values),
                                np.concatenate(factors)))
    return distances, overlaps, hits, constraints


def body_weights(points, body, names, tree):
    body_points, body_triangles = mesh_arrays(body.data)
    _, surface, _, faces = nearest(tree, points)
    corners = body_triangles[faces]
    bary = PRIOR["barycentric"](body_points[corners], surface)
    weights = PRIOR["read_weights"](body, names)
    return np.einsum("vi,vib->vb", bary, weights[corners])


def shape_seed(original, weights, body, names, tree, graph):
    d, _, normal, _ = nearest(tree, original)
    x, y, z = original.T
    hip_side = smoothstep(.044, .096, abs(x)) * smoothstep(.285, .358, z)
    front_hip = smoothstep(.035, .085, abs(x)) * smoothstep(.034, .072, -y) * smoothstep(.30, .39, z)
    contact_side = np.maximum(hip_side, .72 * front_hip)
    middle = 1 - smoothstep(.048, .087, abs(x))
    saddle = smoothstep(.250, .283, z) * (1 - smoothstep(.342, .373, z)) * middle
    knee = smoothstep(.145, .181, z) * (1 - smoothstep(.245, .280, z))
    room = .0060 * saddle + .0040 * knee
    movement = (np.minimum(d, .0024) - d) * contact_side + room
    delta = normal * movement[:, None]
    for _ in range(4):
        delta = .75 * delta + .25 * average(delta, graph)
    points = original + delta
    mapped = body_weights(points, body, names, tree)
    for _ in range(2):
        mapped += .12 * (average(mapped, graph) - mapped)
    return points, limit_weights(.45 * weights + .55 * mapped)


def split_edges(garment, triangles, hits, local=False):
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    bm.verts.index_update()
    frequency = {}
    coords, _ = mesh_arrays(garment.data)
    for face, count in zip(triangles, hits):
        if count:
            shifted = np.roll(face, 1)
            longest = np.square(coords[face] - coords[shifted]).sum(axis=1).argmax()
            key = tuple(sorted((face[longest], shifted[longest])))
            frequency[key] = frequency.get(key, 0) + int(count)
    options = []
    for edge in bm.edges:
        key = tuple(sorted(v.index for v in edge.verts))
        length = edge.calc_length()
        count = frequency.get(key, 0)
        center = (edge.verts[0].co + edge.verts[1].co) * .5
        loft = local and .27 <= center.z <= .379 and abs(center.x) < .075 and count >= 2
        if count and (length > .012 or (loft and length > .005)):
            options.append((-length * (1 + math.log1p(count)), key, edge))
    selected = []
    remaining = min(460, TRIANGLE_LIMIT - len(triangles))
    for _, _, edge in sorted(options):
        cost = len(edge.link_faces)
        if cost <= remaining:
            selected.append(edge)
            remaining -= cost
    if selected:
        bmesh.ops.subdivide_edges(bm, edges=selected, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[face for face in bm.faces if len(face.verts) != 3])
        bm.to_mesh(garment.data)
        garment.data.update()
    bm.free()
    assert len(garment.data.polygons) <= TRIANGLE_LIMIT
    return len(selected)


def skin_columns(weights, names, points):
    """Give each vertex a small, anatomically local set of movable influences."""
    def joint(name):
        return names.index("mixamorig:" + name)

    x, _, z = points.T
    hips, spine = joint("Hips"), joint("Spine")
    left_up, right_up = joint("LeftUpLeg"), joint("RightUpLeg")
    upper = np.where(x >= 0, left_up, right_up)
    opposite = np.where(x >= 0, right_up, left_up)
    knee = np.where(x >= 0, joint("LeftLeg"), joint("RightLeg"))
    foot = np.where(x >= 0, joint("LeftFoot"), joint("RightFoot"))
    toe = np.where(x >= 0, joint("LeftToeBase"), joint("RightToeBase"))
    base = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    for i in range(len(points)):
        if z[i] > .375:
            order = [hips, upper[i], spine, opposite[i]]
        elif z[i] > .294:
            order = [hips, upper[i], knee[i], opposite[i]]
        elif z[i] > .166:
            order = [upper[i], knee[i], hips, foot[i]]
        else:
            order = [upper[i], knee[i], foot[i], toe[i]]
        active = [int(j) for j in base[i] if weights[i,j] > .015]
        base[i] = list(dict.fromkeys(active + list(map(int, order))))[:4]
    return base


def simplex(values):
    sorted_values = np.sort(values, axis=1)[:, ::-1]
    partial = (np.cumsum(sorted_values, axis=1) - 1) / np.arange(1, values.shape[1] + 1)
    rho = (sorted_values > partial).sum(axis=1) - 1
    return np.maximum(0, values - partial[np.arange(len(values)), rho, None])


def limit_delta(delta, limit):
    return delta * np.minimum(1, limit / np.linalg.norm(delta, axis=1).clip(1e-9))[:, None]


def correct_rest(points, originals, tree, rest_floor):
    adjusted = points.copy()
    for _ in range(4):
        d, _, normal, _ = nearest(tree, adjusted)
        adjusted += (np.maximum(rest_floor - d, 0) - np.maximum(d - CAP + .00012, 0))[:, None] * normal
        adjusted = originals + limit_delta(adjusted - originals, CAP)
    return adjusted


def gather_planes(constraints, points, columns, skin, transforms, margin, weight_scale):
    """Keep peak deficits by direction across the complete pose sweep."""
    count = len(points)
    slots = 14
    gates = np.zeros((count * slots, 8), dtype=np.float32)
    rankings = np.zeros(count * slots, dtype=np.float32)
    for row, ids, world_normal, values, factors in constraints:
        rest_gradient = np.einsum("vi,vij->vj", world_normal, skin[row, ids, :, :3])
        joints = transforms[row, columns[ids]]
        endpoints = np.einsum("vcij,vj->vci", joints[..., :3], points[ids]) + joints[..., 3]
        derivatives = np.einsum("vi,vci->vc", world_normal, endpoints)
        derivatives -= derivatives.mean(axis=1, keepdims=True)
        normals = np.c_[rest_gradient, derivatives / weight_scale]
        strength = np.linalg.norm(normals, axis=1).clip(.15)
        deficit = (margin - values) * factors
        planes = np.c_[normals / strength[:, None], deficit / strength]
        maximum_axis = abs(rest_gradient).argmax(axis=1)
        direction = rest_gradient[np.arange(len(ids)), maximum_axis] >= 0
        # Separate torso, limbs, and strongly different bone responses so a
        # deeper contact cannot erase an opposing constraint.
        weight_axis = abs(derivatives).argmax(axis=1)
        weight_direction = derivatives[np.arange(len(ids)), weight_axis] >= 0
        group = np.where(abs(derivatives).max(axis=1) > .025, 6 + 2 * weight_axis + weight_direction,
                         2 * maximum_axis + direction)
        group = ids * slots + group
        better = deficit > rankings[group]
        np.maximum.at(rankings, group[better], deficit[better])
        chosen = better & (deficit >= rankings[group])
        gates[group[chosen]] = planes[chosen]
    return gates.reshape(count, slots, 8), rankings.reshape(count, slots)


def fit_step(points, original, weights, columns, skin, transforms, constraints, graph, tree,
             margin, use_weights):
    scale = .075 if use_weights else 1000.
    planes, importance = gather_planes(constraints, points, columns, skin, transforms, margin, scale)
    normals, targets = planes[..., :-1], planes[..., -1]
    raw_weights = np.take_along_axis(weights, columns, axis=1)
    delta = np.zeros((len(points), 7), dtype=np.float32)
    # Minimize the worst locally projected penetration in conflicting poses.
    # The lower rest floor keeps the waistband between hips and swinging arms.
    rest_floor = .0016
    p_cap = .0035 if use_weights else .004
    for _ in range(22):
        violation = targets - np.einsum("vsi,vi->vs", normals, delta)
        violation = np.where(importance > 0, violation, -1)
        worst = violation.argmax(axis=1)
        ids = np.arange(len(points))
        g = normals[ids, worst]
        magnitude = np.maximum(0, violation[ids, worst])
        delta += .44 * magnitude[:, None] * g
        delta[:, :3] = limit_delta(delta[:, :3], p_cap)
        updated = simplex(raw_weights + (delta[:, 3:] / scale).clip(-.22, .22))
        delta[:, 3:] = (updated - raw_weights) * scale
    step = delta[:, :3]
    length = np.linalg.norm(step, axis=1).clip(1e-12)
    direction = step / length[:, None]
    smoothed = step.copy()
    for _ in range(3):
        smoothed += .36 * (average(smoothed, graph) - smoothed)
    missing = np.maximum(0, length - np.einsum("vi,vi->v", smoothed, direction))
    smoothed += missing[:, None] * direction
    # Spread the Laplacian transition more broadly than the worst contact
    # while preserving its required component at every constrained vertex.
    proposed = correct_rest(points + smoothed, original, tree, rest_floor)
    if use_weights:
        changes = np.zeros_like(weights)
        np.put_along_axis(changes, columns, delta[:, 3:] / scale, axis=1)
        local = smoothstep(.25, .34, points[:, 2]) + .65 * np.exp(-((points[:, 2] - .210) / .040)**2)
        for _ in range(2):
            changes += (.23 * local[:, None]) * (average(changes, graph) - changes)
        weights = limit_weights(np.maximum(0, weights + changes))
    return proposed, weights


def rest_guard(old, proposed, triangles, tree):
    """Reject local triangle inversions, excessive stretch and body cuts."""
    before = old[triangles]
    normals = np.cross(before[:, 1] - before[:, 0], before[:, 2] - before[:, 0])
    old_area = np.linalg.norm(normals, axis=1)
    result = proposed.copy()
    previous_clearance, _, _, _ = nearest(tree, old)
    minimum = np.minimum(.00125, previous_clearance - .00001)
    for attempt in range(12):
        current = result[triangles]
        crossed = np.cross(current[:, 1] - current[:, 0], current[:, 2] - current[:, 0])
        area = np.linalg.norm(crossed, axis=1)
        cosine = (crossed * normals).sum(axis=1) / (area * old_area).clip(1e-14)
        bad = (old_area > 2e-8) & ((cosine < .45) | (area < .24 * old_area) | (area > 3.00 * old_area))
        signed, _, _, _ = nearest(tree, result)
        collisions = tree.overlap(tree_from(result, triangles))
        ids = np.unique(np.r_[triangles[bad].ravel(), [v for _, t in collisions for v in triangles[t]],
                              np.flatnonzero((signed < minimum) | (signed > CAP))]).astype(np.int32)
        if not len(ids):
            return result
        result[ids] = old[ids] + (.37 if attempt < 7 else 0) * (result[ids] - old[ids])
    return old.copy()


def build():
    scene, arm, body, garment = setup_editable()
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    mesh = garment.data
    original, triangles = mesh_arrays(mesh)
    weights = PRIOR["read_weights"](garment, names)
    graph = adjacency(mesh)
    seed, weights = shape_seed(original, weights, body, names, rest, graph)
    points = rest_guard(original, seed, triangles, rest)
    best = None
    history = []
    for iteration in range(ITERATIONS + 1):
        skin = skin_matrices(transforms, weights)
        margin = MARGIN
        d, overlaps, hits, constraints = scan(skin_positions(points, skin), triangles, samples, margin)
        summary = PRIOR["summarize"](d, overlaps, samples)
        score = bake_score(d, overlaps)
        print("FIT", iteration, len(triangles), score, [(name, v["max_verts_inside"],
              round(v["min_signed_dist"] * 1000, 3), v["max_triangle_pairs"]) for name, v in summary.items()], flush=True)
        history.append({"iteration": iteration, "triangles": len(triangles), "results": summary})
        if best is None or score < best[0]:
            best = (score, iteration, mesh.copy(), points.copy(), weights.copy())
        if (not any(score[:3]) and d.min() >= 1.5e-3) or iteration == ITERATIONS:
            break
        columns = skin_columns(weights, names, points)
        proposed, adjusted_weights = fit_step(points, original, weights, columns, skin, transforms,
                                               constraints, graph, rest, margin, iteration >= 2)
        points = rest_guard(points, proposed, triangles, rest)
        weights = adjusted_weights
        if iteration in (1, 5, 9) and hits.any():
            set_vertices(mesh, points)
            write_weights(garment, names, weights)
            # Carry the original coordinate field through the same midpoint
            # subdivision so the 30 mm bound survives topology changes.
            attr = mesh.attributes.new("original_fit_position", "FLOAT_VECTOR", "POINT")
            attr.data.foreach_set("vector", original.astype(np.float32).ravel())
            if split_edges(garment, triangles, hits, local=iteration >= 3):
                points, triangles = mesh_arrays(mesh)
                weights = limit_weights(PRIOR["read_weights"](garment, names))
                graph = adjacency(mesh)
                original = np.empty_like(points)
                mesh.attributes["original_fit_position"].data.foreach_get("vector", original.ravel())
                projected = correct_rest(points, original, rest, .0018)
                points = rest_guard(points, projected, triangles, rest)
            mesh.attributes.remove(mesh.attributes["original_fit_position"])
    score, iteration, mesh, points, weights = best
    garment.data = mesh
    report("fit_history.json", {"selected_iteration": iteration, "margin_m": MARGIN, "iterations": history})
    prior_export = PRIOR["export"]
    prior_export.__globals__.update(GLB=GLB, BLEND=BLEND)
    prior_export(scene, arm, body, garment, points, names, weights)
    print("EXPORTED", iteration, score, flush=True)


def bake_score(d, pairs):
    hard = int(d[0].min() < MINIMUM or d[0].max() > CAP or pairs[0] > 0)
    deficit = np.maximum(0, -d)
    return (hard, int(pairs.sum() + 2 * (d < 0).sum() + 1050 * deficit.sum()),
            int((d < MINIMUM).sum()), float(-d.min()))


def choose_local_moves(points, skin, samples, distances, constraints, graph, iteration):
    """Evaluate tangential escape paths where body and arm normals oppose."""
    rest = samples[0][2]
    rest_gap, _, normal, _ = nearest(rest, points)
    directions = np.cross(normal, np.array([0, 0, 1], dtype=np.float32))
    directions /= np.linalg.norm(directions, axis=1).clip(.01)[:, None]
    upwards = np.cross(directions, normal)
    needed = np.zeros_like(distances)
    for row, ids, _, values, factors in constraints:
        np.maximum.at(needed[row], ids, (MARGIN - values) * factors)
    severity = needed.max(axis=0)
    order = np.argsort(-severity, kind="stable")
    active = order[:min(475, np.count_nonzero(severity > .0008))]
    adjustments = np.zeros_like(points)
    cross_steps = [
        (0, 0), (-.004, 0), (.004, 0), (-.008, 0), (.008, 0),
        (0, -.004), (0, .004), (0, -.008), (0, .008),
        (-.005, -.005), (.005, -.005), (-.005, .005), (.005, .005),
    ]
    if iteration > 0:
        cross_steps.extend([(-.014, 0), (.014, 0), (0, -.013), (0, .013)])
    general = np.arange(0, len(samples), 15)
    graph_mean = average(points, graph)
    for v in active:
        best_pose = np.argsort(-needed[:, v], kind="stable")[:24]
        worst_vertex = np.argsort(distances[:, v], kind="stable")[:14]
        rows = np.unique(np.r_[general, best_pose, worst_vertex])
        floor = (.00155 - rest_gap[v]).clip(-.019, .008)
        normal_steps = np.unique([0, floor, .5 * floor, -.003, .003, .006, .011, .017])
        choices = [points[v]] + [
            points[v] + n * normal[v] + u * directions[v] + w * upwards[v]
            for u, w in cross_steps for n in normal_steps
        ]
        choices = np.asarray(choices, dtype=np.float32)
        clearance, _, _, _ = nearest(rest, choices)
        keep = (clearance >= .00135) & (clearance < CAP - .00015)
        keep[0] = True
        choices = choices[keep]
        linear = skin[rows, v]
        moves = np.einsum("rij,cj->rci", linear[..., :3], choices) + linear[..., 3, None].transpose(0, 2, 1)
        gaps = np.asarray([nearest(samples[row][2], coordinates)[0] for row, coordinates in zip(rows, moves)])
        # A triangle witness assigns its corner a stricter desired clearance.
        # Subtract the extra demand as a conservative local approximation.
        demand = np.maximum(0, needed[rows, v] - np.maximum(0, MARGIN - distances[rows, v]))
        deficit = np.maximum(0, MARGIN - gaps + demand[:, None])
        shape_drift = np.linalg.norm(choices - points[v], axis=1)
        edge_cost = np.maximum(0, np.linalg.norm(choices - graph_mean[v], axis=1)
                               - np.linalg.norm(points[v] - graph_mean[v]))
        costs = deficit.max(axis=0) + 2.1 * np.sqrt(np.mean(deficit ** 2, axis=0))
        costs += .09 * shape_drift + .18 * edge_cost
        winner = costs.argmin()
        adjustments[v] = choices[winner] - points[v]
    smooth = adjustments.copy()
    for _ in range(4):
        smooth += .34 * (average(smooth, graph) - smooth)
    motion = .57 * adjustments + .43 * smooth
    return points + limit_delta(motion, .0085)


def restore_dance(points, weights, triangles, graph, samples, transforms, names):
    """Restore the local source bind where the already-clear dance regressed."""
    with bpy.data.libraries.load(str(BASE.with_suffix(".blend"))) as (source, target):
        target.objects = ["Jeans"]
    source, = target.objects
    source_points, source_triangles = mesh_arrays(source.data)
    source_weights = PRIOR["read_weights"](source, names)
    bpy.data.objects.remove(source, do_unlink=True)
    if not np.array_equal(triangles, source_triangles):
        return points, weights, None
    dance_rows = np.asarray([i for i, sample in enumerate(samples) if sample[0] == "dance"])
    dance = [samples[i] for i in dance_rows]
    original_points, original_weights = points, weights
    restoration = np.zeros(len(points), dtype=np.float32)
    rest = samples[0][2]
    for attempt in range(4):
        skin = skin_matrices(transforms[dance_rows], weights)
        distances, pairs, contacts, _ = scan(skin_positions(points, skin), triangles, dance, MINIMUM)
        print("DANCE GUARD", attempt, float(distances.min()), int(pairs.max()), flush=True)
        rest_distance, _, _, _ = nearest(rest, points)
        rest_pairs = rest.overlap(tree_from(points, triangles))
        rest_invalid = (rest_distance < MINIMUM) | (rest_distance > CAP)
        if distances.min() >= MINIMUM and not pairs.any() and not rest_invalid.any() and not rest_pairs:
            return points, weights, restoration
        if attempt == 3:
            break
        restoration[np.unique(triangles[contacts > 0])] = 1
        restoration[(distances < MINIMUM).any(axis=0) | rest_invalid] = 1
        for _, garment_face in rest_pairs:
            restoration[triangles[garment_face]] = 1
        for _ in range(3):
            restoration = np.maximum(restoration, .85 * average(restoration, graph))
        restoration[restoration > .51] = 1
        scale = restoration[:, None]
        points = original_points + scale * (source_points - original_points)
        weights = limit_weights(original_weights + scale * (source_weights - original_weights))
    return original_points, original_weights, None



def polish():
    assert GLB.is_file() and BLEND.is_file()
    scene, arm, body, garment = setup_editable(BLEND)
    names = [bone.name for bone in arm.pose.bones]
    samples, transforms = cache_motion(scene, arm, body)
    rest = samples[0][2]
    points, triangles = mesh_arrays(garment.data)
    weights = PRIOR["read_weights"](garment, names)
    graph = adjacency(garment.data)
    points, weights, restoration = restore_dance(points, weights, triangles, graph, samples, transforms, names)
    dance_rows = np.asarray([i for i, sample in enumerate(samples) if sample[0] == "dance"])
    skin = skin_matrices(transforms, weights)
    initial = points.copy()
    best_score = None
    history_path = OUTPUT / "fit_history.json"
    history = json.loads(history_path.read_text())
    updates = []
    for iteration in range(5):
        d, overlaps, _, constraints = scan(skin_positions(points, skin), triangles, samples)
        score = bake_score(d, overlaps)
        dance_failure = int(d[dance_rows].min() < MINIMUM or overlaps[dance_rows].any())
        score = (score[0], dance_failure, *score[1:])
        summary = PRIOR["summarize"](d, overlaps, samples)
        updates.append({"iteration": iteration, "results": summary, "score": score})
        print("POLISH", iteration, score, [(name, v["max_verts_inside"],
              round(v["min_signed_dist"] * 1000, 3), v["max_triangle_pairs"]) for name, v in summary.items()],
              flush=True)
        if best_score is None or score < best_score:
            best_score, selected, best_points = score, iteration, points.copy()
        if iteration == 4 or (not any(score[:4]) and d.min() >= .0015):
            break
        proposed = choose_local_moves(points, skin, samples, d, constraints, graph, iteration)
        if restoration is not None:
            proposed = points + (1 - restoration[:, None]) * (proposed - points)
        proposed = correct_rest(proposed, initial, rest, .0016)
        points = rest_guard(points, proposed, triangles, rest)
    restored = int(np.count_nonzero(restoration > 0)) if restoration is not None else 0
    history.update(polish=updates, selected_polish_iteration=selected, restored_dance_vertices=restored)
    report("fit_history.json", history)
    if selected or restored:
        # Blender protects the appended input library from save-as. Write
        # the updated source beside it before replacing the published file.
        polished_source = BLEND.with_name(".polished.blend")
        prior_export = PRIOR["export"]
        prior_export.__globals__.update(GLB=GLB, BLEND=polished_source)
        prior_export(scene, arm, body, garment, best_points, names, weights)
        polished_source.replace(BLEND)
    print("POLISH COMPLETE", selected, best_score, flush=True)


def verify():
    import hashlib
    import struct

    def glb_content(path):
        content = path.read_bytes()
        size = struct.unpack_from("<I", content, 12)[0]
        data = json.loads(content[20:20 + size])
        return data, content[28 + size:]

    def image_digests(data, blob):
        digests = []
        for image in data["images"]:
            view = data["bufferViews"][image["bufferView"]]
            offset = view.get("byteOffset", 0)
            digests.append(hashlib.sha256(blob[offset:offset + view["byteLength"]]).hexdigest())
        return sorted(digests)

    verify_export = PRIOR["verify"]
    verify_export.__globals__.update(GLB=GLB, BLEND=BLEND, OUTPUT=OUTPUT, MAX_TRIANGLES=TRIANGLE_LIMIT)
    verify_export()
    details = json.loads((OUTPUT / "export_check.json").read_text())
    data, blob = glb_content(GLB)
    images = image_digests(data, blob)
    details["image_sha256"] = images
    details["identical_images_to_round_1"] = images == image_digests(*glb_content(BASE))
    details["exported_vertices"] = sum(
        data["accessors"][p["attributes"]["POSITION"]]["count"] for p in data["meshes"][0]["primitives"]
    )
    details["has_uv"] = all("TEXCOORD_0" in p["attributes"] for p in data["meshes"][0]["primitives"])
    assert details["has_uv"]
    report("export_check.json", details)


def run_checkers():
    import io
    from contextlib import redirect_stdout

    for stem in ("motion_check", "motion_check_tri"):
        path = HERE / f"{stem}.py"
        code = path.read_text()
        # Keep both supplied measurements and sample times. The separate
        # Cycles render stage avoids the headless Workbench dependency.
        code = code.replace("sc.render.engine='BLENDER_WORKBENCH';", "")
        code = code.replace("bpy.ops.render.render(write_still=True)", "None")
        code = code.replace("{out}/motion_check.json", "{out}/" + stem + ".json")
        argv = sys.argv
        output = io.StringIO()
        try:
            sys.argv = [str(path), "--", str(PRIOR["MASTER"]), str(PRIOR["MOTION"]), str(GLB), str(HERE)]
            with redirect_stdout(output):
                exec(compile(code, str(path), "exec"), {})
        finally:
            sys.argv = argv
        rows = [line for line in output.getvalue().splitlines() if line.startswith("RESULT ")]
        assert len(rows) == 8
        result = "\n".join(rows) + "\n"
        (HERE / f"{stem}.txt").write_text(result)
        print(result, end="", flush=True)


def render():
    import hashlib
    from mathutils import Vector

    scene, arm, body, garment = PRIOR["setup"](GLB)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = scene.render.resolution_y = 576
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("QA Studio")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.70, .76, .85, 1)
    background.inputs[1].default_value = .5
    rest_center = Vector((0, -.01, .248))
    for name, location, energy, size in (
        ("Key", (-.65, -1.25, 1.35), 65, 1.55),
        ("Fill", (.8, -.3, .68), 26, 1.3),
        ("Rim", (.3, 1.1, 1.0), 49, 1.2),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = location
        lamp.rotation_euler = (rest_center - lamp.location).to_track_quat("-Z", "Y").to_euler()
    lens = bpy.data.cameras.new("QA Orthographic")
    lens.type = "ORTHO"
    camera = bpy.data.objects.new(lens.name, lens)
    scene.collection.objects.link(camera)
    scene.camera = camera
    dense = json.loads((HERE / "dense_check.json").read_text())["results"]
    views = []

    def capture(filename, clip, frame, center, direction, size):
        PRIOR["set_pose"](scene, arm, clip, frame)
        lens.ortho_scale = size
        camera.location = center + Vector(direction).normalized() * 3
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / filename)
        bpy.ops.render.render(write_still=True)
        views.append({"file": filename, "clip": clip, "frame": frame, "direction": direction, "width_m": size})

    directions = ((0, -1, 0), (.63, -1, .14), (1, 0, 0), (0, 1, 0), (-.63, 1, .14), (-1, 0, 0))
    size, gutter = scene.render.resolution_x, 8
    sheet = np.full((2 * size + gutter, 3 * size + 2 * gutter, 4), (.12, .14, .17, 1), dtype=np.float32)
    for index, direction in enumerate(directions):
        filename = f".view_{index}.png"
        capture(filename, "rest", 1, rest_center, direction, .49)
        cell = bpy.data.images.load(str(HERE / filename))
        pixels = np.empty(size * size * 4, dtype=np.float32)
        cell.pixels.foreach_get(pixels)
        col, row_from_bottom = index % 3, 1 - index // 3
        y, x = row_from_bottom * (size + gutter), col * (size + gutter)
        sheet[y:y + size, x:x + size] = pixels.reshape(size, size, 4)
        bpy.data.images.remove(cell)
        (HERE / filename).unlink()
        views[-1]["file"] = "six_view.png"
        views[-1]["cell"] = {"row": 1 + index // 3, "column": 1 + col}
    contact_sheet = bpy.data.images.new("Six orthographic views", width=sheet.shape[1], height=sheet.shape[0], alpha=True)
    contact_sheet.pixels.foreach_set(sheet.ravel())
    contact_sheet.filepath_raw = str(HERE / "six_view.png")
    contact_sheet.file_format = "PNG"
    contact_sheet.save()

    for clip in ("walk", "run", "wave", "jump"):
        entry = dense[clip]
        frame = entry["worst_overlap_frame"] if entry["max_triangle_pairs"] else entry["worst_vertex_frame"]
        PRIOR["set_pose"](scene, arm, clip, frame)
        points, _ = PRIOR["evaluated_arrays"](garment, bpy.context.evaluated_depsgraph_get())
        center = Vector((points.min(axis=0) + points.max(axis=0)) * .5)
        direction = (-.56, -1, .13) if clip == "walk" else (.56, -1, .13)
        capture(f"{clip}.png", clip, frame, center, direction, .56)
    for entry in views:
        entry["sha256"] = hashlib.sha256((HERE / entry["file"]).read_bytes()).hexdigest()
    report("render_manifest.json", {"glb_sha256": hashlib.sha256(GLB.read_bytes()).hexdigest(),
                                    "engine": "Cycles CPU", "samples": scene.cycles.samples, "views": views})


if __name__ == "__main__":
    if "--polish" in sys.argv:
        polish()
    elif "--verify" in sys.argv:
        verify()
    elif "--checkers" in sys.argv:
        run_checkers()
    elif "--renders" in sys.argv:
        render()
    else:
        build()
