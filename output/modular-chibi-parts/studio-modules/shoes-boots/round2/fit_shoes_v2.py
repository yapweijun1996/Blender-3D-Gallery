"""Repair the v1 boot GLB against corrected run poses in Blender 5."""
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from fit_shoes import (evaluated_points, export_glb, intersection_probes, master_scene,
                       posed_points, topology)

V1 = HERE.parent / 'shoes_boots_v1.glb'
V2 = HERE / 'shoes_boots_v2.glb'
SHARED = PARTS / 'body-fix/motion_fixed.glb'
BANKS = (
    (SHARED, ('walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance')),
    (PARTS / 'actions-fix/actions_fixed.glb', ('sit_down', 'sit_idle', 'stand_up', 'hold_item')),
    (PARTS / 'actions-hold2/hold_actions.glb', ('hold_box', 'hold_bag', 'take_item')),
)
MARGIN = .0015
MOVE_LIMIT = .020
ITERATIONS = 14


def write_report(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mount(path, arm):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=False)
    imported = set(bpy.context.scene.objects) - before
    boot, = [obj for obj in imported if obj.type == 'MESH' and obj.vertex_groups]
    world = boot.matrix_world.copy()
    boot.parent = None
    boot.matrix_world = world
    for modifier in list(boot.modifiers):
        boot.modifiers.remove(modifier)
    for obj in imported - {boot}:
        bpy.data.objects.remove(obj, do_unlink=True)
    boot.modifiers.new('Master skin', 'ARMATURE').object = arm
    bpy.context.view_layer.update()
    assert np.allclose(boot.matrix_world, np.eye(4), rtol=0, atol=1e-6)
    return boot


def load_actions(path, names):
    objects, actions = set(bpy.context.scene.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path))
    for obj in set(bpy.context.scene.objects) - objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    created = set(bpy.data.actions) - actions
    return {name: next(action for action in created
                       if action.name == name or action.name.startswith(name + '.'))
            for name in names}


def sample_times(action, steps=2):
    start, end = [float(t) for t in action.frame_range]
    # The integer checker fields round imported GLB endpoint floats.
    first, last = round(start * steps), round(end * steps)
    return [tick / steps for tick in range(first, last + 1)]


def pose(scene, arm, action, time):
    if action != arm.animation_data.action:
        arm.animation_data.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        arm.animation_data.action = action
        if action:
            arm.animation_data.action_slot = action.slots[0]
    scene.frame_set(math.floor(time), subframe=time % 1)
    bpy.context.view_layer.update()


def tree_for(points, faces):
    return BVHTree.FromPolygons(points.tolist(), faces, all_triangles=True)


def positions(obj):
    return np.array([tuple(vertex.co) for vertex in obj.data.vertices], np.float64)


def fit_topology(boot):
    used_groups = {item.group for vertex in boot.data.vertices
                   for item in vertex.groups if item.weight > 0}
    names = [group.name for group in boot.vertex_groups if group.index in used_groups]
    columns = {boot.vertex_groups[name].index: i for i, name in enumerate(names)}
    source = positions(boot)
    weights = np.zeros((len(source), len(names)))
    for vertex in boot.data.vertices:
        for item in vertex.groups:
            if item.weight > 0:
                weights[vertex.index, columns[item.group]] = item.weight
    assert np.allclose(weights.sum(axis=1), 1)
    _, first, weld = np.unique(np.round(np.column_stack((source, weights)), 7),
                              axis=0, return_inverse=True, return_index=True)
    weights = weights[first]
    weights /= weights.sum(axis=1, keepdims=True)
    triangles = weld[topology(boot)]
    neighbors = [set() for _ in first]
    for a, b, c in triangles:
        neighbors[a].update((b, c))
        neighbors[b].update((a, c))
        neighbors[c].update((a, b))
    neighbors = [np.array(sorted(group - {i}), dtype=int) for i, group in enumerate(neighbors)]
    assert all(len(group) for group in neighbors)
    return source[first], weights, weld, triangles, neighbors, names


def cache_run(scene, arm, body, names):
    run = load_actions(SHARED, ('run',))['run']
    bones = [arm.pose.bones[name] for name in names]
    inverse = [bone.bone.matrix_local.inverted() for bone in bones]
    faces = topology(body).tolist()
    times, transforms, trees, body_points = sample_times(run), [], [], []
    for time in times:
        pose(scene, arm, run, time)
        transforms.append([np.asarray(bone.matrix @ inv)[:3] for bone, inv in zip(bones, inverse)])
        points = evaluated_points(body)
        trees.append(tree_for(points, faces))
        body_points.append(points)
    pose(scene, arm, None, 1)
    return times, np.array(transforms), trees, body_points, np.array(faces)


