"""Repair v2 Studio T-shirt against the corrected master clips in Blender 5."""
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys

import bpy
import numpy as np


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "round2"
ROUND2 = runpy.run_path(str(BASE / "fit_tshirt_r2.py"))
PRIOR = ROUND2["PRIOR"]
SHARED = ROUND2["SHARED"]
FIXED = HERE.parents[2] / "body-fix" / "motion_fixed.glb"
V2 = BASE / "tshirt_v2.glb"
OUT = HERE
V3 = OUT / "tshirt_v3.glb"
SHARED.update(OUT=OUT, NAME="tshirt_v3", GLB=V3, MOTION=FIXED, TRIANGLE_LIMIT=8000)
ROUND2["render_evidence"].__globals__.update(OUT=OUT, GLB=V3)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


CLIPS = SHARED["CLIPS"]
TARGET = .0005
MARGIN = .002
CAP = .030
MAX_PASSES = 16
stats = PRIOR["stats"]
signed = PRIOR["signed"]
coords = PRIOR["coordinates"]
faces_of = PRIOR["triangles"]
mean = PRIOR["mean_neighbors"]
skin = PRIOR["skin"]
limit_weights = PRIOR["limit_weights"]
region = PRIOR["region_faces"]
write_json = PRIOR["write_json"]


def baseline():
    SHARED.update(NAME="tshirt_v2", GLB=V2)
    inspect_export = SHARED["inspect_export"]

    def baseline_structure():
        SHARED["OUT"] = BASE
        try:
            return inspect_export()
        finally:
            SHARED["OUT"] = HERE / ".runtime"

    SHARED["inspect_export"] = baseline_structure
    PRIOR["verify"]()


def report_scan(label, samples, d, pairs):
    metrics = PRIOR["summarize"](samples, d, pairs)
    print("FIT", label, "pairs", int(pairs.sum()), "inside", int((d < 0).sum()),
          "under 0.5 mm", int((d < TARGET).sum()), "min mm", round(float(d.min()) * 1000, 4),
          [(name, m["max_triangle_pairs"], round(m["min_signed_dist"] * 1000, 3))
           for name, m in metrics.items()], flush=True)
    return metrics


def score(d, pairs):
    # Weight the cap, hard gate, and clearance in that order on the same poses.
    deficit = 1000 * np.maximum(.00065 - d, 0)
    return (float(1e6 * (pairs[0] + np.count_nonzero((d[0] < TARGET) | (d[0] > CAP))))
            + float(pairs.sum() + 7 * np.count_nonzero(d < 0))
            + float(85 * np.square(deficit.max()) + 2.5 * np.square(deficit).sum()))


def pack_contacts(contacts):
    frame = np.concatenate([np.full(len(c[1]), c[0], np.int32) for c in contacts])
    indices, bary, direction, distance = (np.concatenate(part) for part in zip(
        *(c[1:] for c in contacts)))
    return frame, indices, bary, direction, distance


def local_skin_columns(weights, support, affected):
    # Keep the original nonzero bindings at untouched vertices. For the patch,
    # allow a stronger adjacent-body influence to replace a negligible one.
    preference = weights.copy()
    preference[affected] += .22 * support[affected]
    columns = np.argsort(-preference, axis=1, kind="stable")[:, :4]
    active = np.take_along_axis(weights, columns, axis=1)
    active /= active.sum(axis=1, keepdims=True)
    return columns, active


def worst_offset(indices, bary, directions, distance, count, margin):
    # Invert the blended pose matrix adjoint along the contact direction.
    # For a face witness, distribute the displacement over its three corners.
    gradient = directions * bary[..., None]
    impulse = (np.maximum(margin - distance, 0) /
               np.square(gradient).sum(axis=(1, 2)).clip(.10))
    moves = gradient.reshape(-1, 3) * np.repeat(impulse, 3)[:, None]
    flat = indices.ravel()
    length = np.linalg.norm(moves, axis=1)
    peak = np.zeros(count, dtype=np.float32)
    np.maximum.at(peak, flat, length)
    winning = np.flatnonzero((length >= peak[flat]) & (length > 0))
    winner = np.full(count, -1, dtype=np.int32)
    np.maximum.at(winner, flat[winning], winning)
    result = np.zeros((count, 3), dtype=np.float32)
    result[winner >= 0] = moves[winner[winner >= 0]]
    return result


