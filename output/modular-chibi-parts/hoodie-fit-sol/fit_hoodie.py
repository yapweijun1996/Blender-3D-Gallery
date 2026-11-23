"""Rebuild the Tripo hoodie against the chibi master with Blender 5.1.

Run Blender in background mode with --python-exit-code 1 --python fit_hoodie.py.
Only the module mesh and the master skeleton are exported to GLB.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


HERE = Path(__file__).resolve().parent
MASTER = HERE.parent / "master/GJH_Chibi_Master_rigged.blend"
SOURCE = HERE.parent / "tripo-top/tripo-out/modular-top-hoodie-34a980eb/model.glb"
MOTION = HERE.parents[2] / "models/tripo-chibi-motion/motion.glb"
NAME = "top_hoodie_v1"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
JOINT = "mixamorig:"


def ramp(value, start, end):
    t = np.clip((value - start) / (end - start), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a + (b - a) * t


def mesh_points(mesh):
    points = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", points)
    return points.reshape(-1, 3)


def mesh_triangles(mesh):
    mesh.calc_loop_triangles()
    return [tuple(triangle.vertices) for triangle in mesh.loop_triangles]


def surface(points, triangles):
    return BVHTree.FromPolygons(points.tolist(), triangles, all_triangles=True)


def import_mesh(path):
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=True)
    return next(obj for obj in bpy.context.selected_objects if obj.type == "MESH")


def open_cuffs(mesh):
    """Remove the recessed sleeve plugs, retaining the cylindrical inner lips."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
    plugs = [
        v for v in bm.verts
        if abs(v.co.x) > 0.355
        and math.hypot((v.co.y + 0.039) / 0.041, (v.co.z - 0.038) / 0.035) < 1
    ]
    bmesh.ops.delete(bm, geom=plugs, context="VERTS")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    print(f"Removed {len(plugs)} sleeve plug vertices", flush=True)


def cast_radius(tree, center, ray, distance=0.34):
    """Find the outer section along a polar ray, looking toward its axis."""
    hit, _, index, _ = tree.ray_cast(center + distance * ray, -ray, distance)
    return (hit - center).dot(ray) if index is not None else None


