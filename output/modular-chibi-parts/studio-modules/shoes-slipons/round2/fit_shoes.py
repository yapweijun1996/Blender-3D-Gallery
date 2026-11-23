"""Refit v1 against the corrected run bank with Blender's evaluated master rig.

The exported v1 buffers remain authoritative for topology, UVs and bind data.
Only contact geometry, nearby skin weights, affected shading frames and image
payloads are replaced. Run with the adjacent guarded Blender launcher.
"""

from itertools import product
from pathlib import Path
import hashlib
import json
import math
import struct

import bpy
import numpy as np
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
SOURCE = HERE.parent / "shoes_slipons_v1.glb"
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS / "body-fix/motion_fixed.glb"
ACTIONS = PARTS / "actions-fix/actions_fixed.glb"
CARRY = PARTS / "actions-hold2/hold_actions.glb"
EXPORT = HERE / "shoes_slipons_v2.glb"
BLEND = HERE / "shoes_slipons_v2.blend"
GATE = .0005
MARGIN = .0015
LIMIT = .02
BUDGET = math.floor(1.2 * 1024 ** 2)
SHARED = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
ADDED = ("sit_down", "sit_idle", "stand_up", "hold_item")
CARRY_NAMES = ("hold_box", "hold_bag", "take_item")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


class Glb:
    def __init__(self, path):
        blob = path.read_bytes()
        size, = struct.unpack_from("<I", blob, 12)
        self.doc = json.loads(blob[20:20 + size])
        self.views = [
            blob[28 + size + view.get("byteOffset", 0):28 + size
                 + view.get("byteOffset", 0) + view["byteLength"]]
            for view in self.doc["bufferViews"]
        ]
        self.primitives = self.doc["meshes"][0]["primitives"]
        self.joints = [self.doc["nodes"][i]["name"] for i in self.doc["skins"][0]["joints"]]

    def array(self, accessor):
        spec = self.doc["accessors"][accessor]
        view = self.doc["bufferViews"][spec["bufferView"]]
        assert not view.get("byteStride")
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[spec["type"]]
        dtype = {5126: "<f4", 5121: "u1", 5123: "<u2"}[spec["componentType"]]
        return np.frombuffer(self.views[spec["bufferView"]], dtype=dtype,
                             offset=spec.get("byteOffset", 0), count=spec["count"] * width
                             ).reshape(-1, width).copy()

    def update(self, accessor, values, bounds=False):
        spec = self.doc["accessors"][accessor]
        data = np.asarray(values, dtype={5126: "<f4", 5121: "u1"}[spec["componentType"]])
        assert not spec.get("byteOffset") and data.shape[0] == spec["count"]
        self.views[spec["bufferView"]] = data.tobytes()
        if bounds:
            spec["min"], spec["max"] = data.min(axis=0).tolist(), data.max(axis=0).tolist()

    def encode(self):
        binary = bytearray()
        for view, payload in zip(self.doc["bufferViews"], self.views, strict=True):
            binary.extend(bytes((-len(binary)) % 4))
            view["byteOffset"], view["byteLength"] = len(binary), len(payload)
            binary.extend(payload)
        self.doc["buffers"][0]["byteLength"] = len(binary)
        binary.extend(bytes((-len(binary)) % 4))
        header = json.dumps(self.doc, separators=(",", ":")).encode()
        header += b" " * ((-len(header)) % 4)
        return (struct.pack("<4sIIII", b"glTF", 2, 28 + len(header) + len(binary),
                            len(header), 0x4E4F534A)
                + header + struct.pack("<II", len(binary), 0x004E4942) + binary)


def blender_axes(gltf):
    return np.column_stack((gltf[:, 0], -gltf[:, 2], gltf[:, 1]))


def gltf_axes(blender):
    return np.column_stack((blender[:, 0], blender[:, 2], -blender[:, 1]))


