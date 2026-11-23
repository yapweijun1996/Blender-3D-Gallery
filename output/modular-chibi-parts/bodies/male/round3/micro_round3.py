"""Clear isolated vertex witnesses while guarding incident triangles."""
import json
import sys

import numpy as np

from asset_io import write_json
from body_audit import load_body_motion
from fit_module import CAP, nearest, read_module
from fitting_geometry import laplacian, tree, weights
from fit_round3 import Fit, OUT
from gltf_pose import normalized
from motion_repair import FIXED
from polish_round3 import AXES, read_failures, sample_selection
from verify_round3 import module_path
from vertex_refit import signed_at

GOAL = .00056
SEARCH_RADII = (.00015, .00030, .00055, .00085, .0012, .0017, .0023, .0032,
                .0045, .006, .0085, .012, .016)


def body_workspace(samples, fit, groups, radius, dense):
    faces = np.asarray(samples[0].faces)
    active = np.flatnonzero(np.isin(fit.graph[0], groups))
    reach = radius * 2 + .012
    for sample in samples:
        full = tree(sample.body, sample.faces)
        if not dense:
            sample.cached_tree = full
            continue
        faces_near = set()
        for p in sample.garment[active].tolist():
            _, _, _, distance = full.find_nearest(p)
            faces_near.update(int(row[2]) for row in full.find_nearest_range(p, distance + reach))
        if not faces_near:
            sample.cached_tree = full
            continue
        subset = faces[sorted(faces_near)]
        ids, remap = np.unique(subset, return_inverse=True)
        sample.cached_tree = tree(sample.body[ids], remap.reshape(-1, 3).tolist())


def stable_signed_at(bvh, points):
    distances = []
    for point in points.tolist():
        q, n, _, distance = bvh.find_nearest(point)
        tied = bvh.find_nearest_range(point, distance + .000003)
        if not tied:
            tied = [(q, n, None, distance)]
        distances.append(min((point[0] - loc.x) * normal.x + (point[1] - loc.y) * normal.y
                             + (point[2] - loc.z) * normal.z for loc, normal, _, _ in tied))
    return distances


def active_groups(fit, samples, failures):
    inv = fit.graph[0]
    groups = {}
    for sample in samples:
        if (sample.clip, sample.frame) not in failures:
            continue
        surface = tree(sample.body, sample.faces)
        d, _, _ = nearest(surface, sample.garment[fit.representatives])
        for i, value in zip(inv[fit.representatives], d):
            if value < GOAL:
                groups[int(i)] = min(float(value), groups.get(int(i), 1.))
    return sorted(groups, key=groups.get)


