"""Reimport the exact GLB, check all motion, and render shoe/skin controls."""

from pathlib import Path
import json
import math
import struct
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fit_shoes import (DESTINATION, EXPORT, HERE, MASTER, MOTION, NAME, SIDES, SOURCE,
                       TREAD_Z, Foot, adjacency, connected, digest, frames, hull, import_objects,
                       load_master, loop_edges, measure_vertices, set_pose)

QA = DESTINATION / "qa"


def write_report(filename, result):
    (QA / filename).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


def load_export():
    scene, arm, body = load_master()
    imported = import_objects(EXPORT)
    shoes, = (o for o in imported if o.type == "MESH" and o.vertex_groups)
    shoes.parent = None
    for o in imported:
        if o != shoes:
            bpy.data.objects.remove(o, do_unlink=True)
    shoes.modifiers.clear()
    shoes.parent = arm
    shoes.modifiers.new("QA: master armature", "ARMATURE").object = arm
    set_pose(scene, arm, "rest", 1)
    return scene, arm, body, shoes


def glb_document(data):
    size, kind = struct.unpack_from("<I4s", data, 12)
    assert kind == b"JSON"
    return json.loads(data[20:20 + size]), 28 + size


def read_accessor(doc, data, start, idx, layout):
    accessor = doc["accessors"][idx]
    view = doc["bufferViews"][accessor["bufferView"]]
    base = start + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    row_size = struct.calcsize(layout)
    for row in range(accessor["count"]):
        yield struct.unpack_from(layout, data, base + row * view.get("byteStride", row_size))


def inspect_glb(shoes, arm):
    binary = EXPORT.read_bytes()
    doc, start = glb_document(binary)
    mesh, = doc["meshes"]
    skin, = doc["skins"]
    joints = [doc["nodes"][i]["name"] for i in skin["joints"]]
    base_path = HERE.parents[1] / "master" / "base_body.glb"
    master = base_path.read_bytes()
    reference, ref_start = glb_document(master)
    reference_skin, = reference["skins"]
    reference_names = [reference["nodes"][i]["name"] for i in reference_skin["joints"]]
    assert joints == reference_names
    assert list(read_accessor(doc, binary, start, skin["inverseBindMatrices"], "<16f")) == list(
        read_accessor(reference, master, ref_start, reference_skin["inverseBindMatrices"], "<16f"))
    assert len(joints) == 65 and set(joints) == set(arm.data.bones.keys())
    assert not (doc.get("animations") or doc.get("cameras"))
    triangles = max_weights = 0
    side_max = {side: 0 for side in SIDES}
    toe_peak = {side: 0 for side in SIDES}
    toe_front = {side: [] for side in SIDES}
    for primitive in mesh["primitives"]:
        attrs = primitive["attributes"]
        assert {"JOINTS_0", "WEIGHTS_0", "TEXCOORD_0"} <= attrs.keys()
        assert not {"JOINTS_1", "WEIGHTS_1"} & attrs.keys()
        wt = list(read_accessor(doc, binary, start, attrs["WEIGHTS_0"], "<4f"))
        joint_type = doc["accessors"][attrs["JOINTS_0"]]["componentType"]
        ids = list(read_accessor(doc, binary, start, attrs["JOINTS_0"], {5121: "<4B", 5123: "<4H"}[joint_type]))
        coords = list(read_accessor(doc, binary, start, attrs["POSITION"], "<3f"))
        for xyz, row, bones in zip(coords, wt, ids):
            side = "Left" if xyz[0] > 0 else "Right"
            active = [(joints[b], w) for b, w in zip(bones, row) if w > 0]
            assert active and abs(sum(w for _, w in active) - 1) < 1e-5
            assert all(name.startswith(f"mixamorig:{side}") for name, _ in active)
            side_max[side] = max(side_max[side], len(active))
            toe_weight = sum(w for name, w in active if name.endswith("ToeBase"))
            toe_peak[side] = max(toe_peak[side], toe_weight)
            if xyz[2] > .105 and xyz[1] < .021:
                toe_front[side].append(toe_weight)
            max_weights = max(max_weights, len(active))
        triangles += doc["accessors"][primitive["indices"]]["count"] // 3
    assert triangles <= 3500 and max_weights <= 4
    images = {node.image.name: list(node.image.size)
              for m in shoes.data.materials for node in m.node_tree.nodes if node.type == "TEX_IMAGE"}
    assert len(images) == len(doc["images"]) == 3
    assert all(max(size) <= 1024 for size in images.values())
    result = {
        "glb_bytes": len(binary), "blend_bytes": (DESTINATION / f"{NAME}.blend").stat().st_size,
        "glb_sha256": digest(EXPORT), "blend_sha256": digest(DESTINATION / f"{NAME}.blend"),
        "source_sha256": digest(SOURCE), "master_sha256": digest(MASTER),
        "motion_sha256": digest(MOTION), "meshes": len(doc["meshes"]), "skins": len(doc["skins"]),
        "animations": 0, "joints": len(joints), "inverse_binds_match_master_export": True,
        "triangles": triangles, "max_influences": max_weights,
        "max_influences_by_side": side_max, "toe_base_peak_by_side": toe_peak,
        "front_sole_average_toe_weight": {side: float(np.mean(weights)) for side, weights in toe_front.items()},
        "image_sizes": images, "blender": bpy.app.version_string,
    }
    write_report("asset_contract.json", result)
    print("ASSET", result, flush=True)


