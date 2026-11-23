"""Fit the decimated surface against the posed master, then export that geometry."""
from dataclasses import dataclass
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_npc import WORK, export_mesh, load_mesh, read_mesh, rebuild
from check_motion import ACTIONS, ALL, LEGACY, MASTER, MOTION


@dataclass
class Frame:
    clip: str
    number: int
    points: np.ndarray
    faces: np.ndarray
    tree: BVHTree


def cache_motion():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[n] for n in ('Armature', 'Base_Body'))
    assert np.allclose(arm.matrix_world, np.eye(4))
    arm.animation_data_create()
    arm.animation_data.use_nla = False
    names = tuple(bone.name for bone in arm.data.bones)
    bones = [arm.pose.bones[n] for n in names]
    modes = [b.rotation_mode for b in bones]
    bind = [bone.bone.matrix_local.inverted() for bone in bones]
    body.data.calc_loop_triangles()
    triangles = [tuple(t.vertices) for t in body.data.loop_triangles]
    faces = np.asarray(triangles)
    cache, matrices = [], []

    def append(action_name, number):
        scene.frame_set(number)
        b = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        v = np.empty(3 * len(b.data.vertices), dtype=np.float32)
        b.data.vertices.foreach_get('co', v)
        m = np.array(b.matrix_world, dtype=np.float32)
        p = v.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
        cache.append(Frame(action_name, number, p, faces,
                           BVHTree.FromPolygons(p.tolist(), triangles, all_triangles=True)))
        matrices.append(np.asarray([bone.matrix @ inverse for bone, inverse in zip(bones, bind)], dtype=np.float32)[:, :3])

    arm.animation_data.action = None
    for bone in bones:
        bone.matrix_basis.identity()
    append('rest', 1)
    for path, clips in ((MOTION, LEGACY[1:]), (ACTIONS, ALL[len(LEGACY):])):
        if path == ACTIONS:
            scene.render.fps = 30
            scene.render.fps_base = 1
        old_objects, old_actions = set(scene.objects), set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(path))
        actions = set(bpy.data.actions) - old_actions
        for obj in set(scene.objects) - old_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for name in clips:
            action, = [a for a in actions if a.name == name or a.name.startswith(name + '.')]
            arm.animation_data.action = action
            arm.animation_data.action_slot = action.slots[0]
            first, last = map(round, action.frame_range)
            for number in range(first, last + 1):
                append(name, number)
            print('POSES', name, first, last, flush=True)
    assert modes == [b.rotation_mode for b in bones]
    return cache, np.asarray(matrices), names


def pose_matrices(matrices, weights):
    active = weights.max(axis=0) > 0
    return np.einsum('vb,fbjk->fvjk', weights[:, active].astype(np.float32),
                     matrices[:, active], optimize=True)


def posed_points(matrices, points):
    return np.einsum('fvjk,vk->fvj', matrices[..., :3], points.astype(np.float32)) + matrices[..., 3]


def nearest(tree, point):
    co, normal, _, _ = tree.find_nearest(point)
    return (point-co).dot(normal), normal


def normalized(v):
    return v / np.maximum(1e-9, np.linalg.norm(v, axis=-1, keepdims=True))


def normals(points, faces):
    tris = points[faces]
    cross = np.cross(tris[:, 1]-tris[:, 0], tris[:, 2]-tris[:, 0])
    n = np.zeros_like(points)
    for col in faces.T:
        np.add.at(n, col, cross)
    return normalized(n), cross


def crossings(garment, body):
    # Intersections identify where to distribute a corrective offset on a face.
    result = []
    for verts, target in ((garment, body), (body, garment)):
        for a, b in zip(verts, verts[1:]+verts[:1]):
            hit = intersect_ray_tri(*target, b-a, a, True)
            if hit is not None and (hit-a).dot(hit-b) <= 1e-12:
                result.append(hit)
    return result


def barycentric(p, tri):
    a, b, c = map(np.asarray, tri)
    v, w, q = b-a, c-a, np.asarray(p)-a
    vv, vw, ww = v@v, v@w, w@w
    inv = 1/max(1e-20, vv*ww-vw*vw)
    s, t = (ww*(q@v)-vw*(q@w))*inv, (vv*(q@w)-vw*(q@v))*inv
    return np.clip([1-s-t, s, t], 0, 1)


