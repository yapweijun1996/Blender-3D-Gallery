"""Build the modular T-shirt with Blender 5.1.2 in background mode.

Usage: Blender -b --python make_tshirt_v3.py -- [--check] [--cpu-render]
Geometry, skinning and collision queries run in Blender. NumPy is bundled
with Blender and is used for the dense skinning and Laplacian calculations.
"""

import argparse
from collections import defaultdict
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from itertools import product
import hashlib
import json
import math
from pathlib import Path
from runpy import run_path
import sys
from types import SimpleNamespace

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


ROOT = Path(__file__).resolve().parent
MASTER = ROOT.parents[1] / "master" / "GJH_Chibi_Master_rigged.blend"
MOTION = ROOT.parents[3] / "models" / "tripo-chibi-motion" / "motion.glb"
NAME = "top_tshirt_v3"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
GRID = .009
STANDOFF = .0046
MOTION_GAP = .0008
MAX_OFFSET = .020
HEM_Z = .417
SLEEVE_LENGTH = .40
MAX_ITERATIONS = 8
COLOR = (.075, .40, .37, 1.)
PREFIX = "mixamorig:"


def log(message):
    print(message, flush=True)


def signed_hit(tree, point):
    near, normal, index, _ = tree.find_nearest(point)
    return (Vector(point) - near).dot(normal), near, normal, index


def mesh_vertices(mesh):
    vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", vertices)
    return vertices.reshape(-1, 3)


def capture_body(body):
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        positions = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        faces = [tuple(face.vertices) for face in mesh.polygons]
        return positions, faces, BVHTree.FromPolygons(positions, faces, all_triangles=True)
    finally:
        evaluated.to_mesh_clear()


def cuff_planes(rig):
    def head(joint):
        return rig.matrix_world @ rig.data.bones[PREFIX + joint].head_local

    planes = []
    for side in ("Left", "Right"):
        shoulder, elbow = head(side + "Arm"), head(side + "ForeArm")
        axis = (elbow - shoulder).normalized()
        cuff = shoulder.lerp(elbow, SLEEVE_LENGTH)
        planes.append((axis, axis.dot(cuff)))
    return planes


def neckline(point):
    # Two joined half ellipses have the same tangent at the sides. The cut
    # follows the shoulder surface and sits lower in front than in back.
    x, y, z = point
    y += .016
    radius_y = .063 if y < 0 else .060
    radial = math.hypot((x - .0007) / .055, y / radius_y)
    return radial - min(1., max(0., (z - .535) / .024))


def body_offset_grid(tree):
    """Extract the offset isosurface with surface nets on a regular grid."""
    origin = np.array((-.141, -.136, .398))
    size = (33, 30, 26)
    field = np.empty(size)
    for index in np.ndindex(size):
        point = origin + GRID * np.array(index)
        field[index] = signed_hit(tree, point)[0] - STANDOFF

    corners = np.array(list(product((0, 1), repeat=3)))
    cube_edges = [(i, j) for i, j in product(range(8), repeat=2)
                  if i < j and np.abs(corners[i] - corners[j]).sum() == 1]
    cells = np.full(tuple(np.array(size) - 1), -1, dtype=int)
    points, faces = [], []
    for index in np.ndindex(cells.shape):
        levels = field[tuple((np.array(index) + corners).T)]
        if np.all(levels >= 0.) or np.all(levels < 0.):
            continue
        crossings = []
        for i, j in cube_edges:
            if (levels[i] < 0.) == (levels[j] < 0.):
                continue
            fraction = levels[i] / (levels[i] - levels[j])
            crossings.append(corners[i] + fraction * (corners[j] - corners[i]))
        cells[index] = len(points)
        points.append(origin + GRID * (np.array(index) + np.mean(crossings, axis=0)))

    # Each lattice edge with a sign change joins four neighboring cells.
    for axis in range(3):
        other = ((axis + 1) % 3, (axis + 2) % 3)
        bounds = [range(1, length - 1) for length in size]
        bounds[axis] = range(size[axis] - 1)
        for index in product(*bounds):
            end = list(index)
            end[axis] += 1
            if (field[index] < 0.) == (field[tuple(end)] < 0.):
                continue
            face = []
            for a, b in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
                cell = list(index)
                cell[other[0]] += a
                cell[other[1]] += b
                face.append(int(cells[tuple(cell)]))
            if field[index] >= 0.:
                face.reverse()
            faces.append(face)
    return points, faces


