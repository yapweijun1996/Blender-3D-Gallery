"""Bake bind-space clearance using all motion samples and face witnesses."""
import time

import numpy as np

import fit_module as fit
import polish
from layer_contacts import Layers

MARGIN = .0018
BATCH = 24
DIRECTIONS = 27
WEIGHT_SCALE = 30.


def constrain(directions, requirements, vertices, normals, rhs):
    xyz = fit.normalized(normals[:, :3])
    signs = 1 + (xyz >= .31).astype(int) - (xyz <= -.31).astype(int)
    cells = DIRECTIONS * vertices + signs @ np.array([1, 3, 9])
    order = np.lexsort((-rhs, cells))
    unique = order[np.r_[True, np.diff(cells[order]) != 0]]
    update = unique[rhs[unique] > requirements[cells[unique]]]
    requirements[cells[update]] = rhs[update]
    directions[cells[update]] = normals[update]


def measure(points, faces, weights, data, margin, joints=None, draggable=None, layering=None):
    _, _, _, rows, transforms = data
    channels = 3 if joints is None else 6
    directions = np.zeros((DIRECTIONS * len(points), channels), np.float32)
    requirements = np.zeros(DIRECTIONS * len(points), np.float32)
    peak_deficit = np.zeros(len(points), np.float32)
    pair_total, pair_peak, inside_total, inside_peak = 0, 0, 0, 0
    min_signed, min_row, min_vertex = np.inf, 0, 0
    layer_total, layer_peak = 0, 0
    frame_cost = np.zeros(len(rows), np.float32)
    for start in range(0, len(rows), BATCH):
        batch = slice(start, start + BATCH)
        skin = fit.GEOMETRY["pose_matrices"](transforms[batch], weights)
        posed = fit.GEOMETRY["skin_positions"](points, skin)
        distance, pairs, _, hits = fit.SOURCE["scan"](posed, faces, rows[batch], margin=margin)
        inside = (distance < 0).sum(axis=1)
        frame_cost[batch] = pairs + 4 * inside + (np.maximum(0, margin - distance) * 1000).sum(axis=1)
        if layering is not None:
            layer_pairs, extra = layering.scan(posed, faces, rows[batch], margin)
            frame_cost[batch] += layer_pairs
            layer_total += int(layer_pairs.sum())
            layer_peak = max(layer_peak, int(layer_pairs.max()))
            hits.extend(extra)
        pair_total += int(pairs.sum())
        pair_peak = max(pair_peak, int(pairs.max()))
        inside_total += int(inside.sum())
        inside_peak = max(inside_peak, int(inside.max()))
        minimum = float(distance.min())
        if minimum < min_signed:
            row, min_vertex = np.unravel_index(distance.argmin(), distance.shape)
            min_signed, min_row = minimum, start + row
        peak_deficit = np.maximum(peak_deficit, np.maximum(0, margin - distance.min(axis=0)))
        for row, vertices, world_normal, signed, factors in hits:
            gradients = np.einsum("vi,vij->vj", world_normal, skin[row, vertices, :, :3])
            if joints is not None:
                joint_skin = transforms[start + row, joints[vertices]]
                joint_world = (np.einsum("vnij,vj->vni", joint_skin[..., :3], points[vertices]) +
                               joint_skin[..., 3])
                influence = np.einsum("vni,vi->vn", joint_world[:, 1:] - joint_world[:, :1], world_normal)
                gradients = np.column_stack((gradients, WEIGHT_SCALE * influence * draggable[vertices]))
            length = np.linalg.norm(gradients, axis=1).clip(.15)
            rhs = np.minimum(.025, (margin - signed) * factors / length)
            constrain(directions, requirements, vertices, gradients / length[:, None], rhs)
    worst_clip, worst_frame = rows[min_row][:2]
    report = dict(peak_pairs=pair_peak, peak_inside=inside_peak, total_pairs=pair_total,
                  total_inside=inside_total, peak_layer_pairs=layer_peak, total_layer_pairs=layer_total, minimum_signed_mm=min_signed * 1000, minimum_clip=worst_clip,
                  minimum_frame=worst_frame, minimum_vertex=int(min_vertex),
                  witness_rest_mm=(points[min_vertex] * 1000).round(3).tolist(),
                  worst_margin_deficit_mm=float(peak_deficit.max() * 1000))
    return (report, directions.reshape(len(points), DIRECTIONS, channels),
            requirements.reshape(len(points), DIRECTIONS), peak_deficit, frame_cost)


def solve(normals, required, graph, limit):
    """Smooth the worst per-vertex displacement while retaining its projection."""
    step = np.zeros_like(normals[:, 0])
    for _ in range(18):
        gap = required - np.einsum("vij,vj->vi", normals, step)
        active = gap.argmax(axis=1)
        rows = np.arange(len(step))
        move = np.maximum(0, gap[rows, active])
        step += .65 * move[:, None] * normals[rows, active]
        step = fit.SOURCE["limit_delta"](step, limit)
    smooth = step.copy()
    for _ in range(3):
        smooth = .74 * smooth + .26 * fit.average(smooth, graph)
    direction = fit.normalized(step)
    loss = np.maximum(0, np.linalg.norm(step, axis=1) - (smooth * direction).sum(axis=1))
    return smooth + .88 * loss[:, None] * direction


