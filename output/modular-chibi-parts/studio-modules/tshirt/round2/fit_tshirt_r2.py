"""Fit the Studio T-shirt on the master at half-frame intervals in Blender 5."""
from pathlib import Path
from contextlib import redirect_stdout
import hashlib
import io
import json
import math
import runpy
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
PRIOR = runpy.run_path(str(HERE.parent / "fit_tshirt.py"))
SHARED = PRIOR["verify"].__globals__
SHARED.update(OUT=HERE, NAME="tshirt_v2", GLB=HERE / "tshirt_v2.glb", TRIANGLE_LIMIT=8000)
if "--workspace" in sys.argv:
    directory = (HERE / sys.argv[sys.argv.index("--workspace") + 1]).resolve()
    if directory == HERE or not directory.is_relative_to(HERE):
        raise ValueError("Workspace must be a subdirectory of round 2")
    directory.mkdir(exist_ok=True)
    SHARED.update(OUT=directory, GLB=directory / "tshirt_v2.glb")
GLB = SHARED["GLB"]
OUT = SHARED["OUT"]
CLIPS = SHARED["CLIPS"]
TARGET, MARGIN, REST_CAP = .0005, .002, .030
MAX_PASSES = 16
coordinates = PRIOR["coordinates"]
triangles = PRIOR["triangles"]
geometry = PRIOR["geometry"]
signed = PRIOR["signed"]
adjacency = PRIOR["adjacency"]
mean_neighbors = PRIOR["mean_neighbors"]
limit_weights = PRIOR["limit_weights"]
project_simplex = PRIOR["project_simplex"]
read_weights = PRIOR["read_weights"]
skin = PRIOR["skin"]
summarize = PRIOR["summarize"]
write_json = PRIOR["write_json"]


def start():
    scene, arm, body, garment = PRIOR["reimport"]()
    # The round 1 GLB is the input. Weld geometric duplicates while retaining
    # separate corner UVs, so constraints and skinning stay continuous at seams.
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=.0000003)
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.data.update()
    names = tuple(b.name for b in arm.data.bones)
    return scene, arm, body, garment, names


def scan(points, weights, faces, samples, transforms, rows=None, collect=False):
    if rows is None:
        rows = np.arange(len(samples))
    posed, matrices = skin(points, weights, transforms[rows])
    values = np.empty(posed.shape[:2], dtype=np.float32)
    overlaps = np.empty(len(rows), dtype=np.int32)
    hits = np.zeros(len(faces), dtype=np.int32)
    long_hits = np.zeros((len(faces), 3), dtype=np.int32)
    constraints = []
    for i, row in enumerate(rows):
        d, normals, _, pairs, witness = PRIOR["scan_frame"](
            posed[i], faces, samples[row], collect=collect
        )
        values[i], overlaps[i] = d, len(pairs)
        if not collect:
            continue
        v = np.flatnonzero(d < MARGIN + .0007)
        ids = np.repeat(v[:, None], 3, axis=1)
        bary = np.zeros_like(ids, dtype=np.float32)
        bary[:, 0] = 1
        normals, d = normals[v], d[v]
        if witness is not None:
            fi, co, wd, wn, _ = witness
            hits[fi] += 1
            edge = posed[i, faces[fi]]
            long_hits[fi] += np.linalg.norm(edge - np.roll(edge, -1, axis=1), axis=2) > .012
            ids = np.concatenate((ids, faces[fi]))
            bary = np.concatenate((bary, co))
            normals = np.concatenate((normals, wn))
            d = np.r_[d, wd]
        if len(ids):
            constraints.append((i, ids, bary, normals, d))
    return values, overlaps, (hits, long_hits, constraints, matrices)


def summarize_run(iteration, samples, distances, overlaps):
    summary = summarize(samples, distances, overlaps)
    print("FIT", iteration, "pairs", int(overlaps.sum()), "inside", int((distances < 0).sum()),
          "worst mm", round(float(distances.min()) * 1000, 3),
          [(k, v["max_triangle_pairs"], round(v["min_signed_dist"] * 1000, 2))
           for k, v in summary.items()], flush=True)
    return summary