def scan(points, faces, skin, frames, floor, collect):
    pose = posed_points(skin, points)
    polys = faces.tolist()
    gaps = np.empty((len(frames), len(points)), dtype=np.float32)
    pairs = []
    correction = np.zeros_like(points)
    max_offset = np.zeros(len(points))
    votes = np.zeros(len(points))
    n_rest = normals(points, faces)[0]
    for fi, (frame, points_f) in enumerate(zip(frames, pose, strict=True)):
        tree = frame.tree
        verts = [Vector(v) for v in points_f]
        data = [nearest(tree, v) for v in verts]
        gaps[fi] = [d for d,_ in data]
        garment_tree = BVHTree.FromPolygons(points_f.tolist(), polys, all_triangles=True)
        overlaps = tree.overlap(garment_tree)
        pairs.append(len(overlaps))
        if not collect:
            continue

        def vote(vertices, weights, normal, depth):
            inv = skin[fi, vertices, :, :3]
            local = normalized(np.einsum('vij,i->vj', inv, np.asarray(normal)))
            near = n_rest[vertices]
            # Prefer along-surface normals unless the posed contact points elsewhere.
            agreement = (near*local).sum(axis=1)
            local = normalized(local + near * (.42*np.maximum(agreement, 0))[:, None])
            correction[vertices] += local * (weights * depth)[:, None]
            max_offset[vertices] = np.maximum(max_offset[vertices], np.minimum(depth*1.35, depth * np.sqrt(weights) + .00008))
            votes[vertices] += weights

        for v in np.flatnonzero(gaps[fi] < floor):
            distance, normal = data[v]
            vote(np.array([v]), np.ones(1), normal, floor-distance)

        covered = set()
        for face_id, garment_id in sorted(overlaps):
            if garment_id in covered:
                continue
            covered.add(garment_id)
            ids = faces[garment_id]
            triangle = tuple(verts[i] for i in ids)
            body_tri = tuple(Vector(p) for p in frame.points[frame.faces[face_id]])
            hits = crossings(triangle, body_tri)
            local_points = [*hits, sum(triangle, Vector())/3]
            d, n, contact = min(((*nearest(tree, p), p) for p in local_points), key=lambda item: item[0])
            weight = .14+.86*barycentric(contact, triangle)
            vote(ids, weight, n, max(.00016, .00022 - d, min(floor, .00035)))
    report = {}
    for i, f in enumerate(frames):
        row = report.setdefault(f.clip, {'inside': 0, 'overlap': 0, 'min_m': 9})
        row['inside'] = max(row['inside'], int((gaps[i]<0).sum()))
        row['overlap'] = max(row['overlap'], pairs[i])
        row['min_m'] = min(row['min_m'], float(gaps[i].min()))
    deficit = np.maximum(0, floor-gaps)
    scores = (sum(pairs), int((gaps<0).sum()), float(deficit.sum()), float(deficit.max()))
    applied = normalized(correction) * np.minimum(.0015, max_offset)[:, None]
    return report, scores, applied


def damp(points, offsets, links, faces, original_normals):
    delta = offsets.copy()
    for i, ring in enumerate(links):
        if ring:
            delta[i] = .83*offsets[i] + .17*offsets[sorted(ring)].mean(axis=0)
    for _ in range(5):
        _, crosses = normals(points+delta, faces)
        flipped = (normalized(crosses)*normalized(original_normals)).sum(axis=1) < .3
        if not flipped.any():
            break
        ids = np.unique(faces[flipped])
        delta[ids] *= .35
    return delta


def fit(name, frames, transforms, motion_bones):
    dest = WORK / name
    geometry = dest/'guarded.glb'
    if not geometry.exists():
        geometry = dest/'decimated.glb'
    garment, arm = load_mesh(geometry)
    points, weights, face_data, bones = read_mesh(garment, arm)
    assert set(bones) == set(motion_bones) and len(bones) == 65
    faces = np.array([f.vertices for f in face_data])
    skin = pose_matrices(transforms[:, [motion_bones.index(b) for b in bones]], weights)
    floor = .00058 if name == 'top-dress' else .00022
    required = .00050 if name == 'top-dress' else 0.
    original = points.copy()
    links = [set() for _ in points]
    for row in faces.tolist():
        for id in row:
            links[id].update(set(row)-{id})
    original_normals = normals(points, faces)[1]
    best = None
    history = []
    for iteration in range(13):
        report, score, offset = scan(points, faces, skin, frames, floor, True)
        history.append(dict(score=score, clips=report))
        print('FIT', name, iteration, score,
              {k: [v['inside'], v['overlap'], round(v['min_m']*1e3, 4)] for k,v in report.items()
               if v['inside'] or v['overlap'] or v['min_m'] < required}, flush=True)
        rank = (sum(v['min_m'] < required for v in report.values()) * (name=='top-dress'), *score)
        if best is None or rank < best[0]:
            best = rank, points.copy(), iteration
        if score[0] == score[1] == 0 and min(v['min_m'] for v in report.values()) >= required + .000015:
            best = rank, points.copy(), iteration
            break
        scale = .90 if iteration < 7 else .54
        shift = points + scale*damp(points, offset, links, faces, original_normals) - original
        max_shift = .008 if name=='top-tshirt' else .006
        points = original + shift * np.minimum(1, max_shift/np.maximum(1e-9,np.linalg.norm(shift,axis=1)))[:,None]
    _, chosen, iteration = best
    if iteration:
        rebuild(garment, chosen, weights, face_data, bones)
        export_mesh(garment, arm, dest/'fitted.glb', bool(face_data[0].uv))
    else:
        (dest/'fitted.glb').write_bytes(geometry.read_bytes())
    displacement = np.linalg.norm(chosen-original, axis=1)
    (dest/'fit.json').write_text(json.dumps(dict(chosen_iteration=iteration,
        moved_vertices=int((displacement>1e-7).sum()), max_displacement_m=float(displacement.max()),
        frames=len(frames), iterations=history), indent=2)+'\n')


if __name__ == '__main__':
    motion = cache_motion()
    for module in sys.argv[sys.argv.index('--')+1:]:
        fit(module, *motion)
