"""Clip and measure body-derived garment panels."""
import numpy as np


PALETTES = {
    'top-hoodie': ((.035,.24,.21), (.016,.104,.086), (.105,.40,.29)),
    'top-jacket': ((.24,.078,.033), (.088,.027,.014), (.51,.23,.075)),
    'bottom-shorts': ((.035,.087,.17), (.015,.039,.081), (.10,.20,.30)),
    'bottom-skirt': ((.17,.052,.15), (.072,.025,.066), (.28,.075,.21)),
}


def unit(vector):
    return vector / np.maximum(np.linalg.norm(vector, axis=1, keepdims=True), 1.e-10)


def cut(points, faces, skin, mask):
    """Clip the triangulated body against an interpolated vertex mask."""
    vertices, indices, weights, cache = [], [], [], {}
    for face in faces:
        if mask[face].max() < 0:
            continue
        polygon = []
        for a, b in zip(face, np.roll(face, -1)):
            edges = []
            if mask[a] >= 0:
                edges.append((a, a))
            if (mask[a] >= 0) != (mask[b] >= 0):
                edges.append(tuple(sorted((a, b))))
            for key in edges:
                if key not in cache:
                    i, j = key
                    t = 0. if i == j else mask[i] / (mask[i] - mask[j])
                    cache[key] = len(vertices)
                    vertices.append(points[i] + t * (points[j] - points[i]))
                    weights.append(skin[i] + t * (skin[j] - skin[i]))
                polygon.append(cache[key])
        indices.extend((polygon[0], polygon[i], polygon[i+1]) for i in range(1, len(polygon)-1))
    if not indices:
        raise ValueError('The panel cut produced no triangles.')
    p, first, inverse = np.unique(np.round(vertices, 7), axis=0, return_index=True, return_inverse=True)
    f = inverse[np.array(indices)]
    keep = np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]], p[f[:,2]]-p[f[:,0]]),axis=1) > 1.e-10
    f = f[keep]
    used, remap = np.unique(f,return_inverse=True)
    return p[used], remap.reshape(-1,3), np.array(weights)[first[used]]


def normals(p, f):
    n = np.zeros_like(p)
    vectors = np.cross(p[f[:,1]]-p[f[:,0]], p[f[:,2]]-p[f[:,0]])
    for i in range(3):
        np.add.at(n, f[:,i], vectors)
    return unit(n)