def fit_shape(mesh, body_tree):
    source = mesh_points(mesh)
    source_tree = surface(source, mesh_triangles(mesh))
    fitted = []
    source_center = Vector((0, -0.038, 0.039))
    hood_mask = []
    for x, y, z in source:
        width = abs(x)
        torso_z = np.interp(
            z, [-0.287, -0.251, -0.222, -0.075, 0.04, 0.122, 0.170],
            [0.387, 0.402, 0.417, 0.515, 0.563, 0.590, 0.604],
        )
        torso = Vector((0.54 * x + 0.0008, 0.59 * (y + 0.046) - 0.019, torso_z))
        # Fit horizontal torso sections while carrying forward folds and the
        # thickness of the original hem instead of flattening to a body copy.
        if z < -0.068 and width < 0.24:
            ray = Vector((x, y + 0.046, 0)).normalized()
            source_z = max(z, -0.269)
            radius = cast_radius(source_tree, Vector((0, -0.046, source_z)), ray)
            body_center = Vector((0.0008, -0.018, torso_z))
            body_radius = cast_radius(body_tree, body_center, ray, 0.17)
            if radius is not None and body_radius is not None:
                relief = math.hypot(x, y + 0.046) - radius
                bulge = 0.008 + 0.003 * ramp(-z, 0.10, 0.20)
                target = body_center + ray * (body_radius + bulge + 0.48 * relief)
                torso = torso.lerp(target, float(1 - ramp(z, -0.10, -0.067)))

        # Sleeve axes follow the master arm slope. Keep the puff and cuff relief
        # around the axis, independently of the lower torso width.
        arm_x = math.copysign(float(np.interp(width, [0, 0.22, 0.5], [0, 0.114, 0.263])), x)
        arm_z = 0.567 - 0.005 * ramp(abs(arm_x), 0.09, 0.265)
        arm_y = -0.009 - 0.003 * ramp(abs(arm_x), 0.13, 0.265)
        seam = ramp(width, 0.16, 0.26) * ramp(z, -0.12, -0.066)
        sleeve_center = Vector((arm_x, arm_y, arm_z))
        local = Vector((0, y, z)) - source_center
        direction = local.normalized()
        radius = local.length
        cuff = ramp(width, 0.365, 0.448)
        inflation = 0.005 * ramp(width, 0.17, 0.28)
        inflation += 0.004 * ramp(width, 0.25, 0.34) * (1 - ramp(width, 0.38, 0.435)) * (0.5 + 0.5 * direction.z)
        sleeve = sleeve_center + direction * (0.50 * radius + inflation)
        if width > 0.225 and radius > 0:
            body_radius = cast_radius(body_tree, sleeve_center, direction, 0.075)
            if body_radius is not None:
                # Widen the inner radius without flattening the cuff wall or
                # pushing its ends independently along the forearm.
                inner_radius = 0.041
                cuff_radius = body_radius + 0.007 + 0.24 * (radius - inner_radius)
                sleeve = sleeve.lerp(sleeve_center + direction * cuff_radius, float(cuff))
                # The lower sleeve faces the trunk once the arm drops. Keep
                # ease there while preserving the puff on the exposed half.
                medial = ramp(-direction.z, 0.1, 0.85) * ramp(width, 0.225, 0.32)
                sleeve = sleeve.lerp(sleeve_center + direction * (body_radius + 0.007), float(0.83 * medial))
        position = torso.lerp(sleeve, float(seam))
        shoulder_top = ramp(width, 0.108, 0.152) * (1 - ramp(width, 0.212, 0.275))
        center_section = 1 - ramp(abs(y + 0.019), 0.018, 0.08)
        position.z += 0.011 * shoulder_top * center_section * ramp(z, 0.055, 0.14)

        # Roll the upper opening back under the chibi's low, oversized head.
        # The lower front rim and the drawstrings stay at the neck and chest.
        back = ramp(y, -0.018, 0.105)
        upper_hood = ramp(z, 0.11, 0.262) * (1 - ramp(width, 0.19, 0.24))
        high = max(z - 0.16, 0)
        position.y += 0.022 * back * upper_hood + 0.023 * upper_hood
        position.z += (0.145 + 0.115 * back) * high
        hood_mask.append((1 - ramp(width, 0.16, 0.24)) * ramp(z, 0.06, 0.25) * (0.30 + 0.7 * back))
        fitted.append(tuple(position))
    return source, np.array(fitted, dtype=np.float32), np.array(hood_mask, dtype=np.float32)


def adjacency(mesh):
    rows = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        rows[a].append(b)
        rows[b].append(a)
    columns = np.zeros((len(rows), max(map(len, rows))), dtype=np.int32)
    for index, neighbors in enumerate(rows):
        columns[index] = neighbors + [index] * (columns.shape[1] - len(neighbors))
    factors = (columns != np.arange(len(rows))[:, None]).astype(np.float32)
    factors /= np.maximum(1, factors.sum(axis=1, keepdims=True))
    return columns, factors


def average(values, neighbors):
    indices, factors = neighbors
    return (values[indices] * factors[:, :, None]).sum(axis=1)


def correct_rest(points, body_tree, source):
    """Push rest intersections out without shrinking intentional cloth detail."""
    for i, point in enumerate(points):
        loc, normal, _, _ = body_tree.find_nearest(point)
        offset = Vector(point) - loc
        minimum = 0.0045
        if offset.dot(normal) >= minimum:
            continue
        x, y, z = source[i]
        if abs(x) > 0.23 and z > -0.11:
            ray = Vector((0, point[1] + 0.009, point[2] - 0.563)).normalized()
        elif z > 0.13 and y > 0.045:
            ray = Vector((0.25 * point[0], 1, -0.38)).normalized()
        else:
            ray = Vector((point[0], point[1] + 0.018, 0)).normalized()
        if normal.dot(ray) < 0.27:
            ray = normal
        points[i] += tuple(ray * ((minimum - offset.dot(normal)) / normal.dot(ray)))


