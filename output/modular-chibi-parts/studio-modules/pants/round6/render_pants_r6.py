"""Capture six rest views and paired views at the tightest evaluated action frames."""
import json
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_pants_r6.py"))
REST = (
    ("front", (0, -1, .035), True),
    ("front_three_quarter", (.66, -1, .06), True),
    ("side", (1, 0, .035), True),
    ("back", (0, 1, .035), True),
    ("waist", (-.7, -1, .68), False),
    ("cuffs", (.52, 1, -.62), False),
)
MOTION_VIEWS = {
    "walk": ((.44, -1, .08), (-.72, .80, .10)),
    "run": ((.62, -1, .08), (-.65, .80, .16)),
    "sit_idle": ((.74, -1, .5), (-.92, .45, .43)),
    "hold_item": ((.5, -1, .12), (-.76, .85, .14)),
    "take_item": ((.58, -1, .23), (-.78, .82, .22)),
}


def render():
    glb = FIT["GLB"]
    digest = FIT["digest"](glb)
    report = json.loads((HERE / "motion_summary.json").read_text())
    assert report["glb_sha256"] == digest
    scene, arm, body, garment, actions = FIT["setup"](glb, merge=False)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Pants inspection")
    scene.world.use_nodes = True
    ambient = scene.world.node_tree.nodes["Background"]
    ambient.inputs[0].default_value = (.7, .75, .82, 1)
    ambient.inputs[1].default_value = .55
    origin = Vector((0, 0, .245))
    for name, xyz, energy, size in (
        ("Key", (-1, -1.45, 2.25), 115, 2.1),
        ("Fill", (1.25, -.55, .95), 50, 1.6),
        ("Rim", (.4, 1.45, 1.9), 105, 1.6),
        ("Cuff Fill", (-.6, .2, -.6), 13, 1.2),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = xyz
        lamp.rotation_euler = (origin - lamp.location).to_track_quat("-Z", "Y").to_euler()

    lens = bpy.data.cameras.new("Pants orthographic QA")
    lens.type = "ORTHO"
    camera = bpy.data.objects.new(lens.name, lens)
    scene.collection.objects.link(camera)
    scene.camera = camera
    manifest = {}

    def capture(name, target, direction, width, body_visible):
        body.hide_render = not body_visible
        lens.ortho_scale = width
        camera.location = target + Vector(direction).normalized() * 3
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        output = HERE / f".{name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(output))
        x, y = image.size
        pixels = np.empty(x * y * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        bpy.data.images.remove(image)
        output.unlink()
        return pixels.reshape(y, x, 4)

    def sheet(filename, cells, columns):
        height, width = cells[0].shape[:2]
        rows = len(cells) // columns
        gutter = 6
        composite = np.full((rows * height + (rows - 1) * gutter,
                             columns * width + (columns - 1) * gutter, 4), .24, dtype=np.float32)
        composite[:, :, 3] = 1
        for index, pixels in enumerate(cells):
            row, col = divmod(index, columns)
            y, x = (rows - row - 1) * (height + gutter), col * (width + gutter)
            composite[y:y + height, x:x + width] = pixels
        image = bpy.data.images.new(filename, width=composite.shape[1], height=composite.shape[0], alpha=False)
        image.pixels.foreach_set(composite.ravel())
        image.file_format = "PNG"
        image.filepath_raw = str(HERE / filename)
        image.save()
        bpy.data.images.remove(image)
        return FIT["digest"](HERE / filename)

    scene.render.resolution_x = scene.render.resolution_y = 600
    FIT["set_pose"](scene, arm, actions, "rest", 1)
    if "--motion-only" not in sys.argv:
        cells = [capture(name, origin, direction, .50, visible) for name, direction, visible in REST]
        manifest["six_view.png"] = {"clip": "rest", "frame": 1, "views_in_row_order": REST,
                                     "sha256": sheet("six_view.png", cells, 3)}
    if "--rest-only" not in sys.argv:
        scene.render.resolution_x = scene.render.resolution_y = 760
        for clip, directions in MOTION_VIEWS.items():
            result = report["results"][clip]
            frame = result["minimum_frame"]
            FIT["set_pose"](scene, arm, actions, clip, frame)
            posed = FIT["BASE"]["evaluated_coordinates"](garment)
            low, high = posed.min(axis=0), posed.max(axis=0)
            center = Vector((low + high) * .5)
            width = max(.48, float(np.max(high - low)) * 1.37)
            cells = [capture(f"{clip}_{index}", center, direction, width, True)
                     for index, direction in enumerate(directions)]
            name = clip + ".png"
            manifest[name] = {"clip": clip, "frame": frame, "minimum_signed_m": result["minimum_signed_m"],
                              "directions": directions, "width_m": width, "sha256": sheet(name, cells, 2)}
    FIT["write_json"]("render_manifest.json", {"glb_sha256": digest, "engine": "Cycles CPU",
                                              "samples": scene.cycles.samples, "captures": manifest})


if __name__ == "__main__":
    render()
