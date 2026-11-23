"""Fit the round-two waistband to the female body in bind space."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import fit_module as fit
from refit import read_pose_bank, scan_in_batches, smoothstep
from common import arguments

SOURCE = ROOT.parent / "round2/female-jeans-v2.glb"
OUTPUT = ROOT / "female-jeans-v3.glb"
CENTER = np.array([0, -.018, 0], dtype=np.float32)


def upper_profile(angle, heights):
    """Follow the rise of the opening around the waist, including the back rise."""
    samples = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    separation = np.abs(np.angle(np.exp(1j * (samples[:, None] - angle))))
    envelope = np.where(separation < .19, heights, 0).max(axis=1)
    for _ in range(5):
        envelope = .5 * envelope + .25 * (np.roll(envelope, 1) + np.roll(envelope, -1))
    return np.interp(angle, samples, envelope, period=2 * np.pi)


def radial_fit(tree, points, ray, clearance):
    """Preserve the horizontal angle and height while changing surface clearance."""
    origins = points.copy()
    origins[:, :2] = CENTER[:2]
    hits = [tree.ray_cast(o + .25 * v, -v, .24) for o, v in zip(origins, ray, strict=True)]
    assert all(hit[0] is not None for hit in hits)
    surface = np.array([hit[0][:] for hit in hits], dtype=np.float32)
    low = np.zeros(len(points), dtype=np.float32)
    high = np.full(len(points), .016, dtype=np.float32)
    for _ in range(15):
        middle = (low + high) * .5
        candidate = surface + ray * middle[:, None]
        distance = np.array([tree.find_nearest(pos)[3] for pos in candidate])
        outside = distance >= clearance
        high = np.where(outside, middle, high)
        low = np.where(outside, low, middle)
    candidate = surface + ray * high[:, None]
    # At a facet crease the closest-point vector can differ from the face normal.
    # Resolve those cases along the face normal without perturbing the other rays.
    for _ in range(10):
        signed, _, normal, _ = fit.nearest(tree, candidate)
        error = clearance - signed
        active = np.abs(error) > .00012
        if not active.any():
            break
        candidate[active] += .65 * error[active, None] * normal[active]
    return candidate


def correct_motion(module, rows, matrices, points, weights, blend, core, refinement=False):
    """Resolve contact witnesses without letting the rest waistband flare."""
    edited = blend > 0
    changed_faces = edited[module.unweld[module.source_faces]].any(axis=1)
    ids, indices = np.unique(module.source_faces[changed_faces], return_inverse=True)
    welded = module.unweld[ids]
    patch = SimpleNamespace(points=points, graph=module.graph, unweld=welded,
                            source_faces=indices.reshape(-1, 3))
    original = points.copy()
    rest = rows[0][2]
    core_ids = np.flatnonzero(core)
    scale = .020
    anatomy = [module.names.index("mixamorig:" + name)
               for name in ("Hips", "Spine", "LeftUpLeg", "RightUpLeg")]
    preference = weights[ids].copy()
    preference[:, anatomy] += .00001
    columns = np.argsort(-preference, axis=1, kind="stable")[:, :4]
    source_mask = edited[module.unweld]
    scan_indices = np.arange(len(rows))
    if refinement:
        scan_indices = np.asarray([i for i, row in enumerate(rows)
                                   if row[0] in ("rest", "walk", "run", "sit_down", "sit_idle", "stand_up")])
    full_clear = False
    for iteration in range(16 if refinement else 11):
        selected = [rows[i] for i in scan_indices]
        transforms = matrices[scan_indices]
        result = scan_in_batches(patch, points, weights[ids], selected, transforms)
        distances, pairs, _, constraints, skin, _ = result
        row, col = np.unravel_index(distances.argmin(), distances.shape)
        worst = dict(clip=selected[row][0], frame=selected[row][1],
                     signed_mm=float(distances[row, col] * 1000), weld=int(welded[col]),
                     position_m=points[welded[col]].tolist())
        peak = int(pairs.argmax())
        witness = dict(clip=selected[peak][0], frame=selected[peak][1], pairs=int(pairs[peak]))
        print("WAIST SWEEP", iteration, len(selected), worst, witness, flush=True)
        failing_frames = (distances.min(axis=1) < .00062) | (pairs > 0)
        if not failing_frames.any():
            if len(selected) == len(rows):
                full_clear = True
                break
            scan_indices = np.arange(len(rows))
            continue

        constraints = [(i, vertices[active], directions[active], signed[active], factors[active])
                       for i, vertices, directions, signed, factors in constraints
                       if (active := ((signed < .00076) | ((pairs[i] > 0) & (factors < .9999)))).any()]
        planes, importance = fit.SOURCE["gather_planes"](
            constraints, points[welded], columns, skin, transforms, .00090, scale)
        directions, targets = planes[..., :-1], planes[..., -1]
        active = (importance > 0) & edited[welded, None]
        source = np.take_along_axis(weights[ids], columns, axis=1)
        correction = np.zeros((len(ids), 7), dtype=np.float32)
        slot = np.arange(len(ids))
        signed, _, normals, _ = fit.nearest(rest, points[welded])
        for _ in range(32):
            missing = np.where(active, targets - np.einsum("vsi,vi->vs", directions, correction), 0)
            pick = missing.argmax(axis=1)
            correction += .75 * np.maximum(0, missing[slot, pick, None]) * directions[slot, pick]
            correction[:, :3] = fit.SOURCE["limit_delta"](correction[:, :3], .003)
            outward = (correction[:, :3] * normals).sum(axis=1)
            clamped = np.clip(outward, .0019 - signed, .00295 - signed)
            correction[core[welded], :3] += ((clamped - outward)[:, None] * normals)[core[welded]]
            next_weights = fit.SOURCE["simplex"](source + (correction[:, 3:] / scale).clip(-.26, .26))
            correction[:, 3:] = (next_weights - source) * scale

        full = np.zeros((len(module.source_points), 3), dtype=np.float32)
        full[ids] = correction[:, :3]
        movement = module.welded(full)
        delta = np.zeros_like(weights)
        local = np.zeros_like(weights[ids])
        np.put_along_axis(local, columns, correction[:, 3:] / scale, axis=1)
        delta[ids] = local
        weight_movement = module.welded(delta)
        for _ in range(2):
            movement += .20 * (fit.average(movement, module.graph) - movement)
            weight_movement += .22 * (fit.average(weight_movement, module.graph) - weight_movement)
        movement[~edited] = 0
        weight_movement[~edited] = 0
        points = original + fit.SOURCE["limit_delta"](points + movement - original, .007)
        for _ in range(5):
            distance, _, normal, _ = fit.nearest(rest, points[core_ids])
            points[core_ids] += (np.clip(distance, .00185, .00296) - distance)[:, None] * normal
        updated = weights + weight_movement[module.unweld]
        # Keep the four-column joint basis stable through all solver iterations.
        retained = np.take_along_axis(updated[ids], columns, axis=1)
        retained = fit.SOURCE["simplex"](retained)
        staged = weights[ids].copy()
        staged[edited[welded]] = 0
        np.put_along_axis(staged, columns, retained, axis=1)
        weights[ids[edited[welded]]] = staged[edited[welded]]
        weights[~source_mask] = module.weights[~source_mask]

        # Recheck every affected neighborhood, then sweep all clips before export.
        bad = scan_indices[failing_frames]
        fringe = np.asarray([j for i in bad for j in range(max(0, i - 4), min(len(rows), i + 5))])
        scan_indices = np.unique(np.r_[fringe, 0])
    return points, weights, worst, witness, full_clear


def main():
    names, _, female, rows, matrices = read_pose_bank()
    module = fit.Module(SOURCE, names)
    vertices, faces, weights_body, *_ = female
    p = module.points
    rest = rows[0][2]
    radial = p - CENTER
    radial[:, 2] = 0
    ray = fit.normalized(radial)
    angle = np.arctan2(ray[:, 1], ray[:, 0])
    rim = upper_profile(angle, p[:, 2])
    depth = rim - p[:, 2]
    blend = 1 - smoothstep(.025, .038, depth)
    ids = np.flatnonzero(blend > 0)
    core = depth <= .025
    points = p.copy()
    # Remove small scallops at the opening while retaining its larger rise.
    points[ids, 2] += ((rim[ids] - p[ids, 2]).clip(-.004, .004)
                       * (1 - smoothstep(.001, .009, np.abs(depth[ids]))) * .55)
    before, *_ = fit.nearest(rest, p[ids])
    # A little radial relief separates the existing topstitch and panel layers.
    clearance = np.interp(before, [.002, .022], [.00250, .00287]).astype(np.float32)
    fitted = radial_fit(rest, points[ids], ray[ids], clearance)
    points[ids] = p[ids] + blend[ids, None] * (fitted - p[ids])
    after, surface, _, face = fit.nearest(rest, points[ids])
    corners = faces[face]
    bary = fit.barycentric(vertices[corners], surface)
    target = module.welded(module.weights)
    target[ids] = np.einsum("vi,vij->vj", bary, weights_body[corners])
    mask = blend[module.unweld, None]
    weights = module.weights.copy()
    edited = mask[:, 0] > 0
    weights[edited] = fit.limit_weights((weights * (1 - mask) + target[module.unweld] * mask)[edited])

    print("REST SEED", after[core[ids]].min(), after[core[ids]].max(), flush=True)
    if "--resume" in arguments():
        with np.load(ROOT / ".runtime/fit-diagnostic.npz") as checkpoint:
            points, weights = checkpoint["points"], checkpoint["weights"]
        clear = False
    else:
        points, weights, worst, witness, clear = correct_motion(module, rows, matrices, points, weights, blend, core)
    if not clear:
        points, weights, worst, witness, clear = correct_motion(module, rows, matrices, points, weights,
                                                               blend, core, refinement=True)
    after, *_ = fit.nearest(rest, points[ids])
    asset = module.glb
    # Reuse the existing normal/tangent rotation and exact texture payload.
    module.texture_cache[1024] = ([], [(im["mimeType"], asset.payload(im["bufferView"]))
                                      for im in asset.doc["images"]])
    module.write(OUTPUT, points, weights)
    # Keep the original position and joint bytes outside the edited band.
    output = fit.Glb(OUTPUT)
    for attrs, sl in module.parts:
        fixed = ~edited[sl]
        for label in ("POSITION", "JOINTS_0", "WEIGHTS_0"):
            idx = attrs[label]
            output.accessor(idx)[fixed] = asset.accessor(idx)[fixed]
        idx = attrs["POSITION"]
        data = output.accessor(idx)
        output.doc["accessors"][idx].update(min=data.min(axis=0).tolist(), max=data.max(axis=0).tolist())
    output.write(OUTPUT)

    np.savez(ROOT / ".runtime/fit-diagnostic.npz", points=points, depth=depth, blend=blend, weights=weights)
    report = dict(source_sha256=fit.sha(SOURCE), output_sha256=fit.sha(OUTPUT),
                  core_depth_mm=25, transition_end_mm=38, core_vertices=int(core.sum()),
                  edited_vertices=len(ids), rest_clearance_before_mm=(1000 * np.array(
                      [before[core[ids]].min(), before[core[ids]].max()])).tolist(),
                  rest_clearance_mm=(1000 * np.array(
                      [after[core[ids]].min(), after[core[ids]].max()])).tolist(),
                  modified_vertex_motion_worst=worst, modified_face_overlap_worst=witness, motion_probe_clear=clear)
    (ROOT / "waistband.json").write_text(json.dumps(report, indent=2) + "\n")
    print("WAIST FIT", report, flush=True)


if __name__ == "__main__":
    main()