def crop_shell(points, faces, cuts):
    """Clip the open surface while sharing new edge vertices across faces."""
    boundary = {}
    for name, value in cuts:
        crossings = {}
        clipped = []
        levels = [value(point) for point in points]
        for face in faces:
            polygon = []
            for a, b in zip(face, face[1:] + face[:1]):
                inside_a, inside_b = levels[a] >= 0., levels[b] >= 0.
                if inside_a:
                    polygon.append(a)
                if inside_a == inside_b:
                    continue
                key = (min(a, b), max(a, b))
                if key not in crossings:
                    low, high = (a, b) if inside_a else (b, a)
                    start, end = points[low], points[high]
                    s, t = 0., 1.
                    for _ in range(17):
                        mid = (s + t) / 2.
                        if value(start + mid * (end - start)) >= 0.:
                            s = mid
                        else:
                            t = mid
                    crossings[key] = len(points)
                    boundary[len(points)] = name
                    points.append(start + (s + t) / 2. * (end - start))
                polygon.append(crossings[key])
            if len(polygon) >= 3:
                clipped.append(polygon)
        faces = clipped
    used = sorted({i for face in faces for i in face})
    remap = {old: new for new, old in enumerate(used)}
    return ([points[i] for i in used], [tuple(remap[i] for i in face) for face in faces],
            {remap[i]: name for i, name in boundary.items() if i in remap})


def round_neckline(bm, opening, body):
    """Fair the neck rim in height while retaining its elliptical plan."""
    rim = [v for v in bm.verts if v.is_boundary and v[opening] == 4]
    points = np.array([tuple(v.co) for v in rim])
    radius_y = np.where(points[:, 1] < -.016, .063, .060)
    angles = np.arctan2((points[:, 1] + .016) / radius_y, (points[:, 0] - .0007) / .055)
    harmonics = np.column_stack([np.ones(len(rim))] + [
        wave(order * angles) for order in range(1, 4) for wave in (np.sin, np.cos)])
    heights = harmonics @ np.linalg.lstsq(harmonics, points[:, 2], rcond=None)[0]
    shift = {}
    for vertex, height in zip(rim, heights):
        position = vertex.co.copy()
        position.z = height
        for _ in range(3):
            gap, _, normal, _ = signed_hit(body, position)
            if gap >= .0036 or normal.z < .20:
                break
            position.z += (.0036 - gap) / normal.z
        if signed_hit(body, position)[0] >= .003:
            shift[vertex] = position.z - vertex.co.z

    # Carry part of the rim motion into the supporting shoulder rings.
    field = shift.copy()
    for _ in range(3):
        field = {v: shift[v] if v in shift else
                 .62 * sum(field.get(e.other_vert(v), 0.) for e in v.link_edges) / len(v.link_edges)
                 if not v.is_boundary else 0. for v in bm.verts}
    for vertex, dz in field.items():
        position = vertex.co.copy()
        position.z += dz
        if signed_hit(body, position)[0] >= .003:
            vertex.co = position


