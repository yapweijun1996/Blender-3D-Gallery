"""Bake a four-influence Studio bomber fit against the unchanged master clips.

Call in Blender background mode. Arguments after -- select --verify,
--checkers, --renders, or --restore to export the saved fitting checkpoint.
"""
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROUND1 = HERE.parent
PRIOR = runpy.run_path(str(ROUND1 / "fit_jacket.py"))
API = PRIOR["open_master"].__globals__
API.update(HERE=HERE, WORK=HERE, GLB=HERE / "jacket_v2.glb",
           BLEND=HERE / "jacket_v2.blend", TRIANGLE_LIMIT=8000)
MASTER, MOTION, CLIPS, GLB, BLEND = (API[key] for key in ("MASTER", "MOTION", "CLIPS", "GLB", "BLEND"))
mesh_points, mesh_faces, neighbors, average, nearest = (
    API[key] for key in ("mesh_points", "mesh_faces", "neighbors", "average", "nearest"))
TARGET = .0005
MARGIN = .002
CAP = .030
ITERATIONS = 16
CHECKPOINT = HERE / "_fit_checkpoint.npz"


def read_weights(obj, names):
    indices = [names.index(group.name) for group in obj.vertex_groups]
    weights = np.zeros((len(obj.data.vertices), len(names)), dtype=np.float32)
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            weights[vertex.index, indices[group.group]] = group.weight
    return API["limit_weights"](weights)


def weights_near_body(points, body, names, tree, existing):
    coords = mesh_points(body.data)
    faces = mesh_faces(body.data)
    names_short = tuple(name.removeprefix("mixamorig:") for name in names)
    body_weights = API["body_weights"](body, names)
    _, _, face_ids, locations = nearest(tree, points.tolist())
    face = faces[face_ids]
    a, b, c = coords[face].transpose(1, 0, 2)
    u, v, w = b - a, c - a, locations - a
    dot = lambda first, second: np.einsum("ni,ni->n", first, second)
    uu, uv, vv, wu, wv = dot(u, u), dot(u, v), dot(v, v), dot(w, u), dot(w, v)
    determinant = np.maximum(uu * vv - uv * uv, 1e-16)
    s, t = (vv * wu - uv * wv) / determinant, (uu * wv - uv * wu) / determinant
    bary = np.column_stack((1 - s - t, s, t)).clip(0, 1)
    bary /= bary.sum(axis=1, keepdims=True)
    anatomical = np.einsum("nc,ncj->nj", bary, body_weights[face])
    x, _, z = points.T
    for side in ("Left", "Right"):
        hand = names_short.index(side + "Hand")
        forearm = names_short.index(side + "ForeArm")
        fingers = [i for i, name in enumerate(names_short) if name.startswith(side + "Hand") and i != hand]
        anatomical[:, hand] += anatomical[:, fingers].sum(axis=1)
        anatomical[:, fingers] = 0
        cuff = (abs(x) > .232) & ((x > 0) == (side == "Left"))
        anatomical[cuff, forearm] += .45 * anatomical[cuff, hand]
        anatomical[cuff, hand] *= .55
    leg = [i for i, name in enumerate(names_short) if any(word in name for word in ("Leg", "Foot", "Toe"))]
    hips = names_short.index("Hips")
    anatomical[:, hips] += .70 * anatomical[:, leg].sum(axis=1)
    anatomical[:, leg] *= .30
    collar = (abs(x) < .078) & (z > .58)
    anatomical[collar] = .8 * existing[collar] + .2 * anatomical[collar]
    return API["limit_weights"](anatomical)


def smooth_weights(mesh, points, weights, amount):
    x, _, z = points.T
    local = ((abs(x) > .065) & (abs(x) < .23)) | (z < .446)
    factor = np.where(local, amount, amount * .3)[:, None]
    return API["limit_weights"]((weights + factor * (average(weights, neighbors(mesh)) - weights)).astype(np.float32))


def cap_rest(points, tree, lower=.0011):
    result = points.copy()
    for _ in range(5):
        signed, normal, _, loc = nearest(tree, result.tolist())
        vector = result - loc
        length = np.linalg.norm(vector, axis=1)
        result -= (np.maximum(length - (CAP - .00016), 0) / length.clip(1e-8))[:, None] * vector
        result += np.maximum(lower - signed, 0)[:, None] * normal
    return result


def scan(points, weights, transforms, poses, triangles, collect=False):
    # Restrict matrix blending to weighted joints.
    active = np.flatnonzero(weights.max(axis=0))
    skin = API["skin_matrices"](np.ascontiguousarray(weights[:, active]), transforms[:, active])
    posed = API["ply_points"](skin, points)
    distances, gradients = np.empty(posed.shape[:2], np.float32), np.empty_like(posed)
    counts, contacts, witnesses = np.zeros(len(poses), dtype=int), [], []
    faces = triangles.tolist()
    grid = np.array([(a / 3, b / 3, (3 - a - b) / 3)
                     for a in range(4) for b in range(4 - a)], dtype=np.float32)
    for i, pose in enumerate(poses):
        coords = posed[i].tolist()
        if collect:
            distances[i], gradients[i] = signed_normals(pose.tree, coords)
        else:
            distances[i] = nearest_signed(pose.tree, coords)
        pairs = pose.tree.overlap(BVHTree.FromPolygons(coords, faces, all_triangles=True))
        counts[i] = len(pairs)
        if not pairs:
            continue
        pairs = np.asarray(pairs, dtype=np.int32)
        contacts.append((i, pairs))
        if not collect:
            continue
        faces_hit = np.unique(pairs[:, 1])
        tri = triangles[faces_hit]
        xy = np.einsum("kc,tcj->tkj", grid, posed[i, tri])
        sd, sn = signed_normals(pose.tree, xy.reshape(-1, 3).tolist())
        sd, sn = sd.reshape(-1, len(grid)), sn.reshape(-1, len(grid), 3)
        use = np.argpartition(sd, 2, axis=1)[:, :2]
        row = np.arange(len(tri))[:, None]
        witnesses.append((i, np.repeat(tri, 2, axis=0), grid[use].reshape(-1, 3),
                          sn[row, use].reshape(-1, 3), sd[row, use].ravel()))
    return distances, gradients, counts, contacts, witnesses, skin, posed


def summary(label, measurement, poses):
    distances, _, counts = measurement[:3]
    ranking = float(counts.sum() + 3 * (distances < 0).sum() +
                    .16 * np.square(np.maximum(0., -distances) * 1000).sum() + 1300 * counts[0])
    stats = API["clip_results"](poses, distances, counts)
    print(label, round(ranking), "pairs", int(counts.sum()), "min mm", round(float(distances.min() * 1000), 3),
          "rest", int(counts[0]), "clips",
          " ".join(f"{clip}:{value['max_triangle_pairs']}/{value['max_verts_inside']}"
                   for clip, value in stats.items()), flush=True)
    return ranking, stats


