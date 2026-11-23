"""Fit the Studio bomber using Blender 5.1 and audit the reimported GLB.

Run with Blender in background mode. Optional arguments after -- are
--verify, --checkers, and --renders.
"""

from contextlib import redirect_stdout
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
MASTER = HERE / "../../master/GJH_Chibi_Master_rigged.blend"
MOTION = HERE / "../../../../models/tripo-chibi-motion/motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
GLB = HERE / "jacket_v1.glb"
BLEND = HERE / "jacket_v1.blend"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
TARGET = .0005
MARGIN = .00205
CAP = .030
TRIANGLE_LIMIT = 6000
ITERATIONS = 12


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_master():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER.resolve()), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    return scene, scene.objects["Armature"], scene.objects["Base_Body"]


def import_mesh(path):
    scene = bpy.context.scene
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    added = [obj for obj in scene.objects if obj not in before]
    mesh, = [obj for obj in added if obj.type == "MESH" and len(obj.data.polygons) > 100]
    return mesh, added


def mesh_points(mesh):
    coordinates = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coordinates)
    return coordinates.reshape(-1, 3)


def mesh_faces(mesh):
    mesh.calc_loop_triangles()
    indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", indices)
    return indices.reshape(-1, 3)


def update_points(garment, points):
    garment.data.vertices.foreach_set("co", np.asarray(points, dtype=np.float32).ravel())
    garment.data.update()


def weld_and_trim(garment):
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=.00001)
    mesh.normal_update()
    discard = []
    for face in mesh.faces:
        x, y, z = face.calc_center_median()
        torso_r = math.hypot(x, y + .007)
        cuff_r = math.hypot(y - .001, z - .326)
        collar_r = math.hypot(x, y + .003)
        torso_out = (face.normal.x * x + face.normal.y * (y + .007)) / max(torso_r, 1e-8)
        cuff_out = (face.normal.y * (y - .001) + face.normal.z * (z - .326)) / max(cuff_r, 1e-8)
        collar_out = (face.normal.x * x + face.normal.y * (y + .003)) / max(collar_r, 1e-8)
        hem_liner = z < .081 and (
            torso_r < .112 or (z > .011 and torso_out < -.22)
        )
        cuff_liner = abs(x) > .409 and (
            cuff_r < .035 or (abs(x) < .478 and cuff_out < -.18)
        )
        collar_liner = z > .398 and abs(x) < .127 and (
            collar_r < .076 or (z < .506 + .19 * y and collar_out < -.27)
        )
        degenerate = face.calc_area() < 1e-10
        if hem_liner or cuff_liner or collar_liner or degenerate:
            discard.append(face)
    bmesh.ops.delete(mesh, geom=discard, context="FACES")
    mesh.verts.index_update()
    remaining = set(mesh.verts)
    components = []
    for root in sorted(mesh.verts, key=lambda v: v.index):
        if root not in remaining:
            continue
        queue = [root]
        remaining.remove(root)
        for vert in queue:
            for edge in vert.link_edges:
                next_vertex = edge.other_vert(vert)
                if next_vertex in remaining:
                    remaining.remove(next_vertex)
                    queue.append(next_vertex)
        components.append(queue)
    main = set(max(components, key=len))
    bmesh.ops.delete(mesh, geom=[v for v in mesh.verts if v not in main], context="VERTS")
    for face in mesh.faces:
        face.smooth = True
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.update()
    print("TRIM", len(discard), "removed faces,", len(garment.data.polygons), "retained", flush=True)


def scale_textures(garment):
    images = sorted({
        node.image
        for material in garment.data.materials
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE" and node.image
    }, key=lambda image: image.name)
    for image in images:
        width, height = image.size
        if max(width, height) > 1024:
            ratio = 1024 / max(width, height)
            image.scale(round(width * ratio), round(height * ratio))
            image.pack()
        if max(image.size) > 1024:
            raise RuntimeError(f"Texture reduction failed for {image.name}")