def adjust(fit, samples, group, radius):
    inv = fit.graph[0]
    changed = np.flatnonzero(inv == group)
    representative = []
    for i in changed:
        distances = [signed_at(sample.cached_tree, sample.garment[i:i+1])[0] for sample in samples]
        representative.append((min(distances), i))
    group_index = min(representative)[1]
    kernel = (inv == group).astype(np.float32)
    soft = np.maximum(kernel, laplacian(kernel, fit.graph) * .92)
    soft = np.maximum(soft, laplacian(soft, fit.graph) * .65)
    triangle_ids = np.flatnonzero((soft[fit.faces] > 0.).any(axis=1))
    nearby_vertices, remap = np.unique(fit.faces[triangle_ids], return_inverse=True)
    near_faces = remap.reshape(-1, 3).tolist()
    vertex = fit.position[group_index]
    index = fit.ids[group_index]
    weight = fit.packed[group_index]
    mats = np.stack([(s.transforms[index] * weight[:, None, None]).sum(axis=0) for s in samples])
    points = np.stack([s.garment[group_index] for s in samples])
    points += np.einsum('fij,j->fi', mats[:, :, :3], vertex - fit.base[group_index])
    hits = [s.cached_tree.find_nearest(p) for s, p in zip(samples, points.tolist())]
    normals = np.asarray([r[1] for r in hits], dtype=np.float32)
    nearest_points = np.asarray([r[0] for r in hits], dtype=np.float32)
    signed = np.einsum('fi,fi->f', points - nearest_points, normals)
    danger = np.flatnonzero(signed < GOAL)
    if not len(danger):
        return None
    closest = np.argsort(signed)[:14]
    axes = np.einsum('fji,fj->fi', mats[closest, :, :3], normals[closest])
    guide = axes.mean(axis=0)
    radial = vertex - np.array([0., -.024, vertex[2]], dtype=np.float32)
    directions = np.unique(np.round(normalized(np.vstack((axes, -axes[:4], guide, radial, AXES))), 4), axis=0)
    candidates = (directions[:, None, :] * np.asarray(SEARCH_RADII)[None, :, None]).reshape(-1, 3)
    anchor = fit.base[group_index]
    used = vertex - anchor
    candidates = candidates[np.linalg.norm(candidates + used, axis=1) <= radius]
    candidates = np.concatenate((np.zeros((1, 3)), candidates)).astype(np.float32)
    sizes = np.linalg.norm(candidates, axis=1)
    close_frames = list(range(len(samples)))
    search_frames = sorted({*closest, *danger[::max(1, len(danger) // 18)]})

    def evaluate(moves, frame_ids):
        counts = np.zeros(len(moves), dtype=int)
        depths = np.zeros(len(moves), dtype=float)
        minima = np.ones(len(moves), dtype=float)
        for i in frame_ids:
            positions = points[i] + moves @ mats[i, :, :3].T
            distance = np.asarray(signed_at(samples[i].cached_tree, positions), dtype=float)
            counts += distance < GOAL
            depths += np.maximum(GOAL - distance, 0.)
            minima = np.minimum(minima, distance)
        return counts, depths, minima

    rough = evaluate(candidates, search_frames)
    order = np.lexsort((sizes, np.maximum(GOAL - rough[2], 0.), rough[1], rough[0]))
    finalists = {0, *order[:42]}
    for lower, upper in ((.0005, .0014), (.0014, .003), (.003, .006), (.006, .01), (.01, .04)):
        finalists.update([i for i in order if lower <= sizes[i] < upper][:18])
    reduced = sorted(finalists)
    fine = evaluate(candidates[reduced], close_frames)
    margins = np.ones(len(reduced), dtype=float)
    unstable = np.zeros(len(reduced), dtype=int)
    for i in close_frames:
        projected = points[i] + candidates[reduced] @ mats[i, :, :3].T
        clearance = np.asarray(stable_signed_at(samples[i].cached_tree, projected))
        margins = np.minimum(margins, clearance)
        unstable += clearance < .00051
    costs = sizes[reduced]
    outcomes = np.lexsort((costs, np.maximum(GOAL - margins, 0.), unstable, fine[1], fine[0]))
    chosen = None
    shape = None
    base_points = fit.position[nearby_vertices]
    for spread in (kernel, soft):
        touched = spread[nearby_vertices] > 0.
        for j in outcomes[:30]:
            proposal_id = reduced[j]
            margin = (fine[0][j], fine[1][j], -fine[2][j])
            if proposal_id == 0 or margin >= (fine[0][0], fine[1][0], -fine[2][0]):
                continue
            delta = candidates[proposal_id]
            after = base_points + spread[nearby_vertices, None] * delta
            shift = after - fit.base[nearby_vertices]
            if np.linalg.norm(shift, axis=1).max() > radius:
                continue
            for i in close_frames:
                sample = samples[i]
                m = (sample.transforms[fit.ids[nearby_vertices]]
                     * fit.packed[nearby_vertices, :, None, None]).sum(axis=1)
                observed = sample.garment[nearby_vertices]
                origin = fit.base[nearby_vertices]
                trial = observed + np.einsum('vij,vj->vi', m[:, :, :3], after - origin)
                old = observed + np.einsum('vij,vj->vi', m[:, :, :3], base_points - origin)
                current = sample.cached_tree
                new_signed, _, _ = nearest(current, trial[touched])
                if (new_signed < .00050).any():
                    old_signed, _, _ = nearest(current, old[touched])
                    if ((new_signed < .00050) & (old_signed >= .00050)).any():
                        break
                new_pairs = current.overlap(tree(trial, near_faces))
                if new_pairs and len(new_pairs) > len(current.overlap(tree(old, near_faces))):
                    break
            else:
                chosen = j
                shape = after
                break
        if chosen is not None:
            break
    if chosen is None:
        print('VERTEX GUARD', fit.key, int(group), float(fine[2][0]), int(fine[0][0]),
              int(fine[0].min()), flush=True)
        return None
    step = candidates[reduced[chosen]]
    fit.position[nearby_vertices] = shape
    return dict(group=int(group), before_mm=float(fine[2][0] * 1000),
                after_mm=float(fine[2][chosen] * 1000),
                remaining_frames=int(fine[0][chosen]), offset_mm=float(np.linalg.norm(step) * 1000.))


def finish(keys, preserve=False, dense=False):
    scene, arm, body, actions = load_body_motion(FIXED)
    names = [bone.name for bone in arm.data.bones]
    for key in keys:
        report = OUT / 'qa' / f'fit-{key}.json'
        record = json.loads(report.read_text())
        failures = read_failures(key, record)
        if not failures:
            continue
        obj = read_module(module_path(key), arm)
        fit = Fit(key, obj, names, np.zeros(len(obj.data.vertices), dtype=bool))
        fit.w = weights(obj, names)
        fit.refresh()
        safe = (record['vertex_displacement_max_mm']
                + record.get('waist_adjustment', {}).get('max_adjustment_mm', 0.)) / 1000.
        exact_bound = OUT / 'qa/offset_measurement.json'
        if exact_bound.is_file():
            measured = json.loads(exact_bound.read_text())[key]
            if measured['sha256'] == record['sha256']:
                safe = measured['upper_bound_mm'] / 1000.
        radius = max(0., CAP - safe - .00015)
        if dense:
            radius = min(radius, .0045)
        samples = sample_selection(scene, arm, body, actions, names, failures, obj, dense_grid=dense)
        groups = active_groups(fit, samples, failures)
        print('VERTEX BANK', key, len(samples), 'poses', len(groups), 'groups', flush=True)
        if not groups:
            continue
        body_workspace(samples, fit, groups, radius, dense)
        history = []
        for group in groups:
            item = adjust(fit, samples, group, radius)
            print('VERTEX PATCH', key, group, item, flush=True)
            if item is not None:
                history.append(item)
        del samples
        if not history:
            continue
        if preserve:
            displacement = np.linalg.norm(fit.position - fit.base, axis=1)
            changed = displacement > 1.e-8
            write_json(OUT / '.runtime' / f'{key}-positions.json', {
                'input': record['sha256'], 'offset_mm': float(displacement.max() * 1000),
                'history': history,
                'rows': [[a.tolist(), b.tolist()] for a, b in zip(fit.base[changed], fit.position[changed])],
            })
            continue
        fit.export_v3(arm, names)
        export = json.loads(report.read_text())
        record.setdefault('vertex_polish', []).append({'input_sha256': record['sha256'], 'patches': history})
        record['sha256'] = export['sha256']
        record['vertex_displacement_max_mm'] += export['vertex_displacement_max_mm']
        write_json(report, record)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    finish([arg for arg in args if not arg.startswith('--')] or ['dress', 'jeans'],
           preserve='--preserve-attributes' in args, dense='--dense' in args)
