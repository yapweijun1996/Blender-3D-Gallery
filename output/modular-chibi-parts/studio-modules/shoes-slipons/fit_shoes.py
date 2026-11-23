"""Fit the supplied Studio slip-on pair using Blender 5.1's Python API.

Run in background Blender with --python fit_shoes.py. All paths are relative
to this file. The separate work/verify_shoes.py checks the exported module.
"""

from collections import Counter
from pathlib import Path
import hashlib
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
MASTER = HERE.parents[1] / "master" / "GJH_Chibi_Master_rigged.blend"
MOTION = HERE.parents[3] / "models" / "tripo-chibi-motion" / "motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
NAME = "shoes_slipons_v1"
DESTINATION = Path(os.environ.get("SLIPONS_FIT_OUTPUT", HERE)).resolve()
if not DESTINATION.is_relative_to(HERE):
    raise ValueError("Outputs must stay inside the slip-on module directory")
EXPORT = DESTINATION / f"{NAME}.glb"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
SIDES = ("Left", "Right")
TREAD_Z = -.010
BED_Z = -.0055
TARGET = .0022
REST_TARGET = .0031


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def set_pose(scene, arm, name, frame):
    action = bpy.data.actions[name] if name != "rest" else None
    if arm.animation_data.action != action:
        arm.animation_data.action = action
        if action:
            arm.animation_data.action_slot = action.slots[0]
    if action is None:
        for bone in arm.pose.bones:
            bone.matrix_basis.identity()
    integer = math.floor(frame)
    scene.frame_set(integer, subframe=frame - integer)


def import_objects(path, **kwargs):
    scene = bpy.context.scene
    existing = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), **kwargs)
    return [obj for obj in scene.objects if obj not in existing]


def load_master(with_motion=True):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    arm, body = (scene.objects[key] for key in ("Armature", "Base_Body"))
    arm.animation_data_create()
    assert len(arm.data.bones) == 65
    assert all(b.rotation_mode == "QUATERNION" for b in arm.pose.bones)
    if with_motion:
        for obj in import_objects(MOTION):
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in scene.objects:
        if obj not in (arm, body):
            obj.hide_viewport = True
            obj.hide_render = True
    set_pose(scene, arm, "rest", 1)
    return scene, arm, body


def frames():
    yield "rest", 1.0
    for name in CLIPS:
        start, end = bpy.data.actions[name].frame_range
        rate = 4 if name in ("walk", "run") else 2
        samples = {float(start), float(end)}
        samples.update(tick / rate for tick in range(math.ceil(rate * start), math.floor(rate * end) + 1))
        samples.update(int(start + (end - start) * k / 12) for k in range(12))
        samples.update(range(int(start), int(end) + 1, 3))
        yield from ((name, time) for time in sorted(samples))


def hull(points):
    points = [Vector(p) for p in points]
    return np.asarray([points[i][:] for i in geometry.convex_hull_2d(points)])


