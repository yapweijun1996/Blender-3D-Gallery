"""Reimport the fitted GLB and run the motion and skin-pixel QA gates."""

from collections import Counter, deque
from contextlib import redirect_stdout
import json
import math
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fit_shoes import (BLEND, CLIPS, EXPORT, FootSurface, HERE, MASTER, MOTION, QA_MARGIN, REFERENCE, SOURCE,
                       digest, import_motion, motion_samples, set_action)

QA_ROOT = HERE

WORKBENCH = ("sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
             "sc.display.shading.color_type='MATERIAL'")
CPU = """
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 6
sc.cycles.use_denoising = True
sc.render.image_settings.file_format = 'PNG'
sc.render.resolution_percentage = 100
sc.world = bpy.data.worlds.new('Checker studio')
sc.world.use_nodes = True
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.86, .89, .96, 1)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
"""


def report(name, content):
    (QA_ROOT / f"{name}.json").write_text(json.dumps(content, indent=2) + "\n")


def run_supplied_checkers(render):
    for checker in ("motion_check", "motion_check_tri"):
        script = HERE / "work" / f"{checker}.py"
        source = script.read_text()
        if render and checker == "motion_check":
            assert source.count(WORKBENCH) == 1
            source = source.replace(WORKBENCH, CPU, 1)
        else:
            source = source[:source.index(WORKBENCH)] + source[source.rindex("json.dump("):]
        with TemporaryDirectory(prefix=".checker-", dir=QA_ROOT) as folder:
            original_args = sys.argv
            sys.argv = [str(script), "--", str(MASTER), str(MOTION), str(EXPORT), folder]
            try:
                with (QA_ROOT / f"{checker}.txt").open("w") as log, redirect_stdout(log):
                    exec(compile(source, str(script), "exec"), {"__name__": "__main__"})
            finally:
                sys.argv = original_args
            (Path(folder) / "motion_check.json").replace(QA_ROOT / f"{checker}.json")
            for png in sorted(Path(folder).glob("*.png")):
                if checker == "motion_check":
                    png.replace(QA_ROOT / png.name)
        data = json.loads((QA_ROOT / f"{checker}.json").read_text())
        ok = all(data[name][0] == 0 and data[name][1] >= QA_MARGIN for name in ("rest", *CLIPS))
        print("CHECKER", checker, "PASS" if ok else "FAIL", data, flush=True)


