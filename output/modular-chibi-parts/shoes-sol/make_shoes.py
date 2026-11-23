"""Build a paired, skinned sneaker module from the local chibi master in Blender."""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
MASTER = HERE.parent / "master" / "GJH_Chibi_Master_rigged.blend"
MOTION = HERE.parents[2] / "models" / "tripo-chibi-motion" / "motion.glb"
NAME = "shoes_sneaker_v1"
EXPORT = HERE / f"{NAME}.glb"
CENTER_X = 0.085927
MIRROR_X = 0.000722
CENTER_Y = -0.008
SEGMENTS = 48
SOLE_HEIGHT = 0.018

# Rings run from the outsole tread edge to the rolled cuff and back down inside.
# fit_height holds the upper shape independent of the sole bevel.
PROFILE = (
    (0.004, 0.011, 0.0015),
    (0.004, 0.011, 0.0055),
    (0.010, 0.013, 0.0090),
    (SOLE_HEIGHT, SOLE_HEIGHT, 0.0090),
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


def posed_feet(body, arm):
    """Read evaluated body geometry and linear skinning matrices from the local clips."""
    scene = bpy.context.scene
    original_fps = scene.render.fps
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in list(scene.objects):
        if obj not in (arm, body):
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data_create()
    inverse = {
        name: arm.data.bones[name].matrix_local.inverted()
        for side in ("Left", "Right")
        for name in bone_names(side)
    }
    surfaces = {}
    polygons = [p.vertices[:] for p in body.data.polygons]
    for sign in (1, -1):
        surfaces[sign] = [
            v.index for v in body.data.vertices if v.co.x * sign > 0 and v.co.z < 0.145
        ]
    samples = {1: [], -1: []}
    actions = [None] + [bpy.data.actions[name] for name in ("walk", "run", "jump", "dance")]
    for act in actions:
        arm.animation_data.action = act
        if act:
            arm.animation_data.action_slot = act.slots[0]
        limits = (1, 1) if act is None else tuple(act.frame_range)
        check_floor = act is not None and act.name in ("walk", "run")
        steps = 4 if check_floor else 1
        for tick in range(steps * int(limits[0]), steps * int(limits[1]) + 1):
            frame, part = divmod(tick, steps)
            scene.frame_set(frame, subframe=part / steps)
            eval_body = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            if part == 0:
                coords = [eval_body.matrix_world @ v.co for v in eval_body.data.vertices]
                tree = BVHTree.FromPolygons(coords, polygons, all_triangles=True)
            else:
                tree = None
            for sign, side in ((1, "Left"), (-1, "Right")):
                matrices = tuple(arm.pose.bones[n].matrix @ inverse[n] for n in bone_names(side))
                floor = None
                if check_floor:
                    floor = min(0.0, min((eval_body.matrix_world @ eval_body.data.vertices[i].co).z
                                         for i in surfaces[sign]))
                samples[sign].append((tree, matrices, floor))
    arm.animation_data_clear()
    scene.frame_set(1)
    scene.render.fps = original_fps
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    return samples


def required_height(point, weights, samples):
    x, y, height = point
    for _, matrices, floor in samples:
        if floor is None:
            continue
        rows = [m[2] for m in matrices]
        baseline = sum(w * (r[0] * x + r[1] * y + r[3]) for r, w in zip(rows, weights))
        rise = sum(w * r[2] for r, w in zip(rows, weights))
        if rise > 0.01:
            height = max(height, (floor + 0.00017 - baseline) / rise)
    return height


def min_clearance(point, weights, samples):
    closest = math.inf
    for tree, matrices, _ in samples:
        if tree is None:
            continue
        posed = (matrices[0] @ point) * weights[0]
        for m, w in zip(matrices[1:], weights[1:]):
            if w:
                posed += (m @ point) * w
        loc, normal, _, _ = tree.find_nearest(posed)
        closest = min(closest, (posed - loc).dot(normal))
    return closest


def mirrored_points(angle, radius, z):
    x = CENTER_X + math.cos(angle) * radius
    y = CENTER_Y + math.sin(angle) * radius
    return {sign: Vector((MIRROR_X + sign * (x - MIRROR_X), y, z)) for sign in (1, -1)}


def pair_clearance(points, weights, samples):
    return min(min_clearance(p, weights[sign], samples[sign]) for sign, p in points.items())


def heel_cut(angle):
    return smoothstep(0.1, 0.90, math.sin(angle))


def cuff_clearance(angle, radius, lift, weights, samples):
    return min(
        pair_clearance(mirrored_points(angle, radius + allowance, height + lift), weights, samples)
        for height, _, allowance in PROFILE[10:]
    )


def cuff_profile(fit, samples, angles):
    """Use a shared sock-like leg blend and one offset for the rolled cuff."""
    samples = {sign: [frames[0], *(f for f in frames if f[2] is not None)]
               for sign, frames in samples.items()}
    radii, fractions = [], []
    for angle in angles:
        heel = heel_cut(angle)
        height = 0.096 - 0.021 * heel
        base_radius = fit.radius(height, Vector((math.cos(angle), math.sin(angle), 0)))
        base_radius += 0.0020 * (1 - heel)
        best_score = -math.inf
        best_fraction = None
        for leg in (0.42, 0.48, 0.54, 0.60, 0.66, 0.72, 0.76, 0.80, 0.84, 0.88):
            w = {sign: [1 - leg, 0, leg] for sign in samples}
            score = (cuff_clearance(angle, base_radius, height - 0.096, w, samples)
                     - abs(leg - (0.80 - 0.15 * heel)) * 0.005)
            if score > best_score:
                best_score, best_fraction = score, leg
        radii.append(base_radius)
        fractions.append(best_fraction)
    cuff = []
    for i, angle in enumerate(angles):
        leg = (0.25 * fractions[i - 1] + 0.50 * fractions[i]
               + 0.25 * fractions[(i + 1) % SEGMENTS])
        w = {sign: [1 - leg, 0, leg] for sign in samples}
        r = radii[i]
        heel = heel_cut(angle)
        lift = -0.021 * heel
        for _ in range(16):
            if cuff_clearance(angle, r, lift, w, samples) >= 0.0017:
                break
            r += 0.00055 * (1 - heel)
            lift += 0.00023 * (1 - 2 * heel)
        cuff.append((r, lift, w))
    return cuff


def instep_weights(point, weights, samples):
    """Tune the ankle transition against run flex before enlarging the shell."""
    foot, toe, leg = weights
    best = weights
    clearance = min_clearance(point, weights, samples)
    for change in (0.025, -0.025, 0.05, -0.05, 0.075, -0.075, 0.1, -0.1):
        if clearance >= 0.0015:
            break
        candidate = [foot - change, toe, leg + change]
        if min(candidate) < 0:
            continue
        distance = min_clearance(point, candidate, samples)
        if distance > clearance:
            best, clearance = candidate, distance
    return best


def build_pair(body, fit, samples):
    surfaces = {sign: FootSurface(body, sign, bone_names(side))
                for sign, side in ((1, "Left"), (-1, "Right"))}
    angles = [math.tau * i / SEGMENTS for i in range(SEGMENTS)]
    coords, weights = {1: [], -1: []}, {1: [], -1: []}
    cuff = cuff_profile(fit, samples, angles)
    rest = {sign: frames[:1] for sign, frames in samples.items()}
    for ring, (height, fit_height, allowance) in enumerate(PROFILE):
        if ring >= 10:
            for angle, (radius, lift, shared_weights) in zip(angles, cuff):
                for sign, p in mirrored_points(angle, radius + allowance, height + lift).items():
                    coords[sign].append(p)
                    weights[sign].append(shared_weights[sign])
            continue
        ring_radii, ring_heights, ring_weights = [], [], []
        for angle in angles:
            direction = Vector((math.cos(angle), math.sin(angle), 0))
            radius = fit.radius(fit_height, direction) + allowance
            if ring == 6:
                radius += 0.0017 * smoothstep(0.57, 0.89, -math.sin(angle))
            x = CENTER_X + direction.x * radius
            y = CENTER_Y + direction.y * radius
            z = height - {8: 0.005, 9: 0.014}.get(ring, 0.0) * heel_cut(angle)
            if ring == 6:
                # A raised vamp rib keeps the long toe-cap triangles above the toe surface.
                z += 0.0023 * smoothstep(0.63, 0.95, -math.sin(angle))
            if ring == 0:
                z = 0.004 * smoothstep(0.060, 0.11, -y) + 0.002 * smoothstep(0.046, 0.075, y)
            both_weights = {}
            for sign, surface in surfaces.items():
                p = Vector((MIRROR_X + sign * (x - MIRROR_X), y, z))
                w = surface.foot_weights(p)
                toe = smoothstep(0.084, 0.110, -y)
                w = [w[0] * (1 - toe), w[1] * (1 - toe) + toe, w[2] * (1 - toe)]
                both_weights[sign] = w
            ring_radii.append(radius)
            ring_heights.append(z)
            ring_weights.append(both_weights)
        # Limit local weight jumps across neighboring body triangles.
        ring_weights = [
            {
                sign: [
                    0.15 * ring_weights[(i - 1) % SEGMENTS][sign][j]
                    + 0.70 * ring_weights[i][sign][j]
                    + 0.15 * ring_weights[(i + 1) % SEGMENTS][sign][j]
                    for j in range(3)
                ]
                for sign in surfaces
            }
            for i in range(SEGMENTS)
        ]
        ring_radii = [
            0.16 * ring_radii[i - 1] + 0.68 * radius + 0.16 * ring_radii[(i + 1) % SEGMENTS]
            for i, radius in enumerate(ring_radii)
        ]
        for i, angle in enumerate(angles):
            radius = ring_radii[i]
            z = ring_heights[i]
            if 1 <= ring <= 4:
                z = max(z, coords[1][(ring - 1) * SEGMENTS + i].z + 0.0016)
            for _ in range(18):
                points = mirrored_points(angle, radius, z)
                z = max(required_height(p, ring_weights[i][sign], samples[sign]) for sign, p in points.items())
                for point in points.values():
                    point.z = z
                if ring == 9:
                    ring_weights[i] = {
                        sign: instep_weights(p, ring_weights[i][sign], samples[sign])
                        for sign, p in points.items()
                    }
                clearance = pair_clearance(points, ring_weights[i], samples)
                if ring >= 4:
                    clearance = min(clearance, pair_clearance(points, ring_weights[i], rest) - 0.00195)
                if clearance >= 0.00125:
                    break
                radius += max(0.0008, min(0.0025, 0.00125 - clearance))
                if ring >= 6 and math.sin(angle) < -0.25:
                    z += 0.0012
            for sign, point in points.items():
                coords[sign].append(point)
                weights[sign].append(ring_weights[i][sign])
    return coords, weights


def add_tread(coords, weights, body, samples):
    """Lay tread across the safe underside, with relief windows at foot contact."""
    surfaces = {sign: FootSurface(body, sign, bone_names(side))
                for sign, side in ((1, "Left"), (-1, "Right"))}
    rim_pairs = (
        (34, 36), (32, 38), (31, 41), (29, 43), (27, 45), (25, 47),
        (23, 1), (21, 3), (19, 5), (17, 7), (15, 9), (13, 11),
    )
    rows = []
    for inner, outer in rim_pairs:
        row = [inner]
        start, end = coords[1][inner], coords[1][outer]
        for col in range(1, 7):
            p = start.lerp(end, col / 7)
            row.append(None)
            for delta in (0.0, -0.0030, 0.0030):
                points = {sign: Vector((MIRROR_X + sign * (p.x - MIRROR_X), p.y + delta, 0))
                          for sign in coords}
                w = {sign: surfaces[sign].foot_weights(point) for sign, point in points.items()}
                height = max(required_height(point, w[sign], samples[sign])
                             for sign, point in points.items())
                for point in points.values():
                    point.z = height
                if pair_clearance(points, w, samples) < 0.00068:
                    continue
                row[-1] = len(coords[1])
                for sign, point in points.items():
                    coords[sign].append(point)
                    weights[sign].append(w[sign])
                break
        rows.append([*row, outer])
    faces = []
    for row, next_row in zip(rows, rows[1:]):
        for a, b, c, d in zip(row, row[1:], next_row[1:], next_row):
            if a is None or c is None:
                if b is not None and d is not None:
                    if a is not None:
                        faces.append((a, d, b))
                    if c is not None:
                        faces.append((b, d, c))
                continue
            if b is not None:
                faces.append((a, c, b))
            if d is not None:
                faces.append((a, d, c))
    return faces


def add_laces(coords, weights, faces, face_materials):
    """Drape two shallow ivory lace strips on the vamp with its local skinning."""
    tree = BVHTree.FromPolygons(coords, faces, all_triangles=True)
    for y in (-0.076, -0.062):
        start = len(coords)
        for i in range(9):
            u = (i - 4) / 4
            x = CENTER_X + 0.033 * u
            for j in range(3):
                dy = (j - 1) * (0.0044 - 0.0010 * u ** 6)
                origin = Vector((x, y + dy + 0.0045 * u * u, 0.15))
                hit, _, face, _ = tree.ray_cast(origin, Vector((0, 0, -1)), 0.15)
                w = blend_weights(hit, faces[face], coords, weights)
                lift = (0.0012 if j == 1 else 0.00055) + 0.0012 * (1 - u * u)
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


def build_left(coords, weights, tread_faces):
    angles = [math.tau * i / SEGMENTS for i in range(SEGMENTS)]
    faces, face_materials = [], []
    for band in range(len(PROFILE) - 1):
        for i, angle in enumerate(angles):
            a = band * SEGMENTS + i
            b = band * SEGMENTS + (i + 1) % SEGMENTS
            c, d = b + SEGMENTS, a + SEGMENTS
            faces.extend(((a, b, c), (a, c, d)))
            face_materials.extend([paint_band(band, angle + math.pi / SEGMENTS)] * 2)
    faces.extend(tread_faces)
    face_materials.extend([2] * len(tread_faces))
    add_laces(coords, weights, faces, face_materials)
    add_star(coords, weights, faces, face_materials)
    return coords, faces, face_materials, weights, bone_names("Left")


def build():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    body = scene.objects["Base_Body"]
    arm = scene.objects["Armature"]
    assert len(arm.data.bones) == 65
    assert all(p.rotation_mode == "QUATERNION" for p in arm.pose.bones)
    assert arm.animation_data is None
    materials = [
        material("Purple upper", (0.17, 0.031, 0.49), 0.37),
        material("Ivory rubber", (0.88, 0.86, 0.95), 0.43),
        material("Deep purple tread", (0.12, 0.028, 0.31), 0.52),
        material("Purple lining", (0.085, 0.032, 0.23), 0.57),
        material("Purple collar piping", (0.35, 0.14, 0.65), 0.42),
    ]
    fit = FootSurface(body, 1, bone_names("Left"))
    samples = posed_feet(body, arm)
    pair_coords, pair_weights = build_pair(body, fit, samples)
    tread_faces = add_tread(pair_coords, pair_weights, body, samples)
    left = build_left(pair_coords[1], pair_weights[1], tread_faces)
    original_mesh_size = len(pair_coords[-1])
    pair_coords[-1].extend(Vector((2 * MIRROR_X - p.x, p.y, p.z)) for p in left[0][original_mesh_size:])
    pair_weights[-1].extend(left[3][original_mesh_size:])
    right_faces = [f[::-1] for f in left[1]]
    right = pair_coords[-1], right_faces, left[2], pair_weights[-1], bone_names("Right")
    verts, faces, face_materials, group_sets = [], [], [], []
    for coords, local_faces, local_mats, weights, names in (left, right):
        offset = len(verts)
        verts.extend(coords)
        faces.extend(tuple(offset + i for i in f) for f in local_faces)
        face_materials.extend(local_mats)
        group_sets.append((offset, weights, names))

    mesh = bpy.data.meshes.new("Sneaker pair")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    shoes = bpy.data.objects.new("Sneaker_Pair", mesh)
    scene.collection.objects.link(shoes)
    for mat in materials:
        mesh.materials.append(mat)
    for poly, mat_index in zip(mesh.polygons, face_materials):
        poly.use_smooth = True
        poly.material_index = mat_index
    for offset, weights, names in group_sets:
        groups = [shoes.vertex_groups.new(name=n) for n in names]
        for i, values in enumerate(weights, start=offset):
            for group, weight in zip(groups, values):
                if weight > 1e-6:
                    group.add([i], weight, "REPLACE")
    shoes.parent = arm
    modifier = shoes.modifiers.new("Armature", "ARMATURE")
    modifier.object = arm
    bpy.data.objects.remove(body, do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.object.select_all(action="DESELECT")
    shoes.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = shoes
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"{NAME}.blend"))
    bpy.ops.export_scene.gltf(
        filepath=str(EXPORT),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=False,
        export_skins=True,
        export_def_bones=False,
        export_armature_object_remove=True,
        export_all_influences=False,
        export_materials="EXPORT",
    )


