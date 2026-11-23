"""Render the exported GLB at reproducible studio angles without editing the source."""
from pathlib import Path
import sys

import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
PREVIEWS = BASE / "previews"
PREVIEWS.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BASE / "exports/mid-autumn-rabbit-lantern.glb"))
scene = bpy.context.scene
target = Vector((-0.031, 0, 0.366))
scene.world = bpy.data.worlds.new("Studio")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes["Background"]
background.inputs["Color"].default_value = (0.12, 0.080, 0.055, 1)
background.inputs["Strength"].default_value = 0.50

for name, position, power, size in (
    ("Key", (1.1, -1.2, 1.8), 72, 1.2),
    ("Fill", (-1.3, -0.8, 0.6), 26, 1.4),
    ("Rim", (0.4, 1.2, 1.4), 65, 1.0),
):
    bpy.ops.object.light_add(type="AREA", location=position)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "CYCLES"
scene.cycles.samples = 20
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 0.92
scene.camera = camera
views = {"hero": (0.68, -2.5, 0.93), "front": (2.60, -0.05, 0.63),
         "other-side": (0.45, 2.5, 0.79), "rear": (-2.5, 0.9, 0.85)}
for name in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["hero"]):
    camera.location = views[name]
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(PREVIEWS / f"{name}.png")
    bpy.ops.render.render(write_still=True)
