"""Try bounded local relief fields when the full-bank clearance solver stalls."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_module import (CAP, GATE, HERE, MODULES, PARTS, SOURCE, Module, cache_scene, nearest, normalized,
                        scan, score, seed_shape, sha, summary, protect_style)
from common import arguments


def selected_rows(result, all_rows):
    distances, pairs = result[:2]
    severity = (distances < GATE).sum(axis=1) + 4 * pairs + 1600 * np.maximum(0, GATE - distances).sum(axis=1)
    rows = {0}
    for name in set(s[0] for s in all_rows):
        group = np.flatnonzero([s[0] == name for s in all_rows])
        for r in group[np.argsort(-severity[group])[:7]]:
            if severity[r] > 0:
                rows.update({int(r), max(group[0], int(r)-1), min(group[-1], int(r)+1)})
    rows.update(range(0, len(all_rows), 32))
    return np.array(sorted(rows))


def patch_centers(module, result, budget=7):
    d, _, hits, *_ = result
    depth = np.maximum(0, GATE - d.min(axis=0))
    priorities = depth.copy()
    for column in module.source_faces.T:
        np.add.at(priorities, column, .00014 * np.minimum(30, hits))
    work = priorities.copy()
    result = []
    for _ in range(budget):
        i = int(work.argmax())
        if work[i] == 0:
            break
        result.append(i)
        near = np.linalg.norm(module.source_points - module.source_points[i], axis=1) < .010
        work[near] = 0
    return result


def local_trial(module, seed, start, current_weights, result, full_rows, transforms, full_bank=False):
    chosen = np.arange(len(full_rows)) if full_bank else selected_rows(result, full_rows)
    rows, matrices = [full_rows[i] for i in chosen], transforms[chosen]
    _, _, normal, _ = nearest(rows[0][2], start)
    points = start.copy()
    tiny = full_bank and score(result) < 15
    for vertex in patch_centers(module, result, budget=5 if full_bank else 7):
        welded = module.unweld[vertex]
        position = points[welded]
        radius = .019 if tiny else .014
        rest_spacing = np.linalg.norm(module.points - module.points[welded], axis=1)
        support = np.exp(-np.square(rest_spacing / radius))[:, None].astype(np.float32)
        patch = support >= .008
        basis = np.concatenate([np.eye(3), -np.eye(3), normal[welded, None], -normal[welded, None]])
        touching = np.any(patch[module.faces].squeeze(-1), axis=1)
        one_ring = np.unique(module.faces[touching])
        affected = np.isin(module.faces, one_ring).any(axis=1)
        triangles = module.source_faces[affected]
        active, remap = np.unique(triangles, return_inverse=True)
        local = SimpleNamespace(unweld=module.unweld[active],
                                source_faces=remap.reshape(-1, 3).astype(np.int32))
        partial_weights = current_weights[active]
        value = score(scan(local, points, partial_weights, rows, matrices))
        best = value, points
        offsets = (.18, .35, .65, 1.1) if tiny else ((1., 2., 3.6) if full_bank else (1.3, 3.1, 5.5, 8.))
        for offset_mm in offsets:
            for axis in basis:
                push = np.where(patch, .001 * offset_mm * support * axis, 0)
                candidate = seed + SOURCE["limit_delta"](points + push - seed, CAP)
                candidate = protect_style(module, points, candidate)
                metrics = scan(local, candidate, partial_weights, rows, matrices)
                trial = score(metrics)
                if trial < best[0]:
                    best = trial, candidate
                if trial == 0:
                    break
            if best[0] < value * .93:
                break
        if best[0] < value:
            print("LOCAL REGION", vertex, position, value, "->", best[0], flush=True)
            value, points = best
    return points


def polish(name, data, full_bank=False):
    names, neutral, female, rows, transforms = data
    source = PARTS / MODULES[name][0]
    output = HERE / f"female-{name}.glb"
    current_record = json.loads(output.with_suffix(".fit.json").read_text())
    module = Module(source, names)
    current = Module(output, names)
    seed, _ = seed_shape(module, neutral, female, rows[0][2])
    points = module.welded(current.source_points).astype(np.float32)
    weights = current.weights.copy()
    initial = scan(module, points, weights, rows, transforms)
    print("LOCAL START", name, score(initial), flush=True)
    for iteration in range(1 if full_bank else 2):
        moved = local_trial(module, seed, points, weights, initial, rows, transforms, full_bank)
        final = scan(module, moved, weights, rows, transforms)
        print("LOCAL FULL", name, score(initial), "->", score(final), flush=True)
        if score(final) >= score(initial):
            break
        images = module.write(output, moved, weights)
        report = summary(module, final, rows, female)
        current_record.update(output_sha256=sha(output), bytes=output.stat().st_size, texture_images=images,
                              max_clearance_offset_m=float(np.linalg.norm(moved-seed, axis=1).max()), results=report)
        history = current_record["history"]
        history.append(dict(iteration=history[-1]["iteration"] + 1, score=score(final), results=report,
                            method="localized signed-distance search"))
        output.with_suffix(".fit.json").write_text(json.dumps(current_record, indent=2) + "\n")
        if score(final) == 0:
            break
        points, initial = moved, final


if __name__ == "__main__":
    data = cache_scene()
    full_bank = "--full-local" in arguments()
    for item in (s for s in arguments() if s != "--full-local"):
        polish(item, data, full_bank)