def score(distances, overlaps):
    deficit = np.maximum(TARGET - distances, 0) * 1000
    rest = (overlaps[0] + (distances[0] < TARGET).sum() + (distances[0] > REST_CAP).sum())
    return float(120_000 * rest + .65 * overlaps.sum() + 7.0 * (distances < 0).sum()
                 + .32 * np.square(deficit).sum() + 210 * deficit.max() ** 2)


def cap_rest(points, reference, rest):
    d = points - reference
    points = reference + d * np.minimum(1, REST_CAP / np.linalg.norm(d, axis=1).clip(1e-9))[:, None]
    cuff = (abs(reference[:, 0]) > .108) & (reference[:, 2] > .51)
    for _ in range(4):
        values, direction = signed(rest, points)
        violation = np.maximum(.0018 - values, 0) - np.maximum(values - REST_CAP + .00012, 0)
        points += direction * violation[:, None]
        points[cuff, 0] = np.clip(points[cuff, 0], reference[cuff, 0] - .005, reference[cuff, 0] + .005)
        points[:, 2] = np.maximum(points[:, 2], .390)
    return points


def weight_support(points, body, names, rest, faces, links, previous):
    body_weights = read_weights(body, names)
    rest_body = coordinates(body.data)
    weights = []
    for p in points:
        q, _, i, _ = rest.find_nearest(p)
        tri = rest_body[faces[i]]
        uv = np.linalg.lstsq((tri[1:] - tri[0]).T, np.asarray(q) - tri[0], rcond=None)[0]
        bary = np.clip(np.r_[1 - uv.sum(), uv], 0, 1)
        weights.append(bary @ body_weights[faces[i]])
    weights = np.asarray(weights, dtype=np.float32)
    for j, name in enumerate(names):
        short = name.split(":")[-1]
        if any(t in short for t in ("Leg", "Foot", "Toe")):
            weights[:, names.index("mixamorig:Hips")] += .6 * weights[:, j]
            weights[:, j] *= .4
        if short in {"Head", "HeadTop_End"}:
            weights[:, names.index("mixamorig:Neck")] += weights[:, j]
            weights[:, j] = 0
    for _ in range(2):
        weights += .23 * (mean_neighbors(weights, links) - weights)
    return limit_weights(.5 * weights + .5 * previous)


def initial_search(garment, body, names, samples, transforms, reference, original_weights):
    faces, links = triangles(garment.data), adjacency(garment.data)
    rest = samples[0][2]
    clearance, normal = signed(rest, reference)
    fresh_weights = weight_support(reference, body, names, rest, samples[0][4], links, original_weights)
    rows = np.r_[0, np.arange(1, len(samples), 8)]
    region = PRIOR["region_faces"](reference)
    torso = np.isin(region, ("front panel", "back panel", "hem"))
    candidates = []
    # Shoulder/cuff loading remains local. Compare a close-cut torso against
    # a loose panel to evaluate which side of the swinging forearms can clear.
    for label, desired, w in [
        ("round1", clearance, original_weights),
        ("rebind", clearance, fresh_weights),
        ("close", np.where(torso, .0035, .006), fresh_weights),
        ("roomy", np.where(torso, .027, .020), fresh_weights),
        ("medium", np.where(torso, .014, .011), fresh_weights),
    ]:
        p = reference + (desired - clearance)[:, None] * normal
        if label != "round1":
            move = p - reference
            for _ in range(4):
                move += .29 * (mean_neighbors(move, links) - move)
            p = cap_rest(reference + move, reference, rest)
            p = prevent_flips(reference, p, faces)
            p = retain_clear_rest(reference, p, faces, samples[0])
        d, o, _ = scan(p, w, faces, samples, transforms, rows)
        value = score(d, o)
        print("SEED", label, round(value), int(o[0]), int(o.sum()), round(d.min() * 1000, 2), flush=True)
        candidates.append((value, label, p, w))
    if "--baseline" in sys.argv:
        return candidates[0][2:]
    return min(candidates, key=lambda c: c[0])[2:]