def hit_direction(tree, points):
    hits = [tree.find_nearest(point) for point in points.tolist()]
    location = np.array([tuple(hit[0]) for hit in hits])
    normal = np.array([tuple(hit[1]) for hit in hits])
    delta = points - location
    signed = np.einsum('ij,ij->i', delta, normal)
    length = np.linalg.norm(delta, axis=1)
    direction = delta * np.where(signed[:, None] < 0, -1, 1) / length[:, None].clip(1e-10)
    # An edge or corner can return a nearly tangential point-to-surface vector.
    # The checker's signed distance is measured along the nearest face normal.
    edge = (direction * normal).sum(axis=1) < .96
    direction[edge] = normal[edge]
    return signed, direction


def skin_matrices(weights, transforms):
    return np.einsum('fbci,nb->fnci', transforms[..., :3], weights, optimize=True)


def scan_run(points, weights, cache, triangles, include_triangle_constraints):
    times, transforms, trees, body_positions, body_faces = cache
    skin = skin_matrices(weights, transforms)
    posed = posed_points(points, weights, transforms)
    rows, constraints = [], []
    faces = triangles.tolist()
    for idx, (time, tree, xyz) in enumerate(zip(times, trees, posed)):
        distances, directions = hit_direction(tree, xyz)
        pairs = sorted(tree.overlap(tree_for(xyz, faces)))
        rows.append(dict(frame=time, inside=int((distances < 0).sum()),
                         overlaps=len(pairs), min_signed_m=float(distances.min()),
                         closest_vertex=int(distances.argmin())))
        bad = np.flatnonzero(distances < MARGIN - 2e-6)
        gradient = np.einsum('nij,ni->nj', skin[idx][bad], directions[bad])
        demand = (MARGIN - distances[bad]).clip(0, MOVE_LIMIT)
        constraints.append((bad, gradient, demand))

        if not pairs or not include_triangle_constraints:
            continue
        body_ids, boot_ids = np.array(pairs).T
        corners = triangles[boot_ids]
        bary = intersection_probes(xyz[corners], body_positions[idx][body_faces[body_ids]])
        crossing = np.einsum('nji,nj->ni', xyz[corners], bary)
        distances, directions = hit_direction(tree, crossing)
        for col in range(3):
            use = bary[:, col] > .025
            ids = corners[use, col]
            gradient = np.einsum('nij,ni->nj', skin[idx][ids], directions[use])
            demand = (MARGIN - distances[use]).clip(0, MOVE_LIMIT)
            # Separate repeated corners so each projection sees preceding updates.
            order = np.argsort(ids, kind='stable')
            ids, gradient, demand = ids[order], gradient[order], demand[order]
            runs = np.r_[True, ids[1:] != ids[:-1]] if len(ids) else np.array([], bool)
            rank = np.arange(len(ids)) - np.maximum.accumulate(
                np.where(runs, np.arange(len(ids)), 0)) if len(ids) else np.array([], int)
            for layer in np.unique(rank):
                use = rank == layer
                constraints.append((ids[use], gradient[use], demand[use]))
    return rows, [constraint for constraint in constraints if len(constraint[0])]


def smooth_weights(points, weights, neighbors, names, constraints):
    contact = {int(i) for ids, _, _ in constraints for i in ids}
    near = contact | {int(j) for i in contact for j in neighbors[i]}
    toe_columns = [i for i, name in enumerate(names) if name.endswith('ToeBase')]
    ankle_or_toe = (points[:, 2] > .038) | (weights[:, toe_columns].sum(axis=1) > .06)
    use = np.array(sorted(i for i in near if ankle_or_toe[i]))
    result = weights.copy()
    for _ in range(2):
        average = np.array([result[neighbors[i]].mean(axis=0) for i in use])
        result[use] = .92 * result[use] + .08 * average
    result[result < 1e-7] = 0
    result /= result.sum(axis=1, keepdims=True)
    assert np.count_nonzero(result, axis=1).max() <= 4
    return result


