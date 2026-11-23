"""Shared clipping, materials and export for the body-derived patterns."""
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


STYLES = {
    "hoodie": (
        ("Wall", (.023, .202, .219), .90, 0.),
        ("Trim", (.012, .094, .108), .94, 0.),
    ),
    "jacket": (
        ("Cinnamon canvas", (.39, .096, .045), .82, 0.),
        ("Espresso rib", (.091, .024, .017), .90, 0.),
        ("Copper placket", (.55, .212, .079), .75, 0.),
    ),
    "shorts": (
        ("Ink twill", (.041, .068, .122), .91, 0.),
        ("Twill waistband", (.021, .036, .071), .92, 0.),
        ("Turned hem", (.071, .112, .170), .87, 0.),
    ),
    "skirt": (
        ("Mulberry gabardine", (.284, .038, .109), .86, 0.),
        ("Mulberry waistband", (.133, .017, .048), .90, 0.),
        ("Mulberry hem", (.194, .025, .076), .87, 0.)),

}


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
