"""Fit the original cargo pants using Blender 5.1 and the gallery master rig.

Background entry points: build (default), verify, checkers, renders.
Pass the entry point after Blender's -- separator. All output stays here.
"""

from collections import defaultdict
from contextlib import redirect_stdout
import hashlib
import io
from itertools import product
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[1]
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS.parents[1] / "models/tripo-chibi-motion/motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
GLB = HERE / "pants_v1.glb"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
MARGIN = .00215
MINIMUM = .0005
REST_LIMIT = .030
TRIANGLE_LIMIT = 6000
ITERATIONS = 12
SIMPLEX = np.eye(3, dtype=np.float32)


def imports(path, merge=False):
    before = set(bpy.context.scene.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=merge)
    return [obj for obj in bpy.context.scene.objects if obj.name not in before]


def load_master():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    arm.animation_data_create()
    assert len(arm.data.bones) == 65
    assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
    assert np.allclose(body.matrix_world, np.eye(4), atol=1e-6)
    return scene, arm, body


def load_actions():
    for obj in imports(MOTION):
        obj.hide_render = obj.hide_viewport = True
    for name in CLIPS:
        assert len(bpy.data.actions[name].slots) == 1


def set_pose(scene, arm, clip, frame):
    action = bpy.data.actions[clip] if clip != "rest" else None
    if arm.animation_data.action != action:
        arm.animation_data.action = action
        if action:
            arm.animation_data.action_slot = action.slots[0]
        else:
            for bone in arm.pose.bones:
                bone.matrix_basis.identity()
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def sample_frames():
    yield "rest", 1.0
    for name in CLIPS:
        first, last = bpy.data.actions[name].frame_range
        times = {first, last}
        times.update(half / 2 for half in range(math.ceil(2 * first), math.floor(2 * last) + 1))
        times.update(int(first + (last - first) * k / 12) for k in range(12))
        times.update(range(int(first), int(last) + 1, 3))
        yield from ((name, frame) for frame in sorted(times))


def coordinates(mesh):
    flat = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", flat)
    return flat.reshape(-1, 3)


def triangles(mesh):
    mesh.calc_loop_triangles()
    return np.asarray([tuple(face.vertices) for face in mesh.loop_triangles], dtype=np.int32)


def evaluated_coordinates(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        points = coordinates(mesh)
        matrix = np.asarray(evaluated.matrix_world, dtype=np.float32)
        return points @ matrix[:3, :3].T + matrix[:3, 3]
    finally:
        evaluated.to_mesh_clear()


def tree_for(points, faces):
    return BVHTree.FromPolygons(points.tolist(), faces, all_triangles=True)


def signed_hits(tree, points):
    signed = np.empty(len(points), dtype=np.float32)
    normals = np.empty((len(points), 3), dtype=np.float32)
    for index, xyz in enumerate(points.tolist()):
        nearest, normal, _, _ = tree.find_nearest(xyz)
        signed[index] = (Vector(xyz) - nearest).dot(normal)
        normals[index] = normal
    return signed, normals


def mesh_neighbors(mesh):
    edges = np.asarray([tuple(edge.vertices) for edge in mesh.edges], dtype=np.int32)
    left, right = np.vstack((edges, edges[:, ::-1])).T
    degree = np.bincount(left, minlength=len(mesh.vertices)).clip(1)
    return left, right, degree


def subdivide_contacts(garment, faces, points, weights, hits):
    """Split long incident edges only where a deformed face hits the body."""
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    mesh.verts.index_update()
    deform = mesh.verts.layers.deform.verify()
    for vertex in mesh.verts:
        vertex.co = points[vertex.index]
        vertex[deform].clear()
        for column in np.flatnonzero(weights[vertex.index]):
            vertex[deform][int(column)] = float(weights[vertex.index, column])
    frequency = defaultdict(int)
    for face, count in zip(faces, hits):
        if count:
            for a, b in zip(face, np.roll(face, 1)):
                frequency[tuple(sorted((a, b)))] += int(count)
    candidates = []
    for edge in mesh.edges:
        key = tuple(sorted(v.index for v in edge.verts))
        count = frequency.get(key, 0)
        span = edge.calc_length()
        if count and span >= .012:
            candidates.append((-(span ** 1.5) * (1 + math.log1p(count)), key, edge))
    budget = min(TRIANGLE_LIMIT - len(faces), 850)
    selected = []
    for _, _, edge in sorted(candidates, key=lambda item: item[:2]):
        cost = len(edge.link_faces)
        if cost <= budget:
            selected.append(edge)
            budget -= cost
    if not selected:
        mesh.free()
        return points, weights
    bmesh.ops.subdivide_edges(mesh, edges=selected, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(mesh, faces=[face for face in mesh.faces if len(face.verts) > 3])
    mesh.verts.index_update()
    rebinding = np.zeros((len(mesh.verts), weights.shape[1]), dtype=np.float32)
    for vertex in mesh.verts:
        for column, weight in vertex[deform].items():
            rebinding[vertex.index, column] = weight
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.update()
    assert len(triangles(garment.data)) <= TRIANGLE_LIMIT
    print("CONTACT EDGES SPLIT", len(selected), flush=True)
    return coordinates(garment.data), trim_weights(rebinding)


def average(values, neighbors):
    left, right, degree = neighbors
    result = np.zeros_like(values)
    np.add.at(result, left, values[right])
    return result / degree.reshape((-1,) + (1,) * (values.ndim - 1))


def unit(vectors):
    return vectors / np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-8)


def trim_source(garment):
    """Remove the ankle end caps and the deck hidden under the belt rim."""
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-6)
    faces_before = len(mesh.faces)
    bmesh.ops.bisect_plane(
        mesh, geom=[*mesh.verts, *mesh.edges, *mesh.faces],
        dist=1e-6, plane_co=(0, 0, .036), plane_no=(0, 0, 1),
        clear_inner=True,
    )
    inner = set()
    for face in mesh.faces:
        x, y, z = face.calc_center_median()
        radius = math.hypot(x / .204, (y - .001) / .162)
        if .88 < z < .948 and radius < 1.07:
            inner.add(face)
    seed = min(inner, key=lambda f: math.hypot(*f.calc_center_median()[:2]))
    cap = [seed]
    inner.remove(seed)
    for face in cap:
        for edge in face.edges:
            for neighbor in edge.link_faces:
                if neighbor in inner:
                    inner.remove(neighbor)
                    cap.append(neighbor)
    bmesh.ops.delete(mesh, geom=cap, context="FACES")
    bmesh.ops.triangulate(mesh, faces=[face for face in mesh.faces if len(face.verts) > 3])
    for face in mesh.faces:
        face.smooth = True
    mesh.normal_update()
    print("SOURCE triangles", faces_before, "waist deck faces", len(cap),
          "remaining triangles", len(mesh.faces), flush=True)
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.update()