def make_shell(tree, rig):
    planes = cuff_planes(rig)
    cuts = [
        ("hem", lambda p: p[2] - HEM_Z),
        ("left cuff", lambda p: max(.500 - p[2], planes[0][1] - planes[0][0].dot(p))),
        ("right cuff", lambda p: max(.500 - p[2], planes[1][1] - planes[1][0].dot(p))),
        ("neck", neckline),
        ("top bound", lambda p: .613 - p[2]),
    ]
    points, faces, boundary = crop_shell(*body_offset_grid(tree), cuts)
    mesh = bpy.data.meshes.new(NAME)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        boundary_layer = bm.verts.layers.int.new("opening")
        names = [name for name, _ in cuts]
        for v in bm.verts:
            if v.index in boundary:
                v[boundary_layer] = names.index(boundary[v.index]) + 1
        # The local grid can include a disconnected sliver of the chin.
        # Keep the surface connected to the waist, away from that sliver.
        connected = {min(bm.verts, key=lambda v: v.co.z)}
        pending = list(connected)
        while pending:
            vertex = pending.pop()
            for edge in vertex.link_edges:
                neighbor = edge.other_vert(vertex)
                if neighbor not in connected:
                    connected.add(neighbor)
                    pending.append(neighbor)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in connected], context="VERTS")
        if any(v[boundary_layer] > 4 for v in bm.verts):
            raise RuntimeError("The neckline cutter left an exposed upper boundary.")

        # Remove very short edges left where a cutter grazes a grid vertex.
        for _ in range(3):
            for edge in list(bm.edges):
                if not edge.is_valid or edge.calc_length() >= GRID * .32:
                    continue
                a, b = edge.verts
                region_a, region_b = a[boundary_layer], b[boundary_layer]
                if region_a == region_b:
                    a.co = (a.co + b.co) * .5
                elif region_b:
                    a, b = b, a
                bmesh.ops.weld_verts(bm, targetmap={b: a})
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        front = [face for face in bm.faces if face.calc_center_median().y < -.081]
        if sum(face.normal.y for face in front) > 0.:
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))

        def opening_gradient(region, point):
            if region == 1:
                return Vector((0., 0., 1.))
            if region in (2, 3):
                return planes[region - 2][0]
            x, y, _ = point
            ry = .063 if y < -.016 else .060
            return Vector(((x - .0007) / .055**2, (y + .016) / ry**2, 0.)).normalized()

        # Relax the sampling grid and reproject to the offset surface. At
        # openings intersect the two tangent planes, preserving the cut.
        for step in range(12):
            updated = []
            for vertex in bm.verts:
                region = vertex[boundary_layer] if vertex.is_boundary else 0
                adjacent = [edge.other_vert(vertex) for edge in vertex.link_edges
                            if not region or edge.is_boundary]
                position = vertex.co.lerp(sum((v.co for v in adjacent), Vector()) / len(adjacent), .45)
                for _ in range(4):
                    if region == 1:
                        position.z = HEM_Z
                    if region in (2, 3):
                        axis, level = planes[region - 2]
                        position += (level - axis.dot(position)) * axis
                    if region == 4:
                        x, y, z = position
                        r = neckline(position) + 1.
                        position = Vector((.0007 + (x - .0007) / r, -.016 + (y + .016) / r, z))
                    gap, _, normal, _ = signed_hit(tree, position)
                    direction = normal.copy()
                    if region:
                        constraint = opening_gradient(region, position)
                        direction -= direction.dot(constraint) * constraint
                    slope = direction.dot(normal)
                    if slope > .04:
                        position += direction * max(-.004, min(.004, (STANDOFF - gap) / slope))
                if region == 1:
                    position.z = HEM_Z
                    # Above the shorts, the nearest normal may point almost
                    # vertically from the recessed waistband seam. Make
                    # room in the plane of the hem in that case.
                    radial = Vector((position.x, position.y + .017, 0.)).normalized()
                    for _ in range(9):
                        if signed_hit(tree, position)[0] >= .0037:
                            break
                        position += .001 * radial
                updated.append(position)
            for vertex, position in zip(bm.verts, updated):
                vertex.co = position

        round_neckline(bm, boundary_layer, tree)
        for face in bm.faces:
            face.smooth = True
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.validate()
    mesh.update()
    shirt = bpy.data.objects.new(NAME, mesh)
    bpy.context.collection.objects.link(shirt)
    return shirt


def adjacency(mesh):
    edges = np.array([tuple(edge.vertices) for edge in mesh.edges])
    start, end = np.concatenate((edges, edges[:, ::-1])).T
    counts = np.bincount(start, minlength=len(mesh.vertices))
    return start, end, counts


