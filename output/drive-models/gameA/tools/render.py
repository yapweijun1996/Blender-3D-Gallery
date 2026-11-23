"""Matched Cycles CPU renders of source and final GLBs."""
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "car_saga": ("proton-saga-1985/exports/proton-saga-1985.glb", 4.1),
    "car_hatchback_hd": ("hatchback-car/exports/optimized.glb", 4.0),
    "motorbike_hd": ("motorcycle/exports/optimized.glb", 2.0),
}
VIEWS = {
    "front": (0,-1,0), "left": (-1,0,0), "rear": (0,1,0),
    "right": (1,0,0), "front-quarter": (-1,-1.65,.70),
    "rear-quarter": (1,1.65,.85),
}
WIDTH, HEIGHT = 440, 270


def aim(obj, target):
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z','Y').to_euler()


def softbox(name, position, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, Vector((0,0,.75)))


def load(file, name, original):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.temporary_directory = str(ROOT / ".work")
    bpy.ops.import_scene.gltf(filepath=str(file))
    roots = [obj for obj in bpy.context.scene.objects if obj.parent is None]
    rotation = Matrix.Rotation(math.pi / 2, 4, 'Z') if original and name == 'car_saga' else Matrix.Identity(4)
    points = [rotation @ obj.matrix_world @ vert.co for obj in bpy.context.scene.objects
              if obj.type == 'MESH' for vert in obj.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    length = MODELS[name][1]
    display_scale = 4 / length
    center = Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,lo.z)) if original else Vector()
    scale = 4 / (hi.y-lo.y) if original else display_scale
    normal = Matrix.Scale(scale, 4) @ Matrix.Translation(-center) @ rotation
    for obj in roots:
        obj.matrix_world = normal @ obj.matrix_world
    return [(p-center)*scale for p in points]


def studio():
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.006))
    matte = bpy.data.materials.new("Studio backdrop")
    matte.use_nodes = True
    matte.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.17,.19,.22,1)
    bpy.context.object.data.materials.append(matte)
    scene = bpy.context.scene
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
    background.inputs[0].default_value = (.65,.71,.79,1)
    background.inputs[1].default_value = .47
    softbox("Key", (2.1,-4.4,6.0), 650, 5)
    softbox("Fill", (-5,-2.0,3.4), 430, 5)
    softbox("Rim", (2.4,4.2,5.6), 770, 4)
    data = bpy.data.cameras.new("Inspection camera")
    data.type = 'ORTHO'
    camera = bpy.data.objects.new("Inspection camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def frame(camera, points, direction):
    camera.location = Vector(direction).normalized() * 12
    aim(camera, Vector((0,0,0)))
    basis = camera.rotation_euler.to_matrix()
    projected = [basis.transposed() @ p for p in points]
    limits = [(min(p[i] for p in projected),max(p[i] for p in projected)) for i in (0,1)]
    w,h = (b-a for a,b in limits)
    camera.data.ortho_scale = max(w,h*WIDTH/HEIGHT,1.35)*1.16
    camera.location += basis @ Vector((sum(limits[0])/2,sum(limits[1])/2,0))


def render(name, variant, points=None):
    source = ROOT.parents[2] / "models" / MODELS[name][0]
    file = source if variant == "original" else ROOT / f"{name}.glb"
    bounds = load(file, name, variant == "original")
    scene, camera = studio()
    for label, direction in VIEWS.items():
        path = ROOT / ".work" / f"{name}-{variant}-{label}.png"
        if variant == "original" and path.exists():
            continue
        frame(camera, points or bounds, direction)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
    return bounds


def sheet(name):
    command = ["ffmpeg", "-loglevel", "error", "-y"]
    positions = []
    for index, label in enumerate(VIEWS):
        for column, variant in enumerate(("original", "game")):
            command += ["-threads", "1", "-i", str(ROOT / ".work" / f"{name}-{variant}-{label}.png")]
            positions.append(f"{(index%2*2+column)*(WIDTH+4)+(index%2)*12}_{(index//2)*(HEIGHT+4)}")
    stack = "xstack=inputs=12:layout=" + "|".join(positions) + ":fill=0x262c36"
    command += ["-filter_complex_threads", "2", "-filter_complex", stack, "-frames:v", "1",
                "-threads", "2", "-update", "1", str(ROOT / "contact-sheets" / f"{name}.png")]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    (ROOT / ".work").mkdir(exist_ok=True)
    (ROOT / "contact-sheets").mkdir(exist_ok=True)
    args = sys.argv[sys.argv.index("--")+1:]
    for name in args[1:] or MODELS:
        points = render(name, "original")
        if args[0] == "compare":
            render(name, "game", points)
            sheet(name)
