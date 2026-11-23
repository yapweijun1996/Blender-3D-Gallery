"""Bake a local, capped offset around the remaining triangulated sleeve contacts."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import fit_module as fit
from common import CLIPS
from refit import assess, bake_offset, limit, preserve_images, read_pose_bank, scan_in_batches, smoothstep, solve_skin_contacts


def sample_bank(result, rows, matrices):
    selected = set(range(0, len(rows), 26))
    distances, pairs = result[:2]
    priority = pairs + 4 * (distances < .00055).sum(axis=1)
    for name in ("rest", *CLIPS):
        indices = np.flatnonzero([row[0] == name for row in rows])
        peak = indices[np.argsort(-priority[indices])[:6]]
        selected.update(peak)
        selected.update(np.clip(peak - 1, indices[0], indices[-1]))
        selected.update(np.clip(peak + 1, indices[0], indices[-1]))
    ids = sorted(selected)
    return [rows[i] for i in ids], matrices[ids]


def localized_choices(module, points, origin, weights, result, tree, matrices):
    risk = np.zeros(len(points), dtype=np.float32)
    risk[module.faces[result[2] > 0].ravel()] = 1
    risk[module.unweld[result[0].min(axis=0) < .0007]] = 1
    for _ in range(8):
        risk = np.maximum(risk, .93 * fit.average(risk, module.graph))
    x, y, z = points.T
    sleeve = smoothstep(.056, .078, abs(x)) * smoothstep(.457, .490, z) * (1 - smoothstep(.542, .575, z))
    cloth = fit.normalized(module.welded(module.surface_normals(points[module.unweld])))
    body = fit.nearest(tree, points)[2]
    outward = fit.normalized(np.c_[.18 * np.sign(x), np.tanh((y + .030) / .012), np.full(len(x), .21)])
    options = []
    for description, directions in (("panel", outward), ("cloth", cloth), ("body", body)):
        for offset in (.0016, .0034, .0056):
            strength = offset * np.maximum(risk, .36 * sleeve)
            step = strength[:, None] * directions
            for _ in range(3):
                step += .18 * (fit.average(step, module.graph) - step)
            options.append((points + step, weights, f"{description} {offset:.4f}"))
    fair = points.copy()
    blend_mask = np.maximum(risk, .60 * sleeve)
    for _ in range(6):
        fair += .22 * blend_mask[:, None] * (fit.average(fair, module.graph) - fair)
    skin_field = module.welded(weights).astype(np.float32)
    for _ in range(3):
        skin_field += .18 * blend_mask[:, None] * (fit.average(skin_field, module.graph) - skin_field)
    smoothed_skin = fit.limit_weights(skin_field[module.unweld])
    smoothed_skin[blend_mask[module.unweld] == 0] = weights[blend_mask[module.unweld] == 0]
    for offset in (.0014, .0030, .0048):
        options.append((fair + offset * blend_mask[:, None] * outward, smoothed_skin, f"armhole smoothing {offset:.4f}"))

    baked = bake_offset(module, result, points, origin)
    joint_shape, joint_weights = solve_skin_contacts(module, points, origin, weights, result, matrices)
    for step in (.33, .66):
        options.append((points + step * (baked - points), weights, f"offset {step}"))
        skin = fit.limit_weights(((1 - step) * weights + step * joint_weights).astype(np.float32))
        options.append((points + step * (joint_shape - points), skin, f"joint {step}"))
    return options


def run():
    names, _, female, rows, matrices = read_pose_bank()
    output = ROOT / "female-tshirt-v2.glb"
    trace_path = output.with_suffix(".fit.json")
    trace = json.loads(trace_path.read_text())
    base = fit.Module(ROOT / ".runtime" / "female-tshirt.glb", names)
    fitted = fit.Module(output, names)
    assert np.array_equal(base.source_faces, fitted.source_faces)
    origin = base.points
    points = base.welded(fitted.source_points).astype(np.float32)
    weights = fitted.weights
    value, result = assess(base, points, weights, rows, matrices)
    samples, transforms = sample_bank(result, rows, matrices)
    baseline = fit.score(scan_in_batches(base, points, weights, samples, transforms))
    ranked = []
    for shape, skin, method in localized_choices(base, points, origin, weights, result, rows[0][2], matrices):
        shape = np.asarray(origin + limit(shape - origin, fit.CAP), dtype=np.float32)
        metrics = scan_in_batches(base, shape, skin, samples, transforms)
        score = fit.score(metrics)
        print("SLEEVE RELIEF", method, round(score, 3), "/", round(baseline, 3), flush=True)
        if score < baseline:
            ranked.append((score, shape, skin, method))
    best = value, points, weights
    for _, shape, skin, method in sorted(ranked, key=lambda item: item[0])[:2]:
        score, checked = assess(base, shape, skin, rows, matrices)
        if score >= best[0] or checked[0].min() < result[0].min() - .0007:
            continue
        best = score, shape, skin
        preserve_images(base)
        base.write(output, shape, skin)
        trace.update(output_sha256=fit.sha(output), max_baked_clearance_offset_m=float(np.linalg.norm(shape - origin, axis=1).max()))
        trace["history"].append(dict(iteration=trace["history"][-1]["iteration"] + 1, score=score,
                                     method=method, results=fit.summary(base, checked, rows, female)))
        trace_path.write_text(json.dumps(trace, indent=2) + "\n")
        if not checked[1].any() and checked[0].min() >= .00053:
            break


if __name__ == "__main__":
    run()
