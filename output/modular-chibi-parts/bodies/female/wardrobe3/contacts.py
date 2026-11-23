"""Locate repeat contacts at the arm-to-torso crease of a prior shell."""
import numpy as np
from mathutils.bvhtree import BVHTree

import fit_module as fit
from gate_module import pose


def underarm(path, report, data):
    names, _, _, rows, transforms = data
    module = fit.Module(path, names)
    polys = module.source_faces.tolist()
    centers = module.source_points[module.source_faces].mean(axis=1)
    vertices = abs(centers[:, 0])
    eligible = (vertices > .043) & (vertices < .150) & (centers[:, 2] < .556)
    eligible &= (centers[:, 2] > .452) & (centers[:, 1] > -.066)
    samples = []
    for clip, result in report["clips"].items():
        risky = sorted(result["frames"], key=lambda v: (v["pairs"], v["inside"], -v["min_signed_mm"]),
                       reverse=True)[:18]
        samples.extend((clip, row["frame"]) for row in risky if row["pairs"])
    selected = set(samples)
    indices = [i for i, row in enumerate(rows) if row[:2] in selected]
    poses = pose(module, transforms[indices])
    touched = np.zeros(len(centers), dtype=bool)
    for i, points in zip(indices, poses, strict=True):
        tree = BVHTree.FromPolygons(points.tolist(), polys, all_triangles=True)
        pairs = rows[i][2].overlap(tree)
        if pairs:
            touched[np.asarray(pairs)[:, 1]] = True
    hits = centers[touched & eligible]
    print("UNDERARM_CONTACTS", path.name, len(hits), "source face centers", flush=True)
    return hits


def finish_vents(item, points, surface, faces, weights, colors, unsafe):
    """Open the rest-space vent along the remaining underarm contacts."""
    x, y, z = surface[faces].mean(axis=1).T
    eligible = (abs(x) > .045) & (abs(x) < .146) & (z > .448) & (z < .556) & (y > -.072)
    if item == "shorts":
        # A short opening inside the split hem relieves the curved inseam.
        eligible = (abs(x) < .023) & (z < .337) & (y > -.066) & (y < .027)
    drop = unsafe & eligible
    if not drop.any() or drop.sum() > .10 * len(faces):
        return points, faces, weights, colors, 0
    # Extend into adjacent vent faces so the cut reads as a seam.
    connected = np.zeros(len(points), dtype=bool)
    connected[faces[drop].ravel()] = True
    drop |= eligible & (connected[faces].sum(axis=1) >= 2)
    retained = faces[~drop]
    used, relabeled = np.unique(retained, return_inverse=True)
    trim = colors[~drop].copy()
    trim[connected[retained].sum(axis=1) >= 2] = 2 if item == "shorts" else 1
    return points[used], relabeled.reshape(-1, 3), weights[used], trim, int(drop.sum())