def position_source(points):
    """Shape-preserving changes of section, with separate hip/crotch heights."""
    x, y, z = points.T
    height = np.interp(z, [.036, .095, .34, .60, .67, .875, .975822],
                       [.073, .104, .193, .292, .320, .380, .416])
    # The off-center calf fabric is tapered relative to the two ankle centers.
    split = np.clip((.612 - z) / .11, 0, 1)
    leg_scale = np.interp(z, [.036, .10, .25, .45, .61], [.408, .365, .337, .385, .429])
    torso_scale = np.interp(z, [.60, .72, .88, .975822], [.43, .444, .466, .481])
    leg_x = np.sign(x) * .079 + (x - np.sign(x) * .187) * leg_scale
    fit_x = .00072 + split * leg_x + (1 - split) * x * torso_scale
    sy = np.interp(z, [.036, .095, .28, .44, .60, .68, .77, .90, .976],
                   [.402, .387, .371, .371, .431, .456, .433, .454, .473])
    dy = np.interp(z, [.036, .10, .25, .42, .60, .69, .83, .975822],
                   [.001, .003, .002, -.002, -.016, -.023, -.023, -.018])
    seat = .009 * np.exp(-((height - .298) / .034) ** 2)
    fit_y = y * sy + dy + seat * np.clip((y - .075) / .07, 0, 1)
    return np.column_stack((fit_x, fit_y, height)).astype(np.float32)


def install_texture(garment):
    images = {}
    for material in garment.data.materials:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                images[node.image.name] = node.image
    for name, image in sorted(images.items()):
        width, height = image.size
        scale = 1024 / max(width, height)
        if scale >= 1:
            continue
        image.scale(round(width * scale), round(height * scale))
        # Repack current pixels. Reusing the originally packed file would
        # otherwise re-export the source 4K image.
        image.file_format = "PNG"
        image.pack()
        image.name = Path(name).stem + "_1024.png"
        image.filepath = "//" + image.name


def rest_project(points, tree, lo=.00235, hi=.0297):
    # A second nearest face can take over at a concave hip or cuff, so
    # re-evaluate the signed distance after each projection.
    result = points.copy()
    for _ in range(7):
        d, n = signed_hits(tree, result)
        bad = (d < lo - .000005) | (d > hi + .000005)
        if not bad.any():
            break
        result[bad] += (d[bad].clip(lo, hi) - d[bad])[:, None] * n[bad]
    return result


def rest_initialize(points, tree, neighbors):
    current = points.copy()
    for index, xyz in enumerate(points):
        x, y, z = xyz
        margin = .0055
        if z >= .323:
            axis = Vector((.00072, -.017, z))
            radius = .23
            margin = .008
        elif z <= .278:
            axis = Vector((math.copysign(.079, x), .008 - .035 * (z - .08), z))
            radius = .11
        else:
            continue
        direction = (Vector(xyz) - axis).normalized()
        origin = axis + direction * radius
        nearest, normal, _, _ = tree.ray_cast(origin, -direction, radius)
        # A medial ray can hit the far leg first. Its near-facing side has
        # the opposite orientation relative to this leg's radial direction.
        if nearest is not None and z <= .278 and abs(x) < .077:
            for _ in range(4):
                if math.copysign(1, nearest.x - .00072) == math.copysign(1, x):
                    break
                origin = nearest - direction * .000015
                nearest, normal, _, _ = tree.ray_cast(origin, -direction, (origin - axis).length)
                if nearest is None:
                    break
        if nearest is not None and normal.dot(direction) > .2:
            deficit = margin / normal.dot(direction) - (Vector(xyz) - nearest).dot(direction)
            if 0 < deficit < .05:
                current[index] += np.asarray(direction) * deficit
    current = rest_project(current, tree, lo=.0055)
    for _ in range(3):
        delta = current - points
        smooth = .85 * delta + .15 * average(delta, neighbors)
        current = rest_project(points + smooth, tree, lo=.0055)
    return current


def tighten_waist(points, tree):
    """Take in the waistband where the master forearms pass the hips."""
    _, direction = signed_hits(tree, points)
    width = .008 * np.exp(-((points[:, 2] - .396) / .042) ** 2)
    return rest_project(points - width[:, None] * direction, tree, lo=.003)


def waist_reference(mesh, points):
    """Build a UV lookup for the fitted silhouette before taking in the belt."""
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.uv
    coords = np.asarray([(*item.vector, 0) for item in uv], dtype=np.float32)
    loops = np.asarray([tuple(face.loops) for face in mesh.loop_triangles])
    uv_faces = coords[loops]
    area = np.cross(uv_faces[:, 1] - uv_faces[:, 0], uv_faces[:, 2] - uv_faces[:, 0])
    valid = np.abs(area[:, 2]) > 1e-11
    vertices = np.asarray([tuple(face.vertices) for face in mesh.loop_triangles])
    return tree_for(coords, loops[valid].tolist()), uv_faces[valid], points[vertices[valid]]


