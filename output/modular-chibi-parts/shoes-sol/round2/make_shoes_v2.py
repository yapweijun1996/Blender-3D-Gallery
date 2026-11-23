"""Build and verify the round-two sneakers in Blender 5.1.2."""

import hashlib
import json
import math
import struct
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
MASTER = HERE.parents[1] / "master" / "GJH_Chibi_Master_rigged.blend"
MOTION = HERE.parents[3] / "models" / "tripo-chibi-motion" / "motion.glb"
NAME = "shoes_sneaker_v2"
EXPORT = HERE / f"{NAME}.glb"
CENTER_X = 0.085927
MIRROR_X = 0.000722
CENTER_Y = -0.008
SEGMENTS = 40
SOLE_HEIGHT = 0.018
EXPORT_FLOOR_EPSILON = 0.0000002
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
SIDES = {1: "Left", -1: "Right"}

# Rings run from the outsole tread edge to the rolled cuff and back down inside.
# fit_height holds the upper shape independent of the sole bevel.
PROFILE = (
    (0, 0.014, 0.0090),
    (0.004, 0.014, 0.0110),
    (0.010, 0.015, 0.0110),
    (SOLE_HEIGHT, SOLE_HEIGHT, 0.0100),
    (0.021, 0.021, 0.0065),
    (0.029, 0.029, 0.0080),
    (0.040, 0.040, 0.0085),
    (0.050, 0.050, 0.0085),
    (0.064, 0.064, 0.0080),
    (0.082, 0.082, 0.0080),
    (0.096, 0.100, 0.0070),
    (0.102, 0.100, 0.0070),
    (0.101, 0.100, 0.0040),
    (0.096, 0.100, 0.0035),
)


def smoothstep(low, high, value):
    t = min(1.0, max(0.0, (value - low) / (high - low)))
    return t * t * (3 - 2 * t)


def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


class FootSurface:
    def __init__(self, body, sign, names):
        self.mesh = body.data
        self.points = [body.matrix_world @ v.co for v in self.mesh.vertices]
        self.polygons = [
            p.vertices[:]
            for p in self.mesh.polygons
            if all(self.points[i].x * sign > 0 and self.points[i].z < 0.15 for i in p.vertices)
        ]
        self.tree = BVHTree.FromPolygons(self.points, self.polygons, all_triangles=True)
        groups = [body.vertex_groups.get(name).index for name in names]
        self.weights = [
            tuple(next((g.weight for g in v.groups if g.group == group), 0.0) for group in groups)
            for v in self.mesh.vertices
        ]

    def foot_weights(self, point):
        hit, _, face, _ = self.tree.find_nearest(point)
        corners = self.polygons[face]
        return blend_weights(hit, corners, self.points, self.weights)

    def radius(self, height, direction):
        center = Vector((CENTER_X, CENTER_Y, height))
        _, _, _, hit_distance = self.tree.ray_cast(center + direction * 0.17, -direction, 0.17)
        if hit_distance is None:
            raise ValueError(f"No foot section at {height:.3f}, {direction}")
        return 0.17 - hit_distance


def blend_weights(point, corners, points, weights):
    a, b, c = (points[i] for i in corners)
    factors = geometry.barycentric_transform(
        point, a, b, c, Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    )
    blended = [
        max(0.0, sum(f * weights[i][g] for f, i in zip(factors, corners)))
        for g in range(3)
    ]
    return [w / sum(blended) for w in blended]


def paint_band(band, angle):
    if band < 2:
        return 2
    if band < 4:
        return 1
    if band < 6 and math.sin(angle) < -0.78:
        return 1
    if band >= 11:
        return 3
    if band == 10:
        return 4
    return 0


def bone_names(side):
    return [f"mixamorig:{side}{part}" for part in ("Foot", "ToeBase", "Leg")]


def add_laces(coords, weights, faces, face_materials):
    """Drape two shallow ivory lace strips on the vamp with its local skinning."""
    tree = BVHTree.FromPolygons(coords, faces, all_triangles=True)
    for y in (-0.082, -0.072):
        start = len(coords)
        for i in range(9):
            u = (i - 4) / 4
            x = CENTER_X + 0.033 * u
            for j in range(3):
                dy = (j - 1) * (0.0044 - 0.0010 * u ** 6)
                origin = Vector((x, y + dy + 0.0045 * u * u, 0.15))
                hit, _, face, _ = tree.ray_cast(origin, Vector((0, 0, -1)), 0.15)
                w = blend_weights(hit, faces[face], coords, weights)
                lift = (0.0030 if j == 1 else 0.0022) + 0.0012 * (1 - u * u)
                coords.append(hit + Vector((0, 0, lift)))
                weights.append(w)
        for i in range(8):
            for j in range(2):
                a = start + 3 * i + j
                faces.extend(((a, a + 3, a + 4), (a, a + 4, a + 1)))
                face_materials.extend((1, 1))