def solve(points, weights, support, transforms, matrices, contacts, links, reference, margin,
          weight_scale):
    frame, ids, bary, direction, distance = pack_contacts(contacts)
    count = len(points)
    mapped = np.einsum("ni,nkij->nkj", direction, matrices[frame[:, None], ids, :, :3])
    worst = worst_offset(ids, bary, mapped, distance, count, margin)
    smoothed = ROUND2["laplacian_floor"](worst, links)
    focus = np.linalg.norm(smoothed, axis=1) > 0
    columns, active = local_skin_columns(weights, support, focus)
    joint = transforms[frame[:, None, None], columns[ids]]
    joint_pos = np.einsum("nkjlm,nkm->nkjl", joint[..., :3], points[ids]) + joint[..., 3]
    skin_dir = np.einsum("nl,nkjl->nkj", direction, joint_pos)
    skin_dir -= skin_dir.mean(axis=2, keepdims=True)

    axis = np.ones_like(points)
    cuff = (np.abs(reference[:, 0]) > .112) & (reference[:, 2] > .51)
    axis[cuff, 0] = .28
    gradient = np.concatenate((mapped * axis[ids], weight_scale * skin_dir), axis=2)
    gradient *= bary[..., None]
    gram = np.square(gradient).sum(axis=(1, 2)).clip(.1)
    flat = ids.ravel()
    step = np.zeros((count, 7), dtype=np.float32)
    step[:, :3] = .72 * smoothed
    # Reweight by the remaining violation so long nearly-identical poses
    # do not drown out a brief but deep contact.
    for _ in range(21):
        residual = np.maximum(margin - distance - np.einsum("nkj,nkj->n", gradient, step[ids]), 0)
        importance = np.maximum(residual, .000030) ** 1.35
        importance[frame == 0] *= 4
        amount = importance * residual / gram
        contribution = gradient * amount[:, None, None]
        normalizer = np.bincount(flat, weights=(importance[:, None] * bary).ravel(),
                                 minlength=count).clip(1e-12)
        update = np.column_stack([np.bincount(flat, weights=column.ravel(), minlength=count)
                                  for column in contribution.transpose(2, 0, 1)]) / normalizer[:, None]
        step += (.80 * update).astype(np.float32)
        step += .12 * (mean(step, links) - step)
        step[:, :3] += .032 * (.6 * smoothed - step[:, :3])
        length = np.linalg.norm(step[:, :3], axis=1).clip(1e-9)
        step[:, :3] *= np.minimum(1, .010 / length)[:, None]
        if weight_scale:
            adjusted = ROUND2["project_simplex"](active + weight_scale * step[:, 3:])
            step[:, 3:] = (adjusted - active) / weight_scale
    revised = weights.copy()
    if weight_scale:
        focused = np.flatnonzero(np.linalg.norm(step[:, 3:], axis=1) > .00001)
        revised[focused] = 0
        revised[focused[:, None], columns[focused]] = adjusted[focused]
    return step[:, :3] * axis, revised, smoothed


def cap_candidate(points, reference, rest, cuff):
    delta = points - reference
    points = reference + delta * np.minimum(1, CAP / np.linalg.norm(delta, axis=1).clip(1e-9))[:, None]
    for _ in range(3):
        clearance, normal = signed(rest, points)
        points += ((np.maximum(.00095 - clearance, 0)
                    - np.maximum(clearance - CAP + .0001, 0))[:, None] * normal)
        points[cuff, 0] = np.clip(points[cuff, 0], reference[cuff, 0] - .004,
                                 reference[cuff, 0] + .004)
        points[:, 2] = points[:, 2].clip(.389)
    return points