def restore_waist_rim(garment, points, reference, rest_tree):
    """Recover the belt thickness and rim from their original UV correspondence."""
    lookup, uv_faces, reference_faces = reference
    mapped = np.zeros_like(points)
    occurrences = np.zeros(len(points), dtype=np.int32)
    for loop, item in zip(garment.data.loops, garment.data.uv_layers.active.uv):
        vertex = loop.vertex_index
        if points[vertex, 2] < .363:
            continue
        hit, _, face, _ = lookup.find_nearest((*item.vector, 0))
        coeff = barycentric(uv_faces[face:face+1], np.asarray([hit[:]], dtype=np.float32))[0]
        location = coeff @ reference_faces[face]
        if np.linalg.norm(location - points[vertex]) < .035:
            mapped[vertex] += location
            occurrences[vertex] += 1
    valid = occurrences > 0
    mapped[valid] /= occurrences[valid, None]
    amount = np.clip((mapped[:, 2] - .368) / .027, 0, 1)
    amount *= amount * (3 - 2 * amount)
    delta = (mapped - points) * amount[:, None]
    face_list = triangles(garment.data).tolist()
    for gain in (1, .85, .65, .4):
        candidate = rest_project(points + gain * delta, rest_tree, lo=.003)
        distance, _ = signed_hits(rest_tree, candidate)
        if (distance.min() >= MINIMUM and distance.max() <= REST_LIMIT and
                not rest_tree.overlap(tree_for(candidate, face_list))):
            print("WAIST RIM RESTORED", gain, int((amount > 0).sum()), flush=True)
            return candidate
    print("WAIST RIM RESTORE REJECTED BY REST GATE", flush=True)
    return points


def body_weights(body, names):
    columns = {group.index: names.index(group.name) for group in body.vertex_groups
               if group.name in names}
    data = np.zeros((len(body.data.vertices), len(names)), dtype=np.float32)
    for vertex in body.data.vertices:
        for group in vertex.groups:
            if group.group in columns:
                data[vertex.index, columns[group.group]] = group.weight
    return data


def trim_weights(weights):
    order = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    result = np.zeros_like(weights)
    np.put_along_axis(result, order, np.take_along_axis(weights, order, axis=1), axis=1)
    result[result < .00005] = 0
    return result / result.sum(axis=1, keepdims=True)


def transfer_weights(points, body_points, body_faces, data, tree, neighbors, names):
    transferred = []
    for point in points.tolist():
        nearest, _, face, _ = tree.find_nearest(point)
        corners = body_faces[face]
        a, b, c = body_points[corners]
        uv = np.linalg.lstsq(np.column_stack((b - a, c - a)), np.asarray(nearest) - a, rcond=None)[0]
        bary = np.r_[1 - uv.sum(), uv].clip(0, 1)
        transferred.append(bary @ data[corners])
    weights = np.asarray(transferred, dtype=np.float32)

    # Inside the leg gap the opposite thigh may be the closest face.
    # Rebind only those vertices to the nearest face on their own side.
    for side, sign in (("Left", 1), ("Right", -1)):
        valid = np.flatnonzero(sign * (body_points[body_faces].mean(axis=1)[:, 0] - .00072) >= 0)
        side_tree = tree_for(body_points, body_faces[valid].tolist())
        other = "Right" if side == "Left" else "Left"
        col = [i for i, n in enumerate(names) if n.split(":")[-1].startswith(other)
               and any(word in n for word in ("Leg", "Foot", "Toe"))]
        bad, = np.where((points[:, 2] < .313) & (sign * (points[:, 0] - .00072) > 0)
                        & (weights[:, col].sum(axis=1) > .25))
        for index in bad:
            nearest, _, face, _ = side_tree.find_nearest(points[index])
            corners = body_faces[valid[face]]
            a, b, c = body_points[corners]
            uv = np.linalg.lstsq(np.column_stack((b - a, c - a)), np.asarray(nearest) - a, rcond=None)[0]
            weights[index] = np.r_[1 - uv.sum(), uv].clip(0, 1) @ data[corners]
    z = points[:, 2]
    blend = (.12 + .16 * np.maximum(np.exp(-((z - .34) / .043) ** 2),
                                    np.exp(-((z - .21) / .038) ** 2)))[:, None]
    for _ in range(3):
        weights = (1 - blend) * weights + blend * average(weights, neighbors)
    return trim_weights(weights)


def cache_motion(scene, arm, body, names, body_faces):
    bones = [arm.pose.bones[name] for name in names]
    inverse = [bone.bone.matrix_local.inverted() for bone in bones]
    modes = [bone.rotation_mode for bone in bones]
    samples, transforms = [], []
    face_list = body_faces.tolist()
    for clip, frame in sample_frames():
        set_pose(scene, arm, clip, frame)
        body_points = evaluated_coordinates(body)
        tree = tree_for(body_points, face_list)
        samples.append((clip, frame, tree, body_points))
        transforms.append(np.asarray([bone.matrix @ inv for bone, inv in zip(bones, inverse)])[:, :3, :])
    assert [bone.rotation_mode for bone in bones] == modes
    print("DENSE POSES", len(samples), flush=True)
    return samples, np.asarray(transforms, dtype=np.float32)


def skin_matrices(weights, transforms):
    packed = transforms.reshape(len(transforms), weights.shape[1], 12)
    return (weights @ packed).reshape(len(packed), len(weights), 3, 4)


def pose_points(points, skin):
    return np.einsum("fvij,vj->fvi", skin[..., :3], points) + skin[..., 3]


def barycentric(tris, points):
    a, b, c = tris.transpose(1, 0, 2)
    u, v, w = b - a, c - a, points - a
    uu, uv, vv, wu, wv = (np.einsum("ij,ij->i", x, y)
                          for x, y in ((u, u), (u, v), (v, v), (w, u), (w, v)))
    denominator = (uu * vv - uv * uv).clip(1e-18)
    s, t = (vv * wu - uv * wv) / denominator, (uu * wv - uv * wu) / denominator
    return np.column_stack((1 - s - t, s, t))


