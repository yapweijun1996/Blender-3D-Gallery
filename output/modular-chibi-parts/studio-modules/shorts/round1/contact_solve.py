"""Regularized coupled clearance solve for the thin garment shell."""
import numpy as np


def proposal(points, weights, shell, shell_faces, poses, skin, transforms, samples,
             graph, distances, overlaps, api, motion, columns, margin, weight_scale=.08):
    n = len(points)
    neighbor = api["average"]
    nearest = api["nearest"]
    witnesses = motion["pair_witnesses"]
    gsets, isets, dsets = [], [], []
    for row in np.flatnonzero((distances.min(axis=1) < margin) | (overlaps > 0)):
        _, _, tree, body, body_faces = samples[row]
        gp = poses[row]
        idx = np.where(distances[row] < margin)[0]
        ids = np.repeat(idx[:, None], 3, axis=1)
        bary = np.tile([1., 0, 0], (len(idx), 1))
        if overlaps[row]:
            pairs = np.array(tree.overlap(api["tree_from"](gp, shell_faces)), dtype=np.int32)
            when, bary_cross = witnesses(gp, shell_faces, body, body_faces, pairs[:, ::-1], dense=True)
            centers = np.unique(pairs[:, 1])
            when = np.r_[when, np.repeat(centers, 4)]
            bary_cross = np.vstack((bary_cross, np.tile(
                [[1/3, 1/3, 1/3], [.5, .5, 0], [0, .5, .5], [.5, 0, .5]], (len(centers), 1))))
            cross = shell_faces[when]
            gaps = nearest(tree, np.einsum("nki,nk->ni", gp[cross], bary_cross))[0]
            order = np.lexsort((gaps, when))
            top = order[np.r_[True, np.diff(when[order]) != 0]]
            ids = np.vstack((ids, cross[top]))
            bary = np.vstack((bary, bary_cross[top]))
        if not len(ids):
            continue
        locations = np.einsum("nki,nk->ni", gp[ids], bary)
        gap, _, normals, _ = nearest(tree, locations)
        include = gap < margin
        ids, bary, gap, normals = ids[include], bary[include], gap[include], normals[include]
        if not len(ids):
            continue
        influence = columns[ids % n]
        joints = transforms[row, influence]
        endpoints = np.einsum("nklij,nkj->nkli", joints[..., :3], shell[ids]) + joints[..., 3]
        gweight = np.einsum("ni,nkli->nkl", normals, endpoints)
        gweight -= gweight.mean(axis=2, keepdims=True)
        gxyz = np.einsum("ni,nkij->nkj", normals, skin[row, ids % n, :, :3])
        grad = np.concatenate((gxyz, gweight / weight_scale), axis=2) * bary[..., None]
        gsets.append(grad.astype(np.float32))
        isets.append(ids % n)
        dsets.append(margin - gap)
    if not isets:
        return points, weights
    ids, gradient, need = (np.concatenate(items) for items in (isets, gsets, dsets))
    flat_ids = ids.ravel()
    flat_grad = gradient.reshape(-1, 7)
    norms = np.linalg.norm(gradient, axis=(1, 2)).clip(.25)
    gradient /= norms[:, None, None]
    need /= norms
    count = len(points)
    w0 = np.take_along_axis(weights, columns, axis=1)
    diags = np.stack([np.bincount(flat_ids, weights=abs(g), minlength=count) for g in flat_grad.T], axis=1)
    smooth = np.array([2.5, 2.5, 2.5, 1.4, 1.4, 1.4, 1.4], dtype=np.float32)
    regular = np.array([.65, .65, .65, 1.5, 1.5, 1.5, 1.5], dtype=np.float32)
    denom = diags + smooth + regular
    offsets = np.zeros((count, 7), dtype=np.float32)
    delta = np.zeros_like(offsets)
    for _ in range(80):
        violation = (need - np.einsum("nki,nki->n", gradient, delta[ids])).clip(0)
        flat = violation.repeat(3)
        pull = np.stack([np.bincount(flat_ids, weights=flat * g, minlength=count) for g in flat_grad.T], axis=1)
        pull += smooth * (neighbor(delta, graph) - delta) - regular * delta
        proposed = delta + .83 * (pull / denom)
        proposed[:, :3] = motion["limit_delta"](proposed[:, :3], .0045)
        w = motion["simplex"](w0 + (proposed[:, 3:] / weight_scale).clip(-.18, .18))
        proposed[:, 3:] = (w - w0) * weight_scale
        offsets, delta = delta, (.8 * proposed + .2 * offsets).astype(np.float32)
    w = weights.copy()
    np.put_along_axis(w, columns, w0 + delta[:, 3:] / weight_scale, axis=1)
    return points + delta[:, :3], api["limit_weights"](w)
