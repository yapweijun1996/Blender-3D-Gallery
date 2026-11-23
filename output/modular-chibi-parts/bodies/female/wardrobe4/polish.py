"""Search a small neighborhood for feasible offsets at isolated clearance witnesses."""
from itertools import product

import numpy as np
from mathutils.bvhtree import BVHTree

import fit_module as fit


def displacement_candidates():
    directions = np.asarray(list(product((-1, 0, 1), repeat=3)), dtype=np.float32)
    directions = fit.normalized(directions[np.any(directions != 0, axis=1)])
    radii = np.asarray((.001, .002, .004, .007, .011, .016, .022), dtype=np.float32)
    return np.vstack((np.zeros((1, 3), np.float32), (radii[:, None, None] * directions).reshape(-1, 3)))


def legal_moves(point, weight, rows, matrices, margin, trials, robust):
    skin = fit.GEOMETRY["pose_matrices"](matrices, weight[None])[:, 0]
    posed = np.einsum("fij,vj->fvi", skin[:, :, :3], point + trials) + skin[:, None, :, 3]
    minimum = np.full(len(trials), np.inf)
    for row, candidates in zip(rows, posed, strict=True):
        signed, _, _, _ = fit.nearest(row[2], candidates)
        minimum = np.minimum(minimum, signed)
    feasible = np.flatnonzero(minimum >= margin)
    if robust and len(feasible):
        # The closest face can change at a shared edge after Float32 export.
        # Test a small neighborhood around each point against both sides.
        offsets = np.r_[np.zeros((1, 3)), np.eye(3), -np.eye(3)] * .000075
        for row, candidates in zip(rows, posed, strict=True):
            probes = candidates[feasible, None] + offsets
            signed, _, _, _ = fit.nearest(row[2], probes.reshape(-1, 3))
            feasible = feasible[(signed.reshape(-1, len(offsets)) >= margin).all(axis=1)]
            if not len(feasible):
                break
    return trials[feasible]


def keep_faces_outside(index, point, neighbors, triangles, rows, skin):
    for row, frame_skin, frame_neighbors in zip(rows, skin, neighbors, strict=True):
        trial = frame_neighbors.copy()
        trial[index] = frame_skin[index, :, :3] @ point + frame_skin[index, :, 3]
        region = BVHTree.FromPolygons(trial.tolist(), triangles, all_triangles=True)
        if row[2].overlap(region):
            return False
    return True


def solve(points, faces, weights, data, bad_ids, margin, goals=None, robust=False):
    result = points.copy()
    rows, matrices = data[3:]
    for vertex in bad_ids:
        if goals is None:
            trials = displacement_candidates()
        else:
            delta = goals[vertex] - result[vertex]
            trials = delta * np.array([1., .85, .70, .55, .40, .25], dtype=np.float32)[:, None]
        moves = legal_moves(result[vertex], weights[vertex], rows, matrices, margin, trials, robust)
        if not len(moves):
            continue
        local = faces[np.any(faces == vertex, axis=1)]
        used, inverse = np.unique(local, return_inverse=True)
        index = int(np.searchsorted(used, vertex))
        triangles = inverse.reshape(local.shape).tolist()
        skin = fit.GEOMETRY["pose_matrices"](matrices, weights[used])
        neighbors = fit.GEOMETRY["skin_positions"](result[used], skin)
        for move in moves[:10]:
            target = result[vertex] + move
            candidate = result[used].copy()
            candidate[index] = target
            corners = candidate[inverse.reshape(local.shape)]
            original = result[local]
            old_normal = np.cross(original[:, 1] - original[:, 0], original[:, 2] - original[:, 0])
            new_normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
            if np.any((old_normal * new_normal).sum(axis=1) <= 0):
                continue
            if keep_faces_outside(index, target, neighbors, triangles, rows, skin):
                result[vertex] = target
                print("POLISH", int(vertex), "move mm", (move * 1000).round(2).tolist(), flush=True)
                break
    return result