def contact_points(posed, faces, body_points, body_faces, pairs):
    """Sample the actual intersection endpoints and interiors of cut triangles."""
    body_ids, face_ids = pairs.T
    garment = posed[faces[face_ids]]
    body = body_points[body_faces[body_ids]]
    hits, factors = [], []
    for reverse in (False, True):
        edge_tri, plane_tri = (body, garment) if reverse else (garment, body)
        normal = np.cross(plane_tri[:, 1] - plane_tri[:, 0], plane_tri[:, 2] - plane_tri[:, 0])
        height = np.einsum("nki,ni->nk", edge_tri - plane_tri[:, :1], normal)
        for index in range(3):
            other = (index + 1) % 3
            h0, h1 = height[:, index], height[:, other]
            valid, = np.where((h0 * h1 <= 0) & (np.abs(h0 - h1) > 1e-15))
            alpha = h0[valid] / (h0[valid] - h1[valid])
            start, end = edge_tri[valid, index], edge_tri[valid, other]
            crossing = start + alpha[:, None] * (end - start)
            bary = barycentric(plane_tri[valid], crossing)
            good = bary.min(axis=1) >= -.0003
            hits.append(face_ids[valid[good]])
            factors.append(bary[good] if reverse else
                           SIMPLEX[index] + alpha[good, None] * (SIMPLEX[other] - SIMPLEX[index]))
    face_ids = np.unique(face_ids)
    grid = np.asarray([(i / 4, j / 4, (4 - i - j) / 4)
                       for i in range(5) for j in range(5 - i) if max(i, j, 4-i-j) < 4],
                      dtype=np.float32)
    hits.append(np.repeat(face_ids, len(grid)))
    factors.append(np.tile(grid, (len(face_ids), 1)))
    ids, bary = np.concatenate(hits), np.concatenate(factors).clip(0, 1)
    bary /= bary.sum(axis=1, keepdims=True)
    return ids, bary


def zone(point):
    x, _, z = point
    if z > .382:
        return "waistband"
    if z > .317:
        return "hips"
    if z > .280 and abs(x) < .040:
        return "crotch / inner thigh"
    side = "left" if x > .00072 else "right"
    if z < .105:
        return side + " cuff"
    if z < .175:
        return side + " lower leg"
    if z < .245:
        return side + " knee"
    return side + " thigh"


def scan(posed, faces, samples, body_faces, rest, collect, zone_details=None):
    distances, counts = [], []
    constraints = []
    cut_faces = np.zeros(len(faces), dtype=np.int32)
    failures = {}
    face_list = faces.tolist()
    face_zones = np.asarray([zone(pt) for pt in rest[faces].mean(axis=1)]) if zone_details is not None else None
    for row, (clip, frame, tree, body) in enumerate(samples):
        points = posed[row]
        signed, normals = signed_hits(tree, points)
        distances.append(signed)
        surface = tree_for(points, face_list)
        pairs = np.asarray(sorted(tree.overlap(surface)), dtype=np.int32).reshape(-1, 2)
        counts.append(len(pairs))
        if collect:
            bad, = np.where(signed < MARGIN)
            if len(bad):
                constraints.append((row, bad[:, None], np.ones((len(bad), 1), dtype=np.float32),
                                    signed[bad], normals[bad]))
        if len(pairs):
            crossing = pairs[:, 1]
            all_clear = np.min(signed[faces[crossing]], axis=1) >= MINIMUM
            np.add.at(cut_faces, crossing[all_clear], 1)
            ids, bary = contact_points(points, faces, body, body_faces, pairs)
            vertices = faces[ids]
            queries = np.einsum("nk,nki->ni", bary, points[vertices])
            margin, normal = signed_hits(tree, queries)
            worst = int(margin.argmin())
            if clip not in failures or margin[worst] < failures[clip]["signed_distance_m"]:
                failures[clip] = {"frame": frame, "zone": zone(bary[worst] @ rest[vertices[worst]]),
                                  "signed_distance_m": float(margin[worst])}
            if zone_details is not None:
                labels, counts_in_zone = np.unique(face_zones[pairs[:, 1]], return_counts=True)
                for label, count in zip(labels, counts_in_zone):
                    detail = zone_details[clip].setdefault(label, {})
                    if count > detail.get("max_triangle_pairs", 0):
                        detail["max_triangle_pairs"] = int(count)
                        detail["max_pairs_frame"] = frame
                    index = np.flatnonzero(face_zones[ids] == label)
                    index = index[int(margin[index].argmin())]
                    if margin[index] < detail.get("deepest_triangle_sample_m", math.inf):
                        detail["deepest_triangle_sample_m"] = float(margin[index])
                        detail["deepest_triangle_frame"] = frame
            if collect:
                order = np.lexsort((margin, ids))
                deepest = order[np.r_[True, np.diff(ids[order]) != 0]]
                constraints.append((row, vertices[deepest], bary[deepest],
                                    margin[deepest], normal[deepest]))
    return np.asarray(distances), np.asarray(counts), constraints, cut_faces, failures


def report_metrics(distance, pairs, samples, points, failures):
    output = {}
    for clip in ("rest", *CLIPS):
        rows = [i for i, s in enumerate(samples) if s[0] == clip]
        field = distance[rows]
        sample, vertex = np.unravel_index(field.argmin(), field.shape)
        output[clip] = {
            "samples": len(rows),
            "max_verts_inside": int((field < 0).sum(axis=1).max()),
            "min_signed_distance_m": float(field.min()),
            "minimum_frame": samples[rows[sample]][1],
            "minimum_zone": zone(points[vertex]),
            "minimum_vertex": int(vertex),
            "max_triangle_pairs": int(pairs[rows].max()),
            "max_pairs_frame": samples[rows[int(pairs[rows].argmax())]][1],
            "frames_with_overlap": int((pairs[rows] > 0).sum()),
        }
        if clip in failures:
            output[clip]["deepest_triangle_sample"] = failures[clip]
    return output