def cross2(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def radial_hit(center, direction, border):
    edges = np.roll(border, -1, axis=0) - border
    offset = border - center
    denom = cross2(direction, edges)
    nonparallel = np.abs(denom) > 1e-10
    radius = cross2(offset[nonparallel], edges[nonparallel]) / denom[nonparallel]
    edge_t = cross2(offset[nonparallel], direction) / denom[nonparallel]
    return float(radius[(radius >= 0) & (edge_t >= -1e-6) & (edge_t <= 1 + 1e-6)].min())


def smoothstep(low, high, value):
    u = np.clip((value - low) / (high - low), 0, 1)
    return u * u * (3 - 2 * u)


def connected(seed, neighbors, allowed):
    found = {seed}
    queue = [seed]
    for vertex in queue:
        for other in neighbors[vertex]:
            if other in allowed and other not in found:
                found.add(other)
                queue.append(other)
    return found


def adjacency(count, faces):
    neighbors = [set() for _ in range(count)]
    for a, b, c in faces:
        neighbors[a].update((b, c))
        neighbors[b].update((a, c))
        neighbors[c].update((a, b))
    return [tuple(sorted(row)) for row in neighbors]


def import_shoes():
    objects = import_objects(SOURCE, merge_vertices=True)
    obj, = (o for o in objects if o.type == "MESH")
    mesh = obj.data
    uv = mesh.uv_layers.active
    material, = mesh.materials
    world = [obj.matrix_world @ v.co for v in mesh.vertices]
    # glTF splits vertices at UV seams. Weld positions and retain per-corner UVs.
    ids, points, indices = {}, [], []
    for v in world:
        key = tuple(round(value, 6) for value in v)
        if key not in ids:
            ids[key] = len(points)
            points.append(tuple(v))
        indices.append(ids[key])
    faces, texcoords, seen = [], [], set()
    for poly in mesh.polygons:
        face = tuple(indices[i] for i in poly.vertices)
        key = tuple(sorted(face))
        if len(set(face)) < 3 or key in seen:
            continue
        seen.add(key)
        faces.append(face)
        texcoords.append(tuple(tuple(uv.uv[i].vector) for i in poly.loop_indices))
    edges = loop_edges(faces)
    kept = []
    for face, corners in zip(faces, texcoords):
        counts = sorted(len(edges[min(a, b), max(a, b)])
                        for a, b in zip(face, face[1:] + face[:1]))
        # Each source shoe contains one hanging triangle over a closed seam.
        if counts != [1, 3, 3]:
            kept.append((face, corners))
    faces, texcoords = map(list, zip(*kept))
    neighbors = adjacency(len(points), faces)
    remaining = {i for i, row in enumerate(neighbors) if row}
    pieces = []
    while remaining:
        ids = sorted(connected(min(remaining), neighbors, remaining))
        remaining.difference_update(ids)
        if len(ids) <= 3:
            continue
        old_to_new = {old: new for new, old in enumerate(ids)}
        selected = [i for i, f in enumerate(faces) if f[0] in old_to_new]
        coords = np.asarray([points[i] for i in ids])
        forward = np.linalg.eigh(np.cov(coords[:, :2].T))[1][:, -1]
        forward *= -np.sign(forward[0])
        lateral = np.array([-forward[1], forward[0]])
        xyz = np.column_stack((coords[:, :2] @ lateral, -coords[:, :2] @ forward, coords[:, 2]))
        pieces.append((float(xyz[:, 0].mean()), forward, xyz,
                       [tuple(old_to_new[v] for v in faces[i]) for i in selected],
                       [texcoords[i] for i in selected]))
    pieces.sort(key=lambda part: -part[0])
    assert len(pieces) == 2
    for o in objects:
        bpy.data.objects.remove(o, do_unlink=True)
    for node in material.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            image = node.image
            if max(image.size) > 1024:
                ratio = 1024 / max(image.size)
                image.scale(*(round(side * ratio) for side in image.size))
                image.pack()
    return pieces, material


class Foot:
    def __init__(self, body, arm, side):
        self.side = side
        sign = 1 if side == "Left" else -1
        self.names = tuple(f"mixamorig:{side}{part}" for part in ("Foot", "ToeBase", "Leg"))
        self.ankle = np.asarray(arm.data.bones[self.names[0]].head_local[:2], dtype=float)
        self.center = np.array([self.ankle[0] + .004 * sign, -.013])
        self.points = np.asarray([body.matrix_world @ v.co for v in body.data.vertices])
        self.ids = np.flatnonzero((self.points[:, 0] * sign > 0) & (self.points[:, 2] < .17))
        remap = {v: i for i, v in enumerate(self.ids)}
        self.faces = [tuple(remap[v] for v in p.vertices) for p in body.data.polygons
                      if all(v in remap for v in p.vertices)]
        self.coords = self.points[self.ids]
        self.tree = BVHTree.FromPolygons(self.coords, self.faces, all_triangles=True)
        self.outline = hull(self.coords[self.coords[:, 2] < .09, :2])
        groups = [body.vertex_groups[name].index for name in self.names]
        self.weights = np.zeros((len(self.ids), 3))
        for row, idx in enumerate(self.ids):
            by_group = {g.group: g.weight for g in body.data.vertices[idx].groups}
            self.weights[row] = [by_group.get(g, 0) for g in groups]

    def sample_weights(self, point, plantar=False):
        coord = Vector(point)
        if plantar:
            delta = Vector((*self.center, point[2])) - coord
            for amount in (0, .10, .20, .35, .50):
                hit, _, face, _ = self.tree.ray_cast(
                    coord + amount * delta + Vector((0, 0, -.18)), Vector((0, 0, 1)), .28)
                if hit is not None:
                    break
            else:
                hit, _, face, _ = self.tree.find_nearest(coord)
        else:
            hit, _, face, _ = self.tree.find_nearest(coord)
        corners = self.faces[face]
        bary = geometry.barycentric_transform(
            hit, *(Vector(self.coords[i]) for i in corners),
            Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        weights = np.maximum(0, np.asarray(bary) @ self.weights[list(corners)])
        weights /= weights.sum()
        if not plantar:
            toe = smoothstep(.081, .108, -point[1])
            weights *= 1 - toe
            weights[1] += toe
        return weights

    def section(self, direction, height):
        center = Vector((*self.ankle, height))
        radial = Vector((*direction, 0))
        hit, _, _, _ = self.tree.ray_cast(center + .20 * radial, -radial, .25)
        return None if hit is None else float((hit - center).dot(radial))


def loop_edges(faces):
    edges = {}
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            key = min(a, b), max(a, b)
            edges.setdefault(key, []).append((a, b))
    return edges


def cavity_cut(points, faces):
    """Find the well from a seed inside the collar and stop below the lip."""
    low, high = points.min(0), points.max(0)
    center_x = (low[0] + high[0]) * .5
    seed_point = (center_x, low[1] + .67 * (high[1] - low[1]), .18)
    seed = int(np.linalg.norm(points - seed_point, axis=1).argmin())
    neighbors = adjacency(len(points), faces)
    allowed = set(np.flatnonzero((points[:, 2] > .11) & (points[:, 2] < .277)))
    assert seed in allowed
    remove = connected(seed, neighbors, allowed)
    keep = [i for i, face in enumerate(faces) if not remove.intersection(face)]
    original_edges = loop_edges(faces)
    exposed = loop_edges([faces[i] for i in keep])
    boundary = {b: a for edge, rows in exposed.items() if len(rows) == 1
                and len(original_edges[edge]) == 2 for a, b in rows}
    start = min(boundary)
    ring = [start]
    while boundary[ring[-1]] != start and len(ring) <= len(boundary):
        ring.append(boundary[ring[-1]])
    assert len(boundary) == len(ring), (len(remove), len(boundary), len(ring))
    assert .08 < len(remove) / len(points) < .35, len(remove)
    assert min(points[ring, 2]) > .18
    return keep, ring, len(remove)


def outline_fit(points, foot):
    low, high = points.min(0), points.max(0)
    origin = (low[:2] + high[:2]) * .5
    source_outline = hull(points[:, :2])
    rounded = [p + np.array([.0115 * math.cos(a), .0065 * math.sin(a)])
               for p in foot.outline for a in (math.tau * i / 24 for i in range(24))]
    target = hull(rounded)
    fitted = np.zeros_like(points)
    for i, point in enumerate(points):
        delta = point[:2] - origin
        radius = np.linalg.norm(delta)
        direction = delta / max(radius, 1e-10)
        source_r = radial_hit(origin, direction, source_outline)
        target_r = radial_hit(foot.center, direction, target)
        fitted[i, :2] = foot.center + delta * target_r / source_r
    fitted[:, 2] = np.interp(points[:, 2], (0, .044, .064, .125, .175, .24, .30, .397),
                             (TREAD_Z, TREAD_Z, -.0065, .006, .017, .041, .069, .101))
    # Preserve the source's vertically stacked welt vertices where flattening
    # would otherwise collapse different layers to identical positions.
    columns = {}
    for idx in np.flatnonzero(fitted[:, 2] == TREAD_Z):
        columns.setdefault(tuple(fitted[idx, :2].round(8)), []).append(idx)
    for column in columns.values():
        for order, idx in enumerate(sorted(column, key=lambda i: points[i, 2])):
            fitted[idx, 2] += order * .00012
    return fitted


def inside_outline(point, border):
    x, y = point
    return sum((a.y > y) != (b.y > y)
               and x < a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y)
               for a, b in zip(border, border[1:] + border[:1])) % 2 == 1


def liner_uv(points, faces, patch_points, patch_faces, patch_uv):
    """Reuse the original cavity island on new lining triangles."""
    tree = BVHTree.FromPolygons(patch_points, patch_faces, all_triangles=True)
    texcoords = []
    for face in faces:
        location = sum((Vector(points[i]) for i in face), Vector()) / 3
        _, _, idx, _ = tree.find_nearest(location)
        triangle = [Vector(patch_points[i]) for i in patch_faces[idx]]
        uv = [Vector((*p, 0)) for p in patch_uv[idx]]
        texcoords.append(tuple(tuple(geometry.barycentric_transform(
            geometry.closest_point_on_tri(Vector(points[i]), *triangle), *triangle, *uv)[:2])
                               for i in face))
    return texcoords


def boundary_loop(faces):
    rows = loop_edges(faces)
    edge = {b: a for values in rows.values() if len(values) == 1 for a, b in values}
    if not edge:
        return None
    ring = [min(edge)]
    while len(ring) <= len(edge):
        nxt = edge.get(ring[-1])
        if nxt == ring[0]:
            return ring if len(ring) == len(edge) else None
        if nxt is None:
            return None
        ring.append(nxt)
    return None


def cap_slab(points, rim, foot, maximum_faces):
    """Give the outsole a closed, recessed roof below the plantar skin."""
    inner_count = len(rim)
    vectors = np.asarray(points)[rim, :2] - foot.center
    winding = np.sign(cross2(vectors, np.roll(vectors, -1, axis=0)).sum())
    angles = np.unwrap(winding * np.arctan2(vectors[:, 1], vectors[:, 0]))
    # Maintain correspondence with the original welt while regularizing the
    # occasional backtrack from the retopology's zigzag seam.
    ordered = np.maximum.accumulate(angles - np.arange(inner_count) * .005)
    ordered += np.arange(inner_count) * .005
    ordered = angles[0] + (ordered - ordered[0]) * min(1.0, 6.27 / (ordered[-1] - ordered[0]))
    inner_ids, inner = [], []
    for theta, v in zip(ordered * winding, vectors):
        direction = np.array([math.cos(theta), math.sin(theta)])
        xy = foot.center + direction * (np.linalg.norm(v) - .0100)
        inner_ids.append(len(points))
        inner.append(Vector(xy))
        points.append([*xy, BED_Z])
    faces = []
    for i, (a, b) in enumerate(zip(rim, inner_ids)):
        j = (i + 1) % inner_count
        faces.extend(((a, rim[j], b), (rim[j], inner_ids[j], b)))

    interior_budget = (maximum_faces - len(faces) - inner_count + 2) // 2
    assert interior_budget >= 8, (len(rim), maximum_faces)
    border = tuple(inner)
    for y in np.arange(-.107, .072, .020):
        for x in np.arange(foot.center[0] - .050, foot.center[0] + .060, .020):
            p = Vector((x, y))
            if len(inner) - inner_count >= interior_budget or not inside_outline(p, border):
                continue
            if min((p - q).length for q in inner) < .004:
                continue
            inner_ids.append(len(points))
            inner.append(p)
            points.append([x, y, BED_Z])
    _, _, triangles, source, _, _ = geometry.delaunay_2d_cdt(
        inner, [], [list(range(inner_count))], 1, 1e-8)
    for triangle in triangles:
        ids = tuple(inner_ids[source[i][0]] for i in triangle)
        a, b, c = (Vector(points[i]) for i in ids)
        faces.append(ids if (b - a).cross(c - a).z > 0 else ids[::-1])
    return faces


def make_shoe(piece, foot):
    _, forward, raw, original_faces, original_uv = piece
    selected, _, removed = cavity_cut(raw, original_faces)
    p = outline_fit(raw, foot)
    lift = smoothstep(.025, .078, p[:, 2])
    y_warp = np.interp(p[:, 1], (-.13, -.020, .087), (-.13, -.052, .087))
    p[:, 1] += lift * (y_warp - p[:, 1])
    p[:, 0] += .11 * lift * (p[:, 0] - foot.ankle[0])
    # The neutral welt hugs the rounded plantar outline. This reserve also
    # covers the concave edge in the original Studio retopology.
    low = 1 - smoothstep(.020, .055, p[:, 2])
    delta = p[:, :2] - foot.center
    direction = delta / np.linalg.norm(delta, axis=1).clip(1e-9)[:, None]
    p[:, :2] += direction * low[:, None] * np.array([.0048, .0008])
    points = [list(point) for point in p]
    kinds = ["tread" if z <= .045 else "sole" if z < .164 else "upper" for z in raw[:, 2]]
    sole_for_face = np.asarray([raw[list(face), 2].mean() for face in original_faces])
    for level in (.155, .145, .166, .172, .135, .126):
        sole_faces_ids = [i for i in selected if sole_for_face[i] < level]
        lower = [original_faces[i] for i in sole_faces_ids]
        seam = boundary_loop(lower)
        if seam is not None and 12 <= len(seam) <= 100:
            break
    else:
        raise RuntimeError(f"No continuous outsole seam for {foot.side}")
    print("SOLE SEAM", foot.side, len(seam), level, flush=True)
    roof = cap_slab(points, seam, foot, 1750 - len(selected))
    kinds.extend("bed" for _ in range(len(points) - len(raw)))
    lower_edges = loop_edges(lower + roof)
    assert all(len(edge) == 2 and edge[0] == edge[1][::-1]
               for edge in lower_edges.values()), (foot.side, len(seam), level)
    # A closed, independently connected sole primitive shares an exact
    # position and deformation with the open upper at every welt vertex.
    upper_map = {}
    for i in seam:
        upper_map[i] = len(points)
        points.append(points[i].copy())
        kinds.append("skirt")
    sole_set = set(sole_faces_ids)
    faces = [
        original_faces[i] if i in sole_set else tuple(upper_map.get(v, v) for v in original_faces[i])
        for i in selected
    ]
    uv = [original_uv[i] for i in selected]
    keep_set = set(selected)
    removed_ids = [i for i in range(len(original_faces)) if i not in keep_set]
    cavity_faces = [original_faces[i] for i in removed_ids]
    cavity_uv = [original_uv[i] for i in removed_ids]
    patch_points = p.copy()
    patch_points[:, 2] = BED_Z + .10 * (raw[:, 2] - .16)
    uv += liner_uv(points, roof, patch_points, cavity_faces, cavity_uv)
    faces += roof
    ids = sorted({v for face in faces for v in face})
    remap = {v: i for i, v in enumerate(ids)}
    points_out = np.asarray([points[i] for i in ids])
    kind_out = np.asarray([kinds[i] for i in ids])
    weights = np.asarray([foot.sample_weights(pt, typ in ("tread", "sole", "bed", "skirt"))
                          for pt, typ in zip(points_out, kind_out)])
    # Both primitives use identical weights at the seam.
    seam_pairs = [(remap[a], remap[b]) for a, b in upper_map.items()]
    for lower_id, upper_id in seam_pairs:
        weights[upper_id] = weights[lower_id]
    meta = {"source_forward_blender": [*forward, 0.0],
            "source_vertices": len(raw), "source_triangles": len(original_faces),
            "original_uv_triangles": len(selected), "cavity_removed_vertices": removed,
            "closed_sole_seam_vertices": len(seam), "closed_sole_roof_triangles": len(roof),
            "sole_face_ids": [i for i, source_id in enumerate(selected) if source_id in sole_set]
                             + list(range(len(selected), len(faces))),
            "seam_pairs": seam_pairs}
    return points_out, weights, [tuple(remap[v] for v in face) for face in faces], uv, kind_out, meta


def motion_cache(scene, body, arm, feet, samples):
    bones = [[arm.pose.bones[name] for name in foot.names] for foot in feet]
    inverses = [[bone.bone.matrix_local.inverted() for bone in row] for row in bones]
    tables = [[] for foot in feet]
    # Retain both feet here. During the crossing step in walk, a shoe can
    # contact the other foot even if its own foot has generous clearance.
    ids = sorted(set().union(*(foot.ids.tolist() for foot in feet)))
    remap = {v: i for i, v in enumerate(ids)}
    body_faces = [tuple(remap[v] for v in p.vertices) for p in body.data.polygons
                  if all(v in remap for v in p.vertices)]
    for name, frame in samples:
        set_pose(scene, arm, name, frame)
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        coords = [evaluated.matrix_world @ evaluated.data.vertices[i].co for i in ids]
        tree = BVHTree.FromPolygons(coords, body_faces, all_triangles=True)
        for table, row, bind in zip(tables, bones, inverses):
            matrices = np.asarray([bone.matrix @ rest for bone, rest in zip(row, bind)])[:, :3]
            table.append((tree, matrices, coords, body_faces))
    set_pose(scene, arm, "rest", 1)
    return tables


def measure_vertices(tree, points):
    distances = np.empty(len(points))
    normals = np.empty((len(points), 3))
    for i, point in enumerate(points.tolist()):
        position = Vector(point)
        hit, normal, _, _ = tree.find_nearest(position)
        distances[i] = (position - hit).dot(normal)
        normals[i] = normal
    return distances, normals


def contact_witness(shoe, body):
    """Return a point on the common segment of a pair of overlapping triangles."""
    hits = []
    for edges, plane in ((shoe, body), (body, shoe)):
        for a, b in zip(edges, edges[1:] + edges[:1]):
            direction = b - a
            if direction.length < 1e-8:
                continue
            hit = geometry.intersect_ray_tri(*plane, direction.normalized(), a, True)
            if hit is not None and -1e-6 <= (hit - a).dot(direction.normalized()) <= direction.length + 1e-6:
                hits.append(hit)
    return sum(hits, Vector()) / len(hits) if hits else None


def fit_clearance(piece, foot, motion, samples, iterations=12, exact=False):
    """Bake the worst constraints from all sampled poses into rest geometry."""
    points, weights, faces, _, kinds, info = piece
    faces_array = np.asarray(faces, dtype=int)
    neighbors = adjacency(len(points), faces)
    row = np.array([i for i, group in enumerate(neighbors) for _ in group])
    col = np.array([j for group in neighbors for j in group])
    degree = np.bincount(row)[:, None]
    locked = kinds == "tread"
    bed = kinds == "bed"
    upper = kinds == "upper"
    original = points.copy()
    matrices = np.stack([mat for _, mat, _, _ in motion])
    seam_base, seam_upper = np.asarray(info["seam_pairs"]).T
    skin = np.einsum("fbci,nb->fnci", matrices, weights)
    extreme = None
    for iteration in range(iterations + 1):
        posed = np.einsum("fnci,ni->fnc", skin[..., :3], points) + skin[..., 3]
        correction = np.zeros_like(points)
        strength = np.zeros(len(points))
        overlaps_max = vertices_max = 0
        min_signed = math.inf
        min_rest_upper = math.inf
        for pose_id, ((tree, _, body_coords, body_faces), coordinates) in enumerate(zip(motion, posed)):
            d, normals = measure_vertices(tree, coordinates)
            vertices_max = max(vertices_max, int((d < 0).sum()))
            if d.min() < min_signed:
                idx = int(d.argmin())
                min_signed = float(d[idx])
                extreme = (samples[pose_id], kinds[idx], idx, points[idx].round(5).tolist())
            overlaps = tree.overlap(BVHTree.FromPolygons(coordinates, faces, all_triangles=True))
            overlaps_max = max(overlaps_max, len(overlaps))
            # Compute the directional derivative in bind space, including
            # nonrigid Foot and ToeBase blending at the ball of the foot.
            gradient = np.einsum("nji,nj->ni", skin[pose_id, :, :, :3], normals)
            desired = np.full(len(points), TARGET)
            if pose_id == 0:
                min_rest_upper = float(d[upper].min())
                desired[upper] = REST_TARGET
            depth = desired - d
            gradient[locked, 2] = 0
            gradient[bed, 2] = np.minimum(0, gradient[bed, 2])
            current = depth > strength
            strength[current] = depth[current]
            size = np.einsum("ni,ni->n", gradient, gradient).clip(.10)
            correction[current] = gradient[current] * (depth[current] / size[current])[:, None]
            if not overlaps:
                continue
            if exact:
                for body_face, shoe_face in overlaps:
                    triangle = faces_array[shoe_face]
                    shoe_triangle = [Vector(coordinates[v]) for v in triangle]
                    body_triangle = [body_coords[v] for v in body_faces[body_face]]
                    hit = contact_witness(shoe_triangle, body_triangle)
                    if hit is None:
                        continue
                    normal = (body_triangle[1] - body_triangle[0]).cross(
                        body_triangle[2] - body_triangle[0]).normalized()
                    bary = geometry.barycentric_transform(
                        hit, *shoe_triangle, Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
                    norm = sum(max(0, w) ** 2 for w in bary)
                    if iteration == 0 and pose_id == 0:
                        print("CONTACT", foot.side, shoe_face, tuple(kinds[triangle]), tuple(hit), tuple(normal),
                              flush=True)
                    for vertex, weight in zip(triangle, bary):
                        required = 1.4 * TARGET * max(0, weight) / max(norm, .20)
                        if required <= strength[vertex]:
                            continue
                        direction = skin[pose_id, vertex, :, :3].T @ np.asarray(normal)
                        if locked[vertex]:
                            direction[2] = 0
                        if bed[vertex]:
                            direction[2] = min(0, direction[2])
                        strength[vertex] = required
                        correction[vertex] = direction * required / max(.10, direction @ direction)
            affected = faces_array[sorted({f for _, f in overlaps})]
            # Cover broad triangles whose vertices individually clear the foot.
            for barycentric in ((1/3, 1/3, 1/3), (.5, .5, 0), (.5, 0, .5), (0, .5, .5)):
                bary = np.asarray(barycentric)
                xyz = np.einsum("nki,k->ni", coordinates[affected], bary)
                face_distance, face_normal = measure_vertices(tree, xyz)
                for local, vertex in np.ndenumerate(affected):
                    face_index, corner = local
                    required = (TARGET - face_distance[face_index]) * 1.20
                    if bary[corner] == 0 or required <= strength[vertex]:
                        continue
                    normal = face_normal[face_index]
                    direction = skin[pose_id, vertex, :, :3].T @ normal
                    if locked[vertex]:
                        direction[2] = 0
                    if bed[vertex]:
                        direction[2] = min(0, direction[2])
                    strength[vertex] = required
                    correction[vertex] = direction * required / max(.10, direction @ direction)
        print("BAKE", foot.side, iteration, vertices_max, overlaps_max,
              round(min_signed * 1000, 3), "rest upper", round(min_rest_upper * 1000, 3),
              extreme, flush=True)
        if overlaps_max == vertices_max == 0 and min_signed >= .00125 and min_rest_upper >= .00295:
            break
        if iteration == iterations:
            break
        smoothed = np.zeros_like(correction)
        np.add.at(smoothed, row, correction[col])
        update = .83 * correction + .30 * smoothed / degree
        update[locked, 2] = 0
        update[bed, 2] = np.minimum(0, update[bed, 2])
        seam_move = (update[seam_base] + update[seam_upper]) / 2
        update[seam_base] = update[seam_upper] = seam_move
        length = np.linalg.norm(update, axis=1)
        points += update * np.minimum(1, .0055 / length.clip(1e-12))[:, None]
        points[bed, 2] = np.maximum(points[bed, 2], TREAD_Z + .0015)
    info["max_baked_offset_m"] = max(float(np.linalg.norm(points - original, axis=1).max()),
                                      info.get("max_baked_offset_m", 0.0))
    info["bake_min_signed_m"] = min_signed
    info["bake_max_vertices_inside"] = vertices_max
    info["bake_max_overlaps"] = overlaps_max
    return piece


def write_glb():
    bpy.ops.export_scene.gltf(
        filepath=str(EXPORT), export_format="GLB", use_selection=True,
        export_animations=False, export_armature_object_remove=True,
        export_all_influences=False, export_materials="EXPORT", export_tangents=True,
    )


def export_pair(scene, arm, pieces, feet, material):
    vertices, faces, texcoords, sole_faces, normals = [], [], [], set(), []
    mesh = bpy.data.meshes.new("Studio slip-on shoes")
    for points, _, local_faces, uv, _, info in pieces:
        n = info["original_uv_triangles"]
        point_normals = np.zeros_like(points)
        outer = np.asarray(local_faces[:n])
        a, b, c = points[outer].transpose(1, 0, 2)
        areas = np.cross(b - a, c - a)
        for column in range(3):
            np.add.at(point_normals, outer[:, column], areas)
        sole_faces.update(len(faces) + i for i in info["sole_face_ids"])
        for lower, upper in info["seam_pairs"]:
            point_normals[lower] = point_normals[upper] = point_normals[lower] + point_normals[upper]
        point_normals /= np.linalg.norm(point_normals, axis=1).clip(1e-12)[:, None]
        for i, face in enumerate(local_faces):
            if i < n:
                normals.extend(tuple(point_normals[v]) for v in face)
            else:
                normals.extend([(0, 0, 0)] * 3)
        faces.extend(tuple(i + len(vertices) for i in face) for face in local_faces)
        vertices.extend(points.tolist())
        texcoords.extend(uv)
    assert len(faces) <= 3500, len(faces)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    assert not mesh.validate(verbose=True)
    material.name = "Tripo Studio Upper"
    mesh.materials.append(material)
    sole_material = material.copy()
    sole_material.name = "Tripo Studio Closed Sole"
    mesh.materials.append(sole_material)
    uv_layer = mesh.uv_layers.new(name="Studio UV")
    for polygon, triangle_uv in zip(mesh.polygons, texcoords):
        polygon.use_smooth = True
        polygon.material_index = int(polygon.index in sole_faces)
        for index, uv in zip(polygon.loop_indices, triangle_uv):
            uv_layer.uv[index].vector = uv
    mesh.normals_split_custom_set(normals)
    shoes = bpy.data.objects.new("Shoes_Slipons", mesh)
    scene.collection.objects.link(shoes)
    shoes.parent = arm
    shoes.modifiers.new("Master armature", "ARMATURE").object = arm
    first = 0
    for foot, (points, weights, _, _, _, _) in zip(feet, pieces):
        groups = [shoes.vertex_groups.new(name=name) for name in foot.names]
        for vertex, coefficients in enumerate(weights, first):
            normalizer = sum(w for w in coefficients if w > 1e-5)
            for group, w in zip(groups, coefficients):
                if w > 1e-5:
                    group.add([vertex], float(w / normalizer), "REPLACE")
        first += len(points)
    set_pose(scene, arm, "rest", 1)
    for obj in list(scene.objects):
        if obj not in (arm, shoes):
            bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for _ in range(4):
        bpy.data.orphans_purge(do_recursive=True)
    select(shoes)
    arm.select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_location = (0, -.02, .042)
                area.spaces.active.region_3d.view_distance = .57
                area.spaces.active.region_3d.view_rotation = Vector((.29, -.53, .30)).to_track_quat("Z", "Y")
                area.spaces.active.overlay.show_overlays = False
                area.spaces.active.shading.color_type = "TEXTURE"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(DESTINATION / f"{NAME}.blend"), compress=True)
    write_glb()


def checkpoint_positions():
    with bpy.data.libraries.load(str(DESTINATION / f"{NAME}.blend"), link=False) as (source, target):
        target.meshes = [name for name in source.meshes if name == "Studio slip-on shoes"]
    mesh, = target.meshes
    positions = np.array([v.co[:] for v in mesh.vertices])
    bpy.data.meshes.remove(mesh)
    return positions


def build():
    scene, arm, body = load_master()
    parts, material = import_shoes()
    feet = [Foot(body, arm, side) for side in SIDES]
    pieces = [make_shoe(part, foot) for part, foot in zip(parts, feet)]
    for foot, (points, weights, faces, uv, kind, info) in zip(feet, pieces):
        print("MESH", foot.side, len(points), len(faces), dict(Counter(kind)), flush=True)
    samples = list(frames())
    if "--baseline" in sys.argv:
        export_pair(scene, arm, pieces, feet, material)
        return
    cache = motion_cache(scene, body, arm, feet, samples)
    if "--refine" in sys.argv:
        saved = checkpoint_positions()
        cursor = 0
        for points, _, _, _, _, _ in pieces:
            end = cursor + len(points)
            points[:] = saved[cursor:end]
            cursor = end
        assert cursor == len(saved)
    coarse = [i for i, (_, frame) in enumerate(samples) if i == 0 or frame % 5 == 0]
    for shoe, foot, motion in zip(pieces, feet, cache):
        if "--refine" not in sys.argv:
            fit_clearance(shoe, foot, [motion[i] for i in coarse],
                          [samples[i] for i in coarse], iterations=8)
        fit_clearance(shoe, foot, motion, samples, iterations=7, exact=True)
    export_pair(scene, arm, pieces, feet, material)
    (DESTINATION / "source_fit.json").write_text(json.dumps(
        {foot.side: {k: v for k, v in piece[-1].items() if k not in ("sole_face_ids", "seam_pairs")}
         for foot, piece in zip(feet, pieces)}, indent=2) + "\n")


if __name__ == "__main__":
    if "--export-only" in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(DESTINATION / f"{NAME}.blend"))
        select(bpy.data.objects["Shoes_Slipons"])
        bpy.data.objects["Armature"].select_set(True)
        write_glb()
    else:
        build()
