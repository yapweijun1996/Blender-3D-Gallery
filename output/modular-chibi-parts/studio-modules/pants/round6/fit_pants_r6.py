"""Refit the round-3 cargo pants against the three corrected action banks."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
SOURCE = HERE.parent / "round3/pants_v3.glb"
JEANS = HERE.parents[1] / "jeans/round5/jeans_v5.glb"
GLB = HERE / "pants_v6.glb"
BANKS = (
    (PARTS / "body-fix/motion_fixed.glb", ("walk", "run", "wave", "jump", "idle", "nod", "dance")),
    (PARTS / "actions-fix/actions_fixed.glb", ("sit_down", "sit_idle", "stand_up", "hold_item")),
    (PARTS / "actions-hold2/hold_actions.glb", ("hold_box", "hold_bag", "take_item")),
)
CLIPS = tuple(clip for _, clips in BANKS for clip in clips)
R3 = runpy.run_path(str(SOURCE.with_name("fit_pants_r3.py")))
BASE = R3["BASE"]
BASE.update(CLIPS=CLIPS, HERE=HERE, GLB=GLB, TRIANGLE_LIMIT=6000)
coords, faces_of = BASE["coordinates"], BASE["triangles"]
read_weights, trim_weights = BASE["body_weights"], BASE["trim_weights"]
average, adjacency = BASE["average"], BASE["mesh_neighbors"]
tree_for, signed_hits = BASE["tree_for"], BASE["signed_hits"]
CAP, MARGIN, FLOOR = .030, .0015, .0005


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def focus_rows(samples, dense=None):
    selected = {0}
    for clip in CLIPS:
        rows = np.asarray([i for i, sample in enumerate(samples) if sample[0] == clip])
        stride = 5 if clip in ("run", "walk", "jump") else 13 if clip in (
            "sit_down", "sit_idle", "stand_up") else 45
        selected.update(rows[::stride])
        selected.add(rows[-1])
    if dense is not None:
        distances, pairs = dense[:2]
        # Keep every vertex's worst pose and the hard triangle failure poses.
        selected.update(np.argmin(distances[:, distances.min(axis=0) < .002], axis=0))
        for clip in CLIPS:
            rows = np.asarray([i for i, sample in enumerate(samples) if sample[0] == clip and pairs[i]], dtype=int)
            selected.update(rows[np.argsort(-pairs[rows], kind="stable")[:24]])
    return np.asarray(sorted(selected), dtype=int)


def setup(path=SOURCE, merge=True):
    scene, arm, body = BASE["load_master"]()
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=merge)
    imported = set(scene.objects) - before
    garment, = [obj for obj in bpy.context.selected_objects if obj in imported and obj.type == "MESH"]
    world = garment.matrix_world.copy()
    garment.parent = arm
    garment.matrix_parent_inverse = Matrix.Identity(4)
    garment.matrix_world = world
    garment.modifiers.clear()
    garment.modifiers.new("Master armature", "ARMATURE").object = arm
    for obj in imported - {garment}:
        bpy.data.objects.remove(obj, do_unlink=True)
    assert np.allclose(garment.matrix_world, np.eye(4), atol=1e-6)
    actions = {}
    for bank, clips in BANKS:
        if bank != BANKS[0][0]:
            scene.render.fps, scene.render.fps_base = 30, 1
        objects = set(scene.objects)
        prior_actions = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(bank))
        new_actions = set(bpy.data.actions) - prior_actions
        for clip in clips:
            action, = [a for a in new_actions if a.name == clip or a.name.startswith(clip + ".")]
            assert len(action.slots) == 1
            actions[clip] = action
        for obj in set(scene.objects) - objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in scene.objects:
        if obj not in (arm, body, garment):
            obj.hide_render = True
            obj.hide_viewport = True
    arm.animation_data.use_nla = False
    set_pose(scene, arm, actions, "rest", 1)
    return scene, arm, body, garment, actions


def set_pose(scene, arm, actions, clip, frame):
    animation = arm.animation_data
    action = actions.get(clip)
    if animation.action != action or action is None:
        animation.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis.identity()
        if action:
            animation.action = action
            animation.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def frames(actions):
    yield "rest", 1.
    for clip, action in actions.items():
        start, end = (round(float(f), 5) for f in action.frame_range)
        times = {start, end}
        times.update(i / 2 for i in range(math.ceil(2 * start), math.floor(2 * end) + 1))
        yield from ((clip, time) for time in sorted(times))


def cache(scene, arm, body, actions, body_faces):
    bones = tuple(arm.pose.bones)
    inverses = [bone.bone.matrix_local.inverted() for bone in bones]
    modes = [bone.rotation_mode for bone in bones]
    poses, transforms = [], []
    face_list = body_faces.tolist()
    for clip, frame in frames(actions):
        set_pose(scene, arm, actions, clip, frame)
        points = BASE["evaluated_coordinates"](body)
        poses.append((clip, frame, tree_for(points, face_list), points))
        transforms.append(np.asarray([bone.matrix @ inv for bone, inv in zip(bones, inverses)])[:, :3])
    assert modes == [bone.rotation_mode for bone in bones]
    print("CACHED", len(poses), "poses", flush=True)
    return poses, np.asarray(transforms, dtype=np.float32)


def boundaries(mesh):
    remaining = {edge for edge in mesh.edges if edge.is_boundary}
    loops = []
    while remaining:
        first = min(remaining, key=lambda e: e.index)
        remaining.remove(first)
        loop = [first]
        start, end = first.verts
        while end != start:
            options = [edge for edge in end.link_edges if edge in remaining]
            if not options:
                break
            edge = min(options, key=lambda e: e.index)
            remaining.remove(edge)
            loop.append(edge)
            end = edge.other_vert(end)
        loops.append(loop)
    return loops


def repair_topology(garment):
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    mesh.verts.index_update()
    mesh.edges.index_update()
    before = len(mesh.verts)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=.000035)
    bmesh.ops.dissolve_degenerate(mesh, edges=list(mesh.edges), dist=.000004)
    mesh.edges.index_update()
    loops = boundaries(mesh)
    detail = []
    for edges in sorted(loops, key=lambda edges: -len(edges)):
        vertices = sorted({v for edge in edges for v in edge.verts}, key=lambda v: v.index)
        center = np.mean([tuple(v.co) for v in vertices], axis=0)
        intentional = (len(edges) >= 12 and (center[2] > .398 or center[2] < .105))
        detail.append({"edges": len(edges), "center_m": center.tolist(), "opening": bool(intentional)})
        if intentional:
            continue
        uv = mesh.loops.layers.uv.active
        source_uv = {v: next((loop[uv].uv.copy() for loop in v.link_loops), None) for v in vertices}
        new = bmesh.ops.holes_fill(mesh, edges=edges, sides=0)["faces"]
        for face in new:
            face.smooth = True
            for loop in face.loops:
                if source_uv[loop.vert] is not None:
                    loop[uv].uv = source_uv[loop.vert]
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    welded = before - len(mesh.verts)
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.update()
    print("TOPOLOGY", welded, detail, flush=True)
    return {"welded_vertices": welded, "boundary_loops": detail}


def prepare(garment, rest, names, body, body_faces, body_points):
    topology = repair_topology(garment)
    mesh = garment.data
    mesh.normals_split_custom_set([(0, 0, 0)] * len(mesh.loops))
    points = coords(mesh)
    graph = adjacency(mesh)
    z = points[:, 2]
    # Relax the pocket flaps and the old thigh dents, while protecting the
    # waistband and ankle hems. Keep original UVs in the mesh corners.
    mask = ((z - .106) / .043).clip(0, 1) * ((.389 - z) / .047).clip(0, 1)
    normal = np.asarray([tuple(v.normal) for v in mesh.vertices], dtype=np.float32)
    rest_distance, radial = signed_hits(rest, points)
    pocket = np.clip((abs(points[:, 0]) - .068) / .025, 0, 1)
    pocket *= np.clip((-.015 - points[:, 1]) / .035, 0, 1)
    pocket *= np.clip((z - .205) / .033, 0, 1) * np.clip((.361 - z) / .025, 0, 1)
    points -= (pocket * (rest_distance - .017).clip(0, .014))[:, None] * radial
    for _ in range(8):
        correction = average(points, graph) - points
        points += (.44 * mask)[:, None] * correction
        points -= (.15 * mask)[:, None] * (average(points, graph) - points)
    points = BASE["rest_project"](points, rest, lo=.0018, hi=.0294)
    mesh.vertices.foreach_set("co", np.asarray(points, dtype=np.float32).ravel())
    mesh.update()
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    modifier = garment.modifiers.new("Triangle budget", "DECIMATE")
    modifier.ratio = min(1, 5470 / len(faces_of(mesh)))
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_move_up(modifier=modifier.name)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = garment.data
    points = coords(mesh)
    graph = adjacency(mesh)
    weights = read_weights(garment, names)
    natural = BASE["transfer_weights"](points, body_points, body_faces, read_weights(body, names),
                                        rest, graph, names)
    z = points[:, 2]
    near_joint = np.maximum(np.exp(-((z - .335) / .055) ** 2),
                            np.exp(-((z - .205) / .055) ** 2))[:, None]
    for _ in range(5):
        weights += .27 * near_joint * (average(weights, graph) - weights)
    weights = trim_weights(weights)
    trial = trim_weights(.72 * weights + .28 * natural)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(JEANS), merge_vertices=True)
    guide, = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    guide_points, guide_faces = coords(guide.data), faces_of(guide.data)
    guide_tree = tree_for(guide_points, guide_faces.tolist())
    hits = [guide_tree.find_nearest(point) for point in points]
    corners = guide_faces[[hit[2] for hit in hits]]
    nearest = np.array([tuple(hit[0]) for hit in hits])
    bary = BASE["barycentric"](guide_points[corners], nearest).clip(0, 1)
    bary /= bary.sum(axis=1, keepdims=True).clip(1e-6)
    guide_weights = np.einsum("ni,nij->nj", bary, read_weights(guide, names)[corners])
    for obj in set(bpy.context.scene.objects) - before:
        bpy.data.objects.remove(obj, do_unlink=True)
    trial = trim_weights(.33 * trial + .67 * guide_weights)
    return points, trial, topology


def scan(points, weights, faces, samples, transforms, body_faces):
    skin = BASE["skin_matrices"](weights, transforms)
    posed = BASE["pose_points"](points, skin)
    distances, pairs, contacts, cuts, failures = BASE["scan"](
        posed, faces, samples, body_faces, points, collect=True)
    return distances, pairs, contacts, cuts, failures, skin


def quality(result):
    distances, pairs = result[:2]
    deficit = np.maximum(0, .00066 - distances)
    cap = np.maximum(0, distances[0] - CAP)
    return float(pairs.sum() * .7 + 2.2e6 * (deficit ** 2).sum()
                 + 1.3e7 * (deficit.max(axis=0) ** 2).sum() + 4e8 * (cap ** 2).sum())


def passed(result):
    distances, pairs = result[:2]
    return not pairs.any() and distances.min() >= .0006 and distances[0].max() <= .02998


def summarize(label, current, samples, points):
    distances, pairs, _, _, failures, _ = current
    report = BASE["report_metrics"](distances, pairs, samples, points, failures)
    print(label, "loss", round(quality(current), 3), "rest max mm", round(1000 * distances[0].max(), 3),
          [(name, row["max_verts_inside"], row["max_triangle_pairs"],
            round(row["min_signed_distance_m"] * 1000, 3), row["minimum_frame"])
           for name, row in report.items()], flush=True)
    return report


def write_geometry(garment, points, weights, names):
    garment.data.vertices.foreach_set("co", np.ascontiguousarray(points, dtype=np.float32).ravel())
    garment.data.update()
    garment.vertex_groups.clear()
    for name, values in zip(names, weights.T):
        group = garment.vertex_groups.new(name=name)
        for vertex in np.flatnonzero(values):
            group.add([int(vertex)], float(values[vertex]), "REPLACE")


def offset(points, anchors, rest):
    shift = points - anchors
    length = np.linalg.norm(shift, axis=1).clip(1e-8)
    points = anchors + shift * np.minimum(1, CAP / length)[:, None]
    return BASE["rest_project"](points, rest, lo=.0009, hi=.0297)


def split_contacts(garment, points, weights, faces, contacts, names):
    write_geometry(garment, points, weights, names)
    mass = Counter(tuple(sorted(ids)) for _, vertices, _, _, _ in contacts
                   if vertices.shape[1] == 3 for ids in vertices)
    hits = [mass[tuple(sorted(row))] for row in faces]
    return BASE["subdivide_contacts"](garment, faces, points, weights, hits)


def texture_padding(garment):
    """Extrude nearest chart colours into eight pixels of unused UV space."""
    mesh = garment.data
    mesh.calc_loop_triangles()
    uv_layer = mesh.uv_layers.active
    uv = np.array([tuple(v.uv) for v in uv_layer.data])
    corner_triangles = np.array([list(t.loops) for t in mesh.loop_triangles])
    material, = garment.data.materials
    for node in material.node_tree.nodes:
        if node.type != "TEX_IMAGE" or node.image is None:
            continue
        src = node.image
        w, h = src.size
        assert max(w, h) <= 1024
        covered = np.zeros((h, w), dtype=bool)
        for tri in uv[corner_triangles] * (w, h):
            origin, b, c = tri
            d, e = b - origin, c - origin
            det = d[0] * e[1] - d[1] * e[0]
            if abs(det) < 1e-8:
                continue
            x0, y0 = np.maximum(0, np.floor(tri.min(axis=0)).astype(int))
            x1, y1 = np.minimum((w, h), np.ceil(tri.max(axis=0)).astype(int))
            dx = np.arange(x0, x1)[None, :] + .5 - origin[0]
            dy = np.arange(y0, y1)[:, None] + .5 - origin[1]
            s = (dx * e[1] - dy * e[0]) / det
            t = (dy * d[0] - dx * d[1]) / det
            covered[y0:y1, x0:x1] |= (s >= 0) & (t >= 0) & (s + t <= 1)
        pixels = np.empty(w * h * 4, dtype=np.float32)
        src.pixels.foreach_get(pixels)
        pixels = pixels.reshape(h, w, 4)
        indices = np.arange(h * w).reshape(h, w)
        seeds = np.where(covered, indices, -1)
        for _ in range(8):
            prior = seeds.copy()
            for y, x in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                sy = slice(max(0, y), min(h, h + y))
                sx = slice(max(0, x), min(w, w + x))
                ty = slice(max(0, -y), min(h, h - y))
                tx = slice(max(0, -x), min(w, w - x))
                target = seeds[ty, tx]
                np.copyto(target, prior[sy, sx], where=target < 0)
        added = (~covered) & (seeds >= 0)
        pixels[added] = pixels.reshape(-1, 4)[seeds[added]]
        src.pixels.foreach_set(pixels.ravel())
        src.pack()
        print("PADDED", src.name, int(added.sum()), flush=True)


def save(arm, body, garment, points, weights, names):
    write_geometry(garment, points, weights, names)
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    for face in mesh.faces:
        face.smooth = True
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.normals_split_custom_set([(0, 0, 0)] * len(garment.data.loops))
    texture_padding(garment)
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(1)
    for obj in list(bpy.context.scene.objects):
        if obj not in (arm, garment):
            bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    garment.name = garment.data.name = GLB.stem
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    assert len(faces_of(garment.data)) <= 6000
    bpy.ops.export_scene.gltf(
        filepath=str(GLB), export_format="GLB", use_selection=True, export_animations=False,
        export_all_influences=False, export_def_bones=False, export_tangents=True,
        export_image_format="JPEG", export_jpeg_quality=93, export_image_quality=93)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(GLB.with_suffix(".blend")))


def fit():
    scene, arm, body, garment, actions = setup()
    names = tuple(arm.pose.bones.keys())
    body_faces = faces_of(body.data)
    samples, transforms = cache(scene, arm, body, actions, body_faces)
    rest = samples[0][2]
    full_samples, full_transforms = samples, transforms
    history = {"source_sha256": digest(SOURCE), "master_sha256": digest(MASTER),
               "weight_guide_sha256": digest(JEANS),
               "action_banks": {path.name: digest(path) for path, _ in BANKS}, "steps": []}
    name = "fit_history.json" if GLB.name == "pants_v6.glb" else ".fast_history.json"
    if "--baseline" in sys.argv:
        source_points = coords(garment.data)
        baseline = scan(source_points, read_weights(garment, names), faces_of(garment.data),
                        samples, transforms, body_faces)
        write_json("round3_baseline.json", summarize("ROUND3", baseline, samples, source_points))
        return
    points, weights, history["topology"] = prepare(garment, rest, names, body, body_faces, samples[0][3])
    faces = faces_of(garment.data)
    graph = adjacency(garment.data)
    anchors = points.copy()
    initial = weights.copy()
    indices = focus_rows(full_samples)
    samples = [full_samples[row] for row in indices]
    transforms = full_transforms[indices]
    current = scan(points, weights, faces, samples, transforms, body_faces)
    old_region_coverage = set(indices)
    for iteration in range(27):
        report = summarize(f"FIT {iteration}", current, samples, points)
        history["steps"].append({"iteration": iteration, "triangles": len(faces), "clips": report})
        write_json(name, history)
        if passed(current) or iteration in (5, 12, 20, 26):
            dense = scan(points, weights, faces, full_samples, full_transforms, body_faces)
            history["dense_fit"] = summarize("DENSE", dense, full_samples, points)
            write_json(name, history)
            if passed(dense) or iteration == 26:
                current, samples = dense, full_samples
                break
            old_region_coverage.update(focus_rows(full_samples, dense))
            indices = np.asarray(sorted(old_region_coverage))
            samples = [full_samples[row] for row in indices]
            transforms = full_transforms[indices]
            current = scan(points, weights, faces, samples, transforms, body_faces)
        distances, pairs, contacts, cuts, _, skin = current
        if iteration in (1, 7) and pairs.any():
            next_points, next_weights = split_contacts(garment, points, weights, faces, contacts, names)
            if len(next_points) != len(points):
                points, weights = next_points, next_weights
                anchors, initial = points.copy(), weights.copy()
                faces, graph = faces_of(garment.data), adjacency(garment.data)
                current = scan(points, weights, faces, samples, transforms, body_faces)
                continue
        target = MARGIN if iteration < 8 else .001
        demand = contacts
        if pairs.any():
            demand += R3["outer_contact_planes"](points, skin, weights, faces, samples, body_faces,
                                                pairs, rest, body, names)
        shift, binding = R3["linear_planes"](points, weights, skin, transforms, demand, graph, rest,
                                            target, rebind=iteration >= 1)
        old_score = quality(current)
        for gain in (1., .5):
            trial_points = offset(points + gain * shift, anchors, rest)
            trial_weights = trim_weights(weights + gain * (binding - weights))
            trial = scan(trial_points, trial_weights, faces, samples, transforms, body_faces)
            if passed(trial) or quality(trial) < old_score:
                points, weights, current = trial_points, trial_weights, trial
                break
        else:
            natural = BASE["transfer_weights"](points, samples[0][3], body_faces,
                                                read_weights(body, names), rest, graph, names)
            trial_points, trial_weights = R3["local_search"](
                points.copy(), weights.copy(), anchors, initial, natural, samples, transforms,
                distances, contacts, graph, .002 if old_score > 35 else .0009,
                faces, direct=True, exact_pairs=True)
            trial = scan(trial_points, trial_weights, faces, samples, transforms, body_faces)
            if passed(trial) or quality(trial) < old_score:
                points, weights, current = trial_points, trial_weights, trial
        if iteration in (2, 6, 11, 17, 22):
            save_checkpoint(garment, points, weights, names, anchors, initial)
    history["final_fit"] = summarize("FINAL FIT", current, samples, points)
    history["fitter_pass"] = bool(passed(current))
    write_json(name, history)
    save(arm, body, garment, points, weights, names)


def save_checkpoint(garment, points, weights, names, anchors, initial):
    write_geometry(garment, points, weights, names)
    np.savez_compressed(HERE / (GLB.stem + "_checkpoint.npz"), anchors=anchors, initial=initial)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / (GLB.stem + "_checkpoint.blend")))


if __name__ == "__main__":
    if "--draft" in sys.argv:
        GLB = HERE / ".fast.glb"
    fit()