def offset_step(points, skin, constraints, tree, neighbors):
    """Project the worst clearance deficits into rest space, then smooth the offsets."""
    size = len(points)
    worst = np.zeros(size, dtype=np.float32)
    preference = np.zeros((size, 3), dtype=np.float32)
    linearized = []
    for row, ids, bary, signed, normals in constraints:
        gradient = np.einsum("ni,nkij->nkj", normals, skin[row, ids, :, :3])
        amount = np.maximum(MARGIN - signed, 0)
        bound_gradient = np.einsum("nk,nki->ni", bary, gradient)
        # Repeated observations add coherently. Squared deficits give the
        # largest penetration precedence over incidental low margins.
        for i in range(ids.shape[1]):
            contribution = amount * bary[:, i]
            np.maximum.at(worst, ids[:, i], contribution)
            np.add.at(preference, ids[:, i], (contribution ** 2)[:, None] * gradient[:, i])
        if ids.shape[1] > 1:
            gradient = .75 * gradient + .25 * bound_gradient[:, None, :]
        linearized.append((ids, bary, amount, gradient))
    _, rest_normals = signed_hits(tree, points)
    direction = unit(unit(preference) + .18 * rest_normals)
    required = np.zeros(size, dtype=np.float32)
    for ids, bary, amount, gradient in linearized:
        slope = np.einsum("nki,nki->nk", gradient, direction[ids])
        response = np.maximum((slope * bary).sum(axis=1), .38)
        for i in range(ids.shape[1]):
            active = (bary[:, i] > .12) & (slope[:, i] > .04)
            target = (amount[active] / response[active]).clip(0, .0105)
            target *= np.minimum(1, 2.5 * bary[active, i])
            np.maximum.at(required, ids[active, i], target)
    required = np.maximum(required, .55 * worst).clip(0, .0105)
    offset = required.copy()
    for _ in range(2):
        offset = np.maximum(required, .54 * offset + .46 * average(offset, neighbors))
    # Neighbors of the moving patches follow the nearest major direction.
    blended = average((required[:, None] * direction), neighbors)
    direction = unit(direction * required[:, None] + .37 * blended + 1e-7 * rest_normals)
    return rest_project(points + offset[:, None] * direction, tree)


