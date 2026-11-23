"""Bake bind-space clearance using all motion samples and face witnesses."""
import time

import numpy as np

import fit_module as fit

MARGIN = .0018
BATCH = 24


def constrain(directions, requirements, vertices, normals, rhs):
    axis = np.abs(normals).argmax(axis=1)
    cells = 6 * vertices + 2 * axis + (normals[np.arange(len(axis)), axis] >= 0)
    order = np.lexsort((-rhs, cells))
    unique = order[np.r_[True, np.diff(cells[order]) != 0]]
    update = unique[rhs[unique] > requirements[cells[unique]]]
    requirements[cells[update]] = rhs[update]
    directions[cells[update]] = normals[update]


def measure(points, faces, weights, data):
    _, _, _, rows, transforms = data
    directions = np.zeros((6 * len(points), 3), np.float32)
    requirements = np.zeros(6 * len(points), np.float32)
    peak_deficit = np.zeros(len(points), np.float32)
    intersecting = np.zeros(len(faces), dtype=bool)
    pair_total, pair_peak, inside_total, inside_peak = 0, 0, 0, 0
    min_signed, min_row, min_vertex = np.inf, 0, 0
    for start in range(0, len(rows), BATCH):
        batch = slice(start, start + BATCH)
        skin = fit.GEOMETRY["pose_matrices"](transforms[batch], weights)
        posed = fit.GEOMETRY["skin_positions"](points, skin)
        distance, pairs, face_hits, hits = fit.SOURCE["scan"](posed, faces, rows[batch], margin=MARGIN)
        intersecting |= face_hits > 0
        inside = (distance < 0).sum(axis=1)
        pair_total += int(pairs.sum())
        pair_peak = max(pair_peak, int(pairs.max()))
        inside_total += int(inside.sum())
        inside_peak = max(inside_peak, int(inside.max()))
        minimum = float(distance.min())
        if minimum < min_signed:
            row, min_vertex = np.unravel_index(distance.argmin(), distance.shape)
            min_signed, min_row = minimum, start + row
        peak_deficit = np.maximum(peak_deficit, np.maximum(0, MARGIN - distance.min(axis=0)))
        for row, vertices, world_normal, signed, factors in hits:
            gradients = np.einsum("vi,vij->vj", world_normal, skin[row, vertices, :, :3])
            length = np.linalg.norm(gradients, axis=1).clip(.15)
            rhs = np.minimum(.025, (MARGIN - signed) * factors / length)
            constrain(directions, requirements, vertices, gradients / length[:, None], rhs)
    worst_clip, worst_frame = rows[min_row][:2]
    report = dict(peak_pairs=pair_peak, peak_inside=inside_peak, total_pairs=pair_total,
                  total_inside=inside_total, minimum_signed_mm=min_signed * 1000, minimum_clip=worst_clip,
                  minimum_frame=worst_frame, minimum_vertex=int(min_vertex),
                  worst_margin_deficit_mm=float(peak_deficit.max() * 1000))
    unsafe_vertices = peak_deficit > MARGIN - .00053
    unsafe_faces = intersecting | unsafe_vertices[faces].any(axis=1)
    return report, directions.reshape(len(points), 6, 3), requirements.reshape(len(points), 6), unsafe_faces


def solve(normals, required, graph):
    """Smooth the worst per-vertex displacement while retaining its projection."""
    step = np.zeros_like(normals[:, 0])
    for _ in range(10):
        gap = required - np.einsum("vij,vj->vi", normals, step)
        active = gap.argmax(axis=1)
        rows = np.arange(len(step))
        move = np.maximum(0, gap[rows, active])
        step += .65 * move[:, None] * normals[rows, active]
        step = fit.SOURCE["limit_delta"](step, .012)
    smooth = step.copy()
    for _ in range(3):
        smooth = .74 * smooth + .26 * fit.average(smooth, graph)
    direction = fit.normalized(step)
    loss = np.maximum(0, np.linalg.norm(step, axis=1) - (smooth * direction).sum(axis=1))
    return smooth + .88 * loss[:, None] * direction


def score(report):
    clearance = max(0., .5 - report["minimum_signed_mm"])
    return report["total_pairs"] + 4 * report["total_inside"] + 8 * clearance


def bake(item, number, seed, surface, outward, faces, weights, graph, data):
    points = seed.copy()
    history = []
    best = None
    rejected = 0
    topology = type("Topology", (), {"faces": faces})
    iterations = 7 if number == 3 and item in {"shorts", "skirt", "boots"} else 5
    for iteration in range(iterations):
        start = time.monotonic()
        stats, normals, required, unsafe = measure(points, faces, weights, data)
        value = score(stats)
        stats.update(iteration=iteration + 1, score=value)
        history.append(stats)
        print("BAKE", item, number, stats, "seconds", round(time.monotonic() - start, 1), flush=True)
        if best is None or value < best[0]:
            best = value, points.copy(), solve(normals, required, graph), unsafe
            rejected = 0
        else:
            rejected += 1
        if value == 0 or rejected == 2:
            break
        step = best[2] * (1 if rejected == 0 else .38)
        base = best[1]
        cap = .060 if item == "skirt" else .030
        candidate = seed + fit.SOURCE["limit_delta"](base + step - seed, cap)
        if item != "skirt":
            projection = ((candidate - surface) * outward).sum(axis=1)
            candidate += np.maximum(0, .0007 - projection)[:, None] * outward
        points = fit.protect_style(topology, base, candidate)
    return best[1], history, best[3]
