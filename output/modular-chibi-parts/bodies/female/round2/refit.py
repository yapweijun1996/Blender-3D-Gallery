"""Bake female garment clearance at original clip endpoints and every half frame."""
import json
from functools import lru_cache
from pathlib import Path
import shutil
import sys
import time
import zipfile

import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT.parent))
import fit_module as fit
from common import CLIPS, HERE, MASTER, MOTION, arguments
from glb_io import Glb

RUNTIME = ROOT / ".runtime"
GARMENTS = ("tshirt", "dress", "jeans")
smoothstep = fit.GEOMETRY["smoothstep"]
limit = fit.SOURCE["limit_delta"]


class PoseTree:
    def __init__(self, points, faces):
        self.points = points
        self.faces = faces

    @lru_cache(maxsize=10)
    def bvh(self):
        return fit.tree_from(self.points, self.faces)

    def __getattr__(self, name):
        return getattr(self.bvh(), name)


class SkinField:
    def __init__(self, matrices, weights):
        self.matrices = matrices
        self.weights = weights

    def __getitem__(self, indices):
        frame, vertices, *axes = indices
        weights = self.weights[vertices]
        flat = weights.reshape(-1, weights.shape[-1])
        mat = fit.GEOMETRY["pose_matrices"](self.matrices[frame:frame + 1], flat)[0]
        mat = mat.reshape((*weights.shape[:-1], 3, 4))
        return mat[(..., *axes)] if axes else mat


class PosedCloth:
    def __init__(self, points, matrices):
        self.points = points
        self.skin = matrices

    def __getitem__(self, indices):
        if not isinstance(indices, tuple):
            indices = (indices, slice(None))
        frame, vertices, *axes = indices
        skin = self.skin[frame, vertices]
        xyz = self.points[vertices]
        result = np.einsum("...ij,...j->...i", skin[..., :3], xyz) + skin[..., 3]
        return result[(..., *axes)] if axes else result


def read_pose_bank():
    cache_path = RUNTIME / ("poses-" + fit.sha(MASTER)[:12] + "-" + fit.sha(MOTION)[:12] + ".npz")
    if not cache_path.exists():
        # The round-one cache function resolves its writable path through HERE.
        fit.HERE = ROOT
        try:
            fit.cache_scene()
        finally:
            fit.HERE = HERE
    names, neutral, female, *_ = fit.load_rest()
    faces = female[1]
    arrays = {}
    with zipfile.ZipFile(cache_path) as archive:
        for name in ("labels", "frames", "points", "matrices"):
            target = cache_path.with_name(cache_path.stem + "-" + name + ".npy")
            if not target.exists():
                pending = target.with_suffix(".pending")
                with archive.open(name + ".npy") as src, pending.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                pending.replace(target)
            arrays[name] = np.load(target, mmap_mode="r", allow_pickle=False)
    matrices = arrays["matrices"]
    rows = [(str(clip), float(frame), PoseTree(points, faces), points, faces)
            for clip, frame, points in zip(arrays["labels"], arrays["frames"], arrays["points"], strict=True)]
    return names, neutral, female, rows, matrices


def scan_in_batches(module, points, weights, samples, matrices):
    distances = np.empty((len(samples), len(weights)), dtype=np.float32)
    overlaps = np.empty(len(samples), dtype=np.int32)
    face_hits = np.zeros(len(module.source_faces), dtype=np.int32)
    constraints = []
    for start in range(0, len(samples), 48):
        batch = slice(start, start + 48)
        d, ov, hits, planes, _, _ = fit.scan(module, points, weights, samples[batch], matrices[batch])
        distances[batch], overlaps[batch] = d, ov
        face_hits += hits
        constraints.extend((start + row, ids, normal, depth, factors)
                           for row, ids, normal, depth, factors in planes)
    skin = SkinField(matrices, weights)
    return distances, overlaps, face_hits, constraints, skin, PosedCloth(points[module.unweld], skin)