def smooth(field, links):
    start, end, counts = links
    if field.ndim == 1:
        return np.bincount(start, weights=field[end], minlength=len(field)) / counts
    return np.stack([smooth(axis, links) for axis in field.T], axis=-1)


def bind_weights(body, shirt, rig, surface):
    body_points, body_faces, tree = surface
    names = [bone.name for bone in rig.data.bones]
    group_bones = [names.index(group.name) for group in body.vertex_groups]
    source_weights = np.zeros((len(body_points), len(names)))
    for vertex in body.data.vertices:
        for group in vertex.groups:
            source_weights[vertex.index, group_bones[group.group]] = group.weight

    weights = []
    bary_axes = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    for vertex in shirt.data.vertices:
        _, location, _, poly = signed_hit(tree, vertex.co)
        face = list(body_faces[poly])
        bary = barycentric_transform(location, *(body_points[i] for i in face), *bary_axes)
        weights.append(np.asarray(bary) @ source_weights[face])
    weights = np.maximum(0., weights)
    # Diffuse sharp transitions between supporting triangles.
    links = adjacency(shirt.data)
    weights = .85 * weights + .15 * smooth(weights, links)
    for _ in range(2):
        weights = .48 * weights + .52 * smooth(weights, links)
    for index, name in enumerate(names):
        shirt.vertex_groups.new(name=name)
    write_weights(shirt, weights)


def write_weights(shirt, weights):
    chosen = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    sparse = np.take_along_axis(weights, chosen, axis=1)
    sparse[sparse < 1.e-6] = 0.
    sparse /= sparse.sum(axis=1, keepdims=True)
    for vertex, groups, values in zip(shirt.data.vertices, chosen, sparse):
        for group in [membership.group for membership in vertex.groups]:
            shirt.vertex_groups[group].remove([vertex.index])
        for group, value in zip(groups, values):
            if value:
                shirt.vertex_groups[int(group)].add([vertex.index], float(value), "REPLACE")


@dataclass
class Pose:
    name: str
    frame: int
    surface: BVHTree
    bones: np.ndarray


def capture_poses(body, rig, path):
    scene = bpy.context.scene
    collections = (bpy.data.objects, bpy.data.actions, bpy.data.meshes,
                   bpy.data.armatures, bpy.data.materials, bpy.data.images,
                   bpy.data.collections, bpy.data.node_groups)
    originals = [set(collection) for collection in collections]
    bpy.ops.import_scene.gltf(filepath=str(path))
    for obj in set(bpy.data.objects) - originals[0]:
        obj.hide_viewport = True
        obj.hide_render = True
    new_actions = {action.name: action for action in set(bpy.data.actions) - originals[1]}
    rig.animation_data_create()
    inverses = [bone.matrix_local.inverted() for bone in rig.data.bones]
    bones = [rig.pose.bones[bone.name] for bone in rig.data.bones]

    def record(name, frame):
        _, _, tree = capture_body(body)
        matrices = np.array([rig.matrix_world @ bone.matrix @ inverse
                             for bone, inverse in zip(bones, inverses)], dtype=np.float32)
        return Pose(name, frame, tree, matrices[:, :3, :])

    scene.frame_set(1)
    poses = [record("rest", 1)]
    for name in CLIPS:
        action = new_actions[name]
        if not action.slots:
            raise RuntimeError(f"Missing quaternion action slot for {name}.")
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        first, last = map(int, action.frame_range)
        for frame in range(first, last + 1):
            scene.frame_set(frame)
            poses.append(record(name, frame))
        log(f"Cached {name}, frames {first}–{last}")
    rig.animation_data_clear()
    for bone in bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    bpy.data.batch_remove(ids={item for collection, original in zip(collections, originals)
                              for item in collection if item not in original})
    bpy.context.view_layer.update()
    return poses