def split_loft(garment, points, weights, reference, faces, hits, long_hits, add_loft):
    """Insert shared edge midpoints with per-face UVs at colliding spans."""
    mesh = garment.data
    attached = {}
    priorities = {}
    for i, face in enumerate(faces):
        for j, (a, b) in enumerate(zip(face, np.roll(face, -1))):
            edge = tuple(sorted((a, b)))
            attached.setdefault(edge, []).append(i)
            if not hits[i]:
                continue
            length = np.linalg.norm(points[a] - points[b])
            armpit = .062 < abs(float(reference[[a, b], 0].mean())) < .115
            armpit &= .490 < float(reference[[a, b], 2].mean()) < .555
            if long_hits[i, j] or (add_loft and armpit and hits[i] > 6 and length > .005):
                rank = (1 + math.log1p(hits[i])) * (length + .001 * math.log1p(long_hits[i, j]))
                priorities[edge] = max(priorities.get(edge, 0), rank)

    budget = min(880, 8000 - len(faces))
    split, taken = {}, {}
    for edge in sorted(priorities, key=lambda e: (-priorities[e], e)):
        if len(attached[edge]) > budget or any(i in taken for i in attached[edge]):
            continue
        split[edge] = len(points) + len(split)
        budget -= len(attached[edge])
        taken.update((i, edge) for i in attached[edge])
    if not split:
        return points, weights, reference, 0

    new_faces, uv_data = [], []
    layer = mesh.uv_layers.active
    for i, face in enumerate(faces):
        uv = [np.array(layer.uv[j].vector) for j in mesh.polygons[i].loop_indices]
        if i not in taken:
            new_faces.append(face.tolist())
            uv_data.append(uv)
            continue
        edge = taken[i]
        a = next(j for j in range(3) if tuple(sorted((face[j], face[(j + 1) % 3]))) == edge)
        b, c = (a + 1) % 3, (a + 2) % 3
        mid = split[edge]
        midpoint_uv = (uv[a] + uv[b]) * .5
        new_faces.extend(([face[a], mid, face[c]], [mid, face[b], face[c]]))
        uv_data.extend(([uv[a], midpoint_uv, uv[c]], [midpoint_uv, uv[b], uv[c]]))

    edges = np.array(list(split))
    points = np.r_[points, points[edges].mean(axis=1)]
    reference = np.r_[reference, reference[edges].mean(axis=1)]
    weights = limit_weights(np.r_[weights, weights[edges].mean(axis=1)])
    target = bpy.data.meshes.new("T-shirt local loft")
    target.from_pydata(points.tolist(), [], new_faces)
    for material in mesh.materials:
        target.materials.append(material)
    uv = target.uv_layers.new(name=layer.name)
    for face, values in zip(target.polygons, uv_data):
        for loop, value in zip(face.loop_indices, values):
            uv.uv[loop].vector = value
    garment.data = target
    target.update()
    return points, weights, reference, len(split)


def laplacian_floor(delta, links):
    length = np.linalg.norm(delta, axis=1)
    direction = delta / length.clip(1e-8)[:, None]
    smooth = delta.copy()
    for _ in range(3):
        average = .72 * smooth + .28 * mean_neighbors(smooth, links)
        needed = np.maximum(length - (average * direction).sum(axis=1), 0)
        smooth = average + needed[:, None] * direction
    return smooth