def setup():
    bpy.ops.wm.open_mainfile(filepath=str(ROUND1 / "jacket_v1.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, jacket = [scene.objects[name] for name in ("Armature", "Base_Body", "Jacket_Bomber")]
    body.hide_set(False)
    body.hide_viewport = False
    assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
    assert np.allclose(jacket.matrix_world, np.eye(4), atol=1e-6)
    names = tuple(b.name for b in arm.pose.bones)
    poses, transforms = API["cache_motion"](scene, arm, body)
    return scene, arm, body, jacket, names, poses, transforms


def seed_fit(jacket, body, names, poses, transforms):
    points = mesh_points(jacket.data)
    existing = read_weights(jacket, names)
    rest = poses[0].tree
    triangles = mesh_faces(jacket.data)
    anatomical = weights_near_body(points, body, names, rest, existing)
    for _ in range(2):
        anatomical = smooth_weights(jacket.data, points, anatomical, .30)
    signed, n, _, _ = nearest(rest, points.tolist())
    x, _, z = points.T
    torso = (abs(x) < .135) & (z < .54)
    seed = []
    for label, rest_gap, weight_amount, torso_change in (
        ("round1", 0, 0, 0),
        ("rebind", 0, .88, 0),
        ("loft", .016, .76, .25),
        ("trim", .012, .84, .63),
        ("near shell", .005, .97, .86),
        ("loose shell", .024, .85, .57),
    ):
        blend = np.full(len(x), weight_amount, dtype=np.float32)
        weights = API["limit_weights"](existing * (1 - blend[:, None]) + anatomical * blend[:, None])
        step = (rest_gap - signed) * np.where(torso, torso_change, torso_change * .35)
        first = cap_rest(points + n * step[:, None], rest)
        measure = scan(first, weights, transforms, poses, triangles)
        rank, report = summary("SEED " + label, measure, poses)
        seed.append((rank, label, first, weights, report))
    return min(seed, key=lambda row: row[0]), anatomical


def select_frames(poses, distances, counts, stride=33):
    rows = {0, *range(1, len(poses), stride)}
    for clip in CLIPS:
        group = np.asarray([i for i, pose in enumerate(poses) if pose.clip == clip])
        rows.update(group[np.argsort(counts[group], kind="stable")[-3:]])
        rows.update(group[np.argsort(distances[group].min(axis=1), kind="stable")[:3]])
    return np.asarray(sorted(rows))


def smooth_floor(step, adjacency, passes=3):
    result = step.copy()
    for _ in range(passes):
        result = .70 * result + .30 * average(result, adjacency)
    length = np.linalg.norm(step, axis=1)
    direction = step / length.clip(1e-9)[:, None]
    shortfall = length - np.einsum("vi,vi->v", result, direction)
    return result + direction * shortfall.clip(0)[:, None]


def limit_length(step, length):
    return step * np.minimum(1, length / np.linalg.norm(step, axis=1).clip(1e-9))[:, None]


def weight_columns(points, weights, anatomical, adjacency, names):
    support = np.maximum(weights, .72 * anatomical)
    support = np.maximum(support, .68 * average(weights, adjacency))
    x, _, z = points.T
    for side, direction in (("Left", 1), ("Right", -1)):
        torso_side = (x * direction > .055) & (abs(x) < .149) & (z < .54)
        for bone, capacity in (("Arm", .105), ("ForeArm", .080), ("Shoulder", .070)):
            col = names.index("mixamorig:" + side + bone)
            support[torso_side, col] = np.maximum(support[torso_side, col], capacity)
    result = np.argsort(-support, axis=1, kind="stable")[:, :7]
    # The active and anatomical weights must remain available to the search.
    return result


def position_guard(before, after, anchor, triangles, rest_tree):
    old = np.cross(before[triangles[:, 1]] - before[triangles[:, 0]],
                   before[triangles[:, 2]] - before[triangles[:, 0]])
    cuff = abs(anchor[:, 0]) > .241
    after[cuff, 0] = np.clip(after[cuff, 0], anchor[cuff, 0] - .0017, anchor[cuff, 0] + .0017)
    for _ in range(3):
        after = cap_rest(after, rest_tree)
        new = np.cross(after[triangles[:, 1]] - after[triangles[:, 0]],
                       after[triangles[:, 2]] - after[triangles[:, 0]])
        flipped = np.einsum("ni,ni->n", old, new) < .26 * np.square(old).sum(axis=1)
        if not flipped.any():
            break
        unstable = np.unique(triangles[flipped])
        after[unstable] = before[unstable] + .28 * (after[unstable] - before[unstable])
    for _ in range(3):
        pairs = rest_tree.overlap(BVHTree.FromPolygons(after.tolist(), triangles.tolist(), all_triangles=True))
        if not pairs:
            break
        affected = np.unique(triangles[np.asarray(pairs)[:, 1]])
        after[affected] = before[affected] + .13 * (after[affected] - before[affected])
    return after


def deltas(measure, points, weights, transforms, poses, columns, cuff, adjacency):
    d, normals, _, _, contacts, skin, _ = measure
    gaps = np.maximum(MARGIN - d, 0)
    index = np.arange(len(points))
    frame = d.argmin(axis=0)
    worst = gaps[frame, index]
    world_normal = normals[frame, index]
    vec = np.einsum("vi,vij->vj", world_normal, skin[frame, index, :, :3])
    norm_sq = np.square(vec).sum(axis=1).clip(.12)
    geometry = vec * (np.minimum(worst, CAP) / norm_sq)[:, None]
    worst_step = smooth_floor(geometry, adjacency)

    # A deeper witness has more leverage, while repeated contact continues to
    # contribute. Both vertex witnesses and face interiors share this system.
    size = len(points)
    position_sum = np.zeros((size, 3), np.float32)
    weight_sum = np.zeros((size, columns.shape[1]), np.float32)
    position_norm = np.zeros((size, 1), np.float32)
    weight_norm = np.zeros((size, columns.shape[1]), np.float32)
    importance_sum = np.zeros(size, np.float32)
    patch_depth = worst.copy()

    def accumulate(row, vertex, bary, normal, gap, strength):
        if not len(vertex):
            return
        weights_local = weights[vertex]
        columns_local = columns[vertex]
        local_transforms = transforms[row, columns_local]
        current = points[vertex]
        world = np.einsum("nqij,nj->nqi", local_transforms[..., :3], current) + local_transforms[..., 3]
        direction_w = np.einsum("ni,nqi->nq", normal, world)
        existing = np.take_along_axis(weights_local, columns_local, axis=1)
        mean = (existing * direction_w).sum(axis=1) / existing.sum(axis=1).clip(.001)
        direction_w -= mean[:, None]
        direction_p = np.einsum("ni,nij->nj", normal, skin[row, vertex, :, :3])
        importance = strength * np.maximum(.16, gap / np.maximum(patch_depth[vertex], MARGIN)) ** 2
        q = importance * bary
        np.add.at(position_sum, vertex, (q * gap)[:, None] * direction_p)
        np.add.at(weight_sum, vertex, (q * gap)[:, None] * direction_w)
        np.add.at(position_norm[:, 0], vertex, q * bary * np.square(direction_p).sum(axis=1))
        np.add.at(weight_norm, vertex, (q * bary)[:, None] * np.square(direction_w))
        np.add.at(importance_sum, vertex, q)

    for row in range(len(poses)):
        affected, = np.where(gaps[row] > 0)
        accumulate(row, affected, np.ones(len(affected), np.float32), normals[row, affected],
                   gaps[row, affected], 1.)
    for row, triangles, bary, normal, signed in contacts:
        need = MARGIN - signed
        for corner in range(3):
            good = (bary[:, corner] > .08) & (need > 0)
            vertex = triangles[good, corner]
            np.maximum.at(patch_depth, vertex, need[good] * bary[good, corner])
            accumulate(row, vertex, bary[good, corner], normal[good], need[good], .36)
    mean = position_sum / (position_norm + .05)
    raw = mean * .70 + geometry * .30
    raw[cuff, 0] *= .12
    mean_step = smooth_floor(raw, adjacency)
    weight_step = weight_sum / (weight_norm + .00035 * importance_sum[:, None] + .00001)
    return worst_step, mean_step, weight_step, patch_depth


def cell_score(distances, counts, original, points, weights, reference, adjacency):
    g = np.maximum(0, MARGIN - distances) * 1000
    p = np.maximum(0, -distances) * 1000
    change = (points - original) * 1000
    roughness = change - average(change, adjacency)
    w_roughness = (weights - average(weights, adjacency)) - (reference - average(reference, adjacency))
    return (float(counts.sum()) + 3.2 * (distances < 0).sum() + .17 * np.square(p).sum()
            + .037 * np.square(g).sum() + 1300 * counts[0]
            + .06 * np.square(roughness).sum() + 19 * np.square(w_roughness).sum())


def evaluate_subset(points, weights, transforms, poses, triangles, rows, anchor, reference, adjacency):
    result = scan(points, weights, transforms[rows], [poses[row] for row in rows], triangles)
    return cell_score(result[0], result[2], anchor, points, weights, reference, adjacency)


def global_step(measure, points, weights, anchor, anatomical, scene_mesh, transforms, poses, names, triangles):
    d, _, counts = measure[:3]
    adjacency = neighbors(scene_mesh)
    columns = weight_columns(anchor, weights, anatomical, adjacency, names)
    cuff = abs(anchor[:, 0]) > .241
    worst, mean, correction, depth = deltas(measure, points, weights, transforms, poses, columns, cuff, adjacency)
    _, radial, _, _ = nearest(poses[0].tree, points.tolist())
    radial_step = radial * depth[:, None]
    rows = select_frames(poses, d, counts)
    score = evaluate_subset(points, weights, transforms, poses, triangles, rows, anchor, anatomical, adjacency)
    best = score, "unchanged", points, weights
    alternatives = (
        ("worst frame", worst, .55, 0., .005),
        ("pooled", mean, .63, .25, .005),
        ("weight and loft", mean, .22, .66, .003),
        ("outward", radial_step, .30, 0., .004),
        ("inward", radial_step, -.28, 0., .004),
    )
    for label, delta, scale, reweight, limit in alternatives:
        shape = position_guard(points, points + limit_length(delta * scale, limit),
                               anchor, triangles, poses[0].tree)
        changed = weights.copy()
        local = np.take_along_axis(changed, columns, axis=1)
        local = np.clip(local + (correction * reweight).clip(-.085, .085), 0, 1)
        np.put_along_axis(changed, columns, local, axis=1)
        changed = API["limit_weights"](changed)
        value = evaluate_subset(shape, changed, transforms, poses, triangles, rows, anchor, anatomical, adjacency)
        if value < best[0]:
            best = value, label, shape, changed
    print("PATCH SEARCH", best[1], round(score), "->", round(best[0]), flush=True)
    return best[2], best[3], worst, mean, depth, columns


def nearest_signed(tree, coordinates):
    find = tree.find_nearest
    signed = []
    for x, y, z in coordinates:
        (a, b, c), (u, v, w), _, _ = find((x, y, z))
        signed.append((x - a) * u + (y - b) * v + (z - c) * w)
    return signed


def signed_normals(tree, coordinates):
    find = tree.find_nearest
    signed, normals = [], []
    for x, y, z in coordinates:
        (a, b, c), (u, v, w), _, _ = find((x, y, z))
        signed.append((x - a) * u + (y - b) * v + (z - c) * w)
        normals.append((u, v, w))
    return np.asarray(signed, dtype=np.float32), np.asarray(normals, dtype=np.float32)


def local_step(measure, points, weights, anchor, anatomical, mesh, triangles, poses, transforms, columns,
               mean, worst, depth, iteration):
    distances, _, counts, _, contact, skin, _ = measure
    adjacency = neighbors(mesh)
    vertices = np.flatnonzero(depth > .0006)
    vertices = vertices[np.argsort(-depth[vertices], kind="stable")][:1150]
    clips = [np.asarray([i for i, pose in enumerate(poses) if pose.clip == clip]) for clip in CLIPS]
    patch = [[] for _ in points]
    tri = API["mesh_faces"](mesh)
    tri_map = [[] for _ in points]
    for triangle in tri:
        for vertex in triangle:
            tri_map[vertex].append(triangle)
    for row, corners, bary, _, dist in contact:
        for index in np.flatnonzero(dist < MARGIN):
            for j in np.flatnonzero(bary[index] >= .18):
                patch[corners[index, j]].append((float(dist[index]), row, corners[index], bary[index], j))
    point_next, weight_next = points.copy(), weights.copy()
    anchor_current = anchor + average(points - anchor, adjacency)
    smooth = average(weights, adjacency)
    _, radial, _, _ = nearest(poses[0].tree, points.tolist())
    axes = np.eye(3, dtype=np.float32)
    diagonals = np.array([(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)
                          if sum(abs(c) for c in (x, y, z)) > 1], dtype=np.float32)
    directions = np.vstack((axes, -axes, diagonals / np.linalg.norm(diagonals, axis=1)[:, None]))
    changes = 0
    for v in vertices:
        depth_by_pose = distances[:, v]
        rows = {0, *np.argsort(depth_by_pose, kind="stable")[:10]}
        for clip in clips:
            rows.update(clip[np.argsort(depth_by_pose[clip], kind="stable")[:2]])
        rows = np.array(sorted(rows))
        nearby = sorted(patch[v], key=lambda item: item[0])
        witnesses = nearby[:8]
        if nearby:
            witnesses += [nearby[k] for k in np.linspace(0, len(nearby)-1, 6, dtype=int)]
        p, w = points[v], weights[v]
        scale = .007 if iteration < 7 else .005
        if iteration >= 11 and depth[v] < .004:
            scale = .0035
        layout = np.vstack((np.zeros((1, 3)), mean[v] * .75, worst[v] * .8,
                            (anchor_current[v] - p) * .6, directions * scale,
                            radial[v] * .5 * scale, -radial[v] * .5 * scale,
                            directions[:6] * .43 * scale,
                            radial[v] * 1.7 * scale, -radial[v] * 1.7 * scale))
        wp = [w] * len(layout)
        pp = list(p + layout)
        for joint in columns[v]:
            if w[joint] >= .995:
                continue
            for amount in (.10, .27 if iteration < 10 else .19):
                modified = w * (1. - amount)
                modified[joint] += amount
                wp.extend((modified, modified))
                pp.extend((p, p + .55 * layout[1]))
        for other in (anatomical[v], smooth[v]):
            wp.append(.62 * w + .38 * other)
            pp.append(p)
        pp, wp = np.asarray(pp, np.float32), API["limit_weights"](np.asarray(wp, np.float32))
        if abs(anchor[v, 0]) > .241:
            pp[:, 0] = np.clip(pp[:, 0], anchor[v, 0] - .0017, anchor[v, 0] + .0017)
        joints = np.flatnonzero(wp.max(axis=0))
        visible_w = wp[:, joints]

        def trace(frame_ids):
            matrix = (visible_w @ transforms[frame_ids[:, None], joints].reshape(len(frame_ids), len(joints), 12)
                      ).reshape(len(frame_ids), len(wp), 3, 4)
            return np.einsum("nkij,kj->nki", matrix[..., :3], pp) + matrix[..., 3]

        posed = trace(rows)
        signed = np.asarray([nearest_signed(poses[row].tree, positions.tolist())
                             for row, positions in zip(rows, posed)])
        gaps = np.maximum(0, MARGIN - signed) * 1000
        costs = np.square(gaps).mean(axis=0) + 2.1 * np.square(gaps.max(axis=0))
        if witnesses:
            frame_ids = np.asarray([item[1] for item in witnesses])
            face = np.asarray([item[2] for item in witnesses])
            bary = np.asarray([item[3] for item in witnesses])
            corner = np.asarray([item[4] for item in witnesses])
            tr = np.einsum('ncij,ncj->nci', skin[frame_ids[:, None], face, :, :3], points[face])
            tr += skin[frame_ids[:, None], face, :, 3]
            samples = np.einsum("nc,nci->ni", bary, tr)
            r = np.arange(len(bary))
            delta = trace(frame_ids) - tr[r, corner, :][:, None]
            q = samples[:, None] + bary[r, corner][:, None, None] * delta
            gaps_face = np.maximum(0, MARGIN - np.asarray([
                nearest_signed(poses[row].tree, entries.tolist()) for row, entries in zip(frame_ids, q)])) * 1000
            costs += 1.3 * np.square(gaps_face).mean(axis=0) + .6 * np.square(gaps_face.max(axis=0))
        costs += .075 * np.square((pp - anchor_current[v]) * 1000).sum(axis=1)
        costs += .05 * np.square((pp - p) * 1000).sum(axis=1)
        costs += 15. * np.square(wp - smooth[v]).sum(axis=1) + 9. * np.square(wp - w).sum(axis=1)
        sd, _, _, loc = nearest(poses[0].tree, pp.tolist())
        absolute = np.linalg.norm(pp - loc, axis=1)
        costs[(sd < .0010) | (absolute > CAP - .00012)] = np.inf
        # Keep faces adjacent to a replacement from folding in the T-pose.
        faces = np.asarray(tri_map[v])
        reference_face = point_next[faces]
        normals = np.cross(reference_face[:, 1] - reference_face[:, 0], reference_face[:, 2] - reference_face[:, 0])
        for proposal in np.argsort(costs, kind="stable")[:10]:
            if proposal == 0 or not np.isfinite(costs[proposal]) or costs[proposal] >= costs[0] - .01:
                break
            updated = reference_face.copy()
            updated[faces == v] = pp[proposal]
            new_normals = np.cross(updated[:, 1] - updated[:, 0], updated[:, 2] - updated[:, 0])
            if np.any(np.einsum("ni,ni->n", normals, new_normals) < .34 * np.square(normals).sum(axis=1)):
                continue
            point_next[v], weight_next[v] = pp[proposal], wp[proposal]
            changes += 1
            break
    print("LOCAL LOFT", len(vertices), "changed", changes, flush=True)
    return point_next, weight_next


def patch_cost(distances, prefix):
    gap = np.maximum(0, MARGIN - distances) * 1000
    deep = np.maximum(0, -(distances + .006)) * 1000
    return float(np.square(gap).sum() + 2.4 * np.square(deep).sum() +
                 1.3 * np.square(gap.max(axis=0)).sum()) / prefix


def hotspot_step(points, weights, anchor, anatomical, mesh, triangles, measure, poses, transforms, names, iteration):
    """Test coherent displacements through the occupied contact regions."""
    d, normals, counts, _, _, skin, _ = measure
    adjacency = neighbors(mesh)
    columns = weight_columns(anchor, weights, anatomical, adjacency, names)
    pressure = np.maximum(0., MARGIN - d)
    maximum = pressure.max(axis=0)
    eps = .0001
    row_set = select_frames(poses, d, counts, stride=57)
    before = evaluate_subset(points, weights, transforms, poses, triangles, row_set, anchor, anatomical, adjacency)
    best = before, points, weights
    visited = np.zeros(len(points), bool)
    aggregate_p, aggregate_w = points.copy(), weights.copy()
    cutoff = .0035 if iteration < 12 else .0020
    patches = 0
    for candidate in np.argsort(-maximum, kind="stable"):
        if visited[candidate] or maximum[candidate] < cutoff:
            continue
        patches += 1
        xyz = anchor - anchor[candidate]
        radius = .024 if abs(anchor[candidate, 0]) < .155 else .019
        length = np.linalg.norm(xyz, axis=1)
        visited |= length <= radius * 1.3
        vertices = np.flatnonzero(length <= radius * 1.7)
        falloff = np.maximum(0., 1. - np.square(length[vertices] / (1.7 * radius))) ** 2
        frames = {0, *row_set}
        local_depth = d[:, vertices].min(axis=1)
        for clip in CLIPS:
            group = np.asarray([i for i, pose in enumerate(poses) if pose.clip == clip])
            frames.update(group[np.argsort(local_depth[group], kind="stable")[:4]])
        rows = np.asarray(sorted(frames))
        base = d[rows[:, None], vertices]
        matrices = skin[rows[:, None], vertices]
        frame = int(d[:, candidate].argmin())
        direction = normals[frame, candidate] @ skin[frame, candidate, :, :3]
        direction /= max(eps, np.linalg.norm(direction))
        _, normal, _, _ = nearest(poses[0].tree, [points[candidate].tolist()])
        axis = np.eye(3, dtype=np.float32)
        directions = np.vstack((direction, -direction, normal, -normal, axis, -axis,
                                direction + axis, direction - axis))
        directions /= np.linalg.norm(directions, axis=1).clip(eps)[:, None]
        # Search beyond the local contact boundary so a panel can route around
        # an arm instead of remaining inside between opposing nearest normals.
        amplitude = min(.022, max(.0055, maximum[candidate] * .90))
        choice_p, choice_w = points[vertices], weights[vertices]
        nearby = points[vertices]
        value = patch_cost(base, len(vertices))
        proposals = []
        for axis in directions:
            for factor in (.46, 1.):
                update = nearby + factor * amplitude * falloff[:, None] * axis
                update = anchor[vertices] + limit_length(update - anchor[vertices], CAP - .0002)
                cuff = abs(anchor[vertices, 0]) > .241
                update[cuff, 0] = np.clip(update[cuff, 0], anchor[vertices[cuff], 0] - .0017,
                                        anchor[vertices[cuff], 0] + .0017)
                update = cap_rest(update, poses[0].tree)
                posed = np.einsum("rvij,vj->rvi", matrices[..., :3], update) + matrices[..., 3]
                s = np.array([nearest_signed(poses[r].tree, p.tolist()) for r, p in zip(rows, posed)])
                fit = patch_cost(s, len(vertices)) + .05 * np.square((update - nearby) * 1000).mean()
                if fit < value:
                    proposals.append((fit, update, weights[vertices]))
        for joint in columns[candidate, :4]:
            for amount in (.075, .19, .31):
                influence = (amount * falloff)[:, None]
                vertex_weights = weights[vertices] * (1. - influence)
                vertex_weights[:, joint] += influence[:, 0]
                vertex_weights = API["limit_weights"](vertex_weights.astype(np.float32))
                used = np.flatnonzero(vertex_weights.max(axis=0))
                changed_matrices = API["skin_matrices"](np.ascontiguousarray(vertex_weights[:, used]),
                                                          transforms[rows[:, None], used])
                posed = API["ply_points"](changed_matrices, nearby)
                s = np.array([nearest_signed(poses[r].tree, p.tolist()) for r, p in zip(rows, posed)])
                fit = patch_cost(s, len(vertices)) + .65 * np.square(vertex_weights - weights[vertices]).sum()
                if fit < value:
                    proposals.append((fit, nearby, vertex_weights))
        if proposals:
            choice_value, choice_p, choice_w = min(proposals, key=lambda item: item[0])
            aggregate_p[vertices] += choice_p - nearby
            aggregate_w[vertices] += choice_w - weights[vertices]
            print("CONTACT PATCH", int(candidate), poses[frame].clip, poses[frame].frame,
                  round(value, 2), "->", round(choice_value, 2), flush=True)
        if patches >= 4 or visited.sum() >= max(110, len(points) * .27):
            break
    for power in (1., .45, .16):
        shape = position_guard(points, points + power * (aggregate_p - points), anchor, triangles, poses[0].tree)
        blend = API["limit_weights"]((weights + power * (aggregate_w - weights)).clip(0).astype(np.float32))
        score = evaluate_subset(shape, blend, transforms, poses, triangles, row_set, anchor, anatomical, adjacency)
        if score < best[0]:
            best = score, shape, blend
    print("CONTACT PATCH SEARCH", round(before), "->", round(best[0]), flush=True)
    return best[1:]


def bind_contact_loft(jacket, points, anchor, weights, triangles, contacts, poses, transforms):
    """Match each inserted midpoint to the old edge trajectory before refitting."""
    edge_parent = {}
    for edge in jacket.data.edges:
        a, b = edge.vertices[:]
        edge_parent[tuple((points[a] + points[b]) * .5)] = a, b
    original_positions = {tuple(point) for point in points}
    before = points
    blended = API["skin_matrices"](weights, transforms)
    old_pose = API["ply_points"](blended, points)
    API["update_points"](jacket, points)
    points, anchor, fitted_weights = API["subdivide"](jacket, triangles, points, anchor, weights, contacts)
    updates = 0
    corrections = points.copy()
    for vertex, point in enumerate(points):
        key = tuple(point)
        if key in original_positions or key not in edge_parent:
            continue
        a, b = edge_parent[key]
        midpoint = (old_pose[:, a] + old_pose[:, b]) * .5
        original = fitted_weights[vertex]
        columns = np.flatnonzero(original)
        motion = transforms[:, columns]
        values = original[columns]
        position = point.copy()
        for _ in range(2):
            estimates = np.einsum("rqij,j->rqi", motion[..., :3], position) + motion[..., 3]
            base = estimates[:, -1, :]
            other = (estimates[:, :-1, :] - base[:, None, :]).transpose(0, 2, 1)
            if len(columns) > 1:
                system = other.reshape(-1, len(columns) - 1)
                target = (midpoint - base).ravel()
                regularizer = .11 * np.eye(len(columns) - 1)
                solution = np.linalg.lstsq(np.vstack((system, regularizer)),
                                            np.r_[target, regularizer @ original[columns[:-1]]], rcond=None)[0]
                values = np.r_[solution, 1 - solution.sum()].clip(0, 1)
                values /= values.sum()
            matrix = np.einsum("q,rqij->rij", values, motion)
            # High rest regularization keeps the new support loop in the
            # original panel unless the motion samples agree on a change.
            system = matrix[..., :3].reshape(-1, 3)
            target = (midpoint - matrix[..., 3]).ravel()
            regularizer = 13. * np.eye(3)
            position = np.linalg.lstsq(np.vstack((system, regularizer)),
                                       np.r_[target, regularizer @ point], rcond=None)[0]
        candidate = point + limit_length((position - point)[None], .002)[0]
        candidate = cap_rest(candidate[None], poses[0].tree)[0]
        fitted_weights[vertex, columns] = values
        corrections[vertex] = candidate
        updates += 1
    result = position_guard(points, corrections, anchor, mesh_faces(jacket.data), poses[0].tree)
    print("MIDPOINT TRAJECTORIES", updates, "new vertices", len(points) - len(before), flush=True)
    return result, anchor, fitted_weights


def export(scene, arm, body, jacket, points, names, weights):
    API["set_pose"](scene, arm, "rest", 1.)
    arm.animation_data_clear()
    API["update_points"](jacket, points)
    API["write_weights"](jacket, names, weights)
    for obj in list(scene.objects):
        if obj not in (arm, body, jacket):
            bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    bpy.ops.object.select_all(action="DESELECT")
    jacket.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = jacket
    assert len(arm.data.bones) == 65 and len(mesh_faces(jacket.data)) <= 8000
    # Export the skinned mesh and skeleton as separate scene roots. The
    # armature modifier gives the exporter the skin without a parent node.
    bind_world = jacket.matrix_world.copy()
    jacket.parent = None
    jacket.matrix_world = bind_world
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                             export_animations=False, export_yup=True, export_all_influences=False,
                             export_def_bones=False, export_normals=True, export_texcoords=True, export_tangents=True)
    jacket.parent = arm
    jacket.matrix_world = bind_world
    body.hide_set(True)
    body.hide_render = True
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def save_checkpoint(jacket, points, names, weights, anchor, anatomical, iteration, rank):
    API["update_points"](jacket, points)
    API["write_weights"](jacket, names, weights)
    np.savez_compressed(CHECKPOINT, points=points, weights=weights, anchor=anchor, anatomical=anatomical,
                        iteration=iteration, rank=rank)
    # The UV interpolation done during local splits lives in the mesh data.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "_fit_mesh.blend"), compress=True, copy=True)


def build(resume=False, restore=False, start=4):
    if restore:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / "_fit_mesh.blend"), load_ui=False, use_scripts=False)
        scene = bpy.context.scene
        arm, body, jacket = [scene.objects[name] for name in ("Armature", "Base_Body", "Jacket_Bomber")]
        names = tuple(b.name for b in arm.pose.bones)
        saved = np.load(CHECKPOINT)
        export(scene, arm, body, jacket, saved["points"], names, saved["weights"])
        return
    scene, arm, body, jacket, names, poses, transforms = setup()
    anchor = mesh_points(jacket.data)
    if resume:
        checkpoint = np.load(CHECKPOINT)
        points, weights, anatomical = [checkpoint[key] for key in ("points", "weights", "anatomical")]
        label = "round1 geometry and weights"
        if "anchor" in checkpoint.files:
            anchor = checkpoint["anchor"]
            bpy.ops.wm.open_mainfile(filepath=str(HERE / "_fit_mesh.blend"), load_ui=False, use_scripts=False)
            scene = bpy.context.scene
            arm, body, jacket = [scene.objects[name] for name in ("Armature", "Base_Body", "Jacket_Bomber")]
    else:
        seed, anatomical = seed_fit(jacket, body, names, poses, transforms)
        _, label, points, weights, _ = seed
    history = []
    best = float("inf")
    for iteration in range(start, ITERATIONS + 1):
        if iteration in (9, 14) and iteration > start:
            checkpoint = np.load(CHECKPOINT)
            points, weights, anchor, anatomical = [checkpoint[key] for key in ("points", "weights", "anchor", "anatomical")]
            bpy.ops.wm.open_mainfile(filepath=str(HERE / "_fit_mesh.blend"), load_ui=False, use_scripts=False)
            scene = bpy.context.scene
            arm, body, jacket = [scene.objects[name] for name in ("Armature", "Base_Body", "Jacket_Bomber")]
        triangles = mesh_faces(jacket.data)
        measure = scan(points, weights, transforms, poses, triangles, collect=iteration < ITERATIONS)
        d, _, pairs, faces = measure[:4]
        score, stats = summary(f"FIT {iteration}", measure, poses)
        record = {"iteration": iteration, "seed": label, "score": score, "triangles": len(triangles),
                  "summed_overlap_pairs": int(pairs.sum()), "clips": stats}
        history.append(record)
        API["write_json"](HERE / "fit_history.json", history)
        if score < best and not pairs[0] and d[0].min() >= TARGET:
            best = score
            save_checkpoint(jacket, points, names, weights, anchor, anatomical, iteration, score)
        if (not pairs.any() and d.min() >= TARGET) or iteration == ITERATIONS:
            break
        if iteration == 14:
            points, anchor, weights = bind_contact_loft(jacket, points, anchor, weights, triangles,
                                                        faces, poses, transforms)
            anatomical = weights_near_body(points, body, names, poses[0].tree, weights)
            continue
        if iteration >= 9:
            next_p, next_w = hotspot_step(points, weights, anchor, anatomical, jacket.data, triangles, measure,
                                          poses, transforms, names, iteration)
        else:
            next_p, next_w = points, weights
        if iteration < 9 or (next_p is points and iteration % 2 == 0):
            next_p, next_w, worst, mean, depth, columns = global_step(
                measure, points, weights, anchor, anatomical, jacket.data, transforms, poses, names, triangles)
            trial_p, trial_w = local_step(measure, points, weights, anchor, anatomical, jacket.data, triangles,
                                         poses, transforms, columns, mean, worst, depth, iteration)
            adjacency = neighbors(jacket.data)
            rows = select_frames(poses, d, pairs, stride=46)
            baseline = evaluate_subset(next_p, next_w, transforms, poses, triangles, rows, anchor, anatomical, adjacency)
            dp, dw = trial_p - points, trial_w - weights
            x, _, z = anchor.T
            left_panel = (x > .035) & (x < .141) & (z < .533)
            right_panel = (x < -.035) & (x > -.141) & (z < .533)
            zones = [np.ones(len(points), dtype=bool), left_panel, right_panel,
                     ~(left_panel | right_panel) & (z < .598)]
            candidates = [(np.ones(len(points)), dim, wdim) for dim, wdim in (
                (0., .65), (.35, 0.), (.10, .10), (.35, .35), (.70, .70), (1., 1.))]
            candidates.extend((average(mask.astype(np.float32), adjacency), .58, .55)
                              for mask in zones[1:])
            for index, (strength, factor, weight_factor) in enumerate(candidates):
                p = position_guard(points, points + factor * strength[:, None] * dp,
                                   anchor, triangles, poses[0].tree)
                w = API["limit_weights"]((weights + weight_factor * strength[:, None] * dw).astype(np.float32))
                trial = evaluate_subset(p, w, transforms, poses, triangles, rows, anchor, anatomical, adjacency)
                if trial < baseline:
                    next_p, next_w, baseline = p, w, trial
                    print("LOCAL ACCEPT", index, round(trial), flush=True)
        points, weights = next_p, next_w
        if iteration in (6, 10):
            API["update_points"](jacket, points)
            # Use UV-preserving one-edge splits to add local loft controls to
            # crossing faces whose longest rest edge exceeds twelve millimetres.
            points, anchor, weights = API["subdivide"](jacket, triangles, points, anchor, weights, faces)
            anatomical = weights_near_body(points, body, names, poses[0].tree, weights)
            neighbor_mean = average(weights, neighbors(jacket.data))
            transition = (abs(anchor[:, 0]) > .079) & (abs(anchor[:, 0]) < .15) & (anchor[:, 2] > .50)
            weights[transition] = API["limit_weights"](.985 * weights[transition] + .015 * neighbor_mean[transition])
    build(restore=True)


