"""Body-derived garment patterns and sewn details for the female rig."""
from pathlib import Path

import numpy as np
from mathutils.bvhtree import BVHTree

import construct
import fit_module as fit
import skirt_envelope
import polish
from common import FEMALE


def weights_at(body, points):
    _, hits, _, triangles = fit.nearest(fit.tree_from(body.points, body.faces), points)
    corners = body.faces[triangles]
    bary = fit.barycentric(body.points[corners], hits)
    return np.einsum("vi,vij->vj", bary, body.welded(body.weights)[corners])


def loft_faces(rows, columns, wrap=True):
    faces = []
    for row in range(rows - 1):
        for column in range(columns if wrap else columns - 1):
            left = row * columns + column
            right = row * columns + (column + 1) % columns
            faces.extend(((left, right, right + columns), (left, right + columns, left + columns)))
    return np.asarray(faces, dtype=np.int32)


def split_panel(points, faces, weights, field):
    sides = []
    for sign in (1, -1):
        a, b, mix, tri = construct.clip_surface(points, faces, field * sign)
        sides.append((points[a] * (1 - mix) + points[b] * mix, tri,
                      weights[a] * (1 - mix) + weights[b] * mix))
    return sides


def join(parts):
    points, faces, weights, colors = [], [], [], []
    offset = 0
    for xyz, tri, influence, color in parts:
        points.append(xyz)
        faces.append(tri + offset)
        weights.append(influence)
        colors.append(np.broadcast_to(color, len(tri)))
        offset += len(xyz)
    points = np.vstack(points)
    full_weights = np.vstack(weights)
    # A material border is a single sewn edge with one position and skin field.
    keys = np.column_stack((np.round(points, 7), np.round(full_weights, 6)))
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    triangles = inverse[np.vstack(faces)]
    valid = (triangles != np.roll(triangles, 1, axis=1)).all(axis=1)
    return points[first].astype(np.float32), triangles[valid], full_weights[first], np.concatenate(colors)[valid]


def ribbon(coords, radius, influences, sides=8, trim=1):
    coords = np.asarray(coords)
    tangent = fit.normalized(np.gradient(coords, axis=0))
    side = fit.normalized(np.cross(tangent, [0, 1, 0]))
    other = np.cross(tangent, side)
    angle = np.arange(sides) * 2 * np.pi / sides
    points = coords[:, None] + radius * (side[:, None] * np.cos(angle)[None, :, None]
                                         + other[:, None] * np.sin(angle)[None, :, None])
    return points.reshape(-1, 3), loft_faces(len(coords), sides), np.repeat(influences, sides, axis=0), trim