def add_star(coords, weights, faces, face_materials):
    """Conform a small, beveled star to the lateral quarter."""
    tree = BVHTree.FromPolygons(coords, faces, all_triangles=True)
    start = len(coords)
    for scale, lift in ((1.0, 0.00045), (0.88, 0.0017)):
        for i in range(10):
            angle = math.tau * i / 10
            radius = (0.0165 if i % 2 == 0 else 0.0084) * scale
            projection = Vector((0.18, 0.006 + radius * math.sin(angle),
                                 0.042 + radius * math.cos(angle)))
            hit, _, face, _ = tree.ray_cast(projection, Vector((-1, 0, 0)), 0.12)
            weights.append(blend_weights(hit, faces[face], coords, weights))
            coords.append(hit + Vector((lift, 0, 0)))
    hit, _, face, _ = tree.ray_cast(Vector((0.18, 0.006, 0.042)), Vector((-1, 0, 0)), 0.12)
    weights.append(blend_weights(hit, faces[face], coords, weights))
    coords.append(hit + Vector((0.00175, 0, 0)))
    for i in range(10):
        a, b = start + i, start + (i + 1) % 10
        faces.extend(((b, a, a + 10), (b, a + 10, b + 10), (b + 10, a + 10, start + 20)))
        face_materials.extend((1, 1, 1))


def set_action(armature, action):
    armature.animation_data.action = action
    if action:
        armature.animation_data.action_slot = action.slots[0]


def import_clips(scene, armature, keep):
    objects = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in set(scene.objects) - objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    armature.animation_data_create()
    for obj in scene.objects:
        if obj not in keep:
            obj.hide_viewport = True
            obj.hide_render = True


class FootMotion:
    def __init__(self, scene, body, armature, sign):
        names = bone_names(SIDES[sign])
        inverse = [armature.data.bones[name].matrix_local.inverted() for name in names]
        vertices = [
            v.index for v in body.data.vertices
            if v.co.x * sign > 0 and v.co.z < 0.145
        ]
        ids = {source: local for local, source in enumerate(vertices)}
        polys = [
            tuple(ids[i] for i in p.vertices)
            for p in body.data.polygons if all(i in ids for i in p.vertices)
        ]
        self.frames, self.trees = [], []
        matrices, floors = [], []
        actions = [None, *(bpy.data.actions[name] for name in CLIPS)]
        for action in actions:
            set_action(armature, action)
            name = action.name if action else "rest"
            start, end = map(int, action.frame_range) if action else (1, 1)
            steps = 4 if name in ("walk", "run") else 1
            for tick in range(steps * start, steps * end + 1):
                frame, subframe = divmod(tick, steps)
                scene.frame_set(frame, subframe=subframe / steps)
                evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
                points = [evaluated.matrix_world @ evaluated.data.vertices[i].co for i in vertices]
                self.frames.append((name, tick / steps))
                self.trees.append(BVHTree.FromPolygons(points, polys, all_triangles=True))
                matrices.append([armature.pose.bones[n].matrix @ inv for n, inv in zip(names, inverse)])
                floors.append(min(0.0, min(p.z for p in points)) if steps == 4 else -1.0)
        self.matrices = np.asarray(matrices, dtype=float)[:, :, :3, :]
        self.floors = np.asarray(floors)
        self.floor_rows = self.matrices[self.floors > -1, :, 2, :]
        self.floor_clip = self.floors[self.floors > -1] + 0.000003

    def pose(self, points, weights):
        return np.einsum("fbci,nb,ni->fnc", self.matrices, weights, points)

    def clearance(self, point, weights, cutoff=-math.inf):
        posed = self.pose([[*point, 1.0]], [weights])[:, 0]
        closest = math.inf
        for tree, coord in zip(self.trees, posed):
            position = Vector(coord)
            hit, normal, _, _ = tree.find_nearest(position)
            distance = (position - hit).dot(normal)
            closest = min(closest, distance)
            if closest < cutoff:
                break
        return closest


def reset_pose(scene, armature):
    set_action(armature, None)
    for bone in armature.pose.bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    bpy.context.view_layer.update()


def mirrored(point, sign):
    return Vector((MIRROR_X + sign * (point.x - MIRROR_X), point.y, point.z))


def heel_cut(angle):
    return smoothstep(0.1, 0.90, math.sin(angle))


