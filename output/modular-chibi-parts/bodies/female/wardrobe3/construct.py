"""Construct new garment surfaces from the exported female body."""
from copy import deepcopy

import numpy as np

import fit_module as fit
from common import BODY


def normals(points, faces):
    tri = points[faces]
    area = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    result = np.zeros_like(points)
    np.add.at(result, faces.ravel(), np.repeat(area, 3, axis=0))
    return fit.normalized(result)


def clip_surface(points, faces, field):
    """Preserve face winding and share the interpolated vertices on mask edges."""
    vertices, polygons, keys = [], [], {}

    def vertex(a, b):
        key = tuple(sorted((a, b)))
        if key not in keys:
            mix = 0. if a == b else float(field[a] / (field[a] - field[b]))
            keys[key] = len(vertices)
            vertices.append((a, b, mix))
        return keys[key]

    for face in faces.tolist():
        poly = []
        for a, b in zip(face, face[1:] + face[:1]):
            if field[a] >= 0.:
                poly.append(vertex(a, a))
            if (field[a] > 0 > field[b]) or (field[b] > 0 > field[a]):
                poly.append(vertex(a, b))
        polygons.extend((poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1))
    a, b, mix = np.asarray(vertices).T
    return a.astype(int), b.astype(int), mix[:, None], np.asarray(polygons, dtype=np.int32)


def top_field(item, points, round_number):
    x, y, z = points.T
    width = abs(x)
    # A cropped torso leaves space for the shipped jeans' raised waistband.
    hem = (.430, .437, .444)[round_number - 1]
    cuff = (.269, .255, .236)[round_number - 1]
    collar = .584 + .12 * np.maximum(0, y + .024)
    top = np.minimum.reduce((z - hem, cuff - width, collar - z))
    if item == "hoodie":
        # The back of the neck connects directly to the scalp. The arched
        # opening leaves the face, chin and ears visible.
        opening = .010 - .175 * np.clip((z - .730) / .247, 0, 1) ** 1.25
        opening += .14 * np.clip(z - .650, 0, .185)
        scalp = np.minimum(z - .576, y - opening)
        top = np.maximum(top, scalp)
    else:
        opening = .015 + .086 * np.clip((z - .501) / .102, 0, 1)
        top = np.minimum(top, np.maximum(width - opening, y + .027))
    if round_number == 3:
        # The vent opens where the arm closes against the chest. Keep the
        # shoulder seam and the outer sleeve connected above it.
        ellipse = ((width - .079) / .036) ** 2 + ((y + .010) / .034) ** 2 + ((z - .516) / .025) ** 2
        top = np.minimum(top, .025 * (ellipse - 1))
    return top


def section_rings(body, weights, round_number):
    """Loft ring samples from the outer intersections of body cross sections."""
    levels = np.linspace((.427, .419, .413)[round_number - 1], (.309, .329, .345)[round_number - 1], 16, dtype=np.float32)
    angles = np.arange(80) * (2 * np.pi / 80)
    ray = np.column_stack((np.cos(angles), np.sin(angles)))
    center = np.array((0., -.018))
    graph_tree = fit.tree_from(body.points, body.faces)
    shapes, layers = [], []
    for index, z in enumerate(levels):
        origin = np.tile(np.r_[center, z], (len(ray), 1))
        direction = np.column_stack((ray, np.zeros(len(ray))))
        start = origin + direction * .40
        shell = []
        raw = []
        for p, d in zip(start, direction):
            hit, _, face, length = graph_tree.ray_cast(p, -d, .40)
            if hit is None:
                shell.append(.040)
                raw.append(np.full(3, np.nan))
            else:
                shell.append(.40 - length)
                raw.append(tuple(hit))
        radius = np.asarray(shell)
        # Use the outer body envelope and progressively widen the straight
        # loft from the waist. This bridges gaps between the legs.
        if index == 0:
            waist_radius = radius.copy()
        rate = index / (len(levels) - 1)
        skirt_radius = waist_radius + (.042 + .008 * (round_number - 1)) * rate
        radius = np.maximum(radius + .003, skirt_radius)
        radius = .5 * radius + .25 * (np.roll(radius, 1) + np.roll(radius, -1))
        for i, p in enumerate(origin):
            p[:2] += ray[i] * radius[i]
        # Sample the female skin field from corresponding body sections.
        refs = np.asarray(raw)
        missed = ~np.isfinite(refs[:, 0])
        refs[missed] = origin[missed]
        _, closest, _, tri = fit.nearest(graph_tree, refs)
        corners = body.faces[tri]
        bary = fit.barycentric(body.points[corners], closest)
        w = np.einsum("vi,vib->vb", bary, weights[corners])
        if index == 0:
            waist_weights = w.copy()
        carry = min(.62 + .11 * (round_number - 1), rate * 1.4)
        w = (1 - carry) * w + carry * waist_weights
        shapes.append(origin.copy())
        layers.append(w)
    faces = []
    for j in range(len(levels) - 1):
        for i in range(len(ray)):
            a, b = j * len(ray) + i, j * len(ray) + (i + 1) % len(ray)
            c, d = a + len(ray), b + len(ray)
            faces.extend(((a, c, b), (b, c, d)))
    points = np.concatenate(shapes)
    direction = np.tile(np.column_stack((ray, np.zeros(len(ray)))), (len(levels), 1))
    return points, np.asarray(faces, dtype=np.int32), np.concatenate(layers), direction