def project(move, constraints, sweeps):
    for _ in range(sweeps):
        for ids, gradient, demand, length_squared in constraints:
            correction = (demand - (move[ids] * gradient).sum(axis=1)).clip(0)
            move[ids] += gradient * (correction / length_squared)[:, None]


def resolve_surface_switches(points, original, weights, cache, active, raw):
    """Resolve nearest-face switches that a local plane approximation can miss."""
    _, transforms, trees, _, _ = cache
    affine = np.einsum('fbci,nb->fnci', transforms, weights[active], optimize=True)
    tests = np.array([d for d in product((-1., 0., 1.), repeat=3) if any(d)])
    for col, vertex in enumerate(active):
        directions = [gradient[ids == vertex] for ids, gradient, _ in raw
                      if np.any(ids == vertex)]
        vectors = np.concatenate([*directions, tests])
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True).clip(1e-9)
        vectors = np.unique(np.round(vectors, 5), axis=0)
        best = points[vertex].copy()
        minimum = -math.inf
        for radius in (0, .00012, .00024, .00036, .0005, .00075, .001, .0014, .002, .003):
            candidates = points[vertex] + vectors * radius if radius else points[[vertex]].copy()
            lengths = np.linalg.norm(candidates - original[vertex], axis=1)
            for p in candidates[np.argsort(lengths, kind='stable')]:
                if np.linalg.norm(p - original[vertex]) > MOVE_LIMIT:
                    continue
                xyz = affine[:, col, :, :3] @ p + affine[:, col, :, 3]
                signed = math.inf
                for tree, location in zip(trees, xyz):
                    loc, normal, _, _ = tree.find_nearest(location)
                    signed = min(signed, sum((location[j] - loc[j]) * normal[j]
                                             for j in range(3)))
                    if signed <= minimum:
                        break
                if signed > minimum:
                    minimum, best = signed, p.copy()
                if minimum >= MARGIN + 4e-6:
                    break
            if minimum >= MARGIN + 4e-6:
                break
        points[vertex] = best


def tuck_rear_collar(points, original, triangles):
    """Keep the affected right liner corner under the original rear leather."""
    location = np.array([-.0817541, .0726702, .0866236])
    vertex = int(np.linalg.norm(original - location, axis=1).argmin())
    assert np.linalg.norm(original[vertex] - location) < 1e-6
    x, _, z = original[vertex] + (.0001, 0, -.0003)
    shell = tree_for(original, triangles.tolist())
    surface, normal, _, _ = shell.ray_cast(Vector((x, .25, z)), Vector((0, -1, 0)))
    assert surface is not None and normal.y > .8
    previous = points[vertex].copy()
    points[vertex] = (x, surface.y - .00065, z)
    return dict(vertex=vertex, untucked_position_m=previous.tolist(),
                rest_position_m=points[vertex].tolist(), rear_occlusion_margin_m=.00065)


def repair(points, weights, triangles, neighbors, names, cache):
    original = points.copy()
    baseline, constraints = scan_run(points, weights, cache, triangles, False)
    new_weights = smooth_weights(points, weights, neighbors, names, constraints)
    history = []
    for iteration in range(ITERATIONS):
        rows, raw = scan_run(points, new_weights, cache, triangles, iteration > 0)
        minimum = min(row['min_signed_m'] for row in rows)
        count = max(row['inside'] for row in rows)
        overlaps = max(row['overlaps'] for row in rows)
        history.append(dict(min_signed_m=minimum, max_inside=count, max_overlaps=overlaps))
        closest = min(rows, key=lambda row: row['min_signed_m'])
        print('FIT', iteration, history[-1], 'constraints', sum(len(c[0]) for c in raw),
              'worst frame/vertex', closest['frame'], closest['closest_vertex'], flush=True)
        if not overlaps and minimum >= MARGIN - 4e-6:
            break
        constraints = [(ids, gradient, demand, np.square(gradient).sum(axis=1).clip(1e-8))
                       for ids, gradient, demand in raw]
        active = np.unique(np.concatenate([ids for ids, *_ in constraints]))
        if iteration >= 3 and not overlaps:
            resolve_surface_switches(points, original, new_weights, cache, active, raw)
            continue
        delta = np.zeros_like(points)
        project(delta, constraints, 12)
        # Smooth the first displacement. Later passes are contact-only so
        # smoothing cannot undo clearance already recovered in another pose.
        for _ in range(3 if iteration == 0 else 0):
            displacement = points + delta - original
            average = np.array([displacement[neighbors[i]].mean(axis=0) for i in active])
            delta[active] += .25 * (average - displacement[active])
            project(delta, constraints, 12)
        total = points + delta - original
        length = np.linalg.norm(total, axis=1)
        points = original + total * np.minimum(1, MOVE_LIMIT / length.clip(1e-10))[:, None]
    else:
        raise RuntimeError(f'Run fitting did not converge: {history[-1]}')

    collar = tuck_rear_collar(points, original, triangles)
    rows, _ = scan_run(points, new_weights, cache, triangles, True)
    assert not any(row['inside'] or row['overlaps'] for row in rows)
    assert min(row['min_signed_m'] for row in rows) >= MARGIN - 4e-6

    shifts = np.linalg.norm(points - original, axis=1)
    return points, new_weights, dict(
        baseline_samples=baseline,
        final_fit_samples=rows,
        baseline_deepest=min(baseline, key=lambda row: row['min_signed_m']),
        final_fit_closest=min(rows, key=lambda row: row['min_signed_m']),
        rear_collar=collar,
        iterations=history,
        welded_vertices=len(points),
        position_changed=int((shifts > 1e-6).sum()),
        max_position_change_m=float(shifts.max()),
        weight_changed=int((abs(new_weights - weights).max(axis=1) > 1e-6).sum()),
        max_weight_change=float(abs(new_weights - weights).max()),
    )