def sole_options(surface, point):
    """Prefer the body's blend, with enough range to accommodate toe flex."""
    base = skin_weights(surface, point)
    toe, leg = base[1:]
    toe_min = 0.52 * smoothstep(0.073, 0.112, -point.y)
    toe_max = 0.18 + 0.82 * smoothstep(0.038, 0.084, -point.y)
    leg_max = 0.30 * (1 - smoothstep(0.048, 0.090, -point.y))
    options = []
    for t in sorted({toe, toe_min, toe_max, *(i / 10 for i in range(11))}):
        if not toe_min <= t <= toe_max + 1e-9:
            continue
        for l in sorted({leg, 0.0, 0.065, 0.13, 0.21, 0.3}):
            if l > min(leg_max + 1e-9, 1 - t):
                continue
            options.append((1 - t - l, t, l))
    return np.asarray(options), base


def fit_sole(motion, point, min_height, clearance, rim=False):
    options, base_weights = sole_options(motion.surface, point)
    rows = np.einsum("fbi,nb->nfi", motion.floor_rows, options)
    xyz = rows[:, :, 0] * point.x + rows[:, :, 1] * point.y + rows[:, :, 3]
    rise = rows[:, :, 2]
    active = rise > 1e-6
    heights = np.maximum(min_height, np.where(active, (motion.floor_clip - xyz) /
                         np.where(active, rise, 1), 0).max(axis=1))
    feasible = (xyz + heights[:, None] * rise >= motion.floor_clip - 1e-9).all(axis=1)
    weight_cost = np.sum(np.abs(options - base_weights), axis=1)
    ranking = np.argsort(heights + (0.006 if rim else 0.00065) * weight_cost, kind="stable")
    for i in ranking:
        if not feasible[i]:
            continue
        p = Vector((point.x, point.y, heights[i]))
        if motion.clearance(p, options[i], cutoff=clearance) >= clearance:
            return p, tuple(options[i])
    return None


def taper_outsole(point, ring):
    """Inset the lower toe and heel while the midsole stays wide at the welt."""
    if ring == 0:
        point.y = max(-0.104, min(0.062, point.y))
    elif ring == 1:
        point.y = max(-0.113, min(0.069, point.y))
    elif ring == 2:
        point.y = max(-0.118, min(0.075, point.y))
    return point


def cuff_profile(surface, motions, angles):
    """Choose a single axial offset and Leg fraction for all four cuff rings."""
    result = []
    for angle in angles:
        radial = Vector((math.cos(angle), math.sin(angle), 0))
        heel = heel_cut(angle)
        z_offset = -0.021 * heel
        base = surface.radius(0.096 + z_offset, radial)
        leg_default = 0.76 - 0.13 * heel
        for step in range(28):
            radius = base + 0.00085 * step
            lift = z_offset + 0.00042 * step * (1 - 2 * heel)
            best = None
            for leg in (leg_default, leg_default + 0.08, leg_default - 0.09, leg_default - 0.17):
                w = (1 - leg, 0, leg)
                if all(
                    motion.clearance(
                        mirrored(Vector((CENTER_X, CENTER_Y, height + lift)) +
                                 radial * (radius + padding), sign),
                        w, cutoff=0.0042,
                    ) >= 0.0042
                    for height, _, padding in PROFILE[10:]
                    for sign, motion in motions.items()
                ):
                    best = (radius, lift, w)
                    break
            if best is not None:
                result.append(best)
                break
        else:
            raise ValueError(f"No cuff clearance at angle {math.degrees(angle):.1f}")
    return result