def replace_mesh(asset, primitive, arrays, triangles, output):
    replacements = {}
    indices = primitive["indices"]
    faces = np.asarray(triangles, dtype=np.int32)
    used, inverse = np.unique(faces, return_inverse=True)
    for key, index in primitive["attributes"].items():
        old_dtype = asset.accessor(index).dtype
        values = arrays[key][used].astype(old_dtype)
        acc = asset.doc["accessors"][index]
        acc["count"] = len(values)
        if "min" in acc:
            acc.update(min=values.min(axis=0).tolist(), max=values.max(axis=0).tolist())
        replacements[acc["bufferView"]] = values.tobytes()
    old = asset.accessor(indices)
    acc = asset.doc["accessors"][indices]
    acc["count"] = faces.size
    replacements[acc["bufferView"]] = inverse.astype(old.dtype).tobytes()
    asset.repack_views(replacements)
    asset.write(output)


def interpolate_edges(module, asset, primitive, edges, fraction):
    """Split the surface and its UVs, tangent basis and four-joint skin together."""
    edges = np.asarray(edges)
    t = np.asarray(fraction, dtype=np.float32).reshape(-1, 1)
    attrs = primitive["attributes"]
    original = {name: asset.accessor(index) for name, index in attrs.items()}
    extension = {name: data[edges[:, 0]] * (1 - t) + data[edges[:, 1]] * t
                 for name, data in original.items() if name not in ("JOINTS_0", "WEIGHTS_0")}
    full = module.weights[edges[:, 0]] * (1 - t) + module.weights[edges[:, 1]] * t
    weights = full[:, module.name_indices]
    joints = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    weights = np.take_along_axis(weights, joints, axis=1)
    joints[weights == 0] = 0
    weights /= weights.sum(axis=1, keepdims=True)
    extension.update(JOINTS_0=joints, WEIGHTS_0=weights)
    extension["NORMAL"] = normal = fit.normalized(extension["NORMAL"])
    tangent = extension["TANGENT"][:, :3]
    tangent -= (tangent * normal).sum(axis=1, keepdims=True) * normal
    degenerate = np.linalg.norm(tangent, axis=1) < .01
    tangent[degenerate] = np.cross(normal[degenerate], np.eye(3)[abs(normal[degenerate]).argmin(axis=1)])
    extension["TANGENT"][:, :3] = fit.normalized(tangent)
    extension["TANGENT"][:, 3] = original["TANGENT"][edges[:, 0], 3]
    return {key: np.concatenate((data, extension[key].astype(data.dtype))) for key, data in original.items()}


def trim_lower_edge(module, output, height, inset, rise):
    """Shorten already-rigged panels and turn the cut edge inward."""
    asset = Glb(module.path)
    primitive, = asset.doc["meshes"][0]["primitives"]
    points = module.source_points
    z = points[:, 2]
    edges, seam, kept = {}, [], []
    for face in module.source_faces:
        polygon = []
        for a, b in zip(face, np.roll(face, -1)):
            if z[a] >= height:
                polygon.append(int(a))
            if (z[a] >= height) != (z[b] >= height):
                edge = tuple(sorted((a, b)))
                polygon.append(edges.setdefault(edge, len(points) + len(edges)))
        for i in range(1, len(polygon) - 1):
            kept.append((polygon[0], polygon[i], polygon[i + 1]))
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            if a >= len(points) and b >= len(points):
                seam.append((a, b))
    edge_pairs = np.asarray(list(edges))
    a, b = edge_pairs.T
    arrays = interpolate_edges(module, asset, primitive, edge_pairs, (height - z[a]) / (z[b] - z[a]))
    positions = arrays["POSITION"]
    ring = positions[len(points):].copy()
    # Give the opening a shallow turned-under edge. The textile UV of each
    # cut vertex carries around the fold and across any original panel seam.
    inward = arrays["NORMAL"][len(points):].copy()
    inward[:, 1] = 0
    inward = fit.normalized(inward)
    inside = ring - inset * inward
    inside[:, 1] += rise
    tangent = arrays["TANGENT"][len(points):].copy()
    tangent[:, :3] = fit.normalized(np.cross(np.tile((0, -1, 0), (len(ring), 1)), inward))
    normal = np.tile((0, -1, 0), (len(ring), 1))
    size = len(positions)
    for name, data in arrays.items():
        outer, inner = data[len(points):], data[len(points):]
        if name == "POSITION":
            outer, inner = ring, inside
        if name == "NORMAL":
            outer = inner = normal
        if name == "TANGENT":
            outer = inner = tangent
        arrays[name] = np.concatenate((data, outer.astype(data.dtype), inner.astype(data.dtype)))
    for a, b in seam:
        a, b = size + a - len(points), size + b - len(points)
        kept.extend(((b, a, a + len(ring)), (b, a + len(ring), b + len(ring))))
    replace_mesh(asset, primitive, arrays, kept, output)
    return len(seam)