def contact_step(points, weights, support, reference, links, matrices, transforms, constraints,
                 weight_scale, max_move):
    count = len(points)
    rows = np.concatenate([np.full(len(c[1]), c[0], np.int32) for c in constraints])
    ids, bary, normals, distance = (np.concatenate(part) for part in zip(
        *(c[1:] for c in constraints)
    ))
    columns = np.argsort(-(.60 * weights + .40 * support), axis=1, kind="stable")[:, :4]
    current = np.take_along_axis(weights, columns, axis=1)
    current /= current.sum(axis=1, keepdims=True).clip(1e-9)
    cuff = (abs(reference[:, 0]) > .108) & (reference[:, 2] > .51)
    axis_scale = np.ones_like(points)
    axis_scale[cuff, 0] = .27
    axis_scale[reference[:, 2] < .406, 2] = .42
    required = np.maximum(MARGIN - distance, 0)
    direction = np.einsum("ni,nkij->nkj", normals, matrices[rows[:, None], ids, :, :3])

    # Bake the largest measured deficit at each vertex in its contact
    # direction, expressed in unposed coordinates. Triangle constraints
    # distribute their proposed offset across the three corners.
    raw = direction * bary[..., None]
    unit = raw / np.square(raw).sum(axis=(1, 2)).clip(.18)[:, None, None]
    displacement = required[:, None, None] * unit
    influence = np.linalg.norm(displacement, axis=2)
    peak = np.zeros(count, dtype=np.float32)
    np.maximum.at(peak, ids.ravel(), influence.ravel())
    chosen = np.full(count, -1, dtype=np.int32)
    flat = ids.ravel()
    winners = np.flatnonzero((influence.ravel() >= peak[flat]) & (influence.ravel() > 0))
    np.maximum.at(chosen, flat[winners], winners)
    move = np.zeros_like(points)
    selected = chosen >= 0
    move[selected] = displacement.reshape(-1, 3)[chosen[selected]]
    move = laplacian_floor(move, links)

    # Alternate directional planes and weight updates. Scaling coefficients
    # to metre-sized motion makes a shoulder/hip weight change comparable
    # to a direct geometry change under large pose transforms.
    joint = transforms[rows[:, None, None], columns[ids]]
    posed = np.einsum("nkjlm,nkm->nkjl", joint[..., :3], points[ids]) + joint[..., 3]
    influence = np.einsum("nl,nkjl->nkj", normals, posed)
    influence -= influence.mean(axis=2, keepdims=True)
    gradient = np.concatenate((direction * axis_scale[ids], influence * weight_scale), axis=2)
    gradient *= bary[..., None]
    gram = np.square(gradient).sum(axis=(1, 2)).clip(.12)
    delta = np.zeros((count, 7), dtype=np.float32)
    delta[:, :3] = .48 * move
    rest = rows == 0
    for _ in range(14):
        residual = np.maximum(MARGIN - distance - np.einsum("nkj,nkj->n", gradient, delta[ids]), 0)
        importance = np.maximum(residual, .00003) ** 1.5
        importance[rest] *= 4
        amount = importance * residual / gram
        norm = np.bincount(flat, weights=(importance[:, None] * abs(bary)).ravel(),
                           minlength=count).clip(1e-12)
        force = gradient * amount[:, None, None]
        update = np.column_stack([np.bincount(flat, weights=f.ravel(), minlength=count)
                                  for f in force.transpose(2, 0, 1)]) / norm[:, None]
        delta += (.95 * update).astype(np.float32)
        delta += .08 * (mean_neighbors(delta, links) - delta)
        # Maintain a dependence on the worst measured requirement while
        # allowing incompatible directions to share the local displacement.
        delta[:, :3] += .035 * (.48 * move - delta[:, :3])
        length = np.linalg.norm(delta[:, :3], axis=1).clip(1e-9)
        delta[:, :3] *= np.minimum(1, max_move / length)[:, None]
        adjusted = project_simplex(current + delta[:, 3:] * weight_scale)
        delta[:, 3:] = (adjusted - current) / weight_scale
    limited = np.zeros_like(weights)
    np.put_along_axis(limited, columns, adjusted, axis=1)
    return delta[:, :3] * axis_scale, limited


def choose_rows(samples, d, o):
    choose = {0, *range(1, len(samples), 12)}
    for clip in CLIPS:
        group = np.array([i for i, s in enumerate(samples) if s[0] == clip])
        choose.update(group[np.argsort(o[group], kind="stable")[-3:]])
        choose.update(group[np.argsort(d[group].min(axis=1), kind="stable")[:3]])
    return np.array(sorted(choose))


def prevent_flips(points, candidate, faces):
    tri = points[faces]
    original = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    for _ in range(3):
        test = candidate[faces]
        normal = np.cross(test[:, 1] - test[:, 0], test[:, 2] - test[:, 0])
        bad = np.unique(faces[(normal * original).sum(axis=1) < 0])
        candidate[bad] = .55 * candidate[bad] + .45 * points[bad]
    return candidate