def upper_profile(surface, motions):
    angles = [math.tau * index / SEGMENTS for index in range(SEGMENTS)]
    radii = []
    for _, sample_height, padding in PROFILE:
        section = [surface.radius(sample_height, Vector((math.cos(a), math.sin(a), 0))) for a in angles]
        radii.append([
            0.16 * section[i - 1] + 0.68 * section[i] + 0.16 * section[(i + 1) % SEGMENTS] + padding
            for i in range(SEGMENTS)
        ])
    cuff = cuff_profile(surface, motions, angles)
    pair_points, pair_weights = {1: [], -1: []}, {1: [], -1: []}
    for ring, (base_height, _, padding) in enumerate(PROFILE):
        for i, angle in enumerate(angles):
            heel = heel_cut(angle)
            radial = Vector((math.cos(angle), math.sin(angle), 0))
            z = base_height - {8: 0.005, 9: 0.014}.get(ring, 0.0) * heel
            radius = radii[ring][i]
            if ring == 0:
                radius = radii[1][i] - 0.0025
            if ring >= 10:
                radius, lift, w = cuff[i]
                point = Vector((CENTER_X, CENTER_Y, z + lift)) + radial * (radius + padding)
                for sign in motions:
                    pair_points[sign].append(mirrored(point, sign))
                    pair_weights[sign].append(w)
                continue
            if ring <= 3:
                for sign, motion in motions.items():
                    low = z
                    if ring:
                        low = max(z, pair_points[sign][-SEGMENTS].z + 0.0006)
                    candidate = None
                    for extra in range(21):
                        nominal = Vector((CENTER_X, CENTER_Y, z)) + radial * (radius + extra * 0.001)
                        tapered = taper_outsole(nominal.copy(), ring)
                        for factor in (0, 0.5, 1):
                            p = tapered.lerp(nominal, factor)
                            candidate = fit_sole(motion, mirrored(p, sign), low, 0.0042, rim=True)
                            if candidate is not None:
                                break
                        if candidate is not None:
                            break
                    if candidate is None:
                        raise ValueError(f"No exterior sole at {sign} {ring} {i}")
                    pair_points[sign].append(candidate[0])
                    pair_weights[sign].append(candidate[1])
                continue

            if ring == 4:
                z = max(z, *(pair_points[sign][-SEGMENTS].z + 0.0008 for sign in motions))
            p = Vector((CENTER_X, CENTER_Y, z)) + radial * radius
            w = {sign: skin_weights(motion.surface, mirrored(p, sign))
                 for sign, motion in motions.items()}
            target = 0.0042
            for _ in range(44):
                p = Vector((CENTER_X, CENTER_Y, z)) + radial * radius
                if min(motion.clearance(mirrored(p, sign), w[sign], cutoff=target)
                       for sign, motion in motions.items()) >= target:
                    break
                radius += 0.0008
                if math.sin(angle) < -0.30:
                    z += 0.0006 if ring < 10 else 0.0004
            else:
                raise ValueError(f"No upper clearance at {ring} {i}")
            for sign in motions:
                pair_points[sign].append(mirrored(p, sign))
                pair_weights[sign].append(w[sign])
    return pair_points, pair_weights


def skin_weights(surface, point):
    _, toe, leg = surface.foot_weights(point)
    full_toe = smoothstep(0.081, 0.110, -point.y)
    return ((1 - toe - leg) * (1 - full_toe), toe * (1 - full_toe) + full_toe,
            leg * (1 - full_toe))


def initial_shell(points, weights):
    faces, materials = [], []
    for band in range(len(PROFILE) - 1):
        for i in range(SEGMENTS):
            a = band * SEGMENTS + i
            b = band * SEGMENTS + (i + 1) % SEGMENTS
            c, d = b + SEGMENTS, a + SEGMENTS
            angle = math.tau * (i + 0.5) / SEGMENTS
            faces.extend(((a, b, c), (a, c, d)))
            materials.extend([paint_band(band, angle)] * 2)
    add_laces(points, weights, faces, materials)
    add_star(points, weights, faces, materials)
    return faces, materials


def signed_area(a, b, c):
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def interior_xy(p, border):
    count = 0
    for a, b in zip(border, border[1:] + border[:1]):
        if (a.y > p.y) != (b.y > p.y):
            count += a.x + (b.x - a.x) * (p.y - a.y) / (b.y - a.y) > p.x
    return count % 2 == 1


def edge_distance(p, border):
    shortest = math.inf
    for a, b in zip(border, border[1:] + border[:1]):
        segment = b - a
        fraction = (p - a).dot(segment) / max(1e-12, segment.length_squared)
        delta = p - a - max(0, min(1, fraction)) * segment
        shortest = min(shortest, delta.length)
    return shortest


def make_footbed(motion, points, weights, spacing=0.009):
    """Drape a locally tessellated tread through the available underfoot space."""
    border = [Vector(p[:2]) for p in points[:SEGMENTS]]
    ids = list(range(SEGMENTS))
    for row, y in enumerate(np.arange(-0.104, 0.067, spacing * 0.87)):
        for x in np.arange(min(p.x for p in border), max(p.x for p in border), spacing):
            p = Vector((x + (row % 2) * 0.5 * spacing, y))
            if not interior_xy(p, border) or edge_distance(p, border) < 0.002:
                continue
            candidate = fit_sole(motion, Vector((*p, 0)), 0, 0.00054)
            if candidate:
                ids.append(len(points))
                points.append(candidate[0])
                weights.append(candidate[1])
    return ids