def transfer_weights(body, hoodie, arm, points, source, hood_mask, body_tree, triangles):
    names = tuple(b.name for b in arm.data.bones)
    name_index = {name: index for index, name in enumerate(names)}
    groups = [name_index.get(vg.name) for vg in body.vertex_groups]
    body_weights = np.zeros((len(body.data.vertices), len(names)), dtype=np.float32)
    for vertex in body.data.vertices:
        for assignment in vertex.groups:
            col = groups[assignment.group]
            if col is not None:
                body_weights[vertex.index, col] = assignment.weight

    weights = np.zeros((len(points), len(names)), dtype=np.float32)
    positions = [v.co.copy() for v in body.data.vertices]
    axes = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    for i, point in enumerate(points):
        loc, _, face, _ = body_tree.find_nearest(point)
        corners = triangles[face]
        barycentric = barycentric_transform(loc, *(positions[j] for j in corners), *axes)
        weights[i] = np.array(barycentric) @ body_weights[list(corners)]

    def bone(name):
        return name_index[JOINT + name]

    for side, side_sign in (("Left", 1), ("Right", -1)):
        forearm = bone(side + "ForeArm")
        hand_columns = [index for index, name in enumerate(names) if name.startswith(JOINT + side + "Hand")]
        # Wrist cuffs belong to the forearm. Finger articulation is independent.
        weights[:, forearm] += weights[:, hand_columns].sum(axis=1)
        weights[:, hand_columns] = 0
        cuff = ramp(side_sign * source[:, 0], 0.414, 0.485)[:, None]
        weights *= 1 - cuff
        weights[:, forearm] += cuff[:, 0]

    hips = bone("Hips")
    leg_columns = [idx for idx, name in enumerate(names) if "Leg" in name or "Foot" in name or "Toe" in name]
    weights[:, hips] += weights[:, leg_columns].sum(axis=1)
    weights[:, leg_columns] = 0
    hem = 0.88 * (1 - ramp(source[:, 2], -0.258, -0.19))
    weights *= 1 - hem[:, None]
    weights[:, hips] += hem

    head = bone("Head")
    head_columns = [head, bone("HeadTop_End")]
    weights[:, bone("Neck")] += weights[:, head_columns].sum(axis=1)
    weights[:, head_columns] = 0
    hood = 0.88 * hood_mask
    weights *= 1 - hood[:, None]
    weights[:, head] += 0.68 * hood * hood_mask
    weights[:, bone("Neck")] += hood * (1 - 0.68 * hood_mask)

    neighbors = adjacency(hoodie.data)
    x = np.abs(points[:, 0])
    shoulder = ramp(x, 0.05, 0.105) * (1 - ramp(x, 0.13, 0.16)) * ramp(points[:, 2], 0.49, 0.55)
    elbow = ramp(x, 0.13, 0.168) * (1 - ramp(x, 0.195, 0.23))
    waist = 1 - ramp(points[:, 2], 0.395, 0.447)
    smoothing = (0.30 * np.maximum.reduce((shoulder, elbow, waist)))[:, None]
    for _ in range(3):
        weights = mix(weights, average(weights, neighbors), smoothing)
    weights = np.maximum(0, weights)
    keep = np.argsort(-weights, kind="stable")[:, :4]
    limited = np.zeros_like(weights)
    np.put_along_axis(limited, keep, np.take_along_axis(weights, keep, axis=1), axis=1)
    limited[limited < 0.00005] = 0
    assert np.all(limited.sum(axis=1) > 0)
    limited /= limited.sum(axis=1, keepdims=True)
    return names, limited