def split_crossing_edges(module, face_hits, output):
    """Bisect long crossed edges, including matching edges across UV seams."""
    edges = np.sort(module.faces[:, [[0, 1], [1, 2], [2, 0]]], axis=2)
    lengths = np.linalg.norm(module.points[edges[:, :, 0]] - module.points[edges[:, :, 1]], axis=2)
    longest = lengths.argmax(axis=1)
    selected = set()
    budget = min(520, 6000 - len(module.faces))
    candidates = np.flatnonzero((face_hits > 0) & (lengths.max(axis=1) > .009))
    for face in sorted(candidates, key=lambda i: -lengths[i, longest[i]] * np.log1p(face_hits[i])):
        edge = tuple(edges[face, longest[face]])
        if edge not in selected:
            cost = int((edges == edge).all(axis=2).sum())
            if cost <= budget:
                selected.add(edge)
                budget -= cost
    if not selected:
        return 0

    asset = Glb(module.path)
    primitive, = asset.doc["meshes"][0]["primitives"]
    midpoints = {}
    triangles = []
    for triangle in module.source_faces:
        pieces = [tuple(triangle)]
        for a, b in zip(triangle, np.roll(triangle, -1)):
            if tuple(sorted((module.unweld[a], module.unweld[b]))) not in selected:
                continue
            key = tuple(sorted((a, b)))
            midpoint = midpoints.setdefault(key, len(module.source_points) + len(midpoints))
            for i, piece in enumerate(pieces):
                for j in range(3):
                    start, end, third = piece[j], piece[(j + 1) % 3], piece[(j + 2) % 3]
                    if tuple(sorted((start, end))) == key:
                        pieces[i] = (start, midpoint, third)
                        pieces.append((midpoint, end, third))
                        break
                else:
                    continue
                break
        triangles.extend(pieces)

    arrays = interpolate_edges(module, asset, primitive, list(midpoints), .5)
    replace_mesh(asset, primitive, arrays, triangles, output)
    return len(selected)


def relax_weights(module, weights, result, points, female, rest_tree, transfer):
    distances, _, hits = result[:3]
    contacted = np.zeros(len(points), dtype=np.float32)
    contacted[module.unweld[distances.min(axis=0) < .00075]] = 1
    contacted[module.faces[hits > 0].ravel()] = 1
    influence = contacted.copy()
    for _ in range(7):
        influence = np.maximum(influence, .90 * fit.average(influence, module.graph))
    if not np.any(influence):
        return weights
    mapped = fit.refit_contact_weights(module, points, weights, result, female, rest_tree)
    base = weights + transfer * (mapped - weights)
    field = module.welded(base).astype(np.float32)
    for _ in range(3):
        field += .32 * influence[:, None] * (fit.average(field, module.graph) - field)
    raw = field[module.unweld]
    # Smooth the active neighborhood, including coincident UV seam vertices.
    strength = influence[module.unweld, None]
    changed = fit.limit_weights(((1 - strength) * base + strength * raw).astype(np.float32))
    changed[strength[:, 0] == 0] = weights[strength[:, 0] == 0]
    return changed


def focus_constraints(constraints):
    focused = []
    for row, vertices, directions, signed, factors in constraints:
        active = (signed < .00075) | (factors < .9999)
        if np.any(active):
            focused.append((row, vertices[active], directions[active], signed[active], factors[active]))
    return focused