def retain_clear_rest(before, candidate, faces, sample):
    """Backtrack the vertices of any new rest intersection or cap violation."""
    for attempt in range(9):
        d, _, _, pairs, _ = PRIOR["scan_frame"](candidate, faces, sample)
        invalid = np.flatnonzero((d < .00062) | (d > REST_CAP))
        if not len(pairs) and not len(invalid):
            return candidate
        invalid = np.unique(np.r_[invalid, faces[pairs[:, 0]].ravel()])
        if attempt < 4:
            candidate[invalid] = .55 * before[invalid] + .45 * candidate[invalid]
        else:
            candidate[invalid] = before[invalid]
    d, _, _, pairs, _ = PRIOR["scan_frame"](candidate, faces, sample)
    if not len(pairs) and (d >= .00062).all() and (d <= REST_CAP).all():
        return candidate
    return before.copy()


def contact_trial(points, weights, reference, displacement, adjusted, gain, faces, links,
                  rest_sample, blend):
    p = cap_rest(points + gain * displacement, reference, rest_sample[2])
    p = prevent_flips(points, p, faces)
    p = retain_clear_rest(points, p, faces, rest_sample)
    w = (1 - gain) * weights + gain * adjusted
    w = limit_weights(w + blend[:, None] * (mean_neighbors(w, links) - w))
    return p, w


def vertex_objective(dist):
    deficit = np.maximum(MARGIN - dist, 0) * 1000
    return .45 * np.square(deficit.max(axis=0)) + 1.6 * np.square(deficit).mean(axis=0) + (
        3 * (dist < 0).mean(axis=0)
    )


def search_contact_sides(points, weights, reference, support, displacement, adjusted, samples,
                         transforms, d, o, links, iteration):
    """Test changes through the nonlinear nearest-surface query.

    Opposing arm and torso contacts can make a single linearized direction
    inaccurate. Keep a move only when the sampled vertex trajectory improves.
    """
    rest = samples[0][2]
    importance = vertex_objective(d)
    vertices = np.argsort(-importance, kind="stable")[:640]
    vertices = vertices[d[:, vertices].min(axis=0) < MARGIN]
    if not len(vertices):
        return points, weights
    rows = choose_rows(samples, d, o)
    # Add the actual worst pose of each selected vertex, regardless of the
    # line search cadence. Every committed patch is rescanned at half frames.
    rows = np.unique(np.r_[rows, d[:, vertices].argmin(axis=0)])
    ts = transforms[rows]
    p0, w0 = points[vertices], weights[vertices]
    ref = reference[vertices]
    result_p, result_w = p0.copy(), w0.copy()
    best = vertex_objective(d[rows][:, vertices])
    _, radial = signed(rest, p0)
    near = mean_neighbors(points, links)[vertices] - p0
    nw = mean_neighbors(weights, links)[vertices]
    impulse = displacement[vertices]
    dominant = np.zeros_like(w0)
    dominant[np.arange(len(vertices)), w0.argmax(axis=1)] = 1
    mm = .004 if iteration < 6 else .0024
    offsets = [impulse * factor for factor in (.34, .70)]
    offsets += [radial * factor * mm for factor in (-1.9, -1., 1., 2.)]
    offsets += [np.broadcast_to(mm * axis, p0.shape)
                for axis in np.r_[np.eye(3), -np.eye(3)]]
    offsets += [.68 * near]
    candidates = [(p0 + off, w0) for off in offsets]
    candidates += [
        (p0, limit_weights(.62 * w0 + .38 * adjusted[vertices])),
        (p0, limit_weights(.55 * w0 + .45 * support[vertices])),
        (p0, limit_weights(.56 * w0 + .44 * nw)),
        (p0, limit_weights(.71 * w0 + .29 * dominant)),
        (p0 + .42 * impulse, limit_weights(.72 * w0 + .28 * adjusted[vertices])),
    ]
    for p, w in candidates:
        p = cap_rest(p, ref, rest)
        posed, _ = skin(p, w, ts)
        values = np.array([signed(samples[row][2], posed[i])[0] for i, row in enumerate(rows)])
        criterion = vertex_objective(values)
        criterion += .030 * np.square(np.linalg.norm(p - p0, axis=1) * 1000)
        criterion += .30 * np.square(w - w0).sum(axis=1)
        improve = criterion < best - .025
        best[improve] = criterion[improve]
        result_p[improve] = p[improve]
        result_w[improve] = w[improve]
    move = np.zeros_like(points)
    move[vertices] = result_p - p0
    weight_move = np.zeros_like(weights)
    weight_move[vertices] = result_w - w0
    move += .34 * (mean_neighbors(move, links) - move)
    weight_move += .26 * (mean_neighbors(weight_move, links) - weight_move)
    return points + move, limit_weights(np.maximum(weights + weight_move, 0))