def refine_patches(points, weights, reference, faces, samples, transforms, distances, contacts,
                   move, revised, support, scan_rows, iteration):
    """Choose a smooth patch move by testing the exact local triangle BVH."""
    _, ids, bary, _, depth = pack_contacts(contacts)
    # One corner per plane suffices to choose a connected patch center.
    anchors = ids[np.arange(len(ids)), bary.argmax(axis=1)]
    loads = np.bincount(anchors, weights=1 + np.maximum(TARGET - depth, 0) * 1800,
                        minlength=len(points)).astype(np.float32)
    severity = distances.min(axis=0).copy()
    np.minimum.at(severity, anchors, depth)
    loads[severity >= .00105] *= .045
    current, binding = points.copy(), weights.copy()
    tree = samples[0][2]
    changed = 0
    examined = 0
    # Individual patch proposals are tested on the intersecting faces plus
    # their touching triangles at every vertex carried by the patch.
    while examined < 19 and loads.max() > .1:
        seed = loads.argmax()
        scale = np.array([1.05, .72, .90], dtype=np.float32)
        gap = np.linalg.norm((reference - reference[seed]) * scale, axis=1)
        radius = (.026, .017, .010)[(iteration - 6) % 3]
        if reference[seed, 2] < .435:
            radius *= 1.18
        falloff = np.maximum(1 - (gap / radius) ** 2, 0) ** 2
        affected = falloff > .012
        active = np.flatnonzero(affected)
        loads[gap < radius * .60] = 0
        if not len(active):
            continue
        hit = affected[anchors] & (depth < .0024)
        if not hit.any():
            continue
        examined += 1
        touched_faces = faces[affected[faces].any(axis=1)]
        local, loc_faces = np.unique(touched_faces, return_inverse=True)
        loc_faces = loc_faces.reshape(-1, 3)
        affected = affected[local]
        taper = np.where(affected, falloff[local], 0)[:, None]
        original = current[local].copy()
        original_w = binding[local].copy()
        tri = original[loc_faces]
        normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        poses = transforms[scan_rows]
        sub_samples = [samples[i] for i in scan_rows]

        def cost(p, w):
            clearance, _ = signed(tree, p[affected])
            if clearance.min() < .00068 or clearance.max() > CAP - .00003:
                return float("inf")
            if np.linalg.norm(p - reference[local], axis=1).max() > CAP or p[:, 2].min() < .389:
                return float("inf")
            t = p[loc_faces]
            normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
            if ((normal * normals).sum(axis=1) < 0).any():
                return float("inf")
            posed, _ = skin(p, w, poses)
            score = 0.0
            worst = 0.0
            for i, sample in enumerate(sub_samples):
                d, _, _, pairs, _ = PRIOR["scan_frame"](posed[i], loc_faces, sample)
                if not i and len(pairs):
                    return float("inf")
                deficit = 1000 * np.maximum(.00065 - d[affected], 0)
                score += len(pairs) + 7 * (d[affected] < 0).sum() + 2.5 * np.square(deficit).sum()
                worst = max(worst, float(deficit.max()))
            return float(score) + 85 * worst ** 2

        base = cost(original, original_w)
        if base <= .0001:
            continue
        best = base, original, original_w
        facet_normal = signed(tree, reference[[seed]])[1][0]
        weight_step = revised[local] - original_w
        weight_support = support[local] - original_w
        proposal = move[local] * np.sqrt(taper)
        extent = max(.0014, radius * .24)
        axes = np.r_[np.eye(3), -np.eye(3), [facet_normal, -facet_normal]]
        offsets = [extent * vec * taper for vec in axes]
        offsets += [.43 * extent * vec * taper for vec in axes]
        if radius >= .016:
            directions = np.array([[0., -1., -.32], [0., 1., .32], [0., 1., -.32],
                                   [.32, -1., 0.], [-.32, -1., 0.], [.32, 1., 0.], [-.32, 1., 0.]])
            offsets += [1.5 * extent * vec * taper for vec in directions]
        trials = [(p, np.zeros_like(original_w)) for p in offsets]
        trials += [(f * proposal, f * taper * weight_step) for f in (.24, .52, 1., 1.6)]
        trials += [(f * proposal, f * taper * weight_support) for f in (0., .65, 1.)]
        trials += [(offsets[j], .42 * taper * weight_support) for j in (1, 2, 4, 5, 6)]
        for offset, change in trials:
            p = original + offset
            cuff = (abs(reference[local, 0]) > .112) & (reference[local, 2] > .51)
            cuff &= affected
            p[cuff, 0] = np.clip(p[cuff, 0], reference[local[cuff], 0] - .004,
                                 reference[local[cuff], 0] + .004)
            w = limit_weights(np.maximum(original_w + change, 0))
            value = cost(p, w)
            if value < best[0]:
                best = value, p, w
        if best[0] < base:
            changed += 1
            current[local] = best[1]
            binding[local] = best[2]
            print("PATCH", iteration, seed, len(active), round(base, 1), "->", round(best[0], 1),
                  flush=True)
    print("PATCHES APPLIED", changed, flush=True)
    return current, binding


