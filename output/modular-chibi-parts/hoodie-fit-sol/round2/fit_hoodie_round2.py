"""Fit round one's editable hoodie with Blender 5.1, then check the exported GLB.

Run in background mode with --python-exit-code 1 --python fit_hoodie_round2.py.
Use -- --baseline to measure round one's GLB, or -- --verify to check v2 only.
"""

import hashlib
import json
import math
import runpy
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
ROUND1 = HERE.parent
PRIOR = runpy.run_path(str(ROUND1 / "fit_hoodie.py"))
MASTER, MOTION, CLIPS = (PRIOR[key] for key in ("MASTER", "MOTION", "CLIPS"))
NAME = "top_hoodie_v2"
GLB = HERE / (NAME + ".glb")
TARGET = 0.0005
MARGIN = 0.0008
FIT_FLOOR = 0.00057
REST_FLOOR = 0.0022
OFFSET_LIMIT = 0.020
TORSO_LIMIT = 0.020
ITERATIONS = 6
mesh_points = PRIOR["mesh_points"]
mesh_triangles = PRIOR["mesh_triangles"]
adjacency = PRIOR["adjacency"]
average = PRIOR["average"]


def read_weights(mesh_object, names, validate=True):
    columns = [names.index(group.name) for group in mesh_object.vertex_groups]
    weights = np.zeros((len(mesh_object.data.vertices), len(names)), dtype=np.float32)
    for vertex in mesh_object.data.vertices:
        for group in vertex.groups:
            weights[vertex.index, columns[group.group]] = group.weight
    if validate:
        assert np.allclose(weights.sum(axis=1), 1, atol=1e-5)
        assert ((weights > 0).sum(axis=1) <= 4).all()
    return weights


def set_pose(scene, arm, name, frame):
    action = bpy.data.actions[name] if name != "rest" else None
    arm.animation_data.action = action
    if action:
        arm.animation_data.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def load_motion(scene, arm, body, garment):
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in scene.objects:
        if obj.type in {"MESH", "ARMATURE"} and obj not in (arm, body, garment):
            obj.hide_viewport = True
            obj.hide_render = True
    arm.animation_data_create()


def frames():
    yield "rest", 1
    for name in CLIPS:
        first, last = bpy.data.actions[name].frame_range
        # Include every integer frame, both endpoints, and any earlier frame
        # reached by truncation in the manager's 12-point sampler.
        times = {*range(math.ceil(first), math.floor(last) + 1), first, last}
        times.update(int(first + (last - first) * k / 12) for k in range(12))
        for frame in sorted(times):
            yield name, frame


def body_surface(body, depsgraph):
    posed = body.evaluated_get(depsgraph)
    mesh = posed.to_mesh()
    try:
        coordinates = [posed.matrix_world @ vertex.co for vertex in mesh.vertices]
        faces = [poly.vertices[:] for poly in mesh.polygons]
        return BVHTree.FromPolygons(coordinates, faces)
    finally:
        posed.to_mesh_clear()


def clearance(tree, point):
    nearest, normal, _, _ = tree.find_nearest(point)
    return (Vector(point) - nearest).dot(normal)


def nearest_details(tree, point):
    nearest, normal, face, _ = tree.find_nearest(point)
    return (Vector(point) - nearest).dot(normal), tuple(normal), face


def cache_motion(scene, arm, body, garment, names):
    load_motion(scene, arm, body, garment)
    bones = [arm.pose.bones[name] for name in names]
    inverse_bind = [bone.bone.matrix_local.inverted() for bone in bones]
    samples, transforms = [], []
    for name, frame in frames():
        set_pose(scene, arm, name, frame)
        assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
        assert np.allclose(garment.matrix_world, np.eye(4), atol=1e-6)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        samples.append((name, frame, body_surface(body, depsgraph)))
        matrix = np.array([bone.matrix @ inv for bone, inv in zip(bones, inverse_bind)])
        transforms.append(matrix[:, :3, :])
    print("DENSE SAMPLE COUNT", len(samples), flush=True)
    return samples, np.asarray(transforms, dtype=np.float32)


def skin_matrices(transforms, weights):
    flat = transforms.reshape(len(transforms), len(weights[0]), 12)
    return (weights @ flat).reshape(len(flat), len(weights), 3, 4)


def evaluate(points, samples, skin, normals=False):
    posed = np.einsum("fvij,vj->fvi", skin[..., :3], points) + skin[..., 3]
    shape = posed.shape[:2]
    distances = np.empty(shape, dtype=np.float32)
    gradients = np.zeros_like(posed) if normals else None
    for row, (_, _, tree) in enumerate(samples):
        for vertex, position in enumerate(posed[row].tolist()):
            nearest, normal, _, _ = tree.find_nearest(position)
            distance = (Vector(position) - nearest).dot(normal)
            distances[row, vertex] = distance
            if normals and distance < MARGIN:
                gradients[row, vertex] = normal
    if normals:
        gradients = np.einsum("fvi,fvij->fvj", gradients, skin[..., :3])
    return distances, gradients


def summarize(distances, samples):
    result = {}
    for name in ("rest", *CLIPS):
        rows = [index for index, (clip, _, _) in enumerate(samples) if clip == name]
        d = distances[rows]
        row, vertex = np.unravel_index(d.argmin(), d.shape)
        result[name] = {
            "samples": len(rows),
            "max_verts_inside": int((d < 0).sum(axis=1).max()),
            "min_signed_dist": float(d[row, vertex]),
            "worst_frame": samples[rows[row]][1],
        }
    return result