def triangulate_tread(points, ids):
    border = list(range(SEGMENTS))
    planar = [Vector(points[i][:2]) for i in ids]
    _, _, faces, source, _, _ = geometry.delaunay_2d_cdt(
        planar, [], [border], 1, 1e-7,
    )
    result = []
    for face in faces:
        a, b, c = (ids[source[i][0]] for i in face)
        area = signed_area(points[a], points[b], points[c])
        if abs(area) > 1e-9:
            result.append((c, b, a) if area * (1 if points[0].x > 0 else -1) > 0 else (a, b, c))
    return result


def subdivide_tread(motion, points, weights, ids, budget):
    """Resolve long crossing diagonals with additional safe tread vertices."""
    border = [Vector(p[:2]) for p in points[:SEGMENTS]]
    for _ in range(2):
        tread = triangulate_tread(points, ids)
        overlaps, _ = timing_check(motion, points, weights, tread)
        if not overlaps:
            return tread
        ordered = sorted(overlaps, key=lambda f: -abs(signed_area(*(points[i] for i in tread[f]))))
        for face_id in ordered:
            if 2 * len(ids) - SEGMENTS - 2 >= budget:
                break
            a, b, c = (Vector(points[i][:2]) for i in tread[face_id])
            for sample in ((a + b + c) / 3, (a + b) / 2, (b + c) / 2, (c + a) / 2):
                if 2 * len(ids) - SEGMENTS - 2 >= budget:
                    break
                if edge_distance(sample, border) < 0.0008 or min(
                    (sample - Vector(points[i][:2])).length for i in ids
                ) < 0.002:
                    continue
                candidate = fit_sole(motion, Vector((*sample, 0)), 0, 0.00054)
                if candidate:
                    ids.append(len(points))
                    points.append(candidate[0])
                    weights.append(candidate[1])
    tread = triangulate_tread(points, ids)
    overlaps, _ = timing_check(motion, points, weights, tread)
    print(f"TREAD {len(tread) - len(overlaps)} faces, {len(overlaps)} excluded for clearance", flush=True)
    return [face for i, face in enumerate(tread) if i not in overlaps]


def refine_tread(motion, points, weights, ids, budget):
    """Spend the unused face allowance near the remaining relief boundaries."""
    base = subdivide_tread(motion, points, weights, ids, budget)
    full = triangulate_tread(points, ids)
    retained = set(base)
    denied = [f for f in full if f not in retained]
    border = [Vector(p[:2]) for p in points[:SEGMENTS]]
    limit = budget - len(base)
    if limit <= 0:
        return base
    base_ids = ids.copy()
    extra = []
    denied.sort(key=lambda face: (
        0 if sum(points[i].y for i in face) / 3 < -0.072 else 1,
        -abs(signed_area(*(points[i] for i in face))),
    ))
    for face in denied:
        a, b, c = (Vector(points[i][:2]) for i in face)
        positions = [((a * i + b * j + c * (4 - i - j)) / 4)
                     for i in range(5) for j in range(5 - i)
                     if max(i, j, 4 - i - j) < 4]
        for sample in positions:
            if not interior_xy(sample, border) or edge_distance(sample, border) < 0.0005:
                continue
            if min((sample - Vector(points[i][:2])).length for i in ids) < 0.00125:
                continue
            test = fit_sole(motion, Vector((*sample, 0.0)), 0.0, 0.000535)
            if test:
                extra.append(len(points))
                ids.append(len(points))
                points.append(test[0])
                weights.append(test[1])
                if len(extra) >= limit:
                    break
        if len(extra) >= limit:
            break

    def safe_faces(subset):
        tread = triangulate_tread(points, base_ids + extra[:subset])
        hits, _ = timing_check(motion, points, weights, tread)
        return [f for i, f in enumerate(tread) if i not in hits]
    best = base
    for subset in (len(extra), limit * 3 // 4, limit // 2, limit // 3):
        proposed = safe_faces(subset)
        if len(best) < len(proposed) <= budget:
            best = proposed
    print(f"TREAD {len(best)} faces after boundary refinement", flush=True)
    return best


def timing_check(motion, points, weights, faces):
    posed = motion.pose(np.column_stack((np.asarray(points), np.ones(len(points)))), np.asarray(weights))
    counts, floor = {}, {}
    for (name, frame), body, vertices, ground in zip(motion.frames, motion.trees, posed, motion.floors):
        mesh = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
        for _, face in body.overlap(mesh):
            counts.setdefault(face, set()).add((name, frame))
        if ground > -1:
            difference = vertices[:, 2].min() - ground
            floor[name] = min(floor.get(name, (math.inf,)), (difference, frame))
    return counts, floor


def export_asset(scene, body, arm, pair_points, pair_weights, pair_faces, pair_materials):
    materials = [
        material("Purple upper", (0.17, 0.031, 0.49), 0.37),
        material("Ivory rubber", (0.88, 0.86, 0.95), 0.43),
        material("Deep purple tread", (0.12, 0.028, 0.31), 0.52),
        material("Purple lining", (0.085, 0.032, 0.23), 0.57),
        material("Purple collar piping", (0.35, 0.14, 0.65), 0.42),
    ]
    points = pair_points[1] + pair_points[-1]
    offset = len(pair_points[1])
    faces = pair_faces[1] + [tuple(offset + i for i in reversed(face)) for face in pair_faces[-1]]
    assert len(faces) <= 3500
    mesh = bpy.data.meshes.new("Sneaker pair")
    mesh.from_pydata(
        [(p.x, p.y, p.z + EXPORT_FLOOR_EPSILON) for p in points], [], faces,
    )
    mesh.update()
    shoes = bpy.data.objects.new("Sneaker_Pair", mesh)
    scene.collection.objects.link(shoes)
    for mat in materials:
        mesh.materials.append(mat)
    for poly, mat_index in zip(mesh.polygons, pair_materials[1] + pair_materials[-1]):
        poly.use_smooth = mat_index != 2
        poly.material_index = mat_index
    for sign, start in ((1, 0), (-1, offset)):
        groups = [shoes.vertex_groups.new(name=n) for n in bone_names(SIDES[sign])]
        for index, weights in enumerate(pair_weights[sign], start=start):
            for group, weight in zip(groups, weights):
                if weight > 1e-7:
                    group.add([index], weight, "REPLACE")
    shoes.parent = arm
    shoes.modifiers.new("Master skin", "ARMATURE").object = arm
    for obj in list(scene.objects):
        if obj not in (arm, shoes):
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data_clear()
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.object.select_all(action="DESELECT")
    shoes.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = shoes
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"{NAME}.blend"))
    bpy.ops.export_scene.gltf(
        filepath=str(EXPORT), export_format="GLB", use_selection=True,
        export_yup=True, export_animations=False, export_skins=True,
        export_def_bones=False, export_armature_object_remove=True,
        export_all_influences=False, export_materials="EXPORT",
    )


