"""Search local lofts and weight blends around exact clearance witnesses."""
from itertools import product
import json
import sys
from collections import defaultdict

import numpy as np

from asset_io import CLIPS, bpy, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import CAP, FLOOR, Sample, influences, nearest, read_module
from fitting_geometry import arrays, laplacian, limit_weights, tree, weights, welded
from fit_round3 import Fit, OUT
from gltf_pose import normalized
from motion_repair import FIXED
from robust_refit import GuardedGarment
from verify import grids
from verify_round3 import module_path

SEARCH_FLOOR = FLOOR + .000035
AXES = normalized(np.asarray([axis for axis in product((-1., 0., 1.), repeat=3) if any(axis)]))


def read_failures(key, record):
    audit = OUT / 'qa/modules' / f'{key}.json'
    if audit.is_file():
        data = json.loads(audit.read_text())
        if data['sha256'] == record['sha256']:
            return {(name, f['frame']) for name, c in data['clips'].items() for f in c['frames']
                    if f['inside'] or f['triangle_pairs'] or f['min_signed_m'] < SEARCH_FLOOR}
    stages = record.get('passes', [])
    if stages:
        return {(clip, frame) for clip, frame, *_ in stages[-1]['failures']}
    return set()


def sample_selection(scene, arm, body, actions, names, failures, garment=None, dense_grid=False):
    rest_matrices = [arm.data.bones[n].matrix_local.inverted() for n in names]
    bfaces = arrays(body)[1].tolist()
    likely = defaultdict(list)
    for clip, frame in failures:
        likely[clip].append(frame)
    samples = []
    for clip in ('rest', *CLIPS):
        action = actions.get(clip)
        frames = grids(action, scene.render.fps) if action else [0.]
        dense = likely[clip]
        selected = set(frames[::11]) | {frames[-1]}
        if dense or dense_grid:
            selected.update(frames)
        if clip == 'idle':
            selected.add(24.)
        use_action(arm, action)
        for frame in sorted(selected):
            set_frame(scene, frame)
            matrices = np.asarray([arm.pose.bones[n].matrix @ rest
                                   for n, rest in zip(names, rest_matrices)], dtype=np.float32)
            sample = Sample(clip, frame, posed(body), bfaces, matrices[:, :3])
            if garment is not None:
                sample.garment = posed(garment)
            samples.append(sample)
    use_action(arm, None)
    set_frame(scene, 0.)
    return samples


def witnesses(fit, samples):
    hits = defaultdict(list)
    inv = fit.graph[0]
    for i, pose in enumerate(samples):
        row, evidence = fit.measure(pose, tree(pose.body, pose.faces), True, trigger=SEARCH_FLOOR)
        if row[0] or row[1] or row[2] < SEARCH_FLOOR:
            if evidence is None:
                continue
            vertices, axes, depth = evidence
            for j, axis, need in zip(inv[vertices], axes, depth):
                hits[int(j)].append((i, axis, float(need)))
    return hits


def zones(graph, hits):
    _, p, q, _, _ = graph
    live = set(hits)
    groups = []
    while live:
        seed = min(live)
        live.remove(seed)
        zone = {seed}
        frontier = {seed}
        while frontier:
            adjacent = set(q[np.isin(p, list(frontier))])
            frontier = adjacent.intersection(live)
            live.difference_update(frontier)
            zone.update(frontier)
        groups.append(sorted(zone))
    return sorted(groups, key=lambda z: -max(rec[2] for k in z for rec in hits[k]))