STYLES = {
    "hoodie": (
        ("Petrol fleece", (.023, .202, .219), .90, 0.),
        ("Petrol rib knit", (.012, .094, .108), .94, 0.),
        ("Hood binding", (.055, .315, .315), .86, 0.),
        ("Kangaroo pocket", (.025, .235, .244), .90, 0.)),
    "jacket": (
        ("Cinnamon canvas", (.39, .096, .045), .82, 0.),
        ("Espresso rib", (.091, .024, .017), .90, 0.),
        ("Copper placket", (.55, .212, .079), .75, 0.),
        ("Chest welts", (.216, .048, .025), .84, 0.)),
    "shorts": (
        ("Ink twill", (.041, .068, .122), .91, 0.),
        ("Twill waistband", (.021, .036, .071), .92, 0.),
        ("Turned hem", (.071, .112, .170), .87, 0.),
        ("Pocket facing", (.028, .047, .083), .94, 0.)),
    "skirt": (
        ("Mulberry gabardine", (.284, .038, .109), .86, 0.),
        ("Mulberry waistband", (.133, .017, .048), .90, 0.),
        ("Mulberry hem", (.194, .025, .076), .87, 0.)),
    "boots": (
        ("Oxblood leather", (.17, .044, .030), .62, 0.),
        ("Charcoal lug sole", (.021, .018, .018), .90, 0.),
        ("Folded leather cuff", (.095, .026, .019), .68, 0.),
        ("Leather heel guard", (.115, .030, .022), .70, 0.)),
}


def garment_style(item, points, faces, directions, round_number):
    x, y, z = points.T
    width = abs(x)
    step = fit.GEOMETRY["smoothstep"]
    color = np.zeros(len(faces), dtype=np.int32)
    px, py, pz = points[faces].mean(axis=1).T
    offset = np.full(len(points), .0030)
    if item in {"hoodie", "jacket"}:
        sleeve = step(.070, .156, width)
        offset += .0052 * (1 - sleeve) + .0028 * sleeve
        # Reduce cloth loft at the joint creases, where unrelated body
        # components pass close to the sleeve and sides of the torso.
        underarm = step(.043, .082, width) * (1 - step(.091, .136, width))
        underarm *= 1 - step(.515, .553, z)
        offset -= .0048 * underarm
        if round_number > 1:
            near_shoulder = step(.043, .068, width) * (1 - step(.118, .167, width))
            near_shoulder *= 1 - step(.545, .578, z)
            sleeve_inward = step(.084, .135, width) * np.clip(-directions[:, 2] + .28, 0, 1)
            tight = np.maximum(near_shoulder, sleeve_inward)
            offset = np.minimum(offset, .0018 + .0062 * (1 - tight))
        if round_number == 3:
            localized = (1 - step(.14, .22, width)) * (1 - step(.575, .625, z))
            offset = np.minimum(offset, .0018 + .004 * (1 - localized))
        hem = (.430, .437, .444)[round_number - 1]
        cuff = (.269, .255, .236)[round_number - 1]
        color[(pz < hem + .012) | (abs(px) > cuff - .015)] = 1
        if item == "hoodie":
            offset += .008 * step(.620, .745, z)
            opening = top_field(item, points, round_number)[faces].mean(axis=1)
            color[(pz > .627) & (opening < .013)] = 2
            pocket = (abs(px) < .042) & (abs(px) + (pz - .449) * .57 < .057)
            pocket &= (pz > .444) & (pz < .481) & (py < -.060)
            color[pocket] = 3
        else:
            slit = .015 + .086 * np.clip((pz - .501) / .102, 0, 1)
            color[(abs(px) < slit + .016) & (py < -.027)] = 2
            color[(abs(px) > .028) & (abs(px) < .064) & (pz > .469) & (pz < .485) & (py < -.064)] = 3
    elif item == "shorts":
        medial = (1 - step(.015, .055, width)) * (1 - step(.316, .373, z))
        offset += .0030 * (1 - medial)
        if round_number == 3:
            gusset = (1 - step(.010, .033, width)) * step(.273, .301, z) * (1 - step(.345, .378, z))
            offset = (1 - gusset) * offset + gusset * .0018
        color[pz > (.430, .420, .414)[round_number - 1] - .012] = 1
        color[pz < (.248, .263, .280)[round_number - 1] + .010] = 2
        color[(pz > .394) & (pz < .424) & (abs(px) > .045) & (py < -.028)] = 3
    elif item == "skirt":
        color[pz > z.max() - .014] = 1
        color[pz < z.min() + .011] = 2
    else:
        medial = (1 - step(.024, .048, width))
        offset += .0024 * (1 - medial)
        sole = 1 - step(.002, .028, z)
        offset += .0035 * sole * np.clip(-directions[:, 2], 0, 1)
        color[pz < .018] = 1
        color[pz > (.103, .093, .084)[round_number - 1] - .010] = 2
        color[(pz >= .021) & (pz < .056) & (py > .030)] = 3
    return offset.astype(np.float32), color