def bake_offset(module, result, points, origin):
    distances, counts, hits, constraints, skin, posed = result
    focused = focus_constraints(constraints)
    planes, incremental = fit.worst_planes(module, (distances, counts, hits, focused, skin, posed))
    axis = np.arange(len(points))
    active = incremental > 0
    total = points - origin
    requirement = np.where(active, np.clip(incremental + np.einsum("vij,vj->vi", planes, total), 0, fit.CAP), 0)

    def project(field, count):
        for _ in range(count):
            gap = np.where(active, requirement - np.einsum("vij,vj->vi", planes, field), 0)
            side = gap.argmax(axis=1)
            missing = np.maximum(0, gap[axis, side])
            field = limit(field + missing[:, None] * planes[axis, side], fit.CAP)
        return field

    corrected = project(total, 24)
    step = corrected - total
    # Diffuse the new field along connected cloth, then restore its lower bound.
    for _ in range(7):
        step = .64 * step + .36 * fit.average(step, module.graph)
    return origin + project(limit(total + step, fit.CAP), 24)


def solve_skin_contacts(module, points, origin, weights, result, matrices):
    """Find compatible position and weight changes when pose constraints conflict."""
    high = module.welded(weights).astype(np.float32)
    surrounding = fit.average(high, module.graph)[module.unweld]
    columns = np.argsort(-(weights + .15 * surrounding), axis=1, kind="stable")[:, :4]
    original = np.take_along_axis(weights, columns, axis=1)
    original /= original.sum(axis=1, keepdims=True)
    scale = .065
    planes, importance = fit.SOURCE["gather_planes"](
        focus_constraints(result[3]), points[module.unweld], columns, result[4], matrices,
        fit.MARGIN, scale)
    directions, targets = planes[..., :-1], planes[..., -1]
    active = importance > 0
    rows = np.arange(len(weights))
    delta = np.zeros((len(weights), 7), dtype=np.float32)
    for _ in range(28):
        gaps = np.where(active, targets - np.einsum("vsi,vi->vs", directions, delta), 0)
        index = gaps.argmax(axis=1)
        delta += .6 * np.maximum(0, gaps[rows, index, None]) * directions[rows, index]
        delta[:, :3] = limit(delta[:, :3], .006)
        updated = fit.SOURCE["simplex"](original + np.clip(delta[:, 3:] / scale, -.24, .24))
        delta[:, 3:] = (updated - original) * scale
    displacement = module.welded(delta[:, :3]).astype(np.float32)
    smoothed = displacement.copy()
    for _ in range(5):
        smoothed += .32 * (fit.average(smoothed, module.graph) - smoothed)
    direction = fit.normalized(displacement)
    required = np.linalg.norm(displacement, axis=1) - (smoothed * direction).sum(axis=1)
    smoothed += np.maximum(required, 0)[:, None] * direction
    adjusted = origin + limit(points + smoothed - origin, fit.CAP)

    weight_delta = np.zeros_like(weights)
    np.put_along_axis(weight_delta, columns, delta[:, 3:] / scale, axis=1)
    weighted = module.welded(weight_delta).astype(np.float32)
    for _ in range(3):
        weighted += .26 * (fit.average(weighted, module.graph) - weighted)
    next_weights = fit.limit_weights(np.maximum(0, weights + weighted[module.unweld]))
    next_weights[np.all(weighted[module.unweld] == 0, axis=1)] = weights[
        np.all(weighted[module.unweld] == 0, axis=1)]
    return adjusted, next_weights


def front_hip_trial(name, module, points, origin, weights, result, female, rest_tree):
    """Keep flexing thigh panels smooth while giving the measured contacts room."""
    _, y, z = points.T
    band = smoothstep(.29, .326, z) * (1 - smoothstep(.375, .419, z))
    front = 1 - smoothstep(-.090, -.062, y)
    normals = fit.nearest(rest_tree, points)[2]
    away = fit.normalized(np.c_[.25 * normals[:, 0], -np.ones(len(points)), .15 * normals[:, 2]])
    position = origin + limit(points + .0045 * (band * front)[:, None] * away - origin, fit.CAP)
    skin = relax_weights(module, weights, result, points, female, rest_tree, .08)
    return position, skin if name == "jeans" else weights