def fit_regions(points):
    x = points[:, 0]
    side = np.where(x > .025, "left ", np.where(x < -.025, "right ", "center "))
    return np.char.add(side, API["zones"](points))


def rest_surface_clearance(tree, coordinates, triangles, labels, grid):
    """Check the sampled rest face interiors for clearance-cap excursions."""
    shape = coordinates[triangles]
    statistics = {}
    for label in sorted(set(labels)):
        faces = shape[labels == label]
        low, high = 0, 0
        min_signed, max_euclidean = float("inf"), 0.
        for start in range(0, len(faces), 192):
            sample = np.einsum("gc,fci->fgi", grid, faces[start:start + 192]).reshape(-1, 3)
            signed, _, _, loc = nearest(tree, sample.tolist())
            straight = np.linalg.norm(sample - loc, axis=1)
            low += int((signed < TARGET).sum())
            high += int((straight > CAP).sum())
            min_signed = min(min_signed, float(signed.min()))
            max_euclidean = max(max_euclidean, float(straight.max()))
        statistics[str(label)] = {"samples": len(faces) * len(grid), "below_minimum": low,
                                  "over_cap": high, "min_signed_m": min_signed,
                                  "max_euclidean_m": max_euclidean}
    return statistics


def append_rest_surface():
    import json
    path = HERE / "dense_check.json"
    report = json.loads(path.read_text())
    assert report["glb_sha256"] == API["hash_file"](GLB)
    scene, arm, body, jacket = API["reimport"]()
    API["set_pose"](scene, arm, "rest", 1.)
    dg = bpy.context.evaluated_depsgraph_get()
    bp, bf = API["evaluated_surface"](body, dg)
    gp, gf = API["evaluated_surface"](jacket, dg)
    coords = np.asarray(gp, np.float32)
    tree = BVHTree.FromPolygons(bp, bf.tolist(), all_triangles=True)
    labels = fit_regions(coords[gf].mean(axis=1))
    grid = np.array([(a / 10, b / 10, (10 - a - b) / 10)
                     for a in range(11) for b in range(11 - a)], np.float32)
    report["rest"]["surface_samples"] = rest_surface_clearance(tree, coords, gf, labels, grid)
    API["write_json"](path, report)