def skinning(shirt, poses):
    indices = np.zeros((len(shirt.data.vertices), 4), dtype=int)
    values = np.zeros(indices.shape, dtype=np.float32)
    for vertex in shirt.data.vertices:
        for slot, group in enumerate(vertex.groups):
            indices[vertex.index, slot] = group.group
            values[vertex.index, slot] = group.weight
    values /= values.sum(axis=1, keepdims=True)
    return [np.einsum("vkij,vk->vij", pose.bones[indices], values) for pose in poses]


def triangles(shirt):
    shirt.data.calc_loop_triangles()
    return np.array([tuple(triangle.vertices) for triangle in shirt.data.loop_triangles])


def offset_directions(shirt, tree):
    normals = np.array([tuple(vertex.normal) for vertex in shirt.data.vertices])
    nearby = np.array([tuple(signed_hit(tree, vertex.co)[2]) for vertex in shirt.data.vertices])
    directions = smooth(.65 * normals + .35 * nearby, adjacency(shirt.data))
    openings = shirt.data.attributes["opening"]
    return constrain_directions(shirt, directions, openings)


def constrain_directions(shirt, directions, openings):
    planes = cuff_planes(bpy.data.objects["Armature"])
    for vertex in shirt.data.vertices:
        region = openings.data[vertex.index].value
        if region == 1:
            directions[vertex.index, 2] = 0.
        if region in (2, 3):
            axis = np.array(planes[region - 2][0])
            directions[vertex.index] -= np.dot(directions[vertex.index], axis) * axis
    directions /= np.maximum(1e-8, np.linalg.norm(directions, axis=1, keepdims=True))
    return directions


def section(point):
    x, y, z = point
    if z < .438:
        return "hem"
    if abs(x) > .098:
        return "left sleeve" if x > 0. else "right sleeve"
    if abs(x) > .063 and z > .493:
        return "left armhole" if x > 0. else "right armhole"
    if z > .566 and abs(x) < .061:
        return "neckline"
    return "front torso" if y < -.016 else "back torso"


def set_positions(shirt, positions):
    shirt.data.vertices.foreach_set("co", np.asarray(positions, dtype=np.float32).ravel())
    shirt.data.update()


