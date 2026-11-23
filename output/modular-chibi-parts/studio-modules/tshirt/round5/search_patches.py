"""Try coherent offsets and alternate arm/torso weights at persistent contacts."""
import numpy as np
from mathutils.bvhtree import BVHTree


def patch_step(fit, points, weights, reference, names, support, links, faces, samples,
               transforms, d, pairs, hits, margin=.0011):
    skin, signed, mean = (fit[key] for key in ("skin", "signed", "mean"))
    limit = fit["limit_weights"]
    directions = np.array([(a,b,c) for a in (-1,0,1) for b in (-1,0,1)
                           for c in (-1,0,1) if 0 < abs(a)+abs(b)+abs(c) <= 2], dtype=np.float32)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    seeds = np.maximum(0, margin - d.min(axis=0)) * 1000
    np.maximum.at(seeds, faces[hits > 0].ravel(), 1.65)
    occ = np.minimum(1, seeds / 2.5)
    rows = {0}
    for clip in fit["CLIPS"]:
        ix = np.array([i for i, sample in enumerate(samples) if sample[0] == clip])
        rows.update(ix[np.argsort(pairs[ix], kind="stable")[-2:]])
        rows.update(ix[np.argsort(d[ix].min(axis=1), kind="stable")[:2]])
        rows.update(ix[::64])
    rows = np.array(sorted(rows))
    trees = [samples[row][2] for row in rows]
    all_transforms = transforms[rows]
    start_points = points.copy()
    start_weights = weights.copy()
    x, _, z = reference.T
    zones = ((z >= .458) & (x > .042), (z >= .458) & (x < -.042), z < .458)
    for zone, side in zip(zones, ("Left", "Right", "hem")):
        patch = (occ * zone).copy()
        if not patch.any():
            continue
        for _ in range(5):
            patch = np.maximum(patch, .85 * mean(patch, links))
        patch[patch < .035] = 0
        # A few neighboring triangles span the edge of the edit.
        touching = faces[(patch[faces] > 0).any(axis=1)]
        inds = np.unique(touching)
        face_list = np.searchsorted(inds, touching).tolist()
        p0, w0, amount = points[inds].copy(), weights[inds].copy(), patch[inds, None]
        cap = reference[inds]
        _, radial = signed(trees[0], p0)
        skin_array = all_transforms

        def evaluate(p, w):
            disp = np.linalg.norm(p - cap, axis=1)
            if disp.max() > .0298:
                return float("inf")
            pos, _ = skin(p.astype(np.float32), w.astype(np.float32), skin_array)
            count, error, maximum, inside = 0, 0., 0., 0
            for j, pts in enumerate(pos):
                close = signed(trees[j], pts)[0]
                overlap = len(trees[j].overlap(
                    BVHTree.FromPolygons(pts.tolist(), face_list, all_triangles=True)))
                if j == 0 and (overlap or close.min() < .00063 or close.max() > .02995):
                    return float("inf")
                deficit = 1000 * np.maximum(.00078 - close, 0)
                count += overlap
                inside += int((close < 0).sum())
                error += float(np.square(deficit).sum())
                maximum = max(maximum, float(deficit.max()))
            return 3 * count + 3 * inside + 1.5 * error + 150 * maximum**2

        best = (evaluate(p0, w0), p0, w0, "unchanged")
        baseline = best[0]

        def consider(p, w, label):
            nonlocal best
            score = evaluate(p, w)
            if score < best[0]:
                best = (score, p, w, label)

        if side == "hem":
            joint_candidates = ("Hips", "Spine", "LeftUpLeg", "RightUpLeg")
        else:
            joint_candidates = (side+"Arm", side+"Shoulder", "Spine2", "Spine1")
        pos, reconstructed = p0.copy(), w0.copy()
        for w in (support[inds], mean(weights, links)[inds]):
            for influence in (.35, .72):
                consider(pos, limit(w0 + influence * amount * (w-w0)), "interpolated skin")
        for name in joint_candidates:
            index = names.index("mixamorig:"+name)
            for strength in (.30, .65, .95):
                coeff = strength * amount
                w = reconstructed * (1-coeff)
                w[:, index] += coeff[:,0]
                consider(pos, limit(w), name)
        _, start, binding, _ = best
        circumferential = np.zeros_like(p0)
        circumferential[:,1] = np.tanh((p0[:,1] + .022) / .008)
        for direction in (*directions, radial, circumferential):
            for mm in (.004, .009):
                consider(start + mm * amount * direction, binding, f"localized {mm*1000:g} mm")
        _, start, binding, _ = best
        for name in joint_candidates:
            index = names.index("mixamorig:"+name)
            for strength in (.18, .40):
                coeff = strength * amount
                w = binding * (1-coeff)
                w[:, index] += coeff[:,0]
                consider(start, limit(w), name)
        print("PATCH", side, len(inds), f"{baseline:.3f} -> {best[0]:.3f}", best[3], flush=True)
        points[inds], weights[inds] = best[1:3]
    return points - start_points, weights - start_weights
