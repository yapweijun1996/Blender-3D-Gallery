"""Render the exact round-4 GLB in rest and at the lowest signed-distance frames."""

import json
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_jeans_r4.py"))
VIEWS = ((0, -1, 0), (.63, -1, .14), (1, 0, 0), (0, 1, 0), (-.63, 1, .14), (-1, 0, 0))


def main():
    glb = FIT["GLB"]
    report = json.loads((HERE / "motion_check.json").read_text())
    digest = FIT["sha256"](glb)
    assert report["garment_sha256"] == digest
    scene, arm, body, garment = FIT["setup"](glb)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = scene.render.resolution_y = 576
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("QA Studio")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.70, .76, .85, 1)
    background.inputs[1].default_value = .5
    rest_center = Vector((0, -.01, .248))
    for name, location, energy, size in (
        ("Key", (-.65, -1.25, 1.35), 65, 1.55),
        ("Fill", (.8, -.3, .68), 26, 1.3),
        ("Rim", (.3, 1.1, 1.0), 49, 1.2),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = location
        lamp.rotation_euler = (rest_center - lamp.location).to_track_quat("-Z", "Y").to_euler()

    lens = bpy.data.cameras.new("QA Orthographic")
    lens.type = "ORTHO"
    camera = bpy.data.objects.new(lens.name, lens)
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = []

    def capture(filename, clip, frame, center, direction, width):
        FIT["set_pose"](scene, arm, clip, frame)
        lens.ortho_scale = width
        camera.location = center + Vector(direction).normalized() * 3
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / filename)
        bpy.ops.render.render(write_still=True)
        views.append({"file": filename, "clip": clip, "frame": frame, "direction": direction, "width_m": width})

    size, gutter = scene.render.resolution_x, 8
    sheet = np.full((2 * size + gutter, 3 * size + 2 * gutter, 4), (.12, .14, .17, 1), dtype=np.float32)
    for index, direction in enumerate(VIEWS):
        filename = ".view_" + str(index) + ".png"
        capture(filename, "rest", 1, rest_center, direction, .49)
        cell = bpy.data.images.load(str(HERE / filename))
        pixels = np.empty(size * size * 4, dtype=np.float32)
        cell.pixels.foreach_get(pixels)
        row, col = divmod(index, 3)
        y, x = (1 - row) * (size + gutter), col * (size + gutter)
        sheet[y:y + size, x:x + size] = pixels.reshape(size, size, 4)
        bpy.data.images.remove(cell)
        (HERE / filename).unlink()
        views[-1].update(file="six_view.png", cell={"row": row + 1, "column": col + 1})
    image = bpy.data.images.new("Six orthographic views", width=sheet.shape[1], height=sheet.shape[0], alpha=True)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(HERE / "six_view.png")
    image.file_format = "PNG"
    image.save()

    scene.render.resolution_x = scene.render.resolution_y = 840
    for clip, direction in (("sit_idle", (-.94, -1, .45)), ("hold_item", (.62, -1, .12))):
        details = report["results"][clip]["closest"]
        frame = details["frame"]
        FIT["set_pose"](scene, arm, clip, frame)
        points, _ = FIT["evaluated_arrays"](garment, bpy.context.evaluated_depsgraph_get())
        center = Vector((points.min(axis=0) + points.max(axis=0)) * .5)
        center.z += .135 if clip == "hold_item" else .080
        capture(clip + ".png", clip, frame, center, direction, .82 if clip == "hold_item" else .65)
        views[-1]["minimum_signed_m"] = details["minimum_m"]
    for view in views:
        view["sha256"] = FIT["sha256"](HERE / view["file"])
    assert FIT["sha256"](glb) == digest
    FIT["write_json"]("render_manifest.json", {"glb_sha256": digest, "engine": "Cycles CPU",
                                              "samples": scene.cycles.samples, "views": views})


if __name__ == "__main__":
    main()