def patch(fit, samples, zone, hits, radius):
    graph = fit.graph
    inv = graph[0]
    kernel = np.isin(inv, zone).astype(float)
    soft = kernel.copy()
    for _ in range(3):
        soft = np.maximum(soft, laplacian(soft, graph) * .83)
    sharp = np.maximum(kernel, laplacian(kernel, graph) * .75)
    face_ids = np.flatnonzero((soft[fit.faces] > 0.).any(axis=1))
    vertices, remap = np.unique(fit.faces[face_ids], return_inverse=True)
    faces = remap.reshape(-1, 3).tolist()
    initial = fit.position[vertices].copy()
    initial_w = fit.w[vertices].copy()
    anchor = fit.base[vertices]
    records = sorted((item for k in zone for item in hits[k]), key=lambda item: -item[2])
    impacted = {i for i, _, _ in records}
    affected_clips = {samples[i].clip for i in impacted}
    support = {i for i, p in enumerate(samples) if p.clip in affected_clips}
    support.update(range(0, len(samples), 4))
    support.update(i for i, p in enumerate(samples) if p.clip == 'rest' or (p.clip == 'idle' and p.frame == 24.))
    fast_ids = sorted(impacted)
    if len(fast_ids) > 14:
        fast_ids = sorted({*fast_ids[::max(1, len(fast_ids) // 10)], *(i for i, _, _ in records[:6])})
    full_ids = sorted(support | impacted)
    want = records[0][2]
    proposal_axes = np.array([r[1] for r in records[:18]])
    average = proposal_axes.sum(axis=0)
    guide = fit.guide[np.isin(inv, zone)].mean(axis=0)
    axes = np.unique(np.round(normalized(np.vstack((proposal_axes, -proposal_axes[:5], average, guide, AXES))), 4), axis=0)
    axes = axes[np.argsort(-(axes @ records[0][1]))]

    def transforms(w, frame_ids):
        ids, values = influences(w)
        return [(samples[i].transforms[ids] * values[:, :, None, None]).sum(axis=1) for i in frame_ids]

    matrices = dict(zip(full_ids, transforms(initial_w, full_ids)))
    body_faces = np.asarray(samples[0].faces)
    nearby = {}
    for i, basis in matrices.items():
        posed = np.einsum('vij,vj->vi', basis[:, :, :3], initial) + basis[:, :, 3]
        p = samples[i].body
        bounds_min = posed.min(axis=0) - .045
        bounds_max = posed.max(axis=0) + .045
        in_box = ((p >= bounds_min) & (p <= bounds_max)).all(axis=1)
        selected = body_faces[in_box[body_faces].any(axis=1)]
        if not len(selected):
            nearby[i] = tree(p, samples[i].faces)
            continue
        used, remap = np.unique(selected, return_inverse=True)
        nearby[i] = tree(p[used], remap.reshape(-1, 3).tolist())

    def measure(shape, frame_ids, transform_map=matrices, failed=None):
        bad_count = pair_count = inside = 0
        delta = 0.
        minimum = 1.
        for i in frame_ids:
            basis = transform_map[i]
            points = np.einsum('vij,vj->vi', basis[:, :, :3], shape) + basis[:, :, 3]
            bvh = nearby[i]
            d, _, _ = nearest(bvh, points)
            low = float(d.min())
            pairs = len(bvh.overlap(tree(points, faces)))
            if pairs or low < SEARCH_FLOOR:
                if failed is not None:
                    failed.append((i, pairs, low))
                bad_count += 1
                pair_count += pairs
                inside += int((d < 0.).sum())
                delta += float(np.maximum(SEARCH_FLOOR - d, 0.).sum())
                minimum = min(minimum, low)
        return (bad_count, pair_count + inside, delta, -minimum)

    print('ZONE', fit.key, len(zone), 'vertices', len(vertices), 'poses', len(full_ids),
          'critical', len(fast_ids), flush=True)
    failures = []
    full_rank = measure(initial, full_ids, failed=failures)
    if not full_rank[0]:
        return None
    hard = sorted(failures, key=lambda row: (-row[1], row[2]))
    fast_ids = sorted({*fast_ids, *(i for i, _, _ in hard[:15])})
    sizes = np.unique(np.r_[.00035, .0008, .0014, .002, .003, .0045, .0065, .009, .012, .016,
                            want * .75, want, want * 1.5]).clip(0., radius)
    finalists = []
    picked = initial
    picked_w = initial_w
    label = 'baseline'

    def apply(delta):
        shift = initial + delta - anchor
        shift *= np.minimum(1., radius / np.linalg.norm(shift, axis=1, keepdims=True).clip(1.e-9, None))
        return (anchor + shift).astype(np.float32)

    for mask, name in ((soft, 'smooth loft'), (sharp, 'local loft'), (kernel, 'witness only')):
        profile = mask[vertices, None]
        for axis in axes:
            for size in sizes:
                candidate = apply(profile * (size * axis))
                rank = measure(candidate, fast_ids)
                finalists.append((rank, size, name, candidate))
    finalists.sort(key=lambda p: p[:2])
    shortlist = finalists[:8]
    for label in ('smooth loft', 'local loft', 'witness only'):
        for lower, upper in ((.0, .0015), (.0015, .004), (.004, .008), (.008, 1.)):
            matching = [trial for trial in finalists if trial[2] == label and lower <= trial[1] < upper]
            shortlist.extend(matching[:2])
    checked = set()
    for _, _, name, proposal in shortlist:
        token = id(proposal)
        if token in checked:
            continue
        checked.add(token)
        guarded = measure(proposal, full_ids)
        if guarded < full_rank:
            picked, full_rank, label = proposal, guarded, name
        if not full_rank[0]:
            break
    if full_rank[0]:
        local_mask = soft[vertices, None]
        neighbors = welded(laplacian(fit.w, graph), graph)[vertices]
        goals = [('smoothed weights', neighbors), ('body-following weights', fit.surface_w[vertices])]
        for description, weighted in goals:
            for mix in (.10, .24, .40):
                w = limit_weights(initial_w * (1. - mix * local_mask) + weighted * (mix * local_mask))
                alternative = dict(zip(full_ids, transforms(w, full_ids)))
                for shape in (picked, initial):
                    guarded = measure(shape, full_ids, alternative)
                    if guarded < full_rank:
                        picked, picked_w, full_rank, label = shape, w, guarded, description
                if not full_rank[0]:
                    break
            if not full_rank[0]:
                break
    if not np.array_equal(picked, initial) and not full_rank[0] and np.array_equal(picked_w, initial_w):
        # Blend only along the accepted patch and replay it before storing.
        weight_goal = welded(laplacian(fit.w, graph), graph)[vertices]
        for strength in (.07, .03):
            blend = strength * soft[vertices, None]
            w = limit_weights(initial_w * (1. - blend) + weight_goal * blend)
            alternative = dict(zip(full_ids, transforms(w, full_ids)))
            if not measure(picked, full_ids, alternative)[0]:
                picked_w = w
                label += ' with smoothed weights'
                break
    if np.array_equal(picked, initial) and np.array_equal(picked_w, initial_w):
        print('PATCH kept', fit.key, len(zone), len(impacted), full_rank, flush=True)
        return None
    fit.position[vertices] = picked
    fit.w[vertices] = picked_w
    fit.refresh()
    item = {'mode': label, 'affected_welded_vertices': len(zone), 'support_frames': len(full_ids),
            'score': full_rank, 'peak_delta_mm': float(np.linalg.norm(picked - initial, axis=1).max() * 1000)}
    print('PATCH', fit.key, item, flush=True)
    return item


def polish(keys):
    scene, arm, body, actions = load_body_motion(FIXED)
    names = [b.name for b in arm.data.bones]
    for key in keys:
        qa = OUT / 'qa' / f'fit-{key}.json'
        record = json.loads(qa.read_text())
        failures = read_failures(key, record)
        if not failures:
            print('No residual witnesses', key, flush=True)
            continue
        garment = read_module(module_path(key), arm)
        fit = Fit(key, garment, names, np.zeros(len(garment.data.vertices), dtype=bool))
        fit.w = weights(garment, names)
        fit.guide, fit.surface_w = GuardedGarment.guides(fit, body, names)
        fit.refresh()
        used = (record['vertex_displacement_max_mm'] +
                record.get('waist_adjustment', {}).get('max_adjustment_mm', 0.)) / 1000.
        palette = max(0., CAP - used - .0001)
        samples = sample_selection(scene, arm, body, actions, names, failures)
        print('LOCAL BANK', key, len(samples), 'poses', len(failures), 'failing', flush=True)
        history = []
        for iteration in range(2):
            hits = witnesses(fit, samples)
            print('WITNESSES', key, iteration, len(hits), flush=True)
            if not hits:
                break
            n_before = len(history)
            for zone in zones(fit.graph, hits):
                item = patch(fit, samples, zone, hits, palette)
                if item:
                    history.append(item)
                if len(zone) > 1 and (item is None or item['score'][0]):
                    for vertex in zone:
                        single = patch(fit, samples, [vertex], hits, palette)
                        if single:
                            history.append(single)
            if n_before == len(history):
                break
        if history:
            fit.export_v3(arm, names)
            result = json.loads(qa.read_text())
            record.setdefault('local_polish', []).append({
                'input_sha256': record['sha256'], 'patches': history,
                'offset_mm': result['vertex_displacement_max_mm'],
            })
            record['sha256'] = result['sha256']
            record['vertex_displacement_max_mm'] += result['vertex_displacement_max_mm']
            write_json(qa, record)


if __name__ == '__main__':
    polish(sys.argv[sys.argv.index('--') + 1:] or ['dress', 'jeans'])