def zones(points):
    x, y, z = points.T
    collar = (z >= 0.546) & (y < -0.071) & (abs(x) <= 0.075)
    hood = (z >= 0.595) | ((z >= 0.547) & (y >= 0.055))
    sleeves = ~(hood | collar) & (abs(x) >= 0.129)
    armpits = ~(hood | collar) & ~sleeves & (abs(x) >= 0.086) & (z >= 0.478)
    hem = ~(hood | collar) & ~sleeves & ~armpits & (z < 0.426)
    return {
        "torso": ~(hood | collar | sleeves),
        "torso_body": ~(hood | collar | sleeves | armpits | hem),
        "hem": hem,
        "shoulder_armpit": armpits,
        "sleeve": sleeves & (abs(x) < 0.235),
        "cuff": sleeves & (abs(x) >= 0.235),
        "collar": collar & ~hood,
        "hood": hood,
    }


def stats(distances):
    values = np.quantile(distances, [0, 0.1, 0.5, 0.9, 0.95, 1])
    return {"count": len(distances), **dict(zip(("min", "p10", "median", "p90", "p95", "max"),
                                               map(float, values)))}


def scaled_directions(count):
    height = 1 - 2 * (np.arange(count) + 0.5) / count
    angle = np.arange(count) * np.pi * (3 - np.sqrt(5))
    radius = np.sqrt(1 - height ** 2)
    return np.column_stack((radius * np.cos(angle), radius * np.sin(angle), height))


def project_to_limit(offsets):
    scale = np.minimum(1, OFFSET_LIMIT / np.maximum(np.linalg.norm(offsets, axis=-1), 1e-9))
    return offsets * scale[..., None]


def smooth_floor(required, neighbors):
    smoothed = required[:, None]
    for _ in range(3):
        smoothed = 0.55 * smoothed + 0.45 * average(smoothed, neighbors)
    return np.maximum(required, smoothed[:, 0]).clip(0, OFFSET_LIMIT)


def normal_step(points, original, normals, distances, gradients, neighbors):
    """Bake enough offset to meet the worst positive outward requirement."""
    derivative = np.einsum("fvi,vi->fv", gradients, normals)
    required = np.divide(
        np.maximum(0, MARGIN - distances), derivative,
        out=np.zeros_like(distances), where=derivative > 0.30,
    ).max(axis=0)
    offset = np.einsum("vi,vi->v", points - original, normals)
    required = np.clip(offset + required, 0, OFFSET_LIMIT)
    baked = smooth_floor(required, neighbors)
    return original + normals * baked[:, None]


def candidate_clearance(choices, vertex, sample_rows, samples, skin):
    matrix = skin[sample_rows, vertex]
    posed = np.einsum("sij,cj->sci", matrix[..., :3], choices) + matrix[:, None, :, 3]
    return np.array([
        [clearance(samples[row][2], p) for p in positions]
        for row, positions in zip(sample_rows, posed.tolist())
    ])


def surface_cost(values, rest, torso):
    violation = np.maximum(0, MARGIN - values)
    violation[0] = np.maximum(0, REST_FLOOR - rest)
    excess = np.where(torso, np.maximum(0, rest - 0.01995), 0)
    violation = np.vstack((violation, 1.8 * excess))
    return violation.max(axis=0) + 0.13 * np.sqrt(np.square(violation).sum(axis=0))


class RestShape:
    """Reject local triangle flips and contacts as one rest vertex moves."""

    def __init__(self, mesh, points, tree):
        self.tree = tree
        self.triangles = np.array(mesh_triangles(mesh))
        coordinates = points[self.triangles]
        self.normals = np.cross(coordinates[:, 1] - coordinates[:, 0], coordinates[:, 2] - coordinates[:, 0])
        incidence = [[] for _ in points]
        for row, face in enumerate(self.triangles):
            for vertex in face:
                incidence[vertex].append(row)
        self.incidence = [np.array(rows, dtype=np.int32) for rows in incidence]

    def accepts(self, vertex, choice, points):
        if np.linalg.norm(choice - points[vertex]) < 1e-8:
            return True
        rows = self.incidence[vertex]
        if not len(rows):
            return True
        triangles = self.triangles[rows]
        coordinates = points[triangles].copy()
        coordinates[triangles == vertex] = choice
        normals = np.cross(coordinates[:, 1] - coordinates[:, 0], coordinates[:, 2] - coordinates[:, 0])
        reference = self.normals[rows]
        old_area = np.linalg.norm(reference, axis=1)
        area = np.linalg.norm(normals, axis=1)
        agreement = (normals * reference).sum(axis=1)
        stable = old_area > 4e-8
        if ((agreement < 0.28 * area * old_area) & stable).any():
            return False
        if (((area > old_area * 3.7) | (area < old_area * .22)) & stable).any():
            return False
        patch = BVHTree.FromPolygons(coordinates.reshape(-1, 3).tolist(),
                                     [(i, i+1, i+2) for i in range(0, 3 * len(rows), 3)], all_triangles=True)
        return not self.tree.overlap(patch)

    def choose(self, vertex, choices, values, quality, points, torso, factor=5):
        rest = values[0]
        # A seam can move a point into the torso region in the exported mesh.
        torso_mask = torso | zones(choices)["torso"]
        passing = (values.min(axis=0) >= FIT_FLOOR) & (~torso_mask | (rest <= TORSO_LIMIT - 0.00004))
        score = surface_cost(values, rest, torso_mask)
        order = np.argsort(np.where(passing, score + quality, factor * score + quality + 0.1), kind="stable")
        return next(i for i in order if self.accepts(vertex, choices[i], points))

    def compress_torso(self, points, neighbors):
        """Take in the upper torso just enough to leave 20 mm of rest clearance."""
        torso = zones(points)["torso"]
        hits = [nearest_details(self.tree, p) for p in points]
        distances = np.array([hit[0] for hit in hits])
        normals = np.array([hit[1] for hit in hits])
        required = np.where(torso, np.maximum(0, distances - (TORSO_LIMIT - .00035)), 0)
        offset = -normals * smooth_floor(required, neighbors)[:, None]
        for vertex in np.flatnonzero(np.linalg.norm(offset, axis=1) > 0.000025):
            start = points[vertex]
            for amount in (1., .7, .45, .22):
                choice = start + amount * offset[vertex]
                if self.accepts(vertex, choice, points):
                    points[vertex] = choice
                    break



