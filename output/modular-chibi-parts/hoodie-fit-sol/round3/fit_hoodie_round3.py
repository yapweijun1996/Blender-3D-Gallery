"""Bake the hoodie fit in Blender and verify the reimported skinned GLB.

Run in Blender background mode with round 2, the master, and the motion file in
their gallery locations. Use --verify, --baseline, --checkers or --renders
after Blender's -- separator to run an individual verification stage.
"""

from contextlib import redirect_stdout
import hashlib
import io
import json
import math
from pathlib import Path
import runpy
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
ROUND2 = HERE.parent / "round2"
PRIOR = runpy.run_path(str(ROUND2 / "fit_hoodie_round2.py"))
MASTER, MOTION, CLIPS = (PRIOR[key] for key in ("MASTER", "MOTION", "CLIPS"))
NAME = "top_hoodie_v3"
GLB = HERE / f"{NAME}.glb"
MARGIN = .00205
TRIANGLE_LIMIT = 7000
ITERATIONS = 12

set_pose = PRIOR["set_pose"]
load_motion = PRIOR["load_motion"]
mesh_points = PRIOR["mesh_points"]
mesh_triangles = PRIOR["mesh_triangles"]
read_weights = PRIOR["read_weights"]
write_weights = PRIOR["write_weights"]
skin_matrices = PRIOR["skin_matrices"]
limit_weights = PRIOR["limit_weights"]
stats = PRIOR["stats"]
zones = PRIOR["zones"]


def frames():
    yield "rest", 1.0
    for name in CLIPS:
        first, last = bpy.data.actions[name].frame_range
        times = {first, last, *(half / 2 for half in range(math.ceil(2 * first), math.floor(2 * last) + 1))}
        times.update(int(first + (last - first) * k / 12) for k in range(12))
        times.update(range(int(first), int(last) + 1, 3))
        yield from ((name, frame) for frame in sorted(times))


def posed_mesh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        coords = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        faces = [poly.vertices[:] for poly in mesh.polygons]
    finally:
        evaluated.to_mesh_clear()
    return coords, faces


def cache_motion(scene, arm, body, garment, names):
    load_motion(scene, arm, body, garment)
    bones = [arm.pose.bones[name] for name in names]
    modes = tuple(bone.rotation_mode for bone in bones)
    inverse_bind = [bone.bone.matrix_local.inverted() for bone in bones]
    samples, transforms, shared_faces = [], [], None
    for name, frame in frames():
        set_pose(scene, arm, name, frame)
        assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
        assert np.allclose(garment.matrix_world, np.eye(4), atol=1e-6)
        coords, faces = posed_mesh(body, bpy.context.evaluated_depsgraph_get())
        tree = BVHTree.FromPolygons(coords, faces)
        if shared_faces is None:
            shared_faces = np.asarray(faces, dtype=np.int32)
        samples.append((name, frame, tree, np.asarray(coords, dtype=np.float32), shared_faces))
        transforms.append(np.array([bone.matrix @ inv for bone, inv in zip(bones, inverse_bind)])[:, :3, :])
    assert modes == tuple(bone.rotation_mode for bone in bones)
    print("DENSE SAMPLE COUNT", len(samples), flush=True)
    return samples, np.asarray(transforms, dtype=np.float32)


def limits(points):
    masks = zones(points)
    result = np.full(len(points), .030, dtype=np.float32)
    result[masks["torso_body"] | masks["cuff"]] = .020
    result[masks["hood"] | masks["collar"]] = np.inf
    return result


def signed_hits(tree, coordinates):
    distance, normal = [], []
    for p in coordinates:
        nearest, n, _, _ = tree.find_nearest(p)
        # Dot product against the checkers' nearest oriented triangle.
        distance.append((Vector(p) - nearest).dot(n))
        normal.append(n[:])
    return np.asarray(distance, dtype=np.float32), np.asarray(normal, dtype=np.float32)


def barycentric(triangle, p):
    a, b, c = triangle.transpose(1, 0, 2)
    u, v, w = b - a, c - a, p - a
    uu = np.einsum("ij,ij->i", u, u)
    uv = np.einsum("ij,ij->i", u, v)
    vv = np.einsum("ij,ij->i", v, v)
    wu = np.einsum("ij,ij->i", w, u)
    wv = np.einsum("ij,ij->i", w, v)
    det = uu * vv - uv * uv
    s = (vv * wu - uv * wv) / det.clip(1e-18)
    t = (uu * wv - uv * wu) / det.clip(1e-18)
    return np.column_stack((1 - s - t, s, t))