def signed_outline_distance(point, outline):
    edges = np.roll(outline, -1, axis=0) - outline
    offsets = point - outline
    fractions = np.clip(np.einsum("ni,ni->n", edges, offsets) /
                        np.einsum("ni,ni->n", edges, edges), 0, 1)
    dist = np.linalg.norm(offsets - fractions[:, None] * edges, axis=1).min()
    cross = edges[:, 0] * offsets[:, 1] - edges[:, 1] * offsets[:, 0]
    return float(dist if (cross >= -1e-8).all() or (cross <= 1e-8).all() else -dist)


def inspect_rest(body, arm, shoes):
    points = np.asarray([shoes.matrix_world @ v.co for v in shoes.data.vertices])
    # The imported primitive can have multiple vertices at exactly the same
    # position for a UV seam. Concentrate on connectivity after that weld.
    keys, vertices, faces = {}, [], []
    source_faces = [tuple(p.vertices) for p in shoes.data.polygons]
    for poly, tri in zip(shoes.data.polygons, source_faces):
        row = []
        for i in tri:
            key = (poly.material_index, *points[i])
            if key not in keys:
                keys[key] = len(vertices)
                vertices.append(points[i])
            row.append(keys[key])
        faces.append(tuple(row))
    neighbors = adjacency(len(vertices), faces)
    unassigned = set(range(len(vertices)))
    components = []
    membership = {}
    while unassigned:
        group = connected(min(unassigned), neighbors, unassigned)
        for v in group:
            membership[v] = len(components)
        components.append(group)
        unassigned.difference_update(group)
    shells = [[i for i, f in enumerate(faces) if membership[f[0]] == n]
              for n in range(len(components))]
    body_tree = BVHTree.FromPolygons(points, source_faces, all_triangles=True)
    topology = [set(face) for face in faces]
    self_pairs = sum(a < b and membership[faces[a][0]] == membership[faces[b][0]]
                     and not topology[a].intersection(topology[b])
                     for a, b in body_tree.overlap(body_tree))
    rest = {"glb_sha256": digest(EXPORT), "mesh_components": len(components),
            "nonadjacent_pairs_within_components": self_pairs, "shoes": {}}
    for sign, side in zip((1, -1), SIDES):
        foot = Foot(body, arm, side)
        side_mask = points[:, 0] * sign > 0
        sole_ids = next(i for i, part in enumerate(components)
                        if any(vertices[v][0] * sign > 0 and vertices[v][2] < TREAD_Z + 1e-5 for v in part))
        sole_part = components[sole_ids]
        sole_points = np.asarray([vertices[v] for v in sorted(sole_part)])
        sole_faces = [source_faces[i] for i in shells[sole_ids]]
        edge_map = loop_edges([faces[i] for i in shells[sole_ids]])
        bad = sum(len(uses) != 2 or uses[0] != uses[1][::-1] for uses in edge_map.values())
        tread = sole_points[:, 2] <= TREAD_Z + 1e-5
        sole_outline = hull(sole_points[:, :2])
        tread_outline = hull(sole_points[tread, :2])
        upper = side_mask & (points[:, 2] > .022)
        distances, _ = measure_vertices(foot.tree, points[upper])
        sole_tree = BVHTree.FromPolygons(points, sole_faces, all_triangles=True)
        tests = misses = 0
        for a, b in zip(foot.outline, np.roll(foot.outline, -1, axis=0)):
            for k in range(count := max(1, math.ceil(np.linalg.norm(b - a) / .003))):
                p = a + (b - a) * k / count
                for theta in np.arange(24) * math.tau / 24:
                    x, y = p + .003 * np.array([math.cos(theta), math.sin(theta)])
                    hit, _, _, _ = sole_tree.ray_cast(Vector((x, y, -.08)), Vector((0, 0, 1)), .15)
                    tests += 1
                    misses += hit is None
        rest["shoes"][side] = {
            "sole_length_m": float(np.ptp(sole_points[:, 1])),
            "foot_length_m": float(np.ptp(foot.outline[:, 1])),
            "projected_sole_hull_overhang_m": min(signed_outline_distance(p, sole_outline) for p in foot.outline),
            "overhang_3mm_rays": tests, "overhang_3mm_misses": misses,
            "closed_sole_open_or_inconsistent_edges": bad,
            "min_flat_tread_overhang_m": min(signed_outline_distance(p, tread_outline) for p in foot.outline),
            "sole_min_z_m": float(sole_points[:, 2].min()), "sole_max_z_m": float(sole_points[:, 2].max()),
            "flat_tread_vertices": int(tread.sum()),
            "upper_clearance_m_percentiles_0_10_50_90_100": np.percentile(distances, (0, 10, 50, 90, 100)).tolist(),
        }
    write_report("sole_geometry.json", rest)
    print("SOLE", rest, flush=True)