def contract():
    data = EXPORT.read_bytes()
    json_size, = struct.unpack_from("<I", data, 12)
    gltf = json.loads(data[20:20 + json_size])
    bin_start = 28 + json_size

    def accessor_bytes(idx):
        a = gltf["accessors"][idx]
        v = gltf["bufferViews"][a["bufferView"]]
        start = bin_start + v.get("byteOffset", 0) + a.get("byteOffset", 0)
        dtype = {5126: "<f4", 5123: "<u2", 5121: "u1", 5125: "<u4"}[a["componentType"]]
        width = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
        return np.ndarray((a["count"], width), dtype=dtype, buffer=data, offset=start,
                          strides=(v.get("byteStride", np.dtype(dtype).itemsize * width),
                                   np.dtype(dtype).itemsize))

    mesh, = gltf["meshes"]
    skin, = gltf["skins"]
    joints = [gltf["nodes"][i]["name"] for i in skin["joints"]]
    assert len(joints) == 65 and not gltf.get("animations")
    assert sum("mesh" in node for node in gltf["nodes"]) == 1
    assert all(not {"JOINTS_1", "WEIGHTS_1"}.intersection(p["attributes"]) for p in mesh["primitives"])
    by_side = Counter()
    influences = 0
    triangles = 0
    for p in mesh["primitives"]:
        attrs = p["attributes"]
        coords = accessor_bytes(attrs["POSITION"])
        w = accessor_bytes(attrs["WEIGHTS_0"])
        j = accessor_bytes(attrs["JOINTS_0"])
        assert np.max(abs(w.sum(1) - 1)) <= 1e-5
        for x, weights, js in zip(coords[:, 0], w, j):
            side = "Left" if x > 0 else "Right"
            active = [joints[i] for i, weight in zip(js, weights) if weight > 0]
            assert active and all(name.startswith("mixamorig:" + side) for name in active)
            by_side[side] += 1
            influences = max(influences, len(active))
        triangles += gltf["accessors"][p["indices"]]["count"] // 3
    assert triangles <= 3500 and influences <= 4
    legacy = HERE.parents[1] / "shoes-sol/round3/shoes_sneaker_v3.glb"
    older = legacy.read_bytes()
    older_size, = struct.unpack_from("<I", older, 12)
    old = json.loads(older[20:20 + older_size])
    old_skin, = old["skins"]
    assert [old["nodes"][j]["name"] for j in old_skin["joints"]] == joints
    a = old["accessors"][old_skin["inverseBindMatrices"]]
    v = old["bufferViews"][a["bufferView"]]
    start = 28 + older_size + v.get("byteOffset", 0) + a.get("byteOffset", 0)
    assert np.array_equal(accessor_bytes(skin["inverseBindMatrices"]),
                          np.frombuffer(older, dtype="<f4", offset=start, count=65 * 16).reshape(65, 16))
    return {
        "export_sha256": digest(EXPORT), "blend_sha256": digest(BLEND),
        "master_sha256": digest(MASTER), "motion_sha256": digest(MOTION),
        "source_sha256": digest(SOURCE), "reference_sha256": digest(REFERENCE),
        "blender": bpy.app.version_string, "triangles": triangles, "joints": len(joints),
        "max_influences": influences, "export_vertices_by_side": dict(by_side),
        "mesh_count": 1, "animations": 0, "images": len(gltf.get("images", [])),
        "glb_bytes": len(data), "blend_bytes": BLEND.stat().st_size,
        "checker_code_sha256": {name: digest(HERE / "work" / f"{name}.py")
                                for name in ("motion_check", "motion_check_tri")},
    }


def on_master():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    old = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(EXPORT), merge_vertices=True)
    imported = set(scene.objects) - old
    shoes, = (obj for obj in imported if obj.type == "MESH" and obj.vertex_groups)
    shoes.parent = None
    for obj in imported - {shoes}:
        bpy.data.objects.remove(obj, do_unlink=True)
    shoes.modifiers.clear()
    shoes.parent = arm
    shoes.modifiers.new("Master Skin", "ARMATURE").object = arm
    actions = import_motion(scene)
    set_action(arm, scene, None)
    return scene, body, arm, shoes, actions


