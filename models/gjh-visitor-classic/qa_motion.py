"""Measure foot and seat contact on a re-imported delivery GLB in background Blender.

blender -b --python-exit-code 2 --python qa_motion.py -- character.glb report.json
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.geometry import intersect_ray_tri


def mesh_points(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    matrix = evaluated.matrix_world
    return [matrix @ v.co for v in evaluated.data.vertices]


def shorts_clearance(parts, depsgraph, front_edge_y):
    lowest = math.inf
    for obj in parts:
        evaluated = obj.evaluated_get(depsgraph)
        points = mesh_points(obj, depsgraph)
        mesh = evaluated.data
        mesh.calc_loop_triangles()
        for tri in mesh.loop_triangles:
            loop = [points[i] for i in tri.vertices]
            for a, b in zip(loop, loop[1:] + loop[:1]):
                if a.y >= front_edge_y:
                    lowest = min(lowest, a.z)
                if (a.y - front_edge_y) * (b.y - front_edge_y) < 0:
                    z = a.z + (b.z - a.z) * (front_edge_y - a.y) / (b.y - a.y)
                    lowest = min(lowest, z)
    return lowest


def upper_thigh_samples(legs):
    # The classic hem is at rest Z=.246. Probe triangle centers clearly above it.
    result = {}
    for obj in legs:
        obj.data.calc_loop_triangles()
        rest_height = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
        result[obj] = [tuple(t.vertices) for t in obj.data.loop_triangles
                       if sum(rest_height[i] for i in t.vertices) / 3 > .262]
        if not result[obj]:
            raise ValueError(f"No testable upper thigh faces on {obj.name}")
    return result


def cuff_apertures(parts):
    # glTF can split a single geometric vertex at material/normal boundaries. Weld by
    # rest position for edge counting and retain the matching evaluated vertex IDs.
    apertures = []
    for obj in parts:
        mesh = obj.data
        ids, world, edges = {}, {}, {}
        for v in mesh.vertices:
            point = obj.matrix_world @ v.co
            key = tuple(round(n, 6) for n in point)
            ids[v.index] = key
            world[key] = v.index
        for poly in mesh.polygons:
            indices = list(poly.vertices)
            for a, b in zip(indices, indices[1:] + indices[:1]):
                edge = tuple(sorted((ids[a], ids[b])))
                edges[edge] = edges.get(edge, 0) + 1
        for sign in (1, -1):
            boundary = [[world[a], world[b]] for (a, b), n in edges.items()
                        if n == 1 and a[0] * sign > 0 and b[0] * sign > 0
                        and .22 < a[2] < .28 and .22 < b[2] < .28]
            if not boundary:
                continue
            apertures.append((obj, boundary))
            # A folded cuff also has an outer mouth. A camera can see down the
            # channel between its inside return and the larger visible opening.
            border = {i for edge in boundary for i in edge}
            edge_ids = [(world[a], world[b]) for a, b in edges]
            outside = {b for a, b in edge_ids if a in border and b not in border}
            outside.update(a for a, b in edge_ids if b in border and a not in border)
            fold = [(a, b) for a, b in edge_ids if a in outside and b in outside]
            if len(fold) == len(boundary):
                apertures.append((obj, fold))
    return apertures


def aperture_triangles(apertures, dep):
    triangles = []
    for obj, edges in apertures:
        points = mesh_points(obj, dep)
        vertices = {i for edge in edges for i in edge}
        center = sum((points[i] for i in vertices), Vector((0, 0, 0))) / len(vertices)
        triangles.extend((center, points[i], points[j]) for i, j in edges)
    return triangles


def exposed_thighs(scene, depsgraph, samples, cuffs):
    # A skin surface facing a camera and reaching it without hitting the outfit is visible.
    count = 0
    directions = [Vector((math.sin(a * math.tau / 12), -math.cos(a * math.tau / 12), .12)).normalized()
                  for a in range(12)]
    apertures = aperture_triangles(cuffs, depsgraph)
    for obj, faces in samples.items():
        points = mesh_points(obj, depsgraph)
        for i, j, k in faces:
            a, b, c = points[i], points[j], points[k]
            center = (a + b + c) / 3
            normal = (b - a).cross(c - a).normalized()
            for direction in directions:
                if normal.dot(direction) <= .055:
                    continue
                hit, *_ = scene.ray_cast(depsgraph, center + direction * .00001, direction, distance=3)
                if hit:
                    continue
                # Looking through an intentional leg opening is legitimate. Other clear
                # sight lines expose skin through a wall or a seam in the shorts.
                through_cuff = False
                for a1, b1, c1 in apertures:
                    crossing = intersect_ray_tri(a1, b1, c1, direction, center, True)
                    if crossing is not None and (crossing - center).dot(direction) > .00001:
                        through_cuff = True
                        break
                if not through_cuff:
                    count += 1
    return count


def finger_isolation(rig, slots):
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    fingers = [f"{name}.{side}" for side in ("L", "R") for name in ("Thumb", "Index", "Middle", "Ring", "Pinky")]

    def positions():
        deps = bpy.context.evaluated_depsgraph_get()
        return {slot: [v for obj in slots[slot] for v in mesh_points(obj, deps)] for slot in fingers}

    rest = positions()
    result = {}
    for name in fingers:
        bone = rig.pose.bones[name]
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = Quaternion((1, 0, 0), math.radians(25))
        bpy.context.view_layer.update()
        current = positions()
        delta = {s: max((a - b).length for a, b in zip(rest[s], current[s])) for s in fingers}
        neighbour = max(v for s, v in delta.items() if s != name)
        result[name] = {"driven_m": delta[name], "other_fingers_max_m": neighbour,
                        "passed": delta[name] > .002 and neighbour < .00001}
        bone.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
    return result


def check(file):
    if not bpy.app.background:
        raise RuntimeError("Use a separate background Blender process for this check.")
    input_hash = hashlib.sha256(file.read_bytes()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(file))
    rig = next(o for o in scene.objects if o.type == "ARMATURE")
    anim = rig.animation_data
    tracks = {t.name: (t.strips[0].action, t.strips[0].action_slot) for t in anim.nla_tracks}
    for track in anim.nla_tracks:
        track.mute = True
    slots = {}
    for obj in scene.objects:
        if obj.type == "MESH":
            slots.setdefault(obj.get("partSlot"), []).append(obj)
    thigh_samples = upper_thigh_samples(slots["Leg.L"] + slots["Leg.R"])
    cuffs = cuff_apertures(slots["Shorts"])
    seat_height, front_edge_y = .14225, .045
    seat_support_y = front_edge_y + .05
    tolerance = .0005
    report = {
        "source": file.name, "sha256": input_hash,
        "blender": bpy.app.version_string, "samples_per_clip": 121,
        "seat_height_m": seat_height, "seat_front_edge_blender_y_m": front_edge_y,
        "support_check_blender_y_m": seat_support_y,
        "contact_tolerance_m": tolerance, "upper_thigh_faces_tested": sum(len(x) for x in thigh_samples.values()),
        "upper_thigh_test": "13 clip times, 12 orbit angles, upper thigh center visibility excluding sight lines through the open cuffs",
        "cuff_boundary_edges": [len(edges) for _, edges in cuffs], "clips": {},
        "scope": "Classic outfit. Geometric checks in background Blender. Seat limited to the shorts over the seat plane.",
    }
    for name in ("idle", "walk", "run", "sit", "stand_up"):
        action, slot = tracks[name]
        anim.action = action
        anim.action_slot = slot
        start, end = action.frame_range
        duration = (end - start) / scene.render.fps
        gait = name in ("walk", "run")
        seated = name in ("sit", "stand_up")
        stance = .6 if name == "walk" else .4
        travel = .115 if name == "walk" else .155
        speed = travel / (duration * stance)
        worst_contact = 0.
        highest_sole = -math.inf
        lowest_sole = min_seat = math.inf
        worst_drift = 0.
        stance_starts = {}
        exposed_probes = 0
        for i in range(121):
            t = i / 120
            frame = start + (end - start) * t
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            dep = bpy.context.evaluated_depsgraph_get()
            if i % 10 == 0:
                exposed_probes += exposed_thighs(scene, dep, thigh_samples, cuffs)
            for side, shift in (("L", 0.), ("R", .5)):
                points = [v for obj in slots["Shoe." + side] for v in mesh_points(obj, dep)]
                bottom = min(p.z for p in points)
                lowest_sole = min(lowest_sole, bottom)
                highest_sole = max(highest_sole, bottom)
                phase = (t + shift) % 1
                stance_now = phase < stance - 1e-7
                if not gait or stance_now:
                    worst_contact = max(worst_contact, abs(bottom))
                if gait and stance_now:
                    # All vertices follow Foot rigidly. One vertex suffices to detect horizontal slip.
                    pos = points[0].y - speed * duration * t
                    step = (side, math.floor(t + shift))
                    stance_starts.setdefault(step, pos)
                    worst_drift = max(worst_drift, abs(pos - stance_starts[step]))
            if seated:
                clearance = shorts_clearance(slots["Shorts"], dep, front_edge_y) - seat_height
                min_seat = min(min_seat, clearance)
                if i == (120 if name == "sit" else 0):
                    endpoint_clearance = clearance
                    support_gap = shorts_clearance(slots["Shorts"], dep, seat_support_y) - seat_height
        sub = {"duration_s": duration, "lowest_sole_m": lowest_sole, "highest_sole_m": highest_sole,
               "max_stance_vertical_error_m": worst_contact, "visible_upper_thigh_probes": exposed_probes}
        passed = lowest_sole >= -tolerance and worst_contact < tolerance and exposed_probes == 0
        if gait:
            sub.update(forward_speed_m_s=speed, max_support_phase_slip_m=worst_drift)
            passed = passed and worst_drift < tolerance and highest_sole > .02
        if seated:
            sub.update(seated_gap_m=endpoint_clearance, rear_support_gap_m=support_gap, minimum_seat_gap_m=min_seat)
            passed = passed and min_seat >= -tolerance and abs(endpoint_clearance) < tolerance and abs(support_gap) < tolerance
        sub["passed"] = passed
        report["clips"][name] = sub
    report["finger_isolation"] = finger_isolation(rig, slots)
    if input_hash != hashlib.sha256(file.read_bytes()).hexdigest():
        raise RuntimeError("The character GLB changed during QA. Repeat on the completed export.")
    report["passed"] = all(v["passed"] for section in ("clips", "finger_isolation") for v in report[section].values())
    return report


if __name__ == "__main__":
    source, dest = (Path(arg).resolve() for arg in sys.argv[sys.argv.index("--") + 1:])
    result = check(source)
    dest.write_text(json.dumps(result, indent=2) + "\n")
    if not result["passed"]:
        raise RuntimeError(f"Motion checks failed. See {dest}")