def restore_split_clearance(points, reference, garment, sample):
    faces = triangles(garment.data)
    links = adjacency(garment.data)
    p = PRIOR["guard_rest"](points, faces, sample, reference, links)
    p = cap_rest(p, reference, sample[2])
    d, _, _, pairs, _ = PRIOR["scan_frame"](p, faces, sample)
    if len(pairs) or d.min() < TARGET or d.max() > REST_CAP:
        return None
    return p


def bake(garment, body, names, reference, points, weights, samples, transforms):
    history, best = [], None
    rest = samples[0][2]
    support = weight_support(points, body, names, rest, samples[0][4],
                             adjacency(garment.data), weights)
    stop = int(sys.argv[sys.argv.index("--passes") + 1]) if "--passes" in sys.argv else MAX_PASSES
    assert 0 <= stop <= MAX_PASSES
    for iteration in range(stop + 1):
        faces = triangles(garment.data)
        links = adjacency(garment.data)
        d, o, (hits, long_hits, constraints, matrices) = scan(
            points, weights, faces, samples, transforms, collect=True
        )
        report = summarize_run(iteration, samples, d, o)
        value = score(d, o)
        # Topology splits raise the raw count for the same crossing patch.
        value *= (3903 / len(faces)) ** .65
        history.append({"pass": iteration, "score": value, "triangles": len(faces), "clips": report})
        if best is None or value < best[0]:
            best = value, iteration, garment.data, points.copy(), weights.copy()
        if iteration == stop or (not o.any() and d.min() >= TARGET and d[0].max() <= REST_CAP):
            break
        if iteration in (2, 6, 10):
            previous_mesh = garment.data
            p, w, r, inserted = split_loft(garment, points, weights, reference, faces, hits,
                                           long_hits, add_loft=iteration > 2)
            if inserted:
                cleared = restore_split_clearance(p, r, garment, samples[0])
                if cleared is not None:
                    points, weights, reference = cleared, w, r
                    support = weight_support(points, body, names, rest, samples[0][4],
                                             adjacency(garment.data), weights)
                    print("LOFT", inserted, "edges", flush=True)
                    continue
                print("LOFT REJECTED", inserted, "edges", flush=True)
                rejected_mesh = garment.data
                garment.data = previous_mesh
                bpy.data.meshes.remove(rejected_mesh)
        rows = choose_rows(samples, d, o)
        trial = score(d[rows], o[rows]), points, weights
        zone = PRIOR["region_faces"](reference)
        blend = np.where(np.isin(zone, ("hem", "shoulder / armpit", "sleeve / cuff")), .07, .03)
        scale = 7.5 if iteration < 7 else 4.5
        displacement, adjusted = contact_step(
            points, weights, support, reference, links, matrices, transforms, constraints,
            weight_scale=scale, max_move=.014 if iteration < 7 else .009,
        )
        searched, searched_weights = search_contact_sides(
            points, weights, reference, support, displacement, adjusted, samples, transforms,
            d, o, links, iteration,
        )
        for move, revised in ((searched - points, searched_weights), (displacement, adjusted)):
            for gain in (.92, .52, .24):
                p, w = contact_trial(points, weights, reference, move, revised, gain,
                                     faces, links, samples[0], blend)
                dd, oo, _ = scan(p, w, faces, samples, transforms, rows)
                candidate = score(dd, oo)
                if candidate < trial[0]:
                    trial = candidate, p, w
        print("TRIAL", round(score(d[rows], o[rows])), "->", round(trial[0]), flush=True)
        points, weights = trial[1:]
        if iteration >= 10 and trial[0] >= score(d[rows], o[rows]) and iteration != 10:
            break
    _, chosen, mesh, points, weights = best
    garment.data = mesh
    write_json("fit_history.json", {"selected_pass": chosen, "margin_m": MARGIN, "passes": history})
    print("SELECTED", chosen, len(triangles(mesh)), flush=True)
    return points, weights