def build():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    body, arm = (scene.objects[n] for n in ("Base_Body", "Armature"))
    assert len(arm.data.bones) == 65
    assert all(b.rotation_mode == "QUATERNION" for b in arm.pose.bones)
    import_clips(scene, arm, (body, arm))
    motions = {}
    for sign, side in SIDES.items():
        motions[sign] = FootMotion(scene, body, arm, sign)
        reset_pose(scene, arm)
        motions[sign].surface = FootSurface(body, sign, bone_names(side))
    points, weights = upper_profile(motions[1].surface, motions)
    pair_faces, pair_materials = {}, {}
    geometry_size = len(points[1])
    faces, materials = initial_shell(points[1], weights[1])
    points[-1].extend(mirrored(point, -1) for point in points[1][geometry_size:])
    weights[-1].extend(weights[1][geometry_size:])
    n_shell = len(faces)
    for sign, motion in motions.items():
        collisions, _ = timing_check(motion, points[sign], weights[sign], faces)
        if collisions:
            summary = {face: (len(frames), min(frames)) for face, frames in collisions.items()}
            raise ValueError(f"Shoe side {sign} shell collisions: {summary}")
        ids = make_footbed(motion, points[sign], weights[sign])
        tread = refine_tread(motion, points[sign], weights[sign], ids, 1750 - n_shell)
        pair_faces[sign] = faces + tread
        pair_materials[sign] = materials + [2] * len(tread)
    reset_pose(scene, arm)
    export_asset(scene, body, arm, points, weights, pair_faces, pair_materials)



def verify_asset_contract():
    """Confirm the exported skin is interchangeable with the round-one asset."""
    def read_contract(path):
        data = path.read_bytes()
        size, = struct.unpack_from("<I", data, 12)
        document = json.loads(data[20:20 + size])
        skin, = document["skins"]
        joints = [document["nodes"][i]["name"] for i in skin["joints"]]
        accessor = document["accessors"][skin["inverseBindMatrices"]]
        view = document["bufferViews"][accessor["bufferView"]]
        start = 28 + size + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        return data, document, joints, data[start:start + 64 * accessor["count"]]

    data, gltf, joints, inverse_bind = read_contract(EXPORT)
    _, _, first_joints, first_bind = read_contract(HERE.parent / "shoes_sneaker_v1.glb")
    assert len(joints) == 65 and joints == first_joints and inverse_bind == first_bind
    assert not gltf.get("animations") and not gltf.get("images")
    mesh, = gltf["meshes"]
    triangles, lowest_z = 0, math.inf
    for primitive in mesh["primitives"]:
        attrs = primitive["attributes"]
        assert {"JOINTS_0", "WEIGHTS_0"} <= attrs.keys()
        assert not {"JOINTS_1", "WEIGHTS_1"} & attrs.keys()
        triangles += gltf["accessors"][primitive["indices"]]["count"] // 3
        lowest_z = min(lowest_z, gltf["accessors"][attrs["POSITION"]]["min"][1])
    assert triangles <= 3500
    assert 0 <= lowest_z <= EXPORT_FLOOR_EPSILON * 1.001
    print(f"ASSET {triangles} triangles, {len(data)} bytes, {len(joints)} joints, min Z {lowest_z:g}")