def armhole_trial(module, points, origin, weights, result, female, samples, matrices):
    """Reseat the blended sleeve attachment using nearby female body weights."""
    body_points, body_faces, body_weights, *_ = female
    _, body_sites, _, face_ids = fit.nearest(samples[0][2], points)
    faces = body_faces[face_ids]
    bary = fit.barycentric(body_points[faces], body_sites)
    mapped = np.einsum("vi,vib->vb", bary, body_weights[faces])
    for _ in range(2):
        mapped += .19 * (fit.average(mapped, module.graph) - mapped)

    x, y, z = points.T
    side = smoothstep(.052, .076, abs(x)) * (1 - smoothstep(.101, .124, abs(x)))
    height = smoothstep(.468, .506, z) * (1 - smoothstep(.541, .572, z))
    support = side * height
    field = np.c_[np.sign(x) * .001, .0035 * np.tanh((y + .032) / .015), np.full(len(x), .006)]
    compressed = points + support[:, None] * field
    raised = points + support[:, None] * np.array((0., 0., .009), dtype=np.float32)
    extended = points + support[:, None] * np.c_[
        np.sign(x) * .002, .012 * np.tanh((y + .032) / .014), np.full(len(x), .010)]
    sample_indices = set(range(0, len(samples), 17))
    penalties = result[1] + (result[0] < .0005).sum(axis=1)
    for clip in ("rest", *CLIPS):
        indices = np.array([i for i, row in enumerate(samples) if row[0] == clip])
        sample_indices.update(indices[np.argsort(-penalties[indices])[:5]])
    chosen = np.asarray(sorted(sample_indices))
    bank = [samples[i] for i in chosen]
    transforms = matrices[chosen]
    variants = []
    for blend in (.32, .63, .94):
        mix = blend * support[module.unweld, None]
        skin = fit.limit_weights(((1 - mix) * weights + mix * mapped[module.unweld]).astype(np.float32))
        skin[mix[:, 0] == 0] = weights[mix[:, 0] == 0]
        for shape in (points, compressed, raised, extended):
            shape = origin + limit(shape - origin, fit.CAP)
            metrics = scan_in_batches(module, shape, skin, bank, transforms)
            variants.append((fit.score(metrics), shape, skin))

    # The dress's cap sleeves provide a stable, already female-rigged sleeve
    # attachment. Match local panels while preserving the T-shirt UV mesh.
    reference = fit.Module(ROOT / "female-dress-v2.glb", module.names)
    surface = fit.tree_from(reference.source_points, reference.source_faces)
    normals = fit.normalized(module.welded(module.surface_normals(points[module.unweld])))
    width = smoothstep(.050, .073, abs(x)) * (1 - smoothstep(.106, .130, abs(x)))
    area = smoothstep(.457, .487, z) * (1 - smoothstep(.555, .588, z))
    mask = width * area
    guides = points.copy()
    suggested = module.welded(weights).astype(np.float32)
    for i in np.flatnonzero(mask > 0.):
        hits = surface.find_nearest_range(points[i], .033)
        compatible = [(p, n, face, d, float(np.dot(n, normals[i]))) for p, n, face, d in hits]
        compatible = [hit for hit in compatible if hit[4] >= .10]
        if not compatible:
            continue
        pos, outward, face, _, cosine = min(compatible, key=lambda h: h[3] + .010 * (1 - h[4]))
        corners = reference.source_faces[face]
        bary = fit.barycentric(reference.source_points[corners][None], np.array([pos]))[0]
        suggested[i] = bary @ reference.weights[corners]
        guides[i] = np.asarray(pos) + .0016 * np.asarray(outward) * cosine
    for amount in (.65, .85, 1.):
        mix = amount * mask
        diff = mix[:, None] * (guides - points)
        for _ in range(2):
            diff += .19 * (fit.average(diff, module.graph) - diff)
        shape = origin + limit(points + diff - origin, fit.CAP)
        share = mix[module.unweld, None]
        skin = fit.limit_weights(((1 - share) * weights + share * suggested[module.unweld]).astype(np.float32))
        skin[share[:, 0] == 0] = weights[share[:, 0] == 0]
        metrics = scan_in_batches(module, shape, skin, bank, transforms)
        variants.append((fit.score(metrics), shape, skin))
    proxy, shape, skin = min(variants, key=lambda item: item[0])
    print("RESEAT SLEEVE", round(proxy, 2), "on", len(bank), "poses", flush=True)
    return shape, skin


