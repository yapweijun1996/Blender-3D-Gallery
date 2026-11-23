"""Bake the Studio cargo pants against the master T-pose and seven clips.

Run in Blender with -- build, verify, checkers or renders. Measurements use
the exported mesh reattached to the unchanged master armature by joint name.
"""
from collections import defaultdict
from contextlib import redirect_stdout
from itertools import product
import hashlib
import io
import json
from pathlib import Path
import runpy
import struct
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
PRIOR = runpy.run_path(str(HERE.parent / "fit_pants.py"))
BASE = PRIOR["load_master"].__globals__
GLB = HERE / "pants_v2.glb"
BASE.update(HERE=HERE, GLB=GLB, MARGIN=.002, TRIANGLE_LIMIT=8000)
CLIPS = BASE["CLIPS"]
MARGIN = .002
MINIMUM = .0005
LIMIT = .030
STEPS = 16
load_master = BASE["load_master"]
coordinates = BASE["coordinates"]
triangles = BASE["triangles"]
neighbors_of = BASE["mesh_neighbors"]
average = BASE["average"]
unit = BASE["unit"]
skin_matrices = BASE["skin_matrices"]
pose_points = BASE["pose_points"]
tree_for = BASE["tree_for"]
signed_hits = BASE["signed_hits"]
rest_project = BASE["rest_project"]
trim_weights = BASE["trim_weights"]


def assess(points, weights, faces, samples, transforms, body_faces, collect=False):
    posed = pose_points(points, skin_matrices(weights, transforms))
    distances, overlaps, contacts = [], [], []
    hits = np.zeros(len(faces), dtype=np.int32)
    face_list = faces.tolist()
    for row, (clip, frame, tree, body) in enumerate(samples):
        xyz = posed[row]
        s, normal = signed_hits(tree, xyz)
        distances.append(s)
        count = tree.overlap(tree_for(xyz, face_list))
        overlaps.append(len(count))
        if not collect:
            continue
        if len(count):
            pairs = np.asarray(count)
            face_ids = np.unique(pairs[:, 1])
            hits[face_ids] += 1
            ids, bary = BASE["contact_points"](xyz, faces, body, body_faces, pairs)
            point = np.einsum("nk,nki->ni", bary, xyz[faces[ids]])
            depth, direction = signed_hits(tree, point)
            order = np.lexsort((depth, ids))
            worst = order[np.r_[True, np.diff(ids[order]) != 0]]
            contacts.append((row, faces[ids[worst]], bary[worst], depth[worst], direction[worst]))
        active = np.flatnonzero(s < MARGIN)
        if len(active):
            contacts.append((row, active[:, None], np.ones((len(active), 1), np.float32),
                             s[active], normal[active]))
    return np.asarray(distances), np.asarray(overlaps), contacts, hits


def objective(distance, overlap):
    """Penalize persistent contacts, then improve the clearance around them."""
    deficit = (MARGIN - distance).clip(0) * 1000
    rest = 1e6 * (overlap[0] + np.count_nonzero(
        (distance[0] < MINIMUM) | (distance[0] > LIMIT)))
    return float(rest + overlap.sum() + 1.4 * (distance < 0).sum()
                 + .065 * (deficit ** 2).sum()
                 + 2. * (deficit.max(axis=0) ** 2).sum())


def smooth_floor(displacement, neighbors):
    smooth = displacement.copy()
    for _ in range(3):
        smooth = .68 * smooth + .32 * average(smooth, neighbors)
    direction = unit(displacement)
    floor = np.linalg.norm(displacement, axis=1)
    return smooth + (floor - (smooth * direction).sum(axis=1)).clip(0)[:, None] * direction


def capped(points, original, rest_tree):
    move = points - original
    points = original + move * np.minimum(1, LIMIT / np.linalg.norm(move, axis=1).clip(1e-9))[:, None]
    points[:, 2] = points[:, 2].clip(.067, .433)
    return rest_project(points, rest_tree, lo=.00145, hi=.0298)