def smootherstep(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def source_fit(garment):
    raw = mesh_points(garment.data)
    x, y, z = raw.T
    arm = smootherstep((abs(x) - .14) / .215)
    torso_height = np.interp(
        z, (0, .075, .20, .32, .41, .474, .5412),
        (.386, .413, .477, .538, .575, .588, .602),
    )
    sleeve_height = .565 + (z - .329) * .455
    torso_center = np.interp(
        z, (0, .12, .32, .46, .542), (-.016, -.020, -.028, -.012, -.005),
    )
    depth_scale = np.interp(z, (0, .30, .43, .542), (.535, .515, .500, .460))
    points = np.column_stack((
        x * .546 + .0007,
        (torso_center + y * depth_scale) * (1 - arm) + (-.012 + (y - .003) * .435) * arm,
        torso_height * (1 - arm) + sleeve_height * arm,
    )).astype(np.float32)
    return raw, points


def body_weights(body, names):
    groups = [names.index(group.name) for group in body.vertex_groups]
    weights = np.zeros((len(body.data.vertices), len(names)), dtype=np.float32)
    for vertex in body.data.vertices:
        for group in vertex.groups:
            weights[vertex.index, groups[group.group]] = group.weight
    return weights


def limit_weights(weights):
    indices = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    result = np.zeros_like(weights)
    np.put_along_axis(result, indices, np.take_along_axis(weights, indices, axis=1), axis=1)
    result[result < 1e-5] = 0
    return result / result.sum(axis=1, keepdims=True)


def neighbors(mesh):
    edges = np.array([tuple(edge.vertices) for edge in mesh.edges], dtype=np.int32)
    i, j = np.concatenate((edges, edges[:, ::-1]), axis=0).T
    return i, j, np.maximum(np.bincount(i, minlength=len(mesh.vertices)), 1)


def average(values, adjacency):
    i, j, degree = adjacency
    result = np.zeros_like(values)
    np.add.at(result, i, values[j])
    return result / degree.reshape((-1,) + (1,) * (values.ndim - 1))


def barycentric(triangle, p):
    a, b, c = triangle
    u, v, w = b - a, c - a, p - a
    uu, uv, vv, wu, wv = u @ u, u @ v, v @ v, w @ u, w @ v
    denominator = uu * vv - uv * uv
    if denominator <= 1e-15:
        return np.array([1., 0., 0.])
    s, t = (vv * wu - uv * wv) / denominator, (uu * wv - uv * wu) / denominator
    weights = np.clip([1 - s - t, s, t], 0, 1)
    return weights / weights.sum()


def transfer(points, raw, body, names, adjacency):
    coords = mesh_points(body.data)
    faces = mesh_faces(body.data)
    tree = BVHTree.FromPolygons(coords.tolist(), faces.tolist(), all_triangles=True)
    base = body_weights(body, names)
    result = []
    for point, original in zip(points, raw):
        x, _, z = original
        nearest, _, face, _ = tree.find_nearest(point)
        tri = faces[face]
        weights = barycentric(coords[tri], np.array(nearest)) @ base[tri]
        # A loose sleeve can be geometrically nearer the torso at its root.
        # Limit enclosed cuffs and forearms to their own arm branch.
        if abs(x) > .285:
            side = "Left" if x > 0 else "Right"
            allowed = [i for i, name in enumerate(names) if name.startswith("mixamorig:" + side)
                       and name.split(":")[-1][len(side):] in ("Arm", "ForeArm", "Hand")]
            weights[np.setdiff1d(np.arange(len(names)), allowed)] = 0
            if weights.sum() < 1e-5:
                weights[allowed[1]] = 1
        # Fingers must not pull back a cuff. Reassign their tiny transfer
        # contribution to the wrist on the same anatomical side.
        for side in ("Left", "Right"):
            hand = names.index("mixamorig:" + side + "Hand")
            fingers = [i for i, name in enumerate(names) if name.startswith(names[hand]) and i != hand]
            weights[hand] += weights[fingers].sum()
            weights[fingers] = 0
        result.append(weights / weights.sum())
    weights = np.asarray(result, dtype=np.float32)
    x, _, z = raw.T
    joint = (((abs(x) > .12) & (abs(x) < .26) & (z > .22))
             | ((abs(x) > .28) & (abs(x) < .38)) | (z < .11))
    strength = np.where(joint, .38, .12)[:, None]
    for _ in range(4):
        weights = (1 - strength) * weights + strength * average(weights, adjacency)
    return limit_weights(weights.astype(np.float32))


def load_motion(scene, arm):
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(MOTION.resolve()))
    for obj in scene.objects:
        if obj not in before:
            obj.hide_viewport = True
            obj.hide_render = True
    arm.animation_data_create()


def set_pose(scene, arm, clip, frame):
    action = bpy.data.actions[clip] if clip != "rest" else None
    data = arm.animation_data
    if data.action != action:
        data.action = action
        if action is None:
            for bone in arm.pose.bones:
                bone.matrix_basis.identity()
        else:
            data.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def frames():
    yield "rest", 1.
    for clip in CLIPS:
        a, b = bpy.data.actions[clip].frame_range
        times = {a, b, *(k / 2 for k in range(math.ceil(2 * a), math.floor(2 * b) + 1))}
        times.update(int(a + (b - a) * k / 12) for k in range(12))
        times.update(range(int(a), int(b) + 1, 3))
        yield from ((clip, frame) for frame in sorted(times))


