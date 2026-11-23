"""Fit the v1 sandals to the corrected run, then export the module."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import bpy
import numpy as np
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
PARTS = OUT.parents[2]
SOURCE = OUT.parent / "shoes_sandals_v1.glb"
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS / "body-fix/motion_fixed.glb"
EXPORT = OUT / "shoes_sandals_v2.glb"
BLEND = EXPORT.with_suffix(".blend")
MARGIN = 0.0015
GATE = 0.0005
MAX_PUSH = 0.02
BONES = tuple(f"mixamorig:{side}{part}" for side in ("Left", "Right")
              for part in ("Foot", "ToeBase", "Leg"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def import_glb(path, merge=False):
    objects, actions = set(bpy.context.scene.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=merge)
    return set(bpy.context.scene.objects) - objects, set(bpy.data.actions) - actions


def bind(arm, action=None):
    data = arm.animation_data_create()
    data.use_nla = False
    data.action = None
    for bone in arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    if action is not None:
        data.action = action
        data.action_slot = action.slots[0]
    bpy.context.view_layer.update()


def attach(path, merge=False):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    objects, _ = import_glb(path, merge)
    shoe, = (obj for obj in objects if obj.type == "MESH" and obj.vertex_groups)
    bpy.context.view_layer.update()
    world = shoe.matrix_world.copy()
    shoe.parent = arm
    shoe.matrix_world = world
    shoe.modifiers.clear()
    shoe.modifiers.new("Master Skin", "ARMATURE").object = arm
    for obj in objects - {shoe}:
        bpy.data.objects.remove(obj, do_unlink=True)
    bind(arm)
    scene.frame_set(1)
    return scene, arm, body, shoe


def load_bank(path):
    objects, actions = import_glb(path)
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    return {act.name.split(".")[0]: act for act in actions}


def coords(mesh):
    array = np.empty(3 * len(mesh.vertices), dtype=np.float32)
    mesh.vertices.foreach_get("co", array)
    return array.reshape(-1, 3)


def world_coords(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    world = np.asarray(evaluated.matrix_world)
    return coords(evaluated.data) @ world[:3, :3].T + world[:3, 3]


def faces(mesh):
    mesh.calc_loop_triangles()
    return np.array([tuple(face.vertices) for face in mesh.loop_triangles], dtype=np.int32)


def positions_and_weld(shoe):
    raw = coords(shoe.data)
    weights = np.zeros((len(raw), len(BONES)), np.float64)
    names = {group.index: BONES.index(group.name) for group in shoe.vertex_groups if group.name in BONES}
    for v in shoe.data.vertices:
        for group in v.groups:
            if group.weight > 0:
                weights[v.index, names[group.group]] = group.weight
    assert np.allclose(weights.sum(1), 1, atol=1e-6)
    weights /= weights.sum(1)[:, None]
    # glTF splits vertices at material, UV, and normal seams. Keep all corners
    # of each seam together during the fit and copy back to the original indices.
    _, representatives, mapping = np.unique(raw, return_index=True, return_inverse=True, axis=0)
    assert np.allclose(weights, weights[representatives][mapping], atol=1e-6)
    tri = mapping[faces(shoe.data)]
    neighbors = [set() for _ in representatives]
    for a, b, c in tri:
        neighbors[a].update((b, c))
        neighbors[b].update((a, c))
        neighbors[c].update((a, b))
    return raw[representatives].astype(np.float64), weights[representatives], mapping, tri, [
        np.array(sorted(group)) for group in neighbors
    ]


def posed_frames(scene, arm, body, shoe, action):
    bind(arm, action)
    body_tri = faces(body.data)
    left = shoe.matrix_world.inverted() @ arm.matrix_world
    right = arm.matrix_world.inverted() @ shoe.matrix_world
    inverse = [arm.data.bones[name].matrix_local.inverted() for name in BONES]
    first, last = map(round, action.frame_range)
    frames = []
    for tick in range(first * 2, last * 2 + 1):
        frame = tick / 2
        scene.frame_set(tick // 2, subframe=frame % 1)
        pts = world_coords(body)
        tree = BVHTree.FromPolygons(pts.tolist(), body_tri.tolist(), all_triangles=True)
        matrices = np.asarray([shoe.matrix_world @ left @ arm.pose.bones[name].matrix @ inv @ right
                               for name, inv in zip(BONES, inverse)])[:, :3]
        frames.append((frame, pts, tree, matrices))
    return body_tri, frames


def blend_matrices(frames, weights):
    return np.einsum("fbij,vb->fvij", np.array([entry[3] for entry in frames]), weights)


def deform(points, skin):
    return np.einsum("fvij,vj->fvi", skin[..., :3], points) + skin[..., 3]


def signed_nearest(tree, point):
    point = Vector(point)
    hit, normal, _, _ = tree.find_nearest(point)
    return (point - hit).dot(normal), normal


SAMPLES = tuple((a / 6, b / 6, (6 - a - b) / 6) for a in range(7) for b in range(7 - a)
                if max(a, b, 6 - a - b) < 6)
UNIT_BARY = tuple(Vector(axis) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))


def edge_hits(shoe_tri, body_tri):
    upper = [Vector(p) for p in shoe_tri]
    obstacle = [Vector(p) for p in body_tri]
    for face, target in ((upper, obstacle), (obstacle, upper)):
        for i, origin in enumerate(face):
            edge = face[(i + 1) % 3] - origin
            hit = geometry.intersect_ray_tri(*target, edge, origin, True)
            if hit is not None and (hit - origin).dot(edge) >= -1e-9 and (hit - origin).length <= edge.length + 1e-7:
                bary = np.maximum(geometry.barycentric_transform(hit, *upper, *UNIT_BARY), 0)
                yield bary / bary.sum()


def scan(points, skin, tri, body_tri, frames, constraints=True):
    posed = deform(points, skin)
    rows, requirements = [], []
    triangles = tri.tolist()
    for row, (frame, obstacle, tree, _) in enumerate(frames):
        p = posed[row]
        linear = skin[row, ..., :3]
        shell = BVHTree.FromPolygons(p.tolist(), triangles, all_triangles=True)
        overlap = sorted(tree.overlap(shell))
        nearest = [signed_nearest(tree, point) for point in p]
        d = np.array([entry[0] for entry in nearest])
        row_report = dict(frame=frame, inside=int((d < 0).sum()), overlap_pairs=len(overlap),
                          min_signed_m=float(d.min()), deepest_contact_m=float(d.min()),
                          deepest_point_world_m=p[int(d.argmin())].tolist())
        rows.append(row_report)
        if not constraints:
            continue
        for i in np.flatnonzero(d < MARGIN):
            gradient = np.asarray(nearest[i][1]) @ linear[i]
            requirements.append((np.array([i]), gradient[None, :], MARGIN - d[i]))
        colliding_faces = {}
        for other, face in overlap:
            colliding_faces.setdefault(face, []).append(other)
        for face, obstacle_faces in colliding_faces.items():
            ids = tri[face]
            verts = p[ids]
            samples = list(SAMPLES)
            for body_face in obstacle_faces:
                samples.extend(edge_hits(verts, obstacle[body_tri[body_face]]))
            for bary in samples:
                bary = np.asarray(bary)
                sample = bary @ verts
                distance, normal = signed_nearest(tree, sample)
                if distance < row_report["deepest_contact_m"]:
                    row_report["deepest_contact_m"] = float(distance)
                    row_report["deepest_point_world_m"] = sample.tolist()
                if distance < MARGIN:
                    gradient = bary[:, None] * np.einsum("i,vij->vj", normal, linear[ids])
                    requirements.append((ids, gradient, MARGIN - distance))
    return rows, requirements


def summarize(rows):
    deepest = min(rows, key=lambda row: row["deepest_contact_m"])
    return dict(samples=len(rows), max_inside=max(row["inside"] for row in rows),
                max_overlap_pairs=max(row["overlap_pairs"] for row in rows),
                min_signed_m=min(row["min_signed_m"] for row in rows), deepest=deepest)


def smooth_weights(weights, active, neighbors):
    result = weights.copy()
    # The ankle and toe transitions use Foot/Leg or Foot/ToeBase. Pure-weight
    # points enter the blend only when an incident neighbor crosses a transition.
    transition = [i for i in active if len(neighbors[i]) and
                  np.max(np.ptp(weights[np.r_[i, neighbors[i]]], axis=0)) > 0.005]
    for _ in range(2):
        previous = result.copy()
        for i in transition:
            result[i] = 0.85 * previous[i] + 0.15 * previous[neighbors[i]].mean(0)
    local = result[transition]
    local[local < 0.0001] = 0
    result[transition] = local / local.sum(1)[:, None]
    return result, transition


def project(displacement, anchor, requirements, sweeps=24):
    """Project Laplacian proposals onto the sampled outward constraints."""
    if not requirements:
        return displacement
    points = np.zeros((len(requirements), 3), dtype=np.int32)
    gradients = np.zeros((len(requirements), 3, 3))
    depth = np.empty(len(requirements))
    for row, (ids, gradient, value) in enumerate(requirements):
        points[row, :len(ids)] = ids
        gradients[row, :len(ids)] = gradient
        depth[row] = np.clip(value, 0, MAX_PUSH)
    norm = np.square(gradients).sum(axis=(1, 2)).clip(1e-12)
    correction = displacement - anchor
    for _ in range(sweeps):
        residual = depth - np.einsum("rvi,rvi->r", gradients, correction[points])
        violating = np.flatnonzero(residual > 1e-6)
        if not len(violating):
            break
        for row in violating[np.argsort(-residual[violating], kind="stable")]:
            ids, gradient = points[row], gradients[row]
            missing = depth[row] - np.sum(gradient * correction[ids])
            if missing > 1e-6:
                np.add.at(correction, ids, gradient * (missing / norm[row]))
        displacement = anchor + correction
        lengths = np.linalg.norm(displacement, axis=1)
        displacement *= np.minimum(1, MAX_PUSH / lengths.clip(1e-12))[:, None]
        correction = displacement - anchor
    missing = depth - np.einsum("rvi,rvi->r", gradients, correction[points])
    if missing.max() > 2e-6:
        raise RuntimeError(f"Contact projection fell short by {missing.max():.6g} m")
    return anchor + correction


def fit(scene, arm, body, shoe):
    points, weights, mapping, tri, neighbors = positions_and_weld(shoe)
    action = load_bank(MOTION)["run"]
    body_tri, frames = posed_frames(scene, arm, body, shoe, action)
    skin = blend_matrices(frames, weights)
    # Check the cached linear skinning against the evaluated Blender mesh.
    error = np.abs(deform(points, skin)[-1][mapping] - world_coords(shoe)).max()
    assert error < 1e-6, error
    rows, requirements = scan(points, skin, tri, body_tri, frames)
    baseline = summarize(rows)
    print("BASELINE", baseline, flush=True)
    report("run_v1_half_frames.json", rows)
    old_weights = weights
    active = np.unique(np.concatenate([ids for ids, _, _ in requirements]))
    weights, transition = smooth_weights(weights, active, neighbors)
    skin = blend_matrices(frames, weights)
    displacement = np.zeros_like(points)
    history = []
    for attempt in range(14):
        rows, requirements = scan(points + displacement, skin, tri, body_tri, frames)
        summary = summarize(rows)
        history.append(summary)
        print("FIT", attempt, summary, "constraints", len(requirements), flush=True)
        if attempt and summary["max_inside"] == summary["max_overlap_pairs"] == 0 and summary["min_signed_m"] >= GATE:
            break
        anchor = displacement.copy()
        if requirements:
            active = np.unique(np.concatenate([active, *(ids for ids, _, _ in requirements)]))
        # Keep the linearized limits through each Laplacian pass. Keep all
        # non-contact vertices fixed, including neighbors used as the boundary.
        displacement = project(displacement, anchor, requirements)
        for _ in range(3):
            trial = displacement.copy()
            for i in active:
                if len(neighbors[i]):
                    trial[i] += 0.24 * (displacement[neighbors[i]].mean(0) - displacement[i])
            displacement = project(trial, anchor, requirements)
    else:
        raise RuntimeError(f"Run fit failed: {history[-1]}")
    # Baseline and final measured values stay with the build for reproduction.
    report("fit_metrics.json", dict(v1_sha256=digest(SOURCE), run_sha256=digest(MOTION),
           master_sha256=digest(MASTER), baseline=baseline, iterations=history,
           affected_vertices=int((np.linalg.norm(displacement, axis=1) > 1e-9).sum()),
           welded_vertices=len(points), smoothed_weight_vertices=len(transition),
           maximum_weight_change=float(np.abs(weights - old_weights).max()),
           maximum_push_m=float(np.linalg.norm(displacement, axis=1).max()),
           rms_push_m=float(np.sqrt(np.mean(np.square(displacement).sum(axis=1)))),
           cache_error_m=float(error)))
    report("run_fit_half_frames.json", rows)
    final = (points + displacement)[mapping].astype(np.float32)
    shoe.data.vertices.foreach_set("co", final.ravel())
    shoe.data.update()
    groups = {group.name: group for group in shoe.vertex_groups}
    for i, index in enumerate(mapping):
        for bone, old, new in zip(BONES, old_weights[index], weights[index]):
            if abs(old - new) <= 1e-7:
                continue
            group = groups.get(bone)
            if new > 0:
                if group is None:
                    group = shoe.vertex_groups.new(name=bone)
                    groups[bone] = group
                group.add([i], float(new), "REPLACE")
            elif group is not None:
                group.remove([i])
    bind(arm)
    scene.frame_set(1)

def pack_demo_maps(scene, shoe):
    """Keep the base-color JPEG and resize the two data maps to packed PNGs."""
    materials = set(shoe.data.materials)
    image_nodes = [node for material in materials for node in material.node_tree.nodes
                   if node.type == "TEX_IMAGE" and node.image]
    data_maps = {node.image for node in image_nodes if node.image.name.endswith(("_normal", "_rm"))}
    assert len(data_maps) == 2
    view = scene.view_settings
    view.view_transform = "Standard"
    view.look = "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 45
    with TemporaryDirectory(prefix=".maps-", dir=OUT) as folder:
        for image in sorted(data_maps, key=lambda image: image.name):
            rgba = np.empty(4 * image.size[0] * image.size[1], dtype=np.float32)
            image.pixels.foreach_get(rgba)
            sample = bpy.data.images.new("Resampling buffer", width=image.size[0], height=image.size[1])
            sample.colorspace_settings.name = "Non-Color"
            sample.pixels.foreach_set(rgba)
            sample.scale(512, 512)
            path = Path(folder) / f"{image.name}.png"
            sample.save_render(str(path), scene=scene)
            packed = bpy.data.images.load(str(path), check_existing=False)
            packed.colorspace_settings.name = "Non-Color"
            packed.pack()
            for node in image_nodes:
                if node.image == image:
                    node.image = packed
            name = image.name
            bpy.data.images.remove(image)
            bpy.data.images.remove(sample)
            packed.name = name
            packed.filepath = f"//{name}.png"


def save_module(scene, arm, shoe):
    for obj in list(scene.objects):
        if obj not in (arm, shoe):
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data_clear()
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.object.select_all(action="DESELECT")
    shoe.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = shoe
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=str(EXPORT), export_format="GLB", use_selection=True,
        export_yup=True, export_animations=False, export_skins=True,
        export_def_bones=False, export_armature_object_remove=True,
        export_all_influences=False, export_materials="EXPORT", export_tangents=True,
    )


if __name__ == "__main__":
    scene, arm, body, shoe = attach(SOURCE)
    fit(scene, arm, body, shoe)
    pack_demo_maps(scene, shoe)
    save_module(scene, arm, shoe)
