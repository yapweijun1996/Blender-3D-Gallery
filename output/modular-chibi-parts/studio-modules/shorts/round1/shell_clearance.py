"""Offset a thin lining with local face-plane constraints at folded rims."""
import numpy as np


def lining_normals(points, faces, weighted):
    """Keep the offset inward for every incident exterior triangle."""
    ids = faces.ravel()
    normals = weighted / np.linalg.norm(weighted, axis=1, keepdims=True).clip(1e-12)
    constraints = np.repeat(normals, 3, axis=0)
    direction = np.zeros_like(points)
    np.add.at(direction, ids, constraints)
    direction /= np.linalg.norm(direction, axis=1, keepdims=True).clip(1e-9)
    # The source folds contain very short faces. Enforcing all their normals
    # avoids a thickness vector that follows a large face through a small one.
    for _ in range(36):
        projection = np.einsum("ni,ni->n", direction[ids], constraints)
        violation = np.maximum(0, .20 - projection)
        largest = np.zeros(len(points))
        np.maximum.at(largest, ids, violation)
        useful = (violation > 1e-4) & (violation >= largest[ids] - 1e-8)
        correction = np.zeros_like(points)
        np.add.at(correction, ids[useful], constraints[useful] * violation[useful, None])
        count = np.bincount(ids[useful], minlength=len(points)).clip(1)[:, None]
        direction += .78 * correction / count
        direction /= np.maximum(1, np.linalg.norm(direction, axis=1, keepdims=True) / 2.8)
    return direction


def generate(points, faces, thickness):
    tri = points[faces]
    normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    return points - thickness * lining_normals(points, faces, normal)


def axis_candidates(tri_a, tri_b):
    edge_a = np.roll(tri_a, -1, axis=0) - tri_a
    edge_b = np.roll(tri_b, -1, axis=0) - tri_b
    n_a = np.cross(edge_a[0], edge_a[1])
    n_b = np.cross(edge_b[0], edge_b[1])
    axes = np.vstack((n_a, n_b, np.cross(edge_a[:, None, :], edge_b[None, :, :]).reshape(-1, 3),
                      np.cross(n_a, edge_a), np.cross(n_b, edge_b)))
    norm = np.linalg.norm(axes, axis=1)
    axes = axes[norm > 1e-13] / norm[norm > 1e-13, None]
    return np.vstack((axes, -axes))


def pair_shift(points, a, b, exterior, margin, free_outer=False):
    axes = axis_candidates(points[a], points[b])
    pa, pb = points[a] @ axes.T, points[b] @ axes.T
    fixed_a, fixed_b = (a < exterior) & (not free_outer), (b < exterior) & (not free_outer)
    weight_a, weight_b = np.where(a < exterior, 32., 1.), np.where(b < exterior, 32., 1.)
    amax, bmin = pa.max(axis=0), pb.min(axis=0)
    af = np.where(fixed_a[:, None], pa, -np.inf).max(axis=0)
    bf = np.where(fixed_b[:, None], pb, np.inf).min(axis=0)
    feasible = af + margin <= bf
    wa, wb = weight_a[pa.argmax(axis=0)], weight_b[pb.argmin(axis=0)]
    mid = np.clip((wa * amax + wb * bmin) / (wa + wb), af + margin * .5, bf - margin * .5)
    a_move = np.where(fixed_a[:, None], 0, np.maximum(0, pa - mid + margin * .5))
    b_move = np.where(fixed_b[:, None], 0, np.maximum(0, mid - pb + margin * .5))
    cost = np.where(feasible, (np.square(a_move) * weight_a[:, None]).sum(axis=0) +
                    (np.square(b_move) * weight_b[:, None]).sum(axis=0), np.inf)
    choice = cost.argmin()
    if not np.isfinite(cost[choice]) or cost[choice] <= 1e-16:
        return
    vector = axes[choice]
    points[a] -= a_move[:, choice, None] * vector
    points[b] += b_move[:, choice, None] * vector


