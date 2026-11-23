"""Resolve residual contacts on the exported, UV-split Blender mesh."""

import json
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_jeans_r5.py"))
R2, PRIOR = FIT["R2"], FIT["PRIOR"]
TARGET = .00062


def gaps(tree, points):
    """Use the Blender nearest-face sign with the supplied checker precision."""
    result = []
    for point in map(Vector, points.tolist()):
        surface, normal, _, _ = tree.find_nearest(point)
        result.append((point - surface).dot(normal))
    return np.asarray(result, dtype=np.float32)


def contact_score(distances, counts):
    deficit = np.maximum(0, TARGET - distances)
    return (int(counts.sum()) + 4 * int((distances < .0005).sum()),
            int(np.count_nonzero(deficit)), float(deficit.sum()))


def sample_export(scene, arm, body, garment):
    poses, samples, transforms = [], [], []
    names = [bone.name for bone in arm.pose.bones]
    bones = [arm.pose.bones[name] for name in names]
    inverse = [bone.bone.matrix_local.inverted() for bone in bones]
    modes = [bone.rotation_mode for bone in bones]
    _, bf = FIT["mesh_arrays"](body.data)
    for clip, frame in FIT["frames"]():
        FIT["set_pose"](scene, arm, clip, frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        points = []
        for obj in (body, garment):
            evaluated = obj.evaluated_get(depsgraph)
            coordinates = np.empty(3 * len(evaluated.data.vertices), dtype=np.float32)
            evaluated.data.vertices.foreach_get("co", coordinates)
            world = np.asarray(evaluated.matrix_world)
            points.append(coordinates.reshape(-1, 3) @ world[:3, :3].T + world[:3, 3])
        samples.append((clip, frame, FIT["tree_from"](points[0], bf)))
        poses.append(points[1])
        transforms.append(np.asarray([bone.matrix @ bind for bone, bind in zip(bones, inverse)])[:, :3])
    assert modes == [bone.rotation_mode for bone in bones]
    return names, samples, np.asarray(transforms, dtype=np.float32), np.asarray(poses)


def measure(samples, posed, faces):
    nearest, pairs = [], []
    for (_, _, tree), points in zip(samples, posed):
        nearest.append(gaps(tree, points))
        pairs.append(tree.overlap(FIT["tree_from"](points, faces)))
    return np.asarray(nearest), pairs


def local_search(points, weights, faces, samples, transforms, posed, distances, pairs, names, mesh):
    rest = samples[0][2]
    shapes = R2["HOODIE"]["PRIOR"]["RestShape"](mesh, points, rest)
    unit = R2["HOODIE"]["PRIOR"]["scaled_directions"](36)
    unit = np.r_[unit, np.eye(3), -np.eye(3)]
    offsets = np.asarray([np.zeros(3), *(size * axis for size in
                         (.00045, .001, .0022, .004, .006, .009, .013) for axis in unit)], dtype=np.float32)
    _, canonical = np.unique(np.rint(points * 1e7).astype(np.int64), axis=0, return_inverse=True)
    crossing = np.zeros((len(samples), len(faces)), dtype=np.int16)
    for row, hit in enumerate(pairs):
        if hit:
            np.add.at(crossing[row], np.asarray(hit)[:, 1], 1)
    rank = (distances < TARGET).sum(axis=0) * 5
    rank += np.bincount(faces.ravel(), weights=np.repeat(crossing.sum(axis=0), 3),
                        minlength=len(points)).astype(rank.dtype)
    ordered = np.argsort(-rank, kind="stable")
    visited, changes = set(), []
    for vertex in ordered[rank[ordered] > 0]:
        key = canonical[vertex]
        if key in visited:
            continue
        visited.add(key)
        group = np.flatnonzero(canonical == key)
        incident = np.unique(np.concatenate([shapes.incidence[i] for i in group]))
        patch, mapped = np.unique(faces[incident], return_inverse=True)
        patch_faces = mapped.reshape(-1, 3)
        slots = np.searchsorted(patch, group)
        base_p, base_w = points[group], weights[group]
        start_pose = posed[:, group].copy()
        start_patch = posed[:, patch].copy()
        matrix = FIT["skin_matrices"](transforms, base_w)
        deficits = distances[:, group].min(axis=1)
        cuts = crossing[:, incident].sum(axis=1)
        if not cuts.any() and deficits.min() >= TARGET:
            continue
        mandatory = np.flatnonzero((deficits < TARGET) | (cuts > 0))
        per_clip = np.r_[0, np.flatnonzero([samples[i][0] != samples[i-1][0]
                                             for i in range(1, len(samples))]) + 1]
        rows = np.unique(np.r_[0, per_clip, np.arange(0, len(samples), 23),
                               np.argsort(deficits, kind="stable")[:28],
                               np.argsort(-cuts, kind="stable")[:25], mandatory[::max(1, len(mandatory)//25)]])
        anatomy = [j for j, name in enumerate(names) if (
            name.split(":")[-1] in ("Hips", "Spine", "Spine1")
            or (("Left" if points[vertex, 0] > 0 else "Right") in name
                and any(f"{side}{label}" in name for side in ("Left", "Right")
                        for label in ("Leg", "UpLeg", "Foot"))))]
        anatomy = sorted(set(anatomy) | set(np.flatnonzero(base_w.max(axis=0))))
        prelim = matrix[rows, 0, :3, :3] @ offsets.T
        trials = start_pose[rows, 0, None, :] + prelim.transpose(0, 2, 1)
        trial_distances = np.asarray([gaps(samples[i][2], p) for i, p in zip(rows, trials)])
        miss = np.maximum(0, TARGET - trial_distances)
        index = np.argsort((miss * 900 + 0.18 * (trial_distances < .0005)).sum(axis=0)
                           + np.linalg.norm(offsets, axis=1) * 20, kind="stable")
        possible = [(offsets[k], base_w) for k in index[:55]]
        small = index[:5]
        for joint in anatomy:
            for scale in (.05, .13, .27):
                weight = (1 - scale) * base_w
                weight[:, joint] += scale
                weight = FIT["limit_weights"](weight)
                possible.extend((offsets[k], weight) for k in small)
        coarse = []
        before_approx = contact_score(deficits[rows], cuts[rows])[0]
        collision_rows = np.unique(np.r_[0, np.argsort(-cuts[rows], kind="stable")[:12],
                                         np.argsort(deficits[rows], kind="stable")[:9]])
        for offset, weight in possible:
            rest_dist = gaps(rest, base_p + offset)
            if rest_dist.min() < .00063 or rest_dist.max() > .02997:
                continue
            if not all(shapes.accepts(v, p + offset, points) for v, p in zip(group, base_p)):
                continue
            trial_skin = FIT["skin_matrices"](transforms[rows], weight)
            delta = FIT["skin_positions"](base_p + offset, trial_skin) - FIT["skin_positions"](base_p, matrix[rows])
            trial = start_pose[rows] + delta
            d = np.asarray([gaps(samples[i][2], p).min() for i, p in zip(rows, trial)])
            cut_count = 0
            for j in collision_rows:
                trial_patch = start_patch[rows[j]].copy()
                trial_patch[slots] = trial[j]
                cut_count += len(samples[rows[j]][2].overlap(FIT["tree_from"](trial_patch, patch_faces)))
            merit = (cut_count + 4 * int((d < .0005).sum()),
                     float(np.maximum(0, TARGET - d).sum()
                           + .015 * np.linalg.norm(offset) + .0009 * np.abs(weight - base_w).sum()))
            if merit[0] <= before_approx + 2:
                coarse.append((merit, offset, weight))
        coarse.sort(key=lambda candidate: candidate[0])
        best = contact_score(deficits, cuts)
        initial = best
        winner = None
        inverse_orders = np.unique(np.r_[rows, mandatory])
        order = np.r_[inverse_orders, np.setdiff1d(np.arange(len(samples)), inverse_orders)]
        for _, offset, weight in coarse[:22]:
            candidate_skin = FIT["skin_matrices"](transforms, weight)
            delta = FIT["skin_positions"](base_p + offset, candidate_skin) - FIT["skin_positions"](base_p, matrix)
            trial = start_pose + delta
            d = np.empty((len(samples), len(group)), dtype=np.float32)
            counts = np.zeros(len(samples), dtype=np.int16)
            new_crossings = np.zeros((len(samples), len(incident)), dtype=np.int16)
            cost = 0
            for i in order:
                tree = samples[i][2]
                d[i] = gaps(tree, trial[i])
                trial_patch = start_patch[i].copy()
                trial_patch[slots] = trial[i]
                found = tree.overlap(FIT["tree_from"](trial_patch, patch_faces))
                counts[i] = len(found)
                if found:
                    np.add.at(new_crossings[i], np.asarray(found)[:, 1], 1)
                cost += len(found) + 4 * int(d[i].min() < .0005)
                if (i == 0 and (len(found) or d[i].min() < .0005 or d[i].max() > .03)) or cost > best[0]:
                    break
            else:
                value = contact_score(d.min(axis=1), counts)
                if value < best:
                    best, winner = value, (offset, weight, trial, d, new_crossings)
                    if not value[0] and not value[1]:
                        break
        if winner is not None:
            offset, weight, trial, d, new_crossings = winner
            points[group] = base_p + offset
            weights[group] = weight
            posed[:, group] = trial
            distances[:, group] = d
            crossing[:, incident] = new_crossings
            changes.append({"vertex_ids": group.tolist(), "zone": FIT["zone"](base_p[0]),
                            "offset_m": offset.tolist(), "before": initial, "after": best})
            print("REFINED", changes[-1], flush=True)
        else:
            print("RESIDUAL", int(vertex), FIT["zone"](base_p[0]), base_p[0].tolist(), initial, flush=True)
    return changes


def main():
    scene, arm, body, garment = FIT["setup"](FIT["GLB"])
    points, faces = FIT["mesh_arrays"](garment.data)
    names, samples, transforms, posed = sample_export(scene, arm, body, garment)
    weights = FIT["read_weights"](garment, names)
    distances, pairs = measure(samples, posed, faces)
    counts = np.asarray(list(map(len, pairs)))
    print("EXACT INPUT", FIT["summarize"](distances, counts, samples), flush=True)
    if not counts.any() and distances.min() >= .0005:
        return
    changes = local_search(points, weights, faces, samples, transforms, posed,
                           distances, pairs, names, garment.data)
    if not changes:
        return
    distances, pairs = measure(samples, posed, faces)
    print("EXACT PATCH", FIT["summarize"](distances, np.asarray(list(map(len, pairs))), samples), flush=True)
    path = HERE / "fit_history.json"
    history = json.loads(path.read_text())
    history.setdefault("exact_local_refit", []).append(changes)
    FIT["save_fit"](arm, body, garment, points, weights, names)
    FIT["write_json"](path.name, history)


if __name__ == "__main__":
    main()
