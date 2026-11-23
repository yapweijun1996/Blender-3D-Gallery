"""Refine the Round 2 skinned pants against the corrected master actions.

Run in Blender 5.1. The reproduction commands in NOTES.md build and refine
the Round 2 checkpoint, smooth the binding, and verify the exported GLB.
"""

from collections import defaultdict
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import runpy
import sys

import bmesh
import bpy
import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "round2/pants_v2.glb"
DESTINATION = Path(os.environ.get("PANTS_ROUND3_OUTPUT", HERE)).resolve()
if not DESTINATION.is_relative_to(HERE):
    raise ValueError("Output must be inside round3")
OUTPUT = DESTINATION / "pants_v3.glb"
MOTION = HERE.parents[2] / "body-fix/motion_fixed.glb"
ROUND2 = runpy.run_path(str(SOURCE.with_name("fit_pants_r2.py")))
BASE = ROUND2["BASE"]
BASE.update(HERE=DESTINATION, GLB=OUTPUT, MOTION=MOTION, TRIANGLE_LIMIT=8000)
CLIPS = ("rest", *BASE["CLIPS"])
MARGIN = .002
MINIMUM = .0005
LIMIT = .030
STEPS = 16

coords = BASE["coordinates"]
triangles = BASE["triangles"]
signed_hits = BASE["signed_hits"]
tree_for = BASE["tree_for"]
average = BASE["average"]
unit = BASE["unit"]
trim_weights = BASE["trim_weights"]


def load_fit():
    scene, arm, body = BASE["load_master"]()
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE), merge_vertices=True)
    imported = [obj for obj in scene.objects if obj not in before]
    garment, = [obj for obj in bpy.context.selected_objects if obj in imported and obj.type == "MESH"]
    garment.parent = None
    for obj in imported:
        if obj != garment:
            bpy.data.objects.remove(obj, do_unlink=True)
    garment.modifiers.clear()
    garment.parent = arm
    garment.modifiers.new("Master armature", "ARMATURE").object = arm
    BASE["load_actions"]()
    names = tuple(arm.data.bones.keys())
    body_faces = triangles(body.data)
    samples, transforms = BASE["cache_motion"](scene, arm, body, names, body_faces)
    weights = trim_weights(BASE["body_weights"](garment, names))
    return arm, body, garment, names, body_faces, samples, transforms, weights


def print_results(stats, label):
    for clip, row in stats.items():
        print(label, clip, row["max_verts_inside"], row["max_triangle_pairs"],
              round(row["min_signed_distance_m"] * 1000, 4), row["minimum_frame"],
              row["minimum_zone"], flush=True)


def measure(points, skin, faces, samples, body_faces):
    posed = BASE["pose_points"](points, skin)
    regions = defaultdict(dict)
    distance, pairs, constraints, cuts, failures = BASE["scan"](
        posed, faces, samples, body_faces, points, collect=True, zone_details=regions)
    stats = BASE["report_metrics"](distance, pairs, samples, points, failures)
    return distance, pairs, constraints, cuts, stats, regions


def loss(distance, pairs):
    gap = (MARGIN - distance).clip(0) * 1000
    failure = (MINIMUM - distance).clip(0) * 1000
    ceiling = (distance[0] - LIMIT).clip(0) * 1000
    return float(3 * pairs.sum() + 2 * (failure ** 2).sum() +
                 8 * (failure.max(axis=0) ** 2).sum() + .12 * (gap ** 2).sum() +
                 2000 * (ceiling ** 2).sum())


def checkpoint_loss(distance, pairs):
    gap = (MARGIN - distance).clip(0) * 1000
    ceiling = (distance[0] - LIMIT).clip(0) * 1000
    return float(2 * pairs.sum() + (gap ** 2).sum() +
                 6 * (gap.max(axis=0) ** 2).sum() + 100 * (ceiling ** 2).sum())


def cap(points, original, rest_tree):
    move = points - original
    span = np.linalg.norm(move, axis=1).clip(1e-9)
    points = original + move * np.minimum(1, LIMIT / span)[:, None]
    points[:, 2] = points[:, 2].clip(.067, .433)
    return BASE["rest_project"](points, rest_tree, lo=.00085, hi=.0297)