def run_motion_checker():
    """Use the supplied checker with CPU rendering on a headless macOS host."""
    checker = HERE / "motion_check.py"
    workbench = (
        "sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
        "sc.display.shading.color_type='MATERIAL'"
    )
    cpu_setup = """
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 12
sc.cycles.use_denoising = False
sc.world = bpy.data.worlds.new('Checker studio')
sc.world.use_nodes = True
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.86, .89, .96, 1)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
"""
    source = checker.read_text()
    if workbench not in source:
        raise ValueError("The supplied checker rendering block changed")
    original_argv = sys.argv
    sys.argv = [*sys.argv[:1], "--", str(MASTER), str(MOTION), str(EXPORT), str(HERE)]
    try:
        exec(compile(source.replace(workbench, cpu_setup, 1), str(checker), "exec"),
             {"__name__": "__main__"})
    finally:
        sys.argv = original_argv


def verify_floor():
    """Measure per-foot floor clearance from the exported and reimported mesh."""
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    body, arm = (scene.objects[name] for name in ("Base_Body", "Armature"))
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(EXPORT))
    imported = [o for o in bpy.data.objects if o.name not in before]
    shoes = bpy.data.objects["Sneaker_Pair"]
    matrix = shoes.matrix_world.copy()
    shoes.parent = arm
    shoes.matrix_world = matrix
    for modifier in list(shoes.modifiers):
        shoes.modifiers.remove(modifier)
    shoes.modifiers.new("Master skin", "ARMATURE").object = arm
    for obj in imported:
        if obj != shoes:
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in scene.objects:
        if obj not in (arm, body, shoes):
            obj.hide_viewport = True

    foot_indices = {
        sign: [v.index for v in body.data.vertices if v.co.x * sign > 0 and v.co.z < 0.145]
        for sign in (1, -1)
    }
    shoe_indices = {
        sign: [v.index for v in shoes.data.vertices if (matrix @ v.co).x * sign > 0]
        for sign in (1, -1)
    }
    arm.animation_data_create()
    for name in ("walk", "run"):
        action = bpy.data.actions[name]
        arm.animation_data.action = action
        arm.animation_data.action_slot = action.slots[0]
        start, end = (int(f) for f in action.frame_range)
        worst = {1: (math.inf, 0, 0, 0), -1: (math.inf, 0, 0, 0)}
        for tick in range(4 * start, 4 * end + 1):
            frame, quarter = divmod(tick, 4)
            scene.frame_set(frame, subframe=quarter / 4)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            posed_body, posed_shoes = (o.evaluated_get(depsgraph) for o in (body, shoes))
            for sign in (1, -1):
                shoe_z = min((posed_shoes.matrix_world @ posed_shoes.data.vertices[i].co).z
                             for i in shoe_indices[sign])
                body_z = min((posed_body.matrix_world @ posed_body.data.vertices[i].co).z
                             for i in foot_indices[sign])
                worst[sign] = min(worst[sign], (shoe_z - min(0, body_z), tick / 4, shoe_z, body_z))
        for sign, side in ((1, "Left"), (-1, "Right")):
            margin, frame, shoe_z, body_z = worst[sign]
            print(f"FLOOR {name} {side} frames {start}–{end} margin {margin:.8f} "
                  f"at frame {frame} shoe_z {shoe_z:.8f} body_z {body_z:.8f}")
            if margin < -1e-6:
                raise ValueError(f"Floor clearance regressed for {name} {side}")


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
    if "--assets-only" not in options:
        run_motion_checker()
        verify_floor()
        render_preview()