def evaluated_surface(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        faces = mesh_faces(mesh)
        return points, faces
    finally:
        evaluated.to_mesh_clear()


@dataclass
class Pose:
    clip: str
    frame: float
    tree: BVHTree


def cache_motion(scene, arm, body):
    load_motion(scene, arm)
    bones = list(arm.pose.bones)
    modes = tuple(b.rotation_mode for b in bones)
    inverses = [b.bone.matrix_local.inverted() for b in bones]
    poses, matrices = [], []
    for clip, frame in frames():
        set_pose(scene, arm, clip, frame)
        coords, faces = evaluated_surface(body, bpy.context.evaluated_depsgraph_get())
        tree = BVHTree.FromPolygons(coords, faces.tolist(), all_triangles=True)
        poses.append(Pose(clip, frame, tree))
        matrices.append([np.asarray(b.matrix @ bind)[:3] for b, bind in zip(bones, inverses)])
    assert tuple(b.rotation_mode for b in bones) == modes
    print(f"MOTION {len(poses)} sampled poses", flush=True)
    return poses, np.asarray(matrices, dtype=np.float32)


def nearest(tree, points):
    hits = [tree.find_nearest(point) for point in points]
    coords = np.asarray([hit[0][:] for hit in hits], dtype=np.float32)
    normals = np.asarray([hit[1][:] for hit in hits], dtype=np.float32)
    signed = np.einsum("ij,ij->i", np.asarray(points, dtype=np.float32) - coords, normals)
    return signed, normals, np.asarray([hit[2] for hit in hits]), coords


def rest_clamp(points, tree, low=.0021, high=CAP - .0003):
    fitted = points.copy()
    for _ in range(6):
        distances, normals, _, _ = nearest(tree, fitted.tolist())
        clipped = np.clip(distances, low, high)
        if np.max(abs(clipped - distances)) < 1e-6:
            break
        fitted += (clipped - distances)[:, None] * normals
    return fitted


def settle_rest(points, tree, adjacency):
    # A little extra clearance on nearby vertices keeps the panels coherent
    # at narrow seams where the nearest triangle changes abruptly.
    for _ in range(4):
        dist, normal, _, _ = nearest(tree, points.tolist())
        deficit = np.maximum(.0094 - dist, 0)
        if deficit.max() < .00001:
            break
        amount = smooth_required(deficit, adjacency)
        direction = .83 * normal + .17 * average(normal, adjacency)
        points += amount[:, None] * direction
    return rest_clamp(points, tree, low=.0094)


def skin_matrices(weights, transforms):
    return (weights @ transforms.reshape(len(transforms), weights.shape[1], 12)).reshape(
        len(transforms), len(weights), 3, 4
    )


def ply_points(skin, points):
    return np.einsum("fvij,vj->fvi", skin[..., :3], points) + skin[..., 3]


def scan(points, skin, poses, triangles):
    posed = ply_points(skin, points)
    distances = np.empty(posed.shape[:2], dtype=np.float32)
    gradients = np.empty_like(posed)
    pair_counts, contacts = [], []
    faces = triangles.tolist()
    for row, pose in enumerate(poses):
        vectors = posed[row].tolist()
        dist, normal, _, _ = nearest(pose.tree, vectors)
        distances[row] = dist
        gradients[row] = np.einsum("vi,vij->vj", normal, skin[row, ..., :3])
        pairs = pose.tree.overlap(BVHTree.FromPolygons(vectors, faces, all_triangles=True))
        pair_counts.append(len(pairs))
        if pairs:
            contacts.append((row, np.asarray(pairs, dtype=np.int32)))
    return posed, distances, gradients, np.asarray(pair_counts), contacts


def clip_results(poses, distances, pairs):
    summary = {}
    for clip in ("rest", *CLIPS):
        rows = [i for i, pose in enumerate(poses) if pose.clip == clip]
        d = distances[rows]
        vertex_row, vertex = np.unravel_index(d.argmin(), d.shape)
        p = pairs[rows]
        summary[clip] = {
            "samples": len(rows),
            "max_verts_inside": int((d < 0).sum(axis=1).max()),
            "min_signed_dist_m": float(d[vertex_row, vertex]),
            "min_vertex_frame": poses[rows[vertex_row]].frame,
            "min_vertex_index": int(vertex),
            "max_triangle_pairs": int(p.max()),
            "max_pair_frame": poses[rows[int(p.argmax())]].frame if p.max() else None,
            "frames_with_overlaps": int((p > 0).sum()),
        }
    return summary


def rest_guard(before, proposed, triangles, rest_tree):
    def normals(points):
        edge1, edge2 = (points[triangles[:, k]] - points[triangles[:, 0]] for k in (1, 2))
        return np.cross(edge1, edge2)

    n0 = normals(before)
    n1 = normals(proposed)
    bad = np.einsum("fi,fi->f", n0, n1) < .15 * np.einsum("fi,fi->f", n0, n0)
    if bad.any():
        verts = np.unique(triangles[bad])
        proposed[verts] = before[verts] + .40 * (proposed[verts] - before[verts])
    return rest_clamp(proposed, rest_tree)


def score(distances, pair_counts):
    deficit = np.maximum(MARGIN - distances, 0)
    loss = (deficit * deficit).sum()
    return (int(pair_counts[0]),
            float(loss + 7e-6 * pair_counts.sum()),
            int(pair_counts.sum()), float(distances.min()))


def smooth_required(required, adjacency):
    smoothed = required.copy()
    for _ in range(3):
        smoothed = np.maximum(required, .43 * smoothed + .57 * average(smoothed, adjacency))
    return smoothed


def outward_step(distances, gradients, normals, adjacency):
    response = np.einsum("fvi,vi->fv", gradients, normals)
    required = np.where(
        (distances < MARGIN) & (response > .22),
        (MARGIN - distances) / np.maximum(response, .22),
        0,
    ).max(axis=0)
    return smooth_required(required, adjacency)[:, None] * normals


def contact_samples(posed, contacts, poses, triangles):
    weights = np.array([(a / 4, b / 4, 1 - (a + b) / 4)
                        for a in range(5) for b in range(5 - a)
                        if (a == 0) + (b == 0) + (a + b == 4) < 2], dtype=np.float32)
    for row, pairs in contacts:
        faces = np.unique(pairs[:, 1])
        indices = triangles[faces]
        samples = np.einsum("wi,fij->fwj", weights, posed[row, indices])
        signed, normals, _, _ = nearest(poses[row].tree, samples.reshape(-1, 3).tolist())
        yield row, faces, weights, signed.reshape(len(faces), -1), normals.reshape(len(faces), -1, 3)


def contact_step(contacts, posed, poses, triangles, skin, distances, gradients):
    # The vertex objective sees all frames. For triangle interiors retain
    # the highest-contact frames and a time spread across each clip.
    reduced = []
    for clip in ("rest", *CLIPS):
        group = [(row, pairs) for row, pairs in contacts if poses[row].clip == clip]
        ranked = sorted(group, key=lambda item: (-len(item[1]), item[0]))
        sampled = group[::max(1, len(group) // 4)]
        keep = {row: pairs for row, pairs in ranked[:4] + sampled}
        reduced.extend(sorted(keep.items()))
    step = np.zeros_like(posed[0])
    count = np.zeros((len(step), 1), dtype=np.float32)
    for row, faces, weights, signed, normals in contact_samples(posed, reduced, poses, triangles):
        which = signed.argmin(axis=1)
        local = np.arange(len(faces))
        depth = signed[local, which]
        mask = depth < MARGIN
        tri = triangles[faces[mask]]
        coeff = weights[which[mask]]
        gradient = np.einsum("fi,fcij->fcj", normals[local, which][mask], skin[row, tri, :, :3])
        delta = gradient * (MARGIN - depth[mask])[:, None, None] * coeff[..., None]
        np.add.at(step, tri.ravel(), delta.reshape(-1, 3))
        np.add.at(count[:, 0], tri.ravel(), coeff.ravel())
    return step / np.maximum(count, .5)


def projected_step(distances, gradients):
    # Accumulate the strongest half-frame constraints per vertex. Favor the
    # worst distances without taking a single unstable closest-face normal.
    rank = np.argpartition(distances, 8, axis=0)[:8]
    index = np.arange(distances.shape[1])[None, :]
    gaps = np.maximum(MARGIN - distances[rank, index], 0)
    influence = gaps * gaps
    step = np.einsum("fv,fvj->vj", influence * gaps, gradients[rank, index])
    return step / np.maximum(influence.sum(axis=0)[:, None], 1e-10)


def anatomy_support(raw, names):
    support = np.zeros((len(raw), len(names)), dtype=np.float32)
    x, _, z = raw.T
    sleeve_root = (abs(x) > .125) & (abs(x) < .275) & (z > .23)
    torso_side = (abs(x) > .13) & (abs(x) < .235) & (.18 < z) & (z < .37)
    for side, sign in (("Left", 1), ("Right", -1)):
        support[(sleeve_root | torso_side) & (sign * x > 0), names.index(f"mixamorig:{side}Arm")] = .25
        support[sleeve_root & (sign * x > 0), names.index(f"mixamorig:{side}Shoulder")] = .22
        support[sleeve_root & (sign * x > 0), names.index("mixamorig:Spine1")] = .20
    support[z < .12, names.index("mixamorig:Hips")] = .3
    return support


def local_search(points, raw, weights, base, distances, gradients, poses, transforms,
                 adjacency, clip_rows, support, iteration):
    displacement = projected_step(distances, gradients)
    neighborhood = average(weights, adjacency)
    affected = np.flatnonzero(distances.min(axis=0) < MARGIN)
    coordinates, result = points.copy(), weights.copy()
    axes = np.eye(3)
    diagonal = np.array([(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]) / math.sqrt(3)
    directions = np.vstack((axes, -axes, diagonal))
    radius = .0065 if iteration < 7 else .0045
    for v in affected:
        depth = distances[:, v]
        ranked = np.argsort(depth, kind="stable")
        rows = {0, *ranked[:12]}
        for clip in CLIPS:
            group = clip_rows[clip]
            rows.update(sorted(group, key=lambda i: depth[i])[:2])
        rows = np.array(sorted(rows), dtype=np.int32)
        prior = weights[v]
        p = points[v]
        move = displacement[v]
        move *= min(1., radius / max(1e-8, np.linalg.norm(move)))
        layout = np.vstack((np.zeros((1, 3)), move * np.array([.45, .8, 1.2])[:, None],
                            radius * directions, .50 * radius * directions[:6]))
        if abs(raw[v, 0]) > .432:
            layout[:, 0] *= .10
        options = [prior] * len(layout)
        candidates = list(p + layout)
        joint_support = prior + base[v] + neighborhood[v] + support[v]
        columns = np.argsort(-joint_support, kind="stable")[:6]
        for col in columns:
            if joint_support[col] < .04 or prior[col] >= .994:
                continue
            for amount in (.15, .32):
                bind = prior * (1 - amount)
                bind[col] += amount
                options.extend((bind, bind))
                candidates.extend((p, p + move * .55))
        options = limit_weights(np.array(options, dtype=np.float32))
        candidates = np.array(candidates, dtype=np.float32)
        joints = np.flatnonzero(np.sum(options, axis=0) > 0)
        bind = options[:, joints]
        matrix = transforms[rows[:, None], joints].reshape(len(rows), len(joints), 12)
        posed = (bind @ matrix).reshape(len(rows), len(bind), 3, 4)
        posed = np.einsum("roij,oj->roi", posed[..., :3], candidates) + posed[..., 3]
        test = np.asarray([nearest(poses[row].tree, pc.tolist())[0] for row, pc in zip(rows, posed)])
        gaps = np.maximum(MARGIN - test, 0)
        cost = (gaps * gaps).sum(axis=0) + 5 * gaps.max(axis=0)**2
        cost += .0014 * np.square(options - neighborhood[v]).sum(axis=1)
        cost += .12 * np.square(candidates - p).sum(axis=1)
        cost[(test[0] < .0023) | (test[0] > CAP - .00035)] = np.inf
        best = int(cost.argmin())
        if np.isfinite(cost[best]):
            coordinates[v], result[v] = candidates[best], options[best]
    change = coordinates - points
    return (points + .76 * change + .24 * average(change, adjacency),
            limit_weights((.80 * result + .20 * average(result, adjacency)).astype(np.float32)))


def keep_rest_clear(points, proposed, triangles, tree, require_clear):
    proposed = rest_guard(points, proposed, triangles, tree)
    if not require_clear:
        return proposed
    faces = triangles.tolist()
    for _ in range(4):
        pairs = tree.overlap(BVHTree.FromPolygons(proposed.tolist(), faces, all_triangles=True))
        if not pairs:
            return proposed
        affected = np.unique(triangles[np.asarray(pairs)[:, 1]])
        proposed[affected] = points[affected]
    pairs = tree.overlap(BVHTree.FromPolygons(proposed.tolist(), faces, all_triangles=True))
    return points.copy() if pairs else proposed


def subdivide(garment, triangles, points, raw, weights, contacts, initial=False):
    remaining = TRIANGLE_LIMIT - len(triangles)
    if remaining < 2 or not contacts:
        return points, raw, weights
    hits = np.bincount(np.concatenate([p[:, 1] for _, p in contacts]), minlength=len(triangles))
    candidates = {}
    for face in np.flatnonzero(hits):
        tri = triangles[face]
        edges = [tuple(sorted((int(tri[i]), int(tri[(i + 1) % 3])))) for i in range(3)]
        longest = max(edges, key=lambda edge: np.linalg.norm(points[edge[0]] - points[edge[1]]))
        length = np.linalg.norm(points[longest[0]] - points[longest[1]])
        if length > (.018 if initial else .012):
            priority = length * math.log1p(hits[face])
            candidates[longest] = max(priority, candidates.get(longest, 0))
    if not candidates:
        return points, raw, weights
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    mesh.verts.ensure_lookup_table()
    mesh.edges.ensure_lookup_table()
    layer = mesh.verts.layers.int.new("fitter_origin")
    for v in mesh.verts:
        v[layer] = v.index + 1
    lookup = {tuple(sorted(v.index for v in edge.verts)): edge for edge in mesh.edges}
    ordered = sorted(candidates, key=lambda edge: (-candidates[edge], edge))
    chosen = []
    for key in ordered:
        edge = lookup.get(key)
        if edge is not None and len(edge.link_faces) <= remaining:
            chosen.append(edge)
            remaining -= len(edge.link_faces)
        if len(chosen) >= (130 if initial else 96) or remaining < 1:
            break
    if not chosen:
        mesh.free()
        return points, raw, weights
    midpoints = {}
    for edge in chosen:
        a, b = sorted(v.index for v in edge.verts)
        position = tuple((mesh.verts[a].co + mesh.verts[b].co) * .5)
        midpoints[position] = (a, b)
    bmesh.ops.subdivide_edges(mesh, edges=chosen, cuts=1, use_grid_fill=False)
    bmesh.ops.triangulate(mesh, faces=[f for f in mesh.faces if len(f.verts) > 3])
    mesh.verts.index_update()
    new_points, new_raw, new_weights = [], [], []
    for vertex in mesh.verts:
        origin = vertex[layer] - 1
        position = tuple(vertex.co)
        pair = midpoints.get(position)
        if pair is None:
            if origin < 0:
                position = min(midpoints, key=lambda p: math.dist(p, position))
                assert math.dist(position, tuple(vertex.co)) < 1e-6
                pair = midpoints[position]
            elif math.dist(position, points[origin]) > 1e-6:
                position = min(midpoints, key=lambda p: math.dist(p, position))
                assert math.dist(position, tuple(vertex.co)) < 1e-6
                pair = midpoints[position]
        if pair is None:
            new_points.append(points[origin])
            new_raw.append(raw[origin])
            new_weights.append(weights[origin])
        else:
            a, b = pair
            new_points.append((points[a] + points[b]) / 2)
            new_raw.append((raw[a] + raw[b]) / 2)
            new_weights.append((weights[a] + weights[b]) / 2)
    mesh.verts.layers.int.remove(layer)
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.update()
    assert len(mesh_faces(garment.data)) <= TRIANGLE_LIMIT
    print("SUBDIVIDE", len(chosen), "contact edges", len(mesh_faces(garment.data)), "triangles", flush=True)
    return (np.asarray(new_points), np.asarray(new_raw), limit_weights(np.asarray(new_weights)))


def fit(garment, raw, points, body, poses, transforms, names):
    rest = poses[0].tree
    adjacency = neighbors(garment.data)
    points = settle_rest(points, rest, adjacency)
    weights = transfer(points, raw, body, names, adjacency)
    anchor = points.copy()
    base_weights = weights.copy()
    support = anatomy_support(raw, names)
    history = []
    triangles = mesh_faces(garment.data)
    skin = skin_matrices(weights, transforms)
    measurement = scan(points, skin, poses, triangles)
    clip_rows = {clip: [i for i, pose in enumerate(poses) if pose.clip == clip] for clip in CLIPS}
    for iteration in range(ITERATIONS + 1):
        posed, distances, gradients, counts, contacts = measurement
        report = clip_results(poses, distances, counts)
        loss = score(distances, counts)
        history.append({"iteration": iteration, "score": loss, "clips": report,
                        "triangles": len(triangles)})
        write_json(WORK / "solve_report.json", history)
        print("FIT", iteration, loss, "triangles", len(triangles), flush=True)
        if iteration == ITERATIONS or (not counts.any() and distances.min() >= TARGET):
            break
        if iteration in (6, 9):
            update_points(garment, points)
            before = len(points)
            points, raw, weights = subdivide(garment, triangles, points, raw, weights, contacts,
                                            initial=iteration == 6)
            if len(points) != before:
                triangles = mesh_faces(garment.data)
                adjacency = neighbors(garment.data)
                points = rest_clamp(points, rest)
                anchor = points.copy()
                base_weights = weights.copy()
                support = anatomy_support(raw, names)
                skin = skin_matrices(weights, transforms)
                measurement = scan(points, skin, poses, triangles)
                continue
        _, outward, _, _ = nearest(rest, points.tolist())
        radial = outward_step(distances, gradients, outward, adjacency)
        contact = contact_step(contacts, posed, poses, triangles, skin, distances, gradients)
        correction = projected_step(distances, gradients) + .63 * contact
        correction = .7 * correction + .3 * average(correction, adjacency)
        if iteration in (1, 3, 5, 7, 8, 10, 11):
            local, proposed_weights = local_search(
                points, raw, weights, base_weights, distances, gradients, poses,
                transforms, adjacency, clip_rows, support, iteration,
            )
            delta = .80 * (local - points) + .22 * correction
        else:
            proposed_weights = weights
            delta = .34 * radial + .69 * correction
        offset = points - anchor
        delta += .12 * (average(offset, adjacency) - offset)
        length = np.linalg.norm(delta, axis=1, keepdims=True)
        delta *= np.minimum(1., .007 / np.maximum(length, 1e-8))
        delta[abs(raw[:, 0]) > .432, 0] *= .22
        proposed = keep_rest_clear(points, points + delta, triangles, rest, counts[0] == 0)
        proposed_skin = skin if proposed_weights is weights else skin_matrices(proposed_weights, transforms)
        tested = scan(proposed, proposed_skin, poses, triangles)
        if score(tested[1], tested[3]) < loss:
            points, weights, skin, measurement = proposed, proposed_weights, proposed_skin, tested
    return points, weights


def write_weights(garment, names, weights):
    garment.vertex_groups.clear()
    for column, name in enumerate(names):
        group = garment.vertex_groups.new(name=name)
        for index in np.flatnonzero(weights[:, column]):
            group.add([int(index)], float(weights[index, column]), "REPLACE")


def tidy_rest(body, garment, points, reference_mesh, reference_points):
    """Smooth the motion bake in UV space so the source pocket welts survive."""
    uv = reference_mesh.uv_layers.active.data
    reference_mesh.calc_loop_triangles()
    uv_points = [(corner.uv.x, corner.uv.y, 0.) for corner in uv]
    loop_faces = [tri.loops[:] for tri in reference_mesh.loop_triangles]
    spatial_faces = [tri.vertices[:] for tri in reference_mesh.loop_triangles]
    uv_tree = BVHTree.FromPolygons(uv_points, loop_faces, all_triangles=True)
    uv_points = np.asarray(uv_points, dtype=np.float32)
    uv = garment.data.uv_layers.active.data
    anchor = points.copy()
    best = np.full(len(points), np.inf, dtype=np.float32)
    for loop in garment.data.loops:
        index = loop.vertex_index
        u, v = uv[loop.index].uv
        location, _, tri, distance = uv_tree.find_nearest((u, v, 0.), .00008)
        if tri is None:
            continue
        coeff = barycentric(uv_points[list(loop_faces[tri])], np.asarray(location))
        candidate = coeff @ reference_points[list(spatial_faces[tri])]
        error = np.linalg.norm(candidate - points[index])
        if error < min(.048, best[index]):
            anchor[index], best[index] = candidate, error
    adjacency = neighbors(garment.data)
    displacement = points - anchor
    filtered = displacement.copy()
    for _ in range(3):
        filtered = .48 * filtered + .52 * average(filtered, adjacency)
    x, y, z = anchor.T
    pocket = smootherstep((abs(x) - .026) / .041) * smootherstep((.136 - abs(x)) / .029)
    pocket *= smootherstep((-.045 - y) / .043) * smootherstep((z - .403) / .030)
    pocket *= smootherstep((.515 - z) / .039)
    # Match the source offsets at the pocket hems while retaining the
    # broad changes that reduce shoulder and armpit contact.
    strength = (.32 + .39 * pocket)[:, None]
    proposal = anchor + displacement * (1 - strength) + filtered * strength
    proposal -= .50 * pocket[:, None] * (proposal - anchor)
    coords, faces = evaluated_surface(body, bpy.context.evaluated_depsgraph_get())
    body_tree = BVHTree.FromPolygons(coords, faces.tolist(), all_triangles=True)
    triangles = mesh_faces(garment.data)
    overlaps = body_tree.overlap(BVHTree.FromPolygons(points.tolist(), triangles.tolist(), all_triangles=True))
    return keep_rest_clear(points, proposal, triangles, body_tree, not overlaps)


def finish_rest(body, garment, points):
    """Clamp true surface distance and the wrist span before export."""
    coords, faces = evaluated_surface(body, bpy.context.evaluated_depsgraph_get())
    tree = BVHTree.FromPolygons(coords, faces.tolist(), all_triangles=True)
    points = points.copy()
    for side in (-1, 1):
        side_x = points[:, 0] * side
        excess = side_x.max() - .2696
        if excess > 0:
            scale = smootherstep((side_x - .232) / (side_x.max() - .232))
            points[:, 0] -= side * excess * scale
    # Signed distance uses the nearest face normal. At an edge the true
    # distance can be larger, so constrain the Euclidean distance as well.
    for _ in range(4):
        dist, normal, _, near = nearest(tree, points.tolist())
        difference = points - near
        length = np.linalg.norm(difference, axis=1)
        points -= np.maximum(length - (CAP - .00035), 0)[:, None] * difference / np.maximum(length[:, None], 1e-8)
        points += np.maximum(.0015 - dist, 0)[:, None] * normal
    triangles = mesh_faces(garment.data)
    triplets = triangles.tolist()
    adjacency = neighbors(garment.data)
    for _ in range(6):
        overlaps = tree.overlap(BVHTree.FromPolygons(points.tolist(), triplets, all_triangles=True))
        if not overlaps:
            break
        affected = np.unique(triangles[np.asarray(overlaps)[:, 1]])
        strength = np.zeros(len(points), dtype=np.float32)
        strength[affected] = .0011
        strength = smooth_required(strength, adjacency)
        _, normal, _, _ = nearest(tree, points.tolist())
        cuff = abs(points[:, 0]) > .232
        radial = points[cuff] - np.column_stack((points[cuff, 0],
                                                np.full(cuff.sum(), -.012),
                                                np.full(cuff.sum(), .565)))
        normal[cuff] = radial / np.maximum(np.linalg.norm(radial, axis=1)[:, None], 1e-8)
        points += strength[:, None] * normal
    return points


def export(scene, arm, body, garment, points, names, weights):
    set_pose(scene, arm, "rest", 1.)
    arm.animation_data_clear()
    points = finish_rest(body, garment, points)
    update_points(garment, points)
    write_weights(garment, names, weights)
    garment.name = garment.data.name = "Jacket_Bomber"
    source_parent = garment.parent
    garment.parent = None
    if source_parent:
        bpy.data.objects.remove(source_parent, do_unlink=True)
    for obj in list(scene.objects):
        if obj not in (arm, body, garment):
            bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    garment.modifiers.new("Armature", "ARMATURE").object = arm
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    assert len(arm.data.bones) == 65 and len(mesh_faces(garment.data)) <= TRIANGLE_LIMIT
    bpy.ops.export_scene.gltf(
        filepath=str(GLB), export_format="GLB", use_selection=True,
        export_animations=False, export_yup=True, export_all_influences=False,
        export_def_bones=False, export_normals=True, export_texcoords=True, export_tangents=True,
    )
    garment.parent = arm
    body.hide_set(True)
    body.hide_render = True
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def build():
    scene, arm, body = open_master()
    garment, _ = import_mesh(SOURCE)
    transform = garment.matrix_world.copy()
    garment.parent = None
    garment.matrix_world.identity()
    garment.data.transform(transform)
    weld_and_trim(garment)
    scale_textures(garment)
    raw, points = source_fit(garment)
    names = tuple(bone.name for bone in arm.pose.bones)
    poses, transforms = cache_motion(scene, arm, body)
    ref_mesh = garment.data.copy()
    ref_points = settle_rest(points.copy(), poses[0].tree, neighbors(ref_mesh))
    points, weights = fit(garment, raw, points, body, poses, transforms, names)
    set_pose(scene, arm, "rest", 1.)
    points = tidy_rest(body, garment, points, ref_mesh, ref_points)
    bpy.data.meshes.remove(ref_mesh)
    export(scene, arm, body, garment, points, names, weights)


def reimport():
    scene, arm, body = open_master()
    garment, imported = import_mesh(GLB)
    garment.parent = None
    for obj in imported:
        if obj.type == "ARMATURE":
            bpy.data.objects.remove(obj, do_unlink=True)
    garment.modifiers.clear()
    garment.parent = arm
    garment.modifiers.new("Armature", "ARMATURE").object = arm
    load_motion(scene, arm)
    return scene, arm, body, garment


def zones(points):
    x, _, z = points.T
    masks = np.full(len(points), "torso panels", dtype="<U24")
    masks[z < .414] = "ribbed hem"
    masks[(abs(x) > .098) & (z > .505)] = "shoulder and armpit"
    masks[abs(x) > .155] = "sleeves"
    masks[abs(x) > .234] = "ribbed cuffs"
    masks[(abs(x) < .075) & (z > .582)] = "stand collar"
    return masks


def verify():
    scene, arm, body, garment = reimport()
    triangles = mesh_faces(garment.data)
    names = tuple(b.name for b in arm.pose.bones)
    rest_points = mesh_points(garment.data)
    region = zones(rest_points)
    gfaces = triangles.tolist()
    face_joint = np.asarray(names)[body_weights(body, names)[mesh_faces(body.data)].sum(axis=1).argmax(axis=1)]
    poses, distances, pair_counts, failures = [], [], [], []
    witnesses, residual_zones = {}, {}
    rest_absolute = None
    for clip, frame in frames():
        set_pose(scene, arm, clip, frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        body_coords, faces = evaluated_surface(body, depsgraph)
        coords, _ = evaluated_surface(garment, depsgraph)
        tree = BVHTree.FromPolygons(body_coords, faces.tolist(), all_triangles=True)
        pose = Pose(clip, frame, tree)
        poses.append(Pose(clip, frame, None))
        signed, _, hits, locations = nearest(tree, coords)
        if clip == "rest":
            rest_absolute = np.linalg.norm(np.asarray(coords, dtype=np.float32) - locations, axis=1)
        distances.append(signed)
        pairs = tree.overlap(BVHTree.FromPolygons(coords, gfaces, all_triangles=True))
        pair_counts.append(len(pairs))
        if signed.min() >= TARGET and not pairs:
            continue
        idx = int(signed.argmin())
        row = {"clip": clip, "frame": frame, "inside": int((signed < 0).sum()),
               "pairs": len(pairs), "min_signed_dist_m": float(signed[idx]),
               "vertex_zone": str(region[idx]), "body_joint": str(face_joint[hits[idx]]),
               "garment_side": "Left" if rest_points[idx, 0] > .025 else
                               "Right" if rest_points[idx, 0] < -.025 else "Center"}
        for idx in np.flatnonzero(signed < TARGET):
            key = (clip, str(region[idx]), str(face_joint[hits[idx]]))
            if key not in residual_zones or signed[idx] < residual_zones[key]["min_signed_dist_m"]:
                residual_zones[key] = {"clip": clip, "zone": key[1], "body_joint": key[2],
                                       "frame": frame, "min_signed_dist_m": float(signed[idx])}
        if pairs:
            unique, counts = np.unique(np.array(pairs)[:, 1], return_counts=True)
            most_hit = triangles[unique[counts.argmax()]]
            row["most_intersected_face_zone"] = str(region[most_hit[0]])
            xyz = np.asarray(coords, dtype=np.float32)[None]
            _, face_ids, grid, depth, _ = next(contact_samples(
                xyz, [(0, np.asarray(pairs))], [pose], triangles
            ))
            i, j = np.unravel_index(depth.argmin(), depth.shape)
            row["surface_witness_m"] = float(depth[i, j])
            surface_triangle = triangles[face_ids[i]]
            row["surface_witness_zone"] = str(region[surface_triangle[0]])
            witness = grid[j] @ xyz[0, surface_triangle]
            row["surface_witness_body_joint"] = str(face_joint[tree.find_nearest(witness)[2]])
        failures.append(row)
        if clip not in witnesses or row["min_signed_dist_m"] < witnesses[clip]["min_signed_dist_m"]:
            witnesses[clip] = row
    distances = np.asarray(distances)
    results = clip_results(poses, distances, np.asarray(pair_counts))
    statistics = {}
    for label in ("all", *sorted(set(region))):
        d = distances[0] if label == "all" else distances[0][region == label]
        statistics[label] = dict(zip(("min", "p10", "median", "p90", "p95", "max"),
                                     map(float, np.percentile(d, [0, 10, 50, 90, 95, 100]))))
        statistics[label]["vertices"] = len(d)
    rest = mesh_points(garment.data)
    rest_cuffs = [rest[rest[:, 0] > .234, 0].max(), rest[rest[:, 0] < -.234, 0].min()]
    hem = rest[region == "ribbed hem", 2]
    report = {"glb_sha256": hash_file(GLB), "poses": len(poses), "clips": results,
              "rest_clearance_m": statistics, "rest_euclidean_max_m": float(rest_absolute.max()),
              "rest_bounds_m": [rest.min(axis=0).tolist(), rest.max(axis=0).tolist()],
              "cuff_x_extrema_m": list(map(float, rest_cuffs)),
              "hem_z_range_m": [float(hem.min()), float(hem.max())],
              "worst_vertices": witnesses, "failed_poses": failures,
              "zone_residuals": [residual_zones[key] for key in sorted(residual_zones)]}
    write_json(HERE / "dense_check.json", report)
    for clip, values in results.items():
        print("DENSE", clip, values, flush=True)


def run_checker(stem):
    path = WORK / f"{stem}.py"
    source = path.read_text()
    workbench = ("sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
                 "sc.display.shading.color_type='MATERIAL'")
    assert source.count(workbench) == 1
    assert source.count("bpy.ops.render.render(write_still=True)") == 1
    source = source.replace(workbench, "")
    source = source.replace("bpy.ops.render.render(write_still=True)", "None")
    source = source.replace("{out}/motion_check.json", "{out}/" + stem + ".json")
    captured = io.StringIO()
    argv = sys.argv
    try:
        sys.argv = [str(path), "--", str(MASTER.resolve()), str(MOTION.resolve()), str(GLB), str(HERE)]
        with redirect_stdout(captured):
            exec(compile(source, str(path), "exec"), {})
    finally:
        sys.argv = argv
    lines = [line for line in captured.getvalue().splitlines() if line.startswith("RESULT ")]
    assert len(lines) == 8
    (HERE / f"{stem}.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


def render():
    scene, arm, body, garment = reimport()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
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
    output = HERE / "renders"
    output.mkdir(exist_ok=True)
    records = {}
    for name, direction, show_body in (
        ("rest_front", (0, -1, 0), True),
        ("rest_back", (0, 1, 0), True),
        ("rest_left", (1, 0, 0), True),
        ("rest_right", (-1, 0, 0), True),
        ("rest_three_quarter", (.55, -1, .21), True),
        ("rest_jacket_only", (-.36, -1, .31), False),
        ("walk", (.30, -1, .10), True),
        ("run", (-.38, -1, .08), True),
        ("wave", (.18, -1, .11), True),
        ("jump", (-.28, -1, .15), True),
    ):
        clip = "rest" if name.startswith("rest_") else name
        frame = 1.
        if clip != "rest":
            start, end = bpy.data.actions[clip].frame_range
            frame = float(int(start + (end - start) * .4))
        set_pose(scene, arm, clip, frame)
        body.hide_render = not show_body
        if clip == "rest":
            aim = focus
            data.ortho_scale = .655 if show_body else .625
            scene.render.resolution_x, scene.render.resolution_y = 860, 560
        else:
            aim = (arm.pose.bones["mixamorig:Hips"].head + arm.pose.bones["mixamorig:Head"].head) / 2
            data.ortho_scale = .94
            scene.render.resolution_x, scene.render.resolution_y = 690, 690
        camera.location = aim + 3 * Vector(direction)
        camera.rotation_euler = (aim - camera.location).to_track_quat("-Z", "Y").to_euler()
        filename = output / f"{name}.png"
        scene.render.filepath = str(filename)
        bpy.ops.render.render(write_still=True)
        records[name] = {"clip": clip, "frame": frame, "view": direction,
                         "show_body": show_body, "sha256": hash_file(filename)}
    write_json(output / "manifest.json", {"glb_sha256": hash_file(GLB), "renderer": "Cycles CPU",
                                         "samples": scene.cycles.samples, "images": records})


def inspect_export():
    glb = GLB.read_bytes()
    magic, version, size, json_size = struct.unpack_from("<4sIII", glb)
    assert (magic, version, size) == (b"glTF", 2, len(glb))
    data = json.loads(glb[20:20 + json_size])
    blob = glb[28 + json_size:]
    assert len(data["meshes"]) == len(data["skins"]) == 1 and not data.get("animations")
    joints = [data["nodes"][index]["name"] for index in data["skins"][0]["joints"]]
    _, arm, _ = open_master()
    assert len(joints) == 65 and set(joints) == {bone.name for bone in arm.data.bones}
    triangles = vertices = max_influences = 0
    for primitive in data["meshes"][0]["primitives"]:
        attributes = primitive["attributes"]
        assert primitive.get("mode", 4) == 4 and "WEIGHTS_1" not in attributes and "TEXCOORD_0" in attributes
        triangles += data["accessors"][primitive["indices"]]["count"] // 3
        accessor = data["accessors"][attributes["WEIGHTS_0"]]
        vertices += accessor["count"]
        assert accessor["type"] == "VEC4" and accessor["componentType"] == 5126
        view = data["bufferViews"][accessor["bufferView"]]
        start = accessor.get("byteOffset", 0) + view.get("byteOffset", 0)
        for i in range(accessor["count"]):
            weights = struct.unpack_from("<4f", blob, start + i * view.get("byteStride", 16))
            assert abs(sum(weights) - 1) < 1e-5 and min(weights) >= 0
            max_influences = max(max_influences, sum(weight > 0 for weight in weights))
    assert triangles <= TRIANGLE_LIMIT and max_influences <= 4
    # Reimport images to validate embedded formats and dimensions as Blender sees them.
    _, _ = import_mesh(GLB)
    garment_images = [image for image in bpy.data.images if image.name in {x.get("name") for x in data["images"]}]
    assert len(garment_images) == len(data["images"])
    assert all(max(image.size) <= 1024 and image.packed_file for image in garment_images)
    dimensions = [{"name": image.name, "size": list(image.size)} for image in garment_images]
    report = {"glb_sha256": hash_file(GLB), "blend_sha256": hash_file(BLEND),
              "source_sha256": hash_file(SOURCE), "glb_bytes": len(glb), "blend_bytes": BLEND.stat().st_size,
              "meshes": len(data["meshes"]), "animations": len(data.get("animations", [])),
              "joints": joints, "max_influences": max_influences, "triangles": triangles,
              "vertices": vertices, "textures": dimensions}
    write_json(HERE / "export_check.json", report)
    print("EXPORT", {key: value for key, value in report.items() if key != "joints"}, flush=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--verify" in args:
        inspect_export()
        verify()
    elif "--checkers" in args:
        run_checker("motion_check")
        run_checker("motion_check_tri")
    elif "--renders" in args:
        render()
    else:
        build()


if __name__ == "__main__":
    main()
