"""Fit the supplied Tripo sandals to the master rig in Blender 5.1.

Run with the guarded Blender executable and --python fit_shoes.py.
The master, motion, reference and Tripo GLB are read-only inputs.
"""

import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
MASTER = HERE.parents[1] / "master/GJH_Chibi_Master_rigged.blend"
MOTION = HERE.parents[3] / "models/tripo-chibi-motion/motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
REFERENCE = HERE.parents[1] / "white-bg/shoes-09-purple-sandals.png"
EXPORT = HERE / "shoes_sandals_v1.glb"
BLEND = EXPORT.with_suffix(".blend")
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
PARTS = ("Foot", "ToeBase", "Leg")
SIDES = ("Left", "Right")
FIT_MARGIN = 0.0016
QA_MARGIN = 0.0005


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(name, content):
    (HERE / f"{name}.json").write_text(json.dumps(content, indent=2) + "\n")


def bone_names(side):
    return [f"mixamorig:{side}{part}" for part in PARTS]


def set_action(armature, scene, action):
    armature.animation_data_create()
    armature.animation_data.action = action
    if action is not None:
        armature.animation_data.action_slot = action.slots[0]
    else:
        for bone in armature.pose.bones:
            bone.matrix_basis.identity()
        scene.frame_set(1)


def import_motion(scene):
    existing = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in set(scene.objects) - existing:
        bpy.data.objects.remove(obj, do_unlink=True)
    return [bpy.data.actions[name] for name in CLIPS]