def motion_samples(scene, arm, body, names, weights):
    """Cache posed body surfaces and linear skin transforms in master space."""
    prior = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in list(scene.objects):
        if obj not in prior:
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data_create()
    bones = [arm.pose.bones[name] for name in names]
    inverse_bind = [bone.bone.matrix_local.inverted() for bone in bones]
    triangles = mesh_triangles(body.data)
    sample_times = {"rest": [1]}
    for name in CLIPS:
        first, last = bpy.data.actions[name].frame_range
        frames = set(range(math.ceil(first), math.floor(last) + 1)) | {first, last}
        frames.update(int(first + (last - first) * k / 12) for k in range(12))
        sample_times[name] = sorted(frames)
    for name, frames in sample_times.items():
        action = bpy.data.actions.get(name)
        arm.animation_data.action = action
        if action:
            arm.animation_data.action_slot = action.slots[0]
        for frame in frames:
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            posed_body = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            tree = surface(mesh_points(posed_body.data), triangles)
            transforms = np.array([bone.matrix @ inverse for bone, inverse in zip(bones, inverse_bind)])
            transforms = transforms[:, :3, :].astype(np.float32)
            skin = (weights @ transforms.reshape(len(bones), 12)).reshape(-1, 3, 4)
            yield name, frame, tree, skin[:, :, :3].copy(), skin[:, :, 3].copy()
    arm.animation_data_clear()
    for bone in bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    for name in CLIPS:
        bpy.data.actions.remove(bpy.data.actions[name])


def signed_clearance(tree, point):
    location, normal, _, _ = tree.find_nearest(point)
    return (Vector(point) - location).dot(normal)


def repair_rest(points, mesh, body_tree):
    """Clear surface contacts, including face interiors, with smooth bind offsets."""
    triangles = np.array(mesh_triangles(mesh), dtype=np.int32)
    neighbors = adjacency(mesh)
    original = points.copy()
    for iteration in range(12):
        garment = surface(points, triangles.tolist())
        hits = sorted({garment_face for _, garment_face in body_tree.overlap(garment)})
        delta = np.zeros_like(points)
        for i, point in enumerate(points):
            loc, n, _, _ = body_tree.find_nearest(point)
            signed = (Vector(point) - loc).dot(n)
            if signed < 0.0045:
                delta[i] = tuple((0.0045 - signed) * n)
        for face in hits:
            corners = triangles[face]
            centroid = points[corners].mean(axis=0)
            loc, n, _, _ = body_tree.find_nearest(centroid)
            # These faces spend their rest clearance in the middle of an edge.
            # Lift the patch together, including corners outside the contact.
            normal = Vector(centroid) - loc
            if normal.dot(n) < 0 or normal.length < 0.0003:
                normal = n
            normal.normalize()
            delta[corners] += np.array(normal) * 0.00075
        if not hits and float(np.linalg.norm(delta, axis=1).max()) < 0.00015:
            break
        # Expand the correction one ring without flattening lining or trims.
        points += 0.80 * delta + 0.35 * average(delta, neighbors)
    print("REST SURFACE", iteration, len(hits), "intersections;", "max repair",
          round(float(np.linalg.norm(points - original, axis=1).max()), 5), flush=True)