def save_assets(scene, arm, body, boot, points, weights, weld, names):
    previous = positions(boot)
    for vertex, p in zip(boot.data.vertices, points[weld]):
        if np.linalg.norm(p - previous[vertex.index]) > 1e-7:
            vertex.co = p
    for column, name in enumerate(names):
        group = boot.vertex_groups[name]
        for vertex, value in enumerate(weights[weld, column]):
            old = next((item.weight for item in boot.data.vertices[vertex].groups
                        if item.group == group.index), 0)
            if abs(old - value) < 1e-8:
                continue
            if value > 0:
                group.add([vertex], float(value), 'REPLACE')
            else:
                group.remove([vertex])
    boot.data.update()
    boot.name = boot.data.name = V2.stem
    assert len(topology(boot)) <= 3500 and len(arm.data.bones) == 65

    arm.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for obj in scene.objects:
        obj.hide_set(obj not in (boot, arm))
        if obj != boot:
            obj.hide_render = True
    bpy.ops.object.select_all(action='DESELECT')
    for obj in (arm, boot):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = boot
    export_glb(HERE / 'boots_export_raw.glb')

    boot.parent = arm
    body.hide_set(True)
    arm.select_set(False)
    arm.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                from mathutils import Vector
                view = area.spaces.active.region_3d
                view.view_location = (0, -.017, .062)
                view.view_distance = .46
                view.view_rotation = Vector((.65, -.93, .54)).to_track_quat('Z', 'Y')
                area.spaces.active.shading.color_type = 'TEXTURE'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(V2.with_suffix('.blend')), compress=True)


def encode_textures():
    """Keep the source PNG textures in Blender and encode a separate web payload."""
    images = {node.image for material in bpy.data.materials if material.users and material.use_nodes
              for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image
              and node.image.name.startswith('b31fe20b') and len(node.image.pixels)}
    assert len(images) == 3, [image.name for image in images]
    for image in images:
        # Image.save writes raw image channels, with no view transform.
        output = HERE / f'{image.name}.jpg'
        image.file_format = 'JPEG'
        image.save(filepath=str(output), quality=94)
        print('TEXTURE', image.name, output.stat().st_size, flush=True)


def build():
    scene, arm, body = master_scene()
    boot = mount(V1, arm)
    arm.animation_data_create()
    points, weights, weld, triangles, neighbors, names = fit_topology(boot)
    cache = cache_run(scene, arm, body, names)
    points, weights, report = repair(points, weights, triangles, neighbors, names, cache)
    save_assets(scene, arm, body, boot, points, weights, weld, names)
    report['v1_sha256'] = digest(V1)
    report['corrected_motion_sha256'] = digest(SHARED)
    report['margin_m'] = MARGIN
    report['max_displacement_m'] = MOVE_LIMIT
    write_report(HERE / 'fit_report.json', report)
    encode_textures()


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if args == ['--textures']:
        bpy.ops.wm.open_mainfile(filepath=str(V2.with_suffix('.blend')), load_ui=False, use_scripts=False)
        encode_textures()
    else:
        build()