def linear_planes(points, weights, skin, transforms, constraints, adjacency, rest_tree,
                  target, rebind):
    """Pull back posed nearest-surface normals through linear blend skinning."""
    local_joints = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    local_weights = np.take_along_axis(weights, local_joints, axis=1)
    weight_scale = .06
    vertices, directions, requirements = [], [], []
    for row, ids, bary, distance, normal in constraints:
        active = distance < target
        ids, bary, distance, normal = ids[active], bary[active], distance[active], normal[active]
        if not len(ids):
            continue
        jacobian = np.einsum("ni,nkij->nkj", normal, skin[row, ids, :, :3])
        if rebind and row:
            bones = transforms[row, local_joints[ids]]
            posed = np.einsum("nkbic,nkc->nkbi", bones[..., :3], points[ids]) + bones[..., 3]
            valid = local_weights[ids] > 0
            center = (posed * valid[..., None]).sum(axis=-2) / valid.sum(axis=-1)[..., None]
            grad = np.einsum("ni,nkbi->nkb", normal, posed - center[:, :, None])
            jacobian = np.concatenate((jacobian, grad * valid / weight_scale), axis=-1)
        elif rebind:
            jacobian = np.pad(jacobian, ((0, 0), (0, 0), (0, 4)))
        usable = bary >= .15
        # A witness on a triangle distributes its clearance deficit over
        # the corners. At a vertex the entire deficit goes to that vertex.
        fractions = bary * usable
        impact = (fractions * bary).sum(axis=1).clip(.2)
        vertices.append(ids[usable])
        directions.append(jacobian[usable])
        requirements.append(((target - distance).clip(0, LIMIT)[:, None] * fractions /
                             impact[:, None])[usable])
    ids = np.concatenate(vertices)
    gradients = np.concatenate(directions)
    depth = np.concatenate(requirements)
    norm = np.square(gradients).sum(axis=1).clip(.1)

    # Start with the deepest required move per vertex. Additional passes
    # resolve other time samples and spread the offsets to adjacent vertices.
    step = np.zeros((len(points), gradients.shape[1]), dtype=np.float32)
    peak = np.zeros(len(points), dtype=np.float32)
    rest_distance, rest_normal = signed_hits(rest_tree, points)
    for sweep in range(18):
        if sweep in (2, 5, 8):
            step = .78 * step + .22 * average(step, adjacency)
        residual = depth - np.einsum("ni,ni->n", gradients, step[ids])
        peak.fill(0)
        np.maximum.at(peak, ids, residual)
        active = np.flatnonzero((residual == peak[ids]) & (residual > 1e-6))
        worst = np.full(len(points), -1, dtype=np.int32)
        np.maximum.at(worst, ids[active], active)
        active = worst[worst >= 0]
        step[ids[active]] += (.9 * residual[active] / norm[active])[:, None] * gradients[active]
        height = (step[:, :3] * rest_normal).sum(axis=1) + rest_distance
        step[:, :3] += (height.clip(.001, .0298) - height)[:, None] * rest_normal
    binding = weights.copy()
    if rebind:
        values = (local_weights + step[:, 3:] / weight_scale).clip(0, 1)
        values[local_weights == 0] = 0
        np.put_along_axis(binding, local_joints, values, axis=1)
        binding = trim_weights(binding)
    return step[:, :3], binding


def weight_columns(weights, initial, natural, neighbor):
    blends = np.vstack((weights, initial, natural, neighbor,
                        .55 * weights + .45 * natural, .25 * weights + .75 * natural,
                        .6 * weights + .4 * neighbor, .3 * weights + .7 * neighbor))
    joints = np.flatnonzero(blends.max(axis=0) > .018)
    joints = np.union1d(joints, np.flatnonzero(weights))
    axes = np.eye(len(joints), dtype=np.float32)
    local = weights[joints]
    blends = np.vstack((blends[:, joints], .8 * local + .2 * axes,
                        .5 * local + .5 * axes, .2 * local + .8 * axes, axes))
    # Keep the incumbent first after removing equivalent hypotheses.
    blends = trim_weights(blends)
    _, indices = np.unique(blends.round(4), axis=0, return_index=True)
    return joints, blends[np.sort(indices)]