def probe_vertex_clearance(module, points, origin, result, samples):
    """Search small, bounded moves where nearby body normals change with pose."""
    distances, _, _, _, skin, posed = result
    penetration = distances.min(axis=0)
    first = np.argsort(penetration)
    source, welded = [], set()
    for index in first[:100]:
        vertex = module.unweld[index]
        if penetration[index] >= .00057 or len(source) == 24:
            break
        if vertex not in welded:
            source.append(index)
            welded.add(vertex)
    if not source:
        return points
    source = np.asarray(source)
    weld = module.unweld[source]
    axes = np.asarray([(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1)
                       for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)], dtype=np.float32)
    axes = fit.normalized(axes)
    offsets = np.concatenate([axes * step for step in (.0007, .0015, .0027, .0042, .0065)])
    offsets = np.concatenate((np.zeros((1, 3), dtype=np.float32), offsets))
    candidates = points[weld, None, :] + offsets[None]
    flat = candidates.reshape(-1, 3)
    clipped = limit(flat - np.repeat(origin[weld], len(offsets), axis=0), fit.CAP)
    movement = (clipped + np.repeat(origin[weld], len(offsets), axis=0)).reshape(candidates.shape) - points[weld, None, :]
    minimum = np.full(movement.shape[:2], 9.)
    deficit = np.zeros_like(minimum)
    count = np.zeros_like(minimum)
    for i, (_, _, tree, _, _) in enumerate(samples):
        position = posed[i, source, None, :] + np.einsum("vij,vkj->vki", skin[i, source, :, :3], movement)
        values = fit.nearest(tree, position.reshape(-1, 3))[0].reshape(minimum.shape)
        minimum = np.minimum(minimum, values)
        deficit += np.maximum(0., .00060 - values)
        count += values < 0
    costs = 3000 * deficit + count * 5 + 12000 * np.maximum(0., .00056 - minimum)
    costs += np.linalg.norm(movement, axis=2) * 8.
    finalists = np.argsort(costs, axis=1, kind="stable")[:, :10]
    last_movement = movement[np.arange(len(weld))[:, None], finalists]
    guard = np.full(finalists.shape, 9.)
    for i, (_, _, tree, _, _) in enumerate(samples):
        offsets = np.einsum("vij,vkj->vki", skin[i, source, :, :3], last_movement)
        current = posed[i, source, None, :] + offsets
        values = []
        for xyz in current.reshape(-1, 3):
            query = Vector(xyz)
            site, normal, _, distance = tree.find_nearest(query)
            nearby = tree.find_nearest_range(query, distance + 1.e-6)
            values.append(min(((query - q).dot(n) for q, n, _, _ in nearby),
                              default=(query - site).dot(normal)))
        guard = np.minimum(guard, np.asarray(values).reshape(finalists.shape))
    defended = np.take_along_axis(costs, finalists, axis=1) + 16000 * np.maximum(0., .00056 - guard)
    best = finalists[np.arange(len(weld)), defended.argmin(axis=1)]
    required = movement[np.arange(len(weld)), best]
    change = np.zeros_like(points)
    change[weld] = required
    # Smooth onto the immediate cloth neighborhood and retain the selected
    # motion-safe correction at every constrained vertex.
    for _ in range(2):
        change += .12 * (fit.average(change, module.graph) - change)
        change[weld] = required
    print("LOCAL CLEARANCE SEARCH", len(weld), "vertices", int((best > 0).sum()), "moved", flush=True)
    return origin + limit(points + change - origin, fit.CAP)