def inspect_poses(poses, matrices, positions, directions, faces):
    """Find worst rest-space correction and exact BVH overlaps at every frame."""
    required = np.zeros(len(positions))
    offset_budget = np.full(len(positions), MAX_OFFSET)
    results = {}
    contact_edges = defaultdict(int)
    world_directions = [np.einsum("vij,vj->vi", matrix[:, :, :3], directions)
                        for matrix in matrices]
    sample_weights = np.array(((.5, .5, 0.), (.5, 0., .5), (0., .5, .5),
                               (1/3, 1/3, 1/3), (.75, .25, 0.), (.25, .75, 0.),
                               (.75, 0., .25), (.25, 0., .75),
                               (0., .75, .25), (0., .25, .75)))
    faces_tuple = [tuple(face) for face in faces]
    for pose, matrix, slopes in zip(poses, matrices, world_directions):
        posed = np.einsum("vij,vj->vi", matrix[:, :, :3], positions) + matrix[:, :, 3]
        hit = [signed_hit(pose.surface, point) for point in posed]
        gaps = np.array([item[0] for item in hit])
        threshold = .00325 if pose.name == "rest" else MOTION_GAP
        normals = np.array([tuple(item[2]) for item in hit])
        gradients = np.einsum("ij,ij->i", slopes, normals)
        opposing = gradients < -.12
        offset_budget[opposing] = np.minimum(
            offset_budget[opposing], np.maximum(0., gaps[opposing] - threshold) /
            -gradients[opposing])
        for i in np.flatnonzero(gaps < threshold):
            slope = gradients[i]
            if slope > .12:
                required[i] = max(required[i], (threshold - gaps[i]) / slope)

        tree = BVHTree.FromPolygons(posed.tolist(), faces_tuple, all_triangles=True)
        pairs = pose.surface.overlap(tree)
        intersecting = sorted({garment for _, garment in pairs})
        face_depth = 0.
        face_location = None
        for face_index in intersecting:
            face = faces[face_index]
            face_required = 0.
            for weights, point in zip(sample_weights, sample_weights @ posed[face]):
                gap, _, normal, _ = signed_hit(pose.surface, point)
                if gap < face_depth:
                    face_depth = gap
                    face_location = section(weights @ positions[face])
                slope = np.dot(weights @ slopes[face], normal)
                if slope > .12:
                    face_required = max(face_required, (threshold - gap) / slope)
            if np.all(gaps[face] >= 0.):
                for a, b in zip(face, np.roll(face, 1)):
                    if np.linalg.norm(posed[a] - posed[b]) > .012:
                        contact_edges[(min(a, b), max(a, b))] += 1
            # Even shallow cuts between samples need a positive correction.
            required[face] = np.maximum(required[face], max(.00045, face_required))

        record = results.setdefault(pose.name, {
            "max_inside": 0, "min_distance": 1., "max_pairs": 0,
            "deepest_face_sample": 0.,
        })
        record["max_inside"] = max(record["max_inside"], int(np.count_nonzero(gaps < 0.)))
        if (minimum := float(gaps.min())) < record["min_distance"]:
            index = int(gaps.argmin())
            record.update(min_distance=minimum, vertex_frame=pose.frame,
                          vertex_zone=section(positions[index]),
                          vertex_index=index, vertex_rest_position=positions[index].tolist())
        if len(pairs) > record["max_pairs"]:
            record.update(max_pairs=len(pairs), pair_frame=pose.frame,
                          pair_zones=sorted({section(positions[faces[i]].mean(axis=0))
                                             for i in intersecting}))
        if face_depth < record["deepest_face_sample"]:
            record.update(deepest_face_sample=face_depth, face_depth_frame=pose.frame,
                          face_depth_zone=face_location)
    return required, results, offset_budget, contact_edges


def subdivide_contacts(shirt, base, offsets, directions, contact_edges, rest):
    """Split supported grid edges of triangles whose corners clear the body."""
    mesh = shirt.data
    points = list(mesh_vertices(mesh))
    polygons = [tuple(poly.vertices) for poly in mesh.polygons]
    edge_use = defaultdict(int)
    for face in polygons:
        for a, b in zip(face, face[1:] + face[:1]):
            edge_use[(min(a, b), max(a, b))] += 1
    candidates = [(key, votes) for key, votes in contact_edges.items() if edge_use[key] == 2]
    candidates.sort(key=lambda item: (-item[1], item[0]))
    selected = [key for key, _ in candidates[:48]]
    if not selected:
        return None

    openings = [entry.value for entry in mesh.attributes["opening"].data]
    group_names = [group.name for group in shirt.vertex_groups]
    weights = np.zeros((len(points), len(group_names)))
    for vertex in mesh.vertices:
        for group in vertex.groups:
            weights[vertex.index, group.group] = group.weight

    split_indexes = {}
    for a, b in selected:
        point = (points[a] + points[b]) * .5
        gap, _, normal, _ = signed_hit(rest, point)
        point += max(.00015, .0037 - gap) * np.asarray(normal)
        split_indexes[(a, b)] = len(points)
        points.append(point)
    new_faces = []
    for face in polygons:
        updated = []
        for a, b in zip(face, face[1:] + face[:1]):
            updated.append(a)
            split = split_indexes.get((min(a, b), max(a, b)))
            if split is not None:
                updated.append(split)
        new_faces.append(updated)

    new_mesh = bpy.data.meshes.new(NAME)
    new_mesh.from_pydata(points, [], new_faces)
    new_mesh.update()
    opening = new_mesh.attributes.new("opening", "INT", "POINT")
    opening.data.foreach_set("value", openings + [0] * len(selected))
    for material in mesh.materials:
        new_mesh.materials.append(material)
    for face in new_mesh.polygons:
        face.use_smooth = True
    shirt.data = new_mesh
    bpy.data.meshes.remove(mesh)
    new_mesh.name = NAME
    for name in group_names:
        shirt.vertex_groups.new(name=name)
    interpolated = [(weights[a] + weights[b]) * .5 for a, b in selected]
    write_weights(shirt, np.vstack((weights, interpolated)))
    new_base = np.vstack((base, points[len(base):]))
    new_offsets = np.pad(offsets, (0, len(selected)))
    new_directions = offset_directions(shirt, rest)
    new_directions[:len(base)] = directions
    return new_base, new_offsets, new_directions, len(selected)