def dense(scene, arm, body, shoes):
    shoe_faces = [face.vertices[:] for face in shoes.data.polygons]
    body_faces = [face.vertices[:] for face in body.data.polygons]
    shoe_coords = np.asarray([v.co for v in shoes.data.vertices])
    sole_ids = [(shoe_coords[:, 0] * sign > 0) & (shoe_coords[:, 2] <= .019) for sign in (1, -1)]
    results, best_lifts = {}, {}
    for name, frame in frames():
        set_pose(scene, arm, name, frame)
        graph = bpy.context.evaluated_depsgraph_get()
        b, s = (obj.evaluated_get(graph) for obj in (body, shoes))
        bcoords, scoords = [np.asarray([obj.matrix_world @ v.co for v in obj.data.vertices]) for obj in (b, s)]
        tree = BVHTree.FromPolygons(bcoords, body_faces, all_triangles=True)
        shoe_tree = BVHTree.FromPolygons(scoords, shoe_faces, all_triangles=True)
        d, _ = measure_vertices(tree, scoords)
        measures = results.setdefault(name, {"samples": 0, "inside": 0, "triangle_pairs": 0,
                                              "minimum_signed_m": math.inf, "worst_frame": None})
        measures["samples"] += 1
        measures["inside"] = max(measures["inside"], int((d < 0).sum()))
        measures["triangle_pairs"] = max(measures["triangle_pairs"], len(tree.overlap(shoe_tree)))
        if d.min() < measures["minimum_signed_m"]:
            measures["minimum_signed_m"] = float(d.min())
            measures["worst_frame"] = frame
        if name not in ("walk", "run") or frame != int(frame):
            continue
        for side, mask in zip(SIDES, sole_ids):
            height = float(scoords[mask, 2].min())
            if height > best_lifts.get((name, side), (-math.inf, None))[0]:
                best_lifts[name, side] = (height, int(frame))
    lifts = [{"clip": clip, "side": side, "frame": frame, "lowest_sole_point_z_m": z}
             for (clip, side), (z, frame) in best_lifts.items()]
    for name, item in results.items():
        print("DENSE RESULT", name, item, flush=True)
    write_report("dense_check.json", {"glb_sha256": digest(EXPORT), "results": results, "peak_lifts": lifts})
    return lifts