def cowl(body, hood, number, shell=None):
    # The hood is a folded horseshoe with a rolled lip. Taper the ends
    # toward the neckline so the opening stays visible from the front.
    angles = np.linspace(-.81 * np.pi, .81 * np.pi, 33)
    t = np.arange(14) * 2 * np.pi / 14
    rear = np.maximum(0, np.cos(angles))
    taper = np.sin(np.linspace(0, np.pi, len(angles))) ** .65
    rr = (.003 + (.013 + .015 * rear) * taper) if hood else (.003 + .005 * taper)
    rz = (.003 + (.014 + .018 * rear) * taper) if hood else (.004 + .007 * taper)
    center = np.column_stack((.048 * np.sin(angles), -.016 + (.050 if hood else .027) * np.cos(angles),
                              (.552 if hood else .562) + (.002 if hood else .004) * rear))
    fitted = not hood or number > 1
    if fitted:
        angles = np.linspace(-1.51, 1.51, 33)
        rear = np.cos(angles)
        if hood:
            rr = .004 + .030 * taper
            rz = .0035 + .0205 * taper
            center = np.column_stack((.069 * np.sin(angles), .046 + .033 * rear,
                                      .550 - .013 * rear - (.0025 if number == 3 else 0.)))
        else:
            rr, rz = .003 + .005 * taper, .004 + .007 * taper
            center = np.column_stack((.047 * np.sin(angles), .036 + .014 * rear,
                                      .565 - .004 * rear))
    radial = np.column_stack((np.sin(angles), np.cos(angles), np.zeros(len(angles))))
    points = (center[:, None] + (rr[:, None] * np.cos(t))[:, :, None] * radial[:, None])
    points[..., 2] += rz[:, None] * np.sin(t)
    # A stable upper-spine attachment keeps the folded volume off the scalp.
    w = np.zeros((len(angles), len(body.names)))
    w[:, body.names.index("mixamorig:Spine2")] = 1
    w = np.repeat(w[:, None], len(t), axis=1)
    if hood and number == 3:
        cloth, shell_faces, shell_weights = shell
        tree = BVHTree.FromPolygons(cloth.tolist(), shell_faces.tolist(), all_triangles=True)
        for row, angle in enumerate(angles):
            for col, fold in enumerate(t):
                attach = np.clip((-np.cos(fold) - .14) / .86, 0, 1)
                if attach < .08:
                    continue
                p = points[row, col]
                # The inside of the fold is sewn into the upper back panel.
                # Only the exposed part keeps the rigid spine attachment.
                x = p[0] * (1 - .13 * attach)
                hit, _, tri, _ = tree.ray_cast((x, .20, p[2]), (0, -1, 0), .23)
                if hit is None:
                    continue
                corners = shell_faces[tri]
                bary = fit.barycentric(cloth[corners][None], np.asarray(hit)[None])[0]
                anchor = np.array(hit) + (0., .0003, 0.)
                points[row, col] += attach * (anchor - p)
                w[row, col] += attach * (bary @ shell_weights[corners] - w[row, col])
    flat = points.reshape(-1, 3)
    faces = loft_faces(len(angles), len(t))
    if not fitted:
        faces = faces[:, ::-1]
    caps = []
    for start, flip in ((0, True), ((len(angles)-1)*len(t), False)):
        caps.extend((start, start + j + int(flip), start + j + int(not flip)) for j in range(1, len(t)-1))
    return flat, np.vstack((faces, caps)), w.reshape(len(flat), -1), 0 if hood else 1


def pocket(shell, faces, weights, hem):
    positions, influences = [], []
    tree = BVHTree.FromPolygons(shell.tolist(), faces.tolist(), all_triangles=True)
    for z, width, bulge in ((hem+.014, .035, .003), (hem+.022, .042, .011),
                            (hem+.040, .039, .011), (hem+.050, .028, .0035)):
        for u in np.linspace(-1, 1, 13):
            x = u * width
            hit, _, index, _ = tree.ray_cast((x, -.2, z), (0, 1, 0), .3)
            corners = faces[index]
            bary = fit.barycentric(shell[corners][None], np.asarray(hit)[None])[0]
            positions.append((x, hit.y - (bulge * (1 - .76 * u**6)), z))
            influences.append(bary @ weights[corners])
    return np.asarray(positions), loft_faces(4, 13, False), np.asarray(influences), 0


def over_jeans(cloth, base, jeans, hem):
    tree = fit.tree_from(jeans.points, jeans.faces)
    for i in np.flatnonzero(base[:, 2] < .436):
        center = np.array([0, -.026, min(base[i, 2], .418)])
        radial = fit.normalized(np.array([[cloth[i, 0], cloth[i, 1] + .026, 0.]]))[0]
        hit, _, _, distance = tree.ray_cast(center + .23 * radial, -radial, .23)
        if hit is None:
            continue
        radius = .23 - distance
        existing = np.dot(cloth[i] - center, radial)
        lower = 1 - np.clip((base[i, 2] - hem) / (.438 - hem), 0, 1)
        cloth[i] += max(0, radius + .012 - existing) * (.3 + .7 * lower) * radial
    return cloth