def run_bake(garment, body, names, points, weights, samples, transforms):
    history = []
    reference = points.copy()
    best = None
    rest = samples[0][2]
    split_passes = {0, 3}
    for iteration in range(MAX_PASSES + 1):
        faces, links = faces_of(garment.data), PRIOR["adjacency"](garment.data)
        cuff = (np.abs(reference[:, 0]) > .112) & (reference[:, 2] > .51)
        d, pairs, (hits, long_hits, contacts, matrices) = ROUND2["scan"](
            points, weights, faces, samples, transforms, collect=True)
        metrics = report_scan(iteration, samples, d, pairs)
        value = score(d, pairs)
        if best is None or value < best[0]:
            best = value, points.copy(), weights.copy(), reference.copy(), garment.data, iteration
        record = {"pass": iteration, "score": value, "triangles": len(faces), "clips": metrics}
        history.append(record)
        write_json("fit_history.json", {"source_glb_sha256": digest(V2), "motion_sha256": digest(FIXED),
                                        "offset_margin_m": MARGIN, "passes": history})
        if (d.min() >= TARGET and not pairs.any() and d[0].max() <= CAP) or iteration == MAX_PASSES:
            break
        if iteration in split_passes and hits.any():
            previous = garment.data
            p, w, r, count = ROUND2["split_loft"](
                garment, points, weights, reference, faces, hits, long_hits, add_loft=iteration >= 3)
            if count:
                new_faces = faces_of(garment.data)
                new_links = PRIOR["adjacency"](garment.data)
                p = PRIOR["guard_rest"](p, new_faces, samples[0], r, new_links)
                p = cap_candidate(p, r, rest, (np.abs(r[:, 0]) > .112) & (r[:, 2] > .51))
                dd, _, _, oo, _ = PRIOR["scan_frame"](p, new_faces, samples[0])
                if not len(oo) and dd.min() >= TARGET and dd.max() <= CAP:
                    points, weights, reference = p, w, r
                    print("LOFT", iteration, count, "edges", flush=True)
                    continue
                rejected = garment.data
                garment.data = previous
                bpy.data.meshes.remove(rejected)
                print("LOFT rest guard rejected", iteration, count, flush=True)
        rows = ROUND2["choose_rows"](samples, d, pairs)
        previous_score = score(d[rows], pairs[rows])
        support = ROUND2["weight_support"](points, body, names, rest, samples[0][4], links, weights)
        margin = MARGIN if d.min() < -.0007 or iteration <= 6 else .00135
        move, revised, raw = solve(points, weights, support, transforms, matrices, contacts, links,
                                   reference, margin, weight_scale=2.6)
        pure, _, _ = solve(points, weights, support, transforms, matrices, contacts, links,
                           reference, margin, weight_scale=0)
        zone = region(reference)
        blend = np.where(np.isin(zone, ("hem", "shoulder / armpit", "sleeve / cuff")), .14, .06)
        weight_delta = revised - weights
        weight_delta += blend[:, None] * (mean(weight_delta, links) - weight_delta)
        trial = previous_score, points, weights, "unchanged"
        for tag, step, wd, gain in (
            ("geometry", pure, 0 * weight_delta, 1.0),
            ("coupled", move, weight_delta, .90),
            ("coupled damped", move, weight_delta, .43),
            ("worst offsets", raw, 0 * weight_delta, .68),
            ("skin", move * .38, weight_delta, 1.0),
            ("geometry relaxed", mean(pure, links), 0 * weight_delta, .72),
        ):
            p = cap_candidate(points + gain * step, reference, rest, cuff)
            p = ROUND2["prevent_flips"](points, p, faces)
            p = ROUND2["retain_clear_rest"](points, p, faces, samples[0])
            w = limit_weights(np.maximum(weights + gain * wd, 0))
            dd, oo, _ = ROUND2["scan"](p, w, faces, samples, transforms, rows)
            value = score(dd, oo)
            if value < trial[0]:
                trial = value, p, w, tag
        if iteration >= 9:
            p, w = refine_patches(points, weights, reference, faces, samples, transforms, d,
                                  contacts, move, revised, support, rows, iteration)
            dd, oo, _ = ROUND2["scan"](p, w, faces, samples, transforms, rows)
            print("PATCH TRIAL", round(score(dd, oo), 2), int(oo.sum()),
                  round(float(dd.min()) * 1000, 4), flush=True)
            if score(dd, oo) < trial[0]:
                trial = score(dd, oo), p, w, "exact triangle patches"
        print("TRIAL", trial[3], round(previous_score, 1), "->", round(trial[0], 1), flush=True)
        points, weights = trial[1:3]
        record["step"] = trial[3]
    _, points, weights, reference, mesh, selected = best
    garment.data = mesh
    write_json("fit_history.json", {"source_glb_sha256": digest(V2), "motion_sha256": digest(FIXED),
                                    "offset_margin_m": MARGIN, "selected_pass": selected,
                                    "offset_m": stats(np.linalg.norm(points - reference, axis=1)),
                                    "passes": history})
    return points, weights


