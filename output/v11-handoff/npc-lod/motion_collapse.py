"""Use the corrected poses to reject garment edge collapses that cross the body."""
import json
from pathlib import Path
import sys

from mathutils.bvhtree import BVHTree
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_npc import (LIMITS, SOURCE, WORK, Decimator, export_mesh, load_mesh, read_mesh,
                       rebuild, smooth_weights, topology)
from fit_motion import cache_motion, pose_matrices, posed_points


class MotionGuard:
    def __init__(self, poses, frames, faces, tshirt):
        self.poses = poses
        self.frames = frames
        self.faces = faces
        self.checked = self.rejected = 0
        self.clearance = []
        self.tshirt = tshirt
        for frame, xyz in zip(frames, poses, strict=True):
            self.clearance.append([frame.tree.find_nearest(v)[3] for v in xyz])
        self.clearance = np.asarray(self.clearance, dtype=np.float32)

    def __call__(self, removed, changed):
        self.checked += 1
        ids, lookup = np.unique([f.vertices for f in changed.values()], return_inverse=True)
        cells = lookup.reshape(-1, 3)
        verts = self.poses[:, ids]
        tri = verts[:, cells]
        # A vertex farther from the body than either of its edges certifies
        # the whole triangle clear, without a per-frame BVH intersection query.
        edges = np.linalg.norm(tri - np.roll(tri, -1, axis=2), axis=3)
        radius = np.maximum(edges, np.roll(edges, 1, axis=2))
        may_touch = np.all(self.clearance[:, ids[cells]] <= radius + .000001, axis=2)
        for row in np.flatnonzero(may_touch.any(axis=1)):
            frame = self.frames[row]
            cells_f = cells[may_touch[row]]
            new_tree = BVHTree.FromPolygons(verts[row].tolist(), cells_f.tolist(), all_triangles=True)
            hits = len(frame.tree.overlap(new_tree))
            if not hits:
                continue
            if self.tshirt and frame.clip in {'walk','run','dance','sit_down','sit_idle','stand_up','hold_item'}:
                initial = [self.faces[j].vertices for j in changed]
                base = BVHTree.FromPolygons(self.poses[row].tolist(), initial, all_triangles=True)
                if len(frame.tree.overlap(base)) >= hits:
                    continue
            self.rejected += 1
            return False
        return True


class ShoeLayerGuard:
    """Keep the fitted 1.2 mm inset lining behind the outer shoe shell."""
    def __init__(self, points, faces):
        self.points = points
        self.coordinates = points.tolist()
        self.faces = faces
        self.rejected = 0

    def __call__(self, removed, changed):
        for lining in (False, True):
            additions = [f.vertices for f in changed.values() if (f.material == 3) == lining]
            if not additions:
                continue
            other = [changed.get(j, face).vertices for j, face in self.faces.items()
                     if (face.material == 3) != lining and j not in removed]
            lo = self.points[additions].min(axis=(0, 1))
            hi = self.points[additions].max(axis=(0, 1))
            xyz = self.points[other]
            neighbor = (xyz.max(axis=1) >= lo).all(axis=1) & (xyz.min(axis=1) <= hi).all(axis=1)
            other = [other[j] for j in np.flatnonzero(neighbor)]
            if not other:
                continue
            patch = BVHTree.FromPolygons(self.coordinates, additions, all_triangles=True)
            exterior = BVHTree.FromPolygons(self.coordinates, other, all_triangles=True)
            if any(not set(additions[i]) & set(other[j]) for i,j in patch.overlap(exterior)):
                self.rejected += 1
                return False
        return True


def build(name, frames, transforms, motion_bones):
    dest = WORK / name
    garment, arm = load_mesh(SOURCE/(name+'.glb'))
    points, weights, faces, bones = read_mesh(garment, arm)
    weights = smooth_weights(points, weights, faces, name)
    skin = pose_matrices(transforms[:, [motion_bones.index(b) for b in bones]], weights)
    poses = posed_points(skin, points)
    priority = (2.5, 8.0, .20, .028, 2.5, 7.0) if name == 'shoes-sneakers' else None
    decimator = Decimator(points, weights, faces, .00085, priority)
    guard = MotionGuard(poses, frames, decimator.faces, name == 'top-tshirt')
    layers = ShoeLayerGuard(points, decimator.faces) if name == 'shoes-sneakers' else None
    def accept(removed, changed):
        return (layers is None or layers(removed, changed)) and guard(removed, changed)
    result = decimator.run(LIMITS[name], accept)
    print('GUARDED', name, len(faces), len(result), guard.checked, guard.rejected, flush=True)
    assert topology(result) == topology(faces)
    rebuild(garment, points, weights, result, bones)
    export_mesh(garment, arm, dest/'guarded.glb', bool(faces[0].uv))
    (dest/'guard.json').write_text(json.dumps(dict(triangles=len(result),
        tested_collapses=guard.checked, rejected_collapses=guard.rejected,
        frames=len(frames), topology=topology(result),
        rejected_layer_collapses=layers.rejected if layers else 0),indent=2)+'\n')


if __name__ == '__main__':
    motion = cache_motion()
    for name in sys.argv[sys.argv.index('--')+1:]:
        build(name, *motion)