def candidate_quality(choices, vertex, points, triangles, normals, centers, original):
    """Penalize a change that turns or pinches a neighboring triangle."""
    if not len(triangles):
        return np.linalg.norm(choices - original, axis=1)
    coordinates = np.broadcast_to(points[triangles], (len(choices), len(triangles), 3, 3)).copy()
    coordinates[:, triangles == vertex] = choices[:, None]
    corner_normals = np.cross(coordinates[:, :, 1] - coordinates[:, :, 0],
                              coordinates[:, :, 2] - coordinates[:, :, 0])
    areas = np.linalg.norm(corner_normals, axis=2)
    reference = np.linalg.norm(normals, axis=1).clip(1e-10)
    similarity = (corner_normals * normals).sum(axis=2) / (areas.clip(1e-10) * reference)
    fold = np.maximum(0, 0.45 - similarity).mean(axis=1)
    pinch = np.maximum(0, 0.30 - areas / reference).mean(axis=1)
    stretch = np.maximum(0, areas / reference - 2.7).mean(axis=1)
    return (0.09 * np.linalg.norm(choices - centers, axis=1)
            + 0.025 * np.linalg.norm(choices - original, axis=1)
            + 0.0016 * fold + 0.001 * pinch + 0.00045 * stretch)


def refine(points, original, baseline, distances, gradients, samples, skin, neighbors, shape, torso):
    """Loosen only failing patches, checking alternative inverse-skinned directions."""
    points = points.copy()
    all_rows = np.arange(len(samples))
    directions = scaled_directions(66)
    relative = (np.array([.002, .004, .007, .011, .015, .020])[:, None, None] * directions).reshape(-1, 3)
    local = (np.array([.0007, .0016, .0030, .005])[:, None, None] * directions[::2]).reshape(-1, 3)
    neighborhood = average(points - original, neighbors) + original
    worst = distances.min(axis=0)
    failing = (worst < MARGIN) | (torso & (distances[0] > 0.01995))
    print("LOCAL CANDIDATES", int(failing.sum()), flush=True)

    by_clip = [np.array([r for r, (clip, _, _) in enumerate(samples) if clip == name]) for name in CLIPS]
    for vertex in np.flatnonzero(failing)[np.argsort(worst[failing], kind="stable")]:
        current = points[vertex]
        ranked = distances[:, vertex].argsort(kind="stable")
        selected = set(ranked[:15])
        for clip_rows in by_clip:
            selected.update(clip_rows[np.argsort(distances[clip_rows, vertex], kind="stable")[:2]])
        selected.add(0)
        rows = np.array(sorted(selected))
        deficit = np.maximum(0, MARGIN - distances[rows, vertex])
        gradient = gradients[rows, vertex]
        moves = deficit[:, None] * gradient / (gradient ** 2).sum(axis=1).clip(0.09)[:, None]
        normal_choices = current + (np.array([.9, 1.25, 1.8, 2.8])[:, None, None] * moves).reshape(-1, 3)
        choices = np.vstack((current, neighborhood[vertex], baseline[vertex], original[vertex],
                             normal_choices, original[vertex] + relative, current + local,
                             original[vertex] + np.array([.25, .50, .75])[:, None]
                             * (baseline[vertex] - original[vertex])))
        choices = original[vertex] + project_to_limit(choices - original[vertex])
        values = candidate_clearance(choices, vertex, rows, samples, skin)
        score = surface_cost(values, values[0], torso[vertex])
        incident = shape.incidence[vertex]
        quality = candidate_quality(choices, vertex, points, shape.triangles[incident], shape.normals[incident],
                                    neighborhood[vertex], original[vertex])
        # Keep both the best geometry and the best clearance from the shortlist.
        ranked_options = np.unique(np.r_[0, np.argsort(score + quality, kind="stable")[:27],
                                          np.argsort(score, kind="stable")[:15]])
        finalists = np.array([idx for idx in ranked_options if shape.accepts(vertex, choices[idx], points)])
        values = candidate_clearance(choices[finalists], vertex, all_rows, samples, skin)
        index = shape.choose(vertex, choices[finalists], values, quality[finalists], points, torso[vertex])
        points[vertex] = choices[finalists[index]]
    return points


def limit_weights(weights):
    order = np.argsort(-weights, axis=-1, kind="stable")[..., :4]
    limited = np.zeros_like(weights)
    np.put_along_axis(limited, order, np.take_along_axis(weights, order, axis=-1), axis=-1)
    limited[limited < 0.00005] = 0
    total = limited.sum(axis=-1, keepdims=True)
    assert (total > 0).all()
    return limited / total


