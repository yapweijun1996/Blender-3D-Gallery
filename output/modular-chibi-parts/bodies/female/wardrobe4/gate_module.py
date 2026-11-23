"""Check the final GLB's skin against the female body and shipped outfit layers."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

import fit_module as fit
from common import BODY, CLIPS, FEMALE, HERE, MASTER, MOTION, arguments

SHIPPED = {
    "tshirt": FEMALE / "round2/female-tshirt-v2.glb",
    "jeans": FEMALE / "round3/female-jeans-v3.glb",
    "boots": FEMALE / "wardrobe3/boots.glb",
    "sneakers": FEMALE / "female-sneakers.glb",
}
LIMITS = dict(hoodie=6000, jacket=6000, shorts=6000, skirt=6000, boots=3500)


def layers_for(label):
    if label in ("shorts", "skirt"):
        return ("tshirt", "sneakers", "boots")
    if label == "boots":
        return ("tshirt", "jeans")
    return (("jeans", "tshirt", "sneakers", "boots") if label == "jacket" else ("jeans", "sneakers", "boots"))


def pose(module, matrices):
    weights = fit.GEOMETRY["pose_matrices"](matrices, module.weights)
    return fit.GEOMETRY["skin_positions"](module.source_points, weights)


def bound_to_body(module, template):
    def skeleton(glb):
        doc = glb.doc
        skin, = doc["skins"]
        by_name = {doc["nodes"][i]["name"]: matrix for i, matrix in
                   zip(skin["joints"], glb.accessor(skin["inverseBindMatrices"]), strict=True)}
        nodes = {node["name"]: node for node in doc["nodes"] if "mesh" not in node}
        return by_name, nodes

    target, target_nodes = skeleton(template)
    actual, actual_nodes = skeleton(module.glb)
    return (len(actual) == 65 and actual.keys() == target.keys() and
            all(np.array_equal(actual[name], target[name]) for name in actual) and
            actual_nodes == target_nodes)


def textures(module):
    sizes = []
    for image in module.glb.doc.get("images", []):
        suffix = ".png" if image["mimeType"] == "image/png" else ".jpg"
        path = HERE / ".runtime" / ("gate-texture" + suffix)
        path.write_bytes(module.glb.payload(image["bufferView"]))
        texture = bpy.data.images.load(str(path), check_existing=False)
        sizes.append(list(texture.size))
        bpy.data.images.remove(texture)
        path.unlink()
    return sizes


def mesh_components(module):
    edges = [[] for _ in module.points]
    for a, b, c in module.faces:
        edges[a].extend((b, c))
        edges[b].extend((a, c))
        edges[c].extend((a, b))
    pending = set(range(len(edges)))
    components = []
    while pending:
        seed = pending.pop()
        group = [seed]
        for vertex in group:
            neighbors = pending.intersection(edges[vertex])
            pending.difference_update(neighbors)
            group.extend(neighbors)
        components.append(np.asarray(group))
    return sorted(components, key=len, reverse=True)


def unexpected_top_boundaries(module, label):
    shell = mesh_components(module)[0]
    faces = module.faces[np.isin(module.faces, shell).all(axis=1)]
    edges = np.sort(np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]])), axis=1)
    edge, count = np.unique(edges, axis=0, return_counts=True)
    x, y, z = module.points[edge[count == 1]].mean(axis=1).T
    opening = (abs(x) > .247) | (z < .430) | (z > .559)
    if label == "jacket":
        opening |= (abs(x) < .068) & (y < -.013)
    return int((~opening).sum())


def hoodie_cowl(module):
    groups = mesh_components(module)
    groups = [group for group in groups[1:] if len(group) > 100 and module.points[group, 1].mean() > 0.]
    if not groups:
        return None
    group = groups[0]
    use = np.isin(module.unweld, group)
    triangles = module.source_faces[use[module.source_faces].all(axis=1)]
    return use, triangles


def box_gaps(a_low, a_high, b_low, b_high):
    return np.linalg.norm(np.maximum(0, np.maximum(a_low - b_high, b_low - a_high)), axis=-1)


def cowl_head_bound(points, mask, faces, head):
    xyz = points[mask]
    head_low, head_high = head.min(axis=1), head.max(axis=1)
    distance = box_gaps(xyz.min(axis=0), xyz.max(axis=0), head_low, head_high)
    if distance.min() >= .0015:
        return distance.min()
    close = distance < .0015
    cloth = points[faces]
    cloth_low, cloth_high = cloth.min(axis=1), cloth.max(axis=1)
    return min(.0015, box_gaps(cloth_low[:, None], cloth_high[:, None],
                               head_low[None, close], head_high[None, close]).min())


def gate(path, output, data, assets):
    names, _, female, rows, transforms = data
    label = path.stem
    module = fit.Module(path, names)
    assert bound_to_body(module, fit.Glb(BODY)), "Exported bind differs from the supplied female body"
    assert np.all((module.weights > 0).sum(axis=1) <= 4)
    expected_clips = ("rest", *CLIPS)
    frames = {clip: [] for clip in expected_clips}
    cowl = hoodie_cowl(module) if label == "hoodie" else None
    leg_tubes = np.flatnonzero(module.source_points[:, 2] <= .350) if label == "shorts" else None
    tube_minimum = np.inf
    head_faces = None
    head_clearance = np.inf
    cowl_thickness = None
    if cowl:
        rest_body, original_faces = rows[0][3:]
        head_faces = original_faces[rest_body[original_faces, 2].max(axis=1) > .584]
        rear_center = module.source_points[cowl[0] & (abs(module.source_points[:, 0]) < .005), 1]
        cowl_thickness = float(np.ptp(rear_center) * 1000)
    garment_faces = module.source_faces.tolist()
    layer_faces = {name: m.source_faces.tolist() for name, m in assets.items()}
    for start in range(0, len(rows), 24):
        batch = slice(start, start + 24)
        posed = pose(module, transforms[batch])
        layer_points = {name: pose(m, transforms[batch]) for name, m in assets.items()}
        for i, (clip, frame, body_tree, body_points, _) in enumerate(rows[batch]):
            points = posed[i]
            signed, _, _, _ = fit.nearest(body_tree, points)
            tree = BVHTree.FromPolygons(points.tolist(), garment_faces, all_triangles=True)
            pairs = body_tree.overlap(tree)
            layer_counts = {}
            low, high = points.min(axis=0), points.max(axis=0)
            for name, pos in layer_points.items():
                other = pos[i]
                if np.any(other.min(axis=0) > high) or np.any(other.max(axis=0) < low):
                    layer_counts[name] = 0
                else:
                    other_tree = BVHTree.FromPolygons(other.tolist(), layer_faces[name], all_triangles=True)
                    layer_counts[name] = len(tree.overlap(other_tree))
            witness = int(signed.argmin())
            leg_result = {}
            if leg_tubes is not None:
                leg_vertex = leg_tubes[signed[leg_tubes].argmin()]
                tube_minimum = min(tube_minimum, float(signed[leg_vertex]))
                leg_result = dict(tube_min_signed_mm=float(signed[leg_vertex]) * 1000, tube_vertex=int(leg_vertex))
            if cowl and head_clearance > 0.:
                head_clearance = min(head_clearance, cowl_head_bound(points, *cowl, body_points[head_faces]))
            frames[clip].append(dict(frame=frame, inside=int((signed < 0).sum()), pairs=len(pairs),
                                     min_signed_mm=float(signed[witness]) * 1000,
                                     vertex=witness, layer_pairs=layer_counts, **leg_result))
    assert set(motion_names()) == set(CLIPS)
    clips = {}
    for label_key, values in frames.items():
        assert values
        clips[label_key] = dict(samples=len(values), peak_inside=max(v["inside"] for v in values),
            peak_pairs=max(v["pairs"] for v in values),
            min_signed_mm=min(v["min_signed_mm"] for v in values),
            peak_layer_pairs={name: max(v["layer_pairs"][name] for v in values) for name in assets},
            frames=values)
    shoe_floor = None
    floor_reference_mm = None
    if label == "boots":
        floor_reference_mm = float(fit.Module(SHIPPED["sneakers"], names).source_points[:, 2].min()) * 1000
        shoe_floor = {}
        for name, side in (("left", 1), ("right", -1)):
            points = module.source_points[module.source_points[:, 0] * side > 0]
            shoe_floor[name] = float(points[:, 2].min()) * 1000
    texture_sizes = textures(module)
    stats = dict(triangles=len(garment_faces), bytes=path.stat().st_size,
                 texture_dimensions=texture_sizes,
                 max_texture_px=max((max(s) for s in texture_sizes), default=0))
    issues = []
    if stats["triangles"] > LIMITS[label] or stats["bytes"] > fit.BYTE_LIMIT or module.glb.doc.get("textures") or texture_sizes:
        issues.append("Asset budget")
    if not all(min(size) > 0 for size in texture_sizes):
        issues.append("Texture decode")
    if any(clip["peak_inside"] or clip["peak_pairs"] or clip["min_signed_mm"] < .5 for clip in clips.values()):
        issues.append("Posed body clearance")
    if any(any(clip["peak_layer_pairs"].values()) for clip in clips.values()):
        issues.append("Shipped outfit layering")
    if cowl and (head_clearance < .0015 or not 60 <= cowl_thickness <= 100):
        issues.append("Hood thickness or conservative head clearance")
    feature = {}
    if leg_tubes is not None:
        feature["leg_tube_min_signed_mm"] = tube_minimum * 1000
        if tube_minimum < .0015:
            issues.append("Shorts leg tube clearance")
    if label in {"hoodie", "jacket"}:
        feature["unexpected_shell_boundary_edges"] = unexpected_top_boundaries(module, label)
        if feature["unexpected_shell_boundary_edges"]:
            issues.append("Unexpected opening in the torso or sleeves")
    if cowl:
        feature.update(cowl_rest_rear_thickness_mm=cowl_thickness,
                       cowl_head_separation_lower_bound_mm=float(head_clearance * 1000))
    report = dict(item=label, sha256=fit.sha(path), body_sha256=fit.sha(BODY),
                  master_sha256=fit.sha(MASTER), motion_sha256=fit.sha(MOTION),
                  layers={name: dict(file=str(SHIPPED[name].relative_to(FEMALE)), sha256=fit.sha(SHIPPED[name]))
                          for name in assets}, fps=30, frame_step=.5, floor_mm=shoe_floor, floor_reference_mm=floor_reference_mm,
                  asset=stats, features=feature, clips=clips, geometry_and_budget_pass=not issues, issues=issues)
    output.write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
    print("GATE", label, stats, issues, "floor", shoe_floor,
          "inside", max(v["peak_inside"] for v in clips.values()),
          "pairs", max(v["peak_pairs"] for v in clips.values()),
          "signed", round(min(v["min_signed_mm"] for v in clips.values()), 5),
          "layer", {n: max(v["peak_layer_pairs"][n] for v in clips.values()) for n in assets}, flush=True)
    return report


def motion_names():
    return [animation["name"] for animation in fit.Glb(MOTION).doc["animations"]]


if __name__ == "__main__":
    path, output = [Path(s).resolve() for s in arguments()]
    assert path.is_relative_to(HERE) and output.is_relative_to(HERE)
    from cache import load_scene
    data = load_scene()
    assets = {name: fit.Module(SHIPPED[name], data[0]) for name in layers_for(path.stem)}
    gate(path, output, data, assets)