def construct(item, body, round_number, vents=None):
    points, faces = body.points, body.faces
    weights = body.welded(body.weights)
    if item == "skirt":
        points, faces, weights, direction = section_rings(body, weights, round_number)
    else:
        if item in {"hoodie", "jacket"}:
            mask = top_field(item, points, round_number)
            if vents is not None and len(vents):
                for section in np.array_split(vents, 8):
                    if len(section):
                        distance = np.linalg.norm(points[:, None] - section[None, :], axis=2).min(axis=1)
                        mask = np.minimum(mask, distance - .0085)
        elif item == "shorts":
            z = points[:, 2]
            mask = np.minimum((.430, .420, .414)[round_number - 1] - z, z - (.248, .263, .280)[round_number - 1])
        else:
            mask = (.103, .093, .084)[round_number - 1] - points[:, 2]
        unit = normals(points, faces)
        a, b, mix, faces = clip_surface(points, faces, mask)
        direction = fit.normalized(unit[a] * (1 - mix) + unit[b] * mix)
        weights = weights[a] * (1 - mix) + weights[b] * mix
        points = points[a] * (1 - mix) + points[b] * mix
    points = points.astype(np.float32)
    direction = direction.astype(np.float32)
    graph = fit.adjacency(faces, len(points))
    weight_mix = .06 if round_number == 1 and item in {"hoodie", "jacket"} else .012
    weights = fit.limit_weights(((1 - weight_mix) * weights + weight_mix * fit.average(weights, graph)).astype(np.float32))
    offset, color = garment_style(item, points, faces, direction, round_number)
    return points + direction * offset[:, None], points, faces, weights, direction, graph, color


def write(path, points, faces, weights, colors, names, item):
    template = fit.Glb(BODY)
    asset = fit.Glb()
    asset.doc["nodes"] = deepcopy(template.doc["nodes"])
    asset.doc["scenes"] = deepcopy(template.doc["scenes"])
    asset.doc["scene"] = template.doc.get("scene", 0)
    mesh_node, = [n for n in asset.doc["nodes"] if "mesh" in n]
    mesh_node["name"] = item.title()
    skin = deepcopy(template.doc["skins"][0])
    skin["inverseBindMatrices"] = asset.floats(template.accessor(skin["inverseBindMatrices"]), "MAT4")
    asset.doc["skins"] = [skin]
    order = [names.index(asset.doc["nodes"][i]["name"]) for i in skin["joints"]]
    weights = weights[:, order]
    joints = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    values = np.take_along_axis(weights, joints, axis=1)
    values /= values.sum(axis=1, keepdims=True)
    joints[values == 0] = 0
    p = fit.gltf_axes(points).astype(np.float32)
    n = fit.gltf_axes(normals(points, faces)).astype(np.float32)
    assert np.all(np.linalg.norm(n, axis=1) > .99)

    def unsigned(data, kind, target):
        a = dict(bufferView=asset.view(np.asarray(data, "<u2").tobytes(), target=target),
                 componentType=5123, count=len(data), type=kind)
        asset.doc["accessors"].append(a)
        return len(asset.doc["accessors"]) - 1

    materials, primitives = [], []
    for material, (label, rgb, roughness, metallic) in enumerate(STYLES[item]):
        subset = faces[colors == material]
        if not len(subset):
            continue
        used, indices = np.unique(subset, return_inverse=True)
        positions = p[used]
        pos_acc = asset.floats(positions, "VEC3")
        asset.doc["accessors"][pos_acc].update(min=positions.min(axis=0).tolist(),
                                               max=positions.max(axis=0).tolist())
        attrs = {"POSITION": pos_acc, "NORMAL": asset.floats(n[used], "VEC3"),
                 "JOINTS_0": unsigned(joints[used], "VEC4", 34962),
                 "WEIGHTS_0": asset.floats(values[used], "VEC4")}
        for accessor in attrs.values():
            view = asset.doc["accessors"][accessor]["bufferView"]
            asset.doc["bufferViews"][view]["target"] = 34962
        primitives.append(dict(attributes=attrs, indices=unsigned(indices.ravel(), "SCALAR", 34963),
                               material=len(materials)))
        materials.append(dict(name=label, doubleSided=True,
                              pbrMetallicRoughness=dict(baseColorFactor=[*rgb, 1.],
                                                        roughnessFactor=roughness, metallicFactor=metallic)))
    asset.doc.update(meshes=[dict(name=item.title(), primitives=primitives)], materials=materials)
    asset.write(path)
