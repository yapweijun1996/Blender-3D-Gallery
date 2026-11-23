"""Produce six orthographic views and a skirt motion contact sheet."""
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import BODY, HERE, MOTION, arguments, bind, dispose, load_glb, set_frame
from gate_module import SHIPPED
import render
import fit_module as fit


def add_floor(scene, height):
    bpy.ops.mesh.primitive_plane_add(size=200)
    floor = bpy.context.object
    floor.location.z = height - .00001
    floor.name = "Shipped sneaker sole plane"
    material = bpy.data.materials.new("Studio floor")
    material.diffuse_color = (.19, .21, .25, 1)
    floor.data.materials.append(material)
    scene.cycles.samples = 8
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2


def render_item(path):
    label = path.stem
    layers = ("tshirt", "sneakers") if label.startswith("bottom") else ()
    if label.startswith("shoes"):
        framing = (.132 if label == "shoes-boots" else .095, .49)
    elif label.startswith("bottom"):
        framing = (.31, .58)
    else:
        framing = (.82, .72)

    sneaker = fit.Glb(SHIPPED["sneakers"])
    floor = min(sneaker.doc["accessors"][p["attributes"]["POSITION"]]["min"][1]
                for p in sneaker.doc["meshes"][0]["primitives"])
    render.CUSTOM.update({label: path, **SHIPPED})
    render.FRAMING[label] = framing
    original = render.setup

    def setup():
        scene, camera = original()
        add_floor(scene, floor)
        return scene, camera

    render.setup = setup
    render.render_set([label, *layers], render.ANGLES, label, label)
    render.setup = original
    if label == "bottom-skirt":
        skirt_motion(label, floor)


def skirt_motion(label, floor):
    scene, camera = render.setup()
    add_floor(scene, floor)
    objects = load_glb(BODY)
    arm, = [obj for obj in objects if obj.type == "ARMATURE"]
    dispose(objects - {arm, scene.objects["Base_Body"]})
    render.add_module(arm, label)
    render.add_module(arm, "tshirt")
    render.add_module(arm, "sneakers")
    dispose(load_glb(MOTION))
    folder = render.OUT / label
    layouts = []
    for clip, frames in (("walk", (12, 28, 44)), ("run", (6, 17, 29)),
                         ("sit_down", (10, 23, 33))):
        bind(arm, bpy.data.actions[clip])
        row = []
        for frame in frames:
            set_frame(scene, frame)
            center = arm.pose.bones["mixamorig:Hips"].head.copy()
            focus = (center.x, center.y, max(.18, center.z - .10))
            camera.location = (focus[0] + 1.7, focus[1] - 2.5, focus[2] + .4)
            camera.data.ortho_scale = .76
            render.point_camera(camera, focus)
            image = folder / f"{clip}-{frame}.png"
            scene.render.filepath = str(image)
            bpy.ops.render.render(write_still=True)
            row.append(image)
        layouts.append(row)
    render.sheet(layouts, folder / "motion.png")
    (folder / "motion-views.json").write_text(json.dumps({
        "motion_sha256": render.digest(MOTION),
        "views": [[{"image": p.name, "sha256": render.digest(p)} for p in row] for row in layouts],
    }, indent=2) + "\n")


if __name__ == "__main__":
    path, directory = [Path(arg).resolve() for arg in arguments()]
    assert path.is_relative_to(HERE) and directory.is_relative_to(HERE)
    render.OUT = directory
    render_item(path)