def render_setup(scene, size, samples):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.resolution_percentage = 100
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("Studio environment")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (.85, .90, 1.0, 1.0)
    bg.inputs["Strength"].default_value = .55
    camera = bpy.data.objects.new("Shoe QA camera", bpy.data.cameras.new("Shoe QA camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    return camera


def aim(camera, center, offset, scale, up=None):
    camera.location = center + offset
    camera.data.ortho_scale = scale
    if up is None:
        camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
    else:
        from mathutils import Matrix
        outward = offset.normalized()
        right = up.cross(outward).normalized()
        camera.rotation_euler = Matrix((right, outward.cross(right), outward)).transposed().to_euler()


def capture(scene, path, pixels=False):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if pixels:
        image = bpy.data.images.load(str(path), check_existing=False)
        data = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(data)
        bpy.data.images.remove(image)
        return data.reshape(scene.render.resolution_y, scene.render.resolution_x, 4)[::-1]


def preview(scene, arm, body):
    camera = render_setup(scene, (780, 600), 18)
    scene.cycles.use_denoising = True
    set_pose(scene, arm, "rest", 1)
    body.hide_render = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -.65
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, TREAD_Z - .00015))
    ground = bpy.context.object
    white = bpy.data.materials.new("White studio floor")
    white.use_nodes = True
    white.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.86, .86, .86, 1)
    ground.data.materials.append(white)
    for name, location, energy, size in (
        ("Softbox", (.20, -.45, .55), 34, .65),
        ("Fill", (-.51, -.20, .38), 18, .55),
        ("Rim", (.18, .42, .48), 22, .65),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, light)
        obj.location = location
        obj.rotation_euler = (-obj.location).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(obj)
    center = Vector((0, -.021, .036))
    for name, offset in (("preview", (.36, -.59, .36)), ("rest_side", (.65, -.06, .19))):
        aim(camera, center, Vector(offset), .43)
        capture(scene, QA / f"{name}.png")


def filled_silhouette(opaque):
    border = np.pad(opaque, 1)
    outside = bytearray((~border).ravel())
    remaining = [0]
    exterior = np.zeros(border.size, dtype=bool)
    exterior[0] = True
    outside[0] = 0
    stride = border.shape[1]
    for index in remaining:
        row, col = divmod(index, stride)
        for neighbor in (index - 1 if col else 0, index + 1 if col + 1 < stride else 0,
                         index - stride if row else 0, index + stride if row + 1 < border.shape[0] else 0):
            if outside[neighbor]:
                outside[neighbor] = 0
                exterior[neighbor] = True
                remaining.append(neighbor)
    return ~exterior.reshape(border.shape)[1:-1, 1:-1]


def expand(mask, radius):
    result = np.zeros_like(mask)
    for row in range(-radius, radius + 1):
        for col in range(-radius, radius + 1):
            result |= np.roll(mask, (row, col), axis=(0, 1))
    return result