def build():
    # reimport() gets the input path through the round 1 module's globals.
    SHARED["GLB"] = HERE.parent / "tshirt_v1.glb"
    scene, arm, body, garment, names = start()
    SHARED["GLB"] = GLB
    reference = coordinates(garment.data)
    weights = read_weights(garment, names)
    print("INPUT", len(reference), len(triangles(garment.data)), flush=True)
    samples, transforms = PRIOR["cache_motion"](scene, arm, body, names)
    print("CACHED", len(samples), flush=True)
    points, weights = initial_search(garment, body, names, samples, transforms, reference, weights)
    if "--baseline" in sys.argv:
        d, o, _ = scan(points, weights, triangles(garment.data), samples, transforms)
        summarize_run(0, samples, d, o)
        return
    points, weights = bake(garment, body, names, reference, points, weights, samples, transforms)
    PRIOR["export"](garment, arm, body, points, names, weights)


def check_body_contacts():
    """Count distal arm / trunk intersections at the measured failure poses."""
    path = OUT / "dense_check.json"
    report = json.loads(path.read_text())
    scene, arm, body = PRIOR["open_master"]()
    PRIOR["load_motion"]()
    names = tuple(b.name for b in arm.data.bones)
    rest_faces = triangles(body.data)
    scores = read_weights(body, names)[rest_faces].sum(axis=1)
    dominant = np.array(names)[scores.argmax(axis=1)]
    distal = {side: np.array([f"mixamorig:{side}ForeArm" == n or
                              n.startswith(f"mixamorig:{side}Hand") for n in dominant])
              for side in ("Left", "Right")}
    trunk = np.array([any(text in name for text in ("Spine", "Hips", "UpLeg")) for name in dominant])
    check = {}
    for clip in CLIPS:
        data = report["clips"][clip]
        if not data["max_triangle_pairs"] and data["min_signed_dist"] >= TARGET:
            continue
        poses = {data["minimum_vertex_frame"], data["max_pair_frame"]}
        for frame in sorted(poses):
            PRIOR["set_pose"](scene, arm, clip, frame)
            positions, faces = geometry(body, bpy.context.evaluated_depsgraph_get())
            assert np.array_equal(rest_faces, faces)
            world = positions.tolist()
            trunk_tree = BVHTree.FromPolygons(world, faces[trunk].tolist(), all_triangles=True)
            pairs = {}
            for side, mask in distal.items():
                arm_tree = BVHTree.FromPolygons(world, faces[mask].tolist(), all_triangles=True)
                pairs[side] = len(trunk_tree.overlap(arm_tree))
            check.setdefault(clip, []).append({"frame": frame, "body_triangle_pairs": pairs})
    report["body_distal_arm_vs_trunk_at_failure_poses"] = check
    path.write_text(json.dumps(report, indent=2) + "\n")


def supplied_checker(stem):
    """Run the supplied measurement code with unique output and no renders."""
    path = HERE / f"{stem}.py"
    source = path.read_text().replace("bpy.ops.render.render(write_still=True)", "None")
    source = source.replace("{out}/motion_check.json", "{out}/" + stem + ".json")
    output = io.StringIO()
    saved = sys.argv
    try:
        sys.argv = [str(path), "--", str(SHARED["MASTER"].resolve()),
                    str(SHARED["MOTION"].resolve()), str(GLB), str(OUT)]
        with redirect_stdout(output):
            exec(compile(source, str(path), "exec"), {})
    finally:
        sys.argv = saved
    lines = [line for line in output.getvalue().splitlines() if line.startswith("RESULT ")]
    assert len(lines) == 8
    result = "\n".join(lines) + "\n"
    (OUT / (stem + ".txt")).write_text(result)
    print(result, end="", flush=True)