def pair_witnesses(posed, triangles, body, body_faces, pairs, dense=False):
    """Find garment barycentrics at intersection segments and inside each cut."""
    face_ids, body_ids = pairs.T
    garment_tri = posed[triangles[face_ids]]
    body_tri = body[body_faces[body_ids]]
    body_normal = np.cross(body_tri[:, 1] - body_tri[:, 0], body_tri[:, 2] - body_tri[:, 0])
    garment_normal = np.cross(garment_tri[:, 1] - garment_tri[:, 0], garment_tri[:, 2] - garment_tri[:, 0])
    rows, uvw = [], []
    eye = np.eye(3, dtype=np.float32)

    # An edge of either triangle crossing the other triangle's plane gives
    # an intersection endpoint. Check its barycentrics on the opposite face.
    for reverse in (False, True):
        edge_tri, plane_tri = (body_tri, garment_tri) if reverse else (garment_tri, body_tri)
        plane_normal = garment_normal if reverse else body_normal
        height = np.einsum("nki,ni->nk", edge_tri - plane_tri[:, :1], plane_normal)
        for index in range(3):
            other = (index + 1) % 3
            h0, h1 = height[:, index], height[:, other]
            valid, = np.where((h0 * h1 <= 0) & (np.abs(h0 - h1) > 1e-15))
            alpha = h0[valid] / (h0[valid] - h1[valid])
            a, b = edge_tri[valid, index], edge_tri[valid, other]
            cross = a + alpha[:, None] * (b - a)
            coeff = barycentric(plane_tri[valid], cross)
            good = coeff.min(axis=1) >= -0.0003
            rows.append(valid[good])
            if reverse:
                uvw.append(coeff[good])
            else:
                uvw.append(eye[index] + alpha[good, None] * (eye[other] - eye[index]))

    rows, uvw = np.concatenate(rows), np.concatenate(uvw)
    sums = np.zeros((len(pairs), 3), dtype=np.float32)
    count = np.bincount(rows, minlength=len(pairs))
    np.add.at(sums, rows, uvw)
    uv = sums / np.maximum(1, count)[:, None]
    fallback_faces = np.unique(face_ids[count == 0])
    cut_faces = np.unique(face_ids)
    # In addition to the contact segment, sample into the garment triangle
    # to distinguish true penetration depth from the contact's zero distance.
    edge_mid = (eye + np.roll(eye, 1, axis=0)) / 2
    grid = np.vstack((np.full((1, 3), 1 / 3), edge_mid, (eye + 1 / 3) / 2))
    if dense:
        div = 10
        grid = np.asarray([(a / div, b / div, (div - a - b) / div)
                           for a in range(div + 1) for b in range(div + 1 - a)], dtype=np.float32)
    face_list = [face_ids[count > 0], np.repeat(cut_faces, len(grid))]
    coeff_list = [uv[count > 0], np.tile(grid, (len(cut_faces), 1))]
    if len(fallback_faces):
        # Duplicate-free fallback for nearly coplanar triangle-pair hits.
        face_list.append(fallback_faces)
        coeff_list.append(np.full((len(fallback_faces), 3), 1 / 3))
    return np.concatenate(face_list), np.concatenate(coeff_list).clip(0, 1)


def summarize(distance, overlaps, samples):
    result = {}
    for name in ("rest", *CLIPS):
        rows = [i for i, sample in enumerate(samples) if sample[0] == name]
        d = distance[rows]
        frame, _ = np.unravel_index(d.argmin(), d.shape)
        pairs = overlaps[rows]
        result[name] = {
            "samples": len(rows),
            "max_verts_inside": int((d < 0).sum(axis=1).max()),
            "min_signed_dist": float(d.min()),
            "minimum_vertex_frame": samples[rows[frame]][1],
            "max_triangle_pairs": int(pairs.max()),
            "max_pair_frame": samples[rows[int(pairs.argmax())]][1],
            "sum_triangle_pairs": int(pairs.sum()),
            "overlap_frames": int((pairs > 0).sum()),
        }
    return result


def scan(posed, triangles, samples, collect=False, body_zones=None, garment_zones=None):
    distance = np.empty(posed.shape[:2], dtype=np.float32)
    overlaps = np.zeros(len(samples), dtype=int)
    face_hits = np.zeros(len(triangles), dtype=int)
    constraints, residuals = [], []
    tri_tuples = [tuple(tri) for tri in triangles.tolist()]
    for i, (name, frame, tree, body, body_faces) in enumerate(samples):
        points = posed[i]
        coords = points.tolist()
        signed, norms = signed_hits(tree, coords)
        distance[i] = signed
        surface = BVHTree.FromPolygons(coords, tri_tuples, all_triangles=True)
        pairs = np.asarray(sorted(tree.overlap(surface)), dtype=np.int32).reshape(-1, 2)
        overlaps[i] = len(pairs)

        if collect:
            failures, = np.where(signed < MARGIN)
            # Repeat vertex indices in all slots so both contact types share
            # the same three-corner interpolation and Jacobian representation.
            vert = np.repeat(failures[:, None], 3, axis=1)
            factor = np.zeros(vert.shape, dtype=np.float32)
            factor[:, 0] = 1
            normals = norms[failures]
            values = signed[failures]
        if len(pairs):
            np.add.at(face_hits, pairs[:, 1], 1)
            if collect or body_zones is not None:
                f, bary = pair_witnesses(points, triangles, body, body_faces, pairs[:, ::-1],
                                         dense=body_zones is not None and name != "rest")
                corners = triangles[f]
                contact = np.einsum("nk,nki->ni", bary, points[corners])
                d, n = signed_hits(tree, contact.tolist())
                if collect:
                    # One deepest signed witness per face plus any true
                    # intersection points are enough to move the whole patch.
                    order = np.lexsort((d, f))
                    worst = order[np.r_[True, np.diff(f[order]) != 0]]
                    use = worst
                    vert = np.concatenate((vert, corners[use]))
                    factor = np.concatenate((factor, bary[use]))
                    normals = np.concatenate((normals, n[use]))
                    values = np.r_[values, d[use]]
                if body_zones is not None:
                    names = {}
                    for b, g in pairs:
                        label = garment_zones[g] + " / " + body_zones[b]
                        if label not in names:
                            names[label] = {"pairs": 0, "garment_faces": set()}
                        names[label]["pairs"] += 1
                        names[label]["garment_faces"].add(int(g))
                    for info in names.values():
                        mask = np.isin(f, list(info.pop("garment_faces")))
                        info["deepest_sample_mm"] = float(min(0, d[mask].min()) * 1000)
                    residuals.append({"clip": name, "frame": frame, "pairs": len(pairs),
                                      "deepest_sample_mm": float(min(0, d.min()) * 1000),
                                      "regions": names})
        if collect and len(vert):
            keep = values < MARGIN
            constraints.append((i, vert[keep], factor[keep], normals[keep], values[keep]))
    return distance, overlaps, face_hits, constraints, residuals


def reimport(path):
    return PRIOR["reimport"](path)