def flat_projection(points, faces, tags, camera, width, height):
    """Rasterize Blender's evaluated triangles by orthographic depth at pixel centers."""
    world_to_camera = np.asarray(camera.matrix_world.inverted())
    local = points @ world_to_camera[:3, :3].T + world_to_camera[:3, 3]
    pixels_per_meter = max(width, height) / camera.data.ortho_scale
    u = width / 2 + local[:, 0] * pixels_per_meter - .5
    v = height / 2 - local[:, 1] * pixels_per_meter - .5
    xy = np.column_stack((u, v))
    depth = -local[:, 2]
    buffer = np.full((height, width), np.inf)
    labels = np.zeros((height, width), dtype=np.uint8)
    for vertices, tag in zip(faces, tags):
        verts = xy[vertices]
        lo_x, lo_y = np.maximum(0, np.ceil(verts.min(axis=0)).astype(int))
        hi_x, hi_y = np.minimum((width - 1, height - 1), np.floor(verts.max(axis=0)).astype(int))
        if lo_x > hi_x or lo_y > hi_y:
            continue
        (ax, ay), (bx, by), (cx, cy) = verts
        area = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(area) < 1e-12:
            continue
        y, x = np.ogrid[lo_y:hi_y + 1, lo_x:hi_x + 1]
        f0 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / area
        f1 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / area
        f2 = 1.0 - f0 - f1
        eps = -1e-10
        za, zb, zc = depth[vertices]
        z = f0 * za + f1 * zb + f2 * zc
        row = slice(lo_y, hi_y + 1)
        col = slice(lo_x, hi_x + 1)
        best = buffer[row, col]
        keep = (f0 >= eps) & (f1 >= eps) & (f2 >= eps) & (z > 0) & (z < best)
        best[keep] = z[keep]
        labels[row, col][keep] = tag
    return buffer, labels