def fit_shell(shirt, poses, iterations):
    """Bake the worst required rest-normal offset and preserve its floor."""
    base = mesh_vertices(shirt.data)
    directions = offset_directions(shirt, poses[0].surface)
    links = adjacency(shirt.data)
    matrices = skinning(shirt, poses)
    offsets = np.zeros(len(base))
    best = None
    split_count = 0
    for attempt in range(iterations + 1):
        points = base + offsets[:, None] * directions
        set_positions(shirt, points)
        needed, report, budget, contact_edges = inspect_poses(
            poses, matrices, points, directions, triangles(shirt))
        pairs = sum(row["max_pairs"] for row in report.values())
        inside = sum(row["max_inside"] for row in report.values())
        quality = (pairs + inside, pairs, inside)
        log(f"Fit {attempt}, {pairs} overlaps and {inside} inside summed across clip peaks. "
            f"Peak offset {offsets.max():.6f} m.")
        log(" | ".join(f"{name} {row['max_inside']}v/{row['max_pairs']}t"
                       for name, row in report.items()))

        rest_ok = .003 <= report["rest"]["min_distance"] <= .02
        if rest_ok and (best is None or quality < best[0]):
            if best is not None:
                bpy.data.meshes.remove(best[1])
            best = (quality, shirt.data.copy(), report, float(offsets.max()), attempt, split_count)
        if attempt == iterations or (rest_ok and pairs + inside == 0):
            break
        if attempt == 2 and contact_edges:
            split = subdivide_contacts(
                shirt, base, offsets, directions, contact_edges, poses[0].surface)
            if split is not None:
                base, offsets, directions, split_count = split
                links = adjacency(shirt.data)
                matrices = skinning(shirt, poses)
                log(f"  Subdivided {split_count} long contact edges.")
                continue

        # An arm can move into the torso during a clip. For a normal that
        # points toward that arm, a positive thickness change has an upper
        # bound as well as the clearance floor from the supporting body.
        limit = np.minimum(MAX_OFFSET, offsets + .65 * budget)
        floor = np.minimum(limit, offsets + np.minimum(needed, .002))
        field = floor
        for _ in range(7):
            field = np.clip(.48 * field + .52 * smooth(field, links), floor, limit)
        offsets = field

    if best is None:
        raise RuntimeError("No candidate met bind clearance.")
    old_mesh = shirt.data
    _, chosen, report, biggest_offset, chosen_attempt, chosen_splits = best
    shirt.data = chosen
    bpy.data.meshes.remove(old_mesh)
    chosen.name = NAME
    log(f"Selected fit {chosen_attempt}, with {chosen_splits} split edges.")
    return report, biggest_offset, chosen_attempt, chosen_splits


def finish_shirt(shirt, rig):
    fabric = bpy.data.materials.new("Sea Green Cotton")
    fabric.diffuse_color = COLOR
    fabric.use_nodes = True
    shader = fabric.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = COLOR
    shader.inputs["Roughness"].default_value = .85
    shirt.data.materials.append(fabric)
    shirt.parent = rig
    shirt.modifiers.new("Armature", "ARMATURE").object = rig


def export(shirt, rig):
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    bpy.ops.export_scene.gltf(
        filepath=str(ROOT / f"{NAME}.glb"), export_format="GLB",
        use_selection=True, export_animations=False, export_skins=True,
        export_all_influences=False, export_armature_object_remove=True,
    )
    rig.select_set(False)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / f"{NAME}.blend"), copy=True)