def build():
    SHARED["GLB"] = V2
    scene, arm, body, garment, names = ROUND2["start"]()
    SHARED["GLB"] = V3
    points = coords(garment.data)
    weights = limit_weights(PRIOR["read_weights"](garment, names))
    print("ROUND 2 INPUT", len(points), len(faces_of(garment.data)), flush=True)
    samples, transforms = PRIOR["cache_motion"](scene, arm, body, names)
    print("CACHED", len(samples), "poses with the fixed motion", flush=True)
    points, weights = run_bake(garment, body, names, points, weights, samples, transforms)
    PRIOR["export"](garment, arm, body, points, names, weights)
    history = json.loads((OUT / "fit_history.json").read_text())
    history["repaired_export_tangents"] = repair_tangents(V3)
    write_json("fit_history.json", history)


def repair_tangents(path):
    """Repair zero-length exported tangents while preserving the UV chart."""
    data = bytearray(path.read_bytes())
    json_size = struct.unpack_from("<I", data, 12)[0]
    model = json.loads(data[20:20 + json_size])
    bin_start = 28 + json_size

    def accessor(index):
        acc = model["accessors"][index]
        view = model["bufferViews"][acc["bufferView"]]
        dtype = np.dtype({5121: "u1", 5123: "<u2", 5125: "<u4",
                          5126: "<f4"}[acc["componentType"]])
        width = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[acc["type"]]
        start = bin_start + view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride", width * dtype.itemsize)
        return np.ndarray((acc["count"], width), dtype=dtype, buffer=data, offset=start,
                          strides=(stride, dtype.itemsize))

    repaired = 0
    for primitive in model["meshes"][0]["primitives"]:
        attr = primitive["attributes"]
        normals = accessor(attr["NORMAL"])
        tangents = accessor(attr["TANGENT"])
        triangles = accessor(primitive["indices"]).reshape(-1, 3)
        lengths = np.linalg.norm(tangents[:, :3], axis=1)
        for vertex in np.flatnonzero(~np.isfinite(lengths) | (abs(lengths - 1) > .0003)):
            normal = normals[vertex]
            connected = np.unique(triangles[(triangles == vertex).any(axis=1)])
            good = connected[abs(lengths[connected] - 1) <= .0003]
            if len(good):
                nearest_normal = good[(normals[good] @ normal).argmax()]
                axis = tangents[nearest_normal, :3].copy()
            else:
                axis = np.eye(3, dtype=np.float32)[abs(normal).argmin()]
            direction = axis - (axis @ normal) * normal
            tangent_length = np.linalg.norm(direction)
            if tangent_length < 1e-7:
                axis = np.eye(3, dtype=np.float32)[abs(normal).argmin()]
                direction = axis - (axis @ normal) * normal
                tangent_length = np.linalg.norm(direction)
            tangents[vertex, :3] = direction / tangent_length
            if tangents[vertex, 3] not in (-1., 1.):
                tangents[vertex, 3] = 1.
            repaired += 1
    if repaired:
        path.write_bytes(data)
    print("TANGENTS repaired", repaired, flush=True)
    return repaired