def save_mask(path, labels):
    colors = np.asarray(((0, 0, 0, 0), (1, 0, 0, 1), (0, 1, 0, 1),
                         (0, 0, 1, 1), (0, 1, 0, 1)), dtype=np.float32)
    h, w = labels.shape
    image = bpy.data.images.new(path.stem, width=w, height=h, alpha=True)
    image.pixels.foreach_set(colors[labels[::-1]].ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def skin_test(scene, arm, body, shoes, lifts):
    """Verify visible green pixels with shoes-on, shoes-only and body-only passes."""
    cases = [("walk", 19, "Left"), ("walk", 23, "Left"),
             ("run", 4, "Right"), ("run", 12, "Right")]
    cases += [(row["clip"], row["frame"], row["side"]) for row in lifts]
    camera = bpy.data.objects.new("Shoe mask camera", bpy.data.cameras.new("Shoe mask camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    face_centers = np.asarray([p.center[:] for p in shoes.data.polygons])
    closed_sole = [p.material_index for p in shoes.data.polygons]
    sole_slots = {i for i, mat in enumerate(shoes.data.materials) if "Closed Sole" in mat.name}
    if sole_slots:
        tags_shoes = np.where(np.isin(closed_sole, list(sole_slots)), 3, 1)
    else:
        tags_shoes = np.where(face_centers[:, 2] < .021, 3, 1)
    body_rest = np.asarray([p.center[:] for p in body.data.polygons])
    shoe_faces = np.asarray([p.vertices[:] for p in shoes.data.polygons])
    body_faces = np.asarray([p.vertices[:] for p in body.data.polygons])
    rest = np.asarray([v.co[:] for v in shoes.data.vertices])
    measurements = {}
    width, height = 700, 590
    for clip, frame, side in sorted(set(cases)):
        set_pose(scene, arm, clip, frame)
        sign = 1 if side == "Left" else -1
        focused_faces = face_centers[:, 0] * sign > 0
        is_target_foot = (body_rest[:, 2] <= .065) & (body_rest[:, 0] * sign > 0)
        tags_body = np.where(is_target_foot, 4, 2)
        graph = bpy.context.evaluated_depsgraph_get()
        foot_objs = [obj.evaluated_get(graph) for obj in (shoes, body)]
        shoe_points, body_points = [np.asarray([obj.matrix_world @ v.co for v in obj.data.vertices])
                                    for obj in foot_objs]
        center = Vector(shoe_points[(rest[:, 0] * sign > 0) & (rest[:, 2] < .018)].mean(axis=0))
        bone = arm.pose.bones[f"mixamorig:{side}Foot"]
        deformation = (bone.matrix @ bone.bone.matrix_local.inverted()).to_3x3()
        camera_specs = {
            "below": (deformation @ Vector((.025 * sign, -.10, -.65)), deformation @ Vector((0, -1, 0))),
            "side": (deformation @ Vector((.64 * sign, -.022, -.008)), deformation @ Vector((0, 0, 1))),
        }
        for view, (offset, up) in camera_specs.items():
            name = f"{clip}_{frame:02d}_{side.lower()}_{view}"
            aim(camera, center, offset, .315, up)
            bpy.context.view_layer.update()
            shoe_z, shoe_mask = flat_projection(
                shoe_points, shoe_faces[focused_faces], tags_shoes[focused_faces], camera, width, height)
            body_z, control = flat_projection(body_points, body_faces, tags_body, camera, width, height)
            combined = np.where(body_z < shoe_z, control, shoe_mask)
            cover = shoe_mask != 0
            outline = filled_silhouette(cover)
            green = (combined == 2) | (combined == 4)
            foot_green = combined == 4
            blue = shoe_mask == 3
            # Through-holes use a filled silhouette of the lifted shoe alone.
            # The outside band tests its plantar skin. The head, calf and
            # other foot can project behind this band's background.
            band = expand(blue, 2) & ~outline
            side_zone = blue | ((outline & ~cover) & expand(blue, 2))
            roi = side_zone if view == "side" else outline
            edge_skin = band & foot_green
            through_skin = roi & green
            evidence = {}
            for suffix, pixels in (("silhouette", shoe_mask), ("skin", combined), ("control", control)):
                path = QA / f"{name}_{suffix}.png"
                save_mask(path, pixels)
                evidence[path.name] = digest(path)
            measurements[name] = {
                "skin_pixels": int((through_skin | edge_skin).sum()),
                "skin_pixels_inside_full_shoe_outline": int((outline & green).sum()),
                "skin_pixels_in_sole_region": int((side_zone & green).sum()),
                "foot_pixels_immediately_outside_sole": int(edge_skin.sum()),
                "body_only_control_pixels": int((roi & (control == 4)).sum()),
                "region_pixels": int(roi.sum()), "camera_location": list(camera.location),
                "camera_rotation": list(camera.rotation_euler), "ortho_scale": camera.data.ortho_scale,
                "png_sha256": evidence,
            }
            print("SKIN RESULT", name, measurements[name]["skin_pixels"],
                  "control", measurements[name]["body_only_control_pixels"], flush=True)
    write_report("skin_check.json", {
        "glb_sha256": digest(EXPORT), "renderer": "Blender evaluated mesh, orthographic depth raster",
        "resolution": [width, height], "total_skin_pixels": sum(row["skin_pixels"] for row in measurements.values()),
        "views": measurements,
    })
    assert all(v["skin_pixels"] == 0 and v["body_only_control_pixels"] > 0
               for v in measurements.values()), "Skin-pixel gate failed"


def main():
    QA.mkdir(exist_ok=True)
    scene, arm, body, shoes = load_export()
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--preview" in args:
        preview(scene, arm, body)
    elif "--skin" in args:
        payload = json.loads((QA / "dense_check.json").read_text())
        assert payload["glb_sha256"] == digest(EXPORT)
        skin_test(scene, arm, body, shoes, payload["peak_lifts"])
    else:
        inspect_glb(shoes, arm)
        inspect_rest(body, arm, shoes)
        dense(scene, arm, body, shoes)


if __name__ == "__main__":
    main()
