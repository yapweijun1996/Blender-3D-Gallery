"""Build the GJH chibi T-shirt in the folder containing this script.

Pass the source .blend path after Blender's "--" separator, or use the
default rigged master from this repository. Use --check to rebuild the
checker outputs alongside the Blend and GLB.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


OUTPUT_DIR = Path(__file__).resolve().parent
MASTER_BLEND = OUTPUT_DIR.parents[1] / "master" / "GJH_Chibi_Master_rigged.blend"
MOTION_GLB = OUTPUT_DIR.parents[3] / "models" / "tripo-chibi-motion" / "motion.glb"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
NAME = "top_tshirt_v2"
MIN_CLEARANCE = 0.0005
SLEEVE_FRACTION = 0.40
FABRIC_COLOR = (0.075, 0.40, 0.37, 1.0)


def bone_head(rig, name):
    return rig.matrix_world @ rig.data.bones[f"mixamorig:{name}"].head_local


def count_openings(mesh):
    neighbors = {}
    for edge in mesh.edges:
        if not edge.is_boundary:
            continue
        first, second = edge.verts
        neighbors.setdefault(first, []).append(second)
        neighbors.setdefault(second, []).append(first)
    if any(len(adjacent) != 2 for adjacent in neighbors.values()):
        raise RuntimeError("The garment has a branched boundary.")
    remaining = set(neighbors)
    openings = 0
    while remaining:
        loop = [remaining.pop()]
        for vertex in loop:
            for neighbor in neighbors[vertex]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    loop.append(neighbor)
        openings += 1
    return openings


def make_shell(rig):
    """Loft the torso, round collar and two sleeves as one continuous surface."""
    count = 48
    half_hole = 5
    lower_hole = 8
    upper_hole = 14
    neck = bone_head(rig, "Neck")
    # Body sections at the waist, chest and shoulder. The two ends of a
    # section use the same x radius but the front and back have their own depth.
    # z center, side rise, x radius, front radius, back radius, y center
    sections = (
        (.427, .027, .103, .094, .094, -.022),
        (.431, .025, .103, .093, .088, -.022),
        (.436, .024, .104, .090, .082, -.022),
        (.447, .018, .103, .089, .077, -.022),
        (.457, .015, .102, .088, .074, -.022),
        (.469, .011, .100, .087, .073, -.022),
        (.481, .009, .098, .085, .075, -.022),
        (.492, .008, .097, .082, .078, -.022),
        (.502, .007, .096, .080, .079, -.021),
        (.510, .014, .096, .078, .080, -.021),
        (.518, .022, .096, .075, .079, -.021),
        (.523, .033, .096, .073, .075, -.020),
        (.529, .043, .094, .071, .071, -.020),
        (.535, .051, .093, .068, .064, -.019),
        (.541, .063, .091, .066, .056, -.018),
    )
    vertices, faces = [], []
    centered_x = bone_head(rig, "Hips").x - .00195

    def append(point):
        index = len(vertices)
        vertices.append(Vector(point))
        return index

    def connect(inner, outer):
        for i in range(len(inner)):
            j = (i + 1) % len(inner)
            faces.append((inner[i], inner[j], outer[j], outer[i]))

    torso = []
    for level, (z, rise, width, front, back, mid_y) in enumerate(sections):
        ring = []
        for i in range(count):
            angle = i * (2 * math.pi / count)
            across, depth = math.cos(angle), math.sin(angle)
            # Keep a close side seam at the hip. Higher up, the shoulder
            # sweeps down toward the centre front of the collar.
            exponent = 1.25 if level >= lower_hole else 4
            height = z + rise * abs(across) ** exponent
            y = mid_y + depth * (front if depth < 0 else back)
            ring.append(append((centered_x + width * across, y, height)))
        torso.append(ring)

    for level, (lower, upper) in enumerate(zip(torso, torso[1:])):
        for i in range(count):
            column = (i + half_hole) % (count // 2)
            if lower_hole <= level < upper_hole and column < 2 * half_hole:
                continue
            j = (i + 1) % count
            faces.append((lower[i], lower[j], upper[j], upper[i]))

    collar = []
    for i in range(count):
        angle = i * (2 * math.pi / count)
        across, depth = math.cos(angle), math.sin(angle)
        # A round oval in plan, lowered in front and raised along the back.
        z = neck.z + .009 - .046 * max(0, -depth) ** 1.65 - .012 * max(0, depth) ** 1.35
        collar.append(Vector((centered_x + .048 * across, -.019 + .059 * depth, z)))
    previous = torso[-1]
    for fraction in (.25, .50, .75, 1.0):
        ring = [append(vertices[outer].lerp(inner, fraction))
                for outer, inner in zip(torso[-1], collar)]
        connect(previous, ring)
        previous = ring

    for side, center in (("Left", 0), ("Right", count // 2)):
        def at(level, column):
            return torso[level][(center + column) % count]

        rim = [at(lower_hole, i) for i in range(-half_hole, half_hole)]
        rim += [at(level, half_hole) for level in range(lower_hole, upper_hole)]
        rim += [at(upper_hole, i) for i in range(half_hole, -half_hole, -1)]
        rim += [at(level, -half_hole) for level in range(upper_hole, lower_hole, -1)]

        shoulder = bone_head(rig, side + "Arm")
        elbow = bone_head(rig, side + "ForeArm")
        cuff = shoulder.lerp(elbow, SLEEVE_FRACTION)
        sleeve = []
        for index in rim:
            point = vertices[index]
            angle = math.atan2((point.z - .557) / .052, (point.y + .012) / .053)
            # Cut the cuff perpendicular to the upper arm axis.
            y = math.cos(angle) * (.055 if math.cos(angle) < 0 else .050)
            z = math.sin(angle) * (.050 if math.sin(angle) < 0 else .044)
            x = -((elbow.y - shoulder.y) * y + (elbow.z - shoulder.z) * z) / (elbow.x - shoulder.x)
            sleeve.append(cuff + Vector((x, y, z)))

        previous = rim
        for fraction in (.24, .46, .66, .84, 1.0):
            ring = [append(vertices[origin].lerp(edge, fraction)) for origin, edge in zip(rim, sleeve)]
            connect(previous, ring)
            previous = ring

    data = bpy.data.meshes.new(NAME)
    data.from_pydata(vertices, [], faces)
    shell = bmesh.new()
    try:
        shell.from_mesh(data)
        bmesh.ops.delete(shell, geom=[v for v in shell.verts if not v.link_edges], context="VERTS")
        bmesh.ops.recalc_face_normals(shell, faces=list(shell.faces))
        front_faces = [face for face in shell.faces if face.calc_center_median().y < -.09]
        if sum(face.normal.y for face in front_faces) > 0:
            bmesh.ops.reverse_faces(shell, faces=list(shell.faces))
        bmesh.ops.triangulate(shell, faces=list(shell.faces), quad_method='BEAUTY')
        if count_openings(shell) != 4:
            raise RuntimeError("Expected only the collar, hem, and two sleeve openings.")
        for face in shell.faces:
            face.smooth = True
        shell.to_mesh(data)
    finally:
        shell.free()
    data.update()
    shirt = bpy.data.objects.new(NAME, data)
    bpy.context.collection.objects.link(shirt)
    return shirt


def copy_weights(body, shirt):
    for group in body.vertex_groups:
        shirt.vertex_groups.new(name=group.name)

    transfer = shirt.modifiers.new("Transfer body weights", "DATA_TRANSFER")
    transfer.object = body
    transfer.use_vert_data = True
    transfer.data_types_verts = {"VGROUP_WEIGHTS"}
    transfer.vert_mapping = "POLYINTERP_NEAREST"
    transfer.layers_vgroup_select_src = "ALL"
    transfer.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.modifier_apply(modifier=transfer.name)

    # Interpolate on the uninflated shell so the offset cannot change which
    # side of the armpit or waist crease supplies the source skin weights.
    weights = [
        {entry.group: entry.weight for entry in vertex.groups if entry.weight > 0.0}
        for vertex in shirt.data.vertices
    ]
    neighbors = [[] for _ in weights]
    for edge in shirt.data.edges:
        first, second = edge.vertices
        neighbors[first].append(second)
        neighbors[second].append(first)
    for _ in range(2):
        relaxed = []
        for index, own in enumerate(weights):
            share = 0.18 / len(neighbors[index])
            blended = {group: 0.82 * weight for group, weight in own.items()}
            for neighbor in neighbors[index]:
                for group, weight in weights[neighbor].items():
                    blended[group] = blended.get(group, 0.0) + share * weight
            relaxed.append(blended)
        weights = relaxed

    for vertex, group_weights in zip(shirt.data.vertices, weights):
        leading = sorted(group_weights.items(), key=lambda item: (-item[1], item[0]))[:4]
        if not leading:
            raise RuntimeError(f"Data Transfer left vertex {vertex.index} unweighted.")
        for group in [entry.group for entry in vertex.groups]:
            shirt.vertex_groups[group].remove([vertex.index])
        total = sum(weight for _, weight in leading)
        for group, weight in leading:
            shirt.vertex_groups[group].add([vertex.index], weight / total, "REPLACE")


def finish_shirt(shirt, rig):
    fabric = bpy.data.materials.new("T-shirt | Sea Green")
    fabric.diffuse_color = FABRIC_COLOR
    surface = fabric.node_tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = FABRIC_COLOR
    surface.inputs["Roughness"].default_value = 0.85
    shirt.data.materials.append(fabric)

    # Keep the mesh in the same world-space bind position used for transfer.
    bind_transform = shirt.matrix_world.copy()
    shirt.parent = rig
    shirt.matrix_world = bind_transform
    deform = shirt.modifiers.new("Armature", "ARMATURE")
    deform.object = rig


def surface_triangles(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.data
    mesh.calc_loop_triangles()
    positions = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    triangles = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]
    return positions, triangles


def verify_fit(body_surface, shirt, rig):
    shirt.data.calc_loop_triangles()
    triangle_count = len(shirt.data.loop_triangles)
    print(f"T-shirt triangles: {triangle_count}", flush=True)
    if not 1500 <= triangle_count <= 4000:
        raise RuntimeError("T-shirt triangle count is outside the requested range.")

    deform_groups = {
        group.index for group in shirt.vertex_groups
        if (bone := rig.data.bones.get(group.name)) is not None and bone.use_deform
    }
    for vertex in shirt.data.vertices:
        weights = [entry for entry in vertex.groups if entry.weight > 0.0]
        if (
            not 1 <= len(weights) <= 4
            or any(entry.group not in deform_groups for entry in weights)
            or abs(sum(entry.weight for entry in weights) - 1.0) > 0.00001
        ):
            raise RuntimeError(f"Invalid skin weights at vertex {vertex.index}.")

    shirt_positions, shirt_triangles = surface_triangles(shirt)
    shirt_surface = BVHTree.FromPolygons(shirt_positions, shirt_triangles, all_triangles=True)
    distances = []
    torso_distances = []
    for position in shirt_positions:
        nearest, normal, _, _ = body_surface.find_nearest(position)
        signed_distance = (position - nearest).dot(normal)
        distances.append(signed_distance)
        if abs(position.x) < .076 and .46 < position.z < .535:
            torso_distances.append(signed_distance)
    minimum = min(distances)
    torso_minimum = min(torso_distances)
    intersections = len(body_surface.overlap(shirt_surface))
    self_intersections = sum(
        not set(shirt_triangles[first]).intersection(shirt_triangles[second])
        for first, second in shirt_surface.overlap(shirt_surface)
        if first < second
    )
    print(f"Bind pose clearance {minimum:.6f} m. Torso minimum {torso_minimum:.6f} m. "
          f"{intersections} shirt/body face pairs and {self_intersections} cloth self-overlap pairs.",
          flush=True)
    if minimum < MIN_CLEARANCE or torso_minimum > .015:
        raise RuntimeError("The bind pose is outside the requested vertex clearance range.")


def fit_under_motion(body, shirt, rig, motion_path):
    """Fit the bind mesh against the skinned body over the motion library."""
    scene = bpy.context.scene
    original_objects = set(scene.objects)
    original_actions = set(bpy.data.actions)
    import_collections = (bpy.data.meshes, bpy.data.armatures, bpy.data.materials,
                          bpy.data.images, bpy.data.collections, bpy.data.node_groups)
    original_data = [set(collection) for collection in import_collections]
    bpy.ops.import_scene.gltf(filepath=str(motion_path))
    imported_objects = [obj for obj in scene.objects if obj not in original_objects]
    imported_actions = [action for action in bpy.data.actions if action not in original_actions]
    for obj in imported_objects:
        obj.hide_viewport = True
        obj.hide_render = True
    rig.animation_data_create()

    weights = np.zeros((len(shirt.data.vertices), len(shirt.vertex_groups)))
    for vertex in shirt.data.vertices:
        for membership in vertex.groups:
            weights[vertex.index, membership.group] = membership.weight
    bones = [rig.pose.bones[group.name] for group in shirt.vertex_groups]
    inverses = [bone.bone.matrix_local.inverted() for bone in bones]
    rig_world = rig.matrix_world.copy()
    rig_to_shirt = rig_world.inverted() @ shirt.matrix_world

    def capture_pose():
        depsgraph = bpy.context.evaluated_depsgraph_get()
        posed_body = body.evaluated_get(depsgraph)
        mesh = posed_body.to_mesh()
        try:
            tree = BVHTree.FromPolygons(
                [posed_body.matrix_world @ vertex.co for vertex in mesh.vertices],
                [tuple(face.vertices) for face in mesh.polygons],
            )
        finally:
            posed_body.to_mesh_clear()
        bone_transforms = np.array([
            rig_world @ bone.matrix @ inverse @ rig_to_shirt
            for bone, inverse in zip(bones, inverses)
        ])[:, :3, :]
        transforms = (weights @ bone_transforms.reshape(len(bones), 12)).reshape(-1, 3, 4)
        return tree, transforms[:, :, :3], transforms[:, :, 3], bone_transforms

    frames = [capture_pose()]
    verification_frames = frames.copy()
    for name in CLIPS:
        action = next(action for action in imported_actions if action.name == name)
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        first, last = map(int, action.frame_range)
        sample_frames = set()
        sample_frames.update(int(first + (last - first) * k / 12) for k in range(12))
        sample_frames.add(last)
        for frame in range(first, last + 1):
            scene.frame_set(frame)
            snapshot = capture_pose()
            verification_frames.append(snapshot)
            if frame in sample_frames:
                frames.append(snapshot)

    rig.animation_data_clear()
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    for obj in imported_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for action in imported_actions:
        bpy.data.actions.remove(action)
    imported_data = {entry for collection, original in zip(import_collections, original_data)
                     for entry in collection if entry not in original}
    bpy.data.batch_remove(ids=imported_data)

    base = np.array([vertex.co for vertex in shirt.data.vertices])
    offsets = np.zeros_like(base)
    edges = np.array([tuple(edge.vertices) for edge in shirt.data.edges])
    start, end = np.concatenate((edges, edges[:, ::-1])).T
    neighbor_weight = 1.0 / np.maximum(np.linalg.norm(base[start] - base[end], axis=1), .004)
    normalizer = np.bincount(start, weights=neighbor_weight, minlength=len(base))

    def smooth(field):
        return np.stack([
            np.bincount(start, weights=neighbor_weight * axis[end], minlength=len(base)) / normalizer
            for axis in field.T
        ], axis=-1)

    for iteration in range(5):
        positions = base + offsets
        worst = np.zeros(len(base))
        corrections = np.zeros_like(base)
        for frame_index, (tree, rotation, translation, _) in enumerate(frames):
            clearance = .002 if frame_index > 0 else .003
            deformed = np.einsum('vij,vj->vi', rotation, positions) + translation
            for index, point in enumerate(deformed):
                closest, normal, _, _ = tree.find_nearest(point)
                distance = (Vector(point) - closest).dot(normal)
                deficit = clearance - distance
                if deficit > worst[index]:
                    gradient = np.asarray(normal) @ rotation[index]
                    corrections[index] = deficit * gradient / (gradient @ gradient)
                    worst[index] = deficit
        print(f"Fit iteration {iteration}: {sum(worst > .0002)} low vertices, "
              f"worst deficit {max(worst):.5f}", flush=True)
        if max(worst) < .0002:
            break
        offsets += .52 * corrections + .21 * (smooth(offsets) - offsets)
        offsets *= np.minimum(1., .011 / np.maximum(np.linalg.norm(offsets, axis=1), 1e-8))[:, None]
    desired = np.array([.0024] + [.00115] * (len(frames) - 1))
    trees = [frame[0] for frame in frames]
    bone_matrices = np.stack([frame[3] for frame in frames])
    base_weights = weights.copy()
    group_index = {group.name.removeprefix("mixamorig:"): group.index for group in shirt.vertex_groups}
    affected = []
    for vertex, vertex_weights in zip(base, base_weights):
        x, y, z = vertex
        side = "Left" if x > .001 else "Right"
        proposed = np.flatnonzero(vertex_weights > 0).tolist()
        if z >= .497 and abs(x) > .047:
            alternatives = (side + "Shoulder", side + "Arm", side + "ForeArm", "Spine2", "Spine1", "Neck")
        elif z < .49 and abs(x) > .058:
            alternatives = ("Hips", side + "UpLeg", "Spine", "Spine1", side + "Arm", side + "Shoulder")
        else:
            alternatives = ("Hips", "Spine", "Spine1", "Spine2", side + "Shoulder", "Neck")
        proposed.extend(group_index[name] for name in alternatives if group_index[name] not in proposed)
        proposed.extend(index for index in range(len(group_index)) if index not in proposed)
        affected.append(proposed[:8])
    affected = np.array(affected)
    compact_weights = np.take_along_axis(base_weights, affected, axis=1)
    adjacency = [end[start == index] for index in range(len(base))]
    rng = np.random.default_rng(674)
    random_directions = rng.normal(size=(128, 3))
    random_directions /= np.linalg.norm(random_directions, axis=1, keepdims=True)
    directions = np.array([
        (x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)
        if (x, y, z) != (0, 0, 0)
    ])
    directions = directions / np.linalg.norm(directions, axis=1, keepdims=True)

    count = len(frames)
    frame_indexes = list(range(count))

    for pass_index in range(20):
        smoothed = smooth(offsets)
        dense_weights = np.zeros_like(weights)
        np.put_along_axis(dense_weights, affected, compact_weights, axis=1)
        blends = np.take_along_axis(smooth(dense_weights), affected, axis=1)
        blends /= blends.sum(axis=1, keepdims=True)
        unsolved = []
        current_positions = base + offsets
        for index, offset in enumerate(offsets):
            center = base[index] + .87 * smoothed[index]
            neighbors = adjacency[index]
            reference_edges = base[neighbors] - base[index]
            neighbor_positions = current_positions[neighbors]
            lengths = np.maximum(np.linalg.norm(reference_edges, axis=1), .004)
            centered_weights = .8 * blends[index] + .2 * base_weights[index, affected[index]]
            point = base[index] + offset
            vertex_weights = compact_weights[index].copy()
            transforms = bone_matrices[:, affected[index]]
            frame_order = frame_indexes.copy()

            def score(position, mixture, limit):
                p = np.append(position, 1.)
                posed = np.einsum('fbmc,b,c->fm', transforms, mixture, p)
                penalty = 0.
                offender = frame_order[0]
                for frame_index in frame_order:
                    world = posed[frame_index]
                    closest, normal, _, _ = trees[frame_index].find_nearest(world)
                    distance = (Vector(world) - closest).dot(normal)
                    deficit = desired[frame_index] - distance
                    if deficit > penalty:
                        penalty, offender = deficit, frame_index
                    if penalty > limit:
                        break
                return penalty, offender

            def cost(position, mixture):
                edge_change = np.linalg.norm(neighbor_positions - position - reference_edges, axis=1)
                distortion = np.mean(np.maximum(0, edge_change - .30 * lengths)**2 / lengths)
                return (.018 * np.linalg.norm(position - base[index]) + .28 * distortion
                        + .00125 * np.linalg.norm(mixture - centered_weights))

            penalty, offender = score(point, vertex_weights, float('inf'))
            frame_order.remove(offender)
            frame_order.insert(0, offender)
            fit_cost = cost(point, vertex_weights)
            if penalty == 0 and (pass_index < 4 or pass_index >= 11):
                continue

            def attempt(position, mixture):
                nonlocal point, vertex_weights, penalty, fit_cost
                maximum_offset = .025 if pass_index < 8 else .043 if pass_index < 11 else .074
                if np.linalg.norm(position - base[index]) > maximum_offset:
                    return
                if np.count_nonzero(mixture > 1e-7) > 4:
                    mixture = mixture.copy()
                    mixture[np.argsort(-mixture, kind='stable')[4:]] = 0
                    mixture /= mixture.sum()
                candidate_cost = cost(position, mixture)
                if penalty <= 0 and candidate_cost >= fit_cost:
                    return
                limit = fit_cost + penalty - candidate_cost if pass_index < 5 else penalty + 0.0000001
                if limit < 0:
                    return
                candidate, frame = score(position, mixture, limit)
                if pass_index < 5:
                    better = candidate + candidate_cost < penalty + fit_cost
                else:
                    better = (candidate, candidate_cost) < (penalty, fit_cost)
                if better:
                    point, vertex_weights, penalty, fit_cost = position, mixture, candidate, candidate_cost
                    frame_order.remove(frame)
                    frame_order.insert(0, frame)

            for share in (.33, .66, 1.):
                attempt(point * (1-share) + center * share, vertex_weights)
                attempt(point, vertex_weights * (1-share) + centered_weights * share)
            if penalty > 0 or pass_index >= 5:
                for step in (.46, .20, .075):
                    for b in np.flatnonzero(vertex_weights > 1e-6):
                        for a in range(len(vertex_weights)):
                            if a == b:
                                continue
                            move = min(step, vertex_weights[b])
                            mix = vertex_weights.copy()
                            mix[a] += move
                            mix[b] -= move
                            attempt(point, mix)
            if pass_index < 5 or penalty > 0:
                anchor = point.copy()
                original_mix = vertex_weights.copy()
                for step in (.0015, .0035, .007, .014, .024, .036):
                    for candidate in np.concatenate((center + step * directions, anchor + step * directions)):
                        attempt(candidate, original_mix)
                    if penalty == 0 and step >= .007:
                        break
            if penalty > 0 and pass_index >= 5:
                for direction in random_directions:
                    amplitude = rng.uniform(.001, .021)
                    candidate = point + amplitude * direction
                    mixture = vertex_weights.copy()
                    source = rng.choice(np.flatnonzero(mixture > 1e-6))
                    destination = rng.integers(len(mixture))
                    move = rng.uniform(0, min(.45, mixture[source]))
                    mixture[source] -= move
                    mixture[destination] += move
                    attempt(candidate, mixture)
                    if penalty == 0:
                        break
            if penalty > 0:
                unsolved.append((round(penalty, 7), index))
            offsets[index] = point - base[index]
            current_positions[index] = point
            compact_weights[index] = vertex_weights
        print(f"Fit pass {pass_index + 1}: {len(unsolved)} vertices below fitting target.", flush=True)

    for index, vertex in enumerate(shirt.data.vertices):
        for group in [entry.group for entry in vertex.groups]:
            shirt.vertex_groups[group].remove([index])
        for group, weight in zip(affected[index], compact_weights[index]):
            if weight > 1e-7:
                shirt.vertex_groups[group].add([index], weight, "REPLACE")

    positions = base + offsets
    print("Fit displacement percentiles", np.percentile(np.linalg.norm(offsets,axis=1), [50,90,99,100]), flush=True)
    shirt.data.vertices.foreach_set("co", positions.ravel())
    shirt.data.update()
    # Read the stored Blender weights to account for the exporter's float
    # precision before deciding which creased edges can safely be simplified.
    final_weights = np.zeros_like(weights)
    for vertex in shirt.data.vertices:
        for entry in vertex.groups:
            final_weights[vertex.index, entry.group] = entry.weight
    # Frames between the coarse fitting samples can expose brief contacts.
    # Search a small neighbourhood before simplifying edges in those areas.
    pose_trees = [frame[0] for frame in verification_frames]
    pose_bones = np.stack([frame[3] for frame in verification_frames])
    minimum = np.full(len(base), np.inf)
    for index in range(len(base)):
        point = positions[index].copy()
        active = np.flatnonzero(final_weights[index] > 0.)
        matrices = np.einsum('fbmc,b->fmc', pose_bones[:, active], final_weights[index, active])

        def posed_distances(coordinate, order, limit):
            world_points = matrices @ np.append(coordinate, 1.)
            samples = []
            lowest = float('inf')
            for frame in order:
                world = Vector(world_points[frame])
                closest, normal, _, _ = pose_trees[frame].find_nearest(world)
                gap = (world - closest).dot(normal)
                samples.append((gap, frame))
                lowest = min(lowest, gap)
                if lowest < limit:
                    break
            return lowest, samples

        minimum[index], samples = posed_distances(point, range(len(pose_trees)), -float('inf'))
        if minimum[index] >= .00072:
            continue
        order = [frame for _, frame in sorted(samples)]
        best = point
        for step in (.0016, .0034, .0058, .0090):
            for direction in directions:
                candidate = point + step * direction
                gap, _ = posed_distances(candidate, order, .00072)
                if gap >= .00072:
                    best = candidate
                    minimum[index] = gap
                    break
            if minimum[index] >= .00072:
                break
        positions[index] = best
    shirt.data.vertices.foreach_set("co", positions.ravel())
    shirt.data.update()
    print(f"{sum(minimum < .00065)} vertices below cleanup clearance.", flush=True)
    return base, minimum, [(tree, matrices) for tree, _, _, matrices in verification_frames]


def simplify_wrinkles(shirt, body_surface, reference, clearance):
    """Remove stretched edges without moving the remaining fitted vertices."""
    shell = bmesh.new()
    try:
        shell.from_mesh(shirt.data)
        shell.verts.ensure_lookup_table()
        original = {v: np.array(reference[v.index]) for v in shell.verts}
        layer = shell.verts.layers.deform.active
        saved_weights = {v: dict(v[layer].items()) for v in shell.verts}
        gap = {v: clearance[v.index] for v in shell.verts}
        starting_faces = len(shell.faces)
        for _ in range(22):
            faces = list(shell.faces)
            indices = {v: i for i, v in enumerate(shell.verts)}
            triangles = [tuple(indices[v] for v in face.verts) for face in faces]
            tree = BVHTree.FromPolygons([v.co for v in shell.verts], triangles, all_triangles=True)
            issues = {v: 0 for v in shell.verts}
            for i, j in tree.overlap(tree):
                if i < j and not set(triangles[i]).intersection(triangles[j]):
                    for v in (*faces[i].verts, *faces[j].verts):
                        issues[v] += 1
            for _, j in body_surface.overlap(tree):
                for v in faces[j].verts:
                    issues[v] += 1
            # Only unambiguous edge collapses can keep the four openings intact.
            ranks = []
            for edge in shell.edges:
                a, b = edge.verts
                if a.is_boundary != b.is_boundary or (a.is_boundary and not edge.is_boundary):
                    continue
                if len(set(e.other_vert(a) for e in a.link_edges) &
                       set(e.other_vert(b) for e in b.link_edges)) != len(edge.link_faces):
                    continue
                rest_length = np.linalg.norm(original[a] - original[b])
                used_length = edge.calc_length()
                stretching = abs(used_length - rest_length) / max(rest_length, .004)
                escapes = min(gap[a], gap[b]) < .00065
                if not escapes and max(issues[a], issues[b]) < 3:
                    continue
                # Keep the endpoint with a smaller displacement and fewer folds.
                a_cost = np.linalg.norm(np.array(a.co) - original[a]) + .0006 * issues[a]
                b_cost = np.linalg.norm(np.array(b.co) - original[b]) + .0006 * issues[b]
                if escapes:
                    source, target = (a, b) if gap[a] < gap[b] else (b, a)
                else:
                    source, target = (a, b) if a_cost >= b_cost else (b, a)
                if source.is_boundary and len(source.link_edges) <= 2:
                    continue
                rank = stretching + .25 * max(issues[a], issues[b])
                if escapes:
                    rank += 100 + 1000 * (min(gap[target], .004) - gap[source])
                ranks.append((rank, indices[source], source, target))

            chosen = {}
            touched = set()
            clearance_cleanup = any(gap[v] < .00065 for v in shell.verts)
            for rank, _, source, target in sorted(ranks, key=lambda row: (-row[0], row[1])):
                if clearance_cleanup and rank < 100:
                    break
                if source in touched or target in touched:
                    continue
                floor = 1510 if clearance_cleanup else 1730
                if len(shell.faces) - 2 * (len(chosen) + 1) < floor:
                    break
                neighborhood = {e.other_vert(source) for e in source.link_edges}
                neighborhood.update(e.other_vert(target) for e in target.link_edges)
                chosen[source] = target
                touched.update(neighborhood)
                if len(chosen) >= 18:
                    break
            if not chosen:
                break
            bmesh.ops.weld_verts(shell, targetmap=chosen)
            for target in chosen.values():
                deform = target[layer]
                deform.clear()
                for group, weight in saved_weights[target].items():
                    deform[group] = weight
        if count_openings(shell) != 4:
            raise RuntimeError("Simplification changed the openings.")
        lowest_gap = min(gap[v] for v in shell.verts)
        print(f"Removed {starting_faces - len(shell.faces)} triangles during local cleanup. "
              f"Estimated dense minimum clearance {lowest_gap:.6f} m.", flush=True)
        shell.to_mesh(shirt.data)
    finally:
        shell.free()
    shirt.data.update()


def repair_bind_faces(shirt, body_surface, verification_frames):
    """Refine bind-pose triangles while preserving per-vertex motion clearance."""
    shell = bmesh.new()
    try:
        shell.from_mesh(shirt.data)
        shell.verts.index_update()
        layer = shell.verts.layers.deform.active

        def overlap(faces):
            if not faces:
                return 0
            points = [point for face in faces for point in face]
            polygons = [(i, i + 1, i + 2) for i in range(0, len(points), 3)]
            surface = BVHTree.FromPolygons(points, polygons, all_triangles=True)
            return len(body_surface.overlap(surface))

        def collided_faces():
            vertices = list(shell.verts)
            faces = list(shell.faces)
            surface = BVHTree.FromPolygons(
                [v.co for v in vertices],
                [tuple(v.index for v in face.verts) for face in faces],
                all_triangles=True,
            )
            collisions = body_surface.overlap(surface)
            return {faces[j] for _, j in collisions}

        def pose_clear(vertex, position):
            group_weights = list(vertex[layer].items())
            groups, skin_weights = zip(*group_weights)
            slot = np.array((*position, 1.))
            for tree, bone_matrices in verification_frames:
                transform = np.einsum('i,ijk->jk', skin_weights, bone_matrices[list(groups)])
                world = Vector(transform @ slot)
                closest, normal, _, _ = tree.find_nearest(world)
                if (world - closest).dot(normal) < .00063:
                    return False
            return True

        for _ in range(5):
            affected = collided_faces()
            if not affected:
                break
            rotated = 0
            for edge in list(shell.edges):
                if not edge.is_valid:
                    continue
                left = tuple(edge.link_faces)
                if len(left) != 2 or left[0] not in affected and left[1] not in affected:
                    continue
                first, second = edge.verts
                third = next(v for v in left[0].verts if v not in (first, second))
                fourth = next(v for v in left[1].verts if v not in (first, second))
                if third == fourth or shell.edges.get((third,fourth)) is not None:
                    continue
                across = (third.co - fourth.co).length
                if across > 1.7 * edge.calc_length():
                    continue
                before = [[v.co for v in f.verts] for f in left]
                after = [(third.co, fourth.co, first.co), (fourth.co, third.co, second.co)]
                if overlap(after) < overlap(before):
                    if bmesh.utils.edge_rotate(edge, False) is not None:
                        rotated += 1
            if rotated == 0:
                break

        for _ in range(4):
            affected = collided_faces()
            points = sorted({v for f in affected for v in f.verts}, key=lambda v:v.index)
            changed = False
            shell.normal_update()
            for vertex in points:
                old = vertex.co.copy()
                _, nearest_normal, _, _ = body_surface.find_nearest(old)
                normal = vertex.normal.copy()
                ring = list(vertex.link_faces)
                count = overlap([[v.co for v in face.verts] for face in ring])
                if not count:
                    continue
                neighborhood = [edge.other_vert(vertex).co for edge in vertex.link_edges]
                blend = (sum(neighborhood, Vector()) / len(neighborhood) - old)
                if vertex.is_boundary:
                    blend = Vector()
                directions = (normal, nearest_normal, (normal + nearest_normal).normalized(),
                              (normal + blend.normalized()).normalized())
                best = old
                for step in (.001, .0025, .0045, .0075):
                    for direction in directions:
                        point = old + step * direction
                        after = [[point if v == vertex else v.co for v in f.verts] for f in ring]
                        score = overlap(after)
                        if score < count and pose_clear(vertex, point):
                            best, count = point, score
                    if count == 0:
                        break
                if best != old:
                    vertex.co = best
                    changed = True
            if not changed:
                break
        shell.to_mesh(shirt.data)
    finally:
        shell.free()
    shirt.data.update()


def run_checker(source, motion, garment, cpu_render):
    """Run the supplied checker against the exported GLB."""
    from runpy import run_path
    from types import SimpleNamespace

    checker = OUTPUT_DIR / "motion_check.py"
    original_argv = sys.argv
    render_module = bpy.ops.render
    if cpu_render:
        def render_on_cpu(**options):
            scene = bpy.context.scene
            scene.render.engine = "CYCLES"
            scene.cycles.device = "CPU"
            scene.cycles.samples = 16
            scene.cycles.use_denoising = True
            scene.render.image_settings.file_format = "PNG"
            scene.view_settings.view_transform = "AgX"
            if scene.world is None:
                scene.world = bpy.data.worlds.new("Checker studio")
            scene.world.use_nodes = True
            background = scene.world.node_tree.nodes.get("Background")
            background.inputs[0].default_value = (.35, .40, .50, 1.0)
            background.inputs[1].default_value = .65
            if bpy.data.objects.get("Checker key") is None:
                studio = (
                    ("Checker key", (-1.7, -2.6, 3.0), 200, 2.5),
                    ("Checker fill", (1.4, -1.2, 1.3), 55, 1.8),
                    ("Checker rim", (0.0, 1.6, 2.6), 120, 2.0),
                )
                for name, location, energy, size in studio:
                    light = bpy.data.lights.new(name, "AREA")
                    light.energy, light.shape, light.size = energy, "DISK", size
                    obj = bpy.data.objects.new(name, light)
                    scene.collection.objects.link(obj)
                    obj.location = location
                    target = Vector((0.0, 0.0, .53)) - obj.location
                    obj.rotation_euler = target.to_track_quat("-Z", "Y").to_euler()
            return render_module.render(**options)

        # The supplied checker still chooses its poses, cameras and output
        # paths. Only its render operator uses Cycles instead of Workbench.
        bpy.ops.render = SimpleNamespace(render=render_on_cpu)

    try:
        sys.argv = [str(checker), "--", str(source), str(motion), str(garment), str(OUTPUT_DIR)]
        run_path(str(checker), run_name="__main__")
    finally:
        sys.argv = original_argv
        bpy.ops.render = render_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=MASTER_BLEND)
    parser.add_argument("--motion", type=Path, default=MOTION_GLB)
    parser.add_argument("--check", action="store_true", help="Regenerate the motion checker outputs.")
    parser.add_argument("--cpu-render", action="store_true", help="Render checker PNGs without Metal.")
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    options = parser.parse_args(arguments)
    source = options.source.resolve()
    motion = options.motion.resolve()
    blend_path = OUTPUT_DIR / f"{NAME}.blend"
    glb_path = OUTPUT_DIR / f"{NAME}.glb"
    if {source, motion} & {blend_path.resolve(), glb_path.resolve()}:
        raise ValueError("The source must be separate from the generated files.")

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    body = bpy.data.objects["Base_Body"]
    rig = bpy.data.objects["Armature"]
    if len(rig.pose.bones) != 65 or any(
        not bone.name.startswith("mixamorig:") or bone.rotation_mode != "QUATERNION"
        for bone in rig.pose.bones
    ):
        raise RuntimeError("Expected the 65-bone Mixamo quaternion rig.")
    original_pose_mode = rig.data.pose_position
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()

    body_positions, body_triangles = surface_triangles(body)
    body_surface = BVHTree.FromPolygons(body_positions, body_triangles, all_triangles=True)
    shirt = make_shell(rig)
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    copy_weights(body, shirt)
    for _ in range(4):
        for vertex in shirt.data.vertices:
            closest, normal, _, _ = body_surface.find_nearest(vertex.co)
            gap = (vertex.co - closest).dot(normal)
            vertex.co += max(0.0, .0042 - gap) * normal
        shirt.data.update()
    finish_shirt(shirt, rig)
    rig.data.pose_position = original_pose_mode
    bpy.context.view_layer.update()
    reference, clearance, verification_frames = fit_under_motion(body, shirt, rig, motion)
    simplify_wrinkles(shirt, body_surface, reference, clearance)
    repair_bind_faces(shirt, body_surface, verification_frames)
    bpy.context.view_layer.update()
    body_positions, body_triangles = surface_triangles(body)
    body_surface = BVHTree.FromPolygons(body_positions, body_triangles, all_triangles=True)
    verify_fit(body_surface, shirt, rig)
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    rig.select_set(True)
    # Omit the Blender-only armature wrapper while retaining the joint tree.
    result = bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_skins=True,
        export_animations=False,
        export_all_influences=False,
        export_armature_object_remove=True,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export failed: {result}")
    rig.select_set(False)
    file_preferences = bpy.context.preferences.filepaths
    file_preferences.save_version = 0
    file_preferences.file_preview_type = "NONE"
    result = bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), copy=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blend save failed: {result}")
    if options.check:
        run_checker(source, motion, glb_path, options.cpu_render)
        results = json.loads((OUTPUT_DIR / "motion_check.json").read_text())
        if any(clip not in results or results[clip][0] or results[clip][1] < MIN_CLEARANCE
               for clip in ("rest", *CLIPS)):
            raise RuntimeError("The exported GLB failed the motion checker.")


if __name__ == "__main__":
    main()
