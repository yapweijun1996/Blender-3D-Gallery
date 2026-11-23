"""Render six module angles and full outfits with Blender's Cycles CPU renderer."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BODY, HERE, MODULES, MOTION, arguments, bind, dispose, load_glb, set_frame

OUT = HERE / "renders"
ASSETS = HERE
CUSTOM = {}
ANGLES = {"front": 0, "front-left": 45, "left": 90, "back": 180,
          "right": 270, "front-right": 315}
# Center and scale each slot so the fitted region remains legible.
FRAMING = {"hair-bob": (.75, .57), "hair-spiky": (.77, .69), "hair-sidepart": (.77, .64),
           "tshirt": (.54, .82), "dress": (.465, .91),
           "jeans": (.27, .69), "sneakers": (.11, .54), "outfit": (.49, 1.20)}
OUTFITS = {
    "bob-casual": ("hair-bob", "tshirt", "jeans", "sneakers"),
    "spiky-casual": ("hair-spiky", "tshirt", "jeans", "sneakers"),
    "sidepart-dress": ("hair-sidepart", "dress", "sneakers"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point_camera(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 10
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Studio fill")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.36, .40, .49, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .55
    for label, place, power, size in (
            ("Key", (-1.1, -2.0, 2.0), 145, 1.45), ("Fill", (1.6, -1.5, 1.5), 70, 1.5),
            ("Rim", (.2, 1.2, 1.7), 110, 1.1), ("Rear fill", (1.2, 1.5, .85), 60, 1.5)):
        data = bpy.data.lights.new(label, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        light = bpy.data.objects.new(label, data)
        light.location = place
        scene.collection.objects.link(light)
        point_camera(light, (0, 0, .53))
    camera = bpy.data.cameras.new("Orthographic")
    camera.type = "ORTHO"
    obj = bpy.data.objects.new("Orthographic", camera)
    scene.collection.objects.link(obj)
    scene.camera = obj
    return scene, obj


def add_module(arm, label):
    path = CUSTOM.get(label, ASSETS / f"female-{label}.glb")
    objects = load_glb(path)
    mesh, = [obj for obj in objects if obj.type == "MESH" and obj.vertex_groups]
    world = mesh.matrix_world.copy()
    mesh.parent = arm
    mesh.matrix_world = world
    mesh.modifiers.clear()
    mesh.modifiers.new("Female skin", "ARMATURE").object = arm
    dispose(objects - {mesh})
    return mesh


def render_set(slugs, angles, category, stem, action=None, frame=0., motion_views=None):
    scene, camera = setup()
    objects = load_glb(BODY)
    arm, = [o for o in objects if o.type == "ARMATURE"]
    dispose(objects - {arm, scene.objects["Base_Body"]})
    for label in slugs:
        add_module(arm, label)
    if category == "outfit" and action is None:
        action, frame = "idle", 18.
    if action or motion_views:
        dispose(load_glb(MOTION))
    poses = {name: (action or "rest", frame, name) for name in angles}
    if motion_views:
        poses.update(motion_views)
    bind(arm, None)
    focus_z, scale = FRAMING[category]
    pelvis = arm.pose.bones["mixamorig:Hips"]
    anchor = arm.matrix_world @ pelvis.head
    focus = (0, 0, focus_z)
    folder = OUT / stem
    folder.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for name, (pose, active_frame, view) in poses.items():
        bind(arm, None if pose == "rest" else bpy.data.actions[pose])
        set_frame(scene, active_frame)
        angle = math.radians(ANGLES[view])
        offset = (arm.matrix_world @ pelvis.head) - anchor
        subject = Vector(focus) + Vector((offset.x, offset.y, .8 * offset.z))
        camera.location = subject + Vector((2.5 * math.sin(angle), -2.5 * math.cos(angle),
                                           .17 if category == "outfit" else .12))
        camera.data.ortho_scale = scale
        point_camera(camera, subject)
        path = folder / f"{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        mapping[name] = dict(file=str(path.relative_to(HERE)), sha256=digest(path),
                             camera_location=list(camera.location), pose=pose, frame=active_frame, view=view)
    record = dict(body_sha256=digest(BODY), motion_sha256=digest(MOTION) if action or motion_views else None,
                  module_sha256={slug: digest(CUSTOM.get(slug, ASSETS / f"female-{slug}.glb")) for slug in slugs},
                  pose=action or "rest", frame=frame, fps=30, blender=bpy.app.version_string, renderer="Cycles CPU",
                  orthographic_scale=scale, focus=focus, images=mapping)
    (folder / "views.json").write_text(json.dumps(record, indent=2) + "\n")
    return [OUT / stem / (name + ".png") for name in poses]


def sheet(rows, destination):
    width = 400
    gap = 12
    canvas = np.full((len(rows) * (width + gap) + gap,
                      len(rows[0]) * (width + gap) + gap, 4), (.035, .045, .06, 1), dtype=np.float32)
    for r, paths in enumerate(rows):
        for c, path in enumerate(paths):
            tex = bpy.data.images.load(str(path), check_existing=False)
            tex.colorspace_settings.name = "Non-Color"
            values = np.empty(width * width * 4, dtype=np.float32)
            tex.pixels.foreach_get(values)
            row = (len(rows) - r - 1) * (width + gap) + gap
            col = c * (width + gap) + gap
            canvas[row:row + width, col:col + width] = values.reshape(width, width, 4)
            bpy.data.images.remove(tex)
    result = bpy.data.images.new("Outfit contact sheet", canvas.shape[1], canvas.shape[0], alpha=False)
    result.colorspace_settings.name = "Non-Color"
    result.pixels.foreach_set(canvas.ravel())
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Raw"
    result.save_render(filepath=str(destination), scene=scene)


def main():
    global OUT, ASSETS
    preview = "--seed-preview" in arguments()
    if preview:
        ASSETS, OUT = HERE / ".runtime", HERE / ".runtime/preview"
    jobs = [a for a in arguments() if not a.startswith("--")] or [*MODULES, *([] if preview else ["outfits"])]
    for label in jobs:
        if label == "outfits":
            angles = ("front", "front-left", "back", "right")
            rows = [render_set(parts, angles, "outfit", name) for name, parts in OUTFITS.items()]
            sheet(rows, OUT / "full-outfits.png")
        else:
            render_set([label], ("front",) if preview else ANGLES, label, label)


if __name__ == "__main__":
    main()
