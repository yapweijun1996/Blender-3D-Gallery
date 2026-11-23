"""Render the shipped GLB on the master at rest and at minimum clearance poses."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shorts import BANKS, GLB, HERE, REFERENCE, SHA, helpers, load_actions, neutral, set_pose, write_json

VIEWS = (
    ("front", (0, -1, 0)), ("front_three_quarter", (.65, -1, .10)), ("left", (1, 0, 0)),
    ("back", (0, 1, 0)), ("back_three_quarter", (-.65, 1, .10)), ("right", (-1, 0, 0)),
)


def setup():
    api, _ = helpers()
    scene, arm, body = neutral()
    body.hide_render = False
    body.hide_viewport = False
    body.hide_set(False)
    obj = api["import_garment"](GLB, merge=False)
    obj.modifiers.clear()
    obj.modifiers.new("Master Skin", "ARMATURE").object = arm
    obj.parent = arm
    for other in scene.objects:
        if other not in {arm, body, obj}:
            other.hide_viewport = other.hide_render = True
    return scene, arm, body, obj, api


def main():
    scene, arm, _, obj, api = setup()
    actions = load_actions(scene)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_compositing = scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Studio")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.76, .81, .88, 1)
    background.inputs[1].default_value = .65
    center = Vector((0, -.014, .335))
    for name, xyz, power, size in (
        ("Key", (-.65, -1.25, 1.35), 68, 1.55),
        ("Fill", (.8, -.35, .68), 32, 1.30),
        ("Rim", (.3, 1.1, 1.0), 57, 1.2),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = power, "DISK", size
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = xyz
        lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()

    lens = bpy.data.cameras.new("Orthographic")
    lens.type = "ORTHO"
    camera = bpy.data.objects.new("Orthographic", lens)
    scene.collection.objects.link(camera)
    scene.camera = camera
    captures = []
    digest = SHA(GLB)

    def capture(filename, clip, frame, target, direction, width):
        set_pose(scene, arm, actions.get(clip), frame)
        lens.ortho_scale = width
        camera.location = target + Vector(direction).normalized() * 3
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        path = HERE / filename
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        captures.append(dict(file=filename, clip=clip, frame=frame, direction=direction, width_m=width,
                             target_m=list(target), sha256=SHA(path)))
        return path

    size, gap = scene.render.resolution_x, 8
    sheet = np.full((2 * size + gap, 3 * size + 2 * gap, 4), (.07, .08, .10, 1), dtype=np.float32)
    for i, (name, direction) in enumerate(VIEWS):
        path = capture(f".view_{i}.png", "rest", 1, center, direction, .405)
        cell = bpy.data.images.load(str(path), check_existing=False)
        pixels = np.empty(size * size * 4, dtype=np.float32)
        cell.pixels.foreach_get(pixels)
        row, column = divmod(i, 3)
        y, x = (1 - row) * (size + gap), column * (size + gap)
        sheet[y:y + size, x:x + size] = pixels.reshape(size, size, 4)
        bpy.data.images.remove(cell)
        path.unlink()
        captures[-1].update(view=name, file="six_view.png", cell=[row + 1, column + 1])
    image = bpy.data.images.new("Six-view sheet", width=sheet.shape[1], height=sheet.shape[0], alpha=True)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(HERE / "six_view.png")
    image.file_format = "PNG"
    image.save()
    for entry in captures:
        entry["sha256"] = SHA(HERE / entry["file"])

    scene.render.resolution_x = scene.render.resolution_y = 720
    for bank, clip, direction, width in (
        ("shared", "run", (.85, -1, .12), .57),
        ("sit", "sit_idle", (-.95, -1, .30), .56),
        ("carry", "take_item", (.69, -1, .15), .62),
    ):
        data = json.loads((HERE / "checks" / f"{bank}_vertex.json").read_text())
        assert data["glb_sha256"] == digest
        worst = min(data["frames"][clip], key=lambda row: row["min_signed_m"])
        frame = worst["frame"]
        set_pose(scene, arm, actions[clip], frame)
        positions, _ = api["evaluated_arrays"](obj, bpy.context.evaluated_depsgraph_get())
        target = Vector((positions.min(axis=0) + positions.max(axis=0)) * .5)
        target.z += .075
        capture(f"{clip}.png", clip, frame, target, direction, width)
        captures[-1]["minimum_signed_m"] = worst["min_signed_m"]

    assert SHA(GLB) == digest
    write_json("render_manifest.json", dict(glb_sha256=digest, engine="Cycles CPU",
                                           samples=scene.cycles.samples, reference_sha256=SHA(REFERENCE),
                                           banks_sha256={key: SHA(path) for key, (path, _) in BANKS.items()},
                                           captures=captures))


if __name__ == "__main__":
    main()