def shape_guard(points, trial, faces, rest_tree):
    """Back off moves that would cut the rest body or sharply fold rest faces."""
    normals = unit(np.cross(points[faces[:, 1]] - points[faces[:, 0]],
                            points[faces[:, 2]] - points[faces[:, 0]]))
    face_list = faces.tolist()
    trial = trial.copy()
    for _ in range(6):
        cross = np.cross(trial[faces[:, 1]] - trial[faces[:, 0]],
                         trial[faces[:, 2]] - trial[faces[:, 0]])
        flipped = np.flatnonzero((normals * unit(cross)).sum(axis=1) < .2)
        pairs = rest_tree.overlap(tree_for(trial, face_list))
        crossed = np.asarray(pairs, dtype=int).reshape(-1, 2)[:, 1]
        bad = np.unique(faces[np.r_[flipped, crossed]].ravel())
        if not len(bad):
            break
        trial[bad] = .5 * (trial[bad] + points[bad])
    return trial


def tightness(z):
    blend = ((z - .294) / .099).clip(0, 1)
    return blend * blend * (3 - 2 * blend)


def smooth_weights(weights, original, adjacency, multiplier):
    z = original[:, 2]
    amount = multiplier * (.24 + .76 * np.maximum(np.exp(-((z - .343) / .048) ** 2),
                                                  np.exp(-((z - .212) / .042) ** 2)))
    return trim_weights(weights + amount[:, None] * (average(weights, adjacency) - weights))


def baseline(points, weights, faces, samples, transforms, body_faces, nearest_weights):
    """Try a coherent waistband alteration before solving individual contacts."""
    rows = subset(samples)
    active = [samples[i] for i in rows]
    matrices = transforms[rows]
    rest_tree = samples[0][2]
    distance, direction = signed_hits(rest_tree, points)
    ramp = tightness(points[:, 2])
    results = []
    for lift, take_in, rebind in product((0, -.011, .011, -.022), (0, .76), (0, .32)):
        trial = points - ((distance - .0021).clip(0) * ramp * take_in)[:, None] * direction
        trial[:, 2] += lift * ramp
        trial = shape_guard(points, capped(trial, points, rest_tree), faces, rest_tree)
        binding = trim_weights(weights + rebind * (nearest_weights - weights))
        d, p, _, _ = assess(trial, binding, faces, active, matrices, body_faces)
        score = objective(d, p)
        results.append((score, trial, binding))
        print("WAIST TRIAL", lift, take_in, rebind, round(score), flush=True)
    return min(results, key=lambda item: item[0])[1:]