def render_evidence():
    scene, arm, body, garment = PRIOR["reimport"]()
    PRIOR["configure_render"](scene)
    camera = bpy.data.objects.new("Fit QA", bpy.data.cameras.new("Fit QA"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"

    def shot(path, focus, direction, scale):
        focus = Vector(focus)
        camera.location = focus + 3 * Vector(direction)
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    set_pose = PRIOR["set_pose"]
    set_pose(scene, arm, "rest", 1)
    scene.render.resolution_x, scene.render.resolution_y = 520, 430
    w, h = scene.render.resolution_x, scene.render.resolution_y
    gutter = 6
    sheet_w, sheet_h = 3 * w + 4 * gutter, 2 * h + 3 * gutter
    pixels = np.ones((sheet_h, sheet_w, 4), dtype=np.float32)
    pixels[..., :3] = .13
    views = [
        ("front", (0, -1, 0)), ("front three-quarter", (.65, -1, .19)), ("right", (1, 0, 0)),
        ("back", (0, 1, 0)), ("back three-quarter", (-.65, 1, .19)), ("left", (-1, 0, 0)),
    ]
    temp = OUT / ".rest_tile.png"
    for i, (_, direction) in enumerate(views):
        shot(temp, (0, -.015, .500), direction, .56)
        tile = bpy.data.images.load(str(temp), check_existing=False)
        buf = np.empty(w * h * 4, dtype=np.float32)
        tile.pixels.foreach_get(buf)
        tile.colorspace_settings.name = "sRGB"
        row, col = divmod(i, 3)
        x, y = gutter + col * (w + gutter), gutter + (1 - row) * (h + gutter)
        pixels[y:y + h, x:x + w] = buf.reshape(h, w, 4)
        bpy.data.images.remove(tile)
    temp.unlink()
    sheet = bpy.data.images.new("Six T-pose views", width=sheet_w, height=sheet_h, alpha=False)
    sheet.colorspace_settings.name = "sRGB"
    sheet.pixels.foreach_set(pixels.ravel())
    sheet.filepath_raw = str(OUT / "six_views.png")
    sheet.file_format = "PNG"
    sheet.save()

    report_path = OUT / "dense_check.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    dense = report.get("clips", {})
    scene.render.resolution_x = scene.render.resolution_y = 750
    motion_frames = {}
    for clip in SHARED["RENDER_CLIPS"]:
        first, last = bpy.data.actions[clip].frame_range
        rows = dense.get(clip, {})
        frame = rows.get("max_pair_frame") if rows.get("max_triangle_pairs", 0) else None
        if frame is None:
            frame = int(first + .4 * (last - first))
        set_pose(scene, arm, clip, frame)
        posed, _ = geometry(body, bpy.context.evaluated_depsgraph_get())
        lo, hi = posed.min(axis=0), posed.max(axis=0)
        motion_frames[clip] = frame
        shot(OUT / f"{clip}.png", (lo + hi) * .5, (.24, -1, .11),
             1.14 * max(float((hi - lo).max()), .96))
    write_json("render_info.json", {
        "engine": "Cycles CPU",
        "glb_sha256": hashlib.sha256(GLB.read_bytes()).hexdigest(),
        "six_view_order": [name for name, _ in views],
        "motion_frames": motion_frames,
        "png_sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                       for name in ["six_views.png", *(f"{c}.png" for c in motion_frames)]},
    })


if __name__ == "__main__":
    if "--verify" in sys.argv:
        PRIOR["verify"]()
        check_body_contacts()
    elif "--checkers" in sys.argv:
        supplied_checker("motion_check")
        supplied_checker("motion_check_tri")
    elif "--renders" in sys.argv:
        render_evidence()
    else:
        build()