def reimport_on_master(export=EXPORT):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    body, arm = (scene.objects[name] for name in ("Base_Body", "Armature"))
    old = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(export))
    imported = set(scene.objects) - old
    shoes, = (obj for obj in imported if obj.type == "MESH" and obj.vertex_groups)
    shoes.parent = None
    for obj in imported - {shoes}:
        bpy.data.objects.remove(obj, do_unlink=True)
    shoes.modifiers.clear()
    shoes.parent = arm
    shoes.modifiers.new("Master skin", "ARMATURE").object = arm
    import_clips(scene, arm, (arm, body, shoes))
    reset_pose(scene, arm)
    return scene, body, arm, shoes


def verify_dense(scene, body, arm, shoes):
    """Check the exact exported asset at every keyed interval plus gait subframes."""
    body_faces = [p.vertices[:] for p in body.data.polygons]
    shoe_faces = [p.vertices[:] for p in shoes.data.polygons]
    foot_ids, shoe_ids = {}, {}
    for sign in SIDES:
        foot_ids[sign] = [v.index for v in body.data.vertices if v.co.x * sign > 0 and v.co.z < 0.145]
        shoe_ids[sign] = [v.index for v in shoes.data.vertices if v.co.x * sign > 0]
    checks, floors = {}, {}
    for action in [None, *(bpy.data.actions[name] for name in CLIPS)]:
        set_action(arm, action)
        name = action.name if action else "rest"
        start, end = map(int, action.frame_range) if action else (1, 1)
        steps = 4 if name in ("walk", "run") else 1
        result = {"samples": 0, "max_vertices_inside": 0, "max_triangle_pairs": 0,
                  "min_signed_distance_m": math.inf, "min_distance_frame": None}
        for tick in range(steps * start, steps * end + 1):
            frame, subframe = divmod(tick, steps)
            scene.frame_set(frame, subframe=subframe / steps)
            graph = bpy.context.evaluated_depsgraph_get()
            be, ge = (obj.evaluated_get(graph) for obj in (body, shoes))
            bv, gv = ([o.matrix_world @ v.co for v in o.data.vertices] for o in (be, ge))
            body_tree = BVHTree.FromPolygons(bv, body_faces, all_triangles=True)
            shoe_tree = BVHTree.FromPolygons(gv, shoe_faces, all_triangles=True)
            distances = []
            for p in gv:
                q, normal, _, _ = body_tree.find_nearest(p)
                distances.append((p - q).dot(normal))
            result["samples"] += 1
            result["max_vertices_inside"] = max(result["max_vertices_inside"], sum(d < 0 for d in distances))
            result["max_triangle_pairs"] = max(result["max_triangle_pairs"], len(body_tree.overlap(shoe_tree)))
            if min(distances) < result["min_signed_distance_m"]:
                result["min_signed_distance_m"] = min(distances)
                result["min_distance_frame"] = tick / steps
            if name in ("rest", "walk", "run"):
                for sign, side in SIDES.items():
                    shoe_z = min(gv[i].z for i in shoe_ids[sign])
                    body_z = min(bv[i].z for i in foot_ids[sign])
                    ground = min(0, body_z) if name != "rest" else 0
                    margin = shoe_z - ground
                    key = f"{name}_{side.lower()}"
                    if key not in floors or margin < floors[key]["min_margin_m"]:
                        floors[key] = {"min_margin_m": margin, "frame": tick / steps,
                                       "shoe_z_m": shoe_z, "body_z_m": body_z}
        checks[name] = result
        print("DENSE", name, result, flush=True)
    payload = {"export_sha256": hashlib.sha256(EXPORT.read_bytes()).hexdigest(),
               "motion": checks, "floor": floors}
    (HERE / "dense_check.json").write_text(json.dumps(payload, indent=2) + "\n")
    assert all(item["max_vertices_inside"] == item["max_triangle_pairs"] == 0
               and item["min_signed_distance_m"] >= 0.0005 for item in checks.values())
    assert all(item["min_margin_m"] >= 0 for item in floors.values())