def fit_motion(points, hoodie, samples):
    """Bake a bounded, spatially smoothed motion offset into the bind mesh."""
    neighbors = adjacency(hoodie.data)
    rest = points.copy()
    rest_tree = samples[0][2]
    rest_normals = np.array([tuple(rest_tree.find_nearest(point)[1]) for point in points], dtype=np.float32)
    limits = {"rest": 0.0045, **dict.fromkeys(CLIPS, 0.002)}
    coarse = [sample for sample in samples if sample[0] == "rest" or int(sample[1]) % 3 == 0]
    for iteration in range(24):
        displacement = np.zeros_like(points)
        largest = np.zeros(len(points), dtype=np.float32)
        total = np.zeros(len(points), dtype=np.float32)
        results = {}
        active = coarse if iteration < 17 else samples
        for clip, frame, tree, linear, translation in active:
            posed = np.einsum("ijk,ik->ij", linear, points) + translation
            old_count, old_min = results.get(clip, (0, math.inf))
            inside = 0
            minimum = math.inf
            for i, point in enumerate(posed.tolist()):
                signed = signed_clearance(tree, point)
                minimum = min(minimum, signed)
                inside += signed < 0
                deficit = limits[clip] - signed
                if deficit <= 0:
                    continue
                _, normal, _, _ = tree.find_nearest(point)
                gradient = linear[i].T @ np.array(normal, dtype=np.float32)
                factor = min(deficit, 0.006) ** 1.4
                if clip == "rest":
                    factor *= 18
                elif gradient @ rest_normals[i] < -0.32:
                    factor *= 0.24
                largest[i] = max(largest[i], deficit)
                displacement[i] += factor * gradient
                total[i] += factor
            results[clip] = (max(old_count, inside), min(old_min, minimum))
        if iteration in (0, 8, 16, 23):
            print("MOTION", iteration, {k: (n, round(d, 6)) for k, (n, d) in results.items()}, flush=True)
        step = np.minimum(largest * 0.5, 0.0026)
        displacement *= (step / np.maximum(1e-10, total))[:, None]
        offsets = points - rest + displacement
        offsets = mix(offsets, average(offsets, neighbors), 0.32)
        # Preserve the ribbing and pocket silhouettes at rest. Large isolated
        # moves can clear vertices while driving the connecting faces inside.
        cap = 0.012
        offsets *= np.minimum(1, cap / np.maximum(1e-10, np.linalg.norm(offsets, axis=1)))[:, None]
        points[:] = rest + offsets
    repair_rest(points, hoodie.data, rest_tree)


def refine_contact_patches(points, mesh, samples, clip_importance=None):
    """Explore small contact corrections while preserving local triangle orientation."""
    triangles = np.array(mesh_triangles(mesh), dtype=np.int32)
    incidence = [[] for _ in points]
    for face, corners in enumerate(triangles):
        for corner in corners:
            incidence[corner].append(face)
    normals = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]],
                       points[triangles[:, 2]] - points[triangles[:, 0]])
    lengths = np.linalg.norm(normals, axis=1)
    neighbors = adjacency(mesh)

    first_frame = {}
    selected = []
    for sample in samples:
        clip, frame, *_ = sample
        if clip == "rest":
            selected.append(sample)
            continue
        if clip not in first_frame:
            first_frame[clip] = frame
        if int(frame - first_frame[clip]) % 3 == 0:
            selected.append(sample)

    prioritize = clip_importance is not None
    importance = np.array(clip_importance if prioritize else [1] * len(CLIPS))[:, None]
    n = 36 if prioritize else 30
    height = np.linspace(1 - 1 / n, -1 + 1 / n, n)
    angles = np.arange(n) * math.pi * (3 - math.sqrt(5))
    ring = np.sqrt(1 - height ** 2)
    directions = np.stack([ring * np.cos(angles), ring * np.sin(angles), height], axis=1)
    offsets = (np.array([0.0015, 0.003, 0.005, 0.008])[:, None, None] * directions).reshape(-1, 3)
    offsets = np.vstack([np.zeros((1, 3)), offsets]).astype(np.float32)
    original = points.copy()
    for iteration in range(1 if prioritize else 2):
        failing = {}
        for k, (clip, _, tree, linear, translation) in enumerate(selected):
            posed = np.einsum("ijk,ik->ij", linear, points) + translation
            for i, position in enumerate(posed.tolist()):
                d = signed_clearance(tree, position)
                if d < 0.0012:
                    failing.setdefault(i, []).append((d, k))

        center = average(points - original, neighbors)
        changed = 0
        for i in sorted(failing):
            near = triangles[incidence[i]]
            start = points[i]
            choices = start + offsets
            coordinates = points[near]
            corners = np.broadcast_to(coordinates, (len(choices), *coordinates.shape)).copy()
            corners[:, near == i] = choices[:, None]
            directions = np.cross(corners[:, :, 1] - corners[:, :, 0], corners[:, :, 2] - corners[:, :, 0])
            cosines = np.einsum("kij,ij->ki", directions, normals[incidence[i]])
            area = np.linalg.norm(directions, axis=2)
            allowed = (cosines >= 0.35 * area * lengths[incidence[i]]).all(axis=1)
            allowed &= (area >= 0.25 * lengths[incidence[i]]).all(axis=1)
            allowed &= (area <= 2.35 * lengths[incidence[i]]).all(axis=1)
            distance = np.linalg.norm(choices - original[i], axis=1)
            allowed &= distance <= (0.005 if prioritize else 0.0115)
            allowed &= np.array([signed_clearance(selected[0][2], p) >= 0.0042 for p in choices])
            allowed[0] = True
            choices = choices[allowed]
            if len(choices) < 2:
                continue

            local = list(dict.fromkeys(k for _, k in sorted(failing[i])[:18]))
            worst = np.zeros((len(CLIPS), len(choices)), dtype=np.float32)
            totals = np.zeros(len(choices), dtype=np.float32)
            regularizer = 0.55 * np.linalg.norm(choices - original[i] - center[i], axis=1)
            regularizer += 0.25 * np.linalg.norm(choices - original[i], axis=1)
            for k in local:
                clip, _, tree, linear, translation = selected[k]
                if clip == "rest":
                    continue
                posed = choices @ linear[i].T + translation[i]
                deficit = np.maximum(0, 0.0012 - np.array([signed_clearance(tree, p) for p in posed]))
                idx = CLIPS.index(clip)
                worst[idx] = np.maximum(worst[idx], deficit)
                totals += deficit
            score = (importance * worst).sum(axis=0) + totals * 0.07 + regularizer
            options = np.array(list(dict.fromkeys([0, *np.argsort(score, kind="stable")[:8]])))
            choices = choices[options]
            worst = worst[:, options]
            totals = totals[options]
            for k, (clip, _, tree, linear, translation) in enumerate(selected):
                if clip == "rest" or k in local:
                    continue
                posed = choices @ linear[i].T + translation[i]
                deficit = np.maximum(0, 0.0012 - np.array([signed_clearance(tree, p) for p in posed]))
                idx = CLIPS.index(clip)
                worst[idx] = np.maximum(worst[idx], deficit)
                totals += deficit
            score = (importance * worst).sum(axis=0) + totals * 0.05 + regularizer[options]
            best = int(np.argmin(score))
            if best and score[best] < score[0] - 0.00015:
                points[i] = choices[best]
                changed += 1
        print("PATCH CLEARANCE", iteration, len(failing), "tested;", changed, "adjusted", flush=True)

    repair_rest(points, mesh, selected[0][2])