def nearest_body_weights(points, body, names, tree):
    body_points = mesh_points(body.data)
    body_weights = read_weights(body, names, validate=False)
    result = []
    for point in points:
        closest, _, face, _ = tree.find_nearest(point)
        corners = np.array(body.data.polygons[face].vertices)
        vertex = body_points[corners]
        uv = np.linalg.lstsq((vertex[1:] - vertex[0]).T, np.array(closest) - vertex[0], rcond=None)[0]
        barycentric = np.r_[1 - uv.sum(), uv].clip(0, 1)
        result.append(barycentric @ body_weights[corners])
    return limit_weights(np.array(result, dtype=np.float32))


def weight_options(current, original, neighborhood, body, anatomical):
    fractions = np.array([0.15, 0.33, 0.57, 0.80, 1.0], dtype=np.float32)[:, None, None]
    columns = np.unique(np.r_[np.flatnonzero(current > 0.055), np.flatnonzero(original > 0.10),
                              np.argsort(-body)[:3], np.argsort(-neighborhood)[:3], anatomical])
    identity = np.eye(len(current), dtype=np.float32)
    families = np.vstack((original[None], neighborhood[None], body[None], identity[columns]))
    blends = current + fractions * (families - current)
    donors = np.flatnonzero(current > 0.05)
    transfers = (identity[columns][None] - identity[donors][:, None]) * current[donors, None, None]
    transfers = current + fractions * transfers.reshape(1, -1, len(current))
    choices = limit_weights(np.vstack((current, blends.reshape(-1, len(current)),
                                      transfers.reshape(-1, len(current)))))
    _, unique = np.unique(np.round(choices, 6), axis=0, return_index=True)
    return choices[np.sort(unique)]


def posed_weight_options(positions, weights, rows, transforms, samples, paired=False):
    joint_positions = np.einsum("sbij,cj->sbci", transforms[rows, ..., :3], positions)
    joint_positions += transforms[rows, :, None, :, 3]
    if paired:
        posed = np.einsum("cb,sbci->sci", weights, joint_positions)
    else:
        posed = np.einsum("wb,sbci->swci", weights, joint_positions).reshape(len(rows), -1, 3)
    return np.array([[clearance(samples[row][2], point) for point in candidates]
                     for row, candidates in zip(rows, posed.tolist())])


def refine_weights(points, weights, original, original_weights, body_weights, names, distances, samples,
                   transforms, neighbors, shape, torso, iteration):
    """Retune only persistent contacts, using the skin already on the adjacent patch."""
    indices = np.arange(len(samples))
    regions = zones(original)
    simple_names = [name.removeprefix("mixamorig:") for name in names]
    neighborhood = limit_weights(average(weights, neighbors))
    mean_points = original + average(points - original, neighbors)
    by_clip = [indices[[n == name for n, _, _ in samples]] for name in CLIPS]
    failing = np.flatnonzero(distances.min(axis=0) < MARGIN)
    counts = 0
    for vertex in failing:
        x, _, _ = original[vertex]
        side = "Left" if x > 0 else "Right"
        neighborhood_bones = ["Hips", "Spine", "Spine1", "Spine2"]
        if regions["hem"][vertex]:
            neighborhood_bones += ["LeftUpLeg", "RightUpLeg"]
        if regions["shoulder_armpit"][vertex] or regions["sleeve"][vertex] or regions["cuff"][vertex]:
            neighborhood_bones += [side + joint for joint in ("Shoulder", "Arm", "ForeArm")]
        if regions["collar"][vertex] or regions["hood"][vertex]:
            neighborhood_bones += ["Neck", "Head"]
        choices = weight_options(weights[vertex], original_weights[vertex], neighborhood[vertex],
                                 body_weights[vertex], [simple_names.index(n) for n in neighborhood_bones])
        rows = np.unique(np.r_[0, np.argsort(distances[:, vertex], kind="stable")[:16],
                               [r for group in by_clip for r in
                                group[np.argsort(distances[group, vertex], kind="stable")[:2]]]])
        point = points[vertex]
        positions = np.array([point, mean_points[vertex], original[vertex],
                              0.5 * (point + original[vertex])], dtype=np.float32)
        scores = posed_weight_options(positions, choices, rows, transforms, samples)
        trial_weights = np.repeat(choices, len(positions), axis=0)
        trial_points = np.tile(positions, (len(choices), 1))
        motion_cost = surface_cost(scores, scores[0], torso[vertex])
        regularizer = (0.00072 * np.abs(trial_weights - neighborhood[vertex]).sum(axis=1)
                       + 0.00026 * np.abs(trial_weights - original_weights[vertex]).sum(axis=1)
                       + 0.052 * np.linalg.norm(trial_points - mean_points[vertex], axis=1))
        finalists = np.unique(np.r_[0, np.argsort(motion_cost + regularizer, kind="stable")[:15],
                                    np.argsort(motion_cost, kind="stable")[:12]])
        values = posed_weight_options(trial_points[finalists], trial_weights[finalists], indices, transforms, samples, paired=True)
        motion_cost = surface_cost(values, values[0], torso[vertex])
        best = shape.choose(vertex, trial_points[finalists], values, regularizer[finalists], points, torso[vertex])
        index = finalists[best]
        if index:
            points[vertex] = trial_points[index]
            weights[vertex] = trial_weights[index]
            counts += 1
    print("LOCAL SKIN", iteration, len(failing), counts, flush=True)


