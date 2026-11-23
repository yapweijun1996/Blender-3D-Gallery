"""Render the exported sandals and the deepest original run contact with Cycles CPU."""
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy
import numpy as np
from mathutils import Vector

from fit_shoes_v2 import BLEND, EXPORT, MOTION, OUT, SOURCE, attach, bind, digest, load_bank, report

WIDTH, HEIGHT = 660, 450
REST_VIEWS = (
    ("Front  |  worn", (0, -1, 0.05), (0, -0.02, 0.052), 0.49, True),
    ("Heel  |  worn", (0, 1, 0.10), (0, -0.02, 0.052), 0.49, True),
    ("Left side  |  worn", (1, 0.06, 0.07), (0, -0.02, 0.047), 0.44, True),
    ("Right side  |  worn", (-1, 0.06, 0.07), (0, -0.02, 0.047), 0.44, True),
    ("Straps  |  top", (0, -0.0001, 1), (0, -0.022, 0.031), 0.50, False),
    ("Tread  |  bottom", (0, -0.0001, -1), (0, -0.022, 0.031), 0.50, False),
)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def set_studio(scene, body, shoe, light_target):
    for obj in scene.objects:
        if obj.type == "MESH" and obj not in (body, shoe):
            obj.hide_render = True
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.cycles.seed = 7
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    image = scene.render.image_settings
    image.file_format = "PNG"
    image.color_mode = "RGB"
    image.color_depth = "8"
    image.compression = 35
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    world = bpy.data.worlds.new("Sandal photo studio")
    world.use_nodes = True
    scene.world = world
    nodes, links = world.node_tree.nodes, world.node_tree.links
    ambient = nodes["Background"]
    ambient.inputs["Color"].default_value = (0.83, 0.88, 0.97, 1)
    ambient.inputs["Strength"].default_value = 0.32
    visible = nodes.new("ShaderNodeBackground")
    visible.inputs["Color"].default_value = (0.79, 0.83, 0.90, 1)
    visible.inputs["Strength"].default_value = 0.92
    mix = nodes.new("ShaderNodeMixShader")
    light_path = nodes.new("ShaderNodeLightPath")
    links.new(light_path.outputs["Is Camera Ray"], mix.inputs[0])
    links.new(ambient.outputs[0], mix.inputs[1])
    links.new(visible.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes["World Output"].inputs["Surface"])

    for name, offset, energy, size in (
        ("Softbox", (0.27, -0.48, 0.55), 14, 0.52),
        ("Fill", (-0.39, -0.28, 0.34), 7, 0.45),
        ("Edge", (0.24, 0.45, 0.27), 10, 0.49),
        ("Tread fill", (0, -0.07, -0.47), 4, 0.45),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = Vector(light_target) + Vector(offset)
        aim(obj, light_target)
    data = bpy.data.cameras.new("Orthographic fit")
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.type = "ORTHO"
    data.clip_start = 0.01

    font = bpy.data.curves.new("Panel label", "FONT")
    label = bpy.data.objects.new(font.name, font)
    scene.collection.objects.link(label)
    label.parent = camera
    for ray in ("visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission"):
        setattr(label, ray, False)
    color = bpy.data.materials.new("Panel label ink")
    color.use_nodes = True
    nodes, links = color.node_tree.nodes, color.node_tree.links
    ink = nodes.new("ShaderNodeEmission")
    ink.inputs["Color"].default_value = (0.014, 0.019, 0.032, 1)
    links.new(ink.outputs[0], nodes["Material Output"].inputs["Surface"])
    font.materials.append(color)
    return camera, label


def render(scene, camera, label, title, offset, target, scale, path):
    camera.location = Vector(target) + Vector(offset)
    aim(camera, target)
    camera.data.ortho_scale = scale
    label.data.body = title
    label.data.size = scale * 0.033
    label.location = (-scale * 0.455, -scale * HEIGHT / WIDTH * 0.445, -0.045)
    label.hide_render = not title
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def read_pixels(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    data = np.empty((height, width, 4), np.float32)
    image.pixels.foreach_get(data.ravel())
    bpy.data.images.remove(image)
    return data


def sheet(tiles, columns, path):
    gap = 10
    rows = math.ceil(len(tiles) / columns)
    width, height = columns * (WIDTH + gap) + gap, rows * (HEIGHT + gap) + gap
    pixels = np.empty((height, width, 4), dtype=np.float32)
    pixels[:] = (0.95, 0.95, 0.96, 1)
    for i, tile in enumerate(tiles):
        row, column = divmod(i, columns)
        x, y = gap + column * (WIDTH + gap), gap + (rows - row - 1) * (HEIGHT + gap)
        pixels[y:y + HEIGHT, x:x + WIDTH] = read_pixels(tile)
    image = bpy.data.images.new(path.stem, width, height)
    image.pixels.foreach_set(pixels.ravel())
    image.file_format = "PNG"
    image.filepath_raw = str(path)
    image.save()
    bpy.data.images.remove(image)


def main():
    with TemporaryDirectory(prefix=".render-", dir=OUT) as folder:
        folder = Path(folder)
        scene, arm, body, shoe = attach(EXPORT)
        camera, label = set_studio(scene, body, shoe, (0, -0.02, 0.05))
        panels = []
        for i, (title, offset, target, lens, worn) in enumerate(REST_VIEWS):
            body.hide_render = not worn
            tile = folder / f"rest-{i}.png"
            render(scene, camera, label, title, offset, target, lens, tile)
            panels.append(tile)
        sheet(panels, 3, OUT / "fit_views_v2.png")

        metrics = json.loads((OUT / "fit_metrics.json").read_text())
        contact = metrics["baseline"]["deepest"]
        frame = contact["frame"]
        target = Vector(contact["deepest_point_world_m"])
        target.z -= 0.022
        panels = []
        for version, module in (("V1", SOURCE), ("V2", EXPORT)):
            scene, arm, body, shoe = attach(module)
            action = load_bank(MOTION)["run"]
            bind(arm, action)
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            camera, label = set_studio(scene, body, shoe, target)
            body.hide_render = False
            tile = folder / f"contact-{version}.png"
            render(scene, camera, label, f"{version}  |  Run frame {frame:g}", (0.78, -0.47, 0.29),
                   target, 0.39, tile)
            panels.append(tile)
            body.hide_render = True
            hero = folder / f"rest-comparison-{version}.png"
            bind(arm)
            scene.frame_set(1)
            render(scene, camera, label, "", (0.36, -0.68, 0.40), (0, -0.022, 0.046), 0.46, hero)
        sheet(panels, 2, OUT / "run_deepest_v2.png")

        v1, v2 = [read_pixels(folder / f"rest-comparison-{version}.png")[..., :3] for version in ("V1", "V2")]
        background = v1[-1, -1]
        foreground = (np.max(abs(v1 - background), axis=2) > 0.08) & (
            np.max(abs(v2 - background), axis=2) > 0.08)
        diff = abs(v1[foreground] - v2[foreground])
        report("render_manifest.json", dict(
            glb_sha256=digest(EXPORT), renderer="Cycles CPU", samples=24,
            rest_views=[view[0] for view in REST_VIEWS],
            deepest_original_run_contact=contact,
            rest_hero_comparison=dict(audited_pixels=int(foreground.sum()),
                                      mean_absolute_rgb_8bit=float(diff.mean() * 255),
                                      percentile_95_absolute_rgb_8bit=float(np.percentile(diff, 95) * 255)),
            images={name: digest(OUT / name) for name in ("fit_views_v2.png", "run_deepest_v2.png")}))
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
    objects = list(bpy.context.scene.objects)
    assert sorted(obj.type for obj in objects) == ["ARMATURE", "MESH"]
    rig, = [obj for obj in objects if obj.type == "ARMATURE"]
    assert len(rig.data.bones) == 65 and not rig.animation_data
    maps = [image for image in bpy.data.images if image.packed_file]
    assert len(maps) == 3 and all(max(image.size) <= 1024 for image in maps)
    print("Saved Blender file reopens with one mesh, 65 bones and three packed map images.")


if __name__ == "__main__":
    main()
