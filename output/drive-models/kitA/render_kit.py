"""Photograph the exported GLBs in six orthographic views, using Cycles CPU."""
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
SHEETS = ROOT / "contact-sheets"
VIEWS = {
    "front": (0,-1,0), "back": (0,1,0), "left": (1,0,0), "right": (-1,0,0),
    "top": (0,0,1), "three-quarter": (1,-1.68,.95),
}
WIDTH, HEIGHT = 480, 338


def aim(obj, target):
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z','Y').to_euler()


def softbox(name, position, power, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, Vector((0,0,1)))


def setup(file):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.temporary_directory = str(ROOT)
    bpy.ops.import_scene.gltf(filepath=str(file))
    scene = bpy.context.scene
    model = next(obj for obj in scene.objects if obj.type == 'MESH')
    raw = [model.matrix_world @ v.co for v in model.data.vertices]
    lo = Vector([min(p[i] for p in raw) for i in range(3)])
    hi = Vector([max(p[i] for p in raw) for i in range(3)])
    scale = 4.0 / max(hi-lo)
    origin = Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,lo.z))
    model.scale *= scale
    model.location -= origin * scale
    points = [(p-origin)*scale for p in raw]
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.009))
    matte = bpy.data.materials.new("Studio backdrop")
    matte.use_nodes = True
    matte.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.245,.30,.37,1)
    bpy.context.object.data.materials.append(matte)

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.world = bpy.data.worlds.new("Studio ambience")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (.52,.62,.74,1)
    background.inputs[1].default_value = .43
    softbox("Key", (2.1,-4.4,6.0), 650, 5, (1,.91,.80))
    softbox("Fill", (-5,-2.0,3.4), 430, 5, (.78,.90,1))
    softbox("Rim", (2.4,4.2,5.6), 770, 4, (.89,.95,1))

    data = bpy.data.cameras.new("Inspection camera")
    data.type = 'ORTHO'
    camera = bpy.data.objects.new("Inspection camera", data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera, points


def frame(camera, points, direction):
    camera.location = Vector(direction).normalized() * 12
    aim(camera, Vector((0,0,0)))
    if direction == (0,0,1):
        camera.rotation_euler = (0,0,math.pi)
    basis = camera.rotation_euler.to_matrix()
    projected = [basis.transposed() @ p for p in points]
    limits = [(min(p[i] for p in projected),max(p[i] for p in projected)) for i in (0,1)]
    w,h = (b-a for a,b in limits)
    camera.data.ortho_scale = max(w,h*WIDTH/HEIGHT,1.35)*1.19
    camera.location += basis @ Vector((sum(limits[0])/2,sum(limits[1])/2,0))


def contact_sheet(file):
    scene, camera, points = setup(file)
    panels = []
    try:
        for label,direction in VIEWS.items():
            frame(camera, points, direction)
            path = SHEETS / f".{file.stem}-{label}.png"
            panels.append(path)
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
        command = ["ffmpeg", "-loglevel", "error", "-y", "-threads", "2"]
        for panel in panels:
            command += ["-i", str(panel)]
        command += ["-filter_complex_threads", "2", "-filter_complex",
                    f"xstack=inputs=6:layout=0_0|{WIDTH+4}_0|{2*(WIDTH+4)}_0|"
                    f"0_{HEIGHT+4}|{WIDTH+4}_{HEIGHT+4}|{2*(WIDTH+4)}_{HEIGHT+4}:fill=0x243042",
                    "-frames:v", "1", "-threads", "2", "-update", "1", str(SHEETS / f"{file.stem}.png")]
        subprocess.run(command, check=True)
    finally:
        for path in panels:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    SHEETS.mkdir(exist_ok=True)
    requested = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    for file in ([ROOT / f"{name}.glb" for name in requested] if requested else sorted(ROOT.glob("*.glb"))):
        contact_sheet(file)
