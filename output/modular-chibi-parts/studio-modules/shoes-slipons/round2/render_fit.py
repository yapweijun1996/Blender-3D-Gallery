"""Render matched v1/v2 orthographic views of the exact GLB exports."""

from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shoes import (EXPORT, HERE, MOTION, SHARED, SOURCE, bind, digest,
                       load_bank, load_master, report, set_frame, world_coords)
from qa_motion import on_master

QA = HERE / "qa"
TILES = QA / "render_tiles"
REST_VIEWS = [
    ("front", (0, -1, 0), (0, 0, 1)),
    ("left", (1, 0, 0), (0, 0, 1)),
    ("back", (0, 1, 0), (0, 0, 1)),
    ("right", (-1, 0, 0), (0, 0, 1)),
    ("top", (0, 0, 1), (0, -1, 0)),
    ("bottom", (0, 0, -1), (0, -1, 0)),
]


def setup(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.cycles.seed = 12
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -.65
    scene.world = bpy.data.worlds.new("Reference comparison environment")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (.88, .92, 1, 1)
    background.inputs["Strength"].default_value = .62
    camera = bpy.data.objects.new("Fit camera", bpy.data.cameras.new("Fit camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    lights = []
    for label, offset, energy, size in [
        ("Softbox", (.24, -.48, .62), 41, .65),
        ("Fill", (-.59, -.23, .35), 20, .55),
        ("Rim", (.20, .41, .52), 26, .65),
        ("Under", (.08, .04, -.41), 10, .50),
    ]:
        data = bpy.data.lights.new(label, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        light = bpy.data.objects.new(label, data)
        scene.collection.objects.link(light)
        lights.append((light, Vector(offset)))
    return camera, lights


def aim(camera, lights, center, direction, up, scale):
    outward = Vector(direction).normalized()
    right = Vector(up).cross(outward).normalized()
    camera.location = center + outward * 1.7
    camera.rotation_euler = Matrix((right, outward.cross(right), outward)).transposed().to_euler()
    camera.data.ortho_scale = scale
    for light, offset in lights:
        light.location = center + offset
        light.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()


def capture(scene, shoes, active, path):
    for obj in shoes:
        obj.hide_render = obj != active
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path), check_existing=False)
    w, h = image.size[:]
    flat = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(flat)
    bpy.data.images.remove(image)
    return flat.reshape((h, w, 4))


def sheet(path, rows):
    gap = 12
    h, w = rows[0][0].shape[:2]
    height = (h + gap) * len(rows) + gap
    width = (w + gap) * len(rows[0]) + gap
    pixels = np.empty((height, width, 4), dtype=np.float32)
    pixels[:] = (.87, .90, .94, 1)
    for row, tiles in enumerate(rows):
        for col, tile in enumerate(tiles):
            x = gap + col * (w + gap)
            y = gap + (len(rows) - 1 - row) * (h + gap)
            bg = np.array([.959, .970, .981], dtype=np.float32)
            pixels[y:y+h, x:x+w, :3] = tile[:, :, :3] * tile[:, :, 3:4] + bg * (1 - tile[:, :, 3:4])
    out = bpy.data.images.new(path.stem, width, height, alpha=False)
    out.pixels.foreach_set(pixels.ravel())
    out.filepath_raw = str(path)
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)


def compare(a, b):
    cover_a, cover_b = a[:, :, 3] >= .5, b[:, :, 3] >= .5
    common = cover_a & cover_b
    delta = np.abs(a[common, :3] - b[common, :3])
    return {"silhouette_intersection_over_union": float(common.sum() / (cover_a | cover_b).sum()),
            "mean_absolute_rgb_delta_8bit": float(delta.mean() * 255),
            "p95_absolute_rgb_delta_8bit": float(np.quantile(delta, .95) * 255)}


def main():
    import json

    TILES.mkdir(parents=True, exist_ok=True)
    scene, arm, body = load_master()
    versions = {"v1": on_master(SOURCE, arm), "v2": on_master(EXPORT, arm)}
    camera, lights = setup(scene)
    bind(arm, None)
    set_frame(scene, 1)
    points = world_coords(versions["v1"])
    center = Vector((points.min(axis=0) + points.max(axis=0)) * .5)
    body.hide_render = True
    scene.render.resolution_x, scene.render.resolution_y = 540, 360
    tiles = {key: [] for key in versions}
    comparisons = {}
    for name, direction, up in REST_VIEWS:
        aim(camera, lights, center, direction, up, .43)
        pair = []
        for key, obj in versions.items():
            tile = capture(scene, versions.values(), obj, TILES / f"{name}_{key}.png")
            tiles[key].append(tile)
            pair.append(tile)
        comparisons[name] = compare(*pair)
    sheet(HERE / "fit_views_v2.png", [tiles["v2"][:3], tiles["v2"][3:]])
    sheet(QA / "fit_views_v1.png", [tiles["v1"][:3], tiles["v1"][3:]])
    # Matched 3/4 angle shows the opening and the toe cap in one view.
    aim(camera, lights, center, (.36, -.59, .36), (0, 0, 1), .43)
    hero = [capture(scene, versions.values(), obj, TILES / f"angled_{key}.png")
            for key, obj in versions.items()]
    sheet(QA / "angled_comparison.png", [hero])
    comparisons["angled"] = compare(*hero)

    motion_report = QA / "motion_gate.json"
    if not motion_report.exists():
        motion_report = HERE / ".runtime/run_render_data.json"
    data = json.loads(motion_report.read_text())
    assert data["glb_sha256"] == digest(EXPORT)
    baseline = min(data["baseline_run"]["frames"], key=lambda s: s["min_signed_m"])
    final = min(data["frames"]["run"], key=lambda s: s["min_signed_m"])
    run = load_bank(MOTION, SHARED)["run"]
    bind(arm, run)
    body.hide_render = False
    scene.render.resolution_x, scene.render.resolution_y = 650, 500
    contact_rows, contact_views = [], []
    for tag, sample in (("v1_deepest", baseline), ("v2_minimum", final)):
        frame = sample["frame"]
        set_frame(scene, frame)
        point = Vector(sample["nearest_vertex_world_m"])
        side = 1 if point.x >= 0 else -1
        # Use a low outside three-quarter view so the ankle, toe and heel
        # remain visible, including when the sole lifts off the rest plane.
        direction = (side, -.60, .30)
        scale = .32
        aim(camera, lights, point, direction, (0, 0, 1), scale)
        images = [capture(scene, versions.values(), obj, TILES / f"{tag}_{key}.png")
                  for key, obj in versions.items()]
        contact_rows.append(images)
        contact_views.append({"row": tag, "frame": frame, "center_m": list(point),
                              "camera_direction": direction, "ortho_scale_m": scale,
                              "same_frame_before": next(s for s in data["baseline_run"]["frames"] if s["frame"] == frame),
                              "same_frame_after": next(s for s in data["frames"]["run"] if s["frame"] == frame)})
    sheet(HERE / "run_deepest_frame_v2.png", contact_rows)
    manifest = {"candidate": digest(EXPORT), "reference": digest(SOURCE),
                "renderer": f"Blender {bpy.app.version_string} Cycles CPU, 20 samples",
                "rest_center_m": list(center), "rest_ortho_scale_m": .43,
                "rest_tile_order": [v[0] for v in REST_VIEWS],
                "rest_views": [{"name": n, "camera_direction": d, "up": u} for n, d, u in REST_VIEWS],
                "run_columns": ["v1", "v2"], "run_rows": contact_views,
                "rest_pixel_comparison": comparisons,
                "files": {str(p.relative_to(HERE)): digest(p) for p in
                          [HERE / "fit_views_v2.png", HERE / "run_deepest_frame_v2.png",
                           QA / "fit_views_v1.png", QA / "angled_comparison.png", *sorted(TILES.glob("*.png"))]}}
    report(QA / "render_manifest.json", manifest)


if __name__ == "__main__":
    main()