def compound_clearance(positions, weights, rows, transforms, samples):
    """Check independent position/skin pairs against the posed body surfaces."""
    active = np.flatnonzero(np.any(weights, axis=0))
    flat = transforms[rows][:, active].reshape(len(rows), len(active), 12)
    matrices = (weights[:, active] @ flat).reshape(len(rows), len(weights), 3, 4)
    posed = np.einsum("scij,cj->sci", matrices[..., :3], positions) + matrices[..., 3]
    return np.array([[clearance(samples[row][2], point) for point in candidates]
                     for row, candidates in zip(rows, posed.tolist())])


def linearized_moves(point, weight, columns, rows, transforms, samples, torso):
    """Pull posed surface normals back to rest position and skin-weight space."""
    motion = transforms[rows][:, columns]
    joint_points = motion[..., :3] @ point + motion[..., 3]
    posed = np.einsum("sbi,b->si", joint_points, weight[columns])
    hits = [nearest_details(samples[row][2], p) for row, p in zip(rows, posed)]
    distances = np.array([hit[0] for hit in hits])
    normals = np.array([hit[1] for hit in hits])
    positions = np.einsum("si,sbij,b->sj", normals, motion[..., :3], weight[columns])
    weights = np.einsum("si,sbi->sb", normals, joint_points)
    weights -= weights.mean(axis=1, keepdims=True)
    scales = np.r_[np.ones(3), np.full(len(columns), 18.0)]
    gradient = np.column_stack((positions, weights)) * scales
    deficit = MARGIN - distances
    if torso:
        gradient = np.vstack((gradient, -gradient[0]))
        deficit = np.r_[deficit, distances[0] - (TORSO_LIMIT - .00015)]
    positive = np.flatnonzero(deficit > 0)
    if not len(positive):
        return np.zeros((1, len(scales)))
    normals_sq = np.square(gradient).sum(axis=1).clip(.045)
    order = positive[np.argsort(-deficit[positive], kind="stable")[:8]]
    moves = [(deficit[i] * gradient[i] / normals_sq[i]) for i in order]

    # The worst active plane can change after crossing the first. Sequential
    # projections incorporate the other poses that constrain the same vertex.
    step = np.zeros_like(scales)
    for _ in range(12):
        remaining = deficit - gradient @ step
        index = np.argmax(remaining)
        if remaining[index] <= 0:
            break
        step += 0.72 * remaining[index] * gradient[index] / normals_sq[index]
        if np.linalg.norm(step) > 0.026:
            break
    moves.append(step)
    moves.append(np.mean(moves, axis=0))
    return np.asarray(moves) * scales


def solve_residuals(points, weights, original, original_weights, body_weights, distances, samples,
                    transforms, neighbors, shape, torso, iteration):
    """Solve stubborn poses with coordinated local rest offsets and weight transfers."""
    all_rows = np.arange(len(samples))
    by_clip = [all_rows[[n == name for n, _, _ in samples]] for name in CLIPS]
    mean_points = original + average(points - original, neighbors)
    mean_weights = limit_weights(average(weights, neighbors))
    worst = distances.min(axis=0)
    remaining = (worst < FIT_FLOOR) | (torso & (distances[0] > TORSO_LIMIT - 0.00003))
    failing = np.flatnonzero(remaining)[np.argsort(worst[remaining], kind="stable")]
    rng = np.random.default_rng(2131 + iteration)
    corrected = 0
    for vertex in failing:
        position, weight = points[vertex].copy(), weights[vertex].copy()
        rest, initial_weight = original[vertex], original_weights[vertex]
        neighborhood, skin_mean = mean_points[vertex], mean_weights[vertex]
        prior_skin = body_weights[vertex]
        column_scores = np.maximum.reduce((weight, initial_weight, skin_mean, prior_skin))
        columns = np.flatnonzero((column_scores > .027) | (weight > 0))
        if not len(columns):
            continue
        values = distances[:, vertex]
        for attempt in range(2):
            rows = np.unique(np.r_[0, np.argsort(values, kind="stable")[:17],
                                   [r for group in by_clip for r in
                                    group[np.argsort(values[group], kind="stable")[:2]]]])
            moves = linearized_moves(position, weight, columns, rows, transforms, samples, torso[vertex])
            moves = (np.array([.50, .85, 1.10, 1.60, 2.30])[:, None, None] * moves).reshape(-1, 3 + len(columns))
            rng_count = 135
            sizes = np.array([.00045, .0012, .0027, .0048, .008, .014, .020])
            directions = rng.normal(0, 1, (rng_count, 3))
            directions /= np.linalg.norm(directions, axis=1, keepdims=True)
            radius = rng.choice(sizes, rng_count)
            offsets = directions * radius[:, None]
            stretch = .68 if attempt == 1 else 1
            offsets *= stretch
            anchors = np.array([position, rest, neighborhood])
            anchors = anchors[rng.choice(3, rng_count, p=(.77, .13, .10))]
            trial_points = np.vstack((position, position + moves[:, :3], anchors + offsets))
            trial_points = rest + project_to_limit(trial_points - rest)
            swing = rng.normal(0, 1, (rng_count, len(columns))) * (radius[:, None] * 22 * stretch)
            swing -= swing.mean(axis=1, keepdims=True)
            base_weights = np.array([weight, initial_weight, skin_mean, prior_skin])
            base_weights = base_weights[rng.choice(4, rng_count, p=(.80, .08, .07, .05))]
            trial_weights = np.vstack((weight, np.tile(weight, (len(moves), 1)), base_weights))
            trial_weights[1:, columns] += np.vstack((moves[:, 3:], swing))
            trial_weights = limit_weights(np.maximum(0, trial_weights))
            rough = (0.035 * np.linalg.norm(trial_points - neighborhood, axis=1)
                     + 0.00035 * abs(trial_weights - skin_mean).sum(axis=1)
                     + 0.016 * np.linalg.norm(trial_points - rest, axis=1))
            trial = compound_clearance(trial_points, trial_weights, rows, transforms, samples)
            penalty = surface_cost(trial, trial[0], torso[vertex])
            shortlist = np.unique(np.r_[0, np.argsort(5 * penalty + rough, kind="stable")[:14],
                                        np.argsort(penalty, kind="stable")[:9]])
            checked = compound_clearance(trial_points[shortlist], trial_weights[shortlist],
                                         all_rows, transforms, samples)
            best = shape.choose(vertex, trial_points[shortlist], checked, rough[shortlist],
                                points, torso[vertex], factor=9)
            index = shortlist[best]
            position, weight, values = trial_points[index], trial_weights[index], checked[:, best]
            points[vertex], weights[vertex] = position, weight
            if values.min() >= FIT_FLOOR and (not torso[vertex] or values[0] <= TORSO_LIMIT):
                corrected += 1
                break
    print("COUPLED RESIDUALS", iteration, len(failing), corrected, flush=True)