def shoe_mesh(glb):
    # V1 duplicates vertices for UVs, tangents and the two materials.
    # Keep each near-coincident position and its weights welded for fitting.
    bones = [i for i, name in enumerate(glb.joints)
             if name.endswith(("LeftLeg", "LeftFoot", "LeftToeBase",
                               "RightLeg", "RightFoot", "RightToeBase"))]
    bone_column = {j: i for i, j in enumerate(bones)}
    table, points, weights, all_faces, maps = {}, [], [], [], []
    for primitive in glb.primitives:
        attributes = primitive["attributes"]
        xyz = blender_axes(glb.array(attributes["POSITION"]))
        rows = glb.array(attributes["WEIGHTS_0"])
        joints = glb.array(attributes["JOINTS_0"])
        mapping = []
        for p, row, ids in zip(xyz, rows, joints, strict=True):
            key = tuple(np.rint(p.astype(float) * 1e7).astype(int))
            w = np.zeros(len(bones))
            for value, joint in zip(row, ids, strict=True):
                if value > 0:
                    w[bone_column[joint]] = value
            if key not in table:
                table[key] = len(points)
                points.append(p)
                weights.append(w)
            u = table[key]
            assert np.max(np.abs(weights[u] - w)) < 1e-7
            mapping.append(u)
        maps.append(np.asarray(mapping))
        all_faces.extend(maps[-1][glb.array(primitive["indices"]).reshape(-1, 3)])
    return np.asarray(points, dtype=float), np.asarray(weights), np.asarray(all_faces), maps, bones


def imported(path):
    before = set(bpy.context.scene.objects)
    actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return set(bpy.context.scene.objects) - before, set(bpy.data.actions) - actions


def load_bank(path, expected):
    objects, actions = imported(path)
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    matched = {name: next(a for a in actions if a.name == name or a.name.startswith(name + "."))
               for name in expected}
    return matched


def load_master():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    assert len(arm.data.bones) == 65
    arm.animation_data_create().use_nla = False
    return scene, arm, body


def bind(arm, action):
    data = arm.animation_data_create()
    data.use_nla = False
    data.action = None
    for bone in arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    if action is not None:
        data.action = action
        data.action_slot = action.slots[0]
    bpy.context.view_layer.update()


def set_frame(scene, frame):
    integer = math.floor(frame)
    scene.frame_set(integer, subframe=frame - integer)


def frames(action, rate=2):
    first, last = map(float, action.frame_range)
    return sorted({first, last, *[tick / rate for tick in
                                 range(math.ceil(first * rate), math.floor(last * rate) + 1)]})


def mesh_faces(obj):
    obj.data.calc_loop_triangles()
    return np.asarray([f.vertices[:] for f in obj.data.loop_triangles])


