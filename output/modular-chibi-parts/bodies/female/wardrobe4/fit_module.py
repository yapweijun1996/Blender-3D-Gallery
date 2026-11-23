"""Fit a neutral skinned module to the Studio female rest shape and motion bank.

Run with ./run.sh fit_module.py -- <source.glb> <female-module.glb> [iterations].
Built-in module slugs can also replace the two paths.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_body import reencode_images
from common import (BODY, CLIPS, HERE, MASTER, MODULES, MOTION, NEUTRAL, PARTS,
                    arguments, bind, dispose, load_glb, samples, set_frame)
from glb_io import Glb
sys.path.insert(1, str(PARTS / "body-fix"))
from bodycheck import pair_depth

SOURCE = runpy.run_path(str(PARTS / "studio-modules/jeans/round2/fit_jeans_r2.py"))
GEOMETRY = SOURCE["PRIOR"]
nearest = GEOMETRY["nearest"]
average = GEOMETRY["average"]
tree_from = GEOMETRY["tree_from"]
barycentric = GEOMETRY["barycentric"]
limit_weights = GEOMETRY["limit_weights"]
MARGIN = .0015
GATE = .0005
CAP = .030
BYTE_LIMIT = int(1.5 * 2**20)
FPS = 30


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gltf_axes(points):
    return points[:, [0, 2, 1]] * (1, 1, -1)


def blender_axes(points):
    return points[:, [0, 2, 1]] * (1, -1, 1)


def normalized(values):
    return values / np.linalg.norm(values, axis=-1, keepdims=True).clip(1.e-12)


def adjacency(faces, size):
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    src, dst = np.unique(np.concatenate([edges, edges[:, ::-1]]), axis=0).T
    return src, dst, np.bincount(src, minlength=size).clip(1)


def rig_data(arm, body, names):
    points, faces = GEOMETRY["mesh_arrays"](body.data)
    weights = GEOMETRY["read_weights"](body, names)
    pivots = np.asarray([arm.data.bones[name].head_local for name in names], dtype=np.float32)
    regions = np.array([joint_region(name) for name in names])
    dom = weights[faces].sum(axis=1).argmax(axis=1)
    return points, faces, weights, pivots, regions[dom]


def joint_region(name):
    label = name.split(":")[-1]
    if label.startswith(("Head", "Neck")):
        return "head"
    for side in ("Left", "Right"):
        if not label.startswith(side):
            continue
        if any(s in label for s in ("Foot", "Toe")):
            return side + " foot"
        if any(s in label for s in ("UpLeg", "Leg")):
            return side + " leg"
        if any(s in label for s in ("Arm", "Hand")):
            return side + " arm"
    return "torso"


def load_rest():
    bpy.ops.wm.open_mainfile(filepath=str(NEUTRAL), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    names = list(scene.objects["Armature"].data.bones.keys())
    neutral = rig_data(scene.objects["Armature"], scene.objects["Base_Body"], names)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    arm, body = [scene.objects[n] for n in ("Armature", "Base_Body")]
    assert set(names) == set(arm.data.bones.keys())
    female = rig_data(arm, body, names)
    return names, neutral, female, scene, arm, body


def cache_scene(motion=MOTION):
    names, neutral, female, scene, arm, body = load_rest()
    dispose(load_glb(motion))
    rig_inverse = [arm.data.bones[n].matrix_local.inverted() for n in names]
    result, matrices = [], []
    before = time.monotonic()
    cache_path = HERE / ".runtime" / ("poses-" + sha(MASTER)[:12] + "-" + sha(motion)[:12] + ".npz")
    if cache_path.exists():
        with np.load(cache_path, allow_pickle=False) as cache:
            for label, frame, points in zip(cache["labels"], cache["frames"], cache["points"], strict=True):
                result.append((str(label), float(frame), tree_from(points, female[1]), points, female[1]))
            return names, neutral, female, result, cache["matrices"]
    for label in ("rest", *CLIPS):
        action = bpy.data.actions.get(label)
        assert label == "rest" or action, label
        bind(arm, action)
        frame_list = samples(*action.frame_range) if action else [0.]
        for frame in frame_list:
            set_frame(scene, frame)
            evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            points = np.empty(len(evaluated.data.vertices) * 3, dtype=np.float32)
            evaluated.data.vertices.foreach_get("co", points)
            points = points.reshape(-1, 3)
            faces = female[1]
            matrix = np.asarray([arm.pose.bones[n].matrix @ inv for n, inv in zip(names, rig_inverse)])
            matrices.append(matrix[:, :3])
            result.append((label, frame, tree_from(points, faces), points, faces))
    bind(arm, None)
    if not cache_path.exists():
        pending = cache_path.with_suffix(f".{os.getpid()}.npz")
        np.savez(pending, labels=np.array([r[0] for r in result]), frames=np.array([r[1] for r in result]),
                 points=np.array([r[3] for r in result], dtype=np.float32),
                 matrices=np.asarray(matrices, dtype=np.float32))
        pending.replace(cache_path)
    print("CACHE", len(result), "samples", round(time.monotonic() - before, 1), "seconds", flush=True)
    return names, neutral, female, result, np.asarray(matrices, dtype=np.float32)


class Module:
    def __init__(self, path, names):
        self.path = path
        self.texture_cache = {}
        self.glb = Glb(path)
        doc = self.glb.doc
        assert len(doc["meshes"]) == len(doc["skins"]) == 1
        self.skin_names = [doc["nodes"][i]["name"] for i in doc["skins"][0]["joints"]]
        name_indices = np.array([names.index(n) for n in self.skin_names])
        self.parts, all_points, all_weights, all_faces = [], [], [], []
        offset = 0
        for primitive in doc["meshes"][0]["primitives"]:
            attrs = primitive["attributes"]
            assert primitive.get("mode", 4) == 4 and "JOINTS_1" not in attrs
            xyz = blender_axes(self.glb.accessor(attrs["POSITION"])).astype(np.float32)
            joints = self.glb.accessor(attrs["JOINTS_0"])
            values = self.glb.accessor(attrs["WEIGHTS_0"])
            assert values.dtype == np.float32
            weights = np.zeros((len(xyz), len(names)), np.float32)
            np.add.at(weights, (np.arange(len(xyz))[:, None], name_indices[joints]), values)
            all_weights.append(weights)
            all_points.append(xyz)
            corners = self.glb.accessor(primitive["indices"]).reshape(-1, 3)
            all_faces.append(corners.astype(np.int32) + offset)
            self.parts.append((attrs, slice(offset, offset + len(xyz))))
            offset += len(xyz)
        source = np.concatenate(all_points)
        weights = np.concatenate(all_weights)
        self.source_points = source
        self.source_faces = np.concatenate(all_faces)
        assert np.allclose(weights.sum(axis=1), 1, atol=1.e-5)
        # Geometrically coincident sleeves, seams and material boundaries share
        # the same displacement. Distinct source weights remain distinct.
        _, indices, self.unweld = np.unique(np.round(source, 7), axis=0, return_index=True, return_inverse=True)
        self.points = source[indices]
        self.weights = weights
        self.faces = self.unweld[self.source_faces]
        self.graph = adjacency(self.faces, len(self.points))
        self.split_count = np.bincount(self.unweld)
        self.names = names
        self.name_indices = name_indices

    def welded(self, values):
        out = np.zeros((len(self.points),) + values.shape[1:], values.dtype)
        np.add.at(out, self.unweld, values)
        return out / self.split_count.reshape((-1,) + (1,) * (values.ndim - 1))

    def write(self, path, fitted, weights):
        asset = Glb(self.path)
        template = Glb(BODY)
        female_doc = template.doc
        nodes = female_doc["nodes"]
        female_index = {node["name"]: i for i, node in enumerate(nodes)}
        source_mesh, = (node for node in asset.doc["nodes"] if "mesh" in node)
        assert not any(k in source_mesh for k in ("matrix", "translation", "rotation", "scale"))
        asset.doc["nodes"] = [source_mesh if "mesh" in node else node for node in nodes]
        asset.doc["scenes"] = female_doc["scenes"]
        skin = asset.doc["skins"][0]
        skin["joints"] = [female_index[n] for n in self.skin_names]
        female_skin = female_doc["skins"][0]
        female_inverses = template.accessor(female_skin["inverseBindMatrices"])
        order = [female_skin["joints"].index(i) for i in skin["joints"]]
        asset.accessor(skin["inverseBindMatrices"])[:] = female_inverses[order]

        final = fitted[self.unweld]
        old_normal = self.surface_normals(self.source_points)
        new_normal = self.surface_normals(final)
        axis = np.cross(old_normal, new_normal)
        cosine = np.einsum("vi,vi->v", old_normal, new_normal)

        def rotate(values, sl):
            vectors = blender_axes(values.copy())
            first = np.cross(axis[sl], vectors)
            moved = vectors + first + np.cross(axis[sl], first) / (1 + cosine[sl, None]).clip(.01)
            rotation = gltf_axes(normalized(moved))
            bad = np.linalg.norm(moved, axis=1) < .001
            rotation[bad] = values[bad]
            return rotation

        keep_weights = np.array_equal(weights, self.weights)
        for attrs, sl in self.parts:
            positions = asset.accessor(attrs["POSITION"])
            positions[:] = gltf_axes(final[sl])
            asset.doc["accessors"][attrs["POSITION"]].update(min=positions.min(axis=0).tolist(),
                                                             max=positions.max(axis=0).tolist())
            if "NORMAL" in attrs:
                normal = asset.accessor(attrs["NORMAL"])
                normal[:] = rotate(normal, sl)
            if "TANGENT" in attrs:
                tangent = asset.accessor(attrs["TANGENT"])
                direction = rotate(tangent[:, :3], sl)
                direction -= normal * (direction * normal).sum(axis=1, keepdims=True)
                tangent[:, :3] = normalized(direction)
            if not keep_weights:
                joint_order = np.argsort(-weights[sl][:, self.name_indices], axis=1, kind="stable")[:, :4]
                top = np.take_along_axis(weights[sl][:, self.name_indices], joint_order, axis=1)
                asset.accessor(attrs["JOINTS_0"])[:] = joint_order
                asset.accessor(attrs["WEIGHTS_0"])[:] = top / top.sum(axis=1, keepdims=True)
            indices = asset.accessor(attrs["JOINTS_0"])
            indices[asset.accessor(attrs["WEIGHTS_0"]) == 0] = 0

        if asset.doc.get("images"):
            for size, quality in [(1024, 88), (896, 87), (768, 86), (640, 85)]:
                if size not in self.texture_cache:
                    before = Glb(self.path)
                    result = reencode_images(before, BYTE_LIMIT, (size,), (quality,))
                    self.texture_cache[size] = (result, [(im["mimeType"], before.payload(im["bufferView"]))
                                                        for im in before.doc["images"]])
                result, payloads = self.texture_cache[size]
                images = asset.doc["images"]
                asset.repack_views({im["bufferView"]: content for im, (_, content) in zip(images, payloads)})
                for im, (mime, _) in zip(images, payloads):
                    im["mimeType"] = mime
                asset.write(path)
                if path.stat().st_size <= BYTE_LIMIT:
                    return result
            raise ValueError(f"{path.name} exceeds {BYTE_LIMIT} bytes")
        asset.write(path)
        return []

    def surface_normals(self, points):
        tri = points[self.source_faces]
        normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        result = np.zeros_like(points)
        np.add.at(result, self.source_faces.ravel(), np.repeat(normals, 3, axis=0))
        return normalized(result)


def surface_map(neutral, female, names):
    a, af, aw, ap, ar = neutral
    b, bf, bw, bp, br = female
    guessed = a + aw @ (bp - ap)
    normal = np.zeros_like(a)
    faces = a[af]
    directions = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    np.add.at(normal, af.ravel(), np.repeat(directions, 3, axis=0))
    normal = normalized(normal)
    trees = {region: tree_from(b, bf[br == region]) for region in set(br)}
    graph = adjacency(af, len(a))
    region_labels = [joint_region(n) for n in names]
    regions = np.array(region_labels)[aw.argmax(axis=1)]
    delta = np.zeros_like(a)
    for i, (p, n, region) in enumerate(zip(guessed, normal, regions)):
        tree = trees[region]
        # Project approximately along the source surface normal and retain
        # tangential bone registration. Reject reverse-facing thin surfaces.
        near = [r for r in tree.find_nearest_range(p, .029) if np.dot(r[1], n) > .4]
        if near:
            hit = min(near, key=lambda r: r[3] + .018 * (1 - np.dot(r[1], n)))
            residual = np.asarray(hit[0]) - p
            projection = np.dot(residual, n) * n
            delta[i] = .85 * projection + .15 * residual
    for _ in range(5):
        delta = .65 * delta + .35 * average(delta, graph)
    return guessed + delta - a


def seed_shape(module, neutral, female, tree):
    p, faces, _, _, _ = neutral
    a, af, aw, *_ = female
    displacement = surface_map(neutral, female, module.names)
    rest_tree = tree_from(p, faces)
    _, surface, _, ids = nearest(rest_tree, module.points)
    corner = faces[ids]
    bary = barycentric(p[corner], surface)
    shift = np.einsum("vi,vij->vj", bary, displacement[corner])
    for _ in range(4):
        shift = .70 * shift + .30 * average(shift, module.graph)
    mapped = module.points + shift
    _, hit, _, ids = nearest(tree, mapped)
    corner = af[ids]
    mapped_weights = np.einsum("vi,vib->vb", barycentric(a[corner], hit), aw[corner])
    source_weights = module.welded(module.weights)
    moved = np.linalg.norm(shift, axis=1)
    # Keep hair and shoe mounting rigid where their source skin is rigid. In
    # blended cloth, transfer smoothly from the newly matched body surface.
    mixed = (source_weights.max(axis=1) < .98) & (moved > .003)
    blend = np.where(mixed, np.minimum(.28, moved * 13), 0).astype(np.float32)
    for _ in range(2):
        blend = .75 * blend + .25 * average(blend, module.graph)
    values = module.weights + (blend[:, None] * (mapped_weights - source_weights))[module.unweld]
    untouched = (blend == 0)[module.unweld]
    values = limit_weights(np.maximum(0, values)).astype(np.float32)
    values[untouched] = module.weights[untouched]
    return mapped.astype(np.float32), values


def scan(module, points, weights, sample_rows, transforms, margin=MARGIN):
    skin = GEOMETRY["pose_matrices"](transforms, weights)
    positions = GEOMETRY["skin_positions"](points[module.unweld], skin)
    distances, overlaps, hits, constraints = SOURCE["scan"](
        positions, module.source_faces, sample_rows, margin=margin, details=False)
    return distances, overlaps, hits, constraints, skin, positions


def score(result):
    d, overlaps = result[:2]
    deficit = np.maximum(0, GATE + .00008 - d)
    return float(overlaps.sum() + 5 * (d < 0).sum() + 1900 * deficit.sum())


def summary(module, result, sample_rows, female):
    distances, overlaps, _, _, _, positions = result
    zones = female[-1]
    records = {}
    for name in ("rest", *CLIPS):
        rows = [i for i, sample in enumerate(sample_rows) if sample[0] == name]
        d = distances[rows]
        frame, vertex = np.unravel_index(d.argmin(), d.shape)
        sample = sample_rows[rows[frame]]
        point = positions[rows[frame], vertex]
        body_triangle = sample[2].find_nearest(point)[2]
        peaks = overlaps[rows]
        zones_at_peak = {}
        peak_row = rows[peaks.argmax()]
        if peaks.max():
            sample_peak = sample_rows[peak_row]
            contacts = np.asarray(sample_peak[2].overlap(
                tree_from(positions[peak_row], module.source_faces)), dtype=np.int32)
            body_ids, garment_ids = contacts.T
            depth = pair_depth(sample_peak[3][sample_peak[4][body_ids]],
                               positions[peak_row, module.source_faces[garment_ids]])
            for zone in set(zones[body_ids]):
                in_zone = zones[body_ids] == zone
                zones_at_peak[str(zone)] = {"pairs": int(in_zone.sum()),
                                            "sat_depth_mm": float(depth[in_zone].max())}
        records[name] = {
            "samples": len(rows), "vertices_inside": int((d < 0).sum(axis=1).max()),
            "triangle_pairs": int(peaks.max()), "total_triangle_pairs": int(peaks.sum()),
            "minimum_signed_m": float(d.min()), "minimum_frame": sample[1],
            "peak_overlap_frame": sample_rows[rows[peaks.argmax()]][1],
            "body_zone": str(zones[body_triangle]), "peak_triangle_zones": zones_at_peak,
            "module_vertex": int(vertex),
            "rest_vertex_m": module.source_points[vertex].tolist(),
        }
    return records


def worst_planes(module, result):
    # Keep the peak penetration-plus-margin along each distinct direction.
    # The skin gradient converts world-surface normals back to garment rest.
    _, _, _, constraints, skin, _ = result
    n = len(module.points)
    normals = np.zeros((n * 6, 3), np.float32)
    reqs = np.zeros(n * 6, np.float32)
    for row, ids, world, ds, factors in constraints:
        gradient = np.einsum("vi,vij->vj", world, skin[row, ids, :, :3])
        length = np.linalg.norm(gradient, axis=1).clip(.15)
        g = gradient / length[:, None]
        req = ((MARGIN - ds) * factors / length).clip(0, CAP)
        axis = abs(g).argmax(axis=1)
        cell = 6 * module.unweld[ids] + axis * 2 + (g[np.arange(len(g)), axis] >= 0)
        np.maximum.at(reqs, cell, req)
        use = req >= reqs[cell]
        normals[cell[use]] = g[use]
    return normals.reshape(n, 6, 3), reqs.reshape(n, 6)


def clearance_step(module, result):
    planes, required = worst_planes(module, result)
    correction = np.zeros_like(module.points)
    rows = np.arange(len(correction))
    for _ in range(24):
        gap = required - np.einsum("vij,vj->vi", planes, correction)
        chosen = gap.argmax(axis=1)
        correction += .52 * np.maximum(0, gap[rows, chosen, None]) * planes[rows, chosen]
        correction = SOURCE["limit_delta"](correction, .009)
    # Preserve the worst-direction component through graph smoothing.
    length = np.linalg.norm(correction, axis=1)
    direction = normalized(correction)
    smooth = correction.copy()
    for _ in range(4):
        smooth = .66 * smooth + .34 * average(smooth, module.graph)
    loss = length - np.einsum("vi,vi->v", smooth, direction)
    return smooth + np.maximum(loss, 0)[:, None] * direction


def protect_style(module, prior, candidate):
    faces = module.faces
    a, b = prior[faces], candidate[faces]
    u = np.cross(a[:, 1] - a[:, 0], a[:, 2] - a[:, 0])
    v = np.cross(b[:, 1] - b[:, 0], b[:, 2] - b[:, 0])
    old_area = np.linalg.norm(u, axis=1)
    new_area = np.linalg.norm(v, axis=1)
    cos = np.einsum("vi,vi->v", u, v) / (old_area * new_area).clip(1.e-14)
    bad = (old_area > 2.e-8) & ((cos < .25) | (new_area < .22 * old_area) | (new_area > 3.7 * old_area))
    candidate[faces[bad].ravel()] = prior[faces[bad].ravel()] * .55 + candidate[faces[bad].ravel()] * .45
    return candidate


def refit_contact_weights(module, seed, weights, result, female, tree):
    # Keep the source weight field outside affected seam neighborhoods. Inside
    # them, a partial body-surface transfer makes cloth follow the nearby skin
    # when different poses require incompatible coordinate-only corrections.
    body_points, body_faces, body_weights, *_ = female
    _, locations, _, indices = nearest(tree, seed)
    corners = body_faces[indices]
    coefficients = barycentric(body_points[corners], locations)
    mapped = np.einsum("vi,vib->vb", coefficients, body_weights[corners])
    active = np.zeros(len(module.points), dtype=np.float32)
    distances, _, face_hits, *_ = result
    touched = module.unweld[np.flatnonzero(distances.min(axis=0) < .0006)]
    active[touched] = 1
    active[module.faces[face_hits > 0].reshape(-1)] = 1
    for _ in range(4):
        active = np.maximum(active, .80 * average(active, module.graph))
    blend = (.52 * active[module.unweld, None]).astype(np.float32)
    changed = limit_weights((1 - blend) * weights + blend * mapped[module.unweld])
    changed[blend[:, 0] == 0] = weights[blend[:, 0] == 0]
    return changed


def fit(path, output, iterations, data, limit, refine=False, retune=False):
    names, neutral, female, frame_samples, transforms = data
    module = Module(path, names)
    assert limit is None or len(module.source_faces) <= limit
    surface_map.names = names
    rest = frame_samples[0][2]
    seed, weights = seed_shape(module, neutral, female, rest)
    points = seed.copy()
    # Begin with a local rest-only pass for seam and shell contacts. The same
    # 30 mm envelope applies to the entire bake, including this prepass.
    static = scan(module, points, weights, frame_samples[:1], transforms[:1])
    for _ in range(4):
        if score(static) == 0:
            break
        candidate = seed + SOURCE["limit_delta"](points + clearance_step(module, static) - seed, CAP)
        candidate = protect_style(module, points, candidate)
        trial = scan(module, candidate, weights, frame_samples[:1], transforms[:1])
        if score(trial) >= score(static):
            break
        points, static = candidate, trial
    history = []
    if refine and output.exists():
        existing = Module(output, names)
        assert np.array_equal(existing.source_faces, module.source_faces)
        points = module.welded(existing.source_points).astype(np.float32)
        weights = existing.weights
        history = json.loads(output.with_suffix(".fit.json").read_text())["history"]
    iteration_origin = history[-1]["iteration"] + 1 if history else 0
    best_score = float("inf")
    best_step = None
    for iteration in range(iterations + 1):
        start = time.monotonic()
        result = scan(module, points, weights, frame_samples, transforms)
        value = score(result)
        rows = summary(module, result, frame_samples, female)
        print("FIT", output.name, iteration, round(value, 2), "seconds", round(time.monotonic() - start, 1),
              "ranked", sorted([(key, v["vertices_inside"], v["triangle_pairs"],
                                round(1000 * v["minimum_signed_m"], 2)) for key, v in rows.items()],
                               key=lambda x: x[-1])[:6], flush=True)
        improved = value < best_score
        if improved:
            best_score = value
            best_points, best_weights = points.copy(), weights.copy()
            history.append(dict(iteration=iteration_origin + iteration, score=value, results=rows))
            output_info = module.write(output, points, weights)
            report = dict(source=str(path.relative_to(PARTS)) if path.is_relative_to(PARTS) else str(path),
                          source_sha256=sha(path), motion_sha256=sha(MOTION),
                          output_sha256=sha(output), triangles=len(module.source_faces),
                          texture_images=output_info, bytes=output.stat().st_size,
                          margin_m=MARGIN, offset_cap_m=CAP, fps=FPS,
                          max_clearance_offset_m=float(np.linalg.norm(points - seed, axis=1).max()),
                          held_source_weight_rows=int(np.all(weights == module.weights, axis=1).sum()),
                          history=history, results=rows)
            output.with_suffix(".fit.json").write_text(json.dumps(report, indent=2) + "\n")
        if value == 0 or iteration == iterations:
            return
        if improved:
            best_step = clearance_step(module, result)
            step = best_step
        else:
            points, weights = best_points.copy(), best_weights.copy()
            step = best_step * (.65 if iteration % 2 else .35)
        if retune and iteration in (0, 3) and improved:
            weights = refit_contact_weights(module, seed, weights, result, female, rest)
        candidate = seed + SOURCE["limit_delta"](points + step - seed, CAP)
        points = protect_style(module, points, candidate)


def main():
    refine = "--refine" in arguments()
    retune = "--retune" in arguments()
    args = [a for a in arguments() if a not in {"--refine", "--retune"}]
    if not args:
        raise SystemExit(__doc__)
    if args[0].split(",")[0] in MODULES or args[0] == "all":
        slugs = MODULES if args[0] == "all" else args[0].split(",")
        jobs = [(PARTS / MODULES[s][0], HERE / ("female-" + s + ".glb"), MODULES[s][1]) for s in slugs]
        iterations = int(args[1]) if len(args) > 1 else 7
    else:
        source, output = map(lambda p: Path(p).resolve(), args[:2])
        assert output.is_relative_to(HERE) and output.suffix == ".glb"
        jobs = [(source, output, None)]
        iterations = int(args[2]) if len(args) > 2 else 7
    if iterations < 0:
        names, neutral, female, *_ = load_rest()
        rest = tree_from(female[0], female[1])
        for source, output, limit in jobs:
            module = Module(source, names)
            assert limit is None or len(module.source_faces) <= limit
            points, weights = seed_shape(module, neutral, female, rest)
            temp = HERE / ".runtime" / output.name
            textures = module.write(temp, points, weights)
            print("SEED", output.name, len(module.source_faces), temp.stat().st_size, textures, flush=True)
        return
    data = cache_scene()
    for source, output, limit in jobs:
        fit(source, output, iterations, data, limit, refine=refine, retune=retune)


if __name__ == "__main__":
    main()