def verify():
    API["inspect_export"]()
    scene, arm, body, jacket = API["reimport"]()
    rest_points = mesh_points(jacket.data)
    garment_faces = mesh_faces(jacket.data)
    garment_face_list = garment_faces.tolist()
    region = fit_regions(rest_points)
    rest_triangles = rest_points[garment_faces]
    face_region = fit_regions(rest_triangles.mean(axis=1))
    longest_rest_edge = np.linalg.norm(rest_triangles - np.roll(rest_triangles, 1, axis=1), axis=2).max(axis=1)
    crossing_faces = set()
    names = tuple(b.name for b in arm.pose.bones)
    body_joint = np.asarray(names)[API["body_weights"](body, names)[mesh_faces(body.data)].sum(axis=1).argmax(axis=1)]
    grid = np.array([(a / 10, b / 10, (10 - a - b) / 10)
                     for a in range(11) for b in range(11 - a)], np.float32)
    poses, distances, counts, frame_failures = [], [], [], []
    zone_failures = {}
    rest_distances, rest_surface = None, None
    for clip, frame in API["frames"]():
        API["set_pose"](scene, arm, clip, frame)
        dg = bpy.context.evaluated_depsgraph_get()
        body_xyz, body_faces = API["evaluated_surface"](body, dg)
        garment_xyz, _ = API["evaluated_surface"](jacket, dg)
        garment_xyz = np.asarray(garment_xyz, dtype=np.float32)
        body_tree = BVHTree.FromPolygons(body_xyz, body_faces.tolist(), all_triangles=True)
        signed, _, face_id, nearest_xyz = nearest(body_tree, garment_xyz.tolist())
        pairs = np.asarray(body_tree.overlap(BVHTree.FromPolygons(
            garment_xyz.tolist(), garment_face_list, all_triangles=True)), dtype=np.int32).reshape(-1, 2)
        poses.append(API["Pose"](clip, frame, None))
        distances.append(signed)
        counts.append(len(pairs))
        if clip == "rest":
            rest_distances = np.linalg.norm(garment_xyz - nearest_xyz, axis=1)
            rest_surface = rest_surface_clearance(body_tree, garment_xyz, garment_faces, face_region, grid)
        missing = signed < TARGET
        if not missing.any() and not len(pairs):
            continue

        def zone_info(label):
            return zones.setdefault(str(label), {
                "inside_vertices": 0, "vertices_below_margin": 0, "triangle_pairs": 0,
                "min_vertex_signed_m": None, "deepest_face_sample_m": None,
            })

        zones = {}
        for label in np.unique(region[missing]):
            rows = np.flatnonzero((region == label) & missing)
            j = rows[signed[rows].argmin()]
            entry = zone_info(label)
            entry.update(inside_vertices=int((signed[rows] < 0).sum()),
                         vertices_below_margin=len(rows), min_vertex_signed_m=float(signed[j]),
                         nearest_vertex_body_joint=str(body_joint[face_id[j]]))
        if len(pairs):
            hit_faces = np.unique(pairs[:, 1])
            crossing_faces.update(map(int, hit_faces))
            samples = np.einsum("gc,fci->fgi", grid, garment_xyz[garment_faces[hit_faces]])
            d = np.asarray(nearest_signed(body_tree, samples.reshape(-1, 3).tolist()),
                           dtype=np.float32).reshape(len(hit_faces), -1)
            for label in np.unique(face_region[hit_faces]):
                use = np.flatnonzero(face_region[hit_faces] == label)
                j, k = np.unravel_index(d[use].argmin(), (len(use), len(grid)))
                row = zone_info(label)
                row.update(triangle_pairs=int((face_region[pairs[:, 1]] == label).sum()),
                           deepest_face_sample_m=float(min(0., d[use[j], k])),
                           nearest_face_body_joint=str(body_joint[body_tree.find_nearest(samples[use[j], k])[2]]))
        for label, entry in zones.items():
            key = clip, label
            record = zone_failures.setdefault(key, {"clip": clip, "zone": label, "failing_samples": 0,
                                                    "max_inside_vertices": 0, "max_triangle_pairs": 0})
            record["failing_samples"] += 1
            record["max_inside_vertices"] = max(record["max_inside_vertices"], entry["inside_vertices"])
            record["max_triangle_pairs"] = max(record["max_triangle_pairs"], entry["triangle_pairs"])
            for field, body_field in (("min_vertex_signed_m", "nearest_vertex_body_joint"),
                                      ("deepest_face_sample_m", "nearest_face_body_joint")):
                value = entry[field]
                if value is not None and value < record.get(field, float("inf")):
                    record.update({field: value, field + "_frame": frame, body_field: entry[body_field]})
        frame_failures.append({"clip": clip, "frame": frame, "inside_vertices": int((signed < 0).sum()),
                               "triangle_pairs": len(pairs), "min_vertex_signed_m": float(signed.min()),
                               "zones": zones})

    d, counts = np.asarray(distances), np.asarray(counts)
    clips = API["clip_results"](poses, d, counts)
    labels = API["zones"](rest_points)
    stats = {}
    for label in ("all", *sorted(set(labels))):
        mask = np.ones(len(labels), dtype=bool) if label == "all" else labels == label
        stats[label] = dict(zip(("min", "p10", "median", "p90", "p95", "max"),
                                map(float, np.percentile(d[0, mask], (0, 10, 50, 90, 95, 100)))))
        stats[label]["vertices"] = int(mask.sum())
        stats[label]["max_euclidean"] = float(rest_distances[mask].max())
    rest = {
        "clearance_m": stats,
        "surface_samples": rest_surface,
        "wrist_x_m": list(map(float, (rest_points[:, 0].max(), rest_points[:, 0].min()))),
        "hem_z_m": list(map(float, (rest_points[labels == "ribbed hem", 2].min(),
                                   rest_points[labels == "ribbed hem", 2].max()))),
    }
    API["write_json"](HERE / "dense_check.json", {
        "glb_sha256": API["hash_file"](GLB), "poses": len(poses), "clip_summary": clips,
        "rest": rest, "zone_residuals": [zone_failures[k] for k in sorted(zone_failures)],
        "failed_poses": frame_failures,
        "distinct_crossing_faces": len(crossing_faces),
        "crossing_faces_with_rest_edge_over_12_mm": sum(bool(longest_rest_edge[i] > .012) for i in crossing_faces),
        "longest_crossing_face_rest_edge_m": float(max((longest_rest_edge[i] for i in crossing_faces), default=0.)),
    })
    for clip, values in clips.items():
        print("DENSE", clip, values, flush=True)


