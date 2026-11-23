"""Repair the v1 high-top GLB against the corrected master animation banks.

Run with Blender 5.1.2 in background mode. See NOTES.md for the offline commands.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import numpy as np


HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
SOURCE = HERE.parent / "shoes_hightop_v1.glb"
DEST = HERE / "shoes_hightop_v2.glb"
BANKS = (
    (PARTS / "body-fix/motion_fixed.glb", ("walk", "run", "wave", "jump", "idle", "nod", "dance")),
    (PARTS / "actions-fix/actions_fixed.glb", ("sit_down", "sit_idle", "stand_up", "hold_item")),
    (PARTS / "actions-hold2/hold_actions.glb", ("hold_box", "hold_bag", "take_item")),
)
MIN_CLEARANCE = .0005
RUN_MARGIN = .0015
MAX_SHIFT = .02
BYTE_LIMIT = int(1.2 * 1024 ** 2)
WITNESSES = np.array([(i / 6, j / 6, (6 - i - j) / 6)
                      for i in range(7) for j in range(7 - i) if max(i, j, 6-i-j) < 6])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


class Glb:
    def __init__(self, path):
        data = path.read_bytes()
        _, version, length, size, tag = struct.unpack_from("<4sIII4s", data)
        assert version == 2 and length == len(data) and tag == b"JSON"
        self.doc = json.loads(data[20:20 + size])
        binary = data[28 + size:]
        self.views = [binary[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]
                      for v in self.doc["bufferViews"]]
        self.primitive, = self.doc["meshes"][0]["primitives"]

    def accessor(self, name):
        index = self.primitive["indices"] if name == "indices" else self.primitive["attributes"][name]
        return self.doc["accessors"][index]

    def array(self, name, dtype, columns):
        a = self.accessor(name)
        view = self.doc["bufferViews"][a["bufferView"]]
        assert not a.get("byteOffset") and not view.get("byteStride")
        return np.frombuffer(self.views[a["bufferView"]], dtype).reshape(-1, columns)

    def replace(self, name, array):
        a = self.accessor(name)
        self.views[a["bufferView"]] = array.tobytes()
        if name == "POSITION":
            a["min"], a["max"] = array.min(0).tolist(), array.max(0).tolist()

    def pack(self):
        binary = bytearray()
        for view, data in zip(self.doc["bufferViews"], self.views):
            view.update(byteOffset=len(binary), byteLength=len(data))
            binary.extend(data)
            binary.extend(b"\0" * (-len(binary) % 4))
        self.doc["buffers"][0]["byteLength"] = len(binary)
        content = json.dumps(self.doc, separators=(",", ":")).encode()
        content += b" " * (-len(content) % 4)
        return (struct.pack("<4sIII4s", b"glTF", 2, 28 + len(content) + len(binary), len(content), b"JSON")
                + content + struct.pack("<I4s", len(binary), b"BIN\0") + binary)


def load_objects(path, **kwargs):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), **kwargs)
    return set(bpy.context.scene.objects) - before


def load_scene():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    arm.animation_data_clear()
    scene.render.fps, scene.render.fps_base = 30, 1
    actions = {}
    for path, names in BANKS:
        before = set(bpy.data.actions)
        for obj in load_objects(path):
            bpy.data.objects.remove(obj, do_unlink=True)
        added = set(bpy.data.actions) - before
        for name in names:
            act, = [a for a in added if a.name == name or a.name.startswith(name + ".")]
            act.use_fake_user = True
            actions[name] = act
    return scene, arm, body, actions


def bind(arm, action):
    animation = arm.animation_data_create()
    animation.action = None
    animation.use_nla = False
    for bone in arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    if action is not None:
        animation.action = action
        animation.action_slot = action.slots[0]


def pose(scene, frame):
    whole = math.floor(frame)
    scene.frame_set(whole, subframe=frame - whole)
    bpy.context.view_layer.update()


def times(action):
    start, stop = map(float, action.frame_range)
    return sorted({start, stop, *(k / 2 for k in range(math.floor(start * 2), math.ceil(stop * 2) + 1)
                                  if start - 1e-5 <= k / 2 <= stop + 1e-5)})


def points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    array = np.empty(3 * len(evaluated.data.vertices), dtype=np.float32)
    evaluated.data.vertices.foreach_get("co", array)
    transform = np.array(evaluated.matrix_world)
    return array.reshape(-1, 3) @ transform[:3, :3].T + transform[:3, 3]


def faces(obj):
    obj.data.calc_loop_triangles()
    return [tuple(tri.vertices) for tri in obj.data.loop_triangles]


def attach_shoes(path, arm, **kwargs):
    imported = load_objects(path, **kwargs)
    shoe, = [obj for obj in imported if obj.type == "MESH" and obj.vertex_groups]
    world = shoe.matrix_world.copy()
    shoe.parent = arm
    shoe.matrix_world = world
    shoe.modifiers.clear()
    shoe.modifiers.new("Master skin", "ARMATURE").object = arm
    for obj in imported - {shoe}:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    return shoe


@dataclass
class Sample:
    clip: str
    frame: float
    tree: BVHTree
    skin: np.ndarray


def snapshots(scene, arm, body, actions, names=None):
    modes = tuple(b.rotation_mode for b in arm.pose.bones)
    assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
    bones = [arm.pose.bones[name] for name in names] if names else []
    inverses = [bone.bone.matrix_local.inverted() for bone in bones]
    triangles = faces(body)
    for clip, action in (("rest", None), *actions.items()):
        bind(arm, action)
        for frame in times(action) if action else (1.,):
            pose(scene, frame)
            tree = BVHTree.FromPolygons(points(body).tolist(), triangles, all_triangles=True)
            transforms = np.array([bone.matrix @ inv for bone, inv in zip(bones, inverses)])
            yield Sample(clip, frame, tree, transforms[:, :3] if bones else transforms)
    assert modes == tuple(b.rotation_mode for b in arm.pose.bones)


def hit(tree, point):
    nearest, normal, _, _ = tree.find_nearest(point)
    ray = Vector(point) - nearest
    distance = ray.dot(normal)
    direction = ray.normalized() * (-1 if distance < 0 else 1)
    if direction.dot(normal) < .8:
        direction = normal
    return distance, direction[:]


def topology(glb):
    original = glb.array("POSITION", "<f4", 3)[:, (0, 2, 1)] * [1, -1, 1]
    skin, = glb.doc["skins"]
    joints = [glb.doc["nodes"][i]["name"] for i in skin["joints"]]
    weight_data = glb.array("WEIGHTS_0", "<f4", 4)
    joint_data = glb.array("JOINTS_0", "u1", 4)
    used = sorted(set(joint_data[weight_data > 0].tolist()))
    weights = np.zeros((len(original), len(used)))
    rows, columns = np.where(weight_data > 0)
    weights[rows, np.searchsorted(used, joint_data[rows, columns])] = weight_data[rows, columns]
    # Give UV/normal splits one displacement and one weight vector per physical vertex.
    keys = np.round(np.c_[original, weights] * 1e7).astype(np.int64)
    _, unique, mapping = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    triangles = mapping[glb.array("indices", "<u2", 3)]
    assert np.all(np.diff(np.sort(triangles, axis=1), axis=1) > 0)
    return original, original[unique], weights[unique], mapping, triangles, used, [joints[i] for i in used]


def adjacency(triangles, count):
    a, b = triangles.ravel(), np.roll(triangles, 1, axis=1).ravel()
    a, b = np.unique(np.c_[np.r_[a, b], np.r_[b, a]], axis=0).T
    degree = np.bincount(a, minlength=count).clip(1)
    return a, b, degree


def laplace(values, graph):
    a, b, degree = graph
    return np.stack([np.bincount(a, values[b, i], minlength=len(values)) / degree
                     for i in range(values.shape[1])], axis=1)


def blend(sample, weights):
    return np.einsum("bjk,vb->vjk", sample.skin, weights)


def posed_positions(blended, rest):
    return np.einsum("vij,vj->vi", blended[:, :, :3], rest) + blended[:, :, 3]


def signed_samples(tree, xyz):
    return [hit(tree, p) for p in xyz.tolist()]


def collect(samples, rest, weights, triangles, *, original_active=None):
    tri_list = triangles.tolist()
    rows, constraints = {}, []
    active = np.zeros(len(rest), dtype=bool)
    for sample in samples:
        blended = blend(sample, weights)
        linear = blended[:, :, :3]
        xyz = posed_positions(blended, rest)
        hits = signed_samples(sample.tree, xyz)
        distance = np.array([h[0] for h in hits])
        tree = BVHTree.FromPolygons(xyz.tolist(), tri_list, all_triangles=True)
        pairs = sample.tree.overlap(tree)
        row = rows.setdefault(sample.clip, dict(samples=0, max_vertices_inside=0,
                              max_triangle_pairs=0, minimum_m=9., minimum_frame=None))
        row["samples"] += 1
        row["max_vertices_inside"] = max(row["max_vertices_inside"], int(np.count_nonzero(distance < 0)))
        row["max_triangle_pairs"] = max(row["max_triangle_pairs"], len(pairs))
        smallest = distance.argmin()
        if distance[smallest] < row["minimum_m"]:
            row.update(minimum_m=float(distance[smallest]), minimum_frame=sample.frame,
                       minimum_vertex=int(smallest), world=xyz[smallest].tolist())

        minimum = MIN_CLEARANCE + .00009
        target = np.full(len(rest), minimum)
        if sample.clip == "run":
            target[distance < MIN_CLEARANCE] = RUN_MARGIN
            if original_active is not None:
                # Keep the full margin at the original run contact samples.
                target[original_active.get(sample.frame, ())] = RUN_MARGIN
        ids = np.flatnonzero(distance < target - .000015)
        active[ids] = True
        if len(ids):
            normals = np.array([hits[i][1] for i in ids])
            gradients = np.einsum("vi,vij->vj", normals, linear[ids])
            for vertex, gradient, depth in zip(ids, gradients, target[ids] - distance[ids]):
                constraints.append((np.array([vertex]), gradient[None], float(depth), sample.clip, sample.frame))
        for face in sorted({pair[1] for pair in pairs}):
            corners = triangles[face]
            witnesses = WITNESSES @ xyz[corners]
            values = signed_samples(sample.tree, witnesses)
            worst = min(range(len(values)), key=lambda i: values[i][0])
            value, normal = values[worst]
            gradient = np.einsum("i,vij->vj", normal, linear[corners]) * WITNESSES[worst, :, None]
            margin = RUN_MARGIN if sample.clip == "run" else minimum
            constraints.append((corners, gradient, max(.00015, margin - value), sample.clip, sample.frame))
            active[corners] = True
    return rows, constraints, active


def project(offset, constraints, limit_base, sweeps):
    # Project minimum displacement onto the posed contact half spaces.
    for _ in range(sweeps):
        largest = 0.
        for ids, gradients, required in constraints:
            shortfall = required - np.sum(offset[ids] * gradients)
            if shortfall <= 1e-7:
                continue
            correction = gradients * (shortfall / max(1e-10, np.sum(gradients**2)))
            offset[ids] += correction
            total = offset[ids] + limit_base[ids]
            lengths = np.linalg.norm(total, axis=1)
            clipped = lengths > MAX_SHIFT
            if clipped.any():
                offset[ids[clipped]] = total[clipped] * (MAX_SHIFT / lengths[clipped, None]) - limit_base[ids[clipped]]
            largest = max(largest, shortfall)
        if largest < 2e-6:
            break
    return offset



def material_colors(source):
    image = next(i for i in source.doc["images"] if i["name"].endswith("_basecolor"))
    path = HERE / ".collar_texture.png"
    path.write_bytes(source.views[image["bufferView"]])
    loaded = bpy.data.images.load(str(path), check_existing=False)
    try:
        width, height = loaded.size
        pixels = np.empty(len(loaded.pixels), np.float32)
        loaded.pixels.foreach_get(pixels)
        return pixels.reshape(height, width, 4)[::-1]
    finally:
        bpy.data.images.remove(loaded)
        path.unlink()


def preserve_collar_layers(source, rest, triangles, shift, *, trim=True):
    """Hold the ivory trim in front of dark purple where the fit crossed layers."""
    from mathutils.geometry import barycentric_transform, intersect_ray_tri

    if trim:
        image = material_colors(source)
        tex_height, tex_width = image.shape[:2]
        uv = source.array("TEXCOORD_0", "<f4", 2)[source.array("indices", "<u2", 3)]
    else:
        sizes = json.loads((HERE.parent / "fit_dimensions.json").read_text())
        exterior = np.zeros(len(triangles), dtype=bool)
        start = 0
        for shoe in sizes:
            exterior[start:start + shoe["source_faces_retained"]] = True
            start += shoe["triangles"]
        assert start == len(triangles)

    old = BVHTree.FromPolygons(rest.tolist(), triangles.tolist(), all_triangles=True)
    fitted = rest + shift
    new = BVHTree.FromPolygons(fitted.tolist(), triangles.tolist(), all_triangles=True)
    axis = Vector((0, -1, 0))
    basis = [Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]

    def red(face, point, vertices):
        bary = barycentric_transform(point, *(Vector(v) for v in vertices[triangles[face]]), *basis)
        st = np.asarray(bary) @ uv[face]
        x = min(tex_width - 1, max(0, int(st[0] * tex_width)))
        y = min(tex_height - 1, max(0, int(st[1] * tex_height)))
        return image[y, x, 0]

    constraints = []
    step = .0004 if trim else .00045
    z_range = (.071, .10) if trim else (.055, .115)
    for sign in (-1, 1):
        for x in np.arange(.050, .115, step) * sign:
            for z in np.arange(*z_range, step):
                origin = Vector((x, 1, z))
                before, _, outer, _ = old.ray_cast(origin, axis)
                after, _, top, _ = new.ray_cast(origin, axis)
                if (outer is None or top is None or before.y < .06 or after.y < .06 or outer == top):
                    continue
                if trim:
                    if (np.intersect1d(triangles[outer], triangles[top]).size
                            or red(outer, before, rest) < .68 or red(top, after, fitted) > .55):
                        continue
                elif not exterior[outer] or exterior[top]:
                    continue
                ids = triangles[outer]
                corners = [Vector(p) for p in fitted[ids]]
                point = intersect_ray_tri(*corners, axis, origin, True)
                if point is None:
                    continue
                depth = float(after.y - point.y) + .00022
                if depth <= 0:
                    continue
                gradient = np.zeros((3, 3))
                gradient[:, 1] = barycentric_transform(point, *corners, *basis)
                constraints.append((ids, gradient, depth))
    constraints.sort(key=lambda item: item[2], reverse=True)
    correction = project(np.zeros_like(shift), constraints, shift, 35)
    positions = shift + correction
    report = {
        "ray_constraints": len(constraints),
        "vertices_adjusted": int(np.count_nonzero(np.linalg.norm(correction, axis=1) > 1e-7)),
        "max_trim_offset_m": float(np.linalg.norm(correction, axis=1).max()),
    }
    return positions, report


def repair_fit(source, scene, arm, body, actions):
    raw, rest, weights, mapping, triangles, used, names = topology(source)
    source_mesh = attach_shoes(SOURCE, arm)
    bind(arm, actions["run"])
    pose(scene, times(actions["run"])[len(times(actions["run"])) // 2])
    reference = points(source_mesh)
    actual = Sample("run", 0, None, np.array([
        arm.pose.bones[name].matrix @ arm.data.bones[name].matrix_local.inverted() for name in names])[:, :3])
    mismatch = np.linalg.norm(posed_positions(blend(actual, weights), rest)[mapping] - reference, axis=1).max()
    assert mismatch < 2e-6, mismatch
    bpy.data.objects.remove(source_mesh, do_unlink=True)
    samples = list(snapshots(scene, arm, body, actions, names))
    run = [s for s in samples if s.clip == "run"]
    baseline, first, active = collect(run, rest, weights, triangles)
    exact = {}
    for ids, _, _, _, frame in first:
        if len(ids) == 1:
            exact.setdefault(frame, set()).add(int(ids[0]))
    exact = {frame: sorted(ids) for frame, ids in exact.items()}
    print("BASELINE", baseline, "affected", int(active.sum()), flush=True)

    graph = adjacency(triangles, len(rest))
    a, b, _ = graph
    near = active.copy()
    near[a[active[b]]] = True
    # Relax only around affected ankle/toe triangles. Keep the original side
    # palette so the blend can never pick up an opposite-foot influence.
    side = np.sign(rest[:, 0])
    palette = np.array([(1 if "Left" in name else -1) for name in names])
    smoothed = weights.copy()
    for _ in range(2):
        next_weights = .88 * smoothed[near] + .12 * laplace(smoothed, graph)[near]
        next_weights *= side[near, None] == palette[None]
        next_weights /= next_weights.sum(axis=1, keepdims=True)
        smoothed[near] = next_weights
    weights = smoothed

    shift = np.zeros_like(rest)
    history = []
    for iteration in range(12):
        rows, contacts, affected = collect(samples, rest + shift, weights, triangles,
                                            original_active=exact)
        passing = all(row["max_vertices_inside"] == row["max_triangle_pairs"] == 0
                      and row["minimum_m"] >= MIN_CLEARANCE for row in rows.values())
        report = dict(iteration=iteration, constraints=len(contacts),
                      max_shift_m=float(np.linalg.norm(shift, axis=1).max()), run=rows["run"],
                      closest=min((row["minimum_m"], clip) for clip, row in rows.items()))
        print("FIT", report, flush=True)
        history.append(report)
        if passing and not contacts:
            break
        if iteration == 11:
            raise RuntimeError(f"Unresolved clearance constraints: {report}")
        constraints = [(ids, gradient, min(MAX_SHIFT, depth)) for ids, gradient, depth, _, _ in contacts]
        constraints.sort(key=lambda row: row[2], reverse=True)
        correction = project(np.zeros_like(shift), constraints, shift, 35)
        if iteration < 3:
            for _ in range(2):
                proposal = .78 * correction + .22 * laplace(correction, graph)
                proposal[~affected] = 0
                correction = project(proposal, constraints, shift, 35)
        shift += correction

    # Evaluate each visual correction at the same float32 precision as the GLB.
    _, representative = np.unique(mapping, return_index=True)

    def stored_shift(value):
        rounded = (raw + value[mapping]).astype("<f4")
        return (rounded - raw)[representative]

    shift, lining = preserve_collar_layers(source, rest, triangles, stored_shift(shift), trim=False)
    shift, trim = preserve_collar_layers(source, rest, triangles, stored_shift(shift))
    collar = {"lining": lining, "ivory_trim": trim}
    print("COLLAR", collar, flush=True)
    output_positions = raw + shift[mapping]
    source.replace("POSITION", (output_positions[:, (0, 2, 1)] * [1, 1, -1]).astype("<f4"))
    original_weights = source.array("WEIGHTS_0", "<f4", 4).copy()
    original_joints = source.array("JOINTS_0", "u1", 4).copy()
    selected = near[mapping]
    w = weights[mapping[selected]]
    order = np.argsort(-w, axis=1)[:, :4]
    trimmed = np.take_along_axis(w, order, axis=1)
    trimmed /= trimmed.sum(axis=1, keepdims=True)
    original_weights[selected] = trimmed
    original_joints[selected] = np.where(trimmed > 0, np.array(used)[order], 0)
    source.replace("WEIGHTS_0", original_weights)
    source.replace("JOINTS_0", original_joints)
    write_json("fit_history.json", dict(source_sha256=sha(SOURCE), master_sha256=sha(MASTER),
               bank_sha256={path.name: sha(path) for path, _ in BANKS}, reproduced_run=baseline["run"],
               unique_vertices=len(rest), moved_vertices=int(np.count_nonzero(np.linalg.norm(shift, axis=1) > 1e-7)),
               weight_vertices=int(near.sum()), collar=collar, iterations=history))
    return baseline["run"]


def compact_textures(glb, scene):
    # Keep the original maps and UV/material channel assignment. Encode directly
    # from image data so the normal and metallic/roughness maps stay non-color.
    textures = glb.doc["images"]
    work = HERE / ".texture"
    work.mkdir(exist_ok=True)
    try:
        images = []
        for i, texture in enumerate(textures):
            view = texture["bufferView"]
            path = work / f"{i}.png"
            path.write_bytes(glb.views[view])
            image = bpy.data.images.load(str(path), check_existing=False)
            if not texture["name"].endswith("_basecolor"):
                image.colorspace_settings.name = "Non-Color"
            assert max(image.size) <= 1024
            images.append((view, image, path))
        for quality in (97, 96, 95, 94, 93, 92, 91, 90, 88, 85, 82):
            settings = []
            for (view, image, original), texture in zip(images, textures):
                encoded = original.with_suffix(".jpg")
                image.file_format = "JPEG"
                image.save(filepath=str(encoded), quality=quality, save_copy=True)
                glb.views[view] = encoded.read_bytes()
                texture["mimeType"] = "image/jpeg"
                settings.append(dict(name=texture["name"], pixels=list(image.size),
                                     quality=quality, bytes=len(glb.views[view])))
            data = glb.pack()
            print("TEXTURES", quality, len(data), settings, flush=True)
            if len(data) <= BYTE_LIMIT:
                DEST.write_bytes(data)
                write_json("texture_encoding.json", {"glb_bytes": len(data), "textures": settings})
                return
        raise ValueError("No image encoding met the GLB byte limit")
    finally:
        for path in work.iterdir():
            path.unlink()
        work.rmdir()


def verify():
    scene, arm, body, actions = load_scene()
    shoe = attach_shoes(DEST, arm)
    triangles = faces(shoe)
    output = Glb(DEST)
    exact_keys = np.c_[output.array("POSITION", "<f4", 3), output.array("JOINTS_0", "u1", 4),
                       output.array("WEIGHTS_0", "<f4", 4)]
    _, representative, group_map, group_size = np.unique(
        exact_keys, axis=0, return_index=True, return_inverse=True, return_counts=True)
    rows, frames = {}, {}
    for sample in snapshots(scene, arm, body, actions):
        xyz = points(shoe)
        min_distance = 9.
        inside = 0
        unique = xyz[representative]
        if np.array_equal(xyz, unique[group_map]):
            vertices, counts = unique.tolist(), group_size.tolist()
        else:
            vertices, counts = xyz.tolist(), [1] * len(xyz)
        for p, copies in zip(vertices, counts):
            nearest, normal, _, _ = sample.tree.find_nearest(p)
            distance = (Vector(p) - nearest).dot(normal)
            inside += copies if distance < 0 else 0
            min_distance = min(distance, min_distance)
        shoe_tree = BVHTree.FromPolygons(xyz.tolist(), triangles, all_triangles=True)
        overlaps = len(sample.tree.overlap(shoe_tree))
        row = dict(frame=sample.frame, vertices_inside=inside, triangle_pairs=overlaps, minimum_m=min_distance)
        frames.setdefault(sample.clip, []).append(row)
        summary = rows.setdefault(sample.clip, dict(samples=0, max_vertices_inside=0, max_triangle_pairs=0,
                                                   minimum_m=9., minimum_frame=None))
        summary["samples"] += 1
        summary["max_vertices_inside"] = max(summary["max_vertices_inside"], inside)
        summary["max_triangle_pairs"] = max(summary["max_triangle_pairs"], overlaps)
        if min_distance < summary["minimum_m"]:
            summary.update(minimum_m=min_distance, minimum_frame=sample.frame)
    for clip, row in rows.items():
        print("DENSE", clip, row, flush=True)
    write_json("motion_half_frames.json", dict(export_sha256=sha(DEST), clips=rows, frames=frames))
    assert len(rows) == 15 and all(r["max_vertices_inside"] == r["max_triangle_pairs"] == 0
                                  and r["minimum_m"] >= MIN_CLEARANCE for r in rows.values())


def verify_editable():
    path = DEST.with_suffix(".blend")
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, shoe = [scene.objects[name] for name in ("Armature", "Base_Body", DEST.stem)]
    assert shoe.parent == arm and shoe.modifiers[0].object == arm
    assert len(arm.data.bones) == 65
    triangles = faces(shoe)
    assert len(triangles) == len(Glb(DEST).array("indices", "<u2", 3))
    assert all(bpy.data.actions[name].slots for _, names in BANKS for name in names)
    assert all(image.packed_file for material in shoe.data.materials for node in material.node_tree.nodes
               if node.type == "TEX_IMAGE" and (image := node.image))
    report = json.loads((HERE / "motion_half_frames.json").read_text())
    body_triangles = faces(body)
    cases = {}
    for name, row in report["clips"].items():
        bind(arm, None if name == "rest" else bpy.data.actions[name])
        pose(scene, row["minimum_frame"])
        body_tree = BVHTree.FromPolygons(points(body).tolist(), body_triangles, all_triangles=True)
        xyz = points(shoe).tolist()
        shoe_tree = BVHTree.FromPolygons(xyz, triangles, all_triangles=True)
        minimum = min(hit(body_tree, p)[0] for p in xyz)
        overlaps = len(body_tree.overlap(shoe_tree))
        assert overlaps == 0 and minimum >= MIN_CLEARANCE, (name, minimum, overlaps)
        assert abs(minimum - row["minimum_m"]) < 2e-6, name
        cases[name] = dict(frame=row["minimum_frame"], minimum_m=minimum, triangle_pairs=overlaps)
    write_json("editable_check.json", dict(blend_sha256=sha(path), export_sha256=sha(DEST),
               triangles=len(triangles), packed_shoe_materials=True, closest_frames=cases))
    print("EDITABLE", len(cases), "closest samples agree with the GLB", flush=True)


def save_editable():
    scene, arm, body, actions = load_scene()
    shoe = attach_shoes(DEST, arm, merge_vertices=True)
    shoe.name = DEST.stem
    shoe.data.name = "Purple star high-top pair"
    for obj in scene.objects:
        if obj.type == "MESH" and obj not in (shoe, body):
            obj.hide_render = True
            obj.hide_set(True)
    bind(arm, None)
    pose(scene, 1.)
    bpy.ops.object.select_all(action="DESELECT")
    shoe.select_set(True)
    bpy.context.view_layer.objects.active = shoe
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.temporary_directory = str(HERE)
    scene.render.filepath = "//"
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST.with_suffix(".blend")), compress=True)


def main():
    bpy.context.preferences.filepaths.temporary_directory = str(HERE)
    opts = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not opts or "--fit" in opts:
        scene, arm, body, actions = load_scene()
        source = Glb(SOURCE)
        repair_fit(source, scene, arm, body, actions)
        compact_textures(source, scene)
    if "--verify" in opts:
        verify()
        verify_editable()
    if "--editable" in opts:
        save_editable()


if __name__ == "__main__":
    main()
