"""Render matched six-view and deepest-run evidence from the exported GLBs."""
import json
from pathlib import Path
import struct
import sys
import zlib

import bpy
from mathutils import Vector
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shoes import DEST, HERE, SOURCE, attach_shoes, bind, load_scene, pose, sha, write_json

REST_VIEWS = (
    ("front", (0, -1, 0)), ("left", (1, 0, 0)), ("back", (0, 1, 0)),
    ("right", (-1, 0, 0)), ("top", (0, 0, 1)), ("bottom", (0, 0, -1)),
)
RUN_VIEWS = (("front oblique", (-.65, -1, .25)), ("rear oblique", (-.8, .7, .40)))


def studio(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.use_denoising = True
    scene.cycles.seed = 17
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("High-top studio")
    scene.world.use_nodes = True
    node = scene.world.node_tree.nodes["Background"]
    node.inputs[0].default_value = (.79, .82, .89, 1)
    node.inputs[1].default_value = .57
    data = bpy.data.cameras.new("Fit camera")
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.type = "ORTHO"
    return camera


def lights(scene, center):
    for name, offset, power, size in (
        ("Key", (-.25, -.35, .42), 5.5, .40),
        ("Fill", (.30, -.13, .17), 2.4, .35),
        ("Rim", (.10, .34, .31), 3.5, .24),
        ("Sole fill", (-.20, -.18, -.30), 1.2, .35),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(offset)
        obj.rotation_euler = (-Vector(offset)).to_track_quat("-Z", "Y").to_euler()


def render(scene, camera, path, center, direction, scale, resolution):
    direction = Vector(direction).normalized()
    camera.location = center + direction * 1.5
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    if abs(direction.z) > .999:
        camera.rotation_euler = (0, 0, 0) if direction.z > 0 else (np.pi, 0, 0)
    camera.data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    try:
        return read_rgb(path)
    finally:
        path.unlink(missing_ok=True)


def read_rgb(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        full = np.empty(len(img.pixels), np.float32)
        img.pixels.foreach_get(full)
        w, h = img.size
        return (full.reshape(h, w, 4)[::-1, :, :3] * 255 + .5).astype(np.uint8)
    finally:
        bpy.data.images.remove(img)


def save_sheet(path, rows):
    gap = 5
    h, w = rows[0][0].shape[:2]
    pixels = np.full((len(rows) * (h + gap) - gap, len(rows[0]) * (w + gap) - gap, 3), 39, np.uint8)
    for y, row in enumerate(rows):
        for x, rgb in enumerate(row):
            start_y, start_x = y * (h + gap), x * (w + gap)
            pixels[start_y:start_y + h, start_x:start_x + w] = rgb

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    hh, ww = pixels.shape[:2]
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">2I5B", ww, hh, 8, 2, 0, 0, 0))
    data += chunk(b"sRGB", b"\0")
    data += chunk(b"IDAT", zlib.compress(b"".join(b"\0" + row.tobytes() for row in pixels), 8))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def main():
    bpy.context.preferences.filepaths.temporary_directory = str(HERE)
    scene, arm, body, actions = load_scene()
    v1, v2 = [attach_shoes(path, arm) for path in (SOURCE, DEST)]
    for obj in scene.objects:
        obj.hide_render = obj not in (v1, v2, body) if obj.type == "MESH" else obj.type == "LIGHT"
    camera = studio(scene)
    center = Vector((0., -.025, .062))
    lights(scene, center)
    bind(arm, None)
    pose(scene, 1.)
    body.hide_render = True
    scratch = HERE / ".render_tile.png"
    reference = HERE / "fit_views_v1_reference.png"
    run_path = HERE / "run_deepest_frame_v2.png"
    settings = "Blender 5.1.2 Cycles CPU, AgX, 8 spp"
    reuse = "--reuse-reference" in sys.argv
    if reuse:
        assert reference.is_file()
    paths = [reference] if reuse else []
    versions = [(v2, v1, "fit_views_v2.png")]
    if not reuse:
        versions.insert(0, (v1, v2, reference.name))
    for show, hide, name in versions:
        show.hide_render, hide.hide_render = False, True
        tiles = [render(scene, camera, scratch, center, direction, .36, (390, 340))
                 for _, direction in REST_VIEWS]
        output = HERE / name
        save_sheet(output, (tiles[:3], tiles[3:]))
        paths.append(output)

    baseline = json.loads((HERE / "fit_history.json").read_text())["reproduced_run"]
    frame = baseline["minimum_frame"]
    body.hide_render = False
    bind(arm, actions["run"])
    pose(scene, frame)
    focus = Vector(baseline["world"]) + Vector((0, -.025, -.018))
    if reuse:
        reference_samples = 16
    else:
        reference_samples = scene.cycles.samples
    run_rows = []
    for show, hide in ((v2, v1),):
        show.hide_render, hide.hide_render = False, True
        run_rows.append([render(scene, camera, scratch, focus, direction, .31, (460, 340))
                         for _, direction in RUN_VIEWS])
    save_sheet(run_path, run_rows)
    paths.append(run_path)
    write_json("render_manifest.json", dict(
        source_sha256=sha(SOURCE), export_sha256=sha(DEST), renderer=settings,
        still_views_row_major=[name for name, _ in REST_VIEWS],
        reference_samples=reference_samples, run_rows=["v2"], run_columns=[name for name, _ in RUN_VIEWS], run_frame=frame,
        images={path.name: sha(path) for path in paths},
    ))


if __name__ == "__main__":
    main()