def render():
    from mathutils import Vector
    import json
    scene, arm, body, jacket = API["reimport"]()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("Fit studio")
    scene.world = world
    world.use_nodes = True
    sky = world.node_tree.nodes["Background"]
    sky.inputs[0].default_value = (.68, .74, .79, 1)
    sky.inputs[1].default_value = .63
    focus = Vector((0, -.015, .502))
    for name, position, power, size in (
        ("Key", (-1.2, -1.6, 2.1), 165, 1.5),
        ("Fill", (1.3, -.7, 1.1), 65, 1.7),
        ("Rim", (.1, 1.4, 1.8), 135, 1.4),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = power, "DISK", size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (focus - obj.location).to_track_quat("-Z", "Y").to_euler()
    data = bpy.data.cameras.new("Fit camera")
    data.type = "ORTHO"
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    dense = json.loads((HERE / "dense_check.json").read_text())
    assert dense["glb_sha256"] == API["hash_file"](GLB), "Verify the current export before rendering."
    views = (
        ("front", "rest", (0, -1, 0), True), ("rear", "rest", (0, 1, 0), True),
        ("left", "rest", (1, 0, 0), True), ("right", "rest", (-1, 0, 0), True),
        ("three_quarter", "rest", (.55, -1, .21), True),
        ("jacket_only", "rest", (-.36, -1, .31), False),
        ("walk", "walk", (.30, -1, .10), True), ("run", "run", (-.38, -1, .08), True),
        ("wave", "wave", (.18, -1, .11), True), ("jump", "jump", (-.28, -1, .15), True),
    )
    cells = []
    manifest = {}
    for label, clip, direction, show_body in views:
        frame = 1. if clip == "rest" else dense["clip_summary"][clip]["min_vertex_frame"]
        API["set_pose"](scene, arm, clip, frame)
        body.hide_render = not show_body
        if clip == "rest":
            aim, data.ortho_scale = focus, .660
            scene.render.resolution_x, scene.render.resolution_y = 700, 490
        else:
            aim = (arm.pose.bones["mixamorig:Hips"].head + arm.pose.bones["mixamorig:Head"].head) / 2
            data.ortho_scale = .89
            scene.render.resolution_x = scene.render.resolution_y = 700
        camera.location = aim + 3 * Vector(direction)
        camera.rotation_euler = (aim - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / (f"_{label}.png" if clip == "rest" else f"{label}.png"))
        bpy.ops.render.render(write_still=True)
        filename = Path(scene.render.filepath)
        if clip == "rest":
            image = bpy.data.images.load(str(filename), check_existing=False)
            pixels = np.empty(700 * 490 * 4, dtype=np.float32)
            image.pixels.foreach_get(pixels)
            cells.append(pixels.reshape(490, 700, 4))
            bpy.data.images.remove(image)
            filename.unlink()
        manifest[label] = {"clip": clip, "frame": frame, "camera_direction": direction,
                           "show_body": show_body}
        if clip != "rest":
            manifest[label]["sha256"] = API["hash_file"](filename)
    # Use Blender images for the contact sheet, preserving the display colors
    # read from the six individual renders.
    separator = 8
    width, height = 2100 + 4 * separator, 980 + 3 * separator
    canvas = np.zeros((height, width, 4), dtype=np.float32)
    canvas[..., :3] = .21
    canvas[..., 3] = 1
    for i, image in enumerate(cells):
        x = separator + (i % 3) * (700 + separator)
        y = separator + (1 - i // 3) * (490 + separator)
        canvas[y:y + 490, x:x + 700] = image
    sheet = bpy.data.images.new("Studio bomber six views", width=width, height=height, alpha=False)
    sheet.pixels.foreach_set(canvas.ravel())
    sheet.filepath_raw = str(HERE / "six_view.png")
    sheet.file_format = "PNG"
    sheet.save()
    API["write_json"](HERE / "_render_manifest.json", {"glb_sha256": API["hash_file"](GLB),
        "six_view_png_sha256": API["hash_file"](HERE / "six_view.png"), "renderer": "Cycles CPU",
        "samples": scene.cycles.samples, "views": manifest})


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args == ["--verify"]:
        verify()
    elif args == ["--checkers"]:
        for stem in ("motion_check", "motion_check_tri"):
            API["run_checker"](stem)
    elif args == ["--renders"]:
        render()
    elif args == ["--rest-surface"]:
        append_rest_surface()

    elif args == ["--restore"]:
        build(restore=True)
    elif args == ["--seed"]:
        scene, arm, body, jacket, names, poses, transforms = setup()
        best, anatomical = seed_fit(jacket, body, names, poses, transforms)
        print("SELECTED SEED", best[:2], flush=True)
        np.savez_compressed(CHECKPOINT, points=best[2], weights=best[3], anatomical=anatomical)
    else:
        build(resume="--resume" in args, start=int(args[1]) if len(args) == 2 else 4)


if __name__ == "__main__":
    main()