def local_refine(points, weights, original, skin, transforms, samples, constraints,
                 distance, neighbors, previous_step, faces):
    """Resolve contacts with conflicting normals and correct local joint blends."""
    motion_rows = [np.asarray([i for i, s in enumerate(samples) if s[0] == name])
                   for name in CLIPS]
    worst = distance.min(axis=0).copy()
    by_vertex = defaultdict(list)
    for row, ids, bary, signed, _ in constraints:
        if ids.shape[1] == 1:
            continue
        for j, (vertices, factors, value) in enumerate(zip(ids, bary, signed)):
            if value >= MINIMUM:
                continue
            for k, vertex in enumerate(vertices):
                if factors[k] >= .18:
                    worst[vertex] = min(worst[vertex], value)
                    by_vertex[vertex].append((value, row, vertices, factors, k))
    active, = np.where(worst < MARGIN)
    active = active[np.argsort(worst[active], kind="stable")]
    grid = unit(np.asarray([v for v in product((-1, 0, 1), repeat=3) if any(v)],
                           dtype=np.float32))
    nearby = average(points - original, neighbors) + original
    weight_average = average(weights, neighbors)
    incident = defaultdict(list)
    for face, vertices in enumerate(faces):
        for corner, vertex in enumerate(vertices):
            incident[vertex].append((face, corner))
    current = points.copy()
    weights = weights.copy()
    change = 0
    for index in active[:260]:
        start = current[index].copy()
        rows = {0, *np.argsort(distance[:, index], kind="stable")[:10]}
        for group in motion_rows:
            rows.update(group[np.argsort(distance[group, index], kind="stable")[:2]])
        rows = np.asarray(sorted(rows), dtype=np.int32)
        witnesses = by_vertex[index]
        if witnesses:
            worst_contacts = sorted(witnesses, key=lambda item: (item[0], item[1]))
            seen, chosen = set(), []
            for value, row, ids, bary, k in worst_contacts:
                key = (samples[row][0], row // 4, *ids)
                if key not in seen:
                    seen.add(key)
                    chosen.append((row, ids, bary, k))
                if len(chosen) == 13:
                    break
            contact_rows = np.asarray([item[0] for item in chosen])
            ids = np.asarray([item[1] for item in chosen])
            bary = np.asarray([item[2] for item in chosen])
            k = np.asarray([item[3] for item in chosen])
            posed_tri = (np.einsum("ncij,ncj->nci", skin[contact_rows[:, None], ids, :, :3],
                                   current[ids]) + skin[contact_rows[:, None], ids, :, 3])
            contact_points_now = np.einsum("nk,nki->ni", bary, posed_tri)
            coefficient = bary[np.arange(len(k)), k]
            unchanged = contact_points_now - coefficient[:, None] * posed_tri[np.arange(len(k)), k]

        def losses(options, bindings):
            all_rows = np.r_[rows, contact_rows] if witnesses else rows
            used = np.flatnonzero(np.any(bindings > 0, axis=0))
            matrix = skin_matrices(bindings[:, used], transforms[all_rows][:, used])
            frame_points = np.einsum("fvij,vj->fvi", matrix[..., :3], options) + matrix[..., 3]
            if witnesses:
                frame_points[len(rows):] = (unchanged[:, None] +
                                             coefficient[:, None, None] * frame_points[len(rows):])
            field = np.asarray([signed_hits(samples[row][2], coordinates)[0]
                                for row, coordinates in zip(all_rows, frame_points)]) * 1000
            # Clearance and surface continuity are both measured in millimeters.
            deficit = np.maximum(MARGIN * 1000 - field, 0)
            score = 3 * np.square(deficit.max(axis=0)) + np.square(deficit).mean(axis=0)
            score += .047 * np.square((options - nearby[index]) * 1000).sum(axis=1)
            score += .010 * np.square((options - original[index]) * 1000).sum(axis=1)
            score += 9 * np.square(bindings - weights[index]).sum(axis=1)
            score[(field[0] > 29.96) | (field[0] < 1.3)] = np.inf
            score[(options[:, 2] > .421) | (options[:, 2] < .066)] = np.inf
            return score

        proposal = previous_step[index]
        layout = np.vstack((np.zeros((1, 3)), .002 * grid, .0045 * grid, .008 * grid[::2],
                            proposal * np.array([.4, .8, 1.2])[:, None], .6 * (nearby[index] - start)))
        options = start + layout
        initial = np.repeat(weights[index][None], len(options), axis=0)
        cost = losses(options, initial)
        positions, bindings, scores = options, initial, cost
        if worst[index] < .0008:
            blend = weights[index]
            neighbors_blend = weight_average[index]
            joint_ids = np.argsort(-(blend + .5 * neighbors_blend), kind="stable")[:4]
            joint_blends = np.eye(len(blend), dtype=np.float32)[joint_ids]
            variants = trim_weights(np.vstack((blend, .65 * blend + .35 * neighbors_blend,
                                               .84 * blend + .16 * joint_blends,
                                               .68 * blend + .32 * joint_blends)))
            anchors = options[np.argsort(cost, kind="stable")[:4]]
            candidates = np.repeat(anchors, len(variants), axis=0)
            candidate_weights = np.tile(variants, (len(anchors), 1))
            scores = np.r_[cost, losses(candidates, candidate_weights)]
            positions = np.vstack((options, candidates))
            bindings = np.vstack((initial, candidate_weights))
        face_ids, corners = np.asarray(incident[index]).T
        patch = current[faces[face_ids]]
        reference = original[faces[face_ids]]
        normal = unit(np.cross(reference[:, 1] - reference[:, 0],
                               reference[:, 2] - reference[:, 0]))
        patch_indices = np.arange(patch.size // 3).reshape(-1, 3).tolist()
        before = np.maximum(MARGIN - distance[:, index], 0)
        before_loss = np.square(before).sum()
        tested = 0
        for c in np.argsort(scores, kind="stable")[:12]:
            if not np.isfinite(scores[c]) or scores[c] >= cost[0] - 1e-5:
                break
            point = positions[c]
            patch[np.arange(len(patch)), corners] = point
            cross = np.cross(patch[:, 1] - patch[:, 0], patch[:, 2] - patch[:, 0])
            if np.any(np.einsum("ij,ij->i", unit(cross), normal) < -.08):
                continue
            if samples[0][2].overlap(tree_for(patch.reshape(-1, 3), patch_indices)):
                continue
            blend = skin_matrices(bindings[c:c+1], transforms)[:, 0]
            trajectory = blend[:, :, :3] @ point + blend[:, :, 3]
            delta = np.asarray([signed_hits(s[2], p[None])[0][0]
                                for s, p in zip(samples, trajectory)])
            after = np.maximum(MARGIN - delta, 0)
            tested += 1
            if (after.max() > before.max() + .0005 or
                    np.square(after).sum() > before_loss + 1e-6):
                if tested == 3:
                    break
                continue
            current[index], weights[index] = point, bindings[c]
            skin[:, index] = blend
            change += 1
            break
    print("LOCAL REFINEMENT", len(active), change, flush=True)
    return current, weights


def export(garment, arm, body, points, weights, names, save_blend=True):
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(1)
    garment.data.vertices.foreach_set("co", np.ascontiguousarray(points, dtype=np.float32).ravel())
    garment.data.update()
    garment.vertex_groups.clear()
    for name, values in zip(names, weights.T):
        group = garment.vertex_groups.new(name=name)
        for i in np.flatnonzero(values):
            group.add([int(i)], float(values[i]), "REPLACE")
    garment.name = garment.data.name = GLB.stem
    assert len(triangles(garment.data)) <= TRIANGLE_LIMIT
    assert ((weights > 0).sum(axis=1) <= 4).all()
    assert np.allclose(weights.sum(axis=1), 1, atol=1e-6)
    for obj in list(bpy.context.scene.objects):
        if obj not in (arm, body, garment):
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
        export_animations=False, export_yup=True, export_all_influences=False,
        export_def_bones=False, export_image_format="AUTO", export_tangents=True,
    )
    garment.parent = arm
    body.hide_render = True
    body.hide_set(True)
    if save_blend:
        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(GLB.with_suffix(".blend")))