def local_search(points, weights, original, initial, natural, samples, transforms,
                 distance, contacts, adjacency, radius, faces, direct=False,
                 exact_pairs=False, checkpoint_search=False):
    """Try exact local point and joint blends where a linearized plane is ambiguous."""
    min_distance = distance.min(axis=0)
    by_vertex = defaultdict(list)
    for row, ids, bary, signed, _ in contacts:
        if ids.shape[1] != 3:
            continue
        for face, fraction, value in zip(ids, bary, signed):
            for corner in np.flatnonzero(fraction >= .16):
                vertex = face[corner]
                min_distance[vertex] = min(min_distance[vertex], value)
                by_vertex[vertex].append((float(value), row, face, fraction, corner))
    active = np.flatnonzero(min_distance < MARGIN)
    active = active[np.argsort(min_distance[active], kind="stable")][:420]
    clip_rows = [np.asarray([i for i, sample in enumerate(samples) if sample[0] == clip])
                 for clip in CLIPS[1:]]
    points, weights = points.copy(), weights.copy()
    near_points = original + average(points - original, adjacency)
    near_weights = trim_weights(average(weights, adjacency))
    skin = BASE["skin_matrices"](weights, transforms)
    incident = defaultdict(list)
    if exact_pairs:
        for face in faces:
            for vertex in face:
                incident[vertex].append(face)
    grid = unit(np.asarray([v for v in product((-1., 0., 1.), repeat=3) if any(v)],
                           dtype=np.float32))
    rest_tree = samples[0][2]
    changes = 0
    for vertex in active:
        current, bind = points[vertex].copy(), weights[vertex].copy()
        frames = {0}
        for rows in clip_rows:
            for band in np.array_split(rows, 5):
                if len(band) and distance[band, vertex].min() < max(.013, 2 * radius):
                    frames.add(int(band[distance[band, vertex].argmin()]))
        frames = sorted(frames)
        witnesses, seen = [], set()
        for entry in sorted(by_vertex.get(vertex, ()), key=lambda record: record[:2]):
            _, row, face, fraction, corner = entry
            key = (row // 3, *face)
            if key not in seen:
                seen.add(key)
                matrix = skin[row, face]
                posed = np.einsum("nij,nj->ni", matrix[..., :3], points[face]) + matrix[..., 3]
                fixed = fraction @ posed - fraction[corner] * posed[corner]
                witnesses.append((row, fraction[corner], fixed))
            if len(witnesses) == 14:
                break
        rows = frames + [w[0] for w in witnesses]
        joints, choices = weight_columns(bind, initial[vertex], natural[vertex], near_weights[vertex])
        bones = transforms[np.ix_(rows, joints)]
        home = near_points[vertex]

        def triangle_counts(anchors, binding):
            """Score incident triangles directly instead of assuming each witness represents the face."""
            if vertex not in incident or not witnesses:
                return np.zeros(len(anchors), dtype=np.float32)
            patch = np.asarray(incident[vertex])
            affected, patch_indices = np.unique(patch, return_inverse=True)
            patch_faces = patch_indices.reshape(-1, 3).tolist()
            changed = int(np.searchsorted(affected, vertex))
            collision_rows = {row for row, _, _ in witnesses}
            collision_rows.update(frames)
            collision_rows = sorted(collision_rows)
            matrices = BASE["skin_matrices"](binding, transforms[np.ix_(collision_rows, joints)])
            pose = np.einsum("fnij,nj->fni", matrices[..., :3], anchors) + matrices[..., 3]
            counts = np.zeros(len(anchors), dtype=np.float32)
            for row, amended in zip(collision_rows, pose):
                matrix = skin[row, affected]
                rest_patch = np.einsum("nij,nj->ni", matrix[..., :3], points[affected]) + matrix[..., 3]
                for option, coordinate in enumerate(amended):
                    rest_patch[changed] = coordinate
                    counts[option] += len(samples[row][2].overlap(tree_for(rest_patch, patch_faces)))
            return counts

        def scores(anchors, binding):
            measured, _ = signed_hits(rest_tree, anchors)
            valid = ((measured >= .0007) & (measured <= .02984)
                     & (np.linalg.norm(anchors - original[vertex], axis=1) <= LIMIT)
                     & (anchors[:, 2] >= .067) & (anchors[:, 2] <= .433))
            out = np.full(len(anchors), np.inf)
            if not valid.any():
                return out
            position, influence = anchors[valid], binding[valid]
            mats = BASE["skin_matrices"](influence, bones)
            posed = np.einsum("fnij,nj->fni", mats[..., :3], position) + mats[..., 3]
            for index, (_, coefficient, fixed) in enumerate(witnesses, len(frames)):
                posed[index] = fixed + coefficient * posed[index]
            field = np.asarray([signed_hits(samples[row][2], xyz)[0]
                                for row, xyz in zip(rows, posed)])
            wanted = np.full((len(rows), 1), MARGIN)
            wanted[0] = .0008
            miss = (wanted - field).clip(0) * 1000
            value = 2.6 * np.square(miss.max(axis=0)) + np.square(miss).sum(axis=0) * .38
            value += .024 * np.square((position - home) * 1000).sum(axis=1)
            value += .008 * np.square((position - original[vertex]) * 1000).sum(axis=1)
            value += 2.6 * np.square(influence - near_weights[vertex, joints]).sum(axis=1)
            out[valid] = value
            return out

        offsets = np.vstack((np.zeros(3), grid * radius, grid * radius * 2.2, home - current))
        anchors = current + offsets
        anchors[1:] = BASE["rest_project"](anchors[1:], rest_tree, lo=.00085, hi=.0297)
        same_weights = np.broadcast_to(bind[joints], (len(anchors), len(joints)))
        position_scores = scores(anchors, same_weights)
        best_positions = np.unique(np.r_[0, np.argsort(position_scores)[:5]])
        bindings = np.tile(choices, (len(best_positions), 1))
        alternatives = np.repeat(anchors[best_positions], len(choices), axis=0)
        weight_scores = scores(alternatives, bindings)
        if direct:
            positions = np.vstack((anchors, alternatives))
            bindings = np.vstack((same_weights, bindings))
            initial_scores = np.r_[position_scores, weight_scores]
            finalists = np.unique(np.r_[0, np.argsort(initial_scores, kind="stable")[:12]])
            ranked = initial_scores[finalists]
            if vertex in incident and witnesses:
                ranked += 2.8 * triangle_counts(positions[finalists], bindings[finalists])
            winner = int(finalists[ranked.argmin()])
            candidate, candidate_weights = positions[winner], bindings[winner]
        else:
            best = int(weight_scores.argmin())
            if weight_scores[best] + .0001 < position_scores[0]:
                candidate, candidate_weights = alternatives[best], bindings[best]
            elif position_scores.min() + .0001 < position_scores[0]:
                candidate, candidate_weights = anchors[position_scores.argmin()], bind[joints]
            else:
                continue
        # Refine position around the selected blend with the actual pose BVHs.
        refined = candidate + np.vstack((np.zeros(3), grid * radius * .45, grid * radius * 1.15))
        refined[1:] = BASE["rest_project"](refined[1:], rest_tree, lo=.00085, hi=.0297)
        refined_score = scores(refined, np.broadcast_to(candidate_weights, (len(refined), len(joints))))
        if vertex in incident and witnesses:
            options = np.unique(np.r_[0, np.argsort(refined_score, kind="stable")[:8]])
            refined_binding = np.broadcast_to(candidate_weights, (len(options), len(joints)))
            refined_score[options] += 2.8 * triangle_counts(refined[options], refined_binding)
            candidate = refined[options[refined_score[options].argmin()]]
        else:
            candidate = refined[refined_score.argmin()]
        if not checkpoint_search:
            axes = np.eye(len(joints), dtype=np.float32)
            fine_blends = trim_weights(np.vstack((candidate_weights,
                .92 * candidate_weights + .08 * axes, .8 * candidate_weights + .2 * axes,
                (1.11 * candidate_weights - .11 * axes).clip(0))))
            fine_score = scores(np.broadcast_to(candidate, (len(fine_blends), 3)), fine_blends)
            if direct:
                final_positions = np.vstack((current, np.broadcast_to(candidate, (len(fine_blends), 3))))
                final_bindings = np.vstack((bind[joints], fine_blends))
                final_scores = np.r_[position_scores[0], fine_score]
                options = np.unique(np.r_[0, np.argsort(final_scores, kind="stable")[:7]])
                adjusted = final_scores[options]
                if vertex in incident and witnesses:
                    adjusted += 2.8 * triangle_counts(final_positions[options], final_bindings[options])
                winner = int(options[adjusted.argmin()])
                if winner == 0:
                    continue
                candidate, candidate_weights = final_positions[winner], final_bindings[winner]
            else:
                candidate_weights = fine_blends[fine_score.argmin()]
        points[vertex] = candidate
        weights[vertex] = 0
        weights[vertex, joints] = candidate_weights
        skin[:, vertex] = BASE["skin_matrices"](weights[vertex:vertex+1], transforms)[:, 0]
        changes += 1
    print("LOCAL SEARCH", len(active), changes, "radius_mm", radius * 1000, flush=True)
    return points, weights


def add_support(garment, points, weights, original, distance, contacts, skin):
    """Shift triangles from short flat edges to the repeatedly cut garment panels."""
    frequency = defaultdict(int)
    lengths = defaultdict(float)
    for row, ids, _, _, _ in contacts:
        if ids.shape[1] != 3:
            continue
        pose = skin[row, ids]
        posed = np.einsum("nkij,nkj->nki", pose[..., :3], points[ids]) + pose[..., 3]
        for first in range(3):
            second = (first + 1) % 3
            spans = np.linalg.norm(posed[:, first] - posed[:, second], axis=1)
            for a, b, span in zip(ids[:, first], ids[:, second], spans):
                key = min(a, b), max(a, b)
                frequency[key] += 1
                lengths[key] = max(lengths[key], float(span))
    if not frequency:
        return None

    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    mesh.verts.index_update()
    deform = mesh.verts.layers.deform.verify()
    source = [mesh.verts.layers.float.new(f"source_{axis}") for axis in "xyz"]
    uv = mesh.loops.layers.uv.active
    for vertex in mesh.verts:
        index = vertex.index
        vertex.co = points[index]
        vertex[deform].clear()
        for joint in np.flatnonzero(weights[index]):
            vertex[deform][int(joint)] = float(weights[index, joint])
        for axis, layer in enumerate(source):
            vertex[layer] = float(original[index, axis])
    mesh.normal_update()
    contact_edges, short_edges = [], []
    critical = {int(vertex) for edge in frequency for vertex in edge}
    safety = distance.min(axis=0)
    for edge in mesh.edges:
        key = tuple(sorted(vertex.index for vertex in edge.verts))
        span = edge.calc_length()
        if key in frequency and max(span, lengths[key]) > .012:
            contact_edges.append((0, -frequency[key], -max(span, lengths[key]), key, edge))
        elif key in frequency and span > .006:
            center = points[list(key)].mean(axis=0)
            if (BASE["zone"](center) == "crotch / inner thigh"
                    or (abs(center[0]) < .065 and .245 < center[2] < .340)):
                contact_edges.append((1, -frequency[key], -span, key, edge))
        if not (edge.is_manifold and edge.is_contiguous and span < .0025):
            continue
        neighborhood = {v.index for endpoint in edge.verts for face in endpoint.link_faces
                        for v in face.verts}
        if not critical.isdisjoint(neighborhood) or min(safety[list(neighborhood)]) < .0038:
            continue
        a, b = edge.link_faces
        if a.normal.dot(b.normal) < .95:
            continue
        if uv and any((next(loop[uv].uv for loop in a.loops if loop.vert == v)
                       - next(loop[uv].uv for loop in b.loops if loop.vert == v)).length > 1e-6
                      for v in edge.verts):
            continue
        short_edges.append((span, key, edge, neighborhood))
    wanted = [record[-1] for record in sorted(contact_edges, key=lambda x: x[:-1])[:96]]
    if not wanted:
        mesh.free()
        return None
    available = 8000 - len(triangles(garment.data))
    reserved = sum(len(edge.link_faces) for edge in wanted)
    selected, occupied = [], set()
    for _, _, edge, neighborhood in sorted(short_edges, key=lambda row: row[:2]):
        if available + 2 * len(selected) >= reserved:
            break
        if occupied.isdisjoint(neighborhood):
            selected.append(edge)
            occupied.update(neighborhood)
    if selected:
        bmesh.ops.collapse(mesh, edges=selected, uvs=True)
    available = 8000 - sum(len(face.verts) - 2 for face in mesh.faces)
    splitting = []
    for edge in wanted:
        count = len(edge.link_faces)
        if count <= available:
            splitting.append(edge)
            available -= count
    if not splitting:
        mesh.free()
        return None
    bmesh.ops.subdivide_edges(mesh, edges=splitting, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(mesh, faces=[face for face in mesh.faces if len(face.verts) > 3])
    mesh.verts.index_update()
    binding = np.zeros((len(mesh.verts), weights.shape[1]), dtype=np.float32)
    anchors = np.empty((len(mesh.verts), 3), dtype=np.float32)
    for vertex in mesh.verts:
        for joint, value in vertex[deform].items():
            binding[vertex.index, joint] = value
        anchors[vertex.index] = [vertex[layer] for layer in source]
    for layer in source:
        mesh.verts.layers.float.remove(layer)
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.update()
    assert len(triangles(garment.data)) <= 8000
    print("LOCAL SUPPORT", len(splitting), "split edges", len(selected), "collapsed edges", flush=True)
    return coords(garment.data), trim_weights(binding), anchors


def outer_contact_planes(points, skin, weights, faces, samples, body_faces, pairs,
                         rest_tree, body, names):
    """Push underlying leg protrusions past the full cloth face at the collision."""
    body_regions = BASE["body_weights"](body, names)[body_faces].sum(axis=1).argmax(axis=1)
    lower = np.asarray([any(label in name for label in ("Leg", "Hips", "Foot", "Toe"))
                        for name in names])
    rest_normal = signed_hits(rest_tree, points[faces].mean(axis=1))[1]
    rest_cross = np.cross(points[faces[:, 1]] - points[faces[:, 0]],
                          points[faces[:, 2]] - points[faces[:, 0]])
    side = np.where((rest_cross * rest_normal).sum(axis=1) >= 0, 1, -1)
    restrictions = []
    face_list = faces.tolist()
    for row in np.flatnonzero(pairs):
        if row == 0:
            continue
        _, _, surface, body_points = samples[row]
        posed = np.einsum("vij,vj->vi", skin[row, ..., :3], points) + skin[row, ..., 3]
        hit = np.asarray(surface.overlap(tree_for(posed, face_list)), dtype=np.int32).reshape(-1, 2)
        b, g = hit[lower[body_regions[hit[:, 0]]]].T
        if not len(b):
            continue
        panel = posed[faces[g]]
        normal = unit(np.cross(panel[:, 1] - panel[:, 0], panel[:, 2] - panel[:, 0]))
        normal *= side[g, None]
        b_world = body_points[body_faces[b]]
        height = np.einsum("nki,ni->nk", b_world - panel[:, :1], normal)
        bary = BASE["barycentric"](np.repeat(panel, 3, axis=0), b_world.reshape(-1, 3))
        z = height.ravel()
        active = (bary.min(axis=1) >= -.09) & (z > -.0003) & (z < .018)
        if not active.any():
            continue
        bary = bary[active].clip(0, 1)
        bary /= bary.sum(axis=1, keepdims=True)
        restrictions.append((row, faces[np.repeat(g, 3)[active]], bary, -z[active],
                             np.repeat(normal, 3, axis=0)[active]))
    return restrictions


def build(baseline=False, direct=False, checkpoint=None, checkpoint_search=False):
    arm, body, garment, names, body_faces, samples, transforms, weights = load_fit()
    points = coords(garment.data)
    original = points.copy()
    faces = triangles(garment.data)
    adjacency = BASE["mesh_neighbors"](garment.data)
    rest_tree = samples[0][2]
    initial = weights.copy()
    natural = BASE["transfer_weights"](points, samples[0][3], body_faces,
                                       BASE["body_weights"](body, names), rest_tree,
                                       adjacency, names)
    history = []
    start = 0
    if checkpoint:
        source_history = json.loads((checkpoint / "fit_history.json").read_text())
        start = source_history["selected_iteration"]
        history = [value for value in source_history["iterations"] if value["iteration"] < start]
        with bpy.data.libraries.load(str(checkpoint / "pants_v3.blend"), link=False) as (_, data):
            data.objects = ["pants_v3"]
        fitted, = data.objects
        assert np.array_equal(triangles(fitted.data), faces), "Checkpoint topology differs from Round 2"
        garment.data = fitted.data.copy()
        points = coords(fitted.data)
        weights = BASE["body_weights"](fitted, names)
        bpy.data.objects.remove(fitted, do_unlink=True)
    skin = BASE["skin_matrices"](weights, transforms)
    current = measure(points, skin, faces, samples, body_faces)
    print_results(current[4], "CHECKPOINT" if checkpoint else "ROUND2 BASELINE")
    if baseline:
        return
    best = None
    last_support = -5
    score_fit = checkpoint_loss if checkpoint_search else loss
    for iteration in range(start, STEPS + 1):
        distance, pairs, contacts, _, summaries, regions = current
        clean = not pairs.any() and distance.min() >= MINIMUM and distance[0].max() <= LIMIT
        score = score_fit(distance, pairs)
        print("ITERATION", iteration, round(score, 5), "clean", clean, flush=True)
        print_results(summaries, "DENSE")
        history.append({"iteration": iteration, "score": score, "clips": summaries})
        if (not pairs[0] and distance[0].min() >= MINIMUM and distance[0].max() <= LIMIT
                and (best is None or clean or score < best[0])):
            if best is not None:
                bpy.data.meshes.remove(best[4])
            best = score, iteration, points.copy(), weights.copy(), garment.data.copy()
        if clean or iteration == STEPS:
            break
        support = None
        support_slots = (start,) if checkpoint else (5, 10)
        if not checkpoint_search and iteration in support_slots and pairs.any():
            support = add_support(garment, points, weights, original, distance, contacts, skin)
        if support is not None:
            points, weights, original = support
            faces = triangles(garment.data)
            adjacency = BASE["mesh_neighbors"](garment.data)
            initial = weights.copy()
            natural = BASE["transfer_weights"](points, samples[0][3], body_faces,
                                                BASE["body_weights"](body, names), rest_tree,
                                                adjacency, names)
            skin = BASE["skin_matrices"](weights, transforms)
            current = measure(points, skin, faces, samples, body_faces)
            last_support = iteration
            continue
        if (iteration >= 2 and (iteration % 2 == 0 or iteration == last_support + 1)) or score < 200:
            radius = .004 if score > 10000 else .002 if score > 300 else .0008
            position, binding = local_search(points, weights, original, initial, natural,
                                             samples, transforms, distance, contacts, adjacency, radius,
                                             faces, direct=direct, exact_pairs=direct and score < 15000,
                                             checkpoint_search=checkpoint_search)
            step = position - points
        else:
            demand = contacts
            if checkpoint and pairs.any():
                demand = contacts + outer_contact_planes(points, skin, weights, faces, samples,
                                                          body_faces, pairs, rest_tree, body, names)
            step, binding = linear_planes(points, weights, skin, transforms, demand, adjacency,
                                          rest_tree, MARGIN, rebind=iteration > 1)
        for gain in (1., .5, .25):
            trial = ROUND2["shape_guard"](
                points, cap(points + gain * step, original, rest_tree), faces, rest_tree)
            trial_binding = trim_weights(weights + gain * (binding - weights))
            trial_skin = BASE["skin_matrices"](trial_binding, transforms)
            candidate = measure(trial, trial_skin, faces, samples, body_faces)
            if score_fit(*candidate[:2]) < score:
                points, weights, skin, current = trial, trial_binding, trial_skin, candidate
                break
        else:
            print("LINEAR FIT STALLED", iteration, dict(regions), flush=True)
            if checkpoint_search:
                break
            if iteration > 11 and not pairs.any() and distance.min() < MINIMUM:
                # Use the hard deficit to break a tie when the 2 mm soft
                # target conflicts with stable sub-margin points.
                step, binding = linear_planes(points, weights, skin, transforms, contacts, adjacency,
                                              rest_tree, .001, rebind=True)
                trial = ROUND2["shape_guard"](points, cap(points + step, original, rest_tree),
                                               faces, rest_tree)
                trial_skin = BASE["skin_matrices"](binding, transforms)
                candidate = measure(trial, trial_skin, faces, samples, body_faces)
                if score_fit(*candidate[:2]) < score:
                    points, weights, skin, current = trial, binding, trial_skin, candidate
    assert best is not None
    _, step, points, weights, mesh = best
    garment.data = mesh
    (DESTINATION / "fit_history.json").write_text(json.dumps({"selected_iteration": step,
        "iterations": history}, indent=2) + "\n")
    BASE["export"](garment, arm, body, points, weights, names, save_blend=False)
    ROUND2["save_module_blend"].__globals__.update(HERE=DESTINATION, GLB=OUTPUT)
    ROUND2["save_module_blend"]()


def verify():
    BASE["verify"]()
    path = DESTINATION / "dense_check.json"
    data = json.loads(path.read_text())
    data["motion_sha256"] = hashlib.sha256(MOTION.read_bytes()).hexdigest()
    data["source_sha256"] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    data["texture_matches_round2_bytes"] = {
        key: value == ROUND2["texture_hashes"](SOURCE)[key]
        for key, value in ROUND2["texture_hashes"](OUTPUT).items()}
    path.write_text(json.dumps(data, indent=2) + "\n")


def load_binding():
    scene, arm, body = BASE["load_master"]()
    with bpy.data.libraries.load(str(OUTPUT.with_suffix(".blend")), link=False) as (_, data):
        data.objects = ["pants_v3"]
    garment, = data.objects
    scene.collection.objects.link(garment)
    garment.parent = arm
    garment.modifiers.clear()
    garment.modifiers.new("Master armature", "ARMATURE").object = arm
    BASE["load_actions"]()
    names = tuple(arm.data.bones.keys())
    points = coords(garment.data)
    faces, body_faces = triangles(garment.data), triangles(body.data)
    neighbors = BASE["mesh_neighbors"](garment.data)
    samples, transforms = BASE["cache_motion"](scene, arm, body, names, body_faces)
    weights = BASE["body_weights"](garment, names)
    return arm, body, garment, names, points, faces, body_faces, neighbors, samples, transforms, weights


def export_binding(garment, arm, body, points, weights, names):
    BASE["export"](garment, arm, body, points, weights, names, save_blend=False)
    # The currently loaded library is the old deliverable. Write the editable
    # revision to a sibling first to avoid Blender's library guard.
    saver = ROUND2["save_module_blend"]
    staged = OUTPUT.with_name(".smooth_v3.glb")
    saver.__globals__["GLB"] = staged
    try:
        saver()
        staged.with_suffix(".blend").replace(OUTPUT.with_suffix(".blend"))
    finally:
        saver.__globals__["GLB"] = OUTPUT


def smooth_binding():
    """Re-smooth the hip and knee binding, retaining the measured collision gains."""
    arm, body, garment, names, points, faces, body_faces, neighbors, samples, transforms, weights = load_binding()
    current = measure(points, BASE["skin_matrices"](weights, transforms), faces, samples, body_faces)
    z = points[:, 2]
    joint_area = np.maximum(np.exp(-((z - .340) / .059) ** 2),
                            np.exp(-((z - .215) / .045) ** 2))
    clear = current[0].min(axis=0)
    clear = np.minimum(clear, average(clear, neighbors))

    def preserves(candidate):
        for clip, row in current[4].items():
            proposed = candidate[4][clip]
            if proposed["max_triangle_pairs"] > row["max_triangle_pairs"]:
                return False
            if proposed["max_verts_inside"] > row["max_verts_inside"]:
                return False
            if proposed["min_signed_distance_m"] < min(MINIMUM, row["min_signed_distance_m"] - 1e-6):
                return False
        return True

    for strength, clear_only in ((.25, False), (.10, False), (.10, True), (.035, True)):
        amount = joint_area * strength
        if clear_only:
            amount *= ((clear - .003) / .005).clip(0, 1)
        binding = weights.copy()
        for _ in range(2):
            binding = trim_weights(binding + amount[:, None] * (average(binding, neighbors) - binding))
        result = measure(points, BASE["skin_matrices"](binding, transforms), faces, samples, body_faces)
        if not preserves(result):
            continue
        print("SMOOTH ACCEPTED", strength, "clear_only", clear_only, flush=True)
        export_binding(garment, arm, body, points, binding, names)
        break
    else:
        print("SMOOTH REJECTED all gains failed the collision comparison", flush=True)


def smooth_outliers():
    """Ease unusually stretched weight transitions while preserving every sampled contact count."""
    arm, body, garment, names, points, faces, _, neighbors, samples, transforms, weights = load_binding()
    skin = BASE["skin_matrices"](weights, transforms)
    posed = BASE["pose_points"](points, skin)
    local = trim_weights(average(weights, neighbors))
    run = [i for i, s in enumerate(samples) if s[0] == "run"]
    target_skin = BASE["skin_matrices"](local, transforms[run])
    neighbors_pose = BASE["pose_points"](points, target_skin)
    gap = np.linalg.norm(neighbors_pose - posed[run], axis=-1).max(axis=0)
    order = np.argsort(-gap, kind="stable")
    accepted = []
    for vertex in order[:40]:
        if gap[vertex] < .004:
            break
        if not .155 < points[vertex, 2] < .395:
            continue
        patch = faces[(faces == vertex).any(axis=1)]
        if not len(patch):
            continue
        affected, inverse = np.unique(patch, return_inverse=True)
        face_list = inverse.reshape(-1, 3).tolist()
        index = int(np.searchsorted(affected, vertex))
        candidate = trim_weights(np.vstack([weights[vertex] + gain * (local[vertex] - weights[vertex])
                                           for gain in (1., .65, .35, .16)]))
        response = BASE["skin_matrices"](candidate, transforms)
        moved = np.einsum("fwik,k->fwi", response[..., :3], points[vertex]) + response[..., 3]
        allowed = np.ones(len(candidate), dtype=bool)
        for row, (_, _, tree, _) in enumerate(samples):
            xyz = posed[row, affected].copy()
            old, _ = signed_hits(tree, xyz[index:index + 1])
            old_pairs = len(tree.overlap(tree_for(xyz, face_list)))
            distances, _ = signed_hits(tree, moved[row])
            allowed &= distances >= min(.0005, old[0] - 1e-7)
            for option in np.flatnonzero(allowed):
                xyz[index] = moved[row, option]
                allowed[option] = len(tree.overlap(tree_for(xyz, face_list))) <= old_pairs
            if not allowed.any():
                break
        if allowed.any():
            best = np.flatnonzero(allowed)[0]
            weights[vertex] = candidate[best]
            displacement = float(np.linalg.norm(moved[run, best] - posed[run, vertex], axis=-1).max())
            posed[:, vertex] = moved[:, best]
            accepted.append((int(vertex), round(displacement * 1000, 3)))
    print("OUTLIER SMOOTHING", len(accepted), accepted, flush=True)
    if accepted:
        export_binding(garment, arm, body, points, weights, names)


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    ROUND2["renders"].__globals__.update(HERE=DESTINATION, GLB=OUTPUT)
    stages = {"baseline": lambda: build(baseline=True), "build-loft": build,
              "build-direct": lambda: build(direct=True),
              "build-checkpoint": lambda: build(checkpoint_search=True),
              "polish": lambda: build(direct=True, checkpoint=HERE / ".runtime/local"),
              "smooth": smooth_binding, "smooth-outliers": smooth_outliers,
              "cap-rest": ROUND2["cap_reexport"],
              "verify": verify, "renders": ROUND2["renders"]}
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["verify"]
    for stage in args:
        stages[stage]()


if __name__ == "__main__":
    main()
