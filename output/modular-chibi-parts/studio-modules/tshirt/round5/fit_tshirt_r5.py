"""Fit the shipped T-shirt to the corrected Blender action banks."""
import argparse
from pathlib import Path
import runpy
import sys

import numpy as np

OUT = Path(__file__).resolve().parent
PARTS = OUT.parents[2]
SOURCE = OUT.parent / "round3/tshirt_v3.glb"
EXPORT = OUT / "tshirt_v5.glb"
ACTIONS = PARTS / "actions-fix/actions_fixed.glb"
FIT = runpy.run_path(str(OUT.parent / "round4/fit_tshirt_r4.py"))
FIT["load_clips"].__globals__.update(OUT=OUT, SOURCE=SOURCE, EXPORT=EXPORT, ACTIONS=ACTIONS)
FIT["SHARED"].update(OUT=OUT, NAME="tshirt_v5", GLB=EXPORT)

R2, PRIOR, R3 = (FIT[key] for key in ("R2", "PRIOR", "PREVIOUS"))
coordinates, faces_of, mean, signed = (FIT[key] for key in ("coords", "faces_of", "mean", "signed"))
report_scan, digest, write_json = (FIT[key] for key in ("report_scan", "digest", "write_json"))
TARGET, CAP = .0005, .03


def packed_contacts(contacts):
    frames, ids, bary, normal, distance = R3["pack_contacts"](contacts)
    vertex = bary[:, 0] == 1
    anchor = ids[:, 0]
    # Similar constraints in nearby poses need one representative per time span.
    key = (frames // 8 * (ids.max() + 1) + anchor) * 2 + vertex
    order = np.lexsort((distance, key))
    keep = order[np.r_[True, np.diff(key[order]) != 0]]
    return tuple(array[keep] for array in (frames, ids, bary, normal, distance))


def solve(points, weights, original_weights, links, matrices, transforms, contacts, margin, skin_scale):
    frames, ids, bary, normal, distance = packed_contacts(contacts)
    gradient = np.einsum("ni,nkij->nkj", normal, matrices[frames[:, None], ids, :, :3])
    initial = R3["worst_offset"](ids, bary, gradient, distance, len(points), margin)
    initial = R2["laplacian_floor"](initial, links).astype(np.float32)
    columns = np.argsort(-(weights + original_weights * .01), axis=1, kind="stable")[:, :4]
    current = np.take_along_axis(weights, columns, axis=1)
    if skin_scale:
        joint = transforms[frames[:, None, None], columns[ids]]
        posed = np.einsum("nkjlm,nkm->nkjl", joint[..., :3], points[ids]) + joint[..., 3]
        leverage = np.einsum("nl,nkjl->nkj", normal, posed)
        leverage -= leverage.mean(axis=-1, keepdims=True)
        gradient = np.concatenate((gradient, skin_scale * leverage), axis=-1)
    gradient *= bary[..., None]
    squared = np.square(gradient).sum(axis=(1, 2)).clip(.08)
    flat = ids.ravel()
    step = np.zeros((len(points), gradient.shape[-1]), dtype=np.float32)
    step[:, :3] = initial * .45
    for iteration in range(43):
        error = np.maximum(margin - distance - np.einsum("nkj,nkj->n", gradient, step[ids]), 0)
        importance = error ** 2
        importance[frames == 0] *= 16
        force = (importance * error / squared)[:, None, None] * gradient
        denominator = np.bincount(flat, weights=(importance[:, None] * np.abs(bary)).ravel(),
                                  minlength=len(points)).clip(1e-16)
        update = np.column_stack([np.bincount(flat, weights=column.ravel(), minlength=len(points))
                                  for column in force.transpose(2, 0, 1)])
        step += (1.10 * update / denominator[:, None]).astype(np.float32)
        smoothing = .22 if iteration < 10 else .09
        step += (smoothing * (mean(step, links) - step)).astype(np.float32)
        movement = np.linalg.norm(step[:, :3], axis=1).clip(1e-9)
        step[:, :3] *= np.minimum(1, .0045 / movement)[:, None]
        if skin_scale:
            revised = R2["project_simplex"](current + skin_scale * step[:, 3:])
            step[:, 3:] = (revised - current) / skin_scale
    adjusted = weights.copy()
    if skin_scale:
        np.put_along_axis(adjusted, columns, revised, axis=1)
    return step[:, :3], adjusted, initial


def objective(d, pairs):
    deficit = np.maximum(.00068 - d, 0) * 1000
    above = np.maximum(d[0] - CAP + .00002, 0) * 1000
    return (float(1e5 * (pairs[0] + (deficit[0] > .18).sum() + (above > 0).sum()))
            + float(3 * pairs.sum() + 3 * (d < 0).sum()
                    + 1.5 * np.square(deficit).sum() + 250 * deficit.max() ** 2))


def representative_rows(samples, distances, pairs, cadence):
    """Choose the worst samples and regular anchors for each local BVH search."""
    rows = {0}
    for clip in FIT["CLIPS"]:
        group = np.array([i for i, sample in enumerate(samples) if sample[0] == clip])
        rows.update(group[::cadence])
        rows.update(group[np.argsort(distances[group].min(axis=1), kind="stable")[:3]])
        rows.update(group[np.argsort(pairs[group], kind="stable")[-3:]])
    return sorted(rows)


def restore_passing_clips(points, weights, reference, original_weights, faces, links, samples, transforms):
    """Retain the three motions that passed the requested gate in Round 3."""
    selected = ("rest", "wave", "idle", "nod")
    rows = [i for i, sample in enumerate(samples) if sample[0] in selected]
    poses = transforms[rows]
    body_samples = [samples[i] for i in rows]
    delta, rebind = points - reference, weights - original_weights
    edited = (np.abs(delta).max(axis=1) > 1e-9) | (np.abs(rebind).max(axis=1) > 1e-7)
    touched = faces[edited[faces].any(axis=1)]
    if not len(touched):
        return points, weights, []
    local, patch = np.unique(touched, return_inverse=True)
    patch = patch.reshape(-1, 3)
    alpha = np.ones(len(points), dtype=np.float32)
    history = []
    for i in range(8):
        p = reference + alpha[:, None] * delta
        w = PRIOR["limit_weights"](original_weights + alpha[:, None] * rebind)
        d, overlaps = FIT["scan_pairs"](p[local], w[local], patch, body_samples, poses)
        bad = np.any(d < .00053, axis=0)
        crossing = {face for hits in overlaps for _, face in hits}
        history.append({"pass": i, "vertices_below_floor": int(bad.sum()),
                        "triangle_pair_occurrences": sum(map(len, overlaps))})
        print("PRESERVE PASSING", history[-1], flush=True)
        if not bad.any() and not crossing:
            return p, w, history
        if crossing:
            bad[patch[sorted(crossing)].ravel()] = True
        retain = np.ones_like(alpha)
        retain[local[bad]] = .32 if i < 3 else 0
        alpha *= np.minimum(retain, .82 * mean(retain, links) + .18)
    return points, weights, history


def clear_jump_cuff(points, weights, faces, links, samples, transforms):
    """Test a small coherent offset where jump's sleeve edge touches the arm."""
    protected = {"rest", "jump", "wave", "idle", "nod"}
    rows = [i for i, sample in enumerate(samples) if sample[0] in protected]
    jump = np.array([i for i in rows if samples[i][0] in ("rest", "jump")])
    _, _, (hits, _, _, _) = R2["scan"](
        points, weights, faces, samples, transforms, rows=jump, collect=True)
    if not hits.any():
        return points, 0.

    falloff = np.zeros(len(points), dtype=np.float32)
    falloff[np.unique(faces[hits > 0])] = 1
    for _ in range(3):
        falloff = np.maximum(falloff, .62 * mean(falloff, links))
    patch = faces[(falloff[faces] > .012).any(axis=1)]
    local, remapped = np.unique(patch, return_inverse=True)
    axes = np.array([(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1)
                     for z in (-1, 0, 1) if x or y or z], dtype=np.float32)
    axes /= np.linalg.norm(axes, axis=1)[:, None]
    for size in (.00015, .00035, .00065, .001):
        for direction in axes:
            offset = falloff[local, None] * size * direction
            candidate = points[local] + offset
            distances, overlaps = FIT["scan_pairs"](
                candidate, weights[local], remapped.reshape(-1, 3),
                [samples[i] for i in rows], transforms[rows])
            if not any(overlaps) and distances.min() >= .00053 and distances[0].max() <= CAP:
                adjusted = points.copy()
                adjusted[local] = candidate
                return adjusted, size
    return points, 0.


def build(exact_passes):
    scene, arm, body, garment, names = FIT["open_fit"]()
    reference = coordinates(garment.data)
    original_weights = PRIOR["limit_weights"](PRIOR["read_weights"](garment, names))
    points, weights = reference.copy(), original_weights.copy()
    samples, transforms = FIT["cache_motion"](scene, arm, body, names)
    faces, links = faces_of(garment.data), PRIOR["adjacency"](garment.data)
    find_support = PRIOR["nearest_weights"]
    support = find_support(reference, body, samples[0][4], names, samples[0][2], links)
    patch_step = runpy.run_path(str(OUT / "search_patches.py"))["patch_step"]
    scans = []
    best = (float("inf"), "initial", points.copy(), weights.copy())

    def scan(label):
        nonlocal best
        d, pairs, contacts = R2["scan"](points, weights, faces, samples, transforms, collect=True)
        metrics = report_scan(label, samples, d, pairs)
        score = objective(d, pairs)
        passes = bool(d.min() >= TARGET and not pairs.any() and d[0].max() <= CAP)
        scans.append({"stage": label, "score": score, "clips": metrics, "all_pass": passes})
        if passes or score < best[0]:
            best = (score, label, points.copy(), weights.copy())
        return d, pairs, contacts, passes

    for i in range(3):
        d, pairs, (hits, _, _, _), passes = scan(f"coherent-{i}")
        if passes:
            break
        move, rebind = patch_step(FIT, points.copy(), weights.copy(), reference, names, support,
                                  links, faces, samples, transforms, d, pairs, hits)
        points += move
        weights += rebind

    support = find_support(points, body, samples[0][4], names, samples[0][2], links)
    for i in range(exact_passes + 1):
        d, pairs, (_, _, constraints, matrices), passes = scan(f"exact-{i}")
        if passes or i == exact_passes:
            break
        move, revised, _ = solve(points, weights, original_weights, links, matrices, transforms,
                                  constraints, .0013, 5.5)
        rows = np.array(representative_rows(samples, d, pairs, 21))
        points, weights = R3["refine_patches"](points, weights, reference, faces, samples, transforms,
                                               d, constraints, move, revised, support, rows, i + 6)

    _, stage, points, weights = best
    points, weights, preserved = restore_passing_clips(
        points, weights, reference, original_weights, faces, links, samples, transforms)
    if preserved and not preserved[-1]["vertices_below_floor"] and not preserved[-1]["triangle_pair_occurrences"]:
        stage += " with passing clips preserved"
    scans.append({"stage": "preserve passing clips", "passes": preserved})
    points, cuff_move = clear_jump_cuff(points, weights, faces, links, samples, transforms)
    if cuff_move:
        stage += " and jump cuff adjusted"
    scans.append({"stage": "jump cuff", "move_m": cuff_move})
    export_fit(garment, arm, body, names, points, weights, reference, original_weights, stage, scans)


def export_fit(garment, arm, body, names, points, weights, reference, original_weights, stage, scans):
    FIT["export_result"](garment, arm, body, names, points, weights)
    write_json("fit_history.json", {
        "source_glb_sha256": digest(SOURCE),
        "motion_sha256": digest(FIT["FIXED"]),
        "actions_sha256": digest(ACTIONS),
        "glb_sha256": digest(EXPORT),
        "selected_stage": stage,
        "target_m": TARGET,
        "rest_limit_m": CAP,
        "local_solve_margin_m": .0013,
        "rest_displacement_m": PRIOR["stats"](np.linalg.norm(points - reference, axis=1)),
        "edited_weights": int((abs(weights - original_weights).sum(axis=1) > .001).sum()),
        "stages": scans,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-passes", type=int, default=6)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    build(args.exact_passes)
