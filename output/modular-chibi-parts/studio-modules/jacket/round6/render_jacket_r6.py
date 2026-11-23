"""Make Cycles CPU proof renders from the reimported jacket GLB."""

import json
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_jacket_r6.py"))
REST = ((0,-1,.05),(.65,-1,.12),(1,0,.025),(0,1,.05),(-.65,1,.12),(-1,0,.025))
ACTION = {
    "walk": ((.6,-1,.10),(-.75,1,.16)),
    "run": ((-.55,-1,.15),(.86,1,.11)),
    "sit_idle": ((-.85,-1,.25),(.64,1,.2)),
    "hold_item": ((.64,-1,.18),(-.85,1,.15)),
    "take_item": ((-.72,-1,.18),(.8,1,.12)),
}


def render(mode="all", filename="jacket_v6.glb"):
    source = (HERE / filename).resolve()
    scene, arm, body, jacket = FIT["setup"](source)
    if mode != "preview":
        FIT["import_actions"](scene)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 18
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Jacket studio")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (.66,.72,.82,1)
    bg.inputs[1].default_value = .68
    center = Vector((0,-.01,.497))
    for name, pos, energy, size in (
        ("Key",(-.61,-1.02,1.39),54,1.35),("Fill",(.68,-.38,.71),33,1.3),
        ("Back",(.38,1.08,1.01),67,1.4),("Rear fill",(-.53,.77,.60),24,1.22)
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        obj = bpy.data.objects.new(name,light)
        scene.collection.objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (center-obj.location).to_track_quat("-Z","Y").to_euler()
    lens = bpy.data.cameras.new("Jacket evaluation")
    lens.type = "ORTHO"
    camera = bpy.data.objects.new(lens.name,lens)
    scene.collection.objects.link(camera)
    scene.camera = camera

    def sheet(name, clip, frame, angles, rows, cols, width, height, scale):
        FIT["set_pose"](scene,arm,clip,frame)
        pts = FIT["evaluated_points"](jacket)
        focus = Vector((pts.min(axis=0)+pts.max(axis=0))*.5)
        focus.z -= .013
        padding = 8
        sheet_width, sheet_height = cols * width + (cols - 1) * padding, rows * height + (rows - 1) * padding
        result = np.full((sheet_height, sheet_width, 4), (.15,.16,.17,1), np.float32)
        scene.render.resolution_x, scene.render.resolution_y = width,height
        for index, direction in enumerate(angles):
            lens.ortho_scale = scale
            camera.location = focus + Vector(direction).normalized()*3
            camera.rotation_euler = (focus-camera.location).to_track_quat("-Z","Y").to_euler()
            tile = HERE / ".runtime" / f"render_{name}_{index}.png"
            scene.render.filepath = str(tile)
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(str(tile), check_existing=False)
            pixels = np.empty(width*height*4,np.float32)
            image.pixels.foreach_get(pixels)
            row,col = divmod(index,cols)
            y,x = (rows-1-row)*(height+padding),col*(width+padding)
            result[y:y+height,x:x+width] = pixels.reshape(height,width,4)
            bpy.data.images.remove(image)
            tile.unlink()
        image = bpy.data.images.new(name,width=sheet_width,height=sheet_height,alpha=False)
        image.pixels.foreach_set(result.ravel())
        image.filepath_raw = str(HERE / (name+".png"))
        image.file_format = "PNG"
        image.save()
        return dict(file=name+".png", frame=frame, directions=angles, resolution=[sheet_width,sheet_height],
                    sha256=FIT["sha"](HERE/(name+".png")))

    views = {}
    if mode in ("all","rest","preview"):
        name = "preview" if mode=="preview" else "six_view"
        views["rest"] = sheet(name,"rest",1.,REST,2,3,528,416,.674)
    if mode in ("all","actions"):
        aggregate = json.loads((HERE/"motion_check.json").read_text())
        assert aggregate["garment_sha256"] == FIT["sha"](source)
        for clip, angles in ACTION.items():
            poses = aggregate["clips"][clip]
            frame = poses["deepest_frame"]
            views[clip] = sheet(clip,clip,frame,angles,1,2,640,600,.63)
            views[clip]["signed_m"] = poses["minimum_signed_m"]
    manifest = HERE / "render_manifest.json"
    if manifest.is_file() and mode in ("actions","rest"):
        old = json.loads(manifest.read_text())
        if old["garment_sha256"] == FIT["sha"](source):
            views = {**old["views"], **views}
    if mode != "preview":
        FIT["write_json"](manifest,dict(garment_sha256=FIT["sha"](source),engine="Cycles CPU",
                                       samples=scene.cycles.samples,views=views))


if __name__ == "__main__":
    render(*sys.argv[sys.argv.index("--")+1:])