def setup_cpu_render(scene, samples, width, height):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("Soft studio")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.86, 0.89, 0.96, 1)
    background.inputs["Strength"].default_value = 0.65


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_motion_detail(scene, arm, shoes):
    setup_cpu_render(scene, 36, 700, 590)
    data = bpy.data.cameras.new("Foot detail")
    camera = bpy.data.objects.new("Foot detail", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.type = "ORTHO"
    data.ortho_scale = 0.29
    for name, frame, sign, offset, output in (
        ("run", 4, -1, (-0.35, -0.48, 0.105), "run_frame4_toe.png"),
        ("run", 4, -1, (-0.09, -0.08, -0.60), "run_frame4_underside.png"),
        ("walk", 19, 1, (0.30, -0.43, 0.075), "walk_frame19_toe.png"),
    ):
        set_action(arm, bpy.data.actions[name])
        scene.frame_set(frame)
        posed = shoes.evaluated_get(bpy.context.evaluated_depsgraph_get())
        vertices = [posed.matrix_world @ evaluated.co
                    for rest, evaluated in zip(shoes.data.vertices, posed.data.vertices)
                    if sign * rest.co.x > 0 and rest.co.z < 0.05]
        center = sum(vertices, Vector()) / len(vertices)
        camera.location = center + Vector(offset)
        aim(camera, center)
        scene.render.filepath = str(HERE / output)
        bpy.ops.render.render(write_still=True)


def run_supplied_checkers():
    from contextlib import redirect_stdout
    from tempfile import TemporaryDirectory

    workbench = (
        "sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
        "sc.display.shading.color_type='MATERIAL'"
    )
    cpu = """
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 12
sc.cycles.use_denoising = False
sc.render.image_settings.file_format = 'PNG'
sc.render.resolution_percentage = 100
sc.world = bpy.data.worlds.new('Checker studio')
sc.world.use_nodes = True
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.86, .89, .96, 1)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
"""
    original_args = sys.argv
    try:
        for name in ("motion_check", "motion_check_tri"):
            checker = HERE / f"{name}.py"
            source = checker.read_text()
            assert source.count(workbench) == 1
            with TemporaryDirectory(prefix=".checker-", dir=HERE) as tmp:
                sys.argv = [original_args[0], "--", str(MASTER), str(MOTION), str(EXPORT), tmp]
                with (HERE / f"{name}.txt").open("w") as log, redirect_stdout(log):
                    exec(compile(source.replace(workbench, cpu, 1), str(checker), "exec"),
                         {"__name__": "__main__"})
                path = Path(tmp)
                (path / "motion_check.json").replace(HERE / f"{name}.json")
                if name == "motion_check":
                    for image in path.glob("*.png"):
                        image.replace(HERE / image.name)
                print((HERE / f"{name}.txt").read_text(), end="", flush=True)
    finally:
        sys.argv = original_args


def render_preview():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=str(EXPORT))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 28
    scene.render.resolution_x = 760
    scene.render.resolution_y = 630
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("Soft studio")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.82, 0.88, 1.0, 1)
    background.inputs["Strength"].default_value = 0.37
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.0006))
    bpy.context.object.data.materials.append(material("Backdrop", (0.70, 0.73, 0.80), 0.63))

    def point_at(obj, target):
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

    for name, loc, power, size, color in (
        ("Key", (0.02, -0.4, 0.54), 14, 0.42, (1.0, 0.95, 0.87)),
        ("Fill", (-0.4, -0.05, 0.27), 9, 0.38, (0.81, 0.87, 1.0)),
        ("Rim", (0.20, 0.28, 0.42), 17, 0.28, (0.98, 0.96, 1.0)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size, data.color = power, "DISK", size, color
        lamp = bpy.data.objects.new(name, data)
        scene.collection.objects.link(lamp)
        lamp.location = loc
        point_at(lamp, (0, -0.025, 0.035))
    camera = bpy.data.cameras.new("Preview")
    scene.camera = bpy.data.objects.new("Preview", camera)
    scene.collection.objects.link(scene.camera)
    camera.type = "ORTHO"
    camera.ortho_scale = 0.41
    scene.camera.location = (0.44, -0.68, 0.42)
    point_at(scene.camera, (0, -0.026, 0.030))
    scene.render.filepath = str(HERE / "sneaker_preview.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    options = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--qa-only" not in options:
        build()
    verify_asset_contract()
    if "--assets-only" not in options:
        run_supplied_checkers()
        setup = reimport_on_master()
        verify_dense(*setup)
        render_motion_detail(setup[0], setup[2], setup[3])
        render_preview()