def verify(path):
    scene, arm, body, garment = reimport(path)
    points = mesh_points(garment.data)
    triangles = np.array(mesh_triangles(garment.data), dtype=np.int32)
    names = tuple(bone.name for bone in arm.data.bones)
    body_weights = read_weights(body, names, validate=False)
    body_zones = [names[body_weights[list(face.vertices)].sum(axis=0).argmax()].removeprefix("mixamorig:")
                  for face in body.data.polygons]
    mask = zones(points[triangles].mean(axis=1))
    garment_zones = [next(name for name, region in mask.items() if name != "torso" and region[i])
                     for i in range(len(triangles))]
    samples, positions, shared_faces = [], [], None
    for name, frame in frames():
        set_pose(scene, arm, name, frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        coords, faces = posed_mesh(body, depsgraph)
        if shared_faces is None:
            shared_faces = np.asarray(faces, dtype=np.int32)
        samples.append((name, frame, BVHTree.FromPolygons(coords, faces),
                        np.asarray(coords, dtype=np.float32), shared_faces))
        posed, _ = posed_mesh(garment, depsgraph)
        positions.append(posed)
    distances, overlaps, face_hits, _, residuals = scan(
        np.asarray(positions, dtype=np.float32), triangles, samples,
        body_zones=body_zones, garment_zones=garment_zones,
    )
    result = {
        "glb_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "triangles": len(triangles), "vertices": len(points),
        "samples": len(samples), "clips": summarize(distances, overlaps, samples),
        "rest_clearance": {zone: stats(distances[0, mask]) for zone, mask in zones(points).items()},
        "longest_affected_edges_mm": float(np.linalg.norm(
            points[triangles[face_hits > 0]] - points[np.roll(triangles[face_hits > 0], 1, axis=1)],
            axis=2).max(initial=0) * 1000),
        "rest_limit_m": {"torso_body": .020, "cuff": .020, "hem": .030,
                         "shoulder_armpit": .030, "sleeve": .030},
        "rest_vertices_over_limit": int((distances[0] > limits(points) + 1e-6).sum()),
        "cuff_x_span_m": {
            side: [float(value) for value in (points[mask, 0].min(), points[mask, 0].max())]
            for side, mask in (("left", zones(points)["cuff"] & (points[:, 0] > 0)),
                               ("right", zones(points)["cuff"] & (points[:, 0] < 0)))
        },
        "vertex_residuals": [
            {"clip": name, "frame": frame, "vertices": int((row < 0).sum()),
             "deepest_mm": float(-row.min() * 1000)}
            for (name, frame, _, _, _), row in zip(samples, distances) if row.min() < 0
        ],
        "triangle_residuals": residuals,
    }
    output = "baseline_dense.json" if path != GLB else "dense_check.json"
    (HERE / output).write_text(json.dumps(result, indent=2) + "\n")
    print("DENSE EXPORTED", result["clips"], flush=True)


def smooth_weights(mesh, points, weights, amount):
    neighbor = PRIOR["adjacency"](mesh)
    average = PRIOR["average"]
    x, _, z = points.T
    shoulder = (np.abs(x) > .065) & (np.abs(x) < .16) & (z > .46) & (z < .59)
    elbow = (np.abs(x) >= .145) & (np.abs(x) < .237)
    hem = (z < .455) & (np.abs(x) < .135)
    factor = (amount * np.where(shoulder | elbow | hem, 1, .15))[:, None]
    return limit_weights(weights + factor * (average(weights, neighbor) - weights))


def anatomical_weights(garment, body, names, points, tree):
    prior = read_weights(garment, names)
    weights = PRIOR["nearest_body_weights"](points, body, names, tree)
    region = zones(points)
    simple = tuple(name.removeprefix("mixamorig:") for name in names)
    x = points[:, 0]
    for side, sign in (("Left", 1), ("Right", -1)):
        forearm = simple.index(side + "ForeArm")
        hand = simple.index(side + "Hand")
        fingers = [i for i, name in enumerate(simple) if name.startswith(side + "Hand") and i != hand]
        weights[:, hand] += weights[:, fingers].sum(axis=1)
        weights[:, fingers] = 0
        # Keep the rim attached at the arm end even when fingers curl.
        cuff = region["cuff"] & (sign * x > 0)
        weights[cuff, forearm] += .75 * weights[cuff, hand]
        weights[cuff, hand] *= .25
    legs = [i for i, name in enumerate(simple) if any(token in name for token in ("Leg", "Foot", "Toe"))]
    weights[:, simple.index("Hips")] += .65 * weights[:, legs].sum(axis=1)
    weights[:, legs] *= .35
    # Keep the supported hood/collar blend, and rebind the panels and sleeves
    # to their anatomical neighborhood instead of isolated pose corrections.
    weights[region["hood"] | region["collar"]] = prior[region["hood"] | region["collar"]]
    for _ in range(3):
        weights = smooth_weights(garment.data, points, weights, .31)
    return limit_weights(weights)


def subdivide_contacts(garment, triangles, hits, budget):
    if budget <= 1 or not hits.any():
        return 0
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.index_update()
    bm.edges.index_update()
    frequency = {}
    for face, count in zip(triangles, hits):
        if count == 0:
            continue
        for a, b in zip(face, np.roll(face, 1)):
            key = tuple(sorted((a, b)))
            frequency[key] = frequency.get(key, 0) + int(count)
    candidates = []
    for edge in bm.edges:
        key = tuple(sorted(v.index for v in edge.verts))
        length = edge.calc_length()
        count = frequency.get(key, 0)
        if count and length >= .009 and edge.link_faces:
            priority = length ** 1.5 * (1 + math.log1p(count))
            candidates.append((-priority, key, edge))
    candidates.sort(key=lambda item: item[:2])
    selected = []
    for _, _, edge in candidates:
        cost = len(edge.link_faces)
        if cost <= budget:
            selected.append(edge)
            budget -= cost
        if budget == 0:
            break
    if not selected:
        bm.free()
        return 0
    bmesh.ops.subdivide_edges(bm, edges=selected, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[face for face in bm.faces if len(face.verts) > 3])
    bm.to_mesh(garment.data)
    bm.free()
    garment.data.update()
    assert len(mesh_triangles(garment.data)) <= TRIANGLE_LIMIT
    return len(selected)


def skin_pose(points, weights, transforms):
    matrices = skin_matrices(transforms, weights)
    posed = np.einsum("fvij,vj->fvi", matrices[..., :3], points) + matrices[..., 3]
    return posed, matrices


def simplex(weights):
    """Project four coefficients to the nonnegative, normalized simplex."""
    order = np.sort(weights, axis=1)[:, ::-1]
    excess = (order.cumsum(axis=1) - 1) / np.arange(1, 5)
    offset = np.max(excess, axis=1, keepdims=True)
    return np.maximum(0, weights - offset).astype(np.float32)


def contact_planes(constraints, points, weights, columns, skin, transforms, cuff, weight_scale):
    ids, gradients, depths = [], [], []
    for frame, v, factor, normal, value in constraints:
        if not len(v):
            continue
        local = np.einsum("ni,ncij->ncj", normal, skin[frame, v, :, :3])
        local[..., 0] *= np.where(cuff[v], .10, 1)
        matrices = transforms[frame, columns[v]]
        joint_positions = np.einsum("ncqij,ncj->ncqi", matrices[..., :3], points[v]) + matrices[..., 3]
        skin_term = np.einsum("ni,ncqi->ncq", normal, joint_positions)
        skin_term -= skin_term.mean(axis=2, keepdims=True)
        skin_term *= weight_scale[v, None]
        ids.append(v)
        gradients.append(np.concatenate((local, skin_term), axis=2) * factor[..., None])
        depths.append(value)
    return np.concatenate(ids), np.concatenate(gradients), np.concatenate(depths)


def cap_rest(points, tree):
    caps = limits(points)
    for _ in range(3):
        d, normal = signed_hits(tree, points.tolist())
        correction = np.maximum(.0004 - d, 0) - np.maximum(d - caps + .00006, 0)
        points += normal * correction[:, None]
    return points


def smooth_step(step, neighbors):
    avg = PRIOR["average"]
    smooth = step.copy()
    for _ in range(3):
        smooth = .68 * smooth + .32 * avg(smooth, neighbors)
    length = np.linalg.norm(step, axis=1)
    direction = step / length.clip(1e-9)[:, None]
    required = np.maximum(0, length - np.einsum("vi,vi->v", smooth, direction))
    return smooth + direction * required[:, None]


def limited_step(delta, maximum):
    return delta * np.minimum(1, maximum / np.linalg.norm(delta, axis=1).clip(1e-9))[:, None]


def worst_directional_step(v, gradient, value, count):
    """Keep the worst constraint in each rest-space direction at a vertex."""
    size = np.linalg.norm(gradient, axis=2)
    row = np.repeat(np.arange(len(v)), 3)
    directions = gradient[..., :3]
    axis = abs(directions).argmax(axis=2)
    sign = np.take_along_axis(directions, axis[..., None], axis=2).squeeze(2) > 0
    group = (6 * v + 2 * axis + sign).ravel()
    norm_sq = np.square(gradient).sum(axis=(1, 2)).clip(.055)
    requirement = np.maximum(0, MARGIN - value) / norm_sq
    rank = (requirement[:, None] * size).ravel()
    strongest = np.zeros(6 * count)
    np.maximum.at(strongest, group, rank)
    active, = np.where((rank > 1e-8) & (rank >= strongest[group]))
    chosen = np.full(6 * count, -1)
    np.maximum.at(chosen, group[active], active)
    active = chosen[chosen >= 0]
    result = np.zeros((count, 7), dtype=np.float32)
    normalized = gradient.reshape(-1, 7)[active] * requirement[row[active], None]
    # Large penetrations get priority when planes oppose one another.
    importance = rank[active].clip(1e-4) ** 1.3
    ids = v.ravel()[active]
    total = np.bincount(ids, weights=importance, minlength=count)
    for c in range(result.shape[1]):
        result[:, c] = np.bincount(ids, weights=normalized[:, c] * importance, minlength=count)
    return result / total.clip(1e-12)[:, None]


def radial_step(v, gradient, value, direction):
    component = np.einsum("nci,nci->nc", gradient[..., :3], direction[v])
    directional = component.clip(0).sum(axis=1)
    valid = (directional >= .40)[:, None] & (component >= .14)
    offsets = np.where(valid, (MARGIN - value)[:, None] / directional.clip(.40)[:, None], 0)
    required = np.zeros(len(direction), dtype=np.float32)
    np.maximum.at(required, v.ravel(), offsets.ravel())
    return direction * required[:, None]


def pose_subset(samples, distance, overlaps, constraints):
    size = len(samples)
    rows = {0, *range(1, size, 19)}
    for name in CLIPS:
        group = np.array([i for i, sample in enumerate(samples) if sample[0] == name])
        rows.update(group[np.argsort(overlaps[group], kind="stable")[-3:]])
        rows.update(group[np.argsort(distance[group].min(axis=1), kind="stable")[:3]])
    # Include the worst triangle-interior sample even if the corners clear.
    depth = [(values.min(), frame) for frame, _, _, _, values in constraints if len(values)]
    rows.update(frame for _, frame in sorted(depth)[:8])
    return np.array(sorted(rows))


def score_pose(points, weights, triangles, samples, transforms):
    posed, _ = skin_pose(points, weights, transforms)
    distances, overlaps, _, _, _ = scan(posed, triangles, samples)
    return float(overlaps.sum() + (distances < 0).sum() * 3 + overlaps[0] * 18
                 + np.square(np.maximum(0, -distances) * 1000).sum() * .11
                 + ((distances[0] > limits(points) + .000065).sum() * 70))


def guard_rest(mesh, before, after, rest_tree):
    shape = PRIOR["RestShape"](mesh, before, rest_tree)
    current = before.copy()
    change = after - before
    moved = np.linalg.norm(change, axis=1)
    for v in np.argsort(-moved, kind="stable"):
        if moved[v] < 0.000005:
            break
        for fraction in (1., .65, .35, .15):
            proposal = before[v] + fraction * change[v]
            if shape.accepts(v, proposal, current):
                current[v] = proposal
                break
    return current


def local_cost(distance, weight=None):
    deficit = np.maximum(MARGIN - distance, 0) * 1000
    if weight is None:
        weight = np.ones((len(distance), 1), dtype=np.float32)
    return ((.55 * deficit.max(axis=0) ** 2) + ((deficit ** 2 * weight).sum(axis=0) / weight.sum())
            + 1.8 * ((distance < 0) * weight).sum(axis=0) / weight.sum())


def local_fit(mesh, points, original, weights, constraints, skin, transforms, samples, distances,
              displacement, columns, correction, iteration):
    """Refit contact patches against both endpoints and triangle interiors."""
    tree = samples[0][2]
    shape = PRIOR["RestShape"](mesh, points, tree)
    cuff = zones(original)["cuff"]
    v, bary, posed_rows, known = [], [], [], []
    for frame, corners, coeff, _, signed in constraints:
        if frame:
            # One-vertex entries duplicate the corner index by design. The
            # independent vertex tests below cover them at greater density.
            selected = (coeff > .12).sum(axis=1) > 1
            v.append(corners[selected])
            bary.append(coeff[selected])
            posed_rows.extend([frame] * int(selected.sum()))
            known.append(signed[selected])
    v, bary, known = np.concatenate(v), np.concatenate(bary), np.concatenate(known)
    posed_rows = np.asarray(posed_rows, dtype=np.int32)
    flat = v.ravel()
    order = np.argsort(flat, kind="stable")
    groups = np.searchsorted(flat[order], np.arange(len(points) + 1))
    worst = distances.min(axis=0).copy()
    np.minimum.at(worst, flat, np.repeat(known, 3))
    affected, = np.where(worst < MARGIN)
    affected = affected[np.argsort(worst[affected], kind="stable")]
    neighbors = PRIOR["adjacency"](mesh)
    neighborhood = PRIOR["average"](points - original, neighbors) + original
    cuff_span = .0012
    directions = PRIOR["scaled_directions"](18).astype(np.float32)
    rng = np.random.default_rng(531 + iteration)
    if len(affected) > 1600:
        affected = affected[:1600]
    change_count = 0
    clip_rows = [np.asarray([r for r, entry in enumerate(samples) if entry[0] == clip]) for clip in CLIPS]
    for i in affected:
        initial = points[i].copy()
        initial_weights = weights[i].copy()
        rows = {0, *np.argsort(distances[:, i], kind="stable")[:11]}
        for group in clip_rows:
            rows.update(group[np.argsort(distances[group, i], kind="stable")[:2]])
        row_list = np.asarray(sorted(rows), dtype=np.int32)
        contact = order[groups[i]:groups[i + 1]]
        contact = contact[bary.ravel()[contact] > .13]
        contact_depth = known[contact // 3]
        if len(contact):
            ranked = contact[np.argsort(contact_depth, kind="stable")]
            by_clip = []
            for group in clip_rows:
                in_clip = ranked[np.isin(posed_rows[ranked // 3], group)]
                by_clip.extend(in_clip[:3])
            spread = contact[np.linspace(0, len(contact) - 1, min(7, len(contact)), dtype=int)]
            contact = np.unique(np.r_[ranked[:11], by_clip, spread]).astype(np.int32)
        contact_frame = posed_rows[contact // 3]
        group = v[contact // 3]
        coefficients = bary[contact // 3]
        current_triangle = (np.einsum("ncij,ncj->nci", skin[contact_frame[:, None], group, :, :3],
                                     points[group]) + skin[contact_frame[:, None], group, :, 3])
        witness = np.einsum("nci,nc->ni", current_triangle, coefficients)
        old_trajectories = np.einsum("nij,j->ni", skin[contact_frame, i, :, :3], initial) + skin[contact_frame, i, :, 3]
        coefficient = bary.ravel()[contact]
        layout = np.vstack((np.zeros((1, 3)), displacement[i] * np.array([.35, 1., 1.65])[:, None],
                            (neighborhood[i] - initial) * np.array([.35, .8])[:, None],
                            (.00145 * directions), (.0038 * directions[::2]),
                            (.006 * directions[1::3])))
        jitter = rng.choice(len(directions), 8, replace=False)
        layout = np.vstack((layout, .002 * directions[jitter], .0039 * directions[jitter[:4]]))
        options = initial + layout
        if cuff[i]:
            options[:, 0] = np.clip(options[:, 0], original[i, 0] - cuff_span, original[i, 0] + cuff_span)
        active = columns[i]
        start = initial_weights[active]
        proposal_weights = np.tile(initial_weights, (len(options), 1))
        wdelta = np.clip(correction[i], -.075, .075)
        sw = np.vstack((np.zeros((len(options) - len(jitter) - 4, 4)),
                       np.tile(.65 * wdelta, (len(jitter), 1)),
                       np.tile(wdelta, (4, 1))))
        proposal_weights[:, active] = simplex(start + sw)
        union = np.flatnonzero(np.any(proposal_weights > 0, axis=0))
        weights_used = proposal_weights[:, union]

        def trace(pose_rows):
            matrix = transforms[pose_rows][:, union].reshape(len(pose_rows), len(union), 12)
            blend = (weights_used @ matrix).reshape(len(pose_rows), len(options), 3, 4)
            return np.einsum("ncij,cj->nci", blend[..., :3], options) + blend[..., 3]

        candidate_vertex = trace(row_list)
        d = np.array([signed_hits(samples[row][2], p.tolist())[0]
                      for row, p in zip(row_list, candidate_vertex)])
        if len(contact):
            candidate_contact = witness[:, None] + coefficient[:, None, None] * (
                trace(contact_frame) - old_trajectories[:, None])
            triangle_d = np.array([signed_hits(samples[row][2], p.tolist())[0]
                                   for row, p in zip(contact_frame, candidate_contact)])
            good = np.vstack((d, triangle_d))
            importance = np.r_[np.ones(len(d)), np.full(len(triangle_d), .62)][:, None]
        else:
            good = d
            importance = None
        score = local_cost(good, importance)
        score += .13 * np.linalg.norm((options - neighborhood[i]) * 1000, axis=1) ** 2
        score += .12 * np.linalg.norm((options - initial) * 1000, axis=1)
        score += .25 * np.square((proposal_weights - initial_weights) * 20).sum(axis=1)
        score[d[0] > limits(options) - .00004] = np.inf
        score[d[0] < .00017] = np.inf
        for candidate in np.argsort(score, kind="stable")[:9]:
            if candidate == 0:
                break
            if not np.isfinite(score[candidate]) or not shape.accepts(i, options[candidate], points):
                continue
            points[i] = options[candidate]
            weights[i] = proposal_weights[candidate]
            # Keep neighboring triangle witnesses consistent during the pass.
            skin[:, i] = (weights[i, union] @ transforms[:, union].reshape(len(samples), len(union), 12)).reshape(-1, 3, 4)
            change_count += 1
            break
    print("LOCAL CONTACT REFINEMENT", iteration, len(affected), change_count, flush=True)
    return points, smooth_weights(mesh, points, weights, .013)


def fit_step(mesh, points, original, weights, anatomical, constraints, skin, transforms, samples,
             distances, overlaps, triangles, iteration):
    if not constraints:
        return points, weights
    rest_tree = samples[0][2]
    cuff = zones(original)["cuff"]
    columns = np.argsort(-np.maximum(weights, anatomical * .8), axis=1, kind="stable")[:, :4]
    active = np.take_along_axis(weights, columns, axis=1)
    scales = np.full(len(points), 3., dtype=np.float32)
    scales[cuff] = 1.4
    v, gradient, value = contact_planes(constraints, points, weights, columns, skin, transforms,
                                        cuff, scales)
    delta = worst_directional_step(v, gradient, value, len(points))
    avg_neighbors = PRIOR["adjacency"](mesh)
    adj = PRIOR["average"]
    raw = delta[:, :3]
    raw[cuff, 0] *= .1
    _, direction = signed_hits(rest_tree, points.tolist())
    garment_normal = np.asarray([v.normal[:] for v in mesh.vertices], dtype=np.float32)
    matching = np.einsum("vi,vi->v", direction, garment_normal) > .40
    direction[matching] = .60 * direction[matching] + .40 * garment_normal[matching]
    direction[cuff, 0] *= .10
    radial = radial_step(v, gradient, value, direction)
    smoothed = smooth_step(raw, avg_neighbors)
    radial = smooth_step(radial, avg_neighbors)
    # Test patch moves at different magnitudes against all clips, including
    # negative space between nearby limbs. A large outward move can remove
    # contact with the torso while creating contact with a swinging forearm.
    rows = pose_subset(samples, distances, overlaps, constraints)
    tests = [samples[row] for row in rows]
    motion = transforms[rows]
    best_score = score_pose(points, weights, triangles, tests, motion)
    best = points, weights, "unchanged"
    previous_score = best_score
    trials = (
        ("project", smoothed, 1, .75, .0035),
        ("damped", smoothed, .42, .35, .0017),
        ("radial", radial, .72, 0, .0032),
        ("smooth", adj(smoothed, avg_neighbors), 1.15, .30, .0031),
        ("reweight", smoothed, .18, 1.7, .0010),
        ("take-in", -.36 * radial, .75, 0, .0016),
    )
    for name, shift, factor, skin_factor, budget in trials:
        trial = points + limited_step(shift * factor, budget)
        trial[cuff, 0] = np.clip(trial[cuff, 0], original[cuff, 0] - .0012, original[cuff, 0] + .0012)
        trial = cap_rest(trial, rest_tree)
        trial = guard_rest(mesh, points, trial, rest_tree)
        new_weights = weights.copy()
        if skin_factor:
            correction = np.clip(delta[:, 3:] * scales[:, None] * skin_factor, -.032, .032)
            np.put_along_axis(new_weights, columns, simplex(active + correction), axis=1)
        new_weights = smooth_weights(mesh, trial, new_weights, .018)
        score = score_pose(trial, new_weights, triangles, tests, motion)
        if score < best_score:
            best_score = score
            best = trial, new_weights, name
    if iteration >= 6:
        inward = smooth_step(radial_step(v, gradient, value, -direction), avg_neighbors)
        for name, move, amount in (("inward", inward, 1.), ("balanced", .65 * radial + inward, .78),
                                   ("outward-small", radial, .28)):
            trial = points + limited_step(move * amount, .0028)
            trial[cuff, 0] = np.clip(trial[cuff, 0], original[cuff, 0] - .0012, original[cuff, 0] + .0012)
            trial = guard_rest(mesh, points, cap_rest(trial, rest_tree), rest_tree)
            new_weights = smooth_weights(mesh, trial, weights, .012)
            score = score_pose(trial, new_weights, triangles, tests, motion)
            if score < best_score:
                best_score, best = score, (trial, new_weights, name)
    if iteration >= 3 and (best_score > previous_score * .96 or iteration % 2 == 0):
        local_points, local_weights = local_fit(mesh, points.copy(), original, weights.copy(), constraints,
                                                skin, transforms, samples, distances, smoothed, columns,
                                                delta[:, 3:] * scales[:, None], iteration)
        factors = (1.,) if iteration < 6 else (1., .5, .23)
        for factor in factors:
            candidate = points + factor * (local_points - points)
            local_skin = limit_weights(weights + factor * (local_weights - weights))
            local_score = score_pose(candidate, local_skin, triangles, tests, motion)
            if local_score < best_score:
                best_score = local_score
                best = candidate, local_skin, f"local {factor:g}"
    print("LINE SEARCH", iteration, best[2], round(best_score), len(rows), flush=True)
    return best[:2]


def finalize_rest(garment, points, weights, tree):
    """Enforce the clearance cap at final region boundaries before export."""
    before = points
    points = points.copy()
    shape = PRIOR["RestShape"](garment.data, points, tree)
    distance, normals = signed_hits(tree, points.tolist())
    cap = limits(points)
    for vertex in np.flatnonzero(distance > cap - .00002):
        point = points[vertex].copy()
        inward = normals[vertex]
        excess = distance[vertex] - cap[vertex] + .00016
        for stretch in (1., 1.5, 2.4, 3.5):
            proposal = point - inward * (excess * stretch)
            d, _ = signed_hits(tree, [proposal.tolist()])
            upper = limits(np.asarray([proposal]))[0]
            if .00022 <= d[0] <= upper - .00004 and shape.accepts(vertex, proposal, points):
                points[vertex] = proposal
                break
    touched = np.linalg.norm(points - before, axis=1) > 1e-7
    if touched.any():
        smoothed = smooth_weights(garment.data, points, weights, .013)
        weights = np.where(touched[:, None], smoothed, weights)
    return points, weights, int(touched.sum())


def export(garment, arm, body, points, names, weights):
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    garment.data.vertices.foreach_set("co", np.asarray(points, dtype=np.float32).ravel())
    garment.data.update()
    write_weights(garment, names, limit_weights(weights))
    garment.name = garment.data.name = NAME
    assert len(mesh_triangles(garment.data)) <= TRIANGLE_LIMIT
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
        filepath=str(GLB), export_format="GLB", use_selection=True, export_animations=False,
        export_yup=True, export_all_influences=False, export_def_bones=False,
    )
    garment.parent = arm
    body.hide_render = True
    body.hide_set(True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"{NAME}.blend"))


def build():
    bpy.ops.wm.open_mainfile(filepath=str(ROUND2 / "top_hoodie_v2.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, garment = (scene.objects[name] for name in ("Armature", "Base_Body", "top_hoodie_v2"))
    body.hide_set(False)
    names = tuple(bone.name for bone in arm.data.bones)
    samples, transforms = cache_motion(scene, arm, body, garment, names)
    rest = samples[0][2]
    points = mesh_points(garment.data)
    weights = anatomical_weights(garment, body, names, points, rest)
    triangles = np.asarray(mesh_triangles(garment.data))
    posed, _ = skin_pose(points, weights, transforms)
    d, pairs, hits, _, _ = scan(posed, triangles, samples)
    print("ANATOMICAL REBIND", summarize(d, pairs, samples), flush=True)
    write_weights(garment, names, weights)
    split = subdivide_contacts(garment, triangles, hits, TRIANGLE_LIMIT - len(triangles))
    print("CONTACT EDGES SPLIT", split, flush=True)
    points = mesh_points(garment.data)
    triangles = np.asarray(mesh_triangles(garment.data))
    weights = limit_weights(read_weights(garment, names, validate=False))
    weights = smooth_weights(garment.data, points, weights, .13)
    original = points.copy()
    reference = weights.copy()


    history = []
    best = None
    for iteration in range(ITERATIONS + 1):
        if iteration == 5 and best[1] != 5:
            # A representative subset can prefer a step that regresses the
            # full sweep. Start the second contact search from the best sweep.
            points, weights = best[2].copy(), best[3].copy()
        posed, skin = skin_pose(points, weights, transforms)
        d, pairs, _, constraints, _ = scan(posed, triangles, samples, collect=True)
        metrics = summarize(d, pairs, samples)
        print("FIT", iteration, metrics,
              "triangle pairs", int(pairs.sum()),
              "negative vertices", int((d < 0).sum()),
              "rest max cap excess mm", (d[0] - limits(points)).max() * 1000, flush=True)
        history.append(metrics)
        score = float(pairs.sum() + 3 * (d < 0).sum() + 1000 * (pairs[0] > 0)
                      + 1000 * ((d[0] - limits(points)) > .0001).sum())
        if best is None or score < best[0]:
            best = score, iteration, points.copy(), weights.copy()
        if iteration == ITERATIONS or ((d >= 0).all() and not pairs.any()):
            break
        points, weights = fit_step(garment.data, points, original, weights, reference, constraints,
                                   skin, transforms, samples, d, pairs, triangles, iteration + 1)
    _, chosen, points, weights = best
    points, weights, cap_adjustments = finalize_rest(garment, points, weights, rest)
    print("REST BOUNDARY ADJUSTMENTS", cap_adjustments, flush=True)
    print("EXPORT ITERATION", chosen, "OFFSET METERS", stats(np.linalg.norm(points - original, axis=1)),
          "triangles", len(triangles), flush=True)
    (HERE / "fit_history.json").write_text(json.dumps({
        "margin_m": MARGIN, "selected_iteration": chosen, "split_edges": split,
        "rest_boundary_adjustments": cap_adjustments,
        "offset_m": stats(np.linalg.norm(points - original, axis=1)), "iterations": history,
    }, indent=2) + "\n")
    export(garment, arm, body, points, names, weights)


def configure_render(scene, samples=16):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("QA studio")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.68, .73, .8, 1)
    background.inputs[1].default_value = .42
    focus = Vector((0, 0, .512))
    for name, position, power, size in (
        ("Key", (-1, -1.5, 2.6), 150, 2.2),
        ("Fill", (1.2, -.7, 1.25), 38, 1.8),
        ("Rim", (.4, 1.45, 2), 110, 1.5),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        lamp = bpy.data.objects.new(name, data)
        scene.collection.objects.link(lamp)
        lamp.location = position
        lamp.rotation_euler = (focus - lamp.location).to_track_quat("-Z", "Y").to_euler()


def run_checker(stem):
    path = HERE / (stem + ".py")
    source = path.read_text()
    workbench = ("sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
                 "sc.display.shading.color_type='MATERIAL'")
    assert source.count(workbench) == 1
    source = source.replace(workbench, "")
    # Both supplied scripts use the same filename. Keep each report under its
    # checker name and render the shared camera poses once in --renders.
    source = source.replace("{out}/motion_check.json", "{out}/" + stem + ".json")
    source = source.replace("bpy.ops.render.render(write_still=True)", "None")
    output = io.StringIO()
    argv = sys.argv
    try:
        sys.argv = [str(path), "--", str(MASTER), str(MOTION), str(GLB), str(HERE)]
        with redirect_stdout(output):
            exec(compile(source, str(path), "exec"), {})
    finally:
        sys.argv = argv
    lines = [line for line in output.getvalue().splitlines() if line.startswith("RESULT ")]
    assert len(lines) == 8
    report = "\n".join(lines) + "\n"
    (HERE / (stem + ".txt")).write_text(report)
    print(report, end="", flush=True)


def render():
    scene, arm, body, garment = reimport(GLB)
    configure_render(scene)
    source = json.loads((HERE / "dense_check.json").read_text())
    set_pose(scene, arm, "rest", 1)
    scene.render.resolution_x, scene.render.resolution_y = 900, 580
    focus = Vector((0, 0, .512))
    data = bpy.data.cameras.new("Fit QA camera")
    data.type, data.ortho_scale = "ORTHO", .66
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, direction, show_body in (
        ("rest_front", (0, -1, .04), True),
        ("rest_back", (.30, 1, .27), True),
        ("rest_hoodie", (.24, -1, .28), False),
        ("rest_side", (1, -.15, .14), True),
    ):
        body.hide_render = not show_body
        camera.location = focus + 3 * Vector(direction)
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    body.hide_render = False
    scene.render.resolution_x = scene.render.resolution_y = 640
    data.ortho_scale = 1.30
    focus = Vector((0, 0, .5))
    camera.location = (0, -6, .5)
    camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
    for name in CLIPS:
        summary = source["clips"][name]
        frame = (summary["max_pair_frame"] if summary["max_triangle_pairs"]
                 else summary["minimum_vertex_frame"])
        set_pose(scene, arm, name, frame)
        scene.render.filepath = str(HERE / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def inspect_export():
    glb = GLB.read_bytes()
    magic, version, size, json_size = struct.unpack_from("<4sIII", glb)
    assert (magic, version, size) == (b"glTF", 2, len(glb))
    data = json.loads(glb[20:20 + json_size])
    blob = glb[28 + json_size:]
    assert len(data["meshes"]) == len(data["skins"]) == 1 and not data.get("animations")
    joints = data["skins"][0]["joints"]
    assert len(joints) == 65
    primitives = data["meshes"][0]["primitives"]
    triangles = vertices = max_influences = 0
    for primitive in primitives:
        attr = primitive["attributes"]
        assert primitive.get("mode", 4) == 4 and "WEIGHTS_1" not in attr
        triangles += data["accessors"][primitive["indices"]]["count"] // 3
        accessor = data["accessors"][attr["WEIGHTS_0"]]
        vertices += accessor["count"]
        assert accessor["type"] == "VEC4" and accessor["componentType"] == 5126
        view = data["bufferViews"][accessor["bufferView"]]
        start = accessor.get("byteOffset", 0) + view.get("byteOffset", 0)
        stride = view.get("byteStride", 16)
        for i in range(accessor["count"]):
            weights = struct.unpack_from("<4f", blob, start + i * stride)
            assert abs(sum(weights) - 1) < 1e-5 and min(weights) >= 0
            max_influences = max(max_influences, sum(weight > 0 for weight in weights))
    assert triangles <= TRIANGLE_LIMIT and max_influences <= 4
    dimensions = []
    for image in data["images"]:
        view = data["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        assert blob[start:start + 8] == b"\x89PNG\r\n\x1a\n"
        dimensions.append(struct.unpack_from(">II", blob, start + 16))
    assert dimensions == [(1024, 1024)]
    result = {
        "glb_sha256": hashlib.sha256(glb).hexdigest(), "glb_bytes": len(glb),
        "blend_bytes": (HERE / f"{NAME}.blend").stat().st_size,
        "mesh_count": len(data["meshes"]), "animation_count": len(data.get("animations", [])),
        "joints": [data["nodes"][joint]["name"] for joint in joints],
        "max_influences": max_influences, "texture_dimensions": dimensions,
        "triangles": triangles, "vertices": vertices,
    }
    (HERE / "export_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print("EXPORT CHECK", {k: v for k, v in result.items() if k != "joints"}, flush=True)


if __name__ == "__main__":
    if "--baseline" in sys.argv:
        verify(ROUND2 / "top_hoodie_v2.glb")
    elif "--verify" in sys.argv:
        inspect_export()
        verify(GLB)
    elif "--checkers" in sys.argv:
        run_checker("motion_check")
        run_checker("motion_check_tri")
    elif "--renders" in sys.argv:
        render()
    else:
        build()