def world_coords(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    xyz = np.empty(3 * len(evaluated.data.vertices), dtype=np.float32)
    evaluated.data.vertices.foreach_get("co", xyz)
    matrix = np.asarray(evaluated.matrix_world)
    return xyz.reshape((-1, 3)) @ matrix[:3, :3].T + matrix[:3, 3]


def nearest(tree, positions):
    distances, normals = [], []
    for position in positions:
        hit, normal, _, _ = tree.find_nearest(position)
        distances.append((Vector(position) - hit).dot(normal))
        normals.append(normal)
    return np.asarray(distances), np.asarray(normals)


def run_poses(scene, arm, body, action, joints):
    bind(arm, action)
    faces = mesh_faces(body).tolist()
    bones = [arm.pose.bones[name] for name in joints]
    inv_bind = [bone.bone.matrix_local.inverted() for bone in bones]
    cache = []
    for frame in frames(action):
        set_frame(scene, frame)
        body_points = world_coords(body).tolist()
        tree = BVHTree.FromPolygons(body_points, faces, all_triangles=True)
        matrices = np.asarray([arm.matrix_world @ bone.matrix @ inv for bone, inv in
                               zip(bones, inv_bind, strict=True)])[:, :3]
        cache.append((frame, tree, matrices, body_points))
    return cache, np.asarray(faces)


def neighbors_for(points, faces):
    neighbors = [set() for _ in points]
    for a, b, c in faces:
        neighbors[a].update((b, c))
        neighbors[b].update((a, c))
        neighbors[c].update((a, b))
    return [sorted(group - {i}) for i, group in enumerate(neighbors)]


def resmooth_weights(weights, neighbors, support):
    result = weights.copy()
    for _ in range(2):
        old = result.copy()
        for v in sorted(support):
            # Restrict smoothing to the same Foot/ToeBase/Leg chain. The
            # same row also applies to all UV and material copies of v.
            mean = old[neighbors[v]].mean(axis=0)
            result[v] = .85 * old[v] + .15 * mean
    result[result < 1e-5] = 0
    return result / result.sum(axis=1, keepdims=True)


def segment_witnesses(shoe, body):
    """Find both ends of the triangle intersection segment where possible."""
    hits = []
    for edges, plane in ((shoe, body), (body, shoe)):
        for a, b in zip(edges, edges[1:] + edges[:1]):
            direction = b - a
            length = direction.length
            if length <= 1e-9:
                continue
            unit = direction / length
            hit = geometry.intersect_ray_tri(*plane, unit, a, True)
            if hit is not None and -1e-6 <= (hit - a).dot(unit) <= length + 1e-6:
                if all((hit - other).length > 1e-6 for other in hits):
                    hits.append(hit)
    if len(hits) > 1:
        hits.append(sum(hits, Vector()) / len(hits))
    return hits


def add_constraint(rows, ids, factors, skin, normal, distance, offsets):
    gradient = (np.einsum("nki,k->ni", skin[ids, :, :3], normal)
                * np.asarray(factors)[:, None])
    needed = float(np.clip(MARGIN - distance, 0, LIMIT))
    if needed > 0:
        lower = needed + float(np.sum(gradient * offsets[ids]))
        rows.append((np.asarray(ids), gradient, lower))


def inspect_run(original, offsets, skins, faces, cache, body_faces, counts_per_vertex):
    rows, support, samples = [], set(), []
    positions = original + offsets
    shoe_faces = faces.tolist()
    basis = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    barycentric = np.asarray([(1/3, 1/3, 1/3), (.5, .5, 0), (.5, 0, .5), (0, .5, .5)])
    for (frame, tree, _, body_points), skin in zip(cache, skins, strict=True):
        posed = np.einsum("nci,ni->nc", skin[..., :3], positions) + skin[..., 3]
        distances, normals = nearest(tree, posed)
        overlaps = sorted(tree.overlap(BVHTree.FromPolygons(posed.tolist(), shoe_faces, all_triangles=True)))
        worst = int(np.argmin(distances))
        samples.append({"frame": frame, "inside": int(counts_per_vertex[distances < 0].sum()),
                        "overlaps": len(overlaps), "min_signed_m": float(distances[worst]),
                        "nearest_vertex_world_m": posed[worst].tolist(), "vertex": worst})
        for v in np.flatnonzero(distances < GATE + .00001):
            support.add(int(v))
            add_constraint(rows, [v], [1], skin, normals[v], distances[v], offsets)
        for body_i, shoe_i in overlaps:
            ids = faces[shoe_i]
            support.update(map(int, ids))
            shoe = [Vector(p) for p in posed[ids]]
            body = [Vector(body_points[i]) for i in body_faces[body_i]]
            face_normal = np.asarray((body[1] - body[0]).cross(body[2] - body[0]).normalized())
            for point in segment_witnesses(shoe, body):
                factors = np.asarray(geometry.barycentric_transform(point, *shoe, *basis)).clip(0, 1)
                if factors.sum() > 0:
                    add_constraint(rows, ids, factors / factors.sum(), skin, face_normal, 0, offsets)
        for shoe_i in sorted({s for _, s in overlaps}):
            ids = faces[shoe_i]
            distances, normals = nearest(tree, barycentric @ posed[ids])
            for factors, distance, normal in zip(barycentric, distances, normals, strict=True):
                add_constraint(rows, ids, factors, skin, normal, distance, offsets)
    return rows, support, samples


def project(offsets, rows):
    for _ in range(250):
        peak = 0.0
        for ids, gradient, lower in rows:
            previous = offsets[ids]
            gap = lower - np.sum(gradient * previous)
            if gap <= 2e-7:
                continue
            peak = max(peak, gap)
            moved = previous + gradient * (gap / max(1e-9, np.sum(gradient ** 2)))
            scale = np.minimum(1, LIMIT / np.linalg.norm(moved, axis=1).clip(1e-12))
            offsets[ids] = moved * scale[:, None]
        if peak <= 2e-7:
            break
    return float(max((lower - np.sum(g * offsets[ids]) for ids, g, lower in rows), default=0.0))


def laplacian(offsets, support, neighbors, rows):
    for _ in range(3):
        previous = offsets.copy()
        for v in sorted(support):
            offsets[v] = .72 * previous[v] + .28 * previous[neighbors[v]].mean(axis=0)
        if project(offsets, rows) > 1e-6:
            raise RuntimeError("Laplacian step could not preserve the clearance constraints")


def fit(original, weights, faces, maps, cache, body_faces):
    matrices = np.stack([entry[2] for entry in cache])
    counts = np.bincount(np.concatenate(maps), minlength=len(original))
    offsets = np.zeros_like(original)
    inspect = lambda skins: inspect_run(original, offsets, skins, faces, cache, body_faces, counts)
    baseline_rows, support, baseline = inspect(np.einsum("fbci,nb->fnci", matrices, weights))
    neighbors = neighbors_for(original, faces)
    # Smooth the original collision patch before building active geometry
    # constraints so the new weights are included in all pose measurements.
    revised = resmooth_weights(weights, neighbors, support)
    skins = np.einsum("fbci,nb->fnci", matrices, revised)
    rows, more_support, samples = inspect(skins)
    # Keep the v1 contact constraints even when weight smoothing alone
    # would clear a contact. Project after each pass to retain the margin.
    rows = baseline_rows + rows
    support.update(more_support)
    iterations = []
    worst = lambda samples: min(samples, key=lambda row: row["min_signed_m"])
    for iteration in range(20):
        state = {"iteration": iteration, "active_vertices": len(support), "constraints": len(rows),
                 "max_vertices_inside": max(s["inside"] for s in samples),
                 "max_triangle_pairs": max(s["overlaps"] for s in samples),
                 "worst": worst(samples)}
        iterations.append(state)
        print("FIT", json.dumps(state), flush=True)
        if state["max_vertices_inside"] == state["max_triangle_pairs"] == 0 and (
                state["worst"]["min_signed_m"] >= GATE + .00001):
            break
        error = project(offsets, rows)
        if error > 1e-6:
            raise RuntimeError(f"Run constraints were infeasible by {error:.8f} m")
        laplacian(offsets, support, neighbors, rows)
        new_rows, more_support, samples = inspect(skins)
        support.update(more_support)
        rows.extend(new_rows)
    else:
        raise RuntimeError("Run fit did not reach the clearance and overlap gates")
    displacements = np.linalg.norm(offsets, axis=1)
    summary = {"source_glb_sha256": digest(SOURCE), "corrected_run_sha256": digest(MOTION),
               "margin_m": MARGIN, "max_allowed_offset_m": LIMIT,
               "laplacian_passes_per_iteration": 3, "baseline": baseline,
               "baseline_constraints": len(baseline_rows), "baseline_deepest": worst(baseline),
               "iterations": iterations, "final": samples,
               "fitted_vertices": int((displacements > 1e-9).sum()),
               "reweighted_vertices": int((np.max(abs(weights - revised), axis=1) > 1e-7).sum()),
               "largest_weight_change": float(np.max(abs(weights - revised))),
               "max_displacement_m": float(displacements.max()),
               "mean_displacement_on_moved_vertices_m": float(displacements[displacements > 1e-9].mean())}
    summary["max_constraint_residual_m"] = float(max(
        (max(0, limit - np.sum(gradient * offsets[ids])) for ids, gradient, limit in rows),
        default=0.0))
    return offsets, revised, summary


def update_mesh(glb, offsets, weights, maps, bones, original_weights):
    # Rotate each affected source normal/tangent by the same change in
    # incident face direction, preserving the original split normal seams.
    shading = []
    incident = {}
    for primitive, mapping in zip(glb.primitives, maps, strict=True):
        a = primitive["attributes"]
        indices = glb.array(primitive["indices"]).reshape(-1, 3)
        normals = glb.array(a["NORMAL"])
        positions = glb.array(a["POSITION"])
        modified = positions + gltf_axes(offsets[mapping])
        keys = [(int(i), *map(float, n)) for i, n in zip(mapping, normals, strict=True)]
        before, after = (np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
                         for t in (positions[indices], modified[indices]))
        for face, v1, v2 in zip(indices, before, after, strict=True):
            for index in face:
                pair = incident.setdefault(keys[index], np.zeros((2, 3)))
                pair[0] += v1
                pair[1] += v2
        shading.append((keys, normals, glb.array(a["TANGENT"])))
        glb.update(a["POSITION"], modified, bounds=True)
        j = glb.array(a["JOINTS_0"])
        w = glb.array(a["WEIGHTS_0"])
        for index, v in enumerate(mapping):
            if np.max(np.abs(weights[v] - original_weights[v])) < 1e-7:
                continue
            order = [k for k in np.argsort(-weights[v]) if weights[v, k] > 0]
            assert len(order) <= 4
            j[index, :] = 0
            w[index, :] = 0
            j[index, :len(order)] = [bones[k] for k in order]
            w[index, :len(order)] = weights[v, order]
        glb.update(a["JOINTS_0"], j)
        glb.update(a["WEIGHTS_0"], w)
    rotations = {key: Vector(before).rotation_difference(Vector(after))
                 for key, (before, after) in incident.items()
                 if np.linalg.norm(after - before) > 1e-12
                 and min(np.linalg.norm(before), np.linalg.norm(after)) > 1e-12}
    for primitive, (keys, normals, tangents) in zip(glb.primitives, shading, strict=True):
        for i, key in enumerate(keys):
            if key not in rotations:
                continue
            r = rotations[key]
            n = (r @ Vector(normals[i])).normalized()
            t = r @ Vector(tangents[i, :3])
            normals[i] = n
            tangents[i, :3] = (t - n * n.dot(t)).normalized()
        glb.update(primitive["attributes"]["NORMAL"], normals)
        glb.update(primitive["attributes"]["TANGENT"], tangents)


def encode_textures(glb):
    # Use the same three maps at 1024 px. Keep channels in the source
    # colour space and use high JPEG quality with GLB-core image support.
    cache = HERE / ".runtime/textures"
    cache.mkdir(parents=True, exist_ok=True)
    choices = []
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    for i, image in enumerate(glb.doc["images"]):
        original = cache / f"{i}.png"
        original.write_bytes(glb.views[image["bufferView"]])
        asset = bpy.data.images.load(str(original), check_existing=False)
        asset.colorspace_settings.name = "sRGB" if image["name"].endswith("_basecolor") else "Non-Color"
        options = {}
        for quality in range(85, 101):
            target = cache / f"{i}_{quality}.jpg"
            scene.render.image_settings.quality = quality
            asset.save_render(str(target), scene=scene)
            options[quality] = target.read_bytes()
        choices.append(options)
        bpy.data.images.remove(asset)
    image_views = {i["bufferView"] for i in glb.doc["images"]}
    geometry_size = sum(len(view) for i, view in enumerate(glb.views) if i not in image_views)
    approximate_overhead = len(json.dumps(glb.doc, separators=(",", ":"))) + geometry_size + 100
    # Prefer preserving the diffuse map, then the normal map, when equal
    # aggregate quality settings produce alternative payload combinations.
    possibilities = [q for q in product(*[sorted(o) for o in choices])
                     if approximate_overhead + sum(len(o[k]) for o, k in zip(choices, q)) <= BUDGET]
    if not possibilities:
        raise RuntimeError("These texture encodings exceed the GLB budget")
    qualities = max(possibilities, key=lambda q: (sum(q), min(q), q[1], q[0], q[2]))
    result = {}
    for image, options, quality in zip(glb.doc["images"], choices, qualities, strict=True):
        image["mimeType"] = "image/jpeg"
        data = options[quality]
        assert data[:2] == b"\xff\xd8"
        glb.views[image["bufferView"]] = data
        result[image["name"]] = {"jpeg_quality": quality, "bytes": len(data), "size": [1024, 1024]}
    return result


def save_blend():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects, _ = imported(EXPORT)
    shoes, = [obj for obj in objects if obj.type == "MESH" and obj.vertex_groups]
    arm, = [obj for obj in objects if obj.type == "ARMATURE"]
    for obj in objects - {shoes, arm}:
        # The importer may store a hidden custom bone-shape object.
        for bone in arm.pose.bones:
            if bone.custom_shape == obj:
                bone.custom_shape = None
        bpy.data.objects.remove(obj, do_unlink=True)
    for image in bpy.data.images:
        if image.source == "FILE" and image.users and not image.packed_file:
            image.pack()
    for _ in range(3):
        bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.object.select_all(action="DESELECT")
    shoes.select_set(True)
    bpy.context.view_layer.objects.active = shoes
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.region_3d.view_location = (0, -.02, .04)
                view.region_3d.view_distance = .59
                view.region_3d.view_rotation = Vector((.29, -.53, .30)).to_track_quat("Z", "Y")
                view.overlay.show_overlays = False
                view.shading.color_type = "TEXTURE"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)


def main():
    glb = Glb(SOURCE)
    original, weights, faces, maps, bone_ids = shoe_mesh(glb)
    scene, arm, body = load_master()
    run = load_bank(MOTION, SHARED)["run"]
    cache, body_faces = run_poses(scene, arm, body, run, [glb.joints[j] for j in bone_ids])
    offsets, revised, summary = fit(original, weights, faces, maps, cache, body_faces)
    update_mesh(glb, offsets, revised, maps, bone_ids, weights)
    summary["textures"] = encode_textures(glb)
    encoded = glb.encode()
    assert len(encoded) <= BUDGET, len(encoded)
    EXPORT.write_bytes(encoded)
    save_blend()
    summary["glb_sha256"], summary["blend_sha256"] = digest(EXPORT), digest(BLEND)
    report(HERE / "fit_report.json", summary)


if __name__ == "__main__":
    main()