def score(report, threshold):
    clearance = max(0., threshold - report["minimum_signed_mm"])
    return report["total_pairs"] + 4 * report["total_inside"] + report["total_layer_pairs"] + 8 * clearance


def diagnostic_subset(data, costs):
    labels, rows, matrices = data[0], data[3], data[4]
    sampled = set(range(0, len(rows), 12))
    for clip in dict.fromkeys(row[0] for row in rows):
        indices = np.asarray([i for i, row in enumerate(rows) if row[0] == clip])
        sampled.update(indices[np.argsort(costs[indices])[-10:]])
        sampled.update((indices[0], indices[-1]))
    selected = sorted(sampled)
    return labels, data[1], data[2], [rows[i] for i in selected], matrices[selected]


def tune_weights(weights, seed_weights, joints, delta):
    existing = np.take_along_axis(weights, joints, axis=1)
    seed = np.take_along_axis(seed_weights, joints, axis=1)
    moving = existing[:, 1:] + WEIGHT_SCALE * delta
    lower = np.maximum(0., seed[:, 1:] - .22)
    upper = np.minimum(1., seed[:, 1:] + .22)
    moving = np.clip(moving, lower, upper)
    moving[seed[:, 1:] == 0.] = 0.
    moving /= np.maximum(moving.sum(axis=1, keepdims=True), 1.)
    changed = np.zeros_like(weights)
    np.put_along_axis(changed, joints, np.column_stack((1. - moving.sum(axis=1), moving)), axis=1)
    return changed


def bake(item, number, seed, faces, seed_weights, graph, data, assets):
    layering = Layers({name: assets[name] for name in ("tshirt", "jeans")}, data) if item == "jacket" and number >= 2 else None
    weights = seed_weights.copy()
    fit_weights = item in {"jacket", "shorts", "skirt"} and number >= 2
    joints = np.argsort(-seed_weights, axis=1, kind="stable")[:, :4] if fit_weights else None
    draggable = np.take_along_axis(seed_weights, joints, axis=1)[:, 1:] > 0. if fit_weights else None
    points = seed.copy()
    history = []
    best = None
    topology = type("Topology", (), {"faces": faces})
    iterations = (9, 10, 16)[number - 1]
    if number == 3 and item == "skirt":
        iterations = 1
    elif number == 3 and item == "jacket":
        iterations = 5
    threshold = 1.5 if item == "shorts" else .5
    top = item in {"hoodie", "jacket"}
    margin = .0025 if item == "shorts" else (.00125 if top else MARGIN)
    step_limit = .004 if top else .010
    full = True
    subset = data
    best_step = None
    backtracking = 1.
    for iteration in range(iterations):
        start = time.monotonic()
        frame_data = data if full else subset
        stats, normals, required, deficits, costs = measure(points, faces, weights, frame_data, margin, joints, draggable, layering)
        value = score(stats, threshold + .07)
        stats.update(iteration=iteration + 1, score=value, samples=len(frame_data[3]))
        history.append(stats)
        print("BAKE", item, number, stats, "seconds", round(time.monotonic() - start, 1), flush=True)
        step = solve(normals, required, graph, step_limit)
        if full:
            subset = diagnostic_subset(data, costs)
            if best is None or value < best[0]:
                best = value, points.copy(), weights.copy(), deficits, stats
                best_step = step
                backtracking = 1.
            elif value > best[0]:
                backtracking *= .65
                points, weights = best[1].copy(), best[2].copy()
                step = best_step * backtracking
            if value == 0:
                break
        cap = .065 if item == "skirt" else .034
        candidate = seed + fit.SOURCE["limit_delta"](points + step[:, :3] - seed, cap)
        points = fit.protect_style(topology, points, candidate)
        if fit_weights:
            weights = tune_weights(weights, seed_weights, joints, step[:, 3:])
        full = value == 0 or (iteration + 1) % 4 == 0 or iteration + 2 == iterations
    value, points, weights, deficits, report = best
    if number >= 2 and 0 < value and report["peak_pairs"] <= 5:
        active = np.flatnonzero(deficits > margin - (threshold + .05) / 1000.)
        if 0 < len(active) <= 12:
            candidate = polish.solve(points, faces, weights, data, active, (threshold + .09) / 1000.)
            if not np.array_equal(candidate, points):
                stats, _, _, _, _ = measure(candidate, faces, weights, data, margin, layering=layering)
                final_score = score(stats, threshold + .07)
                stats.update(stage="local-clearance-search", score=final_score, samples=len(data[3]))
                history.append(stats)
                print("POLISH_GATE", stats, flush=True)
                if final_score < value:
                    points = candidate
    return points, weights, history
