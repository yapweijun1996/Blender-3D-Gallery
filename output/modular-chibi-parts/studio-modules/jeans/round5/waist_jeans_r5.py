"""Recover the shipped round-3 weighting around the rear waistband seam."""

import argparse
from itertools import product
import json
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REFINE = runpy.run_path(str(HERE / "refine_jeans_r5.py"))
FIT, PRIOR = REFINE["FIT"], REFINE["PRIOR"]
gaps, measure = REFINE["gaps"], REFINE["measure"]


def uv_keys(mesh):
    coords = np.empty(2 * len(mesh.loops), dtype=np.float32)
    mesh.uv_layers.active.uv.foreach_get("vector", coords)
    vertices = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", vertices)
    keys = [set() for _ in mesh.vertices]
    for index, uv in zip(vertices, np.rint(1e6 * coords.reshape(-1, 2)).astype(int)):
        keys[index].add(tuple(uv))
    return [tuple(sorted(uv)) for uv in keys]


def source_correspondence(garment, names, points, ids):
    original = PRIOR["import_garment"](FIT["BASE"], merge=False)
    source_points, _ = FIT["mesh_arrays"](original.data)
    source_weights = FIT["read_weights"](original, names)
    by_uv = {}
    for i, key in enumerate(uv_keys(original.data)):
        by_uv.setdefault(key, []).append(i)
    keys = uv_keys(garment.data)
    matched = []
    for index in ids:
        candidates = by_uv.get(keys[index], [])
        if not candidates:
            distances = np.linalg.norm(source_points - points[index], axis=1)
            candidates = np.argsort(distances)[:1].tolist()
        idx = min(candidates, key=lambda i: np.linalg.norm(source_points[i] - points[index]))
        matched.append(idx)
    bpy.data.objects.remove(original, do_unlink=True)
    return source_points[matched], source_weights[matched]


def rank(distances, pairs, rest=None):
    d = distances.min(axis=1)
    hard = int(d[0] < .0005 or (rest is not None and rest.max() > .03) or len(pairs[0]) > 0)
    return (hard, sum(map(len, pairs)) + 4 * int((d < .0005).sum()),
            int((d < .00064).sum()), float(np.maximum(0, .00064 - d).sum()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=FIT["GLB"])
    parser.add_argument("--trial", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    scene, arm, body, garment = FIT["setup"](args.input.resolve())
    points, faces = FIT["mesh_arrays"](garment.data)
    names = [bone.name for bone in arm.pose.bones]
    weights = FIT["read_weights"](garment, names)
    center = np.array((-.015, .0635, .426), dtype=np.float32)
    proximity = np.linalg.norm(points - center, axis=1)
    affected = np.flatnonzero(proximity < .027)
    face_ids = np.flatnonzero(np.isin(faces, affected).any(axis=1))
    local, inverse = np.unique(faces[face_ids], return_inverse=True)
    face_map = inverse.reshape(-1, 3)
    p0, w0 = points[local], weights[local]
    ps, ws = source_correspondence(garment, names, points, local)
    print("WAIST CORRESPONDENCE", len(local), "max offset mm",
          float(np.linalg.norm(p0 - ps, axis=1).max() * 1000), flush=True)

    names, samples, transforms, posed = REFINE["sample_export"](scene, arm, body, garment)
    base = posed[:, local]
    all_orig = FIT["skin_positions"](p0, FIT["skin_matrices"](transforms, w0))
    distances, pairs = measure(samples, base, face_map)
    initial = rank(distances, pairs, distances[0])
    mandatory = [i for i, (d, pairs) in enumerate(zip(distances, pairs))
                 if d.min() < .00065 or pairs]
    cover = np.unique(np.r_[0, mandatory, np.arange(0, len(samples), 14)]).astype(int)
    test_samples = [samples[i] for i in cover]
    print("WAIST START", initial, len(mandatory), "critical poses", len(cover), flush=True)
    winners = []
    rest_tree = samples[0][2]
    smoothstep = PRIOR["smoothstep"]
    deltas = (np.zeros(3), (.0007, .0007, 0.), (-.0007, .0007, 0.),
              (0., .0013, .0008), (0., .0014, -.0007), (0., -.0010, 0.),
              (0., .0026, .001), (0., 0., .0015))
    original_options = list(product((.006, .010, .015), (0., .5, 1.), (.40, .70, 1.), deltas))
    for serial, (radius, geometry, skin, delta) in enumerate(original_options):
        support = (1 - smoothstep(radius, radius + .010, proximity[local]))[:, None]
        p = p0 + support * (geometry * (ps - p0) + delta)
        w = FIT["limit_weights"](w0 + skin * support * (ws - w0))
        rest = gaps(rest_tree, p)
        if rest.min() < .00062 or rest.max() > .02998:
            continue
        rest_faces = p[face_map]
        n0 = np.cross(p0[face_map[:, 1]] - p0[face_map[:, 0]], p0[face_map[:, 2]] - p0[face_map[:, 0]])
        n = np.cross(rest_faces[:, 1] - rest_faces[:, 0], rest_faces[:, 2] - rest_faces[:, 0])
        a0, a = np.linalg.norm(n0, axis=1), np.linalg.norm(n, axis=1)
        if (((n * n0).sum(axis=1) < .20 * a0 * a) & (a0 > 5e-8)).any():
            continue
        linear = FIT["skin_matrices"](transforms[cover], w)
        check_pose = base[cover] + FIT["skin_positions"](p, linear) - all_orig[cover]
        cd, cp = measure(test_samples, check_pose, face_map)
        value = rank(cd, cp, rest)
        winners.append((value, serial, p, w, (radius, geometry, skin, list(delta))))
        if (value == (0, 0, 0, 0) and sum(x[0] == value for x in winners) >= 5):
            break
    winners.sort(key=lambda row: (row[0], row[1]))
    print("WAIST COARSE", [(x[0], x[-1]) for x in winners[:5]], flush=True)
    chosen, best = None, initial
    for coarse, _, p, w, parameters in winners[:20]:
        if coarse > best:
            break
        new = base + FIT["skin_positions"](p, FIT["skin_matrices"](transforms, w)) - all_orig
        d, intersections = measure(samples, new, face_map)
        score = rank(d, intersections, d[0])
        print("WAIST CANDIDATE", parameters, score, flush=True)
        if score < best:
            chosen, best = (p, w, parameters), score
            if not any(best):
                break
    if chosen is None:
        return
    p, w, parameters = chosen
    points[local], weights[local] = p, w
    if args.trial:
        FIT["save_fit"].__globals__.update(GLB=HERE / ".waist.glb", BLEND=HERE / ".waist.blend")
    FIT["save_fit"](arm, body, garment, points, weights, names)
    path = HERE / ("waist_trial.json" if args.trial else "fit_history.json")
    hist = json.loads(path.read_text()) if path.exists() else {}
    hist.setdefault("rear_waistband", []).append({
        "input_sha256": FIT["sha256"](args.input), "before": initial, "after": best,
        "support_parameters": parameters, "vertices": len(local),
    })
    path.write_text(json.dumps(hist, indent=2) + "\n")


if __name__ == "__main__":
    main()
