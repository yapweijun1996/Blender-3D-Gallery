"""Clamp the skirt's radial loft against the posed lower-body envelope."""
import numpy as np
from mathutils.bvhtree import BVHTree

import fit_module as fit


def clamp(seed, weights, outward, data, rings, sides, center_y, margin, smooth=False):
    _, _, _, rows, transforms = data
    center = seed.copy()
    center[:, :2] = (0., center_y)
    radius = ((seed - center) * outward).sum(axis=1)
    # Cast from the outside toward the section axis. Use only rest-space
    # lower-body faces here so a passing hand cannot inflate the skirt.
    full_faces = rows[0][4]
    full_rest = rows[0][3]
    faces = full_faces[full_rest[full_faces, 2].min(axis=1) < .460].tolist()
    outer = .340
    for start in range(0, len(rows), 24):
        batch = slice(start, start + 24)
        skin = fit.GEOMETRY["pose_matrices"](transforms[batch], weights)
        pose_axes = np.einsum("fvij,vj->fvi", skin[..., :3], outward)
        pose_center = fit.GEOMETRY["skin_positions"](center, skin)
        starts = pose_center + outer * pose_axes
        scales = np.linalg.norm(pose_axes, axis=2)
        directions = -pose_axes / scales[..., None].clip(.05)
        for idx, (_, _, _, points, _) in enumerate(rows[batch]):
            tree = BVHTree.FromPolygons(points.tolist(), faces, all_triangles=True)
            distances = np.array([tree.ray_cast(a, b, outer * c)[3] or outer * c
                                  for a, b, c in zip(starts[idx].tolist(), directions[idx].tolist(),
                                                     scales[idx].tolist(), strict=True)])
            radius = np.maximum(radius, outer - distances / scales[idx] + margin)
    radius = radius.reshape(rings, sides)
    # Keep local maxima when easing the angular and vertical transitions.
    for _ in range(9):
        angular = (np.roll(radius, 1, axis=1) + np.roll(radius, -1, axis=1)) * .5
        vertical = np.vstack((radius[:1], radius[:-1])) * .5 + np.vstack((radius[1:], radius[-1:])) * .5
        radius = np.maximum(radius, .45 * radius + .35 * angular + .20 * vertical)
    if smooth:
        reflected = (sides // 2 - np.arange(sides)) % sides
        radius = np.maximum(radius, radius[:, reflected])
        low = np.fft.rfft(radius, axis=1)
        low[:, 6:] = 0
        regular = np.fft.irfft(low, n=sides, axis=1)
        radius = regular + np.maximum(0, (radius - regular).max(axis=1, keepdims=True))
        radius[5:] = np.maximum.accumulate(radius[5:], axis=0)
        vertical = .5 * (radius[:-2] + radius[2:])
        radius[1:-1] = np.maximum(radius[1:-1], .67 * radius[1:-1] + .33 * vertical)
    print("SKIRT_ENVELOPE max radius mm", round(float(radius.max() * 1000), 3), flush=True)
    return (center + outward * radius.reshape(-1, 1)).astype(np.float32)
