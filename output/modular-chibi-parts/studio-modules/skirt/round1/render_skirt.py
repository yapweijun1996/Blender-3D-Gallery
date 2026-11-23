"""Render the exported skirt on the neutral master and minimum-clearance poses."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_skirt import GLB, HERE, WORK, coords, digest, import_exported, load_actions, set_pose, write_json

VIEWS = (
    ("front", (0,-1,0)), ("front three-quarter", (.78,-1,.16)), ("right", (1,0,0)),
    ("back", (0,1,0)), ("back three-quarter", (-.78,1,.16)), ("left", (-1,0,0)),
)
POSES = (("run",(.78,-1,.23)),("sit_idle",(.88,-1,.54)),("take_item",(-.67,-1,.26)))


def studio(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Review backdrop")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.52,.60,.71,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .53
    focus = Vector((0,0,.35))
    for name, xyz, energy, size in (
        ("Key",(-.66,-1.22,1.32),65,1.40),
        ("Fill",(.76,-.25,.72),25,1.0),
        ("Rim",(.27,1.12,1.04),44,1.10),
    ):
        data = bpy.data.lights.new(name,"AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        light = bpy.data.objects.new(name,data)
        scene.collection.objects.link(light)
        light.location = xyz
        light.rotation_euler = (focus-light.location).to_track_quat("-Z","Y").to_euler()
    data = bpy.data.cameras.new("Review orthographic")
    data.type = "ORTHO"
    camera = bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def run(draft=False):
    model_path = WORK/"draft.glb" if draft else GLB
    scene,arm,body,garment = import_exported(model_path)
    camera = studio(scene)
    glb_hash = digest(model_path)
    views = []
    if not draft:
        report = json.loads((HERE/"motion_check.json").read_text())
        assert report["garment_sha256"] == glb_hash
        actions = load_actions(scene)

    def capture(path, label, clip, frame, center, direction, width, size):
        camera.data.ortho_scale = width
        camera.location = Vector(center) + Vector(direction).normalized()*3
        camera.rotation_euler = (Vector(center)-camera.location).to_track_quat("-Z","Y").to_euler()
        scene.render.resolution_x = scene.render.resolution_y = size
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        views.append({"file":path.name,"view":label,"clip":clip,"frame":frame,
                      "direction":direction,"width_m":width})

    neutral = (0.,-.02,.345)
    if draft:
        capture(WORK/"draft.png","front","rest",1,neutral,(0.,-1.,.16),.43,560)
        return
    size, gap = 480, 6
    sheet = np.full((2*size+gap,3*size+2*gap,4),(.22,.25,.28,1),dtype=np.float32)
    for i,(label,direction) in enumerate(VIEWS):
        path = WORK/f"cell_{i}.png"
        capture(path,label,"rest",1,neutral,direction,.45,size)
        image = bpy.data.images.load(str(path))
        data = np.empty(size*size*4,dtype=np.float32)
        image.pixels.foreach_get(data)
        bpy.data.images.remove(image)
        path.unlink()
        r,c = divmod(i,3)
        x,y = c*(size+gap),(1-r)*(size+gap)
        sheet[y:y+size,x:x+size] = data.reshape(size,size,4)
        views[-1].update(file="six_view.png",row=r+1,column=c+1)
    image = bpy.data.images.new("Six views",width=sheet.shape[1],height=sheet.shape[0],alpha=True)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(HERE/"six_view.png")
    image.file_format = "PNG"
    image.save()
    for name,direction in POSES:
        row = report["results"][name]
        frame = row["minimum_frame"]
        set_pose(scene,arm,actions[name],frame)
        points = coords(garment,evaluated=True)
        center = .5*(points.min(axis=0)+points.max(axis=0))
        center[2] += .067
        capture(HERE/(name+".png"),"minimum signed clearance",name,frame,center,
                direction,.62 if name=="sit_idle" else .64,720)
        views[-1]["min_signed_m"] = row["minimum_m"]
    for view in views:
        view["sha256"] = digest(HERE/view["file"])
    assert digest(model_path) == glb_hash
    write_json("render_manifest.json",{"glb_sha256":glb_hash,"renderer":"Cycles CPU",
                                       "samples":scene.cycles.samples,"views":views})


if __name__ == "__main__":
    run("draft" in sys.argv[sys.argv.index("--")+1:])
