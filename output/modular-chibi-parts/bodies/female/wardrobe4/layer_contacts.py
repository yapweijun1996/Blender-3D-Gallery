"""Constraints from real intersections with the jacket's inner layers."""
import numpy as np
from mathutils.bvhtree import BVHTree

import fit_module as fit


class Layers:
    def __init__(self, assets, scene):
        self.trees = {}
        matrices = scene[4]
        for name, module in assets.items():
            points = module.source_points
            faces = module.source_faces
            if name == "jeans":
                faces = faces[points[faces, 2].max(axis=1) > .357]
            used, inverse = np.unique(faces, return_inverse=True)
            triangles = inverse.reshape(faces.shape)
            triangle_list = triangles.tolist()
            for start in range(0, len(matrices), 24):
                batch = slice(start, start + 24)
                skin = fit.GEOMETRY["pose_matrices"](matrices[batch], module.weights[used])
                posed = fit.GEOMETRY["skin_positions"](points[used], skin)
                for row, shape in zip(scene[3][batch], posed, strict=True):
                    tree = BVHTree.FromPolygons(shape.tolist(), triangle_list, all_triangles=True)
                    self.trees.setdefault(row[:2], []).append((tree, shape, triangles))
        print("LAYER_FIT", ", ".join(assets), len(self.trees), "frames", flush=True)

    def scan(self, posed, faces, rows, margin):
        garment_faces = faces.tolist()
        counts = np.zeros(len(rows), dtype=np.int32)
        constraints = []
        for i, (row, points) in enumerate(zip(rows, posed, strict=True)):
            garment = BVHTree.FromPolygons(points.tolist(), garment_faces, all_triangles=True)
            for tree, layer, triangles in self.trees[row[:2]]:
                pairs = tree.overlap(garment)
                counts[i] += len(pairs)
                if not pairs:
                    continue
                ordered = np.asarray(pairs, dtype=np.int32)
                if len(ordered) > 400:
                    order = np.lexsort((ordered[:, 0], ordered[:, 1]))
                    ordered = ordered[order]
                    _, first, count = np.unique(ordered[:, 1], return_index=True, return_counts=True)
                    ordered = ordered[first + count // 2]
                face_ids, bary = fit.SOURCE["pair_witnesses"](
                    points, faces, layer, triangles, ordered[:, ::-1])
                corners = faces[face_ids]
                surface = np.einsum("vi,vij->vj", bary, points[corners])
                signed, _, normals, _ = fit.nearest(tree, surface)
                order = np.lexsort((signed, face_ids))
                unique = order[np.r_[True, np.diff(face_ids[order]) != 0]]
                depth = np.minimum(signed[unique], margin * .2)
                for column in range(3):
                    eligible = bary[unique, column] >= .10
                    choose = unique[eligible]
                    if len(choose):
                        constraints.append((i, corners[choose, column], normals[choose], depth[eligible],
                                            .65 + .35 * bary[choose, column]))
        return counts, constraints
