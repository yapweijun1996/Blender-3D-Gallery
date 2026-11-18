"""CPU studio photography of the primary catalog GLB, with a fitted orthographic camera."""
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import subprocess

import bpy
from mathutils import Vector


def aim(obj, target):
    obj.rotation_euler = (target-obj.location).to_track_quat("-Z","Y").to_euler()


def studio(folder: Path, spec, low):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = folder/"exports"/("lod1.glb" if low else "optimized.glb")
    bpy.ops.import_scene.gltf(filepath=str(source))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 5
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("Soft dove-grey studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.41,.45,.49,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .7
    w,h,d = spec["anchor"]["envelope_whd_m"]
    centre = Vector((0,0,.50*h))
    size = max(w,h,d)
    points = [Vector((x,y,z)) for x,y,z in product((-.5*w,.5*w),(-.5*d,.5*d),(0,h))]
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.003))
    floor = bpy.data.materials.new("Studio stone")
    floor.diffuse_color = (.22,.247,.252,1)
    bpy.context.object.data.materials.append(floor)
    for name,pos,power,diameter,color in [
        ("Softbox",(-1.6,-2,2.5),105,1.55,(1,.90,.78)),
        ("Window",(1.7,-.8,1.4),62,1.75,(.79,.91,1)),
        ("Rim",(.75,1.5,1.9),130,1.30,(1,.95,.86))]:
        bpy.ops.object.light_add(type="AREA",location=centre+Vector(pos)*size)
        obj = bpy.context.object
        obj.name = name
        obj.data.energy = power*size*size
        obj.data.shape = "DISK"
        obj.data.size = diameter*size
        obj.data.color = color
        aim(obj,centre)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    scene.camera = camera
    camera.data.type = "ORTHO"
    output = folder/("reports" if low else "previews")
    output.mkdir(exist_ok=True)
    views = [("low-393",(.12,-1,.12))] if low else [
        ("hero",(.42,-1,.28)),("front",(0,-1,.035)),("side",(1,-.015,.04)),("3q",(-.8,-1,.46))]
    hashes = {}
    for view,direction in views:
        if spec["slot"]=="S15" and view=="hero":
            direction = (-.63,-1,.36)
        if spec["slot"]=="S02":
            direction = (direction[0],direction[1],-abs(direction[2])-.10)
            bpy.data.objects["Plane"].hide_render = True
        camera.location = centre+Vector(direction).normalized()*size*4
        aim(camera,centre)
        rot = camera.rotation_euler.to_matrix().transposed()
        local = [rot@(p-centre) for p in points]
        x0,x1 = min(v.x for v in local),max(v.x for v in local)
        y0,y1 = min(v.y for v in local),max(v.y for v in local)
        scene.render.resolution_x = scene.render.resolution_y = 393 if low else 512
        camera.data.ortho_scale = max(x1-x0,y1-y0)*1.13
        png = output/(view+".png")
        scene.render.filepath = str(png)
        bpy.ops.render.render(write_still=True)
        if low:
            hashes[str(png.relative_to(folder))] = sha256(png.read_bytes()).hexdigest()
            continue
        subprocess.run(["cwebp","-quiet","-q","86",str(png),"-o",str(png.with_suffix(".webp"))],check=True)

        for image in (png,png.with_suffix(".webp")):
            hashes[str(image.relative_to(folder))] = sha256(image.read_bytes()).hexdigest()
    return {"source":str(source.relative_to(folder)),"sha256":sha256(source.read_bytes()).hexdigest(),"views":hashes}


def render_views(folder,spec):
    records = [studio(folder,spec,low) for low in (False,True)]
    (folder/"reports"/"previews.json").write_text(json.dumps(records,indent=2)+"\n")