def sweep_outer(points, weights, radial, obstacle, data, margin, triangles=None, reach=.06):
    matrices = data[4]
    original = obstacle.points
    shape_weights = obstacle.welded(obstacle.weights)
    faces = obstacle.faces if triangles is None else triangles
    used, indices = np.unique(faces, return_inverse=True)
    remapped = indices.reshape(faces.shape).tolist()
    radius = np.zeros(len(points))
    for start in range(0, len(matrices), 24):
        batch = slice(start, start + 24)
        m = fit.GEOMETRY["pose_matrices"](matrices[batch], weights)
        centers = fit.GEOMETRY["skin_positions"](points, m)
        axes = np.einsum("fvij,vj->fvi", m[..., :3], radial)
        scale = np.linalg.norm(axes, axis=2).clip(.1)
        targets = centers + axes * reach
        directions = -axes / scale[..., None]
        g = fit.GEOMETRY["pose_matrices"](matrices[batch], shape_weights[used])
        other = fit.GEOMETRY["skin_positions"](original[used], g)
        for source, target, direction, ratios in zip(other, targets, directions, scale, strict=True):
            tree = BVHTree.FromPolygons(source.tolist(), remapped, all_triangles=True)
            distances = np.asarray([tree.ray_cast(a, b, float(s) * (2 * reach))[3]
                                    for a, b, s in zip(target.tolist(), direction.tolist(), ratios, strict=True)], dtype=float)
            delta = np.nan_to_num(reach - distances / ratios + margin, nan=0.)
            radius = np.maximum(radius, delta)
    print("LAYER_SWEEP", obstacle.path.name, "largest correction mm", round(radius.max() * 1000, 3), flush=True)
    return (points + radial * radius[:, None]).astype(np.float32)


def over_tshirt(cloth, base, outward, tshirt, number):
    tree = fit.tree_from(tshirt.points, tshirt.faces)
    reach = .044 if number == 1 else .035
    for i in np.flatnonzero((abs(base[:, 0]) < .13) & (base[:, 2] > .422)):
        ray = outward[i]
        hit, _, _, distance = tree.ray_cast(base[i] + reach * ray, -ray, reach)
        if hit is None:
            continue
        delta = reach - distance + (.0045 if number == 1 else .0028)
        if number >= 2:
            x, _, z = base[i]
            underarm = fit.GEOMETRY["smoothstep"](.042, .072, abs(x)) * (
                1 - fit.GEOMETRY["smoothstep"](.543, .570, z))
            delta = min(delta, (1 - underarm) * .023 + underarm * .0025)
        existing = np.dot(cloth[i] - base[i], ray)
        cloth[i] += max(0, delta - existing) * ray
    return cloth


def zipper(tree, cloth, faces, weights, hem):
    parts = []
    for side in (-1, 1):
        coords, skin = [], []
        for z in np.linspace(hem+.010, .558, 20):
            slit = .018 + .034 * np.clip((z - .507) / .075, 0, 1)
            x = side * (slit + .005)
            hit, _, index, _ = tree.ray_cast((x, -.21, z), (0, 1, 0), .16)
            if hit is None:
                continue
            corners = faces[index]
            bary = fit.barycentric(cloth[corners][None], np.asarray(hit)[None])[0]
            coords.append((x, hit.y - .0022, z))
            skin.append(bary @ weights[corners])
        if len(coords) > 1:
            parts.append(ribbon(coords, .0014, skin, sides=6, trim=2))
    return parts


def bomber_envelope(cloth, base, weights, tshirt, data):
    x, y, z = base.T
    width = abs(x)
    step = fit.GEOMETRY["smoothstep"]
    # The front and back panels are cut with room over the fitted jersey.
    # Keep the extra depth predominantly along the chest, away from the axilla.
    torso = 1 - step(.067, .113, width)
    neck = 1 - .76 * step(.545, .583, z)
    cloth[:, 1] += .018 * torso * neck * np.tanh((y + .026) / .021)
    cloth[:, 0] += .004 * torso * np.tanh(x / .045)
    selected = np.flatnonzero((width < .088) & (z > .421))
    radial = fit.normalized(np.column_stack((cloth[selected, 0] * .57, cloth[selected, 1] + .026,
                                             np.zeros(len(selected)))))
    padded = sweep_outer(cloth[selected], weights[selected], radial, tshirt, data, .005, reach=.034)
    move = fit.SOURCE["limit_delta"](padded - cloth[selected], .022)
    cloth[selected] += move * (1 - step(.054, .088, width[selected]))[:, None]

    for side in (-1, 1):
        ids = np.flatnonzero((x * side > .064) & (width < .145) & (z > .506))
        direction = fit.normalized(np.column_stack((np.zeros(len(ids)), y[ids] + .029, z[ids] - .545)))
        local = tshirt.faces[(tshirt.points[tshirt.faces, 0].mean(axis=1) * side > .043)]
        padded = sweep_outer(cloth[ids], weights[ids], direction, tshirt, data, .0035, local, reach=.026)
        fade = step(.064, .083, width[ids]) * (1 - step(.115, .145, width[ids]))
        cloth[ids] += fit.SOURCE["limit_delta"](padded - cloth[ids], .012) * fade[:, None]
    return cloth