def rank_armhole_repairs(module, points, origin, weights, result, samples, matrices):
    """Rank small corrections around the residual contacts before the full sweep."""
    from polish_module import local_trial

    indices = set(range(0, len(samples), 35))
    distances, pairs = result[:2]
    penalty = pairs + 3 * (distances < 0).sum(axis=1)
    for clip in ("rest", *CLIPS):
        rows = np.array([i for i, record in enumerate(samples) if record[0] == clip])
        peaks = rows[np.argsort(-penalty[rows])[:5]]
        indices.update(peaks)
        indices.update(np.clip(peaks - 1, rows[0], rows[-1]))
        indices.update(np.clip(peaks + 1, rows[0], rows[-1]))
    ids = np.asarray(sorted(indices))
    bank, transforms = [samples[i] for i in ids], matrices[ids]
    baseline = fit.score(scan_in_batches(module, points, weights, bank, transforms))
    trial = bake_offset(module, result, points, origin)
    joint_shape, joint_weights = solve_skin_contacts(module, points, origin, weights, result, matrices)
    candidates = [(points + alpha * (trial - points), weights, f"offset {alpha}") for alpha in (.23, .46, .72)]
    candidates += [(points + alpha * (joint_shape - points),
                    fit.limit_weights(((1 - alpha) * weights + alpha * joint_weights).astype(np.float32)),
                    f"joint {alpha}") for alpha in (.36, .68)]
    local = local_trial(module, origin, points, weights, result, samples, matrices)
    candidates.append((local, weights, "local relief"))
    scored = []
    for shape, skin, label in candidates:
        value = fit.score(scan_in_batches(module, np.asarray(shape, dtype=np.float32), skin, bank, transforms))
        print("ARMHOLE OPTION", label, round(value, 2), "of", round(baseline, 2), flush=True)
        if value < baseline:
            scored.append((value, shape, skin))
    return [(shape, skin) for _, shape, skin in sorted(scored, key=lambda item: item[0])[:2]]


def preserve_images(module):
    images = module.glb.doc.get("images", [])
    previous = HERE / (module.path.name.removesuffix(".glb") + ".fit.json")
    records = json.loads(previous.read_text()).get("texture_images", []) if previous.exists() else []
    module.texture_cache[1024] = (records, [
        (image["mimeType"], module.glb.payload(image["bufferView"])) for image in images])


def assess(module, points, weights, samples, matrices):
    start = time.monotonic()
    result = scan_in_batches(module, np.asarray(points, dtype=np.float32), weights, samples, matrices)
    distances, pairs = result[:2]
    score = fit.score(result)
    print("SWEEP", module.path.name, "score", round(score, 3), "inside", int((distances < 0).sum(axis=1).max()),
          "pairs", int(pairs.max()), "min-mm", round(distances.min() * 1000, 3),
          "seconds", round(time.monotonic() - start, 1), flush=True)
    worst = np.argsort(distances.min(axis=1))[:4]
    for index in worst:
        if distances[index].min() < .00058 or pairs[index]:
            i = int(distances[index].argmin())
            print("WITNESS", samples[index][:2], i, points[module.unweld[i]].tolist(),
                  round(float(distances[index, i] * 1000), 4), int(pairs[index]), flush=True)
    return score, result