def patch_loss(values):
    """Rank local patches by the number and depth of dense pose failures."""
    deficit = np.maximum(0, FIT_FLOOR - values)
    worst = deficit.max(axis=0) * 1000
    return 2 * np.count_nonzero(worst > FIT_FLOOR * 1000) + np.sum(worst ** 1.35) + 2 * worst.max()


def safe_patch(shape, old, proposed, torso_limit):
    if np.linalg.norm(proposed - old, axis=1).max() < 1e-8:
        return False
    before = old[shape.triangles]
    after = proposed[shape.triangles]
    normals = np.cross(before[:, 1] - before[:, 0], before[:, 2] - before[:, 0])
    new_normals = np.cross(after[:, 1] - after[:, 0], after[:, 2] - after[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    new_lengths = np.linalg.norm(new_normals, axis=1)
    stable = lengths > 4e-8
    if np.any((np.einsum("fi,fi->f", normals, new_normals) < 0.72 * lengths * new_lengths) & stable):
        return False
    if np.any(((new_lengths < 0.58 * lengths) | (new_lengths > 1.7 * lengths)) & stable):
        return False
    moved = np.linalg.norm(proposed - old, axis=1) > 1e-8
    for point, is_torso in zip(proposed[moved], zones(proposed)["torso"][moved]):
        signed = clearance(shape.tree, point)
        if signed < FIT_FLOOR or (is_torso and signed > torso_limit):
            return False
    mesh = BVHTree.FromPolygons(proposed.tolist(), shape.triangles.tolist(), all_triangles=True)
    return not shape.tree.overlap(mesh)


def stabilize_torso(garment, points, original, tree):
    """Leave headroom for a nearest-face tie after glTF coordinate conversion."""
    shape = RestShape(garment.data, original, tree)
    neighbors = adjacency(garment.data)
    hits = [nearest_details(tree, point) for point in points]
    distances = np.array([hit[0] for hit in hits])
    normals = np.array([hit[1] for hit in hits])
    torso = zones(points)["torso"]
    required = np.where(torso, np.maximum(0, distances - (TORSO_LIMIT - .00065)), 0)
    offset = -normals * smooth_floor(required, neighbors)[:, None]
    candidate = original + project_to_limit(points + offset - original)
    if safe_patch(shape, points, candidate, TORSO_LIMIT):
        return candidate
    return points



def finish_fit(garment, samples, transforms, weights, points, original):
    """Apply coherent local loosening and close any remaining rest torso excess."""
    shape = RestShape(garment.data, original, samples[0][2])
    neighbors = adjacency(garment.data)
    skin = skin_matrices(transforms, weights)
    values, gradients = evaluate(points, samples, skin, normals=True)
    points = points.copy()
    maximum = max(TORSO_LIMIT, float(values[0, zones(points)["torso"]].max()))

    # A smooth inward falloff can move a seam together when its individual
    # triangles otherwise prevent a one-vertex fit correction.
    if maximum > TORSO_LIMIT:
        rest = values[0]
        region = zones(points)["torso"]
        excess = np.where(region & (rest > TORSO_LIMIT - .00005), rest - (TORSO_LIMIT - .00025), 0)
        normal = np.array([nearest_details(shape.tree, p)[1] for p in points])
        for strength in (1.12, .92, .72):
            correction = -normal * smooth_floor(excess, neighbors)[:, None] * strength
            proposal = original + project_to_limit(points + correction - original)
            if safe_patch(shape, points, proposal, maximum):
                new_values, new_gradients = evaluate(proposal, samples, skin, normals=True)
                new_max = float(new_values[0, zones(proposal)["torso"]].max())
                if new_max < maximum:
                    points, values, gradients, maximum = proposal, new_values, new_gradients, new_max
                if maximum <= TORSO_LIMIT:
                    break

    regions = zones(original)
    zones_to_loosen = (regions["hem"], regions["torso_body"],
                       regions["shoulder_armpit"] | regions["sleeve"] | regions["cuff"])
    for zone in zones_to_loosen:
        for side in (-1, 1):
            worst = values.min(axis=0)
            seeds = zone & (np.sign(original[:, 0]) == side) & (worst < FIT_FLOOR)
            if not seeds.any():
                continue
            required = np.where(seeds, np.maximum(0, MARGIN - worst), 0)
            weight = np.square(np.maximum(0, MARGIN - values))
            direction = np.einsum("fv,fvi->vi", weight, gradients)
            direction /= np.linalg.norm(direction, axis=1, keepdims=True).clip(1e-12)
            field = required[:, None] * direction
            support = required[:, None]
            for _ in range(5):
                field = 0.68 * field + 0.32 * average(field, neighbors)
                support = 0.68 * support + 0.32 * average(support, neighbors)
            support = support[:, 0]
            ids = np.flatnonzero(support > 0.000025)
            if not len(ids):
                continue
            heading = direction[seeds].T @ required[seeds]
            heading /= max(1e-10, np.linalg.norm(heading))
            directions = (field, support[:, None] * heading)
            best = patch_loss(values[:, ids])
            best_points = points
            for displacement in directions:
                for scale in (0.70, 1.45, 2.5, 4.0):
                    proposal = points.copy()
                    proposal[ids] = original[ids] + project_to_limit(points[ids] + scale * displacement[ids] - original[ids])
                    if not safe_patch(shape, points, proposal, min(maximum, TORSO_LIMIT) + 0.000001):
                        continue
                    local, _ = evaluate(proposal[ids], samples, skin[:, ids])
                    cost = patch_loss(local)
                    if cost < best - 0.002:
                        best, best_points = cost, proposal
            if best_points is not points:
                points = best_points
                values, gradients = evaluate(points, samples, skin, normals=True)
                print("LOCAL BULGE", int(seeds.sum()), "vertices across", len(ids), "patch vertices", flush=True)

    points = stabilize_torso(garment, np.asarray(points, dtype=np.float32), original, shape.tree)
    print("FINAL SHAPE torso cap",
          max(clearance(shape.tree, point) for point in points[zones(points)["torso"]]), flush=True)
    return points



def fit(garment, body, names, samples, transforms, weights):
    mesh = garment.data
    original = mesh_points(mesh).copy()
    points = original.copy()
    original_weights = weights.copy()
    neighbors = adjacency(mesh)
    shape = RestShape(mesh, original, samples[0][2])
    torso = zones(original)["torso"]
    shape.compress_torso(points, neighbors)
    skin = skin_matrices(transforms, weights)
    garment_normals = np.array([tuple(v.normal) for v in mesh.vertices], dtype=np.float32)
    body_normals = np.array([nearest_details(samples[0][2], p)[1] for p in points], dtype=np.float32)
    agreement = (garment_normals * body_normals).sum(axis=1)
    normals = np.where((agreement >= 0.35)[:, None], garment_normals, body_normals)
    body_weights = nearest_body_weights(original, body, names, samples[0][2])
    distances, gradients = evaluate(points, samples, skin, normals=True)
    print("BASELINE", summarize(distances, samples), flush=True)
    print("BASELINE REST", {name: stats(distances[0, mask]) for name, mask in zones(original).items()}, flush=True)
    history = []

    for iteration in range(1, ITERATIONS + 1):
        proposed = normal_step(points, original, normals, distances, gradients, neighbors)
        points = refine(points, original, proposed, distances, gradients, samples, skin, neighbors, shape, torso)
        distances, gradients = evaluate(points, samples, skin, normals=True)
        if iteration > 1 and distances.min() < FIT_FLOOR:
            refine_weights(points, weights, original, original_weights, body_weights, names, distances, samples,
                           transforms, neighbors, shape, torso, iteration)
            skin = skin_matrices(transforms, weights)
            distances, gradients = evaluate(points, samples, skin, normals=True)
        if iteration > 2 and (distances.min() < FIT_FLOOR or distances[0, torso].max() > TORSO_LIMIT):
            solve_residuals(points, weights, original, original_weights, body_weights, distances, samples,
                            transforms, neighbors, shape, torso, iteration)
            skin = skin_matrices(transforms, weights)
            distances, gradients = evaluate(points, samples, skin, normals=True)
        result = summarize(distances, samples)
        print("FIT", iteration, result, "torso max", float(distances[0, torso].max()),
              "vertices below target", int((distances.min(axis=0) < TARGET).sum()), flush=True)
        history.append(result)
        if distances.min() >= FIT_FLOOR and distances[0, torso].max() <= TORSO_LIMIT:
            break

    print("OFFSET STATS", stats(np.linalg.norm(points - original, axis=1)),
          "changed weights", int(np.any(abs(weights - original_weights) > 1e-6, axis=1).sum()), flush=True)
    return points, history

def write_weights(garment, names, weights):
    for group in list(garment.vertex_groups):
        garment.vertex_groups.remove(group)
    for name, column in zip(names, weights.T):
        positive = np.flatnonzero(column)
        if len(positive):
            group = garment.vertex_groups.new(name=name)
            for vertex in positive:
                group.add([int(vertex)], float(column[vertex]), "REPLACE")


def export(garment, arm, body, points, names, weights):
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    garment.data.vertices.foreach_set("co", np.asarray(points, dtype=np.float32).ravel())
    garment.data.update()
    write_weights(garment, names, weights)
    garment.name = garment.data.name = NAME
    assert len(mesh_triangles(garment.data)) <= 6000
    assert len(arm.data.bones) == 65
    for obj in list(bpy.context.scene.objects):
        if obj not in (arm, body, garment) and obj.type in {"MESH", "ARMATURE"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    garment.parent = None
    bpy.ops.export_scene.gltf(
        filepath=str(GLB), export_format="GLB", use_selection=True,
        export_animations=False, export_yup=True, export_all_influences=False, export_def_bones=False,
    )
    garment.parent = arm
    body.hide_render = True
    body.hide_set(True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / (NAME + ".blend")))


def build():
    bpy.ops.wm.open_mainfile(filepath=str(ROUND1 / "top_hoodie_v1.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, garment = (scene.objects[name] for name in ("Armature", "Base_Body", "top_hoodie_v1"))
    body.hide_set(False)
    bone_names = tuple(bone.name for bone in arm.data.bones)
    weights = read_weights(garment, bone_names)
    samples, transforms = cache_motion(scene, arm, body, garment, bone_names)
    points, history = fit(garment, body, bone_names, samples, transforms, weights)
    points = finish_fit(garment, samples, transforms, weights, points, mesh_points(garment.data))
    export(garment, arm, body, points, bone_names, weights)
    return history


def reimport(path):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in scene.objects if obj not in before]
    garment, = [obj for obj in bpy.context.selected_objects if obj in imported and obj.type == "MESH"]
    garment.parent = None
    for obj in imported:
        if obj.type == "ARMATURE":
            bpy.data.objects.remove(obj, do_unlink=True)
    for modifier in list(garment.modifiers):
        garment.modifiers.remove(modifier)
    garment.parent = arm
    garment.modifiers.new("Armature", "ARMATURE").object = arm
    load_motion(scene, arm, body, garment)
    return scene, arm, body, garment


def verify(path, history=None):
    """Independently measure the export using actual evaluated armature meshes."""
    scene, arm, body, garment = reimport(path)
    result = {}
    distances = []
    samples = []
    failures = {name: {} for name in ("rest", *CLIPS)}
    original = mesh_points(garment.data)
    regions = zones(original)
    bone_names = tuple(bone.name for bone in arm.data.bones)
    body_weights = read_weights(body, bone_names, validate=False)
    face_bones = [bone_names[body_weights[list(face.vertices)].sum(axis=0).argmax()]
                  for face in body.data.polygons]
    for name, frame in frames():
        set_pose(scene, arm, name, frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        tree = body_surface(body, depsgraph)
        obj = garment.evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        try:
            coords = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
            hits = [nearest_details(tree, p) for p in coords]
            row = np.array([distance for distance, _, _ in hits])
            distances.append(row)
            samples.append((name, frame, None))
            if name == "rest":
                garment_surface = BVHTree.FromPolygons(coords, [p.vertices[:] for p in mesh.polygons])
                result["rest_intersecting_face_pairs"] = len(tree.overlap(garment_surface))
            for vertex in np.flatnonzero(row < TARGET):
                zone = next(k for k, mask in regions.items() if k != "torso" and mask[vertex])
                bone = face_bones[hits[vertex][2]].removeprefix("mixamorig:")
                label = zone + " / " + bone
                entry = failures[name].setdefault(label, {"min_signed_dist": 9})
                if row[vertex] < entry["min_signed_dist"]:
                    entry.update(min_signed_dist=float(row[vertex]), frame=frame, vertex=int(vertex))
        finally:
            obj.to_mesh_clear()
    values = np.array(distances)
    result.update(
        glb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        samples=len(samples), clips=summarize(values, samples),
        rest_clearance={zone: stats(values[0, mask]) for zone, mask in regions.items()},
        failures={name: zones for name, zones in failures.items() if zones},
    )
    if history is not None:
        result["iterations"] = history
    print("DENSE EXPORTED", result["clips"], "rest face pairs", result["rest_intersecting_face_pairs"], flush=True)
    output = "baseline_dense.json" if path != GLB else "dense_check.json"
    (HERE / output).write_text(json.dumps(result, indent=2) + "\n")


def run_checker():
    # The round-one helper replaces the single Workbench setup line in memory.
    # The supplied checker file, measurement code, and image poses stay intact.
    checker = PRIOR["run_checker"]
    variables = checker.__globals__
    variables["HERE"], variables["NAME"] = HERE, NAME
    checker()


def render_rest():
    scene, arm, body, garment = reimport(GLB)
    set_pose(scene, arm, "rest", 1)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 900, 560
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Fit QA world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.68, 0.73, 0.8, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.42
    garment.hide_render = False

    focus = Vector((0, 0, 0.512))
    for position, power, size in (((-1, -1.5, 2.6), 150, 2.2), ((1.2, -.7, 1.25), 38, 1.8),
                                  ((.4, 1.45, 2), 110, 1.5)):
        data = bpy.data.lights.new("Fit QA area", "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        lamp = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(lamp)
        lamp.location = position
        lamp.rotation_euler = (focus - lamp.location).to_track_quat("-Z", "Y").to_euler()

    data = bpy.data.cameras.new("Fit QA camera")
    data.type, data.ortho_scale = "ORTHO", 0.69
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, direction, show_body in (("rest_front", (0, -1, .04), True),
                                        ("rest_back", (.30, 1, .27), True),
                                        ("rest_hoodie", (.24, -1, .28), False)):
        body.hide_render = not show_body
        camera.location = focus + 3 * Vector(direction)
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / (name + ".png"))
        bpy.ops.render.render(write_still=True)


def main():
    options = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--baseline" in options:
        verify(ROUND1 / "top_hoodie_v1.glb")
    elif "--verify" in options:
        verify(GLB)
    elif "--checker" in options:
        run_checker()
    elif "--renders" in options:
        render_rest()
    else:
        verify(GLB, build())


if __name__ == "__main__":
    main()