def top(item, body, number, layers, data):
    hood = item == "hoodie"
    x, y, z = body.points.T
    width = abs(x)
    hem = ((.407, .408, .409) if hood else (.421, .423, .424))[number - 1]
    cuff = .322 if hood and number == 2 else (.279 if hood else .278)
    neckline = .578 + .10 * (y + .024)
    field = np.minimum.reduce((z - hem, cuff - width, neckline - z))
    if not hood:
        opening = .018 + .034 * np.clip((z - .507) / .075, 0, 1)
        field = np.minimum(field, np.maximum(width - opening, y + .019))
    a, b, mix, faces = construct.clip_surface(body.points, body.faces, field)
    base = body.points[a] * (1 - mix) + body.points[b] * mix
    weights = body.welded(body.weights)
    weights = weights[a] * (1 - mix) + weights[b] * mix
    # Split exactly on the rib knit boundaries before applying the cloth loft.
    rib = np.maximum(hem + .014 - base[:, 2], abs(base[:, 0]) - (cuff - .019))
    if not hood and number >= 2:
        lapel = .578 + .10 * (base[:, 1] + .024)
        collar = np.minimum(base[:, 2] - lapel + .010, .090 - abs(base[:, 0]))
        rib = np.maximum(rib, collar)
    parts = []
    for color, (p, f, w) in zip((1, 0), split_panel(base, faces, weights, rib), strict=True):
        if hood or color == 1 or number == 3:
            parts.append((p, f, w, color))
        else:
            x, y, z = p.T
            opening = .018 + .034 * np.clip((z - .507) / .075, 0, 1)
            facing = np.minimum(opening + .0045 - abs(x), -y - .021)
            for band, (q, g, v) in zip((2, 0), split_panel(p, f, w, facing), strict=True):
                parts.append((q, g, v, band))
    base, faces, weights, colors = join(parts)
    # Get the outward field from the original body shell, including neckline,
    # waist and wrist boundaries where the garment has only one adjacent face.
    _, hits, _, nearest = fit.nearest(fit.tree_from(body.points, body.faces), base)
    corners = body.faces[nearest]
    bary = fit.barycentric(body.points[corners], hits)
    normal = construct.normals(body.points, body.faces)
    outward = fit.normalized(np.einsum("vi,vij->vj", bary, normal[corners]))
    x, y, z = base.T
    width = abs(x)
    step = fit.GEOMETRY["smoothstep"]
    axilla = step(.041, .072, width) * (1 - step(.125, .166, width)) * (1 - step(.525, .560, z))
    if (hood and number == 3) or (not hood and number >= 2):
        axilla = step(.033, .057, width) * (1 - step(.134, .167, width)) * (1 - step(.541, .563, z))
    loft = (1 - axilla) * (.0074 if hood else .0088) + axilla * (.0015 if number < 3 else .00135)
    rib = np.clip((hem + .013 - z) / .006, 0, 1) + np.clip((width - cuff + .018) / .009, 0, 1)
    loft += .0022 * rib
    if not hood:
        cuff_angle = np.arctan2(z - .545, y + .034)
        waist_angle = np.arctan2(y + .026, x)
        cuff_knit = np.clip((width - cuff + .018) / .007, 0, 1)
        waist_knit = np.clip((hem + .013 - z) / .006, 0, 1)
        loft += .00065 * (cuff_knit * (1 + np.cos(10 * cuff_angle)) +
                          waist_knit * (1 + np.cos(20 * waist_angle)))
    cloth = base + outward * loft[:, None]
    if not hood or number > 1:
        cloth = over_jeans(cloth, base, layers["jeans"], hem)
    if not hood and number == 3:
        cloth = bomber_envelope(cloth, base, weights, layers["tshirt"], data)
    elif not hood:
        cloth = over_tshirt(cloth, base, outward, layers["tshirt"], number)
        if number == 2:
            ids = np.flatnonzero((abs(base[:, 0]) < .087) & (base[:, 2] > .420))
            radial = fit.normalized(np.column_stack((cloth[ids, 0], cloth[ids, 1] + .026, np.zeros(len(ids)))))
            expansion = (1 - step(.044, .086, abs(base[ids, 0])))
            padded = sweep_outer(cloth[ids], weights[ids], radial, layers["tshirt"], data, .0065, reach=.031)
            delta = fit.SOURCE["limit_delta"](padded - cloth[ids], .025)
            cloth[ids] += delta * expansion[:, None]
    if hood and number == 3:
        jeans = layers["jeans"]
        ids = np.flatnonzero(base[:, 2] < .440)
        radial = fit.normalized(np.column_stack((cloth[ids, 0], cloth[ids, 1] + .026, np.zeros(len(ids)))))
        upper_jeans = jeans.faces[jeans.points[jeans.faces, 2].max(axis=1) > .348]
        cloth[ids] = sweep_outer(cloth[ids], weights[ids], radial, jeans, data, .0055, upper_jeans)
    parts = [(cloth, faces, weights, colors)]
    if hood or number == 1:
        parts.append(cowl(body, hood, number, (cloth, faces, weights)))
    if hood:
        parts.append(pocket(cloth, faces, weights, hem))
    tree = BVHTree.FromPolygons(cloth.tolist(), faces.tolist(), all_triangles=True)
    if hood:
        for sign in (-1, 1):
            coords, pull = [], []
            for fraction in np.linspace(0, 1, 9):
                z = .568 - .047 * fraction
                x = sign * (.020 + .007 * fraction - .002 * np.sin(fraction * 2 * np.pi))
                hit, _, i, _ = tree.ray_cast((x, -.20, z), (0, 1, 0), .30)
                if hit is None:
                    continue
                corners = faces[i]
                pull.append(fit.barycentric(cloth[corners][None], np.asarray(hit)[None])[0] @ weights[corners])
                coords.append((x, hit.y - .0035 - .004 * np.sin(np.pi * fraction), z))
            parts.append(ribbon(coords, .00165, pull))
    else:
        parts.extend(zipper(tree, cloth, faces, weights, hem))
    points, faces, weights, colors = join(parts)
    weights = fit.limit_weights(weights.astype(np.float32))
    return points, faces, weights, colors