def prepare_asset(hoodie, arm, names, weights, points):
    mesh = hoodie.data
    mesh.vertices.foreach_set("co", points.ravel())
    mesh.update()
    if mesh.has_custom_normals:
        # Rebuild loop normals after the large nonuniform rest-shape transform.
        bpy.context.view_layer.objects.active = hoodie
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for poly in mesh.polygons:
        poly.use_smooth = True

    for col, name in enumerate(names):
        ids = np.flatnonzero(weights[:, col])
        if not len(ids):
            continue
        group = hoodie.vertex_groups.new(name=name)
        for i in ids:
            group.add([int(i)], float(weights[i, col]), "REPLACE")
    hoodie.name = NAME
    mesh.name = NAME
    hoodie.parent = arm
    modifier = hoodie.modifiers.new("Armature", "ARMATURE")
    modifier.object = arm

    for material in mesh.materials:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                image = node.image
                width, height = image.size
                scale = min(1, 1024 / max(width, height))
                if scale < 1:
                    image.scale(round(width * scale), round(height * scale))
                    image.pack()


def main():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    body = scene.objects["Base_Body"]
    arm = scene.objects["Armature"]
    hoodie = import_mesh(SOURCE)
    mesh = hoodie.data
    for vertex in mesh.vertices:
        x, y, z = hoodie.matrix_world @ vertex.co
        vertex.co = (y, -x, z)
    open_cuffs(mesh)
    body_triangles = mesh_triangles(body.data)
    body_tree = surface(mesh_points(body.data), body_triangles)
    source, points, hood_mask = fit_shape(mesh, body_tree)
    shape = points.copy()
    neighbors = adjacency(mesh)
    for _ in range(5):
        correct_rest(points, body_tree, source)
        offsets = points - shape
        points[:] = shape + mix(offsets, average(offsets, neighbors), 0.28)
    repair_rest(points, mesh, body_tree)
    names, weights = transfer_weights(body, hoodie, arm, points, source, hood_mask, body_tree, body_triangles)
    samples = list(motion_samples(scene, arm, body, names, weights))
    fit_motion(points, hoodie, samples)
    refine_contact_patches(points, mesh, samples)
    refine_contact_patches(points, mesh, samples, (1, 1, 1, 1, 1.8, 2.4, 2.1))
    refine_contact_patches(points, mesh, samples, (1, 1, 1, 1, 4.0, 8.0, 2.3))
    prepare_asset(hoodie, arm, names, weights, points)
    assert len(mesh_triangles(mesh)) <= 6000
    assert len(arm.data.bones) == 65
    assert np.all((weights > 0).sum(axis=1) <= 4)
    assert np.allclose(weights.sum(axis=1), 1)
    assert not body_tree.overlap(surface(points, mesh_triangles(mesh)))
    print("Final triangles:", len(mesh_triangles(mesh)), flush=True)

    bpy.ops.object.select_all(action="DESELECT")
    hoodie.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = hoodie
    # A root-level glTF mesh avoids inheriting a transform ignored by skinning.
    # Retain the editable armature parenting in the saved Blender scene.
    hoodie.parent = None
    bpy.ops.export_scene.gltf(
        filepath=str(HERE / f"{NAME}.glb"), export_format="GLB",
        use_selection=True, export_animations=False, export_yup=True,
        export_all_influences=False, export_def_bones=False,
    )
    hoodie.parent = arm
    body.hide_render = True
    body.hide_set(True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            viewport = area.spaces.active
            viewport.overlay.show_overlays = False
            viewport.shading.type = "SOLID"
            viewport.shading.color_type = "TEXTURE"
            viewport.region_3d.view_rotation = Vector((-0.15, 1, -0.13)).to_track_quat("-Z", "Y")
            viewport.region_3d.view_location = (0, 0, 0.515)
            viewport.region_3d.view_distance = 0.85
            viewport.region_3d.view_perspective = "ORTHO"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"{NAME}.blend"))