def fit_garment(name, data, iterations, resume=False, targeted=False):
    names, _, female, samples, matrices = data
    original = HERE / f"female-{name}.glb"
    module = fit.Module(original, names)
    trimmed = split = 0
    output = ROOT / f"female-{name}-v2.glb"
    report_path = output.with_suffix(".fit.json")
    history = []
    hems = {"jeans": (.134, .00075, .0012), "tshirt": (.430, .00045, .00085)}
    if name in hems:
        path = RUNTIME / "trimmed" / original.name
        path.parent.mkdir(exist_ok=True)
        if not resume:
            trimmed = trim_lower_edge(module, path, *hems[name])
        module = fit.Module(path, names)
    cosmetic = module.points.copy()
    weights = module.weights.copy()
    if resume:
        record = json.loads(report_path.read_text())
        split, trimmed, history = (record["split_edges"],
                                   record.get("turned_hem_boundary_edges", record.get("turned_cuff_boundary_edges")),
                                   record["history"])
        if split:
            module = fit.Module(RUNTIME / original.name, names)
            cosmetic = module.points.copy()
        existing = fit.Module(output, names)
        assert np.array_equal(existing.source_faces, module.source_faces)
        points, weights = module.welded(existing.source_points).astype(np.float32), existing.weights
        value, result = assess(module, points, weights, samples, matrices)
    else:
        points = cosmetic.copy()
        value, result = assess(module, points, weights, samples, matrices)
    if not resume and np.any(result[2]):
        tessellated = RUNTIME / original.name
        split = split_crossing_edges(module, result[2], tessellated)
        if split:
            module = fit.Module(tessellated, names)
            cosmetic = module.points.copy()
            weights = module.weights.copy()
            points = cosmetic.copy()
            value, result = assess(module, points, weights, samples, matrices)
    preserve_images(module)

    def save(iteration):
        rows = fit.summary(module, result, samples, female)
        actual = max(float(np.linalg.norm(points - cosmetic, axis=1).max()), 0.)
        history.append({"iteration": iteration, "score": value, "results": rows})
        module.write(output, points, weights)
        evidence = dict(source_sha256=fit.sha(original), output_sha256=fit.sha(output),
                        motion_sha256=fit.sha(MOTION), offset_cap_m=fit.CAP, margin_m=fit.MARGIN,
                        split_edges=split, turned_hem_boundary_edges=trimmed, max_baked_clearance_offset_m=actual,
                        hem_cut_height_m=hems[name][0] if name in hems else None,
                        triangles=len(module.faces), history=history)
        report_path.write_text(json.dumps(evidence, indent=2) + "\n")

    start = history[-1]["iteration"] if history else 0
    if not resume:
        save(start)
    for iteration in range(start + 1, start + iterations + 1):
        if not result[1].any() and result[0].min() >= .00053:
            break
        if targeted and name == "tshirt" and value >= 80:
            tests = rank_armhole_repairs(module, points, cosmetic, weights, result, samples, matrices)
            if not tests:
                break
        else:
            tests = [(bake_offset(module, result, points, cosmetic), weights)]
        if iteration == start + 1 and name == "tshirt" and value > 12 and not targeted:
            tests.insert(0, armhole_trial(module, points, cosmetic, weights, result, female, samples, matrices))
        if iteration == start + 1 and value < 80:
            tests.insert(0, (probe_vertex_clearance(module, points, cosmetic, result, samples), weights))
        elif iteration == start + 1 and (name == "jeans" or (name == "dress" and value > 1)):
            tests.insert(0, front_hip_trial(name, module, points, cosmetic, weights, result, female, samples[0][2]))
        if iteration == 1 and value > 40 and not resume:
            relaxed = relax_weights(module, weights, result, points, female, samples[0][2], .18)
            tests.insert(0, (tests[0][0], relaxed))
        best = value, points, weights, result
        for candidate, skin in tests:
            attempt, metrics = assess(module, candidate, skin, samples, matrices)
            if attempt < best[0]:
                best = attempt, candidate, skin, metrics
            if best[0] == 0 or attempt < .52 * value:
                break
        if best[0] >= value and not targeted:
            if value > 12:
                candidate, skin = solve_skin_contacts(module, points, cosmetic, weights, result, matrices)
                attempt, metrics = assess(module, candidate, skin, samples, matrices)
                if attempt < best[0]:
                    best = attempt, candidate, skin, metrics
        if best[0] >= value and not targeted:
            if value < 80:
                candidate = probe_vertex_clearance(module, points, cosmetic, result, samples)
                attempt, metrics = assess(module, candidate, weights, samples, matrices)
                if attempt < best[0]:
                    best = attempt, candidate, weights, metrics
        if best[0] >= value and not targeted:
            from polish_module import local_trial
            candidate = local_trial(module, cosmetic, points, weights, result, samples, matrices)
            attempt, metrics = assess(module, candidate, weights, samples, matrices)
            if attempt < best[0]:
                best = attempt, candidate, weights, metrics
        if best[0] >= value:
            break
        value, points, weights, result = best
        save(iteration)
    print("RESULT", name, value, flush=True)


if __name__ == "__main__":
    RUNTIME.mkdir(exist_ok=True)
    data = read_pose_bank()
    args = arguments()
    labels = [name for name in args if not name.startswith("--")] or ("dress", "jeans", "tshirt")
    for label in labels:
        fit_garment(label, data, 14, resume="--resume" in args, targeted="--targeted" in args)