def cpu_render(**options):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Checker studio")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (.35, .40, .50, 1.)
    background.inputs[1].default_value = .65
    if bpy.data.objects.get("Checker key") is None:
        for name, location, energy, size in (
            ("Checker key", (-1.7, -2.6, 3.), 200, 2.5),
            ("Checker fill", (1.4, -1.2, 1.3), 55, 1.8),
            ("Checker rim", (0., 1.6, 2.6), 120, 2.),
        ):
            light = bpy.data.lights.new(name, "AREA")
            light.energy, light.shape, light.size = energy, "DISK", size
            obj = bpy.data.objects.new(name, light)
            scene.collection.objects.link(obj)
            obj.location = location
            obj.rotation_euler = (Vector((0., 0., .53)) - obj.location).to_track_quat(
                "-Z", "Y").to_euler()
    return RENDER_OPS.render(**options)


RENDER_OPS = bpy.ops.render


def run_checkers(use_cpu):
    """Run the supplied measurements on the GLB and render their four poses."""
    garment = ROOT / f"{NAME}.glb"
    original_argv = sys.argv
    for checker_name in ("motion_check", "motion_check_tri"):
        checker = ROOT / f"{checker_name}.py"
        # Both checkers use the same fixed render frames and JSON filename.
        # Render that shared evidence once and route the two data outputs.
        output = ROOT / checker_name
        output.mkdir(exist_ok=True)
        captured = StringIO()
        try:
            if checker_name.endswith("_tri"):
                bpy.ops.render = SimpleNamespace(render=lambda **_: {"FINISHED"})
            elif use_cpu:
                bpy.ops.render = SimpleNamespace(render=cpu_render)
            sys.argv = [str(checker), "--", str(MASTER), str(MOTION), str(garment), str(output)]
            with redirect_stdout(captured):
                run_path(str(checker), run_name="__main__")
        finally:
            sys.argv = original_argv
            bpy.ops.render = RENDER_OPS
        results = [line for line in captured.getvalue().splitlines() if line.startswith("RESULT ")]
        (ROOT / f"{checker_name}.log").write_text("\n".join(results) + "\n")
        (output / "motion_check.json").replace(ROOT / f"{checker_name}.json")
        for image in sorted(output.glob("*.png")):
            image.replace(ROOT / image.name)
        output.rmdir()
        log("\n".join(results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, choices=range(MAX_ITERATIONS + 1),
                        default=MAX_ITERATIONS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--cpu-render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.check_only:
        run_checkers(args.cpu_render)
        return
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    body = bpy.data.objects["Base_Body"]
    rig = bpy.data.objects["Armature"]
    if len(rig.data.bones) != 65 or any(
        not bone.name.startswith(PREFIX) or bone.rotation_mode != "QUATERNION"
        for bone in rig.pose.bones
    ):
        raise RuntimeError("Expected the 65-bone quaternion master rig.")
    surface = capture_body(body)
    shirt = make_shell(surface[2], rig)
    tri_count = len(triangles(shirt))
    log(f"Shell: {len(shirt.data.vertices)} vertices, {tri_count} triangles")
    if not 1500 <= tri_count <= 5000:
        raise RuntimeError("Triangle count outside 1,500–5,000.")
    bind_weights(body, shirt, rig, surface)
    finish_shirt(shirt, rig)
    poses = capture_poses(body, rig, MOTION)
    report, biggest_offset, chosen_attempt, split_count = fit_shell(shirt, poses, args.iterations)
    export(shirt, rig)
    glb_hash = hashlib.sha256((ROOT / f"{NAME}.glb").read_bytes()).hexdigest()
    (ROOT / "dense_motion.json").write_text(json.dumps({
        "glb_sha256": glb_hash, "frames": len(poses), "fit_iteration": chosen_attempt, "split_edges": split_count,
        "maximum_baked_offset_m": biggest_offset, "results": report,
    }, indent=2) + "\n")
    if args.check:
        run_checkers(args.cpu_render)


if __name__ == "__main__":
    main()