def clean_pairs(points, triangles, exterior_count, tree_from, iterations=40, max_outer=0.):
    """Separate lining contacts without moving the rendered exterior cage."""
    placement = points.copy()
    best = placement.copy()
    best_count = np.inf
    for pass_id in range(iterations):
        tree = tree_from(placement, triangles)
        pairs = sorted((a, b) for a, b in tree.overlap(tree)
                       if a < b and not np.isin(triangles[a], triangles[b]).any())
        count = len(pairs)
        if count < best_count:
            best, best_count = placement.copy(), count
        if not count:
            break
        for i, j in (pairs if pass_id % 2 == 0 else reversed(pairs)):
            pair_shift(placement, triangles[i], triangles[j], exterior_count, .000014, max_outer > 0)
        delta = placement - points
        bound = np.r_[np.full(exterior_count, max_outer), np.full(exterior_count, .00135)]
        scale = np.minimum(1, bound / np.linalg.norm(delta, axis=1).clip(1e-10))
        placement = points + delta * scale[:, None]
    return best, int(best_count)

def separating_gaps(points, triangles, pairs):
    """Return positive gaps between triangles when a separating plane exists."""
    gaps = []
    for a, b in pairs:
        tri_a, tri_b = points[triangles[a]], points[triangles[b]]
        axes = axis_candidates(tri_a, tri_b)
        gaps.append(float(((tri_b @ axes.T).min(axis=0) - (tri_a @ axes.T).max(axis=0)).max()))
    return np.asarray(gaps)


def local_polish(points, faces, exterior, tree_from, reference, passes=4):
    """Remove tightly folded rim contacts with bounded one-vertex moves."""
    result = points.copy()
    face_ids = np.arange(len(faces))
    incidence = [np.flatnonzero(np.any(faces == i, axis=1)) for i in range(len(points))]
    moves = np.concatenate([np.r_[np.eye(3), -np.eye(3)] * length
                            for length in (.000045, .00011, .00023, .00040)])
    for _ in range(passes):
        tree = tree_from(result, faces)
        pairs = [(a, b) for a, b in tree.overlap(tree)
                 if a < b and not np.isin(faces[a], faces[b]).any()]
        if not pairs:
            break
        bad = np.bincount(faces[np.asarray(pairs)].ravel(), minlength=len(points))
        order = sorted(np.flatnonzero(bad), key=lambda i: (i < exterior, -bad[i], i))
        changed = 0
        for idx in order:
            selected = incidence[idx]
            local = result[faces[selected]]
            low, high = local.min(axis=(0, 1)) - .001, local.max(axis=(0, 1)) + .001
            nearby = result[faces]
            share = np.isin(face_ids, selected)
            candidate = np.flatnonzero(~share & np.all(nearby.max(axis=1) >= low, axis=1)
                                       & np.all(nearby.min(axis=1) <= high, axis=1))
            used, remap = np.unique(faces[selected], return_inverse=True)
            local_faces = remap.reshape(-1, 3)
            cache, ix = np.unique(faces[candidate], return_inverse=True)
            static_tree = tree_from(result[cache], ix.reshape(-1, 3))
            comparable = (faces[selected, None, :, None] == faces[candidate][None, :, None, :]).any(axis=(2, 3))
            base = result[used].copy()
            iv = np.searchsorted(used, idx)
            before = local
            old_normal = np.cross(before[:, 1] - before[:, 0], before[:, 2] - before[:, 0])

            def collision(local_points):
                trial = tree_from(local_points, local_faces)
                return sum(not comparable[a, b] for a, b in trial.overlap(static_tree))

            score = collision(base)
            if not score:
                continue
            best = result[idx].copy()
            extra = .00056 if idx < exterior else .00160
            for move in moves:
                choice = result[idx] + move
                if np.linalg.norm(choice - reference[idx]) > extra:
                    continue
                base[iv] = choice
                t = base[local_faces]
                normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
                if (np.einsum("ni,ni->n", old_normal, normal) < 0).any():
                    continue
                value = collision(base)
                if value < score:
                    best, score = choice, value
                    if not score:
                        break
            if np.any(best != result[idx]):
                result[idx] = best
                changed += 1
        if not changed:
            break
    tree = tree_from(result, faces)
    pairs = [(a, b) for a, b in tree.overlap(tree) if a < b and not np.isin(faces[a], faces[b]).any()]
    return result, pairs
