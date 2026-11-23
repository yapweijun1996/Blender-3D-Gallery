"""Check the final GLB's skin against the female body and shipped outfit layers."""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

import fit_module as fit
from common import BODY, CLIPS, FEMALE, HERE, MASTER, MOTION, arguments

SHIPPED = {
    "tshirt": FEMALE / "round2/female-tshirt-v2.glb",
    "jeans": FEMALE / "round3/female-jeans-v3.glb",
    "sneakers": FEMALE / "female-sneakers.glb",
}
LIMITS = {
    "shoes-boots": 3500, "bottom-skirt": 6000, "bottom-shorts": 6000,
    "shoes-sandals": 3500, "shoes-slipons": 3500,
    "shoes-hightop": 3500, "hair-ponytail": 3000,
}


def layers_for(label):
    if label.startswith("bottom-"):
        return ("tshirt", "sneakers")
    if label.startswith("shoes-"):
        return ("tshirt", "jeans")
    return ("tshirt", "jeans", "sneakers")


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


def gate(path, output, data, assets):
    names, _, female, rows, transforms = data
    label = path.stem
    module = fit.Module(path, names)
    assert bound_to_body(module, fit.Glb(BODY)), "Exported bind differs from the supplied female body"
    expected_clips = ("rest", *CLIPS)
    frames = {clip: [] for clip in expected_clips}
    garment_faces = module.source_faces.tolist()
    layer_faces = {name: m.source_faces.tolist() for name, m in assets.items()}
    for start in range(0, len(rows), 24):
        batch = slice(start, start + 24)
        posed = pose(module, transforms[batch])
        layer_points = {name: pose(m, transforms[batch]) for name, m in assets.items()}
        for i, (clip, frame, body_tree, _, _) in enumerate(rows[batch]):
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
            frames[clip].append(dict(frame=frame, inside=int((signed < 0).sum()), pairs=len(pairs),
                                     min_signed_mm=float(signed[witness]) * 1000,
                                     vertex=witness, layer_pairs=layer_counts))
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
    if label.startswith("shoes-"):
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
    if stats["triangles"] > LIMITS[label] or stats["bytes"] > fit.BYTE_LIMIT or stats["max_texture_px"] > 1024:
        issues.append("Asset budget")
    if not all(min(size) > 0 for size in texture_sizes):
        issues.append("Texture decode")
    if any(clip["peak_inside"] or clip["peak_pairs"] or clip["min_signed_mm"] < .5 for clip in clips.values()):
        issues.append("Posed body clearance")
    if any(any(clip["peak_layer_pairs"].values()) for clip in clips.values()):
        issues.append("Shipped outfit layering")
    if shoe_floor and any(abs(value - floor_reference_mm) > .5 for value in shoe_floor.values()):
        issues.append("Rest sole floor contact")
    report = dict(item=label, sha256=fit.sha(path), body_sha256=fit.sha(BODY),
                  master_sha256=fit.sha(MASTER), motion_sha256=fit.sha(MOTION),
                  layers={name: dict(file=str(SHIPPED[name].relative_to(FEMALE)), sha256=fit.sha(SHIPPED[name]))
                          for name in assets}, fps=30, frame_step=.5, floor_mm=shoe_floor, floor_reference_mm=floor_reference_mm,
                  asset=stats, clips=clips, geometry_and_budget_pass=not issues, issues=issues)
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
    data = fit.cache_scene()
    assets = {name: fit.Module(SHIPPED[name], data[0]) for name in layers_for(path.stem)}
    gate(path, output, data, assets)
