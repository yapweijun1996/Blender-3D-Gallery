"""Use the original T-shirt contact solver with female pose and triangle witnesses."""
import json
from pathlib import Path
import runpy
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import fit_module as fit
from refit import assess, read_pose_bank, scan_in_batches, preserve_images, limit
from sleeve_clearance import sample_bank


def gather_witnesses(points, triangles, posed, rows):
    contacts = []
    pairs_at = np.zeros(len(rows), dtype=np.int32)
    d_at = np.empty((len(rows), len(points)), dtype=np.float32)
    for i, ((_, _, tree, body, body_faces), coords) in enumerate(zip(rows, posed, strict=True)):
        d, _, normals, _ = fit.nearest(tree, coords)
        d_at[i] = d
        vertices = np.flatnonzero(d < .00165)
        indices = np.repeat(vertices[:, None], 3, axis=1)
        bary = np.zeros(indices.shape, dtype=np.float32)
        bary[:, 0] = 1
        directions, signed = normals[vertices], d[vertices]
        pairs = np.asarray(tree.overlap(fit.tree_from(coords, triangles)), dtype=np.int32).reshape(-1, 2)
        pairs_at[i] = len(pairs)
        if len(pairs):
            face, coeff = fit.SOURCE["pair_witnesses"](coords, triangles, body, body_faces, pairs[:, ::-1], dense=False)
            locations = np.einsum("vi,vix->vx", coeff, coords[triangles[face]])
            depths, _, outward, _ = fit.nearest(tree, locations)
            ordered = np.lexsort((depths, face))
            lowest = ordered[np.r_[True, np.diff(face[ordered]) != 0]]
            lowest = lowest[depths[lowest] < .0015]
            indices = np.concatenate((indices, triangles[face[lowest]]))
            bary = np.concatenate((bary, coeff[lowest]))
            directions = np.concatenate((directions, outward[lowest]))
            signed = np.concatenate((signed, depths[lowest]))
        if len(indices):
            contacts.append((i, indices, bary, directions, signed))
    return contacts, d_at, pairs_at


def run():
    legacy = runpy.run_path(str(fit.PARTS / "studio-modules/tshirt/round5/fit_tshirt_r5.py"))
    names, _, female, rows, matrices = read_pose_bank()
    path = ROOT / "female-tshirt-v2.glb"
    record_path = path.with_suffix(".fit.json")
    record = json.loads(record_path.read_text())
    origin = fit.Module(ROOT / ".runtime/female-tshirt.glb", names)
    current = fit.Module(path, names)
    assert np.array_equal(origin.source_faces, current.source_faces)
    points = origin.welded(current.source_points).astype(np.float32)
    reference = origin.points.copy()
    weights = current.weights.copy()

    score, result = assess(origin, points, weights, rows, matrices)
    samples, transforms = sample_bank(result, rows, matrices)
    base_score = fit.score(scan_in_batches(origin, points, weights, samples, transforms))
    common_weights = fit.limit_weights(origin.welded(weights).astype(np.float32))
    joint_field = fit.GEOMETRY["pose_matrices"](transforms, common_weights)
    poses = fit.GEOMETRY["skin_positions"](points, joint_field)
    contacts, distances, overlaps = gather_witnesses(points, origin.faces, poses, samples)
    print("COUPLED WITNESSES", len(contacts), int(overlaps.sum()), float(distances.min()), flush=True)
    active = np.zeros(len(points), dtype=np.float32)
    active[origin.faces[result[2] > 0].ravel()] = 1
    active[origin.unweld[result[0].min(axis=0) < .0008]] = 1
    for _ in range(5):
        active = np.maximum(active, .92 * fit.average(active, origin.graph))

    output_candidates = []
    for binding in (0., 5.5, 9.):
        step, next_skin, initial = legacy["solve"](points, common_weights, common_weights, origin.graph,
            joint_field, transforms, contacts, fit.MARGIN, binding)
        for gain in (.30, .63, 1.):
            shape = reference + limit(points + gain * step - reference, fit.CAP)
            skin = fit.limit_weights(np.maximum(0., weights + (gain * active[:, None] * (next_skin-common_weights))[origin.unweld]))
            skin[active[origin.unweld] == 0] = weights[active[origin.unweld] == 0]
            metrics = scan_in_batches(origin, shape, skin, samples, transforms)
            objective = fit.score(metrics)
            print("COUPLED TRIAL", binding, gain, objective, "/", base_score, flush=True)
            if objective < base_score:
                output_candidates.append((objective, binding, gain, shape, skin))

    for _, binding, gain, candidate, skin in sorted(output_candidates, key=lambda item: item[0])[:2]:
        value, checked = assess(origin, candidate, skin, rows, matrices)
        if value >= score:
            continue
        preserve_images(origin)
        origin.write(path, candidate, skin)
        record.update(output_sha256=fit.sha(path), max_baked_clearance_offset_m=float(np.linalg.norm(candidate-reference, axis=1).max()))
        record["history"].append(dict(iteration=record["history"][-1]["iteration"] + 1, score=value,
            method="coupled vertex and triangle witness bake", binding=binding, gain=gain,
            results=fit.summary(origin, checked, rows, female)))
        record_path.write_text(json.dumps(record, indent=2) + "\n")
        break


if __name__ == "__main__":
    run()