def glb_sections(path):
    payload = path.read_bytes()
    json_bytes = struct.unpack_from("<I", payload, 12)[0]
    return json.loads(payload[20:20 + json_bytes]), payload[28 + json_bytes:]


def verify():
    PRIOR["verify"]()
    result = json.loads((OUT / "export_check.json").read_text())
    old, old_bin = glb_sections(V2)
    new, new_bin = glb_sections(V3)

    def embedded(document, binary, view_id):
        view = document["bufferViews"][view_id]
        start = view.get("byteOffset", 0)
        return binary[start:start + view["byteLength"]]

    def bind_matrices(document, binary):
        skin = document["skins"][0]
        view = document["accessors"][skin["inverseBindMatrices"]]["bufferView"]
        return embedded(document, binary, view)

    def images(document, binary):
        return sorted(hashlib.sha256(embedded(document, binary, img["bufferView"])).hexdigest()
                      for img in document["images"])

    result["motion_sha256"] = digest(FIXED)
    result["source_glb_sha256"] = digest(V2)
    result["material_matches_round2"] = old["materials"] == new["materials"]
    result["embedded_images_match_round2"] = images(old, old_bin) == images(new, new_bin)
    result["inverse_bind_matrices_match_round2"] = bind_matrices(old, old_bin) == bind_matrices(new, new_bin)
    blend = OUT / "tshirt_v3.blend"
    result["blend_sha256"] = digest(blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, shirt = (scene.objects[name] for name in ("Armature", "Base_Body", "tshirt_v3"))
    assert body.type == shirt.type == "MESH"
    assert len(arm.data.bones) == 65
    assert len(faces_of(shirt.data)) == result["triangles"]
    assert any(mod.type == "ARMATURE" and mod.object == arm for mod in shirt.modifiers)
    packed = {node.image for material in shirt.data.materials for node in material.node_tree.nodes
              if node.type == "TEX_IMAGE" and node.image is not None and node.image.packed_file}
    assert len(packed) == 3
    result["blend_reopened"] = True
    write_json("export_check.json", result)
    dense = json.loads((OUT / "dense_check.json").read_text())
    dense.update(motion_sha256=digest(FIXED), master_sha256=digest(SHARED["MASTER"].resolve()))
    write_json("dense_check.json", dense)


def render():
    ROUND2["render_evidence"]()
    manifest = json.loads((OUT / "render_info.json").read_text())
    manifest["motion_sha256"] = digest(FIXED)
    write_json("render_info.json", manifest)


if __name__ == "__main__":
    (HERE / ".runtime").mkdir(exist_ok=True)
    if "--baseline" in sys.argv:
        baseline()
    elif "--repair-tangents" in sys.argv:
        repair_tangents(V3)
    elif "--verify" in sys.argv:
        verify()
    elif "--renders" in sys.argv:
        render()
    else:
        build()
