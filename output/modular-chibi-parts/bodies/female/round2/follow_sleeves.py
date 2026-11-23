"""Fit the existing shirt armhole vertices to a collision-checked sleeve trajectory."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import fit_module as fit
from refit import assess, read_pose_bank, preserve_images, scan_in_batches, smoothstep, limit
from common import arguments


def corresponding_surface(module, guide, points, sources, margin):
    tree = fit.tree_from(guide.source_points, guide.source_faces)
    normals = fit.normalized(module.welded(module.surface_normals(points[module.unweld])))
    locations, hit_normals, face_ids, kept = [], [], [], []
    for index in sources:
        point = points[index]
        hits = [(q, n, f, d, np.dot(normals[index], n)) for q, n, f, d in tree.find_nearest_range(point, .037)]
        valid = [value for value in hits if value[4] >= .08]
        if not valid:
            continue
        q, n, face, _, alignment = min(valid, key=lambda row: row[3] + .011 * (1 - row[4]))
        locations.append(q)
        hit_normals.append(np.asarray(n) * (margin * max(.25, alignment)))
        face_ids.append(face)
        kept.append(index)
    corners = guide.source_faces[face_ids]
    bary = fit.barycentric(guide.source_points[corners], np.asarray(locations))
    return np.asarray(kept), corners, bary, np.asarray(locations) + np.asarray(hit_normals), np.asarray(hit_normals)


def follow_guide(guide, corners, bary, positions, relief, transforms):
    """Alternate a bind-position solve and a simplex-projected skin solve."""
    weights = guide.weights[corners]
    guess = np.einsum("vi,vij->vj", bary, weights).astype(np.float32)
    columns = np.argsort(-guess, axis=1, kind="stable")[:, :4]
    full = np.empty((len(positions), len(guide.names)), dtype=np.float32)
    matched = positions.copy()
    simplex = fit.SOURCE["simplex"]
    for start in range(0, len(positions), 32):
        sl = slice(start, start + 32)
        vertices = corners[sl]
        dense_weights = weights[sl].reshape(-1, len(guide.names))
        old_matrices = fit.GEOMETRY["pose_matrices"](transforms, dense_weights)
        endpoints = fit.GEOMETRY["skin_positions"](guide.source_points[vertices].reshape(-1, 3), old_matrices)
        target = np.einsum("vi,fvik->fvk", bary[sl], endpoints.reshape(len(transforms), -1, 3, 3))
        geom = transforms[:, columns[sl], :, :]
        rotations = geom[..., :3]
        translation = geom[..., 3]
        w0 = np.take_along_axis(guess[sl], columns[sl], axis=1)
        w0 /= w0.sum(axis=1, keepdims=True)
        w = w0.copy()
        point = positions[sl].copy()
        target += np.einsum("vj,fvjik,vk->fvi", w, rotations, relief[sl])
        for _ in range(3):
            site = np.einsum("fvjik,vk->fvji", rotations, point) + translation
            derivative = site - site.mean(axis=2, keepdims=True)
            gram = np.einsum("fvji,fvli->vjl", derivative, derivative)
            step = .87 / np.abs(gram).sum(axis=2).max(axis=1).clip(1.e-8)
            for _ in range(35):
                error = np.einsum("vj,fvji->fvi", w, site) - target
                gradient = np.einsum("fvji,fvi->vj", derivative, error)
                w = simplex(w - step[:, None] * (gradient + .00015 * (w - w0)))
            matrix = np.einsum("vj,fvjik->fvik", w, rotations)
            offset = np.einsum("vj,fvji->fvi", w, translation)
            system = np.einsum("fvik,fvil->vkl", matrix, matrix)
            rhs = np.einsum("fvik,fvi->vk", matrix, target - offset)
            point = np.linalg.solve(system, rhs[..., None])[..., 0]
        stored = np.zeros((len(w), full.shape[1]), dtype=np.float32)
        np.put_along_axis(stored, columns[sl], w, axis=1)
        full[sl] = stored
        matched[sl] = point
    return matched, full


def run(margin):
    names, _, female, rows, matrices = read_pose_bank()
    path = ROOT / "female-tshirt-v2.glb"
    record_path = path.with_suffix(".fit.json")
    record = json.loads(record_path.read_text())
    base = fit.Module(ROOT / ".runtime" / "female-tshirt.glb", names)
    existing = fit.Module(path, names)
    reference = fit.Module(ROOT / "female-dress-v2.glb", names)
    assert np.array_equal(base.source_faces, existing.source_faces)
    origin = base.points.copy()
    points = base.welded(existing.source_points).astype(np.float32)
    weights = existing.weights.copy()
    value, result = assess(base, points, weights, rows, matrices)

    risk = np.zeros(len(points), dtype=np.float32)
    risk[base.unweld[result[0].min(axis=0) < .00075]] = 1
    risk[base.faces[result[2] > 0].ravel()] = 1
    for _ in range(10):
        risk = np.maximum(risk, .97 * fit.average(risk, base.graph))
    x, _, z = points.T
    region = smoothstep(.040, .065, abs(x)) * smoothstep(.442, .475, z) * (1 - smoothstep(.556, .585, z))
    support = np.maximum(np.where(risk >= .99, 1., .70 * risk), .72 * region)
    candidates, corners, bary, mapped, outward = corresponding_surface(
        base, reference, points, np.flatnonzero(support > .045), margin)
    penalties = result[1] + (result[0] < .0005).sum(axis=1)
    sample_indices = set(range(0, len(rows), 13))
    for clip in {row[0] for row in rows}:
        ids = np.array([i for i, row in enumerate(rows) if row[0] == clip])
        sample_indices.update(ids[np.argsort(-penalties[ids])[:5]])
    ids = np.asarray(sorted(sample_indices))
    bank, transforms = [rows[i] for i in ids], matrices[ids]
    mapped, mapped_skin = follow_guide(reference, corners, bary, mapped, outward, transforms)
    matches = points.copy()
    matches[candidates] = mapped
    replacement = base.welded(weights).astype(np.float32)
    replacement[candidates] = mapped_skin
    changed = np.zeros(len(points), dtype=np.float32)
    changed[candidates] = support[candidates]
    ranked = []
    for factor in (.56, .78, 1.):
        w = (factor * changed)[base.unweld, None]
        skin = fit.limit_weights(((1 - w) * weights + w * replacement[base.unweld]).astype(np.float32))
        delta = factor * changed[:, None] * (matches - points)
        shape = origin + limit(points + delta - origin, fit.CAP)
        score = fit.score(scan_in_batches(base, np.asarray(shape, dtype=np.float32), skin, bank, transforms))
        print("SLEEVE TRAJECTORY", factor, float(score), flush=True)
        ranked.append((score, factor, shape, skin))
    _, factor, candidate, weighted = min(ranked, key=lambda v: v[0])
    score, metrics = assess(base, candidate, weighted, rows, matrices)
    if score >= value:
        return
    preserve_images(base)
    base.write(path, candidate, weighted)
    record.update(output_sha256=fit.sha(path), max_baked_clearance_offset_m=float(np.linalg.norm(candidate-origin, axis=1).max()))
    record["history"].append(dict(iteration=record["history"][-1]["iteration"] + 1, score=score,
        method="fitted sleeve trajectories", blend=factor, guide_margin_m=margin,
        results=fit.summary(base, metrics, rows, female)))
    record_path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    args = arguments()
    run(float(args[0]) if args else .0018)