def skirt(body, number, data):
    sides, levels = 64, 15
    hem = (.307, .300, .304)[number - 1]
    z = np.r_[.425, .421, .413, .410, np.linspace(.402, hem + .004, levels - 5), hem]
    rate = np.clip((.411 - z) / (.411 - hem), 0, 1)
    angles = np.arange(sides) * (2 * np.pi / sides)
    radial = np.column_stack((np.cos(angles), np.sin(angles), np.zeros(sides)))
    center = np.column_stack((np.zeros(levels), np.full(levels, -.015), z))
    rays = np.tile(radial, (levels, 1))
    centers = np.repeat(center, sides, axis=0)
    rest_tree = fit.tree_from(body.points, body.faces)
    ref = []
    for origin, ray in zip(centers, rays, strict=True):
        hit, _, _, _ = rest_tree.ray_cast(origin + .31 * ray, -ray, .31)
        ref.append(origin if hit is None else hit[:])
    ref = np.asarray(ref)
    rest_radius = ((ref - centers) * rays).sum(axis=1).reshape(levels, sides)
    rest_radius = .50 * rest_radius + .25 * (np.roll(rest_radius, 1, axis=1) + np.roll(rest_radius, -1, axis=1))
    fit_radius = rest_radius[0] + np.array([.003, .007, .007, .004] + [0.] * (levels - 4))[:, None]
    radius = np.maximum(rest_radius + .004, fit_radius + .060 * rate[:, None])
    reference_weights = weights_at(body, ref).reshape(levels, sides, -1)
    # Both thighs carry the lower edge. A smooth left/right distribution
    # prevents valleys in the weight field at the front and back centre.
    w = np.repeat(reference_weights[:1], levels, axis=0)
    left = .5 + .42 * np.cos(angles)
    drive = ((.62, .82, .91)[number - 1] * rate)[:, None]
    w *= 1 - drive[..., None]
    for side, share in (("Left", left), ("Right", 1 - left)):
        w[:, :, body.names.index(f"mixamorig:{side}UpLeg")] += drive * share
    w = fit.limit_weights(w.reshape(levels * sides, -1).astype(np.float32))
    points = centers + rays * radius.reshape(-1, 1)
    points = skirt_envelope.clamp(points, w, rays, data, rings=levels, sides=sides,
                                  center_y=-.015, margin=(.006, .0075, .009)[number - 1], smooth=number >= 2)
    # Sixteen folds, each with a rounded crest and a tighter trailing groove.
    crease = np.tile([0., .0045, .0065, .0020] if number >= 2 else [0., .0031, .0045, .0011], sides // 4)
    points += rays * (rate[:, None] ** .75 * crease[None, :]).reshape(-1, 1)
    faces = loft_faces(levels, sides)[:, ::-1]
    colors = np.repeat([1, 1, 1] + [0] * (levels - 5) + [2], 2 * sides)
    return points.astype(np.float32), faces, w, colors


def shorts_panels(surface, waist, hem):
    z = surface.points[:, 2]
    field = np.minimum(waist - z, z - hem)
    a, b, mix, faces = construct.clip_surface(surface.points, surface.faces, field)
    base = surface.points[a] * (1 - mix) + surface.points[b] * mix
    weights = surface.welded(surface.weights)
    weights = weights[a] * (1 - mix) + weights[b] * mix
    lower, upper = split_panel(base, faces, weights, hem + .011 - base[:, 2])
    upper_trim, cloth = split_panel(*upper, upper[0][:, 2] - (waist - .013))
    return join([(*lower, 2), (*upper_trim, 1), (*cloth, 0)])


def shorts(body, number, data):
    waist, hem = .419, (.285, .275, .280)[number-1]
    base, faces, weights, colors = shorts_panels(body, waist, hem)
    _, hits, _, nearest = fit.nearest(fit.tree_from(body.points, body.faces), base)
    corners = body.faces[nearest]
    bary = fit.barycentric(body.points[corners], hits)
    normals = construct.normals(body.points, body.faces)
    outward = fit.normalized(np.einsum("vi,vij->vj", bary, normals[corners]))
    x, y, z = base.T
    step = fit.GEOMETRY["smoothstep"]
    # Preserve space between the legs by tapering the flare on the medial
    # quarters. The continuous saddle still uses the body's skin field.
    medial = step(.010, .051, abs(x))
    # Route the exposed ends of the gusset forward and back around the fold.
    # Moving inwards from the inner-thigh surface consumes the narrow gap
    # between the legs when a knee swings across the midline.
    saddle = ((1 - step(.013, .029, abs(x))) * step(.296, .310, z) *
              (1 - step(.330, .354, z)))
    front = 1 - step(-.060, -.042, y)
    rear = step(.023, .042, y)
    flank = saddle * np.maximum(front, rear)
    bias = np.column_stack((np.zeros(len(x)), rear - front, np.zeros(len(x))))
    outward = fit.normalized(outward * (1 - .72 * flank[:, None]) + .72 * flank[:, None] * bias)
    cuff = 1 - step(hem + .004, hem + .025, z)
    band = step(waist - .014, waist - .007, z)
    level_edge = np.maximum(band, cuff)
    outward[:, 2] *= 1 - .92 * level_edge
    outward = fit.normalized(outward)
    loft = .0025 + .0040 * medial + (.005 + .001 * number) * cuff * (.18 + .82 * medial) + .002 * band + .0035 * flank
    points = (base + outward * loft[:, None]).astype(np.float32)
    weights = fit.limit_weights(weights.astype(np.float32))
    reference = body.points[body.faces]
    centers = reference.mean(axis=1)
    for side in (-1, 1):
        sweep_top = .324 if number == 1 else hem + .020
        use = (z < sweep_top) & (x * side > 0)
        same_thigh = ((centers[:, 0] * side > 0) & (reference[:, :, 2].min(axis=1) < .354) &
                      (reference[:, :, 2].max(axis=1) > .222))
        reach = .028 if number == 1 else .009
        fitted = sweep_outer(points[use], weights[use], outward[use], body, data, .0018,
                             body.faces[same_thigh], reach=reach)
        if number >= 2:
            ease = 1 - step(hem + .009, sweep_top, z[use])
            change = fit.SOURCE["limit_delta"](fitted - points[use], .007)
            fitted = points[use] + change * ease[:, None]
        points[use] = fitted
    return points, faces, weights, colors


def retopologized_shorts(body, data):
    # The shipped female fit supplies a reparameterized saddle and a tested
    # skin field. The new cut and its cuff room are fitted to the supplied body.
    fitted = fit.Module(FEMALE / "round3/female-jeans-v3.glb", body.names)
    waist, hem = .419, .276
    points, faces, weights, colors = shorts_panels(fitted, waist, hem)
    weights = fit.limit_weights(weights.astype(np.float32))
    tree = fit.tree_from(body.points, body.faces)
    signed, _, normal, _ = fit.nearest(tree, points)
    x, y, z = points.T
    step = fit.GEOMETRY["smoothstep"]
    cuff = 1 - step(hem + .002, hem + .023, z)
    side = step(.009, .044, abs(x))
    flare = np.column_stack((normal[:, 0], normal[:, 1], np.zeros(len(points))))
    flare = fit.normalized(flare)
    correction = np.clip(.0033 - signed, 0, .0045)
    points = points + normal * correction[:, None]
    points += flare * (cuff * (.00035 + .0028 * side))[:, None]

    sections = body.points[body.faces]
    centers = sections.mean(axis=1)
    for sign in (-1, 1):
        use = (x * sign > 0) & (z < hem + .014) & (abs(x) > .016)
        leg = ((centers[:, 0] * sign > 0) & (sections[:, :, 2].min(axis=1) < .317) &
               (sections[:, :, 2].max(axis=1) > .225))
        room = sweep_outer(points[use], weights[use], flare[use], body, data, .0018,
                           body.faces[leg], reach=.008)
        points[use] += fit.SOURCE["limit_delta"](room - points[use], .0028)
    return points.astype(np.float32), faces, weights, colors


def refine_skirt(body, data):
    nominal, faces, weights, colors = skirt(body, 1, data)
    prior_path = Path(__file__).resolve().parent / "attempts/skirt/1/skirt.glb"
    prior = fit.Module(prior_path, body.names)
    points = np.empty_like(nominal)
    weights = np.empty_like(weights)
    for color, (_, indices) in enumerate(prior.parts):
        used = np.unique(faces[colors == color])
        points[used] = prior.source_points[indices]
        weights[used] = prior.weights[indices]
    # Level the waist and the turned hem, while keeping each crease in the
    # original ring instead of averaging adjacent folds into a flat surface.
    goal = points.copy()
    z_error = points[:, 2] - nominal[:, 2]
    goal[:, 2] = nominal[:, 2] + np.clip(z_error, -.0025, .003)
    radial_error = (points - nominal).reshape(15, 64, 3).copy()
    radial_error[..., 2] = 0.
    soft = .50 * radial_error + .25 * (np.roll(radial_error, 4, axis=1) + np.roll(radial_error, -4, axis=1))
    goal += .75 * (soft - radial_error).reshape(-1, 3)
    improvement = np.linalg.norm(goal - points, axis=1)
    candidates = np.argsort(-improvement)
    candidates = candidates[improvement[candidates] > .004][:32]
    points = polish.solve(points, faces, weights, data, candidates, .00062, goals=goal)
    return points, faces, weights, colors


def bottom(item, body, number, data):
    if item == "skirt":
        return refine_skirt(body, data) if number == 3 else skirt(body, number, data)
    return retopologized_shorts(body, data) if number == 3 else shorts(body, number, data)