def posed(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    values = np.empty(len(evaluated.data.vertices) * 3, dtype=np.float32)
    evaluated.data.vertices.foreach_get("co", values)
    return values.reshape(-1, 3)


def dense_check(scene, body, arm, shoes, actions):
    body_faces = [p.vertices[:] for p in body.data.polygons]
    shoe_faces = [p.vertices[:] for p in shoes.data.polygons]
    result = {}
    for action in (None, *actions):
        name = action.name if action else "rest"
        set_action(arm, scene, action)
        stat = {"samples": 0, "max_vertices_inside": 0, "max_overlap_pairs": 0,
                "minimum_signed_distance_m": math.inf, "minimum_distance_frame": None}
        for frame, fraction in motion_samples(action):
            scene.frame_set(frame, subframe=fraction)
            b, s = posed(body), posed(shoes)
            bt = BVHTree.FromPolygons(b.tolist(), body_faces, all_triangles=True)
            st = BVHTree.FromPolygons(s.tolist(), shoe_faces, all_triangles=True)
            inside, smallest = 0, math.inf
            for v in s:
                point = Vector(v)
                hit, normal, _, _ = bt.find_nearest(point)
                signed = (point - hit).dot(normal)
                inside += signed < 0
                smallest = min(smallest, signed)
            stat["max_vertices_inside"] = max(inside, stat["max_vertices_inside"])
            stat["max_overlap_pairs"] = max(len(bt.overlap(st)), stat["max_overlap_pairs"])
            stat["samples"] += 1
            if smallest < stat["minimum_signed_distance_m"]:
                stat["minimum_signed_distance_m"] = smallest
                stat["minimum_distance_frame"] = frame + fraction
        result[name] = stat
        print("DENSE", name, stat, flush=True)
    report("dense_check", {"export_sha256": digest(EXPORT), "clips": result})


def rest_geometry(body, shoes):
    """Measure the watertight fitted surface and projected 3 mm sole coverage."""
    bm = bmesh.new()
    bm.from_mesh(shoes.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    coords = [v.co.copy() for v in bm.verts]
    polygons = [tuple(v.index for v in face.verts) for face in bm.faces]
    shell = BVHTree.FromPolygons(coords, polygons, all_triangles=True)
    by_side = {}
    for sign, side in ((1, "Left"), (-1, "Right")):
        foot = FootSurface(body, side, sign)
        sole, gap = [], []
        for face in bm.faces:
            center = face.calc_center_median()
            if sign * center.x <= 0:
                continue
            if "Sole" in shoes.data.materials[face.material_index].name:
                sole.append(tuple(v.index for v in face.verts))
            elif center.z > 0.012:
                hit, _, _, _ = foot.tree.find_nearest(center)
                delta = hit - center
                if delta.length < 0.025 and face.normal.dot(delta.normalized()) > 0.75:
                    gap.append(delta.length * 1000)
        sole_tree = BVHTree.FromPolygons(coords, sole, all_triangles=True)
        missed, total = 0, 0
        for i, a in enumerate(foot.footprint):
            b = foot.footprint[(i + 1) % len(foot.footprint)]
            for point in (a, 0.5 * (a + b)):
                for j in range(48):
                    theta = math.tau * j / 48
                    x, y = point + 0.003 * np.array((math.cos(theta), math.sin(theta)))
                    hit, _, _, _ = sole_tree.ray_cast(Vector((x, y, -0.06)), Vector((0, 0, 1)), 0.13)
                    missed += hit is None
                    total += 1
        by_side[side] = {
            "3mm_outline_samples": total, "3mm_outline_uncovered": missed,
            "inner_upper_samples": len(gap),
            "inner_upper_gap_mm_10th_50th_90th_percentiles": np.percentile(gap, (10, 50, 90)).tolist(),
        }
    result = {"export_sha256": digest(EXPORT), "open_edges": sum(edge.is_boundary for edge in bm.edges),
              "nonmanifold_edges": sum(not edge.is_manifold for edge in bm.edges),
              "inconsistent_edges": sum(not edge.is_contiguous for edge in bm.edges),
              "rest_nonadjacent_shoe_self_overlap_pairs": sum(
                  i < j and not set(polygons[i]).intersection(polygons[j]) for i, j in shell.overlap(shell)
              ), "sides": by_side}
    bm.free()
    report("rest_geometry", result)
    print("REST_GEOMETRY", result, flush=True)


def aim(obj, at):
    obj.rotation_euler = (Vector(at) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_studio(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 10
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = 720
    scene.render.resolution_y = 600
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("Soft studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.78, 0.83, 0.93, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.28
    scene.world = world
    for name, location, energy, size in (
        ("Key", (0.24, -0.52, 0.68), 13, 0.55),
        ("Fill", (-0.35, -0.20, 0.40), 4.5, 0.47),
        ("Rim", (0.35, 0.45, 0.63), 12, 0.47),
        ("Tread fill", (0.15, -0.13, -0.42), 2.6, 0.46),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy
        light.shape = "DISK"
        light.size = size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = location
        aim(obj, (0, 0, 0.08))
    cam = bpy.data.cameras.new("Fit QA")
    camera = bpy.data.objects.new("Fit QA", cam)
    scene.collection.objects.link(camera)
    scene.camera = camera
    cam.type = "ORTHO"
    return camera


def render_png(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def previews(scene, body, arm, shoes):
    camera = scene.camera
    set_action(arm, scene, None)
    camera.data.ortho_scale = 0.42
    vertices = posed(shoes)
    z = float(vertices[:, 2].min())
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, z - 0.0004))
    plane = bpy.context.object
    floor = bpy.data.materials.new("Studio background")
    floor.diffuse_color = (0.82, 0.85, 0.9, 1)
    plane.data.materials.append(floor)
    target = Vector((0.0, -0.017, 0.031))
    body.hide_render = True
    camera.location = target + Vector((0.36, -0.68, 0.40))
    aim(camera, target)
    render_png(scene, QA_ROOT / "sandals_preview.png")
    body.hide_render = False
    plane.hide_render = True
    for name, delta in (("rest_fit", (0.36, -0.68, 0.30)), ("rest_side", (0.78, -0.065, 0.022))):
        camera.location = target + Vector(delta)
        aim(camera, target)
        render_png(scene, QA_ROOT / f"{name}.png")
    # The isolated sole geometry is useful for checking the repaired source hole.
    body.hide_render = True
    camera.location = target + Vector((0.015, -0.03, -0.55))
    aim(camera, target)
    render_png(scene, QA_ROOT / "rest_tread.png")
    body.hide_render = False


def emission(name, color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    node = tree.nodes.new("ShaderNodeEmission")
    node.inputs["Color"].default_value = (*color, 1)
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(node.outputs[0], output.inputs["Surface"])
    return material


def png_pixels(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        values = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(values)
        return values.reshape(image.size[1], image.size[0], 4)
    finally:
        bpy.data.images.remove(image)


def fill_holes(mask):
    """Flood only the outer background so enclosed holes remain testable."""
    blocked = np.pad(mask, 1, constant_values=False)
    height, width = blocked.shape
    outer = bytearray((~blocked).ravel())
    queue = deque((0,))
    outer[0] = 0
    exterior = np.zeros(height * width, dtype=bool)
    while queue:
        i = queue.pop()
        exterior[i] = True
        for j in (i - 1 if i % width else 0,
                  i + 1 if i % width != width - 1 else 0,
                  i - width if i >= width else 0,
                  i + width if i < (height - 1) * width else 0):
            if outer[j]:
                outer[j] = 0
                queue.append(j)
    return ~exterior.reshape(height, width)[1:-1, 1:-1]


def camera_foot_basis(arm, side):
    n = f"mixamorig:{side}Foot"
    return (arm.pose.bones[n].matrix @ arm.data.bones[n].matrix_local.inverted()).to_3x3()


def aim_foot_view(camera, center, up):
    back = (camera.location - center).normalized()
    right = up.cross(back).normalized()
    vertical = back.cross(right)
    camera.rotation_euler = Matrix((right, vertical, back)).transposed().to_euler()


def skin_check(scene, body, arm, shoes):
    out = QA_ROOT / "skin"
    out.mkdir(exist_ok=True)
    camera = scene.camera
    camera.data.ortho_scale = 0.28
    scene.render.resolution_x = 640
    scene.render.resolution_y = 520
    scene.render.film_transparent = True
    rest = np.array([v.co[:] for v in shoes.data.vertices])
    sole_faces = [(p.vertices[:], 1 if rest[p.vertices[0], 0] > 0 else -1)
                  for p in shoes.data.polygons if "Sole" in shoes.data.materials[p.material_index].name]
    by_side = {sign: [i for i in sorted({v for f, side in sole_faces if side == sign for v in f})]
               for sign in (1, -1)}
    original_body = list(body.data.materials)
    original_shoes = list(shoes.data.materials)
    green = emission("Body QA green", (0, 1, 0))
    magenta = emission("Other body QA magenta", (1, 0, 1))
    red = emission("Strap QA red", (1, 0, 0))
    blue = emission("Sole QA blue", (0, 0, 1))
    world = scene.world
    black = bpy.data.worlds.new("Mask black")
    black.color = (0, 0, 0)

    body_faces = [(polygon.index, polygon.material_index,
                   1 if all(body.data.vertices[i].co.x > 0 for i in polygon.vertices)
                   else -1 if all(body.data.vertices[i].co.x < 0 for i in polygon.vertices) else 0,
                   max(body.data.vertices[i].co.z for i in polygon.vertices))
                  for polygon in body.data.polygons]
    green_slot = len(body.data.materials)
    body.data.materials.append(green)
    magenta_slot = len(body.data.materials)
    body.data.materials.append(magenta)

    def modes(flat, sign):
        scene.world = black if flat else world
        scene.view_settings.view_transform = "Standard" if flat else "AgX"
        scene.cycles.samples = 8 if flat else 10
        scene.cycles.use_denoising = not flat
        scene.cycles.use_adaptive_sampling = not flat
        scene.cycles.max_bounces = 0 if flat else 8
        scene.render.image_settings.color_mode = "RGBA"
        for i, original, side, height in body_faces:
            # Tag the target foot green. The rest of the body stays in the
            # render and uses magenta to identify unrelated screen overlap.
            body.data.polygons[i].material_index = (
                green_slot if side == sign and height < 0.080 else magenta_slot
            ) if flat else original
        for i, material in enumerate(original_shoes):
            shoes.data.materials[i] = (blue if "Sole" in material.name else red) if flat else material

    result = {}
    cases = (("walk", 19, 1), ("walk", 23, 1), ("run", 4, -1), ("run", 12, -1))
    for name, frame, sign in cases:
        set_action(arm, scene, bpy.data.actions[name])
        scene.frame_set(frame)
        coords = posed(shoes)
        side = "Left" if sign > 0 else "Right"
        sole_points = coords[by_side[sign]]
        center = Vector((sole_points.min(0) + sole_points.max(0)) * 0.5)
        lateral = rest[by_side[sign], 0] * sign
        midline = 0.5 * (lateral.min() + lateral.max())
        basis = camera_foot_basis(arm, side)
        for view, local in (("below", (0.06, 0.06, -1.0)), ("side", (sign, -0.12, -0.15))):
            stem = f"{name}_{frame}_{side.lower()}_{view}"
            # A low side camera looks across the open toe and heel. Its
            # foreground cheek wall is the occluder. A distant lip can
            # project behind exposed skin even when the near wall is sound.
            faces = [f for f, tag in sole_faces if tag == sign and
                     (view == "below" or (rest[list(f), 0] * sign).mean() >= midline)]
            sole_mesh = bpy.data.meshes.new("Sole QA")
            sole_mesh.from_pydata(coords.tolist(), [], faces)
            sole = bpy.data.objects.new("Sole QA", sole_mesh)
            scene.collection.objects.link(sole)
            sole.data.materials.append(blue)
            camera.location = center + basis @ Vector(local) * 0.66
            camera_up = Vector((0, 1, 0) if view == "below" else (0, 0, 1))
            aim_foot_view(camera, center, basis @ camera_up)
            modes(False, sign)
            sole.hide_render = True
            render_png(scene, out / f"{stem}.png")
            modes(True, sign)
            skin_path = out / f"{stem}_skin.png"
            render_png(scene, skin_path)
            combined = png_pixels(skin_path)
            body.hide_render = True
            shoes.hide_render = True
            sole.hide_render = False
            mask_path = out / f"{stem}_sole_mask.png"
            render_png(scene, mask_path)
            mask_pixels = png_pixels(mask_path)
            sole.hide_render = True
            body.hide_render = False
            control = out / f".{stem}_control.png"
            render_png(scene, control)
            body_pixels = png_pixels(control)
            control.unlink()
            shoes.hide_render = False

            solid = mask_pixels[:, :, 3] >= 0.99
            tested = fill_holes(solid)
            skin = combined[:, :, 1] > 0.02
            # Convert the PNG's sRGB channels before adding them. Red and
            # blue antialiasing can otherwise imitate the magenta body tag.
            rb = combined[:, :, (0, 2)]
            linear_rb = np.where(rb <= 0.04045, rb / 12.92, ((rb + 0.055) / 1.055) ** 2.4)
            other_body = linear_rb.sum(2) > 1.2
            control_skin = (body_pixels[:, :, 1] >= 0.98) & (body_pixels[:, :, 3] >= 0.99)
            # Include the immediate exterior edge underneath the sole. Open
            # uppers and the exposed top edge of an open sandal are outside this ROI.
            fringe = np.zeros_like(tested)
            if view == "side":
                for x in range(tested.shape[1]):
                    edge = np.flatnonzero(tested[:, x])
                    if len(edge):
                        fringe[max(0, edge[0]-2):edge[0], x] = True
            else:
                padded = np.pad(tested, 2)
                h, w = tested.shape
                for dy, dx in ((2, 0), (2, 1), (2, 3), (2, 4), (0, 2), (1, 2), (3, 2), (4, 2)):
                    fringe |= padded[dy:dy+h, dx:dx+w]
                fringe &= ~tested
            result[stem] = {
                "clip": name, "frame": frame, "side": side, "view": view,
                "mask_scope": "full sole" if view == "below" else "camera-facing sole half",
                "target_sole_lowest_z_m": float(sole_points[:, 2].min()),
                "tested_silhouette_pixels": int(tested.sum()),
                "enclosed_hole_pixels": int((tested & ~solid).sum()),
                "skin_pixels_through_sole": int((skin & tested).sum()),
                "skin_pixels_around_sole": int((skin & fringe).sum()),
                "non_target_body_pixels_through_sole": int((other_body & tested).sum()),
                "body_only_pixels_in_sole_region": int((control_skin & tested).sum()),
                "body_only_pixels_in_crop": int(control_skin.sum()),
                "camera": {"location": list(camera.location), "rotation": list(camera.rotation_euler),
                           "orthographic_scale": camera.data.ortho_scale,
                           "resolution": [scene.render.resolution_x, scene.render.resolution_y]},
                "png_sha256": {suffix: digest(out / f"{stem}{suffix}.png")
                               for suffix in ("", "_skin", "_sole_mask")},
            }
            print("SKIN", stem, {k: v for k, v in result[stem].items() if "pixel" in k}, flush=True)
            bpy.data.objects.remove(sole, do_unlink=True)
            bpy.data.meshes.remove(sole_mesh)
    report("skin_check", {"export_sha256": digest(EXPORT), "views": result})


def main():
    global QA_ROOT, BLEND, EXPORT
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for arg in args:
        if arg.startswith("--candidate-dir="):
            QA_ROOT = (HERE / arg.split("=", 1)[1]).resolve()
            assert QA_ROOT.is_relative_to(HERE) and QA_ROOT.is_dir()
            BLEND, EXPORT = QA_ROOT / BLEND.name, QA_ROOT / EXPORT.name
    if "--checkers-only" in args:
        run_supplied_checkers(render="--no-render" not in args)
        return
    asset = contract()
    scene, body, arm, shoes, actions = on_master()
    embedded_images = {node.image for mat in shoes.data.materials for node in mat.node_tree.nodes
                       if node.type == "TEX_IMAGE" and node.image}
    texture_sizes = {image.name: image.size[:] for image in sorted(embedded_images, key=lambda image: image.name)}
    assert len(texture_sizes) == 3 and all(max(size) <= 1024 for size in texture_sizes.values())
    asset["texture_sizes_px"] = texture_sizes
    report("asset_contract", asset)
    if "--preview-only" in args:
        setup_studio(scene)
        previews(scene, body, arm, shoes)
        return
    if "--skin-only" not in args:
        rest_geometry(body, shoes)
        dense_check(scene, body, arm, shoes, actions)
    if "--dense-only" not in args:
        setup_studio(scene)
        if "--skin-only" not in args:
            previews(scene, body, arm, shoes)
        skin_check(scene, body, arm, shoes)
        report("render_manifest", {"export_sha256": digest(EXPORT), "renderer": "Cycles CPU",
                                   "images": {p.name: digest(p) for p in sorted(QA_ROOT.glob("*.png"))}})


if __name__ == "__main__":
    main()