def run_checker():
    """Run the supplied check with a CPU renderer for headless macOS."""
    checker = HERE / "motion_check.py"
    source = checker.read_text(encoding="utf-8")
    workbench_setup = "sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL'"
    cycles_setup = """
sc.render.engine='CYCLES'
sc.cycles.device='CPU'
sc.cycles.samples=16
sc.cycles.use_denoising=True
sc.render.resolution_percentage=100
sc.render.use_compositing=False
sc.render.use_sequencer=False
sc.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('QA studio')
sc.world=world
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(0.68,0.73,0.8,1)
world.node_tree.nodes['Background'].inputs[1].default_value=0.38
from mathutils import Vector
for name, pos, power, size in (
  ('Key', (-1.0,-1.5,2.6), 150, 2.2),
  ('Fill', (1.2,-0.7,1.25), 38, 1.8),
  ('Rim', (0.4,1.45,2.0), 105, 1.5),
):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=power
    data.shape='DISK'
    data.size=size
    light=bpy.data.objects.new(name,data)
    sc.collection.objects.link(light)
    light.location=pos
    light.rotation_euler=(Vector((0,0,0.52))-light.location).to_track_quat('-Z','Y').to_euler()
"""
    assert source.count(workbench_setup) == 1, "The checker render setup changed"
    source = source.replace(workbench_setup, cycles_setup)
    argv = sys.argv
    try:
        sys.argv = [str(checker), "--", str(MASTER), str(MOTION),
                    str(HERE / f"{NAME}.glb"), str(HERE)]
        exec(compile(source, str(checker), "exec"), {"__name__": "__main__"})
    finally:
        sys.argv = argv


if __name__ == "__main__":
    main()
    if "--build-only" not in sys.argv:
        run_checker()
