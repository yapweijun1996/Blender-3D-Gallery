"""Build and verify the round-three sneakers in Blender 5.1.2."""

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
NAME = "shoes_sneaker_v3"
EXPORT = HERE / f"{NAME}.glb"
CENTER_X = 0.085927
MIRROR_X = 0.000722
CENTER_Y = -0.008
SEGMENTS = 36
TREAD_THICKNESS = 0.0025
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
SIDES = {1: "Left", -1: "Right"}

# Outer profile from vamp to the folded collar. Lower rings come from the
# projected footprint, so the toe and heel stay continuous through the bevel.
PROFILE = (
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
        matrices = []
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
        self.matrices = np.asarray(matrices, dtype=float)[:, :, :3, :]

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
                    for height, _, padding in PROFILE[5:]
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


def upper_profile(surface, motions, angles):
    cuff = cuff_profile(surface, motions, angles)
    pair_points, pair_weights = {1: [], -1: []}, {1: [], -1: []}
    for ring, (height, sample_height, padding) in enumerate(PROFILE):
        section = [surface.radius(sample_height, Vector((math.cos(a), math.sin(a), 0))) for a in angles]
        for i, angle in enumerate(angles):
            heel = heel_cut(angle)
            radial = Vector((math.cos(angle), math.sin(angle), 0))
            z = height - {3: 0.005, 4: 0.014}.get(ring, 0.0) * heel
            if ring >= 5:
                radius, lift, w = cuff[i]
                p = Vector((CENTER_X, CENTER_Y, z + lift)) + radial * (radius + padding)
                for sign in motions:
                    pair_points[sign].append(mirrored(p, sign))
                    pair_weights[sign].append(w)
                continue

            radius = 0.22 * section[i - 1] + 0.56 * section[i] + 0.22 * section[(i + 1) % SEGMENTS] + padding
            p = Vector((CENTER_X, CENTER_Y, z)) + radial * radius
            w = {sign: skin_weights(motion.surface, mirrored(p, sign))
                 for sign, motion in motions.items()}
            target = 0.0047
            for _ in range(44):
                p = Vector((CENTER_X, CENTER_Y, z)) + radial * radius
                if all(motion.clearance(mirrored(p, sign), w[sign], cutoff=target) >= target
                       for sign, motion in motions.items()):
                    break
                radius += 0.0008
                if math.sin(angle) < -0.30:
                    z += 0.0005
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


def footprint(surface):
    """Sample a rounded 2D convex footprint around all skin below the cuff."""
    ids = {index for face in surface.polygons for index in face}
    projected = [Vector(surface.points[i][:2]) for i in sorted(ids) if surface.points[i].z < 0.09]
    hull = [projected[i] for i in geometry.convex_hull_2d(projected)]
    # A circular offset rounds each corner of the hull before radial resampling.
    rounded = [p + 0.010 * Vector((math.cos(a), math.sin(a))) for p in hull
               for a in (math.tau * i / 32 for i in range(32))]
    return [rounded[i] for i in geometry.convex_hull_2d(rounded)]


def perimeter(hull):
    """Resample by arc length to keep enough vertices at the toe and heel."""
    center = Vector((CENTER_X, CENTER_Y))
    start = max(range(len(hull)), key=lambda i: hull[i].x - 5 * abs(hull[i].y - CENTER_Y))
    hull = hull[start:] + hull[:start]
    if (hull[1] - hull[0]).cross(center - hull[0]) < 0:
        hull = hull[:1] + hull[:0:-1]
    edges = list(zip(hull, hull[1:] + hull[:1]))
    lengths = [(b - a).length for a, b in edges]
    spacing = sum(lengths) / SEGMENTS
    index, walked, outline = 0, 0, []
    for step in range(SEGMENTS):
        distance = step * spacing
        while walked + lengths[index] < distance:
            walked += lengths[index]
            index += 1
        a, b = edges[index]
        outline.append(a.lerp(b, (distance - walked) / lengths[index]))
    angles = [math.atan2(p.y - center.y, p.x - center.x) for p in outline]
    return outline, angles


def lower_weights(surface, point):
    """Use the plantar skin weights throughout the outsole and toe transition."""
    up = Vector((0, 0, 1))
    hit, _, _, _ = surface.tree.ray_cast(Vector((point.x, point.y, -0.10)), up, 0.22)
    if hit is None:
        # Project slightly inboard at the welt so outer edges follow the foot sole.
        center = mirrored(Vector((CENTER_X, CENTER_Y, 0)), 1 if point.x > 0 else -1)
        p = Vector((point.x, point.y, 0)).lerp(center, 0.16)
        hit, _, _, _ = surface.tree.ray_cast(p - 0.1 * up, up, 0.22)
    return surface.foot_weights(point if hit is None else hit)


def edge_distance(p, border):
    shortest = math.inf
    for a, b in zip(border, border[1:] + border[:1]):
        segment = b - a
        fraction = (p - a).dot(segment) / segment.length_squared
        shortest = min(shortest, (p - a - max(0, min(1, fraction)) * segment).length)
    return shortest


def interior_xy(p, border):
    count = 0
    for a, b in zip(border, border[1:] + border[:1]):
        if (a.y > p.y) != (b.y > p.y):
            count += a.x + (b.x - a.x) * (p.y - a.y) / (b.y - a.y) > p.x
    return count % 2 == 1


def plantar_height(point):
    """A small toe spring and heel bevel leave a broad, nearly planar tread."""
    return (-0.0035 + 0.0055 * smoothstep(0.100, 0.128, -point.y)
            + 0.004 * smoothstep(0.059, 0.085, point.y))


def slab_rings(surface, outline, upper, upper_weights, sign):
    center = Vector((CENTER_X, CENTER_Y))
    rings, weighted = [], []
    for band in range(5):
        ring, ring_weights = [], []
        for i, p in enumerate(outline):
            inward = (center - p).normalized()
            bevel = (0.0023, 0.0003, 0.0, 0.0010, 0.0030)[band]
            medial = (1 - smoothstep(0.014, 0.039, p.x)) * smoothstep(-0.027, 0.008, p.y)
            if band < 4:
                bevel += medial * (0.0040, 0.0040, 0.0035, 0.0020)[band]
            xy = p + inward * bevel
            offsets = (-TREAD_THICKNESS, -0.0013, 0.002, 0.014, 0.021)
            z = plantar_height(p) + offsets[band]
            if band < 3:
                z += medial * (0.0028, 0.0026, 0.0014)[band]
            point = mirrored(Vector((*xy, z)), sign)
            w = lower_weights(surface, mirrored(Vector((*p, z)), sign))
            if band == 4:
                point = point.lerp(upper[i], 0.18)
                w = tuple(0.80 * a + 0.20 * b for a, b in zip(w, upper_weights[i]))
            ring.append(point)
            ring_weights.append(w)
        rings.extend(ring)
        weighted.extend(ring_weights)
    return rings, weighted


def footbed_height(point):
    relief = smoothstep(0.053, 0.072, -point.y) * (1 - smoothstep(0.099, 0.114, -point.y))
    return plantar_height(point) - 0.0017 * relief


def close_sole(points, weights, rim_start, motion, sign):
    """Skin the outsole and footbed on one paired triangulation."""
    outsole = list(range(SEGMENTS))
    footbed = list(range(rim_start, rim_start + SEGMENTS))
    border = [Vector(points[i][:2]) for i in footbed]
    low_x, high_x = min(p.x for p in border), max(p.x for p in border)
    samples = [Vector((x + row % 2 * 0.0145, y))
               for row, y in enumerate(np.arange(-0.115, 0.078, 0.0275))
               for x in np.arange(low_x, high_x, 0.029)]
    center = mirrored(Vector((CENTER_X, 0, 0)), sign).x
    samples.extend(Vector((center + sign * dx, y))
                   for y in (-0.098, -0.076)
                   for dx in (-0.040, -0.016, 0.008, 0.032))
    planar = border.copy()
    for p in samples:
        if not interior_xy(p, border) or edge_distance(p, border) < 0.003:
            continue
        if any((p - other).length < 0.003 for other in planar):
            continue
        top = Vector((*p, footbed_height(p)))
        bottom = Vector((*p, plantar_height(p) - TREAD_THICKNESS))
        # Paired points stay on the same skinning column through toe flex.
        blend = lower_weights(motion.surface, top)
        outsole.append(len(points))
        footbed.append(len(points) + 1)
        points.extend((bottom, top))
        weights.extend((blend, blend))
        planar.append(p)
    _, _, triangles, source, _, _ = geometry.delaunay_2d_cdt(
        planar, [], [list(range(SEGMENTS))], 1, 1e-7)
    base_faces, bed_faces = [], []
    for triangle in triangles:
        a, b, c = (source[i][0] for i in triangle)
        if ((planar[b] - planar[a]).cross(planar[c] - planar[a]) > 0) != (sign > 0):
            a, c = c, a
        bed_faces.append(tuple(footbed[i] for i in (a, b, c)))
        base_faces.append(tuple(outsole[i] for i in (c, b, a)))
    return base_faces, bed_faces


def make_shoe(motion, sign, outline, upper, upper_weights, angles):
    points, weights = slab_rings(motion.surface, outline, upper, upper_weights, sign)
    points.extend(upper)
    weights.extend(upper_weights)
    # Inner lining follows the same deformation as the adjacent outer panels.
    for row in (9, 8, 7, 6, 5, 4, 3):
        for i in range(SEGMENTS):
            index = row * SEGMENTS + i if row > 3 else i
            point = points[index].copy()
            center = mirrored(Vector((CENTER_X, CENTER_Y, point.z)), sign)
            point += (center - point).normalized() * (0.0012 if row > 3 else 0.0006)
            if row == 3:
                point.z = max(footbed_height(point), points[index].z + 0.0008)
            points.append(point)
            weights.append(weights[index])

    rows = len(points) // SEGMENTS
    faces, mats = [], []
    for band in range(rows - 1):
        for i, angle in enumerate(angles):
            a = band * SEGMENTS + i
            b = band * SEGMENTS + (i + 1) % SEGMENTS
            c, d = b + SEGMENTS, a + SEGMENTS
            if band >= 13:
                # The liner descends. Match the outside diagonal to keep its
                # nonplanar quads parallel to the outer panels.
                faces.extend(((a, b, d), (b, c, d)))
            else:
                faces.extend(((a, b, c), (a, c, d)))
            if band >= 12:
                mat = 3
            elif band == 11:
                mat = 4
            elif band < 2:
                mat = 2
            elif band < 4:
                mat = 5
            elif band < 6 and math.sin(angle) < -0.68:
                mat = 1
            else:
                mat = 0
            mats.extend((mat, mat))
    surface_faces = len(faces)
    if sign == 1:
        add_laces(points, weights, faces, mats)
        add_star(points, weights, faces, mats)
    return points, weights, faces, mats, rows, surface_faces


def verify_closed_shell(points, faces, surface_faces, detail_faces, motion, sign):
    """Check the body of each shoe separately from its applied lace and star trims."""
    edges = {}
    for a, b, c in faces[:surface_faces] + faces[detail_faces:]:
        for u, v in ((a, b), (b, c), (c, a)):
            key = (min(u, v), max(u, v))
            count, balance = edges.get(key, (0, 0))
            edges[key] = (count + 1, balance + (1 if u < v else -1))
    assert all(count == 2 and balance == 0 for count, balance in edges.values())
    border = [Vector(v[:2]) for v in points[:SEGMENTS]]
    skin = [Vector(motion.surface.points[i][:2])
            for i in {v for f in motion.surface.polygons for v in f}
            if motion.surface.points[i].z < 0.09]
    overhang = min(edge_distance(v, border) * (1 if interior_xy(v, border) else -1)
                   for v in skin)
    assert overhang >= 0.003, (SIDES[sign], overhang)
    return {"shell_edges": len(edges), "open_or_inconsistent_shell_edges": 0,
            "min_rest_outsole_overhang_m": overhang}


def timing_check(motion, other, points, weights, faces):
    posed = motion.pose(np.column_stack((np.asarray(points), np.ones(len(points)))), np.asarray(weights))
    counts = {}
    for (name, frame), body, opposite, vertices in zip(motion.frames, motion.trees, other.trees, posed):
        mesh = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
        for _, face in body.overlap(mesh) + opposite.overlap(mesh):
            counts.setdefault(face, set()).add((name, frame))
    return counts


def export_asset(scene, body, arm, pair_points, pair_weights, pair_faces, pair_materials):
    materials = [
        material("Purple upper", (0.17, 0.031, 0.49), 0.37),
        material("Ivory rubber", (0.88, 0.86, 0.95), 0.43),
        material("Deep purple tread", (0.12, 0.028, 0.31), 0.52),
        material("Purple lining", (0.085, 0.032, 0.23), 0.57),
        material("Purple collar piping", (0.35, 0.14, 0.65), 0.42),
        material("Ivory midsole", (0.88, 0.86, 0.95), 0.43),
    ]
    points = pair_points[1] + pair_points[-1]
    offset = len(pair_points[1])
    faces = pair_faces[1] + [tuple(offset + i for i in reversed(face)) for face in pair_faces[-1]]
    assert len(faces) <= 3500
    mesh = bpy.data.meshes.new("Sneaker pair")
    mesh.from_pydata(
        points, [], faces,
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
    outline, angles = perimeter(footprint(motions[1].surface))
    upper, upper_weights = upper_profile(motions[1].surface, motions, angles)
    points, weights, pair_faces, pair_materials = {}, {}, {}, {}
    details, fit_report = None, {}
    for sign, motion in motions.items():
        p, w, faces, mats, rows, surface_faces = make_shoe(
            motion, sign, outline, upper[sign], upper_weights[sign], angles,
        )
        if sign == 1:
            details = (p[rows * SEGMENTS:].copy(), w[rows * SEGMENTS:].copy(),
                       faces[surface_faces:].copy(), mats[surface_faces:].copy())
        else:
            detail_p, detail_w, detail_f, detail_m = details
            p.extend(mirrored(v, sign) for v in detail_p)
            w.extend(detail_w)
            faces.extend(detail_f)
            mats.extend(detail_m)
        detail_end = len(faces)
        base, bed = close_sole(p, w, (rows - 1) * SEGMENTS, motion, sign)
        faces.extend(base + bed)
        mats.extend([2] * len(base) + [3] * len(bed))
        fit_report[SIDES[sign]] = verify_closed_shell(p, faces, surface_faces, detail_end, motion, sign)
        overlaps = timing_check(motion, motions[-sign], p, w, faces)
        print(f"FIT {sign} {len(faces)} triangles, {len(overlaps)} overlap faces", flush=True)
        for f, frames in sorted(overlaps.items(), key=lambda item: -len(item[1]))[:24]:
            center = sum((p[i] for i in faces[f]), Vector()) / 3
            print(f"  {f}: {len(frames)} samples, {min(frames)}, {tuple(round(v*1000, 1) for v in center)}")
        points[sign], weights[sign], pair_faces[sign], pair_materials[sign] = p, w, faces, mats
    reset_pose(scene, arm)
    export_asset(scene, body, arm, points, weights, pair_faces, pair_materials)
    (HERE / "sole_geometry_check.json").write_text(json.dumps({
        "export_sha256": hashlib.sha256(EXPORT.read_bytes()).hexdigest(),
        "shoes": fit_report,
    }, indent=2) + "\n")


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
    triangles, lowest_z, max_influences = 0, math.inf, 0
    for primitive in mesh["primitives"]:
        attrs = primitive["attributes"]
        assert {"JOINTS_0", "WEIGHTS_0"} <= attrs.keys()
        assert not {"JOINTS_1", "WEIGHTS_1"} & attrs.keys()
        weights = gltf["accessors"][attrs["WEIGHTS_0"]]
        buffer = gltf["bufferViews"][weights["bufferView"]]
        json_size, = struct.unpack_from("<I", data, 12)
        start = 28 + json_size + buffer.get("byteOffset", 0) + weights.get("byteOffset", 0)
        code = {5121: "B", 5123: "H", 5126: "f"}[weights["componentType"]]
        stride = buffer.get("byteStride", struct.calcsize("<" + 4 * code))
        max_influences = max(max_influences, max(
            sum(weight > 0 for weight in struct.unpack_from("<" + 4 * code, data, start + i * stride))
            for i in range(weights["count"])
        ))
        triangles += gltf["accessors"][primitive["indices"]]["count"] // 3
        lowest_z = min(lowest_z, gltf["accessors"][attrs["POSITION"]]["min"][1])
    assert triangles <= 3500 and 1 <= max_influences <= 4
    (HERE / "asset_contract.json").write_text(json.dumps({
        "export_sha256": hashlib.sha256(data).hexdigest(),
        "triangles": triangles, "glb_bytes": len(data), "joints": len(joints),
        "max_influences": max_influences, "lowest_raw_z_m": lowest_z,
    }, indent=2) + "\n")
    print(f"ASSET {triangles} triangles, {len(data)} bytes, {len(joints)} joints, min Z {lowest_z:g}, max influences {max_influences}")


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


def emission_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    light = nodes.new("ShaderNodeEmission")
    light.inputs["Color"].default_value = (*color, 1)
    output = nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(light.outputs["Emission"], output.inputs["Surface"])
    return mat


def silhouette_interior(coverage, width, height):
    """Include enclosed holes in the projected outline, even if a sole omits faces."""
    filled = np.pad(coverage.reshape(height, width), 1, constant_values=False)
    outside = ~filled
    stride = width + 2
    available = bytearray(outside.ravel())
    stack = [0]
    available[0] = 0
    while stack:
        index = stack.pop()
        row, col = divmod(index, stride)
        adjacent = (
            index - 1 if col else 0,
            index + 1 if col <= width else 0,
            index - stride if row else 0,
            index + stride if row <= height else 0,
        )
        for other in adjacent:
            if available[other]:
                available[other] = 0
                outside.flat[other] = False
                stack.append(other)
    outside[0, 0] = False
    return (filled | outside)[1:-1, 1:-1].ravel()


def render_skin_masks(scene, body, shoes, stem, flat):
    """Count directly visible tagged body pixels in a shoes-only silhouette."""
    original_body = list(body.data.materials)
    original_shoes = list(shoes.data.materials)
    settings = (scene.world, scene.render.film_transparent, scene.view_settings.view_transform,
                scene.cycles.samples, scene.render.image_settings.color_mode)
    green, red, blue, black = flat
    scene.world = black
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.color_mode = "RGBA"
    scene.cycles.samples = 12
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.max_bounces = 0
    for i in range(len(original_body)):
        body.data.materials[i] = green
    for i, mat in enumerate(original_shoes):
        shoes.data.materials[i] = blue if any(name in mat.name.lower() for name in ("tread", "midsole")) else red

    def capture(suffix):
        path = HERE / f"{stem}_{suffix}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path), check_existing=False)
        try:
            pixels = np.empty(len(image.pixels), dtype=np.float32)
            image.pixels.foreach_get(pixels)
            return pixels.reshape(-1, 4)
        finally:
            bpy.data.images.remove(image)

    body.hide_render = True
    silhouette = capture("silhouette")
    body.hide_render = False
    combined = capture("skin")
    shoes.hide_render = True
    control = capture("body_control")
    shoes.hide_render = False
    (HERE / f"{stem}_body_control.png").unlink()

    # The green channel is unique to the body with zero light bounces.
    # Omit only the partial-coverage pixels at the exterior antialiased edge.
    solid = silhouette[:, 3] >= 0.99
    inside = silhouette_interior(solid, scene.render.resolution_x, scene.render.resolution_y)
    sole = (solid & (silhouette[:, 2] >= 0.98)) | (inside & ~solid)
    tagged_sole_edge = solid & (silhouette[:, 2] > 0.02) & ~sole
    is_skin = combined[:, 1] > 0.02
    control_skin = (control[:, 1] >= 0.98) & (control[:, 3] >= 0.99)
    result = {
        "silhouette_pixels": int(inside.sum()),
        "enclosed_hole_pixels": int((inside & ~solid).sum()),
        "untested_boundary_pixels": int(((silhouette[:, 3] > 0) & ~inside).sum()),
        "skin_pixels_inside_shoe_silhouette": int((inside & is_skin).sum()),
        "skin_pixels_inside_sole_silhouette": int((sole & is_skin).sum()),
        "skin_pixels_on_mixed_sole_tag_boundary": int((tagged_sole_edge & is_skin).sum()),
        "body_only_pixels_inside_shoe_silhouette": int((inside & control_skin).sum()),
        "body_only_pixels_inside_sole_silhouette": int((sole & control_skin).sum()),
    }
    assert result["body_only_pixels_inside_shoe_silhouette"] > 0, result
    for i, original in enumerate(original_body):
        body.data.materials[i] = original
    for i, original in enumerate(original_shoes):
        shoes.data.materials[i] = original
    scene.world, scene.render.film_transparent, scene.view_settings.view_transform, \
        scene.cycles.samples, scene.render.image_settings.color_mode = settings
    scene.cycles.max_bounces = 12
    return result


def render_motion_detail(scene, body, arm, shoes, export=EXPORT, baseline=False):
    setup_cpu_render(scene, 24, 700, 590)
    data = bpy.data.cameras.new("Foot detail")
    camera = bpy.data.objects.new("Foot detail", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.type = "ORTHO"
    black = bpy.data.worlds.new("Black mask world")
    flat = (emission_material("Body mask green", (0, 1, 0)),
            emission_material("Shoe mask red", (1, 0, 0)),
            emission_material("Tread mask blue", (0, 0, 1)),
            black)
    cases = (("walk", 19, 1), ("walk", 23, 1), ("run", 4, -1), ("run", 12, -1))
    results = {}
    candidate_cameras = json.loads((HERE / "skin_check.json").read_text())["views"] if baseline else {}
    for name, frame, sign in cases:
        if baseline and (name, frame) not in (("walk", 19), ("run", 4)):
            continue
        set_action(arm, bpy.data.actions[name])
        scene.frame_set(frame)
        posed = shoes.evaluated_get(bpy.context.evaluated_depsgraph_get())
        vertices = [posed.matrix_world @ evaluated.co
                    for rest, evaluated in zip(shoes.data.vertices, posed.data.vertices)
                    if sign * rest.co.x > 0 and rest.co.z < 0.05]
        center = sum(vertices, Vector()) / len(vertices)
        cameras = {
            "front": (None, 1.5, 500, 500),
            "underside": ((-0.09, -0.08, -0.60), 0.35, 700, 590),
            "side": ((sign * 0.58, -0.045, -0.025), 0.37, 700, 590),
            "toe": ((sign * 0.34, -0.45, 0.085), 0.32, 700, 590),
        }
        for view, (offset, scale, width, height) in cameras.items():
            if baseline and view != "underside":
                continue
            if view == "toe" and (name, frame) not in (("walk", 19), ("run", 4)):
                continue
            scene.render.resolution_x, scene.render.resolution_y = width, height
            data.ortho_scale = scale
            if offset is None:
                camera.location = (0, -6, 0.5)
                camera.rotation_euler = (math.pi / 2, 0, 0)
            else:
                camera.location = center + Vector(offset)
                aim(camera, center)
            view_name = f"{name}_frame{frame}_{view}"
            stem = view_name
            if baseline:
                stem = f"round2_{view_name}"
                match = candidate_cameras[view_name]
                camera.location = match["camera_location"]
                camera.rotation_euler = match["camera_rotation"]
                data.ortho_scale = match["ortho_scale"]
            if not baseline:
                scene.render.filepath = str(HERE / f"{stem}.png")
                bpy.ops.render.render(write_still=True)
            if view != "toe":
                result = render_skin_masks(scene, body, shoes, stem, flat)
                result["camera_location"] = list(camera.location)
                result["camera_rotation"] = list(camera.rotation_euler)
                result["ortho_scale"] = scale
                result["resolution"] = [width, height]
                result["png_sha256"] = {suffix: hashlib.sha256(
                    (HERE / f"{stem}{suffix}.png").read_bytes()).hexdigest()
                    for suffix in (("_silhouette", "_skin") if baseline else ("", "_silhouette", "_skin"))}
                results[stem] = result
                print("SKIN", stem, result, flush=True)
    report = {"export_sha256": hashlib.sha256(export.read_bytes()).hexdigest(), "views": results}
    filename = "round2_skin_check.json" if baseline else "skin_check.json"
    (HERE / filename).write_text(json.dumps(report, indent=2) + "\n")
    if not baseline:
        underside = [result for name, result in results.items() if name.endswith("_underside")]
        assert len(underside) == 4
        assert all(result["skin_pixels_inside_shoe_silhouette"] == 0 for result in underside)


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
    shoe = next(obj for obj in scene.objects if obj.type == "MESH")
    bpy.context.view_layer.update()
    evaluated = shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
    floor_z = min((evaluated.matrix_world @ v.co).z for v in evaluated.data.vertices)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, floor_z - 0.0006))
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
    if "--assets-only" in options or not options:
        build()
    if "--baseline-only" not in options:
        verify_asset_contract()
    if "--qa-only" in options or not options:
        run_supplied_checkers()
        verify_dense(*reimport_on_master())
        render_motion_detail(*reimport_on_master())
        render_preview()
    if "--checker-only" in options:
        run_supplied_checkers()
    if "--dense-only" in options:
        verify_dense(*reimport_on_master())
    if "--render-only" in options:
        render_motion_detail(*reimport_on_master())
        render_preview()
    if "--baseline-only" in options:
        baseline = HERE.parent / "round2" / "shoes_sneaker_v2.glb"
        render_motion_detail(*reimport_on_master(baseline), export=baseline, baseline=True)