def build():
    scene, arm, body = load_master()
    imported = imports(SOURCE, merge=True)
    garment, = [obj for obj in imported if obj.type == "MESH"]
    assert np.allclose(garment.matrix_world, np.eye(4), atol=1e-6)
    garment.parent = None
    garment.matrix_world = Matrix.Identity(4)
    trim_source(garment)
    install_texture(garment)
    garment.parent = arm
    garment.modifiers.new("Armature", "ARMATURE").object = arm
    names = tuple(bone.name for bone in arm.data.bones)
    body_faces = triangles(body.data)
    rest_body = evaluated_coordinates(body)
    rest_tree = tree_for(rest_body, body_faces.tolist())
    neighbors = mesh_neighbors(garment.data)
    points = rest_initialize(position_source(coordinates(garment.data)), rest_tree, neighbors)
    rim = waist_reference(garment.data, points)
    weights = transfer_weights(points, rest_body, body_faces, body_weights(body, names),
                               rest_tree, neighbors, names)
    points = tighten_waist(points, rest_tree)
    load_actions()
    samples, transforms = cache_motion(scene, arm, body, names, body_faces)
    faces = triangles(garment.data)
    skin = skin_matrices(weights, transforms)
    original = points.copy()
    best, best_points, best_weights = None, points.copy(), weights.copy()
    best_step = 0
    history = []
    for step in range(ITERATIONS + 1):
        distance, pairs, contacts, cut_faces, failures = scan(
            pose_points(points, skin), faces, samples, body_faces, points, collect=step < ITERATIONS
        )
        result = report_metrics(distance, pairs, samples, points, failures)
        history.append(result)
        print("ITERATION", step, [(clip, v["max_verts_inside"], v["max_triangle_pairs"],
                                   round(v["min_signed_distance_m"] * 1000, 3))
                                  for clip, v in result.items()], flush=True)
        print("CONTACT LOCATIONS", [(clip, row["minimum_frame"], row["minimum_zone"],
                                     row.get("deepest_triangle_sample"))
                                    for clip, row in result.items()
                                    if row["min_signed_distance_m"] < MINIMUM or row["max_triangle_pairs"]],
              flush=True)
        if step == 0 and cut_faces.any():
            points, weights = subdivide_contacts(garment, faces, points, weights, cut_faces)
            faces, neighbors = triangles(garment.data), mesh_neighbors(garment.data)
            points = rest_project(points, rest_tree, lo=.0055)
            skin = skin_matrices(weights, transforms)
            original = points.copy()
            continue
        failures_count = int((distance < MINIMUM).sum())
        max_rest = float(distance[0].max())
        score = (int(bool(pairs[0] or max_rest > REST_LIMIT + .00001)),
                 int(pairs.sum() + 3 * (distance < 0).sum()),
                 failures_count, -float(distance.min()))
        if best is None or score < best:
            best, best_points, best_weights = score, points.copy(), weights.copy()
            best_step = step
        if not any(score[:3]) and float(distance.min()) >= MARGIN:
            break
        if step - best_step >= 3:
            print("STOPPED AFTER THREE NON-IMPROVING SWEEPS", flush=True)
            break
        if step < ITERATIONS:
            offset = offset_step(points, skin, contacts, rest_tree, neighbors)
            points, weights = local_refine(points, weights, original, skin, transforms,
                                           samples, contacts, distance, neighbors, offset - points,
                                           faces)
    (GLB.parent / "fit_history.json").write_text(
        json.dumps({"selected_iteration": best_step, "iterations": history}, indent=2) + "\n"
    )
    best_points = restore_waist_rim(garment, best_points, rim, rest_tree)
    export(garment, arm, body, best_points, best_weights, names)