def motion_samples(action):
    if action is None:
        return [(1, 0.0)]
    first, last = map(int, action.frame_range)
    steps = 4 if action.name in ("walk", "run") else 1
    return [(i // steps, i % steps / steps) for i in range(first * steps, last * steps + 1)]


def smoothstep(start, end, value):
    t = np.clip((value - start) / (end - start), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def convex_hull(points):
    vectors = [Vector(p) for p in points]
    return np.asarray([vectors[i][:] for i in geometry.convex_hull_2d(vectors)])


def cross_section(hull, y):
    y = np.clip(y, hull[:, 1].min() + 1e-5, hull[:, 1].max() - 1e-5)
    end = np.roll(hull, -1, axis=0)
    active = (y >= np.minimum(hull[:, 1], end[:, 1])) & (y <= np.maximum(hull[:, 1], end[:, 1]))
    a, b = hull[active], end[active]
    good = abs(b[:, 1] - a[:, 1]) > 1e-9
    a, b = a[good], b[good]
    x = a[:, 0] + (b[:, 0] - a[:, 0]) * (y - a[:, 1]) / (b[:, 1] - a[:, 1])
    return x.min(), x.max()


def footprint_overhang(foot, shoe):
    signed_distances = []
    for a, b in zip(shoe, np.roll(shoe, -1, axis=0)):
        edge = b - a
        inward = np.array([-edge[1], edge[0]]) / np.linalg.norm(edge)
        if np.dot(shoe.mean(0) - a, inward) < 0:
            inward *= -1
        signed_distances.extend((foot - a) @ inward)
    return float(min(signed_distances))


def outside_footprint(points, hull):
    edges = np.roll(hull, -1, axis=0) - hull
    out = np.column_stack((edges[:, 1], -edges[:, 0]))
    out /= np.linalg.norm(out, axis=1)[:, None]
    inward = np.sum((hull.mean(0) - hull) * out, axis=1) > 0
    out[inward] *= -1
    return ((points[:, None] - hull) * out).sum(2).max(1)


def close_source(mesh):
    """Close the seven-edge pinhole, retaining the atlas loops on every source face."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    openings = [e for e in bm.edges if e.is_boundary]
    assert len(openings) == 7, f"Unexpected Tripo boundary: {len(openings)}"
    uv = bm.loops.layers.uv.active
    neighbors = {
        (v, edge.link_faces[0]): next(loop[uv].uv.copy()
                                     for loop in edge.link_faces[0].loops if loop.vert == v)
        for edge in openings for v in edge.verts
    }
    fill = bmesh.ops.holes_fill(bm, edges=openings, sides=7)["faces"]
    assert len(fill) == 1
    for loop in fill[0].loops:
        # Choose a source UV island that borders this patch. Existing loops stay unchanged.
        candidates = [coord for (v, _), coord in neighbors.items() if v == loop.vert]
        loop[uv].uv = candidates[0]
    fill[0].smooth = True
    bmesh.ops.triangulate(bm, faces=fill, ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(e.is_manifold and e.is_contiguous for e in bm.edges)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


class FootSurface:
    def __init__(self, body, side, sign):
        self.points = [v.co.copy() for v in body.data.vertices]
        self.tris = [
            p.vertices[:] for p in body.data.polygons
            if all(self.points[i].x * sign > 0 and self.points[i].z < 0.155 for i in p.vertices)
        ]
        self.tree = BVHTree.FromPolygons(self.points, self.tris, all_triangles=True)
        self.footprint = convex_hull([p[:2] for p in self.points if p.x * sign > 0 and p.z < 0.09])
        groups = [body.vertex_groups[name].index for name in bone_names(side)]
        self.weights = np.zeros((len(self.points), len(groups)))
        for v in body.data.vertices:
            for group in v.groups:
                if group.group in groups:
                    self.weights[v.index, groups.index(group.group)] = group.weight

    def local_weights(self, point, plantar):
        p = Vector(point)
        if plantar:
            hit, _, face, _ = self.tree.ray_cast(Vector((*p[:2], -0.14)), Vector((0, 0, 1)), 0.20)
            if hit is None:
                # Clamp edge samples near the support surface, including the rounded toe.
                p.z = 0.008
                hit, _, face, _ = self.tree.find_nearest(p)
        else:
            hit, _, face, _ = self.tree.find_nearest(p)
        ids = self.tris[face]
        factors = geometry.barycentric_transform(
            hit, *(self.points[i] for i in ids), Vector((1, 0, 0)),
            Vector((0, 1, 0)), Vector((0, 0, 1))
        )
        values = np.maximum(np.asarray(factors) @ self.weights[list(ids)], 0)
        return values / values.sum() if values.sum() else [1, 0, 0]


def match_sole_projection(source, faces, footprint):
    """Map the actual tread silhouette, including its concave waist."""
    sole = source[:, 2] <= 0.153
    source_min, source_max = source[sole, :2].min(0), source[sole, :2].max(0)
    source_center = 0.5 * (source_min + source_max)
    foot_center = 0.5 * (footprint.min(0) + footprint.max(0))
    base_scale = np.ptp(footprint, axis=0) / (source_max - source_min)
    local = (source[:, :2] - source_center) * base_scale
    coords = np.column_stack((local, source[:, 2]))
    sole_tree = BVHTree.FromPolygons(coords.tolist(), [f for f in faces if all(sole[i] for i in f)],
                                    all_triangles=True)
    angles = np.arange(32) * math.tau / 32
    circle = np.column_stack((np.cos(angles), np.sin(angles)))
    offset = np.column_stack((0.0078 * circle[:, 0],
                              (0.0082 + 0.0040 * smoothstep(0.05, 0.8, circle[:, 1])) * circle[:, 1]))
    border = convex_hull((footprint[:, None] + offset).reshape(-1, 2))
    centered = border - foot_center
    edges = np.roll(centered, -1, axis=0) - centered
    radii = []
    for angle in np.linspace(-math.pi, math.pi, 481):
        ray = np.array((math.cos(angle), math.sin(angle)))
        low, high = 0.0, 0.15
        for _ in range(16):
            radius = 0.5 * (low + high)
            x, y = ray * radius
            hit, _, _, _ = sole_tree.ray_cast(Vector((x, y, -0.10)), Vector((0, 0, 1)), 0.30)
            if hit is None:
                high = radius
            else:
                low = radius
        across = edges[:, 1] * ray[0] - edges[:, 0] * ray[1]
        valid = abs(across) > 1e-10
        t = -(centered[:, 1] * ray[0] - centered[:, 0] * ray[1])[valid] / across[valid]
        crossing = centered[valid] + edges[valid] * t[:, None]
        target = (crossing @ ray)[(t >= 0) & (t <= 1)].max()
        # A wider heel shoulder covers the plantar pad when the heel is
        # exposed at the deepest ankle flex in the run clip.
        target += 0.0048 * smoothstep(0.12, 0.69, ray[1])
        radii.append(target / max(low, 0.030))
    theta = np.arctan2(local[:, 1], local[:, 0])
    # Sampling the actual rim can reveal small local tread notches. Keep their
    # inverse correction smooth to preserve the original strap topology.
    values = np.asarray(radii[:-1])
    values = 0.52 * values + 0.24 * (np.roll(values, 1) + np.roll(values, -1))
    scale = np.interp(theta, np.linspace(-math.pi, math.pi, len(radii)), np.r_[values, values[0]])
    mapped = foot_center + local * scale[:, None]
    return mapped, border, foot_center, source_min[1], source_max[1]


def initial_fit(source, surface, faces):
    mapped, border, center, source_min, source_max = match_sole_projection(source, faces, surface.footprint)
    target_min, target_max = border[:, 1].min(), border[:, 1].max()
    xx, y0 = mapped.T.copy()
    x, y, z = source.T
    sole = z <= 0.153
    source_outline = convex_hull(source[sole, :2])
    # Preserve the original transverse section of the upper. The radial
    # correction at the sole fades out before the widest strap and buckle.
    for i in np.flatnonzero(~sole):
        y_upper = np.interp(y[i], (source_min, source_max), (target_min, target_max))
        a, b = cross_section(source_outline, y[i])
        c, d = cross_section(border, y_upper)
        ratio = 0.5 + (x[i] - 0.5 * (a + b)) / max(0.055, b - a)
        blend = smoothstep(0.153, 0.243, z[i])
        xx[i] = (1 - blend) * xx[i] + blend * (c + ratio * (d - c))
        y0[i] = (1 - blend) * y0[i] + blend * y_upper
    # Keep the instep ahead of the ankle and the heel loop behind the Achilles.
    upper = smoothstep(0.152, 0.26, z)
    upper_y = np.interp(y, (source_min, -0.32, -0.135, -0.08, 0.10, 0.17, 0.25, 0.36, source_max),
                        (target_min, -0.097, -0.065, -0.061, -0.048, 0.004, 0.053, target_max - 0.005, target_max))
    yy = (1 - upper) * y0 + upper * upper_y
    slope = 0.365 + 0.036 * smoothstep(-0.15, 0.0, y)
    zz = np.where(sole, -0.013 + 0.009 * np.clip((z - 0.010) / 0.143, 0, 1),
                  -0.004 + slope * (z - 0.153))
    relative = np.clip((xx - center[0]) / 0.053, -1, 1)
    side = smoothstep(0.35, 0.93, abs(relative))
    forefoot = 1 - smoothstep(-0.145, -0.069, y)
    flare = smoothstep(0.137, 0.216, z)
    xx += flare * (0.010 + 0.0045 * forefoot) * side * np.sign(relative)
    zz += flare * forefoot * (0.0165 + 0.010 * smoothstep(-0.32, -0.14, y))
    yy += flare * 0.006 * smoothstep(0.16, 0.31, y)
    # A raised outer welt occludes the plantar edge from a grazing side view.
    # The interior bed remains recessed below the skin and thickens to the rim.
    edge = outside_footprint(np.column_stack((xx, yy)), surface.footprint)
    zz += (0.014 * smoothstep(0.002, 0.0072, edge) * smoothstep(0.056, 0.126, z)
           * (1 - smoothstep(0.150, 0.263, z)))
    sign = 1 if source[0, 0] > 0 else -1
    medial = xx * sign
    low = medial.min()
    if low < 0.006:
        narrow = medial < 0.020
        medial[narrow] = 0.006 + (medial[narrow] - low) * 0.014 / (0.020 - low)
        xx = medial * sign
    p = np.column_stack((xx, yy, zz))
    # Project skinning to the foot surface. The underside and footbed use
    # matching plantar weights at the same XY, independent of their depth.
    weights = np.asarray([surface.local_weights(point, bool(base)) for point, base in zip(p, sole)])
    front = smoothstep(-0.15, -0.027, y)
    heelwards = smoothstep(0.165, 0.34, y)
    # Constraints use the direction of each physical surface, so a failing
    # triangle in the sole cannot be pushed up through the foot.
    direction = np.column_stack((np.sign(relative) * side,
                                 (1 - side * 0.6) * (heelwards - front),
                                 (1 - side) * (1 - 0.75 * np.maximum(front, heelwards))))
    direction[sole] = (0, 0, -1)
    direction /= np.linalg.norm(direction, axis=1).clip(1e-12)[:, None]
    return p, weights, direction, sole


class MotionCache:
    def __init__(self, scene, arm, body, actions):
        body_faces = [p.vertices[:] for p in body.data.polygons]
        rest = np.array([v.co[:] for v in body.data.vertices])
        self.patches = {}
        for sign in (1, -1):
            ids = np.flatnonzero((rest[:, 0] * sign > 0) & (rest[:, 2] < 0.168))
            local = {int(v): i for i, v in enumerate(ids)}
            faces = [tuple(local[i] for i in f) for f in body_faces if all(i in local for i in f)]
            self.patches[sign] = (ids, faces)
        names = [n for side in SIDES for n in bone_names(side)]
        inverse = [arm.data.bones[n].matrix_local.inverted() for n in names]
        self.keys = []
        trees = {1: [], -1: []}
        self.bounds = {1: [], -1: []}
        self.world = {1: [], -1: []}
        self.matrices = []
        for action in [None, *actions]:
            set_action(arm, scene, action)
            for frame, subframe in motion_samples(action):
                scene.frame_set(frame, subframe=subframe)
                obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
                coords = np.empty(len(rest) * 3, dtype=np.float32)
                obj.data.vertices.foreach_get("co", coords)
                coords = coords.reshape(-1, 3)
                for sign, (ids, faces) in self.patches.items():
                    patch = coords[ids]
                    trees[sign].append(BVHTree.FromPolygons(patch.tolist(), faces, all_triangles=True))
                    self.bounds[sign].append((patch.min(0), patch.max(0)))
                    self.world[sign].append(patch)
                self.keys.append((action.name if action else "rest", frame + subframe))
                self.matrices.append([arm.pose.bones[n].matrix @ inv for n, inv in zip(names, inverse)])
        self.matrices = np.asarray(self.matrices, dtype=np.float32)[:, :, :3, :]
        self.trees = trees
        set_action(arm, scene, None)


def smooth_weights(mesh, ids, weights, sole):
    adjacent = [[] for i in ids]
    index = {v: k for k, v in enumerate(ids)}
    for e in mesh.edges:
        a, b = e.vertices
        if a in index and b in index:
            a, b = index[a], index[b]
            if sole[a] == sole[b]:
                adjacent[a].append(b)
                adjacent[b].append(a)
    for _ in range(2):
        weights = np.asarray([0.72 * w + 0.28 * weights[near].mean(0) if near and not sole[i] else w
                              for i, (w, near) in enumerate(zip(weights, adjacent))])
    weights[weights < 0.0001] = 0
    return weights / weights.sum(1)[:, None]


def intersection_samples(shoe, body):
    """Locate edge hits precisely when regular triangle samples miss a contact."""
    upper = [Vector(p) for p in shoe]
    obstacle = [Vector(p) for p in body]
    barycentric_basis = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    for triangle, other in ((upper, obstacle), (obstacle, upper)):
        for i, origin in enumerate(triangle):
            edge = triangle[(i + 1) % 3] - origin
            hit = geometry.intersect_ray_tri(*other, edge, origin, True)
            if hit is None or (hit - origin).dot(edge) < -1e-8 or (hit - origin).length > edge.length + 1e-6:
                continue
            yield tuple(geometry.barycentric_transform(hit, *upper, *barycentric_basis))


def scan_fit(coords, skin, cache, sign, faces, directions, sole, rows):
    posed = np.einsum("fvij,vj->fvi", skin[..., :3], coords) + skin[..., 3]
    required = np.zeros(len(coords))
    minimum, max_inside, max_pairs = math.inf, 0, 0
    outer_rows = []
    free = np.zeros_like(coords)
    for f in rows:
        tree, frame_points = cache.trees[sign][f], posed[f]
        lo, hi = cache.bounds[-sign][f]
        cross = (np.all(frame_points.min(0) < hi + 0.002)
                 and np.all(lo < frame_points.max(0) + 0.002))
        other = cache.trees[-sign][f] if cross else None
        inside, worst = 0, math.inf
        for i, xyz in enumerate(frame_points):
            point = Vector(xyz)
            hit, normal, _, _ = tree.find_nearest(point)
            signed = (point - hit).dot(normal)
            foreign = False
            if other and np.all(xyz > lo - 0.002) and np.all(xyz < hi + 0.002):
                q, n, _, _ = other.find_nearest(point, 0.018)
                if q is not None and (point - q).dot(n) < signed:
                    signed, normal = (point - q).dot(n), n
                    foreign = True
            inside += signed < 0
            worst = min(worst, signed)
            if signed < FIT_MARGIN:
                sensitivity = normal.dot(Vector(skin[f, i, :, :3] @ directions[i]))
                if sensitivity > 0.18:
                    required[i] = max(required[i], (FIT_MARGIN - signed) / sensitivity)
                elif not sole[i] or foreign:
                    candidate = skin[f, i, :, :3].T @ np.asarray(normal) * (FIT_MARGIN - signed)
                    if np.linalg.norm(candidate) > np.linalg.norm(free[i]):
                        free[i] = candidate
        shell = BVHTree.FromPolygons(frame_points.tolist(), faces, all_triangles=True)
        pairs = sorted((face, 0, body_face) for body_face, face in tree.overlap(shell))
        if other:
            pairs.extend(sorted((face, 1, body_face) for body_face, face in other.overlap(shell)))
        if pairs:
            # Triangle interior samples retain coarse retopology across the
            # ball. The barycentric sensitivity distributes their correction.
            overlapped = {}
            for face, cross, body_face in pairs:
                overlapped.setdefault((face, cross), []).append(body_face)
            for (face, cross), body_faces in overlapped.items():
                ids = np.asarray(faces[face])
                tri = frame_points[ids]
                obstacles = other if cross else tree
                samples = [(1/3, 1/3, 1/3), (0.5, 0.5, 0), (0, 0.5, 0.5), (0.5, 0, 0.5),
                           (0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6)]
                if len(pairs) <= 46:
                    obstacle_side = -sign if cross else sign
                    polygons = cache.patches[obstacle_side][1]
                    obstacle_points = cache.world[obstacle_side][f]
                    for index in body_faces:
                        samples.extend(intersection_samples(tri, obstacle_points[list(polygons[index])]))
                derivatives = np.einsum("nij,nj->ni", skin[f, ids, :, :3], directions[ids])
                for sample in samples:
                    bary = np.asarray(sample)
                    point = Vector(bary @ tri)
                    hit, normal, _, _ = obstacles.find_nearest(point)
                    signed = (point - hit).dot(normal)
                    sensitivity = derivatives @ np.asarray(normal)
                    if signed < FIT_MARGIN:
                        average = bary @ np.maximum(sensitivity, 0)
                        if average > 0.20 and not (any(sole[ids]) and not all(sole[ids])):
                            good = (sensitivity > 0.15) & (bary > 0)
                            required[ids[good]] = np.maximum(required[ids[good]], (FIT_MARGIN - signed) / average)
                        else:
                            for i in ids[(bary > 0.15) & (~sole[ids] | bool(cross))]:
                                index = int(np.where(ids == i)[0][0])
                                projected = sensitivity[index]
                                candidate = (directions[i] * (FIT_MARGIN - signed) / max(projected, 0.3)
                                             if projected > 0.23 else
                                             skin[f, i, :, :3].T @ np.asarray(normal) * (FIT_MARGIN - signed))
                                if np.linalg.norm(candidate) > np.linalg.norm(free[i]):
                                    free[i] = candidate
        if inside or pairs or worst < QA_MARGIN:
            outer_rows.append((f, inside, len(pairs), worst))
        max_inside, max_pairs, minimum = max(max_inside, inside), max(max_pairs, len(pairs)), min(minimum, worst)
    directional = directions * required[:, None]
    use_free = np.linalg.norm(free, axis=1) > 0.5 * required
    directional[use_free] += free[use_free]
    return directional, (max_inside, max_pairs, minimum), outer_rows


def bake_fit(coords, weights, dirs, sole, faces, cache, sign, side):
    block = slice(0, 3) if sign == 1 else slice(3, 6)
    skin = np.einsum("fbci,nb->fnci", cache.matrices[:, block], weights).astype(np.float32)
    original = coords.copy()
    history = []
    all_rows = list(range(len(cache.keys)))
    coarse = sorted({0, *range(1, len(cache.keys), 21), *(
        i for i, key in enumerate(cache.keys)
        if key in (("walk", 19), ("walk", 23), ("walk", 51), ("run", 4), ("run", 12))
    )})
    # Spread corrections in space across both sides of thin straps. Topology
    # alone would pull the interior through the exterior on these UV islands.
    delta = original[:, None, :] - original[None, :, :]
    delta[..., 2] *= np.where(sole[:, None] & sole[None, :], 0.0, 0.80)
    window = np.where(sole[:, None], 0.0105, 0.0155)
    kernel = np.exp(-np.square(delta).sum(2) / np.square(window))
    kernel[sole[:, None] != sole[None, :]] = 0
    for attempt in range(12):
        rows = coarse if attempt < 4 else all_rows
        step, summary, residuals = scan_fit(coords, skin, cache, sign, faces, dirs, sole, rows)
        history.append({"samples": len(rows), "max_vertices_inside": summary[0],
                        "max_overlap_pairs": summary[1], "min_signed_distance_m": summary[2]})
        print("BAKE", side, attempt, len(rows), summary, "remaining", len(residuals), flush=True)
        lengths = np.linalg.norm(step, axis=1)
        if attempt >= 4 and (summary[0] == summary[1] == 0 and summary[2] >= QA_MARGIN
                             or not np.any(lengths > 0.00001)):
            break
        step *= np.minimum(1, 0.0065 / lengths.clip(1e-9))[:, None]
        spread = np.column_stack([
            (kernel * values.clip(0)).max(1) + (kernel * values.clip(max=0)).min(1)
            for values in step.T
        ])
        coords += np.where(sole[:, None], 0.18 * step + 0.94 * spread, 1.085 * spread)
    if residuals:
        worst = sorted(residuals, key=lambda r: (r[-1], -r[2]))[:5]
        print("RESIDUAL", side, [(cache.keys[f], i, p, d) for f, i, p, d in worst], flush=True)
    return coords, {"passes": history, "max_displacement_m": float(np.linalg.norm(coords - original, axis=1).max())}


def resize_texture_images(material, folder):
    nodes = material.node_tree.nodes
    images = {node.image for node in nodes if node.type == "TEX_IMAGE" and node.image}
    for original in sorted(images, key=lambda image: image.name):
        ratio = min(1.0, 1024 / max(original.size))
        if ratio == 1:
            continue
        color_space = original.colorspace_settings.name
        image_size = tuple(round(n * ratio) for n in original.size)
        image = original.copy()
        image.scale(*image_size)
        suffix = ".jpg" if original.file_format == "JPEG" and color_space == "sRGB" else ".png"
        image.file_format = "JPEG" if suffix == ".jpg" else "PNG"
        target = folder / (Path(original.name).stem + suffix)
        image.save(filepath=str(target))
        replacement = bpy.data.images.load(str(target), check_existing=False)
        replacement.colorspace_settings.name = color_space
        replacement.name = target.name
        replacement.pack()
        replacement.filepath = "//" + target.name
        for node in nodes:
            if node.type == "TEX_IMAGE" and node.image == original:
                node.image = replacement
        bpy.data.images.remove(image)


def stabilize_tangents(mesh):
    """Keep UVs intact when a folded smooth corner gives a zero MikkTSpace tangent."""
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    bad = [p.index for p in mesh.polygons if any(mesh.loops[i].tangent.length < 0.8 for i in p.loop_indices)]
    mesh.free_tangents()
    for i in bad:
        mesh.polygons[i].use_smooth = False
    mesh.update()
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    assert min(loop.tangent.length for loop in mesh.loops) > 0.8
    mesh.free_tangents()
    return bad


def subdivide_fold_prone_edges(mesh, body):
    """Add samples to coarse triangles where the smooth fitting map bends most."""
    original = np.asarray([v.co[:] for v in mesh.vertices])
    polygons = [p.vertices[:] for p in mesh.polygons]
    score = {}
    for sign, side in ((1, "Left"), (-1, "Right")):
        ids = np.flatnonzero(original[:, 0] * sign > 0).tolist()
        lookup = {v: i for i, v in enumerate(ids)}
        faces = [tuple(lookup[v] for v in f) for f in polygons if f[0] in lookup]
        points = initial_fit(original[ids], FootSurface(body, side, sign), faces)[0]
        tree = BVHTree.FromPolygons(points.tolist(), faces, all_triangles=True)
        counts = np.zeros(len(faces), dtype=int)
        for i, j in tree.overlap(tree):
            if i < j and not set(faces[i]).intersection(faces[j]):
                counts[i] += 1
                counts[j] += 1
        for f, burden in zip(faces, counts):
            for a, b in zip(f, (f[1], f[2], f[0])):
                key = tuple(sorted((ids[a], ids[b])))
                length = np.linalg.norm(points[a] - points[b])
                if length > 0.011:
                    score[key] = max(score.get(key, 0), length * (1 + int(burden)) ** 0.62)
    budget = min(236, (3500 - len(polygons)) // 2)
    chosen = set(sorted(score, key=lambda e: (-score[e], e))[:budget])
    bm = bmesh.new()
    bm.from_mesh(mesh)
    edges = [e for e in bm.edges if tuple(sorted(v.index for v in e.verts)) in chosen]
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    assert all(e.is_manifold and e.is_contiguous for e in bm.edges)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(chosen)


def build():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    actions = import_motion(scene)
    cache = MotionCache(scene, arm, body, actions)
    existing = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE), merge_vertices=True)
    imported = set(scene.objects) - existing
    shoes, = (obj for obj in imported if obj.type == "MESH")
    shoes.parent = None
    for obj in imported - {shoes}:
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = shoes.data
    # Topology changes invalidate Tripo's split vertex normals. Regenerate
    # geometric normals, retaining tangents through the original UV atlas.
    if mesh.has_custom_normals:
        bpy.context.view_layer.objects.active = shoes
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    close_source(mesh)
    subdivided_edges = subdivide_fold_prone_edges(mesh, body)
    xyz = np.array([v.co[:] for v in mesh.vertices])
    face_indices = [p.vertices[:] for p in mesh.polygons]
    assert all(len(p) == 3 and len({xyz[v, 0] > 0 for v in p}) == 1 for p in face_indices)
    history, widths = {}, {}
    sole_face_ids = []
    for side, sign in zip(SIDES, (1, -1)):
        ids = np.flatnonzero(sign * xyz[:, 0] > 0).tolist()
        index = {v: i for i, v in enumerate(ids)}
        faces = [tuple(index[i] for i in f) for f in face_indices if f[0] in index]
        surface = FootSurface(body, side, sign)
        p, w, direction, sole = initial_fit(xyz[ids], surface, faces)
        w = smooth_weights(mesh, ids, w, sole)
        p, history[side] = bake_fit(p, w, direction, sole, faces, cache, sign, side)
        sole_face_ids.extend(i for i, f in enumerate(face_indices) if f[0] in index
                             and all(sole[index[v]] for v in f))
        for i, point in zip(ids, p):
            mesh.vertices[i].co = point
        for joint, values in zip(bone_names(side), w.T):
            group = shoes.vertex_groups.new(name=joint)
            for i, value in zip(ids, values):
                if value > 0:
                    group.add([i], float(value), "REPLACE")
        widths[side] = {"sole_length_m": float(np.ptp(p[sole, 1])),
                        "foot_length_m": float(np.ptp(surface.footprint[:, 1])),
                        "projected_sole_hull_overhang_m": footprint_overhang(surface.footprint, convex_hull(p[sole, :2])),
                        "sole_minimum_z_m": float(p[sole, 2].min())}

    mesh.update()
    mesh.calc_loop_triangles()
    assert len(mesh.loop_triangles) <= 3500
    shoes.name = "Sandals_Pair"
    mesh.name = "Tripo Purple Sandals"
    shoes.parent = arm
    shoes.modifiers.new("Master Skin", "ARMATURE").object = arm
    # Use the same material in both primitive slots. A stable named material
    # variant tags sole faces for the independent pixel visibility check.
    mat = mesh.materials[0]
    mat.name = "Tripo Sandals - Straps"
    with TemporaryDirectory(prefix=".textures-", dir=HERE) as folder:
        resize_texture_images(mat, Path(folder))
    sole_mat = mat.copy()
    sole_mat.name = "Tripo Sandals - Sole"
    mesh.materials.append(sole_mat)
    for poly in mesh.polygons:
        poly.material_index = 1 if poly.index in sole_face_ids else 0
        poly.use_smooth = True
    flat_faces = stabilize_tangents(mesh)
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
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=str(EXPORT), export_format="GLB", use_selection=True,
        export_yup=True, export_animations=False, export_skins=True,
        export_def_bones=False, export_armature_object_remove=True,
        export_all_influences=False, export_materials="EXPORT", export_tangents=True,
    )
    report("fit_geometry", {"export_sha256": digest(EXPORT), "source_sha256": digest(SOURCE),
                           "repaired_source_boundary_edges": 7, "closed_components": 2,
                           "subdivided_source_edges": subdivided_edges,
                           "flat_faces_for_tangent_validation": flat_faces,
                           "fit": widths, "baked_clearance": history})


if __name__ == "__main__":
    build()