def subset(samples, distance=None, overlap=None):
    rows = {0}
    for clip in CLIPS:
        ix = np.asarray([i for i, sample in enumerate(samples) if sample[0] == clip])
        rows.update(ix[::max(2, len(ix) // 9)])
        if distance is not None:
            rows.update(ix[np.argsort(distance[ix].min(axis=1))[:4]])
            rows.update(ix[np.argsort(-overlap[ix], kind="stable")[:4]])
    return sorted(rows)


def required_steps(points, weights, transforms, contacts, adjacency, rest_tree):
    """Build rest-space planes from worst-frame nearest surfaces and triangle witnesses."""
    skin = skin_matrices(weights, transforms)
    smooth = average(weights, adjacency)
    columns = np.argsort(-(weights + .25 * smooth), axis=1, kind="stable")[:, :4]
    local_weights = np.take_along_axis(weights, columns, axis=1)
    scale = .048
    vertices, gradient, amounts = [], [], []
    for row, ids, bary, signed, normals in contacts:
        jac = np.einsum("ni,nkij->nkj", normals, skin[row, ids, :, :3])
        bones = transforms[row, columns[ids]]
        xyz = np.einsum("nkbic,nkc->nkbi", bones[..., :3], points[ids]) + bones[..., 3]
        weighted = xyz - xyz.mean(axis=-2, keepdims=True)
        weight_jac = np.einsum("ni,nkbi->nkb", normals, weighted) / scale
        grad = np.concatenate((jac, weight_jac), axis=-1)
        # Give a face witness influence over all three corners in proportion
        # to their contribution to the posed contact point.
        grad *= bary[:, :, None]
        deficit = (MARGIN - signed).clip(0, LIMIT)
        vertices.append(ids.ravel())
        gradient.append(grad.reshape(-1, 7))
        amounts.append(np.repeat(deficit / np.square(bary).sum(axis=1).clip(.34), ids.shape[1]))
    vids, grad, depth = np.concatenate(vertices), np.concatenate(gradient), np.concatenate(amounts)
    axis = np.abs(grad[:, :3]).argmax(axis=1)
    group = vids * 6 + axis * 2 + (grad[np.arange(len(axis)), axis] > 0)
    magnitude = np.linalg.norm(grad[:, :3], axis=1)
    rank = depth * magnitude
    peak = np.zeros(len(points) * 6, dtype=np.float32)
    np.maximum.at(peak, group, rank)
    best = np.flatnonzero((rank == peak[group]) & (rank > 1e-8))
    chosen = np.full(len(peak), -1, dtype=np.int32)
    np.maximum.at(chosen, group[best], best)
    chosen = chosen[chosen >= 0]
    vids, grad, depth = vids[chosen], grad[chosen], depth[chosen]
    response = np.square(grad).sum(axis=1).clip(.15)
    strength = depth ** 1.3
    movement = np.zeros((len(points), 7), dtype=np.float32)
    mass = np.bincount(vids, weights=strength, minlength=len(points)).clip(1e-12)
    np.add.at(movement, vids, (strength * depth / response)[:, None] * grad)
    movement /= mass[:, None]
    # Supplement the combined response with the single deepest requirement.
    worst = np.zeros(len(points), dtype=np.float32)
    np.maximum.at(worst, vids, depth)
    top = np.flatnonzero((depth == worst[vids]) & (depth > 1e-8))
    best_per_vertex = np.full(len(points), -1, dtype=int)
    np.maximum.at(best_per_vertex, vids[top], top)
    active = np.flatnonzero(best_per_vertex >= 0)
    top = best_per_vertex[active]
    peak_step = np.zeros_like(movement)
    peak_step[active] = (depth[top] / response[top])[:, None] * grad[top]
    rest_direction = signed_hits(rest_tree, points)[1]
    slope = (grad[:, :3] * rest_direction[vids]).sum(axis=1)
    for factor in (1, -1):
        requirement = np.zeros(len(points), dtype=np.float32)
        active_plane = (factor * slope > .25)
        np.maximum.at(requirement, vids[active_plane],
                      (depth[active_plane] / (factor * slope[active_plane])).clip(0, LIMIT))
        yield factor * rest_direction * requirement[:, None], np.zeros_like(local_weights), columns
    yield movement[:, :3], movement[:, 3:] / scale, columns
    yield peak_step[:, :3], peak_step[:, 3:] / scale, columns


def broaden(points, weights, faces, original, samples, transforms, body_faces,
            adjacency, distance, overlap, contacts, iteration):
    rows = subset(samples, distance, overlap)
    active = [samples[i] for i in rows]
    matrices = transforms[rows]
    base_distance, base_pair = distance[rows], overlap[rows]
    incumbent = objective(base_distance, base_pair)
    candidates = [(incumbent, points, weights, "unchanged")]
    for index, (delta, weight_delta, columns) in enumerate(
        required_steps(points, weights, transforms, contacts, adjacency, samples[0][2])
    ):
        offset = smooth_floor(delta, adjacency)
        controls = ((.45, 0.), (.85, .45)) if index < 2 else ((.52, .32), (.85, .7))
        for strength, binding_strength in controls:
            move = strength * offset
            ceiling = .0065 if iteration < 5 else .0038
            move *= np.minimum(1, ceiling / np.linalg.norm(move, axis=1).clip(1e-9))[:, None]
            trial = shape_guard(points, capped(points + move, original, samples[0][2]),
                                faces, samples[0][2])
            binding = weights.copy()
            local = np.take_along_axis(weights, columns, axis=1)
            local = np.maximum(local + binding_strength * weight_delta.clip(-.14, .14), 0)
            np.put_along_axis(binding, columns, local, axis=1)
            binding = smooth_weights(trim_weights(binding), original, adjacency, .048)
            d, p, _, _ = assess(trial, binding, faces, active, matrices, body_faces)
            merit = objective(d, p)
            candidates.append((merit, trial, binding, f"direction {index}, gain {strength:g}"))
    winner = min(candidates, key=lambda item: item[0])
    print("OFFSET SEARCH", winner[3], round(incumbent), "->", round(winner[0]), flush=True)
    return winner[1:3]


def local_refine(points, weights, original, faces, samples, transforms, distance,
                 contacts, adjacency, amount):
    """Search around dense residuals where opposing surface normals cancel."""
    by_vertex = defaultdict(list)
    for row, ids, bary, signed, normal in contacts:
        if ids.shape[1] != 3:
            continue
        for face, factors, depth in zip(ids, bary, signed):
            for corner in np.flatnonzero(factors > .22):
                by_vertex[face[corner]].append((float(depth), row, face, factors, corner))
    worst = distance.min(axis=0).copy()
    for vertex, witnesses in by_vertex.items():
        worst[vertex] = min(worst[vertex], min(row[0] for row in witnesses))
    order = np.argsort(worst, kind="stable")
    active = order[worst[order] < MARGIN][:330]
    rows_by_clip = [np.asarray([i for i, sample in enumerate(samples) if sample[0] == clip])
                    for clip in CLIPS]
    nearby = original + average(points - original, adjacency)
    neighbor_weights = average(weights, adjacency)
    points, weights = points.copy(), weights.copy()
    skin = skin_matrices(weights, transforms)
    grid = unit(np.asarray([v for v in product((-1., 0, 1), repeat=3) if any(v)],
                           dtype=np.float32))
    changes = 0
    for index in active:
        rows = {0}
        for clip_rows in rows_by_clip:
            clip_dist = distance[clip_rows, index]
            for interval in np.array_split(clip_rows, 3):
                if len(interval) and distance[interval, index].min() < .012:
                    rows.add(int(interval[np.argmin(distance[interval, index])]))
            rows.add(int(clip_rows[np.argmin(clip_dist)]))
        rows = sorted(rows)
        witnesses = []
        seen = set()
        for record in sorted(by_vertex.get(index, ()), key=lambda item: item[:2]):
            key = (record[1] // 5, *record[2])
            if key in seen:
                continue
            seen.add(key)
            witnesses.append(record)
            if len(witnesses) == 10:
                break
        extra = [record[1] for record in witnesses]
        if witnesses:
            ids = np.asarray([record[2] for record in witnesses])
            factors = np.asarray([record[3] for record in witnesses])
            corner = np.asarray([record[4] for record in witnesses])
            coefficient = factors[np.arange(len(corner)), corner]
            patch_skin = skin[np.asarray(extra)[:, None], ids]
            patch = np.einsum("ncij,ncj->nci", patch_skin[..., :3], points[ids]) + patch_skin[..., 3]
            fixed = np.einsum("nc,nci->ni", factors, patch) - coefficient[:, None] * patch[
                np.arange(len(corner)), corner]
        start = points[index]
        blend = weights[index]
        custom = np.vstack((np.zeros(3), grid * amount, grid * (amount * 2.25),
                            .7 * (nearby[index] - start)))
        choices = start + custom
        column = np.flatnonzero(np.maximum(blend, neighbor_weights[index]) > .025)
        column = np.union1d(column, np.flatnonzero(blend))
        local_matrix = transforms[rows + extra][:, column]
        current = blend[column]
        natural = neighbor_weights[index, column]
        natural /= natural.sum().clip(1e-8)

        def cost(options, bindings):
            mixed = skin_matrices(bindings, local_matrix)
            posed = np.einsum("fvij,vj->fvi", mixed[..., :3], options) + mixed[..., 3]
            if witnesses:
                posed[len(rows):] = fixed[:, None] + coefficient[:, None, None] * posed[len(rows):]
            field = np.asarray([signed_hits(samples[row][2], xyz)[0]
                                for row, xyz in zip(rows + extra, posed)])
            miss = (MARGIN - field).clip(0) * 1000
            loss = 2.4 * (miss.max(axis=0) ** 2) + (miss ** 2).mean(axis=0)
            loss += .13 * (((options - nearby[index]) * 1000) ** 2).sum(axis=1)
            loss += .028 * (((options - original[index]) * 1000) ** 2).sum(axis=1)
            loss += 16 * ((bindings - current) ** 2).sum(axis=1)
            valid = ((field[0] > .00115) & (field[0] < .0299)
                     & (np.linalg.norm(options - original[index], axis=1) <= LIMIT)
                     & (options[:, 2] >= .067) & (options[:, 2] <= .433))
            loss[~valid] = np.inf
            return loss

        same = np.broadcast_to(current, (len(choices), len(current)))
        scores = cost(choices, same)
        joint = np.eye(len(column), dtype=np.float32)
        proposals = trim_weights(np.vstack((current, .76 * current + .24 * natural,
                                            .88 * current + .12 * joint,
                                            .72 * current + .28 * joint)))
        anchors = choices[np.argsort(scores, kind="stable")[:3]]
        alternatives = np.repeat(anchors, len(proposals), axis=0)
        bindings = np.tile(proposals, (len(anchors), 1))
        scores = np.r_[scores, cost(alternatives, bindings)]
        winner = int(scores.argmin())
        if scores[winner] + .005 >= scores[0] or not np.isfinite(scores[winner]):
            continue
        if winner < len(choices):
            points[index] = choices[winner]
        else:
            chosen = winner - len(choices)
            points[index] = alternatives[chosen]
            weights[index] = 0
            weights[index, column] = bindings[chosen]
            skin[:, index] = skin_matrices(weights[index:index+1], transforms)[:, 0]
        changes += 1
    print("LOCAL CONTACT SEARCH", len(active), changes, flush=True)
    return points, weights


def local_loft(garment, faces, points, weights, hits, rest_tree):
    """Insert support loops over crossing long edges, including the inner thigh."""
    before = len(points)
    points, weights = BASE["subdivide_contacts"](garment, faces, points, weights, hits)
    if len(points) == before:
        return points, weights
    points = rest_project(points, rest_tree, lo=.002, hi=.0298)
    adjacency = neighbors_of(garment.data)
    weights = smooth_weights(weights, points, adjacency, .16)
    return points, weights


def build():
    scene, arm, body = load_master()
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(HERE.parent / "pants_v1.glb"), merge_vertices=True)
    garments = [item for item in scene.objects if item not in before]
    garment, = [item for item in bpy.context.selected_objects
                if item in garments and item.type == "MESH"]
    garment.parent = None
    for item in garments:
        if item != garment:
            bpy.data.objects.remove(item, do_unlink=True)
    garment.modifiers.clear()
    garment.parent = arm
    garment.modifiers.new("Master armature", "ARMATURE").object = arm
    names = tuple(arm.data.bones.keys())
    # Match the vertex groups to the bone column indices before BMesh splits.
    rounded = BASE["body_weights"](garment, names)
    weights = trim_weights(rounded)
    garment.vertex_groups.clear()
    for name in names:
        garment.vertex_groups.new(name=name)
    body_faces = triangles(body.data)
    points = coordinates(garment.data)
    faces = triangles(garment.data)
    print("ROUND 1 IMPORT", len(points), len(faces), flush=True)
    BASE["load_actions"]()
    samples, transforms = BASE["cache_motion"](scene, arm, body, names, body_faces)
    rest_tree, rest_body = samples[0][2:]
    adjacency = neighbors_of(garment.data)
    surface_weights = BASE["transfer_weights"](
        points, rest_body, body_faces, BASE["body_weights"](body, names), rest_tree,
        adjacency, names)
    points, weights = baseline(points, weights, faces, samples, transforms, body_faces, surface_weights)
    original = points.copy()
    best = None
    history = []
    for iteration in range(STEPS + 1):
        distance, overlap, contacts, hits = assess(
            points, weights, faces, samples, transforms, body_faces, collect=iteration < STEPS)
        stats = BASE["report_metrics"](distance, overlap, samples, points, {})
        score = objective(distance, overlap)
        print("DENSE ITERATION", iteration, round(score),
              [(clip, v["max_verts_inside"], v["max_triangle_pairs"],
                round(v["min_signed_distance_m"] * 1000, 3)) for clip, v in stats.items()],
              flush=True)
        history.append({"iteration": iteration, "score": score, "clips": stats})
        accepted = (not overlap.any() and distance.min() >= MINIMUM and distance[0].max() <= LIMIT)
        valid_rest = not overlap[0] and distance[0].min() >= MINIMUM and distance[0].max() <= LIMIT
        comparable = score * 5774 / len(faces)
        if valid_rest and (best is None or comparable < best[0] or accepted):
            if best is None or best[4] != garment.data:
                if best is not None:
                    bpy.data.meshes.remove(best[4])
                mesh = garment.data.copy()
            else:
                mesh = best[4]
            best = (comparable, iteration, points.copy(), weights.copy(), mesh)
        if iteration == STEPS or accepted:
            break
        if iteration in (0, 4, 8) and hits.any():
            count = len(points)
            points, weights = local_loft(garment, faces, points, weights, hits, rest_tree)
            if len(points) != count:
                faces, adjacency = triangles(garment.data), neighbors_of(garment.data)
                original = points.copy()
                continue
        candidate, binding = broaden(points, weights, faces, original, samples, transforms,
                                     body_faces, adjacency, distance, overlap, contacts, iteration)
        if iteration >= 2:
            relaxed, local_weights = local_refine(candidate, binding, original, faces, samples,
                                                  transforms, distance, contacts, adjacency,
                                                  .0022 if iteration < 10 else .00125)
            rows = subset(samples, distance, overlap)
            checks = [samples[i] for i in rows]
            adj_motion = transforms[rows]
            d, p, _, _ = assess(candidate, binding, faces, checks, adj_motion, body_faces)
            best_merit = objective(d, p)
            for gain in (.85, .45):
                move = smooth_floor(relaxed - candidate, adjacency)
                trial = shape_guard(candidate, capped(candidate + gain * move, original, rest_tree),
                                    faces, rest_tree)
                trial_weights = smooth_weights(trim_weights(binding + gain * (local_weights - binding)),
                                               original, adjacency, .045)
                d, p, _, _ = assess(trial, trial_weights, faces, checks, adj_motion, body_faces)
                merit = objective(d, p)
                if merit < best_merit:
                    best_merit, candidate, binding = merit, trial, trial_weights
                    break
        points, weights = candidate, binding
    assert best is not None, "No candidate satisfied the rest clearance and topology limits"
    _, step, points, weights, mesh = best
    garment.data = mesh
    print("SELECTED", step, len(triangles(mesh)), flush=True)
    (HERE / "fit_history.json").write_text(json.dumps(
        {"best_iteration": step, "iterations": history}, indent=2) + "\n")
    points = enforce_rest_ceiling(points, triangles(mesh), rest_tree)
    BASE["export"](garment, arm, body, points, weights, names, save_blend=False)
    save_module_blend()
    cap_reexport()


def save_module_blend():
    scene = bpy.context.scene
    body = scene.objects.get("Base_Body")
    if body is not None:
        bpy.data.objects.remove(body, do_unlink=True)
    assert sorted(obj.type for obj in scene.objects) == ["ARMATURE", "MESH"]
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(GLB.with_suffix(".blend")))


def enforce_rest_ceiling(points, faces, tree):
    """Keep headroom at the clearance limit when a nearby triangle changes."""
    distance, _ = signed_hits(tree, points)
    result = points.copy()
    high = np.flatnonzero(distance > .02985)
    for index in high:
        nearest, normal, _, _ = tree.find_nearest(points[index])
        inward = unit(np.asarray(nearest) - points[index])
        toward = np.vstack((inward, -np.asarray(normal)))
        amount = max(float(distance[index]) - .02969, .0002)
        options = points[index] + (toward[:, None] * amount *
                                   np.asarray([1, 1.5, 2., 3.])[None, :, None]).reshape(-1, 3)
        measured, _ = signed_hits(tree, options)
        valid = np.flatnonzero((measured >= MINIMUM) & (measured <= .0298))
        if not len(valid):
            raise RuntimeError(f"Rest clearance ceiling could not be enforced at {index}")
        shortest = np.linalg.norm(options[valid] - points[index], axis=1).argmin()
        result[index] = options[valid[shortest]]
    if len(high):
        assert not tree.overlap(tree_for(result, faces.tolist()))
        print("REST CEILING CLAMP", len(high), "vertices", flush=True)
    return result


def cap_reexport():
    """Apply the rest ceiling to an already saved candidate and export it again."""
    scene, arm, body, exported = BASE["reimport"]()
    BASE["set_pose"](scene, arm, "rest", 1)
    surface = tree_for(BASE["evaluated_coordinates"](body), triangles(body.data).tolist())
    exact = BASE["evaluated_coordinates"](exported)
    repaired = enforce_rest_ceiling(exact, triangles(exported.data), surface)
    changed = np.flatnonzero(np.any(repaired != exact, axis=1))
    if not len(changed):
        print("Rest ceiling already satisfied after reimport", flush=True)
        return
    bpy.ops.wm.open_mainfile(filepath=str(GLB.with_suffix(".blend")), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, garment = scene.objects["Armature"], scene.objects[GLB.stem]
    points = coordinates(garment.data)
    index = KDTree(len(points))
    for vertex, position in enumerate(points):
        index.insert(position, vertex)
    index.balance()
    mapped = set()
    for source in changed:
        _, vertex, distance = index.find(exact[source])
        assert distance < .00015
        if vertex not in mapped:
            points[vertex] += repaired[source] - exact[source]
            mapped.add(vertex)
    print("REST EXPORT CLAMP", len(mapped), "source vertices", flush=True)
    garment.data.vertices.foreach_set("co", np.ascontiguousarray(points, dtype=np.float32).ravel())
    garment.data.update()
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    garment.parent = None
    bpy.ops.export_scene.gltf(
        filepath=str(GLB), export_format="GLB", use_selection=True,
        export_animations=False, export_yup=True, export_all_influences=False,
        export_def_bones=False, export_image_format="AUTO", export_tangents=True,
    )
    garment.parent = arm
    save_module_blend()


def checkers():
    for stem in ("motion_check", "motion_check_tri"):
        path = HERE / (stem + ".py")
        source, render_section = path.read_text().split("sc.render.engine=", 1)
        assert "bpy.ops.render.render" in render_section
        source += f'with open(f"{{out}}/{stem}.json", "w") as f: json.dump(res, f)\n'
        capture = io.StringIO()
        original_args = sys.argv
        try:
            sys.argv = [str(path), "--", str(BASE["MASTER"]), str(BASE["MOTION"]),
                        str(GLB), str(HERE)]
            with redirect_stdout(capture):
                exec(compile(source, str(path), "exec"), {})
        finally:
            sys.argv = original_args
        lines = [line for line in capture.getvalue().splitlines() if line.startswith("RESULT ")]
        assert len(lines) == 8
        result = "\n".join(lines) + "\n"
        (HERE / (stem + ".txt")).write_text(result)
        print(result, end="", flush=True)


def texture_hashes(path):
    data = path.read_bytes()
    json_size = struct.unpack_from("<I", data, 12)[0]
    content = json.loads(data[20:20 + json_size])
    mat, = content["materials"]
    pbr = mat["pbrMetallicRoughness"]
    result = {}
    for label, reference in (("normal", mat["normalTexture"]),
                             ("base_color", pbr["baseColorTexture"]),
                             ("metallic_roughness", pbr["metallicRoughnessTexture"])):
        tex = content["textures"][reference["index"]]
        image = content["images"][tex["source"]]
        view = content["bufferViews"][image["bufferView"]]
        start = 28 + json_size + view.get("byteOffset", 0)
        result[label] = hashlib.sha256(data[start:start + view["byteLength"]]).hexdigest()
    return result


def verify():
    BASE["verify"]()
    path = HERE / "dense_check.json"
    data = json.loads(path.read_text())
    prior = texture_hashes(HERE.parent / "pants_v1.glb")
    current = texture_hashes(GLB)
    data["texture_matches_round1_bytes"] = {name: prior[name] == value
                                             for name, value in current.items()}
    data["source_sha256"] = {name: hashlib.sha256(file.read_bytes()).hexdigest()
                             for name, file in (("master", BASE["MASTER"]),
                                                ("motion", BASE["MOTION"]),
                                                ("pants_v1", HERE.parent / "pants_v1.glb"))}
    data["blend_sha256"] = hashlib.sha256(GLB.with_suffix(".blend").read_bytes()).hexdigest()
    data["blend_bytes"] = GLB.with_suffix(".blend").stat().st_size
    assert data["triangles"] <= 8000
    assert data["max_influences"] <= 4 and data["unweighted_vertices"] == 0
    path.write_text(json.dumps(data, indent=2) + "\n")


def renders():
    """Capture the exported garment, including the highest-overlap motion poses."""
    scene, arm, body, garment = BASE["reimport"]()
    evidence = json.loads((HERE / "dense_check.json").read_text())["clips"]
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = scene.render.resolution_y = 600
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Fit QA Studio")
    scene.world.use_nodes = True
    ambient = scene.world.node_tree.nodes["Background"]
    ambient.inputs[0].default_value = (.68, .73, .82, 1)
    ambient.inputs[1].default_value = .48
    center = Vector((0, 0, .245))
    for name, xyz, energy, size in (("Key", (-1, -1.5, 2.6), 115, 2.1),
                                     ("Fill", (1.3, -.5, 1.25), 48, 1.65),
                                     ("Rim", (.4, 1.45, 2), 110, 1.55)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = xyz
        lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
    camera = bpy.data.cameras.new("Fit QA Camera")
    camera.type = "ORTHO"
    obj = bpy.data.objects.new(camera.name, camera)
    scene.collection.objects.link(obj)
    scene.camera = obj

    def capture(name, target, direction, scale, show_body):
        body.hide_render = not show_body
        camera.ortho_scale = scale
        obj.location = target + Vector(direction).normalized() * 3
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        return Path(scene.render.filepath)

    BASE["set_pose"](scene, arm, "rest", 1)
    poses = (
        ("front", (0, -1, .035), True),
        ("front_three_quarter", (.66, -1, .06), True),
        ("side", (1, 0, .035), True),
        ("back", (0, 1, .035), True),
        ("waist", (-.7, -1, .68), False),
        ("cuffs", (.52, 1, -.62), False),
    )
    size, gap = 600, 6
    width, height = 3 * size + 2 * gap, 2 * size + gap
    sheet = np.full((height, width, 4), .24, dtype=np.float32)
    sheet[:, :, 3] = 1
    for index, (name, direction, show_body) in enumerate(poses):
        path = capture("." + name, center, direction, .50, show_body)
        image = bpy.data.images.load(str(path))
        pixels = np.empty(size * size * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        x = (index % 3) * (size + gap)
        y = (1 - index // 3) * (size + gap)
        sheet[y:y + size, x:x + size] = pixels.reshape(size, size, 4)
        bpy.data.images.remove(image)
        path.unlink()
    image = bpy.data.images.new("Studio cargo pants six views", width, height, alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    image.file_format = "PNG"
    image.filepath_raw = str(HERE / "six_view.png")
    image.save()
    for clip, direction in (("walk", (.22, -1, .13)), ("run", (.52, -1, .09)),
                            ("wave", (-.38, -1, .14)), ("jump", (-.45, -1, .10))):
        frame = evidence[clip]["max_pairs_frame"]
        if evidence[clip]["max_triangle_pairs"] == 0:
            frame = evidence[clip]["minimum_frame"]
        BASE["set_pose"](scene, arm, clip, frame)
        points = BASE["evaluated_coordinates"](garment)
        target = Vector((points.min(axis=0) + points.max(axis=0)) / 2)
        capture(clip, target, direction, .57, True)
        print("RENDER", clip, frame, flush=True)


def main():
    stages = {"build": build, "verify": verify, "checkers": checkers,
              "renders": renders, "cap-reexport": cap_reexport}
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for stage in args or ("build",):
        stages[stage]()


if __name__ == "__main__":
    main()