def restore_rim():
    """Replay the finish on the current saved fit without rebaking skin weights."""
    scene, arm, body = load_master()
    source, = [obj for obj in imports(SOURCE, merge=True) if obj.type == "MESH"]
    source.parent = None
    trim_source(source)
    rest_tree = tree_for(evaluated_coordinates(body), triangles(body.data).tolist())
    points = rest_initialize(position_source(coordinates(source.data)), rest_tree,
                             mesh_neighbors(source.data))
    rim = waist_reference(source.data, points)
    bpy.ops.wm.open_mainfile(filepath=str(GLB.with_suffix(".blend")), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, garment = (scene.objects[name] for name in ("Armature", "Base_Body", GLB.stem))
    names = tuple(arm.data.bones.keys())
    points = restore_waist_rim(garment, coordinates(garment.data), rim, rest_tree)
    export(garment, arm, body, points, body_weights(garment, names), names)


def reimport():
    scene, arm, body = load_master()
    imported = imports(GLB)
    garment, = [obj for obj in bpy.context.selected_objects if obj in imported and obj.type == "MESH"]
    garment.parent = None
    for obj in imported:
        if obj != garment:
            bpy.data.objects.remove(obj, do_unlink=True)
    garment.modifiers.clear()
    garment.parent = arm
    garment.modifiers.new("Master armature", "ARMATURE").object = arm
    load_actions()
    return scene, arm, body, garment


def statistics(values):
    return {name: float(value) for name, value in zip(
        ("min", "p10", "median", "p90", "p95", "max"), np.percentile(values, [0, 10, 50, 90, 95, 100])
    )}


def inspect_export(arm):
    data = GLB.read_bytes()
    magic, version, length, json_length, tag = struct.unpack_from("<4sIII4s", data)
    assert (magic, version, length, tag) == (b"glTF", 2, len(data), b"JSON")
    content = json.loads(data[20:20 + json_length])
    assert len(content["meshes"]) == len(content["skins"]) == 1
    assert len([node for node in content["nodes"] if "mesh" in node]) == 1
    skin = content["skins"][0]
    joints = [content["nodes"][idx]["name"] for idx in skin["joints"]]
    assert len(joints) == 65 and set(joints) == set(arm.data.bones.keys())
    assert not content.get("animations")
    for primitive in content["meshes"][0]["primitives"]:
        attributes = primitive["attributes"]
        assert {"JOINTS_0", "WEIGHTS_0", "TEXCOORD_0", "TANGENT"} <= attributes.keys()
        assert "JOINTS_1" not in attributes and "WEIGHTS_1" not in attributes
    textures = {}
    for image in content["images"]:
        view = content["bufferViews"][image["bufferView"]]
        start = 28 + json_length + view.get("byteOffset", 0)
        assert data[start:start+8] == b"\x89PNG\r\n\x1a\n"
        textures[image["name"]] = struct.unpack_from(">II", data, start + 16)
    assert len(textures) == 3 and all(max(size) <= 1024 for size in textures.values())
    return textures


def verify():
    scene, arm, body, garment = reimport()
    textures = inspect_export(arm)
    body_faces = triangles(body.data)
    faces = triangles(garment.data)
    posed, samples = [], []
    points = evaluated_coordinates(garment)
    face_list = body_faces.tolist()
    for clip, frame in sample_frames():
        set_pose(scene, arm, clip, frame)
        coords = evaluated_coordinates(body)
        samples.append((clip, frame, tree_for(coords, face_list), coords))
        posed.append(evaluated_coordinates(garment))
    details = defaultdict(dict)
    distance, pairs, _, _, failures = scan(posed, faces, samples, body_faces, points, collect=False,
                                           zone_details=details)
    result = report_metrics(distance, pairs, samples, points, failures)
    regions = np.asarray([zone(point) for point in points])
    stats = {"all": statistics(distance[0])}
    stats.update({name: statistics(distance[0, regions == name]) for name in sorted(set(regions))})
    names = tuple(arm.data.bones.keys())
    face_weights = body_weights(body, names)[body_faces].mean(axis=1)
    face_bones = face_weights.argmax(axis=1)
    for clip, summary in result.items():
        rows = np.asarray([i for i, sample in enumerate(samples) if sample[0] == clip])
        for region in sorted(set(regions)):
            columns = np.flatnonzero(regions == region)
            field = distance[np.ix_(rows, columns)]
            if field.min() >= MINIMUM:
                continue
            row, col = np.unravel_index(field.argmin(), field.shape)
            index, vertex = rows[row], columns[col]
            _, _, tree, _ = samples[index]
            _, _, body_face, _ = tree.find_nearest(posed[index][vertex])
            details[clip].setdefault(region, {}).update({
                "max_verts_inside": int((field < 0).sum(axis=1).max()),
                "min_signed_distance_m": float(field[row, col]),
                "minimum_frame": samples[index][1],
                "body_zone": names[face_bones[body_face]],
            })
            if region == summary["minimum_zone"]:
                summary["minimum_body_zone"] = names[face_bones[body_face]]
    centers = samples[0][3][body_faces].mean(axis=1)
    arms = [i for i, name in enumerate(names) if "Arm" in name or "Hand" in name]
    arm_faces = face_weights[:, arms].sum(axis=1) > .55
    pelvis = (centers[:, 2] > .26) & (centers[:, 2] < .445) & ~arm_faces
    self_contacts = {}
    for clip, summary in result.items():
        frame = summary["minimum_frame"]
        coords = next(sample[3] for sample in samples if sample[:2] == (clip, frame))
        a = tree_for(coords, body_faces[arm_faces].tolist())
        b = tree_for(coords, body_faces[pelvis].tolist())
        self_contacts[clip] = {"frame": frame, "arm_pelvis_pairs": len(a.overlap(b))}
    counts = [sum(group.weight > 0 for group in v.groups) for v in garment.data.vertices]
    data = {
        "sha256": hashlib.sha256(GLB.read_bytes()).hexdigest(), "bytes": GLB.stat().st_size,
        "triangles": len(faces), "exported_vertices": len(points), "joints": len(arm.data.bones),
        "max_influences": max(counts), "unweighted_vertices": counts.count(0), "textures": textures,
        "rest_bounds": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
        "rest_clearance_m": stats, "clips": result, "remaining_by_clip_and_zone": details,
        "base_body_self_contacts_at_minimum_frames": self_contacts,
    }
    (HERE / "dense_check.json").write_text(json.dumps(data, indent=2) + "\n")
    for clip, row in result.items():
        print("DENSE RESULT", clip, row, flush=True)


def checkers():
    """Execute the supplied collision logic unchanged with a separate render pass."""
    for stem in ("motion_check", "motion_check_tri"):
        path = HERE / "work" / (stem + ".py")
        source = path.read_text()
        head, render_section = source.split("sc.render.engine=", 1)
        assert "bpy.ops.render.render" in render_section
        source = head + f'json.dump(res,open(f"{{out}}/{stem}.json","w"))\n'
        output = io.StringIO()
        old_argv = sys.argv
        try:
            sys.argv = [str(path), "--", str(MASTER), str(MOTION), str(GLB), str(HERE)]
            with redirect_stdout(output):
                exec(compile(source, str(path), "exec"), {})
        finally:
            sys.argv = old_argv
        lines = [line for line in output.getvalue().splitlines() if line.startswith("RESULT ")]
        assert len(lines) == 8
        log = "\n".join(lines) + "\n"
        (HERE / (stem + ".txt")).write_text(log)
        print(log, end="", flush=True)


def renders():
    scene, arm, body, garment = reimport()
    output = HERE / "renders"
    output.mkdir(exist_ok=True)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = scene.render.resolution_y = 680
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_compositing = scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("QA Studio")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (.68, .73, .82, 1)
    bg.inputs[1].default_value = .48
    focus = Vector((0, 0, .24))
    for name, xyz, energy, size in (
        ("Key", (-1, -1.5, 2.6), 115, 2.1),
        ("Fill", (1.3, -.5, 1.25), 48, 1.65),
        ("Rim", (.4, 1.45, 2), 110, 1.55),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = xyz
        lamp.rotation_euler = (focus - lamp.location).to_track_quat("-Z", "Y").to_euler()
    camera = bpy.data.cameras.new("Fit QA Camera")
    camera.type = "ORTHO"
    obj = bpy.data.objects.new(camera.name, camera)
    scene.collection.objects.link(obj)
    scene.camera = obj

    def capture(name, target, direction, scale, show_body=True):
        body.hide_render = not show_body
        camera.ortho_scale = scale
        obj.location = target + Vector(direction).normalized() * 3
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    set_pose(scene, arm, "rest", 1)
    for name, direction, visible in (
        ("rest_front", (0, -1, .035), True),
        ("rest_back", (0, 1, .035), True),
        ("rest_left", (1, 0, .035), True),
        ("rest_right", (-1, 0, .035), True),
        ("rest_waist", (.55, -1, .68), False),
        ("rest_cuffs", (-.4, -1, -.61), False),
    ):
        capture(name, focus, direction, .52, visible)

    for clip, direction in (
        ("walk", (.45, -1, .12)), ("run", (.8, -1, .05)),
        ("wave", (-.28, -1, .14)), ("jump", (-.65, -1, .05)),
    ):
        first, last = bpy.data.actions[clip].frame_range
        frame = int(first + (last - first) * .4)
        set_pose(scene, arm, clip, frame)
        points = evaluated_coordinates(garment)
        target = Vector((points.min(axis=0) + points.max(axis=0)) / 2)
        capture(clip, target, direction, .62)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stages = {"build": build, "verify": verify, "checkers": checkers, "renders": renders,
              "restore-rim": restore_rim}
    for stage in args or ("build",):
        stages[stage]()
